#!/usr/bin/env python3
"""
Hale Orchestrator — Stop hook backstop.

Fires on every Stop event. Guarantees universal Plan coverage without ever
blocking session end:
  1. Any OPEN plan for this session with no matching CLOSE -> auto-closed
     FAIL, notes="never reached assessment" (an abandoned plan is real
     signal, not something to hide).
  2. If this session has zero Plan entries at all but the transcript shows
     tool activity -> auto-files a trivial default Plan, closed PASS with
     all default criteria marked unverified (the hook cannot mechanically
     check them — see design doc Error Handling).

All exceptions are caught and logged; this script always exits 0.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, "/home/john/Thunderbird/.claude/worktrees/hale-orchestrator")

from core.ops.hale_orchestrator import (  # noqa: E402
    Plan,
    AssessResult,
    PlanStore,
    _new_plan_id,
    _DEFAULT_CRITERIA,
    logger,
)


def _transcript_has_tool_use(transcript_path: str) -> bool:
    try:
        p = Path(transcript_path)
        if not transcript_path or not p.exists():
            return False
        with open(p, errors="ignore") as f:
            for line in f:
                if '"type": "tool_use"' in line or '"type":"tool_use"' in line:
                    return True
    except Exception:
        pass
    return False


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception as exc:
        logger.error("backstop: failed to parse stdin: %s", exc)
        return 0

    session_id = payload.get("session_id") or "unknown"
    transcript_path = payload.get("transcript_path", "")

    try:
        orphaned = PlanStore.find_orphaned_opens(session_id)
        for o in orphaned:
            PlanStore.write_close(AssessResult(
                plan_id=o["plan_id"],
                verdict="FAIL",
                notes="never reached assessment",
            ))

        if not PlanStore.session_has_any_plan(session_id) and _transcript_has_tool_use(transcript_path):
            plan = Plan(
                plan_id=_new_plan_id(),
                task_summary="auto-filed: turn had tool activity with no explicit Plan",
                tier="trivial",
                session_id=session_id,
                criteria=list(_DEFAULT_CRITERIA),
            )
            PlanStore.write_open(plan)
            PlanStore.write_close(AssessResult(
                plan_id=plan.plan_id,
                verdict="PASS",
                criteria_unverified=list(_DEFAULT_CRITERIA),
                notes="auto-filed by backstop hook — criteria not mechanically checked",
            ))
    except Exception as exc:
        logger.error("backstop: unexpected failure: %s", exc)

    return 0


if __name__ == "__main__":
    sys.exit(main())
