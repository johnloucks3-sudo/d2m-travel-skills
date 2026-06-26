#!/usr/bin/env python3
"""
bg_llm.py — Background LLM caller. Drop-in for headless `claude --print` in overnight scripts.

Routes: Gemini 2.5 Flash-Lite (primary, free) → GitHub Models Mistral Small (fallback, free).
Both confirmed working from yoga's IP. Zero cost — no Poe points consumed.

Usage:
  # As CLI (prompt via stdin or --prompt):
  echo "Summarize X" | python3 scripts/bg_llm.py
  python3 scripts/bg_llm.py --prompt "Summarize X" --system "You are..."

  # As library:
  from scripts.bg_llm import bg_complete
  text = bg_complete(prompt="Summarize X", system="You are...")
"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).parent.parent

GEMINI_MODEL = "gemini-2.5-flash-lite"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
GITHUB_FALLBACK_MODEL = "mistral-small-2503"  # GitHub Models free tier, Azure-backed, no IP block


def _load_env():
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())


def _post_json(url: str, payload: dict, headers: dict, timeout: int = 60) -> dict:
    data = json.dumps(payload).encode()
    h = {**headers, "Content-Type": "application/json"}
    req = urllib.request.Request(url, data=data, headers=h, method="POST")
    resp = urllib.request.urlopen(req, timeout=timeout)
    return json.loads(resp.read())


def _gemini_complete(prompt: str, system: str, max_tokens: int, temperature: float) -> str:
    """Call Gemini 2.5 Flash-Lite via Google AI direct API. Free tier, no IP restrictions."""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")

    contents = []
    if system:
        contents.append({"role": "user", "parts": [{"text": f"[System context]: {system}"}]})
        contents.append({"role": "model", "parts": [{"text": "Understood. I'll follow those instructions."}]})
    contents.append({"role": "user", "parts": [{"text": prompt}]})

    payload = {
        "contents": contents,
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": temperature,
        },
    }
    url = f"{GEMINI_API_URL}?key={api_key}"
    result = _post_json(url, payload, {}, timeout=90)
    text = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
    if not text:
        raise RuntimeError(f"Gemini returned empty content: {result}")
    return text


def _github_complete(prompt: str, system: str, model: str, max_tokens: int) -> str:
    """Call GitHub Models (Azure-backed, free tier). GITHUB_TOKEN required."""
    if str(ROOT / "core/ai_infra") not in sys.path:
        sys.path.insert(0, str(ROOT))
    from core.ai_infra.free_model_router import free_infer
    return free_infer(prompt, provider="github", model=model, system=system, max_tokens=max_tokens)


def bg_complete(
    prompt: str,
    system: str = "You are a helpful AI assistant for Dreams2Memories Travel.",
    model: str | None = None,
    max_tokens: int = 2048,
    temperature: float = 0.7,
) -> str:
    """Return completion text. Raises on all-provider failure.

    Provider chain (both $0, confirmed working from yoga's IP):
      1. Gemini 2.5 Flash-Lite — Google AI free tier, 1M tok/day
      2. GitHub Models Mistral Small — Azure-backed, free with GITHUB_TOKEN
    """
    _load_env()

    # 1. Gemini primary
    try:
        text = _gemini_complete(prompt, system, max_tokens, temperature)
        print(f"[bg_llm] Gemini 2.5 Flash-Lite", file=sys.stderr)
        return text
    except Exception as e:
        print(f"[bg_llm] Gemini failed ({e}), trying GitHub Models", file=sys.stderr)

    # 2. GitHub Models fallback (free, Azure-backed, no IP block)
    try:
        gh_model = GITHUB_FALLBACK_MODEL
        text = _github_complete(prompt, system, gh_model, max_tokens)
        print(f"[bg_llm] GitHub Models {gh_model}", file=sys.stderr)
        return text
    except Exception as e:
        print(f"[bg_llm] GitHub Models failed: {e}", file=sys.stderr)

    raise RuntimeError("All LLM providers failed (Gemini + GitHub Models)")


def main():
    parser = argparse.ArgumentParser(description="Background LLM — free model, no Claude Max")
    parser.add_argument("--prompt", "-p", help="Prompt text (or read from stdin)")
    parser.add_argument("--system", "-s", default="You are a helpful AI assistant for Dreams2Memories Travel.")
    parser.add_argument("--model", "-m", default=None)
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument("--temperature", type=float, default=0.7)
    args = parser.parse_args()

    if args.prompt:
        prompt = args.prompt
    elif not sys.stdin.isatty():
        prompt = sys.stdin.read().strip()
    else:
        parser.print_help()
        sys.exit(1)

    try:
        result = bg_complete(
            prompt=prompt,
            system=args.system,
            model=args.model,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
        )
        print(result)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
