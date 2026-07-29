"""tests/test_human_override_close.py — regression suite for the Commander
human-override close path (SO 2026-07-29).

CHIEF SILVER's back-gate exists to stop an AI seat from self-certifying a
hollow completion, not to interrogate the Commander. Covers all three real
close entry points end to end via their actual public dispatch functions:

  - OpsCenter/mission_board_sync.py's `EXEC: closeout SSS-ID :: COMMANDER`
    and `EXEC: complete MISSION-ID COMMANDER` (process_exec_command)
  - tcd/writeback.py's `_handle_close(..., actor="commander")`

Every test asserts BOTH directions: a human override succeeds with no
machine-checkable artifact, AND an AI-seat close on the same kind of item
remains fully gated — a fix that lets agents self-certify would be a
regression, not a fix.
"""
from __future__ import annotations

import json

import pytest


@pytest.fixture
def isolated_ledgers(tmp_path, monkeypatch):
    """Redirect Silver's ledger + the mandatory-directive ledger to tmp so
    this suite never pollutes (or is polluted by) the live audit trail."""
    from core.silver import gate
    monkeypatch.setattr(gate, "LEDGER", tmp_path / "silver_ledger.jsonl")
    monkeypatch.setattr(gate, "DECISIONS", tmp_path / "hale_decisions.md")
    from core.staffing import directive_ledger
    monkeypatch.setattr(directive_ledger, "LEDGER", tmp_path / "mandatory_directives.jsonl")
    return gate


@pytest.fixture
def board(tmp_path, monkeypatch):
    """A real, empty mission board + lock, isolated from the live 100+
    mission production board — process_exec_command drives the actual
    load_board/save_board/acquire_lock/release_lock functions against it."""
    import OpsCenter.mission_board_sync as mbs
    board_path = tmp_path / "mission_board.json"
    lock_path = tmp_path / "mission_board.lock"
    board_path.write_text(json.dumps({"missions": [], "suspense_watch": []}))
    monkeypatch.setattr(mbs, "BOARD_PATH", board_path)
    monkeypatch.setattr(mbs, "LOCK_PATH", lock_path)
    return mbs


def _ledger_rows(gate_mod):
    if not gate_mod.LEDGER.exists():
        return []
    return [json.loads(line) for line in gate_mod.LEDGER.read_text().splitlines()]


# ── EXEC: closeout SSS-ID :: COMMANDER ──────────────────────────────────────

def test_sss_commander_closeout_needs_no_artifact(isolated_ledgers, board):
    board.process_exec_command(
        "sss Dani :: APPR :: verify override :: artifact at /home/john/Thunderbird/CLAUDE.md must exist"
        " :: :: :: :: CC :: /home/john/Thunderbird/CLAUDE.md"
    )
    b = board.load_board()
    sid = b["missions"][-1]["id"]
    assert b["missions"][-1]["status"] == "coordinated"   # no chop/decide/accomplish yet

    result = board.process_exec_command(f"closeout {sid} :: COMMANDER :: Yoda said ship it")
    assert "CLOSED" in result and "Commander" in result

    b2 = board.load_board()
    m = [x for x in b2["missions"] if x["id"] == sid][0]
    assert m["status"] == "closed"
    assert m["certified_by"] == "Commander"

    rows = _ledger_rows(isolated_ledgers)
    override_rows = [r for r in rows if r["mission_id"] == sid and r["verdict"] == "OVERRIDE"]
    assert len(override_rows) == 1
    assert override_rows[0]["overridden_by"] == "Commander"


def test_sss_ai_seat_closeout_still_gated(isolated_ledgers, board):
    """REGRESSION GUARD: the exact same not-yet-accomplished sheet, closed
    without the COMMANDER token, must still be blocked — same as before this
    fix existed."""
    board.process_exec_command(
        "sss OC :: APPR :: ai path check :: artifact at /home/john/Thunderbird/CLAUDE.md must exist"
        " :: :: :: :: CC :: /home/john/Thunderbird/CLAUDE.md"
    )
    b = board.load_board()
    sid = b["missions"][-1]["id"]

    result = board.process_exec_command(f"closeout {sid} :: CC :: logs/x@ok")
    assert "held" in result.lower() or "⛔" in result

    b2 = board.load_board()
    m = [x for x in b2["missions"] if x["id"] == sid][0]
    assert m["status"] != "closed"


# ── EXEC: complete MISSION-ID COMMANDER ─────────────────────────────────────

def test_mission_complete_commander_override_no_artifact(isolated_ledgers, board):
    b = board.load_board()
    b["missions"].append({
        "id": "MISSION-1", "title": "override complete", "status": "pending_review",
        "assigned_to": "CC", "priority": "P2", "logs": [], "acceptance_criteria": "",
    })
    fd = board.acquire_lock()
    board.save_board(b, fd)

    result = board.process_exec_command("complete MISSION-1 COMMANDER")
    assert "Completed" in result and "Commander override" in result

    b2 = board.load_board()
    m = [x for x in b2["missions"] if x["id"] == "MISSION-1"][0]
    assert m["status"] == "completed"
    assert "COMMANDER OVERRIDE" in m["logs"][-1]

    rows = _ledger_rows(isolated_ledgers)
    override_rows = [r for r in rows if r["mission_id"] == "MISSION-1" and r["verdict"] == "OVERRIDE"]
    assert len(override_rows) == 1


def test_mission_complete_ai_seat_still_gated_no_override_token(isolated_ledgers, board):
    """REGRESSION GUARD: same cross-Hale-assigned mission, no COMMANDER
    token — must still require a real verification_artifact + certifier."""
    b = board.load_board()
    b["missions"].append({
        "id": "MISSION-2", "title": "ai path still gated", "status": "pending_review",
        "assigned_to": "CC", "priority": "P2", "logs": [],
        "acceptance_criteria": "must have 3 things", "certified_by": "OC",
        "verification_artifact": "",
    })
    fd = board.acquire_lock()
    board.save_board(b, fd)

    result = board.process_exec_command("complete MISSION-2")
    assert "Cannot complete" in result

    b2 = board.load_board()
    m = [x for x in b2["missions"] if x["id"] == "MISSION-2"][0]
    assert m["status"] == "pending_review"


# ── tcd/writeback.py — TCD Decision Board Close action ──────────────────────

def test_writeback_commander_close_no_artifact(isolated_ledgers, tmp_path):
    import tcd.writeback as wb
    row = {"id": "TCD-ROW-1", "title": "commander closes bare row", "comments": ""}
    wb._handle_close(row, tmp_path / "hale_decisions.md",
                      overrides_path=tmp_path / "overrides.json", actor="commander")
    rows = _ledger_rows(isolated_ledgers)
    override_rows = [r for r in rows if r["mission_id"] == "TCD-ROW-1" and r["verdict"] == "OVERRIDE"]
    assert len(override_rows) == 1
    assert override_rows[0]["overridden_by"] == "Commander"


def test_writeback_ai_actor_close_still_gated(isolated_ledgers, tmp_path):
    """REGRESSION GUARD: the default/AI actor path on the same function must
    still run the real back-gate and HOLD on a bare claim."""
    import tcd.writeback as wb
    row = {"id": "TCD-ROW-2", "title": "ai closes bare claim", "comments": "done, trust me"}
    wb._handle_close(row, tmp_path / "hale_decisions.md",
                      overrides_path=tmp_path / "overrides.json", actor="ai")
    rows = _ledger_rows(isolated_ledgers)
    hold_rows = [r for r in rows if r["mission_id"] == "TCD-ROW-2" and r["verdict"] == "HOLD"]
    assert len(hold_rows) == 1
    assert not any(r["mission_id"] == "TCD-ROW-2" and r["verdict"] == "OVERRIDE" for r in rows)
