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
  /sss          — Staff Summary Sheet (formal coordination)
  /drafts       — Pending email drafts for approval
  /scan         — Scan all dossiers for gaps and issues
  /learn        — Learning compiler: digest, approve/reject/edit/supersede/history
  /voice        — Voice ledger summary
  /inbox        — Sweep Commander's personal inbox for D2M emails

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
import time
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
    call_cos_via_sdk,
    classify_intent,
    _is_draft_request,
)
from thunderbird_telegram_fmt import (
    md_to_telegram,
    send_claude_response,
    send_telegram,
    split_message,
    escape_md2,
    sitrep_to_telegram,
    SitrepBrief,
    _PYDANTIC_AVAILABLE,
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
MAX_HISTORY = 40  # Doubled again from 20 — Commander directive 2026-03-20

def _add_to_history(user_id: int, role: str, text: str):
    if user_id not in _conversation_history:
        _conversation_history[user_id] = []
    _conversation_history[user_id].append({
        "role": role, "text": text[:3200],  # Doubled again from 1600 — Commander directive 2026-03-20
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
# Progress infrastructure — replaces silent "typing..." for long ops
# ---------------------------------------------------------------------------

_PROGRESS_RATE_LIMIT = 1.5  # min seconds between status message edits


async def _typing_heartbeat(update: Update, stop_event: asyncio.Event) -> None:
    """Send typing action every 4s until stop_event fires."""
    while not stop_event.is_set():
        try:
            await update.message.chat.send_action(ChatAction.TYPING)
        except Exception:
            pass
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=4.0)
        except asyncio.TimeoutError:
            pass


async def _make_progress_updater(msg, stop_event: asyncio.Event, update: Update):
    """Create a live progress updater for long-running agent calls.

    Returns (on_progress, heartbeat_task, typing_task).

    on_progress(text): edits msg with current tool activity (rate-limited 3s).
    heartbeat_task: edits msg every 60s with elapsed time + last activity.
    typing_task: sends Telegram typing indicator every 4s.

    Caller must set stop_event and cancel both tasks when done.
    """
    start_time = time.monotonic()
    _last_edit: list[float] = [0.0]
    _last_activity: list[str] = ["Working..."]

    async def on_progress(text: str) -> None:
        _last_activity[0] = text[:60]
        now = time.monotonic()
        if now - _last_edit[0] < _PROGRESS_RATE_LIMIT:
            return
        _last_edit[0] = now
        try:
            await msg.edit_text(f"⚙️ {text[:200]}")
        except Exception:
            pass

    async def _heartbeat() -> None:
        while not stop_event.is_set():
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=8.0)
            except asyncio.TimeoutError:
                pass
            if stop_event.is_set():
                break
            elapsed = int(time.monotonic() - start_time)
            mins, secs = divmod(elapsed, 60)
            elapsed_str = f"{mins}m {secs}s" if mins else f"{secs}s"
            activity = _last_activity[0]
            try:
                await msg.edit_text(f"⏳ {elapsed_str} — {activity}")
                await update.message.chat.send_action(ChatAction.TYPING)
            except Exception:
                pass

    hb_task = asyncio.create_task(_heartbeat())
    typing_task = asyncio.create_task(_typing_heartbeat(update, stop_event))
    return on_progress, hb_task, typing_task


async def _run_with_typing(update: Update, coro_or_callable, loop=None):
    """Legacy: run a blocking callable in executor with typing indicator.

    Used by commands that haven't been upgraded to _make_progress_updater yet.
    """
    stop_typing = asyncio.Event()
    typing_task = asyncio.create_task(_typing_heartbeat(update, stop_typing))
    _loop = loop or asyncio.get_event_loop()
    try:
        result = await _loop.run_in_executor(None, coro_or_callable)
        return result
    finally:
        stop_typing.set()
        try:
            await asyncio.wait_for(typing_task, timeout=0.5)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            pass


# ---------------------------------------------------------------------------
# Message sending helper
# ---------------------------------------------------------------------------

async def send_long_message(update: Update, text: str):
    """Send Claude's markdown response with MarkdownV2 conversion and smart splitting."""
    await send_claude_response(update, text)

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
        "/sss — Staff Summary Sheet (formal coordination)",
        "/drafts — Pending email drafts for approval",
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "*IOC Commands*",
        "/scan — Scan all dossiers for gaps and issues",
        "/learn — Learning: digest, approve/reject/edit/supersede/history",
        "/voice — Voice ledger summary",
        "/inbox — Sweep Commander's personal inbox for D2M emails",
        "/usage — Claude Code usage meter (tokens, cost, block, monthly)",
        "/restart — Restart both Telegram bots (C2 + Dani)",
        "/intel — Push morning intel brief now (A2→A1→COS chain)",
        "/brief — Push FPD/departure/CC brief now",
        "/fpd — FPD alert scan",
        "/dossier <name> — Quick dossier lookup by client name",
        "/ask <query> — Search intel archives for D2M-applicable insights",
        "",
        "_Type \"STAFF SUMMARY\" to start an SSS._",
        "_Plain text goes to COS (Opus via Agent SDK)._",
    ])
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN_V2)


@commander_only
async def cmd_sitrep(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Quick status report — structured output (Pydantic) or markdown fallback."""
    ack_msg = await update.message.reply_text("📊 Assembling SITREP...")

    # Structured output path (Pydantic + direct Anthropic client)
    if _PYDANTIC_AVAILABLE and SitrepBrief and os.environ.get("ANTHROPIC_API_KEY"):
        loop = asyncio.get_event_loop()
        try:
            def _structured_sitrep():
                import anthropic
                client = anthropic.Anthropic()
                response = client.messages.parse(
                    model="claude-3-5-haiku-20241022",  # Haiku — SITREP is classification/lookup, not creative (SO-2026-03-25)
                    max_tokens=1024,
                    system=(
                        "You are COS Hale assembling a SITREP for Commander Loucks at "
                        "Dreams2Memories Travel. Pull real booking data from your knowledge. "
                        "Be precise: client names, dates, amounts, deadlines. "
                        "Status: GREEN=all nominal, AMBER=attention needed, RED=urgent."
                    ),
                    messages=[{"role": "user", "content":
                        "SITREP: status of all active bookings, pending actions, flags."}],
                    output_format=SitrepBrief,
                )
                return response.parsed_output

            brief = await loop.run_in_executor(None, _structured_sitrep)
            await ack_msg.delete()
            _log_command("SITREP", "COS", "structured", str(brief))
            header = format_persona_header("COS")
            body = sitrep_to_telegram(brief)
            await send_long_message(update, f"{header}\n\n{body}")
            return
        except Exception as e:
            logger.warning("Structured SITREP failed (%s) — falling back to SDK", e)

    # SDK fallback
    query = "SITREP: Give me a quick status on all active bookings, pending actions, and system health."
    stop_event = asyncio.Event()
    on_progress, hb_task, typing_task = await _make_progress_updater(ack_msg, stop_event, update)
    try:
        result = await call_cos_via_sdk(
            message=query, persona="COS", intent_type="SITREP", on_progress=on_progress
        )
        answer = result.get("response", "COS reporting: No response generated.")
    except Exception as e:
        logger.error(f"SITREP failed: {e}")
        answer = f"SITREP error: {e}"
    finally:
        stop_event.set()
        hb_task.cancel()
        typing_task.cancel()

    try:
        await ack_msg.delete()
    except Exception:
        pass

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

    logger.info(f"Staff meeting via C2: {query}")

    staff_query = (
        f"STAFF MEETING REQUEST from Commander:\n\n{query}\n\n"
        "Consult all relevant Wing personas and compile their responses. "
        "Use subagents if needed for parallel consultation."
    )

    ack_msg = await update.message.reply_text("🪖 Convening staff...")

    stop_event = asyncio.Event()
    on_progress, hb_task, typing_task = await _make_progress_updater(ack_msg, stop_event, update)
    try:
        result = await call_cos_via_sdk(
            message=staff_query, persona="COS", intent_type="TASK", on_progress=on_progress
        )
        answer = result.get("response", "COS reporting: No response generated.")
    except Exception as e:
        logger.error(f"Staff meeting failed: {e}")
        answer = f"Staff meeting error: {e}"
    finally:
        stop_event.set()
        hb_task.cancel()
        typing_task.cancel()

    try:
        await ack_msg.delete()
    except Exception:
        pass

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

    logger.info(f"C2 persona {persona_id}: {query}")

    user_id = update.effective_user.id
    _add_to_history(user_id, "user", f"[/{command}] {query}")

    # Drafting personas always use direct client (thinking+caching+Files API)
    # For other personas, activate draft mode if message is a drafting request
    _DRAFTING_PERSONAS = {"A3", "EXEC", "A6"}
    is_draft = persona_id in _DRAFTING_PERSONAS or _is_draft_request(query)

    ack_msg = await update.message.reply_text("⚙️ Working...")
    stop_event = asyncio.Event()
    on_progress, hb_task, typing_task = await _make_progress_updater(ack_msg, stop_event, update)
    try:
        result = await call_cos_via_sdk(
            message=query, persona=persona_id, intent_type="TASK",
            on_progress=on_progress, draft_mode=is_draft,
        )
        answer = result.get("response", "COS reporting: No response generated.")
    except Exception as e:
        logger.error(f"C2 persona call failed: {e}")
        answer = f"Error: {e}"
    finally:
        stop_event.set()
        hb_task.cancel()
        typing_task.cancel()

    try:
        await ack_msg.delete()
    except Exception:
        pass

    _add_to_history(user_id, "assistant", answer)
    _log_command("TASK", persona_id, query, answer)

    header = format_persona_header(persona_id)
    await send_long_message(update, f"{header}\n\n{answer}")


@commander_only
async def cmd_scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Scan all dossiers for gaps and issues."""
    ack = await update.message.reply_text("🔍 Scanning dossiers...")
    loop = asyncio.get_event_loop()
    try:
        from thunderbird_dossier_scanner import scan_all_dossiers, generate_alert_digest
        alerts = await loop.run_in_executor(None, scan_all_dossiers)
        digest = await loop.run_in_executor(None, generate_alert_digest)
        await ack.delete()
        critical = sum(1 for a in alerts if a.severity == 'CRITICAL')
        text = f"📋 *Dossier Scan: {len(alerts)} alerts*\n"
        text += f"🔴 {critical} critical\n\n{digest[:3500]}"
        await send_long_message(update, text)
    except Exception as e:
        await ack.edit_text(f"Scan failed: {e}")


@commander_only
async def cmd_learn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Learning compiler — full subcommand handler.

    /learn              — digest + pending principles
    /learn approve <id> — approve a principle
    /learn reject <id>  — reject a principle
    /learn edit <id> <new_text> — edit and approve
    /learn history      — principle history
    /learn supersede <id> <new_text> — supersede with temporal versioning
    """
    from thunderbird_learning import (
        get_learning_digest,
        validate_principle,
        list_rules,
        get_principle_history,
        supersede_principle,
    )

    args = context.args or []
    subcmd = args[0].lower() if args else ""

    # ── /learn (no args) — digest + pending ──
    if not subcmd:
        digest = get_learning_digest()
        pending = list_rules(status="pending", limit=10)
        text = f"*Learning Compiler*\n\n{digest or 'No corrections captured yet.'}"
        if pending:
            text += f"\n\n*{len(pending)} Pending Principles:*\n"
            for p in pending:
                tier = p.get("priority_tier", "ctx")[:3].upper()
                domain = p.get("domain", "voice")
                pid = p.get("persona_id") or "ALL"
                text += (
                    f"\n`#{p['rule_id']}` [{tier}] [{domain}] @{pid}\n"
                    f"  {p['principle_text'][:150]}\n"
                )
            text += (
                "\n_Commands:_\n"
                "`/learn approve <id>` — approve\n"
                "`/learn reject <id>` — reject\n"
                "`/learn edit <id> <text>` — edit & approve\n"
                "`/learn supersede <id> <text>` — replace with versioning\n"
                "`/learn history` — full history"
            )
        await send_long_message(update, text)
        return

    # ── /learn approve <id> ──
    if subcmd == "approve":
        if len(args) < 2 or not args[1].isdigit():
            await update.message.reply_text("Usage: `/learn approve <id>`", parse_mode=ParseMode.MARKDOWN_V2)
            return
        rule_id = int(args[1])
        result = validate_principle(rule_id, action="approve")
        if "error" in result:
            await update.message.reply_text(f"Error: {result['error']}")
        else:
            text = result.get("principle_text", "")[:200]
            await update.message.reply_text(
                f"Principle `#{rule_id}` *APPROVED*\n\n_{text}_",
                parse_mode=ParseMode.MARKDOWN,
            )
            _log_command("LEARN_APPROVE", "LEARNING", f"rule_id={rule_id}", f"approved: {text[:80]}")
        return

    # ── /learn reject <id> ──
    if subcmd == "reject":
        if len(args) < 2 or not args[1].isdigit():
            await update.message.reply_text("Usage: `/learn reject <id>`", parse_mode=ParseMode.MARKDOWN_V2)
            return
        rule_id = int(args[1])
        result = validate_principle(rule_id, action="reject")
        if "error" in result:
            await update.message.reply_text(f"Error: {result['error']}")
        else:
            await update.message.reply_text(
                f"Principle `#{rule_id}` *REJECTED*",
                parse_mode=ParseMode.MARKDOWN,
            )
            _log_command("LEARN_REJECT", "LEARNING", f"rule_id={rule_id}", "rejected")
        return

    # ── /learn edit <id> <new_text> ──
    if subcmd == "edit":
        if len(args) < 3 or not args[1].isdigit():
            await update.message.reply_text(
                "Usage: `/learn edit <id> <new principle text>`",
                parse_mode=ParseMode.MARKDOWN,
            )
            return
        rule_id = int(args[1])
        new_text = " ".join(args[2:])
        result = validate_principle(rule_id, action="edit", edited_text=new_text)
        if "error" in result:
            await update.message.reply_text(f"Error: {result['error']}")
        else:
            await update.message.reply_text(
                f"Principle `#{rule_id}` *EDITED & APPROVED*\n\n_{new_text[:200]}_",
                parse_mode=ParseMode.MARKDOWN,
            )
            _log_command("LEARN_EDIT", "LEARNING", f"rule_id={rule_id}", f"edited: {new_text[:80]}")
        return

    # ── /learn history ──
    if subcmd == "history":
        history = get_principle_history()
        if not history:
            await update.message.reply_text("No principle history found.")
            return
        text = f"*Principle History* ({len(history)} entries)\n"
        for h in history[:15]:
            status_icon = {"approved": "+", "rejected": "x", "pending": "?"}.get(
                h.get("validation_status", ""), "?"
            )
            superseded = f" -> #{h['superseded_by']}" if h.get("superseded_by") else ""
            text += (
                f"\n`#{h['rule_id']}` [{status_icon}] [{h.get('domain', '')}] "
                f"{h.get('principle_text', '')[:100]}{superseded}\n"
                f"  _Created: {h.get('created_date', 'unknown')[:10]}_\n"
            )
        await send_long_message(update, text)
        return

    # ── /learn supersede <id> <new_text> ──
    if subcmd == "supersede":
        if len(args) < 3 or not args[1].isdigit():
            await update.message.reply_text(
                "Usage: `/learn supersede <id> <new principle text>`",
                parse_mode=ParseMode.MARKDOWN,
            )
            return
        old_id = int(args[1])
        new_text = " ".join(args[2:])
        result = supersede_principle(old_id, new_text, reason="Commander C2 supersede")
        if "error" in result:
            await update.message.reply_text(f"Error: {result['error']}")
        else:
            new_id = result.get("new_rule_id", "?")
            await update.message.reply_text(
                f"Principle `#{old_id}` *SUPERSEDED* by `#{new_id}`\n\n"
                f"_Old:_ {result.get('old_principle', {}).get('principle_text', '')[:100]}\n"
                f"_New:_ {new_text[:150]}\n\n"
                f"_New principle is pending — use `/learn approve {new_id}` to activate._",
                parse_mode=ParseMode.MARKDOWN,
            )
            _log_command("LEARN_SUPERSEDE", "LEARNING", f"old={old_id} new={new_id}", new_text[:80])
        return

    # Unknown subcommand
    await update.message.reply_text(
        "*Learning Compiler Commands:*\n\n"
        "`/learn` — digest + pending\n"
        "`/learn approve <id>`\n"
        "`/learn reject <id>`\n"
        "`/learn edit <id> <text>`\n"
        "`/learn history`\n"
        "`/learn supersede <id> <text>`",
        parse_mode=ParseMode.MARKDOWN,
    )


@commander_only
async def cmd_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show voice ledger summary."""
    from thunderbird_voice_ledger import get_ledger_summary
    summary = get_ledger_summary()
    await send_long_message(update, f"🎙 *Voice Ledger*\n\n{summary or 'Voice ledger empty.'}")


@commander_only
async def cmd_usage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Claude Code usage meter — token costs, current block, daily and monthly totals."""
    import subprocess, json as _json
    from datetime import date as _date

    ack = await update.message.reply_text("⚡ Pulling usage data...")

    def _bar(fraction: float, width: int = 12) -> str:
        """Return a Unicode block progress bar."""
        filled = int(round(fraction * width))
        filled = max(0, min(width, filled))
        return "█" * filled + "░" * (width - filled)

    def _fmt(n: int) -> str:
        """Format token count with K/M suffix."""
        if n >= 1_000_000:
            return f"{n/1_000_000:.1f}M"
        if n >= 1_000:
            return f"{n/1_000:.0f}K"
        return str(n)

    try:
        # --- fetch data via ccusage --json ---
        today_str = _date.today().strftime("%Y%m%d")
        month_str = _date.today().strftime("%Y%m")

        daily_raw = subprocess.run(
            ["ccusage", "daily", "--json", "--since", today_str],
            capture_output=True, text=True, timeout=20
        )
        monthly_raw = subprocess.run(
            ["ccusage", "monthly", "--json"],
            capture_output=True, text=True, timeout=20
        )
        blocks_raw = subprocess.run(
            ["ccusage", "blocks", "--json"],
            capture_output=True, text=True, timeout=20
        )

        daily_data   = _json.loads(daily_raw.stdout)   if daily_raw.returncode == 0 else {}
        monthly_data = _json.loads(monthly_raw.stdout) if monthly_raw.returncode == 0 else {}
        blocks_data  = _json.loads(blocks_raw.stdout)  if blocks_raw.returncode == 0 else {}

        # --- today ---
        today_entries = daily_data.get("daily", [])
        today_cost    = sum(e.get("totalCost", 0) for e in today_entries)
        today_tokens  = sum(e.get("totalTokens", 0) for e in today_entries)

        # --- monthly ---
        month_entries = monthly_data.get("monthly", [])
        month_entry   = next((m for m in month_entries if m.get("month", "").startswith(month_str[:7])), None)
        month_cost    = month_entry.get("totalCost", 0) if month_entry else 0
        month_tokens  = month_entry.get("totalTokens", 0) if month_entry else 0

        # Max plan = $100/month; value multiplier
        MAX_PLAN_COST = 100.0
        multiplier    = month_cost / MAX_PLAN_COST if MAX_PLAN_COST else 0

        # --- active block ---
        blocks     = blocks_data.get("blocks", [])
        active_blk = next((b for b in blocks if b.get("isActive") and not b.get("isGap")), None)

        # --- build message ---
        now_utc = datetime.now(timezone.utc).strftime("%H:%M UTC")
        lines = [
            "⚡ *CLAUDE CODE — USAGE METER*",
            f"_{_date.today().strftime('%d %b %Y')} · {now_utc}_",
            "━━━━━━━━━━━━━━━━━━━━━━",
        ]

        # Active billing block
        if active_blk:
            blk_cost     = active_blk.get("costUSD", 0)
            blk_tokens   = active_blk.get("totalTokens", 0)
            burn         = active_blk.get("burnRate", {}) or {}
            proj         = active_blk.get("projection", {}) or {}
            blk_proj_cost = proj.get("totalCost", 0)
            blk_rem_min   = proj.get("remainingMinutes", 0)
            cost_per_hr   = burn.get("costPerHour", 0)

            # Block window: 5-hour = 300 min; calc elapsed fraction
            start_t = active_blk.get("startTime", "")
            end_t   = active_blk.get("endTime", "")
            blk_frac = 0.0
            try:
                from datetime import datetime as _dt
                st  = _dt.fromisoformat(start_t.replace("Z", "+00:00"))
                et  = _dt.fromisoformat(end_t.replace("Z", "+00:00"))
                now_dt = _dt.now(timezone.utc)
                blk_frac = min(1.0, (now_dt - st).total_seconds() / (et - st).total_seconds())
            except Exception:
                pass

            blk_bar = _bar(blk_frac)
            lines += [
                "",
                "*🟢 CURRENT BLOCK (5-hr window)*",
                f"`{blk_bar}` {blk_frac*100:.0f}%",
                f"  Cost:    *${blk_cost:.2f}*  →  proj *${blk_proj_cost:.2f}*",
                f"  Tokens:  {_fmt(blk_tokens)}",
                f"  Burn:    ${cost_per_hr:.2f}/hr",
                f"  Rem:     {blk_rem_min:.0f} min",
            ]
        else:
            lines += ["", "*🔵 No active block*"]

        # Today
        lines += [
            "",
            "*📅 TODAY*",
            f"  Cost:    *${today_cost:.2f}*",
            f"  Tokens:  {_fmt(today_tokens)}",
        ]

        # Monthly
        month_bar = _bar(min(1.0, month_cost / (MAX_PLAN_COST * 12)))  # visual vs $1200/yr
        lines += [
            "",
            "*📆 MARCH 2026*",
            f"`{month_bar}` ${month_cost:.2f} API-equiv",
            f"  Max plan cost: *$100.00*",
            f"  *Value multiplier: {multiplier:.1f}x* 🔥",
            f"  Tokens: {_fmt(month_tokens)}",
        ]

        # Model breakdown (monthly)
        if month_entry:
            breakdowns = month_entry.get("modelBreakdowns", [])
            if breakdowns:
                lines.append("")
                lines.append("*Model Split:*")
                for bd in sorted(breakdowns, key=lambda x: x.get("cost", 0), reverse=True):
                    model_short = bd["modelName"].replace("claude-", "").replace("-4-5-20251001", "").replace("-4-6", "")
                    lines.append(f"  {model_short}: ${bd['cost']:.2f}")

        lines.append("\n━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("_Source: ccusage (local Claude Code logs)_")
        lines.append("_claude.ai/settings/usage blocked by Cloudflare_")

        await ack.delete()
        await send_long_message(update, "\n".join(lines))

    except Exception as e:
        await ack.edit_text(f"Usage meter failed: {e}")


@commander_only
async def cmd_restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Restart both Telegram bots via systemd."""
    ack = await update.message.reply_text("🔄 Restarting Telegram bots...")
    try:
        import subprocess
        result = subprocess.run(
            ["/home/john/restart-telegram.sh"],
            capture_output=True, text=True, timeout=30
        )
        output = result.stdout.strip() or result.stderr.strip() or "Done"
        await ack.edit_text(f"🔄 *Restart complete*\n\n```\n{output[-800:]}\n```", parse_mode="Markdown")
    except Exception as e:
        await ack.edit_text(f"⚠️ Restart failed: {e}")


@commander_only
async def cmd_poe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Switch Telegram bot to Poe gateway (burns Poe points, uses Sonnet)."""
    ack = await update.message.reply_text("🔀 Switching to POE mode...")
    try:
        import subprocess, re as _re
        env_path = "/home/john/Thunderbird/config/poe.env"
        with open(env_path) as f:
            content = f.read()
        content = _re.sub(r"POE_MODE=\d", "POE_MODE=1", content)
        with open(env_path, "w") as f:
            f.write(content)
        # Restart this service so it picks up the new env
        subprocess.run(["systemctl", "--user", "restart", "d2m-telegram.service"],
                       timeout=15, check=False)
        await ack.edit_text(
            "🔀 *POE MODE ACTIVE*\n\n"
            "• Backend: Poe gateway (Sonnet)\n"
            "• Cost: Burns Poe points\n"
            "• Scope: *Telegram bot only*\n"
            "• CLI + Desktop unaffected\n\n"
            "Use `/max` to return to Max plan ($0).",
            parse_mode="Markdown"
        )
    except Exception as e:
        await ack.edit_text(f"⚠️ POE switch failed: {e}")


@commander_only
async def cmd_max(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Switch Telegram bot back to Max plan OAuth ($0, Opus)."""
    ack = await update.message.reply_text("🔀 Switching to MAX mode...")
    try:
        import subprocess, re as _re
        env_path = "/home/john/Thunderbird/config/poe.env"
        with open(env_path) as f:
            content = f.read()
        content = _re.sub(r"POE_MODE=\d", "POE_MODE=0", content)
        with open(env_path, "w") as f:
            f.write(content)
        subprocess.run(["systemctl", "--user", "restart", "d2m-telegram.service"],
                       timeout=15, check=False)
        await ack.edit_text(
            "✅ *MAX MODE ACTIVE*\n\n"
            "• Backend: Max plan OAuth (Opus)\n"
            "• Cost: $0 (subscription)\n"
            "• Scope: *Telegram bot only*\n"
            "• CLI + Desktop unaffected\n\n"
            "Use `/poe` to switch to Poe gateway.",
            parse_mode="Markdown"
        )
    except Exception as e:
        await ack.edit_text(f"⚠️ MAX switch failed: {e}")


@commander_only
async def cmd_intel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Run the morning intel pipeline (A2→A1→COS) on demand and push to C2."""
    ack = await update.message.reply_text("🔵 Running intel pipeline (A2→A1→COS)…")
    loop = asyncio.get_event_loop()
    try:
        import subprocess
        result = await loop.run_in_executor(None, lambda: subprocess.run(
            ["/home/john/Thunderbird/.venv/bin/python3",
             "/home/john/Thunderbird/thunderbird_intel_telegram.py"],
            capture_output=True, text=True, timeout=540,
            env={**os.environ, "PYTHONPATH": "/home/john/Thunderbird"}
        ))
        out = (result.stdout + result.stderr).strip()[-300:]
        await ack.edit_text(f"🔵 *Intel pipeline complete*\n\n`{out}`", parse_mode="Markdown")
    except Exception as e:
        await ack.edit_text(f"⚠️ Intel pipeline error: {e}")


@commander_only
async def cmd_brief(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fire the FPD/departure morning brief on demand."""
    ack = await update.message.reply_text("🌅 Running morning brief…")
    loop = asyncio.get_event_loop()
    try:
        import subprocess
        result = await loop.run_in_executor(None, lambda: subprocess.run(
            ["/usr/bin/python3",
             "/home/john/Thunderbird/thunderbird_brief_telegram.py"],
            capture_output=True, text=True, timeout=60,
            env={**os.environ, "PYTHONPATH": "/home/john/Thunderbird"}
        ))
        await ack.edit_text("✅ Morning brief sent." if result.returncode == 0
                             else f"⚠️ Brief error:\n`{result.stderr[-200:]}`",
                             parse_mode="Markdown")
    except Exception as e:
        await ack.edit_text(f"⚠️ Brief error: {e}")


@commander_only
async def cmd_fpd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Run FPD alert check on demand."""
    ack = await update.message.reply_text("📋 Checking FPDs…")
    loop = asyncio.get_event_loop()
    try:
        import subprocess
        result = await loop.run_in_executor(None, lambda: subprocess.run(
            ["/usr/bin/python3",
             "/home/john/Thunderbird/thunderbird_fpd_alert.py"],
            capture_output=True, text=True, timeout=30,
            env={**os.environ, "PYTHONPATH": "/home/john/Thunderbird"}
        ))
        await ack.edit_text("✅ FPD alert sent." if result.returncode == 0
                             else f"⚠️ FPD error:\n`{result.stderr[-200:]}`",
                             parse_mode="Markdown")
    except Exception as e:
        await ack.edit_text(f"⚠️ FPD error: {e}")


@commander_only
async def cmd_dossier(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Quick dossier lookup — /dossier <client name or keyword>"""
    from pathlib import Path
    import re
    args = context.args
    if not args:
        await update.message.reply_text("Usage: `/dossier <name>`\nExample: `/dossier Morton`",
                                         parse_mode="Markdown")
        return
    query = " ".join(args).lower()
    dossier_dir = Path("/home/john/Thunderbird/dossiers")
    matches = []
    for f in sorted(dossier_dir.glob("*.md")):
        if f.name == "CLAUDE.md":
            continue
        if query in f.stem.lower():
            matches.append(f)
        elif query in f.read_text(errors="ignore")[:500].lower():
            matches.append(f)

    if not matches:
        await update.message.reply_text(f"No dossier found matching `{query}`.",
                                         parse_mode="Markdown")
        return

    # Return first 3 matches summary (first 600 chars each)
    lines = [f"*📂 Dossier — {query.title()}*\n"]
    for f in matches[:3]:
        text = f.read_text(errors="ignore")
        # Strip frontmatter
        body = re.sub(r"^---.*?---\s*", "", text, flags=re.DOTALL).strip()
        preview = body[:500].strip()
        lines.append(f"*{f.stem}*\n{preview}\n")

    await send_long_message(update, "\n".join(lines))


@commander_only
async def cmd_ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Search intel archives for a D2M-applicable insight. /ask <query>"""
    query = " ".join(context.args) if context.args else ""
    if not query:
        await update.message.reply_text(
            "Usage: `/ask <query>`\nExample: `/ask real estate post-sale lifecycle`",
            parse_mode="Markdown",
        )
        return

    ack = await update.message.reply_text(
        f"🔍 Searching archives for: `{query}`…", parse_mode="Markdown"
    )
    try:
        from pathlib import Path as _Path
        intel_dir = _Path("/home/john/Thunderbird/intel")
        query_lower = query.lower()
        query_terms = [t for t in query_lower.split() if len(t) > 2]
        results = []

        for f in sorted(intel_dir.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True):
            try:
                content = f.read_text(encoding="utf-8", errors="replace")
                content_lower = content.lower()
                score = sum(content_lower.count(t) for t in query_terms)
                if score == 0:
                    continue
                lines = content.split("\n")
                best = []
                for i, line in enumerate(lines):
                    if any(t in line.lower() for t in query_terms):
                        start = max(0, i - 1)
                        end = min(len(lines), i + 3)
                        best.extend(lines[start:end])
                        if len(best) >= 8:
                            break
                if best:
                    results.append((score, f.name, "\n".join(best[:8])))
            except Exception:
                pass

        if not results:
            await ack.edit_text(
                f"🔍 Nothing in archives for: `{query}`\nTry `/ask` with different terms.",
                parse_mode="Markdown",
            )
            return

        results.sort(key=lambda x: x[0], reverse=True)
        out = [f"🗂 *Archive: {query}* — {len(results)} file(s)\n"]
        for _, fname, excerpt in results[:2]:
            out.append(f"📄 `{fname}`")
            safe = excerpt[:400].replace("*", "").replace("`", "").replace("_", " ")
            out.append(safe)
            out.append("")
        if len(results) > 2:
            out.append(f"_{len(results) - 2} more files. Refine query to narrow._")

        await ack.edit_text("\n".join(out), parse_mode="Markdown")
    except Exception as e:
        await ack.edit_text(f"⚠️ Search error: {e}")


@commander_only
async def cmd_inbox(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sweep Commander's personal inbox for D2M emails."""
    ack = await update.message.reply_text("📬 Sweeping inbox...")
    loop = asyncio.get_event_loop()
    try:
        from thunderbird_commander_inbox import run_commander_inbox_sweep
        result = await loop.run_in_executor(None, run_commander_inbox_sweep)
        await ack.delete()
        summary = result.get('summary', str(result)[:500]) if isinstance(result, dict) else str(result)[:500]
        await send_long_message(update, f"📬 *Inbox Sweep*\n\n{summary}")
    except Exception as e:
        await ack.edit_text(f"Sweep failed: {e}")


@commander_only
async def handle_plain_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Plain text from Commander → COS via Opus Agent SDK with live progress."""
    query = update.message.text
    if not query or not query.strip():
        return

    # Keyword trigger: "STAFF SUMMARY" → launch SSS flow
    if "STAFF SUMMARY" in query.upper():
        return await cmd_sss(update, context)

    # SSS text input intercept (issue / action officer entry)
    if await _handle_sss_text_input(update, context):
        return

    user_id = update.effective_user.id

    # Draft comment intercept — Commander typed a comment after pressing 💬
    if user_id in _draft_comment_pending:
        draft_id = _draft_comment_pending.pop(user_id)
        comment_text = query.strip()
        try:
            from thunderbird_gmail import gmail_get_draft_sync
            loop = asyncio.get_event_loop()
            draft_meta = await loop.run_in_executor(None, lambda: gmail_get_draft_sync(draft_id))
            subject = draft_meta.get("subject", "(unknown subject)")
            to_addr  = draft_meta.get("to", "?")
        except Exception:
            subject = "(unknown subject)"
            to_addr  = "?"
        keep_note = (
            f"📝 Draft Comment — {subject}\n"
            f"To: {to_addr}\n"
            f"Draft ID: {draft_id}\n\n"
            f"{comment_text}"
        )
        try:
            from thunderbird_keep import create_note as keep_create_note
            loop_k = asyncio.get_event_loop()
            await loop_k.run_in_executor(
                None,
                lambda: keep_create_note(
                    title=f"Draft Comment: {subject[:60]}",
                    body=keep_note,
                    color="YELLOW",
                )
            )
            await update.message.reply_text(
                f"💬 *Comment saved to Keep.*\n"
                f"_{subject[:80]}_",
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception as e:
            await update.message.reply_text(
                f"💬 Comment noted (Keep save failed: {e}):\n_{comment_text[:300]}_",
                parse_mode=ParseMode.MARKDOWN,
            )
        _log_command("DRAFT_COMMENT", "KEEP", f"draft_id={draft_id}", comment_text[:80])
        return
    ack_msg = await update.message.reply_text("⚙️ Working...")
    _add_to_history(user_id, "user", query)

    logger.info(f"C2 Commander msg -> COS (Opus): {query}")

    history = _get_history(user_id)
    conv_hist = [{"role": h["role"], "text": h["text"]} for h in history[:-1]]

    is_draft = _is_draft_request(query)
    stop_event = asyncio.Event()
    on_progress, hb_task, typing_task = await _make_progress_updater(ack_msg, stop_event, update)

    try:
        result = await call_cos_via_sdk(
            message=query,
            persona="COS",
            intent_type="TASK",
            conversation_history=conv_hist or None,
            on_progress=on_progress,
            draft_mode=is_draft,
        )
        answer = result.get("response", "COS reporting: No response generated.")
    except Exception as e:
        logger.error(f"C2 Opus call failed: {e}")
        answer = f"C2 error: {e}"
    finally:
        stop_event.set()
        hb_task.cancel()
        typing_task.cancel()

    try:
        await ack_msg.delete()
    except Exception:
        pass

    _add_to_history(user_id, "assistant", answer)
    _log_command("TASK", "COS", query, answer)

    header = format_persona_header("COS")
    await send_long_message(update, f"{header}\n\n{answer}")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    from telegram.error import Conflict
    import os, signal
    if isinstance(context.error, Conflict):
        logger.critical("409 Conflict — duplicate C2 instance detected. Exiting for clean systemd restart.")
        os.kill(os.getpid(), signal.SIGTERM)
        return
    logger.error(f"C2 bot error: {context.error}", exc_info=context.error)


# ---------------------------------------------------------------------------
# Staff Summary Sheet — /sss + "STAFF SUMMARY" keyword + checkbox UI
# ---------------------------------------------------------------------------

# Persona list for SSS coordination checkboxes
SSS_PERSONAS = [
    ("COS", "Col Victoria Hale", "Chief of Staff"),
    ("EXEC", "Naia Solberg-Vega", "Voice & Visual"),
    ("A2", "Lt Col Marcus Dembe", "Research & Intel"),
    ("A3", "Danielle Moreau", "Client Concierge"),
    ("A5", "Lt Col Ryan Castillo", "Strategy & Growth"),
    ("A6", "Luna Voss", "Creative Director"),
    ("A9", "Victor Harlan", "Finance"),
    ("CH", "Col James Washington", "Ethics & Morale"),
    ("A12", "ELON", "Innovation"),
]

SSS_SCOPES = {
    "ioc": "IOC (all domains)",
    "client": "Client-specific",
    "hybrid": "Hybrid (client + IOC)",
}

SSS_CATEGORIES = ["payment", "flights", "excursions", "insurance", "pricing", "comms", "logistics", "hotel"]

# In-memory state for SSS creation flow per user
_sss_drafts: dict[int, dict] = {}
_draft_comment_pending: dict[int, str] = {}  # user_id → draft_id awaiting comment text


def _build_persona_keyboard(selected: set[str]) -> InlineKeyboardMarkup:
    """Build inline keyboard with checkboxes for persona selection."""
    rows = []
    for pid, name, role in SSS_PERSONAS:
        check = "☑" if pid in selected else "☐"
        label = f"{check} {pid} — {name}"
        rows.append([InlineKeyboardButton(label, callback_data=f"sss_toggle_{pid}")])

    # Control buttons
    rows.append([
        InlineKeyboardButton("✅ Select All", callback_data="sss_select_all"),
        InlineKeyboardButton("❌ Clear All", callback_data="sss_clear_all"),
    ])
    rows.append([
        InlineKeyboardButton("⚡ Auto (by category)", callback_data="sss_auto"),
    ])
    rows.append([
        InlineKeyboardButton("🚀 LAUNCH COORDINATION", callback_data="sss_launch"),
        InlineKeyboardButton("🔴 Cancel", callback_data="sss_cancel"),
    ])
    return InlineKeyboardMarkup(rows)


def _build_scope_keyboard() -> InlineKeyboardMarkup:
    """Build scope selection keyboard."""
    rows = [
        [InlineKeyboardButton(f"{'●' if k == 'client' else '○'} {v}", callback_data=f"sss_scope_{k}")]
        for k, v in SSS_SCOPES.items()
    ]
    return InlineKeyboardMarkup(rows)


def _build_category_keyboard() -> InlineKeyboardMarkup:
    """Build category selection keyboard."""
    rows = []
    for i in range(0, len(SSS_CATEGORIES), 2):
        row = []
        for cat in SSS_CATEGORIES[i:i+2]:
            row.append(InlineKeyboardButton(cat.title(), callback_data=f"sss_cat_{cat}"))
        rows.append(row)
    return InlineKeyboardMarkup(rows)


@commander_only
async def cmd_sss(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start a Staff Summary Sheet creation flow.

    Usage: /sss <issue description>
    Or just: /sss (interactive mode)
    """
    user_id = update.effective_user.id
    issue_text = " ".join(context.args) if context.args else ""

    # Initialize draft state
    _sss_drafts[user_id] = {
        "step": "scope" if issue_text else "issue",
        "issue": issue_text,
        "scope": "client",
        "category": None,
        "action_officer": None,
        "selected_personas": set(),
        "message_id": None,
    }

    if not issue_text:
        await update.message.reply_text(
            "📋 *STAFF SUMMARY SHEET — NEW*\n\n"
            "Type the ISSUE (one sentence — what this is about):",
            parse_mode=ParseMode.MARKDOWN,
        )
        _sss_drafts[user_id]["step"] = "awaiting_issue"
        return

    # Skip to scope selection
    msg = await update.message.reply_text(
        f"📋 *STAFF SUMMARY SHEET*\n\n"
        f"*ISSUE:* {issue_text}\n\n"
        f"Select SCOPE:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_build_scope_keyboard(),
    )
    _sss_drafts[user_id]["message_id"] = msg.message_id
    _sss_drafts[user_id]["step"] = "scope"


async def _handle_sss_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Handle text input during SSS creation flow. Returns True if consumed."""
    user_id = update.effective_user.id
    draft = _sss_drafts.get(user_id)
    if not draft:
        return False

    text = update.message.text.strip()
    step = draft.get("step")

    if step == "awaiting_issue":
        draft["issue"] = text
        draft["step"] = "scope"
        msg = await update.message.reply_text(
            f"📋 *STAFF SUMMARY SHEET*\n\n"
            f"*ISSUE:* {text}\n\n"
            f"Select SCOPE:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_build_scope_keyboard(),
        )
        draft["message_id"] = msg.message_id
        return True

    elif step == "awaiting_ao":
        # Action officer — accept persona ID or name
        ao = text.upper().strip()
        if ao in [p[0] for p in SSS_PERSONAS]:
            draft["action_officer"] = ao
        else:
            # Try matching by name
            for pid, name, _ in SSS_PERSONAS:
                if text.lower() in name.lower():
                    ao = pid
                    draft["action_officer"] = ao
                    break
            else:
                draft["action_officer"] = "COS"  # default

        # Remove AO from selected if present
        draft["selected_personas"].discard(draft["action_officer"])

        draft["step"] = "coordinators"
        msg = await update.message.reply_text(
            f"📋 *SSS — Select Coordinators*\n\n"
            f"*ISSUE:* {draft['issue']}\n"
            f"*SCOPE:* {draft['scope']} | *AO:* {draft['action_officer']}\n\n"
            f"Toggle personas to coordinate with:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_build_persona_keyboard(draft["selected_personas"]),
        )
        draft["message_id"] = msg.message_id
        return True

    return False


async def handle_sss_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all sss_ callback queries from inline keyboards."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if not _is_commander(user_id):
        return

    draft = _sss_drafts.get(user_id)
    if not draft:
        await query.edit_message_text("SSS session expired. Use /sss to start over.")
        return

    data = query.data

    # --- Scope selection ---
    if data.startswith("sss_scope_"):
        scope = data.replace("sss_scope_", "")
        draft["scope"] = scope

        if scope in ("client", "hybrid"):
            # Need category
            draft["step"] = "category"
            await query.edit_message_text(
                f"📋 *SSS — Select Category*\n\n"
                f"*ISSUE:* {draft['issue']}\n"
                f"*SCOPE:* {scope}\n\n"
                f"What domain does this concern?",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=_build_category_keyboard(),
            )
        else:
            # IOC scope — all personas auto-selected
            draft["selected_personas"] = {p[0] for p in SSS_PERSONAS}
            draft["step"] = "awaiting_ao"
            await query.edit_message_text(
                f"📋 *SSS — Action Officer*\n\n"
                f"*ISSUE:* {draft['issue']}\n"
                f"*SCOPE:* IOC (all domains)\n\n"
                f"Who is the Action Officer? Type persona ID (e.g., A9) or name:",
                parse_mode=ParseMode.MARKDOWN,
            )

    # --- Category selection ---
    elif data.startswith("sss_cat_"):
        cat = data.replace("sss_cat_", "")
        draft["category"] = cat

        # Auto-select coordinators for this category
        from thunderbird_sss import CLIENT_COORDINATION, IOC_COORDINATORS
        auto = set(CLIENT_COORDINATION.get(cat, ["A3", "COS"]))
        if draft["scope"] == "hybrid":
            auto.update(IOC_COORDINATORS)
        draft["selected_personas"] = auto

        draft["step"] = "awaiting_ao"
        await query.edit_message_text(
            f"📋 *SSS — Action Officer*\n\n"
            f"*ISSUE:* {draft['issue']}\n"
            f"*SCOPE:* {draft['scope']} | *Category:* {cat}\n"
            f"*Auto-selected:* {', '.join(sorted(auto))}\n\n"
            f"Who is the Action Officer? Type persona ID (e.g., A9):",
            parse_mode=ParseMode.MARKDOWN,
        )

    # --- Toggle persona ---
    elif data.startswith("sss_toggle_"):
        pid = data.replace("sss_toggle_", "")
        if pid in draft["selected_personas"]:
            draft["selected_personas"].discard(pid)
        else:
            draft["selected_personas"].add(pid)

        # Refresh keyboard
        await query.edit_message_reply_markup(
            reply_markup=_build_persona_keyboard(draft["selected_personas"]),
        )

    # --- Select all ---
    elif data == "sss_select_all":
        draft["selected_personas"] = {p[0] for p in SSS_PERSONAS}
        await query.edit_message_reply_markup(
            reply_markup=_build_persona_keyboard(draft["selected_personas"]),
        )

    # --- Clear all ---
    elif data == "sss_clear_all":
        draft["selected_personas"] = set()
        await query.edit_message_reply_markup(
            reply_markup=_build_persona_keyboard(draft["selected_personas"]),
        )

    # --- Auto by category ---
    elif data == "sss_auto":
        from thunderbird_sss import CLIENT_COORDINATION, IOC_COORDINATORS
        cat = draft.get("category", "")
        if draft["scope"] == "ioc":
            draft["selected_personas"] = set(IOC_COORDINATORS)
        elif cat:
            auto = set(CLIENT_COORDINATION.get(cat, ["A3", "COS"]))
            if draft["scope"] == "hybrid":
                auto.update(IOC_COORDINATORS)
            draft["selected_personas"] = auto
        else:
            draft["selected_personas"] = {"A3", "COS"}

        await query.edit_message_reply_markup(
            reply_markup=_build_persona_keyboard(draft["selected_personas"]),
        )

    # --- Cancel ---
    elif data == "sss_cancel":
        _sss_drafts.pop(user_id, None)
        await query.edit_message_text("SSS cancelled.")

    # --- LAUNCH ---
    elif data == "sss_launch":
        await _launch_sss(query, user_id, draft)


async def _launch_sss(query, user_id: int, draft: dict):
    """Create and coordinate the SSS, then present results."""
    from thunderbird_sss import create_sss, coordinate_sss, present_to_commander

    issue = draft["issue"]
    scope = draft["scope"]
    category = draft.get("category")
    ao = draft.get("action_officer", "COS")
    selected = draft["selected_personas"]

    # Remove AO from coordinators
    selected.discard(ao)

    if not selected:
        await query.edit_message_text("No coordinators selected. Use /sss to start over.")
        _sss_drafts.pop(user_id, None)
        return

    await query.edit_message_text(
        f"🚀 *SSS LAUNCHING*\n\n"
        f"*AO:* {ao} | *Coordinators:* {', '.join(sorted(selected))}\n"
        f"Collecting CONCUR / NON-CONCUR from {len(selected)} domains...\n\n"
        f"_This may take 1-2 minutes._",
        parse_mode=ParseMode.MARKDOWN,
    )

    loop = asyncio.get_event_loop()

    try:
        def _do_sss():
            sss = create_sss(
                action_officer=ao,
                purpose=issue,
                background=f"Commander-initiated via Telegram C2 on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC.",
                discussion="See issue statement. Staff to analyze from their domain perspective.",
                recommendation=f"Pending coordination. {ao} to synthesize after all positions received.",
                scope=scope,
                category=category,
            )
            # Override auto-selected coordinators with Commander's manual selection
            from thunderbird_sss import CoordinationBlock
            sss.coordination = [
                CoordinationBlock(persona_id=pid) for pid in sorted(selected)
            ]
            from thunderbird_sss import _SSS_STORE
            _SSS_STORE[sss.sss_id] = sss

            # Run coordination
            coordinate_sss(sss.sss_id)
            return present_to_commander(sss.sss_id), sss.sss_id

        result_text, sss_id = await loop.run_in_executor(None, _do_sss)

        # Build decision buttons
        decision_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"sss_decide_{sss_id}_approve"),
                InlineKeyboardButton("✏️ Modify", callback_data=f"sss_decide_{sss_id}_modify"),
                InlineKeyboardButton("❌ Reject", callback_data=f"sss_decide_{sss_id}_reject"),
            ]
        ])

        # Send the full SSS (may be long)
        if len(result_text) <= MAX_MESSAGE_LENGTH - 200:
            await query.edit_message_text(
                result_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=decision_keyboard,
            )
        else:
            await query.edit_message_text("📋 SSS coordination complete. Full package below:")
            # Split and send
            chunks = [result_text[i:i+MAX_MESSAGE_LENGTH] for i in range(0, len(result_text), MAX_MESSAGE_LENGTH)]
            for chunk in chunks[:-1]:
                try:
                    await query.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN_V2)
                except Exception:
                    await query.message.reply_text(chunk.replace("*", "").replace("_", ""))
            # Last chunk gets the decision buttons
            try:
                await query.message.reply_text(
                    chunks[-1], parse_mode=ParseMode.MARKDOWN,
                    reply_markup=decision_keyboard,
                )
            except Exception:
                await query.message.reply_text(
                    chunks[-1].replace("*", "").replace("_", ""),
                    reply_markup=decision_keyboard,
                )

    except Exception as e:
        logger.error(f"SSS coordination failed: {e}")
        await query.edit_message_text(f"SSS coordination failed: {e}")
    finally:
        _sss_drafts.pop(user_id, None)


async def handle_sss_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Commander's decision on an SSS (approve/modify/reject)."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if not _is_commander(user_id):
        return

    data = query.data  # sss_decide_{sss_id}_{action}
    parts = data.split("_")
    if len(parts) < 4:
        return

    sss_id = f"SSS-{parts[2]}"
    action = parts[3]

    from thunderbird_sss import record_decision

    if action == "approve":
        record_decision(sss_id, "APPROVED by Commander via Telegram C2")
        await query.edit_message_text(
            f"✅ *SSS {sss_id} — APPROVED*\n\nDecision recorded. All domains aligned.",
            parse_mode=ParseMode.MARKDOWN,
        )
    elif action == "reject":
        record_decision(sss_id, "REJECTED by Commander via Telegram C2")
        await query.edit_message_text(
            f"❌ *SSS {sss_id} — REJECTED*\n\nDecision recorded.",
            parse_mode=ParseMode.MARKDOWN,
        )
    elif action == "modify":
        await query.edit_message_text(
            f"✏️ *SSS {sss_id} — Awaiting modification*\n\n"
            f"Type your modification or new direction:",
            parse_mode=ParseMode.MARKDOWN,
        )
        _sss_drafts[user_id] = {"step": "awaiting_decision_text", "sss_id": sss_id}

    _log_command("SSS_DECISION", "Commander", f"SSS {sss_id}", action)


# ---------------------------------------------------------------------------
# Draft Approval Flow — /drafts, approve, edit, reject via inline buttons
# ---------------------------------------------------------------------------

@commander_only
async def cmd_drafts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List pending Gmail drafts with approve/reject buttons."""
    loop = asyncio.get_event_loop()
    try:
        from thunderbird_gmail import gmail_list_drafts_sync
        drafts = await _run_with_typing(update, lambda: gmail_list_drafts_sync(10), loop)
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
        message_id = d.get("message_id", "")
        to = d.get("To", "?")
        subject = d.get("Subject", "(no subject)")
        snippet = d.get("snippet", "")[:150]

        # Gmail deep link for viewing/editing in browser
        gmail_link = ""
        if message_id:
            gmail_link = f"\n[Open in Gmail](https://mail.google.com/mail/?authuser=d2mconcierge@gmail.com#drafts/{message_id})"

        text = (
            f"📧 *Draft*\n"
            f"*To:* {to}\n"
            f"*Subject:* {subject}\n"
            f"_{snippet}_"
            f"{gmail_link}"
        )

        keyboard = [
            [
                InlineKeyboardButton("✅ Approve & Send", callback_data=f"draft_approve:{draft_id}"),
                InlineKeyboardButton("👁 Preview", callback_data=f"draft_preview:{draft_id}"),
            ],
            [
                InlineKeyboardButton("❌ Reject & Delete", callback_data=f"draft_reject:{draft_id}"),
                InlineKeyboardButton("💬 Comment", callback_data=f"draft_comment:{draft_id}"),
            ],
        ]
        # Add "Edit in Gmail" button if we have a message_id for the deep link
        if message_id:
            keyboard.append([
                InlineKeyboardButton("📝 Edit in Gmail", url=f"https://mail.google.com/mail/?authuser=d2mconcierge@gmail.com#drafts/{message_id}"),
            ])

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
            body_text = draft.get('body_full') or draft.get('body_preview', '(empty)')
            message_id = draft.get('message_id', '')

            # Gmail deep link for viewing/editing in browser
            gmail_link = ""
            if message_id:
                gmail_link = f"\n[Open in Gmail](https://mail.google.com/mail/?authuser=d2mconcierge@gmail.com#drafts/{message_id})\n"

            header = (
                f"📧 *Full Draft Preview*\n"
                f"{'━' * 28}\n"
                f"*From:* {draft.get('from', '?')}\n"
                f"*To:* {draft.get('to', '?')}\n"
                f"*Subject:* {draft.get('subject', '?')}\n"
                f"{gmail_link}\n"
            )

            keyboard = [
                [
                    InlineKeyboardButton("✅ Approve & Send", callback_data=f"draft_approve:{draft_id}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"draft_reject:{draft_id}"),
                ],
                [
                    InlineKeyboardButton("💬 Comment", callback_data=f"draft_comment:{draft_id}"),
                ],
            ]
            # Add "Edit in Gmail" button if we have a message_id for the deep link
            if message_id:
                keyboard.append([
                    InlineKeyboardButton("📝 Edit in Gmail", url=f"https://mail.google.com/mail/?authuser=d2mconcierge@gmail.com#drafts/{message_id}"),
                ])

            # Split long drafts across multiple messages, attach buttons to the last one
            full_text = header + body_text
            if len(full_text) <= MAX_MESSAGE_LENGTH:
                chunks = [full_text]
            else:
                # Send body in chunks; header goes with first chunk
                chunks = []
                remaining = full_text
                while remaining:
                    if len(remaining) <= MAX_MESSAGE_LENGTH:
                        chunks.append(remaining)
                        break
                    # Split at last newline within limit
                    split_at = remaining.rfind('\n', 0, MAX_MESSAGE_LENGTH)
                    if split_at <= 0:
                        split_at = MAX_MESSAGE_LENGTH
                    chunks.append(remaining[:split_at])
                    remaining = remaining[split_at:].lstrip('\n')

            for i, chunk in enumerate(chunks):
                is_last = (i == len(chunks) - 1)
                markup = InlineKeyboardMarkup(keyboard) if is_last else None
                try:
                    await query.message.reply_text(
                        chunk,
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=markup,
                    )
                except Exception:
                    await query.message.reply_text(
                        chunk.replace("*", "").replace("_", ""),
                        reply_markup=markup,
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

    elif action == "draft_comment":
        _draft_comment_pending[user_id] = draft_id
        await query.message.reply_text(
            f"💬 *Add your comment for this draft:*\n"
            f"Draft: `{draft_id}`\n\n"
            f"Type your note — I'll save it to Google Keep.",
            parse_mode=ParseMode.MARKDOWN,
        )


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

    # IOC module commands
    app.add_handler(CommandHandler("scan", cmd_scan))
    app.add_handler(CommandHandler("learn", cmd_learn))
    app.add_handler(CommandHandler("voice", cmd_voice))
    app.add_handler(CommandHandler("inbox", cmd_inbox))
    app.add_handler(CommandHandler("usage", cmd_usage))
    app.add_handler(CommandHandler("restart", cmd_restart))
    app.add_handler(CommandHandler("poe", cmd_poe))
    app.add_handler(CommandHandler("max", cmd_max))
    app.add_handler(CommandHandler("intel", cmd_intel))
    app.add_handler(CommandHandler("brief", cmd_brief))
    app.add_handler(CommandHandler("fpd", cmd_fpd))
    app.add_handler(CommandHandler("dossier", cmd_dossier))
    app.add_handler(CommandHandler("ask", cmd_ask))

    # Draft approval inline buttons (approve/preview/reject)
    app.add_handler(CallbackQueryHandler(handle_draft_callback, pattern=r"^draft_"))

    # Staff Summary Sheet handlers
    app.add_handler(CommandHandler("sss", cmd_sss))
    app.add_handler(CallbackQueryHandler(handle_sss_callback, pattern=r"^sss_(?!decide)"))
    app.add_handler(CallbackQueryHandler(handle_sss_decision, pattern=r"^sss_decide_"))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_plain_text))
    app.add_error_handler(error_handler)

    logger.info("D2MC2C online. Polling...")
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
        bootstrap_retries=5,
    )


if __name__ == "__main__":
    main()
