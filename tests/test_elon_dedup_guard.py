#!/usr/bin/env python3
"""
MISSION-647: board-level find_open_duplicate guard on the two ELON
mission-creation paths (synthesis + adopt pipeline) that previously appended
straight to the board with no board-level dedup.

Offline: MISSION_BOARD + adopt-log/watch-list I/O are redirected to tmp; no
network, no real board writes.
    python3 -m pytest tests/test_elon_dedup_guard.py -v
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "intel" / "daily_search"))

import elon_daily_synthesis as syn  # noqa: E402
import elon_adopt_pipeline as adopt  # noqa: E402


def _titles(board_path):
    mb = json.loads(board_path.read_text())
    return [m["title"] for m in mb["missions"]]


class TestSynthesisBoardDedup:
    def _wire(self, tmp_path, monkeypatch):
        board = tmp_path / "mission_board.json"
        board.write_text(json.dumps({"missions": []}))
        monkeypatch.setattr(syn, "MISSION_BOARD", board)
        # Fresh adopt-log/watch-list each call so the name-key dedup never
        # short-circuits — this isolates the BOARD-level guard under test.
        monkeypatch.setattr(syn, "_load_adopt_log", lambda: {"promoted": {}})
        monkeypatch.setattr(syn, "_save_adopt_log", lambda log: None)
        monkeypatch.setattr(syn, "_load_watch_list", lambda: {"watches": []})
        monkeypatch.setattr(syn, "_save_watch_list", lambda wl: None)
        return board

    def test_implement_now_duplicate_not_filed_twice(self, tmp_path, monkeypatch):
        board = self._wire(tmp_path, monkeypatch)
        synthesis = {"decisions": [{
            "name": "CoolTool", "decision": "IMPLEMENT_NOW",
            "rationale": "useful", "wave": 1, "implementation_notes": "wire it",
        }]}
        syn._apply_decisions(synthesis)
        syn._apply_decisions(synthesis)  # identical re-run
        titles = _titles(board)
        assert titles.count("IMPLEMENT_NOW: CoolTool") == 1, titles
        # The existing open mission carries the block log.
        mb = json.loads(board.read_text())
        dup = [m for m in mb["missions"] if m["title"] == "IMPLEMENT_NOW: CoolTool"][0]
        assert any("duplicate blocked" in l for l in dup["logs"])

    def test_escalate_duplicate_not_filed_twice(self, tmp_path, monkeypatch):
        board = self._wire(tmp_path, monkeypatch)
        synthesis = {"decisions": [{
            "name": "RiskyThing", "decision": "ESCALATE",
            "rationale": "needs review", "wave": 2,
        }]}
        syn._apply_decisions(synthesis)
        syn._apply_decisions(synthesis)
        assert _titles(board).count("ELON ESCALATE: RiskyThing") == 1

    def test_distinct_names_both_filed(self, tmp_path, monkeypatch):
        board = self._wire(tmp_path, monkeypatch)
        synthesis = {"decisions": [
            {"name": "ToolA", "decision": "IMPLEMENT_NOW", "rationale": "a", "wave": 1},
            {"name": "ToolB", "decision": "IMPLEMENT_NOW", "rationale": "b", "wave": 1},
        ]}
        syn._apply_decisions(synthesis)
        titles = _titles(board)
        assert "IMPLEMENT_NOW: ToolA" in titles
        assert "IMPLEMENT_NOW: ToolB" in titles
        assert len(titles) == 2


class TestFindBoardDuplicate:
    def test_synthesis_matches_open_active_mission(self):
        missions = [{"id": "MISSION-500", "title": "IMPLEMENT_NOW: FooTool", "status": "active"}]
        assert syn._find_board_duplicate(missions, "IMPLEMENT_NOW: FooTool")["id"] == "MISSION-500"
        assert syn._find_board_duplicate(missions, "IMPLEMENT_NOW: BarTool") is None

    def test_pipeline_matches_open_active_mission(self):
        missions = [{"id": "MISSION-600", "title": "INTEGRATE_NOW: FooTool", "status": "active"}]
        assert adopt._find_board_duplicate(missions, "INTEGRATE_NOW: FooTool")["id"] == "MISSION-600"
        assert adopt._find_board_duplicate(missions, "INTEGRATE_NOW: BarTool") is None

    def test_completed_mission_is_not_a_duplicate(self):
        # A finished mission of the same name should NOT block a fresh one.
        missions = [{"id": "MISSION-700", "title": "INTEGRATE_NOW: FooTool", "status": "completed"}]
        assert adopt._find_board_duplicate(missions, "INTEGRATE_NOW: FooTool") is None


class TestPipelineIntegrateDedup:
    """Full run_adopt_pipeline integration: analyze_wave + hard-prohibit are
    stubbed so the board-level guard is what's under test."""

    def _wire(self, tmp_path, monkeypatch, seed_missions, scored_items):
        board = tmp_path / "mission_board.json"
        board.write_text(json.dumps({"missions": seed_missions}))
        monkeypatch.setattr(adopt, "MISSION_BOARD", board)
        monkeypatch.setattr(adopt, "_load_adopt_log", lambda: {"promoted": {}})
        monkeypatch.setattr(adopt, "_save_adopt_log", lambda log: None)
        monkeypatch.setattr(adopt, "_hits_hard_prohibit", lambda item: None)
        import inter_wave_analyst as analyst
        monkeypatch.setattr(analyst, "analyze_wave", lambda wp: scored_items)
        wave = tmp_path / "wave3_test.json"
        wave.write_text("{}")
        return board, wave

    def test_integrate_now_blocked_when_board_dup_open(self, tmp_path, monkeypatch):
        # best_by_name would promote "NiftyAPI", but the board already tracks it
        # open under a different id -> the guard resolves to that id, no new row.
        scored = [{"name": "NiftyAPI", "score": 90.0, "id": "x",
                   "result": "a safe api", "result_preview": "a safe api"}]
        board, wave = self._wire(tmp_path, monkeypatch, [
            {"id": "MISSION-800", "title": "INTEGRATE_NOW: NiftyAPI", "status": "active"},
        ], scored)
        result = adopt.run_adopt_pipeline([wave], dry_run=False)
        assert _titles(board).count("INTEGRATE_NOW: NiftyAPI") == 1
        assert result["adopted"][0]["mission_id"] == "MISSION-800"

    def test_integrate_now_novel_name_appends_new(self, tmp_path, monkeypatch):
        scored = [{"name": "FreshTool", "score": 88.0, "id": "y",
                   "result": "a safe tool", "result_preview": "a safe tool"}]
        board, wave = self._wire(tmp_path, monkeypatch, [
            {"id": "MISSION-800", "title": "INTEGRATE_NOW: NiftyAPI", "status": "active"},
        ], scored)
        result = adopt.run_adopt_pipeline([wave], dry_run=False)
        assert "INTEGRATE_NOW: FreshTool" in _titles(board)
        assert result["adopted"][0]["mission_id"] != "MISSION-800"
