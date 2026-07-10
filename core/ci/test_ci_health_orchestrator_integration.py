"""Hale Orchestrator integration for ci_health._try_repair().
Per docs/superpowers/specs/2026-07-09-self-healing-architecture-reverse-engineered.md
— the orchestrator wraps the EXISTING run_capability() decision as a ledger
entry; it must never change what _try_repair() returns or raise past it."""
from __future__ import annotations

import core.ci.ci_health as ci_health_module
import core.ops.hale_orchestrator as ho_module
from core.ci.repairs.schema import Decision, ProbeState


class _FakeResult:
    def __init__(self):
        self.decision = Decision.AUTO_APPLIED
        self.verify_after = ProbeState.GREEN
        self.risk_tier = None
        self.staged_token = None
        self.note = "repaired + verified GREEN"


def _wire_fake_repair(monkeypatch, skill_id: str):
    """Patch the lazy-imported dependencies inside _try_repair so it runs
    end-to-end without touching real systemd/subprocess/notify surfaces."""
    import core.ci.repairs.schema as schema_module
    import core.ci.repairs.rapid_repair as rapid_repair_module
    import core.notify.hale_notify as notify_module

    monkeypatch.setattr(schema_module, "REGISTRY", {skill_id: object()})
    monkeypatch.setattr(schema_module, "run_capability", lambda *a, **k: _FakeResult())
    monkeypatch.setattr(rapid_repair_module, "_load_policy", lambda: set())
    monkeypatch.setattr(notify_module, "notify_hale", lambda *a, **k: None)
    monkeypatch.setattr(notify_module, "notify_sterling", lambda *a, **k: None)


def test_log_repair_plan_writes_open_and_close(tmp_path, monkeypatch):
    monkeypatch.setattr(ho_module, "HALE_DECISIONS", tmp_path / "decisions.md")
    ci_health_module._log_repair_plan("test-skill", True, "auto-repaired")
    text = (tmp_path / "decisions.md").read_text()
    assert text.count("<!-- PLAN:OPEN") == 1
    assert text.count("<!-- PLAN:CLOSE") == 1
    assert "test-skill" in text


def test_log_repair_plan_never_raises_on_orchestrator_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(ho_module, "open_plan", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    ci_health_module._log_repair_plan("test-skill", True, "auto-repaired")  # must not raise


def test_try_repair_return_value_unchanged_by_orchestrator(tmp_path, monkeypatch):
    """The orchestrator ledger call must not alter _try_repair's own decision."""
    monkeypatch.setattr(ho_module, "HALE_DECISIONS", tmp_path / "decisions.md")
    _wire_fake_repair(monkeypatch, "test-skill")

    repaired, detail = ci_health_module._try_repair("test-skill", "true", client_affecting=False)

    assert (repaired, detail) == (True, "auto-repaired")
    text = (tmp_path / "decisions.md").read_text()
    assert "test-skill" in text
    assert text.count("<!-- PLAN:OPEN") == 1


def test_try_repair_survives_orchestrator_exception(tmp_path, monkeypatch):
    """Even if the ledger write itself blows up, _try_repair's real return
    value must be unaffected."""
    _wire_fake_repair(monkeypatch, "test-skill")
    monkeypatch.setattr(ho_module, "open_plan", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))

    repaired, detail = ci_health_module._try_repair("test-skill", "true", client_affecting=False)

    assert (repaired, detail) == (True, "auto-repaired")
