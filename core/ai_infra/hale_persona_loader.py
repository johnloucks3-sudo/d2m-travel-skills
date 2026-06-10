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
_CHARTER_PATH = Path("/home/john/Thunderbird/standing_orders/archive/SO_HALE_REAL_AUTONOMY_20260504.md")

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


def load_compact_persona() -> str:
    """Return a token-bounded persona for thin channels (Telegram, Signal).

    GUARANTEES the four gates are always included — assembled by section
    marker, never by raw char count, so a growing persona file can never
    silently truncate the authority/gates section (the 2026-06-10 audit bug).

    Includes: Layer 1 (identity), Layer 2 (authority + the four gates),
    Layer 4 (voice). Drops the extended governance layers that a C2
    responder does not need per-message. Falls back to a gates-inclusive
    char floor if section markers ever move.
    """
    if not _PERSONA_PATH.exists():
        return ""
    full = _PERSONA_PATH.read_text()

    # Core: identity + authority + gates (start → just before FAILURE MODE block)
    core_end = full.find("## FAILURE MODE CORRECTIONS")
    if core_end == -1:
        # Marker moved — fall back to a floor that still clears the gates
        # (Three Gates section sits ~char 7480; 9000 guarantees inclusion).
        core = full[:9000]
    else:
        core = full[:core_end].rstrip()

    # Voice layer (Layer 4 → before PERSISTENT FILES table)
    voice = ""
    v_start = full.find("## LAYER 4 — VOICE")
    if v_start != -1:
        v_end = full.find("## PERSISTENT FILES", v_start)
        voice = full[v_start:v_end].rstrip() if v_end != -1 else full[v_start:].rstrip()

    # Hard safety check: the gates MUST be present. If not, ship full file.
    if "Three Gates You Cannot Open" not in core:
        return full

    return core + ("\n\n" + voice if voice else "")


def wrap_with_persona(request: str, channel: Optional[str] = None,
                      compact: bool = False) -> str:
    """Prepend Hale persona context to a request.

    Args:
        request: The raw user request.
        channel: Optional channel hint ('telegram', 'claude_code', 'opencode',
                 'email'). Affects how strongly the persona is signaled.
        compact: If True, use the token-bounded gates-guaranteed persona
                 (for thin per-message channels like Telegram/Signal).

    Returns:
        A composed prompt that signals the model to respond AS Hale.
    """
    persona = load_compact_persona() if compact else _load_persona_text()
    if not persona:
        # Fallback if persona files missing — at least set the role
        return (
            "You are Ms. Victoria 'Victory' Hale, SES-6 — VCSAF-equivalent. "
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


_STATE_PATH = Path("/home/john/Thunderbird/hale_state.json")


def load_state_summary(max_tasks: int = 6) -> str:
    """Return a tight live-state summary for per-turn injection on thin channels.

    Single source so Telegram, Signal, and email all answer "what's the McLeod
    FPD / what's overdue" from the same data. Reads hale_state.json (financial
    pulse, open P0/P1 tasks, deferred FPD alerts). Kept compact (~1-1.5K).
    Returns "" on any error — never blocks a reply.
    """
    try:
        import json as _json
        s = _json.loads(_STATE_PATH.read_text())
    except Exception:
        return ""

    lines = ["## LIVE STATE (hale_state.json — current)"]

    fp = s.get("financial_pulse", {})
    pipe = fp.get("total_d2m_pipeline") or fp.get("pipeline_d2m_share_upcoming")
    comm = fp.get("pipeline_commission_upcoming")
    if pipe:
        lines.append(f"- Pipeline: ${pipe:,.2f} D2M share"
                     + (f" · commission ${comm:,.2f}" if comm else ""))

    alerts = s.get("deferred_alerts", [])
    for a in alerts[:3]:
        msg = a.get("message", "")
        if msg:
            lines.append(f"- ALERT: {msg[:140]}")

    tasks = s.get("open_tasks", [])
    p0 = [t for t in tasks if t.get("priority") == "P0"][:max_tasks]
    if p0:
        lines.append(f"- Open P0 ({len(p0)} shown): "
                     + "; ".join(f"{t.get('id')} {t.get('title','')[:40]}" for t in p0))

    return "\n".join(lines) if len(lines) > 1 else ""


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
