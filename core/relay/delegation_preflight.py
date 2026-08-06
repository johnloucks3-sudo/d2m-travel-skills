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


def check_before_self_execute_with_team(task_type: str, **route_kwargs) -> PreflightResult:
    """Composed preflight: seat routing + team assembly (AG gate) + cross-wing
    hail (Grok gate). Runs the team gates FIRST (they're the standing doctrine),
    then the seat-route check. Returns the most severe verdict. Never blocks —
    soft hints only, matching module doctrine."""
    team = check_team_assembly(task_type, **route_kwargs)
    hail = check_cross_wing_hail(task_type, **route_kwargs)
    route = check_before_self_execute(task_type, **route_kwargs)
    # team gates degrade harder than seat routing
    if team.verdict == PreflightVerdict.DEGRADE:
        return team
    if hail.verdict == PreflightVerdict.DEGRADE:
        return hail
    return route


# ── Team-assembly gates (Commander doctrine 2026-08-06: NO MODEL GOES IT ALONE) ──
# AG proposal (SSS-CB7A044E): check_team_assembly — block single-engine execution
# on multi-role operations. Grok proposal: 30s cross-wing hail on task intake to
# surface dependencies before planning. Both implemented as SOFT-HINT gates,
# never hard blocks, matching this module's never-block/log-honestly doctrine.

MULTI_ROLE_HINTS = (
    "team", "multi", "cross", "wing", "hale", "ato", "tasking", "staff",
    "coordinat", "delegat", "collaborat", "joint", "exercise",
)


def _is_multi_role(task_type: str, route_kwargs: dict) -> bool:
    """Heuristic: multi-role tasks usually name teams or coordination in the
    task_type string or kwargs (description, scope, category, purpose)."""
    hay = " ".join([task_type, str(route_kwargs.get("description", "")),
                    str(route_kwargs.get("scope", "")), str(route_kwargs.get("category", "")),
                    str(route_kwargs.get("purpose", ""))]).lower()
    return any(h in hay for h in MULTI_ROLE_HINTS)


def check_team_assembly(task_type: str, **route_kwargs) -> PreflightResult:
    """AG's gate (SSS-CB7A044E, adopted by Commander 2026-08-06): multi-role
    operations should not run single-engine. Returns DEGRADE + a hail hint when
    the task looks multi-role, so the orchestrator assembles the team BEFORE
    codegen — not after a UI/execution wall. Soft hint, never blocks."""
    if not _is_multi_role(task_type, route_kwargs):
        return PreflightResult(PreflightVerdict.PROCEED, recommended_seat="team",
                               rationale="single-role task — no team assembly required")
    return PreflightResult(
        PreflightVerdict.DEGRADE, recommended_seat="team",
        rationale="multi-role task detected — assemble the team before executing",
        hint="NO MODEL GOES IT ALONE (Commander 2026-08-06). This looks multi-role: "
             "run the cross-Hale hail (contact AG/Grok/CC) before codegen. "
             "See docs/MULTI_HALE_TEAM_CALL_PLAYBOOK.md",
    )


def check_cross_wing_hail(task_type: str, **route_kwargs) -> PreflightResult:
    """Grok's gate (SSS-CB7A044E, adopted 2026-08-06): 30-second cross-wing hail
    on task intake to surface dependencies before any planning begins. Soft hint:
    returns DEGRADE with a hail reminder for multi-role / dependency-prone tasks."""
    if not _is_multi_role(task_type, route_kwargs):
        return PreflightResult(PreflightVerdict.PROCEED, recommended_seat="team",
                               rationale="no cross-wing dependencies evident")
    return PreflightResult(
        PreflightVerdict.DEGRADE, recommended_seat="team",
        rationale="cross-wing dependencies possible — hail the wings before planning",
        hint="30-second cross-wing hail (Grok proposal, Commander-adopted): surface "
             "dependencies/team involvement BEFORE planning begins. One line to the "
             "relevant wing/seat, then proceed.",
    )


def check_team_assembly_hard(task_type: str, **route_kwargs) -> bool:
    """Hard variant for caller's explicit opt-in (e.g. before a big build).
    Returns True if team assembly is REQUIRED (multi-role) — the caller decides
    whether to treat it as a gate. Kept separate so default stays soft."""
    return _is_multi_role(task_type, route_kwargs)
