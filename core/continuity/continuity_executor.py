#!/usr/bin/env python3
"""
CONTINUITY OF OPERATIONS EXECUTOR
Autonomous agent spawning for deferred alerts. Survives YOGA offline.

Architecture:
1. Monitor hale_state.json deferred_alerts
2. On trigger condition met (date, dependency), spawn headless Claude
3. Log execution locally (continuity_log.jsonl)
4. On network restore, report results via email + Telegram
5. Zero external dependency for task evaluation
"""

import json
import os
from pathlib import Path
from datetime import datetime
import time

THUNDERBIRD_ROOT = Path("/home/john/Thunderbird")
CONTINUITY_DIR = THUNDERBIRD_ROOT / "core" / "continuity"
CONTINUITY_DIR.mkdir(parents=True, exist_ok=True)

CONTINUITY_LOG = CONTINUITY_DIR / "continuity_log.jsonl"
HALE_STATE = THUNDERBIRD_ROOT / "hale_state.json"

# In-flight spawn guard: a triggered alert may take minutes for the headless
# Claude to write its result file, but poll_deferred_alerts() runs every 30s.
# Without this guard the loop re-spawned a fresh Claude every cycle for the same
# alert — dozens of stacked subprocess trees in this service's cgroup drove the
# OOM kills (8G swap peak per cgroup). We persist the spawned PID per alert and
# refuse to re-spawn while that PID is alive; SPAWN_RETRY_COOLDOWN is only a
# backstop for a spawn that died without producing a result.
SPAWN_MARKER_SUFFIX = ".spawn"
SPAWN_RETRY_COOLDOWN = 3600  # seconds before retrying a dead-and-resultless spawn


def _marker_path(alert_id):
    return CONTINUITY_DIR / "results" / f"{alert_id}{SPAWN_MARKER_SUFFIX}"


def _pid_alive(pid):
    """True if the process is still running (signal 0 is a no-op liveness probe)."""
    if not pid:
        return False
    try:
        os.kill(int(pid), 0)
        return True
    except (ProcessLookupError, ValueError):
        return False
    except PermissionError:
        return True  # exists but owned differently — treat as alive


def _reap_children():
    """Reap finished detached spawns so they do not linger as zombies."""
    while True:
        try:
            pid, _ = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            break
        if pid == 0:
            break


def _record_spawn(alert_id, pid):
    """Persist the spawned PID + timestamp so the guard survives a service restart."""
    _marker_path(alert_id).write_text(
        json.dumps({"pid": pid, "timestamp": datetime.now().isoformat()})
    )


def _clear_marker(alert_id):
    marker = _marker_path(alert_id)
    if marker.exists():
        try:
            marker.unlink()
        except OSError:
            pass


def spawn_in_flight(alert_id):
    """True if a prior spawn for this alert is still running, or died too recently
    to retry. Prevents the 30s re-spawn runaway that caused the OOM cascade."""
    marker = _marker_path(alert_id)
    if not marker.exists():
        return False
    try:
        data = json.loads(marker.read_text())
    except Exception:
        return False
    if _pid_alive(data.get("pid")):
        return True  # still working — do not stack a second Claude
    # Process is gone but no result yet: rate-limit the retry.
    try:
        age = (datetime.now() - datetime.fromisoformat(data.get("timestamp"))).total_seconds()
    except Exception:
        return False
    return age < SPAWN_RETRY_COOLDOWN


def load_hale_state():
    """Load current deferred alerts from hale_state.json"""
    try:
        with open(HALE_STATE) as f:
            state = json.load(f)
        return state.get("deferred_alerts", [])
    except Exception as e:
        log_execution("ERROR", f"Failed to load hale_state: {e}")
        return []


def check_trigger(alert):
    """Evaluate if alert trigger condition is met"""
    trigger_date = alert.get("trigger_date")
    condition_type = alert.get("condition_type", "date")

    if condition_type == "date":
        return trigger_date <= datetime.now().isoformat()
    elif condition_type == "date_and_client_status":
        # For now, assume client_returned if date passed
        return trigger_date <= datetime.now().isoformat()
    elif condition_type == "date_and_dependency":
        # Check dependency status in alert
        dep = alert.get("dependency")
        # TODO: Implement dependency resolver
        return False
    return False


def build_spawn_prompt(alert):
    """Create execution prompt for headless Claude spawn"""
    alert_id = alert.get("id", "UNKNOWN")
    message = alert.get("message", "")
    mission_ref = alert.get("mission_ref", "")

    prompt = f"""CONTINUITY MISSION: {alert_id}
OFFLINE EXECUTION — Autonomous evaluation and recommendation

{message}

WRITE /home/john/Thunderbird/core/continuity/results/{alert_id}_result.json

Instructions:
1. Evaluate the alert condition carefully
2. Determine if immediate action is needed or if this can wait
3. If action needed: outline specific steps (do NOT execute client sends)
4. Return structured JSON with keys: decision, reasoning, recommended_action, blocker (if any)

Result MUST be valid JSON in the specified file."""

    return prompt


def spawn_continuity_claude(alert):
    """Spawn headless Claude (background, foolproof wrapper per SO 24 APR 2026)
    to evaluate alert"""
    alert_id = alert.get("id", "UNKNOWN")

    # Ensure results dir exists
    results_dir = CONTINUITY_DIR / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    # Build prompt (already contains a WRITE [PATH] instruction, required for background mode)
    prompt = build_spawn_prompt(alert)

    from core.ai_infra.thunderbird_headless_spawn import spawn_headless_claude

    result = spawn_headless_claude(
        prompt=prompt,
        output_file=str(results_dir / f"{alert_id}_result.json"),
        model="claude-haiku-4-5-20251001",
        task_name=f"continuity-{alert_id}",
        background=True,
    )

    if result.get("status") == "SPAWNED":
        _record_spawn(alert_id, result.get("pid"))
        log_execution("SPAWN", f"Headless Claude spawned for {alert_id} (PID {result.get('pid')})")
        return True
    else:
        log_execution("ERROR", f"Failed to spawn Claude for {alert_id}: {result}")
        return False


def log_execution(status, message):
    """Append execution log entry"""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "status": status,
        "message": message
    }
    with open(CONTINUITY_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


def poll_deferred_alerts():
    """Main loop: check deferred alerts, spawn as needed"""
    alerts = load_hale_state()
    _reap_children()  # clean up any finished detached spawns before evaluating

    for alert in alerts:
        alert_id = alert.get("id")
        if not alert_id:
            continue

        # Skip if already processed
        result_file = CONTINUITY_DIR / "results" / f"{alert_id}_result.json"
        if result_file.exists():
            _clear_marker(alert_id)  # result arrived — drop the in-flight marker
            continue

        # Check trigger
        if check_trigger(alert):
            # GUARD: never stack a second spawn while one is still in flight (or
            # died within the retry cooldown). This is the fix for the OOM runaway.
            if spawn_in_flight(alert_id):
                continue
            log_execution("TRIGGER", f"Alert {alert_id} triggered: {alert.get('message', '')[:50]}")
            spawn_continuity_claude(alert)
            time.sleep(0.5)  # Brief pause between spawns


def main():
    log_execution("START", "Continuity executor online")

    while True:
        try:
            poll_deferred_alerts()
        except Exception as e:
            log_execution("ERROR", f"Poll cycle failed: {e}")

        time.sleep(30)  # Poll every 30 seconds


if __name__ == "__main__":
    main()
