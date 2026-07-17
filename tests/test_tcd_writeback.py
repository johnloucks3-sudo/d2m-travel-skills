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

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.silver import gate  # noqa: E402
from tcd import overrides as tcd_overrides  # noqa: E402
from tcd import writeback  # noqa: E402
from tcd.writeback import CREATE_TASK_MARKER  # noqa: E402


@pytest.fixture(autouse=True)
def _isolate_silver_gate(tmp_path, monkeypatch):
    """core/silver/gate.py hardcodes LEDGER/DECISIONS as module constants and
    pages the Commander (send_page) on a back-gate HOLD — none of which honor
    writeback's injected decisions_path. Redirect them to this test's tmp dir
    and neutralize the page so the suite never touches the real ledger/audit
    trail or fires a real P1 alert. Autouse: protects every test, including the
    pre-existing close tests that now route through run_gate."""
    monkeypatch.setattr(gate, "LEDGER", tmp_path / "silver_ledger.jsonl")
    monkeypatch.setattr(gate, "DECISIONS", tmp_path / "gate_decisions.md")
    monkeypatch.setattr(gate, "_page_hold", lambda v: None)


def _row(id="task-1", stage="A", status="Open", comments="", title="Test item"):
    return {"id": id, "inbox": "operational", "type": "brief", "priority": "p1",
            "stage": stage, "title": title, "from": "x", "date": "", "snippet": "",
            "body": "", "link": "https://x", "sourcePath": "hale_state.json:open_tasks",
            "comments": comments, "status": status}


def _fake_delete_ok(item_id):
    return {"ok": True, "source": f"hale_state.json:open_tasks:{item_id}"}


def _fake_delete_fail(item_id):
    return {"ok": False, "reason": "not found"}


def _fake_write_ok(item_id, updates):
    pass


class TestDisposeDetection:
    def test_new_dispose_triggers_delete(self, tmp_path):
        state_path = tmp_path / "state.json"
        decisions_path = tmp_path / "hale_decisions.md"
        overrides_path = tmp_path / "overrides.json"
        rows = [_row(status="Delete")]
        result = writeback.process_once(rows, state_path=state_path,
                                        decisions_path=decisions_path,
                                        overrides_path=overrides_path,
                                        delete_fn=_fake_delete_ok)
        assert len(result["disposed"]) == 1
        assert result["disposed"][0]["ok"] is True
        assert result["errors"] == []

    def test_dispose_logged_to_decisions(self, tmp_path):
        state_path = tmp_path / "state.json"
        decisions_path = tmp_path / "hale_decisions.md"
        overrides_path = tmp_path / "overrides.json"
        rows = [_row(id="task-99", status="Delete", title="Kill this")]
        writeback.process_once(rows, state_path=state_path,
                               decisions_path=decisions_path,
                                        overrides_path=overrides_path,
                               delete_fn=_fake_delete_ok)
        text = decisions_path.read_text()
        assert "PLAN:CLOSE" in text
        assert "TCD-DELETE-task-99" in text
        assert "verdict=PASS" in text
        assert "Kill this" in text

    def test_dispose_failure_logged_as_fail_verdict(self, tmp_path):
        state_path = tmp_path / "state.json"
        decisions_path = tmp_path / "hale_decisions.md"
        overrides_path = tmp_path / "overrides.json"
        rows = [_row(status="Delete")]
        result = writeback.process_once(rows, state_path=state_path,
                                        decisions_path=decisions_path,
                                        overrides_path=overrides_path,
                                        delete_fn=_fake_delete_fail)
        assert result["disposed"][0]["ok"] is False
        assert "verdict=FAIL" in decisions_path.read_text()

    def test_dispose_only_fires_once(self, tmp_path):
        # Row already Delete last run (in state) -> don't re-delete on rerun.
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps({"task-1": {"status": "Delete",
                                                       "stage": "A", "comments": ""}}))
        decisions_path = tmp_path / "hale_decisions.md"
        overrides_path = tmp_path / "overrides.json"
        rows = [_row(status="Delete")]
        calls = []
        def counting_delete(item_id):
            calls.append(item_id)
            return {"ok": True}
        result = writeback.process_once(rows, state_path=state_path,
                                        decisions_path=decisions_path,
                                        overrides_path=overrides_path,
                                        delete_fn=counting_delete)
        assert calls == []  # already processed, no re-delete
        assert result["disposed"] == []

    def test_open_status_never_disposes(self, tmp_path):
        state_path = tmp_path / "state.json"
        decisions_path = tmp_path / "hale_decisions.md"
        overrides_path = tmp_path / "overrides.json"
        rows = [_row(status="Open")]
        result = writeback.process_once(rows, state_path=state_path,
                                        decisions_path=decisions_path,
                                        overrides_path=overrides_path,
                                        delete_fn=_fake_delete_ok)
        assert result["disposed"] == []
        assert not decisions_path.exists()


class TestCloseDetection:
    def test_new_close_logged_source_untouched(self, tmp_path):
        state_path = tmp_path / "state.json"
        decisions_path = tmp_path / "hale_decisions.md"
        overrides_path = tmp_path / "overrides.json"
        # Comments carry a concrete verification reference so Silver's back-gate
        # PASSes — this test's intent is "source untouched + audit-logged", not
        # the verdict value (covered separately below).
        calls = []
        def counting_delete(item_id):
            calls.append(item_id)
            return {"ok": True}
        rows = [_row(id="task-77", status="Closed", title="Done with this",
                     comments="Verified and delivered; see /home/john/Thunderbird/hale_state.json")]
        result = writeback.process_once(rows, state_path=state_path,
                                        decisions_path=decisions_path,
                                        overrides_path=overrides_path,
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
        overrides_path = tmp_path / "overrides.json"
        rows = [_row(status="Closed")]
        result = writeback.process_once(rows, state_path=state_path,
                                        decisions_path=decisions_path,
                                        overrides_path=overrides_path,
                                        delete_fn=_fake_delete_ok)
        assert result["closed"] == []

    def test_closed_row_stays_in_state(self, tmp_path):
        # Unlike Delete, a Closed row's source record is kept — state still tracks it.
        state_path = tmp_path / "state.json"
        decisions_path = tmp_path / "hale_decisions.md"
        overrides_path = tmp_path / "overrides.json"
        rows = [_row(id="task-1", status="Closed")]
        writeback.process_once(rows, state_path=state_path,
                               decisions_path=decisions_path,
                                        overrides_path=overrides_path,
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
        overrides_path = tmp_path / "overrides.json"
        rows = [_row(stage="T")]  # Commander moved D -> T in AppSheet
        result = writeback.process_once(rows, state_path=state_path,
                                        decisions_path=decisions_path,
                                        overrides_path=overrides_path,
                                        delete_fn=_fake_delete_ok)
        assert len(result["staged"]) == 1
        assert result["staged"][0] == {"id": "task-1", "from": "D", "to": "T"}
        assert "D -> T" in decisions_path.read_text()

    def test_first_sync_no_stage_move_logged(self, tmp_path):
        # No prior state at all -> nothing to diff against, no false "move".
        state_path = tmp_path / "state.json"
        decisions_path = tmp_path / "hale_decisions.md"
        overrides_path = tmp_path / "overrides.json"
        rows = [_row(stage="A")]
        result = writeback.process_once(rows, state_path=state_path,
                                        decisions_path=decisions_path,
                                        overrides_path=overrides_path,
                                        delete_fn=_fake_delete_ok)
        assert result["staged"] == []
        assert result["unchanged"] == 1

    def test_unchanged_stage_not_logged(self, tmp_path):
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps({"task-1": {"status": "Open",
                                                       "stage": "A", "comments": ""}}))
        decisions_path = tmp_path / "hale_decisions.md"
        overrides_path = tmp_path / "overrides.json"
        rows = [_row(stage="A")]
        result = writeback.process_once(rows, state_path=state_path,
                                        decisions_path=decisions_path,
                                        overrides_path=overrides_path,
                                        delete_fn=_fake_delete_ok)
        assert result["staged"] == []


class TestCommentDetection:
    def test_new_comment_logged(self, tmp_path):
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps({"task-1": {"status": "Open", "stage": "A",
                                                       "comments": "Sterling: looking into it"}}))
        decisions_path = tmp_path / "hale_decisions.md"
        overrides_path = tmp_path / "overrides.json"
        rows = [_row(comments="Sterling: looking into it\nDani: any update?")]
        result = writeback.process_once(rows, state_path=state_path,
                                        decisions_path=decisions_path,
                                        overrides_path=overrides_path,
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
        overrides_path = tmp_path / "overrides.json"
        rows = [_row(comments="Sterling: first note")]
        result = writeback.process_once(rows, state_path=state_path,
                                        decisions_path=decisions_path,
                                        overrides_path=overrides_path,
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
        overrides_path = tmp_path / "overrides.json"
        rows = [_row(id="task-brand-new", comments="pre-existing note")]
        result = writeback.process_once(rows, state_path=state_path,
                                        decisions_path=decisions_path,
                                        overrides_path=overrides_path,
                                        delete_fn=_fake_delete_ok)
        assert result["commented"] == []
        assert not decisions_path.exists()


class TestCreateTaskDetection:
    def _fake_create_task(self, calls):
        def fn(row):
            calls.append(row["id"])
            return "MISSION-999"
        return fn

    def test_marker_in_new_comment_files_a_task(self, tmp_path):
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps({"task-1": {"status": "Open", "stage": "P",
                                                       "comments": ""}}))
        decisions_path = tmp_path / "hale_decisions.md"
        overrides_path = tmp_path / "overrides.json"
        calls = []
        rows = [_row(stage="P", comments="Commander: [CREATE_TASK_REQUESTED]")]
        result = writeback.process_once(rows, state_path=state_path,
                                        decisions_path=decisions_path,
                                        overrides_path=overrides_path,
                                        delete_fn=_fake_delete_ok,
                                        create_task_fn=self._fake_create_task(calls))
        assert calls == ["task-1"]
        assert result["created_tasks"] == [{"id": "task-1", "mission_id": "MISSION-999"}]
        text = decisions_path.read_text()
        assert "TCD-CREATETASK-task-1" in text
        assert "MISSION-999" in text

    def test_comment_without_marker_does_not_file_a_task(self, tmp_path):
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps({"task-1": {"status": "Open", "stage": "P",
                                                       "comments": ""}}))
        decisions_path = tmp_path / "hale_decisions.md"
        overrides_path = tmp_path / "overrides.json"
        calls = []
        rows = [_row(stage="P", comments="Commander: just a note")]
        result = writeback.process_once(rows, state_path=state_path,
                                        decisions_path=decisions_path,
                                        overrides_path=overrides_path,
                                        delete_fn=_fake_delete_ok,
                                        create_task_fn=self._fake_create_task(calls))
        assert calls == []
        assert result["created_tasks"] == []

    def test_marker_already_present_in_prior_comments_not_refiled(self, tmp_path):
        # The marker text itself sat in the PRIOR comments (already handled
        # on an earlier pass) -- only NEWLY-ADDED text containing the marker
        # should trigger filing, not any row whose comments happen to contain it.
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps({"task-1": {"status": "Open", "stage": "P",
                                                       "comments": "[CREATE_TASK_REQUESTED]"}}))
        decisions_path = tmp_path / "hale_decisions.md"
        overrides_path = tmp_path / "overrides.json"
        calls = []
        rows = [_row(stage="P", comments="[CREATE_TASK_REQUESTED]\nDani: on it")]
        result = writeback.process_once(rows, state_path=state_path,
                                        decisions_path=decisions_path,
                                        overrides_path=overrides_path,
                                        delete_fn=_fake_delete_ok,
                                        create_task_fn=self._fake_create_task(calls))
        assert calls == []
        assert result["created_tasks"] == []

    def test_second_click_appends_second_marker_files_second_task(self, tmp_path):
        # Each distinct new marker append is a genuine new Commander request.
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps({"task-1": {"status": "Open", "stage": "P",
                                                       "comments": "[CREATE_TASK_REQUESTED]"}}))
        decisions_path = tmp_path / "hale_decisions.md"
        overrides_path = tmp_path / "overrides.json"
        calls = []
        rows = [_row(stage="P", comments="[CREATE_TASK_REQUESTED]\n[CREATE_TASK_REQUESTED]")]
        result = writeback.process_once(rows, state_path=state_path,
                                        decisions_path=decisions_path,
                                        overrides_path=overrides_path,
                                        delete_fn=_fake_delete_ok,
                                        create_task_fn=self._fake_create_task(calls))
        assert calls == ["task-1"]
        assert len(result["created_tasks"]) == 1

    def test_default_create_task_fn_files_real_mission(self, tmp_path, monkeypatch):
        # Exercises the real (non-injected) path against a temp mission board.
        board_path = tmp_path / "mission_board.json"
        board_path.write_text(json.dumps({"missions": [{"id": "MISSION-001"}],
                                          "last_updated": ""}))
        lock_path = tmp_path / "mission_board.lock"
        from OpsCenter import mission_board_sync as mbs
        monkeypatch.setattr(mbs, "BOARD_PATH", board_path)
        monkeypatch.setattr(mbs, "LOCK_PATH", lock_path)
        row = _row(id="alert-1", title="Follow up on vendor issue", comments="")
        row["priority"] = "p1"
        mission_id = writeback._default_create_task_fn(row)
        assert mission_id == "MISSION-002"
        board = json.loads(board_path.read_text())
        filed = [m for m in board["missions"] if m["id"] == "MISSION-002"][0]
        assert filed["title"] == "Follow up on vendor issue"
        assert filed["status"] == "pending_review"
        assert filed["source"] == "tcd_create_task_action"
        assert filed["priority"] == "P1"

    def test_commander_free_text_in_comments_lands_in_description(self, tmp_path, monkeypatch):
        # The bug: a Commander note typed into the comments box before/after
        # clicking Create Task was silently dropped -- only the email's own
        # body/snippet made it into the filed mission. Ground-truth incident:
        # MISSION-023 (2026-07-14) filed with "Search for larger vehicles and
        # send me estimates" typed in comments, but the mission description
        # was just the raw email quote -- his instruction never landed.
        board_path = tmp_path / "mission_board.json"
        board_path.write_text(json.dumps({"missions": [], "last_updated": ""}))
        lock_path = tmp_path / "mission_board.lock"
        from OpsCenter import mission_board_sync as mbs
        monkeypatch.setattr(mbs, "BOARD_PATH", board_path)
        monkeypatch.setattr(mbs, "LOCK_PATH", lock_path)
        row = _row(id="gmail-1", title="Re: Booking Confirmation",
                   comments="[CREATE_TASK_REQUESTED] [CREATE_TASK_REQUESTED] "
                            "Search for larger vehicles and send me estimates")
        row["body"] = "Original email text."
        mission_id = writeback._default_create_task_fn(row)
        board = json.loads(board_path.read_text())
        filed = [m for m in board["missions"] if m["id"] == mission_id][0]
        assert "Search for larger vehicles and send me estimates" in filed["description"]
        assert "Original email text." in filed["description"]
        assert CREATE_TASK_MARKER not in filed["description"]

    def test_marker_only_comments_no_spurious_commander_note(self, tmp_path, monkeypatch):
        board_path = tmp_path / "mission_board.json"
        board_path.write_text(json.dumps({"missions": [], "last_updated": ""}))
        lock_path = tmp_path / "mission_board.lock"
        from OpsCenter import mission_board_sync as mbs
        monkeypatch.setattr(mbs, "BOARD_PATH", board_path)
        monkeypatch.setattr(mbs, "LOCK_PATH", lock_path)
        row = _row(id="gmail-2", title="No note", comments="[CREATE_TASK_REQUESTED]")
        row["body"] = "Original body."
        mission_id = writeback._default_create_task_fn(row)
        board = json.loads(board_path.read_text())
        filed = [m for m in board["missions"] if m["id"] == mission_id][0]
        assert filed["description"] == "Original body."

    def test_duplicate_create_task_blocked_not_filed_twice(self, tmp_path, monkeypatch):
        # REGRESSION (2026-07-16): _default_create_task_fn hand-rolled the
        # mission dict and appended directly to the board, never calling
        # mission_board_sync._find_open_duplicate() (Silver/Sterling's
        # 2026-07-04 one-and-done fix). Since TCD became the only C2 channel
        # (2026-07-11), every recurring Commander decision routed through
        # here flooded the board with duplicates: Regent pricing refresh x4
        # (MISSION-005/017/034/042), TESS restore x3+, WF-17 drafts x4 with
        # CONFLICTING deadlines on the duplicate tickets. Ground truth: the
        # dedup filter also didn't recognize status="pending_review" (what
        # this function files under) as "open" -- fixed alongside this.
        board_path = tmp_path / "mission_board.json"
        board_path.write_text(json.dumps({"missions": [], "last_updated": ""}))
        lock_path = tmp_path / "mission_board.lock"
        from OpsCenter import mission_board_sync as mbs
        monkeypatch.setattr(mbs, "BOARD_PATH", board_path)
        monkeypatch.setattr(mbs, "LOCK_PATH", lock_path)

        row1 = _row(id="alert-1", title="Produce Regent pricing refresh for Lyons renewal window")
        first_id = writeback._default_create_task_fn(row1)

        row2 = _row(id="alert-2", title="Produce Regent pricing refresh for Lyons renewal window")
        second_id = writeback._default_create_task_fn(row2)

        assert second_id == first_id, "duplicate Create Task action must resolve to the existing mission, not file a new one"
        board = json.loads(board_path.read_text())
        assert len(board["missions"]) == 1, "exactly one mission must exist for this title, not two"
        filed = board["missions"][0]
        assert filed["status"] == "pending_review"
        assert any("duplicate TCD Create Task blocked" in log for log in filed["logs"])


class TestStatePersistence:
    def test_state_file_written(self, tmp_path):
        state_path = tmp_path / "state.json"
        decisions_path = tmp_path / "hale_decisions.md"
        overrides_path = tmp_path / "overrides.json"
        rows = [_row(id="task-1"), _row(id="task-2", stage="D")]
        writeback.process_once(rows, state_path=state_path,
                               decisions_path=decisions_path,
                                        overrides_path=overrides_path,
                               delete_fn=_fake_delete_ok)
        saved = json.loads(state_path.read_text())
        assert set(saved.keys()) == {"task-1", "task-2"}
        assert saved["task-2"]["stage"] == "D"

    def test_disposed_row_removed_from_state(self, tmp_path):
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps({"task-1": {"status": "Open", "stage": "A",
                                                       "comments": ""}}))
        decisions_path = tmp_path / "hale_decisions.md"
        overrides_path = tmp_path / "overrides.json"
        rows = [_row(status="Delete")]
        writeback.process_once(rows, state_path=state_path,
                               decisions_path=decisions_path,
                                        overrides_path=overrides_path,
                               delete_fn=_fake_delete_ok)
        saved = json.loads(state_path.read_text())
        assert "task-1" not in saved

    def test_rerun_is_idempotent_no_errors(self, tmp_path):
        state_path = tmp_path / "state.json"
        decisions_path = tmp_path / "hale_decisions.md"
        overrides_path = tmp_path / "overrides.json"
        rows = [_row()]
        r1 = writeback.process_once(rows, state_path=state_path,
                                    decisions_path=decisions_path,
                                        overrides_path=overrides_path,
                                    delete_fn=_fake_delete_ok)
        r2 = writeback.process_once(rows, state_path=state_path,
                                    decisions_path=decisions_path,
                                        overrides_path=overrides_path,
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
        overrides_path = tmp_path / "overrides.json"
        rows = [
            _row(id="task-1", stage="T"),                       # stage move
            _row(id="task-2", comments="note\nmore"),            # comment
            _row(id="task-3", status="Delete"),                 # dispose
            _row(id="task-4"),                                   # brand new, untouched
        ]
        result = writeback.process_once(rows, state_path=state_path,
                                        decisions_path=decisions_path,
                                        overrides_path=overrides_path,
                                        delete_fn=_fake_delete_ok)
        assert len(result["staged"]) == 1
        assert len(result["commented"]) == 1
        assert len(result["disposed"]) == 1
        assert result["unchanged"] == 1  # task-4
        assert result["errors"] == []

    def test_row_missing_id_skipped(self, tmp_path):
        state_path = tmp_path / "state.json"
        decisions_path = tmp_path / "hale_decisions.md"
        overrides_path = tmp_path / "overrides.json"
        rows = [{"id": "", "status": "Delete"}]
        result = writeback.process_once(rows, state_path=state_path,
                                        decisions_path=decisions_path,
                                        overrides_path=overrides_path,
                                        delete_fn=_fake_delete_ok)
        assert result["disposed"] == []
        assert result["errors"] == []


class TestAutoTaskDT:
    def test_approve_p_to_d_auto_advances_to_t(self, tmp_path):
        # Commander clicks Approve in AppSheet -> row.stage becomes "D".
        # Hale should immediately task it further to "T" and assign an owner.
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps({"task-1": {"status": "Open",
                                                       "stage": "P", "comments": ""}}))
        decisions_path = tmp_path / "hale_decisions.md"
        overrides_path = tmp_path / "overrides.json"
        rows = [_row(stage="D", title="Client booking follow-up")]
        result = writeback.process_once(rows, state_path=state_path,
                                        decisions_path=decisions_path,
                                        overrides_path=overrides_path,
                                        delete_fn=_fake_delete_ok, write_fn=_fake_write_ok)
        assert result["staged"] == [{"id": "task-1", "from": "P", "to": "D"}]
        assert len(result["tasked"]) == 1
        assert result["tasked"][0]["id"] == "task-1"
        assert result["tasked"][0]["owner"]

    def test_both_pd_and_dt_logged_to_decisions(self, tmp_path):
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps({"task-1": {"status": "Open",
                                                       "stage": "P", "comments": ""}}))
        decisions_path = tmp_path / "hale_decisions.md"
        overrides_path = tmp_path / "overrides.json"
        rows = [_row(stage="D")]
        writeback.process_once(rows, state_path=state_path,
                               decisions_path=decisions_path,
                               overrides_path=overrides_path,
                               delete_fn=_fake_delete_ok, write_fn=_fake_write_ok)
        text = decisions_path.read_text()
        assert "P -> D" in text
        assert "D -> T" in text
        assert "TCD-TASK-task-1" in text

    def test_final_materialized_stage_is_t_not_d(self, tmp_path):
        # The saved state (what the next diff compares against) must show
        # "T" — otherwise the next sync logs a second, unattributed D->T move.
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps({"task-1": {"status": "Open",
                                                       "stage": "P", "comments": ""}}))
        decisions_path = tmp_path / "hale_decisions.md"
        overrides_path = tmp_path / "overrides.json"
        rows = [_row(stage="D")]
        writeback.process_once(rows, state_path=state_path,
                               decisions_path=decisions_path,
                               overrides_path=overrides_path,
                               delete_fn=_fake_delete_ok, write_fn=_fake_write_ok)
        saved = json.loads(state_path.read_text())
        assert saved["task-1"]["stage"] == "T"

    def test_owner_persisted_to_overrides(self, tmp_path):
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps({"task-1": {"status": "Open",
                                                       "stage": "P", "comments": ""}}))
        decisions_path = tmp_path / "hale_decisions.md"
        overrides_path = tmp_path / "overrides.json"
        rows = [_row(stage="D", title="CI regression on deploy watchdog")]
        writeback.process_once(rows, state_path=state_path,
                               decisions_path=decisions_path,
                               overrides_path=overrides_path,
                               delete_fn=_fake_delete_ok, write_fn=_fake_write_ok)
        ov = tcd_overrides.load_overrides(overrides_path)
        assert ov["task-1"]["stage"] == "T"
        assert ov["task-1"]["owner"] == "Sterling"

    def test_rerun_does_not_double_task(self, tmp_path):
        # Second pass sees stage already "T" in state (from the T materialize
        # above) -> must not re-fire the auto-task branch.
        state_path = tmp_path / "state.json"
        decisions_path = tmp_path / "hale_decisions.md"
        overrides_path = tmp_path / "overrides.json"
        state_path.write_text(json.dumps({"task-1": {"status": "Open",
                                                       "stage": "P", "comments": ""}}))
        rows = [_row(stage="D")]
        writeback.process_once(rows, state_path=state_path,
                               decisions_path=decisions_path,
                               overrides_path=overrides_path,
                               delete_fn=_fake_delete_ok, write_fn=_fake_write_ok)
        result2 = writeback.process_once([_row(stage="T")], state_path=state_path,
                                         decisions_path=decisions_path,
                                         overrides_path=overrides_path,
                                         delete_fn=_fake_delete_ok, write_fn=_fake_write_ok)
        assert result2["tasked"] == []
        assert result2["staged"] == []
        assert result2["unchanged"] == 1

    def test_direct_p_to_t_skip_does_not_auto_task(self, tmp_path):
        # Auto-task only fires for the specific P->D approve transition, not
        # any other move that happens to land on D or pass through it.
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps({"task-1": {"status": "Open",
                                                       "stage": "T", "comments": ""}}))
        decisions_path = tmp_path / "hale_decisions.md"
        overrides_path = tmp_path / "overrides.json"
        rows = [_row(stage="A")]  # Hale manually advances T -> A
        result = writeback.process_once(rows, state_path=state_path,
                                        decisions_path=decisions_path,
                                        overrides_path=overrides_path,
                                        delete_fn=_fake_delete_ok, write_fn=_fake_write_ok)
        assert result["tasked"] == []
        assert result["staged"] == [{"id": "task-1", "from": "T", "to": "A"}]


class TestOverridePersistence:
    def test_generic_stage_move_persists_override(self, tmp_path):
        # This is the core fix: a manual stage move must survive being
        # re-derived from source on the next sync, not just get audit-logged.
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps({"task-1": {"status": "Open",
                                                       "stage": "T", "comments": ""}}))
        decisions_path = tmp_path / "hale_decisions.md"
        overrides_path = tmp_path / "overrides.json"
        rows = [_row(stage="A")]
        writeback.process_once(rows, state_path=state_path,
                               decisions_path=decisions_path,
                               overrides_path=overrides_path,
                               delete_fn=_fake_delete_ok)
        ov = tcd_overrides.load_overrides(overrides_path)
        assert ov["task-1"]["stage"] == "A"

    def test_dispose_clears_override(self, tmp_path):
        state_path = tmp_path / "state.json"
        decisions_path = tmp_path / "hale_decisions.md"
        overrides_path = tmp_path / "overrides.json"
        tcd_overrides.set_override("task-1", stage="T", owner="Dani", path=overrides_path)
        rows = [_row(status="Delete")]
        writeback.process_once(rows, state_path=state_path,
                               decisions_path=decisions_path,
                               overrides_path=overrides_path,
                               delete_fn=_fake_delete_ok)
        assert tcd_overrides.load_overrides(overrides_path) == {}


class TestAutoTaskWritesSheetCell:
    def test_write_fn_called_with_t_and_owner(self, tmp_path):
        # This is the fix for a real live-verified bug: the auto-tasked "T"
        # must reach the actual Sheet cell immediately, not just local state
        # -- otherwise a standalone tcd_process_writeback call (a real,
        # separate MCP entry point) leaves the Sheet showing stale "D", and
        # the next full sheet_sync misreads that as a fresh regression.
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps({"task-1": {"status": "Open",
                                                       "stage": "P", "comments": ""}}))
        decisions_path = tmp_path / "hale_decisions.md"
        overrides_path = tmp_path / "overrides.json"
        calls = []
        def recording_write(item_id, updates):
            calls.append((item_id, updates))
        rows = [_row(stage="D", title="CI regression on deploy watchdog")]
        writeback.process_once(rows, state_path=state_path,
                               decisions_path=decisions_path,
                               overrides_path=overrides_path,
                               delete_fn=_fake_delete_ok,
                               write_fn=recording_write)
        assert calls == [("task-1", {"stage": "T", "owner": "Sterling"})]

    def test_write_fn_not_called_for_non_auto_task_moves(self, tmp_path):
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps({"task-1": {"status": "Open",
                                                       "stage": "T", "comments": ""}}))
        decisions_path = tmp_path / "hale_decisions.md"
        overrides_path = tmp_path / "overrides.json"
        calls = []
        def recording_write(item_id, updates):
            calls.append((item_id, updates))
        rows = [_row(stage="A")]
        writeback.process_once(rows, state_path=state_path,
                               decisions_path=decisions_path,
                               overrides_path=overrides_path,
                               delete_fn=_fake_delete_ok,
                               write_fn=recording_write)
        assert calls == []

    def test_write_fn_failure_recorded_as_error_not_raised(self, tmp_path):
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps({"task-1": {"status": "Open",
                                                       "stage": "P", "comments": ""}}))
        decisions_path = tmp_path / "hale_decisions.md"
        overrides_path = tmp_path / "overrides.json"
        def failing_write(item_id, updates):
            raise RuntimeError("sheets api down")
        rows = [_row(stage="D")]
        result = writeback.process_once(rows, state_path=state_path,
                                        decisions_path=decisions_path,
                                        overrides_path=overrides_path,
                                        delete_fn=_fake_delete_ok,
                                        write_fn=failing_write)
        assert any(e["action"] == "write_sheet" for e in result["errors"])
        # The tasking itself still happened (owner assigned, override set)
        # even though the live cell write failed -- self-heals on next sync.
        assert len(result["tasked"]) == 1


class TestSilverGateFrontFrame:
    """MISSION-658: D->T auto-task is Silver-front-framed for delegated-work
    rows (mission-/watch-). No criteria -> visible HOLD, not a silent task."""

    def test_delegated_row_no_criteria_holds_visibly(self, tmp_path):
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps({"mission-x": {"status": "Open",
                                                         "stage": "P", "comments": ""}}))
        decisions_path = tmp_path / "hale_decisions.md"
        overrides_path = tmp_path / "overrides.json"
        rows = [_row(id="mission-x", stage="D", title="Do the thing", comments="")]
        result = writeback.process_once(rows, state_path=state_path,
                                        decisions_path=decisions_path,
                                        overrides_path=overrides_path,
                                        delete_fn=_fake_delete_ok, write_fn=_fake_write_ok)
        # Held, not tasked.
        assert result["held"] == [{"id": "mission-x"}]
        assert result["tasked"] == []
        # HOLD is visible in the audit trail...
        text = decisions_path.read_text()
        assert "TCD-TASK-mission-x" in text
        assert "verdict=HOLD" in text
        # ...in the Silver ledger (real front-frame entry)...
        ledger = (tmp_path / "silver_ledger.jsonl").read_text()
        assert '"stage": "front"' in ledger
        assert '"verdict": "HOLD"' in ledger
        # ...and NOT advanced to T: no owner, no override. Leaving no override
        # means the next full sheet_sync surfaces the row back at P (its
        # needs-a-decision resting state), so once criteria are added a
        # re-approve re-frames cleanly — the row is never pinned dead at D.
        ov = tcd_overrides.load_overrides(overrides_path)
        assert "mission-x" not in ov

    def test_hold_note_surfaced_to_sheet_not_double_logged_as_comment(self, tmp_path):
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps({"mission-x": {"status": "Open",
                                                         "stage": "P", "comments": ""}}))
        decisions_path = tmp_path / "hale_decisions.md"
        overrides_path = tmp_path / "overrides.json"
        calls = []
        def recording_write(item_id, updates):
            calls.append((item_id, updates))
        rows = [_row(id="mission-x", stage="D", comments="")]
        result = writeback.process_once(rows, state_path=state_path,
                                        decisions_path=decisions_path,
                                        overrides_path=overrides_path,
                                        delete_fn=_fake_delete_ok, write_fn=recording_write)
        # The HOLD reason is pushed to the Sheet's comments so AppSheet shows it.
        assert len(calls) == 1
        item_id, updates = calls[0]
        assert item_id == "mission-x"
        assert updates["stage"] == "D"
        assert "[SILVER HOLD" in updates["comments"]
        # But it must NOT re-log as a Commander comment event this same pass.
        assert result["commented"] == []

    def test_delegated_row_valid_criteria_still_auto_tasks(self, tmp_path):
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps({"mission-y": {"status": "Open",
                                                         "stage": "P", "comments": ""}}))
        decisions_path = tmp_path / "hale_decisions.md"
        overrides_path = tmp_path / "overrides.json"
        rows = [_row(id="mission-y", stage="D", title="CI regression on deploy watchdog",
                     comments="Deliver 3 fixed timers, verified via systemctl")]
        result = writeback.process_once(rows, state_path=state_path,
                                        decisions_path=decisions_path,
                                        overrides_path=overrides_path,
                                        delete_fn=_fake_delete_ok, write_fn=_fake_write_ok)
        assert result["held"] == []
        assert len(result["tasked"]) == 1
        assert result["tasked"][0]["id"] == "mission-y"
        assert result["tasked"][0]["owner"] == "Sterling"
        ov = tcd_overrides.load_overrides(overrides_path)
        assert ov["mission-y"]["stage"] == "T"

    def test_non_delegated_row_auto_tasks_ungated(self, tmp_path):
        # A task-/gmail-/alert- row with no criteria still auto-tasks as before
        # (routing, not a work-product commitment) — the scoping decision.
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps({"task-1": {"status": "Open",
                                                      "stage": "P", "comments": ""}}))
        decisions_path = tmp_path / "hale_decisions.md"
        overrides_path = tmp_path / "overrides.json"
        rows = [_row(id="task-1", stage="D", comments="")]
        result = writeback.process_once(rows, state_path=state_path,
                                        decisions_path=decisions_path,
                                        overrides_path=overrides_path,
                                        delete_fn=_fake_delete_ok, write_fn=_fake_write_ok)
        assert result["held"] == []
        assert len(result["tasked"]) == 1
        # No front-frame ledger entry for an ungated row.
        assert not (tmp_path / "silver_ledger.jsonl").exists()

    def test_empty_comments_checkable_description_auto_tasks(self, tmp_path):
        # Mission-board rows carry comments=[] but a real description on `body`.
        # A checkable description satisfies the front frame — no false HOLD.
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps({"mission-d": {"status": "Open",
                                                        "stage": "P", "comments": ""}}))
        decisions_path = tmp_path / "hale_decisions.md"
        overrides_path = tmp_path / "overrides.json"
        row = _row(id="mission-d", stage="D", title="Wire deploy watchdog", comments="")
        row["body"] = "Fix intel/daily_search/foo.py — add 3 checks, verified via systemctl."
        result = writeback.process_once([row], state_path=state_path,
                                        decisions_path=decisions_path,
                                        overrides_path=overrides_path,
                                        delete_fn=_fake_delete_ok, write_fn=_fake_write_ok)
        assert result["held"] == []
        assert len(result["tasked"]) == 1

    def test_empty_comments_vague_description_still_holds(self, tmp_path):
        # No checkable criteria in comments OR description -> correctly HOLDs.
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps({"mission-v": {"status": "Open",
                                                        "stage": "P", "comments": ""}}))
        decisions_path = tmp_path / "hale_decisions.md"
        overrides_path = tmp_path / "overrides.json"
        row = _row(id="mission-v", stage="D", title="Follow up", comments="")
        row["body"] = "Follow up on the thing"
        result = writeback.process_once([row], state_path=state_path,
                                        decisions_path=decisions_path,
                                        overrides_path=overrides_path,
                                        delete_fn=_fake_delete_ok, write_fn=_fake_write_ok)
        assert result["held"] == [{"id": "mission-v"}]
        assert result["tasked"] == []


class TestSilverGateBackGate:
    """MISSION-658: Close and stage->C write the REAL Silver verdict, not the
    old hardcoded PASS — to both hale_decisions.md and the Silver ledger."""

    def test_close_empty_comments_writes_real_hold(self, tmp_path):
        state_path = tmp_path / "state.json"
        decisions_path = tmp_path / "hale_decisions.md"
        overrides_path = tmp_path / "overrides.json"
        rows = [_row(id="task-9", status="Closed", title="Close me", comments="")]
        result = writeback.process_once(rows, state_path=state_path,
                                        decisions_path=decisions_path,
                                        overrides_path=overrides_path,
                                        delete_fn=_fake_delete_ok)
        assert len(result["closed"]) == 1  # transition still recorded
        text = decisions_path.read_text()
        assert "TCD-CLOSE-task-9" in text
        assert "verdict=HOLD" in text
        assert "Silver back-gate HOLD" in text
        ledger = (tmp_path / "silver_ledger.jsonl").read_text()
        assert '"stage": "back"' in ledger
        assert '"verdict": "HOLD"' in ledger

    def test_close_with_valid_artifact_writes_real_pass(self, tmp_path):
        state_path = tmp_path / "state.json"
        decisions_path = tmp_path / "hale_decisions.md"
        overrides_path = tmp_path / "overrides.json"
        rows = [_row(id="task-10", status="Closed",
                     comments="Delivered — proof at OpsCenter/silver_ledger.jsonl")]
        result = writeback.process_once(rows, state_path=state_path,
                                        decisions_path=decisions_path,
                                        overrides_path=overrides_path,
                                        delete_fn=_fake_delete_ok)
        assert len(result["closed"]) == 1
        text = decisions_path.read_text()
        assert "TCD-CLOSE-task-10" in text
        assert "verdict=PASS" in text
        ledger = (tmp_path / "silver_ledger.jsonl").read_text()
        assert '"stage": "back"' in ledger
        assert '"verdict": "PASS"' in ledger

    def test_stage_move_into_c_writes_real_verdict(self, tmp_path):
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps({"mission-z": {"status": "Open",
                                                        "stage": "A", "comments": ""}}))
        decisions_path = tmp_path / "hale_decisions.md"
        overrides_path = tmp_path / "overrides.json"
        rows = [_row(id="mission-z", stage="C", comments="")]  # A -> C, no proof
        result = writeback.process_once(rows, state_path=state_path,
                                        decisions_path=decisions_path,
                                        overrides_path=overrides_path,
                                        delete_fn=_fake_delete_ok)
        assert len(result["staged"]) == 1
        text = decisions_path.read_text()
        assert "TCD-STAGE-mission-z" in text
        assert "verdict=HOLD" in text
        assert "A -> C" in text
        ledger = (tmp_path / "silver_ledger.jsonl").read_text()
        assert '"stage": "back"' in ledger

    def test_non_c_stage_move_stays_pass_ungated(self, tmp_path):
        # A move that isn't into Certify is a bare audit record — no gate.
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps({"task-1": {"status": "Open",
                                                      "stage": "T", "comments": ""}}))
        decisions_path = tmp_path / "hale_decisions.md"
        overrides_path = tmp_path / "overrides.json"
        rows = [_row(id="task-1", stage="A", comments="")]  # T -> A
        result = writeback.process_once(rows, state_path=state_path,
                                        decisions_path=decisions_path,
                                        overrides_path=overrides_path,
                                        delete_fn=_fake_delete_ok)
        assert len(result["staged"]) == 1
        assert "verdict=PASS" in decisions_path.read_text()
        assert not (tmp_path / "silver_ledger.jsonl").exists()
