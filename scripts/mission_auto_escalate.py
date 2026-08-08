#!/usr/bin/env python3
"""Mission Auto-Escalate — P0/P1 missions idle >2h get rerouted to a Hale seat.

Pilot #3 (RT-PILOT3-ESCALATE). Cap: one escalation per mission, ever
(escalation_count >= 1 blocks re-escalation). Read-only by default
(--dry-run); --live mutates mission_board.json and reports via
core.comms.commander_channel.notify() at WINDOW urgency.

Import-reuses OpsCenter/mission_board_sync.py for lock/load/save. Does NOT
edit or modify any other file.
"""

import argparse
import fcntl
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from OpsCenter.mission_board_sync import (
    acquire_lock,
    load_board,
    save_board,
)

IDLE_HOURS = 2
ESCALATE_TO = "Hale"
OPEN_STATUSES = ("active", "in_progress", "pending_review", "in_coordination")
WATCH_PRIORITIES = ("P0", "P1")


def parse_dt(value):
    """Naive/aware-safe parse. Naive -> UTC; 'Z' -> +00:00."""
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def is_escalatable(m):
    """Status+priority open, parses, idle > IDLE_HOURS, escalation cap not hit."""
    if m.get("status") not in OPEN_STATUSES:
        return False
    if m.get("priority") not in WATCH_PRIORITIES:
        return False
    if m.get("escalation_count", 0) >= 1:
        return False
    try:
        updated = parse_dt(m.get("updated_at"))
    except (ValueError, TypeError):
        return False
    return (datetime.now(timezone.utc) - updated).total_seconds() > IDLE_HOURS * 3600


def escalate_mission(mut, now, old_owner):
    """Apply the escalation mutation to a copy of the mission."""
    mut["assigned_to"] = ESCALATE_TO
    mut["escalation_count"] = mut.get("escalation_count", 0) + 1
    mut.setdefault("logs", []).append(
        f"{now.isoformat()}: auto-escalated (idle >2h) — reassigned {old_owner} -> {ESCALATE_TO}"
    )
    return mut


def auto_escalate(dry_run=True):
    """Scan board, escalate idle P0/P1 missions, return report dict."""
    board = load_board()
    missions = board.get("missions", [])
    now = datetime.now(timezone.utc)

    escalated, notify_only, capped_skipped = [], [], []
    mutations = []  # list of mutated mission dicts (only when escalating)

    for m in missions:
        if m.get("escalation_count", 0) >= 1:
            capped_skipped.append(m.get("id"))
            continue
        if m.get("status") not in OPEN_STATUSES or m.get("priority") not in WATCH_PRIORITIES:
            continue
        try:
            updated = parse_dt(m.get("updated_at"))
        except (ValueError, TypeError):
            continue
        if (now - updated).total_seconds() <= IDLE_HOURS * 3600:
            continue

        old_owner = m.get("assigned_to")
        if old_owner == ESCALATE_TO:
            notify_only.append(m.get("id"))
        else:
            mut = escalate_mission(dict(m), now, old_owner)
            escalated.append(mut.get("id"))
            mutations.append(mut)

    if not dry_run and (escalated or notify_only):
        fd = acquire_lock()
        try:
            board = load_board()
            for i, m in enumerate(board.get("missions", [])):
                for mut in mutations:
                    if m.get("id") == mut.get("id"):
                        board["missions"][i] = mut
            save_board(board, fd)
        except Exception:
            from OpsCenter.mission_board_sync import release_lock
            release_lock(fd)
            raise

    return {
        "escalated": escalated,
        "notify_only": notify_only,
        "capped_skipped": capped_skipped,
        "scan_time": now.isoformat(),
    }


def report(report_dict):
    """Send the escalation report to the Commander at WINDOW urgency."""
    from core.comms.commander_channel import notify

    body = []
    if report_dict["escalated"]:
        body.append("**Auto-escalated (idle >2h)**")
        for mid in report_dict["escalated"]:
            body.append(f"- `{mid}` reassigned -> {ESCALATE_TO}")
    if report_dict["notify_only"]:
        body.append(f"\n**Notify-only (already {ESCALATE_TO})**")
        for mid in report_dict["notify_only"]:
            body.append(f"- `{mid}` observed idle >2h")
    if report_dict["capped_skipped"]:
        body.append(f"\n**Skipped (cap already used)**")
        for mid in report_dict["capped_skipped"]:
            body.append(f"- `{mid}`")

    notify(
        kind="ops",
        title=f"Mission auto-escalate scan — {'+'.join(map(str, report_dict['escalated'] or [])) or 'no-op'}",
        body_md="\n".join(body),
        urgency="WINDOW",
        source="mission_auto_escalate",
    )


def main():
    ap = argparse.ArgumentParser(
        description="Auto-escalate P0/P1 missions idle >2h to Hale (cap 1 per mission)."
    )
    ap.add_argument("--live", action="store_true",
                    help="Mutate mission_board.json and send notify(). "
                         "Default (omit) is a read-only dry run printing the report as JSON.")
    args = ap.parse_args()

    result = auto_escalate(dry_run=not args.live)

    if not args.live:
        print(json.dumps(result, indent=2))
        if not (result["capped_skipped"] or result["escalated"] or result["notify_only"]):
            print("nothing to escalate")
        return

    print(json.dumps(result, indent=2))
    if result["escalated"] or result["notify_only"]:
        report(result)
    else:
        print("nothing to escalate")


if __name__ == "__main__":
    main()