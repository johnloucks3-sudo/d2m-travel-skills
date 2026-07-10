"""
Integration tests for hale_orchestrator.py — full lifecycle testing.
Tests the open_plan → assess_plan → close_plan workflow end-to-end.
"""
from core.ops.hale_orchestrator import open_plan, assess_plan, close_plan
import core.ops.hale_orchestrator as ho_module


def test_full_lifecycle_trivial_plan(tmp_path, monkeypatch):
    """Test a complete trivial-tier plan workflow: open, assess all criteria met, close."""
    monkeypatch.setattr(ho_module, "HALE_DECISIONS", tmp_path / "decisions.md")

    plan = open_plan("read a config file")
    result = assess_plan(plan, {c: "met" for c in plan.criteria})
    ok = close_plan(result)

    assert ok is True
    text = (tmp_path / "decisions.md").read_text()
    assert f"plan_id={plan.plan_id}" in text
    assert "PLAN:OPEN" in text and "PLAN:CLOSE" in text
    assert text.index("PLAN:OPEN") < text.index("PLAN:CLOSE")


def test_full_lifecycle_t1_plan_with_missed_criterion(tmp_path, monkeypatch):
    """Test a T1-tier plan where one criterion is missed, leading to FAIL verdict and RED quality tier."""
    monkeypatch.setattr(ho_module, "HALE_DECISIONS", tmp_path / "decisions.md")

    plan = open_plan("ship a feature", tier="T1", criteria=["tests pass", "no gate crossed"])
    result = assess_plan(plan, {"tests pass": "missed", "no gate crossed": "met"})
    close_plan(result)

    assert result.verdict == "FAIL"
    assert result.quality_tier == "RED"
    text = (tmp_path / "decisions.md").read_text()
    assert "verdict=FAIL" in text
