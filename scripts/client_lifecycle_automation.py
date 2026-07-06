#!/usr/bin/env python3
"""
Client Lifecycle Automation — 10-Touchpoint T-Minus Timeline
Dreams2Memories Travel, LLC | scripts/client_lifecycle_automation.py

Codifies docs/roadmap_status.md § 6 "CLIENT LIFECYCLE AUTOMATION" (NOT STARTED
since Feb roadmaps) as a runnable engine. Computes the 10 canonical T-minus/
T-plus touchpoints from a booking's anchor dates and stages staff tasks into
the existing scheduler (OpsCenter/staff_tasking_schedule.json + claude_inbox.md
/ opencode_inbox.md) per docs/STAFF_TASKING_TIMER_SCHEMA.md.

Anchors:
  booking_date   — drives nothing directly in this 10-TP set (kept for future use)
  embark_date    — drives touchpoints 1-4, 6-7
  fpd            — final payment date; authoritative over the generic T-90
                    estimate when supplied (Financial Hard-Source Rule)
  disembark_date — drives touchpoints 8-10 (defaults to embark_date + 7d)

Usage:
    python3 scripts/client_lifecycle_automation.py --client kuklinski_group \\
        --embark-date 2026-12-17 --fpd 2026-08-15 --booking-date 2026-06-01

    python3 scripts/client_lifecycle_automation.py --test          # mock run
    python3 scripts/client_lifecycle_automation.py --test --stage  # + queue tasks
"""

from __future__ import annotations

import argparse
import fcntl
import json
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

THUNDERBIRD = Path(__file__).resolve().parent.parent
SCHEDULE_FILE = THUNDERBIRD / "OpsCenter" / "staff_tasking_schedule.json"
DEDUP_FILE = THUNDERBIRD / "OpsCenter" / "lifecycle_automation_dedup.json"
CLAUDE_INBOX = THUNDERBIRD / "claude_inbox.md"
OPENCODE_INBOX = THUNDERBIRD / "OpsCenter" / "collaboration" / "opencode_inbox.md"

# ---------------------------------------------------------------------------
# THE 10 CANONICAL TOUCHPOINTS (docs/roadmap_status.md § 6 "Why This Matters")
# ---------------------------------------------------------------------------
# anchor: 'embark' | 'fpd' | 'disembark'
# offset_days: signed offset from the anchor (negative = before)

TOUCHPOINTS = [
    dict(id="L1", name="Anchor Date verification", anchor="embark", offset_days=-270,
         owners="COS", critical=False,
         note="Confirm booking/embark/FPD/disembark anchors are correct in the dossier."),
    dict(id="L2", name="Insurance waiver", anchor="embark", offset_days=-270,
         owners="A9→A3", critical=True,
         note="Pre-existing-condition insurance waiver window — miss this and coverage is void."),
    dict(id="L3", name="Air routing audit", anchor="embark", offset_days=-150,
         owners="A2→A9", critical=True,
         note="Audit routing/fare class before premium inventory disappears."),
    dict(id="L4", name="Specialty dining", anchor="embark", offset_days=-120,
         owners="A2→A6→A3", critical=False,
         note="Book specialty dining before reservation windows fill."),
    dict(id="L5", name="Final payment", anchor="fpd", offset_days=-90,
         owners="A9→A3", critical=True,
         note="Collect final payment / commission audit. Uses actual FPD when supplied, "
              "else embark-90d estimate (flagged as ESTIMATED)."),
    dict(id="L6", name="Itinerary generation", anchor="embark", offset_days=-21,
         owners="A2→A6→A3", critical=False,
         note="Generate final itinerary documents for delivery."),
    dict(id="L7", name="Embark calendar event", anchor="embark", offset_days=0,
         owners="COS", critical=False,
         note="'Client on ship' calendar event / internal marker."),
    dict(id="L8", name="Satisfaction check-in", anchor="disembark", offset_days=1,
         owners="A3", critical=False,
         note="Same-week satisfaction check-in."),
    dict(id="L9", name="Welcome home", anchor="disembark", offset_days=10,
         owners="A6→A3", critical=False,
         note="Welcome-home follow-up."),
    dict(id="L10", name="Future cruise offer", anchor="disembark", offset_days=10,
         owners="A2→A6→A3", critical=False,
         note="Future cruise credit / next-voyage offer."),
]

INBOX_FOR_OWNER_PREFIX = {
    "A2": OPENCODE_INBOX,  # A2 (Dembe/research) lives on the OpenCode side
}


@dataclass
class Touchpoint:
    id: str
    name: str
    anchor: str
    due_date: date
    owners: str
    critical: bool
    note: str
    estimated: bool = False


def compute_timeline(
    embark_date: date,
    fpd: Optional[date] = None,
    disembark_date: Optional[date] = None,
    booking_date: Optional[date] = None,
) -> list[Touchpoint]:
    """Compute due dates for all 10 touchpoints from anchor dates."""
    if disembark_date is None:
        disembark_date = embark_date + timedelta(days=7)

    anchors = {
        "embark": embark_date,
        "disembark": disembark_date,
        "fpd": fpd,  # may be None
    }

    timeline: list[Touchpoint] = []
    for tp in TOUCHPOINTS:
        estimated = False
        if tp["anchor"] == "fpd" and fpd is None:
            # No real FPD on file — fall back to the generic embark-90 estimate.
            anchor_date = embark_date
            offset = -90
            estimated = True
        elif tp["anchor"] == "fpd":
            anchor_date = fpd
            offset = 0
        else:
            anchor_date = anchors[tp["anchor"]]
            offset = tp["offset_days"]

        due = anchor_date + timedelta(days=offset)
        timeline.append(Touchpoint(
            id=tp["id"], name=tp["name"], anchor=tp["anchor"], due_date=due,
            owners=tp["owners"], critical=tp["critical"], note=tp["note"],
            estimated=estimated,
        ))

    timeline.sort(key=lambda t: t.due_date)
    return timeline


# ---------------------------------------------------------------------------
# SCHEDULER WIRING (OpsCenter/staff_tasking_schedule.json)
# ---------------------------------------------------------------------------

def _load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def _write_json_locked(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            f.seek(0)
            f.truncate()
            json.dump(data, f, indent=2, default=str)
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def stage_to_scheduler(client: str, timeline: list[Touchpoint], dry_run: bool = False) -> dict:
    """Append lifecycle tasks to the shared staff_tasking_schedule.json and
    post inbox cards per docs/STAFF_TASKING_TIMER_SCHEMA.md. Idempotent —
    a (client, touchpoint id) pair is only ever staged once (dedup file)."""
    dedup = _load_json(DEDUP_FILE, {})
    schedule = _load_json(SCHEDULE_FILE, {"generated_at": None, "total_tasks": 0,
                                           "critical_count": 0, "tasks": []})
    existing_ids = {t.get("task_id") for t in schedule.get("tasks", [])}

    staged, skipped = [], []
    now = datetime.now().isoformat()

    for tp in timeline:
        task_id = f"LIFECYCLE-{tp.id}-{client}"
        if task_id in dedup or task_id in existing_ids:
            skipped.append(task_id)
            continue

        entry = {
            "task_id": task_id,
            "client": client,
            "phase": "L",
            "touchpoint": tp.id,
            "deliverable": tp.name,
            "owners": tp.owners,
            "draft_due": tp.due_date.isoformat(),
            "send_date": tp.due_date.isoformat(),
            "status": "PENDING",
            "critical": tp.critical,
            "note": tp.note + (" [ESTIMATED — no FPD on file]" if tp.estimated else ""),
        }
        staged.append(entry)

        if not dry_run:
            schedule["tasks"].append(entry)
            dedup[task_id] = now
            _post_inbox_card(client, tp, task_id, now)

    if not dry_run and staged:
        schedule["generated_at"] = now
        schedule["total_tasks"] = len(schedule["tasks"])
        schedule["critical_count"] = sum(1 for t in schedule["tasks"] if t.get("critical"))
        _write_json_locked(SCHEDULE_FILE, schedule)
        _write_json_locked(DEDUP_FILE, dedup)

    return {"staged": staged, "skipped_already_queued": skipped}


def _post_inbox_card(client: str, tp: Touchpoint, task_id: str, injected_ts: str) -> None:
    """Append a task card to the correct inbox per STAFF_TASKING_TIMER_SCHEMA.md
    inbox_map. A2-owned chains route to OpenCode; everything else to Claude."""
    first_owner = tp.owners.split("→")[0].strip()
    inbox_path = INBOX_FOR_OWNER_PREFIX.get(first_owner, CLAUDE_INBOX)

    card = f"""
---
## TASK: {task_id}
status: UNREAD
from: Client-Lifecycle-Automation
injected: {injected_ts}
priority: {"P0" if tp.critical else "P1"}
due: {tp.due_date.isoformat()}
task: |
  Deliverable: {tp.name}
  Client: {client}
  Touchpoint: {tp.id} (anchor: {tp.anchor})
  Owners: {tp.owners}

  {tp.note}
"""
    with open(inbox_path, "a") as f:
        f.write(card)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def print_timeline(client: str, timeline: list[Touchpoint]) -> None:
    print(f"\nCLIENT LIFECYCLE TIMELINE — {client}")
    print("-" * 78)
    for tp in timeline:
        flag = " [ESTIMATED]" if tp.estimated else ""
        crit = " \U0001F534" if tp.critical else ""
        print(f"{tp.due_date.isoformat()}  {tp.id:4s} {tp.name:28s} "
              f"owners={tp.owners:10s}{crit}{flag}")
    print("-" * 78)


def main() -> None:
    ap = argparse.ArgumentParser(description="Client Lifecycle Automation — 10-TP T-minus timeline")
    ap.add_argument("--client", help="Client dossier slug, e.g. kuklinski_group")
    ap.add_argument("--booking-date", type=_parse_date)
    ap.add_argument("--embark-date", type=_parse_date)
    ap.add_argument("--fpd", type=_parse_date, help="Final payment date (authoritative)")
    ap.add_argument("--disembark-date", type=_parse_date)
    ap.add_argument("--stage", action="store_true", help="Queue tasks into scheduler + inboxes")
    ap.add_argument("--dry-run", action="store_true", help="Show what --stage would do, write nothing")
    ap.add_argument("--test", action="store_true", help="Run built-in mock booking test")
    args = ap.parse_args()

    if args.test:
        client = args.client or "kuklinski_group_MOCK"
        booking_date = args.booking_date or date(2026, 6, 1)
        embark_date = args.embark_date or date(2026, 12, 17)
        fpd = args.fpd if args.fpd is not None else date(2026, 8, 15)
    else:
        if not (args.client and args.embark_date):
            ap.error("--client and --embark-date are required (or use --test)")
        client = args.client
        booking_date = args.booking_date
        embark_date = args.embark_date
        fpd = args.fpd

    timeline = compute_timeline(
        embark_date=embark_date,
        fpd=fpd,
        disembark_date=args.disembark_date,
        booking_date=booking_date,
    )
    print_timeline(client, timeline)

    if args.stage or args.dry_run:
        result = stage_to_scheduler(client, timeline, dry_run=args.dry_run)
        print(f"\n{'[DRY RUN] would stage' if args.dry_run else 'Staged'}: "
              f"{len(result['staged'])} tasks | already queued: {len(result['skipped_already_queued'])}")
        for e in result["staged"]:
            print(f"  + {e['task_id']}  due {e['draft_due']}  ({e['owners']})")


if __name__ == "__main__":
    main()
