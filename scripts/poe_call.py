#!/usr/bin/env python3
"""
poe_call.py — Poe.com model broker (replaces openrouter_call.py)
OpenAI-compatible endpoint. Points/subscription — no per-token billing surprises.

ALIASES (convenience shortcuts):
  deepseek    → deepseek-v3.2
  deepseek-v4 → deepseek-v4-pro-t
  grok        → grok-4.1-fast-non-reasoning
  grok4       → grok-4.3
  r1          → deepseek-r1-di
  kimi        → kimi-k2.5
  kimi2       → kimi-k2.7-code
  gpt4o       → gpt-4o
  o3          → o3
  gemini      → gemini-3.5-flash

ANY RAW POE MODEL ID WORKS DIRECTLY — no registration needed:
  python3 scripts/poe_call.py --model deepseek-v4-pro-t --prompt "..."
  python3 scripts/poe_call.py --model grok-4.3 --prompt "..."
  python3 scripts/poe_call.py --model claude-opus-4.8 --prompt "..."
  python3 scripts/poe_call.py --models   # list ALL 380+ models from Poe live

Usage:
  python3 scripts/poe_call.py --model grok --prompt "..."
  python3 scripts/poe_call.py --model deepseek-v4-pro-t --prompt "..."
  python3 scripts/poe_call.py --model grok --system "SYS PROMPT" --prompt "..."
  echo "prompt" | python3 scripts/poe_call.py --model r1 --stdin
  python3 scripts/poe_call.py --list      # show aliases
  python3 scripts/poe_call.py --models    # show ALL live Poe models
  python3 scripts/poe_call.py --check     # verify API key health
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path


# ── ALIASES — shortcut keys → Poe model IDs ──────────────────────────────────
# If --model doesn't match an alias, it's passed directly as a Poe model ID.
ALIASES = {
    # ── Claude family ─────────────────────────────────────────────────────────
    "claude":        "claude-sonnet-4.6",   # default
    "sonnet":        "claude-sonnet-4.6",
    "opus":          "claude-opus-4.8",
    "claude-code":   "claude-code",
    "cc":            "claude-code",
    "code":          "claude-code",
    "claude-haiku":  "claude-haiku-4.5",
    "haiku":         "claude-haiku-4.5",
    # ── Kimi ──────────────────────────────────────────────────────────────────
    "kimi":          "kimi-k2.5",
    "k2":            "kimi-k2.5",
    "kimi-think":    "kimi-k2-thinking",
    "k2-think":      "kimi-k2-thinking",
    # ── Nano Banana ───────────────────────────────────────────────────────────
    "nano-banana":   "nano-banana",
    "banana":        "nano-banana",
    "nano-banana-2": "nano-banana-2",
    "banana2":       "nano-banana-2",
    "nano-webui":    "nano-banana",         # WebUI variant — falls back to nano-banana
    "webui":         "nano-banana",
    # ── Gemini ────────────────────────────────────────────────────────────────
    "gemini":        "gemini-3.5-flash",
    "flash":         "gemini-3.5-flash",
    "gemini-pro":    "gemini-3.1-pro",
    # ── GPT ───────────────────────────────────────────────────────────────────
    "gpt4":          "gpt-4o",
    "4o":            "gpt-4o",
    "gpt4o":         "gpt-4o",
    "gpt4-mini":     "gpt-4o-mini",
    "mini":          "gpt-4o-mini",
    # ── Speed / Llama ─────────────────────────────────────────────────────────
    "speed":         "llama-3.3-70b",
    "fast":          "llama-3.3-70b",
    # ── Grok ──────────────────────────────────────────────────────────────────
    "grok":          "grok-3",
    "grok4":         "grok-4.3",
    "grok-fast":     "grok-4.1-fast-non-reasoning",
    "grok-imagine":  "grok-imagine-image",
    # ── DeepSeek ──────────────────────────────────────────────────────────────
    "deepseek":      "deepseek-v3.2",
    "deepseek-v4":   "deepseek-v4-pro-t",
    "r1":            "deepseek-r1-di",
    # ── Other ─────────────────────────────────────────────────────────────────
    "o3":            "o3",
}

# Human-readable descriptions for --list
ALIAS_INFO = {
    "claude":        ("Claude Sonnet 4.6",              "200K", "default"),
    "opus":          ("Claude Opus 4.8",                "200K", "Anthropic flagship"),
    "claude-code":   ("Claude Code",                   "200K", "coding specialist  aliases: cc, code"),
    "claude-haiku":  ("Claude Haiku 4.5",              "200K", "fast/cheap  alias: haiku"),
    "kimi":          ("Kimi K2.5",                     "2M",   "large context  alias: k2 [PII-FENCE]"),
    "kimi-think":    ("Kimi K2 Thinking",              "2M",   "extended CoT  alias: k2-think [PII-FENCE]"),
    "nano-banana":   ("Nano Banana",                   "?",    "original  alias: banana"),
    "nano-banana-2": ("Nano Banana 2",                 "?",    "alias: banana2"),
    "nano-webui":    ("Nano Banana WebUI",             "?",    "alias: webui"),
    "gemini":        ("Gemini 3.5 Flash",              "1M",   "multimodal  aliases: flash"),
    "gemini-pro":    ("Gemini 3.1 Pro",                "1M",   "Gemini Pro tier"),
    "gpt4":          ("GPT-4o",                        "128K", "aliases: 4o, gpt4o"),
    "gpt4-mini":     ("GPT-4o Mini",                   "128K", "alias: mini"),
    "speed":         ("Llama 3.3 70B",                  "128K", "fastest  alias: fast"),
    "grok":          ("Grok 3",                        "?",    "xAI Grok 3"),
    "grok4":         ("Grok 4.3",                      "2M",   "latest Grok"),
    "grok-fast":     ("Grok 4.1 Fast",                 "2M",   "Grok 4.1 non-reasoning"),
    "grok-imagine":  ("Grok Imagine",                  "?",    "image generation"),
    "deepseek":      ("DeepSeek V3.2",                 "128K", "[PII-FENCE]"),
    "deepseek-v4":   ("DeepSeek V4 Pro",               "128K", "[PII-FENCE]"),
    "r1":            ("DeepSeek R1",                   "128K", "chain-of-thought [PII-FENCE]"),
    "o3":            ("OpenAI o3",                     "200K", "hard reasoning"),
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


def resolve_model(model_key: str) -> str:
    """Resolve alias → Poe model ID, or pass raw ID through directly."""
    return ALIASES.get(model_key, model_key)


def call_poe(model_key: str, prompt: str, system: str = "") -> str:
    model_id = resolve_model(model_key)
    api_key = load_api_key()

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = json.dumps({
        "model": model_id,
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


def fetch_all_models() -> list:
    api_key = load_api_key()
    req = urllib.request.Request(
        "https://api.poe.com/v1/models",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return [m["id"] for m in data.get("data", [])]


def check_health() -> bool:
    try:
        models = fetch_all_models()
        print(f"OK — Poe API healthy. {len(models)} models available.")
        return True
    except Exception as e:
        print(f"FAIL — Poe API error: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Poe.com model broker — aliases or any raw Poe model ID")
    parser.add_argument("--model", "-m", help="Alias (grok/deepseek/r1/kimi/…) OR any raw Poe model ID")
    parser.add_argument("--prompt", "-p", help="User prompt")
    parser.add_argument("--system", "-s", default="", help="System prompt")
    parser.add_argument("--stdin", action="store_true", help="Read prompt from stdin")
    parser.add_argument("--list", "-l", action="store_true", help="List aliases")
    parser.add_argument("--models", action="store_true", help="List ALL live Poe models (API call)")
    parser.add_argument("--check", action="store_true", help="Check API key health")
    args = parser.parse_args()

    if args.check:
        sys.exit(0 if check_health() else 1)

    if args.list:
        print(f"{'Alias':<14} {'→ Poe Model ID':<40} {'Ctx':<5} Notes")
        print("-" * 85)
        for alias, info in ALIAS_INFO.items():
            label, ctx, notes = info
            print(f"{alias:<14} {ALIASES[alias]:<40} {ctx:<5} {notes}")
        print("\nTip: pass ANY Poe model ID directly — e.g. --model deepseek-v4-pro-t")
        return

    if args.models:
        try:
            models = fetch_all_models()
            print(f"Poe live models ({len(models)} total):\n")
            for m in sorted(models):
                alias_for = [k for k, v in ALIASES.items() if v == m]
                tag = f"  ← alias: {alias_for[0]}" if alias_for else ""
                print(f"  {m}{tag}")
        except Exception as e:
            print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(1)
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
