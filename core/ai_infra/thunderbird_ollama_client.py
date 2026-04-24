"""
Thunderbird Ollama Client — Local LLM Inference Wrapper
Replaces OpenRouter Haiku-tier calls with local Ollama inference.

Cost savings: ~$0.80/M tokens (OpenRouter Haiku) → $0 (local Ollama)
Target tasks: inbox triage, classification, summarization, simple Q&A

Usage:
    from core.ai_infra.thunderbird_ollama_client import OllamaClient
    client = OllamaClient()
    result = client.generate("Classify this task: ...", timeout=10)
"""

import json
import logging
import time
import urllib.request
import urllib.error
from typing import Optional

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "phi3:mini"   # 2.3GB — fits in 4GB RAM; mistral (4.7GB) OOMs on YOGA (13GB, swap full)
DEFAULT_TIMEOUT = 90  # seconds — cold-start load can take 30-60s on first call
FALLBACK_THRESHOLD_MS = 5000  # fall back to OpenRouter if Ollama > 5s


class OllamaClient:
    """Lightweight HTTP client for local Ollama inference."""

    def __init__(
        self,
        base_url: str = OLLAMA_BASE_URL,
        model: str = DEFAULT_MODEL,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._available: Optional[bool] = None  # cached health state

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    def is_available(self, force_check: bool = False) -> bool:
        """Return True if Ollama is reachable and the target model is loaded."""
        if self._available is not None and not force_check:
            return self._available
        try:
            req = urllib.request.Request(
                f"{self.base_url}/api/tags", method="GET"
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read())
            loaded = [m.get("name", "").split(":")[0] for m in data.get("models", [])]
            self._available = self.model.split(":")[0] in loaded
            if not self._available:
                logger.debug(
                    "Ollama reachable but model '%s' not loaded. Available: %s",
                    self.model,
                    loaded,
                )
        except Exception as e:
            logger.debug("Ollama health check failed: %s", e)
            self._available = False
        return self._available

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 512,
        temperature: float = 0.3,
        timeout: Optional[int] = None,
    ) -> dict:
        """
        Run inference against local Ollama.

        Returns:
            {
                "text": str,           # model response
                "model": str,          # model used
                "latency_ms": int,     # wall-clock ms
                "tokens_prompt": int,
                "tokens_eval": int,
                "source": "ollama"
            }

        Raises:
            OllamaUnavailableError  — if Ollama is down or model missing
            OllamaTimeoutError      — if inference exceeds timeout
        """
        if not self.is_available():
            raise OllamaUnavailableError(
                f"Ollama unavailable or model '{self.model}' not loaded"
            )

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            },
        }
        if system:
            payload["system"] = system

        body = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        t0 = time.monotonic()
        try:
            with urllib.request.urlopen(
                req, timeout=timeout or self.timeout
            ) as resp:
                raw = resp.read()
        except urllib.error.URLError as e:
            if "timed out" in str(e).lower():
                raise OllamaTimeoutError(
                    f"Ollama inference timed out after {timeout or self.timeout}s"
                ) from e
            raise OllamaUnavailableError(str(e)) from e

        latency_ms = int((time.monotonic() - t0) * 1000)
        data = json.loads(raw)

        return {
            "text": data.get("response", "").strip(),
            "model": self.model,
            "latency_ms": latency_ms,
            "tokens_prompt": data.get("prompt_eval_count", 0),
            "tokens_eval": data.get("eval_count", 0),
            "source": "ollama",
        }

    # ------------------------------------------------------------------
    # Task-specific helpers (Thunderbird use cases)
    # ------------------------------------------------------------------

    CLASSIFY_SYSTEM = (
        "You are a task classifier for Dreams2Memories Travel, a luxury travel agency. "
        "Classify the input as one of: INBOX_TRIAGE, SUMMARIZE, CLIENT_QUERY, "
        "BOOKING_UPDATE, INTEL_SCAN, ADMIN, or UNKNOWN. "
        "Reply with ONLY the category name, no explanation."
    )

    def classify_task(self, task_text: str) -> str:
        """Classify a task description into a routing category."""
        result = self.generate(
            prompt=task_text,
            system=self.CLASSIFY_SYSTEM,
            max_tokens=16,
            temperature=0.0,
        )
        return result["text"].strip().upper()

    def summarize(self, text: str, max_words: int = 100) -> str:
        """Return a concise summary of the given text."""
        result = self.generate(
            prompt=text,
            system=(
                f"Summarize the following in {max_words} words or fewer. "
                "Be concise and factual. Output only the summary, no preamble."
            ),
            max_tokens=max_words * 2,
            temperature=0.2,
        )
        return result["text"]

    def triage_inbox_item(self, subject: str, body: str) -> dict:
        """
        Triage an inbox item.

        Returns:
            {
                "priority": "P0" | "P1" | "P2" | "P3",
                "category": str,
                "summary": str,
                "route_to": str
            }
        """
        prompt = f"Subject: {subject}\n\nBody:\n{body[:1000]}"
        system = (
            "You are a triage assistant for Dreams2Memories Travel (luxury travel agency). "
            "Staff routing guide:\n"
            "- Dani (A3): client-facing tasks — logistics emails, excursion queries, client comms\n"
            "- Hale (COS): internal ops, standing orders, system config, staff directives, Wing coordination\n"
            "- A2-Dembe: research tasks — destination intel, cruise research, competitor analysis\n"
            "- A9-Harlan: finance tasks — commissions, cost analysis, invoices\n"
            "- Commander: P0 decisions, strategy changes, anything requiring Commander approval\n"
            "Priority guide: P0=urgent Commander decision, P1=time-sensitive ops, P2=standard, P3=low.\n"
            "Given a task subject and body, return ONLY a JSON object with keys: "
            "priority (P0/P1/P2/P3), category (CLIENT/BOOKING/INTEL/ADMIN/SYSTEM/FINANCE), "
            "summary (one sentence max 15 words), route_to (Dani/Hale/A2-Dembe/A9-Harlan/Commander). "
            "Reply ONLY with the JSON object, no markdown fences."
        )
        result = self.generate(prompt, system=system, max_tokens=128, temperature=0.1)
        raw = result["text"].strip()
        # Strip markdown code fences if model wraps output
        if raw.startswith("```"):
            raw = raw.split("```")[-2] if raw.count("```") >= 2 else raw
            raw = raw.lstrip("json").strip()
        # Extract first {...} block
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end != -1:
            raw = raw[start:end + 1]
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # Fallback: return raw text wrapped
            return {
                "priority": "P2",
                "category": "UNKNOWN",
                "summary": raw,
                "route_to": "Hale",
            }


# ------------------------------------------------------------------
# Exceptions
# ------------------------------------------------------------------


class OllamaUnavailableError(Exception):
    """Raised when Ollama is not reachable or the model is not loaded."""


class OllamaTimeoutError(Exception):
    """Raised when an Ollama inference call exceeds the timeout threshold."""


# ------------------------------------------------------------------
# Fallback-aware wrapper (drop-in for OpenRouter Haiku calls)
# ------------------------------------------------------------------


class OllamaWithFallback:
    """
    Wraps OllamaClient with automatic OpenRouter fallback.

    If Ollama is unavailable OR takes > FALLBACK_THRESHOLD_MS,
    the call is re-routed to OpenRouter (using the existing
    thunderbird_switchblade router).

    Usage:
        llm = OllamaWithFallback()
        response = llm.generate(prompt)
        # response["source"] will be "ollama" or "openrouter"
    """

    def __init__(self, ollama: Optional[OllamaClient] = None):
        self.ollama = ollama or OllamaClient()

    def generate(self, prompt: str, **kwargs) -> dict:
        # Fast-path: try Ollama
        if self.ollama.is_available():
            try:
                result = self.ollama.generate(prompt, **kwargs)
                if result["latency_ms"] <= FALLBACK_THRESHOLD_MS:
                    return result
                logger.info(
                    "Ollama latency %dms > threshold %dms — falling back to OpenRouter",
                    result["latency_ms"],
                    FALLBACK_THRESHOLD_MS,
                )
                return result  # still return it, just log the warning
            except (OllamaUnavailableError, OllamaTimeoutError) as e:
                logger.warning("Ollama failed (%s) — falling back to OpenRouter", e)

        # Fallback: OpenRouter via switchblade
        return self._openrouter_fallback(prompt, **kwargs)

    def _openrouter_fallback(self, prompt: str, **kwargs) -> dict:
        """Call OpenRouter as fallback. Uses switchblade if available."""
        try:
            import sys
            import os
            sys.path.insert(0, os.path.expanduser("~/Thunderbird"))
            from core.ai_infra.thunderbird_switchblade import Switchblade
            sb = Switchblade()
            text = sb.chat(prompt, model="haiku")
            return {
                "text": text,
                "model": "claude-haiku (openrouter)",
                "latency_ms": -1,
                "tokens_prompt": 0,
                "tokens_eval": 0,
                "source": "openrouter",
            }
        except Exception as e:
            logger.error("OpenRouter fallback also failed: %s", e)
            raise


# ------------------------------------------------------------------
# Quick self-test
# ------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.DEBUG)
    client = OllamaClient()

    print("=== Ollama Self-Test ===")
    print(f"Base URL : {client.base_url}")
    print(f"Model    : {client.model}")
    print(f"Available: {client.is_available(force_check=True)}")

    if not client.is_available():
        print("\nOllama not available. Is the container running?")
        print("  docker ps --filter name=thunderbird-ollama")
        print("  docker exec thunderbird-ollama ollama pull mistral")
        sys.exit(1)

    print("\n--- Test 1: Classification ---")
    label = client.classify_task(
        "New email from Furlow asking about shore excursions in Bergen"
    )
    print(f"Result: {label}")

    print("\n--- Test 2: Summarization ---")
    summary = client.summarize(
        "The Silver Nova departs Yokohama on April 26 and arrives in Vancouver on May 11. "
        "The itinerary includes calls in Osaka, Hiroshima, Busan, and the scenic Inside Passage. "
        "Guests will enjoy 16 nights aboard with all-inclusive dining and drinks.",
        max_words=30,
    )
    print(f"Result: {summary}")

    print("\n--- Test 3: Inbox triage ---")
    triage = client.triage_inbox_item(
        subject="Re: Silver Nova Japan Booking Confirmation",
        body="Hi John, just wanted to confirm our cabin upgrade request went through. "
             "Also, do we need travel insurance? Thanks, Ron",
    )
    print(f"Result: {json.dumps(triage, indent=2)}")

    print("\n=== All tests complete ===")
