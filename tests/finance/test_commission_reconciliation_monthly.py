"""
Tests for scripts/commission_reconciliation_monthly.py

Exercises the pure reconciliation engine (month_bounds, is_discrepancy,
merge_received, reconcile_month) directly against synthetic fixture data —
no live TESS/Sheets/Gmail credentials required, mirroring the existing
tests/finance/test_oa_commission_tracker.py pattern.

The 6-month synthetic dataset below seeds a small, known set of true
discrepancies (by construction) and asserts reconcile_month() flags exactly
those — proving flagged items are real variances, not artifacts of the
matching/threshold logic (no false positives, no false negatives).
"""
import sys
from datetime import date

sys.path.insert(0, "/home/john/Thunderbird")
sys.path.insert(0, "/home/john/Thunderbird/scripts")

from commission_reconciliation_monthly import (
    month_bounds,
    previous_month_str,
    is_discrepancy,
    merge_received,
    reconcile_month,
    VARIANCE_ABS_THRESHOLD,
    VARIANCE_PCT_THRESHOLD,
)


# ---------------------------------------------------------------------------
# month_bounds / previous_month_str
# ---------------------------------------------------------------------------

def test_month_bounds_31_day_month():
    assert month_bounds("2026-01") == (date(2026, 1, 1), date(2026, 1, 31))


def test_month_bounds_28_day_february_non_leap_year():
    assert month_bounds("2026-02") == (date(2026, 2, 1), date(2026, 2, 28))


def test_month_bounds_december_crosses_year():
    assert month_bounds("2026-12") == (date(2026, 12, 1), date(2026, 12, 31))


def test_previous_month_str_mid_year():
    assert previous_month_str(date(2026, 7, 6)) == "2026-06"


def test_previous_month_str_january_crosses_year_boundary():
    assert previous_month_str(date(2026, 1, 15)) == "2025-12"


# ---------------------------------------------------------------------------
# is_discrepancy — dual threshold (>5% OR >$100)
# ---------------------------------------------------------------------------

def test_is_discrepancy_within_both_thresholds_not_flagged():
    flagged, delta, pct = is_discrepancy(2000.0, 1950.0)  # -$50, -2.5%
    assert flagged is False
    assert delta == -50.0
    assert pct == -2.5


def test_is_discrepancy_flagged_by_percentage_alone():
    # Small dollar commission: 10% variance but only $50 — must still flag via pct.
    flagged, delta, pct = is_discrepancy(500.0, 450.0)
    assert abs(delta) < VARIANCE_ABS_THRESHOLD
    assert abs(pct) > VARIANCE_PCT_THRESHOLD
    assert flagged is True


def test_is_discrepancy_flagged_by_dollar_amount_alone():
    # Large dollar commission: $150 variance but only 3% — must still flag via $ threshold.
    flagged, delta, pct = is_discrepancy(5000.0, 4850.0)
    assert abs(delta) > VARIANCE_ABS_THRESHOLD
    assert abs(pct) < VARIANCE_PCT_THRESHOLD
    assert flagged is True


def test_is_discrepancy_exact_match_not_flagged():
    flagged, delta, pct = is_discrepancy(1000.0, 1000.0)
    assert flagged is False
    assert delta == 0.0
    assert pct == 0.0


def test_is_discrepancy_zero_expected_nonzero_received_flags():
    flagged, delta, pct = is_discrepancy(0.0, 250.0)
    assert flagged is True


# ---------------------------------------------------------------------------
# merge_received — source precedence (TESS > OA > MANUAL)
# ---------------------------------------------------------------------------

def test_merge_received_tess_wins_over_oa_and_manual():
    tess = [{"source": "TESS", "booking_ref": "B1", "client_name": "Ely",
             "supplier": "RSSC", "amount": 1000.0, "date": "2026-06-05", "notes": ""}]
    oa = [{"source": "OA", "booking_ref": "B1", "client_name": "Ely",
           "supplier": "RSSC", "amount": 950.0, "date": "2026-06-06", "notes": "stmt-42"}]
    manual = [{"source": "MANUAL", "booking_ref": "B1", "client_name": "Ely",
               "supplier": "RSSC", "amount": 900.0, "date": "2026-06-07", "notes": "paper check"}]
    merged = merge_received(tess, oa, manual)
    assert len(merged) == 1
    assert merged[0]["source"] == "TESS"
    assert merged[0]["amount"] == 1000.0
    assert "Also seen in OA" in merged[0]["notes"]
    assert "Also seen in MANUAL" in merged[0]["notes"]


def test_merge_received_distinct_refs_all_kept():
    tess = [{"source": "TESS", "booking_ref": "B1", "client_name": "A",
             "supplier": "S1", "amount": 100.0, "date": "2026-06-01", "notes": ""}]
    oa = [{"source": "OA", "booking_ref": "B2", "client_name": "B",
           "supplier": "S2", "amount": 200.0, "date": "2026-06-02", "notes": ""}]
    manual = [{"source": "MANUAL", "booking_ref": "B3", "client_name": "C",
               "supplier": "S3", "amount": 300.0, "date": "2026-06-03", "notes": ""}]
    merged = merge_received(tess, oa, manual)
    assert {m["booking_ref"] for m in merged} == {"B1", "B2", "B3"}


# ---------------------------------------------------------------------------
# reconcile_month — 6-month synthetic historical dataset
# ---------------------------------------------------------------------------

def _synthetic_dataset():
    """Builds 6 months (2026-01..2026-06) of expected + received commissions.

    Per month, seeds:
      - 3 clean matches (delta well under both thresholds)
      - 1 discrepancy flagged by percentage only (small $, big %)
      - 1 discrepancy flagged by dollar amount only (big $, small %)
      - 1 unmatched receipt (booking_ref not present in Booking Master)

    Returns (expected, received, expected_flagged_refs, expected_unmatched_refs).
    """
    months = ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"]
    expected = []
    received = []
    flagged_refs = []
    unmatched_refs = []

    for i, month in enumerate(months):
        base = i * 100

        # 3 clean matches
        for j in range(3):
            ref = f"CLEAN-{base + j}"
            expected.append({"booking_id": ref, "client_name": f"Client{base+j}",
                              "supplier": "RSSC", "expected_commission": 1000.0 + j, "status": "active"})
            received.append({"source": "TESS", "booking_ref": ref, "client_name": f"Client{base+j}",
                              "supplier": "RSSC", "amount": 1000.0 + j + 5.0,  # +$5, 0.5% — clean
                              "date": f"{month}-10", "notes": ""})

        # percentage-only discrepancy: expected $400, received $350 (12.5% / $50)
        pct_ref = f"PCTFLAG-{base}"
        expected.append({"booking_id": pct_ref, "client_name": "PctClient",
                          "supplier": "Viking", "expected_commission": 400.0, "status": "active"})
        received.append({"source": "TESS", "booking_ref": pct_ref, "client_name": "PctClient",
                          "supplier": "Viking", "amount": 350.0, "date": f"{month}-12", "notes": ""})
        flagged_refs.append(pct_ref)

        # dollar-only discrepancy: expected $6000, received $5850 (2.5% / $150)
        dollar_ref = f"DOLLARFLAG-{base}"
        expected.append({"booking_id": dollar_ref, "client_name": "DollarClient",
                          "supplier": "Silversea", "expected_commission": 6000.0, "status": "active"})
        received.append({"source": "TESS", "booking_ref": dollar_ref, "client_name": "DollarClient",
                          "supplier": "Silversea", "amount": 5850.0, "date": f"{month}-15", "notes": ""})
        flagged_refs.append(dollar_ref)

        # unmatched receipt — no corresponding expected entry at all
        unmatched_ref = f"UNMATCHED-{base}"
        received.append({"source": "OA", "booking_ref": unmatched_ref, "client_name": "Unknown",
                          "supplier": "OA-Host", "amount": 777.0, "date": f"{month}-20", "notes": ""})
        unmatched_refs.append(unmatched_ref)

    return expected, received, flagged_refs, unmatched_refs


def test_reconcile_month_flags_only_the_true_discrepancies():
    expected, received, expected_flagged_refs, expected_unmatched_refs = _synthetic_dataset()

    results = reconcile_month(expected, received)

    flagged_refs = {f["booking_ref"] for f in results["flagged"]}
    matched_refs = {m["booking_ref"] for m in results["matched"]}
    unmatched_refs = {u["booking_ref"] for u in results["unmatched"]}

    # No false positives: every flagged ref must be one of the deliberately-seeded discrepancies.
    assert flagged_refs == set(expected_flagged_refs)

    # No false negatives: every clean match must NOT appear in flagged.
    assert not (matched_refs & flagged_refs)

    # Unmatched receipts are exactly the seeded orphan refs.
    assert unmatched_refs == set(expected_unmatched_refs)

    # Across 6 months: 3 clean * 6 = 18 matched, 2 flagged * 6 = 12 flagged, 1 unmatched * 6 = 6 unmatched.
    assert results["counts"]["matched"] == 18
    assert results["counts"]["flagged"] == 12
    assert results["counts"]["unmatched"] == 6
    assert results["counts"]["received_items"] == 36


def test_reconcile_month_totals_only_include_matched_and_flagged_expected():
    expected, received, *_ = _synthetic_dataset()
    results = reconcile_month(expected, received)

    # total_expected_for_matched_bookings should equal sum of expected_commission
    # across matched + flagged (unmatched receipts have no expected figure).
    manual_total = sum(
        e["expected_commission"] for e in expected
        if e["booking_id"] in {m["booking_ref"] for m in results["matched"]}
        or e["booking_id"] in {f["booking_ref"] for f in results["flagged"]}
    )
    assert results["totals"]["total_expected_for_matched_bookings"] == round(manual_total, 2)


def test_reconcile_month_empty_inputs_returns_zero_counts():
    results = reconcile_month([], [])
    assert results["counts"] == {
        "received_items": 0, "matched": 0, "flagged": 0, "unmatched": 0,
    }
