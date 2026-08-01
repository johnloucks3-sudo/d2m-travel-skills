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
    """Call Gemini 2.5 Flash-Lite / 3.6 Flash via Google AI direct API with HTTP 429 exponential backoff."""
    import time, random
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

    # Retries on 429 rate limit with exponential backoff
    for attempt in range(4):
        try:
            result = _post_json(url, payload, {}, timeout=90)
            text = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            if not text:
                raise RuntimeError(f"Gemini returned empty content: {result}")
            return text
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 3:
                sleep_time = (2 ** attempt) + random.uniform(0.5, 1.5)
                print(f"[bg_llm] HTTP 429 Rate Limit. Retrying in {sleep_time:.1f}s (attempt {attempt+1}/4)...", file=sys.stderr)
                time.sleep(sleep_time)
            else:
                raise



def _poe_complete(prompt: str, system: str, max_tokens: int, temperature: float) -> str:
    """Call Poe.com API (Gemini-2.5-Flash) with daily 12,000 point budget cap until Aug 19th, 2026."""
    import time
    from datetime import datetime
    
    api_key = os.environ.get("POE_API_KEY", "")
    if not api_key:
        raise RuntimeError("POE_API_KEY not set")

    # Point Budget Tracking
    ledger_path = ROOT / "logs" / "poe_point_ledger.json"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    ledger = {}
    if ledger_path.exists():
        try:
            ledger = json.loads(ledger_path.read_text())
        except Exception:
            ledger = {}
    
    daily_used = ledger.get(today_str, 0)
    DAILY_CAP = 12000
    
    if daily_used >= DAILY_CAP:
        raise RuntimeError(f"Poe daily point budget reached ({daily_used}/{DAILY_CAP} points used today)")

    url = "https://api.poe.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": "Gemini-2.5-Flash",
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens
    }

    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
    resp = urllib.request.urlopen(req, timeout=60)
    data = json.loads(resp.read())

    text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    if not text:
        raise RuntimeError(f"Poe returned empty content: {data}")

    # Estimate point cost (~20 points per Flash call) and update ledger
    estimated_points = 20
    ledger[today_str] = daily_used + estimated_points
    ledger_path.write_text(json.dumps(ledger, indent=2))
    
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

    Provider Fail-Over Chain:
      1. Direct Gemini API (Gemini 2.5 Flash-Lite / 3.6 Flash with 429 backoff)
      2. Poe.com API (Gemini-2.5-Flash — capped at 12,000 points/day until Aug 19th)
      3. GitHub Models Mistral Small (Azure-backed, free tier)
    """
    _load_env()

    # 1. Direct Gemini primary
    try:
        text = _gemini_complete(prompt, system, max_tokens, temperature)
        print(f"[bg_llm] Direct Gemini API", file=sys.stderr)
        return text
    except Exception as e:
        print(f"[bg_llm] Direct Gemini failed ({e}), trying Poe.com fail-over...", file=sys.stderr)

    # 2. Poe.com fail-over (Gemini-2.5-Flash, max 12,000 pts/day)
    try:
        text = _poe_complete(prompt, system, max_tokens, temperature)
        print(f"[bg_llm] Poe.com Gemini-2.5-Flash (Fail-over)", file=sys.stderr)
        return text
    except Exception as e:
        print(f"[bg_llm] Poe.com fail-over failed ({e}), trying GitHub Models...", file=sys.stderr)

    # 3. GitHub Models fallback (free, Azure-backed, no IP block)
    try:
        gh_model = GITHUB_FALLBACK_MODEL
        text = _github_complete(prompt, system, gh_model, max_tokens)
        print(f"[bg_llm] GitHub Models {gh_model}", file=sys.stderr)
        return text
    except Exception as e:
        print(f"[bg_llm] GitHub Models failed: {e}", file=sys.stderr)

    raise RuntimeError("All LLM providers failed (Direct Gemini + Poe.com + GitHub Models)")



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
