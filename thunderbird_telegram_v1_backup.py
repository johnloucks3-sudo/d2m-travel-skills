"""
Thunderbird Telegram Bot — D2M Client-Facing Concierge + Commander Interface
=============================================================================

Two access modes:
  1. COMMANDER — full Wing access (all persona commands, staff meetings)
  2. CLIENT — talks to Dani only, COS reviews before sending, Commander notified

Commands (Commander only):
  /start        — Welcome message
  /help         — List all commands
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

Client access:
  Plain text → Dani → COS review → respond → notify Commander

Environment Variables:
  TELEGRAM_BOT_TOKEN     — from BotFather
  TELEGRAM_COMMANDER_ID  — your Telegram user ID (numeric)

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

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from telegram.constants import ChatAction, ParseMode

# Import the existing persona system
from thunderbird_personas import (
    call_persona,
    run_staff_meeting,
    get_persona,
    get_roster,
    PERSONA_REGISTRY,
    resolve_id,
)
from thunderbird_context import gather_commander_context
from thunderbird_dani_engine import build_dani_context, cos_review
from thunderbird_telegram_tools import call_cos_with_tools

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_COMMANDER_ID = os.environ.get("TELEGRAM_COMMANDER_ID", "")

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
    # "ikeda": "A10",  # Decommissioned — duties absorbed by COS
    "washington": "CH",
    "elon": "A12",
}

DEFAULT_PERSONA = "A3"      # Dani handles client plain-text messages
COMMANDER_PERSONA = "COS"   # COS handles Commander plain-text messages

# Telegram message length limit
MAX_MESSAGE_LENGTH = 4096

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
# Access control
# ---------------------------------------------------------------------------

def _is_commander(user_id: int) -> bool:
    """Check if this user is the Commander."""
    return bool(AUTHORIZED_IDS) and user_id in AUTHORIZED_IDS


def commander_only(func):
    """Restrict handler to authorized Telegram user IDs (Commander)."""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not _is_commander(user_id):
            logger.warning(
                f"Non-commander tried staff command from user_id={user_id} "
                f"(@{update.effective_user.username})"
            )
            await update.message.reply_text(
                "That command is reserved for the D2M team. "
                "Just send me your question as a plain message and I'll help you!"
            )
            return
        return await func(update, context)
    return wrapper


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


def _build_dani_query(query: str, user_id: int = None) -> str:
    """Build Dani's full-access query — pulls from ALL data sources.

    Dani gets: bookings, dossiers, Sheets, Gmail, anchor dates,
    specialist consultation, AND recent conversation context.
    Commander mode — full access including financials.
    """
    try:
        context = build_dani_context(query, is_commander=True)
        parts = [context]

        # Add conversation history so Dani doesn't repeat herself
        if user_id:
            history = _get_history_context(user_id)
            if history:
                parts.append(history)

        parts.append(f"CLIENT QUESTION: {query}")
        return "\n\n".join(parts)
    except Exception as e:
        logger.warning(f"Dani engine failed, falling back to basic context: {e}")
        return _build_contextual_query(query)


def _build_cos_query(query: str, user_id: int = None) -> str:
    """Build COS query using the Dani data engine but with COS-appropriate rules.

    Same rich data (bookings, dossiers, Sheets, Gmail, anchor dates) but:
    - Strips Dani's persona rules from the context
    - Replaces with COS briefing instructions
    - Labels the query as COMMANDER QUERY, not CLIENT QUESTION
    """
    try:
        context = build_dani_context(query, is_commander=True)

        # Strip Dani's rules — COS has her own system prompt
        if "DANI'S RULES:" in context:
            context = context[:context.index("DANI'S RULES:")]

        # Add COS-specific data presentation rules
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
        logger.warning(f"COS data engine failed, falling back to basic context: {e}")
        return _build_contextual_query(query)


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


# Groq model override for Dani (used when Gemini is down and Groq fallback kicks in)
DANI_GROQ_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"


def _call_persona_safe(persona_id: str, query: str, max_tokens: int = 600) -> dict:
    """Call persona with Gemini→Groq failover (handled by call_persona).

    Additional safety: on 413 (too large), retries with trimmed query.
    On total failure, returns a safe fallback message instead of crashing.
    """
    import time as _time

    pid = resolve_id(persona_id)

    # Dani gets a specific Groq model for the fallback path
    model_override = DANI_GROQ_MODEL if pid == "A3" else None

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
    if _is_commander(user_id):
        welcome = (
            "Welcome to *Thunderbird Command*, Commander.\n\n"
            "Your Wing is standing by. Use a persona command to consult staff, "
            "or just type a message to reach Dani (A3).\n\n"
            "Type /help for the full command list.\n\n"
            f"_Dreams2Memories Travel, LLC_\n"
            f"_{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_"
        )
    else:
        user_first = update.effective_user.first_name or "there"
        welcome = (
            f"Welcome, {user_first}! I'm *Dani Moreau*, your luxury travel "
            f"concierge at Dreams2Memories Travel.\n\n"
            f"I can help you with:\n"
            f"• Your upcoming trip details and itinerary\n"
            f"• Excursion and dining information\n"
            f"• Travel logistics and port information\n"
            f"• Destination questions\n\n"
            f"Just type your question and I'll take care of it!\n\n"
            f"_Dreams2Memories Travel, LLC_"
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
    await update.message.reply_text(welcome, parse_mode=ParseMode.MARKDOWN)


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

    result = await consult_persona_async(persona_id, query, user_id=user_id)

    answer = result.get("answer", FALLBACK_MSG)
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


async def handle_plain_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle plain text messages.

    Commander: direct to COS (Hale), no review gate.
    Client: Dani answers → COS reviews → send → notify Commander always.
    """
    query = update.message.text
    if not query or not query.strip():
        return

    user_id = update.effective_user.id
    is_cmdr = _is_commander(user_id)
    user_name = update.effective_user.full_name or "Unknown"

    await update.message.chat.send_action(ChatAction.TYPING)

    _add_to_history(user_id, "user", query)

    loop = asyncio.get_event_loop()
    if is_cmdr:
        # Commander → Gemini COS with real tool access
        logger.info(f"Commander msg -> COS (Gemini + tools): {query[:80]}...")

        # Build conversation history for context
        history = _conversation_history.get(user_id, [])
        conv_hist = [{"role": h["role"], "text": h["text"]} for h in history[:-1]]  # exclude current msg (already added)

        try:
            answer_text = await loop.run_in_executor(
                None, lambda: call_cos_with_tools(query, conv_hist or None)
            )
            result = {
                "persona": "COS",
                "name": "Col Victoria Hale",
                "icon": "🎖️",
                "answer": answer_text,
            }
        except Exception as e:
            logger.error(f"Gemini tool-calling failed, falling back to Groq COS: {e}")
            # Fallback to original Groq path
            enriched_query = await loop.run_in_executor(
                None, _build_cos_query, query, user_id
            )
            result = await loop.run_in_executor(
                None, lambda: _call_persona_safe(COMMANDER_PERSONA, enriched_query, max_tokens=1500)
            )
    else:
        # Client → Dani with filtered context
        logger.info(f"Client msg -> A3 (Dani): {query[:80]}...")
        enriched_query = await loop.run_in_executor(
            None, lambda: _build_dani_query_client(query, user_id)
        )
        result = await loop.run_in_executor(None, _call_persona_safe, DEFAULT_PERSONA, enriched_query)

    answer = result.get("answer", FALLBACK_MSG)

    # COS Review Gate — clients only
    cos_note = ""
    if not is_cmdr:
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
        # CLIENT: Always notify Commander — every single interaction
        await _notify_commander_client_msg(
            bot, query, answer, user_name, cos_note
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


async def _notify_commander_followup(bot, query: str, user_name: str = "Client"):
    """DM the Commander about a question Dani couldn't answer. Action required."""
    ts = datetime.now(timezone.utc).strftime("%H:%M UTC")
    notice = (
        f"🔴 *DANI NEEDS HELP — {ts}*\n\n"
        f"*From:* {user_name}\n"
        f"*Question:* _{query[:300]}_\n\n"
        "Dani could not answer from available data.\n"
        "*Action required.*"
    )
    await _dm_commander(bot, notice)


async def _notify_commander_client_msg(bot, query: str, answer: str,
                                        user_name: str = "Client",
                                        cos_note: str = ""):
    """DM the Commander on EVERY client interaction — awareness, not just failures."""
    ts = datetime.now(timezone.utc).strftime("%H:%M UTC")
    # Truncate answer for readability
    short_answer = answer[:200] + "..." if len(answer) > 200 else answer
    cos_line = f"\n*COS:* {cos_note}" if cos_note else ""

    notice = (
        f"💬 *CLIENT MESSAGE — {ts}*\n\n"
        f"*From:* {user_name}\n"
        f"*Question:* _{query[:300]}_\n\n"
        f"*Dani's response:* {short_answer}{cos_line}"
    )
    await _dm_commander(bot, notice)


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

    # Plain text fallback — route to Dani
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_plain_text))

    # Error handler
    app.add_error_handler(error_handler)

    logger.info("Thunderbird Telegram Bot is online. Polling...")
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
