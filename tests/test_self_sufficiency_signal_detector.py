"""Regression test for the client self-sufficiency signal detector.

ADDED 2026-07-16 per Commander directive: catch a client quietly asserting
they don't need the Wing's help ("we can book this ourselves") as a leading
indicator of relationship erosion -- distinct from generic negative-
sentiment/complaint detection. Root incident: McLeod said this exact class
of thing 5+ months before their post-voyage survey verdict ("We are not big
fans of the AI portions. We picked a travel agent for a personalized
experience.") and it sat unflagged the whole time.

One occurrence is logged only; a second occurrence for the same client
escalates to a mission-board ticket via the shared dedup-safe add_mission()
path (see OpsCenter/mission_board_sync.py) so it can't silently repeat-file.
"""
import json
import sys
from pathlib import Path

THUNDERBIRD_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(THUNDERBIRD_DIR / "core" / "email"))
sys.path.insert(0, str(THUNDERBIRD_DIR))
sys.path.insert(0, str(THUNDERBIRD_DIR / "OpsCenter"))

import core.email.thunderbird_email_intel as intel  # noqa: E402
import mission_board_sync as mbs  # noqa: E402

REAL_MCLEOD_QUOTE = "All of these are things we can book for ourselves and we have no issue doing so."


def _patch_state_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(intel, "RELATIONSHIP_SIGNALS_FILE", tmp_path / "client_relationship_signals.json")


def test_first_occurrence_is_logged_not_escalated(tmp_path, monkeypatch):
    _patch_state_paths(tmp_path, monkeypatch)
    mission_id = intel._track_self_sufficiency_signal(
        "Erik & Melissa McLeod", "mcleod@example.com", REAL_MCLEOD_QUOTE,
        {"id": "msg1", "headers": {"Date": "2026-01-28", "Subject": "Re: transfers"}},
    )
    assert mission_id is None, "a single occurrence must be logged, not escalated"

    state = json.loads((tmp_path / "client_relationship_signals.json").read_text())
    entry = state["mcleod@example.com"]
    assert len(entry["events"]) == 1
    assert entry["events"][0]["quote"] == REAL_MCLEOD_QUOTE


def test_second_occurrence_escalates_to_mission_board(tmp_path, monkeypatch):
    _patch_state_paths(tmp_path, monkeypatch)
    board_path = tmp_path / "mission_board.json"
    board_path.write_text(json.dumps({"missions": []}))
    monkeypatch.setattr(mbs, "BOARD_PATH", board_path)
    monkeypatch.setattr(mbs, "LOCK_PATH", tmp_path / "mission_board.lock")

    intel._track_self_sufficiency_signal(
        "Erik & Melissa McLeod", "mcleod@example.com", REAL_MCLEOD_QUOTE,
        {"id": "msg1", "headers": {"Date": "2026-01-28", "Subject": "Re: transfers"}},
    )
    mission_id = intel._track_self_sufficiency_signal(
        "Erik & Melissa McLeod", "mcleod@example.com",
        "We found a better hotel ourselves via YouTube reviews",
        {"id": "msg2", "headers": {"Date": "2026-02-14", "Subject": "Re: Venice hotel"}},
    )

    assert mission_id is not None, "a second occurrence for the same client must escalate"
    board = json.loads(board_path.read_text())
    assert any("McLeod" in m["title"] and "self-sufficiency" in m["title"] for m in board["missions"])


def test_repeated_escalation_does_not_file_duplicate_ticket(tmp_path, monkeypatch):
    _patch_state_paths(tmp_path, monkeypatch)
    board_path = tmp_path / "mission_board.json"
    board_path.write_text(json.dumps({"missions": []}))
    monkeypatch.setattr(mbs, "BOARD_PATH", board_path)
    monkeypatch.setattr(mbs, "LOCK_PATH", tmp_path / "mission_board.lock")

    for quote in [REAL_MCLEOD_QUOTE, "We can compare train websites ourselves", "We booked a replacement tour ourselves"]:
        intel._track_self_sufficiency_signal(
            "Erik & Melissa McLeod", "mcleod@example.com", quote,
            {"id": "msg", "headers": {"Date": "2026-02-01", "Subject": "x"}},
        )

    board = json.loads(board_path.read_text())
    matching = [m for m in board["missions"] if "McLeod" in m["title"] and "self-sufficiency" in m["title"]]
    assert len(matching) == 1, "the dedup-safe add_mission path must not file a second ticket for the same client"


def test_self_sufficiency_prompt_rule_distinguishes_from_frustration():
    assert "self_sufficiency_signal" in intel.CLIENT_SYSTEM_PROMPT
    assert "DIFFERENT from sentiment=frustrated" in intel.CLIENT_SYSTEM_PROMPT
