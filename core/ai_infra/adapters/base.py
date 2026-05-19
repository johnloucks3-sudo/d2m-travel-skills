from typing import Protocol, Literal, runtime_checkable
from dataclasses import dataclass

HealthState = Literal["GREEN", "YELLOW", "RED"]


@dataclass
class AdapterResult:
    text: str | None
    error: str | None
    cost_consumed: float
    cost_pool: str
    latency_ms: int
    model_used: str

    @property
    def ok(self) -> bool:
        return self.text is not None and self.error is None and len(self.text.strip()) > 0


@runtime_checkable
class Adapter(Protocol):
    name: str
    tier_capabilities: list[str]
    cost_pool: str
    point_cost_estimate: float

    def health_probe(self) -> tuple[HealthState, str]:
        ...

    def dispatch(self, system: str, user: str, max_tokens: int = 4096) -> AdapterResult:
        ...
