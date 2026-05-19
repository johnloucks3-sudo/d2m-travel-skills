import logging
import os
import time

import requests

from core.ai_infra.adapters.base import AdapterResult, HealthState

log = logging.getLogger("adapter.openrouter_breakglass")

ENGINE_TIMEOUT = 120


class OpenRouterBreakglassAdapter:
    """OpenRouter direct API — break-glass only. Never in default chain.
    Only invocable via explicit --breakglass flag or Commander override."""

    name = "openrouter_breakglass"
    tier_capabilities = []
    cost_pool = "openrouter_credits"
    point_cost_estimate = 1.0

    def health_probe(self) -> tuple[HealthState, str]:
        key = os.environ.get("OPENROUTER_API_KEY", "")
        if not key:
            return ("RED", "OPENROUTER_API_KEY not set")
        return ("GREEN", "OpenRouter key present")

    def dispatch(self, system: str, user: str, max_tokens: int = 4096) -> AdapterResult:
        api_key = os.environ.get("OPENROUTER_API_KEY", "")
        if not api_key:
            return AdapterResult(
                text=None, error="OPENROUTER_API_KEY not set",
                cost_consumed=0, cost_pool=self.cost_pool,
                latency_ms=0, model_used="openrouter_breakglass",
            )

        messages = []
        if system:
            messages.append({"role": "system", "content": system[:3000]})
        messages.append({"role": "user", "content": user})

        t0 = time.monotonic()
        try:
            resp = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "X-Title": "Thunderbird Breakglass",
                },
                json={"model": "google/gemini-2.5-flash", "max_tokens": max_tokens, "messages": messages},
                timeout=ENGINE_TIMEOUT,
            )
            elapsed = int((time.monotonic() - t0) * 1000)

            if resp.status_code == 429:
                return AdapterResult(
                    text=None, error="OpenRouter rate-limited",
                    cost_consumed=0, cost_pool=self.cost_pool,
                    latency_ms=elapsed, model_used="openrouter_breakglass",
                )
            if resp.status_code == 402:
                return AdapterResult(
                    text=None, error="OpenRouter balance depleted",
                    cost_consumed=0, cost_pool=self.cost_pool,
                    latency_ms=elapsed, model_used="openrouter_breakglass",
                )
            resp.raise_for_status()
            choices = resp.json().get("choices", [])
            text = choices[0].get("message", {}).get("content", "").strip() if choices else ""
            if text:
                return AdapterResult(
                    text=text, error=None,
                    cost_consumed=0.001, cost_pool=self.cost_pool,
                    latency_ms=elapsed, model_used="openrouter_breakglass",
                )
            return AdapterResult(
                text=None, error="OpenRouter empty response",
                cost_consumed=0.001, cost_pool=self.cost_pool,
                latency_ms=elapsed, model_used="openrouter_breakglass",
            )
        except requests.Timeout:
            elapsed = int((time.monotonic() - t0) * 1000)
            return AdapterResult(
                text=None, error=f"OpenRouter timeout {ENGINE_TIMEOUT}s",
                cost_consumed=0, cost_pool=self.cost_pool,
                latency_ms=elapsed, model_used="openrouter_breakglass",
            )
        except Exception as e:
            elapsed = int((time.monotonic() - t0) * 1000)
            return AdapterResult(
                text=None, error=str(e),
                cost_consumed=0, cost_pool=self.cost_pool,
                latency_ms=elapsed, model_used="openrouter_breakglass",
            )


adapter = OpenRouterBreakglassAdapter()
