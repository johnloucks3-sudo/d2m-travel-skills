"""
Phase Determination Engine — OpenCode Lifecycle Integration

Thin wrapper around core.lifecycle.client_ingester's algorithmic phase logic
(the single source of truth for PHASE_0..PHASE_5 boundaries). Does not
reimplement that logic — imports and delegates to it, then adds:

  - an injectable `as_of` reference date (already threaded through
    client_ingester as of this integration, so tests and the event handler
    can evaluate "what phase would this client be in on date X" without
    waiting for real time to pass)
  - `anchor_validation` in the pass/fail-with-reason shape the task spec asks
    for (built on core.opencode.anchor_validation, which extends the base
    validator with contract-term + booking<fpd checks)
  - a `payment_status` label in the Deposit / In Progress / FPD Due / Paid
    vocabulary, derived from the raw paid/pending/partial status client
    records use plus timing relative to fpd
  - `phase_window()` — the date range [start, end) a given phase occupies for
    a specific client's anchors, per the boundaries in
    client_ingester.PHASE_DEFINITIONS. Used by lifecycle_event_handler.py to
    select which touchpoints (anchor-relative, from
    config/lifecycle_touchpoints.json) fall inside a phase.
"""

from datetime import date, timedelta
from typing import Optional, Dict, Any

from core.lifecycle.client_ingester import (
    determine_phase,
    PHASE_DEFINITIONS,
)
from core.opencode.anchor_validation import validate_anchors

DEPOSIT_WINDOW_DAYS = 30  # first N days after booking read as "Deposit" rather than "In Progress"


def _payment_status_label(
    raw_status: Optional[str],
    booking_date: date,
    fpd: date,
    as_of: date,
) -> str:
    """
    Map the raw paid/pending/partial status (+ timing) to the four-value
    vocabulary the phase engine reports: Deposit, In Progress, FPD Due, Paid.

    This is a business heuristic, not an anchor rule — it approximates:
    "right after booking, only the deposit is in and nothing is overdue yet."
    """
    if raw_status == "paid":
        return "Paid"
    if as_of >= fpd:
        return "FPD Due"
    if raw_status == "partial":
        return "In Progress"
    # raw_status is None/"pending"
    if as_of < booking_date + timedelta(days=DEPOSIT_WINDOW_DAYS):
        return "Deposit"
    return "In Progress"


def assign_phase(
    booking_date: date,
    fpd: date,
    embark_date: date,
    disembark_date: date,
    payment_status: Optional[str] = None,
    payment_date: Optional[date] = None,
    cruise_line: Optional[str] = None,
    client_label: str = "",
    as_of: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Compute phase + anchor validation + payment status for one client, as of
    a given reference date (default: today).

    Returns:
        {
            "phase_code": "PHASE_2",
            "phase_name": "Execute",
            "anchor_validation": {"pass": bool, "reasons": [...], ...},
            "payment_status": "In Progress",
            "as_of": "2026-07-06",
        }
    """
    today = as_of or date.today()

    validation = validate_anchors(
        booking_date=booking_date,
        embark_date=embark_date,
        disembark_date=disembark_date,
        fpd=fpd,
        cruise_line=cruise_line,
        client_label=client_label,
        as_of=today,
    )

    if not validation["pass"]:
        return {
            "phase_code": "PHASE_INVALID",
            "phase_name": "Invalid anchors",
            "anchor_validation": validation,
            "payment_status": _payment_status_label(payment_status, booking_date, fpd, today) if booking_date and fpd else "Unknown",
            "as_of": today.isoformat(),
        }

    phase_code, phase_name = determine_phase(
        booking_date=booking_date,
        embark_date=embark_date,
        disembark_date=disembark_date,
        fpd=fpd,
        payment_status=payment_status,
        payment_date=payment_date,
        client_label=client_label,
        as_of=today,
    )

    return {
        "phase_code": phase_code,
        "phase_name": phase_name,
        "anchor_validation": validation,
        "payment_status": _payment_status_label(payment_status, booking_date, fpd, today),
        "as_of": today.isoformat(),
    }


def phase_window(
    phase_code: str,
    booking_date: date,
    fpd: date,
    embark_date: date,
    disembark_date: date,
) -> tuple[Optional[date], Optional[date]]:
    """
    Return (start_date, end_date_exclusive) for the given phase, computed
    from this client's own anchors — per the boundary conditions documented
    in client_ingester.PHASE_DEFINITIONS. Either end may be None to mean
    "unbounded" (PHASE_0's start, PHASE_5's end).

    Used to select which anchor-relative touchpoints
    (config/lifecycle_touchpoints.json) are "active" for a phase: a
    touchpoint is active if its own target date falls in [start, end).
    """
    if phase_code == "PHASE_0":
        return (None, booking_date)
    if phase_code == "PHASE_1":
        return (booking_date, booking_date + timedelta(days=60))
    if phase_code == "PHASE_2":
        return (booking_date + timedelta(days=60), fpd)
    if phase_code == "PHASE_3":
        return (fpd, embark_date - timedelta(days=7))
    if phase_code == "PHASE_4":
        return (embark_date - timedelta(days=7), disembark_date + timedelta(days=1))
    if phase_code == "PHASE_5":
        return (disembark_date + timedelta(days=1), None)
    raise ValueError(f"Unknown phase_code: {phase_code}")


if __name__ == "__main__":
    import json
    import sys

    result = assign_phase(
        booking_date=date(2025, 12, 1),
        fpd=date(2026, 8, 15),
        embark_date=date(2026, 12, 17),
        disembark_date=date(2026, 12, 27),
        payment_status="pending",
        cruise_line="Viking",
        client_label="smoke-test",
        as_of=date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else None,
    )
    print(json.dumps(result, indent=2))
