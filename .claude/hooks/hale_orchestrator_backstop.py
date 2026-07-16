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
import subprocess as _subprocess
import sys
from pathlib import Path

# Resolve repo root dynamically to work from both main repo and worktree
try:
    _REPO_ROOT = _subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=True,
        cwd=str(Path(__file__).resolve().parent),
    ).stdout.strip()
except Exception:
    _REPO_ROOT = "/home/john/Thunderbird"  # fallback if git is unavailable

sys.path.insert(0, _REPO_ROOT)

try:
    from core.ops.hale_orchestrator import (  # noqa: E402
        Plan,
        AssessResult,
        PlanStore,
        _new_plan_id,
        _DEFAULT_CRITERIA,
        logger,
    )
    _IMPORT_OK = True
except Exception as _import_exc:  # e.g. module not present yet on this checkout
    import logging as _logging
    logger = _logging.getLogger("hale_orchestrator_backstop_fallback")
    logger.warning("backstop: core.ops.hale_orchestrator not importable (%s) — hook is a no-op this run", _import_exc)
    _IMPORT_OK = False


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
    if not _IMPORT_OK:
        return 0

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

        # RETIRED 2026-07-16 (effectiveness audit): the auto-filed placeholder
        # PASS manufactured compliance records — 67 of 69 session-linked plans
        # were these, all criteria unverified, read by nobody. Silver's
        # mandatory front/back gate (core/silver/gate.py) now covers agent
        # work-products for real; the orphan-FAIL sweep above remains because
        # an abandoned plan is genuine signal.
    except Exception as exc:
        logger.error("backstop: unexpected failure: %s", exc)

    return 0


if __name__ == "__main__":
    sys.exit(main())
