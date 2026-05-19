"""
OpsCenter Task Processor — Hale-Loop Consumer
==============================================
Pops tasks from the JSON queue, classifies them, routes to the
correct engine, and sends results back via Telegram.

⚠️ COST FIX 2026-04-24: DeepSeek V3.1 is NOT free ($0.27/M). Replaced with FREE OpenRouter.

Division of Labor:
    FREE OpenRouter tiers → Hale's primary brain. Operational tasks, summaries, research. $0/month (SO 2026-04-24)
    Gemini Flash Lite ($) → Simple analysis, lightweight inference when free tier unavailable
    Claude MAX ($0)   → Client-facing emails, proposals, voice-matched copy, complex reasoning
    Local Python      → Queue mechanics, deadline checks, format checks (no LLM)

Claude MAX tokens are SCARCE (5-hour window). Never burn them on:
    - Polling/heartbeats
    - Classification/routing decisions
    - Summarization of known data
    - Queue processing overhead

Author: Victoria "Victory" Hale, SES-6 (VCSAF)
"""

import json
import logging
import os
import sys
import time
from typing import Optional
import requests
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add parent dir so we can import thunderbird modules
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

# Load env BEFORE importing model router (it reads keys at import time)
from dotenv import load_dotenv
load_dotenv(str(_ROOT / ".env"))
load_dotenv(str(_ROOT / ".env.telegram"))

from thunderbird_model_router import (
    _call_groq,
    _call_gemini,
    _call_claude,
    _call_openrouter,
    classify_task,
    TaskType,
    DEEPSEEK_PRIMARY_MODEL,
    QWEN_PLUS_FREE_MODEL,  # Legacy alias → DEEPSEEK_PRIMARY_MODEL
    OPENROUTER_API_KEY,
)
from thunderbird_innovation_scanner import run_daily_scan, run_weekly_scan
from thunderbird_morning_briefing import run_briefing as run_morning_briefing_pipeline
from thunderbird_overwatch import run_sentinel_sweep, _check_dossier_currency, _check_commission_math, CheckStatus, CheckResult
from thunderbird_telegram_fmt import split_message, md_to_telegram, strip_markdown


import re

logger = logging.getLogger("opscenter.processor")

# ── MCP Bridge — gives Hale access to all 140+ MCP tools ──
MCP_URL = "http://127.0.0.1:8765/mcp"


def _call_mcp_tool(tool_name: str, arguments: dict, timeout: int = 30) -> str:
    """Call any MCP tool via the Thunderbird MCP HTTP server (JSON-RPC).

    Returns the text result or an error string. Never raises.
    """
    try:
        resp = requests.post(
            MCP_URL,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments},
            },
            headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        if "error" in data:
            return f"[MCP ERROR] {data['error'].get('message', 'Unknown')}"

        result = data.get("result", {})
        content_list = result.get("content", [])
        text_parts = [c.get("text", "") for c in content_list if c.get("type") == "text"]
        output = "\n".join(text_parts)

        if not output:
            sc = result.get("structuredContent", {})
            if sc:
                output = json.dumps(sc, indent=2)

        return output or "[MCP] Tool returned empty result."
    except requests.exceptions.ConnectionError:
        return "[MCP OFFLINE] MCP server not reachable at localhost:8765."
    except requests.exceptions.Timeout:
        return f"[MCP TIMEOUT] {tool_name} timed out after {timeout}s."
    except Exception as e:
        return f"[MCP ERROR] {tool_name} failed: {e}"


def _fetch_mcp_context(content: str) -> str:
    """Pre-fetch real data from MCP tools based on the Commander's message.

    Runs BEFORE Gemini, so Hale answers with facts instead of hallucinations.
    Returns a context block to inject into the Gemini prompt.
    Cost: $0 (local HTTP calls to MCP server).
    """
    content_lower = content.lower()
    context_parts = []

    # --- Client / Booking queries ---
    client_keywords = [
        "furlow", "westbrook", "lyons", "mcleod", "britan",
        "loucks", "ely", "darrow", "booking", "payment", "dossier",
        "client", "reservation", "fpd", "final payment",
    ]
    if any(kw in content_lower for kw in client_keywords):
        dossier_data = _call_mcp_tool("scan_dossiers", {}, timeout=15)
        if not dossier_data.startswith("[MCP"):
            context_parts.append(f"## LIVE DOSSIER DATA\n{dossier_data[:3000]}")

        # TESS client lookup (no search param — just returns all, we filter)
        for name in ["furlow", "westbrook", "lyons", "mcleod", "britan", "ely", "darrow"]:
            if name in content_lower:
                tess_data = _call_mcp_tool("tess_list_clients", {"limit": 50}, timeout=15)
                if not tess_data.startswith("[MCP"):
                    context_parts.append(f"## TESS CLIENTS (looking for: {name.title()})\n{tess_data[:2000]}")
                break

    # --- Email queries ---
    email_keywords = ["email", "draft", "inbox", "gmail", "sent", "reply", "message"]
    if any(kw in content_lower for kw in email_keywords):
        search_q = "newer_than:2d"
        for name in ["furlow", "westbrook", "lyons", "mcleod", "britan", "silversea", "regent", "ponant"]:
            if name in content_lower:
                search_q = f"{name} newer_than:7d"
                break
        # Schema: query* (not q), max_results
        email_data = _call_mcp_tool("gmail_search_messages", {"query": search_q, "max_results": 5}, timeout=15)
        if not email_data.startswith("[MCP"):
            context_parts.append(f"## RECENT EMAILS (query: {search_q})\n{email_data[:2000]}")

    # --- Status / Health queries ---
    status_keywords = ["status", "health", "system", "running", "alive", "check", "ops"]
    if any(kw in content_lower for kw in status_keywords):
        health_data = _call_mcp_tool("system_health_check", {}, timeout=15)
        if not health_data.startswith("[MCP"):
            context_parts.append(f"## SYSTEM HEALTH\n{health_data[:2000]}")

    # --- Task / Queue queries ---
    task_keywords = ["task", "queue", "todo", "pending", "backlog"]
    if any(kw in content_lower for kw in task_keywords):
        task_data = _call_mcp_tool("list_tasks", {}, timeout=15)
        if not task_data.startswith("[MCP"):
            context_parts.append(f"## ACTIVE TASKS\n{task_data[:2000]}")

    # --- Intel / Research queries ---
    intel_keywords = ["intel", "innovation", "research", "scan", "sweep", "brief", "news", "incubator"]
    if any(kw in content_lower for kw in intel_keywords):
        # Check wing memory for recent intel
        mem_data = _call_mcp_tool("wing_memory_search", {"query": content[:200], "limit": 5}, timeout=15)
        if not mem_data.startswith("[MCP"):
            context_parts.append(f"## WING MEMORY (relevant)\n{mem_data[:2000]}")

    # --- Drive / File queries ---
    drive_keywords = ["drive", "file", "document", "folder", "spreadsheet", "sheet"]
    if any(kw in content_lower for kw in drive_keywords):
        drive_data = _call_mcp_tool("drive_list_files", {"max_results": 10}, timeout=15)
        if not drive_data.startswith("[MCP"):
            context_parts.append(f"## RECENT DRIVE FILES\n{drive_data[:2000]}")

    # --- Flight queries ---
    flight_keywords = [
        "flight", "airline", "finnair", "air", "route", "airport",
        "departure", "arrival", "layover", "connection", "pnr",
        "bb4x94", "delayed", "cancel",
    ]
    if any(kw in content_lower for kw in flight_keywords):
        # Try to extract a PNR/booking ref (uppercase alphanumeric 5-6 chars)
        pnr_match = re.search(r'\b([A-Z0-9]{5,6})\b', content)
        if pnr_match:
            pnr = pnr_match.group(1)
            # Check if any client has this PNR via dossier scan (already fetched above)
            _log(f"Flight PNR detected: {pnr}")

        # Check airline route changes
        airline_data = _call_mcp_tool("scan_airline_route_changes", {}, timeout=20)
        if not airline_data.startswith("[MCP"):
            context_parts.append(f"## AIRLINE ROUTE CHANGES\n{airline_data[:2000]}")

        # Check client airline impact
        for name in ["furlow", "westbrook", "lyons", "mcleod", "britan", "ely", "darrow"]:
            if name in content_lower:
                impact_data = _call_mcp_tool(
                    "check_client_airline_impact", {"client_name": name}, timeout=20
                )
                if not impact_data.startswith("[MCP"):
                    context_parts.append(f"## AIRLINE IMPACT: {name.title()}\n{impact_data[:2000]}")
                break

        # FlightAware needs origin* + destination* — skip unless we can extract route
        # For specific flight tracking, use track_flight_fr24 or track_flight_flightaware
        flight_match = re.search(r'(AY|BA|VS|AA|DL|UA|LH|AF|SK|FI)\s*\d{1,4}', content, re.IGNORECASE)
        if flight_match:
            flight_num = flight_match.group(0).replace(" ", "").upper()
            fa_data = _call_mcp_tool(
                "track_flight_fr24", {"flight_number": flight_num}, timeout=20
            )
            if not fa_data.startswith("[MCP"):
                context_parts.append(f"## FLIGHT TRACKING: {flight_num}\n{fa_data[:2000]}")

    # --- Cruise queries ---
    # search_live_cruise_voyages needs url* — requires a specific cruise line URL
    # Use wing_memory + dossier data for cruise context instead
    cruise_keywords = [
        "cruise", "ship", "cabin", "silversea", "regent", "cunard",
        "oceania", "seabourn", "viking", "amawaterways", "ponant",
        "silver nova", "silver muse", "grandeur", "splendor",
        "voyage", "sailing", "deck", "suite", "stateroom",
    ]
    if any(kw in content_lower for kw in cruise_keywords):
        # Pull dossier data if not already fetched
        if not any("DOSSIER" in p for p in context_parts):
            dossier_data = _call_mcp_tool("scan_dossiers", {}, timeout=15)
            if not dossier_data.startswith("[MCP"):
                context_parts.append(f"## DOSSIER DATA (cruise context)\n{dossier_data[:3000]}")
        # Wing memory for cruise intel
        cruise_mem = _call_mcp_tool("wing_memory_search", {"query": content[:200], "limit": 5}, timeout=15)
        if not cruise_mem.startswith("[MCP"):
            context_parts.append(f"## CRUISE INTEL (wing memory)\n{cruise_mem[:2000]}")
        # List available ships
        ship_data = _call_mcp_tool("list_available_ships", {}, timeout=15)
        if not ship_data.startswith("[MCP"):
            context_parts.append(f"## AVAILABLE SHIPS\n{ship_data[:2000]}")

    # --- Hotel queries ---
    # search_hotels needs: check_in*, check_out*, plus destination or lat/lon
    # Only call if we can extract dates, otherwise use wing memory
    hotel_keywords = ["hotel", "resort", "property", "room", "rate", "slh", "hotelbeds", "stay", "accommodation"]
    if any(kw in content_lower for kw in hotel_keywords):
        hotel_mem = _call_mcp_tool("wing_memory_search", {"query": f"hotel {content[:150]}", "limit": 5}, timeout=15)
        if not hotel_mem.startswith("[MCP"):
            context_parts.append(f"## HOTEL INTEL (wing memory)\n{hotel_mem[:2000]}")

    # --- Tour / Excursion queries ---
    # search_tours needs: latitude*, longitude* — skip unless we have coords
    # Use wing memory + viator/getyourguide for text-based search
    tour_keywords = ["tour", "excursion", "activity", "shore", "viator", "getyourguide", "musement"]
    if any(kw in content_lower for kw in tour_keywords):
        tour_mem = _call_mcp_tool("wing_memory_search", {"query": f"tour excursion {content[:150]}", "limit": 5}, timeout=15)
        if not tour_mem.startswith("[MCP"):
            context_parts.append(f"## TOUR INTEL (wing memory)\n{tour_mem[:2000]}")

    # --- Weather queries ---
    weather_keywords = ["weather", "forecast", "temperature", "rain", "storm"]
    if any(kw in content_lower for kw in weather_keywords):
        # Schema: zipcode* (not zip_code)
        weather_data = _call_mcp_tool("get_noaa_forecast_by_zip", {"zipcode": "80132"}, timeout=15)
        if not weather_data.startswith("[MCP"):
            context_parts.append(f"## WEATHER (Monument, CO)\n{weather_data[:1500]}")

    # --- Calendar queries ---
    cal_keywords = ["calendar", "schedule", "event", "meeting", "deadline", "due"]
    if any(kw in content_lower for kw in cal_keywords):
        cal_data = _call_mcp_tool("calendar_list_events", {"days_ahead": 14}, timeout=15)
        if not cal_data.startswith("[MCP"):
            context_parts.append(f"## UPCOMING CALENDAR EVENTS\n{cal_data[:2000]}")

    # --- Transfer queries ---
    # search_blacklane_transfers needs: pickup_location*, dropoff_location*, date*
    # Only useful with specific locations — fall back to wing memory
    transfer_keywords = ["transfer", "pickup", "car service", "limo", "airport transfer", "blacklane"]
    if any(kw in content_lower for kw in transfer_keywords):
        transfer_mem = _call_mcp_tool("wing_memory_search", {"query": f"transfer {content[:150]}", "limit": 5}, timeout=15)
        if not transfer_mem.startswith("[MCP"):
            context_parts.append(f"## TRANSFER INTEL (wing memory)\n{transfer_mem[:2000]}")

    # --- Commission / Finance queries ---
    finance_keywords = ["commission", "markup", "revenue", "profit", "margin", "net", "gross"]
    if any(kw in content_lower for kw in finance_keywords):
        # reconcile_commissions can be slow — use generous timeout
        comm_data = _call_mcp_tool("reconcile_commissions", {"days_back": 30}, timeout=45)
        if not comm_data.startswith("[MCP"):
            context_parts.append(f"## COMMISSION DATA\n{comm_data[:2000]}")

    if not context_parts:
        return ""

    return (
        "\n\n--- LIVE DATA FROM MCP (140+ tools) ---\n"
        "The following is REAL data fetched from MCP tools. "
        "Use ONLY this data to answer. Do NOT add details beyond what is shown.\n\n"
        + "\n\n".join(context_parts)
        + "\n--- END LIVE DATA ---\n"
    )


# ── Hale's Brain: Gemini 3.1 Flash Lite via OpenRouter (Opus plan 2026-05-04) ──
HALE_MODEL = "google/gemini-3.1-flash-lite-preview-20260303"  # ~$0.01/gen, crew standard
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")  # retained for fallback


def _call_hale(system_prompt: str, query: str,
               max_tokens: int = 800, temperature: float = 0.5) -> str:
    """Hale's primary brain: Gemini 3.1 Flash Lite via OpenRouter (~$0.01/gen).
    Falls back to Grok 4.1 Fast on failure.
    """
    try:
        return _call_openrouter(system_prompt, query,
                                model=HALE_MODEL,
                                max_tokens=max_tokens,
                                temperature=temperature)
    except Exception as e:
        logger.warning("Gemini Flash Lite failed (%s), falling back to Grok", e)
        return _call_grok(system_prompt, query,
                          max_tokens=max_tokens,
                          temperature=temperature)


# ── Paths ──
ROOT = Path(__file__).resolve().parent.parent
OPSCENTER = ROOT / "OpsCenter"
QUEUE_FILE = OPSCENTER / "01_TASK_QUEUE.json"
COMMAND_LOG = OPSCENTER / "00_COMMAND_LOG.md"
PROCESS_LOG = OPSCENTER / "process.log"

_file_handler = RotatingFileHandler(
    str(PROCESS_LOG), maxBytes=5*1024*1024, backupCount=5
)
_file_handler.setFormatter(logging.Formatter("%(message)s"))
_process_logger = logging.getLogger("opscenter.process_log")
_process_logger.addHandler(_file_handler)
_process_logger.propagate = False

# ── Telegram ──
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_C2_BOT_TOKEN", "")
TELEGRAM_COMMANDER_ID = os.environ.get("TELEGRAM_COMMANDER_ID", "")

# ── Mountain Time ──
MT = timezone(timedelta(hours=-6))  # MDT


def _log(msg: str):
    """Append timestamped line to process log and stdout."""
    ts = datetime.now(MT).strftime("%Y-%m-%d %H:%M:%S MT")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        _process_logger.info(line)
    except OSError:
        pass



def _sanitize_html(text: str) -> str:
    """Convert Gemini's output to clean Telegram HTML.

    Telegram supports: <b> <i> <u> <s> <code> <pre> <a href> <blockquote>
    This function:
    1. Converts markdown artifacts to HTML (Gemini sometimes mixes formats)
    2. Escapes bare <, >, & that aren't part of valid tags
    3. Auto-closes unclosed tags (Gemini often forgets)
    4. Strips unsupported HTML tags
    """
    # Convert markdown bold **text** → <b>text</b>
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'__(.+?)__', r'<b>\1</b>', text)
    # Convert markdown italic *text* → <i>text</i>
    text = re.sub(r'(?<!</b>)\*(.+?)\*(?!<)', r'<i>\1</i>', text)
    text = re.sub(r'(?<!</)_(.+?)_(?!>)', r'<i>\1</i>', text)
    # Convert markdown code `text` → <code>text</code>
    text = re.sub(r'```(\w*)\n?(.*?)```', r'<pre>\2</pre>', text, flags=re.DOTALL)
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    # Convert markdown headers ## text → <b>text</b>
    text = re.sub(r'^#{1,6}\s+(.+)$', r'<b>\1</b>', text, flags=re.MULTILINE)
    # Convert markdown links [text](url) → <a href="url">text</a>
    text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', text)

    # Auto-close unclosed tags — Gemini often opens <pre> or <b> without closing
    SELF_CLOSING_TAGS = {"b", "i", "u", "s", "code", "pre", "blockquote"}
    open_tags = []
    for m in re.finditer(r'<(/?)(\w+)(?:\s[^>]*)?>',  text):
        is_close = m.group(1) == "/"
        tag_name = m.group(2).lower()
        if tag_name not in SELF_CLOSING_TAGS:
            continue
        if is_close:
            if open_tags and open_tags[-1] == tag_name:
                open_tags.pop()
        else:
            open_tags.append(tag_name)
    # Close any still-open tags in reverse order
    for tag in reversed(open_tags):
        text += f"</{tag}>"

    # Escape bare & < > that aren't part of valid tags
    # First protect valid tags, then escape, then restore
    tag_pattern = re.compile(
        r'<(/?)(?:b|i|u|s|code|pre|a\s[^>]*|/a|blockquote)(?:\s[^>]*)?>',
        re.IGNORECASE,
    )
    tags = []
    def _save_tag(m):
        tags.append(m.group(0))
        return f"\x00TAG{len(tags)-1}\x00"
    text = tag_pattern.sub(_save_tag, text)

    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")

    for i, tag in enumerate(tags):
        text = text.replace(f"\x00TAG{i}\x00", tag)

    return text


def _send_telegram(
    chat_id: str,
    text: Optional[str] = None,
    html_content: Optional[str] = None,
    image_url: Optional[str] = None,
    caption: Optional[str] = None,
    parse_mode: str = "HTML",
) -> bool:
    """Send message(s) and/or image to Commander via Telegram C2 bot.

    HTML-first. Telegram HTML is far more forgiving than MarkdownV2.
    Fallback chain: HTML → plain text (no MarkdownV2 — it's unreliable).
    """
    if not TELEGRAM_BOT_TOKEN:
        _log("WARN: No TELEGRAM_C2_BOT_TOKEN — cannot send reply")
        return False

    success = True
    send_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    # Determine content and parse mode
    if html_content:
        message_to_send = html_content
        current_parse_mode = "HTML"
    elif text:
        message_to_send = _sanitize_html(text)
        current_parse_mode = "HTML"
    else:
        return True  # Nothing to send

    if message_to_send:
        chunks = split_message(message_to_send)

        for i, chunk in enumerate(chunks):
            if not chunk.strip():
                continue

            if len(chunks) > 1:
                part_hdr = f"<b>({i + 1}/{len(chunks)})</b>\n"
                chunk = part_hdr + chunk

            # Try HTML first, then plain text
            sent = False
            for mode in [current_parse_mode, None]:
                try:
                    payload = {"chat_id": chat_id, "text": chunk}
                    if mode:
                        payload["parse_mode"] = mode
                    else:
                        # Strip HTML for plain text fallback
                        payload["text"] = re.sub(r'<[^>]+>', '', chunk)
                    resp = requests.post(send_url, json=payload, timeout=15)
                    if resp.ok:
                        sent = True
                        break
                    _log(f"Telegram send failed ({mode}): {resp.status_code} {resp.text[:150]}")
                except Exception as e:
                    _log(f"Telegram send error ({mode}): {e}")

            if not sent:
                success = False
                _log(f"All send attempts failed for chunk: {chunk[:80]}...")

    # Send image if provided
    if image_url:
        try:
            img_payload = {
                "chat_id": chat_id,
                "photo": image_url,
                "caption": caption or (text[:200] if text else ""),
                "parse_mode": "HTML",
            }
            resp = requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto",
                json=img_payload, timeout=15,
            )
            if not resp.ok:
                success = False
                _log(f"Telegram photo failed: {resp.status_code} {resp.text[:150]}")
        except Exception as e:
            success = False
            _log(f"Telegram photo error: {e}")

    return success



def _log_command(task_id: str, task_type: str, persona: str, result_summary: str):
    """Append to the command log markdown."""
    ts = datetime.now(MT).strftime("%a %b %d %I:%M:%S %p MT %Y")
    entry = f"- **[{ts}]** HALE routed `{task_type}` ({task_id}) → **{persona}** — {result_summary}\n"
    try:
        with open(COMMAND_LOG, "a") as f:
            f.write(entry)
    except OSError:
        pass


# ── Chat Log — full conversation history ─────────────────────────────────────
CHAT_LOG = OPSCENTER / "hale_chat_log.jsonl"
_CHAT_LOG_DRIVE_INTERVAL = 20  # Sync to Drive every N entries
_chat_log_counter = 0

_chat_file_handler = RotatingFileHandler(
    str(CHAT_LOG), maxBytes=10*1024*1024, backupCount=3
)
_chat_file_handler.setFormatter(logging.Formatter("%(message)s"))
_chat_logger = logging.getLogger("opscenter.chat_log")
_chat_logger.addHandler(_chat_file_handler)
_chat_logger.propagate = False


def _log_chat(task: dict, response: str, engine: str = ""):
    """Append full chat exchange to JSONL log.

    Captures: timestamp, Commander's full message, Hale's full response,
    engine used, task metadata. Survives connectivity drops.
    """
    global _chat_log_counter

    entry = {
        "ts": datetime.now(MT).isoformat(),
        "task_id": task.get("task_id", "UNKNOWN"),
        "task_type": task.get("task_type", "unknown"),
        "engine": engine,
        "commander_msg": task.get("content", ""),
        "hale_response": response,
        "chat_id": task.get("chat_id", ""),
        "mcp_context_len": len(task.get("_mcp_context", "")),
    }

    try:
        _chat_logger.info(json.dumps(entry, ensure_ascii=False))
    except OSError as e:
        _log(f"WARN: Chat log write failed: {e}")
        return

    _chat_log_counter += 1

    # Periodic backup to Google Drive
    if _chat_log_counter % _CHAT_LOG_DRIVE_INTERVAL == 0:
        _backup_chat_log_to_drive()


def _backup_chat_log_to_drive():
    """Upload chat log to D2M Google Drive for resilience."""
    try:
        # Schema: local_path*, folder_id?, name?
        result = _call_mcp_tool(
            "drive_upload_file",
            {
                "local_path": str(CHAT_LOG),
                "name": f"hale_chat_log_{datetime.now(MT).strftime('%Y-%m-%d')}.jsonl",
            },
            timeout=30,
        )
        if result.startswith("[MCP"):
            _log(f"Chat log Drive backup failed: {result}")
        else:
            _log("Chat log backed up to Drive: OpsCenter Logs/")
    except Exception as e:
        _log(f"Chat log Drive backup error: {e}")


# ============================================================================
# TASK HANDLERS — Each returns a string response for the Commander
# ============================================================================

def _get_blackboard_context() -> str:
    """Read current blackboard state — injected into Hale's system prompt."""
    summary_path = OPSCENTER / "collaboration" / "blackboard_summary.txt"
    try:
        content = summary_path.read_text(encoding="utf-8").strip()
        if content:
            return f"\n\n## CURRENT BLACKBOARD STATE\n{content}\n"
    except Exception:
        pass
    return ""


def _build_hale_system_prompt() -> str:
    """Build Hale's system prompt grounded in real operational data.

    Hale now has MCP access via _fetch_mcp_context() which pre-fetches
    live data and injects it into the user message. The system prompt
    tells Gemini to use ONLY that data — never fabricate.
    """
    timer_schedule = (
        "Daily automated schedule (all times MDT):\n"
        "  00:30 — Booking monitor\n"
        "  00:50 — Preflight check\n"
        "  01:00 — Intel sweep (A2 → Telegram)\n"
        "  01:30 — Morning brief + factbook refresh\n"
        "  01:35 — FPD (final payment deadline) alerts\n"
        "  01:40 — Airline route monitor\n"
        "  01:45 — Innovation scan (daily)\n"
        "  01:50 — Power harvest (***REMOVED-SECRET*** intel)\n"
        "  01:55 — Incubator AM scrape\n"
        "  02:00 — X/OSINT feed + Evernote backup\n"
        "  02:05 — Sculptor learn\n"
        "  02:10 — Incubator A2 intake\n"
        "  02:15 — Incubator ELON queue\n"
        "  02:30 — Inbox cleanup + backup verify (Mon)\n"
        "  07:00 — Email intel sweep\n"
        "  14:00 — Z Fold test\n"
        "  18:30 — Incubator prompt\n"
        "  19:00 — Incubator execute\n"
        "  19:30 — Incubator review\n"
        "  20:13 — Sculptor harvest\n"
        "Weekly: Innovation deep scan (Sun 01:30), Evernote backup (Mon 02:00)\n"
        "Monthly: Product archive (1st of month 07:15)\n"
    )

    try:
        q = json.loads(QUEUE_FILE.read_text()) if QUEUE_FILE.exists() else []
        q_count = len(q)
    except Exception:
        q_count = 0
    try:
        mq = json.loads((OPSCENTER / "03_CLAUDE_MAX_QUEUE.json").read_text()) \
            if (OPSCENTER / "03_CLAUDE_MAX_QUEUE.json").exists() else []
        mq_count = len(mq)
    except Exception:
        mq_count = 0

    return (
        "You are Ms. Victoria 'Victory' Hale, SES-6 — VCSAF-equivalent, COS of Dreams2Memories Travel.\n"
        "You are running inside the Hale-Loop daemon on DeepSeek V3.1 (OpenRouter).\n"
        "You have access to 140+ MCP tools via the Thunderbird MCP server.\n\n"

        "## HARD RULES — NEVER VIOLATE\n"
        "1. NEVER fabricate data. If LIVE DATA is provided below your message, "
        "use ONLY that data. Do NOT add details, numbers, names, or statuses "
        "beyond what the live data shows.\n"
        "2. If NO live data section is present and the Commander asks about "
        "specific bookings, clients, emails, or operational details (names, amounts, "
        "confirmation numbers) — say: \"No matching data was retrieved. Try being "
        "more specific.\"\n"
        "   BUT: for general research questions (hotels, destinations, experiences, "
        "travel info) — answer fully from your training knowledge. Do NOT refuse.\n"
        "3. NEVER claim to have performed actions (sent emails, updated files, "
        "contacted people). You can only READ data and REPORT it.\n"
        "4. NEVER invent booking statuses, payment amounts, dates, or names "
        "that aren't in the live data.\n"
        "5. If live data contains an error like [MCP ERROR] or [MCP OFFLINE], "
        "report the error honestly — don't work around it.\n\n"

        "## WHAT YOU CAN DO\n"
        "- Summarize and present LIVE DATA from MCP tools (injected below your message)\n"
        "- Answer general travel/business questions from your training data\n"
        "- Report the real automated timer schedule (below)\n"
        f"- Report queue status: Task queue={q_count}, Claude MAX queue={mq_count}\n"
        "- Acknowledge tasks and confirm routing\n"
        "- Provide strategic/operational advice\n\n"

        f"## REAL OPERATIONAL SCHEDULE\n{timer_schedule}\n"

        "## RESPONSE FORMAT — TELEGRAM HTML\n"
        "Output Telegram-compatible HTML. Supported tags:\n"
        "  <b>bold</b>  <i>italic</i>  <code>inline code</code>\n"
        "  <pre>code block</pre>  <a href=\"url\">link</a>\n"
        "Do NOT use markdown (**, ##, ```) — use HTML tags only.\n\n"
        "## VISUAL STRUCTURE\n"
        "Use this layout for data-rich answers:\n"
        "  1. One-line status header with emoji: ✅ ⚠️ ❌ 📊 ✈️ 🚢 💰 📧\n"
        "  2. Section headers in <b>bold</b>\n"
        "  3. Data in <pre> blocks for alignment (tables, lists)\n"
        "  4. Divider lines: ─────────────────────\n"
        "  5. Action items numbered and <b>bold</b>\n\n"
        "Example:\n"
        "  ✈️ <b>FURLOW FLIGHT STATUS</b>\n"
        "  ─────────────────────\n"
        "  <pre>PNR     : BB4X94\n"
        "  Airline : Finnair\n"
        "  Route   : HEL → AMS → JFK\n"
        "  Status  : CONFIRMED</pre>\n\n"
        "  ⚠️ <b>Action Required</b>\n"
        "  1. Seat assignment pending\n\n"
        "## RESPONSE LENGTH\n"
        "- Use as much space as the data requires — up to 3 messages if needed.\n"
        "- Do NOT truncate data to be brief. The Commander wants the FULL picture.\n"
        "- When you don't know something and no live data was fetched, say so in one line.\n"
        "- Sign as 'Hale'.\n"

        # ── Blackboard State (injected automatically by blackboard_sync.py) ──
        + _get_blackboard_context()
    )


def _handle_commander_message(task: dict) -> str:
    """Process a free-text message from the Commander via Telegram.

    Division of labor:
        1. Groq classifies the message (free, fast)
        2. Route to appropriate engine based on classification
        3. Only use Claude MAX for client-facing output
    """
    task_id = task.get("task_id", "UNKNOWN")
    content = task.get("content", "").strip()
    chat_id = task.get("chat_id", TELEGRAM_COMMANDER_ID)

    if not content:
        return "Empty message received. Standing by."

    # ── Hale Brain Override — Commander prefix detection ──
    # "OPUS: [task]"   → force Brain 2 with Claude Opus headless
    # "Sonnet: [task]" → force Brain 2 with Claude Sonnet headless
    brain_override = None
    if content.upper().startswith("OPUS:"):
        brain_override = "opus"
        content = content[5:].strip()
        _log("Brain override: OPUS (Commander prefix)")
    elif content.lower().startswith("sonnet:"):
        brain_override = "sonnet"
        content = content[7:].strip()
        _log("Brain override: Sonnet (Commander prefix)")

    # If brain override set, dispatch directly via HaleDispatcher and return
    if brain_override:
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from hale_dispatcher import HaleDispatcher
            hale = HaleDispatcher()
            return hale.dispatch(content, brain_override=brain_override)
        except Exception as e:
            _log(f"HaleDispatcher override failed: {e} — falling through to standard routing")
            # Fall through to standard routing with stripped content

    # Step 1: Classify with local keyword matcher (zero API cost)
    task_type = classify_task(content)
    _log(f"Classified message as: {task_type.value}")

    # Step 2: Route based on classification
    # GROQ handles: operational, classification, summarization, research
    # GEMINI handles: morning_brief, data_extraction
    # CLAUDE MAX handles: client_facing, creative, voice_profile, crisis, strategic
    GROQ_TASKS = {
        TaskType.OPERATIONAL, TaskType.CLASSIFICATION,
        TaskType.SUMMARIZATION, TaskType.RESEARCH,
        TaskType.DATA_EXTRACTION, TaskType.EXTRACTION,
    }
    GEMINI_TASKS = {
        TaskType.MORNING_BRIEF,
    }
    # Everything else → Claude MAX (the money shot)

    system_prompt = _build_hale_system_prompt()

    # Fetch real data from MCP before calling Gemini
    mcp_context = _fetch_mcp_context(content)
    if mcp_context:
        _log(f"MCP context fetched ({len(mcp_context)} chars)")
        augmented_content = content + "\n" + mcp_context
    else:
        augmented_content = content

    try:
        if task_type in GROQ_TASKS:
            engine = "DeepSeek V3.1 (OpenRouter) + MCP" if mcp_context else "DeepSeek V3.1 (OpenRouter)"
            try:
                response = _call_openrouter(system_prompt, augmented_content,
                                            model=HALE_MODEL,
                                            max_tokens=2500, temperature=0.3)
            except Exception as _ds_err:
                _log(f"Gemini Flash Lite failed, falling back to Grok: {_ds_err}")
                engine = "Grok 4.1 Fast (fallback)"
                response = _call_grok(system_prompt, augmented_content,
                                      max_tokens=2500, temperature=0.3)
        elif task_type in GEMINI_TASKS:
            engine = "Gemini 3.1 Flash Lite (OpenRouter)"
            try:
                response = _call_openrouter(system_prompt, content,
                                            model=HALE_MODEL,
                                            max_tokens=2000, temperature=0.5)
            except Exception as _ds_err:
                _log(f"Gemini Flash Lite failed, falling back to Grok: {_ds_err}")
                engine = "Grok 4.1 Fast (fallback)"
                response = _call_grok(system_prompt, content,
                                      max_tokens=800, temperature=0.5)
        else:
            # Route to Claude MAX queue
            _queue_for_claude_max({
                "task_id": task_id,
                "task_type": task_type.value,
                "content": content,
                "chat_id": chat_id,
                "_mcp_context": mcp_context # Pass MCP context to Claude if available
            })
            engine = "Claude MAX (queued)"
            response = f"Task {task_id} (type: {task_type.value}) queued for Claude MAX. Commander will be notified when processed."

    except Exception as e:
        engine = "ERROR"
        response = f"Engine failure: {e}\nOriginal message: {content[:200]}"
        _log(f"Handler error: {e}")

    _log(f"Processed via {engine}: {content[:80]}...")
    # Stash metadata on task for chat log
    task["_engine"] = engine
    task["_mcp_context"] = mcp_context or ""
    return response


def _queue_for_claude_max(task: dict):
    """Write high-value tasks to a separate queue for Claude Code to process."""
    max_queue = OPSCENTER / "03_CLAUDE_MAX_QUEUE.json"
    try:
        existing = json.loads(max_queue.read_text()) if max_queue.exists() else []
    except (json.JSONDecodeError, OSError):
        existing = []

    task["queued_at"] = datetime.now(MT).isoformat()
    task["requires"] = "claude_max"
    existing.append(task)

    max_queue.write_text(json.dumps(existing, indent=2))


def _handle_send_draft(task: dict) -> str:
    """Handle draft approval — Commander pressed Approve in Telegram."""
    draft_id = task.get("draft_id", "unknown")
    chat_id = task.get("chat_id", TELEGRAM_COMMANDER_ID)

    # This needs MCP gmail tools — queue for Claude Code
    _queue_for_claude_max({
        "task_type": "send_approved_draft",
        "draft_id": draft_id,
        "chat_id": chat_id,
        "queued_at": datetime.now(MT).isoformat(),
    })

    return f"Draft `{draft_id}` approved. Queued for send via Claude Code MCP."


def _handle_innovation_scan(task: dict) -> str:
    """Run innovation scan using thunderbird_innovation_scanner.py."""
    scan_type = task.get("scan_type", "daily")
    try:
        if scan_type == "weekly":
            result = run_weekly_scan()
        else:
            result = run_daily_scan()

        raw_lines = [f"*A12 Innovation Scan Complete ({scan_type.title()})*", ""]
        if result.findings:
            raw_lines.append(f"**Top {len(result.top_findings)} Findings:**")
            for i, f in enumerate(result.top_findings[:5], 1):
                raw_lines.append(f"{i}. [{f.source}] {f.title} (Score: {f.score})")
                raw_lines.append(f"   URL: {f.url}")
            if len(result.findings) > 5:
                raw_lines.append(f"  ...and {len(result.findings) - 5} more. See digest for full details.")
        else:
            raw_lines.append("No significant innovation findings today.")

        if result.errors:
            raw_lines.append("\n**Errors during scan:**")
            for err in result.errors:
                raw_lines.append(f"- {err}")

        raw_lines.append(f"\nFull digest: `~/Thunderbird/intel/daily_innovation_digest.md`")
        raw_output = "\n".join(raw_lines)

        # ── Hale synthesis layer ──
        try:
            sys.path.insert(0, str(OPSCENTER))
            from hale_scan_wrapper import wrap_and_send
            return wrap_and_send(raw_output, scan_type="innovation", send_telegram=False)
        except Exception as synth_err:
            _log(f"Hale synthesis failed (returning raw): {synth_err}")
            return raw_output

    except Exception as e:
        return f"Innovation scan failed: {e}"


def _handle_morning_briefing(task: dict) -> str:
    """Generate and send the morning briefing using the full pipeline."""
    preview = task.get("preview", False)
    weekly = task.get("weekly", False)
    try:
        result_message = run_morning_briefing_pipeline(preview=preview, weekly=weekly)
        status = "Preview saved" if preview else "Briefing sent"
        return f"*{status}*: {result_message}"
    except Exception as e:
        logger.error(f"Morning briefing pipeline failed: {e}", exc_info=True)
        return f"Morning briefing generation failed: {e}"


def _handle_fpd_alert(task: dict) -> str:
    """Process FPD (Final Payment Deadline) alert — local Python, no LLM needed."""
    # Import overwatch checks directly
    try:
        from thunderbird_overwatch import _check_deadline_tracking
        result = _check_deadline_tracking()
        return f"*FPD Alert*\n\nStatus: {result.status.value}\n{result.message}"
    except Exception as e:
        return f"FPD check failed: {e}"


def _handle_sentinel_sweep(task: dict) -> str:
    """Run a full Sentinel sweep and report results."""
    try:
        # Setting use_llm=True for Sentinel to synthesize with Groq, as per Overwatch design.
        # The OpsCenter README says Groq handles operational summaries.
        report = run_sentinel_sweep(use_llm=True)
        response_lines = [
            f"*Sentinel Sweep Complete* (ID: {report.sweep_id})",
            f"Red Flags: {report.red_flags}",
            f"Yellow Flags: {report.yellow_flags}",
            f"Green Checks: {report.green_count}",
            f"Duration: {report.duration_seconds:.2f}s",
            "\n**Detailed Checks:**"
        ]
        for check in report.checks:
            icon = {"green": "✅", "yellow": "⚠️", "red": "❌", "skipped": "➖"}.get(check.status.value, "❓")
            response_lines.append(f"{icon} {check.check_name.replace("_", " ").title()}: {check.message}")
        
        if report.escalated_to_judge:
            response_lines.append("\n*Escalated to The Judge for deeper analysis.*")

        return "\n".join(response_lines)
    except Exception as e:
        logger.error(f"Sentinel sweep failed: {e}", exc_info=True)
        return f"Sentinel sweep failed: {e}"


def _handle_dossier_check(task: dict) -> str:
    """Run a dossier currency check and report results."""
    try:
        result = _check_dossier_currency()
        icon = {"green": "✅", "yellow": "⚠️", "red": "❌", "skipped": "➖"}.get(result.status.value, "❓")
        response_lines = [
            f"*Dossier Currency Check Complete*",
            f"{icon} Status: {result.status.value.upper()}",
            f"Message: {result.message}"
        ]
        if result.details:
            response_lines.append("\n**Details:**")
            for key, value in result.details.items():
                response_lines.append(f"- {key.replace('_', ' ').title()}: {json.dumps(value, indent=2) if isinstance(value, (list, dict)) else value}")
        return "\n".join(response_lines)
    except Exception as e:
        logger.error(f"Dossier currency check failed: {e}", exc_info=True)
        return f"Dossier currency check failed: {e}"


def _handle_commission_audit(task: dict) -> str:
    """Run a commission math check and report results."""
    try:
        result = _check_commission_math()
        icon = {"green": "✅", "yellow": "⚠️", "red": "❌", "skipped": "➖"}.get(result.status.value, "❓")
        response_lines = [
            f"*Commission Math Audit Complete*",
            f"{icon} Status: {result.status.value.upper()}",
            f"Message: {result.message}"
        ]
        if result.details:
            response_lines.append("\n**Details:**")
            for key, value in result.details.items():
                response_lines.append(f"- {key.replace('_', ' ').title()}: {json.dumps(value, indent=2) if isinstance(value, (list, dict)) else value}")
        return "\n".join(response_lines)
    except Exception as e:
        logger.error(f"Commission math audit failed: {e}", exc_info=True)
        return f"Commission math audit failed: {e}"


def _process_claude_max_queue_tasks() -> str:
    """Process tasks from the 03_CLAUDE_MAX_QUEUE.json."""
    max_queue_file = OPSCENTER / "03_CLAUDE_MAX_QUEUE.json"
    if not max_queue_file.exists():
        return "Claude MAX queue is empty or does not exist."

    try:
        queue = json.loads(max_queue_file.read_text())
    except (json.JSONDecodeError, OSError):
        return "Failed to read Claude MAX queue. Invalid JSON or file error."

    if not queue:
        return "Claude MAX queue is empty."

    processed_count = 0
    results = []

    # Process one task at a time to prevent blocking the daemon
    if queue:
        task = queue.pop(0)
        max_queue_file.write_text(json.dumps(queue, indent=2)) # Write back updated queue

        task_type = task.get("task_type", "unknown_claude_max_task")
        chat_id = str(task.get("chat_id", TELEGRAM_COMMANDER_ID))
        task_id = task.get("task_id", "UNKNOWN_MAX")

        _log(f"Processing Claude MAX task {task_id} (type: {task_type})")

        # Dispatch to specific Claude MAX sub-handlers here
        # For now, a placeholder. We will implement these in later steps.
        if task_type == "client_email_draft":
            # This is where the actual drafting logic will go
            results.append(f"Client email draft for task {task_id} initiated (placeholder).")
        elif task_type == "send_approved_draft":
            # This is where the draft sending logic will go
            results.append(f"Approved draft send for {task.get('draft_id')} initiated (placeholder).")
        else:
            results.append(f"Unsupported Claude MAX task type '{task_type}' for task {task_id}. Task content: {task.get('content', '')[:100]}...")

        processed_count += 1
    
    return f"Processed {processed_count} Claude MAX task(s). Results: {' | '.join(results)}"

# New handler for processing the Claude MAX queue
def _handle_process_claude_max_queue(task: dict) -> str:
    """Handler to trigger processing of the Claude MAX queue."""
    return _process_claude_max_queue_tasks()


# ============================================================================
# HANDLER DISPATCH TABLE
# ============================================================================

HANDLERS = {
    "commander_message": _handle_commander_message,
    "send_draft": _handle_send_draft,
    "innovation_scan": _handle_innovation_scan,
    "morning_briefing": _handle_morning_briefing,
    "fpd_alert": _handle_fpd_alert,
    "sentinel_sweep": _handle_sentinel_sweep,
    "dossier_check": _handle_dossier_check,
    "commission_audit": _handle_commission_audit,
    "process_claude_max_queue": _handle_process_claude_max_queue,
}


# ============================================================================
# QUEUE CONSUMER — Pop and process
# ============================================================================

def pop_task() -> dict | None:
    """Atomically pop the first task from the queue. Returns None if empty."""
    if not QUEUE_FILE.exists():
        return None

    try:
        queue = json.loads(QUEUE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return None

    if not queue:
        return None

    task = queue.pop(0)
    QUEUE_FILE.write_text(json.dumps(queue, indent=2))
    return task


def process_one() -> bool:
    """Pop one task, process it, send result back. Returns True if a task was processed."""
    task = pop_task()
    if not task:
        return False

    task_id = task.get("task_id", "UNKNOWN")
    task_type = task.get("task_type", "generic")
    chat_id = str(task.get("chat_id", TELEGRAM_COMMANDER_ID))

    _log(f"Processing task {task_id} (type: {task_type})")

    # Find handler
    handler = HANDLERS.get(task_type)
    if handler:
        try:
            response = handler(task)
        except Exception as e:
            response = f"Handler crashed for {task_type}: {e}"
            _log(f"CRASH in {task_type}: {e}")
    else:
        response = f"Unknown task type: `{task_type}`\nRaw: {json.dumps(task)[:500]}"
        _log(f"No handler for task type: {task_type}")

    # Send result back to Commander via Telegram
    _send_telegram(chat_id, response)

    # Full chat log (Commander in + Hale out) — survives connectivity drops
    _log_chat(task, response, engine=task.get("_engine", ""))

    # Log to command log
    summary = response[:100].replace("\n", " ")
    _log_command(task_id, task_type, "COS", summary)

    _log(f"Task {task_id} complete — response sent to Telegram")
    return True


def run_daemon(poll_interval: int = 5):
    """Run the Hale-Loop: poll queue, process tasks, repeat forever."""
    _log("Hale-Loop Task Processor started (Python)")
    _log(f"Queue: {QUEUE_FILE}")
    _log(f"Poll interval: {poll_interval}s")
    _log(f"Telegram bot: {'configured' if TELEGRAM_BOT_TOKEN else 'MISSING'}")
    _log(f"Commander ID: {TELEGRAM_COMMANDER_ID or 'MISSING'}")

    while True:
        try:
            processed = process_one()
            if processed:
                _log("Task processed. Applying 10-second rate limit before next task.")
                time.sleep(10)  # Apply 10-second rate limit between tasks
                continue
        except Exception as e:
            _log(f"Daemon loop error: {e}")

        time.sleep(poll_interval)


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="OpsCenter Task Processor")
    parser.add_argument("--daemon", action="store_true",
                        help="Run as daemon (poll queue forever)")
    parser.add_argument("--once", action="store_true",
                        help="Process one task and exit")
    parser.add_argument("--status", action="store_true",
                        help="Show queue status")

    args = parser.parse_args()

    if args.daemon:
        run_daemon()
    elif args.once:
        if process_one():
            print("Task processed.")
        else:
            print("Queue empty.")
    elif args.status:
        try:
            queue = json.loads(QUEUE_FILE.read_text()) if QUEUE_FILE.exists() else []
        except (json.JSONDecodeError, OSError):
            queue = []
        max_q = OPSCENTER / "03_CLAUDE_MAX_QUEUE.json"
        try:
            max_queue = json.loads(max_q.read_text()) if max_q.exists() else []
        except (json.JSONDecodeError, OSError):
            max_queue = []
        print(f"Task Queue:       {len(queue)} pending")
        print(f"Claude MAX Queue: {len(max_queue)} pending")
        print(f"Telegram Bot:     {'OK' if TELEGRAM_BOT_TOKEN else 'MISSING'}")
        print(f"Commander ID:     {TELEGRAM_COMMANDER_ID or 'MISSING'}")
    else:
        parser.print_help()
