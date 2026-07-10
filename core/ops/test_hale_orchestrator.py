"""
Tests for core/ops/hale_orchestrator.py — Plan and AssessResult dataclasses.
"""
from core.ops.hale_orchestrator import Plan, AssessResult


def test_plan_defaults():
    plan = Plan(plan_id="PLN-abc123", task_summary="test task")
    assert plan.tier == "trivial"
    assert plan.status == "open"
    assert plan.degraded is False
    assert plan.criteria == []
    assert plan.session_id is None


def test_assess_result_defaults():
    result = AssessResult(plan_id="PLN-abc123")
    assert result.verdict == "PASS"
    assert result.quality_tier is None
    assert result.criteria_met == []
    assert result.degraded is False
