#!/usr/bin/env python3
"""
TP Alert Engine — 14-Day Early Warning + Staff Notification
Dreams2Memories Travel, LLC | scripts/tp_alert_engine.py

Runs the TP scheduler with a 14-day horizon, classifies alerts by severity,
writes staff tasks to wing_comms.md, surfaces to opencode_inbox, and logs
to an audit trail. Designed to run via systemd timer every 6 hours.

Usage:
    python3 tp_alert_engine.py                    # Full scan + notification
    python3 tp_alert_engine.py --report-only      # Print to stdout only
    python3 tp_alert_engine.py --client McLeod     # Filter by client
    python3 tp_alert_engine.py --timer             # Silent mode (systemd timer)
"""

import argparse
import json
import logging
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

THUNDERBIRD = Path.home() / "Thunderbird"
sys.path.insert(0, str(THUNDERBIRD))
sys.path.insert(0, str(THUNDERBIRD / "core" / "booking"))

from thunderbird_tp_scheduler import (
    TPStatus,
    scan_all_actionable,
    format_brief,
    scan_dossiers,
    generate_schedule,
    get_actionable_tps,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s TP-ALERT %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(str(THUNDERBIRD / "logs" / "tp_alert_engine.log"), mode="a"),
    ],
)
logger = logging.getLogger("tp_alert")

ALERT_LOG = THUNDERBIRD / "logs" / "tp_alerts.jsonl"
WING_COMMS = THUNDERBIRD / "OpsCenter" / "collaboration" / "wing_comms.md"
OPENCODE_INBOX = THUNDERBIRD / "OpsCenter" / "collaboration" / "opencode_inbox.md"
MISSION_BOARD = THUNDERBIRD / "OpsCenter" / "mission_board.json"


def classify(tp, threshold_days=14):
    today = date.today()
    if tp.status == TPStatus.OVERDUE:
        days_over = (today - tp.deadline).days if tp.deadline else 0
        if days_over >= 30:
            return "CRITICAL"
        if days_over >= 14:
            return "WARNING"
        return "OVERDUE"
    if tp.status == TPStatus.IN_WINDOW:
        days_left = (tp.deadline - today).days if tp.deadline else threshold_days
        if days_left <= threshold_days:
            return "CRITICAL-APPROACHING"
        return "IN-WINDOW"
    if tp.status == TPStatus.DUE:
        return "APPROACHING"
    return "OK"


def build_staff_alert_text(alerts):
    today = date.today()
    lines = [
        "",
        f"## TP ALERT — {today.isoformat()} — AUTO-GENERATED {datetime.now().strftime('%H:%M MT')}",
        "",
        "### CRITICAL (overdue >30d)",
    ]
    critical = [a for a in alerts if a[0] == "CRITICAL"]
    warning = [a for a in alerts if a[0] == "WARNING"]
    overdue = [a for a in alerts if a[0] == "OVERDUE"]
    approaching = [a for a in alerts if a[0] == "CRITICAL-APPROACHING"]
    approaching_soon = [a for a in alerts if a[0] == "APPROACHING"]

    if critical:
        for sev, tp in critical:
            dl = tp.deadline.isoformat() if tp.deadline else "???"
            lines.append(f"- 🔴 **TP {tp.tp_id}** [{tp.client}] — {tp.label}")
            lines.append(f"  Deadline: {dl} | Lead: {tp.tp_def.staff_lead}")
            lines.append(f"  Action: {tp.tp_def.staff_lead} — escalate immediately")
    else:
        lines.append("- None")

    lines.append("")
    lines.append("### WARNING (overdue 14-30d)")
    if warning:
        for sev, tp in warning:
            dl = tp.deadline.isoformat() if tp.deadline else "???"
            lines.append(f"- 🟠 **TP {tp.tp_id}** [{tp.client}] — {tp.label}")
            lines.append(f"  Deadline: {dl} | Lead: {tp.tp_def.staff_lead}")
    else:
        lines.append("- None")

    lines.append("")
    lines.append("### CRITICAL-APPROACHING (≤14d to deadline)")
    if approaching:
        for sev, tp in approaching:
            dl = tp.deadline.isoformat() if tp.deadline else "???"
            days = (tp.deadline - today).days if tp.deadline else 0
            lines.append(f"- 🟡 **TP {tp.tp_id}** [{tp.client}] — {tp.label}")
            lines.append(f"  Deadline: {dl} (T-{days}d) | Lead: {tp.tp_def.staff_lead}")
            lines.append(f"  Task: {tp.tp_def.staff_lead} — begin work")
    else:
        lines.append("- None")

    lines.append("")
    lines.append("### APPROACHING (due within 14d)")
    if approaching_soon:
        for sev, tp in approaching_soon:
            dl = tp.deadline.isoformat() if tp.deadline else "???"
            days = (tp.deadline - today).days if tp.deadline else 0
            lines.append(f"- 🔵 **TP {tp.tp_id}** [{tp.client}] — {tp.label}")
            lines.append(f"  Deadline: {dl} (T-{days}d) | Lead: {tp.tp_def.staff_lead}")
    else:
        lines.append("- None")

    lines.append("")
    lines.append("### OVERDUE (<14d, recent)")
    if overdue:
        for sev, tp in overdue:
            dl = tp.deadline.isoformat() if tp.deadline else "???"
            lines.append(f"- 🔴 **TP {tp.tp_id}** [{tp.client}] — {tp.label}")
            lines.append(f"  Deadline: {dl} | Lead: {tp.tp_def.staff_lead}")
    else:
        lines.append("- None")

    lines.append("")
    lines.append("---")
    lines.append("*Auto-generated by TP Alert Engine — next scan in 6h*")
    lines.append("")
    return "\n".join(lines)


def build_inbox_task(alerts):
    today = date.today()
    critical_count = len([a for a in alerts if a[0] in ("CRITICAL", "WARNING", "CRITICAL-APPROACHING")])
    return f"""
---
## TASK: TP-ALERT-{today.strftime('%Y%m%d')}
status: UNREAD
from: TP Alert Engine
priority: {"P0" if critical_count > 0 else "P1"}
stakes: {"high" if critical_count > 0 else "medium"}
task: |
  TP Alert Engine ran {today.isoformat()} at {datetime.now().strftime('%H:%M MT')}.
  {critical_count} high-severity touchpoints require attention.
  Review wing_comms.md for full staff tasking.
  Expected output: Review and acknowledge in wing_comms.md
"""


def write_wing_comms(alert_text):
    WING_COMMS.parent.mkdir(parents=True, exist_ok=True)
    with open(WING_COMMS, "a") as f:
        f.write(alert_text)
        f.write("\n")
    logger.info(f"Wrote alerts to wing_comms.md")


def write_opencode_task(task_text):
    OPENCODE_INBOX.parent.mkdir(parents=True, exist_ok=True)
    with open(OPENCODE_INBOX, "a") as f:
        f.write(task_text)
        f.write("\n")
    logger.info(f"Wrote task to opencode_inbox.md")


def log_alerts(alerts):
    ALERT_LOG.parent.mkdir(parents=True, exist_ok=True)
    entries = []
    for sev, tp in alerts:
        entries.append({
            "timestamp": datetime.now().isoformat(),
            "severity": sev,
            "client": tp.client,
            "tp_id": tp.tp_id,
            "label": tp.label,
            "deadline": tp.deadline.isoformat() if tp.deadline else None,
            "status": tp.status.value,
            "staff_lead": tp.tp_def.staff_lead,
        })
    for entry in entries:
        with open(ALERT_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")
    logger.info(f"Logged {len(entries)} alerts to tp_alerts.jsonl")


def run_scan(client_filter=None, horizon=14, report_only=False, timer=False):
    today = date.today()
    logger.info(f"Scanning with horizon={horizon}d, client={client_filter or 'all'}")

    try:
        actionable = scan_all_actionable(
            horizon_days=horizon,
            today=today,
            client_filter=client_filter,
        )
    except Exception as e:
        logger.error(f"TP scan failed: {e}")
        return

    alerts = [(classify(tp, horizon), tp) for tp in actionable]

    if report_only:
        print(format_brief(actionable, today))
        print()
        print("=== SEVERITY CLASSIFICATION ===")
        for sev, tp in alerts:
            print(f"[{sev:22}] TP {tp.tp_id:5} {tp.client:25} {tp.label}")
        return

    alert_text = build_staff_alert_text(alerts)
    task_text = build_inbox_task(alerts)

    if timer:
        logger.info(f"Timer mode — {len(alerts)} actionable TPs, {len([a for a in alerts if a[0] in ('CRITICAL','WARNING','CRITICAL-APPROACHING')])} high-severity")

    write_wing_comms(alert_text)
    write_opencode_task(task_text)
    log_alerts(alerts)

    logger.info(f"Alert engine complete — {len(alerts)} actionable TPs processed")
    print(format_brief(actionable, today))  # Always print brief for visibility


def main():
    parser = argparse.ArgumentParser(description="TP Alert Engine — 14-Day Early Warning + Staff Notification")
    parser.add_argument("--client", help="Filter by client name (partial match)")
    parser.add_argument("--horizon", type=int, default=14, help="Alert horizon in days (default 14)")
    parser.add_argument("--report-only", action="store_true", help="Print to stdout only, no writes")
    parser.add_argument("--timer", action="store_true", help="Silent timer mode (still writes, less verbose)")
    args = parser.parse_args()

    run_scan(
        client_filter=args.client,
        horizon=args.horizon,
        report_only=args.report_only,
        timer=args.timer,
    )


if __name__ == "__main__":
    main()
