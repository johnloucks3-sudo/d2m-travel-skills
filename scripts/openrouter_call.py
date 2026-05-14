#!/usr/bin/env python3
"""
openrouter_call.py — Unified CLI for OpenRouter API calls
Used by Claude Code agents, skills, and escalation hooks.

GUARDRAIL: Only free-model keys are allowed from OpenRouter.
Poe.com models are ALLOWED (user-selectable via Poe gateway).

Available model keys (free from OpenRouter):
  gemma-3, deepseek-r1, deepseek-chat

Usage:
  python3 scripts/openrouter_call.py --model gemma-3 --prompt "..."
  echo "prompt" | python3 scripts/openrouter_call.py --model deepseek-r1 --stdin
  python3 scripts/openrouter_call.py --list
"""

import argparse
import json
import os
import sys
from pathlib import Path

# ── ALLOWED MODELS (FREE ONLY from OpenRouter) ──────────────────────────────
# ...


# ── ALLOWED MODELS (FREE ONLY from OpenRouter) ──────────────────────────────
# NOTE: Poe.com models bypass this restriction — they are allowed via Poe gateway.
MODELS = {
    # FREE MODELS — $0 cost
    "gemma-3": {
        "id": "openrouter/google/gemma-3-27b-it:free",
        "label": "Gemma 3 27B",
        "context": 8192,
        "cost": "FREE",
        "free": True,
        "best_for": "visualization, writing, creative tasks"
    },
    "deepseek-r1": {
        "id": "openrouter/deepseek/deepseek-r1:free",
        "label": "DeepSeek R1",
        "context": 16384,
        "cost": "FREE",
        "free": True,
        "best_for": "reasoning, analysis, logic"
    },
    # WING NODES — paid via OpenRouter (complements Gemini on YOGA)
    # Per April 30 analysis: Gemini Flash-Lite 2.7× cheaper than DeepSeek for bulk tasks.
    # NOTE: Primary Gemini path is OpenCode (gemini-3.1-flash-lite). This is the OpenRouter fallback.
    # NOTE: Grok is NOT a D2M wing resource — removed.
    "gemini": {
        "id": "google/gemini-3.1-flash-lite",
        "label": "Gemini 3.1 Flash Lite",
        "context": 1000000,
        "cost": "$0.016/M",
        "free": False,
        "best_for": "fast ops, summarization, bulk context — cheapest paid model"
    },
    "deepseek": {
        "id": "deepseek/deepseek-chat-v3.1",
        "label": "DeepSeek V3.1",
        "context": 65536,
        "cost": "$0.27/M",
        "free": False,
        "best_for": "OpenCode primary model — ops, research, analysis"
    },
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OpenRouter call (free-model guardrail)")
    parser.add_argument("--model", required=True, help="Model key from MODELS")
    parser.add_argument("--prompt", default="", help="User prompt")
    parser.add_argument("--system", default="", help="System prompt")
    parser.add_argument("--stdin", action="store_true", help="Read prompt from stdin")
    parser.add_argument("--list", action="store_true", help="List allowed models and exit")
    parser.add_argument("--max-tokens", type=int, default=4096, help="Max tokens")
    parser.add_argument("--temperature", type=float, default=0.7, help="Temperature")
    return parser.parse_args()


def _validate_model(model_key: str) -> dict:
    """Ensure model is in allowed list."""
    if model_key not in MODELS:
        allowed = ", ".join(MODELS.keys())
        raise ValueError(
            f"Model '{model_key}' is not allowed from OpenRouter.\n"
            f"Allowed free keys: {allowed}\n"
            f"Poe.com models are allowed via the Poe gateway (use --poe flag if using poe wrapper)."
        )
    return MODELS[model_key]


def _load_stdin() -> str:
    return sys.stdin.read().strip()


from OpsCenter.hale_dispatcher import HaleDispatcher

# ...

def _call_openrouter(model_cfg: dict, system: str, user_prompt: str, args: argparse.Namespace) -> dict:
    """Make the OpenRouter API call."""
    # REFACTORED: Use HaleDispatcher for all calls
    hale = HaleDispatcher()
    
    # Simple dispatch, Hale handles the brain classification based on keywords
    # This replaces the entire requests.post structure
    result_content = hale.dispatch(user_prompt)
    
    # Mock the expected return structure to maintain compatibility
    return {"choices": [{"message": {"content": result_content}}]}



def main():
    args = _parse_args()

    if args.list:
        print("Allowed OpenRouter model keys (FREE or explicitly permitted):")
        for key, cfg in MODELS.items():
            print(f"  {key:16} -> {cfg['label']:32} ({cfg['cost']}) — {cfg['best_for']}")
        return

    # Validate
    model_cfg = _validate_model(args.model)

    # Build prompt
    if args.stdin:
        user_prompt = _load_stdin()
    else:
        user_prompt = args.prompt

    if not user_prompt:
        print("No prompt provided. Use --prompt or pipe via stdin.", file=sys.stderr)
        sys.exit(1)

    # Confirm non-free (if applicable)
    estimated_cost_note = ""
    estimated_cost = model_cfg.get("cost", "FREE")
    if not model_cfg.get("free", False):
        estimated_cost_note = f" [NOTE: model '{args.model}' costs {estimated_cost}]"

    print(f"→ Calling {model_cfg['label']}...{estimated_cost_note}", file=sys.stderr)

    try:
        result = _call_openrouter(model_cfg, args.system, user_prompt, args)
        content = result["choices"][0]["message"]["content"]
        print(content)

        # Log usage if possible
        try:
            usage = result.get("usage", {})
            log_entry = {
                "timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
                "model_key": args.model,
                "model_id": model_cfg["id"],
                "prompt_tokens": usage.get("prompt_tokens"),
                "completion_tokens": usage.get("completion_tokens"),
                "total_tokens": usage.get("total_tokens"),
                "cost_estimate": estimated_cost,
            }
            Path("/home/john/Thunderbird/logs").mkdir(exist_ok=True)
            log_path = Path("/home/john/Thunderbird/logs/openrouter_calls.jsonl")
            with log_path.open("a") as f:
                json.dump(log_entry, f)
                f.write("\n")
        except Exception:
            pass

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
