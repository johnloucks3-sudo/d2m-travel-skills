#!/usr/bin/env python3
"""
Thunderbird Gemini Client — Canonical Direct-API Wrapper
=========================================================
A7 Sterling — 2026-06-01

SINGLE CHOKEPOINT for all Google Gemini API calls in the Thunderbird stack.
ALL other modules that call Gemini MUST delegate here instead of calling
generativelanguage.googleapis.com directly.

FREE-TIER ALLOWLIST GUARD
--------------------------
Only models in GEMINI_FREE_TIER_ALLOWLIST may be called without explicit approval.
Any model NOT in this set requires GEMINI_PAID_TIER_APPROVED=true in env.
This is a code-enforced control. Logging is mandatory on every call (Harlan tracking).

NOTE: The free-vs-paid boundary is a GCP billing property, not a model property.
The three models below are available on the free tier of the D2M Python Pipeline project.
If billing is later enabled on that project, free-tier rate limits (not billing caps)
are the operational guardrail — Sterling cannot guarantee $0 from code alone.

Usage:
    from core.ai_infra.gemini_client import call_gemini, call_gemini_lite, call_gemini_pro

    # Sonnet-equivalent fallback
    text = call_gemini("You are Dani.", "Draft a welcome email.")

    # Haiku-equivalent (fast, cheap)
    text = call_gemini_lite("You are A7.", "Classify this task.")

    # Opus-equivalent (high quality — requires explicit use case)
    text = call_gemini_pro("You are TALON.", "Critique this draft.")

Model routing:
    gemini-2.5-flash      → Sonnet equivalent  (default fallback)
    gemini-2.5-flash-lite → Haiku equivalent   (fast/light tasks)
    gemini-2.5-pro        → Opus equivalent    (high-quality, use sparingly)
"""

import os
import time
import json
import logging
import requests
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("thunderbird.gemini_client")

# ---------------------------------------------------------------------------
# FREE-TIER ALLOWLIST — Commander-authorized models (2026-06-01)
# Any model outside this set requires GEMINI_PAID_TIER_APPROVED=true
# ---------------------------------------------------------------------------
GEMINI_FREE_TIER_ALLOWLIST: set[str] = {
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-2.5-flash-lite",
}

# Model → tier label for logging / Harlan tracking
_TIER_LABELS: dict[str, str] = {
    "gemini-2.5-flash":      "Sonnet-equivalent",
    "gemini-2.5-flash-lite": "Haiku-equivalent",
    "gemini-2.5-pro":        "Opus-equivalent",
}

# API configuration
_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
_DEFAULT_TIMEOUT = 60

# Rate limiting — shared across all calls to stay inside free-tier 15 RPM limit
_LAST_CALL_TS: float = 0.0
_MIN_CALL_GAP: float = float(os.environ.get("GEMINI_INTER_CALL_DELAY", "0"))

# Usage log path (Harlan visibility)
_USAGE_LOG = Path(__file__).parent / "data" / "gemini_usage.jsonl"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_api_key() -> str:
    """Return GOOGLE_AI_API_KEY from env. Raises if absent."""
    key = os.environ.get("GOOGLE_AI_API_KEY", "")
    if not key:
        raise RuntimeError(
            "GOOGLE_AI_API_KEY not set — Gemini calls are unavailable. "
            "Check /home/john/Thunderbird/.env."
        )
    return key


def _enforce_allowlist(model: str) -> None:
    """
    Block any model not in GEMINI_FREE_TIER_ALLOWLIST unless the paid-tier
    approval flag is explicitly set.

    Raises RuntimeError for unapproved models.
    """
    if model not in GEMINI_FREE_TIER_ALLOWLIST:
        approved = os.environ.get("GEMINI_PAID_TIER_APPROVED", "").lower()
        if approved != "true":
            raise RuntimeError(
                f"Model '{model}' is not in the Gemini free-tier allowlist "
                f"({sorted(GEMINI_FREE_TIER_ALLOWLIST)}). "
                f"Set GEMINI_PAID_TIER_APPROVED=true in env to enable paid/experimental models. "
                f"Requires explicit Commander approval — A7 Sterling, 2026-06-01."
            )
        logger.warning(
            "GEMINI_PAID_TIER_APPROVED=true — calling non-allowlist model '%s'. "
            "Harlan notified via usage log.",
            model,
        )


def _rate_limit() -> None:
    """Enforce minimum gap between calls (respects GEMINI_INTER_CALL_DELAY env var)."""
    global _LAST_CALL_TS
    if _MIN_CALL_GAP > 0:
        elapsed = time.time() - _LAST_CALL_TS
        if elapsed < _MIN_CALL_GAP:
            wait = _MIN_CALL_GAP - elapsed
            logger.debug("Gemini rate limiter: sleeping %.1fs", wait)
            time.sleep(wait)


def _log_usage(
    model: str,
    caller: str,
    task_hint: str,
    input_tokens_est: int,
    output_tokens_est: int,
    success: bool,
    error: Optional[str] = None,
) -> None:
    """
    Write one JSONL record to gemini_usage.jsonl for Harlan tracking.
    Never raises — logging failure must not kill the call chain.
    """
    try:
        _USAGE_LOG.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "model": model,
            "tier": _TIER_LABELS.get(model, "unknown"),
            "caller": caller,
            "task_hint": task_hint[:120],
            "input_tokens_est": input_tokens_est,
            "output_tokens_est": output_tokens_est,
            "in_allowlist": model in GEMINI_FREE_TIER_ALLOWLIST,
            "paid_tier_flag": os.environ.get("GEMINI_PAID_TIER_APPROVED", "false"),
            "success": success,
            "error": error,
        }
        with open(_USAGE_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception as log_err:
        logger.warning("gemini_client: usage log write failed: %s", log_err)


def _call(
    model: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 1024,
    temperature: float = 0.7,
    caller: str = "unknown",
    task_hint: str = "",
) -> str:
    """
    Core HTTP call to Google Gemini REST API.
    Enforces allowlist, rate limiting, and Harlan logging on every call.

    Args:
        model:         One of GEMINI_FREE_TIER_ALLOWLIST (or approved paid)
        system_prompt: System instruction text
        user_prompt:   User content
        max_tokens:    Maximum output tokens
        temperature:   Sampling temperature (0.0–1.0)
        caller:        Persona or module ID for logging
        task_hint:     Short description for usage log

    Returns:
        Generated text string.

    Raises:
        RuntimeError if model is blocked, key absent, or API fails after retry.
    """
    global _LAST_CALL_TS

    # 1. Guard: allowlist check
    _enforce_allowlist(model)

    # 2. Guard: key presence
    api_key = _get_api_key()

    # 3. Rate limiter
    _rate_limit()

    url = _BASE_URL.format(model=model) + f"?key={api_key}"
    payload = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": temperature,
        },
    }
    headers = {"Content-Type": "application/json"}

    input_est = (len(system_prompt) + len(user_prompt)) // 4
    text = ""
    error_msg = None

    try:
        _LAST_CALL_TS = time.time()
        logger.info(
            "gemini_client: calling %s [caller=%s, max_tokens=%d]",
            model, caller, max_tokens
        )
        resp = requests.post(url, json=payload, headers=headers, timeout=_DEFAULT_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        candidate = data.get("candidates", [{}])[0]
        finish_reason = candidate.get("finishReason", "UNKNOWN")
        parts = candidate.get("content", {}).get("parts", [])
        text = parts[0].get("text", "") if parts else ""

        # Retry once with doubled token budget on empty response
        if not text and max_tokens < 4096:
            logger.warning(
                "gemini_client: empty response from %s (finishReason=%s), retrying 2x tokens",
                model, finish_reason
            )
            payload["generationConfig"]["maxOutputTokens"] = min(max_tokens * 2, 8192)
            _LAST_CALL_TS = time.time()
            resp2 = requests.post(
                url, json=payload, headers=headers, timeout=_DEFAULT_TIMEOUT
            )
            resp2.raise_for_status()
            data2 = resp2.json()
            parts2 = data2.get("candidates", [{}])[0].get("content", {}).get("parts", [])
            text = parts2[0].get("text", "") if parts2 else ""

        if not text:
            raise RuntimeError(
                f"Gemini {model} returned empty text after retry (finishReason={finish_reason})"
            )

        output_est = len(text) // 4
        _log_usage(
            model=model, caller=caller, task_hint=task_hint or user_prompt[:80],
            input_tokens_est=input_est, output_tokens_est=output_est,
            success=True,
        )
        logger.info(
            "gemini_client: %s success [~%d in / ~%d out tokens]",
            model, input_est, output_est
        )
        return text

    except (requests.exceptions.RequestException, RuntimeError) as exc:
        error_msg = str(exc)
        _log_usage(
            model=model, caller=caller, task_hint=task_hint or user_prompt[:80],
            input_tokens_est=input_est, output_tokens_est=0,
            success=False, error=error_msg,
        )
        logger.error("gemini_client: %s failed: %s", model, error_msg)
        raise RuntimeError(f"Gemini {model} error: {exc}") from exc


# ---------------------------------------------------------------------------
# Public API — three convenience functions matching the three tiers
# ---------------------------------------------------------------------------

def call_gemini(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 1024,
    temperature: float = 0.7,
    caller: str = "unknown",
    task_hint: str = "",
) -> str:
    """
    Gemini 2.5 Flash — Sonnet-equivalent fallback.
    Default model. Use when Claude Sonnet limit is approached.
    Free tier: 15 RPM / 1M TPM / 1500 RPD.
    """
    return _call(
        model="gemini-2.5-flash",
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        max_tokens=max_tokens,
        temperature=temperature,
        caller=caller,
        task_hint=task_hint,
    )


def call_gemini_lite(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 1024,
    temperature: float = 0.7,
    caller: str = "unknown",
    task_hint: str = "",
) -> str:
    """
    Gemini 2.5 Flash-Lite — Haiku-equivalent fallback.
    Fast/light tasks: classification, extraction, status checks.
    Free tier: higher RPM than Flash, lower quality ceiling.
    Falls back to gemini-2.5-flash on failure.
    """
    try:
        return _call(
            model="gemini-2.5-flash-lite",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            caller=caller,
            task_hint=task_hint,
        )
    except RuntimeError as exc:
        logger.warning(
            "gemini_client: flash-lite failed (%s), falling back to flash", exc
        )
        return call_gemini(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            caller=caller,
            task_hint=f"[lite-fallback] {task_hint}",
        )


def call_gemini_pro(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 2048,
    temperature: float = 0.7,
    caller: str = "unknown",
    task_hint: str = "",
) -> str:
    """
    Gemini 2.5 Pro — Opus-equivalent fallback.
    High-quality reasoning. Use sparingly — free-tier RPM is lower.
    Free tier: 5 RPM / 250K TPD.
    Falls back to gemini-2.5-flash on failure.
    """
    try:
        return _call(
            model="gemini-2.5-pro",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            caller=caller,
            task_hint=task_hint,
        )
    except RuntimeError as exc:
        logger.warning(
            "gemini_client: pro failed (%s), falling back to flash", exc
        )
        return call_gemini(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            caller=caller,
            task_hint=f"[pro-fallback] {task_hint}",
        )


def smoke_test() -> dict:
    """
    One-shot smoke test. Calls gemini-2.5-flash-lite with a minimal prompt.
    Returns dict: {success, model, response_preview, error}.
    Use this to verify the key works after configuration changes.
    """
    try:
        result = call_gemini_lite(
            system_prompt="You are a test echo service.",
            user_prompt="Reply with exactly: THUNDERBIRD_OK",
            max_tokens=20,
            temperature=0.0,
            caller="A7_smoke_test",
            task_hint="key validation smoke test",
        )
        return {
            "success": True,
            "model": "gemini-2.5-flash-lite",
            "response_preview": result[:100],
            "error": None,
        }
    except Exception as exc:
        return {
            "success": False,
            "model": "gemini-2.5-flash-lite",
            "response_preview": None,
            "error": str(exc),
        }


if __name__ == "__main__":
    # CLI smoke test — run directly to validate key
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    # Load .env if dotenv is available
    try:
        from dotenv import load_dotenv
        load_dotenv("/home/john/Thunderbird/.env")
    except ImportError:
        pass

    result = smoke_test()
    if result["success"]:
        print(f"[PASS] Gemini direct API verified. Response: {result['response_preview']}")
        sys.exit(0)
    else:
        print(f"[FAIL] Gemini smoke test failed: {result['error']}")
        sys.exit(1)
