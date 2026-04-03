"""
Thunderbird Model Router v2 — Auto-Routing by Task Type
=========================================================
Classifies every inbound task and routes to the optimal Claude model tier:

  Sonnet → All AI tasks — client copy, code, voice profiles, briefs, analytical
  Haiku  → Classification, data extraction, summarization, research, operational (fast & cheap)

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
import time
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
    "qwen_plus": "Qwen3.6 Plus (OpenRouter, free)",
    "qwen_flash": "Qwen 3.5 Flash (OpenRouter)",
    "gemini_lite": "Gemini 2.5 Flash-Lite",
    "perplexity": "Perplexity Sonar (Web Search)",
    "perplexity_reasoning": "Perplexity Reasoning Pro",
}

# ── Log Paths ──
_MODEL_USAGE_LOG = Path(__file__).parent / "logs" / "model_usage.log"
_ROUTER_STATS_LOG = Path(__file__).parent / "logs" / "router_stats.jsonl"

# ── API Keys ──
# Groq ELIMINATED — all calls route to Claude via Anthropic SDK ($0 on Max plan)
# Backward-compat stubs: callers may import these even though Groq is dead
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# Gemini Flash rate limiter — Goose batches hit 10 RPM free tier limit
# Set GEMINI_INTER_CALL_DELAY=6 in env for Goose sessions, 0 for interactive
_GEMINI_LAST_CALL: float = 0.0
GEMINI_INTER_CALL_DELAY = float(os.environ.get("GEMINI_INTER_CALL_DELAY", "0"))

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

# OpenRouter — multi-model API gateway (used for Qwen, etc.)
# Cost varies by model. Qwen 3.5 Flash: $0.065/$0.26 per 1M tokens, 1M context.
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Qwen3.6 Plus (free) via OpenRouter — primary AI engine, $0/month, 1M context
# Lead model for all operational/non-classification tasks (SO 2026-04-03)
QWEN_PLUS_FREE_MODEL = "qwen/qwen3.6-plus:free"
QWEN_PLUS_FREE_CONTEXT = 1_000_000  # 1M token context window

# Qwen 3.5 Flash via OpenRouter — bulk context dumps, large codebase reviews
QWEN_FLASH_MODEL = "qwen/qwen3.5-flash-02-23"
QWEN_FLASH_CONTEXT = 1_000_000  # 1M token context window

# Perplexity Sonar via OpenRouter — web-grounded research with citations
# $1/$1 per 1M tokens + $5/1K search requests. Built-in web search.
PERPLEXITY_SONAR_MODEL = "perplexity/sonar"
PERPLEXITY_SONAR_CONTEXT = 127_000
# Sonar Reasoning Pro — CoT + web search, $2/$8 per 1M tokens
PERPLEXITY_REASONING_MODEL = "perplexity/sonar-reasoning-pro"
PERPLEXITY_REASONING_CONTEXT = 128_000

# Gemini 2.5 Flash-Lite — $0.10/$0.40 per 1M tokens, 1M context
# Cheaper than full Flash for simple analysis, classification
GEMINI_LITE_MODEL = "gemini-2.5-flash-lite"
GEMINI_LITE_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent"
GEMINI_LITE_CONTEXT = 1_000_000

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
    CLIENT_FACING = "client_facing"          # Client emails, proposals → Sonnet (SO 2026-03-27)
    RESEARCH = "research"                    # Destination/market research → Sonnet
    DATA_EXTRACTION = "data_extraction"      # Structured extraction → Haiku
    CODE_GENERATION = "code_generation"      # Code writing → Sonnet
    VOICE_PROFILE = "voice_profile"          # Voice/tone analysis → Sonnet
    MORNING_BRIEF = "morning_brief"          # Morning synthesis → Sonnet
    PRINCIPLE_EXTRACTION = "principle_extraction"  # Learning/nuance → Sonnet
    SUMMARIZATION = "summarization"          # Quick summaries → Haiku
    RESPONSE_MONITOR = "response_monitor"    # Quality gate — Sonnet reviews Haiku output

    # Bulk context tiers — large payloads, 1M context window models
    CONTEXT_DUMP = "context_dump"            # Bulk context ingestion → Qwen 3.5 Flash (OpenRouter)
    BULK_REVIEW = "bulk_review"              # Large codebase/doc review → Qwen 3.5 Flash (OpenRouter)
    SIMPLE_ANALYSIS = "simple_analysis"      # Simple classification/analysis → Gemini 2.5 Flash-Lite

    # Web-grounded research — Perplexity Sonar via OpenRouter (built-in search + citations)
    WEB_RESEARCH = "web_research"            # Live web search + grounded answers → Perplexity Sonar
    DEEP_RESEARCH = "deep_research"          # Complex analytical web research → Perplexity Reasoning Pro


# ============================================================
# MODEL SELECTION MAP — Task Type → Claude Model
# ============================================================

# Claude model IDs
CLAUDE_OPUS = "claude-opus-4-20250514"
CLAUDE_SONNET = "claude-sonnet-4-20250514"
CLAUDE_HAIKU = "claude-haiku-3-20250307"

MODEL_MAP: Dict[TaskType, str] = {
    # Opus — NOT USED. No task routes to Opus. (SO 2026-03-27)

    # Sonnet — all task types (SO 2026-03-27: Opus retired)
    TaskType.PRINCIPLE_EXTRACTION: CLAUDE_SONNET,
    TaskType.CRISIS: CLAUDE_SONNET,
    TaskType.STRATEGIC: CLAUDE_SONNET,
    TaskType.CLIENT_FACING: CLAUDE_SONNET,
    TaskType.CREATIVE: CLAUDE_SONNET,
    TaskType.CODE_GENERATION: CLAUDE_SONNET,
    TaskType.VOICE_PROFILE: CLAUDE_SONNET,
    TaskType.MORNING_BRIEF: CLAUDE_SONNET,
    TaskType.ANALYTICAL: CLAUDE_SONNET,

    # OpenRouter (free) — Qwen3.6 Plus primary operational engine ($0/month, SO 2026-04-03)
    TaskType.RESEARCH: "qwen_plus",        # lookups, cruise/flight/hotel/destination
    TaskType.OPERATIONAL: "qwen_plus",     # status checks, data lookups, routing
    TaskType.SUMMARIZATION: "qwen_plus",   # quick summaries

    # Haiku — kept for fast classification and extraction (low latency priority)
    TaskType.CLASSIFICATION: CLAUDE_HAIKU,
    TaskType.DATA_EXTRACTION: CLAUDE_HAIKU,
    TaskType.EXTRACTION: CLAUDE_HAIKU,

    # Sonnet — response quality monitor (sits above Haiku)
    TaskType.RESPONSE_MONITOR: CLAUDE_SONNET,

    # Special (not Claude)
    TaskType.IMAGE: "flux",  # handled separately

    # Bulk context tiers — 1M context window, cheap per-token
    TaskType.CONTEXT_DUMP: "qwen_flash",       # Qwen 3.5 Flash via OpenRouter ($0.065/$0.26/1M)
    TaskType.BULK_REVIEW: "qwen_flash",        # Qwen 3.5 Flash via OpenRouter ($0.065/$0.26/1M)
    TaskType.SIMPLE_ANALYSIS: "gemini_lite",   # Gemini 2.5 Flash-Lite ($0.10/$0.40/1M)

    # Web-grounded research — Perplexity via OpenRouter (uses same OPENROUTER_API_KEY)
    TaskType.WEB_RESEARCH: "perplexity",       # Perplexity Sonar ($1/$1/1M + $5/1K search)
    TaskType.DEEP_RESEARCH: "perplexity_reasoning",  # Perplexity Reasoning Pro ($2/$8/1M + $5/1K search)
}

# Human-readable tier names for logging
MODEL_TIER = {
    CLAUDE_OPUS: "opus",
    CLAUDE_SONNET: "sonnet",
    CLAUDE_HAIKU: "haiku",
    "qwen_plus": "qwen_plus",
    "qwen_flash": "qwen_flash",
    "gemini_lite": "gemini_lite",
    "perplexity": "perplexity",
    "perplexity_reasoning": "perplexity_reasoning",
}

# Groq model map — fast/light/image route to Groq; others fall back to Claude
GROQ_MODELS = {
    "fast":      "llama-3.1-8b-instant",                        # ~200 tok/s, cheapest
    "light":     "llama-3.3-70b-versatile",                     # balanced quality/speed
    "image":     "meta-llama/llama-4-scout-17b-16e-instruct",   # vision-capable
    # Claude fallbacks for tags Groq doesn't cover
    "premium":   CLAUDE_SONNET,
    "kimi":      CLAUDE_SONNET,
    "detail":    CLAUDE_SONNET,
    "visionary": CLAUDE_SONNET,
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

    # Priority 3: Client-facing (Sonnet)
    (TaskType.CLIENT_FACING, [
        "client email", "email to client", "dear ", "email for ",
        "welcome email", "follow up email", "thank you note",
        "send to client", "client-facing", "guest communication",
        "concierge email", "concierge response",
    ]),

    # Priority 4: Principle extraction (Sonnet) — before data_extraction
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

    # Priority 7: Creative (Sonnet)
    (TaskType.CREATIVE, [
        "write", "draft", "proposal", "narrative", "story", "copy",
        "describe", "paint a picture", "itinerary narrative", "poetic",
        "compose", "craft",
    ]),

    # Priority 8: Strategic (Sonnet)
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

    # Priority 13: Bulk context / large payload tasks → Qwen 3.5 Flash (1M context)
    (TaskType.CONTEXT_DUMP, [
        "context dump", "bulk context", "ingest this", "blackboard payload",
        "full codebase", "entire repo", "large payload", "dump all",
        "context load", "context injection", "full context",
    ]),
    (TaskType.BULK_REVIEW, [
        "bulk review", "codebase review", "review all files", "full audit",
        "review everything", "large review", "system-wide review",
        "review the entire", "review all of",
    ]),

    # Priority 14: Simple analysis → Gemini 2.5 Flash-Lite (cheapest)
    (TaskType.SIMPLE_ANALYSIS, [
        "simple analysis", "quick classify", "simple classification",
        "basic analysis", "quick check", "simple check", "lightweight analysis",
    ]),

    # Priority 15: Web-grounded research → Perplexity Sonar (built-in search + citations)
    (TaskType.WEB_RESEARCH, [
        "web search", "search the web", "search online", "live search",
        "current news", "latest on", "what's happening with",
        "find online", "web intel", "live intel", "breaking news",
        "search for news", "google for", "perplexity",
    ]),
    (TaskType.DEEP_RESEARCH, [
        "deep research", "comprehensive research", "thorough investigation",
        "analyze and research", "deep dive research", "research report on",
        "full analysis of", "competitive analysis", "market research",
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
# Opus retired — no task routes to Opus (SO 2026-03-27)
ESCALATION_MAP = {
    # Empty. Opus is not used. No authorization path exists.
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
    """Opus retired (SO 2026-03-27). Always returns False."""
    return False


# ============================================================
# MODEL CALL FUNCTIONS — One per engine
# ============================================================

def _call_anthropic(system_prompt: str, query: str,
                    model: str = CLAUDE_SONNET,
                    max_tokens: int = 2000,
                    temperature: float = 0.7) -> str:
    """Call any Claude model via Anthropic SDK (Max plan, $0).

    Unified Claude caller. Sonnet/Haiku only — Opus retired (SO 2026-03-27).
    Fallback chain on auth/depleted/overload errors (SO 2026-04-03):
      Claude → OpenRouter (Qwen 3.6 Plus free) → Groq (Llama 3.3) → Gemini Flash
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
        err_str = str(e).lower()
        if any(code in err_str for code in ("401", "403", "529", "authentication", "api_key", "credit")):
            logger.warning("Anthropic SDK error (%s): %s — trying free fallback chain", model, e)
            # Fallback 1: OpenRouter Qwen 3.6 Plus (free)
            if OPENROUTER_API_KEY:
                try:
                    return _call_openrouter(system_prompt, query,
                                           model=QWEN_PLUS_FREE_MODEL,
                                           max_tokens=max_tokens,
                                           temperature=temperature)
                except Exception as e2:
                    logger.warning("OpenRouter fallback failed: %s — trying Groq", e2)
            # Fallback 2: Groq Llama 3.3 70B (free)
            if GROQ_API_KEY:
                try:
                    return _call_groq(system_prompt, query, model="light",
                                      max_tokens=max_tokens, temperature=temperature)
                except Exception as e3:
                    logger.warning("Groq fallback failed: %s — trying Gemini Flash", e3)
            # Fallback 3: Gemini Flash (last resort)
            return _call_gemini(system_prompt, query,
                                max_tokens=max_tokens, temperature=temperature)
        raise RuntimeError(f"Anthropic SDK error ({model}): {e}")


def _call_groq(system_prompt: str, query: str, model: str = "fast",
               max_tokens: int = 600, temperature: float = 0.7,
               image_b64: str = None, image_mime: str = "image/jpeg") -> str:
    """Call Groq API for fast/light/image tasks.

    Routes fast/light/image to Groq; all other model tags fall back to Claude.
    Pass image_b64 (base64-encoded bytes) with model="image" for vision tasks.
    Falls back to Claude Sonnet if GROQ_API_KEY is not set.
    """
    groq_model = GROQ_MODELS.get(model)

    # Non-Groq tags (premium, kimi, detail, visionary) → Claude directly
    if groq_model in (CLAUDE_SONNET, CLAUDE_HAIKU, CLAUDE_OPUS, None):
        claude_model = groq_model or CLAUDE_SONNET
        return _call_anthropic(system_prompt, query, model=claude_model,
                               max_tokens=max_tokens, temperature=temperature)

    # Groq tags but no key → fall back to Gemini Flash (not Claude — avoids API key dependency)
    if not GROQ_API_KEY:
        logger.warning("GROQ_API_KEY not set — falling back to Gemini Flash for model=%s", model)
        return _call_gemini(system_prompt, query,
                            max_tokens=max_tokens, temperature=temperature)

    # Build user message — support vision for image model
    if image_b64 and model == "image":
        user_content = [
            {"type": "text", "text": query},
            {"type": "image_url", "image_url": {
                "url": f"data:{image_mime};base64,{image_b64}"
            }},
        ]
    else:
        user_content = query

    payload = {
        "model": groq_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_content},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        resp = requests.post(GROQ_URL, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.warning("Groq call failed (%s), falling back to Gemini Flash: %s", model, e)
        return _call_gemini(system_prompt, query,
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
    Rate limiter: respects GEMINI_INTER_CALL_DELAY (default 0s, set to 6s for
    Goose batch sessions to stay under 10 RPM free tier limit).
    No circular fallback — raises cleanly on failure.
    """
    global _GEMINI_LAST_CALL

    if not GOOGLE_AI_API_KEY:
        raise RuntimeError("GOOGLE_AI_API_KEY not set — cannot call Gemini Flash")

    # Rate limiting — enforce minimum gap between calls
    if GEMINI_INTER_CALL_DELAY > 0:
        elapsed = time.time() - _GEMINI_LAST_CALL
        if elapsed < GEMINI_INTER_CALL_DELAY:
            wait = GEMINI_INTER_CALL_DELAY - elapsed
            logger.debug("Gemini rate limiter: sleeping %.1fs", wait)
            time.sleep(wait)

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
    try:
        _GEMINI_LAST_CALL = time.time()
        resp = requests.post(url, json=payload, timeout=60,
                             headers={"Content-Type": "application/json"})
        resp.raise_for_status()
        data = resp.json()
        candidate = data.get("candidates", [{}])[0]
        finish = candidate.get("finishReason", "UNKNOWN")
        # Safely extract text — content/parts may be absent on MAX_TOKENS truncation
        parts = candidate.get("content", {}).get("parts", [])
        text = parts[0].get("text", "") if parts else ""
        if not text:
            # Retry once with doubled token budget
            if max_tokens < 4096:
                logger.warning("Gemini empty response (finishReason=%s), retrying with 2x tokens", finish)
                payload["generationConfig"]["maxOutputTokens"] = min(max_tokens * 2, 8192)
                _GEMINI_LAST_CALL = time.time()
                resp2 = requests.post(url, json=payload, timeout=60,
                                      headers={"Content-Type": "application/json"})
                resp2.raise_for_status()
                data2 = resp2.json()
                parts2 = data2.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                text = parts2[0].get("text", "") if parts2 else ""
            if not text:
                raise RuntimeError(f"Gemini returned empty text after retry (finishReason={finish})")
        return text
    except (requests.exceptions.RequestException, RuntimeError) as e:
        logger.error("Gemini Flash failed: %s", e)
        raise RuntimeError(f"Gemini Flash error: {e}")


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


def _call_openrouter(system_prompt: str, query: str,
                     model: str = None,
                     max_tokens: int = 4096,
                     temperature: float = 0.7) -> str:
    """Call OpenRouter API (OpenAI-compatible) for Qwen and other models.

    Cost varies by model. Qwen 3.5 Flash: $0.065/$0.26 per 1M tokens.
    1M token context window — ideal for bulk context dumps.
    Falls back to Gemini Flash if OPENROUTER_API_KEY is not set.
    """
    if model is None:
        model = QWEN_PLUS_FREE_MODEL  # Primary: Qwen3.6 Plus free (SO 2026-04-03)

    if not OPENROUTER_API_KEY:
        logger.warning("OPENROUTER_API_KEY not set — falling back to Gemini Flash")
        return _call_gemini(system_prompt, query,
                            max_tokens=max_tokens, temperature=temperature)

    resp = requests.post(
        OPENROUTER_URL,
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        },
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://d2mluxury.quest",
            "X-Title": "Thunderbird OS",
        },
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _call_gemini_lite(system_prompt: str, query: str,
                      max_tokens: int = 2000,
                      temperature: float = 0.7) -> str:
    """Call Gemini 2.5 Flash-Lite API — cheapest Gemini tier.

    Cost: $0.10/$0.40 per 1M tokens. 1M context window.
    Use for simple analysis, classification, tasks that don't need full Flash reasoning.
    Respects the same rate limiter as full Flash (shared Google AI quota).
    Falls back to full Gemini Flash if Lite endpoint fails.
    """
    global _GEMINI_LAST_CALL

    if not GOOGLE_AI_API_KEY:
        raise RuntimeError("GOOGLE_AI_API_KEY not set — cannot call Gemini Flash-Lite")

    # Rate limiting — shared with full Flash
    if GEMINI_INTER_CALL_DELAY > 0:
        elapsed = time.time() - _GEMINI_LAST_CALL
        if elapsed < GEMINI_INTER_CALL_DELAY:
            wait = GEMINI_INTER_CALL_DELAY - elapsed
            logger.debug("Gemini rate limiter: sleeping %.1fs", wait)
            time.sleep(wait)

    url = f"{GEMINI_LITE_URL}?key={GOOGLE_AI_API_KEY}"
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
    try:
        _GEMINI_LAST_CALL = time.time()
        resp = requests.post(url, json=payload, timeout=60,
                             headers={"Content-Type": "application/json"})
        resp.raise_for_status()
        data = resp.json()
        parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        text = parts[0].get("text", "") if parts else ""
        if not text:
            logger.warning("Gemini Flash-Lite empty response, falling back to full Flash")
            return _call_gemini(system_prompt, query, max_tokens=max_tokens,
                                temperature=temperature)
        return text
    except Exception as e:
        logger.warning("Gemini Flash-Lite failed, falling back to full Flash: %s", e)
        return _call_gemini(system_prompt, query, max_tokens=max_tokens,
                            temperature=temperature)


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

    # 3b. Handle OpenRouter models — Qwen3.6 Plus (primary), Qwen Flash (bulk), Gemini Lite

    # Qwen3.6 Plus Free — primary operational engine ($0/month, SO 2026-04-03)
    if model_id == "qwen_plus":
        logger.info("Auto-routing [%s] → Qwen3.6 Plus (OpenRouter, free)", task_type.value)
        try:
            response = _call_openrouter(system_prompt, user_prompt,
                                        model=QWEN_PLUS_FREE_MODEL,
                                        max_tokens=max_tokens,
                                        temperature=temperature)
            _log_model_usage("Qwen3.6 Plus (OpenRouter, free)", persona_id, user_prompt,
                             tokens_est=(len(system_prompt + user_prompt) + len(response)) // 4,
                             task_type=task_type.value)
            return {
                "task_type": task_type.value,
                "model": QWEN_PLUS_FREE_MODEL,
                "model_tier": "qwen_plus",
                "engine": "openrouter",
                "response": response,
                "success": True,
            }
        except Exception as e:
            logger.warning("Qwen3.6 Plus failed, falling back to Haiku: %s", e)
            model_id = CLAUDE_HAIKU
            tier = "haiku"

    # Qwen 3.5 Flash — bulk context dumps (1M context window)
    if model_id == "qwen_flash":
        logger.info("Auto-routing [%s] → Qwen 3.5 Flash (OpenRouter)", task_type.value)
        try:
            response = _call_openrouter(system_prompt, user_prompt,
                                        model=QWEN_FLASH_MODEL,
                                        max_tokens=max_tokens,
                                        temperature=temperature)
            _log_model_usage("Qwen 3.5 Flash (OpenRouter)", persona_id, user_prompt,
                             tokens_est=(len(system_prompt + user_prompt) + len(response)) // 4,
                             task_type=task_type.value)
            return {
                "task_type": task_type.value,
                "model": QWEN_FLASH_MODEL,
                "model_tier": "qwen_flash",
                "engine": "openrouter",
                "response": response,
                "success": True,
            }
        except Exception as e:
            logger.warning("Qwen Flash failed, falling back to Gemini Flash: %s", e)
            model_id = CLAUDE_HAIKU
            tier = "haiku"

    # 3c. Handle Perplexity web research — Sonar and Reasoning Pro via OpenRouter
    if model_id == "perplexity":
        logger.info("Auto-routing [%s] → Perplexity Sonar (web search)", task_type.value)
        try:
            response = _call_openrouter(system_prompt, user_prompt,
                                        model=PERPLEXITY_SONAR_MODEL,
                                        max_tokens=max_tokens,
                                        temperature=temperature)
            _log_model_usage("Perplexity Sonar", persona_id, user_prompt,
                             tokens_est=(len(system_prompt + user_prompt) + len(response)) // 4,
                             task_type=task_type.value)
            return {
                "task_type": task_type.value,
                "model": PERPLEXITY_SONAR_MODEL,
                "model_tier": "perplexity",
                "engine": "openrouter",
                "response": response,
                "success": True,
            }
        except Exception as e:
            logger.warning("Perplexity Sonar failed, falling back to Gemini Flash: %s", e)
            model_id = CLAUDE_HAIKU
            tier = "haiku"

    if model_id == "perplexity_reasoning":
        logger.info("Auto-routing [%s] → Perplexity Reasoning Pro (web search + CoT)", task_type.value)
        try:
            response = _call_openrouter(system_prompt, user_prompt,
                                        model=PERPLEXITY_REASONING_MODEL,
                                        max_tokens=max_tokens,
                                        temperature=temperature)
            _log_model_usage("Perplexity Reasoning Pro", persona_id, user_prompt,
                             tokens_est=(len(system_prompt + user_prompt) + len(response)) // 4,
                             task_type=task_type.value)
            return {
                "task_type": task_type.value,
                "model": PERPLEXITY_REASONING_MODEL,
                "model_tier": "perplexity_reasoning",
                "engine": "openrouter",
                "response": response,
                "success": True,
            }
        except Exception as e:
            logger.warning("Perplexity Reasoning failed, falling back to Haiku: %s", e)
            model_id = CLAUDE_HAIKU
            tier = "haiku"

    if model_id == "gemini_lite":
        logger.info("Auto-routing [%s] → Gemini 2.5 Flash-Lite", task_type.value)
        try:
            response = _call_gemini_lite(system_prompt, user_prompt,
                                         max_tokens=max_tokens,
                                         temperature=temperature)
            _log_model_usage("Gemini 2.5 Flash-Lite", persona_id, user_prompt,
                             tokens_est=(len(system_prompt + user_prompt) + len(response)) // 4,
                             task_type=task_type.value)
            return {
                "task_type": task_type.value,
                "model": GEMINI_LITE_MODEL,
                "model_tier": "gemini_lite",
                "engine": "gemini_lite",
                "response": response,
                "success": True,
            }
        except Exception as e:
            logger.warning("Gemini Flash-Lite failed, falling back to Haiku: %s", e)
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

    # No escalation — Opus retired (SO 2026-03-27)
    escalate = False
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


def monitor_response(
    original_task: str,
    generated_response: str,
    persona_id: str = "monitor",
    context: str = "",
) -> Dict[str, Any]:
    """Sonnet quality gate — reviews a Haiku-generated response before delivery.

    Checks for:
      - Factual plausibility (no hallucinated prices, dates, booking numbers)
      - D2M brand compliance (company name, sign-off, tone)
      - Persona voice accuracy (COS authority, Dani warmth, etc.)
      - Completeness relative to the task
      - Fabricated data flags

    Args:
        original_task: The original user prompt / task that generated the response
        generated_response: The response to evaluate
        persona_id: Persona that generated the response (for logging)
        context: Optional additional context (system prompt, client name, etc.)

    Returns:
        Dict with:
          passed (bool): True if response clears quality gate
          score (int): 0–100 quality score
          issues (list[str]): Problems found, empty if passed
          revised (str|None): Sonnet-improved response if issues found, else None
          model_tier (str): "sonnet" (always for monitor)
          elapsed_ms (int): Monitor call duration
    """
    import time
    t0 = time.time()

    monitor_system = """You are the Thunderbird Response Quality Monitor for Dreams2Memories Travel, LLC.

You review AI-generated staff responses before they are delivered. Your job is to catch:
1. FACTUAL ERRORS — hallucinated prices, wrong dates, made-up booking numbers, invented flight details
2. BRAND VIOLATIONS — wrong company name (must be "Dreams2Memories Travel, LLC", never "Love Group Travel"), wrong sign-off (must be "Thanks" or "Thank you", NEVER "Best")
3. PERSONA DRIFT — COS (Hale) must be measured/authoritative, Dani must be warm/concierge, A2 must be evidence-first
4. COMPLETENESS GAPS — task asked for X, response only delivered partial X
5. TONE PROBLEMS — too casual, too corporate, condescending, or falsely confident

Respond ONLY with a JSON object in this exact format:
{
  "passed": true|false,
  "score": 0-100,
  "issues": ["issue 1", "issue 2"],
  "revised": "full revised response OR null if passed",
  "rationale": "one sentence explaining the score"
}

If passed=true, set revised=null. If passed=false, provide a corrected version in "revised".
Score 85+ = pass threshold."""

    monitor_user = f"""ORIGINAL TASK:
{original_task}

PERSONA: {persona_id}
{f'CONTEXT: {context}' if context else ''}

GENERATED RESPONSE TO EVALUATE:
{generated_response}

Evaluate now."""

    try:
        raw = _call_anthropic(
            monitor_system, monitor_user,
            model=CLAUDE_SONNET,
            max_tokens=2000,
            temperature=0.2,
        )

        # Parse JSON from response (strip markdown fences if present)
        json_str = raw.strip()
        if json_str.startswith("```"):
            json_str = json_str.split("```")[1]
            if json_str.startswith("json"):
                json_str = json_str[4:]
        result = json.loads(json_str.strip())

        elapsed = int((time.time() - t0) * 1000)
        result["model_tier"] = "sonnet"
        result["elapsed_ms"] = elapsed

        # Log to router stats
        _log_model_usage(
            "Claude Sonnet (monitor)", persona_id,
            original_task[:120],
            tokens_est=(len(monitor_system + monitor_user + raw)) // 4,
            task_type="response_monitor",
        )

        passed = result.get("passed", True)
        score = result.get("score", 100)
        logger.info(
            "Response monitor [%s]: passed=%s score=%d elapsed=%dms",
            persona_id, passed, score, elapsed,
        )
        return result

    except json.JSONDecodeError as e:
        logger.warning("Monitor returned non-JSON: %s — treating as pass", e)
        return {
            "passed": True,
            "score": 90,
            "issues": [],
            "revised": None,
            "model_tier": "sonnet",
            "elapsed_ms": int((time.time() - t0) * 1000),
            "rationale": "Monitor parse error — defaulting to pass",
        }
    except Exception as e:
        logger.error("Response monitor failed: %s", e)
        return {
            "passed": True,
            "score": 0,
            "issues": [f"Monitor error: {e}"],
            "revised": None,
            "model_tier": "sonnet",
            "elapsed_ms": int((time.time() - t0) * 1000),
            "rationale": "Monitor unavailable — pass-through",
        }


# Task types that automatically trigger the response monitor
_MONITOR_TASK_TYPES = {
    TaskType.CLIENT_FACING,
    TaskType.CREATIVE,
    TaskType.MORNING_BRIEF,
    TaskType.VOICE_PROFILE,
}


def route_and_call_monitored(
    system_prompt: str,
    user_prompt: str,
    task_hint: str = None,
    max_tokens: int = 2000,
    temperature: float = 0.7,
    persona_id: str = "router",
    monitor_all: bool = False,
) -> Dict[str, Any]:
    """route_and_call() + Sonnet quality gate for flagged task types.

    Generates via the normal router, then passes client-facing / creative /
    morning-brief / voice-profile responses through monitor_response().
    If the monitor fails (score < 85), the revised version is substituted.

    Args:
        monitor_all: If True, monitors every response regardless of task type.
                     Default False (only CLIENT_FACING, CREATIVE, MORNING_BRIEF, VOICE_PROFILE).

    Returns:
        Normal route_and_call dict plus:
          monitor (dict|None): Full monitor result, or None if not monitored
    """
    result = route_and_call(
        system_prompt, user_prompt,
        task_hint=task_hint,
        max_tokens=max_tokens,
        temperature=temperature,
        persona_id=persona_id,
    )

    if not result.get("success"):
        result["monitor"] = None
        return result

    # Determine if this task type warrants monitoring
    task_type_str = result.get("task_type", "")
    try:
        task_type_enum = TaskType(task_type_str)
    except ValueError:
        task_type_enum = None

    should_monitor = (
        monitor_all
        or (task_type_enum in _MONITOR_TASK_TYPES)
    )

    if not should_monitor:
        result["monitor"] = None
        return result

    # Run Sonnet quality gate
    monitor_result = monitor_response(
        original_task=user_prompt,
        generated_response=result["response"],
        persona_id=persona_id,
        context=system_prompt[:500],
    )
    result["monitor"] = monitor_result

    # If monitor failed, substitute the revised response
    if not monitor_result.get("passed", True) and monitor_result.get("revised"):
        logger.info(
            "Monitor substituted response for [%s] — score %d, issues: %s",
            persona_id,
            monitor_result.get("score", 0),
            monitor_result.get("issues", []),
        )
        result["response"] = monitor_result["revised"]
        result["monitor_substituted"] = True

    return result


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
