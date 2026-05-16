"""
thunderbird_telegram_webhook.py — Thunderbird Telegram Webhook Gateway v2
Dreams2Memories Travel, LLC | 2026-05-16

Bots: HALE-YODA (/hale-yoda, Claude), HALE_D2M (/staff, personas), d2m_channels (/channels)
Cloudflare tunnel: tg.d2mluxury.quest → localhost:8768

ARCH: setWebhook is ONE URL per bot. All update types (message, callback_query) for
a bot arrive at that bot's route. Callback dispatch is colocated in each process_* fn.
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

import requests
from flask import Flask, jsonify, request

logging.basicConfig(level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()])
log = logging.getLogger("tg_webhook")

THUNDERBIRD = Path("/home/john/Thunderbird")
OPS         = THUNDERBIRD / "OpsCenter"
PERSONAS    = THUNDERBIRD / "Personas"

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

PORT             = 8769  # 8768 occupied by travel_mcp_server.py
WEBHOOK_SECRET   = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
TOKEN_HALUYODA   = os.environ.get("TELEGRAM_D2MC2C_TOKEN", "")   # reuse existing var
TOKEN_STAFF      = os.environ.get("TELEGRAM_GOOSE_TOKEN", "")    # reuse existing var
TOKEN_CHANNELS   = os.environ.get("TELEGRAM_DANI_TOKEN", "")     # reuse existing var
COMMANDER_ID     = int(os.environ.get("TELEGRAM_COMMANDER_ID", "7554895206"))
SONNET_MODEL     = "claude-sonnet-4-6"
OPUS_MODEL       = "claude-opus-4-6"
ENGINE_TIMEOUT   = int(os.environ.get("TELEGRAM_GW_TIMEOUT", "300"))
OPENCODE_TIMEOUT = int(os.environ.get("OPENCODE_TIMEOUT", "60"))
MAX_CTX_TURNS    = 12
CHUNK_SIZE       = 4000
OPENCODE_BIN     = Path("/home/john/.opencode/bin/opencode")

# Webhook secret: if unset, log a warning and allow through. A 403 on empty
# secret would silently brick the gateway during initial deployment.
if not WEBHOOK_SECRET:
    log.warning("TELEGRAM_WEBHOOK_SECRET not set — webhook auth disabled. Set it!")

CTX_HALUYODA = OPS / "context_haluyoda.json"
CTX_STAFF    = OPS / "context_staff.json"
STRIKE_FILE  = OPS / "telegram_strike_counter.json"

HALE_SYSTEM     = ""
STAFF_INTRO_TXT = ""

OPENCODE_MODEL_CHAIN = [
    "opencode/big-pickle",              # OpenCode native (zen/ prefix = TUI only; opencode/ = headless)
    "opencode/deepseek-v4-flash-free",  # OpenCode native fallback
    "google/gemini-2.5-flash",          # Non-OpenCode last resort
]
_OC_RATE_MARKERS = ["rate limit", "rate-limit", "too many requests", "429"]

app = Flask(__name__)

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
    try:
        from thunderbird_gmail import gmail_send_from_wing  # type: ignore
        gmail_send_from_wing(to="johnloucks3@gmail.com",
            subject="Thunderbird Telegram — 3 Strikes: Signal Migration Required",
            body="Commander,\n\nHALE-YODA gateway hit 3 strikes. "
                 "Recommend Signal migration or webhook redeploy.\n\n"
                 "Check: OpsCenter/telegram_strike_counter.json\n\n— Iron Vic")
    except Exception as e:
        log.error("Could not send Signal migration notice: %s", e)

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

def _load_personas() -> None:
    global HALE_SYSTEM, STAFF_INTRO_TXT
    hale_cos_path    = PERSONAS / "hale_cos.md"
    staff_intro_path = PERSONAS / "D2M_Staff_Introduction.md"
    hale_state_path  = THUNDERBIRD / "hale_state.json"

    if hale_cos_path.exists():
        HALE_SYSTEM = hale_cos_path.read_text()[:6000]
    if staff_intro_path.exists():
        STAFF_INTRO_TXT = staff_intro_path.read_text()[:3000]

    # Append live state summary (mode + open tasks only — no PII)
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

def call_claude_engine(prompt: str, model: str = SONNET_MODEL) -> str:
    """Claude headless via `claude -p`. Strips ANTHROPIC_API_KEY; uses Max OAuth."""
    env = dict(os.environ)
    env.pop("ANTHROPIC_API_KEY", None)   # Strip stale API key — it overrides OAuth
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
    """OpenCode headless. Chain: zen/big-pickle → zen/deepseek-v4-flash-free → gemini-2.5-flash."""
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
        return choices[0].get("message", {}).get("content", "").strip() if choices else f"[{model} returned empty response]"
    except requests.Timeout:
        return f"[{model} timed out after {ENGINE_TIMEOUT}s]"
    except Exception as e:
        return f"[Engine error — {model}: {e}]"

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

def _balance_html_tags(text: str) -> str:
    """Close unclosed <b>/<i>/<code>/<pre> tags at chunk boundary."""
    open_tags  = re.findall(r"<(b|i|code|pre)>", text)
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
                for i in range(0, len(para), CHUNK_SIZE):
                    chunks.append(para[i:i + CHUNK_SIZE])
                current = ""
            else:
                current = para
    if current:
        chunks.append(current)
    total = len(chunks)
    for idx, chunk in enumerate(chunks, 1):
        prefix  = f"[{idx}/{total}] " if total > 1 else ""
        payload = prefix + (_balance_html_tags(chunk) if parse_mode == "HTML" else chunk)
        tg_send(token, chat_id, payload, parse_mode)
        if idx < total:
            time.sleep(0.3)

def format_brief_header(title: str, emoji: str = "🦅") -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M MT")
    return f"{emoji} <b>{title.upper()}</b> | <i>{now}</i>"

def format_section(title: str, content: str, emoji: str = "") -> str:
    prefix = f"{emoji} " if emoji else ""
    return f"<b>{prefix}{title}</b>\n{content}\n"

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

def _validate_webhook_secret() -> bool:
    if not WEBHOOK_SECRET:
        return True  # Secret disabled — allow through (warning logged at startup)
    return request.headers.get("X-Telegram-Bot-Api-Secret-Token", "") == WEBHOOK_SECRET

def _handle_status(token: str, chat_id: int) -> None:
    state_path = THUNDERBIRD / "hale_state.json"
    try:
        state    = json.loads(state_path.read_text())
        mode     = state.get("system_mode", "UNKNOWN")
        tasks    = len(state.get("open_tasks", []))
        pipeline = state.get("financial_pulse", {}).get("total_d2m_pipeline", 0)
        text = (
            f"{format_brief_header('WING STATUS')}\n\n"
            f"<b>Mode:</b> {mode}\n"
            f"<b>Open Tasks:</b> {tasks}\n"
            f"<b>Pipeline:</b> ${pipeline:,.2f}\n"
            f"<b>Strikes:</b> {get_strike_count()}/3\n"
        )
        tg_send(token, chat_id, text)
    except Exception as e:
        tg_send(token, chat_id, f"Status unavailable: {e}")

def _handle_help(token: str, chat_id: int, bot_name: str) -> None:
    lines = [
        f"<b>{bot_name} — Available Commands</b>", "",
        "/new — Clear context, fresh session",
        "/status — Wing health + financial pulse",
        "/help — This message", "",
    ]
    if "HALE-YODA" in bot_name:
        lines += ["<b>Model Overrides:</b>",
                  "OPUS: [task] — Route to Claude Opus",
                  "Sonnet: [task] — Route to Claude Sonnet (default)"]
    if "Staff" in bot_name:
        lines += ["<b>Persona Routing:</b>",
                  "/" + " | /".join(STAFF_PERSONAS.keys())]
    tg_send(token, chat_id, "\n".join(lines))

def _handle_callback_query(token: str, cbq: dict) -> None:
    """WF-17 inline keyboard. tg_answer_callback fires sync; heavy work in thread."""
    cbq_id  = cbq["id"]
    user_id = cbq["from"]["id"]
    data    = cbq.get("data", "")
    chat_id = cbq.get("message", {}).get("chat", {}).get("id")

    # Answer immediately — clears Telegram spinner
    tg_answer_callback(token, cbq_id, text="Processing...")

    def _process() -> None:
        try:
            if not data or not chat_id:
                return
            if user_id != COMMANDER_ID:
                tg_send(token, chat_id, "Callback restricted to Commander.")
                return
            action, _, payload = data.partition(":")
            if action == "approve":
                try:
                    from thunderbird_gmail import publish_draft  # type: ignore
                    result_msg = publish_draft(payload)
                    tg_send(token, chat_id,
                            f"Draft <code>{payload}</code> approved and sent.\n{result_msg}")
                except ImportError:
                    tg_send(token, chat_id,
                            f"Approval recorded for <code>{payload}</code>. "
                            "Run /approve in Claude Code to complete send.")
            elif action == "reject":
                tg_send(token, chat_id, f"Draft <code>{payload}</code> rejected.")
            elif action == "edit":
                tg_send(token, chat_id,
                        f"Open Gmail drafts to edit <code>{payload}</code>. "
                        "Reply here when ready to approve.")
            else:
                tg_send(token, chat_id, f"Unknown action: <code>{data}</code>")
        except Exception:
            log.exception("_handle_callback_query._process crashed for data=%s", data)

    threading.Thread(target=_process, daemon=True).start()

def process_haluyoda_message(update: dict) -> None:
    """HALE-YODA: handles message, edited_message, callback_query (all at /hale-yoda)."""
    try:
        cbq = update.get("callback_query")
        if cbq:
            _handle_callback_query(TOKEN_HALUYODA, cbq)
            return
        msg = update.get("message") or update.get("edited_message")
        if not msg:
            return
        chat_id = msg["chat"]["id"]
        user_id = msg["from"]["id"]
        text    = msg.get("text", "").strip()
        if not text:
            return
        if user_id != COMMANDER_ID:
            tg_send(TOKEN_HALUYODA, chat_id, "HALE-YODA is Commander-only.")
            return
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
        model = SONNET_MODEL
        if text.upper().startswith("OPUS:"):
            model = OPUS_MODEL
            text  = text[5:].strip()
        elif text.upper().startswith("SONNET:"):
            model = SONNET_MODEL
            text  = text[7:].strip()

        tg(TOKEN_HALUYODA, "sendChatAction", chat_id=chat_id, action="typing")

        ctx_text = format_context_for_prompt(CTX_HALUYODA)
        prompt = (
            f"{HALE_SYSTEM}\n\n"
            f"--- ROLLING CONTEXT (last {MAX_CTX_TURNS} exchanges) ---\n"
            f"{ctx_text}\n"
            f"--- END CONTEXT ---\n\n"
            f"Commander: {text}\n\n"
            'Respond as Col Victoria "Iron Vic" Hale. Open with 🦅. '
            "Brief-first. Execute-then-report posture. No preamble. No trailing summary."
        )

        response = call_claude_engine(prompt, model=model)

        if any(k in response.lower() for k in ["draft_id:", "approve this", "wf-17"]):
            m = re.search(r"draft_id:\s*(\S+)", response, re.IGNORECASE)
            if m:
                draft_id = m.group(1)
                buttons = [
                    [{"text": "Approve", "callback_data": f"approve:{draft_id}"}],
                    [{"text": "Edit in Gmail", "callback_data": f"edit:{draft_id}"},
                     {"text": "Reject", "callback_data": f"reject:{draft_id}"}],
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
    """HALE_D2M: handles message, edited_message, callback_query (all at /staff)."""
    try:
        cbq = update.get("callback_query")
        if cbq:
            _handle_callback_query(TOKEN_STAFF, cbq)
            return
        msg = update.get("message") or update.get("edited_message")
        if not msg:
            return
        chat_id = msg["chat"]["id"]
        user_id = msg["from"]["id"]
        text    = msg.get("text", "").strip()
        if not text:
            return
        if user_id != COMMANDER_ID:
            return
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
        persona_key = "hale"
        if text.startswith("/"):
            parts = text.split(" ", 1)
            cmd   = parts[0][1:].lower()
            if cmd in STAFF_PERSONAS:
                persona_key = cmd
                text = parts[1].strip() if len(parts) > 1 else ""
                if not text:
                    tg_send(TOKEN_STAFF, chat_id, f"Usage: /{persona_key} [your message]")
                    return

        persona_name, engine = STAFF_PERSONAS[persona_key]

        tg(TOKEN_STAFF, "sendChatAction", chat_id=chat_id, action="typing")

        system = (
            f"{STAFF_INTRO_TXT}\n\n"
            f"You are {persona_name} of the Thunderbird Wing, "
            f"Dreams2Memories Travel, LLC.\n\n"
            f"{STAFF_DISAGREE_DIRECTIVE}\n\n"
            "Respond in your persona's voice. Be brief. Lead with the answer."
        )
        ctx_text   = format_context_for_prompt(CTX_STAFF)
        user_input = (f"{ctx_text}\n\nCommander: {text}"
                      if ctx_text != "[No prior context]" else f"Commander: {text}")

        response = (call_claude_engine(f"{system}\n\n{user_input}")
                    if engine == "claude"
                    else call_opencode_engine(system, user_input))

        tg_send_chunked(TOKEN_STAFF, chat_id, f"<b>{persona_name}</b>\n\n{response}")
        append_exchange(CTX_STAFF, text, f"[{persona_name}] {response}")

    except Exception:
        log.exception("process_staff_message crashed")

def process_channels_message(update: dict) -> None:
    """d2m_channels bot — receive-only, log only."""
    try:
        msg = update.get("message") or update.get("channel_post")
        if not msg:
            return
        log.info("[channels] chat=%s: %s",
                 msg.get("chat", {}).get("id", "?"),
                 msg.get("text", "")[:200])
    except Exception:
        log.exception("process_channels_message crashed")

@app.route("/hale-yoda", methods=["POST"])
def webhook_haluyoda():
    """All HALE-YODA updates (messages + callback_query) arrive here."""
    if not _validate_webhook_secret():
        return "Forbidden", 403
    update = request.get_json(silent=True) or {}
    # callback_query: answer_callback must fire sync to clear Telegram's spinner.
    # process_haluyoda_message handles this — it answers sync then spawns the thread.
    if update.get("callback_query"):
        process_haluyoda_message(update)
    else:
        threading.Thread(target=process_haluyoda_message, args=(update,), daemon=True).start()
    return jsonify({"ok": True}), 200

@app.route("/staff", methods=["POST"])
def webhook_staff():
    """All HALE_D2M updates (messages + callback_query) arrive here."""
    if not _validate_webhook_secret():
        return "Forbidden", 403
    update = request.get_json(silent=True) or {}
    if update.get("callback_query"):
        process_staff_message(update)
    else:
        threading.Thread(target=process_staff_message, args=(update,), daemon=True).start()
    return jsonify({"ok": True}), 200

@app.route("/channels", methods=["POST"])
def webhook_channels():
    if not _validate_webhook_secret():
        return "Forbidden", 403
    update = request.get_json(silent=True) or {}
    threading.Thread(target=process_channels_message, args=(update,), daemon=True).start()
    return jsonify({"ok": True}), 200

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "gateway": "thunderbird-telegram-webhook-v2",
        "version": "2.0.1",
        "strikes": get_strike_count(),
        "bots": {
            "hale_yoda": bool(TOKEN_HALUYODA),
            "staff":     bool(TOKEN_STAFF),
            "channels":  bool(TOKEN_CHANNELS),
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

def register_webhooks() -> None:
    """setWebhook for each bot. Run once via WEBHOOK_AUTO_REGISTER=1."""
    base_url = os.environ.get("WEBHOOK_BASE_URL", "https://tg.d2mluxury.quest")
    for token, path, name in [(TOKEN_HALUYODA, "/hale-yoda", "HALE-YODA"),
                               (TOKEN_STAFF,    "/staff",     "Staff"),
                               (TOKEN_CHANNELS, "/channels",  "Channels")]:
        if not token:
            log.warning("[%s] Token not set — skipping webhook registration", name)
            continue
        payload = {
            "url": f"{base_url}{path}",
            "drop_pending_updates": True,
            "allowed_updates": ["message", "edited_message", "callback_query"],
        }
        if WEBHOOK_SECRET:
            payload["secret_token"] = WEBHOOK_SECRET
        data = requests.post(f"https://api.telegram.org/bot{token}/setWebhook",
                             json=payload, timeout=15).json()
        if data.get("ok"):
            log.info("[%s] Webhook registered → %s%s", name, base_url, path)
        else:
            log.error("[%s] Registration failed: %s", name, data)

if __name__ == "__main__":
    _load_personas()
    if os.environ.get("WEBHOOK_AUTO_REGISTER", "0") == "1":
        register_webhooks()
    log.info("Telegram Webhook Gateway v2 starting on port %d", PORT)
    log.info("Bots: HALE-YODA=%s, Staff=%s, Channels=%s",
             bool(TOKEN_HALUYODA), bool(TOKEN_STAFF), bool(TOKEN_CHANNELS))
    app.run(host="0.0.0.0", port=PORT, debug=False, threaded=True)
