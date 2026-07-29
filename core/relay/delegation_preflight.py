"""
core/relay/delegation_preflight.py — soft delegation hint before CC self-executes.

Commander directive 2026-07-29: delegation is soft guidance, not a ceiling —
CC defaults to delegating but keeps judgment to self-execute high-stakes work
even near the budget line. Modeled directly on core/ai_infra/
budget_preflight_guard.py's proven never-block/degrade/log-honestly shape
(same file re-enabled 2026-07-16 specifically because its predecessor was a
hardcoded always-PASS stub — a check that never ran but claimed it did).
This module never returns anything CC is forced to obey; it returns a hint,
and accountability is retrospective via
core.staffing.delegation_outcomes.rollup_stats()'s self_execute_unjustified
counter — visible in the daily brief, never a blocked tool call.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class PreflightVerdict(str, Enum):
    PROCEED = "PROCEED"    # route_task recommends CC, or no hint available
    DEGRADE = "DEGRADE"    # route_task recommends OC/AG; CC should log a rationale if overriding


@dataclass
class PreflightResult:
    verdict: PreflightVerdict
    recommended_seat: str = "CC"
    rationale: str = ""
    hint: str = ""

    @property
    def should_delegate(self) -> bool:
        return self.verdict == PreflightVerdict.DEGRADE


def check_before_self_execute(task_type: str, **route_kwargs) -> PreflightResult:
    """Call before a non-trivial self-execute. Never blocks — if route_task()
    recommends OC/AG, returns DEGRADE with a hint; CC is expected (CLAUDE.md
    standing order) to log self_execute_rationale via record_outcome() if it
    proceeds anyway. Degrades to PROCEED, logged not silent, if routing
    itself is unavailable."""
    import logging
    log = logging.getLogger("delegation_preflight")
    try:
        from core.relay.task_delegation import route_task, CC
    except Exception as e:
        log.warning("preflight degraded to PROCEED — task_delegation unavailable: %s", e)
        return PreflightResult(PreflightVerdict.PROCEED, hint=f"routing unavailable ({e})")

    decision = route_task(task_type, **route_kwargs)
    if decision.seat == CC:
        return PreflightResult(PreflightVerdict.PROCEED, recommended_seat=CC,
                               rationale=decision.rationale)
    return PreflightResult(
        PreflightVerdict.DEGRADE, recommended_seat=decision.seat, rationale=decision.rationale,
        hint=f"route_task recommends {decision.seat} ({decision.rationale}) — "
             f"log self_execute_rationale via delegation_outcomes.record_outcome if proceeding on CC anyway",
    )
