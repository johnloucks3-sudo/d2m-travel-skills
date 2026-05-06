#!/usr/bin/env python3
"""
telegram_hale_router.py — Hale Dispatcher integration for Thunderbird Telegram Gateway.

Pure-logic module. thunderbird_telegram_gw.py stays untouched; wire in via the
hooks documented below.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DEPLOYMENT HOOKS for thunderbird_telegram_gw.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STEP 1 — Add import at top of thunderbird_telegram_gw.py (after existing imports):

    from telegram_hale_router import (
        should_use_hale, get_hale_response, dispatch_status_text,
        savings_text, record_turn, check_correction,
    )

STEP 2 — Add three commands inside handle_message()'s slash-command block
          (after the /reject handler, before the final `else: unknown command`):

    elif cmd == "/dispatch_status":
        tg_send(token, chat_id, dispatch_status_text())
        return
    elif cmd == "/savings":
        tg_send(token, chat_id, savings_text())
        return
    elif cmd == "/dispatch":
        dispatch_text = " ".join(msg.split()[1:]).strip()
        if dispatch_text:
            tg_typing(token, chat_id)
            resp = get_hale_response(dispatch_text)
            chunks = fmt_process(f"<b>Hale | Dispatcher</b>\\n\\n{resp}", CHUNK_SIZE)
            tg_send_chunks(token, chat_id, chunks)
        else:
            tg_send(token, chat_id, "Usage: /dispatch &lt;request&gt;")
        return

STEP 3 — Add correction detection + Hale routing in handle_message()
          BEFORE the `tg_typing(token, chat_id)` line in the non-slash path:

    # Correction detection: check incoming message against the prior turn (any engine)
    if user_id == COMMANDER_ID:
        check_correction(chat_id, msg)

    # Hale-tier auto-routing (Sonnet/Opus tier messages bypass existing engines)
    if (user_id == COMMANDER_ID
            and not model_override
            and not openrouter_override
            and should_use_hale(msg)):
        tg_typing(token, chat_id)
        resp = get_hale_response(msg, channel="telegram")
        record_turn(chat_id, msg, resp)
        full = f"<b>{assistant_label} | Dispatcher</b>\\n\\n{resp}"
        tg_send_chunks(token, chat_id, fmt_process(full, CHUNK_SIZE))
        _append_exchange(ctx_file, msg, resp[:800], "Commander", assistant_label)
        return

STEP 4 — Record ALL turns so correction detection covers routine-engine responses too.
          Add this call RIGHT AFTER the existing `_append_exchange(ctx_file, ...)` call
          at the bottom of handle_message() (~line 1152 in thunderbird_telegram_gw.py):

    # Track last turn for correction detection (covers both Hale-tier and routine engine)
    record_turn(chat_id, msg, raw_response[:800])

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from __future__ import annotations

import sys
import threading
from pathlib import Path
from typing import Optional

_ROOT = Path("/home/john/Thunderbird")
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if str(_ROOT / "OpsCenter") not in sys.path:
    sys.path.insert(0, str(_ROOT / "OpsCenter"))

from agents.hale_substrate_chain import select_substrate, record_correction
from agents.hale_dispatcher_runtime import dispatch_with_telemetry
from core.ops.dispatch_telemetry import status_report, daily_rollup
from core.ops.correction_memory import CorrectionMemory

# ── Per-chat last-turn tracker (for correction detection) ─────────────────────
# Holds {chat_id: {"request": str, "response": str}} — last 1 turn per chat.
# Thread-safe: the gateway dispatches message handlers on daemon threads.
_last_turn: dict[int, dict[str, str]] = {}
_turn_lock = threading.Lock()


# ── Public API ────────────────────────────────────────────────────────────────

def should_use_hale(request: str) -> bool:
    """Return True if this request should route through the Hale dispatcher (Sonnet/Opus tier)."""
    sel = select_substrate(request)
    return sel["substrate"] in ("sonnet", "opus")


def get_hale_response(request: str, channel: str = "telegram") -> str:
    """Dispatch through Hale and return the response string.

    Calls dispatch_with_telemetry internally; callers only see the text.
    """
    result = dispatch_with_telemetry(request, default_substrate="haiku")
    return result["response"]


def dispatch_status_text() -> str:
    """Return formatted dispatch telemetry status for /dispatch_status command."""
    return status_report()


def savings_text() -> str:
    """Return a one-liner savings summary for /savings command."""
    r = daily_rollup()
    if r["total_dispatches"] == 0:
        return "📊 No dispatch activity logged yet today."
    return (
        f"Today: ${r['savings_total_usd']:.4f} saved vs all-API. "
        f"MAX OAuth used: {r['max_oauth_pct']:.0f}%."
    )


def record_turn(chat_id: int, request: str, response: str) -> None:
    """Store the last outgoing turn for correction detection on the next message.

    Call this AFTER sending a response, passing the user request and bot response.
    """
    with _turn_lock:
        _last_turn[chat_id] = {"request": request, "response": response}


def check_correction(chat_id: int, incoming_text: str) -> None:
    """Detect if incoming_text is a Commander correction; if so, log it to Layer 4.

    Must be called BEFORE processing the new message (the prior turn is still in _last_turn).
    No-op if: no prior turn, or incoming message is not a correction pattern.
    """
    if not CorrectionMemory.is_correction(incoming_text):
        return
    with _turn_lock:
        prior = _last_turn.get(chat_id)
    if prior is None:
        return
    record_correction(
        commander_message=incoming_text,
        prior_request=prior["request"],
        prior_response=prior["response"],
    )
