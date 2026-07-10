"""Tests for scripts/centrav_session_warm.py's Hale Orchestrator logging.
Per docs/superpowers/specs/2026-07-09-self-healing-architecture-reverse-
engineered.md pattern — ledger-only, called after warm()'s own decision."""
from __future__ import annotations

import scripts.centrav_session_warm as warm_module
import core.ops.hale_orchestrator as ho_module


def test_log_warm_plan_met_on_success(tmp_path, monkeypatch):
    monkeypatch.setattr(ho_module, "HALE_DECISIONS", tmp_path / "decisions.md")
    warm_module._log_warm_plan(0)
    text = (tmp_path / "decisions.md").read_text()
    assert "session warmed + authenticated" in text
    assert "<!-- PLAN:CLOSE" in text
    assert "verdict=PASS" in text


def test_log_warm_plan_missed_on_dead_session(tmp_path, monkeypatch):
    monkeypatch.setattr(ho_module, "HALE_DECISIONS", tmp_path / "decisions.md")
    warm_module._log_warm_plan(2)
    text = (tmp_path / "decisions.md").read_text()
    assert "session dead" in text
    assert "verdict=FAIL" in text


def test_log_warm_plan_unverified_on_skip(tmp_path, monkeypatch):
    monkeypatch.setattr(ho_module, "HALE_DECISIONS", tmp_path / "decisions.md")
    warm_module._log_warm_plan(3)
    text = (tmp_path / "decisions.md").read_text()
    assert "skipped" in text
    assert "verdict=PASS" in text  # unverified alone caps quality, never a hard FAIL


def test_log_warm_plan_never_raises_on_orchestrator_failure(monkeypatch):
    monkeypatch.setattr(ho_module, "open_plan", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    warm_module._log_warm_plan(0)  # must not raise
