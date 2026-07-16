#!/usr/bin/env python3
"""
update_seat_budget.py — ten-second per-seat budget update.

Usage:
  update_seat_budget.py CC --weekly-pct 64 [--five-hour-pct 20] [--note "..."]
  update_seat_budget.py status
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.ai_infra.seat_budget import update_seat, seat_status, SEATS  # noqa: E402


def _flag(name):
    return float(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    if sys.argv[1] == "status":
        for seat in SEATS:
            s = seat_status(seat)
            flag = "⚠ STALE" if s["stale"] else "fresh"
            print(f"{seat}: weekly={s['weekly_pct']} 5h={s['five_hour_pct']} "
                  f"({flag}, age={s['age_hours']}h) {s.get('note', '')}")
        sys.exit(0)
    seat = sys.argv[1].upper()
    note = sys.argv[sys.argv.index("--note") + 1] if "--note" in sys.argv else ""
    e = update_seat(seat, weekly_pct=_flag("--weekly-pct"),
                    five_hour_pct=_flag("--five-hour-pct"), note=note)
    print(f"{seat} updated: {e}")
