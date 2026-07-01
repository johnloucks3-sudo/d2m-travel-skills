#!/usr/bin/env python3
"""
CI Probe — lifecycle-travel-surveys
Exit 0 = GREEN, Exit 1 = RED.
Final output line: GREEN lifecycle-travel-surveys: <detail>
                or RED lifecycle-travel-surveys: <detail>
"""

import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

THUNDERBIRD = Path("/home/john/Thunderbird")
STATE_FILE = THUNDERBIRD / "OpsCenter" / "state" / "travel_survey_state.json"
STALE_HOURS = 25
WINDOW_DAYS = 30

sys.path.insert(0, str(THUNDERBIRD))


def fail(m):
    print(f"RED lifecycle-travel-surveys: {m}")
    sys.exit(1)


def ok(m):
    print(f"GREEN lifecycle-travel-surveys: {m}")
    sys.exit(0)


def main():
    if not STATE_FILE.exists():
        fail("state file missing — generator never ran")

    try:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"state file unreadable: {exc}")

    last_run_str = state.get("last_run")
    if not last_run_str:
        fail("state file has no last_run timestamp")

    try:
        last_run = datetime.fromisoformat(last_run_str)
        if last_run.tzinfo is None:
            last_run = last_run.replace(tzinfo=timezone.utc)
    except Exception as exc:
        fail(f"cannot parse last_run timestamp: {exc}")

    now = datetime.now(timezone.utc)
    age_seconds = (now - last_run).total_seconds()
    age_hours = age_seconds / 3600
    age_mins = int(age_seconds / 60)

    if age_hours > STALE_HOURS:
        fail(f"stale: last run {age_hours:.1f}h ago")

    try:
        from core.booking.thunderbird_tp_scheduler import scan_dossiers
        records = scan_dossiers()
    except Exception as exc:
        fail(f"scan_dossiers() failed: {exc}")

    today = date.today()
    eligible = [
        r for r in records
        if r.return_date is not None
        and 1 <= (today - r.return_date).days <= WINDOW_DAYS
    ]

    if not eligible:
        evaluated = state.get("evaluated", 0)
        staged = state.get("staged", 0)
        ok(f"ran {age_mins}m ago; 0 returners in window (evaluated={evaluated}, staged={staged})")

    entries = state.get("entries", {})
    missing = [
        r for r in eligible
        if f"{r.path}|{r.return_date}" not in entries
    ]

    if missing:
        names = ", ".join(r.client for r in missing)
        fail(f"{len(eligible)} clients returned, {len(missing)} surveys not staged: {names}")

    evaluated = state.get("evaluated", len(eligible))
    staged = state.get("staged", len(eligible))
    ok(f"ran {age_mins}m ago; {evaluated} evaluated, {staged} staged")


if __name__ == "__main__":
    main()
