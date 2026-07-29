"""Tests for core/oversight/reaper.py — lost/abandoned/silent-success detection.

The behaviour under test is the one the old detector could never exercise:
`delegation_outcomes.outstanding()` was correct but fed by a function nobody
called, so it had no reachable code path at all. These tests exist to prove the
new path is reachable from state that exists regardless of what anyone
remembered to call.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from core.oversight import mast, reaper, spans


@pytest.fixture()
def db(tmp_path):
    p = tmp_path / "spans.db"
    spans.init_db(p)
    return p


def _future(minutes=120):
    return datetime.now(timezone.utc) + timedelta(minutes=minutes)


# ------------------------------------------- the three cases, by ground truth

def test_lost_when_no_heartbeat_and_no_artifacts(db):
    s = spans.open_span(seat="AG", lease_seconds=1, db_path=db)
    out = reaper.reap_spans(db_path=db, now=_future())
    assert len(out) == 1
    assert out[0]["status"] == "LOST"
    assert out[0]["mast_code"] == "FM-3.1"


def test_silent_success_when_artifacts_exist_but_never_reported(db, tmp_path):
    """The live 2026-07-29 10:08 incident: 23KB deliverable written, agent went
    idle without reporting. Must NOT be recorded as a loss."""
    art = tmp_path / "report.md"
    art.write_text("real deliverable content")
    s = spans.open_span(seat="SUBAGENT", lease_seconds=1, db_path=db)
    spans.add_artifact(s["span_id"], str(art), db_path=db)
    out = reaper.reap_spans(db_path=db, now=_future())
    assert out[0]["status"] == "SILENT_SUCCESS"
    assert out[0]["mast_code"] == "WING-1"
    assert "do not re-run" in out[0]["detail"]


def test_abandoned_when_partial_output_and_a_report_exists(db, tmp_path):
    art = tmp_path / "partial.md"
    art.write_text("half done")
    s = spans.open_span(seat="OC", lease_seconds=1, db_path=db)
    spans.add_artifact(s["span_id"], str(art), db_path=db)
    # a reported detail distinguishes "walked away having said something"
    spans.close_span(s["span_id"], status="RUNNING", detail="hit an error",
                     db_path=db)
    out = reaper.reap_spans(db_path=db, now=_future())
    assert out[0]["status"] == "ABANDONED"


def test_empty_artifact_file_is_not_evidence_of_success(db, tmp_path):
    """A zero-byte file is not a deliverable. Ground truth means real bytes."""
    art = tmp_path / "empty.md"
    art.write_text("")
    s = spans.open_span(seat="AG", lease_seconds=1, db_path=db)
    spans.add_artifact(s["span_id"], str(art), db_path=db)
    out = reaper.reap_spans(db_path=db, now=_future())
    assert out[0]["status"] == "LOST"


def test_unverifiable_refs_do_not_count_as_present(db):
    """A URL or commit hash cannot be checked from here, so it must not read as
    verified — that would be exactly the false-success failure we exist to stop."""
    s = spans.open_span(seat="AG", lease_seconds=1, db_path=db)
    spans.add_artifact(s["span_id"], "https://example.com/i-promise", db_path=db)
    spans.add_artifact(s["span_id"], "abc123commit", db_path=db)
    out = reaper.reap_spans(db_path=db, now=_future())
    assert out[0]["status"] == "LOST"


def test_healthy_running_span_is_untouched(db):
    s = spans.open_span(seat="CC", lease_seconds=3600, db_path=db)
    assert reaper.reap_spans(db_path=db) == []
    assert spans.get_span(s["span_id"], db_path=db)["status"] == "RUNNING"


def test_dry_run_reports_without_mutating(db):
    s = spans.open_span(seat="AG", lease_seconds=1, db_path=db)
    out = reaper.reap_spans(db_path=db, dry_run=True, now=_future())
    assert len(out) == 1
    assert spans.get_span(s["span_id"], db_path=db)["status"] == "RUNNING"


def test_reap_is_idempotent(db):
    spans.open_span(seat="AG", lease_seconds=1, db_path=db)
    first = reaper.reap_spans(db_path=db, now=_future())
    second = reaper.reap_spans(db_path=db, now=_future())
    assert len(first) == 1
    assert second == []


# ------------------------------------------------------ mission board intake

def _board(tmp_path, missions):
    p = tmp_path / "mission_board.json"
    p.write_text(json.dumps({"missions": missions}))
    return p


def test_stale_missions_read_board_directly_not_a_dispatch_helper(tmp_path):
    """The whole point: intake must not depend on anyone calling dispatch_to_oc."""
    old = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
    new = datetime.now(timezone.utc).isoformat()
    p = _board(tmp_path, [
        {"id": "M-1", "status": "in_progress", "updated_at": old, "title": "stale"},
        {"id": "M-2", "status": "in_progress", "updated_at": new, "title": "fresh"},
        {"id": "M-3", "status": "completed", "updated_at": old, "title": "done"},
    ])
    out = reaper.stale_missions(board_path=p)
    assert [r["mission_id"] for r in out] == ["M-1"]


def test_stale_missions_sorted_worst_first(tmp_path):
    d = datetime.now(timezone.utc)
    p = _board(tmp_path, [
        {"id": "M-A", "status": "active", "updated_at": (d - timedelta(days=3)).isoformat()},
        {"id": "M-B", "status": "active", "updated_at": (d - timedelta(days=9)).isoformat()},
    ])
    out = reaper.stale_missions(board_path=p)
    assert [r["mission_id"] for r in out] == ["M-B", "M-A"]


def test_unparseable_timestamp_is_skipped_not_crashed(tmp_path):
    p = _board(tmp_path, [{"id": "M-X", "status": "active", "updated_at": "not-a-date"}])
    assert reaper.stale_missions(board_path=p) == []


def test_missing_board_returns_empty_and_does_not_raise(tmp_path):
    assert reaper.stale_missions(board_path=tmp_path / "nope.json") == []


# ------------------------------------------------ who watches the watchmen

def test_reaper_health_reports_never_run(monkeypatch, tmp_path):
    monkeypatch.setattr(reaper, "REAPER_HEARTBEAT", tmp_path / "hb.json")
    ok, msg = reaper.reaper_is_healthy()
    assert ok is False
    assert "NEVER" in msg


def test_reaper_health_detects_stale_oversight(monkeypatch, tmp_path):
    hb = tmp_path / "hb.json"
    old = (datetime.now(timezone.utc) - timedelta(hours=6)).isoformat()
    hb.write_text(json.dumps({"last_run": old}))
    monkeypatch.setattr(reaper, "REAPER_HEARTBEAT", hb)
    ok, msg = reaper.reaper_is_healthy(max_age_minutes=90)
    assert ok is False
    assert "OVERSIGHT DOWN" in msg


def test_reaper_health_passes_when_recent(monkeypatch, tmp_path):
    hb = tmp_path / "hb.json"
    hb.write_text(json.dumps({"last_run": datetime.now(timezone.utc).isoformat()}))
    monkeypatch.setattr(reaper, "REAPER_HEARTBEAT", hb)
    ok, _ = reaper.reaper_is_healthy()
    assert ok is True


# ------------------------------------------------------------ alert policy

def test_silent_success_does_not_page(db, tmp_path, monkeypatch):
    """Alert fatigue is the main way oversight systems die. Recoverable work
    sitting on disk goes in the digest, not to the Commander's phone."""
    paged = []
    import core.staffing.delegation_outcomes as do
    monkeypatch.setattr(do, "page_commander",
                        lambda **kw: paged.append(kw) or True)
    art = tmp_path / "r.md"
    art.write_text("done")
    s = spans.open_span(seat="OC", lease_seconds=1, db_path=db)
    spans.add_artifact(s["span_id"], str(art), db_path=db)
    reaped = reaper.reap_spans(db_path=db, now=_future())
    reaper._page_if_needed(reaped, [], {})
    assert paged == []


def test_lost_work_does_page(db, monkeypatch):
    paged = []
    import core.staffing.delegation_outcomes as do
    monkeypatch.setattr(do, "page_commander",
                        lambda **kw: paged.append(kw) or True)
    spans.open_span(seat="AG", lease_seconds=1, ticket_id="T-9", db_path=db)
    reaped = reaper.reap_spans(db_path=db, now=_future())
    reaper._page_if_needed(reaped, [], {})
    assert len(paged) == 1
    assert "lost or abandoned" in paged[0]["problem"]
