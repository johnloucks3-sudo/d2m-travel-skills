"""
Cross-Hale Task Delegation — LIVE wiring onto the C2 Fabric bus.

Design: docs/CROSS_HALE_TASK_DELEGATION_DESIGN_20260716.md (§3.2-3.6)
Phase:  Phase 1 rollout (design §4) — takes the Phase-0 routing/schema library
        (core/relay/task_delegation.py) live by binding it to three already-live
        primitives:
          - route_task()          — routing/rationale validation (task_delegation)
          - relay_handoff()        — CC↔OC↔AG notification (core/relay/wing_relay, PROTECTED, imported read-only)
          - record_channel_event() — bus lifecycle mirror (core/hale_bus/c2_fabric_write)

This module is the missing wire between mission-board assignment and the bus.
When a mission is assigned to a real cross-Hale seat (CC/OC/AG), delegate_mission()
validates the routing rationale, notifies the target seat, and mirrors the ticket
lifecycle stage onto the unified bus (console channel, filterable by ref=mission_id).

Anti-theater (§3.5): a delegated ticket cannot reach `done` without a
verification_artifact certified by a seat OTHER than assigned_to. certify_mission()
RAISES DelegationError on self-certification or a missing artifact.

Not a protected file (see core/policy/rules_registry.py). Imports wing_relay
read-only; never edits it.
"""
from __future__ import annotations

from typing import Optional

from core.relay.task_delegation import CC, OC, AG, SEATS, route_task
from core.hale_bus.c2_fabric_write import record_channel_event
from core.silver.gate import silver_front_frame, run_gate

# wing_relay is a PROTECTED file — imported read-only, never modified.
from core.relay.wing_relay import relay_handoff, relay_ack

# All delegation lifecycle events mirror onto the "console" channel so a reader
# can reconstruct one ticket's whole lifecycle with
# get_channel_activity(channel="console") filtered on ref=mission_id.
BUS_CHANNEL = "console"

LIFECYCLE_STAGES = (
    "proposed", "assigned", "in_progress", "pending_review", "done", "blocked",
)


class DelegationError(Exception):
    """Raised when a delegation invariant is violated (anti-theater §3.5)."""


def mirror_stage_to_bus(
    mission_id: str,
    stage: str,
    detail: str,
    *,
    confirmed_delivered: bool = False,
) -> dict:
    """Mirror one ticket lifecycle transition onto the C2 Fabric bus.

    ref=mission_id ties every event for a ticket together; event_type carries
    the stage so a reader filtering the console channel reconstructs the full
    proposed→…→done/blocked trail. Returns the written bus entry."""
    if stage not in LIFECYCLE_STAGES:
        raise DelegationError(f"stage must be one of {LIFECYCLE_STAGES}, got {stage!r}")
    return record_channel_event(
        BUS_CHANNEL,
        f"delegation_{stage}",
        detail,
        ref=mission_id,
        confirmed_delivered=confirmed_delivered,
    )


def _notify_handoff(
    from_seat: str,
    to_seat: str,
    title: str,
    mission_id: str,
    acceptance_criteria: str,
    rationale: str,
) -> Optional[int]:
    """Best-effort seat notification via the existing relay primitive. Returns
    the Telegram message_id, or None if the relay is unavailable (no token /
    network) — a missing notification never blocks the durable field write."""
    try:
        return relay_handoff(
            from_seat, to_seat, title,
            detail=f"{mission_id} | crit: {acceptance_criteria} | why: {rationale}",
        )
    except Exception:
        return None


def _resolve_rationale(seat: str, task_type: Optional[str], route_kwargs: dict) -> str:
    """Honest rationale for a directly-assigned seat.

    `assigned_to` is already a chosen seat, so route_task() is used to VALIDATE
    that choice, not to manufacture it (§3.5 forbids back-filled theater):
      - no routing hint       → "direct assignment" (stated plainly as such)
      - hint agrees with seat → the routing rationale, marked validated
      - hint disagrees        → an explicit OVERRIDE note naming both seats
    """
    if not task_type:
        return f"direct assignment to {seat} (no routing hint provided)"
    decision = route_task(task_type, **route_kwargs)
    if decision.seat == seat:
        return f"routing validated ({seat}): {decision.rationale}"
    return (
        f"DIRECT OVERRIDE — assigned {seat}, but route_task recommends "
        f"{decision.seat} ({decision.rationale})"
    )


def delegate_mission(
    mission: dict,
    *,
    from_seat: str = CC,
    task_type: Optional[str] = None,
    **route_kwargs,
) -> dict:
    """Take a seat-assigned mission dict live on the bus (the assignment entry
    point wired into mission_board_sync.add_mission).

    Requires (design §3.5.1): assigned_to ∈ SEATS, a non-empty
    acceptance_criteria, and a certified_by that DIFFERS from assigned_to.
    Side effects, in order: stamp delegation_rationale, notify the target seat
    (best-effort), mirror the `assigned` stage onto the bus. Mutates and returns
    the mission dict."""
    seat = mission.get("assigned_to")
    if seat not in SEATS:
        raise DelegationError(
            f"delegate_mission requires assigned_to in {SEATS}, got {seat!r}"
        )

    acceptance_criteria = (mission.get("acceptance_criteria") or "").strip()
    if not acceptance_criteria:
        raise DelegationError(
            "delegating to a seat requires acceptance_criteria — no criteria, no delegation (§3.5.1)"
        )

    certified_by = (mission.get("certified_by") or CC).strip()
    if certified_by == seat:
        raise DelegationError(
            f"self-certification forbidden — certified_by ({certified_by}) "
            f"must differ from assigned_to ({seat}) (§3.5.3)"
        )
    mission["certified_by"] = certified_by
    mission.setdefault("verification_artifact", "")

    # Silver FRONT frame — MANDATORY (Commander directive 2026-07-16): no
    # concrete, second-seat-verifiable "done" frame, no ticket.
    frame = silver_front_frame(
        mission.get("id", "MISSION-?"),
        mission.get("title", ""),
        acceptance_criteria,
        mission.get("ground_truth_sources") or [],
    )
    if not frame.ok:
        raise DelegationError(
            "CHIEF SILVER front-frame HOLD — " + "; ".join(frame.holds)
        )
    mission["silver_front_frame"] = frame.ts

    rationale = _resolve_rationale(seat, task_type, route_kwargs)
    mission["delegation_rationale"] = rationale

    mission_id = mission.get("id", "MISSION-?")
    _notify_handoff(
        from_seat, seat, mission.get("title", ""),
        mission_id, acceptance_criteria, rationale,
    )
    mirror_stage_to_bus(
        mission_id, "assigned",
        f"{seat} ← {mission.get('title', '')[:80]} | crit: {acceptance_criteria[:80]}",
    )
    return mission


def ack_receipt(seat: str, mission_id: str, detail: str = "") -> dict:
    """Seat acknowledges receipt and starts work: relay ACK (best-effort) +
    mirror the `in_progress` stage onto the bus (§3.4)."""
    try:
        relay_ack(seat, mission_id, "received")
    except Exception:
        pass
    return mirror_stage_to_bus(mission_id, "in_progress", detail or f"{seat} acked {mission_id}")


def submit_for_review(mission_id: str, seat: str, verification_artifact: str) -> dict:
    """Assignee submits a verification artifact and moves to pending_review (§3.4,
    PDTAC A). The artifact CONTENT is validated by the certifier, not here."""
    if not verification_artifact.strip():
        raise DelegationError("submit_for_review requires a non-empty verification_artifact")
    return mirror_stage_to_bus(
        mission_id, "pending_review",
        f"{seat} submitted artifact: {verification_artifact[:120]}",
    )


def certify_mission(
    mission_id: str,
    assigned_to: str,
    certified_by: str,
    verification_artifact: str,
    acceptance_criteria: str,
) -> dict:
    """Certifier closes a delegated ticket (§3.4 PDTAC C, §3.5 anti-theater).

    RAISES DelegationError (item 5: raises/rejects) when:
      - certified_by == assigned_to        → self-certification forbidden (§3.5.3)
      - verification_artifact is empty      → no machine-checkable artifact (§3.5.2)
      - acceptance_criteria is empty        → nothing to validate against (§3.5.1)
      - Silver BACK gate returns HOLD       → content check failed (mandatory 2026-07-16)

    On success, mirrors the `done` stage onto the bus and returns the bus entry."""
    if certified_by == assigned_to:
        raise DelegationError(
            f"self-certification forbidden — certifier ({certified_by}) "
            f"must differ from assignee ({assigned_to}) (§3.5.3)"
        )
    if not verification_artifact.strip():
        raise DelegationError("no verification_artifact — cannot certify done (§3.5.2)")
    if not acceptance_criteria.strip():
        raise DelegationError("no acceptance_criteria — nothing to validate against (§3.5.1)")

    # Silver BACK gate — MANDATORY (Commander directive 2026-07-16): the
    # deterministic battery runs against the actual artifact; HOLD blocks close.
    v = run_gate(verification_artifact, acceptance_criteria, mission_id=mission_id)
    if not v.ok:
        raise DelegationError("CHIEF SILVER back-gate HOLD — " + "; ".join(v.holds))

    return mirror_stage_to_bus(
        mission_id, "done",
        f"{assigned_to} work certified by {certified_by} | artifact: {verification_artifact[:120]}",
        confirmed_delivered=True,
    )


def block_mission(mission_id: str, seat: str, reason: str) -> dict:
    """Mirror the `blocked` stage onto the bus (§3.5.5 watchdog / escalation)."""
    return mirror_stage_to_bus(mission_id, "blocked", f"{seat} blocked: {reason}")
