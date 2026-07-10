"""
Tests for core/ops/hale_orchestrator.py — Plan and AssessResult dataclasses.
"""
import re
import threading
from core.ops.hale_orchestrator import Plan, AssessResult, PlanStore


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


def test_write_open_and_close_roundtrip(tmp_path):
    p = tmp_path / "decisions.md"
    p.write_text("# existing prose\n\n### 2026-07-01 10:00:00 — some old decision\n**Decision:** did a thing\n")

    plan = Plan(plan_id="PLN-111111", task_summary="do a thing", session_id="sess-A",
                criteria=["c1", "c2"])
    PlanStore.write_open(plan, path=p)

    result = AssessResult(plan_id="PLN-111111", verdict="PASS", criteria_met=["c1", "c2"])
    PlanStore.write_close(result, path=p)

    text = p.read_text()
    assert "<!-- PLAN:OPEN plan_id=PLN-111111" in text
    assert "<!-- PLAN:CLOSE plan_id=PLN-111111 verdict=PASS" in text
    # old prose format untouched
    assert "### 2026-07-01 10:00:00 — some old decision" in text


def test_find_orphaned_opens(tmp_path):
    p = tmp_path / "decisions.md"
    plan_a = Plan(plan_id="PLN-aaaaaa", task_summary="a", session_id="sess-A")
    plan_b = Plan(plan_id="PLN-bbbbbb", task_summary="b", session_id="sess-A")
    PlanStore.write_open(plan_a, path=p)
    PlanStore.write_open(plan_b, path=p)
    PlanStore.write_close(AssessResult(plan_id="PLN-aaaaaa", verdict="PASS"), path=p)

    orphaned = PlanStore.find_orphaned_opens("sess-A", path=p)
    assert len(orphaned) == 1
    assert orphaned[0]["plan_id"] == "PLN-bbbbbb"


def test_session_has_any_plan(tmp_path):
    p = tmp_path / "decisions.md"
    assert PlanStore.session_has_any_plan("sess-Z", path=p) is False
    PlanStore.write_open(Plan(plan_id="PLN-cccccc", task_summary="c", session_id="sess-Z"), path=p)
    assert PlanStore.session_has_any_plan("sess-Z", path=p) is True


def test_concurrent_appends_do_not_corrupt(tmp_path):
    p = tmp_path / "decisions.md"
    p.write_text("")

    def worker(i):
        PlanStore.write_open(Plan(plan_id=f"PLN-{i:06d}", task_summary=f"task {i}",
                                   session_id="sess-concurrent"), path=p)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    text = p.read_text()
    opened_ids = set(re.findall(r"plan_id=(PLN-\d{6})", text))
    assert len(opened_ids) == 20  # every write landed, none clobbered another
