"""
core/relay/reconcile_oc.py — the OC-side follow-up sweep.

AG is checked inline, in the same call that dispatched it
(core.staffing.integrity_check.verify_and_record). OC is fire-and-forget
(core.relay.dispatch_oc.dispatch_to_oc), so nothing distinguishes "still
working" from "silently never picked up" until something goes looking. This
is that something — invoked from the evening consolidated brief build
(core/ops/evening_consolidated_eod_engine.py), no new daemon.

Verification uses Silver's deterministic back gate (core.silver.gate.run_gate)
against the OC ticket's own stored acceptance_criteria, not a second AG/CC
dispatch — the entire point of the OC lane is to be the cheap one; spending
an AG call to check every OC ticket would undercut that. Silver's battery is
free, instant, and already the Wing's standard "is this actually done"
check (same one certify_mission() runs).
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone


def _extract_criteria(description: str) -> str:
    """Pull the acceptance_criteria dispatch_to_oc folded into the board
    task's description back out. Falls back to the whole description if the
    marker is missing (defensive — a ticket queued by something other than
    dispatch_to_oc shouldn't crash reconciliation)."""
    marker = "\n\nAcceptance criteria: "
    idx = description.find(marker)
    if idx == -1:
        return description
    return description[idx + len(marker):]


def reconcile_due(sla_extension_hours: float = 1.0) -> list[dict]:
    """Sweep every outstanding async_poll ticket past its follow_up_due.
    One outcome row per ticket per pass: DROPPED (never claimed / vanished),
    STALLED (still claimed after one SLA extension), FAILED (OC reported
    failure), PASS/DISCREPANCY (complete — Silver-gated), or a fresh
    PENDING row extending the SLA once for a ticket still in flight."""
    from core.hale_bus.brain_bridge import BrainBridge
    from core.silver.gate import run_gate
    from core.staffing.delegation_outcomes import outstanding, record_outcome, page_commander

    bb = BrainBridge()
    results = []

    for row in outstanding("async_poll", older_than_hours=0):
        tid = row["ticket_id"]
        task_type = row.get("task_type", "")
        task = bb.get(tid)

        if task is None:
            rec = record_outcome(
                seat="OC", action="reconciliation", verdict="DROPPED",
                ticket_id=tid, task_type=task_type, dispatch_mode="async_poll",
                discrepancy_detail="ticket no longer exists on the brain_bridge board",
                reconciled=True,
            )
            page_commander(
                problem=f"OC ticket DROPPED — {tid}",
                discussion="No longer on the brain_bridge board — a reset, or it was never actually queued.",
                action="No OC output exists to certify.",
                next_steps="Re-dispatch via dispatch_to_oc if the work still needs doing.",
            )
            results.append(rec)
            continue

        status = task.get("status")

        if status == "complete":
            criteria = _extract_criteria(task.get("description", ""))
            verdict_obj = run_gate(task.get("result") or "", criteria, mission_id=tid)
            verdict = "PASS" if verdict_obj.ok else "DISCREPANCY"
            rec = record_outcome(
                seat="OC", action="reconciliation", verdict=verdict,
                ticket_id=tid, task_type=task_type, dispatch_mode="async_poll",
                certified_by="CC",
                discrepancy_detail="; ".join(verdict_obj.holds)[:300],
                reconciled=True,
            )
            if verdict == "DISCREPANCY":
                page_commander(
                    problem=f"OC ticket DISCREPANCY — {tid}: {task.get('title', '')[:80]}",
                    discussion="; ".join(verdict_obj.holds)[:300],
                    action="Silver back-gate held the OC result against its own stated acceptance criteria.",
                    next_steps="Review before treating this as done.",
                )
            results.append(rec)
            continue

        if status == "claimed":
            already_extended = (row.get("discrepancy_detail") or "").startswith("SLA extended")
            if already_extended:
                rec = record_outcome(
                    seat="OC", action="reconciliation", verdict="STALLED",
                    ticket_id=tid, task_type=task_type, dispatch_mode="async_poll",
                    discrepancy_detail="still claimed after SLA + one extension",
                    reconciled=True,
                )
                page_commander(
                    problem=f"OC ticket STALLED — {tid}: {task.get('title', '')[:80]}",
                    discussion="Claimed but never completed, even after one SLA extension.",
                    action="oc_worker.py may be stuck or crash-looped on this task.",
                    next_steps="Check systemctl --user status opencode-worker.service.",
                )
            else:
                new_due = (datetime.now(timezone.utc) + timedelta(hours=sla_extension_hours)).isoformat()
                rec = record_outcome(
                    seat="OC", action="delegated", verdict="PENDING",
                    ticket_id=tid, task_type=task_type, dispatch_mode="async_poll",
                    follow_up_due=new_due,
                    discrepancy_detail="SLA extended once (still claimed)",
                )
            results.append(rec)
            continue

        if status == "pending":
            rec = record_outcome(
                seat="OC", action="reconciliation", verdict="DROPPED",
                ticket_id=tid, task_type=task_type, dispatch_mode="async_poll",
                discrepancy_detail="never claimed — sat pending past SLA",
                reconciled=True,
            )
            page_commander(
                problem=f"OC ticket never claimed — {tid}: {task.get('title', '')[:80]}",
                discussion="Sat pending past its SLA without any worker claiming it.",
                action="No OC output exists to certify.",
                next_steps="Check systemctl --user status opencode-worker.service — worker may be down.",
            )
            results.append(rec)
            continue

        if status == "failed":
            rec = record_outcome(
                seat="OC", action="reconciliation", verdict="FAILED",
                ticket_id=tid, task_type=task_type, dispatch_mode="async_poll",
                discrepancy_detail=f"OC reported failure: {(task.get('result') or '')[:200]}",
                reconciled=True,
            )
            page_commander(
                problem=f"OC ticket FAILED — {tid}: {task.get('title', '')[:80]}",
                discussion=(task.get("result") or "")[:200],
                action="oc_worker.py marked this failed and returned it to the board.",
                next_steps="Review the failure reason; re-dispatch if still needed.",
            )
            results.append(rec)
            continue

    return results
