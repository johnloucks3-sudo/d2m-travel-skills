"""
Cross-Hale Task Delegation — routing + ticket-schema building block.

Design: docs/CROSS_HALE_TASK_DELEGATION_DESIGN_20260716.md
Status: PHASE-0 LIBRARY. This module is a pure building block — it classifies a
task to a seat (CC/OC/AG) and builds a delegation ticket with the anti-theater
schema. It does NOT auto-fire the relay and does NOT write mission_board.json;
callers (a Hale seat, or the AGY mission-board capability being built in
parallel) own those side effects.

It is intentionally NOT one of the 10 policy-protected files
(see core/policy/rules_registry.py). It imports wing_relay READ-ONLY for the
optional convenience wrapper `relay_notify_handoff()`; it never edits it.

Substrate-fit routing does NOT conflict with the equal-performance SO
(05c45c5b3): the SO governs behavioral standard (initiative/boldness/frankness),
this module governs engine fit (context window, cost meter, model family).
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from typing import Optional

# ── Seats ──────────────────────────────────────────────────────────────────
CC = "CC"  # Claude Code — Opus/Sonnet on MAX. Hub. Judgment/architecture/voice.
OC = "OC"  # OpenCode   — Sonnet via MAX OAuth (+ Poe persona lane). Mechanical ops.
AG = "AG"  # Antigravity/Gemini — separate Google meter ($0 Claude). Budget valve.
SEATS = (CC, OC, AG)

@dataclass
class RouteDecision:
    seat: str
    rationale: str


def route_task(
    task_type: str,
    *,
    needs_judgment: bool = False,      # Claude-grade reasoning / client voice / arbitration
    needs_large_context: bool = False, # >~200k tokens; Gemini 1M ctx territory
    is_vision: bool = False,           # image QC / visual
    claude_optional: bool = False,     # Sonnet-tier work that does NOT need Claude judgment
) -> RouteDecision:
    """Return (seat, rationale). First match wins — see design §3.1."""
    # 1. Judgment / architecture / client voice / cross-seat arbitration → CC
    if needs_judgment:
        return RouteDecision(CC, "needs Claude-grade judgment / voice / arbitration")

    # 3-early. Large context or vision must go to Gemini regardless of budget.
    if needs_large_context:
        return RouteDecision(AG, "large-context (Gemini 1M ctx) — off the MAX meter")
    if is_vision:
        return RouteDecision(AG, "vision/image task — Gemini native")

    mechanical = {
        "factbook_refresh", "inbox_triage", "dossier_sync", "mission_status_write",
        "label_fix", "timestamp_fix", "file_move", "scrape_store", "json_validate",
        "ci_probe", "scheduled_sweep", "data_pull",
    }
    # 2. Deterministic ops/mechanical, no judgment → OC (JET default)
    if task_type in mechanical:
        return RouteDecision(OC, "deterministic ops/mechanical — OC JET default")

    # Claude-optional Sonnet-tier work → AG unconditionally. AG is the free
    # Google meter; there is no reason to spend the MAX bucket on work that does
    # not need Claude judgment/voice, at any weekly %.
    if claude_optional:
        return RouteDecision(AG, "Claude-optional — AG (free meter) instead of the MAX bucket")

    # 4. Safe default — CC can re-delegate.
    return RouteDecision(CC, "default — CC (can re-delegate)")


@dataclass
class DelegationTicket:
    """Extended mission-board ticket for delegated work (design §3.2).

    A ticket cannot reach `done` without a verification_artifact certified by a
    seat other than assigned_to — the anti-theater contract (§3.5).
    """
    id: str
    title: str
    assigned_to: str
    acceptance_criteria: str            # PDTAC "T" — delegator-defined, REQUIRED
    delegation_rationale: str
    priority: str = "P2"
    status: str = "assigned"
    verification_artifact: str = ""     # assignee-filled: path | commit | url | sheet row
    certified_by: str = ""              # MUST differ from assigned_to
    deadline: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def can_certify(self, certifier_seat: str) -> tuple[bool, str]:
        """Gate the `done` transition. Enforces cross-seat certify + artifact presence.
        NOTE: presence is necessary but NOT sufficient — the certifier must ALSO
        validate artifact CONTENT against acceptance_criteria (§3.5.1). That
        content check is the caller's responsibility and cannot be faked here."""
        if certifier_seat == self.assigned_to:
            return False, "self-certification forbidden — certifier must differ from assignee"
        if not self.verification_artifact.strip():
            return False, "no verification_artifact — cannot close"
        if not self.acceptance_criteria.strip():
            return False, "no acceptance_criteria — nothing to validate against"
        return True, "eligible — now validate artifact CONTENT vs acceptance_criteria"

    def as_dict(self) -> dict:
        return asdict(self)


def build_delegation_ticket(
    ticket_id: str,
    title: str,
    task_type: str,
    acceptance_criteria: str,
    *,
    priority: str = "P2",
    deadline_hours: Optional[int] = None,
    **route_kwargs,
) -> DelegationTicket:
    """Classify + assemble a ticket. `acceptance_criteria` is REQUIRED (design §3.5.1)."""
    if not acceptance_criteria.strip():
        raise ValueError("acceptance_criteria is required — no criteria, no delegation")
    decision = route_task(task_type, **route_kwargs)
    deadline = ""
    if deadline_hours:
        deadline = (datetime.now(timezone.utc) + timedelta(hours=deadline_hours)).isoformat()
    return DelegationTicket(
        id=ticket_id,
        title=title,
        assigned_to=decision.seat,
        acceptance_criteria=acceptance_criteria,
        delegation_rationale=decision.rationale,
        priority=priority,
        deadline=deadline,
    )


def relay_notify_handoff(ticket: DelegationTicket, from_seat: str = CC) -> Optional[int]:
    """OPTIONAL convenience: emit the hand-off notification via the existing,
    already-coded relay primitive. Read-only use of wing_relay. Returns the
    Telegram message_id, or None if the relay is unavailable (e.g. no token).
    OC<->AG must hub through CC per relay topology — pass from_seat=CC for those."""
    try:
        from core.relay.wing_relay import relay_handoff
    except Exception:
        return None
    try:
        return relay_handoff(
            from_seat, ticket.assigned_to, ticket.title,
            detail=f"{ticket.id} | crit: {ticket.acceptance_criteria} | why: {ticket.delegation_rationale}",
        )
    except Exception:
        return None


# ── Self-test ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    cases = [
        # (kwargs, expected_seat)
        (dict(task_type="delegation_design", needs_judgment=True), CC),
        (dict(task_type="market_intel", needs_large_context=True), AG),
        (dict(task_type="image_qc", is_vision=True), AG),
        (dict(task_type="factbook_refresh"), OC),
        (dict(task_type="inbox_triage"), OC),
        (dict(task_type="summarize_batch", claude_optional=True), AG),
        (dict(task_type="draft_something"), CC),
    ]
    ok = 0
    for kw, exp in cases:
        d = route_task(**kw)
        status = "PASS" if d.seat == exp else "FAIL"
        ok += d.seat == exp
        print(f"[{status}] {kw.get('task_type'):20s} -> {d.seat} ({d.rationale})")

    # Anti-theater gate tests
    t = build_delegation_ticket(
        "MISSION-TEST", "test ticket", "factbook_refresh",
        acceptance_criteria="file X regenerated with 12 rows",
        deadline_hours=6,
    )
    assert t.assigned_to == OC
    good, why = t.can_certify(CC)
    assert good is False and "no verification_artifact" in why, why  # no artifact yet
    t.verification_artifact = "OpsCenter/factbook.json@commit abc123"
    good, why = t.can_certify(OC)
    assert good is False and "self-certification" in why, why        # self-cert blocked
    good, why = t.can_certify(CC)
    assert good is True, why                                          # cross-seat + artifact
    print(f"[PASS] anti-theater gate: cross-seat certify + artifact required")

    try:
        build_delegation_ticket("M2", "no crit", "file_move", acceptance_criteria="  ")
        print("[FAIL] empty acceptance_criteria accepted")
    except ValueError:
        print("[PASS] empty acceptance_criteria rejected")

    print(f"\n{ok}/{len(cases)} routing cases passed")
