"""
Thunderbird Telegram Bot — D2M Client-Facing Concierge (Dani Only)
===================================================================

Client-facing bot. All users talk to Dani (A3), the luxury travel concierge.
COS reviews every response before it goes out. Commander notified of every interaction.

For Commander C2 (staff commands, persona access, ops briefings):
  → Use @D2MC2C_bot (d2m-telegram-c2.service)

Commands:
  /start  — Dani welcome with quick-action menu
  /help   — What Dani can help with

Plain text → Dani → COS review → respond → notify Commander

Environment Variables:
  TELEGRAM_BOT_TOKEN     — from BotFather (@d2m_luxury_travel_bot)
  TELEGRAM_COMMANDER_ID  — Commander's Telegram user ID (for DM notifications)

Usage:
  export TELEGRAM_BOT_TOKEN="123456:ABC-DEF..."
  export TELEGRAM_COMMANDER_ID="123456789"
  python thunderbird_telegram.py
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from functools import wraps

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

# NOTE: All Commander C2 commands (persona commands, /staff, /sitrep, etc.)
# have been moved to @D2MC2C_bot (thunderbird_telegram_c2.py).
# This bot is CLIENT-FACING ONLY.

# Import the existing persona system
from thunderbird_personas import (
    call_persona,
    get_persona,
    resolve_id,
)
from thunderbird_context import gather_commander_context
from thunderbird_dani_engine import build_dani_context, cos_review, pre_send_evaluate
from thunderbird_telegram_tools_sdk import call_cos_with_tools

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_C2_BOT_TOKEN = os.environ.get("TELEGRAM_C2_BOT_TOKEN", "***REMOVED-SECRET***")
TELEGRAM_COMMANDER_ID = os.environ.get("TELEGRAM_COMMANDER_ID", "7554895206")

if not TELEGRAM_BOT_TOKEN:
    print("FATAL: Set TELEGRAM_BOT_TOKEN environment variable.")
    sys.exit(1)

# Parse commander ID — can be comma-separated for multiple authorized users
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
logger = logging.getLogger("thunderbird_telegram")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# ⚠️ COMMANDER KILL SWITCH — Standing Order 2026-03-25
# Dani bot is LOCKED. She does NOT respond to any incoming Telegram messages until
# COS re-enables after supplier audit + token waste investigation.
# To re-enable: set DANI_BOT_ENABLED = True below.
DANI_BOT_ENABLED = True   # RE-ENABLED by COS 2026-03-26 — supplier audit complete

DEFAULT_PERSONA = "A3"      # Dani handles all client messages
COMMANDER_PERSONA = "COS"   # COS handles Commander plain-text messages

# Persona command mapping (kept for /help, /staff, /persona commands)
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

# Telegram message length limit
MAX_MESSAGE_LENGTH = 4096


# ---------------------------------------------------------------------------
# Access control — Commander only (for C2 commands kept in this bot)
# ---------------------------------------------------------------------------

def _is_commander(user_id: int) -> bool:
    return bool(AUTHORIZED_IDS) and user_id in AUTHORIZED_IDS


def commander_only(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if _is_commander(user_id):
            # Commander's channel is @D2MC2C_bot — this bot is clients only
            await update.message.reply_text(
                "⚠️ *Wrong channel, Commander.*\n\n"
                "This bot is reserved for clients only.\n"
                "Use @D2MC2C\\_bot for Wing access, staff commands, and ops.",
                parse_mode=ParseMode.MARKDOWN,
            )
            return
        # Non-commanders: friendly block for staff commands
        logger.warning(f"Unauthorized command attempt: user_id={user_id}")
        await update.message.reply_text(
            "This command is not available. Just send me a message and I'll help!"
        )
        return
    return wrapper

# ---------------------------------------------------------------------------
# Conversation memory — last few exchanges per user for context awareness
# ---------------------------------------------------------------------------

_conversation_history: dict[int, list[dict]] = {}
MAX_HISTORY = 6  # keep last 6 messages (3 exchanges)


def _add_to_history(user_id: int, role: str, text: str):
    """Track conversation so Dani doesn't repeat herself."""
    if user_id not in _conversation_history:
        _conversation_history[user_id] = []
    _conversation_history[user_id].append({
        "role": role, "text": text[:500],  # truncate to keep lean
        "ts": datetime.now(timezone.utc).isoformat(),
    })
    # Trim to max
    if len(_conversation_history[user_id]) > MAX_HISTORY:
        _conversation_history[user_id] = _conversation_history[user_id][-MAX_HISTORY:]


def _get_history_context(user_id: int) -> str:
    """Format recent conversation for context injection."""
    history = _conversation_history.get(user_id, [])
    if not history:
        return ""
    lines = ["RECENT CONVERSATION:"]
    for msg in history:
        speaker = "Commander" if msg["role"] == "user" else "Dani"
        lines.append(f"  {speaker}: {msg['text']}")
    return "\n".join(lines)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def format_persona_header(persona_id: str) -> str:
    """Build a Telegram-friendly header line for a persona response."""
    pid = resolve_id(persona_id)
    persona = get_persona(pid)
    return (
        f"{persona['icon']} *{pid} — {persona['full_name']}*\n"
        f"_{persona['role']}_\n"
        f"{'─' * 28}"
    )


def escape_markdown_v2(text: str) -> str:
    """Escape special chars for Telegram MarkdownV2, preserving bold/italic markers."""
    # We use basic Markdown mode instead of MarkdownV2 to keep things simple
    return text


async def send_long_message(update: Update, text: str, parse_mode=ParseMode.MARKDOWN):
    """Send a message, splitting into chunks if it exceeds Telegram's limit."""
    # Strip problematic markdown if it causes issues
    chunks = []
    while len(text) > MAX_MESSAGE_LENGTH:
        # Find a good split point (newline near the limit)
        split_at = text.rfind("\n", 0, MAX_MESSAGE_LENGTH)
        if split_at < MAX_MESSAGE_LENGTH // 2:
            split_at = MAX_MESSAGE_LENGTH
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    chunks.append(text)

    for chunk in chunks:
        try:
            await update.message.reply_text(chunk, parse_mode=parse_mode)
        except Exception:
            # Fallback: send without parse mode if markdown breaks
            await update.message.reply_text(chunk)


FALLBACK_MSG = (
    "I don't have that information in my records right now, "
    "but I'll forward your question to John and get back to you promptly."
)

# Simple greetings that don't need the full data engine
GREETING_PATTERNS = [
    "good morning", "good afternoon", "good evening", "hello", "hi dani",
    "hey dani", "hi there", "hey there", "morning", "howdy", "what's up",
    "how are you", "how's it going", "greetings",
]


def _is_greeting(query: str) -> bool:
    """Detect if this is a simple greeting (no data lookup needed)."""
    q = query.lower().strip().rstrip("!.,?")
    # Must be short (greetings are brief) and match a pattern
    if len(q.split()) > 6:
        return False
    return any(q.startswith(g) or q == g for g in GREETING_PATTERNS)


def _build_contextual_query(query: str) -> str:
    """Prepend compact operational data to a query (non-Dani personas)."""
    try:
        context = gather_commander_context(query)
        return f"{context}\n\nQUERY: {query}"
    except Exception as e:
        logger.warning(f"Context gather failed: {e}")
        return query



def _build_dani_query_client(query: str, user_id: int = None) -> str:
    """Build Dani's client-facing query — same data but filtered.

    Hides: commissions, margins, internal strategy, other clients' data.
    """
    try:
        context = build_dani_context(query, is_commander=False)
        parts = [context]

        if user_id:
            history = _get_history_context(user_id)
            if history:
                parts.append(history)

        parts.append(
            "IMPORTANT: This is a CLIENT query — not the Commander.\n"
            "- NEVER reveal commission rates, markup percentages, or net costs.\n"
            "- NEVER mention other clients' bookings, names, or travel plans.\n"
            "- NEVER discuss internal D2M strategy, pricing models, or business decisions.\n"
            "- NEVER reveal details about internal team structure, AI workflows, personas, "
            "or operational systems. If asked, say our internal operations are proprietary.\n"
            "- NEVER use placeholder brackets like [Client Name] or [Your Name]. "
            "If you don't know their name, address them warmly without one.\n"
            "- NEVER fabricate booking dates, hotel names, excursion details, dietary "
            "confirmations, payment deadlines, or any specific booking data you were not "
            "given above. If you don't have it, say you need to check your records.\n"
            "- D2M earns commission from suppliers — we do NOT charge clients a separate "
            "fee or percentage. Our services come at no additional cost to the client.\n"
            "- Be warm, helpful, and treat them as a valued luxury travel client."
        )
        parts.append(f"CLIENT QUESTION: {query}")
        return "\n\n".join(parts)
    except Exception as e:
        logger.warning(f"Dani engine (client) failed, falling back: {e}")
        return _build_contextual_query(query)


# Model routing: per-persona map in thunderbird_personas.py (A3=Sonnet, rest=Opus)


def _build_cos_query(query: str, user_id: int = None) -> str:
    """Build COS query with rich data context for Commander briefings.

    Uses the Dani data engine but strips Dani persona rules and replaces
    with COS briefing instructions.
    """
    try:
        context = build_dani_context(query, is_commander=True)

        # Strip Dani's rules — COS has her own system prompt
        if "DANI'S RULES:" in context:
            context = context[:context.index("DANI'S RULES:")]

        cos_rules = (
            "COS DATA PRESENTATION RULES:\n"
            "- You are briefing the COMMANDER. Present ALL data from above — every field, every date, every detail.\n"
            "- Format as a clean briefing: structured, scannable, complete.\n"
            "- Include: names, booking IDs, confirmation numbers, dates, costs, phone numbers, emails, addresses.\n"
            "- Include: anchor date timelines, cancellation penalties, payment status, insurance status.\n"
            "- Include: dossier data, checklist items, logistics, tour/dining status.\n"
            "- If data exists above, PRESENT IT. Do not summarize or skip fields.\n"
            "- If data is missing (shows blank or pending), say so explicitly.\n"
            "- NEVER fabricate data. NEVER narrate around the data. Give the Commander the facts."
        )

        parts = [context.rstrip(), cos_rules]

        if user_id:
            history = _get_history_context(user_id)
            if history:
                parts.append(history)

        parts.append(f"COMMANDER QUERY: {query}")
        return "\n\n".join(parts)
    except Exception as e:
        logger.error(f"_build_cos_query failed: {e}")
        return f"COMMANDER QUERY: {query}"


def _call_persona_safe(persona_id: str, query: str, max_tokens: int = 2000) -> dict:
    """Call persona via Claude Opus with safety fallbacks.

    Additional safety: on 413 (too large), retries with trimmed query.
    On total failure, returns a safe fallback message instead of crashing.
    """
    import time as _time

    pid = resolve_id(persona_id)

    # Model routing handled by PERSONA_MODEL_MAP in thunderbird_personas.py
    model_override = None

    try:
        result = call_persona(pid, query, max_tokens=max_tokens, model_override=model_override)
        return result
    except Exception as e:
        err_str = str(e)

        # On 413 (too large) — retry with just the question
        if "413" in err_str:
            logger.warning(f"413 payload too large — retrying {pid} with raw query")
            try:
                raw = query.split("CLIENT QUESTION: ")[-1] if "CLIENT QUESTION: " in query else query
                raw = raw.split("QUERY: ")[-1] if "QUERY: " in raw else raw
                return call_persona(pid, raw, model_override=model_override)
            except Exception:
                pass

        # All providers failed — return safe fallback
        logger.error(f"All LLM providers failed for {pid}: {e}")
        persona = get_persona(pid)
        return {
            "persona": pid,
            "name": persona["name"],
            "icon": persona["icon"],
            "answer": (
                "All AI services are temporarily unavailable. "
                "Your message has been logged and John will follow up with you directly."
            ),
        }


async def consult_persona_async(persona_id: str, query: str, user_id: int = None) -> dict:
    """Run persona call in a thread to avoid blocking.

    Dani (A3) gets routed through her full-access engine with conversation history.
    Simple greetings skip the heavy data engine — just persona + conversation history.
    All other personas get the compact operational context.
    """
    loop = asyncio.get_event_loop()
    pid = resolve_id(persona_id)

    if pid == "A3":
        if _is_greeting(query):
            # Simple greeting — skip Sheets/Gmail/dossiers, just use persona + history
            logger.info("Greeting detected — lightweight Dani response")
            parts = [
                "You are Dani Moreau, Luxury Travel Concierge at Dreams2Memories Travel. "
                "Be warm, friendly, and professional. You love your job and your clients."
            ]
            if user_id:
                history = _get_history_context(user_id)
                if history:
                    parts.append(history)
            parts.append(f"CLIENT QUESTION: {query}")
            enriched_query = "\n\n".join(parts)
        else:
            # Full engine — Sheets, Gmail, dossiers, specialists, history
            enriched_query = await loop.run_in_executor(
                None, _build_dani_query, query, user_id or 0
            )
    else:
        enriched_query = await loop.run_in_executor(None, _build_contextual_query, query)

    return await loop.run_in_executor(None, _call_persona_safe, pid, enriched_query)


async def run_staff_meeting_async(query: str) -> dict:
    """Run the synchronous staff meeting in a thread."""
    loop = asyncio.get_event_loop()
    enriched_query = await loop.run_in_executor(None, _build_contextual_query, query)
    return await loop.run_in_executor(None, run_staff_meeting, enriched_query, None)


# ---------------------------------------------------------------------------
# Command Handlers
# ---------------------------------------------------------------------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start — different welcome for Commander vs client."""
    user_id = update.effective_user.id
    # Clients can only /start in private DMs — suppress in groups/channels
    if not _is_commander(user_id) and update.effective_chat.type != "private":
        return
    if _is_commander(user_id):
        # Commander testing Dani's channel — give him the client experience
        await update.message.reply_text(
            "🎭 *Commander Mode — Dani Channel*\n\n"
            "You're connected as a client-side observer. Dani will respond to you "
            "with full client voice. COS review gate is bypassed (you're the approver). "
            "Use this to test, coach, or audit Dani's responses.\n\n"
            "_To access Wing ops, use @D2MC2C\\_bot._",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    else:
        user_first = update.effective_user.first_name or "there"
        welcome = (
            f"✨ *Welcome, {user_first}!*\n\n"
            f"I'm *Dani Moreau*, your personal luxury travel concierge "
            f"at Dreams2Memories Travel.\n\n"
            f"I'm delighted you're here. Whether you're dreaming about "
            f"your next voyage or have questions about an upcoming trip, "
            f"I'm at your service.\n\n"
            f"Here are a few things I can help with right now — "
            f"just tap a button or type your question anytime:\n"
        )
        keyboard = [
            [
                InlineKeyboardButton("🚢 Cruise Price Check", callback_data="dani_cruise_price"),
                InlineKeyboardButton("⚓ Ship Comparison", callback_data="dani_ship_compare"),
            ],
            [
                InlineKeyboardButton("🌍 World Travel Intel", callback_data="dani_world_intel"),
                InlineKeyboardButton("☀️ Weather & Forecast", callback_data="dani_weather"),
            ],
            [
                InlineKeyboardButton("📋 My Trip Details", callback_data="dani_my_trip"),
                InlineKeyboardButton("💬 Ask Dani Anything", callback_data="dani_ask"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            welcome, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup
        )

        # Footer message without buttons
        await update.message.reply_text(
            f"_Dreams2Memories Travel, LLC_\n"
            f"_Luxury travel, personally crafted._",
            parse_mode=ParseMode.MARKDOWN,
        )

        # Notify Commander that a client connected
        bot = update.get_bot()
        user_name = update.effective_user.full_name or "Unknown"
        username = update.effective_user.username or "no-username"
        await _dm_commander(
            bot,
            f"🟢 *NEW CLIENT CONNECTED*\n\n"
            f"*Name:* {user_name}\n"
            f"*Username:* @{username}\n"
            f"*User ID:* {user_id}\n"
            f"*Time:* {datetime.now(timezone.utc).strftime('%H:%M UTC')}"
        )
        return


@commander_only
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help — list commands."""
    lines = [
        "*Thunderbird Wing — Command Reference*\n",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
    ]

    for cmd, pid in COMMAND_MAP.items():
        persona = get_persona(pid)
        lines.append(
            f"/{cmd} — {persona['icon']} {persona['full_name']}\n"
            f"  _{persona['role']}_"
        )

    lines.append("")
    lines.append("/staff <message> — Broadcast to all personas")
    lines.append("")
    lines.append("_Plain text (no command) goes to Dani (A3)._")

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


@commander_only
async def cmd_staff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /staff — broadcast to all personas."""
    query = " ".join(context.args) if context.args else ""
    if not query:
        await update.message.reply_text(
            "Usage: /staff <your question or directive>\n\n"
            "This broadcasts to all Wing personas and collects their responses."
        )
        return

    await update.message.chat.send_action(ChatAction.TYPING)
    logger.info(f"Staff meeting requested: {query[:80]}...")

    result = await run_staff_meeting_async(query)

    if result.get("status") != "success":
        await update.message.reply_text(
            "Staff meeting failed. Check server logs."
        )
        return

    # Send each persona's response as a separate message for readability
    responses = result.get("responses", [])
    count = 0
    for r in responses:
        pid = r.get("persona", "??")
        if "answer" in r:
            header = format_persona_header(pid)
            text = f"{header}\n\n{r['answer']}"
        else:
            persona = get_persona(pid)
            text = f"{persona['icon']} {pid}: _Error — {r.get('error', 'unknown')}_"

        await send_long_message(update, text)
        count += 1

    await update.message.reply_text(
        f"\n_Staff meeting complete — {count} personas responded._",
        parse_mode=ParseMode.MARKDOWN,
    )


@commander_only
async def cmd_persona(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generic handler for all persona slash commands."""
    # Extract the command name (e.g., "dani" from "/dani")
    command = update.message.text.split()[0].lstrip("/").lower()
    # Strip any @botname suffix
    if "@" in command:
        command = command.split("@")[0]

    persona_id = COMMAND_MAP.get(command)
    if not persona_id:
        await update.message.reply_text(f"Unknown persona command: /{command}")
        return

    query = " ".join(context.args) if context.args else ""
    if not query:
        persona = get_persona(persona_id)
        await update.message.reply_text(
            f"Usage: /{command} <your message>\n\n"
            f"{persona['icon']} *{persona['full_name']}*\n"
            f"_{persona['role']}_",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    await update.message.chat.send_action(ChatAction.TYPING)
    logger.info(f"Persona {persona_id} consulted: {query[:80]}...")

    user_id = update.effective_user.id
    _add_to_history(user_id, "user", query)

    # Route through Claude CLI (Opus, $0 via Max plan)
    loop = asyncio.get_event_loop()
    answer = await loop.run_in_executor(
        None, lambda: call_cos_via_cli(query, persona=persona_id, intent_type="TASK")
    )
    result = {"persona": persona_id, "answer": answer}
    _add_to_history(user_id, "assistant", answer)

    header = format_persona_header(persona_id)
    text = f"{header}\n\n{answer}"
    await send_long_message(update, text)

    # If Dani couldn't answer, log it and notify Commander
    if _is_followup_needed(answer):
        user_name = update.effective_user.full_name or "Commander"
        _log_followup(query, answer, user_name)
        bot = update.get_bot()
        await _notify_commander_followup(bot, query, user_name)


# ---------------------------------------------------------------------------
# Dani Quick Actions — inline keyboard button callbacks
# ---------------------------------------------------------------------------

DANI_BUTTON_PROMPTS = {
    "dani_cruise_price": (
        "I'd love to help you explore cruise options! "
        "Which cruise line or destination are you interested in? "
        "I can check current pricing on:\n\n"
        "🚢 *Silversea* · *Regent Seven Seas* · *Cunard*\n"
        "⚓ *Oceania* · *Seabourn* · *Viking*\n"
        "🛳️ *AmaWaterways* · *Ponant*\n\n"
        "Just tell me the cruise line, destination, or dates you're considering!"
    ),
    "dani_ship_compare": (
        "I can compare ships side-by-side for you! "
        "Tell me which two ships or cruise lines you'd like compared, and I'll "
        "pull detailed specs, amenities, dining options, and my personal insights.\n\n"
        "For example: _\"Compare Silver Nova vs Viking Neptune\"_"
    ),
    "dani_world_intel": (
        "Here's what I can look into for you:\n\n"
        "🌍 *Travel advisories* for any destination\n"
        "🏖️ *Port information* and local tips\n"
        "📰 *Cruise industry news* and updates\n\n"
        "Which destination or region would you like intel on?"
    ),
    "dani_weather": (
        "I'd be happy to check the weather for you! ☀️\n\n"
        "Just tell me the city or port, and I'll get you:\n"
        "• Current conditions\n"
        "• Extended forecast\n"
        "• Best time to visit recommendations\n\n"
        "Which destination are you curious about?"
    ),
    "dani_my_trip": (
        "Let me pull up your trip details! 📋\n\n"
        "Could you tell me your name or the booking you'd like to check? "
        "I can look up:\n"
        "• Itinerary and port schedule\n"
        "• Excursion details\n"
        "• Dining reservations\n"
        "• Important dates and deadlines\n"
    ),
    "dani_ask": (
        "I'm all yours! 💬\n\n"
        "Ask me anything about luxury travel, your upcoming trip, "
        "destinations, cruise lines, excursions, dining — whatever's on your mind.\n\n"
        "I have access to real-time booking data, destination intelligence, "
        "and years of luxury travel expertise. Fire away!"
    ),
}


async def handle_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard button presses from Dani's welcome menu."""
    query = update.callback_query
    await query.answer()  # Acknowledge the button press

    callback_data = query.data
    user_id = query.from_user.id
    user_name = query.from_user.full_name or "Client"

    # Commander on Dani's channel — let him use the buttons (client experience for testing/coaching)
    if _is_commander(user_id):
        pass  # Fall through — Commander sees Dani's responses like a client
        return

    # Clients can only use buttons in private DMs
    if query.message.chat.type != "private":
        return

    if callback_data in DANI_BUTTON_PROMPTS:
        response_text = DANI_BUTTON_PROMPTS[callback_data]

        # Track in conversation history so Dani has context for the follow-up
        button_labels = {
            "dani_cruise_price": "Cruise Price Check",
            "dani_ship_compare": "Ship Comparison",
            "dani_world_intel": "World Travel Intel",
            "dani_weather": "Weather & Forecast",
            "dani_my_trip": "My Trip Details",
            "dani_ask": "Ask Dani Anything",
        }
        label = button_labels.get(callback_data, callback_data)
        _add_to_history(user_id, "user", f"[Tapped: {label}]")
        _add_to_history(user_id, "assistant", response_text[:500])

        await query.message.reply_text(
            f"🌟 *{label}*\n\n{response_text}",
            parse_mode=ParseMode.MARKDOWN,
        )

        # Notify Commander
        if not _is_commander(user_id):
            bot = query.get_bot()
            await _dm_commander(
                bot,
                f"📲 *CLIENT BUTTON TAP*\n\n"
                f"*From:* {user_name}\n"
                f"*Action:* {label}\n"
                f"*Time:* {datetime.now(timezone.utc).strftime('%H:%M UTC')}"
            )

        logger.info(f"Button callback: {user_name} tapped {label}")
    else:
        await query.message.reply_text(
            "I'm not sure what that button does — just type your question and I'll help!"
        )


async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Transcribe voice messages via Groq Whisper then route to Dani/COS."""
    import tempfile, os, urllib.request, urllib.error

    ack = await update.message.reply_text("🎙 Transcribing...")
    try:
        voice = update.message.voice
        file = await context.bot.get_file(voice.file_id)
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            tmp_path = tmp.name
        await file.download_to_drive(tmp_path)

        groq_key = os.environ.get("GROQ_API_KEY", "os.environ.get("GROQ_API_KEY", "")")
        with open(tmp_path, "rb") as f:
            audio_data = f.read()
        os.unlink(tmp_path)

        # Multipart form upload to Groq Whisper
        boundary = "----ThunderbirdBoundary"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="voice.ogg"\r\n'
            f"Content-Type: audio/ogg\r\n\r\n"
        ).encode() + audio_data + (
            f"\r\n--{boundary}\r\n"
            f'Content-Disposition: form-data; name="model"\r\n\r\nwhisper-large-v3-turbo\r\n'
            f"--{boundary}--\r\n"
        ).encode()

        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/audio/transcriptions",
            data=body,
            headers={
                "Authorization": f"Bearer {groq_key}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            }
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
        transcript = result.get("text", "").strip()

        if not transcript:
            await ack.edit_text("🎙 Could not transcribe — please try again.")
            return

        await ack.edit_text(f"🎙 *Transcribed:* _{transcript}_", parse_mode="Markdown")

        # Inject transcript as a plain text message into the normal flow
        update.message.text = transcript
        await handle_plain_text(update, context)

    except Exception as e:
        logger.error(f"Voice transcription failed: {e}")
        await ack.edit_text("🎙 Transcription failed — please type your message.")


async def handle_plain_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle plain text messages.

    Commander: direct to COS (Hale), no review gate.
    Client: Dani answers → COS reviews → send → notify Commander always.
    """
    # ⚠️ COMMANDER KILL SWITCH — Standing Order 2026-03-25
    if not DANI_BOT_ENABLED:
        logger.warning(
            f"[DANI-BOT-LOCKED] Incoming message from {update.effective_user.id} ignored. "
            "DANI_BOT_ENABLED=False. Re-enable after supplier audit."
        )
        return  # Silent lock — no response to client, no tokens consumed

    query = update.message.text
    if not query or not query.strip():
        return

    user_id = update.effective_user.id
    is_cmdr = _is_commander(user_id)
    user_name = update.effective_user.full_name or "Unknown"
    chat_type = update.effective_chat.type  # "private", "group", "supergroup", "channel"

    # ── SECURITY: Dani must NEVER respond on group/public channels ──
    # Commander can use the bot anywhere; clients must DM only.
    if not is_cmdr and chat_type != "private":
        logger.info(
            f"Ignoring non-private msg from {user_name} (uid={user_id}) "
            f"in {chat_type} chat {update.effective_chat.id}"
        )
        return

    await update.message.chat.send_action(ChatAction.TYPING)

    _add_to_history(user_id, "user", query)

    loop = asyncio.get_event_loop()
    if is_cmdr:
        # Commander testing Dani's channel — route through client path so he hears her voice
        logger.info(f"Commander msg on Dani channel -> A3 (Dani) client path: {query[:80]}...")
        enriched_query = await loop.run_in_executor(
            None, lambda: _build_dani_query_client(query, user_id)
        )
        result = await loop.run_in_executor(None, _call_persona_safe, DEFAULT_PERSONA, enriched_query)
    else:
        # Client → Dani with filtered context
        logger.info(f"Client msg -> A3 (Dani): {query[:80]}...")
        enriched_query = await loop.run_in_executor(
            None, lambda: _build_dani_query_client(query, user_id)
        )
        result = await loop.run_in_executor(None, _call_persona_safe, DEFAULT_PERSONA, enriched_query)

    answer = result.get("answer", FALLBACK_MSG)

    # Sculptor Gate — Z1 three-pass polish (Tone → Format → Voice) before send gates
    if not is_cmdr:
        try:
            from thunderbird_doc_sculptor import sculpt_for_dani
            polished, _changes = sculpt_for_dani(answer, {
                "name": user_name,
                "tier": "client",
                "context": query
            })
            if polished and polished.strip():
                answer = polished
                logger.info(f"Sculptor polished response for {user_name} ({len(_changes)} changes)")
        except Exception as _e:
            logger.debug(f"Sculptor skipped: {_e}")

    # Pre-Send Evaluator Gate — fast regex, zero API cost, runs first
    cos_note = ""
    if not is_cmdr:
        presend = pre_send_evaluate(answer)
        if presend["blocked"]:
            flag_summary = "; ".join(f"{f['type']}='{f['match']}'" for f in presend["flags"])
            logger.warning(f"PRE-SEND BLOCKED for {user_name}: {flag_summary}")
            answer = (
                "Thank you for your question! I'm checking on this with our team "
                "and John will follow up with you shortly."
            )
            cos_note = f"PRE-SEND BLOCKED [{flag_summary}] — COS review skipped."
        else:
            if not presend["clean"]:
                flag_summary = "; ".join(f"{f['type']}='{f['match']}'" for f in presend["flags"])
                logger.info(f"PRE-SEND flagged (non-blocking) for {user_name}: {flag_summary}")

            # COS Review Gate — clients only (runs after pre-send passes)
            cos_result = await loop.run_in_executor(
                None, cos_review, query, answer, True  # is_client=True
            )
            cos_note = cos_result.get("note", "")

            if not cos_result.get("approved", True):
                # COS blocked this response — don't send it to client
                logger.warning(f"COS BLOCKED response to {user_name}: {cos_note}")
                answer = (
                    "Thank you for your question! I'm checking on this with our team "
                    "and John will follow up with you shortly."
                )
            elif cos_result.get("revised"):
                # COS revised the response — use the revised version
                logger.info(f"COS revised response for {user_name}")
                answer = cos_result["revised"]

    _add_to_history(user_id, "assistant", answer)

    header = format_persona_header(COMMANDER_PERSONA if is_cmdr else DEFAULT_PERSONA)
    text = f"{header}\n\n{answer}"
    await send_long_message(update, text)

    bot = update.get_bot()

    if not is_cmdr:
        # LOG: Persistent record of every client interaction
        _log_client_interaction(user_id, user_name, query, answer, cos_note)
        # AUTONOMOUS MODE (2026-03-19): lightweight Commander visibility — read-only, no approval needed
        await _notify_commander(
            bot,
            f"📲 *Dani → {user_name}*\n_{answer[:200]}_"
        )
        # Additional follow-up alert if Dani couldn't answer
        if _is_followup_needed(answer):
            _log_followup(query, answer, user_name)
            await _notify_commander_followup(bot, query, user_name)
    else:
        # COMMANDER: only notify on follow-up needed
        if _is_followup_needed(answer):
            _log_followup(query, answer, "Commander")
            await _notify_commander_followup(bot, query, "Commander")


# ---------------------------------------------------------------------------
# Client Interaction Log — every Dani contact logged persistently
# ---------------------------------------------------------------------------

CLIENT_LOG_FILE = os.path.expanduser("~/Thunderbird/logs/dani_client_interactions.jsonl")
CLIENT_LOG_MD = os.path.expanduser("~/Thunderbird/logs/dani_client_interactions.md")


def _log_client_interaction(user_id: int, user_name: str, query: str,
                            answer: str, cos_note: str = ""):
    """Log every client interaction to JSONL + Markdown for Commander review."""
    try:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        ts_short = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

        # JSONL — machine-readable, append-only
        entry = {
            "timestamp": ts,
            "user_id": user_id,
            "user_name": user_name,
            "query": query,
            "answer": answer[:1000],
            "cos_note": cos_note,
            "channel": "telegram",
        }
        os.makedirs(os.path.dirname(CLIENT_LOG_FILE), exist_ok=True)
        with open(CLIENT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

        # Markdown — human-readable
        if not os.path.exists(CLIENT_LOG_MD):
            with open(CLIENT_LOG_MD, "w", encoding="utf-8") as f:
                f.write("# Dani Client Interaction Log\n\n"
                        "Every client contact with Dani — Telegram + Email.\n\n"
                        "---\n")
        with open(CLIENT_LOG_MD, "a", encoding="utf-8") as f:
            cos_line = f"\n**COS Note:** {cos_note}" if cos_note else ""
            f.write(
                f"\n## {ts_short} — {user_name}\n"
                f"**Channel:** Telegram\n"
                f"**Question:** {query}\n"
                f"**Dani:** {answer[:300]}{'...' if len(answer) > 300 else ''}"
                f"{cos_line}\n\n---\n"
            )

        logger.info(f"Client interaction logged: {user_name} @ {ts_short}")
    except Exception as e:
        logger.error(f"Client interaction log failed: {e}")


# ---------------------------------------------------------------------------
# Follow-up queue — when Dani can't answer, notify John
# ---------------------------------------------------------------------------

FOLLOWUP_FILE = os.path.expanduser("~/Thunderbird/dani_followups.md")
FOLLOWUP_PHRASES = [
    "i don't have that",
    "forward your question to john",
    "get back to you",
    "i'll forward",
    "don't have that information",
    "flagged this for john",
]


def _is_followup_needed(answer: str) -> bool:
    """Detect if Dani's answer indicates she couldn't help."""
    answer_lower = answer.lower()
    return any(phrase in answer_lower for phrase in FOLLOWUP_PHRASES)


def _log_followup(query: str, answer: str, user_name: str = "Commander"):
    """Log unanswered question to the follow-up file."""
    try:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        entry = (
            f"\n## {ts}\n"
            f"**From:** {user_name}\n"
            f"**Question:** {query}\n"
            f"**Dani's response:** {answer[:200]}\n"
            f"**Status:** OPEN\n"
        )

        # Create file with header if it doesn't exist
        if not os.path.exists(FOLLOWUP_FILE):
            with open(FOLLOWUP_FILE, "w") as f:
                f.write("# Dani Follow-Up Queue\n\n"
                        "Questions Dani couldn't answer — John needs to respond.\n\n"
                        "---\n")

        with open(FOLLOWUP_FILE, "a") as f:
            f.write(entry)

        logger.info(f"Follow-up logged: {query[:60]}...")
    except Exception as e:
        logger.error(f"Failed to log follow-up: {e}")


def _dm_commander_c2(text: str):
    """Send an internal Commander DM via the C2 bot (D2MC2C). Non-client traffic only."""
    import requests as _requests
    for commander_id in AUTHORIZED_IDS:
        try:
            _requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_C2_BOT_TOKEN}/sendMessage",
                json={"chat_id": commander_id, "text": text, "parse_mode": "Markdown"},
                timeout=10,
            )
        except Exception as e:
            logger.error(f"C2 Commander notify failed (ID {commander_id}): {e}")
            try:
                plain = text.replace("*", "").replace("_", "")
                _requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_C2_BOT_TOKEN}/sendMessage",
                    json={"chat_id": commander_id, "text": plain},
                    timeout=10,
                )
            except Exception as e2:
                logger.error(f"C2 fallback notify also failed: {e2}")


async def _notify_commander_followup(bot, query: str, user_name: str = "Client"):
    """DM the Commander about a question Dani couldn't answer. Action required."""
    ts = datetime.now(timezone.utc).strftime("%H:%M UTC")
    notice = (
        f"🔴 *DANI NEEDS HELP — {ts}*\n\n"
        f"*From:* {user_name}\n"
        f"*Question:* _{query}_\n\n"
        "Dani could not answer from available data.\n"
        "*Action required.*"
    )
    _dm_commander_c2(notice)


async def _notify_commander_client_msg(bot, query: str, answer: str,
                                        user_name: str = "Client",
                                        cos_note: str = ""):
    """DM the Commander on EVERY client interaction — awareness, not just failures."""
    ts = datetime.now(timezone.utc).strftime("%H:%M UTC")
    # Full response — no truncation (Telegram splits automatically via send_long_message)
    cos_line = f"\n*COS:* {cos_note}" if cos_note else ""

    notice = (
        f"💬 *CLIENT MESSAGE — {ts}*\n\n"
        f"*From:* {user_name}\n"
        f"*Question:* _{query}_\n\n"
        f"*Dani's response:* {answer}{cos_line}"
    )
    _dm_commander_c2(notice)


async def _dm_commander(bot, text: str):
    """Send a DM to all authorized Commander IDs."""
    for commander_id in AUTHORIZED_IDS:
        try:
            await bot.send_message(
                chat_id=commander_id,
                text=text,
                parse_mode=ParseMode.MARKDOWN,
            )
            logger.info(f"Commander notified (ID {commander_id})")
        except Exception as e:
            logger.error(f"Failed to notify Commander {commander_id}: {e}")
            # Fallback without markdown
            try:
                plain = text.replace("*", "").replace("_", "")
                await bot.send_message(chat_id=commander_id, text=plain)
            except Exception as e2:
                logger.error(f"Fallback notify also failed: {e2}")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Log errors from the telegram bot."""
    from telegram.error import Conflict
    import os, signal
    if isinstance(context.error, Conflict):
        logger.critical("409 Conflict — duplicate Dani instance detected. Exiting for clean systemd restart.")
        os.kill(os.getpid(), signal.SIGTERM)
        return
    logger.error(f"Telegram bot error: {context.error}", exc_info=context.error)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    """Start the Thunderbird Telegram bot."""
    logger.info("Initializing Thunderbird Telegram Bot...")
    logger.info(f"Authorized user IDs: {AUTHORIZED_IDS or 'NONE (open access — set TELEGRAM_COMMANDER_ID!)'}")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Register command handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("staff", cmd_staff))

    # Register persona commands
    for cmd_name in COMMAND_MAP:
        app.add_handler(CommandHandler(cmd_name, cmd_persona))

    # Inline keyboard button callbacks (Dani's quick actions)
    app.add_handler(CallbackQueryHandler(handle_button_callback))

    # Plain text fallback — route to Dani
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_plain_text))

    # Voice messages — transcribe via Groq Whisper then route to Dani
    app.add_handler(MessageHandler(filters.VOICE, handle_voice_message))

    # Error handler
    app.add_error_handler(error_handler)

    logger.info("Thunderbird Telegram Bot is online. Polling...")
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
        bootstrap_retries=5,
    )


if __name__ == "__main__":
    main()
