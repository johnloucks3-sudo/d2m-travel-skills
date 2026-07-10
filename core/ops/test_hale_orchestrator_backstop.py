import json
import os
import subprocess
import sys

# Resolve hook path dynamically via git root to work from both main repo and worktree
_REPO_ROOT = subprocess.run(
    ["git", "rev-parse", "--show-toplevel"],
    capture_output=True,
    text=True,
    check=True,
    cwd=os.path.dirname(__file__),
).stdout.strip()
HOOK = f"{_REPO_ROOT}/.claude/hooks/hale_orchestrator_backstop.py"


def _run_hook(stdin_payload: dict, decisions_path) -> str:
    env = os.environ.copy()
    env["HALE_ORCHESTRATOR_DECISIONS_PATH"] = str(decisions_path)
    proc = subprocess.run(
        [sys.executable, HOOK],
        input=json.dumps(stdin_payload),
        capture_output=True,
        text=True,
        env=env,
    )
    return proc.stdout + proc.stderr


def test_backstop_closes_orphaned_plan(tmp_path):
    decisions = tmp_path / "decisions.md"
    from core.ops.hale_orchestrator import Plan, PlanStore
    PlanStore.write_open(Plan(plan_id="PLN-orphan1", task_summary="x",
                               session_id="sess-hook-1"), path=decisions)

    _run_hook({"session_id": "sess-hook-1", "transcript_path": ""}, decisions)

    text = decisions.read_text()
    assert "<!-- PLAN:CLOSE plan_id=PLN-orphan1 verdict=FAIL" in text
    assert "never reached assessment" in text


def test_backstop_files_default_plan_when_transcript_has_tool_use(tmp_path):
    decisions = tmp_path / "decisions.md"
    decisions.write_text("")
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text('{"type": "tool_use", "name": "Read"}\n')

    _run_hook({"session_id": "sess-hook-2", "transcript_path": str(transcript)}, decisions)

    text = decisions.read_text()
    assert "<!-- PLAN:OPEN" in text
    assert "session_id=sess-hook-2" in text
    assert "<!-- PLAN:CLOSE" in text
    assert "verdict=PASS" in text


def test_backstop_exits_zero_on_success(tmp_path):
    decisions = tmp_path / "decisions.md"
    decisions.write_text("")
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text('{"type": "tool_use"}\n')

    env = os.environ.copy()
    env["HALE_ORCHESTRATOR_DECISIONS_PATH"] = str(decisions)
    proc = subprocess.run(
        [sys.executable, HOOK],
        input=json.dumps({"session_id": "sess-exit-check", "transcript_path": str(transcript)}),
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 0, f"Hook exited with {proc.returncode}: {proc.stderr}"
