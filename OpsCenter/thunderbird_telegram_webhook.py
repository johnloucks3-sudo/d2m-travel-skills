"""
thunderbird_telegram_webhook.py — Thunderbird Telegram Webhook Gateway v2
Dreams2Memories Travel, LLC
Version: 2.0.0 | 2026-05-16

Replaces polling-based thunderbird_telegram_gw.py.
Cloudflare tunnel: tg.d2mluxury.quest → localhost:8768

Three bots:
  HALE-YODA   TOKEN_HALUYODA  /hale-yoda  Commander ↔ Hale only, Claude Sonnet
  HALE_D2M    TOKEN_STAFF     /staff      Staff channel, persona routing via slash cmd
  d2m_channels TOKEN_CHANNELS /channels   Infrastructure push, receive-only

Strike counter: 3 strikes → Signal migration notice. A strike = manual declaration
by Commander or automated detection (external daemon). This file implements the
file API only; silent-period detection lives in a separate watchdog.
"""

import json
import logging
import os
import re
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests
from flask import Flask, jsonify, request

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger("tg_webhook")

# ── Paths ─────────────────────────────────────────────────────────────────────
THUNDERBIRD = Path("/home/john/Thunderbird")
OPS = THUNDERBIRD / "OpsCenter"
PERSONAS = THUNDERBIRD / "Personas"

# ── Load .env files ───────────────────────────────────────────────────────────
def _load_env_file(path: str) -> None:
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip())
    except FileNotFoundError:
        pass

_load_env_file(str(THUNDERBIRD / ".env"))
_load_env_file(str(THUNDERBIRD / "config" / "telegram_gw.env"))

# ── Config ────────────────────────────────────────────────────────────────────
PORT = 8768
WEBHOOK_SECRET = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
TOKEN_HALUYODA = os.environ.get("TELEGRAM_D2MC2C_TOKEN", "")   # reuse existing var
TOKEN_STAFF    = os.environ.get("TELEGRAM_GOOSE_TOKEN", "")    # reuse existing var
TOKEN_CHANNELS = os.environ.get("TELEGRAM_DANI_TOKEN", "")     # reuse existing var
COMMANDER_ID   = int(os.environ.get("TELEGRAM_COMMANDER_ID", "7554895206"))
SONNET_MODEL   = "claude-sonnet-4-6"
OPUS_MODEL     = "claude-opus-4-6"
ENGINE_TIMEOUT = int(os.environ.get("TELEGRAM_GW_TIMEOUT", "300"))
OPENCODE_TIMEOUT = int(os.environ.get("OPENCODE_TIMEOUT", "60"))
MAX_CTX_TURNS  = 12
CHUNK_SIZE     = 4000
OPENCODE_BIN   = Path("/home/john/.opencode/bin/opencode")

# Webhook secret: if unset, log a warning but allow through so Commander can
# deploy first and then secure. A 403 on empty secret would silently brick gateway.
if not WEBHOOK_SECRET:
    log.warning("TELEGRAM_WEBHOOK_SECRET not set — webhook auth disabled. Set it!")

# ── Context files ─────────────────────────────────────────────────────────────
CTX_HALUYODA = OPS / "context_haluyoda.json"
CTX_STAFF    = OPS / "context_staff.json"

# ── Strike file ───────────────────────────────────────────────────────────────
STRIKE_FILE = OPS / "telegram_strike_counter.json"

# ── Persona globals (populated at startup) ────────────────────────────────────
HALE_SYSTEM  = ""
STAFF_INTRO_TXT = ""

# ── OpenCode model chain (spec: big-pickle → deepseek-v4-flash-free → gemini-2.5-flash)
OPENCODE_MODEL_CHAIN = [
    "opencode/big-pickle",
    "deepseek/deepseek-v4-flash-free",
    "google/gemini-2.5-flash",
]
_OC_RATE_MARKERS = ["rate limit", "rate-limit", "too many requests", "429"]

app = Flask(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# STRIKE COUNTER
# ─────────────────────────────────────────────────────────────────────────────

def get_strike_count() -> int:
    try:
        return json.loads(STRIKE_FILE.read_text()).get("count", 0)
    except Exception:
        return 0


def record_strike(reason: str) -> int:
    data = {"count": 0, "strikes": []}
    try:
        data = json.loads(STRIKE_FILE.read_text())
    except Exception:
        pass
    data["count"] = data.get("count", 0) + 1
    data.setdefault("strikes", []).append({
        "ts": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
    })
    STRIKE_FILE.write_text(json.dumps(data, indent=2))
    log.warning("Strike recorded (%d): %s", data["count"], reason)
    if data["count"] >= 3:
        _send_signal_migration_notice()
    return data["count"]


def clear_strikes() -> None:
    STRIKE_FILE.write_text(json.dumps({"count": 0, "strikes": []}, indent=2))


def _send_signal_migration_notice() -> None:
    """3-strike threshold hit — notify Commander via email."""
    try:
        from thunderbird_gmail import gmail_send_from_wing  # type: ignore
        gmail_send_from_wing(
            to="johnloucks3@gmail.com",
            subject="⚠️ Thunderbird Telegram — 3 Strikes: Signal Migration Required",
            body=(
                "Commander,\n\n"
                "The HALE-YODA Telegram gateway has hit 3 strikes. "
                "Recommend migrating to Signal or re-deploying the webhook.\n\n"
                "Check: /home/john/Thunderbird/OpsCenter/telegram_strike_counter.json\n\n"
                "— Iron Vic"
            ),
        )
    except Exception as e:
        log.error("Could not send Signal migration notice: %s", e)


# ─────────────────────────────────────────────────────────────────────────────
# CONTEXT MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

def load_context(ctx_file: Path) -> list:
    try:
        return json.loads(ctx_file.read_text())
    except Exception:
        return []


def save_context(ctx_file: Path, exchanges: list) -> None:
    ctx_file.write_text(json.dumps(exchanges[-MAX_CTX_TURNS:], indent=2))


def append_exchange(ctx_file: Path, user_msg: str, assistant_reply: str) -> None:
    exchanges = load_context(ctx_file)
    exchanges.append({
        "ts": datetime.now(timezone.utc).isoformat(),
        "user": user_msg,
        "assistant": assistant_reply,
    })
    save_context(ctx_file, exchanges)


def format_context_for_prompt(ctx_file: Path) -> str:
    exchanges = load_context(ctx_file)
    if not exchanges:
        return "[No prior context]"
    lines = []
    for ex in exchanges[-MAX_CTX_TURNS:]:
        lines.append(f"Commander: {ex.get('user', '')}")
        lines.append(f"Assistant: {ex.get('assistant', '')[:600]}")
    return "\n".join(lines)


def clear_context(ctx_file: Path) -> None:
    ctx_file.write_text("[]")


# ─────────────────────────────────────────────────────────────────────────────
# PERSONA LOADING (called at startup)
# ─────────────────────────────────────────────────────────────────────────────

def _load_personas() -> None:
    global HALE_SYSTEM, STAFF_INTRO_TXT
    hale_cos_path  = PERSONAS / "hale_cos.md"
    staff_intro_path = PERSONAS / "D2M_Staff_Introduction.md"
    hale_state_path = THUNDERBIRD / "hale_state.json"

    if hale_cos_path.exists():
        HALE_SYSTEM = hale_cos_path.read_text()[:6000]
    if staff_intro_path.exists():
        STAFF_INTRO_TXT = staff_intro_path.read_text()[:3000]

    # Append live state summary (mode + open tasks only, no PII)
    if hale_state_path.exists():
        try:
            state = json.loads(hale_state_path.read_text())
            mode  = state.get("system_mode", "GREEN")
            tasks = len(state.get("open_tasks", []))
            HALE_SYSTEM += f"\n\n[LIVE STATE: mode={mode}, open_tasks={tasks}]"
        except Exception:
            pass

    log.info("Personas loaded: HALE_SYSTEM=%d chars, STAFF_INTRO=%d chars",
             len(HALE_SYSTEM), len(STAFF_INTRO_TXT))


# ─────────────────────────────────────────────────────────────────────────────
# ENGINE FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def call_claude_engine(prompt: str, model: str = SONNET_MODEL) -> str:
    """Invoke Claude headless via `claude -p`. Uses Max OAuth token injection."""
    env = dict(os.environ)
    env.pop("ANTHROPIC_API_KEY", None)  # Strip stale API key — it overrides OAuth
    creds = Path.home() / ".claude" / ".credentials.json"
    if creds.exists():
        try:
            tok = json.loads(creds.read_text()).get("claudeAiOauth", {}).get("accessToken")
            if tok:
                env["CLAUDE_CODE_OAUTH_TOKEN"] = tok
        except Exception:
            pass
    try:
        result = subprocess.run(
            ["/home/john/.local/bin/claude", "--model", model, "-p", prompt,
             "--dangerously-skip-permissions"],
            capture_output=True, text=True, timeout=ENGINE_TIMEOUT,
            env=env, cwd=str(THUNDERBIRD),
        )
        if result.returncode == 0:
            return result.stdout.strip()
        log.error("Claude headless rc=%d: %s", result.returncode, result.stderr[:300])
        return f"[Engine error — Claude rc={result.returncode}]"
    except subprocess.TimeoutExpired:
        return "[Engine timeout — Claude exceeded limit]"
    except FileNotFoundError:
        return "[Engine error — claude binary not found at ~/.local/bin/claude]"
    except Exception as e:
        return f"[Engine error — {e}]"


def call_opencode_engine(system_prompt: str, user_msg: str) -> str:
    """Invoke OpenCode headless. Chain: big-pickle → deepseek-v4-flash-free → gemini-2.5-flash."""
    full_prompt = f"{system_prompt[:2000]}\n\n{user_msg}" if system_prompt else user_msg
    env = dict(os.environ)
    env["PATH"] = f"/home/john/.opencode/bin:{env.get('PATH', '')}"

    for model in OPENCODE_MODEL_CHAIN:
        try:
            result = subprocess.run(
                [str(OPENCODE_BIN), "run", "-m", model, full_prompt],
                capture_output=True, text=True, timeout=OPENCODE_TIMEOUT,
                cwd=str(THUNDERBIRD), env=env,
            )
            output = (result.stdout or result.stderr or "").strip()
            if any(m in output.lower() for m in _OC_RATE_MARKERS):
                log.warning("OpenCode rate-limited on %s — next model", model)
                continue
            if result.returncode != 0:
                log.error("OpenCode rc=%d on %s: %s", result.returncode, model, result.stderr[:200])
                continue
            log.info("OpenCode: %s (%d chars)", model, len(output))
            return output or "[Engine returned empty response]"
        except subprocess.TimeoutExpired:
            log.warning("OpenCode timeout on %s — next model", model)
            continue
        except FileNotFoundError:
            return "[Engine error — opencode binary not found at ~/.opencode/bin/opencode]"
        except Exception as e:
            log.error("OpenCode error on %s: %s", model, e)
            continue

    return "[Engine error — all OpenCode models exhausted]"


def call_openrouter_direct(model: str, system: str, user: str) -> str:
    """Direct OpenRouter API call for any model ID."""
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        return "[Engine error — OPENROUTER_API_KEY not set]"
    messages = []
    if system:
        messages.append({"role": "system", "content": system[:3000]})
    messages.append({"role": "user", "content": user})
    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json",
                     "X-Title": "Thunderbird Telegram Webhook GW"},
            json={"model": model, "max_tokens": 4096, "messages": messages},
            timeout=ENGINE_TIMEOUT,
        )
        if resp.status_code == 429:
            return f"[Rate limited on {model} — try again shortly]"
        resp.raise_for_status()
        choices = resp.json().get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content", "").strip()
        return f"[{model} returned empty response]"
    except requests.Timeout:
        return f"[{model} timed out after {ENGINE_TIMEOUT}s]"
    except Exception as e:
        return f"[Engine error — {model}: {e}]"


# ─────────────────────────────────────────────────────────────────────────────
# TELEGRAM API HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def tg(token: str, method: str, **kwargs) -> dict:
    """Low-level Telegram Bot API call."""
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/{method}",
            json=kwargs, timeout=15,
        )
        return resp.json()
    except Exception as e:
        log.error("tg() %s failed: %s", method, e)
        return {"ok": False, "error": str(e)}


def tg_send(token: str, chat_id: int, text: str, parse_mode: str = "HTML") -> bool:
    r = tg(token, "sendMessage", chat_id=chat_id, text=text, parse_mode=parse_mode)
    return bool(r.get("ok"))


def tg_send_photo(token: str, chat_id: int, photo_url_or_file_id: str,
                  caption: str = "", parse_mode: str = "HTML") -> bool:
    r = tg(token, "sendPhoto", chat_id=chat_id, photo=photo_url_or_file_id,
            caption=caption, parse_mode=parse_mode)
    return bool(r.get("ok"))


def tg_send_album(token: str, chat_id: int, photo_list: list) -> bool:
    """Send up to 10 photos as a media group. Each item: {url, caption}."""
    media = []
    for i, item in enumerate(photo_list[:10]):
        entry = {"type": "photo", "media": item.get("url", item.get("media", ""))}
        if i == 0 and item.get("caption"):
            entry["caption"] = item["caption"]
            entry["parse_mode"] = "HTML"
        media.append(entry)
    r = tg(token, "sendMediaGroup", chat_id=chat_id, media=media)
    return bool(r.get("ok"))


def tg_send_with_keyboard(token: str, chat_id: int, text: str,
                           buttons: list, parse_mode: str = "HTML") -> bool:
    """Send message with inline keyboard. buttons = [[{text, callback_data}]]."""
    keyboard = {"inline_keyboard": buttons}
    r = tg(token, "sendMessage", chat_id=chat_id, text=text,
            parse_mode=parse_mode, reply_markup=keyboard)
    return bool(r.get("ok"))


def tg_edit_message(token: str, chat_id: int, message_id: int,
                    new_text: str, parse_mode: str = "HTML") -> bool:
    r = tg(token, "editMessageText", chat_id=chat_id, message_id=message_id,
            text=new_text, parse_mode=parse_mode)
    return bool(r.get("ok"))


def tg_answer_callback(token: str, callback_query_id: str, text: str = "") -> bool:
    r = tg(token, "answerCallbackQuery", callback_query_id=callback_query_id, text=text)
    return bool(r.get("ok"))


def tg_send_document(token: str, chat_id: int, document_url: str, caption: str = "") -> bool:
    r = tg(token, "sendDocument", chat_id=chat_id, document=document_url, caption=caption)
    return bool(r.get("ok"))


def tg_send_voice(token: str, chat_id: int, audio_path: str) -> bool:
    try:
        with open(audio_path, "rb") as af:
            resp = requests.post(
                f"https://api.telegram.org/bot{token}/sendVoice",
                data={"chat_id": chat_id},
                files={"voice": af},
                timeout=30,
            )
        return bool(resp.json().get("ok"))
    except Exception as e:
        log.error("tg_send_voice failed: %s", e)
        return False


def _balance_html_tags(text: str) -> str:
    """Close any unclosed <b>/<i>/<code>/<pre> tags at chunk boundary."""
    open_tags = re.findall(r"<(b|i|code|pre)>", text)
    close_tags = re.findall(r"</(b|i|code|pre)>", text)
    tail = ""
    for tag in reversed(open_tags):
        if open_tags.count(tag) > close_tags.count(tag):
            tail += f"</{tag}>"
            close_tags.append(tag)
    return text + tail


def tg_send_chunked(token: str, chat_id: int, text: str, parse_mode: str = "HTML") -> None:
    """Split long messages on paragraph boundaries and send in order with 0.3s gap."""
    if len(text) <= CHUNK_SIZE:
        tg_send(token, chat_id, text, parse_mode)
        return

    paragraphs = text.split("\n\n")
    chunks, current = [], ""
    for para in paragraphs:
        if len(current) + len(para) + 2 <= CHUNK_SIZE:
            current += ("" if not current else "\n\n") + para
        else:
            if current:
                chunks.append(current)
            if len(para) > CHUNK_SIZE:
                # Hard split for oversized single paragraphs
                for i in range(0, len(para), CHUNK_SIZE):
                    chunks.append(para[i:i + CHUNK_SIZE])
                current = ""
            else:
                current = para
    if current:
        chunks.append(current)

    total = len(chunks)
    for idx, chunk in enumerate(chunks, 1):
        prefix = f"[{idx}/{total}] " if total > 1 else ""
        payload = prefix + (_balance_html_tags(chunk) if parse_mode == "HTML" else chunk)
        tg_send(token, chat_id, payload, parse_mode)
        if idx < total:
            time.sleep(0.3)


# ─────────────────────────────────────────────────────────────────────────────
# FORMATTED BRIEF HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def format_brief_header(title: str, emoji: str = "🦅") -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M MT")
    return f"{emoji} <b>{title.upper()}</b> | <i>{now}</i>"


def format_section(title: str, content: str, emoji: str = "") -> str:
    prefix = f"{emoji} " if emoji else ""
    return f"<b>{prefix}{title}</b>\n{content}\n"


def format_table_pre(headers: list, rows: list) -> str:
    col_widths = [max(len(str(h)), max((len(str(r[i])) for r in rows), default=0))
                  for i, h in enumerate(headers)]
    lines = [" | ".join(str(h).ljust(col_widths[i]) for i, h in enumerate(headers))]
    lines.append("-+-".join("-" * w for w in col_widths))
    for row in rows:
        lines.append(" | ".join(str(row[i] if i < len(row) else "").ljust(col_widths[i])
                                for i in range(len(headers))))
    return "<pre>" + "\n".join(lines) + "</pre>"


# ─────────────────────────────────────────────────────────────────────────────
# STAFF PERSONAS
# ─────────────────────────────────────────────────────────────────────────────

STAFF_PERSONAS = {
    "hale":       ("Col Victoria Hale (COS)", "claude"),
    "dembe":      ("Lt Col Marcus Dembe (A2 — Research)", "opencode"),
    "castillo":   ("Lt Col Ryan Castillo (A5 — Strategy)", "opencode"),
    "sterling":   ("Brig Gen Thomas Sterling (A7 — Process)", "opencode"),
    "harlan":     ("Victor Harlan (A9 — Finance)", "opencode"),
    "washington": ("Col James Washington (CH — Ethics)", "opencode"),
    "elon":       ("ELON (A12 — Innovation)", "opencode"),
    "naia":       ("Naia Solberg-Vega (EXEC — Brand)", "claude"),
    "navarro":    ("Dr. Sofia Navarro (A1 — Intake)", "opencode"),
    "reyes":      ("Marco Reyes (A8 — Experience)", "opencode"),
    "luna":       ("Luna Voss (A6 — Creative)", "claude"),
}

STAFF_DISAGREE_DIRECTIVE = (
    "STAFF DIRECTIVE (2026-05-16): Any Wing staff member may respectfully disagree with "
    "Commander. State your position once, directly, with reasoning. After Commander decides, "
    "all align. Do not suppress a genuine disagreement to please. Honest counsel is the mission."
)


# ─────────────────────────────────────────────────────────────────────────────
# WEBHOOK SECRET VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

def _validate_webhook_secret() -> bool:
    if not WEBHOOK_SECRET:
        return True  # Secret disabled — allow through with warning logged at startup
    incoming = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    return incoming == WEBHOOK_SECRET


# ─────────────────────────────────────────────────────────────────────────────
# MESSAGE PROCESSORS
# ─────────────────────────────────────────────────────────────────────────────

def process_haluyoda_message(update: dict) -> None:
    """Process incoming message for HALE-YODA bot (Commander ↔ Hale only)."""
    try:
        msg = update.get("message") or update.get("edited_message")
        if not msg:
            return

        chat_id = msg["chat"]["id"]
        user_id = msg["from"]["id"]
        text    = msg.get("text", "").strip()

        if not text:
            return

        # Commander-only gate
        if user_id != COMMANDER_ID:
            tg_send(TOKEN_HALUYODA, chat_id, "⚠️ HALE-YODA is Commander-only.")
            return

        # Slash commands
        if text == "/new":
            clear_context(CTX_HALUYODA)
            tg_send(TOKEN_HALUYODA, chat_id, "🦅 Context cleared. Fresh session.")
            return
        if text == "/status":
            _handle_status(TOKEN_HALUYODA, chat_id)
            return
        if text == "/help":
            _handle_help(TOKEN_HALUYODA, chat_id, "HALE-YODA")
            return

        # Model override
        model = SONNET_MODEL
        if text.upper().startswith("OPUS:"):
            model = OPUS_MODEL
            text  = text[5:].strip()
        elif text.upper().startswith("SONNET:"):
            model = SONNET_MODEL
            text  = text[7:].strip()

        # Typing indicator
        tg(TOKEN_HALUYODA, "sendChatAction", chat_id=chat_id, action="typing")

        ctx_text = format_context_for_prompt(CTX_HALUYODA)
        prompt = (
            f"{HALE_SYSTEM}\n\n"
            f"--- ROLLING CONTEXT (last {MAX_CTX_TURNS} exchanges) ---\n"
            f"{ctx_text}\n"
            f"--- END CONTEXT ---\n\n"
            f"Commander: {text}\n\n"
            "Respond as Col Victoria \"Iron Vic\" Hale. Open with 🦅. "
            "Brief-first. Execute-then-report posture. No preamble. No trailing summary."
        )

        response = call_claude_engine(prompt, model=model)

        # WF-17 detection — add approval buttons if draft surfaced
        wf17_triggers = ["draft_id:", "approve this", "wf-17"]
        if any(k in response.lower() for k in wf17_triggers):
            # Extract draft_id if present (TODO: wire full WF-17 approval flow)
            draft_id_match = re.search(r"draft_id:\s*(\S+)", response, re.IGNORECASE)
            if draft_id_match:
                draft_id = draft_id_match.group(1)
                buttons = [
                    [{"text": "✅ Approve", "callback_data": f"approve:{draft_id}"}],
                    [{"text": "✏️ Edit in Gmail", "callback_data": f"edit:{draft_id}"},
                     {"text": "❌ Reject", "callback_data": f"reject:{draft_id}"}],
                ]
                tg_send_with_keyboard(TOKEN_HALUYODA, chat_id, response, buttons)
            else:
                tg_send_chunked(TOKEN_HALUYODA, chat_id, response)
        else:
            tg_send_chunked(TOKEN_HALUYODA, chat_id, response)

        append_exchange(CTX_HALUYODA, text, response)
        clear_strikes()

    except Exception:
        log.exception("process_haluyoda_message crashed")


def process_staff_message(update: dict) -> None:
    """Process incoming message for HALE_D2M staff channel bot."""
    try:
        msg = update.get("message") or update.get("edited_message")
        if not msg:
            return

        chat_id = msg["chat"]["id"]
        user_id = msg["from"]["id"]
        text    = msg.get("text", "").strip()

        if not text:
            return

        if user_id != COMMANDER_ID:
            # Staff channel: Commander + AI staff personas only
            return

        # Slash commands
        if text == "/new":
            clear_context(CTX_STAFF)
            tg_send(TOKEN_STAFF, chat_id, "🦅 Staff context cleared.")
            return
        if text == "/status":
            _handle_status(TOKEN_STAFF, chat_id)
            return
        if text == "/help":
            _handle_help(TOKEN_STAFF, chat_id, "HALE_D2M Staff")
            return

        # Parse slash command for persona routing
        persona_key = "hale"
        if text.startswith("/"):
            parts    = text.split(" ", 1)
            cmd      = parts[0][1:].lower()
            if cmd in STAFF_PERSONAS:
                persona_key = cmd
                text = parts[1].strip() if len(parts) > 1 else ""
                if not text:
                    tg_send(TOKEN_STAFF, chat_id,
                            f"Usage: /{persona_key} [your message]")
                    return

        persona_name, engine = STAFF_PERSONAS[persona_key]

        tg(TOKEN_STAFF, "sendChatAction", chat_id=chat_id, action="typing")

        system = (
            f"{STAFF_INTRO_TXT}\n\n"
            f"You are {persona_name} of the Thunderbird Wing, "
            f"Dreams2Memories Travel, LLC.\n\n"
            f"{STAFF_DISAGREE_DIRECTIVE}\n\n"
            "Respond in your persona's voice. Be brief. Lead with the answer. "
            "Commander's context is the Wing operation."
        )
        ctx_text = format_context_for_prompt(CTX_STAFF)
        user_input = f"{ctx_text}\n\nCommander: {text}" if ctx_text != "[No prior context]" else f"Commander: {text}"

        if engine == "claude":
            prompt   = f"{system}\n\n{user_input}"
            response = call_claude_engine(prompt)
        else:
            response = call_opencode_engine(system, user_input)

        header  = f"<b>{persona_name}</b>"
        payload = f"{header}\n\n{response}"
        tg_send_chunked(TOKEN_STAFF, chat_id, payload)
        append_exchange(CTX_STAFF, text, f"[{persona_name}] {response}")

    except Exception:
        log.exception("process_staff_message crashed")


def process_channels_message(update: dict) -> None:
    """Process d2m_channels bot — receive-only, log only."""
    try:
        msg = update.get("message") or update.get("channel_post")
        if not msg:
            return
        text    = msg.get("text", "")[:200]
        chat_id = msg.get("chat", {}).get("id", "?")
        log.info("[channels] chat=%s: %s", chat_id, text)
    except Exception:
        log.exception("process_channels_message crashed")


# ─────────────────────────────────────────────────────────────────────────────
# SLASH COMMAND HANDLERS (shared)
# ─────────────────────────────────────────────────────────────────────────────

def _handle_status(token: str, chat_id: int) -> None:
    state_path = THUNDERBIRD / "hale_state.json"
    try:
        state = json.loads(state_path.read_text())
        mode  = state.get("system_mode", "UNKNOWN")
        tasks = len(state.get("open_tasks", []))
        fin   = state.get("financial_pulse", {})
        pipeline = fin.get("total_d2m_pipeline", 0)
        strikes  = get_strike_count()
        text = (
            f"{format_brief_header('WING STATUS')}\n\n"
            f"<b>Mode:</b> {mode}\n"
            f"<b>Open Tasks:</b> {tasks}\n"
            f"<b>Pipeline:</b> ${pipeline:,.2f}\n"
            f"<b>Strikes:</b> {strikes}/3\n"
        )
        tg_send(token, chat_id, text)
    except Exception as e:
        tg_send(token, chat_id, f"⚠️ Status unavailable: {e}")


def _handle_help(token: str, chat_id: int, bot_name: str) -> None:
    lines = [
        f"<b>{bot_name} — Available Commands</b>",
        "",
        "/new — Clear context, fresh session",
        "/status — Wing health + financial pulse",
        "/help — This message",
        "",
    ]
    if "HALE-YODA" in bot_name:
        lines += [
            "<b>Model Overrides:</b>",
            "OPUS: [task] — Route to Claude Opus",
            "Sonnet: [task] — Route to Claude Sonnet (default)",
        ]
    if "Staff" in bot_name:
        lines += [
            "<b>Persona Routing:</b>",
            "/" + " | /".join(STAFF_PERSONAS.keys()),
        ]
    tg_send(token, chat_id, "\n".join(lines))


# ─────────────────────────────────────────────────────────────────────────────
# FLASK ROUTES
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/hale-yoda", methods=["POST"])
def webhook_haluyoda():
    if not _validate_webhook_secret():
        return "Forbidden", 403
    update = request.get_json(silent=True) or {}
    t = threading.Thread(target=process_haluyoda_message, args=(update,), daemon=True)
    t.start()
    return jsonify({"ok": True}), 200


@app.route("/staff", methods=["POST"])
def webhook_staff():
    if not _validate_webhook_secret():
        return "Forbidden", 403
    update = request.get_json(silent=True) or {}
    t = threading.Thread(target=process_staff_message, args=(update,), daemon=True)
    t.start()
    return jsonify({"ok": True}), 200


@app.route("/channels", methods=["POST"])
def webhook_channels():
    if not _validate_webhook_secret():
        return "Forbidden", 403
    update = request.get_json(silent=True) or {}
    t = threading.Thread(target=process_channels_message, args=(update,), daemon=True)
    t.start()
    return jsonify({"ok": True}), 200


@app.route("/callback", methods=["POST"])
def webhook_callback():
    """Handle inline keyboard callback queries for all bots."""
    if not _validate_webhook_secret():
        return "Forbidden", 403

    update = request.get_json(silent=True) or {}
    cbq    = update.get("callback_query")
    if not cbq:
        return jsonify({"ok": True}), 200

    cbq_id   = cbq["id"]
    user_id  = cbq["from"]["id"]
    data     = cbq.get("data", "")
    chat_id  = cbq.get("message", {}).get("chat", {}).get("id")

    # Answer immediately — clears Telegram spinner
    # Determine token from message source (best-effort)
    token = TOKEN_HALUYODA or TOKEN_STAFF
    tg_answer_callback(token, cbq_id, text="Processing...")

    def _handle_callback():
        try:
            if not data or not chat_id:
                return
            if user_id != COMMANDER_ID:
                tg_send(token, chat_id, "⚠️ Callback restricted to Commander.")
                return

            action, _, payload = data.partition(":")
            if action == "approve":
                # WF-17 approve flow — delegate to publish_draft if available
                try:
                    from thunderbird_gmail import publish_draft  # type: ignore
                    result_msg = publish_draft(payload)
                    tg_send(token, chat_id,
                            f"✅ Draft <code>{payload}</code> approved and sent.\n{result_msg}")
                except ImportError:
                    tg_send(token, chat_id,
                            f"✅ Approval recorded for <code>{payload}</code>. "
                            "Run /approve in Claude Code to complete send.")
            elif action == "reject":
                tg_send(token, chat_id, f"❌ Draft <code>{payload}</code> rejected.")
            elif action == "edit":
                tg_send(token, chat_id,
                        f"✏️ Open Gmail drafts to edit <code>{payload}</code>. "
                        "Reply here when ready to approve.")
            else:
                tg_send(token, chat_id, f"Unknown action: <code>{data}</code>")
        except Exception:
            log.exception("_handle_callback crashed for data=%s", data)

    threading.Thread(target=_handle_callback, daemon=True).start()
    return jsonify({"ok": True}), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "gateway": "thunderbird-telegram-webhook-v2",
        "version": "2.0.0",
        "strikes": get_strike_count(),
        "bots": {
            "hale_yoda": bool(TOKEN_HALUYODA),
            "staff":     bool(TOKEN_STAFF),
            "channels":  bool(TOKEN_CHANNELS),
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


# ─────────────────────────────────────────────────────────────────────────────
# WEBHOOK REGISTRATION
# ─────────────────────────────────────────────────────────────────────────────

def register_webhooks() -> None:
    """Call Telegram setWebhook for each bot. Run once via WEBHOOK_AUTO_REGISTER=1."""
    base_url = os.environ.get("WEBHOOK_BASE_URL", "https://tg.d2mluxury.quest")
    bots = [
        (TOKEN_HALUYODA, "/hale-yoda", "HALE-YODA"),
        (TOKEN_STAFF,    "/staff",     "Staff"),
        (TOKEN_CHANNELS, "/channels",  "Channels"),
    ]
    for token, path, name in bots:
        if not token:
            log.warning("[%s] Token not set — skipping webhook registration", name)
            continue
        url = f"{base_url}{path}"
        payload = {"url": url, "drop_pending_updates": True}
        if WEBHOOK_SECRET:
            payload["secret_token"] = WEBHOOK_SECRET
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/setWebhook",
            json=payload, timeout=15,
        )
        data = resp.json()
        if data.get("ok"):
            log.info("[%s] Webhook registered → %s", name, url)
        else:
            log.error("[%s] Webhook registration failed: %s", name, data)


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    _load_personas()
    if os.environ.get("WEBHOOK_AUTO_REGISTER", "0") == "1":
        register_webhooks()
    log.info("Telegram Webhook Gateway v2 starting on port %d", PORT)
    log.info("Bots: HALE-YODA=%s, Staff=%s, Channels=%s",
             bool(TOKEN_HALUYODA), bool(TOKEN_STAFF), bool(TOKEN_CHANNELS))
    app.run(host="0.0.0.0", port=PORT, debug=False, threaded=True)
