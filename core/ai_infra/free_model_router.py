#!/usr/bin/env python3
"""
free_model_router.py — Thunderbird unified free-inference router.

Providers (all $0):
  cerebras  — cloud.cerebras.ai       20x speed burst, gpt-oss-120b (reasoning)
  github    — models.inference.ai.azure.com  DeepSeek R1 + Mistral Small (GITHUB_TOKEN)
  groq      — api.groq.com            Llama 3.3-70B / Llama 4 Scout, fast free tier
  ollama    — localhost:11434          Local Llama 3.2 / qwen2.5-coder, private/PII tasks
  deepinfra — deepinfra.com            CASE-1: requires paid balance (MISSION-394 blocked)

Routing heuristic (override with provider= param):
  speed     → cerebras/zai-glm-4.7   (burst tasks, sub-1s)
  reasoning → github/DeepSeek-R1      (chain-of-thought, arbitration)
  mistral   → github/mistral-small-2503 (efficient structured extraction)
  local/pii → ollama                  (no data leaves YOGA)
  default   → groq                    (reliable, Llama 3.3-70B)

Usage:
    from core.ai_infra.free_model_router import free_infer
    result = free_infer("Summarize this doc...", provider="cerebras")
    result = free_infer("Reason step-by-step...", provider="deepinfra", model="deepseek-ai/DeepSeek-R1")
    result = free_infer("PII task...", provider="ollama")
"""
from __future__ import annotations

import os
import json
import logging
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

_ENV = Path(__file__).parent.parent.parent / ".env"

def _load_env_key(key: str) -> str:
    val = os.environ.get(key, "")
    if val:
        return val
    try:
        for line in _ENV.read_text().splitlines():
            if line.startswith(f"{key}=") and not line.startswith("#"):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return ""

# ── Provider defaults ───────────────────────────────────────────────────────

PROVIDERS = {
    "cerebras": {
        "base_url": "https://api.cerebras.ai/v1",
        "key_env":  "CEREBRAS_API_KEY",
        "default_model": "gpt-oss-120b",  # 120B OSS model; also: zai-glm-4.7
    },
    "github": {
        "base_url": "https://models.inference.ai.azure.com",
        "key_env":  "GITHUB_TOKEN",
        "default_model": "DeepSeek-R1",   # DeepSeek R1 full + Mistral Small via GITHUB_TOKEN
    },
    "deepinfra": {
        "base_url": "https://api.deepinfra.com/v1/openai",
        "key_env":  "DEEPINFRA_API_KEY",
        "default_model": "meta-llama/Llama-4-Scout-17B-16E-Instruct",
        "_note": "CASE-1: requires paid balance — HTTP 402 (MISSION-394 blocked)",
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "key_env":  "GROQ_API_KEY",
        "default_model": "llama-3.3-70b-versatile",
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "key_env":  None,
        "default_model": "llama3.2:3b",
    },
}

GITHUB_MODELS = {
    "deepseek-r1":   "DeepSeek-R1",
    "r1":            "DeepSeek-R1",
    "deepseek-r1-0528": "DeepSeek-R1-0528",
    "mistral-small": "mistral-small-2503",
    "mistral":       "mistral-small-2503",
}

DEEPINFRA_MODELS = {
    "llama4":    "meta-llama/Llama-4-Scout-17B-16E-Instruct",
    "llama4big": "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8",
    "deepseek":  "deepseek-ai/DeepSeek-R1-0528",
    "r1":        "deepseek-ai/DeepSeek-R1-0528",
    "mistral":   "mistralai/Mistral-Small-3.2-24B-Instruct-2506",
}

CEREBRAS_MODELS = {
    "fast":      "zai-glm-4.7",    # ZAI GLM-4.7 (Big Pickle lineage)
    "smart":     "gpt-oss-120b",   # 120B OSS model
    "glm":       "zai-glm-4.7",
}


def _openai_call(base_url: str, api_key: str, model: str, messages: list, max_tokens: int = 1024) -> str:
    payload = json.dumps({"model": model, "messages": messages, "max_tokens": max_tokens}).encode()
    headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 Thunderbird-FreeRouter/1.0"}
    if api_key and api_key != "ollama":
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(f"{base_url}/chat/completions", data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read())
            return data["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise RuntimeError(f"HTTP {e.code}: {body[:300]}")


def _cerebras_call(model: str, messages: list, max_tokens: int = 1024) -> str:
    from cerebras.cloud.sdk import Cerebras
    api_key = _load_env_key("CEREBRAS_API_KEY")
    c = Cerebras(api_key=api_key)
    # Cerebras reasoning models need headroom — floor at 512 so content isn't None
    effective_tokens = max(max_tokens, 512)
    resp = c.chat.completions.create(model=model, messages=messages, max_tokens=effective_tokens)
    msg = resp.choices[0].message
    return msg.content or getattr(msg, "reasoning", "") or ""


def free_infer(
    prompt: str,
    provider: str = "groq",
    model: Optional[str] = None,
    system: str = "You are a concise, accurate assistant for Dreams2Memories Travel.",
    max_tokens: int = 1024,
) -> str:
    """Call a free inference provider. Returns the text response."""
    if provider not in PROVIDERS:
        raise ValueError(f"Unknown provider '{provider}'. Choose: {list(PROVIDERS)}")

    cfg = PROVIDERS[provider]
    api_key = _load_env_key(cfg["key_env"]) if cfg["key_env"] else "ollama"
    resolved_model = model or cfg["default_model"]

    # Convenience aliases
    if provider == "github" and resolved_model.lower() in GITHUB_MODELS:
        resolved_model = GITHUB_MODELS[resolved_model.lower()]
    if provider == "deepinfra" and resolved_model in DEEPINFRA_MODELS:
        resolved_model = DEEPINFRA_MODELS[resolved_model]
    if provider == "cerebras" and resolved_model in CEREBRAS_MODELS:
        resolved_model = CEREBRAS_MODELS[resolved_model]

    messages = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
    log.info("free_infer → %s / %s", provider, resolved_model)
    if provider == "cerebras":
        return _cerebras_call(resolved_model, messages, max_tokens)
    return _openai_call(cfg["base_url"], api_key, resolved_model, messages, max_tokens)


def route(prompt: str, hint: str = "default", **kwargs) -> str:
    """Route by hint: speed | reasoning | mistral | local | default."""
    mapping = {
        "speed":     ("cerebras", "zai-glm-4.7"),
        "reasoning": ("github",   "DeepSeek-R1"),        # MISSION-411: GitHub Models free tier
        "mistral":   ("github",   "mistral-small-2503"), # MISSION-412: GitHub Models free tier
        "local":     ("ollama",   None),
        "default":   ("groq",     None),
        "llama4":    ("groq",     "meta-llama/llama-4-scout-17b-16e-instruct"),
    }
    provider, model = mapping.get(hint, ("groq", None))
    return free_infer(prompt, provider=provider, model=model, **kwargs)


if __name__ == "__main__":
    import sys
    p = sys.argv[1] if len(sys.argv) > 1 else "Say hello from Thunderbird free router."
    hint = sys.argv[2] if len(sys.argv) > 2 else "default"
    print(f"[{hint}] →", route(p, hint=hint))
