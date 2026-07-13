#!/usr/bin/env python3
"""
Offline tests for tcd.watchdog — the MISSION-001A Phase 3 generic
long-tail OpsCenter/*.json collector.

    python -m pytest tests/test_tcd_watchdog.py -v
"""
import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tcd import watchdog  # noqa: E402


class TestStaffTasking:
    def test_no_critical_tasks_emits_nothing(self):
        assert watchdog._extract_staff_tasking({"tasks": [{"critical": False}]}) is None

    def test_empty_emits_nothing(self):
        assert watchdog._extract_staff_tasking({}) is None

    def test_critical_task_emits_item(self):
        d = {"generated_at": "2026-07-13T06:00:00", "tasks": [
            {"task_id": "T1", "client": "kuklinski", "deliverable": "x",
             "draft_due": "2026-07-10T00:00:00", "critical": True},
        ]}
        item = watchdog._extract_staff_tasking(d)
        assert item["id"] == "watch-staff-tasking-critical"
        assert item["type"] == "decision"
        assert "kuklinski" in item["body"]


class TestHaleIncidents:
    def test_zero_unresolved_emits_nothing(self):
        assert watchdog._extract_hale_incidents({"summary": {"unresolved": 0}}) is None

    def test_unresolved_emits_item(self):
        d = {"date": "2026-07-13", "summary": {"unresolved": 2},
             "incidents": [{"time": "09:00", "service": "x", "status": "RED", "note": "down"}]}
        item = watchdog._extract_hale_incidents(d)
        assert item["id"] == "watch-incidents-2026-07-13"
        assert "2 unresolved" in item["title"]


class TestPredictionLedger:
    def test_non_list_input_emits_nothing(self):
        assert watchdog._extract_prediction_ledger({}) is None

    def test_recent_open_predictions_not_stale(self):
        today = date.today().isoformat()
        d = [{"id": "P1", "status": "open", "date_predicted": today}]
        assert watchdog._extract_prediction_ledger(d) is None

    def test_stale_open_prediction_emits_item(self):
        old = (date.today() - timedelta(days=10)).isoformat()
        d = [{"id": "P1", "status": "open", "date_predicted": old, "predicted_action": "do the thing"}]
        item = watchdog._extract_prediction_ledger(d)
        assert item["id"] == "watch-prediction-ledger-stale"
        assert "1 open prediction" in item["title"]

    def test_resolved_prediction_not_counted(self):
        old = (date.today() - timedelta(days=10)).isoformat()
        d = [{"id": "P1", "status": "resolved", "date_predicted": old}]
        assert watchdog._extract_prediction_ledger(d) is None


class TestIncubatorGate:
    def test_no_gate_candidate_emits_nothing(self):
        assert watchdog._extract_incubator_gate({}) is None

    def test_non_approved_status_emits_nothing(self):
        d = {"gate_candidate": {"name": "x", "status": "pending"}}
        assert watchdog._extract_incubator_gate(d) is None

    def test_approved_gate_emits_item(self):
        d = {"last_updated": "2026-07-13T00:00:00", "gate_candidate": {
            "name": "claude agents --json session monitor", "owner": "Sterling",
            "status": "approved", "description": "Wire it in"}}
        item = watchdog._extract_incubator_gate(d)
        assert item["type"] == "decision"
        assert "claude agents" in item["title"]


class TestRegistryScaffold:
    def test_missing_file_skipped_not_raised(self, tmp_path):
        registry = ((tmp_path / "nope.json", watchdog._extract_staff_tasking),)
        assert watchdog.collect_watchdog(registry) == []

    def test_one_bad_file_does_not_block_the_rest(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("{not valid json")
        good = tmp_path / "good.json"
        good.write_text(json.dumps({"summary": {"unresolved": 1},
                                    "incidents": [], "date": "2026-07-13"}))
        registry = (
            (bad, watchdog._extract_hale_incidents),
            (good, watchdog._extract_hale_incidents),
        )
        items = watchdog.collect_watchdog(registry)
        assert len(items) == 1
        assert items[0]["id"] == "watch-incidents-2026-07-13"

    def test_extract_fn_exception_isolated(self, tmp_path):
        ok = tmp_path / "ok.json"
        ok.write_text(json.dumps({}))

        def boom(d):
            raise RuntimeError("bad extractor")

        def fine(d):
            return {"id": "watch-fine", "inbox": "operational", "folder": "o-inbox",
                    "type": "decision", "priority": "p2", "unread": True,
                    "title": "ok", "from": "x", "date": "", "snippet": "", "body": "",
                    "tags": [], "comments": []}

        registry = ((ok, boom), (ok, fine))
        items = watchdog.collect_watchdog(registry)
        assert len(items) == 1
        assert items[0]["id"] == "watch-fine"

    def test_default_registry_runs_against_real_files_without_raising(self):
        # Whatever's currently on disk -- must never raise, even if some
        # OpsCenter file is missing or malformed.
        items = watchdog.collect_watchdog()
        assert isinstance(items, list)
