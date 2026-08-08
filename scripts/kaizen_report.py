#!/usr/bin/env python3
"""KAZEN status report — mechanical assembly from real state. Read-only.

Reads:
  OpsCenter/mission_board.json        (missions list)
  OpsCenter/delegation_outcomes.jsonl (JSONL, one verdict row per line)

Never writes to either file. --dry-run (default) prints a human-scannable
status board with === section headers and - bullets. --live prints the same
and sends one notify() to the Commander channel.
"""
import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

MISSION_BOARD = Path("OpsCenter/mission_board.json")
DELEGATION_OUTCOMES = Path("OpsCenter/delegation_outcomes.jsonl")

STATUS_ORDER = [
    "pending_review", "in_progress", "cancelled", "active",
    "completed", "rolled_up", "closed", "in_coordination",
]
OPEN_ACTIVE_PROGRESS = ("active", "in_progress", "in_coordination", "pending_review")
REPORT_VERDICTS = ("PASS", "DISCREPANCY", "UNVERIFIED")


def load_missions():
    data = json.loads(MISSION_BOARD.read_text())
    return data["missions"]


def read_outcomes():
    """Defensive JSONL read — silent skip of malformed lines.

    Mirrors the convention in core/staffing/delegation_outcomes.py's own
    _read_rows(): one json.loads per line, malformed lines skipped.
    """
    if not DELEGATION_OUTCOMES.exists():
        return []
    rows = []
    for line in DELEGATION_OUTCOMES.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def truncate(text, n=150):
    text = text or ""
    if len(text) <= n:
        return text
    return text[: n - 3] + "..."


def build_report(missions, outcomes, now=None):
    now = now or datetime.now(timezone.utc)
    window_start = now - timedelta(hours=24)

    lines = []

    lines.append("=== KAIZEN STATUS REPORT ===")
    lines.append("")

    # Mission status counts
    lines.append("=== MISSIONS BY STATUS ===")
    counts = {}
    for mission in missions:
        counts[mission.get("status")] = counts.get(mission.get("status"), 0) + 1
    for status in STATUS_ORDER:
        lines.append(f"- {status}: {counts.get(status, 0)}")
    lines.append("")

    # P0/P1 still-open-priority missions
    lines.append("=== OPEN P0/P1 MISSIONS (matters, still open) ===")
    open_priority = [
        m for m in missions
        if m.get("priority") in ("P0", "P1")
        and m.get("status") in OPEN_ACTIVE_PROGRESS
    ]
    for m in sorted(open_priority, key=lambda x: x.get("priority", "P2")):
        lines.append(f"- [{m.get('priority')}] {m.get('id')}: {m.get('title')} "
                     f"(assigned: {m.get('assigned_to')}, status: {m.get('status')})")
    lines.append("")

    # Delegation verdicts, last 24h
    lines.append("=== DELEGATION VERDICTS (LAST 24H) ===")
    verdicts = {}
    issues = []
    for row in outcomes:
        ts = row.get("ts")
        if not ts:
            continue
        try:
            row_time = datetime.fromisoformat(ts)
        except (ValueError, TypeError):
            continue
        if row_time < window_start:
            continue
        verdict = row.get("verdict")
        if verdict in REPORT_VERDICTS:
            verdicts[verdict] = verdicts.get(verdict, 0) + 1
        if verdict in ("DISCREPANCY", "UNVERIFIED"):
            issues.append(row)

    for verdict in REPORT_VERDICTS:
        lines.append(f"- {verdict}: {verdicts.get(verdict, 0)}")

    if issues:
        lines.append("")
        lines.append("=== DISCREPANCY / UNVERIFIED ROWS (LAST 24H) ===")
        for row in sorted(issues, key=lambda r: r.get("ts", "")):
            lines.append(f"- [{row.get('seat')}] {row.get('ticket_id')}: "
                         f"{truncate(row.get('discrepancy_detail'))}")
    else:
        lines.append("")
        lines.append("(no DISCREPANCY/UNVERIFIED rows in last 24h)")

    return "\n".join(lines) + "\n"


def parse_args():
    p = argparse.ArgumentParser(
        description="Mechanical KAIZEN status report (read-only).")
    p.add_argument("--live", action="store_true",
                   help="Print report and send one notify() (ops/WINDOW). "
                        "Default is --dry-run: print only.")
    return p.parse_args()


def main():
    args = parse_args()

    missions = load_missions()
    outcomes = read_outcomes()

    text = build_report(missions, outcomes)
    print(text, end="")

    if args.live:
        from core.comms.commander_channel import notify
        notify(kind="ops", title="KAIZEN Status Report", body_md=text,
               urgency="WINDOW", dedup_key="kaizen-report-daily")

    return 0


if __name__ == "__main__":
    sys.exit(main())