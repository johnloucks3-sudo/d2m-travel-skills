#!/usr/bin/env python3
"""
Unit tests — lifecycle_scheduler.py date-window math.
Tests written BEFORE code changes (guardrail per LIFECYCLE_AIRSCAN_VALIDATION_20260609.md).
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import date, timedelta
import pytest

# Import after path setup — will fail until calculate_due_phases is updated
# to the new signature: (lifecycle, check_date, lookback_days=14, client_sent=None) -> (due, stale)
from core.lifecycle.lifecycle_scheduler import calculate_due_phases


TODAY = date(2026, 6, 9)


def make_lifecycle(*phases):
    return {"phases": list(phases)}


def make_phase(phase_id, due_date, status="scheduled"):
    return {"phase_id": phase_id, "due_date": due_date, "status": status}


# ─────────────────────────────────────────────────────────────────────────────
# calculate_due_phases — core date math
# ─────────────────────────────────────────────────────────────────────────────

class TestCalculateDuePhasesDateMath:
    def test_exact_today_fires(self):
        """Phase due exactly today fires."""
        lc = make_lifecycle(make_phase("TP_7", str(TODAY)))
        due, stale = calculate_due_phases(lc, TODAY)
        assert len(due) == 1
        assert due[0]["phase_id"] == "TP_7"
        assert len(stale) == 0

    def test_overdue_within_lookback_fires(self):
        """Phase 7 days overdue within a 14-day window fires (catch-up)."""
        overdue_date = TODAY - timedelta(days=7)
        lc = make_lifecycle(make_phase("TP_7", str(overdue_date)))
        due, stale = calculate_due_phases(lc, TODAY, lookback_days=14)
        assert len(due) == 1

    def test_overdue_at_lookback_edge_fires(self):
        """Phase exactly lookback_days overdue still fires (edge inclusive)."""
        edge_date = TODAY - timedelta(days=14)
        lc = make_lifecycle(make_phase("TP_7", str(edge_date)))
        due, stale = calculate_due_phases(lc, TODAY, lookback_days=14)
        assert len(due) == 1

    def test_overdue_outside_lookback_goes_to_stale(self):
        """Phase 30 days overdue with 14-day window → stale, not due."""
        old_date = TODAY - timedelta(days=30)
        lc = make_lifecycle(make_phase("TP_1", str(old_date)))
        due, stale = calculate_due_phases(lc, TODAY, lookback_days=14)
        assert len(due) == 0
        assert len(stale) == 1
        assert stale[0]["phase_id"] == "TP_1"

    def test_future_phase_fires_neither(self):
        """Future phase produces no output."""
        future_date = TODAY + timedelta(days=5)
        lc = make_lifecycle(make_phase("TP_8", str(future_date)))
        due, stale = calculate_due_phases(lc, TODAY, lookback_days=14)
        assert len(due) == 0
        assert len(stale) == 0

    def test_lookback_zero_means_today_only(self):
        """lookback_days=0 fires only exact today; yesterday goes to stale."""
        yesterday = TODAY - timedelta(days=1)
        lc = make_lifecycle(
            make_phase("TP_A", str(TODAY)),
            make_phase("TP_B", str(yesterday)),
        )
        due, stale = calculate_due_phases(lc, TODAY, lookback_days=0)
        due_ids = {p["phase_id"] for p in due}
        stale_ids = {p["phase_id"] for p in stale}
        assert due_ids == {"TP_A"}
        assert stale_ids == {"TP_B"}


# ─────────────────────────────────────────────────────────────────────────────
# calculate_due_phases — status exclusions
# ─────────────────────────────────────────────────────────────────────────────

class TestCalculateDuePhasesStatusExclusions:
    def test_sent_excluded(self):
        """status=sent phases are never re-fired."""
        lc = make_lifecycle(make_phase("TP_7", str(TODAY), status="sent"))
        due, stale = calculate_due_phases(lc, TODAY)
        assert len(due) == 0
        assert len(stale) == 0

    def test_obe_excluded(self):
        """status=obe phases are never fired."""
        lc = make_lifecycle(make_phase("TP_0.5", str(TODAY), status="obe"))
        due, stale = calculate_due_phases(lc, TODAY)
        assert len(due) == 0

    def test_non_scheduled_statuses_excluded(self):
        """Any status that isn't 'scheduled' is excluded."""
        lc = make_lifecycle(
            make_phase("TP_A", str(TODAY), status="sent"),
            make_phase("TP_B", str(TODAY), status="obe"),
            make_phase("TP_C", str(TODAY), status="sent"),
            make_phase("TP_D", str(TODAY), status="scheduled"),  # only this fires
        )
        due, stale = calculate_due_phases(lc, TODAY)
        assert len(due) == 1
        assert due[0]["phase_id"] == "TP_D"

    def test_tbd_due_date_skipped(self):
        """Phases with TBD/null/NEEDED due dates skip gracefully."""
        lc = make_lifecycle(
            make_phase("TP_X", "TBD"),
            make_phase("TP_Y", None),
            make_phase("TP_Z", "NEEDED"),
        )
        due, stale = calculate_due_phases(lc, TODAY)
        assert len(due) == 0


# ─────────────────────────────────────────────────────────────────────────────
# calculate_due_phases — ledger idempotency
# ─────────────────────────────────────────────────────────────────────────────

class TestCalculateDuePhasesLedger:
    def test_ledger_prevents_refire(self):
        """Phase in sent ledger is not re-fired even if scheduled + within window."""
        lc = make_lifecycle(make_phase("TP_7", str(TODAY)))
        client_sent = {"TP_7": {"sent_date": str(TODAY), "draft_id": "draft_abc"}}
        due, stale = calculate_due_phases(lc, TODAY, client_sent=client_sent)
        assert len(due) == 0

    def test_ledger_only_blocks_matching_phase(self):
        """Ledger entry for TP_7 does not block TP_8."""
        lc = make_lifecycle(
            make_phase("TP_7", str(TODAY)),
            make_phase("TP_8", str(TODAY)),
        )
        client_sent = {"TP_7": {"sent_date": str(TODAY), "draft_id": "draft_abc"}}
        due, stale = calculate_due_phases(lc, TODAY, client_sent=client_sent)
        assert len(due) == 1
        assert due[0]["phase_id"] == "TP_8"

    def test_empty_ledger_behaves_normally(self):
        """Empty ledger dict has no effect."""
        lc = make_lifecycle(make_phase("TP_7", str(TODAY)))
        due, stale = calculate_due_phases(lc, TODAY, client_sent={})
        assert len(due) == 1

    def test_none_ledger_behaves_normally(self):
        """None ledger (default) has no effect."""
        lc = make_lifecycle(make_phase("TP_7", str(TODAY)))
        due, stale = calculate_due_phases(lc, TODAY, client_sent=None)
        assert len(due) == 1


# ─────────────────────────────────────────────────────────────────────────────
# calculate_due_phases — multi-phase mixed scenario
# ─────────────────────────────────────────────────────────────────────────────

class TestCalculateDuePhasesIntegration:
    def test_mixed_scenario(self):
        """Full mixed scenario: due, overdue-in-window, stale, future, sent."""
        lc = make_lifecycle(
            make_phase("TP_A", str(TODAY)),                               # today → due
            make_phase("TP_B", str(TODAY - timedelta(days=7))),          # 7d overdue → due
            make_phase("TP_C", str(TODAY - timedelta(days=30))),         # 30d overdue → stale
            make_phase("TP_D", str(TODAY + timedelta(days=5))),          # future → neither
            make_phase("TP_E", str(TODAY), status="sent"),               # sent → excluded
            make_phase("TP_F", str(TODAY), status="obe"),                # obe → excluded
        )
        due, stale = calculate_due_phases(lc, TODAY, lookback_days=14)
        due_ids = {p["phase_id"] for p in due}
        stale_ids = {p["phase_id"] for p in stale}
        assert due_ids == {"TP_A", "TP_B"}
        assert stale_ids == {"TP_C"}

    def test_furlow_tp7_catches_up(self):
        """Furlow TP_7 overdue since 2026-05-31 fires with 14-day lookback."""
        lc = make_lifecycle(make_phase("TP_7", "2026-05-31"))  # 9 days overdue
        due, stale = calculate_due_phases(lc, TODAY, lookback_days=14)
        assert len(due) == 1, "Furlow TP_7 should catch up"

    def test_mcleod_tp1_248d_stale(self):
        """McLeod TP_1 248 days overdue goes to stale, not due."""
        lc = make_lifecycle(make_phase("TP_1", "2025-10-04"))  # 248d overdue
        due, stale = calculate_due_phases(lc, TODAY, lookback_days=14)
        assert len(due) == 0
        assert len(stale) == 1, "McLeod TP_1 should be stale, not auto-drafted"

    def test_kuklinski_tp3_93d_stale(self):
        """Kuklinski TP_3 93 days overdue goes to stale with default lookback."""
        lc = make_lifecycle(make_phase("TP_3", "2026-03-08"))  # 93d overdue
        due, stale = calculate_due_phases(lc, TODAY, lookback_days=14)
        assert len(due) == 0
        assert len(stale) == 1, "Kuklinski TP_3 should be stale, not auto-drafted"


# ─────────────────────────────────────────────────────────────────────────────
# run_scheduler — dead-man's-switch (P0: "produced nothing when work was due"
# must never be silent). Covers the run_scheduler paging path, not just the
# date math — the prior session's tests stopped at calculate_due_phases.
# ─────────────────────────────────────────────────────────────────────────────

import yaml as _yaml
from core.lifecycle import lifecycle_scheduler as _ls


def _write_client_yaml(dirpath, client_id, phase_id, due_date, departure=None):
    """Write a minimal active-client Blackboard YAML with one scheduled phase."""
    doc = {
        "client_id": client_id,
        "client_names": "Test Client",
        "status": "active",
        "contacts": [{"role": "primary", "email": "test@example.com"}],
        "bookings": [{"booking_type": "cruise", "embarkation_date": departure or "2026-12-31"}],
        "lifecycle": {
            "departure_date": departure or "2026-12-31",
            "phases": [{"phase_id": phase_id, "due_date": due_date, "status": "scheduled"}],
        },
    }
    (dirpath / f"{client_id}.yaml").write_text(_yaml.safe_dump(doc))


class TestDeadMansSwitch:
    def _isolate(self, tmp_path, monkeypatch, draft_return):
        """Point scheduler at a temp Blackboard + ledger, stub draft+telegram, capture pages."""
        bb = tmp_path / "clients"
        bb.mkdir()
        monkeypatch.setattr(_ls, "BLACKBOARD_DIR", bb)
        monkeypatch.setattr(_ls, "SENT_LEDGER_PATH", tmp_path / "ledger.json")
        monkeypatch.setattr(_ls, "AUDIT_LOG", tmp_path / "audit.jsonl")
        pages = []
        monkeypatch.setattr(_ls, "send_telegram_notification", lambda m: pages.append(m))
        monkeypatch.setattr(_ls, "create_gmail_draft", lambda **kw: draft_return)
        return bb, pages

    def test_switch_fires_when_due_but_zero_drafts(self, tmp_path, monkeypatch):
        """Phase due, draft creation fails (returns None) → 0 drafts → MUST page."""
        bb, pages = self._isolate(tmp_path, monkeypatch, draft_return=None)
        _write_client_yaml(bb, "acme", "TP_7", str(TODAY))  # due today
        result = _ls.run_scheduler(TODAY, dry_run=False)
        assert result["phases_due"] == 1
        assert result["drafts_created"] == 0
        switch = [m for m in pages if "DEAD MAN'S SWITCH" in m]
        assert switch, "Dead-man's-switch MUST page when work was due but 0 drafts produced"

    def test_switch_silent_when_drafts_created(self, tmp_path, monkeypatch):
        """Phase due, draft succeeds → switch must NOT fire (no false page)."""
        bb, pages = self._isolate(tmp_path, monkeypatch, draft_return="draft_xyz")
        _write_client_yaml(bb, "acme", "TP_7", str(TODAY))
        result = _ls.run_scheduler(TODAY, dry_run=False)
        assert result["drafts_created"] == 1
        assert not [m for m in pages if "DEAD MAN'S SWITCH" in m], \
            "Switch must stay silent when drafts were produced"

    def test_no_switch_when_nothing_due(self, tmp_path, monkeypatch):
        """No phase due (future) → no drafts expected → switch must NOT fire."""
        bb, pages = self._isolate(tmp_path, monkeypatch, draft_return=None)
        _write_client_yaml(bb, "acme", "TP_7", str(TODAY + timedelta(days=60)))  # future
        result = _ls.run_scheduler(TODAY, dry_run=False)
        assert result["phases_due"] == 0
        assert result["drafts_created"] == 0
        assert not [m for m in pages if "DEAD MAN'S SWITCH" in m], \
            "Switch must not fire when no work was due (0 due, 0 drafts is correct)"
