"""
Anchor Date Validation — OpenCode Lifecycle Integration

Extends core.lifecycle.client_ingester.validate_anchor_dates with two checks
the original validator does not perform:

  1. booking_date < fpd (the original only checks embark/disembark/fpd order,
     not booking-vs-fpd).
  2. FPD alignment with the cruise line's contract term (Regent T-120 vs a
     T-90 default for other lines) — flagged as a WARNING with tolerance,
     never an error, since actual supplier contracts vary by promotion/fare
     class and a mismatch alone doesn't make the anchor set invalid.

Does not duplicate the existence/logical-order checks already in
client_ingester.py — it calls that validator and adds to its report.
"""

from datetime import date, timedelta
from typing import Optional, Dict, Any

from core.lifecycle.client_ingester import validate_anchor_dates as _base_validate

# Cruise-line final-payment contract terms, in days before embarkation.
# Source: standing lifecycle doctrine (Regent T-120; most other lines T-90).
CONTRACT_TERMS_DAYS = {
    "regent": 120,
    "regent seven seas": 120,
    "viking": 90,
    "silversea": 90,
    "princess": 90,
}
DEFAULT_CONTRACT_TERM_DAYS = 90
FPD_TOLERANCE_DAYS = 7  # supplier promos/fare classes can shift FPD a few days


def _expected_fpd(embark_date: date, cruise_line: Optional[str]) -> date:
    term = CONTRACT_TERMS_DAYS.get((cruise_line or "").strip().lower(), DEFAULT_CONTRACT_TERM_DAYS)
    return embark_date - timedelta(days=term)


def validate_anchors(
    booking_date: Optional[date] = None,
    embark_date: Optional[date] = None,
    disembark_date: Optional[date] = None,
    fpd: Optional[date] = None,
    cruise_line: Optional[str] = None,
    client_label: str = "",
    as_of: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Full anchor validation report: base client_ingester checks plus the two
    extensions described in the module docstring.

    Returns the same shape as client_ingester.validate_anchor_dates
    ({"valid", "errors", "warnings", "anchor_count"}) with extra keys:
        "pass": True/False    — same as "valid", the vocabulary the task spec asks for
        "reasons": [...]      — combined errors + warnings, human-readable
    """
    report = _base_validate(
        booking_date=booking_date,
        embark_date=embark_date,
        disembark_date=disembark_date,
        fpd=fpd,
        client_label=client_label,
        as_of=as_of,
    )

    if booking_date and fpd:
        if not (booking_date < fpd):
            report["errors"].append(f"{client_label}: booking_date not before fpd")
            report["valid"] = False

    if embark_date and fpd:
        expected = _expected_fpd(embark_date, cruise_line)
        drift = abs((fpd - expected).days)
        if drift > FPD_TOLERANCE_DAYS:
            term_used = CONTRACT_TERMS_DAYS.get((cruise_line or "").strip().lower(), DEFAULT_CONTRACT_TERM_DAYS)
            report["warnings"].append(
                f"{client_label}: fpd is {drift}d off the T-{term_used} contract-term "
                f"expectation for '{cruise_line or 'default'}' (expected ~{expected.isoformat()}, got {fpd.isoformat()})"
            )

    report["pass"] = report["valid"]
    report["reasons"] = list(report["errors"]) + list(report["warnings"])
    return report
