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

import sys
from pathlib import Path
sys.path.insert(0, "/home/john/Thunderbird")
from OpsCenter.hale_dispatcher import HaleDispatcher

# D2M_SYSTEM is used by the dispatcher if needed, but not directly here anymore

class PerplexityClient:
    """Live web research via Hale Dispatcher (Intel Brain)."""

    def __init__(self, model: str = None, timeout: int = 30):
        self.hale = HaleDispatcher()

    def search(
        self,
        query: str,
        system: Optional[str] = None,
        max_tokens: int = 600,
        pro: bool = False,
    ) -> dict:
        """
        Run a live web-grounded search via Hale Dispatcher.
        """
        # We lose structured source data here, but fulfill the dispatcher pattern.
        # Could be improved by parsing dispatcher output if needed.
        result = self.hale.dispatch(f"Research: {query}")
        return {
            "answer": result,
            "sources": [],
            "model": "hale-dispatcher",
            "latency_ms": 0,
            "tokens_in": 0,
            "tokens_out": 0,
            "cost_est_usd": 0.0,
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
        """

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
