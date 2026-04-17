#!/usr/bin/env python3
"""
openrouter_call.py — Unified CLI for OpenRouter API calls
Used by Claude Code agents, /escalate skill, and escalation hooks.

Usage:
    python3 scripts/openrouter_call.py --model grok --prompt "Analyze this..."
    python3 scripts/openrouter_call.py --model r1 --system "You are..." --prompt "..."
    echo "prompt" | python3 scripts/openrouter_call.py --model deepseek --stdin
    python3 scripts/openrouter_call.py --list
"""

import argparse
import json
import os
import sys
import requests
from pathlib import Path

# Load .env
_env_path = Path("/home/john/Thunderbird/.env")
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip("'\""))

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

MODELS = {
    # ── FREE TIER ($0) ────────────────────────────────────────────────────
    "nemotron": {
        "id": "nvidia/nemotron-3-super-120b-a12b:free",
        "label": "Nemotron 120B Super (FREE)",
        "context": 262_144,
        "cost": "FREE",
        "max_tokens": 8192,
        "tier": "free-reasoning",
    },
    "gpt-oss": {
        "id": "openai/gpt-oss-120b:free",
        "label": "GPT-OSS 120B (FREE)",
        "context": 131_072,
        "cost": "FREE",
        "max_tokens": 4096,
        "tier": "free-reasoning",
    },
    # NOTE: These free models exist but are rate-limited (429) as of 2026-04-17.
    # Kept commented for future retry. Working free: nemotron, gpt-oss, elephant.
    # Rate-limited: hermes 405B, qwen-free 80B, qwen-coder, llama-free 70B,
    #               gemma 27B, minimax m2.5, glm 4.5-air
    "elephant": {
        "id": "openrouter/elephant-alpha",
        "label": "Elephant Alpha (FREE)",
        "context": 262_144,
        "cost": "FREE",
        "max_tokens": 4096,
        "tier": "free-general",
    },
    # ── ULTRA-CHEAP (< $0.15/M input) ────────────────────────────────────
    "qwen-235b": {
        "id": "qwen/qwen3-235b-a22b-2507",
        "label": "Qwen3 235B",
        "context": 262_144,
        "cost": "$0.07/$0.10/M",
        "max_tokens": 8192,
        "tier": "ultra-cheap",
    },
    "gpt-nano": {
        "id": "openai/gpt-4.1-nano",
        "label": "GPT-4.1 Nano",
        "context": 1_047_576,
        "cost": "$0.10/$0.40/M",
        "max_tokens": 4096,
        "tier": "ultra-cheap",
    },
    "gemini-lite": {
        "id": "google/gemini-2.5-flash-lite",
        "label": "Gemini 2.5 Flash Lite",
        "context": 1_048_576,
        "cost": "$0.10/$0.40/M",
        "max_tokens": 8192,
        "tier": "ultra-cheap",
    },
    "llama": {
        "id": "meta-llama/llama-4-maverick",
        "label": "Llama 4 Maverick",
        "context": 1_048_576,
        "cost": "$0.15/$0.60/M",
        "max_tokens": 4096,
        "tier": "ultra-cheap",
    },
    "deepseek": {
        "id": "deepseek/deepseek-chat-v3.1",
        "label": "DeepSeek V3.1",
        "context": 32_768,
        "cost": "$0.15/$0.75/M",
        "max_tokens": 4096,
        "tier": "cheap",
    },
    "qwq": {
        "id": "qwen/qwq-32b",
        "label": "QwQ 32B (Reasoning)",
        "context": 131_072,
        "cost": "$0.15/$0.58/M",
        "max_tokens": 8192,
        "tier": "cheap-reasoning",
    },
    # ── VALUE TIER ($0.15–$0.50/M input) ──────────────────────────────────
    "grok": {
        "id": "x-ai/grok-4.1-fast",
        "label": "Grok 4.1 Fast",
        "context": 2_000_000,
        "cost": "$0.20/$0.50/M",
        "max_tokens": 8192,
        "tier": "value-reasoning",
    },
    "gemini": {
        "id": "google/gemini-3.1-flash-lite-preview",
        "label": "Gemini 3.1 Flash Lite",
        "context": 1_048_576,
        "cost": "$0.25/$1.50/M",
        "max_tokens": 8192,
        "tier": "value",
    },
    "deepseek-v3.2": {
        "id": "deepseek/deepseek-v3.2",
        "label": "DeepSeek V3.2",
        "context": 163_840,
        "cost": "$0.26/$0.38/M",
        "max_tokens": 4096,
        "tier": "value",
    },
    "gpt5-mini": {
        "id": "openai/gpt-5-mini",
        "label": "GPT-5 Mini",
        "context": 400_000,
        "cost": "$0.25/$2.00/M",
        "max_tokens": 4096,
        "tier": "value",
    },
    "gpt": {
        "id": "openai/gpt-4.1-mini",
        "label": "GPT-4.1 Mini",
        "context": 1_047_576,
        "cost": "$0.40/$1.60/M",
        "max_tokens": 4096,
        "tier": "value",
    },
    # ── REASONING TIER ────────────────────────────────────────────────────
    "r1": {
        "id": "deepseek/deepseek-r1-0528",
        "label": "DeepSeek R1 (Reasoning)",
        "context": 163_840,
        "cost": "$0.50/$2.15/M",
        "max_tokens": 8192,
        "tier": "reasoning",
    },
    "mistral": {
        "id": "mistralai/mistral-small-3.2-24b-instruct",
        "label": "Mistral Small 3.2",
        "context": 128_000,
        "cost": "$0.07/$0.20/M",
        "max_tokens": 4096,
        "tier": "cheap",
    },
    # ── PREMIUM (web search, Claude, etc.) ────────────────────────────────
    "perplexity": {
        "id": "perplexity/sonar-reasoning-pro",
        "label": "Perplexity Reasoning Pro",
        "context": 128_000,
        "cost": "$2/$8/M+search",
        "max_tokens": 4096,
        "tier": "web-research",
    },
    "haiku": {
        "id": "anthropic/claude-haiku-4.5",
        "label": "Haiku 4.5 (OpenRouter)",
        "context": 200_000,
        "cost": "$1/$5/M",
        "max_tokens": 4096,
        "tier": "premium",
    },
}


def call_openrouter(model_key, prompt, system=None, max_tokens=None, temperature=0.7):
    """Call an OpenRouter model and return structured result."""
    if not OPENROUTER_API_KEY:
        return {"success": False, "error": "OPENROUTER_API_KEY not set"}

    model = MODELS.get(model_key)
    if not model:
        return {"success": False, "error": f"Unknown model: {model_key}"}

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model["id"],
        "messages": messages,
        "max_tokens": max_tokens or model["max_tokens"],
        "temperature": temperature,
    }

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://d2mluxury.quest",
        "X-Title": "Thunderbird OS",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(BASE_URL, headers=headers, json=payload, timeout=180)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})

        return {
            "success": True,
            "model": model["label"],
            "model_id": model["id"],
            "model_key": model_key,
            "content": content,
            "usage": {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            },
            "cost_tier": model["cost"],
        }

    except requests.exceptions.Timeout:
        return {"success": False, "error": f"{model['label']} timed out (180s)"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"{model['label']} API error: {e}"}
    except (KeyError, IndexError) as e:
        return {"success": False, "error": f"Bad response from {model['label']}: {e}"}


def main():
    parser = argparse.ArgumentParser(
        description="Thunderbird OpenRouter CLI — call any model from Claude Code"
    )
    parser.add_argument(
        "--model", "-m", choices=list(MODELS.keys()), help="Model shortname"
    )
    parser.add_argument("--prompt", "-p", help="Prompt text")
    parser.add_argument("--system", "-s", help="System prompt")
    parser.add_argument("--max-tokens", "-t", type=int, help="Max output tokens")
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--stdin", action="store_true", help="Read prompt from stdin")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--list", "-l", action="store_true", help="List models")

    args = parser.parse_args()

    if args.list:
        print(f"{'Key':15s} {'Model':30s} {'Cost':14s} {'Context':>10s}  {'Tier'}")
        print("-" * 80)
        for key, m in MODELS.items():
            print(
                f"{key:15s} {m['label']:30s} {m['cost']:14s} {m['context']:>10,}  {m['tier']}"
            )
        return

    if not args.model:
        parser.error("--model is required (or use --list)")

    prompt = args.prompt
    if args.stdin or not prompt:
        if not sys.stdin.isatty():
            prompt = sys.stdin.read().strip()

    if not prompt:
        parser.error("No prompt provided (use --prompt or --stdin)")

    result = call_openrouter(
        args.model,
        prompt,
        system=args.system,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
    )

    if args.json:
        print(json.dumps(result, indent=2))
    elif result["success"]:
        print(f"**{result['model']}, OpenRouter**\n")
        print(result["content"])
    else:
        print(f"[ERROR] {result['error']}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
