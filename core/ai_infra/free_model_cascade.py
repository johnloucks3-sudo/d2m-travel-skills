"""
Free Model Cascade — MISSION-329
Groq → Cerebras → Haiku (caller-implemented)
For: classification, log scans, status checks, routing decisions, simple lookups

Usage:
    from core.ai_infra.free_model_cascade import cascade_complete

    result = cascade_complete(
        prompt="Classify this email: ...",
        task_type="classification",  # or "log_scan", "status_check", "routing"
        max_tokens=256
    )
    # result["tier"] == "free" → no MAX budget consumed
    # result["tier"] == "haiku_needed" → caller must dispatch via claude-haiku-4-5-20251001
"""

import json
import os
import urllib.request
from pathlib import Path

_REPO = Path(__file__).parent.parent.parent
_ENV_FILE = _REPO / ".env"


def _load_env() -> dict:
    env = {}
    if _ENV_FILE.exists():
        for line in _ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
    # Live env takes precedence
    for key in ("GROQ_API_KEY", "CEREBRAS_API_KEY"):
        if key in os.environ:
            env[key] = os.environ[key]
    return env


def _try_groq(prompt: str, max_tokens: int, env: dict) -> str | None:
    key = env.get("GROQ_API_KEY", "")
    if not key:
        return None
    try:
        payload = json.dumps({
            "model": "llama-4-scout-17b-16e-instruct",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.1,
        }).encode()
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=payload,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"]
    except Exception:
        return None


def _try_cerebras(prompt: str, max_tokens: int, env: dict) -> str | None:
    key = env.get("CEREBRAS_API_KEY", "")
    if not key:
        return None
    try:
        payload = json.dumps({
            "model": "llama3.1-8b",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.1,
        }).encode()
        req = urllib.request.Request(
            "https://api.cerebras.ai/v1/chat/completions",
            data=payload,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"]
    except Exception:
        return None


def cascade_complete(
    prompt: str,
    task_type: str = "classification",
    max_tokens: int = 256,
) -> dict:
    """Try free models first; escalate only if needed.

    Returns:
        {
            "result": str | None,
            "model_used": str,
            "tier": "free" | "haiku_needed",
            "note": str  (only when tier=="haiku_needed")
        }
    """
    env = _load_env()

    result = _try_groq(prompt, max_tokens, env)
    if result is not None:
        return {"result": result, "model_used": "groq/llama-4-scout-17b", "tier": "free"}

    result = _try_cerebras(prompt, max_tokens, env)
    if result is not None:
        return {"result": result, "model_used": "cerebras/llama3.1-8b", "tier": "free"}

    return {
        "result": None,
        "model_used": "haiku_needed",
        "tier": "haiku_needed",
        "note": "Free tier unavailable — caller must dispatch via claude-haiku-4-5-20251001",
    }
