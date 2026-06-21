#!/usr/bin/env python3
"""
Thunderbird Model Router — Dynamic LLM Selection
Optimizes cost, context, and capability matching for Thunderbird OS tasks.
Updated: 2026-04-28
"""

import json
import logging
from enum import Enum
from typing import Optional
import os

log = logging.getLogger("thunderbird_router")

# API Keys & Constants (used by task_processor and other modules)
# OPENROUTER_API_KEY retired 2026-06-15 (MISSION-267, Commander-approved). The key
# is commented out in .env; os.getenv returns "" so every OpenRouter-routed path is
# dead. Constant retained (empty) only so legacy importers don't ImportError; no live
# code path should reach an OpenRouter call — see _call_openrouter_real() retirement.
OPENROUTER_API_KEY = ""  # RETIRED MISSION-267 — do not re-enable; provider decommissioned
XAI_API_KEY = os.getenv("XAI_API_KEY", "")

# Model aliases. DEEPSEEK_PRIMARY_MODEL retained as a RETIRED sentinel because
# OpsCenter/task_processor.py imports it at module scope (deleting breaks startup).
# Value is a non-routable marker, NOT a real model ID — the OpenRouter lane it fed
# is decommissioned (MISSION-267). The live reasoning lane is call_gemini_large_context.
DEEPSEEK_PRIMARY_MODEL = "RETIRED-openrouter-MISSION-267"

# Legacy task classification enum (for backward compatibility)
class TaskType(Enum):
    """Task classification types (DEPRECATED—use route_model instead)"""
    SIMPLE = "simple"
    STANDARD = "standard"
    COMPLEX = "complex"
    RESEARCH = "research"
    CREATIVE = "creative"


class ModelTier(Enum):
    """Model selection tiers"""
    SONNET_MAX_LARGE = "sonnet_max_large"  # Large context via MAX OAuth (user's primary for large tasks)
    GROK_2M = "grok_2m"              # 2M context, reasoning, cheapest for large (UNAVAILABLE — fallback to SONNET_MAX_LARGE)
    GEMINI_VISION = "gemini_vision"  # 1M context, multimodal, fastest (OpenRouter free)
    GEMINI_LARGE_CONTEXT = "gemini_large_context"  # 1M context, direct Google AI API (Pro sub) — PDF/cruise brochure reads
    DEEPSEEK_OPTIMIZED = "deepseek_optimized"  # 1M context, cheapest reasoning
    FREE = "free"                    # 200K context, $0, rate limited


MODEL_STRATEGY = {
    ModelTier.SONNET_MAX_LARGE.value: {
        "provider": "anthropic",
        "model_id": "claude-sonnet-4-6",
        "context": "200K tokens",
        "cost_per_M": 0,
        "input_cost": 0,
        "output_cost": 0,
        "vision_support": False,
        "reasoning": True,
        "speed": "fast",
        "use_cases": [
            "large_context_research",
            "incubator",
            "intel_sweep",
            "competitive_analysis",
            "ship_research",
            "document_analysis"
        ],
        "rationale": "Claude Sonnet via MAX subscription — user's primary for large context tasks. Headless spawn uses MAX OAuth credentials."
    },


    ModelTier.GEMINI_VISION.value: {
        "provider": "google_ai_direct",
        "model_id": "gemini-2.5-flash-lite",
        "context": "1M tokens",
        "cost_per_M": 0.00,
        "input_cost": 0.00,
        "output_cost": 0.00,
        "vision_support": True,
        "reasoning": False,
        "speed": "fastest",
        "use_cases": [
            "brief_generation",
            "visual_synthesis",
            "itinerary_imagery",
            "dashboard_copy",
            "multimodal_analysis",
            "imagery_processing",
            "routine_ops",
            "context_scan",
            "summarize",
            "ops_task"
        ],
        "rationale": "REWIRED 2026-06-15 (MISSION-267): was OpenRouter free-tier "
                     "'google/gemini-flash-2.5-lite:free' (fabricated ID via retired provider). "
                     "Now the LIVE direct-Google lane — gemini-2.5-flash-lite via "
                     "core.ai_infra.gemini_client (GEMINI_API_KEY). Same lane the _call_* "
                     "ops wrappers and call_gemini_large_context use.",
    },

    ModelTier.GEMINI_LARGE_CONTEXT.value: {
        "provider": "google_ai_direct",
        "model_id": "gemini-2.5-pro",
        "context": "1M tokens",
        "cost_per_M": 0.00,
        "input_cost": 0.00,
        "output_cost": 0.00,
        "vision_support": True,
        "reasoning": True,
        "speed": "moderate",
        "use_cases": [
            "pdf_read",
            "cruise_brochure",
            "document_analysis",
            "large_file_read",
            "notebooklm_prep",
            "deep_research",
            "multi_doc_synthesis",
        ],
        "rationale": "Direct Google AI API via gemini_client.call_gemini_pro. "
                     "1M context window — reads full cruise PDFs, brochures, dossier bundles in one shot. "
                     "Google AI Pro subscription ($20.60/mo) — $0 marginal cost on free tier allowlist. "
                     "Use for any task where content_size > 100K tokens. Re-enabled 2026-06-05.",
    },

    ModelTier.DEEPSEEK_OPTIMIZED.value: {
        "provider": "google_ai_direct",
        "model_id": "gemini-2.5-flash",
        "context": "1M tokens",
        "cost_per_M": 0.00,
        "input_cost": 0.00,
        "output_cost": 0.00,
        "vision_support": False,
        "reasoning": True,
        "speed": "moderate",
        "use_cases": [
            "routine_analysis",
            "fallback",
            "non_vision_tasks",
            "cost_optimized_reasoning"
        ],
        "rationale": "REWIRED 2026-06-15 (MISSION-267): was OpenRouter "
                     "'qwen/qwen3.6-plus-04-02:free' (fabricated ID via retired provider). "
                     "Now LIVE direct-Google gemini-2.5-flash (reasoning-capable, $0 free tier) "
                     "via core.ai_infra.gemini_client. Tier name kept for CREW_MODEL_TIER compat."
    },

    ModelTier.FREE.value: {
        "provider": "google_ai_direct",
        "model_id": "gemini-2.5-flash-lite",
        "context": "200K tokens",
        "cost_per_M": 0.00,
        "input_cost": 0,
        "output_cost": 0,
        "vision_support": False,
        "reasoning": False,
        "speed": "variable",
        "use_cases": [
            "testing",
            "simple_classification",
            "templating",
            "non_critical"
        ],
        "rate_limits": "15 req/min, 1500 req/day (Google free tier)",
        "rationale": "REWIRED 2026-06-15 (MISSION-267): was OpenRouter 'openrouter/free'. "
                     "Now LIVE direct-Google gemini-2.5-flash-lite free tier."
    }
}


# ── Crew Tier Map (SO-TOKEN-DISCIPLINE 2026-05-29) ────────────────────────────
# Maps each A-staff persona to the minimum cost tier appropriate for their role.
# Rule: use the cheapest tier that meets quality bar. Only escalate to Sonnet
# when client-facing copy or complex judgment is required.
# Updated 2026-05-31: Removed unavailable Grok, routed expensive tasks to DeepSeek.
CREW_MODEL_TIER: dict[str, str] = {
    # Client-facing / judgment-required → Sonnet MAX ($0 on MAX plan)
    "HALE":   ModelTier.SONNET_MAX_LARGE.value,   # COS orchestration, decisions
    "A3":     ModelTier.SONNET_MAX_LARGE.value,   # Dani — ALL client-facing copy
    "A6":     ModelTier.SONNET_MAX_LARGE.value,   # Luna — narrative/brand copy
    "A1":     ModelTier.SONNET_MAX_LARGE.value,   # Navarro — profile synthesis (nuance)
    "EXEC":   ModelTier.SONNET_MAX_LARGE.value,   # Solberg-Vega — proposals, voice
    # Research / structured output — Dembe gets large-context direct API for PDF/brochure reads
    "A2":     ModelTier.GEMINI_LARGE_CONTEXT.value,  # Dembe — destination research + PDF brochures (1M ctx)
    "A5":     ModelTier.GEMINI_VISION.value,      # Castillo — strategy drafts
    "A7":     ModelTier.GEMINI_VISION.value,      # Sterling — process/metrics
    "A8":     ModelTier.GEMINI_VISION.value,      # Reyes — product matching
    # Commission analysis / simple extraction → DeepSeek ($0.14/1M input, 95% cheaper than Sonnet)
    "A9":     ModelTier.DEEPSEEK_OPTIMIZED.value, # Harlan — commission audits (structured lookup, not reasoning-heavy)
    # Innovation / large-context → Sonnet MAX (Grok 2M unavailable; MAX is backup for large context)
    "A12":    ModelTier.SONNET_MAX_LARGE.value,   # ELON — innovation/disruption (fallback; ideally use Gemini for fast ideation)
}

# Models explicitly blocked from auto-selection (too expensive for bulk use)
BLOCKED_MODELS: set[str] = {
    "deepseek/deepseek-v4-pro-20260423",
    "deepseek/deepseek-v4-pro",
    "deepseek-v4-pro",
}


def get_crew_model(persona: str) -> dict:
    """Return the model strategy dict for a given crew member."""
    tier = CREW_MODEL_TIER.get(persona.upper(), ModelTier.GEMINI_VISION.value)
    return MODEL_STRATEGY[tier]


def is_model_blocked(model_id: str) -> bool:
    """Return True if model_id is in the BLOCKED_MODELS set."""
    return model_id in BLOCKED_MODELS or any(b in model_id for b in BLOCKED_MODELS)


def route_model(
    task_type: str,
    content_size: Optional[int] = None,
    has_images: bool = False,
    budget: str = "normal",
    required_context: Optional[int] = None
) -> dict:
    """
    Route task to optimal model based on characteristics.

    Args:
        task_type: One of MODEL_STRATEGY.keys() or a use case name
        content_size: Approximate input size in tokens (None = unknown)
        has_images: Whether task includes images/vision
        budget: "minimal", "normal", "premium"
        required_context: Minimum context window needed in tokens

    Returns:
        dict with model_id, provider, and metadata
    """

    # Direct tier selection
    if task_type in MODEL_STRATEGY:
        tier = task_type
        log.info(f"Model route: direct tier {tier}")
        return MODEL_STRATEGY[tier]

    # Use case matching
    for tier, config in MODEL_STRATEGY.items():
        if task_type in config.get("use_cases", []):
            log.info(f"Model route: use case '{task_type}' → {tier}")
            return config

    # Cost optimization: brief/summarization tasks → use cheaper tier (SO-TOKEN-DISCIPLINE 2026-05-29)
    task_lower = task_type.lower()
    if any(keyword in task_lower for keyword in ["brief", "summary", "summariz", "digest", "scan", "report"]):
        log.info(f"Model route: brief/summary task '{task_type}' → {ModelTier.GEMINI_VISION.value}")
        return MODEL_STRATEGY[ModelTier.GEMINI_VISION.value]

    # Cost optimization: audit/extraction tasks → use DeepSeek (cheaper, good for structured tasks)
    if any(keyword in task_lower for keyword in ["audit", "extract", "analyz", "commission", "reconcil", "inventory"]):
        log.info(f"Model route: audit/analysis task '{task_type}' → {ModelTier.DEEPSEEK_OPTIMIZED.value}")
        return MODEL_STRATEGY[ModelTier.DEEPSEEK_OPTIMIZED.value]

    # Heuristic routing
    if has_images and "vision" not in task_type.lower():
        log.info(f"Model route: vision detected → {ModelTier.GEMINI_VISION.value}")
        return MODEL_STRATEGY[ModelTier.GEMINI_VISION.value]

    if content_size and content_size > 100_000:
        log.info(f"Model route: large context ({content_size} tokens) → {ModelTier.GEMINI_LARGE_CONTEXT.value}")
        return MODEL_STRATEGY[ModelTier.GEMINI_LARGE_CONTEXT.value]

    if budget == "minimal":
        log.info(f"Model route: budget minimal → {ModelTier.DEEPSEEK_OPTIMIZED.value}")
        return MODEL_STRATEGY[ModelTier.DEEPSEEK_OPTIMIZED.value]

    if required_context and required_context > 1_000_000:
        log.info(f"Model route: context required {required_context} → {ModelTier.SONNET_MAX_LARGE.value}")
        return MODEL_STRATEGY[ModelTier.SONNET_MAX_LARGE.value]

    # Default: Gemini Flash Lite (fastest, reasonable cost, multimodal ready)
    log.info(f"Model route: default → {ModelTier.GEMINI_VISION.value}")
    return MODEL_STRATEGY[ModelTier.GEMINI_VISION.value]


def estimate_cost(model_tier: str, input_tokens: int, output_tokens: int) -> dict:
    """
    Estimate cost for a task.

    Args:
        model_tier: One of MODEL_STRATEGY.keys()
        input_tokens: Estimated input tokens
        output_tokens: Estimated output tokens

    Returns:
        dict with cost breakdown
    """
    if model_tier not in MODEL_STRATEGY:
        return {"error": f"Unknown model tier: {model_tier}"}

    config = MODEL_STRATEGY[model_tier]
    input_cost = (input_tokens / 1_000_000) * config["input_cost"]
    output_cost = (output_tokens / 1_000_000) * config["output_cost"]
    total = input_cost + output_cost

    return {
        "model": model_tier,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "input_cost": round(input_cost, 4),
        "output_cost": round(output_cost, 4),
        "total_cost": round(total, 4),
        "cost_per_M": config["cost_per_M"]
    }


def get_all_models() -> dict:
    """Return all available models and their specs"""
    return MODEL_STRATEGY


def log_routing_decision(task_type: str, selected_model: str, rationale: str = ""):
    """Log routing decision for audit trail"""
    log.info(f"ROUTE: task={task_type} → model={selected_model} | {rationale}")


# Additional routing functions (backward compatibility)
MODEL_TAGS = {
    "fast": "gemini_vision",        # Grok 2M removed 2026-05-31 (unavailable)
    "vision": "gemini_vision",      # Gemini 3.1 Flash Lite ($0.03/1M input)
    "research": "deepseek_optimized",  # DeepSeek ($0.14/1M input)
    "cheap": "free"                 # OpenRouter free tier (rate limited)
}


def smart_route(task: str, **kwargs) -> dict:
    """Smart routing for tasks with contextual awareness (routes to route_model)"""
    return route_model(task, **kwargs)


def route_call(task: str, prompt: str, **kwargs) -> str:
    """Route task and execute call (DEPRECATED—use _call_claude directly)"""
    return _call_claude(system_prompt=f"Task: {task}", query=prompt, **kwargs)


def route_and_call(task: str, prompt: str, **kwargs) -> str:
    """Route task and execute call (alias for route_call, DEPRECATED)"""
    return route_call(task, prompt, **kwargs)


def register_router_tools() -> dict:
    """Register router tools for MCP server (returns empty dict—MCP tools via travel_mcp_server.py)"""
    return {}


def _call_openrouter_real(system_prompt: str, query: str,
                          model: str = "RETIRED-openrouter-MISSION-267",
                          temperature: float = 0.7, max_tokens: int = 2000) -> str:
    """
    RETIRED 2026-06-15 (MISSION-267, Commander-approved). The OpenRouter provider
    was decommissioned and OPENROUTER_API_KEY removed from .env. This function used
    to issue live OpenRouter calls; it now fails loud rather than silently raising a
    generic 'key not set' that callers swallowed into native-Claude fallback.

    Live replacements:
      - Ops / fast text  → core.ai_infra.gemini_client.call_gemini_lite (direct Google)
      - Large context    → call_gemini_large_context (Gemini 2.5 Pro, direct Google)
    Do NOT re-introduce OpenRouter. Retirement stands.
    """
    raise RuntimeError(
        "OpenRouter provider RETIRED 2026-06-15 (MISSION-267). "
        "_call_openrouter_real is decommissioned — no live OpenRouter path exists. "
        "Use gemini_client.call_gemini_lite (ops) or call_gemini_large_context (large) instead."
    )


# ── Crew-aware model selection ────────────────────────────────────────────────
# OpenRouter Gemini/Grok model aliases RETIRED 2026-06-15 (MISSION-267).
# The ops-text wrappers below now route to the LIVE direct-Google lane
# (core.ai_infra.gemini_client) — same lane call_gemini_large_context uses.


def _call_gemini_lite_direct(system_prompt: str, query: str,
                             temperature: float = 0.7, max_tokens: int = 2000,
                             caller: str = "router") -> str:
    """LIVE ops lane: Gemini 2.5 Flash-Lite via direct Google AI API (GEMINI_API_KEY).
    Replaces the retired OpenRouter Gemini Flash Lite path (MISSION-267).
    gemini_client handles rate-limiting, Harlan cost logging, and flash fallback.
    """
    from core.ai_infra.gemini_client import call_gemini_lite
    return call_gemini_lite(
        system_prompt=system_prompt,
        user_prompt=query,
        max_tokens=max_tokens,
        temperature=temperature,
        caller=caller,
    )


def _call_claude(system_prompt: str, query: str, model: str = "sonnet",
                  temperature: float = 0.7, max_tokens: int = 2000) -> str:
    """Ops-text wrapper (name kept for backward compat). REWIRED 2026-06-15
    (MISSION-267): OpenRouter retired → direct-Google Gemini Flash-Lite."""
    return _call_gemini_lite_direct(system_prompt, query,
                                    temperature=temperature, max_tokens=max_tokens,
                                    caller="_call_claude")


def _call_groq_direct(system_prompt: str, query: str,
                      temperature: float = 0.7, max_tokens: int = 2000,
                      model: str = "llama-3.1-8b-instant",
                      caller: str = "_call_groq_direct") -> str:
    """LIVE: Groq direct API — ultra-fast small-context classify/triage lane.
    Key: GROQ_API_KEY. Model: llama-3.1-8b-instant (free tier, 131K ctx).
    Wired 2026-06-21 (integrate-all-59 C31).
    Falls back to Gemini Flash-Lite on missing key or API error.
    """
    groq_key = os.getenv("GROQ_API_KEY", "")
    if not groq_key:
        log.warning("%s: GROQ_API_KEY not set, falling back to Gemini Flash-Lite", caller)
        return _call_gemini_lite_direct(system_prompt, query,
                                        temperature=temperature, max_tokens=max_tokens,
                                        caller=caller)
    try:
        from groq import Groq
        client = Groq(api_key=groq_key)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content or ""
    except Exception as exc:
        log.warning("%s: Groq error (%s), falling back to Gemini Flash-Lite", caller, exc)
        return _call_gemini_lite_direct(system_prompt, query,
                                        temperature=temperature, max_tokens=max_tokens,
                                        caller=caller)


def _call_groq(system_prompt: str, query: str, model: str = "fast",
               temperature: float = 0.7, max_tokens: int = 2000) -> str:
    """LIVE classify/triage lane via Groq (llama-3.1-8b-instant).
    Rewired 2026-06-21: was Gemini stub (post MISSION-267); now real Groq
    with Gemini Flash-Lite fallback. Key: GROQ_API_KEY."""
    return _call_groq_direct(system_prompt, query,
                             temperature=temperature, max_tokens=max_tokens,
                             caller="_call_groq")


def _call_gemini(system_prompt: str, query: str, model: str = "vision",
                 temperature: float = 0.7, max_tokens: int = 2000) -> str:
    """Backward compat. REWIRED 2026-06-15 (MISSION-267): OpenRouter retired →
    direct-Google Gemini Flash-Lite (the live, healthy lane)."""
    return _call_gemini_lite_direct(system_prompt, query,
                                    temperature=temperature, max_tokens=max_tokens,
                                    caller="_call_gemini")


def _call_cloudflare_workers_ai(system_prompt: str, query: str,
                                temperature: float = 0.7, max_tokens: int = 2000,
                                model: str = "@cf/meta/llama-3.1-8b-instruct",
                                caller: str = "_call_cloudflare_workers_ai") -> str:
    """FREE: Cloudflare Workers AI — 10,000 neurons/day, zero card required.
    Wired 2026-06-21 (daily-search wave 3 integration). Use for classify/triage.
    Keys needed: CLOUDFLARE_ACCOUNT_ID + CLOUDFLARE_API_TOKEN (free at dash.cloudflare.com).
    Falls back to Gemini Flash-Lite on missing keys or API error.
    """
    account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
    api_token = os.getenv("CLOUDFLARE_API_TOKEN", "")
    if not account_id or not api_token:
        log.warning("%s: CLOUDFLARE_ACCOUNT_ID or CLOUDFLARE_API_TOKEN not set — fallback", caller)
        return _call_gemini_lite_direct(system_prompt, query,
                                        temperature=temperature, max_tokens=max_tokens,
                                        caller=caller)
    try:
        import requests as _req
        url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"
        resp = _req.post(
            url,
            headers={"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"},
            json={"messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query},
            ], "max_tokens": max_tokens},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("result", {}).get("response", "") or ""
    except Exception as exc:
        log.warning("%s: Cloudflare Workers AI error (%s) — fallback", caller, exc)
        return _call_gemini_lite_direct(system_prompt, query,
                                        temperature=temperature, max_tokens=max_tokens,
                                        caller=caller)


def _call_github_models(system_prompt: str, query: str,
                        temperature: float = 0.7, max_tokens: int = 2000,
                        model: str = "meta-llama-3.1-8b-instruct",
                        caller: str = "_call_github_models") -> str:
    """FREE: GitHub Models — Azure inference infra, free with GitHub account.
    Wired 2026-06-21 (daily-search wave 3 integration). Use for classify/triage.
    Key needed: GITHUB_TOKEN (PAT with models:read scope, free at github.com/settings/tokens).
    Available models: meta-llama-3.1-8b-instruct, Phi-4, Mistral-small, Cohere-command-r.
    Falls back to Gemini Flash-Lite on missing key or API error.
    """
    github_token = os.getenv("GITHUB_TOKEN", "") or os.getenv("GITHUB_PAT", "")
    if not github_token:
        log.warning("%s: GITHUB_TOKEN not set — fallback to Gemini Flash-Lite", caller)
        return _call_gemini_lite_direct(system_prompt, query,
                                        temperature=temperature, max_tokens=max_tokens,
                                        caller=caller)
    try:
        import requests as _req
        resp = _req.post(
            "https://models.inference.ai.azure.com/chat/completions",
            headers={"Authorization": f"Bearer {github_token}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"] or ""
    except Exception as exc:
        log.warning("%s: GitHub Models error (%s) — fallback to Gemini Flash-Lite", caller, exc)
        return _call_gemini_lite_direct(system_prompt, query,
                                        temperature=temperature, max_tokens=max_tokens,
                                        caller=caller)


def _call_openrouter(system_prompt: str, query: str, model: str = "grok",
                     temperature: float = 0.7, max_tokens: int = 2000) -> str:
    """Backward compat. The OpenRouter provider is RETIRED (MISSION-267); this
    ops-text wrapper behaved as a Gemini Flash-Lite proxy, so it is REWIRED
    2026-06-15 to the live direct-Google Gemini Flash-Lite lane rather than
    failing — callers depend on ops text, not on the OpenRouter transport."""
    return _call_gemini_lite_direct(system_prompt, query,
                                    temperature=temperature, max_tokens=max_tokens,
                                    caller="_call_openrouter")


def _call_grok(system_prompt: str, query: str, model: str = "fast",
               temperature: float = 0.7, max_tokens: int = 2000) -> str:
    """RETIRED 2026-06-15 (MISSION-267). Grok was only reachable via the
    decommissioned OpenRouter transport; there is NO live direct xAI path wired
    in this tree, so this FAILS LOUD rather than silently degrading. All known
    callers (price_monitor, scheduler) gate this behind `if XAI_API_KEY:` and
    fall back to native Claude/Anthropic on exception, so the loud failure is
    caught cleanly downstream. Do NOT build a new direct-xAI path here — that is
    feature work, out of decommission scope."""
    raise RuntimeError(
        "_call_grok RETIRED 2026-06-15 (MISSION-267): OpenRouter decommissioned and "
        "no live direct xAI/Grok path is wired. Callers should fall back to native "
        "Claude (price extraction) — see price_monitor.py / scheduler.py XAI_API_KEY gate."
    )


def classify_task(prompt: str) -> str:
    """
    BACKWARD-COMPATIBILITY STUB: Classify task type.
    Returns "general" for all inputs during recovery.
    """
    return "general"


def call_gemini_large_context(system_prompt: str, user_prompt: str,
                               max_tokens: int = 4096, caller: str = "router",
                               task_hint: str = "") -> str:
    """
    Dispatch to Gemini 2.5 Pro via direct Google AI API.
    Use for any task with >100K token content: cruise PDFs, brochure bundles,
    multi-dossier synthesis, full itinerary reads.
    Routes through gemini_client canonical chokepoint (rate limiting + Harlan logging).
    Google AI Pro subscription — $0 marginal cost on free-tier allowlist.
    """
    from core.ai_infra.gemini_client import call_gemini_pro
    return call_gemini_pro(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        max_tokens=max_tokens,
        caller=caller,
        task_hint=task_hint,
    )


if __name__ == "__main__":
    # Quick test
    logging.basicConfig(level=logging.INFO)

    print("\n=== THUNDERBIRD MODEL ROUTER ===\n")

    # Test 1: Large context research
    result = route_model("incubator", content_size=800_000)
    print(f"Test 1 (large context): {result['model_id']}")

    # Test 2: Imagery task
    result = route_model("brief_generation", has_images=True)
    print(f"Test 2 (imagery): {result['model_id']}")

    # Test 3: Cost-optimized
    result = route_model("routine_analysis", budget="minimal")
    print(f"Test 3 (minimal cost): {result['model_id']}")

    # Test 4: Free tier
    result = route_model("testing")
    print(f"Test 4 (free): {result['model_id']}")

    # Cost estimate (GROK_2M tier retired — use live large-context tier)
    cost = estimate_cost(ModelTier.GEMINI_LARGE_CONTEXT.value, input_tokens=500_000, output_tokens=5_000)
    print(f"\nCost estimate (Gemini Large Context, 500K input, 5K output): ${cost['total_cost']}")

    print("\n✅ Router initialized\n")
