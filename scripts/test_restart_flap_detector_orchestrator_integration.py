"""Hale Orchestrator integration for restart_flap_detector's scan reporting.
Per docs/superpowers/specs/2026-07-09-self-healing-architecture-reverse-engineered.md
— the orchestrator records a scan's flagged units AFTER the state file is
already written; it must never affect detection or the script's exit code."""
from __future__ import annotations

import scripts.restart_flap_detector as flap_module
import core.ops.hale_orchestrator as ho_module


def test_log_flap_plan_writes_open_and_close_when_flagged(tmp_path, monkeypatch):
    monkeypatch.setattr(ho_module, "HALE_DECISIONS", tmp_path / "decisions.md")
    state_file = tmp_path / "restart_flap_state.json"
    state_file.write_text("{}")

    flagged = {"thunderbird-telegram-gw.service": {"starts_7d": 58, "FLAGGED": True}}
    flap_module._log_flap_plan(flagged, state_file)

    text = (tmp_path / "decisions.md").read_text()
    assert text.count("<!-- PLAN:OPEN") == 1
    assert text.count("<!-- PLAN:CLOSE") == 1
    assert "thunderbird-telegram-gw.service" in text


def test_log_flap_plan_no_op_when_nothing_flagged(tmp_path, monkeypatch):
    monkeypatch.setattr(ho_module, "HALE_DECISIONS", tmp_path / "decisions.md")
    flap_module._log_flap_plan({}, tmp_path / "restart_flap_state.json")
    assert not (tmp_path / "decisions.md").exists()


def test_log_flap_plan_never_raises_on_orchestrator_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(ho_module, "open_plan", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    state_file = tmp_path / "restart_flap_state.json"
    state_file.write_text("{}")
    flap_module._log_flap_plan({"unit.service": {"FLAGGED": True}}, state_file)  # must not raise
