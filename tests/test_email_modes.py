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

2026-08-08 (Round Table front-desk redesign): TASKING/CC now assign a real
cross-Hale seat, which routes through delegate_mission() — whose side effects
are a Telegram handoff and a C2 Fabric bus write. Both are stubbed in the
fixture so this suite stays offline and deterministic. Silver's FRONT gate is
deliberately NOT stubbed: it is the gate the new criteria have to satisfy, and
stubbing it would let a broken spec ship green.
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
from core.relay import delegation_wiring  # noqa: E402
from core.silver import gate as silver_gate  # noqa: E402
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
    monkeypatch.setattr(de, "THREAD_INDEX_PATH", tmp_path / "email_thread_missions.json")

    # Silver's ledger + hale_decisions.md are real files the FRONT gate appends
    # to on every verdict. The gate itself still runs; only its logging moves.
    monkeypatch.setattr(silver_gate, "LEDGER", tmp_path / "silver_ledger.jsonl")
    monkeypatch.setattr(silver_gate, "DECISIONS", tmp_path / "hale_decisions.md")

    # Live side effects of the seat-delegation path: Telegram handoff + C2 bus.
    bus_events = []
    monkeypatch.setattr(delegation_wiring, "_notify_handoff",
                        lambda *a, **k: None)
    monkeypatch.setattr(delegation_wiring, "mirror_stage_to_bus",
                        lambda mid, stage, detail, **k: bus_events.append((mid, stage)) or {})

    return board_path


def _mission_count(board_path):
    return len(json.loads(board_path.read_text()).get("missions", []))


def _mission(board_path, mission_id):
    board = json.loads(board_path.read_text())
    return [m for m in board["missions"] if m["id"] == mission_id][0]


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


def test_route_email_fyi_files_a_closed_mission(isolated_board):
    """FYI is a filed row, not work: the mission exists so the letter is not a
    silent drop, and it is closed at creation so it never enters the queue."""
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
    assert result["mission_id"] is not None
    assert after == before + 1
    assert _mission(isolated_board, result["mission_id"])["status"] == "closed"
    assert "DISPOSITION — FYI" in result["receipt"]


def test_route_email_cc_creates_a_mission(isolated_board):
    """Commander's non-negotiable: CC = intent. Being copied is being tasked,
    so a CC letter creates a real ticket with a seat, a suspense, and criteria
    — it is not filed away as informational."""
    before = _mission_count(isolated_board)
    result = de.route_email(
        "Hey Marcus, still on for Saturday? Looping d2m so they have the date.",
        subject="Dinner Saturday",
        to_addr="marcus@example.com",
        cc_addr="d2mconcierge@d2mluxury.quest",
    )
    after = _mission_count(isolated_board)
    assert result["mode"] == MODE_CC
    assert result["status"] == de.TASKED
    assert result["mission_id"] is not None
    assert after == before + 1


def test_tasking_populates_who_rdd_and_action(isolated_board):
    """The defect this closes: every email mission was created "unassigned",
    with no suspense and no acceptance criteria — a row nobody owned."""
    result = de.route_email(
        "Draft the client email for the Kuklinski balance and send me the copy.",
        subject="Kuklinski balance",
        to_addr="d2mconcierge@d2mluxury.quest",
        cc_addr="",
    )
    assert result["status"] == de.TASKED
    created = _mission(isolated_board, result["mission_id"])

    assert created["assigned_to"] not in ("unassigned", "", None)
    assert created["assigned_to"] in ("CC", "OC", "AG")
    assert created["acceptance_criteria"].strip()
    assert created["deadline"]
    assert result["who"] == created["assigned_to"]
    assert result["rdd"]
    assert result["action"]
    # "draft"/"client" are judgment words — this one belongs to CC, not OC.
    assert created["assigned_to"] == "CC"


def test_urgent_letter_pulls_the_rdd_in(isolated_board):
    urgent = de.route_email(
        "URGENT: confirm the Loucks flight times today.",
        subject="URGENT: Loucks flights",
        to_addr="d2mconcierge@d2mluxury.quest",
    )
    standard = de.route_email(
        "Confirm the Westbrook transfer booking reference.",
        subject="Westbrook transfer",
        to_addr="d2mconcierge@d2mluxury.quest",
    )
    assert urgent["rdd"] < standard["rdd"]


def test_ack_closes_the_referenced_ticket(isolated_board):
    """A solo "Roger." is not work — it closes the ticket it answers and gets a
    receipt saying so. No new mission, no silent drop."""
    tasked = de.route_email(
        "Add to Loucks dossier, confirm flight arrangements.",
        subject="Fwd: Wave Pointe confirmation",
        to_addr="d2mconcierge@d2mluxury.quest",
        thread_id="thread-abc",
    )
    assert tasked["status"] == de.TASKED
    before = _mission_count(isolated_board)

    ack = de.route_email(
        "Roger.",
        subject="Re: Fwd: Wave Pointe confirmation",
        to_addr="d2mconcierge@d2mluxury.quest",
        thread_id="thread-abc",
        previous_mission_id=tasked["mission_id"],
    )
    assert ack["status"] == de.ACKED
    assert ack["mission_id"] == tasked["mission_id"]
    assert _mission_count(isolated_board) == before  # no new work
    assert _mission(isolated_board, tasked["mission_id"])["status"] == "closed"
    assert f"ticket {tasked['mission_id']} closed" in ack["receipt"]


def test_ack_by_thread_lookup_without_previous_mission_id(isolated_board):
    """The sweep does not always know the prior ticket — the thread does."""
    tasked = de.route_email(
        "Pull the Regent deposit schedule.",
        subject="Regent deposits",
        to_addr="d2mconcierge@d2mluxury.quest",
        thread_id="thread-xyz",
    )
    ack = de.route_email(
        "Thanks",
        subject="Re: Regent deposits",
        to_addr="d2mconcierge@d2mluxury.quest",
        thread_id="thread-xyz",
    )
    assert ack["status"] == de.ACKED
    assert ack["mission_id"] == tasked["mission_id"]


def test_second_ack_on_the_same_thread_closes_nothing(isolated_board):
    """The thread index still points at the ticket after it is closed. A second
    ack must NOT re-close it and report that as work — the receipt would be a
    lie about a mission that was already finished."""
    tasked = de.route_email(
        "Check the Furlow final payment date.",
        subject="Furlow final payment",
        to_addr="d2mconcierge@d2mluxury.quest",
        thread_id="thread-dup",
    )
    first = de.route_email("Roger.", subject="Re: Furlow final payment",
                           to_addr="d2mconcierge@d2mluxury.quest", thread_id="thread-dup")
    assert first["status"] == de.ACKED

    second = de.route_email("Thanks", subject="Re: Furlow final payment",
                            to_addr="d2mconcierge@d2mluxury.quest", thread_id="thread-dup")
    assert second["status"] == de.LOGGED
    assert second["mission_id"] is None
    assert "no new work" in second["receipt"]
    assert _mission(isolated_board, tasked["mission_id"])["status"] == "closed"


def test_ack_with_no_open_ticket_logs_and_still_replies(isolated_board):
    before = _mission_count(isolated_board)
    ack = de.route_email(
        "Roger.",
        subject="Re: something from last month",
        to_addr="d2mconcierge@d2mluxury.quest",
        thread_id="thread-unknown",
    )
    assert ack["status"] == de.LOGGED
    assert ack["mission_id"] is None
    assert _mission_count(isolated_board) == before
    assert "no new work" in ack["receipt"]


def test_every_letter_gets_a_receipt(isolated_board):
    """No silent drops — TASKING, CC, FYI and ACK all leave with a DISPOSITION
    block carrying WHO / RDD / ACTION / DELIVERABLE."""
    letters = [
        ("Add the Spencer deposit to the board.", "Spencer deposit", ""),
        ("FYI: no action needed.", "FYI: schedule shift", ""),
        ("Looping you in on Saturday.", "Dinner Saturday", "d2mconcierge@d2mluxury.quest"),
        ("Roger.", "Re: nothing open", ""),
    ]
    for body, subject, cc in letters:
        r = de.route_email(
            body, subject=subject,
            to_addr="marcus@example.com" if cc else "d2mconcierge@d2mluxury.quest",
            cc_addr=cc,
        )
        receipt = r.get("receipt", "")
        assert receipt.startswith("DISPOSITION — "), subject
        for field in ("WHO:", "RDD:", "ACTION:", "DELIVERABLE:"):
            assert field in receipt, f"{subject} missing {field}"
        assert r.get("leaf_token")
