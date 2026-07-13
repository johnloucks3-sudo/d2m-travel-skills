#!/usr/bin/env python3
"""
Offline tests for scripts.tcd_data.count_untouched_elon_proposals — the
MISSION-001A ELON proposal-backlog proxy count.

    python -m pytest tests/test_tcd_data_elon.py -v
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import json

from tcd_data import (count_untouched_elon_proposals, build_a7_metrics_alert,  # noqa: E402
                       build_staff_cadence_alert)


def test_missing_dir_returns_none(tmp_path):
    assert count_untouched_elon_proposals(tmp_path / "nope") is None


def test_empty_dir_zero_counts(tmp_path):
    assert count_untouched_elon_proposals(tmp_path) == {"total": 0, "untouched": 0, "touched": 0}


def test_proposal_with_no_execution_reference_is_untouched(tmp_path):
    (tmp_path / "PROPOSAL-20260601-foo.md").write_text("a proposal")
    result = count_untouched_elon_proposals(tmp_path)
    assert result == {"total": 1, "untouched": 1, "touched": 0}


def test_proposal_referenced_in_execution_file_is_touched(tmp_path):
    (tmp_path / "PROPOSAL-20260601-foo.md").write_text("a proposal")
    (tmp_path / "FOO_EXECUTION.md").write_text(
        "# EXECUTION — PROPOSAL-20260601-foo\nDone.")
    result = count_untouched_elon_proposals(tmp_path)
    assert result == {"total": 1, "untouched": 0, "touched": 1}

def test_execution_reference_with_trailing_md_still_matches(tmp_path):
    (tmp_path / "PROPOSAL-20260601-foo.md").write_text("a proposal")
    (tmp_path / "FOO_EXECUTION.md").write_text(
        "Recommend marking `PROPOSAL-20260601-foo.md` as superseded.")
    result = count_untouched_elon_proposals(tmp_path)
    assert result["untouched"] == 0


def test_mixed_touched_and_untouched(tmp_path):
    (tmp_path / "PROPOSAL-20260601-foo.md").write_text("x")
    (tmp_path / "PROPOSAL-20260602-bar.md").write_text("x")
    (tmp_path / "FOO_EXECUTION.md").write_text("PROPOSAL-20260601-foo")
    result = count_untouched_elon_proposals(tmp_path)
    assert result == {"total": 2, "untouched": 1, "touched": 1}


class TestA7MetricsAlert:
    def test_green_overall_emits_nothing(self, tmp_path):
        p = tmp_path / "a7.json"
        p.write_text(json.dumps({"continuity_recert": {"overall": "GREEN"}}))
        assert build_a7_metrics_alert(p) is None

    def test_missing_file_emits_nothing(self, tmp_path):
        assert build_a7_metrics_alert(tmp_path / "nope.json") is None

    def test_red_overall_emits_decision_item(self, tmp_path):
        p = tmp_path / "a7.json"
        p.write_text(json.dumps({
            "generated_at": "2026-07-13T12:00:00Z",
            "continuity_recert": {
                "overall": "RED",
                "timestamp": "2026-07-13T12:00:00Z",
                "red_items": ["failed_unit_count=6 (threshold >2)"],
            },
        }))
        item = build_a7_metrics_alert(p)
        assert item["id"] == "a7metrics-continuity"
        assert item["type"] == "decision"
        assert "RED" in item["title"]
        assert "failed_unit_count=6" in item["body"]


class TestStaffCadenceAlert:
    def test_latest_open_emits_nothing(self, tmp_path):
        p = tmp_path / "cadence.json"
        p.write_text(json.dumps({"runs": [
            {"run_date": "2026-07-07", "gate_decision": "THROTTLED — x"},
            {"run_date": "2026-07-12", "gate_decision": "OPEN — cadence slots issued"},
        ]}))
        assert build_staff_cadence_alert(p) is None

    def test_no_runs_emits_nothing(self, tmp_path):
        p = tmp_path / "cadence.json"
        p.write_text(json.dumps({"runs": []}))
        assert build_staff_cadence_alert(p) is None

    def test_latest_throttled_emits_decision_item(self, tmp_path):
        p = tmp_path / "cadence.json"
        p.write_text(json.dumps({"runs": [
            {"run_date": "2026-07-07", "gate_decision": "OPEN — x"},
            {"run_date": "2026-07-14", "gate_decision": "THROTTLED — integration debt",
             "detail": {"unwired_count": 16}},
        ]}))
        item = build_staff_cadence_alert(p)
        assert item["id"] == "cadence-2026-07-14"
        assert item["type"] == "decision"
        assert "THROTTLED" in item["title"]
        assert "unwired_count" in item["body"]
