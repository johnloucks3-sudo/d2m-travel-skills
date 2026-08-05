#!/usr/bin/env python3
"""
opencode_worker.py — OC-lane pull worker for HALE-OS brain_bridge.
Polls brain_bridge.Board for claimable OC tasks and executes via opencode CLI.

Usage:
    PLAN_ID=MY-PLAN WORKER_ID=oc-scout-1 python3 scripts/opencode_worker.py

Env vars:
    PLAN_ID    (required) — brain_bridge plan to claim from
    WORKER_ID  (optional, default: oc-scout-1)
    LANE       (optional, default: oc)

PII FENCE REMOVED 2026-08-04 (Commander directive) — OC is PII-cleared; no
client-identifier rejection. Note: this worker is legacy — it imports the
documented-broken `brain_bridge` module (see AGENTS.md); the live OC lane is
`scripts/oc_worker.py`.
Non-gated infrastructure — does not touch protected email/relay files.
"""
import os
import sys
import signal
import logging
import subprocess
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Bootstrap: add repo root to sys.path so brain_bridge imports cleanly
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
from brain_bridge import Board  # noqa: E402 — after path fix

# ---------------------------------------------------------------------------
# Config from env
# ---------------------------------------------------------------------------
PLAN_ID = os.environ.get("PLAN_ID", "").strip()
WORKER_ID = os.environ.get("WORKER_ID", "oc-scout-1").strip()
LANE = os.environ.get("LANE", "oc").strip()
POLL_INTERVAL = 10          # seconds between empty-queue polls
TASK_TIMEOUT = 120          # seconds before subprocess is killed
DEFAULT_MODEL = "deepseek-v3.2"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    stream=sys.stdout,
)
log = logging.getLogger("oc-worker")

# ---------------------------------------------------------------------------
# Graceful shutdown flag
# ---------------------------------------------------------------------------
_shutdown = False


def _handle_signal(signum, frame):
    global _shutdown
    log.info("Signal %s received — finishing current task then exiting.", signum)
    _shutdown = True


signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT, _handle_signal)


# PII fence REMOVED 2026-08-04 (Commander directive) — OC is PII-cleared.
# This worker is legacy/dead (imports nonexistent brain_bridge below); the live
# OC lane is oc_worker.py. No PII rejection on either.


# ---------------------------------------------------------------------------
# Task execution
# ---------------------------------------------------------------------------
def _execute(task: dict) -> tuple[str, str]:
    """
    Run `opencode run --model <model> "<task>"`.
    Returns (result_snippet, status).
    """
    model = task.get("model") or DEFAULT_MODEL
    cmd = ["opencode", "run", "--model", model, task["task"]]
    log.info("Executing T%s via opencode model=%s: %.80s…", task["id"], model, task["task"])
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=TASK_TIMEOUT,
            cwd=str(REPO_ROOT),
        )
        output = proc.stdout or proc.stderr or "(no output)"
        snippet = output[:500]
        if proc.returncode == 0:
            log.info("T%s completed (rc=0). snippet: %.80s…", task["id"], snippet)
            return snippet, "completed"
        else:
            log.warning("T%s failed rc=%d. snippet: %.80s…", task["id"], proc.returncode, snippet)
            return f"EXIT-{proc.returncode}: {snippet}", "failed"
    except subprocess.TimeoutExpired:
        log.error("T%s timed out after %ds.", task["id"], TASK_TIMEOUT)
        return f"TIMEOUT after {TASK_TIMEOUT}s", "failed"
    except FileNotFoundError:
        log.error("opencode CLI not found in PATH.")
        return "opencode-not-found", "failed"
    except Exception as exc:  # noqa: BLE001
        log.error("T%s unexpected error: %s", task["id"], exc)
        return f"ERROR: {exc}", "failed"


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
def run():
    if not PLAN_ID:
        print(
            "Usage: PLAN_ID=<plan-id> [WORKER_ID=oc-scout-1] [LANE=oc] "
            "python3 scripts/opencode_worker.py",
            file=sys.stderr,
        )
        sys.exit(1)

    board = Board()
    log.info("OC worker %s starting — plan=%s lane=%s", WORKER_ID, PLAN_ID, LANE)

    while not _shutdown:
        task = board.claim(PLAN_ID, LANE, WORKER_ID)

        if task is None:
            log.debug("No claimable task — sleeping %ds.", POLL_INTERVAL)
            # Interruptible sleep so SIGTERM is noticed promptly
            for _ in range(POLL_INTERVAL):
                if _shutdown:
                    break
                time.sleep(1)
            continue

        result_snippet, status = _execute(task)
        board.done(PLAN_ID, task["id"], result=result_snippet, status=status)
        log.info("T%s marked %s.", task["id"], status)

    log.info("OC worker %s shut down cleanly.", WORKER_ID)


if __name__ == "__main__":
    run()
