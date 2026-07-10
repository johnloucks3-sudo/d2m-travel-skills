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
from pathlib import Path
from datetime import datetime
import time

THUNDERBIRD_ROOT = Path("/home/john/Thunderbird")
CONTINUITY_DIR = THUNDERBIRD_ROOT / "core" / "continuity"
CONTINUITY_DIR.mkdir(parents=True, exist_ok=True)

CONTINUITY_LOG = CONTINUITY_DIR / "continuity_log.jsonl"
HALE_STATE = THUNDERBIRD_ROOT / "hale_state.json"


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

    for alert in alerts:
        alert_id = alert.get("id")
        if not alert_id:
            continue

        # Skip if already processed
        result_file = CONTINUITY_DIR / "results" / f"{alert_id}_result.json"
        if result_file.exists():
            continue

        # Check trigger
        if check_trigger(alert):
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
