import logging

from core.ai_infra.adapters.base import AdapterResult, HealthState

log = logging.getLogger("adapter.bigpickle")

# DISABLED 2026-06-20 — opencode/big-pickle model is unavailable/hanging.
# Dispatcher routes to anthropic/claude-haiku-4-5-20251001 instead.
MODEL_ID = "opencode/big-pickle"


class BigPickleAdapter:
    name = "opencode_bigpickle"
    tier_capabilities = ["BULK", "MID"]
    cost_pool = "opencode_native"
    point_cost_estimate = 0.0

    def health_probe(self) -> tuple[HealthState, str]:
        return ("RED", "opencode/big-pickle disabled — model unavailable")

    def dispatch(self, system: str, user: str, max_tokens: int = 4096) -> AdapterResult:
        return AdapterResult(
            text=None,
            error="opencode/big-pickle is disabled — use anthropic/claude-haiku-4-5-20251001",
            cost_consumed=0, cost_pool=self.cost_pool,
            latency_ms=0, model_used=MODEL_ID,
        )


adapter = BigPickleAdapter()
