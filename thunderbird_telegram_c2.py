"""
D2MC2C — D2M Command and Control Center
=========================================

Commander-only Telegram bot. Direct line to YOGA and the Wing.
Separate from the Dani client-facing bot.

Commands:
  /start        — Welcome
  /help         — Command reference
  /hale <msg>   — COS (Col Victoria Hale)
  /naia <msg>   — EXEC (Naia Solberg-Vega)
  /dembe <msg>  — A2 (Lt Col Marcus Dembe)
  /dani <msg>   — A3 (Danielle Moreau)
  /castillo <msg> — A5 (Lt Col Ryan Castillo)
  /voss <msg>   — A6 (Luna Voss)
  /harlan <msg> — A9 (Victor Harlan)
  /washington <msg> — CH (Col James Washington)
  /elon <msg>   — A12 (ELON)
  /staff <msg>  — Broadcast to all personas
  /sitrep       — Status of all active bookings

Plain text → COS via Claude Opus (Agent SDK, $0 via Max plan)

Environment Variables:
  TELEGRAM_C2_BOT_TOKEN   — D2MC2C bot token from BotFather
  TELEGRAM_COMMANDER_ID   — your Telegram user ID (numeric)
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from telegram.constants import ChatAction, ParseMode

from thunderbird_personas import (
    get_persona,
    get_roster,
    PERSONA_REGISTRY,
    resolve_id,
)
from thunderbird_telegram_tools_sdk import (
    call_cos_with_tools,
    call_cos_via_cli,
    classify_intent,
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

TELEGRAM_C2_BOT_TOKEN = os.environ.get("TELEGRAM_C2_BOT_TOKEN", "")
TELEGRAM_COMMANDER_ID = os.environ.get("TELEGRAM_COMMANDER_ID", "")

if not TELEGRAM_C2_BOT_TOKEN:
    print("FATAL: Set TELEGRAM_C2_BOT_TOKEN environment variable.")
    sys.exit(1)

AUTHORIZED_IDS: set[int] = set()
if TELEGRAM_COMMANDER_ID:
    for uid in TELEGRAM_COMMANDER_ID.split(","):
        uid = uid.strip()
        if uid.isdigit():
            AUTHORIZED_IDS.add(int(uid))

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("d2mc2c")

# ---------------------------------------------------------------------------
# Persona command mapping
# ---------------------------------------------------------------------------

COMMAND_MAP: dict[str, str] = {
    "hale": "COS",
    "naia": "EXEC",
    "dembe": "A2",
    "dani": "A3",
    "castillo": "A5",
    "voss": "A6",
    "harlan": "A9",
    "washington": "CH",
    "elon": "A12",
}

MAX_MESSAGE_LENGTH = 4096

# ---------------------------------------------------------------------------
# Conversation memory
# ---------------------------------------------------------------------------

_conversation_history: dict[int, list[dict]] = {}
MAX_HISTORY = 10  # C2 gets deeper history than client bot

def _add_to_history(user_id: int, role: str, text: str):
    if user_id not in _conversation_history:
        _conversation_history[user_id] = []
    _conversation_history[user_id].append({
        "role": role, "text": text[:800],
        "ts": datetime.now(timezone.utc).isoformat(),
    })
    if len(_conversation_history[user_id]) > MAX_HISTORY:
        _conversation_history[user_id] = _conversation_history[user_id][-MAX_HISTORY:]

def _get_history(user_id: int) -> list[dict]:
    return _conversation_history.get(user_id, [])

# ---------------------------------------------------------------------------
# Access control — Commander only
# ---------------------------------------------------------------------------

def _is_commander(user_id: int) -> bool:
    return bool(AUTHORIZED_IDS) and user_id in AUTHORIZED_IDS

def commander_only(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not _is_commander(user_id):
            logger.warning(f"Unauthorized C2 access attempt: user_id={user_id}")
            await update.message.reply_text(
                "D2M Command Center — authorized access only."
            )
            return
        return await func(update, context)
    return wrapper

# ---------------------------------------------------------------------------
# Triple-write logging
# ---------------------------------------------------------------------------

C2_LOG_FILE = Path.home() / "Thunderbird" / "logs" / "c2_command_log.jsonl"
C2_LOG_FILE.parent.mkdir(exist_ok=True)

def _log_command(cmd_type: str, target: str, query: str, response: str,
                 status: str = "COMPLETE", channel: str = "telegram_c2"):
    """Triple-write: JSONL log + Commander_Log sheet (future) + Master Plan for SOPs."""
    try:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": cmd_type,
            "channel": channel,
            "target": target,
            "query": query[:500],
            "response": response[:1000],
            "status": status,
        }
        with open(C2_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        logger.info(f"C2 logged: {cmd_type} -> {target}: {query[:60]}...")
    except Exception as e:
        logger.error(f"C2 log failed: {e}")

# ---------------------------------------------------------------------------
# Message sending helper
# ---------------------------------------------------------------------------

async def send_long_message(update: Update, text: str):
    """Send message, splitting if over Telegram's 4096 char limit."""
    if len(text) <= MAX_MESSAGE_LENGTH:
        try:
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        except Exception:
            await update.message.reply_text(
                text.replace("*", "").replace("_", "").replace("`", "")
            )
    else:
        chunks = [text[i:i+MAX_MESSAGE_LENGTH] for i in range(0, len(text), MAX_MESSAGE_LENGTH)]
        for chunk in chunks:
            try:
                await update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)
            except Exception:
                await update.message.reply_text(
                    chunk.replace("*", "").replace("_", "").replace("`", "")
                )

def format_persona_header(persona_id: str) -> str:
    """Format persona attribution header."""
    try:
        persona = get_persona(persona_id)
        return f"{persona['icon']} *{persona['full_name']}*\n_{persona['role']}_"
    except Exception:
        return f"*{persona_id}*"

# ---------------------------------------------------------------------------
# Command Handlers
# ---------------------------------------------------------------------------

@commander_only
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome = (
        "Welcome to *D2M Command Center*, Yoda.\n\n"
        "Your Wing is standing by.\n\n"
        "Use a persona command to consult staff, "
        "or just type a message to reach COS.\n\n"
        "Type /help for the full command list.\n\n"
        f"_{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_"
    )
    await update.message.reply_text(welcome, parse_mode=ParseMode.MARKDOWN)


@commander_only
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = [
        "*D2M Command Center — Command Reference*\n",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
    ]
    for cmd, pid in COMMAND_MAP.items():
        try:
            persona = get_persona(pid)
            lines.append(
                f"/{cmd} — {persona['icon']} {persona['full_name']}\n"
                f"  _{persona['role']}_"
            )
        except Exception:
            lines.append(f"/{cmd} — {pid}")

    lines.extend([
        "",
        "/staff <message> — Broadcast to all personas",
        "/sitrep — Status report on all active bookings",
        "",
        "_Plain text goes to COS (Opus via Agent SDK)._",
    ])
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


@commander_only
async def cmd_sitrep(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Quick status report — COS assembles from all sources."""
    await update.message.chat.send_action(ChatAction.TYPING)
    query = "SITREP: Give me a quick status on all active bookings, pending actions, and system health."

    loop = asyncio.get_event_loop()
    answer = await loop.run_in_executor(
        None, lambda: call_cos_with_tools(query)
    )

    _log_command("SITREP", "COS", query, answer)
    header = format_persona_header("COS")
    await send_long_message(update, f"{header}\n\n{answer}")


@commander_only
async def cmd_staff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Staff meeting — broadcast to all personas via COS."""
    query = " ".join(context.args) if context.args else ""
    if not query:
        await update.message.reply_text(
            "Usage: /staff <your question or directive>\n\n"
            "COS will consult all Wing personas and compile responses."
        )
        return

    await update.message.chat.send_action(ChatAction.TYPING)
    logger.info(f"Staff meeting via C2: {query}")

    staff_query = (
        f"STAFF MEETING REQUEST from Commander:\n\n{query}\n\n"
        "Consult all relevant Wing personas and compile their responses. "
        "Use subagents if needed for parallel consultation."
    )

    loop = asyncio.get_event_loop()
    answer = await loop.run_in_executor(
        None, lambda: call_cos_with_tools(staff_query)
    )

    _log_command("TASK", "STAFF", query, answer)
    header = format_persona_header("COS")
    await send_long_message(update, f"{header}\n\n{answer}")


@commander_only
async def cmd_persona(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route to a specific persona via COS."""
    command = update.message.text.split()[0].lstrip("/").lower()
    if "@" in command:
        command = command.split("@")[0]

    persona_id = COMMAND_MAP.get(command)
    if not persona_id:
        await update.message.reply_text(f"Unknown persona: /{command}")
        return

    query = " ".join(context.args) if context.args else ""
    if not query:
        try:
            persona = get_persona(persona_id)
            await update.message.reply_text(
                f"Usage: /{command} <your message>\n\n"
                f"{persona['icon']} *{persona['full_name']}*\n"
                f"_{persona['role']}_",
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception:
            await update.message.reply_text(f"Usage: /{command} <your message>")
        return

    await update.message.chat.send_action(ChatAction.TYPING)
    logger.info(f"C2 persona {persona_id}: {query}")

    user_id = update.effective_user.id
    _add_to_history(user_id, "user", f"[/{command}] {query}")

    loop = asyncio.get_event_loop()
    answer = await loop.run_in_executor(
        None, lambda: call_cos_via_cli(query, persona=persona_id, intent_type="TASK")
    )

    _add_to_history(user_id, "assistant", answer)
    _log_command("TASK", persona_id, query, answer)

    header = format_persona_header(persona_id)
    await send_long_message(update, f"{header}\n\n{answer}")


@commander_only
async def handle_plain_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Plain text from Commander → COS via Opus Agent SDK."""
    query = update.message.text
    if not query or not query.strip():
        return

    user_id = update.effective_user.id
    await update.message.chat.send_action(ChatAction.TYPING)
    _add_to_history(user_id, "user", query)

    logger.info(f"C2 Commander msg -> COS (Opus): {query}")

    history = _get_history(user_id)
    conv_hist = [{"role": h["role"], "text": h["text"]} for h in history[:-1]]

    loop = asyncio.get_event_loop()
    try:
        answer = await loop.run_in_executor(
            None, lambda: call_cos_with_tools(query, conv_hist or None)
        )
    except Exception as e:
        logger.error(f"C2 Opus call failed: {e}")
        answer = f"C2 error: {e}\n\nFalling back..."
        try:
            answer = await loop.run_in_executor(
                None, lambda: call_cos_via_cli(query, intent_type="TASK")
            )
        except Exception as e2:
            answer = f"Both SDK and CLI failed.\nSDK: {e}\nCLI: {e2}"

    _add_to_history(user_id, "assistant", answer)
    _log_command("TASK", "COS", query, answer)

    header = format_persona_header("COS")
    await send_long_message(update, f"{header}\n\n{answer}")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"C2 bot error: {context.error}", exc_info=context.error)


# ---------------------------------------------------------------------------
# Draft Approval Flow — /drafts, approve, edit, reject via inline buttons
# ---------------------------------------------------------------------------

@commander_only
async def cmd_drafts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List pending Gmail drafts with approve/reject buttons."""
    await update.message.chat.send_action(ChatAction.TYPING)

    loop = asyncio.get_event_loop()
    try:
        from thunderbird_gmail import gmail_list_drafts_sync
        drafts = await loop.run_in_executor(None, lambda: gmail_list_drafts_sync(10))
    except Exception as e:
        await update.message.reply_text(f"Failed to fetch drafts: {e}")
        return

    if not drafts:
        await update.message.reply_text("No pending drafts in Gmail.")
        return

    await update.message.reply_text(
        f"*{len(drafts)} Draft(s) Pending Review*\n{'━' * 28}",
        parse_mode=ParseMode.MARKDOWN,
    )

    for d in drafts[:5]:  # Show top 5
        draft_id = d.get("draft_id", "?")
        to = d.get("To", "?")
        subject = d.get("Subject", "(no subject)")
        snippet = d.get("snippet", "")[:150]

        text = (
            f"📧 *Draft*\n"
            f"*To:* {to}\n"
            f"*Subject:* {subject}\n"
            f"_{snippet}_"
        )

        keyboard = [
            [
                InlineKeyboardButton("✅ Approve & Send", callback_data=f"draft_approve:{draft_id}"),
                InlineKeyboardButton("👁 Preview", callback_data=f"draft_preview:{draft_id}"),
            ],
            [
                InlineKeyboardButton("❌ Reject & Delete", callback_data=f"draft_reject:{draft_id}"),
            ],
        ]

        try:
            await update.message.reply_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        except Exception:
            await update.message.reply_text(
                text.replace("*", "").replace("_", ""),
                reply_markup=InlineKeyboardMarkup(keyboard),
            )


async def handle_draft_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle draft approval/preview/reject button presses."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if not _is_commander(user_id):
        await query.message.reply_text("Authorized access only.")
        return

    data = query.data
    if not data or ":" not in data:
        return

    action, draft_id = data.split(":", 1)
    loop = asyncio.get_event_loop()

    if action == "draft_approve":
        try:
            from thunderbird_gmail import gmail_send_draft_sync
            result = await loop.run_in_executor(None, lambda: gmail_send_draft_sync(draft_id))
            await query.message.reply_text(
                f"✅ *Draft sent!*\n"
                f"Message ID: `{result.get('message_id', '?')}`",
                parse_mode=ParseMode.MARKDOWN,
            )
            _log_command("DRAFT_APPROVED", "GMAIL", f"draft_id={draft_id}", "sent")
        except Exception as e:
            await query.message.reply_text(f"Failed to send draft: {e}")

    elif action == "draft_preview":
        try:
            from thunderbird_gmail import gmail_get_draft_sync
            draft = await loop.run_in_executor(None, lambda: gmail_get_draft_sync(draft_id))
            text = (
                f"📧 *Full Draft Preview*\n"
                f"{'━' * 28}\n"
                f"*From:* {draft.get('from', '?')}\n"
                f"*To:* {draft.get('to', '?')}\n"
                f"*Subject:* {draft.get('subject', '?')}\n\n"
                f"{draft.get('body_preview', '(empty)')}"
            )

            keyboard = [
                [
                    InlineKeyboardButton("✅ Approve & Send", callback_data=f"draft_approve:{draft_id}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"draft_reject:{draft_id}"),
                ],
            ]

            try:
                await query.message.reply_text(
                    text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )
            except Exception:
                await query.message.reply_text(
                    text.replace("*", "").replace("_", ""),
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )
        except Exception as e:
            await query.message.reply_text(f"Failed to preview draft: {e}")

    elif action == "draft_reject":
        try:
            from thunderbird_gmail import gmail_delete_draft_sync
            await loop.run_in_executor(None, lambda: gmail_delete_draft_sync(draft_id))
            await query.message.reply_text(
                f"❌ *Draft rejected and deleted.*",
                parse_mode=ParseMode.MARKDOWN,
            )
            _log_command("DRAFT_REJECTED", "GMAIL", f"draft_id={draft_id}", "deleted")
        except Exception as e:
            await query.message.reply_text(f"Failed to delete draft: {e}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    logger.info("=" * 50)
    logger.info("D2MC2C — Command and Control Center")
    logger.info(f"Authorized: {AUTHORIZED_IDS or 'NONE'}")
    logger.info("=" * 50)

    app = Application.builder().token(TELEGRAM_C2_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("sitrep", cmd_sitrep))
    app.add_handler(CommandHandler("staff", cmd_staff))
    app.add_handler(CommandHandler("drafts", cmd_drafts))

    for cmd_name in COMMAND_MAP:
        app.add_handler(CommandHandler(cmd_name, cmd_persona))

    # Draft approval inline buttons (approve/preview/reject)
    app.add_handler(CallbackQueryHandler(handle_draft_callback, pattern=r"^draft_"))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_plain_text))
    app.add_error_handler(error_handler)

    logger.info("D2MC2C online. Polling...")
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
