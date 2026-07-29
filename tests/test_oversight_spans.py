"""Tests for core/oversight — span ledger + MAST taxonomy.

Written alongside the code, not after, because the audit's finding was that
the untested modules were exactly the dead ones. A test here is also a
tripwire: if these ever pass while nothing calls the module in production,
that is MAST code WING-2 (orphaned capability) and the weekly appraisal
is supposed to catch it.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from core.oversight import mast, spans


@pytest.fixture()
def db(tmp_path):
    p = tmp_path / "spans.db"
    spans.init_db(p)
    return p


# ------------------------------------------------------------------ MAST

def test_mast_has_exactly_14_published_modes():
    """The paper defines 14 modes in 3 categories. If this count drifts,
    someone has quietly edited a validated taxonomy."""
    assert len(mast.MODES) == 14
    cats = {m.category for m in mast.MODES.values()}
    assert len(cats) == 3


def test_mast_category_counts_match_paper():
    # Appendix A: FC1 five modes, FC2 six modes, FC3 three modes.
    by_cat: dict[str, int] = {}
    for m in mast.MODES.values():
        by_cat[m.category] = by_cat.get(m.category, 0) + 1
    assert by_cat[mast.FC1] == 5
    assert by_cat[mast.FC2] == 6
    assert by_cat[mast.FC3] == 3


def test_wing_extensions_are_separable_from_mast():
    """Our extensions must never contaminate the published taxonomy, or our
    numbers stop being comparable to the paper's."""
    assert set(mast.MODES) & set(mast.WING_MODES) == set()
    assert all(c.startswith("WING-") for c in mast.WING_MODES)


def test_invalid_code_is_rejected():
    assert not mast.is_valid("FM-9.9")
    assert mast.is_valid("FM-3.1")
    assert mast.is_valid("WING-1")


@pytest.mark.parametrize("facts,expected", [
    # vanished mid-flight
    (dict(declared_done=False, artifacts_exist=False, acceptance_criteria_met=None,
          heartbeat_stale=True, reported_result=False, verification_ran=False),
     "FM-3.1"),
    # work on disk, never reported — the 2026-07-29 10:08 live incident
    (dict(declared_done=False, artifacts_exist=True, acceptance_criteria_met=None,
          heartbeat_stale=False, reported_result=False, verification_ran=False),
     "WING-1"),
    # claimed done with nothing to show — "false success"
    (dict(declared_done=True, artifacts_exist=False, acceptance_criteria_met=None,
          heartbeat_stale=False, reported_result=True, verification_ran=False),
     "FM-1.1"),
    # done, artifacts exist, nobody checked them
    (dict(declared_done=True, artifacts_exist=True, acceptance_criteria_met=None,
          heartbeat_stale=False, reported_result=True, verification_ran=False),
     "FM-3.2"),
    # checked it, passed it, criteria demonstrably unmet
    (dict(declared_done=True, artifacts_exist=True, acceptance_criteria_met=False,
          heartbeat_stale=False, reported_result=True, verification_ran=True),
     "FM-3.3"),
])
def test_mechanical_classification_from_observed_facts(facts, expected):
    assert mast.classify_mechanically(**facts) == expected


def test_mechanical_classifier_returns_none_when_undetermined():
    """Must decline rather than guess — a model may then PROPOSE a code, but
    the classifier itself never invents one."""
    assert mast.classify_mechanically(
        declared_done=True, artifacts_exist=True, acceptance_criteria_met=True,
        heartbeat_stale=False, reported_result=True, verification_ran=True) is None


def test_oversight_failures_are_flagged_separately():
    assert mast.is_oversight_failure("FM-3.2")
    assert mast.is_oversight_failure("WING-2")
    assert not mast.is_oversight_failure("FM-2.3")


# ----------------------------------------------------------------- spans

def test_open_span_returns_ids_and_persists(db):
    row = spans.open_span(seat="CC", task_type="research", db_path=db)
    assert row["span_id"].startswith("sp_")
    assert row["trace_id"].startswith("tr_")
    assert row["status"] == "RUNNING"
    fetched = spans.get_span(row["span_id"], db_path=db)
    assert fetched["seat"] == "CC"


def test_parent_child_makes_phases_visible(db):
    parent = spans.open_span(seat="CC", phase="dispatch", db_path=db)
    child = spans.open_span(seat="AG", phase="work",
                            trace_id=parent["trace_id"],
                            parent_span_id=parent["span_id"], db_path=db)
    lineage = spans.trace(parent["trace_id"], db_path=db)
    assert len(lineage) == 2
    assert child["parent_span_id"] == parent["span_id"]


def test_close_span_computes_elapsed_and_is_terminal(db):
    row = spans.open_span(seat="OC", db_path=db)
    closed = spans.close_span(row["span_id"], status="OK",
                              verified_by="AG", ground_truth_ref="/tmp/x",
                              db_path=db)
    assert closed["status"] == "OK"
    assert closed["elapsed_s"] is not None and closed["elapsed_s"] >= 0
    assert closed["ended_at"]


def test_close_span_on_missing_id_returns_none(db):
    assert spans.close_span("sp_nope", status="OK", db_path=db) is None


def test_invalid_mast_code_is_demoted_not_finalized(db):
    """A bad code must never land in the trusted column."""
    row = spans.open_span(seat="AG", db_path=db)
    closed = spans.close_span(row["span_id"], status="FAILED",
                              mast_code="TOTALLY-MADE-UP", db_path=db)
    assert closed["mast_code"] is None
    assert closed["proposed_mast_code"] == "TOTALLY-MADE-UP"


def test_valid_mast_code_is_kept(db):
    row = spans.open_span(seat="AG", db_path=db)
    closed = spans.close_span(row["span_id"], status="FAILED",
                              mast_code="FM-3.1", db_path=db)
    assert closed["mast_code"] == "FM-3.1"


def test_self_verification_never_counts(db):
    """The whole point of cross-engine checking: CC grading CC is not
    verification, it is self-preference bias."""
    row = spans.open_span(seat="CC", db_path=db)
    closed = spans.close_span(row["span_id"], status="OK", verified_by="CC",
                              db_path=db)
    assert not spans.is_independently_verified(closed)


def test_cross_seat_verification_counts(db):
    row = spans.open_span(seat="CC", db_path=db)
    closed = spans.close_span(row["span_id"], status="OK", verified_by="AG",
                              db_path=db)
    assert spans.is_independently_verified(closed)


def test_unverified_closures_surface_green_on_silence(db):
    a = spans.open_span(seat="CC", db_path=db)
    spans.close_span(a["span_id"], status="OK", db_path=db)          # nobody checked
    b = spans.open_span(seat="OC", db_path=db)
    spans.close_span(b["span_id"], status="OK", verified_by="CC", db_path=db)
    unver = spans.unverified_closures(db_path=db)
    ids = {r["span_id"] for r in unver}
    assert a["span_id"] in ids
    assert b["span_id"] not in ids


def test_heartbeat_renews_lease(db):
    row = spans.open_span(seat="OC", lease_seconds=60, db_path=db)
    before = spans.get_span(row["span_id"], db_path=db)["lease_expires_at"]
    assert spans.heartbeat(row["span_id"], lease_seconds=3600, db_path=db)
    after = spans.get_span(row["span_id"], db_path=db)["lease_expires_at"]
    assert after > before


def test_stale_detects_expired_lease(db):
    row = spans.open_span(seat="AG", lease_seconds=1, db_path=db)
    future = datetime.now(timezone.utc) + timedelta(seconds=120)
    found = spans.stale(db_path=db, now=future)
    assert row["span_id"] in {r["span_id"] for r in found}


def test_stale_ignores_closed_spans(db):
    row = spans.open_span(seat="AG", lease_seconds=1, db_path=db)
    spans.close_span(row["span_id"], status="OK", db_path=db)
    future = datetime.now(timezone.utc) + timedelta(seconds=120)
    assert row["span_id"] not in {r["span_id"] for r in spans.stale(db_path=db, now=future)}


def test_heartbeat_on_closed_span_does_not_resurrect(db):
    row = spans.open_span(seat="OC", db_path=db)
    spans.close_span(row["span_id"], status="OK", db_path=db)
    spans.heartbeat(row["span_id"], db_path=db)
    assert spans.get_span(row["span_id"], db_path=db)["status"] == "OK"


def test_artifacts_accumulate_without_duplicates(db):
    row = spans.open_span(seat="CC", db_path=db)
    spans.add_artifact(row["span_id"], "/a.md", db_path=db)
    spans.add_artifact(row["span_id"], "/a.md", db_path=db)
    spans.add_artifact(row["span_id"], "/b.md", db_path=db)
    closed = spans.close_span(row["span_id"], status="OK",
                              artifact_refs=["/c.md", "/a.md"], db_path=db)
    refs = json.loads(closed["artifact_refs"])
    assert refs.count("/a.md") == 1
    assert set(refs) == {"/a.md", "/b.md", "/c.md"}


def test_todo_roundtrips_for_live_progress(db):
    todo = [{"text": "read audit", "status": "completed"},
            {"text": "write plan", "status": "in_progress"}]
    row = spans.open_span(seat="CC", todo=todo, db_path=db)
    got = json.loads(spans.get_span(row["span_id"], db_path=db)["todo"])
    assert got == todo


def test_live_returns_only_running(db):
    a = spans.open_span(seat="CC", db_path=db)
    b = spans.open_span(seat="OC", db_path=db)
    spans.close_span(b["span_id"], status="OK", db_path=db)
    ids = {r["span_id"] for r in spans.live(db_path=db)}
    assert ids == {a["span_id"]}


def test_by_ticket_joins_across_seats(db):
    """The join the audit said nothing performs: one ticket, many seats."""
    t = spans.new_trace_id()
    spans.open_span(seat="CC", ticket_id="MISSION-42", trace_id=t, db_path=db)
    spans.open_span(seat="AG", ticket_id="MISSION-42", trace_id=t, db_path=db)
    spans.open_span(seat="OC", ticket_id="MISSION-99", db_path=db)
    rows = spans.by_ticket("MISSION-42", db_path=db)
    assert len(rows) == 2
    assert {r["seat"] for r in rows} == {"CC", "AG"}


def test_writes_never_raise_on_bad_db_path(tmp_path):
    """Telemetry must never break real work — the contract inherited from
    delegation_outcomes.record_outcome()."""
    bad = tmp_path / "nonexistent-dir" / "x" / "spans.db"
    bad.parent.mkdir(parents=True)
    bad.parent.chmod(0o400)  # unwritable
    try:
        row = spans.open_span(seat="CC", db_path=bad)
        assert row["span_id"]  # caller still gets usable ids
        assert spans.heartbeat(row["span_id"], db_path=bad) is False
    finally:
        bad.parent.chmod(0o700)


def test_status_vocabulary_covers_commanders_named_cases():
    """The Commander named lost taskings, unaccomplished exits, and successes
    as distinct things. They must be distinct statuses, not one bucket."""
    for s in ("LOST", "ABANDONED", "SILENT_SUCCESS", "OK", "FAILED", "BLOCKED"):
        assert s in spans.STATUSES
