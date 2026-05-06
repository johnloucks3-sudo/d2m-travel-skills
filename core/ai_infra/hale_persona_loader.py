#!/usr/bin/env python3
"""
Hale Persona Loader — Ensures Hale identity persists across all channels.

When a request is classified as Hale-tier (Layer 1) and routed to Sonnet/Opus,
this module prepends the Hale persona file as a system prompt so the model
actually responds AS Hale, not as generic Claude.

Used by:
- agents/hale_dispatcher_runtime.py  (auto-wraps Hale-tier dispatches)
- core/communication/thunderbird_telegram_gw.py  (per-message persona load)
- OpenCode integration shim (when Hale-tier work is dispatched there)
- Email tasking handler

Cache TTL: 60 seconds (persona file rarely changes; reload picks up edits)
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

_PERSONA_PATH = Path("/home/john/Thunderbird/Personas/hale_cos.md")
_CHARTER_PATH = Path("/home/john/Thunderbird/standing_orders/SO_HALE_REAL_AUTONOMY_20260504.md")

_CACHE: dict = {"text": None, "loaded_at": 0.0}
_CACHE_TTL_S = 60


def _load_persona_text() -> str:
    """Load Hale persona + autonomy charter, with TTL cache."""
    now = time.time()
    if _CACHE["text"] is not None and (now - _CACHE["loaded_at"]) < _CACHE_TTL_S:
        return _CACHE["text"]

    parts = []
    if _PERSONA_PATH.exists():
        parts.append("# HALE PERSONA — IDENTITY & AUTHORITY\n")
        parts.append(_PERSONA_PATH.read_text())
    if _CHARTER_PATH.exists():
        parts.append("\n\n# AUTONOMY CHARTER — OPERATING CONSTITUTION\n")
        parts.append(_CHARTER_PATH.read_text())

    text = "\n".join(parts) if parts else ""
    _CACHE["text"] = text
    _CACHE["loaded_at"] = now
    return text


def wrap_with_persona(request: str, channel: Optional[str] = None) -> str:
    """Prepend Hale persona context to a request.

    Args:
        request: The raw user request.
        channel: Optional channel hint ('telegram', 'claude_code', 'opencode',
                 'email'). Affects how strongly the persona is signaled.

    Returns:
        A composed prompt that signals the model to respond AS Hale.
    """
    persona = _load_persona_text()
    if not persona:
        # Fallback if persona files missing — at least set the role
        return (
            "You are Col Victoria 'Iron Vic' Hale, USAF (Ret.), O-6. "
            "Chief of Staff to Commander John Loucks. Operate at 95% autonomy. "
            "Execute first, report results. Banned: 'Should I', 'Would you like', "
            "options menus. Required: past tense + brief reason.\n\n"
            f"Commander's request:\n{request}"
        )

    channel_hint = ""
    if channel == "telegram":
        channel_hint = "\nResponse channel: Telegram. Keep messages tight, scannable, ≤4096 chars per message.\n"
    elif channel == "email":
        channel_hint = "\nResponse channel: Email to johnloucks3@gmail.com. Brief format. Sign off 'Thanks'.\n"
    elif channel == "opencode":
        channel_hint = "\nResponse channel: OpenCode subprocess. Output file-bound; structured deliverables.\n"
    elif channel == "claude_code":
        channel_hint = "\nResponse channel: Claude Code interactive session.\n"

    return (
        f"{persona}\n\n"
        f"---\n"
        f"# ACTIVE SESSION{channel_hint}\n"
        f"---\n\n"
        f"Commander's request:\n{request}\n"
    )


def get_persona_summary() -> dict:
    """Return cache state + file existence for diagnostics."""
    return {
        "persona_path": str(_PERSONA_PATH),
        "persona_exists": _PERSONA_PATH.exists(),
        "charter_path": str(_CHARTER_PATH),
        "charter_exists": _CHARTER_PATH.exists(),
        "cache_age_s": time.time() - _CACHE["loaded_at"] if _CACHE["text"] else None,
        "persona_chars": len(_CACHE["text"]) if _CACHE["text"] else 0,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(get_persona_summary(), indent=2))
    print()
    sample = wrap_with_persona(
        "What's the McLeod FPD status?", channel="telegram"
    )
    print(f"Wrapped prompt: {len(sample):,} chars")
    print(sample[:400] + "...\n[truncated]")
