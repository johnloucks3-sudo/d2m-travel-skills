"""Tests for core/oversight/canary.py — the verifier of the verifier.

A canary that has only ever passed proves nothing. The tests that matter here
are the MUTATION tests: deliberately break each oversight guarantee and assert
the canary screams. If those ever go green while the layer is broken, this
whole subsystem is decorative — which is exactly the condition (six shipped,
zero callers, digest green) that caused it to be built.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from core.oversight import canary, mast, reaper, spans


@pytest.fixture()
def cdb(tmp_path):
    return tmp_path / "canary.db"


@pytest.fixture(autouse=True)
def isolate_state(tmp_path, monkeypatch):
    """Never touch the real canary state file from a test run."""
    monkeypatch.setattr(canary, "CANARY_STATE", tmp_path / "canary_state.json")


# ------------------------------------------------------------ happy path

def test_canary_passes_on_healthy_layer(cdb, tmp_path):
    rep = canary.run(db_path=cdb, page_on_failure=False, tmp_dir=tmp_path / "a")
    assert rep["healthy"] is True
    assert rep["failed"] == 0
    assert rep["passed"] == rep["scenarios_run"] == len(canary.SCENARIOS)


def test_canary_covers_every_declared_scenario(cdb, tmp_path):
    rep = canary.run(db_path=cdb, page_on_failure=False, tmp_dir=tmp_path / "b")
    assert {r["scenario"] for r in rep["results"]} == set(canary.SCENARIOS)


# --------------------------------------------------------- MUTATION TESTS
# Each one breaks a real guarantee and asserts the canary catches it.

def test_canary_catches_dead_reaper(cdb, tmp_path, monkeypatch):
    """The 2026-07-29 condition: detection code exists but never fires."""
    monkeypatch.setattr(reaper, "reap_spans", lambda **kw: [])
    rep = canary.run(db_path=cdb, page_on_failure=False, tmp_dir=tmp_path / "c")
    assert rep["healthy"] is False
    assert any("lost-task detection is DEAD" in f for f in rep["failures"])


def test_canary_catches_self_verification_loophole(cdb, tmp_path, monkeypatch):
    """If CC can rubber-stamp itself, cross-engine doctrine is decorative."""
    monkeypatch.setattr(spans, "is_independently_verified", lambda s: True)
    rep = canary.run(db_path=cdb, page_on_failure=False, tmp_dir=tmp_path / "d")
    assert rep["healthy"] is False
    assert any("decorative" in f for f in rep["failures"])


def test_canary_catches_taxonomy_corruption(cdb, tmp_path, monkeypatch):
    monkeypatch.setattr(mast, "is_valid", lambda c: True)
    rep = canary.run(db_path=cdb, page_on_failure=False, tmp_dir=tmp_path / "e")
    assert rep["healthy"] is False
    assert any("no longer be trusted" in f for f in rep["failures"])


def test_canary_catches_misclassified_silent_success(cdb, tmp_path, monkeypatch):
    """Calling completed work LOST would make the Wing re-run finished work
    and pay for it twice."""
    monkeypatch.setattr(reaper, "classify_stale_span",
                        lambda span: ("LOST", "FM-3.1", "forced"))
    rep = canary.run(db_path=cdb, page_on_failure=False, tmp_dir=tmp_path / "f")
    assert rep["healthy"] is False
    assert any("re-run finished work" in f for f in rep["failures"])


def test_canary_catches_false_positive_reaper(cdb, tmp_path, monkeypatch):
    """A reaper that kills healthy work is worse than one that misses failures."""
    monkeypatch.setattr(spans, "stale",
                        lambda **kw: [dict(r) for r in spans.live(db_path=kw.get("db_path"))])
    rep = canary.run(db_path=cdb, page_on_failure=False, tmp_dir=tmp_path / "g")
    assert rep["healthy"] is False
    assert any("HEALTHY in-flight span" in f or "false positive" in f.lower()
               for f in rep["failures"])


def test_canary_catches_broken_page_lane(cdb, tmp_path, monkeypatch):
    """Detection that cannot reach the Commander is not oversight."""
    import builtins
    real_import = builtins.__import__

    def fake(name, *a, **k):
        if name == "core.comms.wing_page":
            raise ImportError("simulated broken paging lane")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", fake)
    rep = canary.run(db_path=cdb, page_on_failure=False, tmp_dir=tmp_path / "h")
    assert rep["healthy"] is False
    assert any("never reach the Commander" in f for f in rep["failures"])


def test_canary_never_raises_even_when_everything_breaks(cdb, tmp_path, monkeypatch):
    """The canary must report blindness, not become another silent failure."""
    monkeypatch.setattr(reaper, "reap_spans",
                        lambda **kw: (_ for _ in ()).throw(RuntimeError("boom")))
    rep = canary.run(db_path=cdb, page_on_failure=False, tmp_dir=tmp_path / "i")
    assert rep["healthy"] is False
    assert any("unexpected" in f for f in rep["failures"])


# -------------------------------------------------------------- isolation

def test_canary_never_writes_to_production_ledger(cdb, tmp_path, monkeypatch):
    """Synthetic failures must not inflate real seat scorecards or cost."""
    prod = tmp_path / "PRODUCTION.db"
    spans.init_db(prod)
    canary.run(db_path=cdb, page_on_failure=False, tmp_dir=tmp_path / "j")
    with spans._db(prod) as conn:
        n = conn.execute("SELECT COUNT(*) c FROM spans").fetchone()["c"]
    assert n == 0


def test_canary_db_is_reset_each_run_not_accumulated(cdb, tmp_path):
    canary.run(db_path=cdb, page_on_failure=False, tmp_dir=tmp_path / "k")
    with spans._db(cdb) as conn:
        first = conn.execute("SELECT COUNT(*) c FROM spans").fetchone()["c"]
    canary.run(db_path=cdb, page_on_failure=False, tmp_dir=tmp_path / "l")
    with spans._db(cdb) as conn:
        second = conn.execute("SELECT COUNT(*) c FROM spans").fetchone()["c"]
    assert first == second, "canary state accumulated across runs"


# ----------------------------------------------------------- status report

def test_status_reports_never_run(monkeypatch, tmp_path):
    monkeypatch.setattr(canary, "CANARY_STATE", tmp_path / "absent.json")
    ok, msg = canary.canary_status()
    assert ok is False and "NEVER run" in msg


def test_status_reports_failing_distinctly_from_never_run(monkeypatch, tmp_path):
    p = tmp_path / "s.json"
    p.write_text(json.dumps({"ts": datetime.now(timezone.utc).isoformat(),
                             "healthy": False, "failed": 2, "passed": 4,
                             "scenarios_run": 6,
                             "failures": ["lost: detection is DEAD"]}))
    monkeypatch.setattr(canary, "CANARY_STATE", p)
    ok, msg = canary.canary_status()
    assert ok is False and "CANARY FAILING" in msg


def test_status_reports_stale_pass_as_unverified(monkeypatch, tmp_path):
    """A pass from three days ago does not vouch for today."""
    p = tmp_path / "s.json"
    old = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
    p.write_text(json.dumps({"ts": old, "healthy": True, "passed": 6,
                             "scenarios_run": 6, "failures": []}))
    monkeypatch.setattr(canary, "CANARY_STATE", p)
    ok, msg = canary.canary_status(max_age_minutes=1440)
    assert ok is False and "STALE" in msg


def test_status_reports_healthy_when_recent_pass(monkeypatch, tmp_path):
    p = tmp_path / "s.json"
    p.write_text(json.dumps({"ts": datetime.now(timezone.utc).isoformat(),
                             "healthy": True, "passed": 6, "scenarios_run": 6,
                             "failures": []}))
    monkeypatch.setattr(canary, "CANARY_STATE", p)
    ok, msg = canary.canary_status()
    assert ok is True and "healthy" in msg
