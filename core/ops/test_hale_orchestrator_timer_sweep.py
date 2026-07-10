"""
Tests for scripts/hale_orchestrator_timer_sweep.py — cross-engine orphan sweep.
"""
import sys
from pathlib import Path

# Add parent directory to path so we can import from scripts/
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.hale_orchestrator_timer_sweep import sweep_all_orphans
from core.ops.hale_orchestrator import Plan, AssessResult, PlanStore


def test_sweep_closes_orphans_across_multiple_sessions(tmp_path):
    """Verify sweep closes both Claude Code and OpenCode orphans."""
    p = tmp_path / "decisions.md"
    PlanStore.write_open(Plan(plan_id="PLN-cc0001", task_summary="claude code task",
                               session_id="cc-session-1"), path=p)
    PlanStore.write_open(Plan(plan_id="PLN-oc0001", task_summary="opencode task",
                               session_id="oc-session-1"), path=p)
    PlanStore.write_close(AssessResult(plan_id="PLN-cc0001", verdict="PASS"), path=p)
    # PLN-oc0001 left open — simulates OpenCode (no Stop-hook backstop) or a crash

    closed = sweep_all_orphans(path=p, min_age_seconds=0)

    assert closed == ["PLN-oc0001"]
    text = p.read_text()
    assert "<!-- PLAN:CLOSE plan_id=PLN-oc0001 verdict=FAIL" in text
    assert "never reached assessment (timer sweep)" in text


def test_sweep_ignores_recently_opened_plans(tmp_path):
    """Verify sweep doesn't close plans younger than min_age_seconds."""
    p = tmp_path / "decisions.md"
    PlanStore.write_open(Plan(plan_id="PLN-fresh1", task_summary="still running",
                               session_id="sess-live"), path=p)

    closed = sweep_all_orphans(path=p, min_age_seconds=3600)

    assert closed == []
    assert "<!-- PLAN:CLOSE plan_id=PLN-fresh1" not in p.read_text()


def test_sweep_closes_old_orphans_but_not_fresh_ones(tmp_path):
    """Verify sweep respects age threshold, closing only stale orphans."""
    from datetime import datetime, timezone, timedelta
    import core.ops.hale_orchestrator as ho

    p = tmp_path / "decisions.md"

    # Create an old plan (manually set opened_at to 1 hour ago)
    old_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    old_plan = Plan(plan_id="PLN-old001", task_summary="old task", session_id="sess-old",
                    opened_at=old_time)
    PlanStore.write_open(old_plan, path=p)

    # Create a fresh plan (use current time)
    fresh_plan = Plan(plan_id="PLN-fresh001", task_summary="fresh task", session_id="sess-fresh")
    PlanStore.write_open(fresh_plan, path=p)

    # Sweep with 30-minute threshold
    closed = sweep_all_orphans(path=p, min_age_seconds=1800)  # 30 minutes

    # Should close only the old one
    assert "PLN-old001" in closed
    assert "PLN-fresh001" not in closed
    text = p.read_text()
    assert "<!-- PLAN:CLOSE plan_id=PLN-old001 verdict=FAIL" in text
    assert "<!-- PLAN:CLOSE plan_id=PLN-fresh001" not in text


def test_sweep_returns_list_of_closed_plan_ids(tmp_path):
    """Verify sweep returns the list of closed plan_ids."""
    p = tmp_path / "decisions.md"
    PlanStore.write_open(Plan(plan_id="PLN-test1", task_summary="t1", session_id="s1"), path=p)
    PlanStore.write_open(Plan(plan_id="PLN-test2", task_summary="t2", session_id="s2"), path=p)

    closed = sweep_all_orphans(path=p, min_age_seconds=0)

    assert len(closed) == 2
    assert "PLN-test1" in closed
    assert "PLN-test2" in closed


def test_sweep_with_empty_file(tmp_path):
    """Verify sweep handles empty/missing files gracefully."""
    p = tmp_path / "empty_decisions.md"

    closed = sweep_all_orphans(path=p, min_age_seconds=0)

    assert closed == []


def test_sweep_with_no_orphans(tmp_path):
    """Verify sweep returns empty list when all plans are closed."""
    p = tmp_path / "decisions.md"
    PlanStore.write_open(Plan(plan_id="PLN-abc", task_summary="task", session_id="sess"), path=p)
    PlanStore.write_close(AssessResult(plan_id="PLN-abc", verdict="PASS"), path=p)

    closed = sweep_all_orphans(path=p, min_age_seconds=0)

    assert closed == []
