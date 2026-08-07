"""
perplexity_search.py — Thunderbird Perplexity AI Search wrapper.

Exposes two search modes:
  search(query)         → /search endpoint — fast snippet results (3-10 results)
  deep_search(query)    → /v1/responses endpoint (fast-search preset) — 15 results + citations
  embed(texts)          → /v1/embeddings with pplx-embed-v1-4b

Wing usage:
  from core.search.perplexity_search import search, deep_search, embed

Key: PERPLEXITY_API_KEY in .env or environment.
Thunderbird HALE key added 2026-06-14.
"""

import json
import os
import time
from pathlib import Path
from typing import Optional

import requests

# ---------------------------------------------------------------------------
API_BASE = "https://api.perplexity.ai"
EMBED_MODEL = "pplx-embed-v1-4b"
_ENV_FILE = Path(__file__).parents[2] / ".env"


def _get_key() -> str:
    key = os.environ.get("PERPLEXITY_API_KEY", "")
    if not key and _ENV_FILE.exists():
        for line in _ENV_FILE.read_text().splitlines():
            if line.startswith("PERPLEXITY_API_KEY="):
                key = line.split("=", 1)[1].strip()
                break
    if not key:
        raise RuntimeError("PERPLEXITY_API_KEY not set. Add to .env or environment.")
    return key


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {_get_key()}",
        "Content-Type": "application/json",
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def search(query: str, max_results: int = 5, max_tokens_per_page: int = 512) -> list[dict]:
    """Fast web search via Perplexity /search endpoint.

    Returns list of {title, url, snippet, last_updated} dicts.
    Best for: quick fact-checks, current pricing, news, availability.

    Args:
        query: Natural language search query
        max_results: Number of results (1-10)
        max_tokens_per_page: Max tokens per result snippet

    Returns:
        List of result dicts with keys: title, url, snippet, last_updated, date
    """
    payload = {
        "query": query,
        "max_results": max_results,
        "max_tokens_per_page": max_tokens_per_page,
    }
    resp = requests.post(f"{API_BASE}/search", headers=_headers(), json=payload, timeout=30)
    if resp.status_code == 401:  # direct API key expired/invalid — fall back to Poe Perplexity lane
        try:
            import subprocess, sys, os
            poe = Path(__file__).resolve().parents[2] / "scripts" / "poe_call.py"
            out = subprocess.run([sys.executable, str(poe), "--model",
                                  "perplexity-pro-search", "--prompt", query],
                                 capture_output=True, text=True, timeout=120)
            text = (out.stdout or "").strip()
            if text:
                return [{
                    "title": "Perplexity via Poe (fallback)",
                    "url": "https://www.perplexity.ai/search?q=" + _q(query),
                    "snippet": text[:1200],
                    "date": "",
                }]
        except Exception:
            pass
        resp.raise_for_status()
    resp.raise_for_status()
    data = resp.json()
    return data.get("results", [])


def _q(s: str) -> str:
    from urllib.parse import quote
    return quote(s)


def deep_search(query: str) -> dict:
    """Deep web search via Perplexity /v1/responses (fast-search preset).

    Returns up to 15 cited results with full source metadata.
    Best for: research memos, competitor analysis, destination intel, pricing studies.

    Args:
        query: Natural language research question

    Returns:
        Dict with keys: output (list of search output blocks), id, model, created_at
    """
    payload = {
        "preset": "fast-search",
        "input": query,
    }
    resp = requests.post(f"{API_BASE}/v1/responses", headers=_headers(), json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()


def deep_search_text(query: str) -> str:
    """Deep search — returns concatenated snippet text (plaintext, no metadata).

    Convenience wrapper for quick in-context reads by Wing agents.
    """
    data = deep_search(query)
    output_blocks = data.get("output", [])
    texts = []
    for block in output_blocks:
        for result in block.get("results", []):
            title = result.get("title", "")
            snippet = result.get("snippet", "")
            url = result.get("url", "")
            if snippet:
                texts.append(f"## {title}\n{snippet}\nSource: {url}")
    return "\n\n---\n\n".join(texts) if texts else "(no results)"


def embed(texts: list[str], model: str = EMBED_MODEL) -> list[list[float]]:
    """Generate embeddings via Perplexity /v1/embeddings.

    Args:
        texts: List of strings to embed (batch)
        model: Embedding model (default: pplx-embed-v1-4b)

    Returns:
        List of float vectors (one per input text)
    """
    payload = {"input": texts, "model": model}
    resp = requests.post(f"{API_BASE}/v1/embeddings", headers=_headers(), json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return [item["embedding"] for item in data.get("data", [])]


# ---------------------------------------------------------------------------
# Wing-specific convenience functions
# ---------------------------------------------------------------------------

def _sonar_search(query: str, max_tokens: int = 800) -> str:
    """Internal: call /chat/completions with sonar model (cheap, $0.005/call).

    Used by intel_sweep and cruise_search to avoid the expensive /v1/responses
    Response API (which spins up GPT-5.4-mini + Gemini-3-flash internally at
    full provider rates — ~$0.45/call vs $0.005/call for sonar).
    """
    payload = {
        "model": "sonar",
        "messages": [{"role": "user", "content": query}],
        "max_tokens": max_tokens,
        "temperature": 0.1,
    }
    resp = requests.post(
        f"{API_BASE}/chat/completions", headers=_headers(), json=payload, timeout=30
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def cruise_search(query: str) -> str:
    """Search for cruise availability, pricing, or itinerary info."""
    return _sonar_search(f"luxury cruise {query} 2026 2027 pricing availability per person")


def intel_sweep(topic: str) -> str:
    """Research sweep for Dembe-style OSINT — current events, industry news."""
    return _sonar_search(f"{topic} latest news developments 2026")


def flight_intel(origin: str, destination: str, travel_date: str) -> list[dict]:
    """Quick flight price intelligence for a route."""
    query = f"flights from {origin} to {destination} {travel_date} price range economy business"
    return search(query, max_results=5, max_tokens_per_page=300)


def hotel_search(city: str, check_in: str, nights: int, style: str = "luxury") -> list[dict]:
    """Hotel availability and price intel for a destination."""
    query = f"{style} hotels {city} {check_in} {nights} nights price per night availability"
    return search(query, max_results=5, max_tokens_per_page=300)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Regent Seven Seas cruise 2027 pricing"
    print(f"Searching: {query}\n")
    results = search(query, max_results=5)
    for i, r in enumerate(results, 1):
        print(f"[{i}] {r.get('title', '?')}")
        print(f"    {r.get('url', '?')}")
        print(f"    {r.get('snippet', '')[:200]}")
        print()
