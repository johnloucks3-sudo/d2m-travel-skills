#!/usr/bin/env python3
"""
Claude Narrative Generator — Luxury Itinerary Port Narratives
===============================================================
Phase 4B (docs/PHASE_4_ROADMAP.md) — Claude API integration for narrative
generation. Uses claude-sonnet directly via the Anthropic SDK for superior
narrative quality vs the Gemini Flash fallback (200K context window,
better instruction following, consistent luxury voice).

Falls back to core.ai_infra.gemini_client.call_gemini() if the Anthropic
client is unavailable (no API key, import failure, or API error) so the
itinerary pipeline never stalls on a single provider outage.

Usage:
    from core.email.claude_narrative_generator import ClaudeNarrativeGenerator

    gen = ClaudeNarrativeGenerator()
    narrative = gen.generate(
        port_name="Venice, Italy",
        voyage_details="Silversea Silver Nova, Mediterranean Explorer, embark Barcelona",
    )
"""

import os
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("thunderbird.claude_narrative_generator")

MODEL = "claude-sonnet-4-6"
INPUT_COST_PER_M = 3.00
OUTPUT_COST_PER_M = 15.00

DEFAULT_STYLE_GUIDE = (
    "You are a luxury travel copywriter for Dreams2Memories Travel, LLC. "
    "Write sophisticated, sensory, evocative prose for ultra-high-net-worth "
    "travelers. Ground every detail in the voyage information given — never "
    "invent a fact not present in it. No cliches, no exclamation points, no "
    "melodrama."
)

_USAGE_LOG = Path(__file__).parent.parent / "ai_infra" / "data" / "claude_narrative_usage.jsonl"


def _log_usage(port_name: str, model: str, input_tokens: int, output_tokens: int,
                success: bool, fallback_used: bool, error: Optional[str] = None) -> None:
    """Write one JSONL cost-tracking record. Never raises."""
    try:
        _USAGE_LOG.parent.mkdir(parents=True, exist_ok=True)
        cost = (input_tokens / 1_000_000 * INPUT_COST_PER_M) + \
               (output_tokens / 1_000_000 * OUTPUT_COST_PER_M)
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "port_name": port_name,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": round(cost, 6),
            "success": success,
            "fallback_used": fallback_used,
            "error": error,
        }
        with open(_USAGE_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception as log_err:
        logger.warning("claude_narrative_generator: usage log write failed: %s", log_err)


class ClaudeNarrativeGenerator:
    """Generates 3-4 paragraph luxury port narratives via Claude, with Gemini fallback."""

    def __init__(self, model: str = MODEL, style_guide: str = DEFAULT_STYLE_GUIDE):
        self.model = model
        self.style_guide = style_guide
        self._client = None
        try:
            import anthropic
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise RuntimeError("ANTHROPIC_API_KEY not set")
            self._client = anthropic.Anthropic(api_key=api_key)
        except Exception as e:
            logger.warning("claude_narrative_generator: Anthropic client unavailable (%s) — will use Gemini fallback", e)

    def generate(self, port_name: str, voyage_details: str, style_guide: Optional[str] = None) -> str:
        """
        Generate a 3-4 paragraph luxury narrative for a port stop.

        Args:
            port_name:      e.g. "Venice, Italy"
            voyage_details: Ship, itinerary, region context — the factual grounding
            style_guide:    Optional override of the default D2M style/system prompt

        Returns:
            Narrative text. Falls back to Gemini, then a plain-fact sentence, on failure.
        """
        system_prompt = style_guide or self.style_guide
        user_prompt = (
            f"Write a luxury travel narrative for {port_name}.\n\n"
            f"Voyage context: {voyage_details}\n\n"
            f"Length: 3-4 paragraphs. Audience: ultra-high-net-worth travelers."
        )

        if self._client is not None:
            try:
                response = self._client.messages.create(
                    model=self.model,
                    max_tokens=2000,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                )
                narrative = response.content[0].text
                _log_usage(
                    port_name, self.model,
                    response.usage.input_tokens, response.usage.output_tokens,
                    success=True, fallback_used=False,
                )
                return narrative
            except Exception as e:
                logger.error("claude_narrative_generator: Claude call failed for %s (%s) — falling back to Gemini", port_name, e)
                _log_usage(port_name, self.model, 0, 0, success=False, fallback_used=True, error=str(e))

        return self._gemini_fallback(port_name, voyage_details, system_prompt)

    def _gemini_fallback(self, port_name: str, voyage_details: str, system_prompt: str) -> str:
        try:
            from core.ai_infra.gemini_client import call_gemini
            user_prompt = (
                f"Write a luxury travel narrative for {port_name}.\n\n"
                f"Voyage context: {voyage_details}\n\n"
                f"Length: 3-4 paragraphs. Audience: ultra-high-net-worth travelers."
            )
            return call_gemini(
                system_prompt, user_prompt,
                max_tokens=2000, caller="claude_narrative_generator",
                task_hint=f"fallback narrative: {port_name}",
            )
        except Exception as e:
            logger.error("claude_narrative_generator: Gemini fallback also failed for %s (%s)", port_name, e)
            return f"Experience the magic of {port_name}."


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    gen = ClaudeNarrativeGenerator()

    test_cases = [
        ("Venice, Italy", "Silversea Silver Nova, Mediterranean Explorer voyage, overnight call in Venice with gondola access to St. Mark's Square"),
        ("Barcelona, Spain", "Silversea Silver Nova, Mediterranean Explorer voyage, embarkation port, Gaudi architecture and Gothic Quarter"),
        ("Oslo, Norway", "Regent Seven Seas Grandeur, Scandinavia & Baltic voyage, fjord approach with Viking Ship Museum excursion"),
    ]

    for port_name, voyage_details in test_cases:
        print(f"\n{'=' * 70}\n{port_name}\n{'=' * 70}")
        print(gen.generate(port_name, voyage_details))
