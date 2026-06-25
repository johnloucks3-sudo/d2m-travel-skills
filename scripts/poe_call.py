#!/usr/bin/env python3
"""
poe_call.py — Poe.com model broker (replaces openrouter_call.py)
OpenAI-compatible endpoint. Points/subscription — no per-token billing surprises.

Model keys:
  deepseek  → deepseek-v3.2                  (V3.2, ops/research, 128K ctx)
  grok      → grok-4.1-fast-non-reasoning    (Grok 4.1 Fast, strategy, 2M ctx)
  r1        → deepseek-r1-di                 (R1 chain-of-thought reasoning)
  gpt4o     → gpt-4o                         (GPT-4o)
  o3        → o3                             (OpenAI o3 reasoning)
  gemini    → gemini-3.5-flash               (Gemini 3.5 Flash, multimodal)
  kimi      → kimi-k2.5                      (Kimi K2.5, large context)

Usage:
  python3 scripts/poe_call.py --model deepseek --prompt "..."
  python3 scripts/poe_call.py --model grok --system "SYS PROMPT" --prompt "..."
  echo "prompt" | python3 scripts/poe_call.py --model r1 --stdin
  python3 scripts/poe_call.py --list
  python3 scripts/poe_call.py --check       # verify API key health
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path


# ── MODEL CATALOG ────────────────────────────────────────────────────────────
MODELS = {
    "deepseek": {
        "id": "deepseek-v3.2",
        "label": "DeepSeek V3.2",
        "context": 128000,
        "best_for": "ops, research, summarization, data extraction",
        "pii_fence": True,
    },
    "grok": {
        "id": "grok-4.1-fast-non-reasoning",
        "label": "Grok 4.1 Fast",
        "context": 2000000,
        "best_for": "strategy, complex analysis, multi-source synthesis, large docs",
        "pii_fence": False,  # xAI is US-based
    },
    "r1": {
        "id": "deepseek-r1-di",
        "label": "DeepSeek R1",
        "context": 128000,
        "best_for": "chain-of-thought, arbitration, complex logic, math",
        "pii_fence": True,
    },
    "gpt4o": {
        "id": "gpt-4o",
        "label": "GPT-4o",
        "context": 128000,
        "best_for": "general, multimodal, broad compatibility",
        "pii_fence": False,
    },
    "o3": {
        "id": "o3",
        "label": "OpenAI o3",
        "context": 200000,
        "best_for": "hard reasoning, math, science, code",
        "pii_fence": False,
    },
    "gemini": {
        "id": "gemini-3.5-flash",
        "label": "Gemini 3.5 Flash",
        "context": 1000000,
        "best_for": "multimodal, large docs, fast turnaround",
        "pii_fence": False,
    },
    "kimi": {
        "id": "kimi-k2.5",
        "label": "Kimi K2.5",
        "context": 2000000,
        "best_for": "large context, document analysis",
        "pii_fence": True,
    },
}


def load_api_key() -> str:
    env_file = Path(__file__).parent.parent / "config" / "poe.env"
    key = os.getenv("POE_API_KEY", "")
    if not key and env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line.startswith("POE_API_KEY=") and not line.startswith("#"):
                key = line.split("=", 1)[1].strip()
                break
    if not key:
        print("ERROR: POE_API_KEY not set. Check config/poe.env", file=sys.stderr)
        sys.exit(1)
    return key


def call_poe(model_key: str, prompt: str, system: str = "") -> str:
    if model_key not in MODELS:
        print(f"ERROR: Unknown model '{model_key}'. Run --list for options.", file=sys.stderr)
        sys.exit(1)

    model = MODELS[model_key]
    api_key = load_api_key()

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = json.dumps({
        "model": model["id"],
        "messages": messages,
        "temperature": 0.7,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.poe.com/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"ERROR {e.code}: {body}", file=sys.stderr)
        sys.exit(1)


def check_health() -> bool:
    api_key = load_api_key()
    req = urllib.request.Request(
        "https://api.poe.com/v1/models",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            count = len(data.get("data", []))
            print(f"OK — Poe API healthy. {count} models available.")
            return True
    except Exception as e:
        print(f"FAIL — Poe API error: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Poe.com model broker")
    parser.add_argument("--model", "-m", help="Model key (deepseek/grok/r1/gpt4o/o3/gemini/kimi)")
    parser.add_argument("--prompt", "-p", help="User prompt")
    parser.add_argument("--system", "-s", default="", help="System prompt")
    parser.add_argument("--stdin", action="store_true", help="Read prompt from stdin")
    parser.add_argument("--list", "-l", action="store_true", help="List available models")
    parser.add_argument("--check", action="store_true", help="Check API key health")
    args = parser.parse_args()

    if args.check:
        sys.exit(0 if check_health() else 1)

    if args.list:
        print(f"{'Key':<12} {'Model ID':<40} {'Context':<12} Best For")
        print("-" * 90)
        for key, m in MODELS.items():
            ctx = f"{m['context']//1000}K" if m['context'] < 1000000 else f"{m['context']//1000000}M"
            pii = " [PII-FENCE]" if m["pii_fence"] else ""
            print(f"{key:<12} {m['id']:<40} {ctx:<12} {m['best_for']}{pii}")
        return

    if not args.model:
        parser.print_help()
        sys.exit(1)

    if args.stdin:
        prompt = sys.stdin.read().strip()
    elif args.prompt:
        prompt = args.prompt
    else:
        print("ERROR: --prompt or --stdin required", file=sys.stderr)
        sys.exit(1)

    result = call_poe(args.model, prompt, system=args.system)
    print(result)


if __name__ == "__main__":
    main()
