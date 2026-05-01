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
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
XAI_API_KEY = os.getenv("XAI_API_KEY", "")

# Model aliases (Groq eliminated 2026-04-28, replaced with OpenRouter DeepSeek)
DEEPSEEK_PRIMARY_MODEL = "deepseek/deepseek-v4-pro"
QWEN_PLUS_FREE_MODEL = "deepseek/deepseek-v4-pro"  # Legacy alias
GROQ_MODELS = ["groq_fast", "groq_light"]  # Legacy—no longer used

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
    GROK_2M = "grok_2m"              # 2M context, reasoning, cheapest for large
    GEMINI_VISION = "gemini_vision"  # 1M context, multimodal, fastest
    DEEPSEEK_OPTIMIZED = "deepseek_optimized"  # 1M context, cheapest reasoning
    FREE = "free"                    # 200K context, $0, rate limited


MODEL_STRATEGY = {
    ModelTier.GROK_2M.value: {
        "provider": "openrouter",
        "model_id": "x-ai/grok-4.1-fast",
        "context": "2M tokens",
        "cost_per_M": 0.70,
        "input_cost": 0.20,
        "output_cost": 0.50,
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
        "rationale": "2M context for complete document sets; cost-effective reasoning at scale"
    },

    ModelTier.GEMINI_VISION.value: {
        "provider": "openrouter",
        "model_id": "google/gemini-3-flash-preview",
        "context": "1M tokens",
        "cost_per_M": 0.375,
        "input_cost": 0.075,
        "output_cost": 0.30,
        "vision_support": True,
        "reasoning": False,
        "speed": "fastest",
        "use_cases": [
            "brief_generation",
            "visual_synthesis",
            "itinerary_imagery",
            "dashboard_copy",
            "multimodal_analysis",
            "imagery_processing"
        ],
        "rationale": "Multimodal (images, video, audio, PDF); fastest inference; cheaper than Grok for vision"
    },

    ModelTier.DEEPSEEK_OPTIMIZED.value: {
        "provider": "openrouter",
        "model_id": "deepseek/deepseek-v4-pro",
        "context": "1M tokens",
        "cost_per_M": 0.305,
        "input_cost": 0.435,
        "output_cost": 0.87,
        "vision_support": False,
        "reasoning": True,
        "speed": "moderate",
        "use_cases": [
            "routine_analysis",
            "fallback",
            "non_vision_tasks",
            "cost_optimized_reasoning"
        ],
        "rationale": "Lowest cost for pure reasoning; 1M context for standard tasks"
    },

    ModelTier.FREE.value: {
        "provider": "openrouter",
        "model_id": "openrouter/free",
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
        "rate_limits": "20 req/min, 200 req/day",
        "rationale": "Zero cost for non-critical tasks; use within rate limits only"
    }
}


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

    # Heuristic routing
    if has_images and "vision" not in task_type.lower():
        log.info(f"Model route: vision detected → {ModelTier.GEMINI_VISION.value}")
        return MODEL_STRATEGY[ModelTier.GEMINI_VISION.value]

    if content_size and content_size > 500_000 and "vision" not in task_type.lower():
        log.info(f"Model route: large context ({content_size} tokens) → {ModelTier.GROK_2M.value}")
        return MODEL_STRATEGY[ModelTier.GROK_2M.value]

    if budget == "minimal":
        log.info(f"Model route: budget minimal → {ModelTier.DEEPSEEK_OPTIMIZED.value}")
        return MODEL_STRATEGY[ModelTier.DEEPSEEK_OPTIMIZED.value]

    if required_context and required_context > 1_000_000:
        log.info(f"Model route: context required {required_context} → {ModelTier.GROK_2M.value}")
        return MODEL_STRATEGY[ModelTier.GROK_2M.value]

    # Default: Gemini Vision (fastest, reasonable cost, multimodal ready)
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
    "fast": "grok_2m",
    "vision": "gemini_vision",
    "research": "deepseek_optimized",
    "cheap": "free"
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


def _call_claude(system_prompt: str, query: str, model: str = "sonnet",
                  temperature: float = 0.7, max_tokens: int = 2000) -> str:
    """
    BACKWARD-COMPATIBILITY STUB: Direct Claude call (Sonnet).
    Routes to Claude 3.5 Sonnet via Anthropic SDK.
    """
    import anthropic

    client = anthropic.Anthropic()
    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": query}]
        )
        result = response.content[0].text
        log.info(f"_call_claude (stub): {len(result)} chars")
        return result
    except Exception as e:
        log.error(f"_call_claude failed: {e}")
        return f"Error: {str(e)}"


def _call_groq(system_prompt: str, query: str, model: str = "fast",
               temperature: float = 0.7, max_tokens: int = 2000) -> str:
    """
    BACKWARD-COMPATIBILITY STUB: _call_groq routes to Claude Sonnet.

    Groq was eliminated 2026-04-28. All calls route to Claude via Anthropic SDK ($0 on Max plan).
    This stub maintains backward compatibility for existing code that imports _call_groq.

    Args:
        system_prompt: System context/instructions
        query: User query/prompt
        model: Model hint ("fast", "light", etc.) — ignored, uses Sonnet
        temperature: Creativity parameter (0.0-2.0)
        max_tokens: Maximum output tokens

    Returns:
        Response text from Claude Sonnet
    """
    return _call_claude(system_prompt, query, model, temperature, max_tokens)


def _call_gemini(system_prompt: str, query: str, model: str = "vision",
                 temperature: float = 0.7, max_tokens: int = 2000) -> str:
    """
    BACKWARD-COMPATIBILITY STUB: _call_gemini routes to Claude Sonnet.
    """
    return _call_claude(system_prompt, query, model, temperature, max_tokens)


def _call_openrouter(system_prompt: str, query: str, model: str = "grok",
                     temperature: float = 0.7, max_tokens: int = 2000) -> str:
    """
    BACKWARD-COMPATIBILITY STUB: _call_openrouter routes to Claude Sonnet.
    """
    return _call_claude(system_prompt, query, model, temperature, max_tokens)


def _call_grok(system_prompt: str, query: str, model: str = "fast",
               temperature: float = 0.7, max_tokens: int = 2000) -> str:
    """
    BACKWARD-COMPATIBILITY STUB: _call_grok (alternate spelling) routes to Claude Sonnet.
    """
    return _call_claude(system_prompt, query, model, temperature, max_tokens)


def classify_task(prompt: str) -> str:
    """
    BACKWARD-COMPATIBILITY STUB: Classify task type.
    Returns "general" for all inputs during recovery.
    """
    return "general"


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

    # Cost estimate
    cost = estimate_cost(ModelTier.GROK_2M.value, input_tokens=500_000, output_tokens=5_000)
    print(f"\nCost estimate (Grok 2M, 500K input, 5K output): ${cost['total_cost']}")

    print("\n✅ Router initialized\n")
