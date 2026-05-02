#!/usr/bin/env python3
"""
invoke_model.py — Call any OpenRouter model by alias from Claude Code.

Usage:
    python3 scripts/invoke_model.py GROK "What's the best cruise for families?"
    python3 scripts/invoke_model.py DEEPSEEK "Analyze this booking status"
    python3 scripts/invoke_model.py --list                # Show available models
    python3 scripts/invoke_model.py --id google/gemini-3.1-flash-lite-preview "prompt"

Model aliases:
    GROK      → xAI Grok 4.1 Fast          (2M context, ~$0.20/M)
    DEEPSEEK  → DeepSeek V4 Pro            (1M context, ~$0.305/M)
    GEMINI    → Gemini 3.1 Flash Lite      (1M context, ~$0.25/M)
    LLAMA     → Llama 4 Maverick           (1M context, ~$0.15/M)
    GPT       → GPT-4.1 Mini              (1M context, ~$0.40/M)
    HAIKU     → Claude Haiku 4.5           (200K context)
    MISTRAL   → Mistral Small 3.2          (128K context)
    SONNET    → Claude Sonnet 4.6          (200K context)
    OPUS      → Claude Opus 4.6            (200K context)

All responses are prefixed with the model name for attribution.
"""

import json
import os
import sys
import time
from pathlib import Path

# Load .env
_ENV_FILE = Path("/home/john/Thunderbird/.env")
if _ENV_FILE.exists():
    for line in _ENV_FILE.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

MODEL_ALIASES = {
    "GROK":     ("x-ai/grok-4.1-fast",                       "Grok 4.1 Fast",     "~$0.20/M, 2M ctx"),
    "DEEPSEEK": ("deepseek/deepseek-v4-pro",                 "DeepSeek V4 Pro",   "~$0.305/M, 1M ctx"),
    "GEMINI":   ("google/gemini-3.1-flash-lite-preview",     "Gemini 3.1 Flash",  "~$0.25/M, 1M ctx"),
    "LLAMA":    ("meta-llama/llama-4-maverick",              "Llama 4 Maverick",  "~$0.15/M, 1M ctx"),
    "GPT":      ("openai/gpt-4.1-mini",                     "GPT-4.1 Mini",      "~$0.40/M, 1M ctx"),
    "HAIKU":    ("anthropic/claude-haiku-4.5",               "Claude Haiku 4.5",  "200K ctx"),
    "MISTRAL":  ("mistralai/mistral-small-3.2-24b-instruct", "Mistral Small 3.2", "128K ctx"),
    "SONNET":   ("anthropic/claude-sonnet-4-6",              "Claude Sonnet 4.6", "200K ctx"),
    "OPUS":     ("anthropic/claude-opus-4-6",                "Claude Opus 4.6",   "200K ctx"),
}


def list_models():
    print("Available models:")
    print(f"  {'Alias':<10} {'Display Name':<22} {'Cost/Context':<20} Model ID")
    print(f"  {'─'*10} {'─'*22} {'─'*20} {'─'*40}")
    for alias, (model_id, display, cost) in sorted(MODEL_ALIASES.items()):
        print(f"  {alias:<10} {display:<22} {cost:<20} {model_id}")


def call_openrouter(model_id: str, prompt: str, system_prompt: str = "") -> dict:
    """Call OpenRouter API. Returns {model, content, tokens, elapsed}."""
    import requests

    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        return {"error": "OPENROUTER_API_KEY not set in environment or .env"}

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    start = time.time()
    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "X-Title": "Thunderbird Claude Code",
            },
            json={
                "model": model_id,
                "max_tokens": 4096,
                "messages": messages,
            },
            timeout=180,
        )
        elapsed = time.time() - start

        if resp.status_code == 429:
            return {"error": f"Rate limited on {model_id} — try again shortly"}
        if resp.status_code >= 500:
            return {"error": f"OpenRouter server error {resp.status_code}"}

        resp.raise_for_status()
        data = resp.json()

        # OpenAI chat completions format
        choices = data.get("choices", [])
        if choices:
            content = choices[0].get("message", {}).get("content", "")
            usage = data.get("usage", {})
            return {
                "content": content.strip(),
                "model": model_id,
                "tokens": usage.get("total_tokens", 0),
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "elapsed": round(elapsed, 1),
            }

        # Anthropic messages format fallback
        content_blocks = data.get("content", [])
        parts = [b["text"] for b in content_blocks if isinstance(b, dict) and b.get("type") == "text"]
        if parts:
            return {
                "content": "\n".join(parts).strip(),
                "model": model_id,
                "tokens": 0,
                "elapsed": round(elapsed, 1),
            }

        return {"error": f"Empty response from {model_id}", "raw": str(data)[:500]}

    except Exception as e:
        return {"error": str(e)}


def main():
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0

    if args[0] == "--list":
        list_models()
        return 0

    # --id mode: raw OpenRouter model ID
    if args[0] == "--id":
        if len(args) < 3:
            print("Usage: invoke_model.py --id <model_id> \"<prompt>\"")
            return 1
        model_id = args[1]
        display_name = model_id.split("/")[-1] if "/" in model_id else model_id
        prompt = " ".join(args[2:])
    else:
        # Alias mode
        alias = args[0].upper()
        if alias not in MODEL_ALIASES:
            print(f"Unknown model alias: {args[0]}")
            print(f"Available: {', '.join(sorted(MODEL_ALIASES.keys()))}")
            print("Use --list for details or --id <model_id> for raw IDs.")
            return 1
        model_id, display_name, _ = MODEL_ALIASES[alias]
        prompt = " ".join(args[1:])

    if not prompt:
        print("No prompt provided.")
        return 1

    # Optional: system prompt from stdin or file
    system = ""

    result = call_openrouter(model_id, prompt, system)

    if "error" in result:
        print(f"ERROR: {result['error']}")
        return 1

    # Always show model attribution
    tokens_info = ""
    if result.get("tokens"):
        tokens_info = f" | {result['tokens']} tokens"
    print(f"[{display_name} | {result['elapsed']}s{tokens_info}]")
    print()
    print(result["content"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
