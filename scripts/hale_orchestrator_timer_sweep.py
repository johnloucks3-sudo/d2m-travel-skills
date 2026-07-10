#!/usr/bin/env python3
"""
Hale Orchestrator — cross-engine universal backstop.

Runs on a systemd --user timer, independent of any single engine's session
lifecycle. Catches orphaned Plan blocks in hale_decisions.md regardless of
which engine created them (Claude Code, OpenCode, or any future engine) —
including crashes where no Stop hook fires at all. Complements (does not
replace) the Task 6 per-session Stop-hook backstop, which still closes
orphans faster for Claude Code specifically.
"""
import re
import sys
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Add the main Thunderbird repo to path
# Systemd will run this from /home/john/Thunderbird/scripts/
# so we go up one level to the repo root
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

from core.ops.hale_orchestrator import (  # noqa: E402
    AssessResult,
    PlanStore,
    HALE_DECISIONS,
    logger,
)

_ALL_OPENS_RE = re.compile(
    r"<!-- PLAN:OPEN plan_id=(?P<plan_id>\S+) tier=(?P<tier>\S+) "
    r"session_id=(?P<session_id>\S+) opened_at=(?P<opened_at>\S+) -->"
)


def _age_seconds(opened_at: str) -> float:
    """Calculate age of an opened_at timestamp in seconds.

    If timestamp is unparseable, returns inf so it's treated as very old.
    """
    try:
        opened = datetime.fromisoformat(opened_at)
        if opened.tzinfo is None:
            opened = opened.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - opened).total_seconds()
    except Exception:
        return float("inf")  # unparseable timestamp -> treat as old enough to sweep


def sweep_all_orphans(path: Optional[Path] = None, min_age_seconds: int = 900) -> list[str]:
    """Closes every OPEN plan (any session, any engine) older than
    min_age_seconds with no matching CLOSE, as FAIL. Returns the list of
    plan_ids closed. Default 900s (15 min) avoids racing a plan that's
    still legitimately in progress.

    Args:
        path: Path to hale_decisions.md (default: HALE_DECISIONS env var or canonical)
        min_age_seconds: Only sweep plans older than this (default 900 = 15 min)

    Returns:
        List of plan_ids that were closed by this sweep.
    """
    target = path or HALE_DECISIONS
    text = target.read_text(errors="ignore") if target.exists() else ""

    all_opens = {m.group("plan_id"): m.groupdict() for m in _ALL_OPENS_RE.finditer(text)}
    closed_ids = {m.group("plan_id") for m in PlanStore.CLOSE_RE.finditer(text)}

    closed_now = []
    for plan_id, fields in all_opens.items():
        if plan_id in closed_ids:
            continue
        if _age_seconds(fields["opened_at"]) < min_age_seconds:
            continue
        PlanStore.write_close(AssessResult(
            plan_id=plan_id,
            verdict="FAIL",
            notes="never reached assessment (timer sweep)",
        ), path=path)
        closed_now.append(plan_id)

    return closed_now


def main() -> int:
    """Entry point for systemd timer invocation."""
    try:
        closed = sweep_all_orphans()
        if closed:
            logger.info("timer sweep closed %d orphaned plan(s): %s", len(closed), closed)
        return 0
    except Exception as exc:
        logger.error("timer sweep failed: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
