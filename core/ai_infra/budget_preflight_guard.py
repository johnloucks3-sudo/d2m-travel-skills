"""
budget_preflight_guard.py — REAL read, honest degrade (re-enabled 2026-07-16).

History: disabled 2026-05-23 ("20X Claude MAX = unlimited") as a hardcoded
always-PASS stub — a check that never ran but claimed it did. Re-enabled per
the cross-Hale coordination directive: reads the per-seat budget state
(core/ai_infra/seat_budget.py). Policy unchanged in spirit — never block on
unknowns — but the verdict now says WHAT it actually knew:
  PASS     — fresh data, CC weekly < DEGRADE_PCT
  DEGRADE  — fresh data, CC weekly ≥ DEGRADE_PCT → hint the off-MAX lanes
  PASS + stale reason — data missing/stale; degrade-to-PASS is logged, not silent
"""
import logging
import time
from dataclasses import dataclass, field
from enum import Enum

log = logging.getLogger("budget_preflight_guard")

DEGRADE_PCT = 90.0


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
    reason: str = ""

    @property
    def ok(self) -> bool:
        return self.verdict != GuardVerdict.BLOCK

    @property
    def should_degrade(self) -> bool:
        return self.verdict == GuardVerdict.DEGRADE


def run_preflight() -> PreFlightResult:
    """Read CC's real budget state. Never blocks; degrades honestly."""
    try:
        from core.ai_infra.seat_budget import seat_status
        s = seat_status("CC")
    except Exception as e:
        log.warning("preflight degraded to PASS — seat_budget unreadable: %s", e)
        return PreFlightResult(GuardVerdict.PASS, checked_at=time.time(),
                               reason=f"no data ({e}) — degraded to PASS, logged")
    if s["weekly_pct"] is None or s["stale"]:
        log.warning("preflight degraded to PASS — CC budget data %s (age=%sh)",
                    "missing" if s["weekly_pct"] is None else "STALE", s["age_hours"])
        return PreFlightResult(
            GuardVerdict.PASS, checked_at=time.time(),
            reason=f"CC data {'missing' if s['weekly_pct'] is None else 'stale'} "
                   f"(age={s['age_hours']}h) — degraded to PASS, logged")
    pool = PoolSnapshot("claude_max_cc", s["weekly_pct"], 100.0,
                        100.0 - s["weekly_pct"],
                        GuardVerdict.DEGRADE if s["weekly_pct"] >= DEGRADE_PCT
                        else GuardVerdict.PASS)
    if pool.verdict == GuardVerdict.DEGRADE:
        return PreFlightResult(
            GuardVerdict.DEGRADE, pools=[pool],
            degraded_model_hint="route claude_optional→AG (Gemini), mechanical→OC (DeepSeek v4)",
            checked_at=time.time(),
            reason=f"CC weekly at {s['weekly_pct']}% (≥{DEGRADE_PCT}%)")
    return PreFlightResult(GuardVerdict.PASS, pools=[pool], checked_at=time.time(),
                           reason=f"CC weekly at {s['weekly_pct']}% (fresh)")


# Preserved for import compatibility (Harlan/Commander report files retired 2026-05-23)
def read_harlan_verdict() -> dict | None:
    return None


def read_commander_report() -> dict | None:
    return None


def invalidate_claude_cache():
    pass


if __name__ == "__main__":
    r = run_preflight()
    print(f"Verdict: {r.verdict.value} — {r.reason}")
