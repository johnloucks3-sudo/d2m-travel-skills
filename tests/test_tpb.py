#!/usr/bin/env python3
"""
Tests for Target Prosecution Board (tpb.py)
Run: python3 -m pytest tests/test_tpb.py -v
"""

import json
import sys
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock
import pytest

# Add OpsCenter to path so we can import tpb
sys.path.insert(0, str(Path(__file__).parent.parent / "OpsCenter"))
import tpb


def make_state_file(tmp_path: Path, content: dict) -> Path:
    """Write a state JSON to a temp file and return its path."""
    p = tmp_path / "tpb_state.json"
    p.write_text(json.dumps(content))
    return p


def fresh_state() -> dict:
    return {
        "last_id": 0,
        "wip_cap": 5,
        "targets": [],
        "done_today": [],
        "last_updated": "2026-06-22T12:00:00"
    }


@pytest.fixture(autouse=True)
def patch_state_file(tmp_path, monkeypatch):
    """Redirect STATE_FILE to a temp location for every test."""
    fake_path = tmp_path / "tpb_state.json"
    monkeypatch.setattr(tpb, "STATE_FILE", fake_path)
    return fake_path


# ─── Test 1: Empty state initializes correctly ─────────────────────────────

def test_empty_state_initializes(tmp_path):
    # STATE_FILE does not exist — load_state should create it
    state = tpb.load_state()
    assert state["last_id"] == 0
    assert state["wip_cap"] == 5
    assert state["targets"] == []
    assert state["done_today"] == []
    assert tpb.STATE_FILE.exists()


# ─── Test 2: add with space below cap → ENGAGED ────────────────────────────

def test_add_below_cap_creates_engaged(tmp_path, capsys):
    state = fresh_state()
    tpb.save_state(state)
    state = tpb.load_state()

    tpb.cmd_add(state, "First target")

    state = tpb.load_state()
    assert len(state["targets"]) == 1
    assert state["targets"][0]["status"] == tpb.ENGAGED
    assert state["targets"][0]["id"] == "T-01"
    assert state["targets"][0]["name"] == "First target"

    out = capsys.readouterr().out
    assert "ENGAGED" in out
    assert "T-01" in out


# ─── Test 3: add at cap → QUEUED with warning ──────────────────────────────

def test_add_at_cap_creates_queued(tmp_path, capsys):
    state = fresh_state()
    state["wip_cap"] = 2
    state["last_id"] = 2
    state["targets"] = [
        {"id": "T-01", "name": "A", "status": tpb.ENGAGED,
         "opened_at": "2026-06-22T12:00:00", "completed_at": None, "notes": ""},
        {"id": "T-02", "name": "B", "status": tpb.ENGAGED,
         "opened_at": "2026-06-22T12:00:00", "completed_at": None, "notes": ""},
    ]
    tpb.save_state(state)
    state = tpb.load_state()

    tpb.cmd_add(state, "Overflow target")

    state = tpb.load_state()
    new_target = next(t for t in state["targets"] if t["name"] == "Overflow target")
    assert new_target["status"] == tpb.QUEUED

    out = capsys.readouterr().out
    assert "WIP cap reached" in out
    assert "QUEUED" in out


# ─── Test 4: complete moves target name to done_today ──────────────────────

def test_complete_moves_to_done_today(tmp_path, capsys):
    state = fresh_state()
    state["last_id"] = 1
    state["targets"] = [
        {"id": "T-01", "name": "My target", "status": tpb.ENGAGED,
         "opened_at": "2026-06-22T12:00:00", "completed_at": None, "notes": ""},
    ]
    tpb.save_state(state)
    state = tpb.load_state()

    tpb.cmd_complete(state, "T-01")

    state = tpb.load_state()
    assert len(state["targets"]) == 0
    assert "My target" in state["done_today"]

    out = capsys.readouterr().out
    assert "COMPLETE" in out


# ─── Test 5: complete on non-existent ID → error ───────────────────────────

def test_complete_nonexistent_id_errors(tmp_path):
    state = fresh_state()
    tpb.save_state(state)
    state = tpb.load_state()

    with pytest.raises(SystemExit) as exc_info:
        tpb.cmd_complete(state, "T-99")
    assert exc_info.value.code == 1


# ─── Test 6: park sets status to PARKED ────────────────────────────────────

def test_park_sets_status_parked(tmp_path, capsys):
    state = fresh_state()
    state["last_id"] = 1
    state["targets"] = [
        {"id": "T-01", "name": "Target to park", "status": tpb.ENGAGED,
         "opened_at": "2026-06-22T12:00:00", "completed_at": None, "notes": ""},
    ]
    tpb.save_state(state)
    state = tpb.load_state()

    tpb.cmd_park(state, "T-01")

    state = tpb.load_state()
    assert state["targets"][0]["status"] == tpb.PARKED

    out = capsys.readouterr().out
    assert "PARKED" in out


# ─── Test 7: engage moves QUEUED/PARKED → ENGAGED ──────────────────────────

def test_engage_queued_target(tmp_path, capsys):
    state = fresh_state()
    state["last_id"] = 1
    state["targets"] = [
        {"id": "T-01", "name": "Queued target", "status": tpb.QUEUED,
         "opened_at": "2026-06-22T12:00:00", "completed_at": None, "notes": ""},
    ]
    tpb.save_state(state)
    state = tpb.load_state()

    tpb.cmd_engage(state, "T-01")

    state = tpb.load_state()
    assert state["targets"][0]["status"] == tpb.ENGAGED

    out = capsys.readouterr().out
    assert "ENGAGED" in out


def test_engage_parked_target(tmp_path, capsys):
    state = fresh_state()
    state["last_id"] = 1
    state["targets"] = [
        {"id": "T-01", "name": "Parked target", "status": tpb.PARKED,
         "opened_at": "2026-06-22T12:00:00", "completed_at": None, "notes": ""},
    ]
    tpb.save_state(state)
    state = tpb.load_state()

    tpb.cmd_engage(state, "T-01")

    state = tpb.load_state()
    assert state["targets"][0]["status"] == tpb.ENGAGED


# ─── Test 8: engage when at WIP cap → error ────────────────────────────────

def test_engage_at_cap_errors(tmp_path):
    state = fresh_state()
    state["wip_cap"] = 1
    state["last_id"] = 2
    state["targets"] = [
        {"id": "T-01", "name": "Engaged one", "status": tpb.ENGAGED,
         "opened_at": "2026-06-22T12:00:00", "completed_at": None, "notes": ""},
        {"id": "T-02", "name": "Queued one", "status": tpb.QUEUED,
         "opened_at": "2026-06-22T12:00:00", "completed_at": None, "notes": ""},
    ]
    tpb.save_state(state)
    state = tpb.load_state()

    with pytest.raises(SystemExit) as exc_info:
        tpb.cmd_engage(state, "T-02")
    assert exc_info.value.code == 1


# ─── Test 9: time-in-flight formatting ─────────────────────────────────────

def test_format_elapsed_zero():
    # opened_at = right now → should be +0h00m
    now_iso = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    result = tpb._format_elapsed(now_iso)
    assert result.startswith("+0h")


def test_format_elapsed_5_minutes():
    five_ago = (datetime.now() - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%S")
    result = tpb._format_elapsed(five_ago)
    assert result == "+0h05m"


def test_format_elapsed_2h30m():
    t = (datetime.now() - timedelta(hours=2, minutes=30)).strftime("%Y-%m-%dT%H:%M:%S")
    result = tpb._format_elapsed(t)
    assert result == "+2h30m"


def test_format_elapsed_bad_input():
    result = tpb._format_elapsed("not-a-date")
    assert result == "+?h??m"


# ─── Test 10: status output includes ENGAGED count / cap ───────────────────

def test_status_shows_wip_count(tmp_path, capsys):
    state = fresh_state()
    state["wip_cap"] = 5
    state["last_id"] = 2
    state["targets"] = [
        {"id": "T-01", "name": "Alpha", "status": tpb.ENGAGED,
         "opened_at": "2026-06-22T12:00:00", "completed_at": None, "notes": ""},
        {"id": "T-02", "name": "Beta", "status": tpb.QUEUED,
         "opened_at": "2026-06-22T12:00:00", "completed_at": None, "notes": ""},
    ]
    tpb.save_state(state)
    state = tpb.load_state()

    tpb.cmd_status(state)

    out = capsys.readouterr().out
    assert "WIP: 1/5" in out
    assert "ENGAGED" in out
    assert "QUEUED" in out
    assert "T-01" in out
    assert "T-02" in out


def test_status_shows_done_today(tmp_path, capsys):
    state = fresh_state()
    state["done_today"] = ["Finished thing 1", "Finished thing 2"]
    tpb.save_state(state)
    state = tpb.load_state()

    tpb.cmd_status(state)

    out = capsys.readouterr().out
    assert "Done today" in out
    assert "Finished thing 1" in out


# ─── Test 11: queue command adds as QUEUED ─────────────────────────────────

def test_queue_command_adds_queued(tmp_path, capsys):
    state = fresh_state()
    tpb.save_state(state)
    state = tpb.load_state()

    tpb.cmd_queue(state, "Next up target")

    state = tpb.load_state()
    assert len(state["targets"]) == 1
    assert state["targets"][0]["status"] == tpb.QUEUED
    assert state["targets"][0]["name"] == "Next up target"

    out = capsys.readouterr().out
    assert "QUEUED" in out


# ─── Test 12: reset-today clears done_today ────────────────────────────────

def test_reset_today_clears_log(tmp_path, capsys):
    state = fresh_state()
    state["done_today"] = ["item 1", "item 2", "item 3"]
    tpb.save_state(state)
    state = tpb.load_state()

    tpb.cmd_reset_today(state)

    state = tpb.load_state()
    assert state["done_today"] == []

    out = capsys.readouterr().out
    assert "3" in out  # "3 entries removed"


# ─── Test 13: ID auto-increment ────────────────────────────────────────────

def test_id_autoincrement(tmp_path, capsys):
    state = fresh_state()
    tpb.save_state(state)
    state = tpb.load_state()

    tpb.cmd_add(state, "First")
    state = tpb.load_state()
    tpb.cmd_add(state, "Second")
    state = tpb.load_state()
    tpb.cmd_add(state, "Third")
    state = tpb.load_state()

    ids = [t["id"] for t in state["targets"]]
    assert "T-01" in ids
    assert "T-02" in ids
    assert "T-03" in ids
