"""core/relay/delegation.py — single import surface for cross-engine delegation.

W6 consolidation (RT-EFFICACY, 2026-08-08): task_delegation (routing/schema),
delegation_wiring (live bus lifecycle), and delegation_preflight (soft hints)
previously had to be imported as three separate modules; routing rationale and
seat constants were re-declared across them. This facade re-exports the public
API of all three under ONE import path, and adds the single end-to-end entry
`delegate_task()` that binds preflight -> routing -> ticket -> live wiring, so
callers (mission_board_sync, staff_summary_sheet, tests) can import one place.

Backward compatible: the three underlying modules are untouched and remain
importable for any caller that references them directly. No code was deleted;
this is consolidation by import-path unification, not deletion.
"""
from __future__ import annotations

from typing import Optional

# ── task_delegation (routing + ticket schema) ───────────────────────────
from core.relay.task_delegation import (
    CC, OC, AG, SEATS,
    RouteDecision, route_task,
    DelegationTicket, build_delegation_ticket,
)
# ── delegation_wiring (live bus lifecycle) ───────────────────────────────
from core.relay.delegation_wiring import (
    DelegationError, BUS_CHANNEL, LIFECYCLE_STAGES,
    mirror_stage_to_bus, delegate_mission,
    ack_receipt, submit_for_review,
    certify_mission, certify_mission_and_record, block_mission,
)
# ── delegation_preflight (soft hints — never-blocks) ───────────────────────
from core.relay.delegation_preflight import (
    PreflightVerdict, PreflightResult,
    check_before_self_execute, check_before_self_execute_with_team,
    check_team_assembly, check_cross_wing_hail, check_team_assembly_hard,
)

# The duplicate handoff helper lived in BOTH task_delegation and
# delegation_wiring's private _notify_handoff. Canonical one is here now.
def notify_handoff(from_seat: str, to_seat: str, title: str,
                   mission_id: str, acceptance_criteria: str, rationale: str) -> Optional[int]:
    """Best-effort seat notification via the existing relay. Returns the
    Telegram message_id, or None when the relay is unavailable — a missing
    notification never blocks the durable field write. (W6: single definition.)"""
    try:
        from core.relay.wing_relay import relay_handoff
        return relay_handoff(
            from_seat, to_seat, title,
            detail=f"{mission_id} | crit: {acceptance_criteria} | why: {rationale}",
        )
    except Exception:
        return None


def delegate_task(
    mission: dict,
    *,
    from_seat: str = OC,
    task_type: Optional[str] = None,
    **route_kwargs,
) -> dict:
    """The single front-door for cross-Hale delegation: preflight hint ->
    route (budget-aware) -> live wiring (bus mirror + anti-theater gate).

    Returns the mission dict (mutated: rationale stamped, bus mirror fired).
    Raises DelegationError on anti-theater violations (self-cert, no criteria,
    Silver front-frame HOLD) — same invariants as delegate_mission, exposed
    behind one entry point."""
    check_before_self_execute_with_team(task_type or "", **route_kwargs)
    return delegate_mission(mission, from_seat=from_seat, task_type=task_type,
                            **route_kwargs)


__all__ = [
    "CC", "OC", "AG", "SEATS",
    "RouteDecision", "route_task", "DelegationTicket", "build_delegation_ticket",
    "DelegationError", "BUS_CHANNEL", "LIFECYCLE_STAGES",
    "mirror_stage_to_bus", "delegate_mission", "ack_receipt", "submit_for_review",
    "certify_mission", "certify_mission_and_record", "block_mission",
    "PreflightVerdict", "PreflightResult",
    "check_before_self_execute", "check_before_self_execute_with_team",
    "check_team_assembly", "check_cross_wing_hail", "check_team_assembly_hard",
    "notify_handoff", "delegate_task",
]