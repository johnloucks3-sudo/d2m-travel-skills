"""
Tests for core/compliance/cruise_line_policy_checker.py

20 synthetic bookings (fixtures/test_bookings.json) spanning all 4 registered
cruise lines and every rule category: age (alcohol/casino/min-sailing-age),
passport validity, medical pre-approval, mobility aid pre-approval, unknown
cruise line, and clean/no-violation bookings. Synthetic because TESS has no
structured guest DOB/passport/medical schema today (see module docstring) —
this is documented, not hidden.
"""

import json
from pathlib import Path

import pytest

from core.compliance.cruise_line_policy_checker import (
    CruiseLinePolicyChecker,
    URGENCY_HIGH,
)

FIXTURES = Path(__file__).parent / "fixtures" / "test_bookings.json"


@pytest.fixture(scope="module")
def bookings():
    return json.loads(FIXTURES.read_text())["bookings"]


@pytest.fixture(scope="module")
def checker():
    return CruiseLinePolicyChecker()


def _booking(bookings, booking_id):
    return next(b for b in bookings if b["booking_id"] == booking_id)


def test_fixture_has_20_bookings(bookings):
    assert len(bookings) == 20


def test_regent_underage_alcohol_flagged(bookings, checker):
    b = _booking(bookings, "REGENT-001")
    violations = checker.check_booking(b)
    assert any(v.rule_id == "REGENT-AGE-ALCOHOL" for v in violations)


def test_regent_clean_booking_no_violations(bookings, checker):
    b = _booking(bookings, "REGENT-002")
    violations = checker.check_booking(b)
    assert violations == []


def test_regent_medical_no_preapproval(bookings, checker):
    b = _booking(bookings, "REGENT-003")
    violations = checker.check_booking(b)
    assert any(v.rule_id == "REGENT-MEDICAL-PREAPPROVAL" for v in violations)
    assert any(v.urgency == URGENCY_HIGH for v in violations)


def test_regent_medical_with_preapproval_clears(bookings, checker):
    b = _booking(bookings, "REGENT-004")
    violations = checker.check_booking(b)
    assert not any(v.rule_id == "REGENT-MEDICAL-PREAPPROVAL" for v in violations)


def test_regent_passport_expiring_too_soon(bookings, checker):
    b = _booking(bookings, "REGENT-005")
    violations = checker.check_booking(b)
    assert any(v.rule_id == "REGENT-PASSPORT-180" for v in violations)


def test_regent_passport_already_expired_is_high_urgency(bookings, checker):
    b = _booking(bookings, "REGENT-006")
    violations = checker.check_booking(b)
    match = [v for v in violations if v.rule_id == "REGENT-PASSPORT-180"]
    assert match and match[0].urgency == URGENCY_HIGH


def test_regent_missing_passport_flagged(bookings, checker):
    b = _booking(bookings, "REGENT-007")
    violations = checker.check_booking(b)
    assert any("cannot verify validity" in v.violation for v in violations)


def test_regent_mobility_aid_no_preapproval(bookings, checker):
    b = _booking(bookings, "REGENT-008")
    violations = checker.check_booking(b)
    assert any(v.rule_id == "REGENT-MOBILITY-PREAPPROVAL" for v in violations)


def test_regent_mobility_aid_with_preapproval_clears(bookings, checker):
    b = _booking(bookings, "REGENT-009")
    violations = checker.check_booking(b)
    assert not any(v.rule_id == "REGENT-MOBILITY-PREAPPROVAL" for v in violations)


def test_silversea_16yo_alcohol_allowed(bookings, checker):
    b = _booking(bookings, "SILVERSEA-001")
    violations = checker.check_booking(b)
    assert not any(v.rule_id == "SILVERSEA-AGE-ALCOHOL" for v in violations)


def test_silversea_15yo_alcohol_flagged(bookings, checker):
    b = _booking(bookings, "SILVERSEA-002")
    violations = checker.check_booking(b)
    assert any(v.rule_id == "SILVERSEA-AGE-ALCOHOL" for v in violations)


def test_silversea_underage_casino(bookings, checker):
    b = _booking(bookings, "SILVERSEA-003")
    violations = checker.check_booking(b)
    assert any(v.rule_id == "SILVERSEA-AGE-CASINO" for v in violations)


def test_silversea_oxygen_no_form(bookings, checker):
    b = _booking(bookings, "SILVERSEA-004")
    violations = checker.check_booking(b)
    assert any(v.rule_id == "SILVERSEA-MEDICAL-PREAPPROVAL" for v in violations)


def test_silversea_clean_multi_guest_booking(bookings, checker):
    b = _booking(bookings, "SILVERSEA-005")
    violations = checker.check_booking(b)
    assert violations == []


def test_viking_underage_casino(bookings, checker):
    b = _booking(bookings, "VIKING-001")
    violations = checker.check_booking(b)
    assert any(v.rule_id == "VIKING-AGE-CASINO" for v in violations)


def test_viking_below_min_sailing_age(bookings, checker):
    b = _booking(bookings, "VIKING-002")
    violations = checker.check_booking(b)
    match = [v for v in violations if v.rule_id == "VIKING-MIN-AGE-SAILING"]
    assert match and match[0].urgency == URGENCY_HIGH


def test_viking_clean_adult_booking(bookings, checker):
    b = _booking(bookings, "VIKING-003")
    violations = checker.check_booking(b)
    assert violations == []


def test_princess_unknown_confidence_medical_rule_skipped(bookings, checker):
    """Princess's medical-preapproval rule is tagged UNKNOWN (not yet sourced) —
    the checker must skip it rather than fabricate a violation, even though this
    guest carries dialysis equipment with no preapproval on file (Negative-Space
    Rule, SO-PIPELINE-INTEGRITY-20260528)."""
    b = _booking(bookings, "PRINCESS-001")
    violations = checker.check_booking(b)
    assert not any(v.rule_id == "PRINCESS-MEDICAL-PREAPPROVAL" for v in violations)


def test_unknown_cruise_line_flagged(bookings, checker):
    b = _booking(bookings, "UNKNOWN-001")
    violations = checker.check_booking(b)
    assert len(violations) == 1
    assert violations[0].rule_id == "POLICY-UNKNOWN-LINE"


def test_multiple_violations_single_guest_stack(bookings, checker):
    b = _booking(bookings, "REGENT-010")
    violations = checker.check_booking(b)
    rule_ids = {v.rule_id for v in violations}
    assert "REGENT-AGE-ALCOHOL" in rule_ids
    assert "REGENT-MEDICAL-PREAPPROVAL" in rule_ids
    assert "REGENT-PASSPORT-180" in rule_ids


def test_all_20_bookings_run_without_exception(bookings, checker):
    for b in bookings:
        checker.check_booking(b)  # must not raise


def test_alias_resolution_ship_name_matches_line(checker):
    name, entry = checker.resolve_cruise_line("Seven Seas Grandeur")
    assert name == "Regent Seven Seas"


def test_resolve_unknown_line_raises(checker):
    from core.compliance.cruise_line_policy_checker import PolicyNotFoundError
    with pytest.raises(PolicyNotFoundError):
        checker.resolve_cruise_line("Carnival Cruise Line")
