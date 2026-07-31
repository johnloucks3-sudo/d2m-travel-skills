"""
tests/test_tcd_slack_parity.py — TCD->Slack migration, task 22: handler parity +
no-silent-truncation tests.

Covers the four contracts in the task's authoritative description (TaskGet #22),
which is broader than the first-pass summary this file shipped under:

  1. CLOSURE PERMANENCE (core/comms/commander_queue.py) — a Commander close is an
     append-only ledger fact. is_closed()/closed_ids() see it immediately, and
     re-closing the same item is idempotent: the ledger gains a second line (it is
     append-only by design) but the DERIVED closed set still counts the item once.
  2. HANDLER SHAPE (tcd/writeback.py) — each write-back handler (_handle_close,
     _handle_dispose, _handle_stage_move, _handle_comment, _handle_create_task),
     called directly with a synthetic row, appends a decision block that carries
     the row id and the action verb (CLOSE/DELETE/STAGE/COMMENT/CREATETASK).
  3. SILVER BACK GATE (core/silver/gate.py) — a close whose reason is prose with no
     concrete reference (no path, no mission/row id, no thread/url) is HELD, never
     silently passed — tested against the real gate in core/silver/gate.py, not a
     reimplementation of its rule.
  4. NO-SILENT-TRUNCATION (core/comms/slack_home.py's build_home_view) — for 150
     synthetic items, the rendered-vs-hidden split on Band 1's ("Alerts") overflow
     footer is asserted EXACT (not "a footer exists"), the top summary line's
     total/alert counts are cross-checked against home_item_count() so items
     outside the rendered set are still accounted for, and the block count never
     exceeds Slack's MAX_VIEW_BLOCKS. Three real, already-fixed bugs live in this
     file's own history: the original 5-section version once rendered 96/150,
     claimed 17 hidden when 54 actually were, and dropped the Watch section's
     header entirely; the 2026-07-29 AG parity audit then found even a CORRECT
     5-section render goes invisible past ~50 items against a 200+ item board,
     which is why the view was rescoped to Awaiting-You-only; then on 2026-07-30
     the Commander redirected the whole surface again — "I do not need the design
     we spent so much time on... I just need a link to the sheet" — collapsing it
     to a three-band FRONT DOOR: Band 1 ALERTS (only priority=='p0' or a past
     suspense date — narrower even than the old Awaiting-You grouping, which also
     swept in pending_review/deferred/Strategic), Band 2 FRONT DOOR (one fixed
     row per tool: Sheet/Gmail/Drive/Calendar/Keep/Texts/Evernote/Obsidian, never
     truncated), Band 3 TASK (one button). These tests target that current
     three-band contract: the block-budget reservation now covers all of Band 2
     + Band 3 by construction, so only Band 1 items can ever truncate, and only
     after that reserve.

SLACK-PATH PARITY — TWO SEPARATE FINDINGS, both load-bearing for #23 (retiring
AppSheet polling): task #20 (core/comms/tcd_actions.py, "the adapter") landed
WHILE this file was in progress, changing the picture from "doesn't exist yet" to
"exists but isn't wired up":

  (a) core/comms/tcd_actions.py's apply() genuinely achieves parity: for every one
      of close/delete/stage/comment/create_task it calls the EXACT SAME
      tcd/writeback.py handler the Sheets path calls (see its own docstring: "this
      module reimplements none of their logic"). TestSlackActionAdapterParity below
      fires apply() for real (not a reimplementation) for all five actions and
      asserts the hale_decisions.md shape matches TestHandlerShape's assertions —
      because it IS the same handler. apply() takes no dependency injection
      (decisions_path/overrides_path/delete_fn/item source are all hardcoded
      production paths/calls), so isolating it means monkeypatching four module-
      level things directly rather than passing parameters — see isolated_apply.
  (b) But nothing calls apply() yet. core/comms/slack_receiver.py's
      handle_block_action() — the function actually wired to the live Socket Mode
      button clicks — still only handles close/approve/defer, and does so by
      calling commander_queue.close()/reopen() directly, with zero reference to
      tcd_actions anywhere in the file (grep confirms). So today, live, a Slack
      button tap: (1) supports only close/approve/defer, no delete/stage/comment/
      create_task at all; (2) even for close, writes ONLY to the commander_queue
      ledger, never hale_decisions.md — no PLAN:CLOSE block, no Silver back-gate
      run. TestLiveSlackButtonVsAdapter pins both halves of this with real
      assertions (a call-recording stub proving apply() is never invoked, and a
      check that decisions.md stays untouched) specifically so it goes red the
      moment someone wires the two together — at which point these two tests
      should be deleted, not "fixed."

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
  - core/comms/slack_receiver.py's AUDIT_PATH (OpsCenter/slack_interactions.jsonl)
    is likewise a hardcoded module constant, patched per-test.
No test in this file may write to the real hale_decisions.md, OpsCenter/mission_
board.json, OpsCenter/silver_ledger.jsonl, OpsCenter/state/commander_closures.jsonl,
or OpsCenter/slack_interactions.jsonl.

Run: python3 -m pytest tests/test_tcd_slack_parity.py -q
"""
from __future__ import annotations

import json
import re
import sys
from collections import OrderedDict
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.comms import commander_queue  # noqa: E402
from core.comms import slack_home  # noqa: E402
from core.comms import slack_receiver  # noqa: E402
from core.comms import tcd_actions  # noqa: E402
from core.silver import gate  # noqa: E402
from tcd import overrides as tcd_overrides  # noqa: E402
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


# ─────────────────────────────────────────────────────────────────────────────
# 4. NO-SILENT-TRUNCATION — core/comms/slack_home.py build_home_view()
# ─────────────────────────────────────────────────────────────────────────────

def _parse_band1(view: dict) -> dict:
    """Count rendered item ("section"-type) blocks and pull the exact "+N more
    in Alerts" overflow count, if any, scoped strictly to Band 1.

    Band 2 (Front Door) also emits "section"-type blocks -- one fixed row per
    tool -- so counting every "section" block in the view would silently fold
    those 9 fixed-chrome blocks into the item count. Scope to the blocks
    between the FIRST header (Band 1's own title, "Alerts" or the all-clear
    text) and the SECOND header ("Front Door") -- Band 1's own extent, nothing
    else.
    """
    blocks = view["blocks"]
    header_idx = [i for i, b in enumerate(blocks) if b["type"] == "header"]
    assert header_idx, "no header block found -- view has no Band 1 title"
    band1_start = header_idx[0] + 1
    band1_end = header_idx[1] if len(header_idx) > 1 else len(blocks)

    rendered = 0
    hidden = 0
    for b in blocks[band1_start:band1_end]:
        if b["type"] == "section":
            rendered += 1
        elif b["type"] == "context":
            m = re.match(r"\+(\d+) more in (.+)$", b["elements"][0]["text"])
            if m:
                hidden = int(m.group(1))
    return {"rendered": rendered, "hidden": hidden}


def _parse_summary(view: dict) -> tuple[int, int]:
    """(total, alerts) parsed out of the top "{total} open on the board ·
    {alerts} alert(s) right now" context block."""
    text = view["blocks"][0]["elements"][0]["text"]
    m = re.match(r"(\d+) open on the board · (\d+) alerts? right now", text)
    assert m, f"summary line changed shape, update the parser: {text!r}"
    return int(m.group(1)), int(m.group(2))


def _synth_items(n: int, *, id_prefix: str, status: str, inbox: str, priority: str) -> list:
    return [{"id": f"{id_prefix}-{i}", "status": status, "inbox": inbox,
             "priority": priority, "title": f"synthetic {id_prefix} {i}",
             "source": "test-harness", "date": ""}
            for i in range(n)]


class TestNoSilentTruncation:
    """core/comms/slack_home.py's build_home_view() (rewritten again 2026-07-30
    into a three-band FRONT DOOR at the Commander's direction) renders ONLY
    Band 1 "Alerts" -- priority=='p0' or a past suspense date, see
    slack_home._alert_items() -- as itemized rows; Band 2 (Front Door, one
    fixed row per tool) and Band 3 (Task, one button) never truncate, so the
    100-block budget is reserved for them FIRST by construction and only
    Band 1 items can ever be cut. The invariant carried over unchanged from
    every prior version of this view: rendered + declared-hidden == the
    alert set's real size, always, and the top summary line's totals must
    never drift from home_item_count()'s own numbers -- so even items this
    view doesn't itemize (anything not p0/overdue) are still accounted for.
    These tests pin the EXACT counts, not "a footer/summary line exists.\""""

    @pytest.fixture(autouse=True)
    def _no_live_sheet_config(self, tmp_path, monkeypatch):
        # Band 2's Sheet row reads config/tcd_sheet_config.json (a real repo
        # file) for a URL to embed; read-only and harmless, but pinning it to a
        # path that doesn't exist keeps that row's text deterministic instead
        # of depending on whatever happens to be configured live.
        monkeypatch.setattr(slack_home, "SHEET_CONFIG_PATH", tmp_path / "no_such_config.json")

    def test_150_alert_items_footer_exact(self):
        # All 150 are p0 -> all land in Band 1 (Alerts), regardless of inbox
        # or status (urgency outranks workflow state by design). reserved =
        # 3 (summary + Band-1 header + one overflow slot) + 9 (Band 2: header
        # + 8 fixed tool rows) + 2 (Band 3: header + actions) = 14 ->
        # budget=86 -> 150-86=64 hidden.
        items = _synth_items(150, id_prefix="aw", status="Open",
                             inbox="strategic", priority="p0")
        view = slack_home.build_home_view(items)
        assert len(view["blocks"]) <= slack_home.MAX_VIEW_BLOCKS
        parsed = _parse_band1(view)
        assert parsed["rendered"] == 86
        assert parsed["hidden"] == 64
        assert parsed["rendered"] + parsed["hidden"] == 150
        # summary(1) + Band1 header(1) + 86 items + overflow(1) + Band2(9) + Band3(2)
        assert len(view["blocks"]) == 100
        total, alerts = _parse_summary(view)
        assert (total, alerts) == (150, 150)

    def test_150_items_mixed_only_alerts_render_but_total_never_drifts(self):
        # 60 are p0 (Band 1 alerts); 30 each in Operational/Reference/Watch
        # (deliberately non-alert: plain status=Open, non-p0 priority, no
        # suspense date). Those 90 are intentionally not itemized in this
        # scoped view, but must still be counted in the summary line -- the
        # actual no-silent-loss guarantee this view makes.
        items = (
            _synth_items(60, id_prefix="aw", status="Open", inbox="strategic", priority="p0")
            + _synth_items(30, id_prefix="op", status="Open", inbox="operational", priority="p2")
            + _synth_items(30, id_prefix="rf", status="Open", inbox="reference", priority="p3")
            + _synth_items(30, id_prefix="wa", status="Open", inbox="", priority="p3")
        )
        assert len(items) == 150

        # Ground truth for section membership comes from the SAME production
        # function build_home_view calls internally -- not a re-derived rule.
        expected_counts = slack_home.home_item_count(items)
        assert expected_counts == {"Awaiting You": 60, "Operational": 30,
                                   "Reference": 30, "Watch": 30}

        view = slack_home.build_home_view(items)
        assert len(view["blocks"]) <= slack_home.MAX_VIEW_BLOCKS
        parsed = _parse_band1(view)

        # The 60 alerts are under budget (60 < 86) -- no truncation, no
        # overflow footer, everything in Band 1 renders.
        assert parsed == {"rendered": 60, "hidden": 0}

        # The 90 non-alert items aren't itemized here, but the summary line
        # still carries the true total -- this is what "no silent" means for a
        # deliberately scoped view: never itemized without being counted.
        total, alerts = _parse_summary(view)
        assert (total, alerts) == (150, 60)

    def test_no_alert_items_still_reports_the_true_total(self):
        # 5 real items exist, none of them p0/overdue -- must not render as
        # a bare empty state that implies zero items exist anywhere, and must
        # show the all-clear header rather than a blank tab.
        items = _synth_items(5, id_prefix="op", status="Open",
                             inbox="operational", priority="p2")
        view = slack_home.build_home_view(items)
        assert view["blocks"][1] == {"type": "header", "text": {
            "type": "plain_text", "text": "All clear — no P0s, nothing overdue",
            "emoji": True}}
        total, alerts = _parse_summary(view)
        assert (total, alerts) == (5, 0)

    def test_zero_items_reports_zero_not_a_stale_number(self):
        view = slack_home.build_home_view([])
        total, alerts = _parse_summary(view)
        assert (total, alerts) == (0, 0)

    def test_p0_and_overdue_always_render_regardless_of_status(self):
        # The exact bug this whole surface exists to prevent: 4 P0s and 10
        # overdue items sat invisible for up to 36 days because a workflow
        # gate ran BEFORE the urgency check. Pin it directly: a deferred P0
        # and an overdue-but-closed item must both still render in Band 1.
        items = [
            {"id": "P0-DEFERRED", "status": "deferred", "inbox": "operational",
             "priority": "p0", "title": "deferred P0", "source": "test",
             "date": "2026-07-01"},
            {"id": "OVERDUE-CLOSED-WORKFLOW", "status": "in_coordination",
             "inbox": "operational", "priority": "p2", "title": "overdue item",
             "source": "test", "date": "2026-07-01",
             "suspense_date": "2020-01-01"},
        ]
        view = slack_home.build_home_view(items)
        text = json.dumps(view["blocks"])
        assert "P0-DEFERRED" in text, "deferred P0 must still render as an alert"
        assert "OVERDUE-CLOSED-WORKFLOW" in text, (
            "overdue item must render as an alert regardless of workflow status"
        )
        total, alerts = _parse_summary(view)
        assert (total, alerts) == (2, 2)

    def test_small_alert_batch_no_truncation_no_spurious_footer(self):
        # Below the budget entirely -- must render everything and add no
        # overflow footer.
        items = _synth_items(5, id_prefix="aw", status="Open",
                             inbox="strategic", priority="p0")
        view = slack_home.build_home_view(items)
        parsed = _parse_band1(view)
        assert parsed == {"rendered": 5, "hidden": 0}


# ─────────────────────────────────────────────────────────────────────────────
# 5. SLACK-PATH PARITY, PART A — core/comms/tcd_actions.py's apply() (task #20)
#    genuinely calls the same writeback handlers as the Sheets path.
# ─────────────────────────────────────────────────────────────────────────────

class _FakeItem:
    """Stands in for a tcd.item_model.Item -- slack_action_to_row only ever
    calls .to_dict() on whatever collect_all() yields."""
    def __init__(self, row: dict):
        self._row = row

    def to_dict(self) -> dict:
        return self._row


class TestSlackActionAdapterParity:
    @pytest.fixture
    def isolated_apply(self, tmp_path, monkeypatch):
        """apply() takes no parameters for decisions_path/overrides_path/
        delete_fn/item source -- every one is a hardcoded production path or
        live call (writeback.HALE_DECISIONS, tcd.overrides.OVERRIDES_PATH,
        writeback._default_delete_fn, tcd.collectors.collect_all). Isolating
        it for a test means monkeypatching each directly."""
        monkeypatch.setattr(writeback, "HALE_DECISIONS", tmp_path / "decisions.md")
        monkeypatch.setattr(tcd_overrides, "OVERRIDES_PATH", tmp_path / "overrides.json")
        monkeypatch.setattr(writeback, "_default_delete_fn",
                            lambda item_id: {"ok": True, "source": "test-fixture"})
        return tmp_path

    def _stub_items(self, monkeypatch, **row_overrides):
        row = _row(**row_overrides)
        monkeypatch.setattr(tcd_actions, "collect_all", lambda: [_FakeItem(row)])
        return row

    def test_close_writes_same_shape_as_sheets_path(self, isolated_apply, monkeypatch):
        self._stub_items(monkeypatch, id="slack-close-1",
                         comments="closed per row 42 in hale_decisions.md")
        result = tcd_actions.apply("slack-close-1", "close", actor="Commander")
        assert result["ok"] is True
        text = (isolated_apply / "decisions.md").read_text()
        assert "slack-close-1" in text
        assert "TCD-CLOSE-slack-close-1" in text  # same action verb TestHandlerShape checks
        assert "verdict=PASS" in text

    def test_close_ai_actor_prose_only_still_holds(self, isolated_apply, monkeypatch):
        # actor defaults to "ai" unless the caller can positively assert
        # Commander identity -- see tcd_actions.py's own module docstring on
        # why this was deliberately changed FROM defaulting to "Commander".
        self._stub_items(monkeypatch, id="slack-close-2", comments="All set, thanks!")
        tcd_actions.apply("slack-close-2", "close", actor="ai")
        text = (isolated_apply / "decisions.md").read_text()
        assert "verdict=HOLD" in text
        assert "Silver back-gate HOLD" in text

    def test_delete_writes_same_shape_as_sheets_path(self, isolated_apply, monkeypatch):
        self._stub_items(monkeypatch, id="slack-del-1")
        result = tcd_actions.apply("slack-del-1", "delete")
        assert result["ok"] is True
        text = (isolated_apply / "decisions.md").read_text()
        assert "TCD-DELETE-slack-del-1" in text

    def test_stage_writes_same_shape_as_sheets_path(self, isolated_apply, monkeypatch):
        self._stub_items(monkeypatch, id="slack-stage-1", stage="D")
        result = tcd_actions.apply("slack-stage-1", "stage", value="T")
        assert result == {"ok": True, "action": "stage", "id": "slack-stage-1",
                          "from": "D", "to": "T"}
        text = (isolated_apply / "decisions.md").read_text()
        assert "TCD-STAGE-slack-stage-1" in text
        assert "D -> T" in text

    def test_stage_requires_a_target_value(self, isolated_apply, monkeypatch):
        self._stub_items(monkeypatch, id="slack-stage-2", stage="D")
        with pytest.raises(ValueError):
            tcd_actions.apply("slack-stage-2", "stage")

    def test_comment_writes_same_shape_as_sheets_path(self, isolated_apply, monkeypatch):
        self._stub_items(monkeypatch, id="slack-comment-1", comments="Sterling: on it")
        result = tcd_actions.apply("slack-comment-1", "comment", value="any update?")
        assert result["ok"] is True
        text = (isolated_apply / "decisions.md").read_text()
        assert "TCD-COMMENT-slack-comment-1" in text
        assert "any update" in text

    def test_create_task_writes_same_shape_as_sheets_path(self, isolated_apply, monkeypatch):
        self._stub_items(monkeypatch, id="slack-task-1", title="File this")
        board_path = isolated_apply / "mission_board.json"
        board_path.write_text(json.dumps({"missions": [], "last_updated": ""}))
        from OpsCenter import mission_board_sync as mbs
        monkeypatch.setattr(mbs, "BOARD_PATH", board_path)
        monkeypatch.setattr(mbs, "LOCK_PATH", isolated_apply / "mission_board.lock")

        result = tcd_actions.apply("slack-task-1", "create_task", value="do the thing")
        assert result["ok"] is True
        text = (isolated_apply / "decisions.md").read_text()
        assert "TCD-CREATETASK-slack-task-1" in text


# ─────────────────────────────────────────────────────────────────────────────
# 6. SLACK-PATH PARITY, PART B — the LIVE button handler is not wired to the
#    adapter above. These two tests should go RED (and be deleted) the moment
#    someone connects them.
# ─────────────────────────────────────────────────────────────────────────────

class TestLiveSlackButtonVsAdapter:
    @pytest.fixture(autouse=True)
    def _isolate_slack_audit(self, tmp_path, monkeypatch):
        monkeypatch.setattr(slack_receiver, "AUDIT_PATH", tmp_path / "slack_interactions.jsonl")

    def test_live_close_button_closes_the_queue_permanently(self, isolated_queue):
        # The one thing the live path DOES do correctly today.
        payload = {"actions": [{"action_id": "close", "value": "ITEM-SLACK-1"}],
                  "user": {"username": "yoda"}}  # no response_url -- skip the network call
        row = slack_receiver.handle_block_action(payload)
        assert row["status"] == "ok"
        assert isolated_queue.is_closed("ITEM-SLACK-1") is True

    def test_live_close_button_DOES_call_the_adapter(self, isolated_queue, monkeypatch):
        """The Commander's tap must reach the canonical audit trail, not just the ledger.

        This test was originally written inverted — asserting the adapter was NEVER
        reached — to pin a real gap: on 2026-07-29 three genuine Commander taps landed in
        commander_closures.jsonl and left no trace in hale_decisions.md, because
        handle_block_action called commander_queue.close() and stopped there. Silver never
        ran and no PLAN:CLOSE block was written.

        The wiring now exists, so the assertion is flipped rather than deleted: it stays a
        permanent guard that the tap keeps reaching the audit trail. If someone unwires it,
        this goes red instead of the gap returning silently.

        actor must be exactly 'Commander' — this is the one call site that earns the Silver
        bypass, having actually read payload['user'].
        """
        calls = []
        monkeypatch.setattr(tcd_actions, "apply", lambda *a, **k: calls.append((a, k)))
        payload = {"actions": [{"action_id": "close", "value": "ITEM-SLACK-2"}],
                  "user": {"username": "yoda"}}
        slack_receiver.handle_block_action(payload)
        assert calls, "Commander's tap never reached tcd_actions.apply() — audit trail gap"
        args, kwargs = calls[0]
        assert args[0] == "ITEM-SLACK-2"
        assert kwargs.get("actor") == "Commander"

    def test_live_close_button_never_writes_hale_decisions_md(self, isolated_queue):
        # Documents the asymmetry directly: no PLAN:CLOSE block, no Silver
        # back-gate run -- because handle_block_action never calls the
        # handler that would produce either.
        payload = {"actions": [{"action_id": "close", "value": "ITEM-SLACK-3"}],
                  "user": {"username": "yoda"}}
        slack_receiver.handle_block_action(payload)
        assert not gate.DECISIONS.exists()

    def test_live_path_has_no_delete_stage_comment_or_create_task_action(self, isolated_queue):
        # Only close/approve/defer are recognized; everything else is
        # explicitly "ignored", not routed anywhere -- confirmed against the
        # real dispatch, not asserted from reading the source.
        for action_id in ("delete", "stage", "comment", "create_task"):
            payload = {"actions": [{"action_id": action_id, "value": "ITEM-SLACK-4"}],
                      "user": {"username": "yoda"}}
            row = slack_receiver.handle_block_action(payload)
            assert row["status"] == "ignored"
            assert f"unknown action_id {action_id!r}" in row["detail"]
