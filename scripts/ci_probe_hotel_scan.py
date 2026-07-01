#!/usr/bin/env python3
"""
CI EFFICACY PROBE — Hotel Price Scan
=====================================
Dreams2Memories Travel, LLC · CI razor-sharp doctrine (SO 2026-06-20)

Checks:
  1. OpsCenter/state/hotel_scan_state.json exists and last_run < 25h ago
  2. If in-window bookings exist: at least 1 window was attempted
     (windows_scanned >= 1). 0 in-window bookings → GREEN (no work to do).
  3. Anansi binary reachable (scripts/hotel_scan.py dependency).

NOTE on efficacy:
  - 0 in-window bookings + fresh scan → GREEN (correct: no gap, clean state).
  - In-window bookings found + 0 windows scanned → RED (scan skipped work).
  - Stale state (>25h) → RED regardless.

Probe does NOT re-run the scanner. The repair function re-runs it.
Exit 0 = GREEN. Exit 1 = RED.
"""
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

THUNDERBIRD_ROOT = Path("/home/john/Thunderbird")
VENV_PY = str(THUNDERBIRD_ROOT / ".venv" / "bin" / "python3")
STATE_FILE = THUNDERBIRD_ROOT / "OpsCenter" / "state" / "hotel_scan_state.json"
ANANSI = THUNDERBIRD_ROOT / ".venv" / "bin" / "anansi"
CURRENCY_HOURS = 25
ID = "hotel-scan"


def fail(m: str) -> None:
    print(f"RED {ID}: {m}")
    sys.exit(1)


def ok(m: str) -> None:
    print(f"GREEN {ID}: {m}")
    sys.exit(0)


def main() -> None:
    # 1. Anansi binary reachable
    if not ANANSI.exists():
        fail(f"Anansi binary missing at {ANANSI} — hotel_scan.py cannot fetch prices")

    # 2. State file must exist
    if not STATE_FILE.exists():
        fail(f"State file missing: {STATE_FILE} — hotel_scan has never run")

    # 3. Parse and validate state
    try:
        state = json.loads(STATE_FILE.read_text())
    except Exception as e:
        fail(f"State file unreadable: {e}")

    last_run_str = state.get("last_run")
    if not last_run_str:
        fail("State file missing 'last_run' field")

    try:
        last_run = datetime.fromisoformat(last_run_str)
        if last_run.tzinfo is None:
            last_run = last_run.replace(tzinfo=timezone.utc)
    except Exception as e:
        fail(f"Cannot parse last_run '{last_run_str}': {e}")

    age = datetime.now(timezone.utc) - last_run
    if age > timedelta(hours=CURRENCY_HOURS):
        hours_old = age.total_seconds() / 3600
        fail(f"Stale: last_run {hours_old:.1f}h ago (limit {CURRENCY_HOURS}h)")

    # 4. Efficacy check
    bookings_found = state.get("bookings_found", 0)
    windows_scanned = state.get("windows_scanned", 0)

    if bookings_found > 0 and windows_scanned == 0:
        fail(
            f"Efficacy gap: {bookings_found} in-window booking(s) found "
            f"but 0 hotel windows were scanned — scanner may have crashed mid-run"
        )

    hours_old = age.total_seconds() / 3600
    ok(
        f"fresh ({hours_old:.1f}h ago); "
        f"{bookings_found} in-window booking(s); "
        f"{windows_scanned} window(s) scanned"
    )


if __name__ == "__main__":
    main()
