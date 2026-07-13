#!/usr/bin/env python3
"""
Offline tests for tcd.writeback — closing the AppSheet→Python loop.

No credentials, no network: rows/state/decisions-log/delete_fn are all
injected. Run:
    python -m pytest tests/test_tcd_writeback.py -v
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tcd import writeback  # noqa: E402


def _row(id="task-1", stage="A", status="Open", comments="", title="Test item"):
    return {"id": id, "inbox": "operational", "type": "brief", "priority": "p1",
            "stage": stage, "title": title, "from": "x", "date": "", "snippet": "",
            "body": "", "link": "https://x", "sourcePath": "hale_state.json:open_tasks",
            "comments": comments, "status": status}


def _fake_delete_ok(item_id):
    return {"ok": True, "source": f"hale_state.json:open_tasks:{item_id}"}


def _fake_delete_fail(item_id):
    return {"ok": False, "reason": "not found"}


class TestDisposeDetection:
    def test_new_dispose_triggers_delete(self, tmp_path):
        state_path = tmp_path / "state.json"
        decisions_path = tmp_path / "hale_decisions.md"
        rows = [_row(status="Delete")]
        result = writeback.process_once(rows, state_path=state_path,
                                        decisions_path=decisions_path,
                                        delete_fn=_fake_delete_ok)
        assert len(result["disposed"]) == 1
        assert result["disposed"][0]["ok"] is True
        assert result["errors"] == []

    def test_dispose_logged_to_decisions(self, tmp_path):
        state_path = tmp_path / "state.json"
        decisions_path = tmp_path / "hale_decisions.md"
        rows = [_row(id="task-99", status="Delete", title="Kill this")]
        writeback.process_once(rows, state_path=state_path,
                               decisions_path=decisions_path,
                               delete_fn=_fake_delete_ok)
        text = decisions_path.read_text()
        assert "PLAN:CLOSE" in text
        assert "TCD-DELETE-task-99" in text
        assert "verdict=PASS" in text
        assert "Kill this" in text

    def test_dispose_failure_logged_as_fail_verdict(self, tmp_path):
        state_path = tmp_path / "state.json"
        decisions_path = tmp_path / "hale_decisions.md"
        rows = [_row(status="Delete")]
        result = writeback.process_once(rows, state_path=state_path,
                                        decisions_path=decisions_path,
                                        delete_fn=_fake_delete_fail)
        assert result["disposed"][0]["ok"] is False
        assert "verdict=FAIL" in decisions_path.read_text()

    def test_dispose_only_fires_once(self, tmp_path):
        # Row already Delete last run (in state) -> don't re-delete on rerun.
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps({"task-1": {"status": "Delete",
                                                       "stage": "A", "comments": ""}}))
        decisions_path = tmp_path / "hale_decisions.md"
        rows = [_row(status="Delete")]
        calls = []
        def counting_delete(item_id):
            calls.append(item_id)
            return {"ok": True}
        result = writeback.process_once(rows, state_path=state_path,
                                        decisions_path=decisions_path,
                                        delete_fn=counting_delete)
        assert calls == []  # already processed, no re-delete
        assert result["disposed"] == []

    def test_open_status_never_disposes(self, tmp_path):
        state_path = tmp_path / "state.json"
        decisions_path = tmp_path / "hale_decisions.md"
        rows = [_row(status="Open")]
        result = writeback.process_once(rows, state_path=state_path,
                                        decisions_path=decisions_path,
                                        delete_fn=_fake_delete_ok)
        assert result["disposed"] == []
        assert not decisions_path.exists()


class TestCloseDetection:
    def test_new_close_logged_source_untouched(self, tmp_path):
        state_path = tmp_path / "state.json"
        decisions_path = tmp_path / "hale_decisions.md"
        calls = []
        def counting_delete(item_id):
            calls.append(item_id)
            return {"ok": True}
        rows = [_row(id="task-77", status="Closed", title="Done with this")]
        result = writeback.process_once(rows, state_path=state_path,
                                        decisions_path=decisions_path,
                                        delete_fn=counting_delete)
        assert len(result["closed"]) == 1
        assert calls == []  # Closed never calls delete_fn — source is untouched
        text = decisions_path.read_text()
        assert "TCD-CLOSE-task-77" in text
        assert "verdict=PASS" in text
        assert "Done with this" in text

    def test_close_only_fires_once(self, tmp_path):
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps({"task-1": {"status": "Closed",
                                                       "stage": "A", "comments": ""}}))
        decisions_path = tmp_path / "hale_decisions.md"
        rows = [_row(status="Closed")]
        result = writeback.process_once(rows, state_path=state_path,
                                        decisions_path=decisions_path,
                                        delete_fn=_fake_delete_ok)
        assert result["closed"] == []

    def test_closed_row_stays_in_state(self, tmp_path):
        # Unlike Delete, a Closed row's source record is kept — state still tracks it.
        state_path = tmp_path / "state.json"
        decisions_path = tmp_path / "hale_decisions.md"
        rows = [_row(id="task-1", status="Closed")]
        writeback.process_once(rows, state_path=state_path,
                               decisions_path=decisions_path,
                               delete_fn=_fake_delete_ok)
        saved = json.loads(state_path.read_text())
        assert "task-1" in saved
        assert saved["task-1"]["status"] == "Closed"


class TestStageMoveDetection:
    def test_manual_stage_move_logged(self, tmp_path):
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps({"task-1": {"status": "Open",
                                                       "stage": "D", "comments": ""}}))
        decisions_path = tmp_path / "hale_decisions.md"
        rows = [_row(stage="T")]  # Commander moved D -> T in AppSheet
        result = writeback.process_once(rows, state_path=state_path,
                                        decisions_path=decisions_path,
                                        delete_fn=_fake_delete_ok)
        assert len(result["staged"]) == 1
        assert result["staged"][0] == {"id": "task-1", "from": "D", "to": "T"}
        assert "D -> T" in decisions_path.read_text()

    def test_first_sync_no_stage_move_logged(self, tmp_path):
        # No prior state at all -> nothing to diff against, no false "move".
        state_path = tmp_path / "state.json"
        decisions_path = tmp_path / "hale_decisions.md"
        rows = [_row(stage="A")]
        result = writeback.process_once(rows, state_path=state_path,
                                        decisions_path=decisions_path,
                                        delete_fn=_fake_delete_ok)
        assert result["staged"] == []
        assert result["unchanged"] == 1

    def test_unchanged_stage_not_logged(self, tmp_path):
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps({"task-1": {"status": "Open",
                                                       "stage": "A", "comments": ""}}))
        decisions_path = tmp_path / "hale_decisions.md"
        rows = [_row(stage="A")]
        result = writeback.process_once(rows, state_path=state_path,
                                        decisions_path=decisions_path,
                                        delete_fn=_fake_delete_ok)
        assert result["staged"] == []


class TestCommentDetection:
    def test_new_comment_logged(self, tmp_path):
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps({"task-1": {"status": "Open", "stage": "A",
                                                       "comments": "Sterling: looking into it"}}))
        decisions_path = tmp_path / "hale_decisions.md"
        rows = [_row(comments="Sterling: looking into it\nDani: any update?")]
        result = writeback.process_once(rows, state_path=state_path,
                                        decisions_path=decisions_path,
                                        delete_fn=_fake_delete_ok)
        assert len(result["commented"]) == 1
        text = decisions_path.read_text()
        assert "TCD-COMMENT-task-1" in text
        assert "any update" in text

    def test_first_ever_comment_on_tracked_row_is_logged(self, tmp_path):
        # Row was already tracked (seen in a prior sync) with NO comment yet;
        # its first real comment (empty -> text) is a genuine event and must
        # be logged, not swallowed. This was a real bug caught by a live
        # round-trip test against the production Sheet before this fix.
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps({"task-1": {"status": "Open", "stage": "A",
                                                       "comments": ""}}))
        decisions_path = tmp_path / "hale_decisions.md"
        rows = [_row(comments="Sterling: first note")]
        result = writeback.process_once(rows, state_path=state_path,
                                        decisions_path=decisions_path,
                                        delete_fn=_fake_delete_ok)
        assert len(result["commented"]) == 1
        assert "first note" in decisions_path.read_text()

    def test_brand_new_row_with_content_not_flagged_as_comment_event(self, tmp_path):
        # A row never seen before (no cache entry at all, e.g. this sync's
        # first sight of it) has nothing to diff against — its existing
        # comments field (if collectors ever populate one) must NOT be
        # reported as a "new comment" on sync #1.
        state_path = tmp_path / "state.json"  # empty — row never tracked
        decisions_path = tmp_path / "hale_decisions.md"
        rows = [_row(id="task-brand-new", comments="pre-existing note")]
        result = writeback.process_once(rows, state_path=state_path,
                                        decisions_path=decisions_path,
                                        delete_fn=_fake_delete_ok)
        assert result["commented"] == []
        assert not decisions_path.exists()


class TestStatePersistence:
    def test_state_file_written(self, tmp_path):
        state_path = tmp_path / "state.json"
        decisions_path = tmp_path / "hale_decisions.md"
        rows = [_row(id="task-1"), _row(id="task-2", stage="D")]
        writeback.process_once(rows, state_path=state_path,
                               decisions_path=decisions_path,
                               delete_fn=_fake_delete_ok)
        saved = json.loads(state_path.read_text())
        assert set(saved.keys()) == {"task-1", "task-2"}
        assert saved["task-2"]["stage"] == "D"

    def test_disposed_row_removed_from_state(self, tmp_path):
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps({"task-1": {"status": "Open", "stage": "A",
                                                       "comments": ""}}))
        decisions_path = tmp_path / "hale_decisions.md"
        rows = [_row(status="Delete")]
        writeback.process_once(rows, state_path=state_path,
                               decisions_path=decisions_path,
                               delete_fn=_fake_delete_ok)
        saved = json.loads(state_path.read_text())
        assert "task-1" not in saved

    def test_rerun_is_idempotent_no_errors(self, tmp_path):
        state_path = tmp_path / "state.json"
        decisions_path = tmp_path / "hale_decisions.md"
        rows = [_row()]
        r1 = writeback.process_once(rows, state_path=state_path,
                                    decisions_path=decisions_path,
                                    delete_fn=_fake_delete_ok)
        r2 = writeback.process_once(rows, state_path=state_path,
                                    decisions_path=decisions_path,
                                    delete_fn=_fake_delete_ok)
        assert r1["errors"] == [] and r2["errors"] == []
        assert r2["unchanged"] == 1


class TestMixedBatch:
    def test_multiple_rows_independent_actions(self, tmp_path):
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps({
            "task-1": {"status": "Open", "stage": "D", "comments": ""},
            "task-2": {"status": "Open", "stage": "A", "comments": "note"},
            "task-3": {"status": "Open", "stage": "A", "comments": ""},
        }))
        decisions_path = tmp_path / "hale_decisions.md"
        rows = [
            _row(id="task-1", stage="T"),                       # stage move
            _row(id="task-2", comments="note\nmore"),            # comment
            _row(id="task-3", status="Delete"),                 # dispose
            _row(id="task-4"),                                   # brand new, untouched
        ]
        result = writeback.process_once(rows, state_path=state_path,
                                        decisions_path=decisions_path,
                                        delete_fn=_fake_delete_ok)
        assert len(result["staged"]) == 1
        assert len(result["commented"]) == 1
        assert len(result["disposed"]) == 1
        assert result["unchanged"] == 1  # task-4
        assert result["errors"] == []

    def test_row_missing_id_skipped(self, tmp_path):
        state_path = tmp_path / "state.json"
        decisions_path = tmp_path / "hale_decisions.md"
        rows = [{"id": "", "status": "Delete"}]
        result = writeback.process_once(rows, state_path=state_path,
                                        decisions_path=decisions_path,
                                        delete_fn=_fake_delete_ok)
        assert result["disposed"] == []
        assert result["errors"] == []
