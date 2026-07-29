"""
core/relay/dispatch_oc.py — OC's async half of the delegation ledger.

Ground truth (2026-07-29 audit): scripts/opencode_worker.py is dead code — it
imports `from brain_bridge import Board`, a module that does not exist at
repo root (verified: ImportError). The REAL, live OC worker is
scripts/oc_worker.py (systemd unit opencode-worker.service, confirmed
active), which polls core.hale_bus.brain_bridge.BrainBridge for lane="oc"
tasks every 15s and dispatches each to headless Claude Haiku via
OpsCenter/dispatch_claude.py — cheap, off the Sonnet/Opus meter, not
literally the OpenCode/DeepSeek CLI despite the "OC" name. This module wraps
that real board, not the dead one.

AG (core/relay/contact_ag.py) is synchronous — dispatch and verify happen in
one call. OC has no synchronous equivalent: dispatch_to_oc() only queues the
work and records a "delegated"/PENDING row with a follow-up deadline;
reconcile_oc.reconcile_due() is what actually checks in on it later. This
split is why the ledger's dispatch_mode field exists at all.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional


def dispatch_to_oc(
    task: str,
    *,
    acceptance_criteria: str,
    ticket_id: Optional[str] = None,
    task_type: str = "",
    priority: str = "P1",
    sla_hours: float = 1.0,
) -> dict:
    """Queue a task on the OC lane and record it as outstanding. No change
    to scripts/oc_worker.py's poll loop — this only writes to the same
    brain_bridge board it already claims from.

    sla_hours defaults to 1 (not the 4 in the original design draft) —
    ground-truthed against oc_worker.py's real behavior: 15s poll interval,
    300s per-task timeout, so a healthy claim-to-complete cycle is minutes,
    not hours. 1h is a real "something's wrong" signal, not a guess.

    acceptance_criteria is folded into the board task's description (no
    schema change to brain_bridge itself) and re-extracted by
    reconcile_oc.reconcile_due() for the Silver back-gate check."""
    from core.hale_bus.brain_bridge import BrainBridge
    from core.staffing.delegation_outcomes import record_outcome

    if not acceptance_criteria.strip():
        raise ValueError("dispatch_to_oc requires acceptance_criteria — no criteria, no delegation")

    bb = BrainBridge()
    description = f"{task}\n\nAcceptance criteria: {acceptance_criteria}"
    tid = bb.add(
        title=task[:120], description=description, lane="oc",
        priority=priority, task_id=ticket_id,
    )
    due = (datetime.now(timezone.utc) + timedelta(hours=sla_hours)).isoformat()
    record_outcome(
        seat="OC", action="delegated", verdict="PENDING",
        ticket_id=tid, task_type=task_type, dispatch_mode="async_poll",
        follow_up_due=due,
    )
    return {"ok": True, "ticket_id": tid, "follow_up_due": due}
