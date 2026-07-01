#!/usr/bin/env python3
"""
CI EFFICACY PROBE — Transfer Price Scan
=========================================
Dreams2Memories Travel, LLC · CI razor-sharp doctrine (SO 2026-06-20)

Checks:
  1. OpsCenter/state/transfer_scan_state.json exists and last_run < 25h ago
  2. Anansi binary reachable (transfer_scan.py dependency).

NOTE: Per spec, this probe checks freshness only (scan ran <25h).
State proves real work was attempted — routes_checked in state is informational.
Arc4-D lifecycle touchpoint consumes transfer_scan_state.json for its planning work.

Probe does NOT re-run the scanner. The repair function re-runs it.
Exit 0 = GREEN. Exit 1 = RED.
"""
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

THUNDERBIRD_ROOT = Path("/home/john/Thunderbird")
VENV_PY = str(THUNDERBIRD_ROOT / ".venv" / "bin" / "python3")
STATE_FILE = THUNDERBIRD_ROOT / "OpsCenter" / "state" / "transfer_scan_state.json"
ANANSI = THUNDERBIRD_ROOT / ".venv" / "bin" / "anansi"
CURRENCY_HOURS = 25
ID = "transfer-scan"


def fail(m: str) -> None:
    print(f"RED {ID}: {m}")
    sys.exit(1)


def ok(m: str) -> None:
    print(f"GREEN {ID}: {m}")
    sys.exit(0)


def main() -> None:
    # 1. Anansi binary reachable
    if not ANANSI.exists():
        fail(f"Anansi binary missing at {ANANSI} — transfer_scan.py cannot fetch prices")

    # 2. State file must exist
    if not STATE_FILE.exists():
        fail(f"State file missing: {STATE_FILE} — transfer_scan has never run")

    # 3. Parse state
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

    hours_old = age.total_seconds() / 3600
    bookings = state.get("bookings_found", 0)
    routes = state.get("routes_checked", 0)
    ok(
        f"fresh ({hours_old:.1f}h ago); "
        f"{bookings} in-window booking(s); "
        f"{routes} route(s) checked"
    )


if __name__ == "__main__":
    main()
