# Telegram Dumb Pager Architecture
# This script replaces the blocking Telegram bots with instantaneous async queues.

import asyncio
import os
import subprocess
import sys
from datetime import datetime, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from dotenv import load_dotenv

# Load secrets directly from the env file
load_dotenv("/home/john/Thunderbird/.env.telegram")

# SQLite queue (replaces 01_TASK_QUEUE.json)
sys.path.insert(0, "/home/john/Thunderbird")
from OpsCenter.submit_task import queue as _queue_task
from OpsCenter.task_queue import init_db as _init_queue
_init_queue()

# Configuration
TELEGRAM_C2_BOT_TOKEN = os.environ.get("TELEGRAM_C2_BOT_TOKEN")
TELEGRAM_COMMANDER_ID = os.environ.get("TELEGRAM_COMMANDER_ID", "")


async def write_to_queue(task: dict) -> bool:
    """Submit a task to the SQLite dispatcher queue."""
    try:
        _queue_task(
            content=task.get("content", ""),
            assigned_to=task.get("assigned_to", "auto"),
            task_type=task.get("task_type", "general"),
            source=task.get("source_bot", "c2"),
            chat_id=str(task["chat_id"]) if task.get("chat_id") else None,
        )
        return True
    except Exception as e:
        print(f"Failed to write to queue: {e}")
        return False

GOOSE_BOT_TOKEN = "***REMOVED-SECRET***"
WATCHDOG_LOG = "/tmp/goose_watchdog.log"
WATCHDOG_COOLDOWN = 30  # seconds between auto-reconnects
_last_reconnect = 0


def _restart_gateway() -> str:
    """Restart the Goose gateway systemd service. Returns status message."""
    result = subprocess.run(
        ["systemctl", "--user", "restart", "goose-gateway.service"],
        capture_output=True, text=True
    )
    ts = datetime.now().strftime("%H:%M:%S")
    if result.returncode == 0:
        msg = f"[{ts}] Gateway restarted OK"
    else:
        msg = f"[{ts}] Gateway restart FAILED: {result.stderr.strip()}"
    with open(WATCHDOG_LOG, "a") as f:
        f.write(msg + "\n")
    return msg


def _goose_mcp_alive() -> bool:
    """Check if goose_mcp_server.py is running as a child of the gateway."""
    result = subprocess.run(
        ["pgrep", "-f", "goose_mcp_server.py"],
        capture_output=True, text=True
    )
    return result.returncode == 0


async def _notify_commander(app, text: str):
    """Send a message to the Commander via C2 bot."""
    try:
        await app.bot.send_message(chat_id=TELEGRAM_COMMANDER_ID, text=text)
    except Exception as e:
        print(f"Notify failed: {e}")


async def goose_watchdog(app):
    """Background task: monitors Goose MCP health, auto-restarts on failure."""
    global _last_reconnect
    await asyncio.sleep(15)  # initial startup grace period
    print("Goose watchdog active.")
    while True:
        await asyncio.sleep(20)
        if not _goose_mcp_alive():
            now = asyncio.get_event_loop().time()
            if now - _last_reconnect > WATCHDOG_COOLDOWN:
                _last_reconnect = now
                status = _restart_gateway()
                await _notify_commander(
                    app,
                    f"⚡ Goose auto-reconnect\n{status}\nSend any message to Goose to continue."
                )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    await update.message.reply_text("Thunderbird Wing C2 Bot Active. The Watch Officer is listening.")


async def reconnect_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /reconnect — restart Goose gateway and notify."""
    await update.message.reply_text("Reconnecting Goose gateway...")
    status = _restart_gateway()
    await update.message.reply_text(
        f"✅ {status}\nSend any message to your Goose bot to start a fresh session."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Instantly dump incoming messages into the Hale-Loop queue without blocking."""
    text = update.message.text
    
    # Send instant "received" receipt
    await update.message.reply_text("Roger. Tasking Hale...")
    
    # Write task for the daemon to process asynchronously
    task = {
        "task_id": f"msg_{update.message.message_id}",
        "task_type": "commander_message",
        "content": text,
        "source_bot": "c2",
        "chat_id": update.effective_chat.id,
        "assigned_to": "Hale",
        "queued_at": datetime.now(timezone.utc).isoformat(),
    }
    
    await write_to_queue(task)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Instantly handle button presses (like Approve Draft) without blocking."""
    query = update.callback_query
    await query.answer() # Acknowledge the press immediately
    
    data = query.data
    
    if data.startswith("approve_"):
        draft_id = data.split("_")[1]
        
        # Instantly update the UI so the Commander knows it was pressed
        await query.edit_message_text(text=f"{query.message.text}\n\n✅ **APPROVED.** Dispatching...")
        
        # Write the execute order to the Hale-Loop queue
        task = {
            "task_id": f"cb_{query.id}",
            "task_type": "send_draft",
            "draft_id": draft_id,
            "assigned_to": "A3",
            "source_bot": "c2",
            "chat_id": update.effective_chat.id,
            "queued_at": datetime.now(timezone.utc).isoformat(),
        }
        await write_to_queue(task)
        
    elif data.startswith("reject_"):
        await query.edit_message_text(text=f"{query.message.text}\n\n❌ **REJECTED.**")

def main():
    if not TELEGRAM_C2_BOT_TOKEN:
        print("Error: TELEGRAM_C2_BOT_TOKEN not found in /home/john/Thunderbird/.env.telegram")
        sys.exit(1)

    application = Application.builder().token(TELEGRAM_C2_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("reconnect", reconnect_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(handle_callback))

    # Start Goose MCP watchdog
    async def post_init(app):
        asyncio.create_task(goose_watchdog(app))

    application.post_init = post_init

    print("C2 Pager Bot starting in un-freezable polling mode...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
