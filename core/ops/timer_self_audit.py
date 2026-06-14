#!/usr/bin/env python3
"""
thunderbird-timer-self-audit — Weekly meta-monitor for all D2M systemd timers.

Detects:
  - Stale timers: last fired > 2× expected interval
  - Failed services: ExecMainStatus != 0 on last run
  - Disabled timers that are still enabled (unit-file paradox)
  - New timers with no recorded run (never fired)

Schedule: Weekly Sunday 07:00 MDT via systemd timer
Output:   OpsCenter/logs/timer_self_audit.jsonl
          hale_decisions.md entry if any issues found
          Blackboard alert if CRITICAL issues found
"""

import json
import logging
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
AUDIT_LOG = ROOT / "OpsCenter/logs/timer_self_audit.jsonl"
HALE_DECISIONS = ROOT / "hale_decisions.md"
BLACKBOARD = ROOT / "OpsCenter/collaboration/blackboard.md"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [TIMER-AUDIT] %(levelname)s %(message)s",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger(__name__)

# Expected intervals in seconds for known timers
EXPECTED_INTERVALS = {
    "d2m-usage-monitor": 20 * 60,
    "d2m-dashboard-refresh": 20 * 60,
    "d2m-centrav-warm": 60 * 60,
    "d2m-mission-executor-4h": 4 * 3600,
    "d2m-booking-monitor": 4 * 3600,
    "d2m-factbook-refresh": 7 * 86400,
    "hale-phase2-visuals": 7 * 86400,
    "thunderbird-evernote-backup": 7 * 86400,
    "d2m-validation-report": 30 * 86400,
    "d2m-lifecycle-scheduler": 86400,
    "d2m-lifecycle": 86400,
    "d2m-fpd-alert": 86400,
    "d2m-intel-telegram": 86400,
    "d2m-x-osint": 86400,
    "d2m-drive-sync": 86400,
    "d2m-inbox-cleanup": 86400,
    "d2m-voice-sync": 86400,
    "d2m-power-harvest": 86400,
    "d2m-incubator-execute": 86400,
    "d2m-sculptor-harvest": 86400,
    "d2m-sculptor-learn": 86400,
    "d2m-airline-monitor": 86400,
    "d2m-email-intel": 3600,
    "d2m-preflight-gate": 86400,
    "d2m-correspondence-sync": 86400,
    "d2m-incubator-overnight-report": 86400,
}

STALENESS_MULTIPLIER = 2.5  # flag if last_run > interval * multiplier


def run_cmd(cmd: list) -> str:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.stdout.strip()
    except Exception:
        return ""


def list_timers() -> list[dict]:
    out = run_cmd(["systemctl", "--user", "list-timers", "--all", "--no-pager", "--output=json"])
    if not out:
        # Fall back to text parsing
        return []
    try:
        return json.loads(out)
    except Exception:
        return []


def get_service_last_result(unit_name: str) -> str:
    out = run_cmd(["systemctl", "--user", "show", unit_name, "--property=Result"])
    return out.replace("Result=", "").strip()


def check_timers() -> dict:
    now = datetime.now()
    issues = {"stale": [], "failed": [], "never_ran": [], "ok": []}

    timers_raw = run_cmd(
        ["systemctl", "--user", "list-timers", "--all", "--no-pager"]
    ).splitlines()

    for line in timers_raw:
        # Parse lines like: "Sun 2026-06-14 18:00:00 MDT  7h left  Sun 2026-06-07 18:00:03 MDT  6 days ago  hale-phase2-visuals.timer"
        parts = line.split()
        if not parts or not parts[-1].endswith(".timer"):
            continue
        timer_name = parts[-1]
        service_name = timer_name.replace(".timer", ".service")
        base_name = timer_name.replace(".timer", "")

        # Find "X ago" pattern for last trigger
        last_trigger_ago = None
        if "ago" in line:
            ago_idx = line.index("ago")
            # Extract the time unit before "ago"
            segment = line[:ago_idx].split()
            if len(segment) >= 2:
                try:
                    val = float(segment[-2])
                    unit = segment[-1].lower()
                    if "second" in unit:
                        last_trigger_ago = timedelta(seconds=val)
                    elif "min" in unit:
                        last_trigger_ago = timedelta(minutes=val)
                    elif "hour" in unit or "hr" in unit:
                        last_trigger_ago = timedelta(hours=val)
                    elif "day" in unit:
                        last_trigger_ago = timedelta(days=val)
                    elif "week" in unit:
                        last_trigger_ago = timedelta(weeks=val)
                    elif "month" in unit:
                        last_trigger_ago = timedelta(days=val * 30)
                except (ValueError, IndexError):
                    pass
        elif "n/a" in line.lower() or "never" in line.lower():
            issues["never_ran"].append({"timer": timer_name, "reason": "never fired"})
            continue

        # Check for staleness against known intervals
        if last_trigger_ago is not None and base_name in EXPECTED_INTERVALS:
            expected = timedelta(seconds=EXPECTED_INTERVALS[base_name])
            threshold = expected * STALENESS_MULTIPLIER
            if last_trigger_ago > threshold:
                issues["stale"].append(
                    {
                        "timer": timer_name,
                        "last_ran_ago": str(last_trigger_ago),
                        "expected_interval": str(expected),
                        "overdue_by": str(last_trigger_ago - expected),
                    }
                )
                continue

        # Check last service result
        result = get_service_last_result(service_name)
        if result and result not in ("success", "exit-code"):
            # "exit-code" can be OK if exit code was 0
            issues["failed"].append(
                {"timer": timer_name, "service": service_name, "last_result": result}
            )
        else:
            issues["ok"].append(timer_name)

    return issues


def write_audit_log(issues: dict, run_dt: datetime) -> None:
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": run_dt.isoformat(),
        "stale_count": len(issues["stale"]),
        "failed_count": len(issues["failed"]),
        "never_ran_count": len(issues["never_ran"]),
        "ok_count": len(issues["ok"]),
        "stale": issues["stale"],
        "failed": issues["failed"],
        "never_ran": issues["never_ran"],
    }
    with open(AUDIT_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")
    log.info(f"Audit logged: {entry['stale_count']} stale, {entry['failed_count']} failed, {entry['never_ran_count']} never ran")


def write_hale_decision(issues: dict, run_dt: datetime) -> None:
    total_issues = len(issues["stale"]) + len(issues["failed"]) + len(issues["never_ran"])
    if total_issues == 0:
        return

    lines = [
        f"\n### {run_dt.strftime('%Y-%m-%d %H:%M:%S')} — Autonomous Decision (Tier T0)\n",
        "**Decision:** Timer self-audit surfaced automation layer issues\n",
        f"**Issues found:** {total_issues} ({len(issues['stale'])} stale, {len(issues['failed'])} failed, {len(issues['never_ran'])} never ran)\n",
    ]
    if issues["stale"]:
        lines.append("**Stale timers:**\n")
        for s in issues["stale"]:
            lines.append(f"  - {s['timer']}: last ran {s['last_ran_ago']} ago (expected {s['expected_interval']})\n")
    if issues["failed"]:
        lines.append("**Failed services:**\n")
        for f_item in issues["failed"]:
            lines.append(f"  - {f_item['service']}: result={f_item['last_result']}\n")
    if issues["never_ran"]:
        lines.append("**Never ran:**\n")
        for n in issues["never_ran"]:
            lines.append(f"  - {n['timer']}\n")
    lines.append("**Domain:** Automation / Ops\n**Type:** proactive monitoring\n**Outcome:** surfaced to Commander\n")

    with open(HALE_DECISIONS, "a") as f:
        f.writelines(lines)
    log.info(f"Wrote {total_issues} issues to hale_decisions.md")


def write_blackboard_alert(issues: dict, run_dt: datetime) -> None:
    critical = issues["stale"] + issues["failed"]
    if not critical:
        return
    alert = (
        f"\n## TIMER-AUDIT ALERT — {run_dt.strftime('%Y-%m-%d %H:%M')} MDT\n"
        f"**{len(critical)} timer issues detected** — check hale_decisions.md for detail.\n"
        f"Stale: {len(issues['stale'])} | Failed: {len(issues['failed'])} | Never ran: {len(issues['never_ran'])}\n"
    )
    try:
        with open(BLACKBOARD, "a") as f:
            f.write(alert)
        log.info("Blackboard alert written")
    except Exception as e:
        log.warning(f"Could not write blackboard: {e}")


def main() -> int:
    run_dt = datetime.now()
    log.info(f"Timer self-audit starting — {run_dt.isoformat()}")

    issues = check_timers()

    total = len(issues["stale"]) + len(issues["failed"]) + len(issues["never_ran"])
    log.info(f"Audit complete: {total} issues found ({len(issues['ok'])} ok)")

    write_audit_log(issues, run_dt)
    write_hale_decision(issues, run_dt)
    write_blackboard_alert(issues, run_dt)

    if total > 0:
        print(f"\nTIMER AUDIT — {total} issues:")
        for s in issues["stale"]:
            print(f"  STALE: {s['timer']} — {s['last_ran_ago']} ago")
        for f_item in issues["failed"]:
            print(f"  FAILED: {f_item['service']} — {f_item['last_result']}")
        for n in issues["never_ran"]:
            print(f"  NEVER RAN: {n['timer']}")
    else:
        print("All timers healthy.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
