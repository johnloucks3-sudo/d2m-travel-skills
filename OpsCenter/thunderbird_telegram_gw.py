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

# Force all CUDA-aware libraries to CPU-only mode (SO-2026-06-13-ELON).
# Telegram gateway is CPU-only; prevents silent CUDA init crashes from ML libraries
# (PyTorch, TensorFlow, Hugging Face transformers, etc. that auto-init GPU on import).
import os
os.environ["CUDA_VISIBLE_DEVICES"] = ""  # Hide all CUDA devices
os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"  # Explicit mode (safeguard)

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

def pre_process_prompt(prompt: str) -> list:
    """Break large prompts into manageable chunks to prevent timeout errors."""
    if len(prompt) < 15000:
        return [prompt]
    
    # Simple chunking by paragraph if too large
    chunks = prompt.split('\n\n')
    processed_chunks = []
    current_chunk = ""
    for chunk in chunks:
        if len(current_chunk) + len(chunk) < 12000:
            current_chunk += chunk + "\n\n"
        else:
            processed_chunks.append(current_chunk)
            current_chunk = chunk + "\n\n"
    processed_chunks.append(current_chunk)
    return processed_chunks

from thunderbird_tg_formatter import process as fmt_process
from keyword_router import classify_task, CLAUDE_KEYWORD_PATTERN
from thunderbird_gmail import publish_draft, _get_draft_metadata
try:
    from thunderbird_stt import transcribe_audio
except ImportError:
    def transcribe_audio(*args, **kwargs):
        return "[STT unavailable — whisper not installed]"
# TTS optional — if missing, fall back silently
TTS_AVAILABLE = False
def synthesize_speech(text, output_path, voice_name="en-US-Journey-F"):
    print(f"[TTS FALLBACK] TTS not available. Text: {text[:50]}...")
    return False

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
TOKEN_HALE   = os.environ.get("TELEGRAM_GOOSE_TOKEN", "")   # HaleD2M — Hale chat
TOKEN_DANI   = os.environ.get("TELEGRAM_DANI_TOKEN", "")
TOKEN_RELAY  = os.environ.get("TELEGRAM_RELAY_TOKEN", "")   # D2M Channels — system relay
RELAY_CHAT_ID = int(os.environ.get("TELEGRAM_RELAY_CHAT_ID", "0"))

COMMANDER_ID = int(os.environ.get("TELEGRAM_COMMANDER_ID", "7554895206"))

# Dani is open to all — no allow-list needed. D2MC2C and HaleD2M are Commander-only.
POLL_INTERVAL  = float(os.environ.get("TELEGRAM_GW_POLL_INTERVAL", "2"))
ENGINE_TIMEOUT = int(os.environ.get("TELEGRAM_GW_TIMEOUT", "60"))
CHUNK_SIZE     = int(os.environ.get("TELEGRAM_GW_CHUNK_SIZE", "4000"))
CONTEXT_TURNS  = int(os.environ.get("TELEGRAM_GW_CONTEXT_TURNS", "10"))

# All engines → Claude Code. Sonnet auto-escalates on keywords; Opus on explicit request.
SONNET_MODEL = "claude-sonnet-4-6"
OPUS_MODEL   = "claude-opus-4-6"
HAIKU_MODEL  = "claude-haiku-4-5-20251001"

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
    "GROK":             "x-ai/grok-4.3",                             # 2M ctx, successor to grok-4.1-fast
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
    "opencode/big-pickle",                                        # PRIMARY: $0 native, reasoning=True
    "opencode/deepseek-v4-flash-free",                            # $0 native fallback, reasoning=True
    "openrouter/nvidia/nemotron-3-super-120b-a12b:free",         # $0 OR fallback (confirmed free)
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
        # Hale COS persona — single source of truth via hale_persona_loader.
        # GATES-GUARANTEED compact load (~9.5K). The prior [:5000] raw-char
        # truncation silently cut the four gates (authority layer starts at
        # char 5298) — fixed 2026-06-10 (MISSION-179 parity build).
        hale_cos = ""
        try:
            from core.ai_infra.hale_persona_loader import load_compact_persona
            hale_cos = load_compact_persona()
        except Exception as _e:
            log.warning("persona loader unavailable, falling back: %s", _e)
        if not hale_cos:
            if HALE_COS.exists():
                # Fallback floor: 14000 chars clears the gates AND the ACTIVE
                # STANDING ORDERS block (~char 11863–13355). Raised from 9000
                # 2026-06-10 so the 8-Hale governance survives loader failure.
                hale_cos = HALE_COS.read_text(encoding="utf-8")[:14000]
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
    """Long-poll getUpdates (timeout=25). Holds connection; Telegram pushes on new messages."""
    data = tg(token, "getUpdates", offset=offset, timeout=25, limit=20)
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


# ── Media send (M-148 — sendPhoto / sendMediaGroup) ──────────────────────────
# Lets Hale push images/media to the Commander: brief charts, ship photos,
# dossier images. Two transports:
#   • URL or Telegram file_id  → JSON body via tg() (cheap, no upload)
#   • local file path          → multipart upload via requests files=
# A local path is detected by os.path.isfile(); everything else is treated as
# a URL/file_id and sent through the JSON path.
_TG_IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")


def _is_local_path(media: str) -> bool:
    """True if media refers to an existing local file (needs multipart upload)."""
    try:
        return bool(media) and os.path.isfile(media)
    except Exception:
        return False


def tg_send_photo(
    token: str,
    chat_id: int,
    photo: str,
    caption: str = "",
    parse_mode: str = "HTML",
) -> bool:
    """Send a single photo. `photo` is a URL, Telegram file_id, or local path.

    Returns True on success. Captions over Telegram's 1024-char limit are
    truncated so the API call doesn't fail outright.
    """
    if caption and len(caption) > 1024:
        caption = caption[:1020] + "\n…"

    if _is_local_path(photo):
        # Multipart upload — tg()'s JSON path cannot carry a file body.
        url = TG_BASE.format(token=token, method="sendPhoto")
        data = {"chat_id": chat_id}
        if caption:
            data["caption"] = caption
            data["parse_mode"] = parse_mode
        try:
            with open(photo, "rb") as fh:
                r = requests.post(url, data=data, files={"photo": fh}, timeout=60)
            resp = r.json()
            if not resp.get("ok"):
                log.warning("sendPhoto (upload) error: %s", resp.get("description", "?"))
            return bool(resp.get("ok"))
        except Exception as e:
            log.error("sendPhoto (upload) exception: %s", e)
            return False

    # URL or file_id → JSON body
    kwargs = {"chat_id": chat_id, "photo": photo}
    if caption:
        kwargs["caption"] = caption
        kwargs["parse_mode"] = parse_mode
    data = tg(token, "sendPhoto", **kwargs)
    return bool(data.get("ok"))


def tg_send_media_group(
    token: str,
    chat_id: int,
    media: list,
    caption: str = "",
) -> bool:
    """Send 2–10 photos as an album via sendMediaGroup.

    `media` is a list where each item is one of:
      • a str  → URL, file_id, or local file path
      • a dict → {"media": <url/file_id/path>, "caption": <optional>}
    The album caption (if given) is attached to the first item only — Telegram
    shows it under the group.

    Local files are uploaded via multipart using attach:// references; URLs and
    file_ids ride the JSON body. Mixed local + remote in one group is supported.

    Telegram limits a media group to 10 items. Lists >10 are chunked into
    sequential groups. A single item degrades to tg_send_photo.
    """
    # Normalise to list of dicts
    norm = []
    for item in media:
        if isinstance(item, dict):
            norm.append(dict(item))
        else:
            norm.append({"media": item})

    if not norm:
        log.warning("sendMediaGroup called with empty media list")
        return False
    if len(norm) == 1:
        only = norm[0]
        return tg_send_photo(
            token, chat_id, only["media"], caption or only.get("caption", "")
        )

    # Chunk into groups of 10 (Telegram hard cap)
    all_ok = True
    for start in range(0, len(norm), 10):
        group = norm[start : start + 10]
        ok = _send_one_media_group(token, chat_id, group, caption if start == 0 else "")
        all_ok = all_ok and ok
        if len(norm) > 10:
            time.sleep(0.5)
    return all_ok


def _send_one_media_group(
    token: str, chat_id: int, group: list, caption: str
) -> bool:
    """Send a single ≤10-item media group. Builds InputMediaPhoto entries,
    uploading any local files via multipart attach:// refs."""
    input_media = []
    files = {}
    for idx, item in enumerate(group):
        src = item.get("media", "")
        entry = {"type": "photo"}
        if _is_local_path(src):
            attach_name = f"file{idx}"
            entry["media"] = f"attach://{attach_name}"
            files[attach_name] = open(src, "rb")
        else:
            entry["media"] = src
        item_caption = item.get("caption") or (caption if idx == 0 else "")
        if item_caption:
            entry["caption"] = item_caption[:1024]
            entry["parse_mode"] = "HTML"
        input_media.append(entry)

    url = TG_BASE.format(token=token, method="sendMediaGroup")
    try:
        if files:
            # Multipart: media JSON travels as a form field alongside the files.
            data = {"chat_id": chat_id, "media": json.dumps(input_media)}
            r = requests.post(url, data=data, files=files, timeout=120)
        else:
            r = requests.post(
                url,
                json={"chat_id": chat_id, "media": input_media},
                timeout=60,
            )
        resp = r.json()
        if not resp.get("ok"):
            log.warning("sendMediaGroup error: %s", resp.get("description", "?"))
        return bool(resp.get("ok"))
    except Exception as e:
        log.error("sendMediaGroup exception: %s", e)
        return False
    finally:
        for fh in files.values():
            try:
                fh.close()
            except Exception:
                pass


def send_photo_to_commander(
    photo: str, caption: str = "", source: str = "SYSTEM"
) -> bool:
    """Module-level entry mirroring send_to_relay — lets any Wing script push a
    photo to the Commander's C2 channel.

        from thunderbird_telegram_gw import send_photo_to_commander
        send_photo_to_commander("/path/chart.png", "McLeod FPD trend", source="Brief")

    Routes to D2MC2C (Commander C2). Falls back to relay channel if D2MC2C token
    is unset. Returns True on success.
    """
    cap = caption
    if source and source != "SYSTEM" and cap:
        cap = f"[{source}] {cap}"
    if TOKEN_D2MC2C:
        return tg_send_photo(TOKEN_D2MC2C, COMMANDER_ID, photo, cap)
    if TOKEN_RELAY and RELAY_CHAT_ID:
        return tg_send_photo(TOKEN_RELAY, RELAY_CHAT_ID, photo, cap)
    log.warning("send_photo_to_commander: no D2MC2C or relay token configured")
    return False


def send_media_group_to_commander(
    media: list, caption: str = "", source: str = "SYSTEM"
) -> bool:
    """Module-level album entry mirroring send_to_relay. Pushes 2–10 images to
    the Commander's C2 channel (e.g. a ship photo set)."""
    cap = caption
    if source and source != "SYSTEM" and cap:
        cap = f"[{source}] {cap}"
    if TOKEN_D2MC2C:
        return tg_send_media_group(TOKEN_D2MC2C, COMMANDER_ID, media, cap)
    if TOKEN_RELAY and RELAY_CHAT_ID:
        return tg_send_media_group(TOKEN_RELAY, RELAY_CHAT_ID, media, cap)
    log.warning("send_media_group_to_commander: no D2MC2C or relay token configured")
    return False


import re  # noqa: E402 — needed for tg_send_chunks fallback above


# ── Engine: Claude headless ───────────────────────────────────────────────────


def _build_hale_claude_prompt(context_text: str, message: str) -> str:
    """Build the full prompt for Claude/Hale engine."""
    persona = _PERSONA_CACHE.get("hale_system", "")
    memory_snip = _PERSONA_CACHE.get("hale_memory_snippet", "")

    # P4: live state injection — so Telegram-Hale can answer "what's the McLeod
    # FPD / what's overdue" from current hale_state.json (single-source helper).
    state_summary = ""
    try:
        from core.ai_infra.hale_persona_loader import load_state_summary
        state_summary = load_state_summary()
    except Exception:
        pass

    parts = []
    if persona:
        parts.append(persona)
    if state_summary:
        parts.append(f"\n\n---\n{state_summary}")
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
    env.pop("ANTHROPIC_BASE_URL", None)  # Strip MAX proxy URL — breaks headless Claude
    _creds = Path.home() / ".claude" / ".credentials.json"
    if _creds.exists():
        try:
            _tok = json.loads(_creds.read_text()).get("claudeAiOauth", {}).get("accessToken")
            if _tok:
                env["CLAUDE_CODE_OAUTH_TOKEN"] = _tok
        except Exception:
            pass

    try:
        # Use -p - (stdin) to avoid OSError: Argument list too long on large prompts
        result = subprocess.run(
            [
                "/home/john/.local/bin/claude",
                "--model",
                model,
                "-p",
                "-",
                "--output-format",
                "text",
                "--dangerously-skip-permissions",
            ],
            input=prompt,
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

def _strip_ansi(text: str) -> str:
    """Strip ANSI escape codes and OpenCode build-status lines from output."""
    import re
    text = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text)
    text = re.sub(r'^> build .*', '', text, flags=re.MULTILINE)
    return text.strip()

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
                timeout=OPENCODE_TIMEOUT,
                cwd=str(THUNDERBIRD),
                env=env,
            )
            output = _strip_ansi(f"{result.stdout}\n{result.stderr}")
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
        if p_opencode_cmd.match(lower):
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
        if p_opencode_cmd.match(lower):
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

    # Access control:
    # D2MC2C = Commander C2 only (command and control — no other users)
    # HaleD2M = Commander only (personal Hale chat)
    # Dani = open to anyone (client-facing concierge)
    # Relay = system-only (no user interaction)
    if bot_name in ("D2MC2C", "HaleD2M") and user_id != COMMANDER_ID:
        log.warning("[%s] Rejected non-Commander user_id=%d", bot_name, user_id)
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
        elif cmd == "/brief":
            handle_brief(token, chat_id)
            return
        elif cmd == "/help":
            handle_help(token, chat_id, bot_name)
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
        elif cmd == "/agent":
            # MISSION-180: full-MCP async delegation. Tool-needing requests run a
            # detached headless Hale agent (Gmail/Drive/TESS/wing tools) off the poll
            # loop and deliver the result back here. Commander + Hale bots only.
            if user_id != COMMANDER_ID or bot_name not in ("D2MC2C", "HaleD2M"):
                tg_send(token, chat_id, "🦅 /agent is Commander-only on the C2 channel.")
                return
            task = " ".join(msg.split()[1:]).strip()
            if not task:
                tg_send(token, chat_id, "Usage: /agent &lt;task that needs tools — e.g. check my inbox, draft a reply, look up a booking&gt;")
                return
            try:
                import subprocess as _sp_agent
                _sp_agent.Popen(
                    [sys.executable, str(THUNDERBIRD / "OpsCenter" / "telegram_async_agent.py"),
                     "--token", token, "--chat-id", str(chat_id),
                     "--task", task, "--model", "sonnet"],
                    stdout=open(THUNDERBIRD / "logs" / "telegram_async_agent.log", "a"),
                    stderr=_sp_agent.STDOUT,
                    start_new_session=True,   # detached — poll loop never blocks
                    cwd=str(THUNDERBIRD),
                )
                tg_send(token, chat_id, "🦅 Wilco — on it with full tools. I'll deliver the result here shortly.")
            except Exception as e:
                tg_send(token, chat_id, f"🦅 Couldn't launch agent: {e}")
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
    # SECURITY (MISSION-180): the public-facing Dani bot must never expose an
    # internal engine (Hale/OpenCode) to a non-Commander user. A client typing
    # "hale, ..." to Dani was reaching Hale's full COS persona. Cross-bot
    # forwarding from Dani is Commander-only; for the public it falls through to
    # normal Dani handling.
    if forward_target and bot_name == "Dani" and user_id != COMMANDER_ID:
        forward_target = None
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
    
    # TTS stub removed — synthesize_speech() is a no-op (TTS_AVAILABLE=False).
    # Remove this comment when real TTS is implemented.

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
    # Haiku default for Telegram C2 chat — Sonnet auto-escalates via keyword routing
    model = model_override or HAIKU_MODEL
    return call_claude_engine(prompt, model=model)


def hale_chat_engine(
    context_text: str, message: str, model_override: str | None
) -> str:
    """HaleD2M conversational channel — Claude Code (Haiku default, Sonnet on keywords)."""
    prompt = _build_hale_claude_prompt(context_text, message)
    model = model_override or HAIKU_MODEL
    return call_claude_engine(prompt, model=model)


def dani_claude_engine(
    context_text: str, message: str, model_override: str | None
) -> str:
    prompt = _build_dani_claude_prompt(context_text, message)
    # Haiku default — Sonnet on model_override or keyword escalation
    model = model_override or HAIKU_MODEL
    return call_claude_engine(prompt, model=model)


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
            # M-153 — per-update guard. A single malformed update or a failed
            # thread spawn must not kill the poll thread (which main() cannot
            # resurrect — only a full process restart recovers). Advance the
            # offset first so a poison update is never re-fetched, then handle
            # the body defensively.
            try:
                offset = update["update_id"] + 1
            except Exception as e:
                log.error("[%s] Malformed update (no update_id): %s", bot_name, e)
                continue

            try:
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
            except Exception as e:
                log.error("[%s] Update dispatch failed (continuing): %s", bot_name, e)
                continue


        # Brief sleep between polls to avoid hammering Telegram
        time.sleep(POLL_INTERVAL)


# ── D2M Channels Relay ────────────────────────────────────────────────────────

def send_to_relay(message: str, source: str = "SYSTEM") -> bool:
    """
    Send a message to D2M Channels (the system relay channel).
    ALL automated Wing messages go here — never to D2MC2C directly.

    Usage from any script:
        from thunderbird_telegram_gw import send_to_relay
        send_to_relay("Lifecycle alert: McLeod FPD overdue", source="Lifecycle")

    Or standalone:
        python3 thunderbird_telegram_gw.py --relay "message" --source "OC"
    """
    if not TOKEN_RELAY or not RELAY_CHAT_ID:
        log.warning("Relay not configured — message dropped: %s", message[:80])
        return False
    prefix = f"[{source}] " if source and source != "SYSTEM" else ""
    text = f"{prefix}{message}"
    return tg_send(TOKEN_RELAY, RELAY_CHAT_ID, text[:4096])


def relay_poll_loop() -> None:
    """
    D2M Channels relay thread — OC↔CC bidirectional communication.

    Two event sources:
    1. Telegram D2M Channels: Commander-sent @CC: and @OC: directives
    2. relay_queue.jsonl: messages from OC→CC (file-based, since bots can't
       receive their own messages via getUpdates)

    All responses posted to D2M Channels for Commander visibility.
    """
    log.info("[Relay] D2M Channels OC↔CC relay starting (chat_id=%d)", RELAY_CHAT_ID)

    relay_queue = THUNDERBIRD / "OpsCenter" / "relay_queue.jsonl"
    oc_inbox    = THUNDERBIRD / "OpsCenter" / "collaboration" / "opencode_inbox.md"
    cc_inbox    = THUNDERBIRD / "OpsCenter" / "collaboration" / "claude_inbox.md"

    offset   = 0
    _backoff = 5

    def _drain_relay_queue():
        """Process pending OC→CC messages from relay_queue.jsonl."""
        if not relay_queue.exists():
            return
        try:
            raw_lines = relay_queue.read_text().splitlines()
        except Exception:
            return

        # Parse all entries; track updates by id so rewrite is correct
        entries = []
        for line in raw_lines:
            try:
                entries.append(json.loads(line))
            except Exception:
                entries.append(line)  # keep malformed lines as-is

        changed = False
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            if entry.get("to") != "CC" or entry.get("status") != "pending":
                continue
            msg_id   = entry["id"]
            from_app = entry.get("from", "OC")
            message  = entry.get("message", "")
            priority = entry.get("priority", "normal")
            log.info("[Relay] OC→CC queue item #%s: %s...", msg_id, message[:60])

            tg_send(TOKEN_RELAY, RELAY_CHAT_ID,
                    f"📨 <b>[{from_app}→CC]</b> #{msg_id} received — processing...")

            prompt   = _build_hale_claude_prompt("", f"[From {from_app}] {message}")
            response = call_claude_engine(prompt, model=HAIKU_MODEL)

            tg_send(TOKEN_RELAY, RELAY_CHAT_ID,
                    f"✅ <b>[CC→{from_app}]</b> #{msg_id}\n{response[:3600]}")

            ts = __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            try:
                with open(oc_inbox, "a") as f:
                    f.write(
                        f"\n---\n## CC-REPLY-{msg_id} — {ts}\n"
                        f"priority: {priority}\nstatus: UNREAD\ntask: |\n"
                        + "\n".join("  " + l for l in response.splitlines()) + "\n"
                    )
            except Exception as e:
                log.error("[Relay] OC inbox write failed: %s", e)

            # Update status in-place on the dict (entries list holds the same objects)
            entry["status"] = "processed"
            entry["processed_at"] = ts
            changed = True

        if changed:
            # Rewrite using the already-parsed (and mutated) entry dicts
            updated = []
            for e in entries:
                if isinstance(e, dict):
                    updated.append(json.dumps(e))
                else:
                    updated.append(str(e))
            relay_queue.write_text("\n".join(updated) + "\n")

    while True:
        # ── Source 1: relay_queue.jsonl (OC→CC file-based messages) ─────────
        try:
            _drain_relay_queue()
        except Exception as e:
            log.error("[Relay] Queue drain error: %s", e)

        # ── Source 2: Telegram D2M Channels (Commander @CC:/@OC: directives) ─
        try:
            updates = tg_get_updates(TOKEN_RELAY, offset=offset)
            _backoff = 5
        except Exception as e:
            log.error("[Relay] getUpdates exception: %s", e)
            time.sleep(_backoff)
            _backoff = min(_backoff * 2, 60)
            continue

        for update in updates:
            # M-153 — per-update guard (same rationale as bot_poll_loop): a
            # malformed update or an inline engine failure must not kill the
            # relay thread.
            try:
                offset = update["update_id"] + 1
            except Exception as e:
                log.error("[Relay] Malformed update (no update_id): %s", e)
                continue
            try:
                msg_obj = update.get("message") or update.get("channel_post")
                if not msg_obj:
                    continue
                user_id = msg_obj.get("from", {}).get("id", 0)
                text = msg_obj.get("text", "").strip()
                if not text:
                    continue

                # Only process Commander's @CC:/@OC: directives
                if user_id != COMMANDER_ID:
                    continue

                if text.upper().startswith("@CC:"):
                    task = text[4:].strip()
                    log.info("[Relay] Commander @CC: %s...", task[:60])
                    tg_typing(TOKEN_RELAY, RELAY_CHAT_ID)
                    prompt = _build_hale_claude_prompt("", task)
                    response = call_claude_engine(prompt, model=HAIKU_MODEL)
                    tg_send(TOKEN_RELAY, RELAY_CHAT_ID,
                            f"<b>[CC]</b> {response[:3800]}")
                    continue

                if text.upper().startswith("@OC:"):
                    task = text[4:].strip()
                    log.info("[Relay] Commander @OC: forwarding to OC inbox")
                    ts = __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M")
                    try:
                        with open(oc_inbox, "a") as f:
                            f.write(f"\n---\n## COMMANDER→OC — {ts}\n{task}\n")
                        tg_send(TOKEN_RELAY, RELAY_CHAT_ID,
                                f"<b>[Relay→OC]</b> Queued in OC inbox: {task[:100]}")
                    except Exception as e:
                        log.error("[Relay] OC inbox write failed: %s", e)
                    continue
            except Exception as e:
                log.error("[Relay] Update dispatch failed (continuing): %s", e)
                continue

        # Check queue every 15 seconds
        time.sleep(15)


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    log.info("═══════════════════════════════════════")
    log.info("Thunderbird Telegram Gateway v2.0 — Four-Bot Architecture")
    log.info("D2MC2C=C2  HaleD2M=Chat  Dani=Open  Relay=System+OC-CC")
    log.info("All engines: Claude Code (Haiku/Sonnet). No OpenCode. No OpenRouter defaults.")
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
    if not TOKEN_HALE:
        log.warning("TELEGRAM_GOOSE_TOKEN not set — HaleD2M chat bot will be skipped")
    if not TOKEN_RELAY:
        log.warning("TELEGRAM_RELAY_TOKEN not set — D2M Channels relay will be skipped")
    elif not RELAY_CHAT_ID:
        log.warning("TELEGRAM_RELAY_CHAT_ID not set — relay bot won't post to channel")

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
            env_test.pop("ANTHROPIC_BASE_URL", None)  # strip proxy URL same as call_claude_engine
            result = subprocess.run(
                ["/home/john/.local/bin/claude", "--model", SONNET_MODEL,
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

    # ── Bot roles ────────────────────────────────────────────────────────────
    # D2MC2C  → Commander C2: he directs, Wing responds. No automated sends.
    # HaleD2M → Commander ↔ Hale conversational chat.
    # Dani    → Open to all: clients, prospects, anyone. Concierge voice.
    # Relay   → D2M Channels: all system/auto messages + OC↔CC relay.
    # All engines → Claude Code (Haiku default, Sonnet on keyword upgrade).
    bot_configs = [
        {
            "token": TOKEN_D2MC2C,
            "bot_name": "D2MC2C",
            "ctx_file": CTX_D2MC2C,
            "engine_fn": hale_claude_engine,
            "assistant_label": "Hale",
        },
        {
            "token": TOKEN_HALE,
            "bot_name": "HaleD2M",
            "ctx_file": CTX_OPENCODE,
            "engine_fn": hale_chat_engine,
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

    # Drop bots with missing tokens
    bot_configs = [b for b in bot_configs if b["token"]]

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

    # D2M Channels relay thread (OC↔CC relay + all system messages)
    if TOKEN_RELAY and RELAY_CHAT_ID:
        relay_thread = threading.Thread(
            target=relay_poll_loop,
            name="poll_Relay",
            daemon=True,
        )
        relay_thread.start()
        threads.append(relay_thread)
        log.info("[Relay] D2M Channels relay thread started (chat_id=%d)", RELAY_CHAT_ID)

    active = len([b for b in bot_configs if b["token"]])
    log.info("%d bot threads running. Gateway v2.0 LIVE.", active)

    # Keep main thread alive — monitor worker threads.
    # M-153 liveness fix: a dead poll thread = that bot is SILENTLY dead while
    # the process stays alive, so systemd (Restart=always) never sees a fault and
    # the Commander's C2 goes quiet with no recovery. Previously we only logged it.
    # Now: log the dead thread, then force a non-zero process exit so the hardened
    # unit restarts the WHOLE gateway cleanly (re-spawning all poll threads with
    # fresh offsets). The StartLimitIntervalSec=300/StartLimitBurst=5 guard in the
    # unit prevents a tight crash-loop if the death is a persistent code/auth fault.
    # os._exit is used (not sys.exit) so a non-daemon thread can't swallow the exit.
    try:
        while True:
            dead = [t for t in threads if not t.is_alive()]
            if dead:
                for d in dead:
                    log.error(
                        "Thread %s died — bot silently down. Exiting process so "
                        "systemd restarts the full gateway (M-153 liveness).",
                        d.name,
                    )
                os._exit(1)
            time.sleep(30)
    except KeyboardInterrupt:
        log.info("Gateway shutting down (KeyboardInterrupt)")


if __name__ == "__main__":
    # Allow send_to_relay from command line:
    # python3 thunderbird_telegram_gw.py --relay "message" --source "Metronome"
    if len(sys.argv) > 1 and sys.argv[1] == "--relay":
        _load_env_file("/home/john/Thunderbird/.env")
        _load_env_file("/home/john/Thunderbird/config/telegram_gw.env")
        msg = sys.argv[2] if len(sys.argv) > 2 else ""
        src = sys.argv[4] if len(sys.argv) > 4 and sys.argv[3] == "--source" else "SYSTEM"
        if msg:
            ok = send_to_relay(msg, source=src)
            sys.exit(0 if ok else 1)
        sys.exit(1)

    # M-148 — send a photo to the Commander C2 channel:
    # python3 thunderbird_telegram_gw.py --photo /path/img.png --caption "Trend" --source "Brief"
    if len(sys.argv) > 1 and sys.argv[1] == "--photo":
        import argparse
        _load_env_file("/home/john/Thunderbird/.env")
        _load_env_file("/home/john/Thunderbird/config/telegram_gw.env")
        ap = argparse.ArgumentParser(prog="thunderbird_telegram_gw.py")
        ap.add_argument("--photo", required=True, help="URL, file_id, or local path")
        ap.add_argument("--caption", default="")
        ap.add_argument("--source", default="SYSTEM")
        args = ap.parse_args()
        ok = send_photo_to_commander(args.photo, caption=args.caption, source=args.source)
        sys.exit(0 if ok else 1)

    # M-148 — send an album (2–10 images) to the Commander C2 channel:
    # python3 thunderbird_telegram_gw.py --media-group img1.png img2.png --caption "Ship set"
    if len(sys.argv) > 1 and sys.argv[1] == "--media-group":
        import argparse
        _load_env_file("/home/john/Thunderbird/.env")
        _load_env_file("/home/john/Thunderbird/config/telegram_gw.env")
        ap = argparse.ArgumentParser(prog="thunderbird_telegram_gw.py")
        ap.add_argument("--media-group", dest="media", nargs="+", required=True,
                        help="2–10 URLs, file_ids, or local paths")
        ap.add_argument("--caption", default="")
        ap.add_argument("--source", default="SYSTEM")
        args = ap.parse_args()
        ok = send_media_group_to_commander(args.media, caption=args.caption, source=args.source)
        sys.exit(0 if ok else 1)

    main()
