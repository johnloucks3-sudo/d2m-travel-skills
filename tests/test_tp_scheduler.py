#!/usr/bin/env python3
"""
Unit tests — thunderbird_tp_scheduler.py date-window math + completion model.
Tests written BEFORE code changes (guardrail per LIFECYCLE_AIRSCAN_VALIDATION_20260609.md).
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import date
import pytest

from core.booking.thunderbird_tp_scheduler import (
    DossierRecord,
    _compute_ref_date,
    generate_schedule,
    get_actionable_tps,
    DateRef,
    TPDef,
    TPStatus,
)


def make_rec(
    client="TestClient",
    departure=None,
    return_date=None,
    booking_date=None,
    fpd=None,
    completed_tps=None,
):
    rec = DossierRecord(path=Path("/fake/test.md"), client=client)
    rec.departure = departure
    rec.return_date = return_date
    rec.booking_date = booking_date
    rec.fpd = fpd
    rec.completed_tps = set(completed_tps) if completed_tps else set()
    return rec


def make_tp(tp_id, trigger_ref, window_start, window_end, label="Test TP"):
    return TPDef(tp_id, label, 5, "Post-Voyage", trigger_ref, window_start, window_end, "Hale")


# ─────────────────────────────────────────────────────────────────────────────
# _compute_ref_date — POST_DEP uses return_date
# ─────────────────────────────────────────────────────────────────────────────

class TestComputeRefDate:
    DEP  = date(2026, 8, 29)
    RET  = date(2026, 9, 8)
    BOOK = date(2025, 9, 15)
    FPD  = date(2026, 4, 1)

    def test_post_dep_uses_return_date(self):
        """POST_DEP trigger returns return_date, not departure."""
        rec = make_rec(departure=self.DEP, return_date=self.RET)
        tp  = make_tp("5.1", DateRef.POST_DEP, 7, 10)
        assert _compute_ref_date(tp, rec) == self.RET

    def test_post_dep_not_departure(self):
        """POST_DEP never returns departure date (regression guard)."""
        rec = make_rec(departure=self.DEP, return_date=self.RET)
        tp  = make_tp("5.1", DateRef.POST_DEP, 7, 10)
        result = _compute_ref_date(tp, rec)
        assert result != self.DEP, "POST_DEP must not use departure — it fires mid-voyage"

    def test_post_dep_missing_return_gives_none(self):
        """POST_DEP with return_date=None → None → TP becomes BLOCKED."""
        rec = make_rec(departure=self.DEP, return_date=None)
        tp  = make_tp("5.1", DateRef.POST_DEP, 7, 10)
        assert _compute_ref_date(tp, rec) is None

    def test_departure_ref_uses_departure(self):
        """DEPARTURE trigger still uses departure date."""
        rec = make_rec(departure=self.DEP, return_date=self.RET)
        tp  = make_tp("3.1", DateRef.DEPARTURE, -28, -21)
        assert _compute_ref_date(tp, rec) == self.DEP

    def test_booking_missing_gives_none(self):
        """BOOKING with booking_date=None → None → TP becomes BLOCKED (no mtime fallback)."""
        rec = make_rec(departure=self.DEP, booking_date=None)
        tp  = make_tp("0.5", DateRef.BOOKING, 0, 7)
        assert _compute_ref_date(tp, rec) is None

    def test_booking_with_date_returns_date(self):
        """BOOKING with booking_date set returns it."""
        rec = make_rec(booking_date=self.BOOK)
        tp  = make_tp("0.5", DateRef.BOOKING, 0, 7)
        assert _compute_ref_date(tp, rec) == self.BOOK

    def test_fpd_ref_uses_fpd(self):
        """FPD trigger uses fpd date."""
        rec = make_rec(fpd=self.FPD)
        tp  = make_tp("4.1", DateRef.FPD, -21, -14)
        assert _compute_ref_date(tp, rec) == self.FPD

    def test_fpd_missing_gives_none(self):
        """FPD with fpd=None → None → TP becomes BLOCKED."""
        rec = make_rec(fpd=None)
        tp  = make_tp("4.1", DateRef.FPD, -21, -14)
        assert _compute_ref_date(tp, rec) is None


# ─────────────────────────────────────────────────────────────────────────────
# generate_schedule — completion model
# ─────────────────────────────────────────────────────────────────────────────

class TestCompletionModel:
    # Use dates that make TPs clearly OVERDUE without completed_tps
    DEP  = date(2027, 6, 9)    # departure 1 year out
    RET  = date(2027, 6, 19)
    BOOK = date(2025, 6, 9)    # booked 2 years ago → BOOKING TPs overdue
    FPD  = date(2027, 3, 1)
    TODAY = date(2026, 6, 9)

    def _make_rec(self, completed_tps=None):
        return make_rec(
            departure=self.DEP,
            return_date=self.RET,
            booking_date=self.BOOK,
            fpd=self.FPD,
            completed_tps=completed_tps,
        )

    def test_completed_tp_is_complete_not_overdue(self):
        """TP in completed_tps → TPStatus.COMPLETE, not OVERDUE."""
        rec = self._make_rec(completed_tps=["0.5"])
        schedule = generate_schedule(rec, self.TODAY)
        tp_dict = {s.tp_id: s for s in schedule}
        assert tp_dict["0.5"].status == TPStatus.COMPLETE

    def test_non_completed_overdue_tp_is_still_overdue(self):
        """TP not in completed_tps and past deadline → OVERDUE."""
        rec = self._make_rec(completed_tps=[])
        schedule = generate_schedule(rec, self.TODAY)
        tp_dict = {s.tp_id: s for s in schedule}
        # TP 0.5: booking_date+0 to +7 days → deadline 2025-06-16, today 2026-06-09 → OVERDUE
        assert tp_dict["0.5"].status == TPStatus.OVERDUE

    def test_complete_excluded_from_actionable(self):
        """COMPLETE TPs are excluded from get_actionable_tps output."""
        rec = self._make_rec(completed_tps=["0.5", "0.6"])
        schedule = generate_schedule(rec, self.TODAY)
        actionable = get_actionable_tps(schedule, horizon_days=7, today=self.TODAY)
        tp_ids = {s.tp_id for s in actionable}
        assert "0.5" not in tp_ids
        assert "0.6" not in tp_ids

    def test_multiple_completed_tps(self):
        """Multiple completed TPs all show COMPLETE."""
        completed = ["0.5", "0.6", "4.1", "4.2", "4.3", "4.4", "4.5"]
        rec = self._make_rec(completed_tps=completed)
        schedule = generate_schedule(rec, self.TODAY)
        tp_dict = {s.tp_id: s for s in schedule}
        for tp_id in completed:
            assert tp_dict[tp_id].status == TPStatus.COMPLETE, \
                f"TP {tp_id} should be COMPLETE"

    def test_empty_completed_tps_no_false_completes(self):
        """Empty completed_tps set doesn't produce any spurious COMPLETE status."""
        rec = self._make_rec(completed_tps=[])
        schedule = generate_schedule(rec, self.TODAY)
        complete_count = sum(1 for s in schedule if s.status == TPStatus.COMPLETE)
        assert complete_count == 0

    def test_completed_tp_not_in_actionable_reduces_noise(self):
        """Marking payment TPs complete removes them from actionable list."""
        # Without marking complete, payment TPs appear as OVERDUE
        rec_no_complete = self._make_rec(completed_tps=[])
        sched_no = generate_schedule(rec_no_complete, self.TODAY)
        actionable_no = get_actionable_tps(sched_no, today=self.TODAY)
        overdue_no = {s.tp_id for s in actionable_no if s.status == TPStatus.OVERDUE}

        # With payment TPs marked complete, they disappear from actionable
        rec_with_complete = self._make_rec(completed_tps=["4.1", "4.2", "4.3", "4.4", "4.5"])
        sched_with = generate_schedule(rec_with_complete, self.TODAY)
        actionable_with = get_actionable_tps(sched_with, today=self.TODAY)
        overdue_with = {s.tp_id for s in actionable_with if s.status == TPStatus.OVERDUE}

        # Each payment TP removed from actionable
        for tp_id in ["4.1", "4.2", "4.3", "4.4", "4.5"]:
            assert tp_id not in overdue_with, f"TP {tp_id} should not be overdue when complete"


# ─────────────────────────────────────────────────────────────────────────────
# generate_schedule — BLOCKED when dates missing
# ─────────────────────────────────────────────────────────────────────────────

class TestBlockedStatus:
    DEP = date(2027, 6, 9)
    RET = date(2027, 6, 19)
    FPD = date(2027, 3, 1)

    def test_missing_booking_date_blocks_booking_tps(self):
        """When booking_date is None, BOOKING-ref TPs are BLOCKED (not mtime-computed)."""
        rec = make_rec(departure=self.DEP, return_date=self.RET, fpd=self.FPD, booking_date=None)
        schedule = generate_schedule(rec, date(2026, 6, 9))
        tp_dict = {s.tp_id: s for s in schedule}
        # TP 0.5 and 0.6 use DateRef.BOOKING — should be BLOCKED
        assert tp_dict["0.5"].status == TPStatus.BLOCKED
        assert tp_dict["0.6"].status == TPStatus.BLOCKED

    def test_missing_return_date_blocks_post_dep_tps(self):
        """When return_date is None, POST_DEP-ref TPs are BLOCKED."""
        rec = make_rec(
            departure=self.DEP, return_date=None, fpd=self.FPD,
            booking_date=date(2025, 6, 9)
        )
        schedule = generate_schedule(rec, date(2026, 6, 9))
        tp_dict = {s.tp_id: s for s in schedule}
        # TP 5.1-5.4 use DateRef.POST_DEP — should be BLOCKED
        for post_dep_tp in ["5.1", "5.2", "5.3", "5.4"]:
            assert tp_dict[post_dep_tp].status == TPStatus.BLOCKED, \
                f"TP {post_dep_tp} should be BLOCKED when return_date is missing"
