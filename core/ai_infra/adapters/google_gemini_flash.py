import logging
import time

from core.ai_infra.adapters.base import AdapterResult, HealthState

log = logging.getLogger("adapter.gemini_flash")

# Re-enabled 2026-06-05 — now routes through canonical gemini_client.py (A7 Sterling, 2026-06-01)
# Google AI Pro subscription active; direct API replaces OpenRouter free-tier routing.
# Old inline urllib.request logic retired — gemini_client enforces rate limits, Harlan logging,
# free-tier allowlist, and automatic retry. Never call the API directly from this adapter.

MODEL_ID = "gemini-2.5-flash"


class GeminiFlashAdapter:
    name = "google_gemini_flash"
    tier_capabilities = ["BULK"]
    cost_pool = "google_ai_pro"
    point_cost_estimate = 0.0

    def health_probe(self) -> tuple[HealthState, str]:
        try:
            from core.ai_infra.gemini_client import smoke_test
            result = smoke_test()
            if result["success"]:
                return ("GREEN", f"Direct API OK — {result['response_preview']}")
            return ("RED", f"Smoke test failed: {result['error']}")
        except Exception as exc:
            return ("RED", f"gemini_client import failed: {exc}")

    def dispatch(self, system: str, user: str, max_tokens: int = 4096) -> AdapterResult:
        t0 = time.monotonic()
        try:
            from core.ai_infra.gemini_client import call_gemini
            text = call_gemini(
                system_prompt=system,
                user_prompt=user,
                max_tokens=max_tokens,
                caller="adapter.gemini_flash",
                task_hint=user[:80],
            )
            elapsed = int((time.monotonic() - t0) * 1000)
            return AdapterResult(
                text=text, error=None,
                cost_consumed=0, cost_pool=self.cost_pool,
                latency_ms=elapsed, model_used=MODEL_ID,
            )
        except Exception as exc:
            elapsed = int((time.monotonic() - t0) * 1000)
            return AdapterResult(
                text=None, error=str(exc),
                cost_consumed=0, cost_pool=self.cost_pool,
                latency_ms=elapsed, model_used=MODEL_ID,
            )


adapter = GeminiFlashAdapter()
