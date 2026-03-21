"""
Thunderbird Model Router v2 — Auto-Routing by Task Type
=========================================================
Classifies every inbound task and routes to the optimal Claude model tier:

  Opus   → Client-facing copy, principle extraction (nuance matters)
  Sonnet → Research, code generation, voice profiles, morning briefs
  Haiku  → Classification, data extraction, summarization (fast & cheap)

Specialty engines (Gemini, Grok, DeepSeek) retained for specific capabilities.
All Claude calls go through Anthropic SDK ($0 on Max plan).

Usage:
    from thunderbird_model_router import route_and_call, classify_task, TaskType

    # Auto-route based on prompt content
    result = route_and_call("You are Dani.", "Draft a welcome email for the Furlows")

    # Force a specific task type
    result = route_and_call("You are A2.", "Scan cruise intel", task_hint="research")

    # Legacy persona-based routing still works
    from thunderbird_model_router import route_call, smart_route
    result = smart_route("A3", "What's the status of Kuklinski bookings?")
"""

import os
import re
import json
import logging
import requests
import subprocess
import base64
from collections import defaultdict
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Model Usage Tags ──
MODEL_TAGS = {
    "opus": "Claude Opus",
    "sonnet": "Claude Sonnet",
    "haiku": "Claude Haiku",
    "fast": "Claude Sonnet",
    "premium": "Claude Opus",
    "light": "Claude Haiku",
    "kimi": "Claude Sonnet",
    "detail": "Claude Sonnet",
    "visionary": "Claude Opus",
    "gemini": "Gemini Flash",
    "workspace": "Gemini Flash",
    "research": "Grok",
    "grok": "Grok",
    "extraction": "DeepSeek (fenced)",
    "deepseek": "DeepSeek (fenced)",
    "claude": "Claude Sonnet",
}

# ── Log Paths ──
_MODEL_USAGE_LOG = Path(__file__).parent / "logs" / "model_usage.log"
_ROUTER_STATS_LOG = Path(__file__).parent / "logs" / "router_stats.jsonl"

# ── API Keys ──
# Groq ELIMINATED — all calls route to Claude via Anthropic SDK ($0 on Max plan)
# Backward-compat stubs: callers may import these even though Groq is dead
GROQ_API_KEY = ""   # ELIMINATED — stub for backward compat
GROQ_URL = ""       # ELIMINATED — stub for backward compat
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

TOGETHER_API_KEY = os.environ.get("TOGETHER_API_KEY", "")
TOGETHER_URL = "https://api.together.xyz/v1"
HF_API_KEY = os.environ.get("HF_API_KEY", "***REMOVED-SECRET***")
HF_INFERENCE_URL = "https://router.huggingface.co/hf-inference/models"

# Gemini 2.5 Flash — $0.30/$2.50 per 1M tokens
GOOGLE_AI_API_KEY = os.environ.get("GOOGLE_AI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

# Grok 4.1 Fast — $0.20/$0.50 per 1M tokens (OpenAI-compatible)
XAI_API_KEY = os.environ.get("XAI_API_KEY", "")
GROK_MODEL = "grok-4-1-fast"
GROK_URL = "https://api.x.ai/v1/chat/completions"

# DeepSeek V3 — $0.14/$0.28 per 1M tokens (OpenAI-compatible)
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = "deepseek-chat"
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"

# Together AI image models
FLUX_MODEL = "black-forest-labs/FLUX.1-schnell-Free"
FLUX_PRO_MODEL = "black-forest-labs/FLUX.1.1-pro"

# ============================================================
# TASK TYPES — Expanded for auto-routing
# ============================================================

class TaskType(Enum):
    """Task classification for automatic model selection."""
    # Existing types (backward compatible)
    OPERATIONAL = "operational"          # Status checks, data lookups
    ANALYTICAL = "analytical"            # Number crunching, comparisons, audits
    CREATIVE = "creative"               # Client copy, proposals, narratives
    STRATEGIC = "strategic"             # Business decisions, pricing, growth
    CRISIS = "crisis"                   # Time-sensitive logistics, problem solving
    CLASSIFICATION = "classification"   # Email triage, categorization
    IMAGE = "image"                     # Image generation (routes to FLUX.1)
    EXTRACTION = "extraction"           # Data extraction, parsing

    # New granular types for auto-routing
    CLIENT_FACING = "client_facing"          # Client emails, proposals → Opus
    RESEARCH = "research"                    # Destination/market research → Sonnet
    DATA_EXTRACTION = "data_extraction"      # Structured extraction → Haiku
    CODE_GENERATION = "code_generation"      # Code writing → Sonnet
    VOICE_PROFILE = "voice_profile"          # Voice/tone analysis → Sonnet
    MORNING_BRIEF = "morning_brief"          # Morning synthesis → Sonnet
    PRINCIPLE_EXTRACTION = "principle_extraction"  # Learning/nuance → Opus
    SUMMARIZATION = "summarization"          # Quick summaries → Haiku


# ============================================================
# MODEL SELECTION MAP — Task Type → Claude Model
# ============================================================

# Claude model IDs
CLAUDE_OPUS = "claude-opus-4-20250514"
CLAUDE_SONNET = "claude-sonnet-4-20250514"
CLAUDE_HAIKU = "claude-haiku-3-20250307"

MODEL_MAP: Dict[TaskType, str] = {
    # Opus — highest quality, nuance matters
    TaskType.CLIENT_FACING: CLAUDE_OPUS,
    TaskType.CREATIVE: CLAUDE_OPUS,
    TaskType.PRINCIPLE_EXTRACTION: CLAUDE_OPUS,
    TaskType.STRATEGIC: CLAUDE_OPUS,
    TaskType.CRISIS: CLAUDE_OPUS,

    # Sonnet — good quality, reasonable speed
    TaskType.RESEARCH: CLAUDE_SONNET,
    TaskType.CODE_GENERATION: CLAUDE_SONNET,
    TaskType.VOICE_PROFILE: CLAUDE_SONNET,
    TaskType.MORNING_BRIEF: CLAUDE_SONNET,
    TaskType.OPERATIONAL: CLAUDE_SONNET,
    TaskType.ANALYTICAL: CLAUDE_SONNET,

    # Haiku — fast & cheap
    TaskType.CLASSIFICATION: CLAUDE_HAIKU,
    TaskType.DATA_EXTRACTION: CLAUDE_HAIKU,
    TaskType.SUMMARIZATION: CLAUDE_HAIKU,
    TaskType.EXTRACTION: CLAUDE_HAIKU,

    # Special (not Claude)
    TaskType.IMAGE: "flux",  # handled separately
}

# Human-readable tier names for logging
MODEL_TIER = {
    CLAUDE_OPUS: "opus",
    CLAUDE_SONNET: "sonnet",
    CLAUDE_HAIKU: "haiku",
}

# Legacy model map — backward compatibility for callers referencing GROQ_MODELS
GROQ_MODELS = {
    "fast": CLAUDE_SONNET,
    "premium": CLAUDE_OPUS,
    "light": CLAUDE_HAIKU,
    "kimi": CLAUDE_SONNET,
    "detail": CLAUDE_SONNET,
    "visionary": CLAUDE_OPUS,
}

# Claude model — PRIMARY ENGINE
CLAUDE_MODEL = CLAUDE_SONNET  # default for _call_claude()

# Claude 1M context window — GA at standard pricing (no beta header needed)
CLAUDE_MAX_CONTEXT_TOKENS = 1_000_000
CLAUDE_DEFAULT_MAX_OUTPUT = 16_384  # generous default for Claude output


# ============================================================
# TASK CLASSIFICATION — Keyword-based, no API call needed
# ============================================================

# Classification rules: (task_type, keywords, priority)
# Higher priority checked first. First match wins.
_CLASSIFICATION_RULES: List[tuple] = [
    # Priority 1: Crisis (always check first)
    (TaskType.CRISIS, [
        "urgent", "emergency", "cancelled", "missed", "stranded",
        "delay", "problem", "crisis", "broken", "help immediately",
    ]),

    # Priority 2: Classification (Haiku — fast) — before client_facing
    #   "classify this email" should not trigger client_facing from email content
    (TaskType.CLASSIFICATION, [
        "classify", "categorize", "triage", "sort by", "label as",
        "which category", "is this a", "type of",
    ]),

    # Priority 3: Client-facing (Opus quality)
    (TaskType.CLIENT_FACING, [
        "client email", "email to client", "dear ", "email for ",
        "welcome email", "follow up email", "thank you note",
        "send to client", "client-facing", "guest communication",
        "concierge email", "concierge response",
    ]),

    # Priority 4: Principle extraction (Opus nuance) — before data_extraction
    (TaskType.PRINCIPLE_EXTRACTION, [
        "extract principle", "extract the principle", "learning rule",
        "capture the diff", "voice rule", "tone principle",
        "what did i change", "why did commander", "diff between",
        "what changed", "principle from",
    ]),

    # Priority 4: Code generation (Sonnet) — before creative ("write" overlap)
    (TaskType.CODE_GENERATION, [
        "write code", "write a script", "implement", "function(",
        "class ", "def ", "refactor", "debug", "fix the code",
        "add endpoint", "python", "javascript", "typescript",
        "api endpoint", "code review", "write a function",
        "code to parse", "code to handle",
    ]),

    # Priority 5: Voice profile (Sonnet analysis) — before creative ("voice" overlap)
    (TaskType.VOICE_PROFILE, [
        "voice profile", "tone analysis", "voice ledger", "voice rule",
        "how does he write", "writing style", "communication style",
    ]),

    # Priority 6: Morning brief (Sonnet synthesis)
    (TaskType.MORNING_BRIEF, [
        "morning brief", "daily brief", "morning report", "daily digest",
        "overnight summary", "morning intel", "daily summary",
    ]),

    # Priority 7: Creative (Opus quality)
    (TaskType.CREATIVE, [
        "write", "draft", "proposal", "narrative", "story", "copy",
        "describe", "paint a picture", "itinerary narrative", "poetic",
        "compose", "craft",
    ]),

    # Priority 8: Strategic (Opus quality)
    (TaskType.STRATEGIC, [
        "pricing", "strategy", "growth", "compete", "position",
        "should we", "business case", "roi", "market analysis",
        "competitive advantage",
    ]),

    # Priority 9: Research (Sonnet)
    (TaskType.RESEARCH, [
        "research", "investigate", "find out", "what do we know about",
        "intel on", "cruise intel", "destination", "look up",
        "compare options", "scan for", "flight options", "hotel options",
    ]),

    # Priority 10: Data extraction (Haiku — fast) — after principle_extraction
    (TaskType.DATA_EXTRACTION, [
        "extract", "parse", "ocr", "pull data from", "scrape",
        "structured data", "json from", "fields from", "csv from",
        "table from",
    ]),

    # Priority 12: Summarization (Haiku — fast)
    (TaskType.SUMMARIZATION, [
        "summarize", "summary", "tldr", "bullet points",
        "key takeaways", "quick recap", "condense", "brief overview",
    ]),
]


def classify_task(prompt: str, context: str = "") -> TaskType:
    """Classify task type from prompt content using keyword matching.

    Fast, zero-API-call classification. Checks keywords in priority order.
    Falls back to OPERATIONAL if no match.

    Args:
        prompt: The user prompt / query text
        context: Optional additional context (system prompt, etc.)

    Returns:
        TaskType enum value
    """
    text = f"{prompt} {context}".lower()

    for task_type, keywords in _CLASSIFICATION_RULES:
        for kw in keywords:
            if kw in text:
                return task_type

    return TaskType.OPERATIONAL


# ============================================================
# DEEPSEEK PII FENCE — DATA SOVEREIGNTY PROTECTION
# DeepSeek is a Chinese company. NEVER send client PII.
# All requests are scanned. PII triggers automatic reroute to Claude.
# This fence cannot be bypassed by route selection alone.
# ============================================================

# PII detection patterns (compiled once at module load for speed)
_PII_PATTERNS = [
    # Email addresses
    re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}'),
    # Phone numbers: (719) 291-0742, 719-291-0742, +1-719-291-0742, 7192910742
    re.compile(r'(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'),
    # Credit card patterns: 4 groups of 4 digits
    re.compile(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'),
    # Passport / ID numbers: 1-2 letters followed by 6-9 digits
    re.compile(r'\b[A-Z]{1,2}\d{6,9}\b'),
    # US street addresses: number + street name + suffix
    re.compile(
        r'\b\d{1,6}\s+[A-Za-z]+\s+(?:St|Street|Ave|Avenue|Blvd|Boulevard|'
        r'Dr|Drive|Ln|Lane|Rd|Road|Way|Ct|Court|Pl|Place|Cir|Circle)\b',
        re.IGNORECASE,
    ),
    # US ZIP codes (5 or 5+4)
    re.compile(r'\b\d{5}(?:-\d{4})?\b'),
    # Names near PII keywords: "client John Smith", "booking for Jane Doe"
    re.compile(
        r'\b(?:client|guest|passenger|booking\s+for|traveler|pax)\s+'
        r'[A-Z][a-z]+\s+[A-Z][a-z]+',
        re.IGNORECASE,
    ),
    # SSN pattern
    re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
]


def _check_pii_fence(text: str) -> bool:
    """Scan text for PII indicators. Returns True if PII is detected.

    Used to gate DeepSeek calls — if PII is found, the request MUST be
    rerouted to Claude (US-based) instead. This is a data sovereignty safeguard.
    """
    for pattern in _PII_PATTERNS:
        match = pattern.search(text)
        if match:
            logger.warning(
                "PII detected (pattern: %s...) — DeepSeek blocked, routing to Claude",
                pattern.pattern[:40],
            )
            return True
    return False


# ── Routing Rules ──
# Personas that benefit from Claude Opus for certain task types
ESCALATION_MAP = {
    # EXEC always escalate creative tasks — that's their core value
    "EXEC": {TaskType.CREATIVE, TaskType.CLIENT_FACING},
    # A5 (Castillo) escalates strategic analysis
    "A5":   {TaskType.STRATEGIC},
    # CH (Washington) escalates anything — wisdom needs depth
    "CH":   {TaskType.CREATIVE, TaskType.STRATEGIC, TaskType.OPERATIONAL,
             TaskType.CLIENT_FACING, TaskType.PRINCIPLE_EXTRACTION},
}


# ============================================================
# USAGE TRACKING — Log model usage by task type for optimization
# ============================================================

# In-memory counters (reset on process restart, persisted via JSONL)
_usage_counters: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))


def _resolve_model_tag(route_key: str) -> str:
    """Resolve a route key to its human-readable model tag."""
    return MODEL_TAGS.get(route_key, f"unknown ({route_key})")


def _log_model_usage(model_tag: str, persona_id: str, query: str,
                     tokens_est: int = 0, task_type: str = "default") -> None:
    """Append a line to ~/Thunderbird/logs/model_usage.log for every routed call.
    Also updates in-memory counters and persists to router_stats.jsonl.
    """
    try:
        _MODEL_USAGE_LOG.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        preview = query[:60].replace("\n", " ").strip()
        line = (f"[{ts}] {model_tag} | task={task_type} | persona={persona_id} "
                f"| tokens_est=~{tokens_est} | query_preview=\"{preview}\"\n")
        with open(_MODEL_USAGE_LOG, "a", encoding="utf-8") as f:
            f.write(line)

        # Update in-memory counters
        _usage_counters[model_tag][task_type] += 1
        _usage_counters[model_tag]["_total"] += 1
        _usage_counters["_all"]["_total"] += 1
        _usage_counters["_all"][task_type] += 1

        # Persist to JSONL (one line per call, parseable later)
        stat_line = json.dumps({
            "ts": ts,
            "model": model_tag,
            "task": task_type,
            "persona": persona_id,
            "tokens_est": tokens_est,
        })
        with open(_ROUTER_STATS_LOG, "a", encoding="utf-8") as f:
            f.write(stat_line + "\n")

    except Exception as e:
        logger.warning("Model usage log failed: %s", e)


def get_router_stats(days: int = 7) -> Dict[str, Any]:
    """Aggregate model router usage stats from the JSONL log.

    Args:
        days: How many days of history to include (default 7)

    Returns:
        Dict with per-model and per-task breakdowns, total calls, etc.
    """
    from datetime import timedelta

    cutoff = datetime.now() - timedelta(days=days)
    cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")

    model_counts: Dict[str, int] = defaultdict(int)
    task_counts: Dict[str, int] = defaultdict(int)
    model_task: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    total = 0

    try:
        if _ROUTER_STATS_LOG.exists():
            with open(_ROUTER_STATS_LOG, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if entry.get("ts", "") < cutoff_str:
                        continue
                    model = entry.get("model", "unknown")
                    task = entry.get("task", "unknown")
                    model_counts[model] += 1
                    task_counts[task] += 1
                    model_task[model][task] += 1
                    total += 1
    except Exception as e:
        logger.warning("Failed to read router stats: %s", e)

    # Build summary
    return {
        "period_days": days,
        "total_calls": total,
        "by_model": dict(sorted(model_counts.items(), key=lambda x: -x[1])),
        "by_task": dict(sorted(task_counts.items(), key=lambda x: -x[1])),
        "model_x_task": {m: dict(sorted(t.items(), key=lambda x: -x[1]))
                         for m, t in sorted(model_task.items())},
        "routing_config": {
            tt.value: MODEL_TIER.get(MODEL_MAP.get(tt, ""), "special")
            for tt in TaskType
        },
    }


def should_escalate(persona_id: str, task_type: Optional[TaskType] = None) -> bool:
    """Decide if a task should escalate to Opus based on persona + task type."""
    if task_type is None:
        return False
    return task_type in ESCALATION_MAP.get(persona_id, set())


# ============================================================
# MODEL CALL FUNCTIONS — One per engine
# ============================================================

def _call_anthropic(system_prompt: str, query: str,
                    model: str = CLAUDE_SONNET,
                    max_tokens: int = 2000,
                    temperature: float = 0.7) -> str:
    """Call any Claude model via Anthropic SDK (Max plan, $0).

    This is the unified Claude caller. All tiers (Opus/Sonnet/Haiku)
    go through here.
    """
    import anthropic

    client = anthropic.Anthropic()
    try:
        resp = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": query}],
            temperature=temperature,
        )
        return resp.content[0].text
    except Exception as e:
        raise RuntimeError(f"Anthropic SDK error ({model}): {e}")


def _call_groq(system_prompt: str, query: str, model: str = "fast",
               max_tokens: int = 600, temperature: float = 0.7) -> str:
    """Route to Claude via Anthropic SDK (Max plan, $0).

    Name kept for backward compat — Groq is ELIMINATED.
    Now uses route_and_call() internally to auto-select the right model tier.
    """
    # Map legacy model keys to Claude models
    claude_model = GROQ_MODELS.get(model, CLAUDE_SONNET)
    return _call_anthropic(system_prompt, query, model=claude_model,
                           max_tokens=max_tokens, temperature=temperature)


def _call_claude(system_prompt: str, query: str,
                 max_tokens: int = None, temperature: float = 0.7) -> str:
    """Call Anthropic Claude API via SDK.

    Claude now supports 1M context window at GA pricing.
    Default max_tokens raised to CLAUDE_DEFAULT_MAX_OUTPUT (16,384).
    """
    if max_tokens is None:
        max_tokens = CLAUDE_DEFAULT_MAX_OUTPUT

    return _call_anthropic(system_prompt, query, model=CLAUDE_MODEL,
                           max_tokens=max_tokens, temperature=temperature)


def _call_gemini(system_prompt: str, query: str,
                 max_tokens: int = 600, temperature: float = 0.7) -> str:
    """Call Google Gemini 2.5 Flash API.

    Cost: $0.30/$2.50 per 1M tokens — cheap, native Google Workspace affinity.
    Falls back to Claude Sonnet if GOOGLE_AI_API_KEY is not set.
    """
    if not GOOGLE_AI_API_KEY:
        logger.warning("GOOGLE_AI_API_KEY not set — falling back to Claude Sonnet")
        return _call_anthropic(system_prompt, query, model=CLAUDE_SONNET,
                               max_tokens=max_tokens, temperature=temperature)

    url = f"{GEMINI_URL}?key={GOOGLE_AI_API_KEY}"
    payload = {
        "systemInstruction": {
            "parts": [{"text": system_prompt}]
        },
        "contents": [
            {"role": "user", "parts": [{"text": query}]}
        ],
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": temperature,
        },
    }
    resp = requests.post(url, json=payload, timeout=60,
                         headers={"Content-Type": "application/json"})
    resp.raise_for_status()
    data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


def _call_grok(system_prompt: str, query: str,
               max_tokens: int = 600, temperature: float = 0.7) -> str:
    """Call xAI Grok 4.1 Fast API (OpenAI-compatible).

    Cost: $0.20/$0.50 per 1M tokens — cheap, built-in web search capability.
    Falls back to Claude Sonnet if XAI_API_KEY is not set.
    """
    if not XAI_API_KEY:
        logger.warning("XAI_API_KEY not set — falling back to Claude Sonnet")
        return _call_anthropic(system_prompt, query, model=CLAUDE_SONNET,
                               max_tokens=max_tokens, temperature=temperature)

    resp = requests.post(
        GROK_URL,
        json={
            "model": GROK_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        },
        headers={
            "Authorization": f"Bearer {XAI_API_KEY}",
            "Content-Type": "application/json",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _call_deepseek(system_prompt: str, query: str,
                   max_tokens: int = 600, temperature: float = 0.7) -> str:
    """Call DeepSeek V3 API (OpenAI-compatible).

    Cost: $0.14/$0.28 per 1M tokens — cheapest option for non-PII extraction tasks.
    PII fence is enforced by the caller — this function trusts that the fence
    has already been checked. Direct callers MUST call _check_pii_fence() first.
    Falls back to Claude Haiku if DEEPSEEK_API_KEY is not set.
    """
    if not DEEPSEEK_API_KEY:
        logger.warning("DEEPSEEK_API_KEY not set — falling back to Claude Haiku")
        return _call_anthropic(system_prompt, query, model=CLAUDE_HAIKU,
                               max_tokens=max_tokens, temperature=temperature)

    resp = requests.post(
        DEEPSEEK_URL,
        json={
            "model": DEEPSEEK_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        },
        headers={
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def call_deepseek(system_prompt: str, query: str,
                  max_tokens: int = 600, temperature: float = 0.7) -> Dict[str, Any]:
    """Public DeepSeek call with mandatory PII fence.

    Returns dict with: engine, model, response, success, pii_blocked.
    If PII is detected, automatically reroutes to Claude Haiku — NEVER sends PII to DeepSeek.
    """
    combined_text = f"{system_prompt}\n{query}"

    if _check_pii_fence(combined_text):
        # PII detected — hard reroute to Claude Haiku
        response = _call_anthropic(system_prompt, query, model=CLAUDE_HAIKU,
                                   max_tokens=max_tokens, temperature=temperature)
        return {
            "engine": "claude",
            "model": CLAUDE_HAIKU,
            "response": response,
            "success": True,
            "pii_blocked": True,
            "note": "PII detected — rerouted from DeepSeek to Claude Haiku",
        }

    try:
        response = _call_deepseek(system_prompt, query,
                                  max_tokens=max_tokens, temperature=temperature)
        model_used = DEEPSEEK_MODEL if DEEPSEEK_API_KEY else CLAUDE_HAIKU
        engine = "deepseek" if DEEPSEEK_API_KEY else "claude"
        return {
            "engine": engine,
            "model": model_used,
            "response": response,
            "success": True,
            "pii_blocked": False,
        }
    except Exception as e:
        logger.warning("DeepSeek failed, falling back to Claude Haiku: %s", e)
        response = _call_anthropic(system_prompt, query, model=CLAUDE_HAIKU,
                                   max_tokens=max_tokens, temperature=temperature)
        return {
            "engine": "claude",
            "model": CLAUDE_HAIKU,
            "response": response,
            "success": True,
            "pii_blocked": False,
            "note": f"DeepSeek failed ({e}), fell back to Claude Haiku",
        }


# ============================================================
# SMART ROUTER — The main auto-routing function
# ============================================================

def route_and_call(system_prompt: str, user_prompt: str,
                   task_hint: str = None,
                   max_tokens: int = 2000,
                   temperature: float = 0.7,
                   persona_id: str = "router") -> Dict[str, Any]:
    """Auto-route to the best model based on task classification.

    This is the primary entry point for all new code. Classifies the task,
    selects the optimal model tier, makes the call, and logs usage.

    Args:
        system_prompt: System prompt for the model
        user_prompt: User query / task description
        task_hint: Optional override (e.g., "client_facing" forces Opus).
                   Must be a valid TaskType value string.
        max_tokens: Maximum output tokens
        temperature: Sampling temperature
        persona_id: Who's calling (for logging). Default "router".

    Returns:
        Dict with: task_type, model, model_tier, engine, response, success
    """
    # 1. Classify the task
    if task_hint:
        # Try to match the hint to a TaskType
        try:
            task_type = TaskType(task_hint)
        except ValueError:
            logger.warning("Invalid task_hint '%s', auto-classifying", task_hint)
            task_type = classify_task(user_prompt, context=system_prompt)
    else:
        task_type = classify_task(user_prompt, context=system_prompt)

    # 2. Select the model
    model_id = MODEL_MAP.get(task_type, CLAUDE_SONNET)
    tier = MODEL_TIER.get(model_id, "special")

    # 3. Handle special cases (image, extraction with DeepSeek)
    if task_type == TaskType.IMAGE:
        # Image generation handled separately
        return {
            "task_type": task_type.value,
            "model": "flux",
            "model_tier": "image",
            "engine": "huggingface",
            "response": "Use generate_image() for image tasks",
            "success": False,
            "note": "Image tasks should use generate_image() directly",
        }

    if task_type in (TaskType.EXTRACTION, TaskType.DATA_EXTRACTION):
        # Try DeepSeek for extraction (cheap), but PII fence applies
        combined = f"{system_prompt}\n{user_prompt}"
        if not _check_pii_fence(combined) and DEEPSEEK_API_KEY:
            try:
                response = _call_deepseek(system_prompt, user_prompt,
                                          max_tokens=max_tokens,
                                          temperature=temperature)
                _log_model_usage("DeepSeek (fenced)", persona_id, user_prompt,
                                 tokens_est=(len(system_prompt + user_prompt) + len(response)) // 4,
                                 task_type=task_type.value)
                return {
                    "task_type": task_type.value,
                    "model": DEEPSEEK_MODEL,
                    "model_tier": "deepseek",
                    "engine": "deepseek",
                    "response": response,
                    "success": True,
                }
            except Exception as e:
                logger.warning("DeepSeek extraction failed, falling to Haiku: %s", e)
                model_id = CLAUDE_HAIKU
                tier = "haiku"

    # 4. Make the Claude call
    logger.info("Auto-routing [%s] → %s (%s)", task_type.value, tier, model_id)

    try:
        response = _call_anthropic(system_prompt, user_prompt,
                                   model=model_id,
                                   max_tokens=max_tokens,
                                   temperature=temperature)

        # 5. Log usage
        est_tokens = (len(system_prompt + user_prompt) + len(response)) // 4
        model_tag = MODEL_TAGS.get(tier, f"Claude {tier.title()}")
        _log_model_usage(model_tag, persona_id, user_prompt,
                         tokens_est=est_tokens, task_type=task_type.value)

        # 6. Log API cost
        try:
            from thunderbird_api_costs import log_api_call
            est_input = len(system_prompt + user_prompt) // 4
            est_output = len(response) // 4
            log_api_call("claude", model_id, input_tokens=est_input,
                         output_tokens=est_output, caller=persona_id,
                         task=task_type.value, write_sheet=False)
        except Exception:
            pass

        return {
            "task_type": task_type.value,
            "model": model_id,
            "model_tier": tier,
            "engine": "claude",
            "response": response,
            "success": True,
        }

    except Exception as e:
        # Fallback: try Sonnet if Opus/Haiku failed
        fallback = CLAUDE_SONNET if model_id != CLAUDE_SONNET else CLAUDE_HAIKU
        logger.warning("Primary model %s failed, trying fallback %s: %s",
                        model_id, fallback, e)
        try:
            response = _call_anthropic(system_prompt, user_prompt,
                                       model=fallback,
                                       max_tokens=max_tokens,
                                       temperature=temperature)
            fallback_tier = MODEL_TIER.get(fallback, "unknown")
            _log_model_usage(f"FALLBACK ({fallback_tier})", persona_id, user_prompt,
                             tokens_est=(len(system_prompt + user_prompt) + len(response)) // 4,
                             task_type=task_type.value)
            return {
                "task_type": task_type.value,
                "model": fallback,
                "model_tier": fallback_tier,
                "engine": "claude",
                "response": response,
                "success": True,
                "note": f"Fell back from {model_id} to {fallback}",
            }
        except Exception as e2:
            logger.error("Both primary and fallback failed: %s", e2)
            return {
                "task_type": task_type.value,
                "model": model_id,
                "model_tier": tier,
                "engine": "claude",
                "response": f"ERROR: {e} (fallback also failed: {e2})",
                "success": False,
            }


# ============================================================
# IMAGE GENERATION (unchanged)
# ============================================================

def generate_image(prompt: str, output_path: Optional[str] = None,
                   model: str = "schnell") -> Dict[str, Any]:
    """Generate an image using FLUX.1 via HuggingFace Inference API (free).

    Args:
        prompt: Text description of the desired image
        output_path: Where to save the image (default: output/images/<timestamp>.png)
        model: "schnell" (fast/free) or "dev" (higher quality)

    Returns:
        dict with: local_path, model, success, bytes
    """
    if not HF_API_KEY:
        return {"success": False, "error": "HF_API_KEY not set"}

    model_map = {
        "schnell": "black-forest-labs/FLUX.1-schnell",
        "dev": "black-forest-labs/FLUX.1-dev",
        "sd": "stabilityai/stable-diffusion-xl-base-1.0",
    }
    model_id = model_map.get(model, model_map["schnell"])

    try:
        resp = requests.post(
            f"{HF_INFERENCE_URL}/{model_id}",
            json={"inputs": prompt},
            headers={"Authorization": f"Bearer {HF_API_KEY}"},
            timeout=120,
        )
        resp.raise_for_status()

        if "image" not in resp.headers.get("content-type", ""):
            return {"success": False, "error": f"Unexpected content-type: {resp.headers.get('content-type')}", "model": model_id}

        img_bytes = resp.content

        # Save to disk
        if not output_path:
            img_dir = Path(__file__).parent / "output" / "images"
            img_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = str(img_dir / f"flux_{ts}.png")

        Path(output_path).write_bytes(img_bytes)
        logger.info(f"Image generated: {output_path} ({len(img_bytes):,} bytes)")

        # Log cost (free tier)
        try:
            from thunderbird_api_costs import log_api_call
            log_api_call("huggingface", model_id, input_tokens=0, output_tokens=0,
                         caller="image_gen", task="image",
                         write_sheet=False)
        except Exception:
            pass

        return {
            "success": True,
            "local_path": output_path,
            "model": model_id,
            "prompt": prompt,
            "bytes": len(img_bytes),
        }
    except Exception as e:
        logger.error(f"Image generation failed: {e}")
        return {"success": False, "error": str(e), "model": model_id}


# ============================================================
# LEGACY PERSONA-BASED ROUTING (backward compatible)
# ============================================================

def route_call(persona_id: str, query: str,
               task_type: Optional[TaskType] = None,
               max_tokens: int = 600,
               temperature: float = 0.7) -> Dict[str, Any]:
    """Route a persona call to the optimal model.

    NOW USES AUTO-ROUTING: classifies the task and picks the right tier.
    Legacy callers get automatic model selection for free.

    Returns dict with: persona, model_used, engine, response, success, task_type
    """
    from thunderbird_personas import resolve_id, get_persona, build_system_prompt

    pid = resolve_id(persona_id)
    persona = get_persona(pid)
    system_prompt = build_system_prompt(pid)

    # Auto-classify if no task type provided
    if task_type is None:
        task_type = classify_task(query)

    # Check for persona-based escalation to Opus
    escalate = should_escalate(pid, task_type)

    # Determine model: escalation forces Opus, otherwise use MODEL_MAP
    if escalate:
        model_id = CLAUDE_OPUS
    else:
        model_id = MODEL_MAP.get(task_type, CLAUDE_SONNET)

    tier = MODEL_TIER.get(model_id, "sonnet")
    engine = "claude"

    logger.info("Routing %s [%s] → %s (%s)%s",
                pid, task_type.value, tier, model_id,
                " (escalated)" if escalate else "")

    try:
        # Check for specialty routing based on persona model tag
        groq_model = persona.get("model", "fast")

        # Route to Gemini for workspace/gemini-tagged models
        if groq_model in ("gemini", "workspace"):
            response = _call_gemini(system_prompt, query, max_tokens=max_tokens,
                                    temperature=temperature)
            model_used = GEMINI_MODEL if GOOGLE_AI_API_KEY else CLAUDE_SONNET
            engine = "gemini" if GOOGLE_AI_API_KEY else "claude"
        # Route to Grok for research/grok-tagged models
        elif groq_model in ("research", "grok"):
            response = _call_grok(system_prompt, query, max_tokens=max_tokens,
                                  temperature=temperature)
            model_used = GROK_MODEL if XAI_API_KEY else CLAUDE_SONNET
            engine = "grok" if XAI_API_KEY else "claude"
        # Route to DeepSeek for extraction (PII-fenced)
        elif groq_model in ("extraction", "deepseek") or task_type == TaskType.EXTRACTION:
            result = call_deepseek(system_prompt, query, max_tokens=max_tokens,
                                   temperature=temperature)
            response = result["response"]
            model_used = result["model"]
            engine = result["engine"]
        else:
            # Use auto-selected Claude tier
            response = _call_anthropic(system_prompt, query, model=model_id,
                                       max_tokens=max_tokens, temperature=temperature)
            model_used = model_id

        # Resolve model tag
        model_tag = MODEL_TAGS.get(tier, f"Claude {tier.title()}")

        # Log model usage
        est_tokens = (len(system_prompt + query) + len(response)) // 4
        _log_model_usage(model_tag, pid, query, tokens_est=est_tokens,
                         task_type=task_type.value)

        # Log the API call cost
        try:
            from thunderbird_api_costs import log_api_call
            est_input = len(system_prompt + query) // 4
            est_output = len(response) // 4
            log_api_call(engine, model_used, input_tokens=est_input,
                         output_tokens=est_output, caller=pid,
                         task=task_type.value, write_sheet=False)
        except Exception:
            pass

        return {
            "persona": pid,
            "name": persona["name"],
            "engine": engine,
            "model": model_used,
            "model_tag": model_tag,
            "model_tier": tier,
            "task_type": task_type.value,
            "response": response,
            "success": True,
        }
    except Exception as e:
        # Fallback: try Sonnet as safe default
        logger.warning("Route call failed for %s, trying Sonnet fallback: %s", pid, e)
        try:
            response = _call_anthropic(system_prompt, query, model=CLAUDE_SONNET,
                                       max_tokens=max_tokens, temperature=temperature)
            _log_model_usage("FALLBACK (Sonnet)", pid, query,
                             tokens_est=(len(system_prompt + query) + len(response)) // 4,
                             task_type=task_type.value)
            return {
                "persona": pid,
                "name": persona["name"],
                "engine": "claude",
                "model": CLAUDE_SONNET,
                "model_tag": "Claude Sonnet",
                "model_tier": "sonnet",
                "task_type": task_type.value,
                "response": response,
                "success": True,
                "note": f"Fell back to Sonnet: {e}",
            }
        except Exception as e2:
            logger.error("Both primary and fallback failed for %s: %s", pid, e2)
            return {
                "persona": pid,
                "name": persona["name"],
                "engine": engine,
                "model": "none",
                "model_tag": "ERROR",
                "model_tier": "none",
                "task_type": task_type.value,
                "response": f"ERROR: {e} (fallback: {e2})",
                "success": False,
            }


def smart_route(persona_id: str, query: str, **kwargs) -> Dict[str, Any]:
    """Auto-classify and route. Convenience wrapper."""
    task_type = classify_task(query)
    return route_call(persona_id, query, task_type=task_type, **kwargs)


# ============================================================
# MCP TOOL REGISTRATION
# ============================================================

def register_router_tools(mcp_server) -> None:
    """Register model_router_stats as an MCP tool."""

    @mcp_server.tool(
        name="model_router_stats",
        annotations={"title": "Model Router Usage Stats", "readOnlyHint": True},
    )
    async def model_router_stats(
        days: int = 7,
    ) -> str:
        """Show model usage statistics by task type. Helps optimize routing over time.

        Args:
            days: Number of days of history to analyze (default 7)
        """
        try:
            stats = get_router_stats(days=days)
            return json.dumps(stats, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e), "success": False})


# ============================================================
# CLI TEST
# ============================================================

if __name__ == "__main__":
    print("=== Thunderbird Model Router v2 — Auto-Routing Test ===\n")

    test_prompts = [
        ("Draft a welcome email for the Furlow family", None),
        ("Summarize the latest cruise intel", None),
        ("Classify this email: Dear John, I'd like to book...", None),
        ("Extract booking data from the PDF confirmation", None),
        ("Write code to parse the commission CSV", None),
        ("What's the voice profile for Lyons?", None),
        ("Morning brief — what happened overnight?", None),
        ("Extract the principle from Commander's edit", None),
        ("Compare Regent vs Silversea pricing", None),
        ("Urgent — client missed their connection in LAX", None),
        ("Should we raise markup on SLH properties?", None),
        ("Generic operational query about booking status", None),
        # Test task_hint override
        ("Just a regular question", "client_facing"),
    ]

    print(f"{'PROMPT':<55} {'TASK TYPE':<25} {'MODEL TIER':<12} {'MODEL'}")
    print("-" * 120)

    for prompt, hint in test_prompts:
        if hint:
            try:
                tt = TaskType(hint)
            except ValueError:
                tt = classify_task(prompt)
        else:
            tt = classify_task(prompt)

        model = MODEL_MAP.get(tt, CLAUDE_SONNET)
        tier = MODEL_TIER.get(model, "special")
        print(f"{prompt[:53]:<55} {tt.value:<25} {tier:<12} {model}")

    # Print routing config
    print("\n=== Routing Configuration ===")
    print(f"{'TASK TYPE':<25} {'TIER':<10} {'MODEL'}")
    print("-" * 70)
    for tt in TaskType:
        model = MODEL_MAP.get(tt, "N/A")
        tier = MODEL_TIER.get(model, "special")
        print(f"{tt.value:<25} {tier:<10} {model}")

    # Print stats if available
    print("\n=== Usage Stats (last 7 days) ===")
    stats = get_router_stats(7)
    print(f"Total calls: {stats['total_calls']}")
    if stats['by_model']:
        print("By model:")
        for m, c in stats['by_model'].items():
            print(f"  {m}: {c}")
    if stats['by_task']:
        print("By task:")
        for t, c in stats['by_task'].items():
            print(f"  {t}: {c}")
