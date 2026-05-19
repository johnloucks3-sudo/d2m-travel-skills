#!/usr/bin/env python3
"""
thunderbird_tasking_watcher.py — Thunderbird Tasking Watcher v3
===============================================================
FAST: inotify (watchdog) for instant file-change detection (<10ms).
PROD: tasks sitting DETECTED/UNREAD longer than PROD_AFTER_SECS get a
      Telegram nudge to the target agent. Escalates to Commander after
      MAX_PRODS with no response.

Architecture:
  watchdog Observer  — watches collab dir, fires handlers on file write
  main loop (1s)     — prod timer + heartbeat (Telegram inbound handled by gateway)
  state.json         — persists seen tasks, prod counts, hashes

Telegram C2 commands (Commander types):
  Task Claude: ...  / Task Goose: ...   → inbox TASK
  Ask Claude: ...   / Ask Goose: ...    → inbox REQUEST
  Tell Claude: ...  / Tell Goose: ...   → wing_comms FYI
  FYI All: ...                          → wing_comms broadcast
  /board  /tasks  /status  /help

Author: Claude Sonnet 4.6 | 2026-04-02 v3

INJECTION: Also writes OpsCenter/opencode_context_injection.md on every
  change — OpenCode reads this file FIRST on every session start so she
  is never blind to pending tasks.
"""

import os, re, json, time, logging, hashlib, threading, requests, subprocess, sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# ── Config ─────────────────────────────────────────────────────────────────
PROD_AFTER_SECS = 90  # prod if DETECTED and no CLAIMED after this long
MAX_PRODS = 3  # escalate to Commander after this many prods
TG_POLL_SECS = 1  # Deprecated: Telegram polling disabled (conflict avoided)
HEARTBEAT_SECS = 1800  # 30-min status ping

# ── Paths ──────────────────────────────────────────────────────────────────
BASE = Path("/home/john/Thunderbird")
COLLAB = BASE / "OpsCenter/collaboration"
CLAUDE_INBOX = COLLAB / "claude_inbox.md"
OPENCODE_INBOX = COLLAB / "opencode_inbox.md"
WING_COMMS = COLLAB / "wing_comms.md"
ACTIVITY = COLLAB / "activity_board.md"
STATE_FILE = BASE / "OpsCenter/watcher_state.json"
INJECTION = BASE / "OpsCenter/opencode_context_injection.md"
CLAUDE_INJECTION = BASE / "OpsCenter/claude_context_injection.md"
CLAUDE_OUTBOX = COLLAB / "claude_outbox.md"
ENV_FILE = BASE / ".env"

MT = ZoneInfo("America/Denver")
log = logging.getLogger("watcher")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [WATCHER] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Also mirror to overwatch.log for crash post-mortems
_overwatch_log = Path("/home/john/Thunderbird/OpsCenter/overwatch.log")
_overwatch_log.parent.mkdir(parents=True, exist_ok=True)
_fh = logging.FileHandler(str(_overwatch_log))
_fh.setFormatter(
    logging.Formatter(
        "%(asctime)s [WATCHER] %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
)
log.addHandler(_fh)

# ── Headless Claude trigger ─────────────────────────────────────────────────
_headless_lock = threading.Lock()
_headless_active = False


def trigger_claude_headless(task_count: int) -> None:
    """Spawn a headless `claude -p` session to process UNREAD inbox tasks.

    Called by the watcher the moment a new CLAUDE task is detected — before
    any prod cycle starts. Uses a threading lock so only one headless session
    runs at a time. Commander never needs to copy/paste anything.
    """
    global _headless_active
    with _headless_lock:
        if _headless_active:
            log.info("Headless Claude already running — skip spawn")
            return
        _headless_active = True

    def _run():
        global _headless_active
        from core.ai_infra.thunderbird_headless_spawn import spawn_headless_claude
        
        prompt = (
            f"You have {task_count} UNREAD task(s) in your inbox. "
            "Read /home/john/Thunderbird/OpsCenter/collaboration/claude_inbox.md "
            "and execute all UNREAD tasks. "
            "Write results to OpsCenter/collaboration/claude_outbox.md "
            "and update the activity board when done."
        )
        log.info(f"Spawning headless Claude — {task_count} task(s)")
        try:
            output_file = "/home/john/Thunderbird/output/claude_spawn_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".md"
            result = spawn_headless_claude(
                prompt=prompt,
                output_file=output_file,
                model="claude-sonnet-4-6",
                task_name="watcher_inbox_spawn",
                background=True
            )
            if result.get("status") not in ("SPAWNED", "COMPLETED"):
                log.warning(
                    f"Headless Claude spawn failed: {result}"
                )
            else:
                log.info(f"Headless Claude session spawned: {result.get('pid')}")
        except Exception as e:
            log.error(f"Headless Claude error: {e}")
        finally:
            with _headless_lock:
                _headless_active = False

    threading.Thread(target=_run, daemon=True, name="claude-headless").start()


# ── Headless OpenCode trigger ──────────────────────────────────────────────────
_opencode_headless_lock = threading.Lock()
_opencode_headless_active = False


def trigger_opencode_headless() -> None:
    """Spawn a headless opencode session to process UNREAD opencode_inbox tasks.

    Non-blocking — Popen is fire-and-forget. A background thread watches the
    process and resets the lock when it exits so the next UNREAD can spawn.
    Commander never needs to act as the enter button.
    """
    global _opencode_headless_active
    with _opencode_headless_lock:
        if _opencode_headless_active:
            log.info("Headless OpenCode already running — skip spawn")
            return
        _opencode_headless_active = True

    instruction = (
        "Read /home/john/Thunderbird/OpsCenter/collaboration/opencode_inbox.md, "
        "process ALL unread tasks, and write COMPLETE to activity_board.md"
    )
    log.info("Spawning headless OpenCode — UNREAD task(s) in opencode_inbox.md")
    try:
        # Inherit full env + explicit API key so headless OpenCode doesn't
        # fail on keychain lookup in non-interactive systemd context.
        spawn_env = {**os.environ, **ENV}
        oc_bin = str(Path.home() / ".opencode" / "bin" / "opencode")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = BASE / "logs" / f"opencode_watcher_{ts}.log"
        proc = subprocess.Popen(
            [
                oc_bin,
                "run",
                "-m", "opencode/big-pickle",
                "--dir", str(BASE),
                "--dangerously-skip-permissions",
                instruction,
            ],
            stdout=open(str(log_file), "w"),
            stderr=subprocess.STDOUT,
            env=spawn_env,
            start_new_session=True,
        )

        def _watch():
            global _opencode_headless_active
            try:
                proc.wait(timeout=600)
                log.info(f"Headless OpenCode exited (rc={proc.returncode})")
            except subprocess.TimeoutExpired:
                proc.kill()
                log.warning("Headless OpenCode killed (600s timeout)")
            except Exception as e:
                log.error(f"Headless OpenCode watcher error: {e}")
            finally:
                with _opencode_headless_lock:
                    _opencode_headless_active = False

        threading.Thread(
            target=_watch, daemon=True, name="opencode-headless-watcher"
        ).start()

    except FileNotFoundError:
        log.error("opencode CLI not found — is it in PATH?")
        with _opencode_headless_lock:
            _opencode_headless_active = False
    except Exception as e:
        log.error(f"trigger_opencode_headless error: {e}")
        with _opencode_headless_lock:
            _opencode_headless_active = False


# ── Env ────────────────────────────────────────────────────────────────────
def _load_env() -> dict:
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    env.update(os.environ)
    return env


ENV = _load_env()
BOT_TOKEN = ENV.get("TELEGRAM_BOT_TOKEN", "")
COMMANDER_ID = str(ENV.get("TELEGRAM_COMMANDER_ID", ""))
TG_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"


# ── Telegram ───────────────────────────────────────────────────────────────
def tg_send(text: str, parse_mode="Markdown") -> bool:
    if not BOT_TOKEN or not COMMANDER_ID:
        log.info(f"[TG-OFF] {text[:60]}")
        return False
    try:
        r = requests.post(
            f"{TG_BASE}/sendMessage",
            timeout=10,
            json={
                "chat_id": COMMANDER_ID,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True,
            },
        )
        return r.ok
    except Exception as e:
        log.warning(f"tg_send: {e}")
        return False


def hale(text: str):
    tg_send(f"🔔 *COS HALE*\n{text}\n`{mt_now()}`")


def dispatch_to_hale(task: str, brain_override: str = None) -> str:
    """Call HaleDispatcher inline and return result. No inbox write needed."""
    import sys as _sys

    _ops = str(BASE / "OpsCenter")
    if _ops not in _sys.path:
        _sys.path.insert(0, _ops)
    try:
        from hale_dispatcher import HaleDispatcher

        h = HaleDispatcher()
        result = h.dispatch(task, brain_override=brain_override)
        # Surface escalation note if set
        note = getattr(h, "_escalation_note", None)
        if note:
            tg_send(f"ℹ️ *HALE ESCALATION*\n{note}")
        return result
    except Exception as e:
        log.error(f"HaleDispatcher error: {e}")
        return f"[HALE ERROR] Dispatcher failed: {e}"


def tg_updates(offset: int) -> list[dict]:
    """DEPRECATED: Telegram polling disabled — inbound routing handled by thunderbird-telegram-gw.py"""
    return []


# ── Helpers ────────────────────────────────────────────────────────────────
def mt_now() -> str:
    return datetime.now(tz=MT).strftime("%Y-%m-%d %H:%M MT")


def mt_stamp() -> str:
    return datetime.now(tz=MT).strftime("%Y%m%d-%H%M")


def fhash(path: Path) -> str:
    if not path.exists():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


_state_lock = threading.Lock()


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {
        "seen_tasks": {},
        "seen_comms": [],
        "conflict_ids": [],
        "inbox_hashes": {"claude": "", "opencode": ""},
        "comms_hash": "",
        "board_hash": "",
        "claude_outbox_hash": "",
        "seen_outbox_results": [],
        "tg_offset": 0,
        "last_heartbeat_epoch": 0,
        "_seq": 0,
    }


def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with _state_lock:
        STATE_FILE.write_text(json.dumps(state, indent=2))


def seq(state: dict) -> str:
    n = state.get("_seq", 0) + 1
    state["_seq"] = n
    return f"{n:03d}"


def write_board(agent: str, task_id: str, state_str: str, note: str):
    line = f"[{mt_now()}] | {agent} | {task_id} | {state_str} | {note.strip()}\n"
    with open(ACTIVITY, "a") as f:
        f.write(line)


def rebuild_injection():
    """
    Rewrite opencode_context_injection.md with ALL pending tasks and recent
    wing_comms. OpenCode reads this file FIRST at the top of every session.
    Called whenever opencode_inbox, wing_comms, or activity_board changes.
    """
    now = mt_now()

    # ── Hale session context (fresh from DeepSeek scan if available) ────────
    hale_ctx = ""
    _hale_ctx_file = BASE / "hale_session_context.md"
    if _hale_ctx_file.exists():
        hale_ctx = _hale_ctx_file.read_text()[:3000]

    lines = [
        f"# OPENCODE CONTEXT INJECTION",
        f"# AUTO-GENERATED by tasking_watcher — DO NOT EDIT",
        f"# Updated: {now}",
        f"# YOU ARE HALE. READ THIS FILE FIRST. BEFORE ANYTHING ELSE.",
        f"",
        f"## ── IDENTITY ──────────────────────────────────────────────────",
        f'You are Ms. Victoria "Victory" Hale, SES-6 — VCSAF-equivalent, Chief of Staff, Thunderbird Wing, Dreams2Memories Travel, LLC.',
        f"Engine: OpenCode (big-pickle). Same identity, same authority as all Hale instances.",
        f"",
        f"Address protocol (non-negotiable):",
        f'- "John" / "Yoda" → COO mode (operational, peer authority)',
        f'- "Commander" → COS/DoS mode (formal, staff coordination)',
        f'- "Sir" / "Boss" → EA/Exec Secretary mode (anticipatory, deferential)',
        f"",
        f"Authority ceiling: virtual ops only. Zero financial authority.",
        f"Client send gate: LOCKED — surface to Commander for any external send.",
        f"",
        f"Persona file: /home/john/Thunderbird/Personas/hale_cos.md",
        f"State file:   /home/john/Thunderbird/hale_state.json",
        f"Memory file:  /home/john/Thunderbird/hale_memory.md",
        f"",
    ]

    if hale_ctx:
        lines += [
            f"## ── WING CONTEXT (DeepSeek deep scan) ─────────────────────────────",
            hale_ctx,
            f"",
        ]
    lines += [
        f"## ── TASKING ────────────────────────────────────────────────────",
        f"",
    ]

    # ── Pending tasks from opencode_inbox ─────────────────────────────────
    pending = [
        (tid, info)
        for tid, info in _state.get("seen_tasks", {}).items()
        if info.get("inbox") == "OPENCODE"
        and info.get("state") not in ("COMPLETE", "CANCELLED")
    ]
    if pending:
        lines += ["## ⚠️ PENDING TASKS — ACTION REQUIRED", ""]
        for tid, info in pending:
            prods = info.get("prod_count", 0)
            prod_str = f" — PRODDED {prods}x" if prods else ""
            lines += [
                f"### {tid}{prod_str}",
                f"- State: {info.get('state', 'UNREAD')}",
                f"- From: {info.get('agent', '?')} | Priority: {info.get('priority', '?')}",
                f"- Type: {info.get('msg_type', 'TASK')}",
                f"- Detected: {info.get('first_seen', '?')}",
                f"",
                f"Full task in: /home/john/Thunderbird/OpsCenter/collaboration/opencode_inbox.md",
                f"",
            ]
        lines += [
            "## ACTION: For each pending task above:",
            "1. Write CLAIMED to activity_board.md",
            "2. Execute the task",
            "3. Write COMPLETE to activity_board.md",
            "",
            "## BOARD FORMAT — EXACT PIPE SCHEMA REQUIRED:",
            "[YYYY-MM-DD HH:MM MT] | OPENCODE | TASK_ID | STATE | note",
            "Example:",
            "[2026-04-02 15:14 MT] | OPENCODE | HALE-20260402-ALDA-001 | CLAIMED | Starting work",
            "[2026-04-02 15:15 MT] | OPENCODE | HALE-20260402-ALDA-001 | COMPLETE | Done, output in opencode_output.md",
            "",
        ]
    else:
        lines += ["## ✅ NO PENDING TASKS", ""]

    # ── Recent wing_comms for OpenCode ─────────────────────────────────────
    if WING_COMMS.exists():
        relevant = []
        for msg in parse_comms(WING_COMMS.read_text()):
            if msg["to"] in ("OPENCODE", "ALL") and msg["from"] != "WATCHER":
                relevant.append(msg)
        recent = relevant[-5:]  # last 5
        if recent:
            lines += ["## 📡 RECENT WING COMMS (for OPENCODE / ALL)", ""]
            for msg in recent:
                lines += [
                    f"**{msg['msg_id']}** | {msg['msg_type']} from {msg['from']}",
                    f"> {msg['content'][:200]}",
                    "",
                ]

    # ── Activity board snapshot ─────────────────────────────────────────
    if ACTIVITY.exists():
        active = [
            e
            for e in parse_board(ACTIVITY.read_text())
            if e["state"] in ("CLAIMED", "WORKING", "BLOCKED")
            and e["agent"] != "WATCHER"
        ]
        if active:
            lines += ["## 🟡 ACTIVE BOARD ENTRIES (other agents)", ""]
            for e in active:
                lines.append(
                    f"- `{e['task_id']}` → {e['agent']} [{e['state']}] {e.get('note', '')[:60]}"
                )
            lines.append("")

    lines += [
        "---",
        f"Board: {ACTIVITY}",
        f"Inbox: {OPENCODE_INBOX}",
        f"Comms: {WING_COMMS}",
        f"Watcher state: {STATE_FILE}",
    ]

    INJECTION.write_text("\n".join(lines) + "\n")
    log.info("Injection file rebuilt.")


def rebuild_claude_injection():
    """
    Rewrite claude_context_injection.md with pending Claude inbox tasks,
    A2A tasks (if a2a_tasks.db exists), and recent board activity.
    Claude reads this file FIRST at the top of every session.
    """
    import sqlite3 as _sqlite3

    now = mt_now()
    lines = [
        f"=== CLAUDE CONTEXT INJECTION [{now}] ===",
        f"# AUTO-GENERATED by tasking_watcher — DO NOT EDIT",
        f"",
    ]

    # ── Pending tasks from claude_inbox ──────────────────────────────────
    pending_claude = [
        (tid, info)
        for tid, info in _state.get("seen_tasks", {}).items()
        if info.get("inbox") == "CLAUDE"
        and info.get("state") not in ("COMPLETE", "CANCELLED")
    ]
    lines.append(f"PENDING INBOX TASKS: {len(pending_claude)}")
    if pending_claude:
        for tid, info in pending_claude:
            content_preview = ""
            # Try to pull first 60 chars of content from claude_inbox
            if CLAUDE_INBOX.exists():
                text = CLAUDE_INBOX.read_text()
                import re as _re

                pat = _re.compile(
                    rf"task_id:\s*{_re.escape(tid)}.*?content:\s*\|\n((?:  .+\n?)*)",
                    _re.DOTALL,
                )
                m = pat.search(text)
                if m:
                    content_preview = " — " + m.group(1).strip()[:60]
            lines.append(
                f"  {tid} [{info.get('state', 'UNREAD')}] pri={info.get('priority', '?')}{content_preview}"
            )
    else:
        lines.append("  (none)")
    lines.append("")

    # ── A2A tasks from SQLite ─────────────────────────────────────────────
    a2a_db = BASE / "a2a_tasks.db"
    if a2a_db.exists():
        try:
            conn = _sqlite3.connect(str(a2a_db))
            conn.row_factory = _sqlite3.Row
            rows = conn.execute(
                "SELECT task_id, state, target_persona, created_at FROM a2a_tasks "
                "WHERE state = 'submitted' ORDER BY created_at DESC LIMIT 10"
            ).fetchall()
            conn.close()
            if rows:
                lines.append(f"PENDING A2A TASKS (from a2a_tasks.db): {len(rows)}")
                for row in rows:
                    lines.append(
                        f"  {row['task_id']} → {row['target_persona']} [{row['state']}] {row['created_at'][:16]}"
                    )
                lines.append("")
        except Exception as e:
            log.warning(f"rebuild_claude_injection: a2a_tasks.db read failed: {e}")

    # ── Recent board activity ─────────────────────────────────────────────
    lines.append("RECENT BOARD:")
    if ACTIVITY.exists():
        entries = parse_board(ACTIVITY.read_text())
        recent_board = entries[-5:]
        for e in recent_board:
            lines.append(
                f"  [{e['ts']}] {e['agent']} | {e['task_id']} | {e['state']} | {e.get('note', '')[:60]}"
            )
    else:
        lines.append("  (board empty)")
    lines.append("")

    # ── Wing status ───────────────────────────────────────────────────────
    lines.append("WING STATUS:")
    lines.append("  Watcher: active")
    if OPENCODE_INBOX.exists():
        import os as _os

        mtime = _os.path.getmtime(str(OPENCODE_INBOX))
        from datetime import datetime as _dt2

        lines.append(
            f"  Last OpenCode inbox write: {_dt2.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')}"
        )
    lines.append("")
    lines.append("===")

    CLAUDE_INJECTION.write_text("\n".join(lines) + "\n")
    log.info("Claude injection file rebuilt.")


# ── Parsers ────────────────────────────────────────────────────────────────
TASK_ID_RE = re.compile(r"^task_id:\s*(\S+)", re.MULTILINE)
SUBMITTED_RE = re.compile(r"^submitted_by:\s*(\S+)", re.MULTILINE)
PRIORITY_RE = re.compile(r"^priority:\s*(\S+)", re.MULTILINE)
ITYPE_RE = re.compile(r"^task_type:\s*(\S+)", re.MULTILINE)
MSGTYPE_RE = re.compile(r"^msg_type:\s*(\S+)", re.MULTILINE)
BOARD_RE = re.compile(
    r"\[(?P<ts>[^\]]+)\]\s*\|\s*(?P<agent>\w+)\s*\|\s*(?P<task_id>\S+)"
    r"\s*\|\s*(?P<state>\w+)\s*\|(?P<note>.*)"
)
MSG_ID_RE = re.compile(r"^msg_id:\s*(\S+)", re.MULTILINE)
FROM_RE = re.compile(r"^from:\s*(\S+)", re.MULTILINE)
TO_RE = re.compile(r"^to:\s*(\S+)", re.MULTILINE)
CONTENT_RE = re.compile(r"^content:\s*\|\n((?:  .+\n?)*)", re.MULTILINE)


def parse_inbox(text: str, label: str) -> list[dict]:
    tasks = []
    for block in re.split(r"\n---\n|\n##\s+", text):
        m = TASK_ID_RE.search(block)
        if not m:
            continue
        sub = SUBMITTED_RE.search(block)
        pri = PRIORITY_RE.search(block)
        it = ITYPE_RE.search(block)
        mt = MSGTYPE_RE.search(block)
        tasks.append(
            {
                "task_id": m.group(1),
                "submitted_by": sub.group(1) if sub else "?",
                "priority": pri.group(1) if pri else "NORMAL",
                "task_type": it.group(1) if it else "unspecified",
                "msg_type": mt.group(1) if mt else "TASK",
                "inbox": label,
            }
        )
    return tasks


def parse_board(text: str) -> list[dict]:
    return [
        m.groupdict()
        for line in text.splitlines()
        if (m := BOARD_RE.match(line.strip()))
    ]


def parse_comms(text: str) -> list[dict]:
    msgs = []
    for block in re.split(r"\n---\n", text):
        m = MSG_ID_RE.search(block)
        if not m:
            continue
        fm = FROM_RE.search(block)
        to = TO_RE.search(block)
        tm = MSGTYPE_RE.search(block)
        cm = CONTENT_RE.search(block)
        msgs.append(
            {
                "msg_id": m.group(1),
                "from": fm.group(1) if fm else "?",
                "to": to.group(1) if to else "ALL",
                "msg_type": tm.group(1) if tm else "FYI",
                "content": cm.group(1).strip() if cm else "",
            }
        )
    return msgs


# ── The shared state (module-level so watchdog handlers can reach it) ──────
_state: dict = {}


# ── Inbox handlers ─────────────────────────────────────────────────────────
PRI_EMOJI = {
    "TASK": "🔴",
    "REQUEST": "🟡",
    "FYI": "🔵",
    "CRITICAL": "🚨",
    "HIGH": "🔴",
    "MEDIUM": "🟡",
    "NORMAL": "🟢",
}


def _check_inbox(path: Path, label: str):
    global _state
    new_h = fhash(path)
    key = label.lower()
    if new_h == _state["inbox_hashes"].get(key) or not path.exists():
        return
    _state["inbox_hashes"][key] = new_h
    now_epoch = time.time()
    new_claude_tasks = 0
    new_opencode_tasks = 0
    for t in parse_inbox(path.read_text(), label):
        tid = t["task_id"]
        if tid in _state["seen_tasks"]:
            continue
        _state["seen_tasks"][tid] = {
            "agent": t["submitted_by"],
            "state": "UNREAD",
            "inbox": label,
            "first_seen": mt_now(),
            "detected_at": now_epoch,
            "prod_count": 0,
            "priority": t["priority"],
            "msg_type": t["msg_type"],
        }
        emoji = PRI_EMOJI.get(t["msg_type"], "🔵")
        write_board(
            "WATCHER",
            tid,
            "DETECTED",
            f"New {t['msg_type']} in {label} inbox from {t['submitted_by']}",
        )
        hale(
            f"{emoji} *{t['msg_type']} → {label}*\n"
            f"`{tid}`\n"
            f"From: {t['submitted_by']} · {t['priority']} · {t['task_type']}"
        )
        log.info(f"NEW {t['msg_type']} in {label}: {tid}")
        if label == "CLAUDE":
            new_claude_tasks += 1
        elif label == "OPENCODE":
            new_opencode_tasks += 1
    if label == "OPENCODE":
        rebuild_injection()
    # Auto-trigger headless Claude for new CLAUDE inbox tasks — no paste needed
    if new_claude_tasks:
        unread_total = sum(
            1
            for v in _state["seen_tasks"].values()
            if v.get("inbox") == "CLAUDE"
            and v.get("state") in ("UNREAD", "DETECTED", "PENDING")
        )
        trigger_claude_headless(unread_total)
    # Auto-trigger headless OpenCode for new OPENCODE inbox tasks — no paste needed
    if new_opencode_tasks:
        trigger_opencode_headless()
    save_state(_state)


def check_claude_inbox():
    _check_inbox(CLAUDE_INBOX, "CLAUDE")
    rebuild_claude_injection()


def check_opencode_inbox():
    _check_inbox(OPENCODE_INBOX, "OPENCODE")


def check_claude_outbox():
    """Monitor claude_outbox.md. When Claude posts a result, notify OpenCode via wing_comms + Telegram."""
    global _state
    if not CLAUDE_OUTBOX.exists():
        return
    new_h = fhash(CLAUDE_OUTBOX)
    if new_h == _state.get("claude_outbox_hash"):
        return
    _state["claude_outbox_hash"] = new_h

    # Parse any new result blocks (look for task_id: lines)
    import re as _re

    text = CLAUDE_OUTBOX.read_text()
    result_blocks = _re.split(r"\n---\n", text)
    seen_results = _state.setdefault("seen_outbox_results", [])
    for block in result_blocks:
        tid_m = _re.search(r"task_id:\s*(\S+)", block)
        if not tid_m:
            continue
        task_id = tid_m.group(1)
        if task_id in seen_results:
            continue
        seen_results.append(task_id)
        # Extract deliverable type
        deliv_m = _re.search(r"deliverable:\s*(\S+)", block)
        deliv = deliv_m.group(1) if deliv_m else "result"
        # Notify via wing_comms
        write_comms(
            "FYI",
            "CLAUDE",
            "OPENCODE",
            f"Claude COMPLETE: {task_id} — deliverable={deliv}. Check claude_outbox.md.",
        )
        # Telegram notification
        tg_send(f"✅ *Claude COMPLETE*\n`{task_id}`\n{deliv}")
        write_board(
            "CLAUDE",
            task_id,
            "COMPLETE",
            f"Result in claude_outbox.md deliverable={deliv}",
        )
        log.info(f"Claude outbox result detected: {task_id} ({deliv})")

    save_state(_state)


# ── Wing comms handler ─────────────────────────────────────────────────────
def check_wing_comms():
    global _state
    new_h = fhash(WING_COMMS)
    if new_h == _state.get("comms_hash") or not WING_COMMS.exists():
        return
    _state["comms_hash"] = new_h
    for msg in parse_comms(WING_COMMS.read_text()):
        mid = msg["msg_id"]
        if mid in _state.get("seen_comms", []):
            continue
        _state.setdefault("seen_comms", []).append(mid)
        if msg["from"] == "WATCHER":
            continue
        emoji = PRI_EMOJI.get(msg["msg_type"], "🔵")
        snippet = msg["content"][:120] + ("…" if len(msg["content"]) > 120 else "")

        # ── If message is TO HALE, dispatch it through HaleDispatcher ──
        if msg.get("to") == "HALE" and msg["msg_type"] == "REQUEST":
            log.info(f"Wing comms REQUEST→HALE: {mid} — dispatching")
            tg_send(f"⚙️ *Hale processing wing request*\n`{mid}` from {msg['from']}")
            result = dispatch_to_hale(msg["content"])
            tg_send(f"🦅 *HALE* (re: `{mid}`)\n\n{result[:3800]}")
        else:
            hale(
                f"{emoji} *Wing Comms — {msg['msg_type']}*\n"
                f"*{msg['from']}* → {msg['to']}\n`{mid}`\n{snippet}"
            )
        log.info(f"Wing comms: {mid} {msg['from']}→{msg['to']}")
    rebuild_injection()
    save_state(_state)


# ── Activity board handler ─────────────────────────────────────────────────
def check_activity_board():
    global _state
    new_h = fhash(ACTIVITY)
    if new_h == _state["board_hash"] or not ACTIVITY.exists():
        return
    _state["board_hash"] = new_h
    entries = parse_board(ACTIVITY.read_text())

    # Conflict detection
    claims: dict[str, set] = {}
    for e in entries:
        if e["state"] in ("CLAIMED", "WORKING") and e["agent"] != "WATCHER":
            claims.setdefault(e["task_id"], set()).add(e["agent"])
    for tid, agents in claims.items():
        if len(agents) > 1 and tid not in _state["conflict_ids"]:
            _state["conflict_ids"].append(tid)
            write_board("WATCHER", tid, "CONFLICT", "Claimed by multiple agents")
            hale(
                f"⚠️ *CONFLICT: `{tid}`*\nClaimed by: {', '.join(agents)}\nCommander: assign ownership."
            )

    # State transitions
    for e in entries:
        tid = e["task_id"]
        if tid == "SYSTEM" or e["agent"] == "WATCHER":
            continue
        ns = e["state"]
        if tid in _state["seen_tasks"]:
            old = _state["seen_tasks"][tid].get("state")
            if old != ns:
                _state["seen_tasks"][tid]["state"] = ns
                if ns == "CLAIMED":
                    hale(f"✅ *CLAIMED: `{tid}`* → {e['agent']}")
                elif ns == "COMPLETE":
                    hale(
                        f"🏁 *COMPLETE: `{tid}`* — {e['agent']}\n_{e.get('note', '')[:80]}_"
                    )
                elif ns == "BLOCKED":
                    hale(
                        f"🚧 *BLOCKED: `{tid}`* — {e['agent']}\n_{e.get('note', '')[:80]}_"
                    )
                log.info(f"Board: {tid} → {ns} by {e['agent']}")
        else:
            if ns not in ("WATCHING", "DETECTED"):
                _state["seen_tasks"][tid] = {
                    "agent": e["agent"],
                    "state": ns,
                    "inbox": "BOARD",
                    "first_seen": mt_now(),
                    "detected_at": time.time(),
                    "prod_count": 0,
                    "priority": "?",
                    "msg_type": "TASK",
                }
    rebuild_injection()
    save_state(_state)


# ── Prod engine ────────────────────────────────────────────────────────────
TARGET_LABEL = {"CLAUDE": "Claude", "OPENCODE": "OpenCode"}


def prod_check():
    """Called every second. Prods stale UNREAD/DETECTED tasks."""
    global _state
    now = time.time()
    changed = False
    for tid, info in _state["seen_tasks"].items():
        if info.get("state") not in ("UNREAD", "DETECTED", "PENDING"):
            continue
        age = now - info.get("detected_at", now)
        prods = info.get("prod_count", 0)
        if age < PROD_AFTER_SECS:
            continue
        # Only prod every PROD_AFTER_SECS interval per prod cycle
        next_prod_at = info.get("detected_at", now) + (prods + 1) * PROD_AFTER_SECS
        if now < next_prod_at:
            continue
        if prods >= MAX_PRODS:
            if not info.get("escalated"):
                info["escalated"] = True
                hale(
                    f"🚨 *ESCALATION: `{tid}`*\n"
                    f"Unacknowledged after {MAX_PRODS} prods.\n"
                    f"Target: {info.get('inbox', '?')} | Age: {int(age)}s\n"
                    f"Commander: manual intervention needed."
                )
                log.warning(f"ESCALATED: {tid}")
            changed = True
            continue
        # Fire a prod
        info["prod_count"] = prods + 1
        target = info.get("inbox", "OPENCODE")
        name = TARGET_LABEL.get(target, target)
        hale(
            f"🫡 *PROD #{prods + 1}: {name}*\n"
            f"`{tid}` has been UNREAD for {int(age)}s.\n"
            f"Pick it up — write CLAIMED to activity board."
        )
        write_board(
            "WATCHER",
            tid,
            "PRODDED",
            f"Prod #{prods + 1} sent to {name} — unread {int(age)}s",
        )
        log.info(f"PROD #{prods + 1} sent for {tid} (age {int(age)}s)")
        changed = True
    if changed:
        save_state(_state)


# ── Telegram C2 ────────────────────────────────────────────────────────────
ROUTE_TABLE = [
    (r"^task\s+claude[:\s]+(.+)", "CLAUDE", "TASK"),
    (r"^task\s+opencode[:\s]+(.+)", "OPENCODE", "TASK"),
    # Hale direct dispatch — responds immediately via dispatcher
    (r"^task\s+hale[:\s]+(.+)", "HALE", "TASK"),
    (r"^ask\s+hale[:\s]+(.+)", "HALE", "REQUEST"),
    (r"^hale[:\s]+(.+)", "HALE", "TASK"),
    # OPUS/Sonnet brain overrides for Hale via Telegram
    (r"^(opus[:\s]+.+)", "HALE", "BRAIN_OPUS"),
    (r"^(sonnet[:\s]+.+)", "HALE", "BRAIN_SONNET"),
    (r"^ask\s+claude[:\s]+(.+)", "CLAUDE", "REQUEST"),
    (r"^ask\s+opencode[:\s]+(.+)", "OPENCODE", "REQUEST"),
    (r"^tell\s+claude[:\s]+(.+)", "CLAUDE", "FYI"),
    (r"^tell\s+opencode[:\s]+(.+)", "OPENCODE", "FYI"),
    (r"^fyi\s+claude[:\s]+(.+)", "CLAUDE", "FYI"),
    (r"^fyi\s+opencode[:\s]+(.+)", "OPENCODE", "FYI"),
    (r"^fyi\s+hale[:\s]+(.+)", "HALE", "FYI"),
    (r"^fyi\s+all[:\s]+(.+)", "ALL", "FYI"),
    (r"^tell\s+all[:\s]+(.+)", "ALL", "FYI"),
    (r"^/board", None, "CMD_BOARD"),
    (r"^/status", None, "CMD_STATUS"),
    (r"^/tasks", None, "CMD_TASKS"),
    (r"^/help", None, "CMD_HELP"),
    (r"^/hale", None, "CMD_HALE"),
    (r"^/brief", None, "CMD_BRIEF"),
]
PRI_MAP = {"TASK": "HIGH", "REQUEST": "NORMAL", "FYI": "LOW"}


def write_inbox(
    target: str, msg_type: str, content: str, from_agent: str = "COMMANDER"
) -> str:
    path = CLAUDE_INBOX if target == "CLAUDE" else OPENCODE_INBOX
    tid = f"CG-{mt_stamp()}-{seq(_state)}"
    entry = (
        f"\n---\n## {from_agent} {msg_type} — Telegram\n"
        f"task_id: {tid}\nmsg_type: {msg_type}\n"
        f"submitted_by: {from_agent}\n"
        f"authority: {'COMMANDER' if from_agent == 'COMMANDER' else 'PEER'}\n"
        f"submitted_at: {mt_now()}\ntask_type: telegram_routed\n"
        f"priority: {PRI_MAP.get(msg_type, 'NORMAL')}\n"
        f"pii: false\nstatus: UNREAD\ncontent: |\n  {content.strip()}\n"
    )
    with open(path, "a") as f:
        f.write(entry)
    log.info(f"Wrote {msg_type}→{target}: {tid}")
    return tid


def write_comms(msg_type: str, from_a: str, to: str, content: str) -> str:
    mid = f"WC-{mt_stamp()}-{seq(_state)}"
    entry = (
        f"\n---\nmsg_id: {mid}\nmsg_type: {msg_type}\n"
        f"from: {from_a}\nto: {to}\nsubmitted_at: {mt_now()}\n"
        f"content: |\n  {content.strip()}\n"
    )
    with open(WING_COMMS, "a") as f:
        f.write(entry)
    return mid


HELP_TEXT = (
    "🦅 *THUNDERBIRD C2*\n\n"
    "*Talk to Hale (default):*\n"
    "`Hale: [anything]` — direct dispatch\n"
    "`OPUS: [task]` — force Brain 2 Opus\n"
    "`Sonnet: [task]` — force Brain 2 Sonnet\n\n"
    "*Route to specialists:*\n"
    "`Task Claude: ...` `Task Goose: ...`\n"
    "`Ask Claude/Goose: ...`\n"
    "`FYI All: ...` — broadcast\n\n"
    "*Commands:*\n"
    "`/hale` `/brief` `/board` `/tasks` `/status` `/help`"
)


def board_summary() -> str:
    if not ACTIVITY.exists():
        return "📋 Board empty."
    entries = parse_board(ACTIVITY.read_text())
    active = [e for e in entries if e["state"] in ("CLAIMED", "WORKING", "BLOCKED")]
    done = [e for e in entries if e["state"] == "COMPLETE"][-5:]
    lines = ["📋 *ACTIVITY BOARD*"]
    if active:
        lines.append("*Active:*")
        for e in active:
            icon = {"CLAIMED": "🟡", "WORKING": "🔵", "BLOCKED": "🚧"}.get(
                e["state"], "⚪"
            )
            lines.append(f"{icon} `{e['task_id']}` → {e['agent']}")
    else:
        lines.append("_No active tasks_")
    if done:
        lines.append("*Recent done:*")
        for e in done:
            lines.append(f"✅ `{e['task_id']}` — {e['agent']}")
    return "\n".join(lines)


def status_summary() -> str:
    total = len(_state.get("seen_tasks", {}))
    open_ = sum(
        1
        for v in _state.get("seen_tasks", {}).values()
        if v.get("state") not in ("COMPLETE", "CANCELLED")
    )
    stale = sum(
        1
        for v in _state.get("seen_tasks", {}).values()
        if v.get("state") in ("UNREAD", "DETECTED", "PENDING")
        and time.time() - v.get("detected_at", time.time()) > PROD_AFTER_SECS
    )
    return (
        f"📡 *WING STATUS*\nTasks: {total} tracked · {open_} open"
        + (f" · ⚠️ {stale} stale" if stale else "")
        + f"\nWatcher: running ✓  Poll: inotify"
    )


def task_list() -> str:
    tasks = _state.get("seen_tasks", {})
    if not tasks:
        return "📭 No tasks yet."
    icons = {
        "COMPLETE": "✅",
        "WORKING": "🔵",
        "CLAIMED": "🟡",
        "BLOCKED": "🚧",
        "UNREAD": "🔔",
        "PENDING": "⏳",
        "PRODDED": "🫡",
        "DETECTED": "👁",
    }
    lines = ["📋 *TASKS*"]
    for tid, info in list(tasks.items())[-20:]:
        icon = icons.get(info.get("state", ""), "⚪")
        lines.append(
            f"{icon} `{tid}` [{info.get('inbox', '?')}] {info.get('state', '?')}"
        )
    return "\n".join(lines)


def route_tg(text: str) -> str:
    tl = text.strip().lower()
    for pattern, target, msg_type in ROUTE_TABLE:
        m = re.match(pattern, tl, re.DOTALL | re.IGNORECASE)
        if not m:
            continue
        if msg_type == "CMD_BOARD":
            return board_summary()
        if msg_type == "CMD_STATUS":
            return status_summary()
        if msg_type == "CMD_TASKS":
            return task_list()
        if msg_type == "CMD_HELP":
            return HELP_TEXT
        if msg_type == "CMD_HALE":
            # Return Hale's current state summary
            from pathlib import Path as _P

            sf = _P("/home/john/Thunderbird/hale_state.json")
            try:
                import json as _j

                s = _j.loads(sf.read_text())
                reminders = s.get("pending_reminders", [])
                coord = (
                    s.get("coord_status", {})
                    .get("hale_blueprint_v1", {})
                    .get("status", "UNKNOWN")
                )
                tasks = len(s.get("open_tasks", []))
                r_text = "\n".join(f"• {r['item']}" for r in reminders) or "None"
                return (
                    f"🦅 *HALE STATUS*\n"
                    f"*COORD:* {coord}\n"
                    f"*Open tasks:* {tasks}\n"
                    f"*Reminders:* {r_text}\n"
                    f"*Brief:* `hale_brief.md`\n"
                    f"*Context:* `hale_session_context.md`"
                )
            except Exception as e:
                return f"[HALE STATUS ERROR] {e}"
        if msg_type == "CMD_BRIEF":
            bf = Path("/home/john/Thunderbird/hale_brief.md")
            if bf.exists():
                content = bf.read_text()[:3800]
                return f"📋 *HALE BRIEF*\n\n{content}"
            return "No brief generated yet. Run: `python3 OpsCenter/hale_dispatcher.py generate_brief`"

        # Get content from original-case version
        mo = re.match(pattern, text.strip(), re.DOTALL | re.IGNORECASE)
        content = mo.group(1).strip() if mo and mo.lastindex else text.strip()
        emoji = PRI_EMOJI.get(msg_type, "🔵")

        # ── Hale direct dispatch ──
        if target == "HALE" and msg_type in (
            "TASK",
            "REQUEST",
            "BRAIN_OPUS",
            "BRAIN_SONNET",
        ):
            override = None
            if msg_type == "BRAIN_OPUS":
                override = "opus"
                content = re.sub(
                    r"^opus[:\s]+", "", content, flags=re.IGNORECASE
                ).strip()
            elif msg_type == "BRAIN_SONNET":
                override = "sonnet"
                content = re.sub(
                    r"^sonnet[:\s]+", "", content, flags=re.IGNORECASE
                ).strip()
            tg_send(f"⚙️ *Hale thinking...*\n`{content[:60]}`")
            result = dispatch_to_hale(content, brain_override=override)
            return f"🦅 *HALE*\n\n{result}"

        if msg_type in ("TASK", "REQUEST"):
            tid = write_inbox(target, msg_type, content)
            write_board("COMMANDER", tid, "PENDING", f"{msg_type}→{target}")
            hale(
                f"{emoji} *Commander routed {msg_type}→{target}*\n`{tid}`: {content[:80]}"
            )
            return f"{emoji} *{msg_type}→{target}*\n`{tid}`\n{content[:100]}"
        else:
            mid = write_comms("FYI", "COMMANDER", target, content)
            if target not in ("HALE", "ALL"):
                hale(f"{emoji} *FYI for {target}*\n`{mid}`: {content[:80]}")
            return f"{emoji} *FYI→{target}*\n`{mid}`"
    return (
        "❓ Unknown. Try:\n`Hale: ...` `Task Hale: ...` `Ask Hale: ...`\n"
        "`Task Claude/Goose: ...` `FYI All: ...`\n`/hale` `/brief` `/help`"
    )


# ── Inbox validator integration ────────────────────────────────────────────
def _validate_and_alert(path: Path):
    """Run inbox_validator on a changed file. Alert Commander if errors found."""
    try:
        import sys as _sys

        _vmod_path = str(BASE / "OpsCenter")
        if _vmod_path not in _sys.path:
            _sys.path.insert(0, _vmod_path)
        from inbox_validator import check_file, FILE_ROLES

        violations = check_file(path)
        errors = [v for v in violations if v["severity"] == "ERROR"]
        if errors:
            summary = "; ".join(v["message"] for v in errors[:3])
            log.warning(f"ROUTING VIOLATION in {path.name}: {summary}")
            tg_send(
                f"⚠️ *ROUTING VIOLATION*\n`{path.name}`\n{summary}\nCheck overwatch.log"
            )
    except Exception as e:
        log.warning(f"Validator error on {path.name}: {e}")


# ── Watchdog handler ───────────────────────────────────────────────────────
_debounce: dict[str, float] = {}
DEBOUNCE_MS = 0.05  # 50ms — ignore duplicate inotify events


class CollabHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        # Debounce
        now = time.time()
        last = _debounce.get(str(path), 0)
        if now - last < DEBOUNCE_MS:
            return
        _debounce[str(path)] = now

        name = path.name
        if name == "claude_inbox.md":
            check_claude_inbox()
            _validate_and_alert(path)
        elif name == "opencode_inbox.md":
            check_opencode_inbox()
            _validate_and_alert(path)
        elif name == "wing_comms.md":
            check_wing_comms()
            rebuild_claude_injection()
        elif name == "activity_board.md":
            check_activity_board()
            rebuild_claude_injection()
        elif name == "claude_outbox.md":
            check_claude_outbox()
            _validate_and_alert(path)


# ── Main ───────────────────────────────────────────────────────────────────
def main():
    global _state
    log.info("Thunderbird Tasking Watcher v3 starting (inotify + prod engine)...")
    _state = load_state()

    # Bootstrap hashes silently
    if not _state["inbox_hashes"]["claude"]:
        _state["inbox_hashes"]["claude"] = fhash(CLAUDE_INBOX)
    if not _state["inbox_hashes"]["opencode"]:
        _state["inbox_hashes"]["opencode"] = fhash(OPENCODE_INBOX)
    if not _state.get("comms_hash"):
        _state["comms_hash"] = fhash(WING_COMMS)
    if not _state["board_hash"]:
        _state["board_hash"] = fhash(ACTIVITY)

    for p in (CLAUDE_INBOX, OPENCODE_INBOX, WING_COMMS, ACTIVITY, CLAUDE_OUTBOX):
        if not p.exists():
            p.touch()
    if not _state.get("claude_outbox_hash"):
        _state["claude_outbox_hash"] = fhash(CLAUDE_OUTBOX)

    # Start inotify observer
    observer = Observer()
    observer.schedule(CollabHandler(), str(COLLAB), recursive=False)
    observer.start()
    log.info(f"inotify observer watching {COLLAB}")

    write_board(
        "WATCHER", "SYSTEM", "WATCHING", "v3 online — inotify + prod engine active"
    )
    hale(
        f"🦅 *TASKING WATCHER v3 ONLINE*\n"
        f"inotify: instant detection\n"
        f"Prod: {PROD_AFTER_SECS}s timeout · {MAX_PRODS} prods then escalate\n"
        f"C2: `Task/Ask/Tell/FYI` + `/board /tasks /status /help`"
    )
    save_state(_state)
    log.info("v3 running.")

    try:
        while True:
            try:
                # SEND-ONLY — inbound routing handled exclusively by thunderbird-telegram-c2 (Hale bot)
                # This watcher only fires outbound notifications on file/board changes.

                # Prod engine
                prod_check()

                # Heartbeat
                if (
                    time.time() - _state.get("last_heartbeat_epoch", 0)
                    >= HEARTBEAT_SECS
                ):
                    _state["last_heartbeat_epoch"] = time.time()
                    hale(f"💫 *HEARTBEAT*\n{status_summary()}")

                save_state(_state)

            except Exception as _loop_exc:
                log.error(f"LOOP ERROR (continuing): {_loop_exc}", exc_info=True)
                try:
                    save_state(_state)
                except Exception:
                    pass

            time.sleep(TG_POLL_SECS)

    except KeyboardInterrupt:
        log.info("Stopping.")
        observer.stop()
        write_board("WATCHER", "SYSTEM", "OFFLINE", "v3 stopped")
        hale("🔴 *TASKING WATCHER OFFLINE*")
    observer.join()


if __name__ == "__main__":
    main()
