"""
budget_preflight_guard.py — DISABLED. 20X Claude MAX = unlimited, $0.
All non-Claude paths removed per Commander SO 2026-05-23.
"""
import logging
import time
from dataclasses import dataclass, field
from enum import Enum

log = logging.getLogger("budget_preflight_guard")


class GuardVerdict(str, Enum):
    PASS = "PASS"
    DEGRADE = "DEGRADE"
    BLOCK = "BLOCK"


@dataclass
class PoolSnapshot:
    pool: str
    pct_used: float
    limit: float
    remaining: float
    verdict: GuardVerdict
    reason: str = ""


@dataclass
class PreFlightResult:
    verdict: GuardVerdict
    pools: list[PoolSnapshot] = field(default_factory=list)
    degraded_model_hint: str = ""
    checked_at: float = 0.0

    @property
    def ok(self) -> bool:
        return True

    @property
    def should_degrade(self) -> bool:
        return False


def run_preflight() -> PreFlightResult:
    return PreFlightResult(
        verdict=GuardVerdict.PASS,
        checked_at=time.time(),
    )


# Stubs — preserved for import compatibility, always return PASS
def read_harlan_verdict() -> dict | None:
    return None


def read_commander_report() -> dict | None:
    return None


def invalidate_claude_cache():
    pass


if __name__ == "__main__":
    result = run_preflight()
    print(f"Verdict: {result.verdict.value} — Budget guard DISABLED (20X Claude MAX unlimited)")
