import logging
import os
import time

import requests

from core.ai_infra.adapters.base import AdapterResult, HealthState

log = logging.getLogger("adapter.poe")

ENGINE_TIMEOUT = 120


class PoePolyglotAdapter:
    """Poe API adapter — cheap-model whitelist only. Never burn premium points."""

    def __init__(self, name: str, model: str, tier_capabilities: list[str],
                 point_cost_estimate: float = 100.0):
        self.name = name
        self.model = model
        self.tier_capabilities = tier_capabilities
        self.point_cost_estimate = point_cost_estimate
        self.cost_pool = "poe_points"

    def health_probe(self) -> tuple[HealthState, str]:
        key = os.environ.get("POE_API_KEY", "")
        if not key:
            return ("RED", "POE_API_KEY not set")
        return ("GREEN", "Poe API key present")

    def dispatch(self, system: str, user: str, max_tokens: int = 4096) -> AdapterResult:
        api_key = os.environ.get("POE_API_KEY", "")
        if not api_key:
            return AdapterResult(
                text=None, error="POE_API_KEY not set",
                cost_consumed=0, cost_pool=self.cost_pool,
                latency_ms=0, model_used=self.model,
            )
        base = os.environ.get("POE_BASE_URL", "https://api.poe.com")
        messages = []
        if system:
            messages.append({"role": "system", "content": system[:3000]})
        messages.append({"role": "user", "content": user})

        t0 = time.monotonic()
        try:
            resp = requests.post(
                f"{base}/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": self.model, "max_tokens": max_tokens, "messages": messages},
                timeout=ENGINE_TIMEOUT,
            )
            elapsed = int((time.monotonic() - t0) * 1000)
            if resp.status_code == 429:
                return AdapterResult(
                    text=None, error=f"Poe rate-limited on {self.model}",
                    cost_consumed=0, cost_pool=self.cost_pool,
                    latency_ms=elapsed, model_used=self.model,
                )
            if resp.status_code == 402:
                return AdapterResult(
                    text=None, error="Poe out of points",
                    cost_consumed=0, cost_pool=self.cost_pool,
                    latency_ms=elapsed, model_used=self.model,
                )
            resp.raise_for_status()
            choices = resp.json().get("choices", [])
            text = choices[0].get("message", {}).get("content", "").strip() if choices else ""
            if text:
                return AdapterResult(
                    text=text, error=None,
                    cost_consumed=self.point_cost_estimate, cost_pool=self.cost_pool,
                    latency_ms=elapsed, model_used=self.model,
                )
            return AdapterResult(
                text=None, error=f"Poe {self.model} empty response",
                cost_consumed=self.point_cost_estimate, cost_pool=self.cost_pool,
                latency_ms=elapsed, model_used=self.model,
            )
        except requests.Timeout:
            elapsed = int((time.monotonic() - t0) * 1000)
            return AdapterResult(
                text=None, error=f"Poe {self.model} timeout",
                cost_consumed=0, cost_pool=self.cost_pool,
                latency_ms=elapsed, model_used=self.model,
            )
        except Exception as e:
            elapsed = int((time.monotonic() - t0) * 1000)
            return AdapterResult(
                text=None, error=str(e),
                cost_consumed=0, cost_pool=self.cost_pool,
                latency_ms=elapsed, model_used=self.model,
            )


gemini_flash_adapter = PoePolyglotAdapter(
    name="poe_gemini_flash",
    model="Gemini-2.5-Flash",
    tier_capabilities=["BULK"],
    point_cost_estimate=100.0,
)
kimi_k2_adapter = PoePolyglotAdapter(
    name="poe_kimi_k2",
    model="Kimi-K2",
    tier_capabilities=["MID", "ARB"],
    point_cost_estimate=400.0,
)
