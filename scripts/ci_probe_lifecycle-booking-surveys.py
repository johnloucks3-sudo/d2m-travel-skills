#!/usr/bin/env python3
"""CI probe — lifecycle-booking-surveys.
Verifies the booking survey generator ran recently and no confirmed bookings
are missing a staged preferences survey.
Exit 0 = GREEN, exit 1 = RED.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "/home/john/Thunderbird")
from core.booking.thunderbird_tp_scheduler import scan_dossiers

ID = "lifecycle-booking-surveys"
STATE_PATH = Path("/home/john/Thunderbird/OpsCenter/state/booking_survey_state.json")
STALE_HOURS = 25


def fail(m):
    print(f"RED {ID}: {m}")
    sys.exit(1)


def main():
    # 1. State file must exist
    if not STATE_PATH.exists():
        fail("state file missing — generator never ran")

    try:
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        fail(f"state file unreadable: {e}")

    # 2. Check freshness
    last_run_str = state.get("last_run")
    if not last_run_str:
        fail("state file has no last_run timestamp")

    try:
        last_run = datetime.fromisoformat(last_run_str)
        if last_run.tzinfo is None:
            last_run = last_run.replace(tzinfo=timezone.utc)
    except ValueError as e:
        fail(f"cannot parse last_run timestamp: {e}")

    now = datetime.now(timezone.utc)
    age_hours = (now - last_run).total_seconds() / 3600

    if age_hours > STALE_HOURS:
        fail(f"stale: last run {age_hours:.1f}h ago")

    # 3. Check for confirmed bookings absent from state entries
    try:
        records = scan_dossiers()
    except Exception as e:
        fail(f"scan_dossiers() failed: {e}")

    entries = state.get("entries", {})
    active_with_departure = [
        rec for rec in records
        if rec.status == "active" and rec.departure is not None
    ]

    missing = [rec for rec in active_with_departure if str(rec.path) not in entries]

    if missing:
        names = ", ".join(rec.client for rec in missing)
        fail(f"{len(missing)} new booking(s) without survey staged: {names}")

    age_min = int(age_hours * 60)
    evaluated = state.get("evaluated", len(active_with_departure))
    total_staged = state.get("staged", len(entries))

    print(f"GREEN {ID}: ran {age_min}m ago; evaluated {evaluated}, staged {total_staged}")
    sys.exit(0)


if __name__ == "__main__":
    main()
