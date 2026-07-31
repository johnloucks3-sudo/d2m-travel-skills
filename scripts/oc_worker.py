#!/usr/bin/env python3
"""
OC WORKER — HALE-OS OpenCode Pull Loop
Thunderbird Wing · Dreams2Memories Travel, LLC

Systemd service that polls the brain bridge for oc-lane tasks, claims them
atomically, dispatches to headless Claude (Haiku by default — saves MAX bucket),
and writes results back to the claim board.

Run as service:  systemctl --user start opencode-worker.service
Run once:        python3 scripts/oc_worker.py --once
Dry run:         python3 scripts/oc_worker.py --once --dry-run
Status:          python3 scripts/oc_worker.py --status
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ── paths ──────────────────────────────────────────────────────────────────────
ROOT        = Path(__file__).parent.parent
BB_MODULE   = ROOT / "core" / "hale_bus"
DISPATCH    = ROOT / "OpsCenter" / "dispatch_claude.py"
OUTPUT_DIR  = ROOT / "output" / "oc_worker"
LOG_DIR     = ROOT / "logs"
STATUS_FILE = ROOT / "OpsCenter" / "oc_worker_status.json"

sys.path.insert(0, str(ROOT))
from core.hale_bus.brain_bridge import BrainBridge

# ── config ─────────────────────────────────────────────────────────────────────
POLL_INTERVAL   = int(os.getenv("OC_WORKER_POLL_SEC", "15"))   # seconds between polls
TASK_TIMEOUT    = int(os.getenv("OC_WORKER_TIMEOUT_SEC", "300"))  # per-task timeout
AGENT_NAME      = os.getenv("OC_WORKER_AGENT", "hale-oc-worker")
# ── OC LANE MODEL — Commander directive 2026-07-29 ─────────────────────────────
# OC ran `claude -p --model haiku` through the Claude MAX OAuth proxy, which meant
# delegating to OC spent the SAME MAX bucket CC spends — zero budget relief — and did
# it on Haiku, which returned a stub audit that grepped /usr/bin/docker for the string
# "NotImplementedError" and reported byte offsets as findings.
#
# OC is now what its name always claimed: the opencode CLI on DeepSeek v4 Zen FREE.
# Off the Anthropic meter entirely, and a stronger model than Haiku.
#   opencode/deepseek-v4-flash-free   <- Zen free tier. USE THIS.
#   opencode-go/*                     <- different tier, NOT authorised (Commander, 2026-07-29)
OPENCODE_BIN    = os.getenv("OC_WORKER_BIN", str(Path.home() / ".opencode" / "bin" / "opencode"))
DEFAULT_MODEL   = os.getenv("OC_WORKER_MODEL", "opencode/deepseek-v4-flash-free")

# ── logging ────────────────────────────────────────────────────────────────────
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [OC-WORKER] %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / "oc_worker.log"),
    ],
)
log = logging.getLogger("oc_worker")


# ── helpers ────────────────────────────────────────────────────────────────────

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_status(state: dict) -> None:
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text(json.dumps({**state, "updated": now_iso()}, indent=2))


def dispatch_task(task: dict, dry_run: bool = False) -> tuple[bool, str]:
    """
    Dispatch an oc-lane task to headless Claude and return (success, result_text).
    Uses dispatch_claude.py (existing proven infra) with Haiku to save MAX tokens.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = int(time.time())
    out_file = OUTPUT_DIR / f"task_{task['id']}_{ts}.md"

    prompt = (
        f"You are HALE-OC, executing an OC-lane task from the HALE-OS brain bridge.\n\n"
        f"TASK ID: {task['id']}\n"
        f"TITLE: {task['title']}\n"
        f"DESCRIPTION: {task.get('description', '')}\n"
        f"PRIORITY: {task.get('priority', 'P1')}\n\n"
        f"Execute this task fully. Write your complete output and findings.\n"
        f"WRITE your result summary (≤500 words) to: {out_file}\n"
        f"End your output with: TASK_COMPLETE: [one-line summary of what was accomplished]"
    )

    if dry_run:
        log.info(f"[DRY-RUN] Would dispatch task {task['id']} — {task['title']}")
        return True, f"DRY-RUN: task {task['id']} not executed"

    oc_bin = Path(OPENCODE_BIN)
    if not oc_bin.exists():
        log.error(f"opencode CLI not found at {oc_bin} — OC lane cannot run off-meter")
        return False, f"opencode binary missing at {oc_bin}"

    # OC LANE HYGIENE (2026-07-30). `opencode run` either answers in ~25s or
    # blocks FOREVER with zero output — it never errors and never times out from
    # the far side. Measured: three serial runs hung 400s each while other
    # opencode processes were live; the same model answered in 24s once they were
    # cleared. Sweeping stale runs and capping concurrency is what makes this lane
    # usable; without it OC's observed success rate was ~38%, which looked like a
    # model-quality problem and was not.
    try:
        from core.relay.oc_hygiene import before_dispatch, kill_group
        gate = before_dispatch()
        if not gate["ok"]:
            log.warning(f"OC dispatch deferred: {gate['reason']}")
            return False, gate["reason"]
        if gate["swept"]["killed"]:
            log.info(f"OC hygiene swept {len(gate['swept']['killed'])} stale run(s): "
                     f"{[k['pid'] for k in gate['swept']['killed']]}")
    except Exception as e:  # hygiene must never block real work
        log.warning(f"OC hygiene unavailable ({e}) — dispatching unguarded")
        kill_group = None

    log.info(f"Dispatching task {task['id']} → opencode ({DEFAULT_MODEL}) [off Claude meter]")

    try:
        result = subprocess.run(
            [str(oc_bin), "run", "--model", DEFAULT_MODEL, prompt],
            capture_output=True,
            text=True,
            timeout=TASK_TIMEOUT + 30,
            cwd=str(ROOT),
            # New session so a timeout can kill the whole process GROUP. Nothing
            # may survive holding a slot — a survivor is what makes the NEXT
            # dispatch hang.
            start_new_session=True,
        )

        if result.returncode != 0:
            log.warning(f"opencode exited {result.returncode}: {result.stderr[:200]}")
            # Claude fallback is DELIBERATELY not automatic: silently failing over to
            # the MAX meter is how this lane came to bill Anthropic for every "OC" task
            # in the first place. Surface the failure and let the caller decide.
            return False, f"opencode failed rc={result.returncode}: {result.stderr[:200]}"

        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(result.stdout, encoding="utf-8")
        return True, (result.stdout or "").strip()[:4000]

    except subprocess.TimeoutExpired:
        log.error(f"Task {task['id']} timed out after {TASK_TIMEOUT}s")
        # A timed-out run that survives keeps its slot and hangs the NEXT
        # dispatch. Sweep immediately rather than leaving it for the next call.
        try:
            from core.relay.oc_hygiene import sweep_stale
            swept = sweep_stale(stale_after_s=TASK_TIMEOUT)
            if swept["killed"]:
                log.info(f"post-timeout sweep killed {[k['pid'] for k in swept['killed']]}")
        except Exception:
            pass
        return False, f"timeout after {TASK_TIMEOUT}s"
    except Exception as e:
        log.error(f"Dispatch error: {e}")
        return False, str(e)


def _dispatch_direct(task: dict, prompt: str, out_file: Path) -> tuple[bool, str]:
    """Fallback: call claude -p directly (blocking)."""
    creds_path = Path.home() / ".claude" / ".credentials.json"
    env = dict(os.environ)
    try:
        creds = json.loads(creds_path.read_text())
        env["CLAUDE_CODE_OAUTH_TOKEN"] = creds["claudeAiOauth"]["accessToken"]
    except Exception as e:
        log.warning(f"Could not load OAuth token: {e}")

    claude_bin = Path.home() / ".local" / "bin" / "claude"
    if not claude_bin.exists():
        claude_bin = Path("/usr/local/bin/claude")

    try:
        result = subprocess.run(
            [str(claude_bin), "-p", prompt, "--model", "claude-haiku-4-5-20251001"],
            capture_output=True, text=True, env=env, timeout=TASK_TIMEOUT,
        )
        output = result.stdout.strip()
        out_file.write_text(output)
        result_text = _extract_result(out_file, fallback=output[:300])
        return result.returncode == 0, result_text
    except Exception as e:
        return False, str(e)


def _extract_result(out_file: Path, fallback: str = "") -> str:
    """Pull the TASK_COMPLETE: line or first 300 chars of output."""
    try:
        text = out_file.read_text()
        for line in reversed(text.splitlines()):
            if line.startswith("TASK_COMPLETE:"):
                return line[14:].strip()
        return text[:300] if text else fallback
    except FileNotFoundError:
        return fallback or "no output file"


# ── main loop ──────────────────────────────────────────────────────────────────

def run_loop(once: bool = False, dry_run: bool = False) -> None:
    bb = BrainBridge()
    log.info(f"OC Worker started | agent={AGENT_NAME} | model={DEFAULT_MODEL} | poll={POLL_INTERVAL}s")
    write_status({"state": "running", "agent": AGENT_NAME, "model": DEFAULT_MODEL})

    cycles = 0
    while True:
        cycles += 1
        try:
            task = bb.claim(lane="oc", agent=AGENT_NAME)

            if task:
                log.info(f"Claimed: {task['id']} — {task['title']}")
                write_status({"state": "busy", "current_task": task["id"], "title": task["title"]})

                success, result = dispatch_task(task, dry_run=dry_run)

                if success:
                    bb.complete(task["id"], result=result)
                    log.info(f"Completed: {task['id']} | {result[:80]}")
                else:
                    bb.fail(task["id"], reason=result)
                    log.warning(f"Failed: {task['id']} | {result[:80]}")

                write_status({"state": "running", "last_task": task["id"], "last_result": result[:80]})

            else:
                if cycles % 4 == 0:  # log every ~minute
                    summary = bb.status_summary()
                    log.debug(f"Poll cycle {cycles} | board: {summary}")
                write_status({
                    "state": "idle",
                    "cycles": cycles,
                    "board": bb.status_summary(),
                })

        except KeyboardInterrupt:
            log.info("OC Worker stopped by user.")
            write_status({"state": "stopped"})
            break
        except Exception as e:
            log.error(f"Worker error: {e}", exc_info=True)
            write_status({"state": "error", "error": str(e)})

        if once:
            log.info("--once flag: exiting after one cycle.")
            break

        time.sleep(POLL_INTERVAL)


def print_status() -> None:
    try:
        s = json.loads(STATUS_FILE.read_text())
        print(json.dumps(s, indent=2))
    except FileNotFoundError:
        print("OC Worker not running (no status file).")

    bb = BrainBridge()
    print("\nBrain Bridge:")
    print(json.dumps(bb.status_summary(), indent=2))
    pending = bb.list_tasks(status="pending", lane="oc")
    print(f"\nOC-lane pending tasks: {len(pending)}")
    for t in pending[:5]:
        deps = f" (needs: {','.join(t['depends_on'])})" if t["depends_on"] else ""
        print(f"  [{t['priority']}] {t['id']} — {t['title']}{deps}")


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="OC Worker — HALE-OS OpenCode pull loop")
    p.add_argument("--once",    action="store_true", help="Run one poll cycle and exit")
    p.add_argument("--dry-run", action="store_true", help="Claim tasks but don't dispatch")
    p.add_argument("--status",  action="store_true", help="Print worker + board status and exit")
    args = p.parse_args()

    if args.status:
        print_status()
    else:
        run_loop(once=args.once, dry_run=args.dry_run)
