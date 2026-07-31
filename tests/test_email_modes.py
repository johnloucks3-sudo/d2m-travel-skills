#!/usr/bin/env python3
"""
test_email_modes.py
====================
Offline, deterministic tests for:
  * core/comms/email_mode_classifier.py::classify_email_mode
  * core/comms/directive_executor.py::route_email

Guards the measured defect: every inbound Commander email was treated
identically (no TASKING/FYI/CC distinction), so a genuine TASKING email
(2026-07-30, "Add to Loucks dossier, confirm flight arrangements...") produced
no mission and no reply.

All state is tmp_path-scoped. This suite MUST NEVER touch the real
OpsCenter/mission_board.json, OpsCenter/mandatory_directives.jsonl, or
hale_decisions.md — every module-level path the code under test reads or
writes is monkeypatched to a tmp_path file before route_email() is called.
"""

import json
import sys
from pathlib import Path

import pytest

THUNDERBIRD_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(THUNDERBIRD_DIR))

from core.comms import directive_executor as de  # noqa: E402
from core.comms.email_mode_classifier import (  # noqa: E402
    MODE_CC,
    MODE_FYI,
    MODE_TASKING,
    classify_email_mode,
)
from core.staffing import directive_ledger  # noqa: E402
from OpsCenter import mission_board_sync as mbs  # noqa: E402


# ── classify_email_mode: pure function, no I/O ────────────────────────────

def test_forward_with_top_line_instruction_is_tasking():
    """The Wave Pointe case: a Fwd: whose top line is an instruction must
    classify TASKING, not fall through to FYI as a "just forwarding" note."""
    subject = "Fwd: Wave Pointe confirmation"
    body = (
        "Add to Loucks dossier, confirm flight arrangements including flight "
        "number, times, layover.\n\n"
        "---------- Forwarded message ---------\n"
        "From: Wave Pointe <res@wavepointe.example>\n"
        "Subject: Your confirmation\n\n"
        "Thank you for booking..."
    )
    mode, reason = classify_email_mode(
        subject=subject, body=body, to_addr="d2mconcierge@d2mluxury.quest", cc_addr=""
    )
    assert mode == MODE_TASKING
    assert "forward" in reason.lower()


def test_plain_fyi_prefix_is_fyi():
    mode, reason = classify_email_mode(
        subject="FYI: Loucks moved their return flight up a day",
        body="FYI: just so you know, no action needed on this one.",
        to_addr="d2mconcierge@d2mluxury.quest",
        cc_addr="",
    )
    assert mode == MODE_FYI
    assert "explicit" in reason.lower()


def test_cc_only_message_is_cc():
    """d2m present only in Cc, no instruction anywhere — informational visibility,
    not an order."""
    mode, reason = classify_email_mode(
        subject="Dinner Saturday",
        body="Hey Marcus, still on for Saturday? Looping d2m so they have the date.",
        to_addr="marcus@example.com",
        cc_addr="d2mconcierge@d2mluxury.quest",
    )
    assert mode == MODE_CC
    assert "cc" in reason.lower()


def test_ambiguous_defaults_to_tasking():
    """No explicit prefix, no forward, no imperative verb, not Cc-only — the
    doctrine default is TASKING because a dropped order costs more than an
    extra queue item."""
    mode, reason = classify_email_mode(
        subject="Kuklinski",
        body="Where things stand on the balance for the Kuklinski trip.",
        to_addr="d2mconcierge@d2mluxury.quest",
        cc_addr="",
    )
    assert mode == MODE_TASKING
    assert "ambiguous" in reason.lower()


def test_explicit_cc_prefix_outranks_to_addr():
    """An explicit "CC:" prefix is the Commander naming the mode himself — it
    wins even though the recipient is technically in To."""
    mode, reason = classify_email_mode(
        subject="CC: heads up on Regent pricing",
        body="CC: no action, just keeping you in the loop.",
        to_addr="d2mconcierge@d2mluxury.quest",
        cc_addr="",
    )
    assert mode == MODE_CC
    assert "explicit" in reason.lower()


def test_explicit_task_prefix_wins_over_no_imperative_wording():
    mode, reason = classify_email_mode(
        subject="TASK: Kuklinski balance",
        body="TASK: figure out where the Kuklinski balance stands and let me know.",
        to_addr="d2mconcierge@d2mluxury.quest",
        cc_addr="",
    )
    assert mode == MODE_TASKING
    assert "explicit" in reason.lower()


# ── route_email: integration, fully isolated via monkeypatch ──────────────

@pytest.fixture
def isolated_board(tmp_path, monkeypatch):
    """Point every piece of module state route_email()/add_mission() touches
    at tmp_path — the real mission board, lock file, directive ledger, and
    directive-execution log are never opened."""
    board_path = tmp_path / "mission_board.json"
    lock_path = tmp_path / "mission_board.lock"
    board_path.write_text(json.dumps({"missions": []}))
    monkeypatch.setattr(mbs, "BOARD_PATH", board_path)
    monkeypatch.setattr(mbs, "LOCK_PATH", lock_path)

    ledger_path = tmp_path / "mandatory_directives.jsonl"
    monkeypatch.setattr(directive_ledger, "LEDGER", ledger_path)

    log_path = tmp_path / "directive_executions.jsonl"
    monkeypatch.setattr(de, "LOG_PATH", log_path)

    return board_path


def _mission_count(board_path):
    return len(json.loads(board_path.read_text()).get("missions", []))


def test_route_email_tasking_creates_exactly_one_mission(isolated_board):
    before = _mission_count(isolated_board)
    result = de.route_email(
        "Add to Loucks dossier, confirm flight arrangements including flight "
        "number, times, layover.",
        subject="Fwd: Wave Pointe confirmation",
        to_addr="d2mconcierge@d2mluxury.quest",
        cc_addr="",
    )
    after = _mission_count(isolated_board)
    assert result["mode"] == MODE_TASKING
    assert result["status"] == de.TASKED
    assert result["mission_id"] is not None
    assert after == before + 1

    board = json.loads(isolated_board.read_text())
    created = [m for m in board["missions"] if m["id"] == result["mission_id"]][0]
    assert created.get("source") == "email"


def test_route_email_fyi_creates_no_mission(isolated_board):
    before = _mission_count(isolated_board)
    result = de.route_email(
        "FYI: just so you know, no action needed on this one.",
        subject="FYI: Loucks moved their return flight up a day",
        to_addr="d2mconcierge@d2mluxury.quest",
        cc_addr="",
    )
    after = _mission_count(isolated_board)
    assert result["mode"] == MODE_FYI
    assert result["status"] == de.LOGGED
    assert result["mission_id"] is None
    assert after == before  # no mission created


def test_route_email_cc_creates_no_mission(isolated_board):
    before = _mission_count(isolated_board)
    result = de.route_email(
        "Hey Marcus, still on for Saturday? Looping d2m so they have the date.",
        subject="Dinner Saturday",
        to_addr="marcus@example.com",
        cc_addr="d2mconcierge@d2mluxury.quest",
    )
    after = _mission_count(isolated_board)
    assert result["mode"] == MODE_CC
    assert result["status"] == de.LOGGED
    assert result["mission_id"] is None
    assert after == before  # no mission created
