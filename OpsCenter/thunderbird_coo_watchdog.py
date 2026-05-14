#!/usr/bin/env python3
"""
Thunderbird COO Watchdog Daemon
================================
Runs on a 10-minute systemd timer. Each invocation:
  1. Scans all Tier 1 (client-critical) and Tier 2 (operational) services
  2. Compares current scan to the previous state snapshot
  3. Runs targeted diagnostics on newly-detected failures
  4. Attempts self-healing (restart) up to 3 times per hour per service
  5. Logs every scan to coo_watchdog.log

Entry point: __main__ runs exactly one iteration, then exits.
The systemd timer handles periodic invocation.

COO Authority: self-healing is fully authorized within the wing.
Commander is alerted (via Telegram) only on unrecoverable Tier 1 failures.
"""

import json
import logging
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

try:
    from OpsCenter.incident_queue import enqueue_incident
except ImportError:
    try:
        from incident_queue import enqueue_incident
    except ImportError:
        def enqueue_incident(event):
            pass

# ─── Config ───────────────────────────────────────────────────────────────────

BASE = Path("/home/john/Thunderbird")
LOG_DIR = BASE / "logs"
STATE_FILE = BASE / "state" / "watchdog_state.json"
PREFLIGHT_STATUS = BASE / "config" / "preflight_status.json"

LOG_FILE = LOG_DIR / "coo_watchdog.log"
COMMANDER_CHAT_ID = "7554895206"

# Max restart attempts per service per hour before escalating to Commander
MAX_RESTARTS_PER_HOUR = 3

# Tier 1: Client-critical — self-heal + alert Commander if unrecoverable
TIER1_SERVICES: dict[str, str] = {
    "hale-draft-engine":       "Lifecycle email drafts for clients",
    "hale-touchpoint-proposer":"Touchpoint scheduling (what's due today)",
    "d2m-lifecycle":           "Lifecycle state scanner",
    "d2m-correspondence-sync": "Sent email → dossier logging",
    "d2m-fpd-alert":           "Final payment date alerts",
    "thunderbird-drive-sync":  "Dossier → Google Drive mirror",
}

# Tier 2: Operational — self-heal, log; no Commander alert
TIER2_SERVICES: dict[str, str] = {
    "hale-brief-generate":    "Morning brief auto-generation",
    "d2m-email-intel":        "Inbound email intelligence",
    "d2m-booking-monitor":    "Booking status change detection",
    "thunderbird-fare-watch": "Fare price monitoring",
    "d2m-mcp":                "MCP server (port 8765)",
    "d2m-tunnel":             "Cloudflared external tunnel",
}

# Port map for "port not responding" diagnostics
SERVICE_PORTS: dict[str, int] = {
    "d2m-mcp":    8765,
    "d2m-tunnel": 8900,
}

# ─── Logging setup ────────────────────────────────────────────────────────────

LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        # No StreamHandler — daemon output goes to log file only
    ],
)
log = logging.getLogger("coo_watchdog")


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_bot_token() -> str:
    """Read TELEGRAM_BOT_TOKEN from .env files."""
    for env_path in [BASE / ".env", BASE / "OpsCenter" / ".env"]:
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("TELEGRAM_BOT_TOKEN="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("TELEGRAM_BOT_TOKEN not found in .env files")


def _run(cmd: list[str], timeout: int = 15) -> tuple[int, str]:
    """Run a subprocess. Returns (returncode, combined stdout+stderr)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = (result.stdout + result.stderr).strip()
        return result.returncode, output
    except subprocess.TimeoutExpired:
        return -1, f"TIMEOUT after {timeout}s"
    except Exception as exc:
        return -1, f"subprocess error: {exc}"


# ─── Core scan functions ───────────────────────────────────────────────────────

def check_service(name: str) -> dict[str, Any]:
    """
    Return current status of a systemd user service.

    Result keys: name, active (bool), status (str), detail (str)
    """
    rc, raw = _run(["systemctl", "--user", "is-active", f"{name}.service"])
    status = raw.splitlines()[0] if raw else "unknown"

    is_healthy = status in ("active", "inactive")  # inactive = oneshot completed OK

    detail = ""
    if status == "failed":
        _, detail = _run(
            ["systemctl", "--user", "show", f"{name}.service",
             "--property=ExecMainStatus,ExecMainStartTimestamp,ActiveEnterTimestamp"],
        )
        detail = detail.replace("\n", " | ")

    return {
        "name":   name,
        "active": is_healthy,
        "status": status,
        "detail": detail,
    }


def check_timer_armed(name: str) -> bool:
    """Return True if the associated .timer unit is active (waiting)."""
    _, raw = _run(["systemctl", "--user", "is-active", f"{name}.timer"])
    return raw.strip() == "active"


def run_health_scan() -> dict[str, Any]:
    """
    Full scan of all Tier 1 and Tier 2 services.

    Returns a scan dict:
    {
        "timestamp": ISO,
        "tier1": {svc_name: {active, status, detail, timer_ok}, ...},
        "tier2": {svc_name: {active, status, detail}, ...},
        "tier1_failures": [svc_name, ...],
        "tier2_failures": [svc_name, ...],
        "all_clear": bool,
    }
    """
    scan: dict[str, Any] = {
        "timestamp":      _now_iso(),
        "tier1":          {},
        "tier2":          {},
        "tier1_failures": [],
        "tier2_failures": [],
        "all_clear":      True,
    }

    for svc in TIER1_SERVICES:
        result = check_service(svc)
        result["timer_ok"] = check_timer_armed(svc)
        scan["tier1"][svc] = result

        if result["status"] == "failed" or not result["timer_ok"]:
            scan["tier1_failures"].append(svc)
            scan["all_clear"] = False
            reason = "service failed" if result["status"] == "failed" else "timer not armed"
            log.warning("T1 FAIL: %s — %s", svc, reason)
        else:
            log.info("T1 OK: %s", svc)

    for svc in TIER2_SERVICES:
        result = check_service(svc)
        scan["tier2"][svc] = result

        if result["status"] == "failed":
            scan["tier2_failures"].append(svc)
            scan["all_clear"] = False
            log.warning("T2 FAIL: %s", svc)
        else:
            log.info("T2 OK: %s", svc)

    return scan


# ─── State management ─────────────────────────────────────────────────────────

def load_previous_state() -> dict[str, Any]:
    """Load the last watchdog state. Returns empty scaffold if file missing or corrupt."""
    empty: dict[str, Any] = {
        "timestamp": None,
        "services": {},
        "last_failure_restart_times": {},
    }
    if not STATE_FILE.exists():
        return empty
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception as exc:
        log.warning("Could not load state file (%s); starting fresh", exc)
        return empty


def save_state(state: dict[str, Any]) -> None:
    """Persist watchdog state to disk."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        STATE_FILE.write_text(json.dumps(state, indent=2))
    except Exception as exc:
        log.error("Could not save state file: %s", exc)


def build_service_summary(scan: dict[str, Any]) -> dict[str, str]:
    """Flatten scan results into {svc_name: status_string} for state comparison."""
    summary: dict[str, str] = {}
    for svc, data in scan["tier1"].items():
        summary[svc] = data["status"] if not data.get("timer_ok", True) else data["status"]
    for svc, data in scan["tier2"].items():
        summary[svc] = data["status"]
    return summary


def compare_states(
    prev: dict[str, Any],
    curr_scan: dict[str, Any],
) -> list[dict[str, str]]:
    """
    Compare previous service map to current scan.

    Returns list of delta dicts:
    {service, prev_status, curr_status, direction}
    direction: "degraded" | "recovered" | "new"
    """
    prev_services: dict[str, str] = prev.get("services", {})
    curr_services = build_service_summary(curr_scan)

    deltas: list[dict[str, str]] = []
    for svc, curr_status in curr_services.items():
        prev_status = prev_services.get(svc)
        if prev_status is None:
            if curr_status == "failed":
                deltas.append({"service": svc, "prev_status": "unknown",
                                "curr_status": curr_status, "direction": "new"})
        elif prev_status != curr_status:
            if curr_status == "failed":
                direction = "degraded"
            elif prev_status == "failed":
                direction = "recovered"
            else:
                direction = "changed"
            deltas.append({"service": svc, "prev_status": prev_status,
                            "curr_status": curr_status, "direction": direction})

    return deltas


# ─── Diagnostics ──────────────────────────────────────────────────────────────

def run_diagnostics(service: str, failure_reason: str) -> str:
    """
    Collect targeted diagnostic output for a failed service.

    Returns a multi-line diagnostic string for logging.
    """
    sections: list[str] = [f"=== DIAGNOSTICS: {service} ({failure_reason}) ==="]

    # 1. systemctl status
    _, status_out = _run(
        ["systemctl", "--user", "status", f"{service}.service", "--no-pager", "-l"],
        timeout=15,
    )
    sections.append(f"--- systemctl status ---\n{status_out[:2000]}")

    # 2. Recent journal entries
    _, journal_out = _run(
        ["journalctl", "--user-unit", f"{service}.service", "-n", "50", "--no-pager"],
        timeout=15,
    )
    sections.append(f"--- journal (last 50 lines) ---\n{journal_out[:3000]}")

    # 3. Port check if applicable
    port = SERVICE_PORTS.get(service)
    if port:
        _, netstat_out = _run(
            ["netstat", "-tuln"],
            timeout=10,
        )
        port_lines = [l for l in netstat_out.splitlines() if str(port) in l]
        sections.append(f"--- port {port} ---\n" + ("\n".join(port_lines) if port_lines else "NOT LISTENING"))

    return "\n".join(sections)


# ─── Self-healing ─────────────────────────────────────────────────────────────

def _restart_count_this_hour(
    service: str,
    restart_times: dict[str, list[str]],
) -> int:
    """Count how many restarts have been attempted in the last 60 minutes."""
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=1)
    times = restart_times.get(service, [])
    recent = [t for t in times if datetime.fromisoformat(t) > cutoff]
    return len(recent)


def attempt_recovery(
    service: str,
    restart_times: dict[str, list[str]],
) -> tuple[bool, dict[str, list[str]]]:
    """
    Try to restart a failed service via systemctl --user.

    Respects MAX_RESTARTS_PER_HOUR cap. Clears "failed" state first.
    Returns (success_bool, updated_restart_times).
    """
    count = _restart_count_this_hour(service, restart_times)
    if count >= MAX_RESTARTS_PER_HOUR:
        log.warning("Recovery SKIPPED for %s — %d restarts already attempted this hour", service, count)
        return False, restart_times

    log.info("Attempting recovery for %s (attempt %d/%d this hour)", service, count + 1, MAX_RESTARTS_PER_HOUR)

    # Clear failed state first
    _run(["systemctl", "--user", "reset-failed", f"{service}.service"])

    # Attempt restart
    rc, output = _run(
        ["systemctl", "--user", "restart", f"{service}.service"],
        timeout=30,
    )

    # Record this attempt
    updated = dict(restart_times)
    updated.setdefault(service, []).append(_now_iso())

    if rc == 0:
        log.info("Recovery SUCCESS: %s restarted", service)
        enqueue_incident({
            "source": "coo_watchdog",
            "event_type": "auto_healed",
            "severity": "info",
            "service": service,
            "auto_heal_succeeded": True,
            "details": f"COO watchdog restarted service successfully",
        })
        return True, updated
    else:
        log.error("Recovery FAILED: %s — rc=%d — %s", service, rc, output[:500])
        return False, updated


# ─── Alerts ───────────────────────────────────────────────────────────────────

def _send_telegram(message: str) -> None:
    """DEPRECATED 2026-05-13: Routed to Hale incident queue."""
    log.info("[muted→hale_queue] %s", str(message)[:200] if message else "")


def send_unrecoverable_alert(
    service: str,
    desc: str,
    diagnostics: str,
    restart_count: int,
) -> None:
    """Alert through Hale incident queue when a Tier 1 service cannot be recovered."""
    enqueue_incident({
        "source": "coo_watchdog",
        "event_type": "unrecoverable",
        "severity": "tier1_critical",
        "service": service,
        "auto_heal_succeeded": False,
        "details": f"Role: {desc}\nRestarts: {restart_count}/{MAX_RESTARTS_PER_HOUR}\n{diagnostics[:1500]}",
    })


# ─── Logging ──────────────────────────────────────────────────────────────────

def log_scan(
    scan: dict[str, Any],
    deltas: list[dict[str, str]],
    diagnostics_map: dict[str, str],
    recovery_map: dict[str, bool],
) -> None:
    """
    Write a structured scan summary line to the watchdog log.

    Format: timestamp | status | services_checked | failures | diagnostics | recoveries
    """
    total = len(TIER1_SERVICES) + len(TIER2_SERVICES)
    t1_fail = len(scan["tier1_failures"])
    t2_fail = len(scan["tier2_failures"])
    failures = t1_fail + t2_fail

    status = "ALL_GREEN" if scan["all_clear"] else f"DEGRADED(T1={t1_fail},T2={t2_fail})"
    delta_str = ";".join(f"{d['service']}:{d['prev_status']}->{d['curr_status']}" for d in deltas) or "none"
    diag_svcs = ",".join(diagnostics_map.keys()) or "none"
    recovery_str = ";".join(f"{s}={'OK' if ok else 'FAIL'}" for s, ok in recovery_map.items()) or "none"

    log.info(
        "SCAN | %s | services=%d | failures=%d | deltas=[%s] | diagnostics=[%s] | recovery=[%s]",
        status, total, failures, delta_str, diag_svcs, recovery_str,
    )


# ─── Main orchestration ───────────────────────────────────────────────────────

def run_watchdog_cycle() -> None:
    """
    Execute one complete watchdog cycle:
      1. Scan all services
      2. Load previous state
      3. Diff
      4. Diagnostics on new failures
      5. Self-healing
      6. Update + save state
      7. Alert Commander on unrecoverable Tier 1 failures
      8. Log scan summary
    """
    log.info("─── COO Watchdog cycle start ───")

    # 1. Current health scan
    scan = run_health_scan()

    # 2. Load previous state
    prev_state = load_previous_state()
    restart_times: dict[str, list[str]] = prev_state.get("last_failure_restart_times", {})

    # 3. Detect deltas
    deltas = compare_states(prev_state, scan)
    if deltas:
        for d in deltas:
            log.info("DELTA: %s %s→%s (%s)", d["service"], d["prev_status"], d["curr_status"], d["direction"])

    # 4 + 5. Diagnostics and recovery on all current failures
    all_failures = scan["tier1_failures"] + scan["tier2_failures"]
    diagnostics_map: dict[str, str] = {}
    recovery_map: dict[str, bool] = {}

    for svc in all_failures:
        # Determine failure reason
        tier1_data = scan["tier1"].get(svc, {})
        tier2_data = scan["tier2"].get(svc, {})
        svc_data = tier1_data or tier2_data

        if svc_data.get("status") == "failed":
            failure_reason = "service failed"
        elif not tier1_data.get("timer_ok", True):
            failure_reason = "timer not armed"
        else:
            failure_reason = "unknown"

        # Collect diagnostics for newly degraded or fresh failures
        is_new_failure = any(
            d["service"] == svc and d["direction"] in ("degraded", "new")
            for d in deltas
        )
        # Also diagnose persistent failures that haven't been diagnosed recently
        if is_new_failure or svc not in prev_state.get("services", {}):
            diag = run_diagnostics(svc, failure_reason)
            diagnostics_map[svc] = diag
            log.debug("Diagnostics for %s:\n%s", svc, diag[:500])

        # Attempt recovery only for "failed" services (not timer issues)
        if svc_data.get("status") == "failed":
            success, restart_times = attempt_recovery(svc, restart_times)
            recovery_map[svc] = success

            # If Tier 1 and still not recovered, alert Commander
            if not success and svc in TIER1_SERVICES:
                count = _restart_count_this_hour(svc, restart_times)
                if count >= MAX_RESTARTS_PER_HOUR:
                    send_unrecoverable_alert(
                        svc,
                        TIER1_SERVICES[svc],
                        diagnostics_map.get(svc, ""),
                        count,
                    )

    # 6. Save updated state
    new_state: dict[str, Any] = {
        "timestamp":                    _now_iso(),
        "services":                     build_service_summary(scan),
        "last_failure_restart_times":   restart_times,
        "last_scan_all_clear":          scan["all_clear"],
        "last_scan_t1_failures":        scan["tier1_failures"],
        "last_scan_t2_failures":        scan["tier2_failures"],
    }
    save_state(new_state)

    # 7. Log structured summary
    log_scan(scan, deltas, diagnostics_map, recovery_map)
    log.info("─── COO Watchdog cycle complete ───")


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    run_watchdog_cycle()
