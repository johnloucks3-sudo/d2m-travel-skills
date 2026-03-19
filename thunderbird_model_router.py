"""
Thunderbird Model Router
=========================
Claude Opus-first routing via Max plan ($0). All fast/premium calls route to
Claude Opus via CLI subprocess. Specialty models (Gemini, Grok, DeepSeek) retained
for their specific capabilities (Workspace, research, cheap extraction).

Default: Claude Opus (via CLI, $0 on Max plan)
Specialty: Gemini Flash (Workspace), Grok (research), DeepSeek (extraction, PII-fenced)

Usage:
    from thunderbird_model_router import route_call, TaskType, MODEL_TAGS

    # Routes to Claude Opus
    result = route_call("A3", "What's the status of Kuklinski bookings?")

    # Also routes to Claude Opus (creative work)
    result = route_call("EXEC", "Write a proposal for the McLeod Mediterranean trip",
                        task_type=TaskType.CREATIVE)
"""

import os
import re
import logging
import requests
import subprocess
import base64
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Model Usage Tags ──
MODEL_TAGS = {
    "fast": "\U0001f7e3 Claude Opus",
    "premium": "\U0001f7e3 Claude Opus",
    "light": "\U0001f7e3 Claude Opus",
    "kimi": "\U0001f7e3 Claude Opus",
    "detail": "\U0001f7e3 Claude Opus",
    "visionary": "\U0001f7e3 Claude Opus",
    "gemini": "\U0001f48e Gemini Flash",
    "workspace": "\U0001f48e Gemini Flash",
    "research": "\u26a1 Grok",
    "grok": "\u26a1 Grok",
    "extraction": "\U0001f512 DeepSeek (fenced)",
    "deepseek": "\U0001f512 DeepSeek (fenced)",
    "claude": "\U0001f7e3 Claude Sonnet",
}

# ── Model Usage Log Path ──
_MODEL_USAGE_LOG = Path(__file__).parent / "logs" / "model_usage.log"

# ── API Keys ──
# Groq ELIMINATED — all fast/premium calls route to Claude Opus via Max plan ($0)
GROQ_API_KEY = ""  # DEPRECATED — retained for backward compatibility only
GROQ_URL = ""      # DEPRECATED — retained for backward compatibility only
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
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


class TaskType(Enum):
    """Task classification for routing decisions."""
    OPERATIONAL = "operational"      # Status checks, data lookups, summaries
    ANALYTICAL = "analytical"        # Number crunching, comparisons, audits
    CREATIVE = "creative"            # Client copy, proposals, narratives
    STRATEGIC = "strategic"          # Business decisions, pricing, growth
    CRISIS = "crisis"                # Time-sensitive logistics, problem solving
    CLASSIFICATION = "classification"  # Email triage, categorization
    IMAGE = "image"                  # Image generation (routes to FLUX.1)
    EXTRACTION = "extraction"        # Data extraction, parsing (routes to DeepSeek)


# ============================================================
# DEEPSEEK PII FENCE — DATA SOVEREIGNTY PROTECTION
# DeepSeek is a Chinese company. NEVER send client PII.
# All requests are scanned. PII triggers automatic reroute to Claude Opus.
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
    rerouted to Claude Opus (US-based) instead. This is a data sovereignty safeguard.
    """
    for pattern in _PII_PATTERNS:
        match = pattern.search(text)
        if match:
            # Log which pattern type triggered (not the actual PII data)
            logger.warning(
                "PII detected (pattern: %s...) — DeepSeek blocked, routing to Claude Opus",
                pattern.pattern[:40],
            )
            return True
    return False


# ── Routing Rules ──
# Personas that benefit from Claude for certain task types
ESCALATION_MAP = {
    # EXEC and Luna (A6) always escalate creative tasks — that's their core value
    "EXEC": {TaskType.CREATIVE},
    "A6":   {TaskType.CREATIVE},
    # A5 (Castillo) escalates strategic analysis
    "A5":   {TaskType.STRATEGIC},
    # CH (Washington) escalates anything — wisdom needs depth
    "CH":   {TaskType.CREATIVE, TaskType.STRATEGIC, TaskType.OPERATIONAL},
}

# Legacy model map — all keys now resolve to Claude Sonnet via CLI
# Retained for backward compatibility (call_deepseek fallback references, etc.)
GROQ_MODELS = {
    "fast": "claude-sonnet-4-5",
    "premium": "claude-sonnet-4-5",
    "light": "claude-sonnet-4-5",
    "kimi": "claude-sonnet-4-5",
    "detail": "claude-sonnet-4-5",
    "visionary": "claude-sonnet-4-5",
}

# Claude model — PRIMARY ENGINE (via CLI subprocess, Max plan $0)
# All fast/premium calls route here. API model used for direct _call_claude() only.
CLAUDE_MODEL = "claude-sonnet-4-6-20250514"

# Claude 1M context window — GA at standard pricing (no beta header needed)
CLAUDE_MAX_CONTEXT_TOKENS = 1_000_000
CLAUDE_DEFAULT_MAX_OUTPUT = 16_384  # generous default for Claude output

# Together AI image models
FLUX_MODEL = "black-forest-labs/FLUX.1-schnell-Free"
FLUX_PRO_MODEL = "black-forest-labs/FLUX.1.1-pro"


def _resolve_model_tag(route_key: str) -> str:
    """Resolve a route key to its human-readable model tag."""
    return MODEL_TAGS.get(route_key, f"unknown ({route_key})")


def _log_model_usage(model_tag: str, persona_id: str, query: str,
                     tokens_est: int = 0) -> None:
    """Append a line to ~/Thunderbird/logs/model_usage.log for every routed call."""
    try:
        _MODEL_USAGE_LOG.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        preview = query[:60].replace("\n", " ").strip()
        line = f"[{ts}] {model_tag} | persona={persona_id} | tokens_est=~{tokens_est} | query_preview=\"{preview}\"\n"
        with open(_MODEL_USAGE_LOG, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception as e:
        logger.warning("Model usage log failed: %s", e)


def should_escalate(persona_id: str, task_type: Optional[TaskType] = None) -> bool:
    """Decide if a task should escalate (legacy — all calls now go to Claude Opus)."""
    if task_type is None:
        return False  # No explicit task type = stay on default
    return task_type in ESCALATION_MAP.get(persona_id, set())


def _call_groq(system_prompt: str, query: str, model: str = "fast",
               max_tokens: int = 600, temperature: float = 0.7) -> str:
    """Route to Claude Sonnet via CLI subprocess (Max plan, $0).

    Function name retained for backward compatibility — Groq is ELIMINATED.
    All calls now go through Claude Sonnet via the CLI.
    """
    combined_prompt = f"{system_prompt}\n\n{query}"

    # Strip ANTHROPIC_API_KEY so CLI uses Max plan OAuth ($0)
    clean_env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}

    cmd = [
        os.path.expanduser("~/.local/bin/claude"),
        "--print",
        "--model", "sonnet",
        "--dangerously-skip-permissions",
        "--output-format", "text",
        "-p", combined_prompt,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            env=clean_env,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        else:
            stderr = result.stderr.strip()[:200] if result.stderr else "No stderr"
            raise RuntimeError(f"Claude CLI exit {result.returncode}: {stderr}")
    except subprocess.TimeoutExpired:
        raise RuntimeError("Claude CLI timed out after 120s")


def _call_claude(system_prompt: str, query: str,
                 max_tokens: int = None, temperature: float = 0.7) -> str:
    """Call Anthropic Claude API.

    Claude now supports 1M context window at GA pricing (no beta header needed).
    Default max_tokens raised to CLAUDE_DEFAULT_MAX_OUTPUT (16,384).
    """
    if max_tokens is None:
        max_tokens = CLAUDE_DEFAULT_MAX_OUTPUT
    resp = requests.post(
        ANTHROPIC_URL,
        json={
            "model": CLAUDE_MODEL,
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": [{"role": "user", "content": query}],
            "temperature": temperature,
        },
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["content"][0]["text"]


def _call_gemini(system_prompt: str, query: str,
                 max_tokens: int = 600, temperature: float = 0.7) -> str:
    """Call Google Gemini 2.5 Flash API.

    Cost: $0.30/$2.50 per 1M tokens — cheap, native Google Workspace affinity.
    Falls back to Claude Opus if GOOGLE_AI_API_KEY is not set.
    """
    if not GOOGLE_AI_API_KEY:
        logger.warning("GOOGLE_AI_API_KEY not set — falling back to Claude Opus")
        return _call_groq(system_prompt, query, model="fast",
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
    Falls back to Claude Opus if XAI_API_KEY is not set.
    """
    if not XAI_API_KEY:
        logger.warning("XAI_API_KEY not set — falling back to Claude Opus")
        return _call_groq(system_prompt, query, model="fast",
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
    Falls back to Claude Opus if DEEPSEEK_API_KEY is not set.
    """
    if not DEEPSEEK_API_KEY:
        logger.warning("DEEPSEEK_API_KEY not set — falling back to Claude Opus")
        return _call_groq(system_prompt, query, model="fast",
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
    If PII is detected, automatically reroutes to Claude Opus — NEVER sends PII to DeepSeek.
    """
    combined_text = f"{system_prompt}\n{query}"

    if _check_pii_fence(combined_text):
        # PII detected — hard reroute to Claude Opus
        response = _call_groq(system_prompt, query, model="fast",
                              max_tokens=max_tokens, temperature=temperature)
        return {
            "engine": "claude",
            "model": GROQ_MODELS["fast"],
            "response": response,
            "success": True,
            "pii_blocked": True,
            "note": "PII detected — rerouted from DeepSeek to Claude Opus",
        }

    try:
        response = _call_deepseek(system_prompt, query,
                                  max_tokens=max_tokens, temperature=temperature)
        model_used = DEEPSEEK_MODEL if DEEPSEEK_API_KEY else GROQ_MODELS["fast"]
        engine = "deepseek" if DEEPSEEK_API_KEY else "claude"
        return {
            "engine": engine,
            "model": model_used,
            "response": response,
            "success": True,
            "pii_blocked": False,
        }
    except Exception as e:
        logger.warning("DeepSeek failed, falling back to Claude Opus: %s", e)
        response = _call_groq(system_prompt, query, model="fast",
                              max_tokens=max_tokens, temperature=temperature)
        return {
            "engine": "claude",
            "model": GROQ_MODELS["fast"],
            "response": response,
            "success": True,
            "pii_blocked": False,
            "note": f"DeepSeek failed ({e}), fell back to Claude Opus",
        }


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
            from datetime import datetime
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


def route_call(persona_id: str, query: str,
               task_type: Optional[TaskType] = None,
               max_tokens: int = 600,
               temperature: float = 0.7) -> Dict[str, Any]:
    """Route a persona call to the optimal model.

    Returns dict with: persona, model_used, engine (claude/gemini/grok/deepseek), response, tokens
    """
    from thunderbird_personas import resolve_id, get_persona, build_system_prompt

    pid = resolve_id(persona_id)
    persona = get_persona(pid)
    system_prompt = build_system_prompt(pid)
    escalate = should_escalate(pid, task_type)

    # All general calls route to Claude Opus via CLI ($0 on Max plan)
    engine = "claude"
    route_key = "fast"  # default, overridden below
    logger.info(f"Routing {pid} [{task_type.value if task_type else 'default'}] → Claude Opus")

    try:
        if escalate:
            # Escalate — still Claude Opus (all tiers unified)
            response = _call_groq(system_prompt, query, model="premium",
                                  max_tokens=max(max_tokens, 1024),
                                  temperature=temperature)
            model_used = GROQ_MODELS["premium"]
            engine = "claude"
            route_key = "premium"
        else:
            groq_model = persona.get("model", "fast")
            route_key = groq_model
            # Route to Gemini for workspace/gemini-tagged models
            if groq_model in ("gemini", "workspace"):
                response = _call_gemini(system_prompt, query, max_tokens=max_tokens,
                                        temperature=temperature)
                model_used = GEMINI_MODEL if GOOGLE_AI_API_KEY else GROQ_MODELS["fast"]
                engine = "gemini" if GOOGLE_AI_API_KEY else "claude"
            # Route to Grok for research/grok-tagged models
            elif groq_model in ("research", "grok"):
                response = _call_grok(system_prompt, query, max_tokens=max_tokens,
                                      temperature=temperature)
                model_used = GROK_MODEL if XAI_API_KEY else GROQ_MODELS["fast"]
                engine = "grok" if XAI_API_KEY else "claude"
            # Route to DeepSeek for extraction/deepseek-tagged models (PII-fenced)
            elif groq_model in ("extraction", "deepseek") or task_type == TaskType.EXTRACTION:
                result = call_deepseek(system_prompt, query, max_tokens=max_tokens,
                                       temperature=temperature)
                response = result["response"]
                model_used = result["model"]
                engine = result["engine"]
            # Route to Claude — either via API (if key set) or CLI (default)
            elif groq_model == "claude":
                if ANTHROPIC_API_KEY:
                    response = _call_claude(system_prompt, query,
                                            max_tokens=max(max_tokens, CLAUDE_DEFAULT_MAX_OUTPUT),
                                            temperature=temperature)
                    model_used = CLAUDE_MODEL
                    engine = "claude"
                    route_key = "claude"
                else:
                    # Use CLI subprocess (Max plan, $0)
                    response = _call_groq(system_prompt, query, model="fast",
                                          max_tokens=max_tokens, temperature=temperature)
                    model_used = GROQ_MODELS["fast"]
                    engine = "claude"
                    route_key = "claude"
            else:
                response = _call_groq(system_prompt, query, model=groq_model,
                                      max_tokens=max_tokens, temperature=temperature)
                model_used = GROQ_MODELS.get(groq_model, GROQ_MODELS["fast"])

        # Resolve model tag
        model_tag = _resolve_model_tag(route_key)

        # Log model usage
        est_tokens = (len(system_prompt + query) + len(response)) // 4
        _log_model_usage(model_tag, pid, query, tokens_est=est_tokens)

        # Log the API call cost
        try:
            from thunderbird_api_costs import log_api_call
            est_input = len(system_prompt + query) // 4
            est_output = len(response) // 4
            log_api_call(engine, model_used, input_tokens=est_input,
                         output_tokens=est_output, caller=pid,
                         task=task_type.value if task_type else "default",
                         write_sheet=False)  # Local only for speed
        except Exception:
            pass  # Never let cost logging break the call

        return {
            "persona": pid,
            "name": persona["name"],
            "engine": engine,
            "model": model_used,
            "model_tag": model_tag,
            "task_type": task_type.value if task_type else "default",
            "response": response,
            "success": True,
        }
    except Exception as e:
        # Fallback: if primary call fails, retry once; if that fails, report error
        if escalate:
            logger.warning(f"Claude Opus escalation failed for {pid}, retrying: {e}")
            try:
                response = _call_groq(system_prompt, query, max_tokens=max_tokens,
                                      temperature=temperature)
                fallback_tag = _resolve_model_tag("fast")
                _log_model_usage(fallback_tag, pid, query,
                                 tokens_est=(len(system_prompt + query) + len(response)) // 4)
                return {
                    "persona": pid,
                    "name": persona["name"],
                    "engine": "claude",
                    "model": GROQ_MODELS["fast"],
                    "model_tag": fallback_tag,
                    "task_type": task_type.value if task_type else "default",
                    "response": response,
                    "success": True,
                    "note": "Fell back — Claude Opus retry",
                }
            except Exception as e2:
                logger.error(f"Claude Opus failed twice for {pid}: {e2}")

        error_tag = _resolve_model_tag(route_key)
        _log_model_usage(f"ERROR ({error_tag})", pid, query, tokens_est=0)
        return {
            "persona": pid,
            "name": persona["name"],
            "engine": engine,
            "model": "none",
            "model_tag": error_tag,
            "task_type": task_type.value if task_type else "default",
            "response": f"ERROR: {e}",
            "success": False,
        }


def classify_task(query: str) -> TaskType:
    """Auto-classify a query into a TaskType using keyword heuristics.

    Fast, no API call needed. Use this when task_type isn't explicitly set.
    """
    q = query.lower()

    creative_signals = ["write", "draft", "proposal", "narrative", "story", "copy",
                        "describe", "paint a picture", "itinerary narrative", "poetic"]
    strategic_signals = ["pricing", "strategy", "growth", "compete", "position",
                         "should we", "business case", "roi", "market"]
    crisis_signals = ["urgent", "emergency", "cancelled", "missed", "stranded",
                      "delay", "problem", "crisis", "broken"]
    classification_signals = ["classify", "categorize", "triage", "sort", "label",
                              "which category"]
    extraction_signals = ["extract", "parse", "ocr", "pull data from", "scrape",
                          "structured data", "json from", "fields from"]

    for s in crisis_signals:
        if s in q:
            return TaskType.CRISIS
    for s in creative_signals:
        if s in q:
            return TaskType.CREATIVE
    for s in strategic_signals:
        if s in q:
            return TaskType.STRATEGIC
    for s in classification_signals:
        if s in q:
            return TaskType.CLASSIFICATION
    for s in extraction_signals:
        if s in q:
            return TaskType.EXTRACTION

    return TaskType.OPERATIONAL


def smart_route(persona_id: str, query: str, **kwargs) -> Dict[str, Any]:
    """Auto-classify and route. Convenience wrapper."""
    task_type = classify_task(query)
    return route_call(persona_id, query, task_type=task_type, **kwargs)


if __name__ == "__main__":
    # Quick test
    print("=== Thunderbird Model Router Test ===\n")

    tests = [
        ("A3", "What's the status of the Kuklinski Viking bookings?"),
        ("EXEC", "Write a proposal opening for a Mediterranean luxury cruise"),
        ("A5", "Should we increase our markup on Regent bookings?"),
        ("A9", "What's our total commission exposure this quarter?"),
    ]

    for pid, q in tests:
        task_type = classify_task(q)
        will_escalate = should_escalate(pid, task_type)
        print(f"{pid}: [{task_type.value}] → {'OPUS (escalated)' if will_escalate else 'OPUS'}")
        print(f"  Query: {q[:60]}...")
        print()
