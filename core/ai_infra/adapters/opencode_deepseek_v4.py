import logging

from core.ai_infra.adapters.base import AdapterResult, HealthState

log = logging.getLogger("adapter.deepseek")

# DISABLED 2026-06-20 — opencode/deepseek-v4-flash-free model is unavailable/failing.
# Dispatcher routes to anthropic/claude-haiku-4-5-20251001 instead.
MODEL_ID = "opencode/deepseek-v4-flash-free"


class DeepSeekV4Adapter:
    name = "deepseek_v4"
    tier_capabilities = ["ARB"]
    cost_pool = "opencode_native"
    point_cost_estimate = 0.0

    def __init__(self):
        self._cumulative_cost = 0.0

    def health_probe(self) -> tuple[HealthState, str]:
        return ("RED", "opencode/deepseek-v4-flash-free disabled — model unavailable")

    def dispatch(self, system: str, user: str, max_tokens: int = 4096) -> AdapterResult:
        return AdapterResult(
            text=None,
            error="opencode/deepseek-v4-flash-free is disabled — use anthropic/claude-haiku-4-5-20251001",
            cost_consumed=0, cost_pool=self.cost_pool,
            latency_ms=0, model_used=MODEL_ID,
        )


adapter = DeepSeekV4Adapter()
