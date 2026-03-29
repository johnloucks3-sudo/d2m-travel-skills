# Telegram Dumb Pager Architecture
# This script replaces the blocking Telegram bots with instantaneous async queues.

import asyncio
import json
import os
import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from dotenv import load_dotenv

# Load secrets directly from the env file
load_dotenv("/home/john/Thunderbird/.env.telegram")

# Configuration
TELEGRAM_C2_BOT_TOKEN = os.environ.get("TELEGRAM_C2_BOT_TOKEN")
TELEGRAM_COMMANDER_ID = os.environ.get("TELEGRAM_COMMANDER_ID", "")
QUEUE_FILE = "/home/john/Thunderbird/OpsCenter/01_TASK_QUEUE.json"

async def write_to_queue(task):
    """Safely append a task to the shared JSON queue."""
    try:
        if os.path.exists(QUEUE_FILE):
            with open(QUEUE_FILE, "r") as f:
                try:
                    queue = json.load(f)
                except json.JSONDecodeError:
                    queue = []
        else:
            queue = []
            
        queue.append(task)
        
        with open(QUEUE_FILE, "w") as f:
            json.dump(queue, f, indent=4)
        return True
    except Exception as e:
        print(f"Failed to write to queue: {e}")
        return False

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    await update.message.reply_text("Thunderbird Wing C2 Bot Active. The Watch Officer is listening.")

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
        "assigned_to": "Hale"
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
            "chat_id": update.effective_chat.id
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
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(handle_callback))

    print("C2 Pager Bot starting in un-freezable polling mode...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
