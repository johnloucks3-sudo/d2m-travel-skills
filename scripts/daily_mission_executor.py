#!/usr/bin/env python3
"""
D2M DAILY MISSION EXECUTOR
scripts/daily_mission_executor.py

Cron: 06:15 MT daily via systemd timer d2m-daily-executor.timer
Run:  python3 scripts/daily_mission_executor.py [--dry-run] [--mission MISSION-XXX]

Purpose:
  Reads the mission board, identifies active tasks within Hale's autonomous
  execution band (not behind Commander's 4 gates), dispatches headless Claude
  to execute each one, and logs results back to the mission board.

Gate Classification (what requires Commander vs. what Hale executes):
  COMMANDER GATE: Any client-facing send | Financial commitment | New client first
                  contact | Strategy direction
  HALE EXECUTES:  Research | Dossier updates | Draft prep | Code builds |
                  Credential checks | Intel sweeps | Lifecycle monitoring |
                  Supplier contact (informational) | Mission board hygiene

Each dispatched task gets:
  - Full mission context (title, description, last logs)
  - Relevant file paths if mentioned
  - Explicit WRITE [PATH] instruction so output isn't lost
  - 10-minute timeout
"""

import json
import os
import subprocess
import sys
import time
import fcntl
from pathlib import Path
from datetime import datetime, timezone
from urllib.request import Request, urlopen

THUNDERBIRD = Path("/home/john/Thunderbird")
sys.path.insert(0, str(THUNDERBIRD))

TELEGRAM_BOT_TOKEN = "***REMOVED-SECRET***"
COMMANDER_CHAT_ID = 7554895206   # D2MC2C — Hale↔Commander only
RELAY_CHAT_ID     = -5248121475  # relay — all ops/status/automated output
RUN_LOCK = THUNDERBIRD / "OpsCenter" / "executor_run.lock"


def _send_telegram(message: str, chat_id: int = None) -> None:
    target = chat_id if chat_id is not None else COMMANDER_CHAT_ID
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = json.dumps({"chat_id": target, "text": message,
                               "parse_mode": "HTML"}).encode()
        urlopen(Request(url, data=payload,
                        headers={"Content-Type": "application/json"}), timeout=10)
    except Exception:
        pass

OPSCENTER = THUNDERBIRD / "OpsCenter"
BOARD_PATH = OPSCENTER / "mission_board.json"
LOCK_PATH = OPSCENTER / "mission_board.lock"
EXEC_LOG = THUNDERBIRD / "logs" / "daily_executor.log"
EXEC_OUTPUT_DIR = THUNDERBIRD / "output" / "executor_results"

# ─── GATE CLASSIFICATION ──────────────────────────────────────────────────────

# Keywords that flag a task as requiring Commander gate — do NOT auto-execute
GATE_KEYWORDS = [
    "send to client", "email client", "client send", "forward to client",
    "financial commit", "pay ", "payment approval", "book ", "purchase",
    "new client first contact", "strategy direction", "approve spend",
    "wire transfer", "invoice client",
]

# Owners that map to Commander gate (these require human decision)
GATE_OWNERS = {"Commander", "commander", "COMMANDER"}

# Task statuses we skip — pending_review means "executed, awaiting Commander close-out"
SKIP_STATUSES = {"completed", "complete", "done", "archived", "cancelled", "suspended",
                 "pending_review"}

# Max tasks to execute per run (token discipline)
MAX_TASKS_PER_RUN = 4

# Timeout per headless Claude dispatch (seconds)
TASK_TIMEOUT = 600


# ─── UTILITIES ────────────────────────────────────────────────────────────────

def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    EXEC_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(EXEC_LOG, "a") as f:
        f.write(line + "\n")


def load_board() -> dict:
    return json.loads(BOARD_PATH.read_text())


def save_board(board: dict):
    fd_lock = open(LOCK_PATH, "w")
    try:
        fcntl.flock(fd_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        log("Board locked by another process — skipping save")
        return
    BOARD_PATH.write_text(json.dumps(board, indent=2, default=str))
    board["last_updated"] = datetime.now(timezone.utc).isoformat()
    BOARD_PATH.write_text(json.dumps(board, indent=2, default=str))
    fcntl.flock(fd_lock, fcntl.LOCK_UN)
    fd_lock.close()
    try:
        LOCK_PATH.unlink()
    except FileNotFoundError:
        pass


def is_gate_task(mission: dict) -> bool:
    """Return True if this task requires Commander's gate (do not auto-execute)."""
    owner = mission.get("assigned_to", "")
    if owner in GATE_OWNERS:
        return True

    text = (mission.get("title", "") + " " + mission.get("description", "")).lower()
    return any(kw in text for kw in GATE_KEYWORDS)


def is_executable(mission: dict) -> bool:
    """Return True if this task is within Hale's autonomous execution band."""
    status = mission.get("status", "")
    if status in SKIP_STATUSES:
        return False
    if is_gate_task(mission):
        return False
    # Only execute tasks explicitly assigned to Hale or Wing staff (not Commander)
    owner = mission.get("assigned_to", "")
    hale_owners = {"Hale", "hale", "HALE", "Sterling", "Dani", "Intel", "Harlan",
                   "A7 Sterling", "A3 Dani", "A2 Dembe", "A9 Harlan",
                   "ELON", "elon", "Whetstone", "WHETSTONE"}
    if not any(ho in owner for ho in hale_owners):
        return False
    return True


def get_executable_missions(board: dict, priority_filter: list = None) -> list:
    """Return missions ready for autonomous execution, sorted by priority."""
    priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    missions = [
        m for m in board.get("missions", [])
        if is_executable(m)
    ]
    if priority_filter:
        missions = [m for m in missions if m.get("priority") in priority_filter]
    missions.sort(key=lambda m: priority_order.get(m.get("priority", "P3"), 3))
    return missions[:MAX_TASKS_PER_RUN]


# ─── HEADLESS DISPATCH ────────────────────────────────────────────────────────

def _build_max_plan_env() -> dict:
    """Strip API key so claude CLI uses Max plan OAuth."""
    env = dict(os.environ)
    env.pop("ANTHROPIC_API_KEY", None)
    env.pop("ANTHROPIC_BASE_URL", None)
    env["HOME"] = "/home/john"
    env["PATH"] = "/home/john/.local/bin:/usr/local/bin:/usr/bin:/bin"
    return env


def _load_oauth_token() -> str:
    creds_path = Path.home() / ".claude" / ".credentials.json"
    try:
        creds = json.loads(creds_path.read_text())
        return creds.get("claudeAiOauth", {}).get("accessToken", "")
    except Exception:
        return ""


def dispatch_headless(mission: dict, output_path: Path, dry_run: bool = False) -> dict:
    """
    Dispatch a headless Claude process to execute a mission task.
    Returns {"success": bool, "output": str, "elapsed": float}
    """
    mission_id = mission["id"]
    title = mission["title"]
    description = mission.get("description", "No description.")
    owner = mission.get("assigned_to", "Hale")
    raw_logs = mission.get("logs", [])[-5:]
    recent_logs = "\n".join(l if isinstance(l, str) else str(l) for l in raw_logs)

    prompt = f"""You are executing a Wing task from the D2M Thunderbird mission board.

MISSION: {mission_id}
TITLE: {title}
ASSIGNED TO: {owner}
DESCRIPTION: {description}

RECENT ACTIVITY:
{recent_logs or "No prior logs."}

YOUR JOB:
1. Execute this task to the best of your ability with the information available.
2. If the task requires reading files, read them.
3. If the task requires running scripts, run them (non-destructive only).
4. If the task produces a draft/report/analysis, write it.
5. Be specific. Show what you found or did. Don't summarize — produce.

CONSTRAINTS:
- Do NOT send any email to a client address.
- Do NOT make financial commitments.
- Do NOT push to git without explicit instruction.
- If the task turns out to require Commander's approval, say so clearly.

WRITE your results and findings to:
{output_path}

Format: Brief header with mission ID + title, then the work product, then a
3-line status at the end:
STATUS: [COMPLETE / PARTIAL / BLOCKED]
BLOCKER: [what blocked you, or NONE]
NEXT: [what should happen next]
"""

    if dry_run:
        log(f"  [DRY RUN] Would dispatch: {mission_id} — {title}")
        return {"success": True, "output": "[dry-run]", "elapsed": 0.0}

    token = _load_oauth_token()
    env = _build_max_plan_env()
    if token:
        env["CLAUDE_CODE_OAUTH_TOKEN"] = token

    log_path = THUNDERBIRD / "logs" / "executor_results" / f"{mission_id}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    start = time.time()
    try:
        from scripts.bg_llm import bg_complete
        output = bg_complete(
            prompt=prompt,
            system="You are Hale, COS for Dreams2Memories Travel. Execute the mission task described and provide a detailed analysis and action report.",
            max_tokens=4096,
        )
        elapsed = time.time() - start
        if output.strip():
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(output)
            return {"success": True, "output": output[:500], "elapsed": elapsed}
        else:
            return {"success": False, "output": "bg_llm returned empty response", "elapsed": elapsed}
    except Exception as e:
        return {"success": False, "output": str(e), "elapsed": time.time() - start}


def log_result_to_board(board: dict, mission_id: str, result: dict):
    """Append execution result to mission's log array."""
    for m in board.get("missions", []):
        if m["id"] == mission_id:
            ts = datetime.now(timezone.utc).isoformat()[:19]
            status_flag = "✅" if result["success"] else "❌"
            entry = (
                f"[{ts}] {status_flag} Auto-executed by daily_mission_executor — "
                f"{result['elapsed']:.0f}s — "
                f"{'SUCCESS' if result['success'] else 'FAILED'}: "
                f"{result['output'][:200]}"
            )
            m.setdefault("logs", []).append(entry)
            m["updated_at"] = ts
            if result["success"]:
                # Require explicit STATUS: COMPLETE in output to auto-close.
                # Keyword absence alone is not sufficient — avoids silent false-completes.
                output_lower = result["output"].lower()
                has_complete = "status: complete" in output_lower
                has_issues = any(flag in output_lower for flag in [
                    "status: blocked", "status: partial",
                    "error", "failed", "flag", "warning",
                    "blocked", "investigate", "review needed"
                ])

                if has_complete and not has_issues:
                    m["status"] = "completed"
                    m["logs"].append(f"[{ts}] ⚡ HALE auto-approved closure (STATUS: COMPLETE confirmed)")
                else:
                    # Hold for Commander review — page D2MC2C
                    m["status"] = "pending_review"
                    reason = "STATUS: COMPLETE not found" if not has_complete else "issue keywords detected"
                    m["logs"].append(f"[{ts}] ⏸ pending_review: {reason}")
                    title = m.get("title", mission_id)[:45]
                    snippet = result["output"][:200].replace("<", "&lt;").replace(">", "&gt;")
                    _send_telegram(
                        f"⚡ <b>PENDING REVIEW — {mission_id}</b>\n"
                        f"{title}\n\n"
                        f"<i>{reason}</i>\n\n"
                        f"<code>{snippet}</code>\n\n"
                        f"Output: output/executor_results/",
                        chat_id=COMMANDER_CHAT_ID,
                    )
            break


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="D2M Daily Mission Executor")
    parser.add_argument("--dry-run", action="store_true",
                        help="Classify and plan; do not dispatch headless Claude")
    parser.add_argument("--mission", metavar="MISSION-XXX",
                        help="Execute one specific mission by ID")
    parser.add_argument("--priority", choices=["P0", "P1", "P0,P1"],
                        default="P0,P1", help="Priority filter (default: P0,P1)")
    args = parser.parse_args()

    # ── Singleton lock — prevent concurrent runs ─────────────────────────────
    try:
        lock_fd = open(RUN_LOCK, "w")
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_fd.write(str(os.getpid()))
        lock_fd.flush()
    except BlockingIOError:
        print(f"[SKIP] Another executor is already running (lock: {RUN_LOCK}). Exiting.")
        return

    now = datetime.now()
    log(f"Daily Mission Executor — {now.strftime('%Y-%m-%d %H:%M MT')}")

    board = load_board()
    priority_filter = args.priority.split(",") if args.priority else ["P0", "P1"]

    if args.mission:
        all_m = board.get("missions", [])
        targets = [m for m in all_m if m["id"] == args.mission]
        if not targets:
            log(f"Mission {args.mission} not found.")
            return
    else:
        targets = get_executable_missions(board, priority_filter)

    log(f"Executable tasks this run: {len(targets)}")

    if not targets:
        log("Nothing to execute — all active tasks are behind Commander gates or no P0/P1 Hale tasks.")
        return

    # Show what we'll execute
    for m in targets:
        gate = "GATE 🔒" if is_gate_task(m) else "AUTO ✅"
        log(f"  [{m['priority']}] {m['id']}: {m['title'][:55]} | {gate} | → {m.get('assigned_to','?')}")

    EXEC_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results_summary = []

    for mission in targets:
        mid = mission["id"]
        output_path = EXEC_OUTPUT_DIR / f"{mid}_{now.strftime('%Y%m%d')}.md"
        log(f"\nDispatching: {mid} — {mission['title'][:50]}...")

        result = dispatch_headless(mission, output_path, dry_run=args.dry_run)
        log_result_to_board(board, mid, result)

        status_icon = "✅" if result["success"] else "❌"
        log(f"  {status_icon} {mid}: {result['elapsed']:.0f}s — "
            f"{'output at ' + str(output_path.name) if result['success'] else result['output'][:100]}")

        results_summary.append({
            "id": mid,
            "title": mission["title"],
            "success": result["success"],
            "elapsed": result["elapsed"],
            "output_path": str(output_path) if result["success"] else None,
        })

        # Brief pause between dispatches to avoid process contention
        time.sleep(2)

    if not args.dry_run:
        save_board(board)

    # Write execution summary for AM brief pickup
    summary_path = THUNDERBIRD / "OpsCenter" / "executor_last_run.json"
    summary_path.write_text(json.dumps({
        "run_at": now.isoformat(),
        "tasks_attempted": len(results_summary),
        "tasks_succeeded": sum(1 for r in results_summary if r["success"]),
        "results": results_summary,
    }, indent=2))

    succeeded = sum(1 for r in results_summary if r["success"])
    failed = len(results_summary) - succeeded
    log(f"\nExecutor complete: {succeeded}/{len(results_summary)} tasks succeeded.")
    log(f"Summary: {summary_path}")

    # ── Log routine run consumption to usage ledger ──────────────────────────
    try:
        ledger_path = THUNDERBIRD / "OpsCenter" / "usage_ledger.json"
        ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else {"routine_runs": [], "manual_snapshots": []}
        ledger.setdefault("routine_runs", []).append({
            "ts": datetime.now(timezone.utc).isoformat(),
            "count": len(results_summary),
            "succeeded": succeeded,
            "missions": [r["id"] for r in results_summary],
        })
        ledger["routine_runs"] = ledger["routine_runs"][-60:]  # keep last 60 entries
        ledger_path.write_text(json.dumps(ledger, indent=2))
    except Exception as e:
        log(f"  [ledger] write failed: {e}")

    # ── Telegram cycle summary → relay (ops noise, not Commander channel) ──────
    run_label = now.strftime("%H:%M MT")
    lines = [f"⚡ <b>EXECUTOR — {run_label}</b>  {succeeded}/{len(results_summary)} ✅"]
    for r in results_summary:
        icon = "✅" if r["success"] else "❌"
        lines.append(f"{icon} {r['id']}: {r['title'][:45]}")
    if failed:
        lines.append(f"\n⚠️ {failed} dispatch(es) failed — check logs/daily_executor.log")
    lines.append(f"\nOutput: output/executor_results/")
    _send_telegram("\n".join(lines), chat_id=RELAY_CHAT_ID)

    # ── Release run lock ─────────────────────────────────────────────────────
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()
        RUN_LOCK.unlink(missing_ok=True)
    except Exception:
        pass


if __name__ == "__main__":
    main()
