#!/usr/bin/env python3
"""
Lifecycle Phase Assignment — determines which of the 3 lifecycle zones a
client booking is currently in, and which touchpoints are next due.

Source of truth for zone boundaries + touchpoint schedule:
  docs/CLIENT_LIFECYCLE_ARCHITECTURE.md v1.0
  config/lifecycle_touchpoints.json

Zones (measured relative to embark date E, unless noted):
  COMMITMENT  — booking_date  to  E-180  ("everything is ahead")
  PREPARATION — E-180         to  E-30   ("details are hardening")
  EXECUTION   — E-30          to  D+30   ("we are live")
  COMPLETED   — after D+30
"""

import json
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

TOUCHPOINTS_PATH = Path(__file__).resolve().parent.parent / "config" / "lifecycle_touchpoints.json"

ZONE_COMMITMENT = "COMMITMENT"
ZONE_PREPARATION = "PREPARATION"
ZONE_EXECUTION = "EXECUTION"
ZONE_COMPLETED = "COMPLETED"

PREPARATION_START_DAYS_BEFORE_EMBARK = 180  # T-6mo
EXECUTION_START_DAYS_BEFORE_EMBARK = 30     # T-30
EXECUTION_END_DAYS_AFTER_DISEMBARK = 30     # T+30
DEFAULT_VOYAGE_LENGTH_DAYS = 10             # fallback if disembark_date unknown


def _load_touchpoints() -> list[dict]:
    with open(TOUCHPOINTS_PATH) as f:
        return json.load(f)["touchpoints"]


def _resolve_anchor_date(tp: dict, booking_date: date, embark_date: date,
                          fpd_date: date, disembark_date: date) -> Optional[date]:
    """Compute the actual calendar date a touchpoint's anchor_offset_days resolves to."""
    origin_map = {"B": booking_date, "E": embark_date, "FPD": fpd_date, "D": disembark_date}
    origin = origin_map.get(tp.get("anchor_origin"))
    offset = tp.get("anchor_offset_days")
    if origin is None or offset is None:
        return None
    return origin + timedelta(days=offset)


def determine_zone(booking_date: date, fpd_date: date, embark_date: date,
                    disembark_date: Optional[date] = None,
                    today: Optional[date] = None) -> str:
    """Return the current lifecycle zone for a booking."""
    today = today or date.today()
    disembark_date = disembark_date or (embark_date + timedelta(days=DEFAULT_VOYAGE_LENGTH_DAYS))

    execution_end = disembark_date + timedelta(days=EXECUTION_END_DAYS_AFTER_DISEMBARK)
    preparation_start = embark_date - timedelta(days=PREPARATION_START_DAYS_BEFORE_EMBARK)
    execution_start = embark_date - timedelta(days=EXECUTION_START_DAYS_BEFORE_EMBARK)

    if today > execution_end:
        return ZONE_COMPLETED
    if today >= execution_start:
        return ZONE_EXECUTION
    if today >= preparation_start:
        return ZONE_PREPARATION
    return ZONE_COMMITMENT


def days_remaining_in_phase(zone: str, booking_date: date, fpd_date: date, embark_date: date,
                             disembark_date: Optional[date] = None,
                             today: Optional[date] = None) -> int:
    today = today or date.today()
    disembark_date = disembark_date or (embark_date + timedelta(days=DEFAULT_VOYAGE_LENGTH_DAYS))

    if zone == ZONE_COMMITMENT:
        boundary = embark_date - timedelta(days=PREPARATION_START_DAYS_BEFORE_EMBARK)
    elif zone == ZONE_PREPARATION:
        boundary = embark_date - timedelta(days=EXECUTION_START_DAYS_BEFORE_EMBARK)
    elif zone == ZONE_EXECUTION:
        boundary = disembark_date + timedelta(days=EXECUTION_END_DAYS_AFTER_DISEMBARK)
    else:  # COMPLETED
        return 0

    return (boundary - today).days


def next_touchpoints(booking_date: date, fpd_date: date, embark_date: date,
                      disembark_date: Optional[date] = None,
                      today: Optional[date] = None, limit: int = 5) -> list[dict]:
    """Return the next `limit` upcoming touchpoints (any zone), sorted by resolved date."""
    today = today or date.today()
    disembark_date = disembark_date or (embark_date + timedelta(days=DEFAULT_VOYAGE_LENGTH_DAYS))

    resolved = []
    for tp in _load_touchpoints():
        adate = _resolve_anchor_date(tp, booking_date, embark_date, fpd_date, disembark_date)
        if adate is None or adate < today:
            continue
        resolved.append((adate, tp))

    resolved.sort(key=lambda pair: pair[0])
    return [
        {
            "touchpoint_id": tp["touchpoint_id"],
            "zone": tp["zone"],
            "date": adate.isoformat(),
            "days_out": (adate - today).days,
            "owner_primary": tp["owner_primary"],
            "owner_secondary": tp.get("owner_secondary"),
            "content_type": tp["content_type"],
            "description": tp["description"],
        }
        for adate, tp in resolved[:limit]
    ]


def assign_phase(booking_date: date, fpd_date: date, embark_date: date,
                  disembark_date: Optional[date] = None,
                  today: Optional[date] = None) -> dict:
    """Full phase assignment result for a client booking."""
    today = today or date.today()
    zone = determine_zone(booking_date, fpd_date, embark_date, disembark_date, today)
    remaining = days_remaining_in_phase(zone, booking_date, fpd_date, embark_date, disembark_date, today)
    upcoming = next_touchpoints(booking_date, fpd_date, embark_date, disembark_date, today)

    return {
        "scan_date": today.isoformat(),
        "current_phase": zone,
        "days_remaining_in_phase": remaining,
        "next_touchpoints": upcoming,
    }


def format_summary(result: dict) -> str:
    tp_str = ", ".join(
        f"{tp['touchpoint_id']} ({tp['description'].split(chr(45))[0].split(chr(8212))[0][:30].strip()}, {tp['days_out']}d)"
        for tp in result["next_touchpoints"][:2]
    )
    phase = result["current_phase"]
    if phase == ZONE_COMPLETED:
        return f"Client is COMPLETED (lifecycle closed)."
    return (
        f"Client is in {phase} (T{'+' if result['days_remaining_in_phase'] >= 0 else ''}"
        f"{result['days_remaining_in_phase']} days remaining in phase). "
        f"Next TPs: {tp_str if tp_str else 'none upcoming'}"
    )


# ---------------------------------------------------------------------------
# CLI / self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Lifecycle phase assignment")
    parser.add_argument("--booking", required=False, help="Booking date YYYY-MM-DD")
    parser.add_argument("--fpd", required=False, help="Final payment date YYYY-MM-DD")
    parser.add_argument("--embark", required=False, help="Embark date YYYY-MM-DD")
    parser.add_argument("--disembark", required=False, help="Disembark date YYYY-MM-DD")
    parser.add_argument("--today", required=False, help="Override today's date YYYY-MM-DD (testing)")
    parser.add_argument("--test", action="store_true", help="Run built-in 3-client self-test")

    args = parser.parse_args()

    def _d(s):
        return date.fromisoformat(s) if s else None

    if args.test:
        today = _d(args.today) or date(2026, 7, 6)
        cases = [
            ("Kuklinski (Viking Mars, Dec 17 2026)",
             date(2026, 2, 7), date(2026, 3, 31), date(2026, 12, 17), date(2026, 12, 27)),
            ("McLeod (Regent Grandeur 2984034, Dec 19 2026)",
             date(2026, 1, 1), date(2026, 7, 22), date(2026, 12, 19), date(2026, 12, 29)),
            ("Furlow (Regent Grandeur 3071222, Aug 29 2026)",
             date(2025, 9, 10), date(2026, 4, 1), date(2026, 8, 29), date(2026, 9, 8)),
        ]
        for label, booking, fpd, embark, disembark in cases:
            result = assign_phase(booking, fpd, embark, disembark, today=today)
            print(f"\n=== {label} ===", file=sys.stderr)
            print(format_summary(result), file=sys.stderr)
            print(json.dumps(result, indent=2), file=sys.stderr)
        sys.exit(0)

    if not (args.booking and args.fpd and args.embark):
        parser.print_help(sys.stderr)
        sys.exit(1)

    result = assign_phase(_d(args.booking), _d(args.fpd), _d(args.embark), _d(args.disembark),
                           today=_d(args.today))
    print(format_summary(result), file=sys.stderr)
    print(json.dumps(result, indent=2))
