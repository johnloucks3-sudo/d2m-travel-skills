#!/usr/bin/env python3
"""
NEXUS — Autonomous War Room Orchestrator
D2M Thunderbird OS · v1.1 · 2026-04-05
Commander: John Loucks | Author: Hale/COS

State machine with 6 hard stops. Routes tasks to:
  Qwen Free (Goose)  → Action/extraction/ops ($0)
  Claude MAX (Sonnet) → Judgment/voice/strategy ($0 via MAX OAuth)

Hard Stops:
  1. Max iterations: 6 spawns per mission
  2. TTL: 4 hours max
  3. Token budget: 50K per mission
  4. Deadlock: status unchanged for 2 iterations
  5. Explicit COMPLETE: agent writes rationale
  6. No blind pass-through: next action from whitelist

Cost: $0/month (Qwen Free + Claude MAX OAuth)
Gemini: PURGED. DeepSeek: PURGED.

┌─ Changelog ──────────────────────────────────────────────────────────┐
│ [2026-04-05] Extract all config to config.py; from config import *    │
│ [2026-04-05] _scan_inbox_file: detect file-shrink, reset last_line    │
│ [2026-04-05] NexusLock: add shared-instance contract docstring        │
└───────────────────────────────────────────────────────────────────────┘
"""

import json
import os
import sys
import subprocess
import fcntl
import time
import signal
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from enum import Enum


# ── Configuration (from config.py) ───────────────────────────────────────
# All paths, thresholds, and ALLOWED_ACTIONS are loaded from config.py
# via wildcard import. Edit config.py to change paths or limits.
from config import *


# ── Logging ──────────────────────────────────────────────────────────────────
def _ensure_log_dir():
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)

_ensure_log_dir()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [NEXUS] %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(AUDIT_LOG),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("nexus")


def audit(event: str, detail: str = "", mission_id: str = ""):
    """Immutable audit entry to nexus_audit.log."""
    ts = datetime.now(timezone.utc).isoformat()
    line = f"[{ts}] [{mission_id or 'NEXUS'}] {event}"
    if detail:
        line += f" — {detail}"
    log.info(f"{event} {detail}")
    # Also append raw to audit log for immutability
    try:
        with open(AUDIT_LOG, "a") as f:
            f.write(line + "\n")
            f.write(f"[WRITE OK: nexus_audit.log]\n")
    except Exception as e:
        log.error(f"Audit write failed: {e}")


# ── Lock File with Heartbeat ──────────────────────────────────────────────────
class NexusLock:
    """
    File-based mutual exclusion using a single nexus.lock file.

    SHARED-INSTANCE CONTRACT:
    Multiple daemon processes that start concurrently will attempt to
    acquire the SAME nexus.lock file via fcntl.flock(). Only ONE gets
    the exclusive lock; the rest raise RuntimeError with PID info.

    The lock file holds a JSON blob: {pid, started, heartbeat}.
    A forked child heartbeat process updates the heartbeat timestamp
    every HEARTBEAT_INTERVAL seconds to keep the lock alive.

    If the main daemon dies, the flock() is released automatically by
    the kernel. A stale lock on disk is harmless — the flock() is the
    real guard. Delete nexus.lock only if you want to remove stale PID info.

    WARNING: Do NOT run two nexus.py daemon instances. The first to
    acquire the lock wins; the second exits immediately.
    """
    def __init__(self):
        self.fd = None
        self._hb_pid = None

    def acquire(self):
        """Atomic lock creation. Raises if already locked."""
        try:
            self.fd = open(NEXUS_LOCK, "w")
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            existing = NEXUS_LOCK.read_text().strip() if NEXUS_LOCK.exists() else "?"
            raise RuntimeError(
                f"NEXUS ALREADY RUNNING (lock held by PID {existing}). "
                "If stale, delete OpsCenter/nexus.lock and retry."
            )
        self.fd.write(json.dumps({"pid": os.getpid(), "started": datetime.now(timezone.utc).isoformat()}))
        self.fd.flush()
        audit("LOCK_ACQUIRED", f"PID={os.getpid()}")
        self._start_heartbeat()

    def _start_heartbeat(self):
        """Fork a heartbeat writer so lock stays fresh."""
        pid = os.fork()
        if pid == 0:  # child
            signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
            while True:
                try:
                    with open(NEXUS_LOCK, "r+") as f:
                        data = json.load(f)
                        data["heartbeat"] = datetime.now(timezone.utc).isoformat()
                        f.seek(0)
                        json.dump(data, f)
                        f.truncate()
                except Exception:
                    pass
                time.sleep(HEARTBEAT_INTERVAL)
            sys.exit(0)
        else:
            self._hb_pid = pid

    def release(self):
        if self._hb_pid:
            try:
                os.kill(self._hb_pid, signal.SIGTERM)
                os.waitpid(self._hb_pid, 0)
            except Exception:
                pass
        if self.fd:
            fcntl.flock(self.fd, fcntl.LOCK_UN)
            self.fd.close()
        try:
            NEXUS_LOCK.unlink()
        except FileNotFoundError:
            pass
        audit("LOCK_RELEASED", f"PID={os.getpid()}")


# ── Mission Board I/O ─────────────────────────────────────────────────────────
def load_board() -> dict:
    with open(MISSION_BOARD, "r") as f:
        return json.load(f)


def save_board(board: dict):
    with open(MISSION_BOARD, "w") as f:
        json.dump(board, f, indent=2, default=str)
    audit("BOARD_WRITE", f"active={len(board.get('active_missions', []))}")


def find_mission(board: dict, mission_id: str) -> dict | None:
    for bucket in ("active_missions", "suspended_missions"):
        for m in board.get(bucket, []):
            if m["id"] == mission_id:
                return m
    return None


def append_mission_log(board: dict, mission_id: str, message: str):
    m = find_mission(board, mission_id)
    if m is not None:
        m.setdefault("logs", []).append(
            f"[{datetime.now(timezone.utc).isoformat()[:19]}] {message}"
        )
        m["updated_at"] = datetime.now(timezone.utc).isoformat()


# ── Queue Tracking ────────────────────────────────────────────────────────────
_QUEUE = {"qwen": 0, "claude": 0, "max_depth": 20}

def queue_depth(engine: str) -> int:
    """Return current queue depth for an engine."""
    return _QUEUE.get(engine, 0)

def queue_inc(engine: str):
    """Increment queue depth on dispatch."""
    _QUEUE[engine] = _QUEUE.get(engine, 0) + 1

def queue_dec(engine: str):
    """Decrement queue depth on completion."""
    _QUEUE[engine] = max(0, _QUEUE.get(engine, 1) - 1)

def queue_check(engine: str) -> bool:
    """Check if queue is overloaded. Returns True if safe to dispatch."""
    return _QUEUE.get(engine, 0) < _QUEUE["max_depth"]

# ── Routing ───────────────────────────────────────────────────────────────────
CLAUDE_DEFAULT = True  # With Session 1, all unknown tasks route to Claude

def _route(task_text: str, mission_id: str) -> str:
    """Return 'qwen' or 'claude' via keyword_router.py. Default to Claude (safe)."""
    router = BASE_DIR / "keyword_router.py"
    try:
        r = subprocess.run(
            [sys.executable, str(router), task_text],
            capture_output=True, text=True, timeout=10
        )
        output = r.stdout.lower()
        if "engine: claude" in output:
            return "claude"
        if "engine: qwen" in output:
            return "qwen"
    except Exception as e:
        audit("ROUTE_ERROR", f"{e} — defaulting to {'claude' if CLAUDE_DEFAULT else 'qwen'}", mission_id)
    return "claude" if CLAUDE_DEFAULT else "qwen"


def dispatch_to_qwen(task_text: str, mission_id: str) -> str:
    """Append task to Goose inbox (append-only, never overwrite)."""
    entry = (
        f"\n---\n"
        f"**NEXUS TASK** | Mission: {mission_id} | {datetime.now(timezone.utc).isoformat()[:19]}\n"
        f"{task_text}\n"
        f"status:PENDING\n"
    )
    with open(GOOSE_INBOX, "a") as f:
        f.write(entry)
    audit("DISPATCH_QWEN", f"task={task_text[:80]}", mission_id)
    return f"[WRITE OK: goose_inbox.md] Task queued for Qwen/Goose"


CLAUDE_MAX_RETRIES = 2
CLAUDE_TIMEOUT_SECS = 180  # Extended from 120s for complex tasks

def dispatch_to_claude(task_text: str, mission_id: str) -> str:
    """Run claude -p headless for judgment tasks.
    Retry up to CLAUDE_MAX_RETRIES on timeout.
    Falls back to Qwen if Claude CLI not found."""
    if not queue_check("claude"):
        audit("DISPATCH_CLAUDE_BLOCKED", f"Queue depth={queue_depth('claude')} >= {_QUEUE['max_depth']}", mission_id)
        return f"BLOCKED: Claude queue full ({queue_depth('claude')}/{_QUEUE['max_depth']}). Retry later."
    
    queue_inc("claude")
    attempt = 0
    while attempt <= CLAUDE_MAX_RETRIES:
        try:
            r = subprocess.run(
                ["claude", "-p", f"[{mission_id}] {task_text}"],
                capture_output=True, text=True, timeout=CLAUDE_TIMEOUT_SECS
            )
            output = r.stdout.strip() or r.stderr.strip()
            if output:
                audit("DISPATCH_CLAUDE", f"task={task_text[:80]} | chars={len(output)} | attempt={attempt+1}", mission_id)
                queue_dec("claude")
                return output[:2000]  # cap at 2K per spec
            # Empty output is treated as failure
            attempt += 1
            audit("DISPATCH_CLAUDE_RETRY", f"Empty output, attempt {attempt}/{CLAUDE_MAX_RETRIES+1}", mission_id)
            time.sleep(2 * (attempt + 1))  # Exponential backoff
        except FileNotFoundError:
            queue_dec("claude")
            audit("DISPATCH_CLAUDE_FAIL", "claude CLI not found — falling back to Qwen", mission_id)
            return dispatch_to_qwen(task_text, mission_id)
        except subprocess.TimeoutExpired:
            attempt += 1
            audit("DISPATCH_CLAUDE_TIMEOUT", f"{CLAUDE_TIMEOUT_SECS}s exceeded, attempt {attempt}/{CLAUDE_MAX_RETRIES+1}", mission_id)
            if attempt > CLAUDE_MAX_RETRIES:
                queue_dec("claude")
                return f"TIMEOUT: Claude did not respond after {CLAUDE_MAX_RETRIES+1} attempts ({CLAUDE_TIMEOUT_SECS}s each). Fallback to Qwen."
        except Exception as e:
            queue_dec("claude")
            audit("DISPATCH_CLAUDE_ERROR", f"Unexpected: {e}", mission_id)
            return f"ERROR: Claude dispatch failed unexpectedly: {e}"
    
    queue_dec("claude")
    audit("DISPATCH_CLAUDE_FINAL_FAIL", "All retries exhausted", mission_id)
    return dispatch_to_qwen(task_text, mission_id)


def route_and_dispatch(task_text: str, mission_id: str) -> tuple[str, str]:
    """Route task and dispatch. Returns (engine, result)."""
    engine = _route(task_text, mission_id)
    if engine == "claude":
        result = dispatch_to_claude(task_text, mission_id)
    else:
        result = dispatch_to_qwen(task_text, mission_id)
    return engine, result


# ── Six Hard Stops ────────────────────────────────────────────────────────────
class StopReason(Enum):
    MAX_ITERATIONS = "MAX_ITERATIONS"
    TTL_EXCEEDED = "TTL_EXCEEDED"
    TOKEN_BUDGET = "TOKEN_BUDGET"
    DEADLOCK = "DEADLOCK"
    EXPLICIT_COMPLETE = "EXPLICIT_COMPLETE"
    BLIND_PASSTHROUGH = "BLIND_PASSTHROUGH"


def check_hard_stops(
    mission_id: str,
    iterations: int,
    start_time: datetime,
    tokens_used: int,
    last_statuses: list[str],
    next_action: str,
    explicit_complete: bool = False,
) -> StopReason | None:
    """Evaluate all 6 hard stops. Returns first triggered, or None."""

    # 1. Max iterations
    if iterations >= MAX_ITERATIONS:
        return StopReason.MAX_ITERATIONS

    # 2. TTL
    elapsed = datetime.now(timezone.utc) - start_time
    if elapsed > timedelta(hours=MAX_TTL_HOURS):
        return StopReason.TTL_EXCEEDED

    # 3. Token budget
    if tokens_used >= MAX_TOKENS:
        return StopReason.TOKEN_BUDGET

    # 4. Deadlock — status unchanged for DEADLOCK_THRESHOLD consecutive iterations
    if len(last_statuses) >= DEADLOCK_THRESHOLD:
        recent = last_statuses[-DEADLOCK_THRESHOLD:]
        if len(set(recent)) == 1:  # all identical
            return StopReason.DEADLOCK

    # 5. Explicit COMPLETE
    if explicit_complete:
        return StopReason.EXPLICIT_COMPLETE

    # 6. No blind pass-through — next action must be from whitelist
    if next_action and next_action not in ALLOWED_ACTIONS:
        return StopReason.BLIND_PASSTHROUGH

    return None


# ── Mission Runner ────────────────────────────────────────────────────────────
def run_mission(mission_id: str, task_text: str) -> dict:
    """
    Execute a mission through the NEXUS state machine.
    Returns final state dict.
    """
    audit("MISSION_START", f"task={task_text[:80]}", mission_id)

    board = load_board()
    mission = find_mission(board, mission_id)
    if mission is None:
        audit("MISSION_NOT_FOUND", mission_id)
        return {"error": f"Mission {mission_id} not found on board"}

    start_time = datetime.now(timezone.utc)
    iterations = 0
    tokens_used = 0
    last_statuses: list[str] = []
    stop_reason: StopReason | None = None
    results: list[dict] = []

    # Update board: mission is running
    mission["status"] = "running"
    mission["nexus_started"] = start_time.isoformat()
    append_mission_log(board, mission_id, f"NEXUS started — task: {task_text[:80]}")
    save_board(board)

    # ── State Machine Loop ────────────────────────────────────────────────────
    current_task = task_text
    explicit_complete = False
    next_action = "route_to_qwen"  # default first action

    while True:
        iterations += 1
        audit("ITERATION", f"#{iterations} | action={next_action}", mission_id)

        # ── Check hard stops before each iteration ────────────────────────
        stop_reason = check_hard_stops(
            mission_id=mission_id,
            iterations=iterations,
            start_time=start_time,
            tokens_used=tokens_used,
            last_statuses=last_statuses,
            next_action=next_action,
            explicit_complete=explicit_complete,
        )
        if stop_reason:
            audit("HARD_STOP", stop_reason.value, mission_id)
            break

        # ── Dispatch ──────────────────────────────────────────────────────
        engine, result = route_and_dispatch(current_task, mission_id)

        # Estimate tokens (rough: 1 token ≈ 4 chars)
        tokens_used += (len(current_task) + len(result)) // 4

        # ── Parse result for state signals ───────────────────────────────
        result_lower = result.lower()
        if "complete" in result_lower or "done" in result_lower or "finished" in result_lower:
            explicit_complete = True
            next_action = "mark_complete"
        elif "deadlock" in result_lower or "blocked" in result_lower or "stuck" in result_lower:
            next_action = "mark_deadlock"
        elif "escalate" in result_lower or "commander" in result_lower:
            next_action = "escalate_commander"
        else:
            # Continue iterating — route again
            next_action = "route_to_claude" if engine == "qwen" else "route_to_qwen"

        # ── Track status for deadlock detection ───────────────────────────
        last_statuses.append(next_action)

        # ── Log iteration result ──────────────────────────────────────────
        iteration_record = {
            "iteration": iterations,
            "engine": engine,
            "action": next_action,
            "tokens_this_iter": (len(current_task) + len(result)) // 4,
            "tokens_total": tokens_used,
            "result_preview": result[:200],
        }
        results.append(iteration_record)
        board = load_board()
        append_mission_log(board, mission_id, f"Iter {iterations}/{MAX_ITERATIONS}: {engine} → {next_action}")
        save_board(board)

        # If explicit complete, one more check on the loop entry will catch it
        if explicit_complete:
            stop_reason = StopReason.EXPLICIT_COMPLETE
            break

    # ── Finalize mission ──────────────────────────────────────────────────────
    board = load_board()
    mission = find_mission(board, mission_id)

    final_status = _resolve_final_status(stop_reason)
    if mission:
        mission["status"] = final_status
        mission["nexus_completed"] = datetime.now(timezone.utc).isoformat()
        mission["stop_reason"] = stop_reason.value if stop_reason else "UNKNOWN"
        mission["iterations_used"] = iterations
        mission["tokens_used"] = tokens_used
        append_mission_log(board, mission_id, f"NEXUS STOP: {stop_reason.value} after {iterations} iter / {tokens_used} tokens")

        if final_status == "completed":
            active = board.get("active_missions", [])
            if mission in active:
                active.remove(mission)
            board.setdefault("completed_missions", []).append(mission)
        elif final_status == "escalated":
            _escalate_to_commander(mission_id, stop_reason, results)

    save_board(board)
    audit("MISSION_END", f"stop={stop_reason.value if stop_reason else '?'} | iter={iterations} | tokens={tokens_used}", mission_id)

    return {
        "mission_id": mission_id,
        "stop_reason": stop_reason.value if stop_reason else "UNKNOWN",
        "final_status": final_status,
        "iterations": iterations,
        "tokens_used": tokens_used,
        "results": results,
    }


def _resolve_final_status(stop_reason: StopReason | None) -> str:
    if stop_reason == StopReason.EXPLICIT_COMPLETE:
        return "completed"
    if stop_reason in (StopReason.DEADLOCK, StopReason.MAX_ITERATIONS, StopReason.TTL_EXCEEDED, StopReason.TOKEN_BUDGET):
        return "escalated"
    if stop_reason == StopReason.BLIND_PASSTHROUGH:
        return "blocked"
    return "error"


def _escalate_to_commander(mission_id: str, stop_reason: StopReason, results: list):
    """Append escalation notice to claude_inbox for COS/Commander review."""
    entry = (
        f"\n---\n"
        f"**NEXUS ESCALATION** | {datetime.now(timezone.utc).isoformat()[:19]}\n"
        f"Mission: {mission_id}\n"
        f"Stop reason: {stop_reason.value}\n"
        f"Last action: {results[-1].get('action', '?') if results else '?'}\n"
        f"Iterations used: {len(results)}/{MAX_ITERATIONS}\n"
        f"status:PENDING_COMMANDER\n"
    )
    try:
        with open(CLAUDE_INBOX, "a") as f:
            f.write(entry)
        audit("ESCALATION_WRITTEN", f"mission={mission_id} → claude_inbox", mission_id)
    except Exception as e:
        audit("ESCALATION_FAIL", str(e), mission_id)


# ── Suspense Watch ────────────────────────────────────────────────────────────
def check_suspense_alerts():
    """Page Commander for missions within 24h of suspense deadline."""
    board = load_board()
    now = datetime.now(timezone.utc)
    threshold = now + timedelta(hours=24)
    alerts = []

    for m in board.get("active_missions", []):
        suspense_str = m.get("suspense_date")
        if not suspense_str:
            continue
        try:
            suspense = datetime.fromisoformat(suspense_str.replace("Z", "+00:00"))
        except ValueError:
            continue

        if suspense <= threshold and m.get("status") != "completed":
            alerts.append(m)

    if alerts:
        audit("SUSPENSE_ALERT", f"{len(alerts)} mission(s) within 24h of deadline")
        _write_routing_log(f"SUSPENSE ALERT: {', '.join(a['id'] for a in alerts)}")

    return alerts


def _write_routing_log(message: str):
    """Append-only write to routing_log.md."""
    entry = f"\n[{datetime.now(timezone.utc).isoformat()[:19]}] NEXUS: {message}\n"
    try:
        with open(ROUTING_LOG, "a") as f:
            f.write(entry)
    except Exception as e:
        audit("ROUTING_LOG_FAIL", str(e))


# ── Inbox Scanner & Telegram Page ─────────────────────────────────────────────
INBOX_STATE_FILE = BASE_DIR / "nexus_inbox_state.json"

TELEGRAM_BOT_TOKEN = ""
TELEGRAM_COMMANDER_ID = ""

def _load_telegram_creds():
    """Load Telegram creds from .env without importing dotenv."""
    global TELEGRAM_BOT_TOKEN, TELEGRAM_COMMANDER_ID
    env_path = Path("/home/john/Thunderbird/.env")
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k == "TELEGRAM_BOT_TOKEN":
            TELEGRAM_BOT_TOKEN = v
        elif k == "TELEGRAM_COMMANDER_ID":
            TELEGRAM_COMMANDER_ID = v

_load_telegram_creds()

def _send_telegram_page(message: str) -> bool:
    """Send Telegram message to Commander. Returns True on success."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_COMMANDER_ID:
        audit("TELEGRAM_FAIL", "Missing credentials")
        return False
    import urllib.request
    import urllib.parse
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": TELEGRAM_COMMANDER_ID,
        "text": f"🔔 NEXUS ALERT:\n{message}",
        "parse_mode": "Markdown",
    }).encode()
    try:
        req = urllib.request.Request(url, data=data, method="POST")
        urllib.request.urlopen(req, timeout=10)
        audit("TELEGRAM_PAGE_SENT", message[:100])
        return True
    except Exception as e:
        audit("TELEGRAM_PAGE_FAIL", str(e))
        return False

def _load_inbox_state() -> dict:
    if INBOX_STATE_FILE.exists():
        try:
            return json.loads(INBOX_STATE_FILE.read_text())
        except json.JSONDecodeError:
            pass
    return {"goose_last_line": 0, "claude_last_line": 0}

def _save_inbox_state(state: dict):
    INBOX_STATE_FILE.write_text(json.dumps(state))

def _scan_inbox_file(filepath: Path, last_line: int) -> list:
    """Return new NEXUS: prefixed tasks appended since last scan.

    Handles file-shrink: if the inbox was truncated or rewritten to have
    fewer lines than last_line, resets last_line to 0 so we re-scan from
    the top instead of getting an empty slice (or IndexError).
    """
    if not filepath.exists():
        return []
    lines = filepath.read_text().splitlines()
    # Detect file shrink — reset to avoid empty slice or stale offset
    if len(lines) < last_line:
        last_line = 0
    new_lines = lines[last_line:]
    tasks = []
    for i, line in enumerate(new_lines):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.upper().startswith(("NEXUS:", "EXEC:", "TASK:", "MISSION:")):
            tasks.append({
                "text": stripped,
                "source": filepath.name,
                "line_offset": i,
            })
    return tasks

def scan_inboxes() -> list:
    """Scan all inboxes for new tasks. Assigns auto-mission IDs if none present."""
    state = _load_inbox_state()
    all_tasks = []

    for inbox_path, state_key in [(GOOSE_INBOX, "goose_last_line"), (CLAUDE_INBOX, "claude_last_line")]:
        last_line = state.get(state_key, 0)
        new_tasks = _scan_inbox_file(inbox_path, last_line)
        all_tasks.extend(new_tasks)
        if new_tasks:
            total = len(open(str(inbox_path), "r").readlines())
            state[state_key] = total

    _save_inbox_state(state)
    return all_tasks


# ── Daemon Mode ───────────────────────────────────────────────────────────────
def daemon_loop(poll_seconds: int = 60):
    """
    Continuous loop: check suspense watch + drain goose_inbox for NEXUS: tasks.
    Runs until SIGTERM.
    """
    lock = NexusLock()
    lock.acquire()

    def _shutdown(signum, frame):
        audit("DAEMON_SHUTDOWN", f"signal={signum}")
        lock.release()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    audit("DAEMON_START", f"poll_interval={poll_seconds}s")

    try:
        while True:
            # 1. Scan inboxes for new NEXUS: / EXEC: / TASK: tasks
            new_tasks = scan_inboxes()
            for task in new_tasks:
                audit("INBOX_TASK_DETECTED", task["text"][:100], f"src={task['source']}")
                # Extract task text—strip prefix
                txt = task["text"]
                for prefix in ("NEXUS:", "EXEC:", "TASK:", "MISSION:"):
                    if txt.upper().startswith(prefix):
                        txt = txt[len(prefix):].strip()
                        break
                
                # Assign mission ID from board
                board = load_board()
                active = board.get("active_missions", [])
                if not active or active[-1].get("status") == "completed":
                    # Create new mission entry
                    board.setdefault("active_missions", [])
                    existing_ids = [m["id"] for state in ["active_missions", "suspended_missions", "completed_missions"]
                                    for m in board.get(state, [])]
                    mid = f"MISSION-{len(existing_ids) + 1:03d}"
                    from datetime import timezone, datetime
                    board["active_missions"].append({
                        "id": mid,
                        "title": txt[:80],
                        "status": "running",
                        "priority": "P1",
                        "assigned_to": "NEXUS (auto)",
                        "description": txt,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                        "logs": [f"[{datetime.now(timezone.utc).isoformat()[:19]}] Auto-created from inbox"]
                    })
                    save_board(board)
                    mid_to_use = mid
                else:
                    mid_to_use = active[-1]["id"]
                
                # Route and dispatch
                engine, result = route_and_dispatch(txt, mid_to_use)
                _send_telegram_page(f"NEXUS | {mid_to_use} → {engine.upper()}\n{result[:200]}")
            
            # 2. Check suspense alerts + page if needed
            alerts = check_suspense_alerts()
            if alerts:
                for a in alerts:
                    _send_telegram_page(
                        f"⏰ SUSPENSE WARNING: {a['id']} — {a.get('title', '?')}\n"
                        f"Due: {a.get('suspense_date', '?')[:16]} | Status: {a.get('status', '?')}"
                    )
            
            time.sleep(poll_seconds)
    finally:
        lock.release()


# ── CLI ───────────────────────────────────────────────────────────────────────
def _usage():
    print("""
NEXUS — Autonomous War Room Orchestrator

Usage:
  nexus.py run <mission_id> "<task>"  Run a task against a mission
  nexus.py suspense                   Check suspense alerts
  nexus.py daemon [<poll_secs>]       Run continuous daemon (default 60s)
  nexus.py status                     Show lock file status

Examples:
  nexus.py run MISSION-001 "Draft Furlow validation email"
  nexus.py daemon 120
  nexus.py suspense
""")


if __name__ == "__main__":
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help", "help"):
        _usage()
        sys.exit(0)

    cmd = args[0].lower()

    if cmd == "run":
        if len(args) < 3:
            print("Usage: nexus.py run <mission_id> \"<task>\"")
            sys.exit(1)
        mission_id = args[1]
        task_text = " ".join(args[2:])
        result = run_mission(mission_id, task_text)
        print(json.dumps(result, indent=2))

    elif cmd == "suspense":
        alerts = check_suspense_alerts()
        if alerts:
            print(f"⚠️  {len(alerts)} mission(s) within 24h of suspense deadline:")
            for a in alerts:
                print(f"  {a['id']}: {a['title']} — due {a.get('suspense_date', '?')[:16]}")
        else:
            print("✅ No suspense alerts")

    elif cmd == "daemon":
        poll = int(args[1]) if len(args) > 1 else 60
        daemon_loop(poll)

    elif cmd == "status":
        if NEXUS_LOCK.exists():
            try:
                data = json.loads(NEXUS_LOCK.read_text())
                print(f"NEXUS RUNNING — PID={data.get('pid')} | started={data.get('started', '?')[:19]} | heartbeat={data.get('heartbeat', 'none')[:19]}")
            except Exception:
                print("NEXUS LOCK EXISTS (unreadable)")
        else:
            print("NEXUS IDLE — no lock file")

    else:
        print(f"Unknown command: {cmd}")
        _usage()
        sys.exit(1)
