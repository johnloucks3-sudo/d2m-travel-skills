"""
hale_unified_classifier.py — Shared classifier for all Hale comms channels.
All three gateways (Email, Telegram, Signal) call classify_message() before dispatch.
One logic, three channels.

Checked by A7 Sterling verify_comms_health.py L2.1–L2.5.
"""

import re
from typing import Optional

# ---------------------------------------------------------------------------
# Enums (Sterling L2.4 validated)
# ---------------------------------------------------------------------------
VALID_INTENTS  = {"task", "chat", "intel", "client", "urgent", "clarification"}
VALID_BRAINS   = {"haiku", "sonnet", "opus", "self"}
VALID_PERSONAS = {"hale", "dani"}
VALID_FORMATS  = {"tq_talking", "tq_background", "plain", "stationery", "informal"}
VALID_PRIORITIES = {"P0", "P1", "P2", "P3"}

# Commander-override prefixes — Sterling L2.5
_OVERRIDE_PATTERNS = {
    re.compile(r"^OPUS\s*:", re.IGNORECASE): "opus",
    re.compile(r"^SONNET\s*:", re.IGNORECASE): "sonnet",
    re.compile(r"^HAIKU\s*:", re.IGNORECASE): "haiku",
}

# Task verbs that signal work requests
_TASK_VERBS = re.compile(
    r"\b(build|fix|draft|analyze|analyse|task|write|deploy|generate|update|"
    r"create|research|find|pull|run|review|check|send|schedule|book)\b",
    re.IGNORECASE,
)

# Client names for WF-17 gate detection (partial list — Hale adds as needed)
_CLIENT_NAMES = re.compile(
    r"\b(kuklinski|mcleod|furlow|nichols|westbrook|lyons|ely|britan)\b",
    re.IGNORECASE,
)

# Urgency signals
_URGENT_RE = re.compile(r"\b(urgent|p0|emergency|asap|immediate|now)\b", re.IGNORECASE)


def classify_message(
    text: str,
    channel: str,
    sender: str,
    thread_mode: Optional[str] = None,
) -> dict:
    """Classify an incoming message and return routing instructions.

    Args:
        text:        Raw message text.
        channel:     "email" | "telegram" | "signal"
        sender:      "commander" | sender identifier
        thread_mode: "first" | "continuation" — caller provides if known;
                     classifier uses "first" as safe default.

    Returns:
        {
            "intent":      "task|chat|intel|client|urgent|clarification",
            "brain":       "haiku|sonnet|opus|self",
            "persona":     "hale",
            "format":      "tq_talking|tq_background|plain|stationery|informal",
            "priority":    "P0|P1|P2|P3",
            "thread_mode": "first|continuation",
            "override":    None | "opus" | "sonnet" | "haiku",
        }
    """
    text = text or ""
    override = None

    # -- Step 1: Commander-override prefix (highest priority) ----------------
    for pattern, model in _OVERRIDE_PATTERNS.items():
        if pattern.match(text.strip()):
            override = model
            break

    # -- Step 2: Urgency ------------------------------------------------------
    is_urgent = bool(_URGENT_RE.search(text))

    # -- Step 3: Client name detection (WF-17 gate) ---------------------------
    is_client = bool(_CLIENT_NAMES.search(text))

    # -- Step 4: Task verb detection ------------------------------------------
    is_task = bool(_TASK_VERBS.search(text))

    # -- Step 5: Chat heuristic (short, question, no task verbs) --------------
    word_count = len(text.split())
    is_chat = (word_count < 50 and "?" in text and not is_task and not is_urgent)

    # -- Step 6: Intel heuristic ----------------------------------------------
    is_intel = any(kw in text.lower() for kw in (
        "intel", "news", "brief", "sitrep", "scan", "sweep", "report",
        "market", "competitor", "cruise line",
    ))

    # -------------------------------------------------------------------------
    # Routing table — ordered by priority
    # -------------------------------------------------------------------------
    if override:
        intent   = "task"
        brain    = override
        fmt      = "tq_background" if override == "opus" else "plain"
        priority = "P0" if override == "opus" else "P1"

    elif is_urgent:
        intent   = "urgent"
        brain    = "opus"
        fmt      = "plain"
        priority = "P0"

    elif is_client:
        intent   = "client"
        brain    = "sonnet"
        fmt      = "stationery"   # draft only — WF-17 gate holds for Commander
        priority = "P1"

    elif is_task:
        intent   = "task"
        brain    = "sonnet"
        fmt      = "tq_talking"
        priority = "P1"

    elif is_intel:
        intent   = "intel"
        brain    = "self"         # OpenCode handles intel natively
        fmt      = "plain"
        priority = "P2"

    elif is_chat:
        intent   = "chat"
        brain    = "haiku"
        fmt      = "informal"
        priority = "P2"

    else:
        # Default: treat as clarification, light brain
        intent   = "clarification"
        brain    = "self"
        fmt      = "informal"
        priority = "P3"

    # -- Channel format overrides --------------------------------------------
    if channel == "signal":
        # Signal is always plain — no stationery, no T&Q
        fmt = "plain"
    elif channel == "email" and thread_mode == "continuation":
        # Email thread continuations are informal prose (SO 2026-05-18)
        fmt = "informal"

    return {
        "intent":      intent,
        "brain":       brain,
        "persona":     "hale",       # always Hale — Dani is client-only
        "format":      fmt,
        "priority":    priority,
        "thread_mode": thread_mode or "first",
        "override":    override,
    }
