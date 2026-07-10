"""Hale Orchestrator integration for crash_reporter's exception hooks.
Per docs/superpowers/specs/2026-07-09-self-healing-architecture-reverse-engineered.md
— the orchestrator records the crash event AFTER the report is already
written; it must never affect crash-capture behavior or raise."""
from __future__ import annotations

import core.monitoring.crash_reporter as crash_reporter_module
import core.ops.hale_orchestrator as ho_module


def test_log_crash_plan_writes_open_and_close_when_log_exists(tmp_path, monkeypatch):
    monkeypatch.setattr(ho_module, "HALE_DECISIONS", tmp_path / "decisions.md")
    log_path = tmp_path / "some_service_1234.log"
    log_path.write_text("crash trace here\n")

    crash_reporter_module._log_crash_plan("some_service (main thread)", log_path)

    text = (tmp_path / "decisions.md").read_text()
    assert text.count("<!-- PLAN:OPEN") == 1
    assert text.count("<!-- PLAN:CLOSE") == 1
    assert "some_service (main thread)" in text


def test_log_crash_plan_never_raises_on_orchestrator_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(ho_module, "HALE_DECISIONS", tmp_path / "decisions.md")
    log_path = tmp_path / "missing.log"  # does not exist — exercises "unverified" branch too
    crash_reporter_module._log_crash_plan("some_service", log_path)  # must not raise


def test_log_crash_plan_never_raises_when_import_broken(monkeypatch, tmp_path):
    monkeypatch.setattr(ho_module, "open_plan", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    log_path = tmp_path / "x.log"
    log_path.write_text("x")
    crash_reporter_module._log_crash_plan("some_service", log_path)  # must not raise
