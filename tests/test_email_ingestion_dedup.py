"""Regression test — email_ingestion_pipeline mission-board dedup.

Closes the 2026-07-16 hot-window finding: _create_mission_board_ticket()
appended a new P1 mission to the board with NO duplicate check, the same
class of gap fixed the same night in tcd/writeback.py and
generate_weekly_report.py. For inbound email the dedup key is the exact
Gmail message_id (title-based dedup would risk collapsing two distinct
client inquiries whose subjects share 3+ words).

Asserts: ingesting the SAME message_id twice files exactly one mission.
"""
import json
import importlib
from pathlib import Path

import pytest


@pytest.fixture
def pipeline(tmp_path, monkeypatch):
    mod = importlib.import_module("scripts.email_ingestion_pipeline")
    board = tmp_path / "mission_board.json"
    board.write_text(json.dumps({"missions": []}, indent=2))
    monkeypatch.setattr(mod, "MISSION_BOARD_PATH", board)
    monkeypatch.setattr(mod, "_circuit_breaker_run_count", 0, raising=False)
    return mod, board


def _ticket(msg_id, subject):
    return {
        "ts": "2026-07-16T00:00:00+00:00",
        "category": "client_inquiry",
        "message_id": msg_id,
        "from": "someone@example.com",
        "subject": subject,
        "action": "ROUTE_TO_MISSION_BOARD",
        "mission_title": f"Client inquiry: {subject[:60]}",
        "description": f"Inbound client email from someone@example.com — subject: {subject}",
    }


def test_same_message_id_files_one_ticket(pipeline):
    mod, board = pipeline
    mod._create_mission_board_ticket(_ticket("MSG-AAA", "A package is arriving"))
    mod._create_mission_board_ticket(_ticket("MSG-AAA", "A package is arriving"))
    missions = json.loads(board.read_text())["missions"]
    assert len(missions) == 1, f"expected 1 mission, got {len(missions)}"


def test_distinct_message_ids_both_filed(pipeline):
    """Guard against over-dedup: two genuinely different emails must both file,
    even if subjects share words (title-based dedup would have merged these)."""
    mod, board = pipeline
    mod._create_mission_board_ticket(_ticket("MSG-1", "Re: your trip to Lisbon"))
    mod._create_mission_board_ticket(_ticket("MSG-2", "Re: your trip to Rome"))
    missions = json.loads(board.read_text())["missions"]
    assert len(missions) == 2, f"expected 2 distinct missions, got {len(missions)}"
