#!/usr/bin/env python3
"""
thunderbird_telegram_gw.py — Thunderbird Telegram Gateway
Dreams2Memories Travel, LLC
Version: 1.0 | 2026-04-04

⚠️ COST NOTE (2026-05-04): Primary model is Gemini 3.1 Flash Lite (confirmed cheapest per invoice).
DeepSeek V4 Pro is BLOCKED — it was the expensive outlier on 2026-04-30 ($0.03–$2.83/gen).
DeepSeek V3.1 was NOT the expensive item. V4 Pro was. V4 Pro cannot be auto-selected.

Three bots. One process. Clean output.

Bot         Token prefix  Engine         Identity     Audience
─────────────────────────────────────────────────────────────
D2MC2C      8754681793    Claude -p      Hale (COS)   Commander only
Dani        8723918695    Claude -p      Dani Moreau  Clients + Commander

Message Flow:
  Commander → Telegram → getUpdates poll (3 tokens, threaded)
      → COMMANDER_ID whitelist check
      → typing... indicator
      → load rolling context (last 10 turns)
      → invoke engine (Claude or OpenCode headless)
      → Formatter Pipeline (5 stages)
      → send clean chunks (0.5s gap)
      → append exchange to rolling context file

Slash commands (all bots):
    /new     — clear context, fresh session
    /status  — wing health + last activity
    /help    — show available commands

Telegram overrides (D2MC2C only):
    OPUS: [task]   → route to claude-opus-4-6
    Sonnet: [task] → route to claude-sonnet-4-6

Model prefixes (any bot — direct OpenRouter):
    GROK: [task]     → xAI Grok 4.1 Fast (~$0.20/M)
    DEEPSEEK: [task] → DeepSeek V4 Pro (~$0.305/M — cost-optimized reasoning)
    GEMINI: [task]   → Gemini 3.1 Flash Lite (~$0.25/M)
    LLAMA: [task]    → Llama 4 Maverick (~$0.15/M)
    GPT: [task]      → GPT-4.1 Mini (~$0.40/M)
    HAIKU: [task]    → Claude Haiku 4.5 (free on Max plan)
    MISTRAL: [task]  → Mistral Small (~$0.05/M — cheapest option)

Both Ways auto-upgrade:
    Keywords (strategy, architect, draft, etc.) auto-route to Opus/Sonnet.
"""

import json
import logging
import os
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import requests

# ── Add Thunderbird root to path ──────────────────────────────────────────────
sys.path.insert(0, "/home/john/Thunderbird")
sys.path.insert(0, "/home/john/Thunderbird/OpsCenter")
sys.path.insert(0, "/home/john/Thunderbird/core/email")

from thunderbird_tg_formatter import process as fmt_process
from keyword_router import classify_task, CLAUDE_KEYWORD_PATTERN
from thunderbird_gmail import publish_draft, _get_draft_metadata
from thunderbird_stt import transcribe_audio
from thunderbird_tts import synthesize_speech

# ── Hale Dispatcher integration (Hale Everywhere — Phase 2 hook) ──────────────
# Defensive: gateway must keep running even if Hale infra fails to import.
try:
    from telegram_hale_router import (
        should_use_hale,
        get_hale_response,
        dispatch_status_text,
        savings_text,
        record_turn as hale_record_turn,
        check_correction as hale_check_correction,
    )
    _HALE_DISPATCHER_AVAILABLE = True
except Exception as _hale_import_err:
    _HALE_DISPATCHER_AVAILABLE = False
    _HALE_IMPORT_ERR = _hale_import_err

# Disabled: synchronous spawn_headless_claude(timeout=180) blocks the poll thread for
# 3 minutes on every Sonnet-tier message, then returns a FALLBACK PLACEHOLDER string.
_HALE_DISPATCHER_AVAILABLE = False

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger("tg_gw")

# ── Paths ─────────────────────────────────────────────────────────────────────
THUNDERBIRD = Path("/home/john/Thunderbird")
OPS = THUNDERBIRD / "OpsCenter"
PERSONAS = THUNDERBIRD / "Personas"

HALE_COS = THUNDERBIRD / "Personas" / "hale_cos.md"
HALE_INIT = THUNDERBIRD / "hale_init.md"
HALE_MEMORY = THUNDERBIRD / "hale_memory.md"
HALE_BRIEF = THUNDERBIRD / "hale_brief.md"
STAFF_INTRO = PERSONAS / "D2M_Staff_Introduction.md"

CTX_D2MC2C = OPS / "context_d2mc2c.json"
CTX_OPENCODE = OPS / "context_opencode.json"
CTX_DANI = OPS / "context_dani.json"


# ── Config from env ───────────────────────────────────────────────────────────
def _load_env_file(path: str) -> None:
    """Load KEY=VALUE pairs from a file into os.environ."""
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip())
    except FileNotFoundError:
        pass


_load_env_file("/home/john/Thunderbird/.env")
_load_env_file("/home/john/Thunderbird/config/telegram_gw.env")

TOKEN_D2MC2C = os.environ.get("TELEGRAM_D2MC2C_TOKEN", "")
TOKEN_DANI = os.environ.get("TELEGRAM_DANI_TOKEN", "")
COMMANDER_ID = int(os.environ.get("TELEGRAM_COMMANDER_ID", "7554895206"))
POLL_INTERVAL = float(os.environ.get("TELEGRAM_GW_POLL_INTERVAL", "2"))
ENGINE_TIMEOUT = int(os.environ.get("TELEGRAM_GW_TIMEOUT", "180"))
CHUNK_SIZE = int(os.environ.get("TELEGRAM_GW_CHUNK_SIZE", "4000"))
CONTEXT_TURNS = int(os.environ.get("TELEGRAM_GW_CONTEXT_TURNS", "10"))

SONNET_MODEL = "claude-sonnet-4-6"
OPUS_MODEL = "claude-opus-4-6"
HAIKU_MODEL = "claude-haiku-4-5"
OPENCODE_BIN = Path("/home/john/.opencode/bin/opencode")

# ── OpenRouter model aliases — prefix routing (e.g. "GROK: task") ────────────
# Maps short prefix → OpenRouter model ID.  Used by model override detection
# and keyword-based Both Ways routing.
# Synced with scripts/openrouter_call.py — 2026-04-17
OPENROUTER_MODEL_ALIASES: dict[str, str] = {
    # ── FREE ──────────────────────────────────────────────────────────────────
    "NEMOTRON":         "nvidia/nemotron-nano-9b-v2:free",            # 9B, free tier (120B deprecated)
    "GPTOSS":           "openai/gpt-oss-20b:free",                   # 20B, free tier
    "ELEPHANT":         "openrouter/elephant-alpha",                  # 262K ctx, FREE
    # ── ULTRA-CHEAP (<$0.15/M) ────────────────────────────────────────────────
    "QWEN":             "qwen/qwen3-235b-a22b-2507",                 # 235B, $0.07/M
    "GPTNANO":          "openai/gpt-4.1-nano",                       # 1M ctx, $0.10/M
    "GEMLITE":          "google/gemini-2.5-flash-lite",              # 1M ctx, $0.10/M
    "LLAMA":            "meta-llama/llama-4-maverick",               # 1M ctx, $0.15/M
    "DEEPSEEK":         "deepseek/deepseek-chat-v3.1",                  # DeepSeek V3.1 via OpenRouter, ~$0.27/M
    "QWQ":              "qwen/qwq-32b",                              # reasoning, $0.15/M
    # ── VALUE ($0.15–$0.50/M) ────────────────────────────────────────────────
    "GROK":             "x-ai/grok-4.1-fast",                        # 2M ctx, $0.20/M
    "GEMINI":           "google/gemini-3.1-flash-lite-preview",      # 1M ctx, $0.25/M
    "DEEPSEEKV32":      "deepseek/deepseek-v3.2",                    # $0.26/M
    "GPT5MINI":         "openai/gpt-5-mini",                         # 400K ctx, $0.25/M
    "GPT":              "openai/gpt-4.1-mini",                       # 1M ctx, $0.40/M
    "MISTRAL":          "mistralai/mistral-small-3.2-24b-instruct",  # 128K ctx, $0.07/M
    # ── REASONING ─────────────────────────────────────────────────────────────
    "R1":               "deepseek/deepseek-r1-0528",                 # CoT, $0.50/M
    # ── PREMIUM ───────────────────────────────────────────────────────────────
    "PERPLEXITY":       "perplexity/sonar-reasoning-pro",            # web search, $2/M
    "HAIKU":            "anthropic/claude-haiku-4.5",                # $1/M
}

# Reverse: OpenRouter model ID → short display label
_OR_DISPLAY_LABELS = {v: k.title() for k, v in OPENROUTER_MODEL_ALIASES.items()}

# Gemini-first chain (Opus plan 2026-05-04 — confirmed by invoice analysis)
# Invoice confirmed: Gemini 3.1 Flash Lite = $0.005–$0.01/gen NET after cache credits.
# V4 Pro was the expensive outlier (April 30). V4 Pro is blocked in override detection.
# Chain: Gemini Flash Lite → Gemini Flash → FREE tier → Qwen3 free → Mistral cheap
OPENCODE_MODEL_CHAIN = [
    "openrouter/google/gemini-2.5-flash-lite",                   # PRIMARY: confirmed working $0.10/M
    "openrouter/deepseek/deepseek-chat-v3.1",                     # DeepSeek V3.1 paid (~$0.27/M)
    "openrouter/nvidia/nemotron-nano-9b-v2:free",                 # FREE tier fallback
    "openrouter/mistralai/mistral-small-3.2-24b-instruct",       # last resort ($0.07/M)
]
_OC_RATE_MARKERS = (
    "rate limit",
    "rate_limit",
    "429",
    "too many requests",
    "quota exceeded",
    "upstream error from venice",  # Venice/Llama upstream throttle
    "venice",  # Venice catch-all
    "provider is currently unavailable",  # Generic upstream down
    "no endpoints available",  # OpenRouter exhausted all providers
    "provider_unavailable",  # DeepSeek 502 JSON error type
    "network connection lost",  # DeepSeek 502 message
    '"code":502',
    "502",
)  # HTTP 502 bad gateway
MCP_HTTP_URL = "http://localhost:8767"

# ── Persona cache (loaded once at startup) ────────────────────────────────────
_PERSONA_CACHE: dict[str, str] = {}
_PERSONA_LOCK = threading.Lock()


def _load_persona_cache() -> None:
    """Pre-load persona files at startup."""
    global _PERSONA_CACHE
    with _PERSONA_LOCK:
        # Hale COS persona (first 5K chars — the authoritative system prompt)
        hale_cos = ""
        if HALE_COS.exists():
            hale_cos = HALE_COS.read_text(encoding="utf-8")[:5000]
        elif HALE_INIT.exists():
            hale_cos = HALE_INIT.read_text(encoding="utf-8")

        # Hale memory (condensed — Commander prefs, standing orders, clients)
        hale_mem = ""
        if HALE_MEMORY.exists():
            hale_mem = HALE_MEMORY.read_text(encoding="utf-8")[:2000]

        _PERSONA_CACHE["hale_system"] = hale_cos
        _PERSONA_CACHE["hale_memory_snippet"] = hale_mem

        # Dani persona — extract her section from Staff Introduction
        dani_text = _extract_dani_persona()
        _PERSONA_CACHE["dani_system"] = dani_text

        log.info(
            "Persona cache loaded: hale=%d chars, dani=%d chars",
            len(_PERSONA_CACHE["hale_system"]),
            len(_PERSONA_CACHE["dani_system"]),
        )


def _extract_dani_persona() -> str:
    """Extract Dani Moreau's section from D2M_Staff_Introduction.md."""
    try:
        text = STAFF_INTRO.read_text(encoding="utf-8")
        # Find Dani section (starts at A3)
        start = text.find("#### A3")
        if start == -1:
            start = text.find("Dani Moreau")
        end = text.find("#### A5", start + 1)
        if start >= 0 and end > start:
            dani_section = text[start:end].strip()
        elif start >= 0:
            dani_section = text[start : start + 2000].strip()
        else:
            dani_section = ""
    except Exception:
        dani_section = ""

    dani_base = """You are Dani Moreau — A3, D2M Luxury Travel Concierge.
Voice: Warm but operationally crisp. You call clients by name, remember details, run the operation with precision.
Role: Aggregator → Artist → Advocate. You gather intel from specialists, craft communications with voice and tone, present as concierge.
Company: Dreams2Memories Travel, LLC (NEVER "Love Group Travel").
Sign-off: "Thanks" or "Thank you" — NEVER "Best."
You do NOT research. You do NOT brief Commander. You do NOT contact suppliers.
Respond warmly, briefly, and with certainty. Mobile-first: ≤4096 chars, scannable.
"""
    return dani_base + ("\n\n" + dani_section[:1500] if dani_section else "")


# ── Rolling Context Management ────────────────────────────────────────────────
_CTX_LOCKS: dict[Path, threading.Lock] = {
    CTX_D2MC2C: threading.Lock(),
    CTX_OPENCODE: threading.Lock(),
    CTX_DANI: threading.Lock(),
}


def _load_context(ctx_file: Path) -> list[dict]:
    """Load context exchanges from JSON file. Returns list of {role, text}."""
    lock = _CTX_LOCKS.get(ctx_file, threading.Lock())
    with lock:
        try:
            if ctx_file.exists():
                return json.loads(ctx_file.read_text(encoding="utf-8"))
        except Exception:
            pass
        return []


def _save_context(ctx_file: Path, exchanges: list[dict]) -> None:
    """Save context exchanges to JSON file."""
    lock = _CTX_LOCKS.get(ctx_file, threading.Lock())
    with lock:
        try:
            ctx_file.write_text(
                json.dumps(exchanges, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            log.error("Context save failed %s: %s", ctx_file.name, e)


def _append_exchange(
    ctx_file: Path,
    user_msg: str,
    assistant_msg: str,
    user_label: str = "Commander",
    assistant_label: str = "Hale",
) -> None:
    """Append a turn to the rolling context, pruning to CONTEXT_TURNS."""
    exchanges = _load_context(ctx_file)
    exchanges.append({"role": user_label, "text": user_msg})
    exchanges.append({"role": assistant_label, "text": assistant_msg})
    # Keep last (CONTEXT_TURNS * 2) entries = last N turns
    max_entries = CONTEXT_TURNS * 2
    if len(exchanges) > max_entries:
        exchanges = exchanges[-max_entries:]
    _save_context(ctx_file, exchanges)


def _format_context(ctx_file: Path) -> str:
    """Format context for injection into prompt."""
    exchanges = _load_context(ctx_file)
    if not exchanges:
        return ""
    lines = ["[RECENT CONVERSATION — last turns]"]
    for ex in exchanges:
        role = ex.get("role", "Unknown")
        text = ex.get("text", "").strip()
        if text:
            # Truncate very long entries
            if len(text) > 500:
                text = text[:500] + "..."
            lines.append(f"{role}: {text}")
    lines.append("[END CONTEXT]")
    return "\n".join(lines)


def _clear_context(ctx_file: Path) -> None:
    """Wipe context file."""
    lock = _CTX_LOCKS.get(ctx_file, threading.Lock())
    with lock:
        try:
            ctx_file.write_text("[]", encoding="utf-8")
        except Exception:
            pass


# ── Telegram API helpers ──────────────────────────────────────────────────────
TG_BASE = "https://api.telegram.org/bot{token}/{method}"


def tg(token: str, method: str, **kwargs) -> dict:
    """Make a Telegram Bot API call. Returns parsed JSON."""
    url = TG_BASE.format(token=token, method=method)
    try:
        r = requests.post(url, json=kwargs, timeout=35)
        data = r.json()
        if not data.get("ok"):
            log.warning("TG API %s error: %s", method, data.get("description", "?"))
        return data
    except Exception as e:
        log.error("TG API %s exception: %s", method, e)
        return {"ok": False, "description": str(e)}


def tg_get_updates(token: str, offset: int) -> list[dict]:
    """Short-poll getUpdates (timeout=0). Returns list of update objects immediately."""
    data = tg(token, "getUpdates", offset=offset, timeout=0, limit=20)
    if data.get("ok"):
        return data.get("result", [])
    return []


def tg_typing(token: str, chat_id: int) -> None:
    """Send typing indicator."""
    tg(token, "sendChatAction", chat_id=chat_id, action="typing")


def tg_send(token: str, chat_id: int, text: str, parse_mode: str = "HTML") -> bool:
    """Send a single message. Returns True on success."""
    # Telegram hard limit
    if len(text) > 4096:
        text = text[:4090] + "\n…"
    data = tg(token, "sendMessage", chat_id=chat_id, text=text, parse_mode=parse_mode)
    return bool(data.get("ok"))


def tg_send_chunks(token: str, chat_id: int, chunks: list[str]) -> None:
    """Send multiple chunks with 0.5s delay, plain-text fallback on error."""
    for chunk in chunks:
        success = tg_send(token, chat_id, chunk, parse_mode="HTML")
        if not success:
            # Fallback: strip HTML tags and send plain
            plain = re.sub(r"<[^>]+>", "", chunk)
            tg_send(token, chat_id, plain, parse_mode=None)
        if len(chunks) > 1:
            time.sleep(0.5)


import re  # noqa: E402 — needed for tg_send_chunks fallback above


# ── Engine: Claude headless ───────────────────────────────────────────────────


def _build_hale_claude_prompt(context_text: str, message: str) -> str:
    """Build the full prompt for Claude/Hale engine."""
    persona = _PERSONA_CACHE.get("hale_system", "")
    memory_snip = _PERSONA_CACHE.get("hale_memory_snippet", "")

    parts = []
    if persona:
        parts.append(persona)
    if memory_snip:
        parts.append(f"\n\n---\n## CURRENT MEMORY SNAPSHOT\n{memory_snip}")
    if context_text:
        parts.append(f"\n\n---\n{context_text}")
    parts.append(f"\n\nCommander: {message}\nHale:")

    return "".join(parts)


def _build_dani_claude_prompt(context_text: str, message: str) -> str:
    """Build the full prompt for Claude/Dani engine."""
    persona = _PERSONA_CACHE.get("dani_system", "")
    parts = []
    if persona:
        parts.append(persona)
    if context_text:
        parts.append(f"\n\n---\n{context_text}")
    parts.append(f"\n\nCommander/Client: {message}\nDani:")
    return "".join(parts)


def call_claude_engine(prompt: str, model: str = SONNET_MODEL) -> str:
    """
    Invoke Claude headless via `claude -p`.
    Uses Max OAuth — injects CLAUDE_CODE_OAUTH_TOKEN from credentials file
    because the systemd service env does not inherit the interactive session token.
    """
    env = dict(os.environ)
    # Strip stale API key — it overrides OAuth and causes "Invalid API key" rc=1.
    # Headless Claude uses OAuth via CLAUDE_CODE_OAUTH_TOKEN exclusively.
    env.pop("ANTHROPIC_API_KEY", None)
    _creds = Path.home() / ".claude" / ".credentials.json"
    if _creds.exists():
        try:
            _tok = json.loads(_creds.read_text()).get("claudeAiOauth", {}).get("accessToken")
            if _tok:
                env["CLAUDE_CODE_OAUTH_TOKEN"] = _tok
        except Exception:
            pass

    try:
        result = subprocess.run(
            [
                "/home/john/.local/bin/claude",
                "--model",
                model,
                "-p",
                prompt,
                "--dangerously-skip-permissions",
            ],
            capture_output=True,
            text=True,
            timeout=ENGINE_TIMEOUT,
            env=env,
            cwd=str(THUNDERBIRD),
        )
        if result.returncode == 0:
            return result.stdout.strip()
        err = result.stderr.strip()
        log.error("Claude headless rc=%d: %s", result.returncode, err[:300])
        return f"[Engine error — Claude rc={result.returncode}]"
    except subprocess.TimeoutExpired:
        return "[Engine timeout — Claude exceeded limit]"
    except FileNotFoundError:
        return "[Engine error — claude binary not found]"
    except Exception as e:
        return f"[Engine error — {e}]"


# ── Engine: OpenCode headless — free-first fallback chain ────────────────────


def call_opencode_engine(
    system_prompt: str, text_prompt: str, use_mcp: bool = True
) -> str:
    """
    Invoke OpenCode headless via `opencode run` with DeepSeek primary + free fallbacks.
    Chain: DeepSeek V3.1 → Nemotron free → Minimax free → Mistral free → DeepSeek R1 free.
    system_prompt: persona/identity instructions (prepended to prompt)
    text_prompt:   context + user message
    use_mcp:       reserved for compat (OpenCode uses .opencode.json MCP config)
    """
    full_prompt = (
        f"{system_prompt[:2000]}\n\n{text_prompt}" if system_prompt else text_prompt
    )

    env = dict(os.environ)
    env["PATH"] = f"/home/john/.opencode/bin:{env.get('PATH', '')}"

    for model in OPENCODE_MODEL_CHAIN:
        try:
            result = subprocess.run(
                [str(OPENCODE_BIN), "run", "-m", model, full_prompt],
                capture_output=True,
                text=True,
                timeout=ENGINE_TIMEOUT,
                cwd=str(THUNDERBIRD),
                env=env,
            )
            output = result.stdout.strip() or result.stderr.strip()
            if output and any(m in output.lower() for m in _OC_RATE_MARKERS):
                log.warning("OpenCode rate-limited on %s — trying next model", model)
                continue
            if result.returncode != 0:
                log.error(
                    "OpenCode rc=%d on %s: %s",
                    result.returncode,
                    model,
                    result.stderr[:200],
                )
                continue
            tier = "FREE" if model.endswith(":free") else "PAID"
            log.info("OpenCode engine: %s [%s]", model, tier)
            return output or "[Engine returned empty response]"

        except subprocess.TimeoutExpired:
            log.warning("OpenCode timeout on %s — trying next model", model)
            continue
        except FileNotFoundError:
            return (
                "[Engine error — opencode binary not found at ~/.opencode/bin/opencode]"
            )
        except Exception as e:
            log.error("OpenCode error on %s: %s", model, e)
            continue

    return "[Engine error — all models exhausted (rate limits + timeouts)]"


# Legacy alias — keeps any remaining call_opencode_engine references working
call_opencode_engine = call_opencode_engine


# ── Engine: Direct OpenRouter API — call any model by ID ─────────────────────

def call_openrouter_engine(
    model_id: str, prompt: str, system_prompt: str = ""
) -> str:
    """Call any OpenRouter model directly via API.

    Used by Both Ways when Commander specifies a model prefix (GROK:, DEEPSEEK:, etc.)
    or when keyword auto-routing selects an OpenRouter model.
    """
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        return "[Engine error — OPENROUTER_API_KEY not set]"

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt[:3000]})
    messages.append({"role": "user", "content": prompt})

    label = _OR_DISPLAY_LABELS.get(model_id, model_id)
    log.info("OpenRouter direct call: %s (%s)", label, model_id)

    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "X-Title": "Thunderbird Telegram GW",
            },
            json={
                "model": model_id,
                "max_tokens": 4096,
                "messages": messages,
            },
            timeout=ENGINE_TIMEOUT,
        )

        if resp.status_code == 429:
            log.warning("OpenRouter rate-limited on %s", model_id)
            return f"[Rate limited on {label} — try again shortly]"
        if resp.status_code >= 500:
            log.error("OpenRouter %d on %s", resp.status_code, model_id)
            return f"[OpenRouter server error {resp.status_code} on {label}]"

        resp.raise_for_status()
        data = resp.json()

        # OpenAI-compatible chat completions format
        choices = data.get("choices", [])
        if choices:
            content = choices[0].get("message", {}).get("content", "")
            if content:
                log.info("OpenRouter %s returned %d chars", label, len(content))
                return content.strip()

        # Fallback: Anthropic messages format (some models)
        content_blocks = data.get("content", [])
        parts = []
        for block in content_blocks:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block["text"])
        if parts:
            result = "\n".join(parts).strip()
            log.info("OpenRouter %s returned %d chars (messages fmt)", label, len(result))
            return result

        log.error("OpenRouter %s — empty response: %s", model_id, str(data)[:300])
        return f"[{label} returned empty response]"

    except requests.Timeout:
        return f"[{label} timed out after {ENGINE_TIMEOUT}s]"
    except Exception as e:
        log.error("OpenRouter %s error: %s", model_id, e)
        return f"[Engine error — {label}: {e}]"


# ── Slash Command Handlers ────────────────────────────────────────────────────


def handle_new(token: str, chat_id: int, ctx_file: Path) -> None:
    _clear_context(ctx_file)
    tg_send(token, chat_id, "🔄 <b>Context cleared.</b> Fresh session started.")
    log.info("/new — context cleared for %s", ctx_file.name)


def handle_status(token: str, chat_id: int) -> None:
    """Check wing health and report."""
    import socket

    lines = ["<b>⚡ Thunderbird Wing Status</b>", ""]

    # MCP HTTP server check
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect(("localhost", 8767))
        s.close()
        lines.append("🟢 MCP Server — ONLINE (port 8767)")
    except Exception:
        lines.append("🔴 MCP Server — OFFLINE (port 8767)")

    # Context activity
    for label, ctx_file in [
        ("D2MC2C", CTX_D2MC2C),
        ("DECOMMISSIONED", CTX_OPENCODE),
        ("Dani", CTX_DANI),
    ]:
        if ctx_file.exists():
            mtime = datetime.fromtimestamp(ctx_file.stat().st_mtime).strftime(
                "%m/%d %H:%M"
            )
            exchanges = _load_context(ctx_file)
            turns = len(exchanges) // 2
            lines.append(f"📋 {label} context — {turns} turns, last: {mtime}")
        else:
            lines.append(f"📋 {label} context — empty")

    # System time
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines.append(f"\n🕐 {now}")

    tg_send(token, chat_id, "\n".join(lines))


def handle_help(token: str, chat_id: int, bot_name: str) -> None:
    msg = f"""<b>⚡ {bot_name} — Commands</b>

/new — Clear context, fresh session
/status — Wing health + last activity
/help — This menu
/drafts — List pending drafts in d2mconcierge
/approve [id] — Send a draft (first 20 chars of ID)
/reject [id] — Delete a draft
"""
    if bot_name == "DECOMMISSIONED":
        msg += "/brief — Trigger Hale morning brief\n"
    msg += "\n<b>🔄 Both Ways Cross-Bot:</b>\n"
    if bot_name == "D2MC2C":
        msg += "<code>@opencode [msg]</code> — Task OpenCode\n<code>@dani [msg]</code> — Task Dani\n"
    elif bot_name == "DECOMMISSIONED":
        msg += "<code>@claude [msg]</code> — Task Claude\n<code>@dani [msg]</code> — Task Dani\n"
    elif bot_name == "Dani":
        msg += "<code>@opencode [msg]</code> — Task OpenCode\n<code>@claude [msg]</code> — Task Claude\n"
    msg += "\n<b>Model Overrides:</b>\n"
    msg += "<code>OPUS: [task]</code> — Claude Opus\n"
    msg += "<code>Sonnet: [task]</code> — Claude Sonnet\n"
    msg += "<code>GROK: [task]</code> — xAI Grok 4.1\n"
    msg += "<code>DEEPSEEK: [task]</code> — DeepSeek V3.1\n"
    msg += "<code>GEMINI: [task]</code> — Gemini 3.1 Flash\n"
    msg += "<code>LLAMA: [task]</code> — Llama 4 Maverick\n"
    msg += "<code>GPT: [task]</code> — GPT-4.1 Mini\n"
    msg += "<code>HAIKU: [task]</code> — Claude Haiku\n"
    msg += "<code>MISTRAL: [task]</code> — Mistral Small\n"
    msg += "\n<b>🧠 Auto-Upgrade:</b>\nBoth Ways detects keywords (strategy, architect, draft, etc.) and auto-upgrades to Opus/Sonnet when needed."
    tg_send(token, chat_id, msg)


def handle_brief(token: str, chat_id: int) -> None:
    """OpenCode /brief — trigger morning brief via OpenCode/Hale."""
    tg_typing(token, chat_id)
    tg_send(token, chat_id, "⌛ Pulling brief from OpenCode/Hale...")

    system = _PERSONA_CACHE.get("hale_system", "")
    brief_path = str(HALE_BRIEF)
    text = f"""Read {brief_path} and give me the current morning brief.
Format: structured, scannable. Highlight CRITICAL items first.
If the brief is stale or missing, summarize what you know about current wing status."""

    raw = call_opencode_engine(system, text, use_mcp=True)
    chunks = fmt_process(raw, CHUNK_SIZE)
    tg_send_chunks(token, chat_id, chunks)


# ── Draft Approval Commands ───────────────────────────────────────────────────


def _get_d2m_gmail():
    """Get Gmail service for d2mconcierge (gmail_token.json)."""
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build

        token_file = THUNDERBIRD / "gmail_token.json"
        creds_file = THUNDERBIRD / "credentials.json"
        SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
        creds = None
        if token_file.exists():
            creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            token_file.write_text(creds.to_json())
        if not creds or not creds.valid:
            return None
        return build("gmail", "v1", credentials=creds)
    except Exception as e:
        log.error("Gmail service error: %s", e)
        return None


def handle_drafts(token: str, chat_id: int) -> None:
    """List pending drafts in d2mconcierge — /drafts"""
    tg_typing(token, chat_id)
    svc = _get_d2m_gmail()
    if not svc:
        tg_send(token, chat_id, "❌ Gmail unavailable — check credentials.")
        return
    try:
        result = svc.users().drafts().list(userId="me", maxResults=8).execute()
        drafts = result.get("drafts", [])
        if not drafts:
            tg_send(token, chat_id, "📭 No pending drafts in d2mconcierge.")
            return
        lines = ["<b>📋 Pending drafts in d2mconcierge:</b>\n"]
        for d in drafts:
            try:
                detail = (
                    svc.users()
                    .drafts()
                    .get(userId="me", id=d["id"], format="metadata")
                    .execute()
                )
                headers = {
                    h["name"].lower(): h["value"]
                    for h in detail.get("message", {})
                    .get("payload", {})
                    .get("headers", [])
                }
                subject = headers.get("subject", "(no subject)")[:60]
                to = headers.get("to", "?")[:40]
                lines.append(
                    f"<code>{d['id'][:20]}</code>\n  To: {to}\n  Re: {subject}\n"
                )
            except Exception:
                lines.append(f"<code>{d['id'][:20]}</code> (error fetching detail)\n")
        lines.append("\nUse <code>/approve [id]</code> or <code>/reject [id]</code>")
        tg_send(token, chat_id, "\n".join(lines))
    except Exception as e:
        tg_send(token, chat_id, f"❌ Error listing drafts: {e}")


def handle_approve(token: str, chat_id: int, args: list) -> None:
    """Publish a draft — apply stationery template + send. /approve [draft_id]

    Two-lane system (SO 2026-05-07):
    - If draft is in the two-lane registry: fetches edited body, applies template, sends.
    - If no registry entry (old-style draft): falls back to raw drafts().send().
    """
    if not args:
        tg_send(
            token,
            chat_id,
            "Usage: <code>/approve [draft_id]</code>\nGet IDs with /drafts",
        )
        return
    draft_id = args[0]
    tg_typing(token, chat_id)

    # Lane 2: two-lane publish path (template applied at send time)
    metadata = _get_draft_metadata(draft_id)
    if metadata:
        try:
            result = publish_draft(draft_id)
            if result.get("status") == "success":
                tg_send(
                    token,
                    chat_id,
                    f"✅ <b>PUBLISHED</b>\n"
                    f"To: {result['to']}\n"
                    f"Subject: {result['subject']}\n"
                    f"Persona: {result['persona_id']} | Template: {result['template']}\n\n"
                    f"<i>Stationery applied at send-time — Gmail-safe. Draft deleted.</i>",
                )
                log.info("[PUBLISH] %s → %s | %s", result['persona_id'], result['to'], result['subject'][:50])
            else:
                tg_send(token, chat_id, f"❌ Publish failed: {result}")
        except Exception as e:
            tg_send(token, chat_id, f"❌ Publish error: {e}")
        return

    # Fallback: legacy draft not in registry — send raw (no template)
    svc = _get_d2m_gmail()
    if not svc:
        tg_send(token, chat_id, "❌ Gmail unavailable.")
        return
    try:
        detail = (
            svc.users()
            .drafts()
            .get(userId="me", id=draft_id, format="metadata")
            .execute()
        )
        headers = {
            h["name"].lower(): h["value"]
            for h in detail.get("message", {}).get("payload", {}).get("headers", [])
        }
        subject = headers.get("subject", "?")
        to = headers.get("to", "?")
        svc.users().drafts().send(userId="me", body={"id": draft_id}).execute()
        tg_send(
            token,
            chat_id,
            f"✅ <b>SENT</b>\nTo: {to}\nSubject: {subject}\n\n"
            f"<i>Draft {draft_id[:16]}… delivered (legacy — no stationery applied).</i>",
        )
        log.info("[APPROVE-LEGACY] Sent draft %s to %s — %s", draft_id[:16], to, subject)
    except Exception as e:
        tg_send(token, chat_id, f"❌ Send failed: {e}")


def handle_reject(token: str, chat_id: int, args: list) -> None:
    """Delete a draft by ID — /reject [draft_id]"""
    if not args:
        tg_send(
            token,
            chat_id,
            "Usage: <code>/reject [draft_id]</code>\nGet IDs with /drafts",
        )
        return
    draft_id = args[0]
    tg_typing(token, chat_id)
    svc = _get_d2m_gmail()
    if not svc:
        tg_send(token, chat_id, "❌ Gmail unavailable.")
        return
    try:
        detail = (
            svc.users()
            .drafts()
            .get(userId="me", id=draft_id, format="metadata")
            .execute()
        )
        headers = {
            h["name"].lower(): h["value"]
            for h in detail.get("message", {}).get("payload", {}).get("headers", [])
        }
        subject = headers.get("subject", "?")
        svc.users().drafts().delete(userId="me", id=draft_id).execute()
        tg_send(token, chat_id, f"🗑️ <b>REJECTED</b>: {subject[:60]}")
        log.info("[REJECT] Deleted draft %s — %s", draft_id[:16], subject)
    except Exception as e:
        tg_send(token, chat_id, f"❌ Reject failed: {e}")


# ── Both Ways Router ──────────────────────────────────────────────────────────


def _detect_forward(msg: str, bot_name: str) -> str | None:
    """Return 'opencode', 'claude', or 'dani' if msg targets them. Works with typed @ or voice 'at'."""
    lower = msg.lower().strip()

    # Regex catches:
    # 1. Typed: "@opencode do this"
    # 2. Voice: "at opencode do this"
    # 3. Short: "opencode, do this" (Name as imperative)

    p_opencode_cmd = re.compile(r"^(@|at\s+)?opencode[,\s:].*")
    p_claude = re.compile(r"^(@|at\s+)?(claude|hale)[,\s:].*")
    p_dani = re.compile(r"^(@|at\s+)?dani[,\s:].*")

    if bot_name == "D2MC2C":
        # Currently talking to Claude. Forward others.
        if p_opencode.match(lower):
            return "opencode"
        if p_dani.match(lower):
            return "dani"
    elif bot_name == "DECOMMISSIONED":
        # Currently talking to OpenCode. Forward others.
        if p_claude.match(lower):
            return "claude"
        if p_dani.match(lower):
            return "dani"
    elif bot_name == "Dani":
        # Currently talking to Dani. Forward others.
        if p_opencode.match(lower):
            return "opencode"
        if p_claude.match(lower):
            return "claude"

    return None


def _select_model_by_keywords(text: str) -> tuple[str | None, str]:
    """Use keyword_router to pick the best model for a Both Ways task.

    Returns (model_override, reason).
    - High-confidence Claude keywords (>=0.7) → Opus (complex reasoning)
    - Moderate Claude keywords (0.5-0.69)    → Sonnet (creative/voice)
    - No Claude keywords                     → None (use target default)
    """
    decision = classify_task(text)
    if decision["engine"] == "claude":
        conf = decision["confidence"]
        if conf >= 0.7:
            return OPUS_MODEL, f"keywords→Opus ({conf:.0%}): {decision['reason']}"
        else:
            return SONNET_MODEL, f"keywords→Sonnet ({conf:.0%}): {decision['reason']}"
    return None, "no upgrade keywords — using target default"


def _handle_forward(
    token: str,
    chat_id: int,
    msg: str,
    bot_name: str,
    ctx_file: Path,
    target: str,
    model_override: str | None = None,
    openrouter_override: str | None = None,
) -> None:
    """Strip @prefix, classify task via keyword router, call the best engine.

    Priority: explicit openrouter_override > explicit model_override > keyword auto-upgrade > target default.
    """
    parts = msg.split(None, 1)
    stripped = parts[1].strip() if len(parts) > 1 else ""
    if not stripped:
        tg_send(token, chat_id, "Both Ways: no message after @prefix.")
        return

    tg_typing(token, chat_id)

    # ── Direct OpenRouter override (GROK:, DEEPSEEK:, GEMINI:, etc.) ────
    if openrouter_override:
        or_label = _OR_DISPLAY_LABELS.get(openrouter_override, openrouter_override)
        log.info("[%s] Both Ways → %s (OpenRouter direct): %s...", bot_name, or_label, stripped[:80])
        system = _PERSONA_CACHE.get("hale_system", "")
        try:
            raw_response = call_openrouter_engine(openrouter_override, stripped, system)
        except Exception as e:
            log.error("[%s] Both Ways OpenRouter error: %s", bot_name, e)
            raw_response = f"[Both Ways error: {e}]"

        chunks = fmt_process(
            f"🔄 <b>Both Ways via {or_label}</b> 🌐\n\n{raw_response}", CHUNK_SIZE
        )
        tg_send_chunks(token, chat_id, chunks)
        _append_exchange(
            ctx_file,
            user_msg=stripped,
            assistant_msg=raw_response[:800],
            user_label="Commander",
            assistant_label=f"{or_label} (via Both Ways)",
        )
        return

    # ── Keyword-based model upgrade ──────────────────────────────────────
    # If Commander already set OPUS:/Sonnet: prefix, honour that.
    # Otherwise, scan the task text for keyword-router patterns.
    kw_model = None
    kw_reason = ""
    if not model_override:
        kw_model, kw_reason = _select_model_by_keywords(stripped)

    effective_override = model_override or kw_model

    # ── Pick engine + apply upgrade ──────────────────────────────────────
    if target == "opencode":
        if effective_override:
            # Keywords say this needs Claude — upgrade from OpenCode → Claude
            engine_fn = hale_claude_engine
            engine_label = "Opus" if effective_override == OPUS_MODEL else "Sonnet"
            log.info("[%s] Both Ways UPGRADE opencode→%s (%s)", bot_name, engine_label, kw_reason)
        else:
            engine_fn = hale_opencode_engine
            engine_label = "OpenCode"
    elif target == "dani":
        engine_fn = dani_claude_engine
        engine_label = "Dani"
        # Dani always uses Sonnet — no model override applied
        effective_override = None
    else:
        engine_fn = hale_claude_engine
        engine_label = "Opus" if effective_override == OPUS_MODEL else "Sonnet"

    log.info("[%s] Both Ways → %s: %s...", bot_name, engine_label, stripped[:80])
    try:
        raw_response = engine_fn("", stripped, effective_override)
    except Exception as e:
        log.error("[%s] Both Ways engine error: %s", bot_name, e)
        raw_response = f"[Both Ways error: {e}]"

    # Show upgrade badge if keywords triggered a model change
    upgrade_badge = ""
    if kw_model and not model_override:
        upgrade_badge = f"⬆️ <i>Auto-upgraded via keywords</i>\n"

    chunks = fmt_process(
        f"🔄 <b>Both Ways via {engine_label}</b>\n{upgrade_badge}\n{raw_response}", CHUNK_SIZE
    )
    tg_send_chunks(token, chat_id, chunks)

    _append_exchange(
        ctx_file,
        user_msg=stripped,
        assistant_msg=raw_response[:800],
        user_label="Commander",
        assistant_label=f"{engine_label} (via Both Ways)",
    )


# ── Message Handler ───────────────────────────────────────────────────────────


def handle_voice(token, chat_id, user_id, voice_obj, bot_name, ctx_file, engine_fn, assistant_label):
    """Handle voice messages: download, transcribe, dispatch."""
    log.info("[%s] Received voice message", bot_name)
    file_id = voice_obj["file_id"]
    file_data = tg(token, "getFile", file_id=file_id)
    if not file_data.get("ok"):
        tg_send(token, chat_id, "❌ Voice transcription failed (cannot get file path)")
        return

    file_path = file_data["result"]["file_path"]
    download_url = f"https://api.telegram.org/file/bot{token}/{file_path}"
    
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        r = requests.get(download_url, stream=True)
        for chunk in r.iter_content(chunk_size=8192):
            tmp.write(chunk)
        tmp_path = tmp.name

    try:
        text = transcribe_audio(tmp_path)
        log.info("[%s] Transcription: %s", bot_name, text)
        tg_send(token, chat_id, f"🎙️ <i>{text}</i>")
        handle_message(token, chat_id, user_id, text, bot_name, ctx_file, engine_fn, assistant_label)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def handle_message(
    token: str,
    chat_id: int,
    user_id: int,
    text: str,
    bot_name: str,
    ctx_file: Path,
    engine_fn: Callable,
    assistant_label: str,
) -> None:
    """Process one incoming message and send formatted response."""

    # Security: Commander-only for D2MC2C and DECOMMISSIONED
    # For Dani, still only accept Commander ID (clients use a separate flow later)
    if user_id != COMMANDER_ID:
        log.warning("Rejected message from non-Commander user_id=%d", user_id)
        return

    msg = text.strip()

    # ── Slash commands ────────────────────────────────────────────────────────
    if msg.startswith("/"):
        cmd = msg.split()[0].lower()
        if cmd == "/new":
            handle_new(token, chat_id, ctx_file)
            return
        elif cmd == "/status":
            handle_status(token, chat_id)
            return
        elif cmd == "/help":
            handle_help(token, chat_id, bot_name)
            return
            handle_brief(token, chat_id)
            return
        elif cmd == "/drafts":
            handle_drafts(token, chat_id)
            return
        elif cmd == "/approve":
            args = msg.split()[1:]
            handle_approve(token, chat_id, args)
            return
        elif cmd == "/reject":
            args = msg.split()[1:]
            handle_reject(token, chat_id, args)
            return
        elif cmd == "/dispatch_status" and _HALE_DISPATCHER_AVAILABLE:
            try:
                tg_send(token, chat_id, dispatch_status_text())
            except Exception as e:
                tg_send(token, chat_id, f"[/dispatch_status error: {e}]")
            return
        elif cmd == "/savings" and _HALE_DISPATCHER_AVAILABLE:
            try:
                tg_send(token, chat_id, savings_text())
            except Exception as e:
                tg_send(token, chat_id, f"[/savings error: {e}]")
            return
        elif cmd == "/dispatch" and _HALE_DISPATCHER_AVAILABLE:
            dispatch_text = " ".join(msg.split()[1:]).strip()
            if not dispatch_text:
                tg_send(token, chat_id, "Usage: /dispatch &lt;request&gt;")
                return
            tg_typing(token, chat_id)
            try:
                resp = get_hale_response(dispatch_text, channel="telegram")
            except Exception as e:
                resp = f"[Hale dispatcher error: {e}]"
            chunks = fmt_process(f"🦅\n\n{resp}", CHUNK_SIZE)
            tg_send_chunks(token, chat_id, chunks)
            try:
                hale_record_turn(chat_id, dispatch_text, resp[:800])
            except Exception:
                pass
            return
        elif cmd == "/start":
            tg_send(
                token, chat_id, f"<b>{bot_name} online.</b> Type /help for commands."
            )
            return
        else:
            tg_send(token, chat_id, f"Unknown command. Type /help.")
            return

    # ── Model override detection ────────────────────────────────────────────
    # Supports: OPUS: / SONNET: (Claude models via claude -p)
    #           GROK: / DEEPSEEK: / GEMINI: / LLAMA: / GPT: / HAIKU: / MISTRAL:
    #           (OpenRouter models via direct API)
    model_override = None
    openrouter_override = None  # set when targeting an OpenRouter model directly
    msg_upper = msg.upper()
    if msg_upper.startswith("OPUS:"):
        model_override = OPUS_MODEL
        msg = msg[5:].strip()
        log.info("OPUS override activated")
    elif msg_upper.startswith("SONNET:"):
        model_override = SONNET_MODEL
        msg = msg[7:].strip()
        log.info("Sonnet override activated")
    else:
        # Check OpenRouter model aliases (GROK:, DEEPSEEK:, GEMINI:, etc.)
        for prefix, or_model_id in OPENROUTER_MODEL_ALIASES.items():
            if msg_upper.startswith(prefix + ":"):
                # V4 Pro block — too expensive for auto-selection ($0.03–$2.83/gen)
                _V4PRO_BLOCK = {"deepseek-v4-pro", "deepseek/deepseek-v4-pro"}
                if any(b in or_model_id for b in _V4PRO_BLOCK):
                    log.warning("BLOCKED model override attempt: %s — V4 Pro is cost-prohibited", or_model_id)
                    tg_send(token, chat_id, "⛔ Model blocked: DeepSeek V4 Pro is cost-prohibited on this wing ($0.03–$2.83/gen). Use DEEPSEEK: for Qwen free tier or GEMINI: for Flash Lite.")
                    return
                openrouter_override = or_model_id
                msg = msg[len(prefix) + 1:].strip()
                log.info("%s override activated → %s", prefix, or_model_id)
                break

    if not msg:
        return

    # ── Both Ways forward check ────────────────────────────────────────────────
    forward_target = _detect_forward(msg, bot_name)
    if forward_target:
        _handle_forward(token, chat_id, msg, bot_name, ctx_file, forward_target,
                        model_override, openrouter_override)
        return

    # ── Hale Dispatcher: correction detection + auto-routing ─────────────────
    # Correction check runs first (no-op if message isn't a correction pattern).
    # Hale auto-routing fires only when no explicit override is set AND the
    # substrate chain classifies this as Sonnet/Opus tier.  Falls through to
    # the existing engine on any failure or when the Hale infra is unavailable.
    if _HALE_DISPATCHER_AVAILABLE and user_id == COMMANDER_ID:
        try:
            hale_check_correction(chat_id, msg)
        except Exception as e:
            log.warning("[%s] Hale correction check failed (non-fatal): %s", bot_name, e)

        if (not model_override) and (not openrouter_override):
            try:
                _hale_tier = should_use_hale(msg)
            except Exception as e:
                log.warning("[%s] Hale classification failed (non-fatal): %s", bot_name, e)
                _hale_tier = False

            if _hale_tier:
                tg_typing(token, chat_id)
                start_t = time.time()
                try:
                    hale_resp = get_hale_response(msg, channel="telegram")
                except Exception as e:
                    log.error("[%s] Hale dispatcher error, falling through: %s", bot_name, e)
                    hale_resp = None

                if hale_resp:
                    elapsed = time.time() - start_t
                    log.info("[%s] Hale dispatcher returned %d chars in %.1fs",
                             bot_name, len(hale_resp), elapsed)
                    full_label = f"{assistant_label}, Dispatcher"
                    full = f"🦅\n\n{hale_resp}"
                    tg_send_chunks(token, chat_id, fmt_process(full, CHUNK_SIZE))
                    try:
                        hale_record_turn(chat_id, msg, hale_resp[:800])
                    except Exception:
                        pass
                    _append_exchange(
                        ctx_file,
                        user_msg=msg,
                        assistant_msg=hale_resp[:800],
                        user_label="Commander",
                        assistant_label=full_label,
                    )
                    return

    # ── Typing indicator ──────────────────────────────────────────────────────
    tg_typing(token, chat_id)

    # ── Load context ──────────────────────────────────────────────────────────
    context_text = _format_context(ctx_file)

    # ── Invoke engine ─────────────────────────────────────────────────────────
    log.info("[%s] Invoking engine for: %s...", bot_name, msg[:80])
    start_t = time.time()

    try:
        if openrouter_override:
            # Direct OpenRouter model call (GROK:, DEEPSEEK:, GEMINI:, etc.)
            system = _PERSONA_CACHE.get("hale_system", "")
            full_prompt = f"{context_text}\n\nCommander: {msg}" if context_text else msg
            raw_response = call_openrouter_engine(openrouter_override, full_prompt, system)
        else:
            raw_response = engine_fn(context_text, msg, model_override)
    except Exception as e:
        log.error("[%s] Engine exception: %s", bot_name, e)
        raw_response = f"[Internal error: {e}]"

    elapsed = time.time() - start_t
    log.info(
        "[%s] Engine returned %d chars in %.1fs", bot_name, len(raw_response), elapsed
    )

    # ── Determine model label — ALWAYS visible in response ─────────────────
    if openrouter_override:
        or_label = _OR_DISPLAY_LABELS.get(openrouter_override, openrouter_override)
        model_label = or_label
        assistant_label = f"{assistant_label}, {or_label}"
    elif model_override == OPUS_MODEL:
        model_label = "Opus"
        assistant_label = f"{assistant_label}, Opus"
    elif model_override == SONNET_MODEL:
        model_label = "Sonnet"
        assistant_label = f"{assistant_label}, Sonnet"
    elif bot_name == "DECOMMISSIONED":
        model_label = "DeepSeek V3.1"
        assistant_label = f"{assistant_label}, DeepSeek V3.1"
    elif bot_name == "Dani":
        model_label = "Sonnet"
        assistant_label = f"{assistant_label}, Sonnet"
    else:
        model_label = "Sonnet"
        assistant_label = f"{assistant_label}, Sonnet"

    # ── Format and send — model attribution always shown ──────────────────
    raw_response = f"<b>{assistant_label}</b>\n\n{raw_response}"
    
    # ── Text-to-Speech synthesis ──────────────────────────────────────────
    audio_path = f"/tmp/response_{chat_id}_{int(time.time())}.ogg"
    synthesize_speech(raw_response, audio_path)
    
    # Send Voice
    try:
        with open(audio_path, 'rb') as f:
            tg(token, "sendVoice", chat_id=chat_id, voice=f)
    except Exception as e:
        log.error("TTS sending failed: %s", e)
    
    if os.path.exists(audio_path):
        os.remove(audio_path)

    chunks = fmt_process(raw_response, CHUNK_SIZE)
    tg_send_chunks(token, chat_id, chunks)

    # ── Save to rolling context ───────────────────────────────────────────────
    # Use first 800 chars of response to keep context compact
    response_snippet = raw_response[:800].strip()
    _append_exchange(
        ctx_file,
        user_msg=msg,
        assistant_msg=response_snippet,
        user_label="Commander",
        assistant_label=assistant_label,
    )

    # Track last turn for Hale correction detection (covers routine engine path).
    if _HALE_DISPATCHER_AVAILABLE:
        try:
            hale_record_turn(chat_id, msg, response_snippet)
        except Exception:
            pass


# ── Engine function wrappers (match handle_message signature) ─────────────────


def hale_claude_engine(
    context_text: str, message: str, model_override: str | None
) -> str:
    prompt = _build_hale_claude_prompt(context_text, message)
    model = model_override or SONNET_MODEL
    return call_claude_engine(prompt, model=model)


def hale_opencode_engine(
    context_text: str, message: str, model_override: str | None
) -> str:
    """Direct OpenRouter (Gemini 2.5 Flash Lite) as Hale — bypasses opencode shell artifacts."""
    system = _PERSONA_CACHE.get("hale_system", "")
    text = (
        (f"{context_text}\n\n" if context_text else "")
        + f"Commander: {message}\n\n"
        + "Respond as Hale. Brief-first. No preamble. No trailing summary."
    )
    model = model_override or "google/gemini-2.5-flash-lite"
    return call_openrouter_engine(model, text, system_prompt=system)


def dani_claude_engine(
    context_text: str, message: str, model_override: str | None
) -> str:
    prompt = _build_dani_claude_prompt(context_text, message)
    # Dani always uses Sonnet (warm copy, client-facing)
    return call_claude_engine(prompt, model=SONNET_MODEL)


# ── Bot Poll Loop ─────────────────────────────────────────────────────────────


def bot_poll_loop(
    token: str,
    bot_name: str,
    ctx_file: Path,
    engine_fn: Callable,
    assistant_label: str,
) -> None:
    """
    Long-poll loop for one bot. Runs in its own thread.
    Processes messages only from COMMANDER_ID.
    """
    log.info("[%s] Poll loop starting", bot_name)
    offset = 0
    _backoff = 5  # exponential backoff seconds on poll errors (resets on success)

    # Initialize context file if missing
    if not ctx_file.exists():
        _save_context(ctx_file, [])

    while True:
        try:
            updates = tg_get_updates(token, offset=offset)
            _backoff = 5  # reset on successful poll
        except Exception as e:
            log.error("[%s] getUpdates exception: %s", bot_name, e)
            time.sleep(_backoff)
            _backoff = min(_backoff * 2, 60)
            continue

        for update in updates:
            offset = update["update_id"] + 1

            msg_obj = update.get("message")
            if not msg_obj:
                continue  # Skip non-message updates (callbacks, etc.)

            chat_id = msg_obj.get("chat", {}).get("id")
            user_id = msg_obj.get("from", {}).get("id")
            text = msg_obj.get("text", "")

            if not chat_id or not text:
                continue

            # Dispatch in a thread so we don't block the poll loop
            if msg_obj.get("voice"):
                t = threading.Thread(
                    target=handle_voice,
                    args=(
                        token,
                        chat_id,
                        user_id,
                        msg_obj["voice"],
                        bot_name,
                        ctx_file,
                        engine_fn,
                        assistant_label,
                    ),
                    daemon=True,
                )
            else:
                t = threading.Thread(
                    target=handle_message,
                    args=(
                        token,
                        chat_id,
                        user_id,
                        text,
                        bot_name,
                        ctx_file,
                        engine_fn,
                        assistant_label,
                    ),
                    daemon=True,
                )
            t.start()


        # Brief sleep between polls to avoid hammering Telegram
        time.sleep(POLL_INTERVAL)


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    log.info("═══════════════════════════════════════")
    log.info("Thunderbird Telegram Gateway v1.5 — Both Ways Enabled")
    log.info("Three bots. One process. Clean output.")
    log.info("═══════════════════════════════════════")

    # Validate tokens
    missing = []
    if not TOKEN_D2MC2C:
        missing.append("TELEGRAM_D2MC2C_TOKEN")
    if not TOKEN_DANI:
        missing.append("TELEGRAM_DANI_TOKEN")
    if missing:
        log.error("Missing required tokens: %s", ", ".join(missing))
        sys.exit(1)

    # Load persona cache
    _load_persona_cache()

    # ── Startup engine self-test ──────────────────────────────────────────────
    # Fires before threads start. If Claude binary is broken, pages Commander
    # immediately instead of silently returning [Engine error] on every message.
    def _startup_engine_test():
        # Test with a real model call (not just --version) to catch auth failures too.
        env_test = dict(os.environ)
        env_test.pop("ANTHROPIC_API_KEY", None)  # strip stale key that overrides OAuth
        _creds = Path.home() / ".claude" / ".credentials.json"
        if _creds.exists():
            try:
                _tok = json.loads(_creds.read_text()).get("claudeAiOauth", {}).get("accessToken")
                if _tok:
                    env_test["CLAUDE_CODE_OAUTH_TOKEN"] = _tok
            except Exception:
                pass
        try:
            result = subprocess.run(
                ["/home/john/.local/bin/claude", "--model", HAIKU_MODEL,
                 "-p", "Reply with the single word: OK",
                 "--dangerously-skip-permissions"],
                capture_output=True, text=True, timeout=30, env=env_test,
            )
            if result.returncode == 0:
                log.info("Engine self-test OK (auth confirmed)")
            else:
                err = (result.stderr or result.stdout).strip()[:300]
                log.error("ENGINE SELF-TEST FAILED rc=%d: %s", result.returncode, err)
                tg_send(TOKEN_D2MC2C, COMMANDER_ID,
                        f"⚠️ <b>D2MC2C ENGINE BROKEN</b>\n"
                        f"claude rc={result.returncode}\n<code>{err or '(no output)'}</code>\n"
                        f"Messages will return [Engine error] until fixed.")
        except FileNotFoundError:
            log.error("ENGINE SELF-TEST FAILED: claude binary not found")
            tg_send(TOKEN_D2MC2C, COMMANDER_ID,
                    "⚠️ <b>D2MC2C ENGINE BROKEN</b>\n"
                    "claude binary not found at /home/john/.local/bin/claude")
        except Exception as e:
            log.error("ENGINE SELF-TEST exception: %s", e)

    _startup_engine_test()

    # Verify commander ID is set
    log.info("Commander ID: %d", COMMANDER_ID)
    log.info(
        "Engine timeout: %ds | Chunk size: %d | Context turns: %d",
        ENGINE_TIMEOUT,
        CHUNK_SIZE,
        CONTEXT_TURNS,
    )

    # Define bots
    bot_configs = [
        {
            "token": TOKEN_D2MC2C,
            "bot_name": "D2MC2C",
            "ctx_file": CTX_D2MC2C,
            "engine_fn": hale_claude_engine,
            "assistant_label": "Hale",
        },
        {
            "token": TOKEN_DANI,
            "bot_name": "Dani",
            "ctx_file": CTX_DANI,
            "engine_fn": dani_claude_engine,
            "assistant_label": "Dani",
        },
    ]

    # Start a poll thread per bot
    threads = []
    for cfg in bot_configs:
        t = threading.Thread(
            target=bot_poll_loop,
            kwargs=cfg,
            name=f"poll_{cfg['bot_name']}",
            daemon=True,
        )
        t.start()
        threads.append(t)
        log.info("[%s] Poll thread started", cfg["bot_name"])

    log.info("All 3 bot threads running. Gateway is LIVE.")

    # Keep main thread alive — monitor worker threads
    try:
        while True:
            dead = [t for t in threads if not t.is_alive()]
            if dead:
                for d in dead:
                    log.error("Thread %s died — gateway may be degraded", d.name)
            time.sleep(30)
    except KeyboardInterrupt:
        log.info("Gateway shutting down (KeyboardInterrupt)")


if __name__ == "__main__":
    main()
