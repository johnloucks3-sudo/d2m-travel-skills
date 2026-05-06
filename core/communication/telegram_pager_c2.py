# telegram_pager_c2.py — Thunderbird Wing C2 Bot
# Merged: Hale conversational + Tasking Router + WF-17 approve/reject + Goose watchdog
# Token: TELEGRAM_C2_BOT_TOKEN (D2MC2C_bot) — sole owner of this token
#
# Inbound routing:
#   "Task Claude/Goose: ..."  → write to agent inbox
#   "Ask Claude/Goose: ..."   → write REQUEST to inbox
#   "Tell Claude/Goose: ..."  → write FYI to wing_comms
#   "FYI All/Hale: ..."       → write FYI to wing_comms
#   /board /status /tasks /help /reconnect /start
#   anything else             → "Roger. Tasking Hale..." + SQLite queue

import asyncio
import os
import re
import ssl
import subprocess
import sys
import time
import urllib.request
import json as _json
from datetime import datetime, timezone
from pathlib import Path

from telegram import Update
from telegram.ext import (Application, CommandHandler, MessageHandler,
                           CallbackQueryHandler, filters, ContextTypes)
from dotenv import load_dotenv

load_dotenv("/home/john/Thunderbird/.env.telegram")
sys.path.insert(0, "/home/john/Thunderbird")
from OpsCenter.submit_task import queue as _queue_task
from OpsCenter.task_queue import init_db as _init_queue
_init_queue()

# ── Config ───────────────────────────────────────────────────────────────────
BOT_TOKEN    = os.environ.get("TELEGRAM_C2_BOT_TOKEN")
COMMANDER_ID = os.environ.get("TELEGRAM_COMMANDER_ID", "")

COLLAB       = Path("/home/john/Thunderbird/OpsCenter/collaboration")
CLAUDE_INBOX = COLLAB / "claude_inbox.md"
OPENCODE_INBOX = COLLAB / "opencode_inbox.md"
WING_COMMS   = COLLAB / "wing_comms.md"
ACTIVITY     = COLLAB / "activity_board.md"

WATCHDOG_LOG = "/tmp/goose_watchdog.log"

# ── Goose desktop API (HTTPS on GOOSE_PORT) ───────────────────────────────────
def _goose_api_secret() -> str | None:
    """Read GOOSE_SERVER__SECRET_KEY from the running goosed process env."""
    try:
        for pid_dir in Path("/proc").iterdir():
            if not pid_dir.name.isdigit():
                continue
            try:
                exe = (pid_dir / "exe").resolve()
                if "goosed" not in str(exe):
                    continue
                env_raw = (pid_dir / "environ").read_bytes().split(b"\x00")
                for entry in env_raw:
                    kv = entry.decode("utf-8", errors="replace")
                    if kv.startswith("GOOSE_SERVER__SECRET_KEY="):
                        return kv.split("=", 1)[1]
                    if kv.startswith("GOOSE_PORT="):
                        pass  # collected separately
            except Exception:
                continue
    except Exception:
        pass
    return None

def _goose_api_port() -> int:
    """Find GOOSE_PORT from running goosed process env."""
    try:
        for pid_dir in Path("/proc").iterdir():
            if not pid_dir.name.isdigit():
                continue
            try:
                exe = (pid_dir / "exe").resolve()
                if "goosed" not in str(exe):
                    continue
                env_raw = (pid_dir / "environ").read_bytes().split(b"\x00")
                for entry in env_raw:
                    kv = entry.decode("utf-8", errors="replace")
                    if kv.startswith("GOOSE_PORT="):
                        return int(kv.split("=", 1)[1])
            except Exception:
                continue
    except Exception:
        pass
    return 32981  # fallback

def generate_goose_pairing_code() -> dict | None:
    """Call goosed HTTPS API to generate a Telegram pairing code."""
    try:
        secret = _goose_api_secret()
        port   = _goose_api_port()
        if not secret:
            return None
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(
            f"https://localhost:{port}/gateway/pair",
            method="POST",
            data=_json.dumps({"gateway_type": "telegram"}).encode(),
            headers={"X-Secret-Key": secret, "Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, context=ctx, timeout=5)
        return _json.loads(resp.read())
    except Exception as e:
        print(f"goose_pair_code failed: {e}")
        return None

# ── Helpers ──────────────────────────────────────────────────────────────────
def mt_now() -> str:
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/Denver")).strftime("%Y-%m-%d %H:%M MT")
    except Exception:
        return datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

def mt_stamp() -> str:
    return datetime.utcnow().strftime("%Y%m%d-%H%M%S")

_seq_n = 0
def _seq() -> str:
    global _seq_n
    _seq_n += 1
    return f"{_seq_n:03d}"

# ── Tasking Route Table ───────────────────────────────────────────────────────
ROUTE_TABLE = [
    (r"^task\s+claude[:\s]+(.+)",  "CLAUDE", "TASK"),
    (r"^task\s+opencode[:\s]+(.+)",   "OPENCODE",  "TASK"),
    (r"^ask\s+claude[:\s]+(.+)",   "CLAUDE", "REQUEST"),
    (r"^ask\s+opencode[:\s]+(.+)",    "OPENCODE",  "REQUEST"),
    (r"^tell\s+claude[:\s]+(.+)",  "CLAUDE", "FYI"),
    (r"^tell\s+opencode[:\s]+(.+)",   "OPENCODE",  "FYI"),
    (r"^fyi\s+claude[:\s]+(.+)",   "CLAUDE", "FYI"),
    (r"^fyi\s+opencode[:\s]+(.+)",    "OPENCODE",  "FYI"),
    (r"^fyi\s+hale[:\s]+(.+)",     "HALE",   "FYI"),
    (r"^fyi\s+all[:\s]+(.+)",      "ALL",    "FYI"),
    (r"^tell\s+all[:\s]+(.+)",     "ALL",    "FYI"),
]
PRI_MAP   = {"TASK": "HIGH", "REQUEST": "NORMAL", "FYI": "LOW"}
PRI_EMOJI = {"TASK": "🔴", "REQUEST": "🟡", "FYI": "🔵"}

HELP_TEXT = (
    "🦅 *THUNDERBIRD C2 — Hale on watch*\n\n"
    "*Tasking commands:*\n"
    "`Task Claude: <what>`\n"
    "`Task Goose: <what>`\n"
    "`Ask Claude/Goose: <what>`  — soft request\n"
    "`Tell Claude/Goose: <what>` — FYI\n"
    "`FYI All: <what>`           — broadcast\n\n"
    "*Status commands:*\n"
    "`/board`      — activity board\n"
    "`/tasks`      — pending tasks\n"
    "`/status`     — wing services\n"
    "`/goose_code` — get Goose pairing code\n"
    "`/reconnect`  — restart Goose\n\n"
    "Anything else → Hale queue."
)

# ── File writers ──────────────────────────────────────────────────────────────
def write_inbox(target: str, msg_type: str, content: str) -> str:
    path = CLAUDE_INBOX if target == "CLAUDE" else OPENCODE_INBOX
    tid  = f"TG-{mt_stamp()}-{_seq()}"
    entry = (
        f"\n---\n## COMMANDER {msg_type} — Telegram\n"
        f"task_id: {tid}\nmsg_type: {msg_type}\n"
        f"submitted_by: COMMANDER\nauthority: COMMANDER\n"
        f"submitted_at: {mt_now()}\ntask_type: telegram_routed\n"
        f"priority: {PRI_MAP.get(msg_type, 'NORMAL')}\n"
        f"pii: false\nstatus: UNREAD\ncontent: |\n  {content.strip()}\n"
    )
    with open(path, "a") as f:
        f.write(entry)
    return tid

def write_comms(msg_type: str, to: str, content: str) -> str:
    mid = f"WC-{mt_stamp()}-{_seq()}"
    entry = (
        f"\n---\nmsg_id: {mid}\nmsg_type: {msg_type}\n"
        f"from: COMMANDER\nto: {to}\nsubmitted_at: {mt_now()}\n"
        f"content: |\n  {content.strip()}\n"
    )
    with open(WING_COMMS, "a") as f:
        f.write(entry)
    return mid

# ── Board / status summaries ──────────────────────────────────────────────────
def board_summary() -> str:
    if not ACTIVITY.exists():
        return "📋 Board empty."
    icons = {"CLAIMED": "🟡", "WORKING": "🔵", "COMPLETE": "✅",
             "BLOCKED": "🚧", "PENDING": "⏳", "PRODDED": "🫡"}
    lines = ["📋 *ACTIVITY BOARD*"]
    for raw in ACTIVITY.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        for state, icon in icons.items():
            if state in line:
                lines.append(f"{icon} {line[:90]}")
                break
    return "\n".join(lines[-16:]) if len(lines) > 1 else "📋 Board empty."

def status_summary() -> str:
    svcs = [
        ("d2m-tasking-watcher.service", "Watcher"),
        ("thunderbird-overwatch.service", "Overwatch"),
        ("goose-telegram.service", "Goose"),
        ("thunderbird-telegram-c2.service", "Hale-C2"),
    ]
    lines = ["🛡 *WING STATUS*"]
    for svc, label in svcs:
        r = subprocess.run(["systemctl", "--user", "is-active", svc],
                           capture_output=True, text=True)
        state = r.stdout.strip()
        lines.append(f"{'✅' if state == 'active' else '🔴'} {label}: {state}")
    return "\n".join(lines)

def task_list() -> str:
    tasks = []
    for inbox, label in [(CLAUDE_INBOX, "CLAUDE"), (OPENCODE_INBOX, "GOOSE")]:
        if not inbox.exists():
            continue
        for block in inbox.read_text().split("---"):
            if "status: UNREAD" in block:
                tid = next((l.replace("task_id:", "").strip()
                            for l in block.splitlines() if l.startswith("task_id:")), "?")
                tasks.append(f"🔔 `{tid}` [{label}]")
    return ("📋 *PENDING TASKS*\n" + "\n".join(tasks[-15:])) if tasks else "📭 No pending tasks."

# ROUTE_TABLE changes: Define log-only targets for noise
# Modify routing to write to /logs/telegram_noise.log instead of flooding C2
def route_message(text: str) -> str | None:
    """Return formatted reply if text matches a tasking command, else None."""
    for pattern, target, msg_type in ROUTE_TABLE:
        m = re.match(pattern, text.strip(), re.DOTALL | re.IGNORECASE)
        if not m:
            continue
        content = m.group(1).strip() if m.lastindex else text.strip()
        emoji   = PRI_EMOJI.get(msg_type, "🔵")

        # FILTER: Mute repetitive dispatcher tasks in C2
        if "Dispatcher" in content or "DONE" in content:
            with open("/home/john/Thunderbird/logs/telegram_noise.log", "a") as f:
                f.write(f"[{mt_now()}] SILENT ROUTE: {target} | {content}\n")
            return None

        if msg_type in ("TASK", "REQUEST"):
            tid = write_inbox(target, msg_type, content)
            return f"{emoji} *{msg_type} → {target}*\n`{tid}`\n_{content[:120]}_"
        else:
            mid = write_comms(msg_type, target, content)
            return f"{emoji} *FYI → {target}*\n`{mid}`\n_{content[:120]}_"
    return None

# ── Goose reconnect (manual /reconnect only — no auto-watchdog) ──────────────
# Watchdog removed: Restart=on-failure in goose-telegram.service handles crashes.
# Auto-restart was causing repeated pairing code messages on every DNS hiccup.

def _restart_goose() -> str:
    r = subprocess.run(["systemctl", "--user", "restart", "goose-telegram.service"],
                       capture_output=True, text=True)
    ts  = datetime.now().strftime("%H:%M:%S")
    msg = f"[{ts}] {'Restarted OK' if r.returncode == 0 else 'FAILED: ' + r.stderr.strip()}"
    with open(WATCHDOG_LOG, "a") as f:
        f.write(msg + "\n")
    return msg

async def _notify(app, text: str):
    try:
        await app.bot.send_message(chat_id=COMMANDER_ID, text=text)
    except Exception as e:
        print(f"notify failed: {e}")

# ── SQLite queue writer ───────────────────────────────────────────────────────
async def queue_for_hale(text: str, chat_id: int, msg_id: int):
    try:
        _queue_task(
            content=text,
            assigned_to="Hale",
            task_type="commander_message",
            source="c2",
            chat_id=str(chat_id),
        )
    except Exception as e:
        print(f"Queue write failed: {e}")

# ── Telegram handlers ─────────────────────────────────────────────────────────
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🦅 Thunderbird Wing C2 — Hale on watch.\n/help for commands.")

async def reconnect_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Reconnecting Goose...")
    await update.message.reply_text(f"✅ {_restart_goose()}")

async def goose_code_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate a fresh Goose Telegram pairing code and deliver it."""
    await update.message.reply_text("Generating Goose pairing code...")
    data = generate_goose_pairing_code()
    if not data:
        await update.message.reply_text(
            "❌ Could not reach Goose desktop app API.\n"
            "Is the Goose desktop app running on YOGA?"
        )
        return
    code = data.get("code", "?")
    expires_at = data.get("expires_at", 0)
    mins = max(1, int((expires_at - time.time()) / 60))
    await update.message.reply_text(
        f"🦆 *Goose Pairing Code*\n\n"
        f"Send this to @GooseD2M\\_bot:\n\n"
        f"`{code}`\n\n"
        f"⏰ Valid ~{mins} min",
        parse_mode="Markdown"
    )

async def board_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(board_summary(), parse_mode="Markdown")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(status_summary(), parse_mode="Markdown")

async def tasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(task_list(), parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if not text:
        return

    # Tasking commands first
    reply = route_message(text)
    if reply:
        await update.message.reply_text(reply, parse_mode="Markdown")
        return

    # Conversational → Hale queue
    await update.message.reply_text("Roger. Tasking Hale...")
    await queue_for_hale(text, update.effective_chat.id, update.message.message_id)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data  = query.data or ""
    if data.startswith("approve_"):
        draft_id = data.split("_")[1]
        await query.edit_message_text(f"{query.message.text}\n\n✅ APPROVED. Dispatching...")
        try:
            _queue_task(content=draft_id, assigned_to="A3",
                        task_type="send_draft", source="c2",
                        chat_id=str(update.effective_chat.id))
        except Exception as e:
            print(f"Approve queue failed: {e}")
    elif data.startswith("reject_"):
        await query.edit_message_text(f"{query.message.text}\n\n❌ REJECTED.")

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    if not BOT_TOKEN:
        print("ERROR: TELEGRAM_C2_BOT_TOKEN not set in .env.telegram")
        sys.exit(1)

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",      start_command))
    app.add_handler(CommandHandler("reconnect",  reconnect_command))
    app.add_handler(CommandHandler("goose_code", goose_code_command))
    app.add_handler(CommandHandler("board",      board_command))
    app.add_handler(CommandHandler("status",     status_command))
    app.add_handler(CommandHandler("tasks",     tasks_command))
    app.add_handler(CommandHandler("help",      help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))

    print("Thunderbird C2 Hale Bot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
