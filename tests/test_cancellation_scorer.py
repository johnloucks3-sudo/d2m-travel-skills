import json
from datetime import date

import pytest

from core.risk.cancellation_scorer import (
    HIGH_RISK_THRESHOLD,
    BookingFeatures,
    features_from_known_booking,
    score_booking,
    train_logistic_regression,
    write_risk_json,
)


def test_low_risk_paid_engaged_client():
    f = BookingFeatures(
        booking_id="TEST-001",
        days_to_departure=120,
        fpd_status="PAID",
        prior_cancellations=0,
        email_engagement="opened",
        known_fields={"fpd_status", "email_engagement", "prior_cancellations", "competitor_activity"},
    )
    result = score_booking(f)
    assert result.risk_score < HIGH_RISK_THRESHOLD
    assert result.flagged_for_intervention is False
    assert result.confidence == 1.0


def test_high_risk_mirrors_mcleod_use_case():
    # Late FPD + no engagement, close to departure -> matches the McLeod
    # scenario in the task brief (late FPD, no engagement emails opened).
    f = BookingFeatures(
        booking_id="MCLEOD-TEST",
        days_to_departure=30,
        fpd_status="OVERDUE",
        fpd_days_overdue=14,
        prior_cancellations=0,
        email_engagement="no_opens",
        known_fields={"fpd_status", "email_engagement", "prior_cancellations", "competitor_activity"},
    )
    result = score_booking(f)
    assert result.risk_score > HIGH_RISK_THRESHOLD
    assert result.flagged_for_intervention is True
    assert "intervention" in result.recommendation.lower()


def test_threshold_boundary_exact_value_not_flagged():
    # risk_score == threshold should NOT flag (strictly greater than)
    f = BookingFeatures(booking_id="EDGE-001", days_to_departure=200, fpd_status="unknown")
    result = score_booking(f)
    assert result.risk_score == 0
    assert result.flagged_for_intervention is False


def test_score_bounded_0_100():
    f = BookingFeatures(
        booking_id="MAX-001",
        days_to_departure=1,
        fpd_status="OVERDUE",
        fpd_days_overdue=999,
        prior_cancellations=10,
        email_engagement="no_opens",
        competitor_activity=True,
        known_fields={"fpd_status", "email_engagement", "prior_cancellations", "competitor_activity"},
    )
    result = score_booking(f)
    assert 0 <= result.risk_score <= 100


def test_confidence_reflects_missing_fields():
    f = BookingFeatures(booking_id="PARTIAL-001", days_to_departure=60, fpd_status="PENDING",
                         known_fields={"fpd_status"})
    result = score_booking(f)
    assert result.confidence == 0.25  # 1 of 4 trackable fields known


def test_features_from_known_booking_uses_real_fields_only():
    booking = {
        "client": "Test Client",
        "embark_date": date(2026, 12, 1),
        "fpd": date(2026, 7, 1),
        "fpd_status": "PENDING",
    }
    feats = features_from_known_booking("Test_Booking_001", booking, today=date(2026, 7, 20))
    assert feats.fpd_status == "OVERDUE"
    assert feats.fpd_days_overdue == 19
    assert feats.email_engagement == "unknown"  # not present in KNOWN_BOOKINGS -> honestly unknown
    assert "email_engagement" not in feats.known_fields


def test_json_output_shape(tmp_path):
    f = BookingFeatures(booking_id="JSON-001", fpd_status="OVERDUE", fpd_days_overdue=20,
                         email_engagement="no_opens", days_to_departure=10,
                         known_fields={"fpd_status", "email_engagement"})
    result = score_booking(f)
    out = write_risk_json(result, tmp_path / "cancellation_risk.json")
    data = json.loads(out.read_text())
    assert set(data.keys()) == {
        "booking_id", "risk_score", "confidence", "recommendation",
        "flagged_for_intervention", "signal_breakdown", "threshold", "method",
    }
    assert data["method"] == "weighted_heuristic_v1"


def test_train_logistic_regression_raises_not_fabricated():
    with pytest.raises(NotImplementedError):
        train_logistic_regression()
