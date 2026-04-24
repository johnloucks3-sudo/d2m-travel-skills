"""
Thunderbird Perplexity Client — Live Web Research via Sonar API
Routes through OpenRouter (no separate API key needed — uses OPENROUTER_API_KEY).

Cost: ~$0.01-0.05 per intel sweep (Sonar: $1/M tokens + search request fee)
Use cases: A2 destination intel, competitor pricing, cruise news, morning brief research

Usage:
    from core.intel.thunderbird_perplexity import PerplexityClient
    client = PerplexityClient()
    result = client.search("Latest Silversea Silver Nova 2027 itineraries")
    print(result["answer"])
    for src in result["sources"]: print(src["url"])
"""

import json
import logging
import os
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv(Path.home() / "Thunderbird" / ".env")

logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Sonar = web-grounded answers with citations ($1/$1 per M tokens + request fee)
# Sonar Pro = deeper research ($3/$15 per M tokens)
SONAR_MODEL = "perplexity/sonar"
SONAR_PRO_MODEL = "perplexity/sonar-pro"

D2M_SYSTEM = (
    "You are A2 Dembe, research intelligence officer for Dreams2Memories Travel, LLC — "
    "a luxury travel concierge specializing in Silversea, Regent Seven Seas, Cunard, "
    "Oceania, Seabourn, Viking, AmaWaterways, and Ponant. "
    "Provide factual, current, sourced intelligence. "
    "Lead with the most actionable finding. Be concise — max 400 words. "
    "Always cite sources."
)


class PerplexityClient:
    """Live web research via Perplexity Sonar through OpenRouter."""

    def __init__(self, model: str = SONAR_MODEL, timeout: int = 30):
        if not OPENROUTER_API_KEY:
            raise RuntimeError(
                "OPENROUTER_API_KEY not set in ~/Thunderbird/.env"
            )
        self.model = model
        self.timeout = timeout

    def search(
        self,
        query: str,
        system: Optional[str] = None,
        max_tokens: int = 600,
        pro: bool = False,
    ) -> dict:
        """
        Run a live web-grounded search via Perplexity Sonar.

        Returns:
            {
                "answer": str,           # model's answer
                "sources": list[dict],   # [{title, url}]
                "model": str,
                "latency_ms": int,
                "tokens_in": int,
                "tokens_out": int,
                "cost_est_usd": float,   # rough estimate
            }
        """
        model = SONAR_PRO_MODEL if pro else self.model
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system or D2M_SYSTEM},
                {"role": "user", "content": query},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.2,
        }

        body = json.dumps(payload).encode()
        req = urllib.request.Request(
            OPENROUTER_URL,
            data=body,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://d2mluxury.quest",
                "X-Title": "Thunderbird A2 Intel",
            },
            method="POST",
        )

        t0 = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body_err = e.read().decode()[:500]
            raise RuntimeError(f"Perplexity API error {e.code}: {body_err}") from e

        latency_ms = int((time.monotonic() - t0) * 1000)
        choice = raw["choices"][0]
        message = choice["message"]
        answer = message.get("content", "")

        # Extract citations from Perplexity's response format
        sources = []
        citations = raw.get("citations", [])
        for c in citations:
            if isinstance(c, dict):
                sources.append({"title": c.get("title", ""), "url": c.get("url", "")})
            elif isinstance(c, str):
                sources.append({"title": "", "url": c})

        usage = raw.get("usage", {})
        tokens_in = usage.get("prompt_tokens", 0)
        tokens_out = usage.get("completion_tokens", 0)
        # Rough cost: $1/M input + $1/M output + ~$0.005 search fee
        cost_est = (tokens_in + tokens_out) / 1_000_000 + 0.005

        return {
            "answer": answer,
            "sources": sources,
            "model": model,
            "latency_ms": latency_ms,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_est_usd": round(cost_est, 4),
        }

    # ------------------------------------------------------------------
    # D2M-specific helpers
    # ------------------------------------------------------------------

    def cruise_intel(self, cruise_line: str, topic: str = "itineraries and pricing 2026-2027") -> dict:
        """Research a specific cruise line. Returns answer + sources."""
        query = f"{cruise_line} {topic} — latest news, pricing, availability"
        return self.search(query)

    def destination_intel(self, destination: str) -> dict:
        """Research a destination for client trip planning."""
        query = (
            f"Travel intelligence for {destination}: "
            "current travel advisories, best time to visit, top luxury experiences, "
            "port facilities for cruise passengers, shore excursion highlights 2026"
        )
        return self.search(query)

    def competitor_pricing(self, cruise_line: str, route: str) -> dict:
        """Check competitor/public pricing for a specific cruise line + route."""
        query = f"{cruise_line} pricing for {route} — current fares, promotions, availability"
        return self.search(query, pro=True)

    def morning_brief_sweep(self, topics: list[str]) -> list[dict]:
        """Run multiple searches for morning brief. Returns list of results."""
        results = []
        for topic in topics:
            try:
                r = self.search(topic)
                r["topic"] = topic
                results.append(r)
            except Exception as e:
                logger.warning("Perplexity search failed for '%s': %s", topic, e)
                results.append({"topic": topic, "answer": f"Search failed: {e}", "sources": []})
        return results

    def format_intel_report(self, result: dict) -> str:
        """Format a Perplexity result as a D2M intel report section."""
        lines = [result.get("answer", "")]
        if result.get("sources"):
            lines.append("\n**Sources:**")
            for s in result["sources"]:
                title = s.get("title") or s.get("url", "")
                url = s.get("url", "")
                if url:
                    lines.append(f"- [{title}]({url})" if title != url else f"- {url}")
        lines.append(
            f"\n*Sonar · {result.get('latency_ms', 0)}ms · "
            f"est. ${result.get('cost_est_usd', 0):.4f}*"
        )
        return "\n".join(lines)


# ------------------------------------------------------------------
# Self-test
# ------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    client = PerplexityClient()

    print("=== Perplexity Sonar Self-Test ===\n")
    print("Query: Silversea Silver Nova 2027 Japan itinerary pricing\n")

    result = client.cruise_intel("Silversea Silver Nova", "2027 Japan itinerary and pricing")
    print(client.format_intel_report(result))
    print(f"\nTokens: {result['tokens_in']} in / {result['tokens_out']} out")
    print(f"Cost est: ${result['cost_est_usd']:.4f}")
    print(f"Latency: {result['latency_ms']}ms")
    print(f"Sources: {len(result['sources'])}")
