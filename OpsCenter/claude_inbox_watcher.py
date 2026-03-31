"""
claude_inbox_watcher.py — Auto-trigger Claude when Goose writes to claude_inbox.md
====================================================================================
Watches claude_inbox.md for new tasks written by goose_tasker.py.
When a new task appears, calls the Claude API automatically.
Commander writing to Goose is the human-in-the-loop. No further trigger needed.

Flow:
  Goose runs goose_tasker.py → writes to claude_inbox.md
  Watcher detects change → calls Claude API with inbox contents
  Claude executes task → writes to output_destination
  Watcher logs completion → updates routing_log.md

Author: Claude Sonnet 4.6 | Date: 2026-03-30
"""

import json
import os
import sys
import time
import hashlib
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# ── Paths ──
ROOT       = Path(__file__).resolve().parent.parent
OPSCENTER  = ROOT / "OpsCenter"
COLLAB     = OPSCENTER / "collaboration"
INBOX      = COLLAB / "claude_inbox.md"
OUTPUT     = COLLAB / "claude_output.md"
ROUTING    = COLLAB / "routing_log.md"
BLACKBOARD = COLLAB / "blackboard_summary.txt"
STATE_FILE = OPSCENTER / "inbox_watcher_state.json"
LOG_FILE   = ROOT / "logs" / "inbox_watcher.log"

MT = timezone(timedelta(hours=-6))

# ── Claude API ──
ANTHROPIC_API_KEY  = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL       = "claude-sonnet-4-20250514"
CLAUDE_MAX_TOKENS  = 4096

# ── Telegram ──
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_C2_BOT_TOKEN", "")
TELEGRAM_COMMANDER = os.environ.get("TELEGRAM_COMMANDER_ID", "")

def _ts() -> str:
    return datetime.now(MT).strftime("%Y-%m-%dT%H:%M:%S MT")


def _log(msg: str):
    line = f"[{_ts()}] {msg}"
    print(line, flush=True)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def _load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return {"last_hash": "", "last_processed_task": ""}


def _save_state(state: dict):
    try:
        STATE_FILE.write_text(json.dumps(state, indent=2))
    except Exception:
        pass


def _file_hash(path: Path) -> str:
    try:
        return hashlib.md5(path.read_bytes()).hexdigest()
    except Exception:
        return ""


def _send_telegram(text: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_COMMANDER:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_COMMANDER, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception:
        pass


def _get_blackboard_context() -> str:
    try:
        return BLACKBOARD.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def _extract_latest_task(inbox_text: str) -> tuple[str, str]:
    """
    Extract the most recent task block from claude_inbox.md.
    Returns (task_id, task_block).
    Tasks are separated by '---' and start with '## GOOSE TASK' or a task_id line.
    """
    blocks = inbox_text.split("\n---\n")
    # Find last non-empty block that contains a task_id
    for block in reversed(blocks):
        if "task_id:" in block and "instructions:" in block:
            # Extract task_id
            for line in block.splitlines():
                if line.strip().startswith("task_id:"):
                    task_id = line.split(":", 1)[1].strip()
                    return task_id, block.strip()
    return "", ""


def _call_claude(task_block: str, blackboard_context: str) -> str:
    """Call Claude API with the task. Returns Claude's response text."""
    if not ANTHROPIC_API_KEY:
        return "[ERROR] ANTHROPIC_API_KEY not set — cannot call Claude API"

    system = (
        "You are Claude Sonnet, AI consultant to the Thunderbird Wing of "
        "Dreams2Memories Travel, LLC. You are receiving a task submitted by "
        "Goose (Gemini) ON BEHALF OF COMMANDER John Loucks. "
        "Execute the task with full Commander authority. "
        "Be thorough, precise, and write output ready for Commander review.\n\n"
        "Standing directives:\n"
        "- Never send email outside the wing without Commander approval\n"
        "- Never use Love Group Travel branding\n"
        "- Never route PII to Deepseek or Groq\n"
        "- WF-17 gate required before any client output leaves the wing\n"
        "- Deepseek is arbitrator for inter-agent disputes\n\n"
        f"Current blackboard state:\n{blackboard_context}"
    )

    user = (
        f"Execute the following task from Goose (on behalf of Commander):\n\n"
        f"{task_block}\n\n"
        f"Write your complete output. If you have a dissent or concern about "
        f"this task contradicting a standing directive, state it clearly at the "
        f"top with a DISSENT flag, then execute the task anyway."
    )

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": CLAUDE_MODEL,
                "max_tokens": CLAUDE_MAX_TOKENS,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            },
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"]
    except Exception as e:
        return f"[ERROR] Claude API call failed: {e}"

def _write_output(task_id: str, response: str, output_dest: str):
    """Write Claude's response to the specified output destination."""
    header = (
        f"\n---\n"
        f"AGENT: Claude Sonnet (auto-triggered by inbox_watcher)\n"
        f"TASK_ID: {task_id}\n"
        f"COMPLETED_AT: {_ts()}\n"
        f"---\n"
        f"{response}\n"
    )
    dest = Path(output_dest) if output_dest else OUTPUT
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "a", encoding="utf-8") as f:
            f.write(header)
        _log(f"Output written to {dest}")
    except Exception as e:
        _log(f"ERROR writing output: {e}")


def _log_routing(task_id: str, status: str):
    entry = f"[{_ts()}] | {task_id} | auto-watcher→Claude | auto | UNKNOWN | {status} | inbox_watcher auto-execution\n"
    try:
        with open(ROUTING, "a") as f:
            f.write(entry)
    except Exception:
        pass


def _extract_output_dest(task_block: str) -> str:
    for line in task_block.splitlines():
        if line.strip().startswith("output_destination:"):
            return line.split(":", 1)[1].strip()
    return str(OUTPUT)


def process_inbox():
    """Read inbox, find latest unprocessed task, call Claude, write output."""
    state = _load_state()

    try:
        inbox_text = INBOX.read_text(encoding="utf-8")
    except Exception as e:
        _log(f"Cannot read inbox: {e}")
        return

    current_hash = _file_hash(INBOX)
    if current_hash == state.get("last_hash", ""):
        return  # No change

    task_id, task_block = _extract_latest_task(inbox_text)

    if not task_id:
        _log("Inbox changed but no valid task found")
        state["last_hash"] = current_hash
        _save_state(state)
        return

    if task_id == state.get("last_processed_task", ""):
        _log(f"Task {task_id} already processed — skipping")
        state["last_hash"] = current_hash
        _save_state(state)
        return

    _log(f"New task detected: {task_id} — calling Claude API")
    _send_telegram(f"⚡ <b>AUTO-EXECUTING</b> task <code>{task_id}</code> via Claude API")

    blackboard = _get_blackboard_context()
    output_dest = _extract_output_dest(task_block)

    response = _call_claude(task_block, blackboard)

    _write_output(task_id, response, output_dest)
    _log_routing(task_id, "COMPLETE")

    state["last_hash"] = current_hash
    state["last_processed_task"] = task_id
    _save_state(state)

    _send_telegram(
        f"✅ <b>TASK COMPLETE</b> <code>{task_id}</code>\n"
        f"Output written to: <code>{output_dest}</code>\n"
        f"Review: Commander only — no auto-send."
    )
    _log(f"Task {task_id} complete")


class InboxHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if Path(event.src_path) == INBOX:
            _log("Inbox change detected — processing")
            time.sleep(1)  # Brief pause to let Goose finish writing
            process_inbox()

    def on_created(self, event):
        if Path(event.src_path) == INBOX:
            _log("Inbox created — processing")
            time.sleep(1)
            process_inbox()


def run():
    _log("Claude Inbox Watcher starting")
    _log(f"Watching: {INBOX}")

    if not ANTHROPIC_API_KEY:
        _log("WARNING: ANTHROPIC_API_KEY not set — will log tasks but cannot call Claude API")

    # Process any existing unhandled task on startup
    process_inbox()

    observer = Observer()
    observer.schedule(InboxHandler(), path=str(COLLAB), recursive=False)
    observer.start()
    _log("Watcher active — waiting for Goose tasks")

    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
    _log("Watcher stopped")


if __name__ == "__main__":
    run()
