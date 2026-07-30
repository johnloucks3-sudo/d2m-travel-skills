"""
tests/test_tcd_slack_parity.py — TCD->Slack migration, task 22: handler parity +
no-silent-truncation tests.

Locks down three contracts the Slack migration (core/comms/tcd_actions.py, not yet
built) must preserve exactly, because Slack's "Close"/"Approve"/"Comment" buttons will
call the same underlying functions AppSheet's write-back polling calls today:

  1. CLOSURE PERMANENCE (core/comms/commander_queue.py) — a Commander close is an
     append-only ledger fact. is_closed()/closed_ids() see it immediately, and
     re-closing the same item is idempotent: the ledger gains a second line (it is
     append-only by design) but the DERIVED closed set still counts the item once.
  2. HANDLER SHAPE (tcd/writeback.py) — each write-back handler (_handle_close,
     _handle_dispose, _handle_stage_move, _handle_comment, _handle_create_task),
     called directly with a synthetic row, appends a decision block that carries
     the row id and the action verb (CLOSE/DELETE/STAGE/COMMENT/CREATETASK) — the
     exact shape a Slack action handler needs to render a confirmation back to the
     Commander.
  3. SILVER BACK GATE (core/silver/gate.py) — a close whose reason is prose with no
     concrete reference (no path, no mission/row id, no thread/url) is HELD, never
     silently passed — tested against the real gate in core/silver/gate.py, not a
     reimplementation of its rule.

CRITICAL — ISOLATION: on 2026-07-29 a regression test ran against live data and
permanently closed a real production mission (MISSION-COMMANDER-196-CALL). Every path
touched here is tmp_path-scoped:
  - core/comms/commander_queue.py computes its path constants ONCE at import time
    (from the COMMANDER_QUEUE_DATA_ROOT env var), so setting that env var after
    import is a no-op — the constants are monkeypatched directly instead.
  - core/silver/gate.py hardcodes LEDGER/DECISIONS as module constants (not
    parameters) and pages the Commander on a back-gate HOLD; both are neutralized
    for every test in this file via an autouse fixture, regardless of which
    writeback handler ends up calling run_gate()/human_override().
No test in this file may write to the real hale_decisions.md, OpsCenter/mission_
board.json, OpsCenter/silver_ledger.jsonl, or OpsCenter/state/commander_closures.jsonl.

Run: python3 -m pytest tests/test_tcd_slack_parity.py -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.comms import commander_queue  # noqa: E402
from core.silver import gate  # noqa: E402
from tcd import writeback  # noqa: E402
from tcd.item_model import SHEET_COLUMNS  # noqa: E402


# ─────────────────────────────────────────────────────────────────────────────
# Isolation fixtures — no test in this file may touch real repo state.
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _isolate_silver_gate(tmp_path, monkeypatch):
    """Redirect Silver's ledger + audit trail to tmp, and neutralize the real P1
    page on a back-gate HOLD. Autouse: protects every test in this file, including
    ones that only indirectly trigger run_gate()/human_override() via a handler."""
    monkeypatch.setattr(gate, "LEDGER", tmp_path / "silver_ledger.jsonl")
    monkeypatch.setattr(gate, "DECISIONS", tmp_path / "gate_decisions.md")
    monkeypatch.setattr(gate, "_page_hold", lambda v: None)


@pytest.fixture
def isolated_queue(tmp_path, monkeypatch):
    """Redirect every commander_queue.py path constant to tmp_path. These are
    module-level constants computed once at import time — patching the env var
    after import would do nothing, so the constants themselves are patched."""
    monkeypatch.setattr(commander_queue, "CLOSURES_PATH", tmp_path / "commander_closures.jsonl")
    monkeypatch.setattr(commander_queue, "QUEUE_PATH", tmp_path / "commander_queue.json")
    monkeypatch.setattr(commander_queue, "BOARD_PATH", tmp_path / "mission_board.json")
    monkeypatch.setattr(commander_queue, "STATE_PATH", tmp_path / "hale_state.json")
    return commander_queue


def _row(**overrides) -> dict:
    """A synthetic Items-tab row, SHEET_COLUMNS-complete (mirrors item_model.Item)."""
    row = {col: "" for col in SHEET_COLUMNS}
    row.update({
        "id": "row-1", "inbox": "operational", "type": "task", "priority": "p2",
        "stage": "D", "title": "Synthetic test row", "from": "test-harness",
        "date": "2026-07-29", "status": "Open",
    })
    row.update(overrides)
    return row


# ─────────────────────────────────────────────────────────────────────────────
# 1. CLOSURE PERMANENCE — core/comms/commander_queue.py
# ─────────────────────────────────────────────────────────────────────────────

class TestClosurePermanence:
    def test_close_is_reported_by_is_closed(self, isolated_queue):
        isolated_queue.close("ITEM-1", by="Commander", reason="handled")
        assert isolated_queue.is_closed("ITEM-1") is True

    def test_close_appears_in_closed_ids(self, isolated_queue):
        isolated_queue.close("ITEM-2", by="Commander", reason="handled")
        assert "ITEM-2" in isolated_queue.closed_ids()

    def test_unclosed_item_is_not_closed(self, isolated_queue):
        isolated_queue.close("ITEM-OTHER", by="Commander")
        assert isolated_queue.is_closed("ITEM-NEVER-CLOSED") is False
        assert "ITEM-NEVER-CLOSED" not in isolated_queue.closed_ids()

    def test_second_close_is_idempotent_not_a_duplicate(self, isolated_queue):
        # close() is documented as "idempotent; re-closing is a no-op that still
        # records" -- the append-only ledger gains a second line, but the DERIVED
        # closed set must still count the item exactly once, not "twice closed".
        isolated_queue.close("ITEM-3", by="Commander", reason="first close")
        isolated_queue.close("ITEM-3", by="Commander", reason="second close, same item")
        assert isolated_queue.is_closed("ITEM-3") is True
        assert isolated_queue.closed_ids() == {"ITEM-3"}
        lines = isolated_queue.CLOSURES_PATH.read_text().splitlines()
        assert len(lines) == 2  # both closes ARE on the append-only record...
        assert isolated_queue.closure_count() == 1  # ...but count as one closure.

    def test_close_survives_a_queue_rebuild(self, isolated_queue):
        # The whole point of the ledger: build_queue() is safe to rerun on a
        # timer because it is DERIVED from the ledger, not a separate mutable
        # store a regeneration could forget.
        board = {"missions": [{"id": "ITEM-4", "title": "test mission",
                                "status": "pending_review", "priority": "P1"}]}
        isolated_queue.BOARD_PATH.write_text(json.dumps(board))
        q_before = isolated_queue.build_queue()
        assert any(i["id"] == "ITEM-4" for i in q_before["items"])

        isolated_queue.close("ITEM-4", by="Commander", reason="handled")
        q_after = isolated_queue.build_queue()
        assert not any(i["id"] == "ITEM-4" for i in q_after["items"])
        assert q_after["suppressed_by_closure"] == 1

    def test_reopen_then_close_again_later_close_wins(self, isolated_queue):
        # closed_ids() replays the ledger in order: a later reopen wins over an
        # earlier close, and a later close wins over an earlier reopen.
        isolated_queue.close("ITEM-5", by="Commander", reason="closing")
        isolated_queue.reopen("ITEM-5", by="Commander", reason="reopened by mistake")
        assert isolated_queue.is_closed("ITEM-5") is False
        isolated_queue.close("ITEM-5", by="Commander", reason="re-closing for real")
        assert isolated_queue.is_closed("ITEM-5") is True

    def test_close_requires_a_real_actor(self, isolated_queue):
        # `by` is required and validated -- a closure attributed to the Commander
        # must never be forgeable by a bogus/omitted argument.
        with pytest.raises(ValueError):
            isolated_queue.close("ITEM-6", by="nobody")


# ─────────────────────────────────────────────────────────────────────────────
# 2. HANDLER SHAPE — tcd/writeback.py
# ─────────────────────────────────────────────────────────────────────────────

class TestHandlerShape:
    """Each handler, called directly with a synthetic row, must append a decision
    block to the TEMPORARY decisions_path carrying the row id and the action verb
    -- never the real hale_decisions.md."""

    def test_handle_close_ai_actor(self, tmp_path):
        decisions_path = tmp_path / "decisions.md"
        overrides_path = tmp_path / "overrides.json"
        row = _row(id="row-close-1", comments="closing per row 42 in hale_decisions.md")
        writeback._handle_close(row, decisions_path, overrides_path=overrides_path, actor="ai")
        text = decisions_path.read_text()
        assert "row-close-1" in text
        assert "TCD-CLOSE-row-close-1" in text  # action verb: CLOSE

    def test_handle_close_commander_actor(self, tmp_path):
        decisions_path = tmp_path / "decisions.md"
        overrides_path = tmp_path / "overrides.json"
        row = _row(id="row-close-2", comments="")  # no artifact needed -- self-certifying
        writeback._handle_close(row, decisions_path, overrides_path=overrides_path, actor="commander")
        text = decisions_path.read_text()
        assert "row-close-2" in text
        assert "TCD-CLOSE-row-close-2" in text
        assert "verdict=PASS" in text

    def test_handle_dispose(self, tmp_path):
        decisions_path = tmp_path / "decisions.md"
        overrides_path = tmp_path / "overrides.json"
        row = _row(id="row-dispose-1", status="Delete")
        result = writeback._handle_dispose(
            row, lambda item_id: {"ok": True, "source": "test-fixture"},
            decisions_path, overrides_path=overrides_path,
        )
        assert result["ok"] is True
        text = decisions_path.read_text()
        assert "row-dispose-1" in text
        assert "TCD-DELETE-row-dispose-1" in text  # action verb: DELETE

    def test_handle_stage_move(self, tmp_path):
        decisions_path = tmp_path / "decisions.md"
        row = _row(id="row-stage-1", stage="T")
        writeback._handle_stage_move(row, "D", decisions_path, to_stage="T")
        text = decisions_path.read_text()
        assert "row-stage-1" in text
        assert "TCD-STAGE-row-stage-1" in text  # action verb: STAGE
        assert "D -> T" in text

    def test_handle_comment(self, tmp_path):
        decisions_path = tmp_path / "decisions.md"
        row = _row(id="row-comment-1", comments="Sterling: looking into it\nDani: any update?")
        writeback._handle_comment(row, "Sterling: looking into it\n", decisions_path)
        text = decisions_path.read_text()
        assert "row-comment-1" in text
        assert "TCD-COMMENT-row-comment-1" in text  # action verb: COMMENT
        assert "any update" in text

    def test_handle_create_task(self, tmp_path):
        decisions_path = tmp_path / "decisions.md"
        row = _row(id="row-task-1", title="File this")
        mission_id = writeback._handle_create_task(
            row, decisions_path, create_task_fn=lambda r: "MISSION-SYNTH-1",
        )
        assert mission_id == "MISSION-SYNTH-1"
        text = decisions_path.read_text()
        assert "row-task-1" in text
        assert "TCD-CREATETASK-row-task-1" in text  # action verb: CREATETASK
        assert "MISSION-SYNTH-1" in text


# ─────────────────────────────────────────────────────────────────────────────
# 3. SILVER BACK GATE — core/silver/gate.py, tested against the real gate
# ─────────────────────────────────────────────────────────────────────────────

class TestSilverBackGate:
    def test_prose_only_reason_is_held(self):
        # No file path, no mission/row id, no thread/url -- a bare claim.
        verdict = gate.run_gate(
            "Looks good, all done, closing this out.",
            "Looks good, all done, closing this out.",
            mission_id="GATE-TEST-1",
        )
        assert verdict.verdict == gate.HOLD
        assert not verdict.ok

    def test_reason_with_concrete_reference_passes(self):
        # A concrete reference (row ref / file extension) satisfies the gate.
        verdict = gate.run_gate(
            "Closed per row 42 in hale_decisions.md",
            "Closed per row 42 in hale_decisions.md",
            mission_id="GATE-TEST-2",
        )
        assert verdict.verdict == gate.PASS
        assert verdict.ok

    def test_empty_reason_is_held(self):
        verdict = gate.run_gate("", "", mission_id="GATE-TEST-3")
        assert verdict.verdict == gate.HOLD

    def test_handle_close_ai_actor_prose_only_holds_end_to_end(self, tmp_path):
        # The real path a Slack "Close" click takes for any non-Commander-board
        # caller (actor="ai" is the default): prose with no concrete reference
        # must HOLD, not silently PASS.
        decisions_path = tmp_path / "decisions.md"
        overrides_path = tmp_path / "overrides.json"
        row = _row(id="row-holdcheck-1", comments="All set, thanks!")
        writeback._handle_close(row, decisions_path, overrides_path=overrides_path, actor="ai")
        text = decisions_path.read_text()
        assert "verdict=HOLD" in text
        assert "Silver back-gate HOLD" in text

    def test_handle_close_ai_actor_concrete_reference_passes_end_to_end(self, tmp_path):
        decisions_path = tmp_path / "decisions.md"
        overrides_path = tmp_path / "overrides.json"
        row = _row(id="row-holdcheck-2",
                   comments="Verified and delivered; see /home/john/Thunderbird/hale_state.json")
        writeback._handle_close(row, decisions_path, overrides_path=overrides_path, actor="ai")
        text = decisions_path.read_text()
        assert "verdict=PASS" in text

    def test_commander_actor_bypasses_the_gate_by_design(self, tmp_path):
        # Contrast case: the SAME prose-only reason as the HOLD test above, but
        # actor="commander" -- self-certifying, no gate run. Confirms the HOLD
        # above is the gate actually doing its job, not some unrelated codepath
        # rejecting short text.
        decisions_path = tmp_path / "decisions.md"
        overrides_path = tmp_path / "overrides.json"
        row = _row(id="row-holdcheck-3", comments="All set, thanks!")
        writeback._handle_close(row, decisions_path, overrides_path=overrides_path, actor="commander")
        text = decisions_path.read_text()
        assert "verdict=PASS" in text
        assert "self-certifying" in text
