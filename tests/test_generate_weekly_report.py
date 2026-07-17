"""Regression test for scripts/generate_weekly_report.py::inject_task.

REGRESSION (2026-07-16): inject_task() appended directly to board["missions"]
with zero duplicate check -- the same bug class fixed in
tcd/writeback.py::_default_create_task_fn, found independently here. Since
this generator re-runs periodically, it kept re-creating the identical
Regent/TESS/dedup mission-board tickets every cycle (MISSION-621-629, all
"Weekly Report Generator", same titles as earlier duplicates 001/005/011/
017/029/033/034/037/042/046/047).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).parent.parent / "OpsCenter"))

import generate_weekly_report as gwr  # noqa: E402


def test_duplicate_inject_task_blocked_not_filed_twice():
    board = {"missions": []}
    first_id = gwr.inject_task(
        board,
        title="Produce Regent pricing refresh for Lyons renewal window",
        description="desc 1",
        owner="Intel",
        priority="P1",
    )
    second_id = gwr.inject_task(
        board,
        title="Produce Regent pricing refresh for Lyons renewal window",
        description="desc 2 (re-generated next cycle)",
        owner="Intel",
        priority="P1",
    )

    assert second_id == first_id, "re-running the generator must not file a second mission for the same title"
    assert len(board["missions"]) == 1, "exactly one mission must exist for this title, not two"
    filed = board["missions"][0]
    assert any("duplicate blocked" in log for log in filed["logs"])


def test_distinct_titles_still_create_separate_missions():
    board = {"missions": []}
    id_a = gwr.inject_task(board, "Task A", "desc", "Intel", "P2")
    id_b = gwr.inject_task(board, "Completely unrelated Task B", "desc", "Intel", "P2")
    assert id_a != id_b
    assert len(board["missions"]) == 2
