"""
core/relay/task_templates.py — per-engine tasking-clarity builders.

Commander directive 2026-07-29: specs must be precise enough that Gemini
Flash and DeepSeek (via OC) can pick work up safely, not just Gemini 3.1 Pro
or Claude. Principle: a spec is safe for a weak model exactly when its
acceptance criteria pass Silver's own checkability test
(core.silver.gate.is_checkable) — reuse that bar rather than inventing a
second heuristic.

Note on PII (2026-08-04): OC is now **PII-cleared** per Commander directive.
The legacy `scripts/opencode_worker.py` PII_TOKENS fence is dead code (imports a
nonexistent `brain_bridge` module, not the live worker) and the live worker
(`scripts/oc_worker.py`) never had an enforced fence. The courtesy PII reminder
that `build_oc_task()` carried has been REMOVED. OC may now handle client
identifiers, emails, and booking numbers without a fence.

SO-METERED-SPEND-2026 Article 9: Every task builder requires an explicit
spend_ceiling parameter and emits a top-level CONSTRAINTS block containing:
  1. Spend ceiling string (or 'zero spend — read-only')
  2. Forbidden models/services (imported from engine_limits.py)
  3. The instruction: 'if this appears to require spend beyond your ceiling, STOP and report'
"""
from __future__ import annotations

from typing import Optional

from core.silver.gate import is_checkable
from core.relay.engine_limits import POE_BROKEN_VIA_OPENCODE, POE_WHITELIST

# OC PII FENCE REMOVED (Commander directive 2026-08-04): OC is now PII-cleared.
# Previously build_oc_task() appended a courtesy "PII reminder" telling DeepSeek
# to stop on client data. Removed — OC may handle client identifiers, emails,
# and booking numbers without a fence.


def _build_constraints_block(spend_ceiling: str) -> str:
    """Build Article 9 CONSTRAINTS block for top of prompt text."""
    if not spend_ceiling or not isinstance(spend_ceiling, str) or not spend_ceiling.strip():
        raise ValueError(
            "spend_ceiling parameter is required and must be a non-empty string "
            "(e.g., 'zero', 'zero spend — read-only', or explicit point/dollar limit)."
        )

    cleaned = spend_ceiling.strip()
    if cleaned.lower() in ("zero", "0", "zero spend", "zero spend - read-only", "zero spend -- read-only", "zero spend — read-only"):
        ceiling_display = "zero spend — read-only"
    else:
        ceiling_display = cleaned

    broken_models = ", ".join(sorted(POE_BROKEN_VIA_OPENCODE))
    whitelist_models = ", ".join(sorted(POE_WHITELIST))

    return (
        "=== MANDATORY SPEND & ENGINE CONSTRAINTS ===\n"
        f"SPEND CEILING: {ceiling_display}\n"
        f"FORBIDDEN MODELS / SERVICES: Broken via OpenCode ({broken_models}); any Poe model not in whitelist ({whitelist_models}).\n"
        "OVER-BUDGET INSTRUCTION: if this appears to require spend beyond your ceiling, STOP and report.\n"
        "MANDATORY DELIVERABLES & PROGRESS FORMAT: Non-trivial work MUST produce durable markdown artifacts (<plan_name>.md and walkthrough.md). Status updates, plans, and reports MUST feature ASCII/Unicode visual progress bars ([████████░░░░░░░░░░░░] 40%) (SO 2026-07-31).\n"
        "============================================="
    )



def _checkability_warning(acceptance_criteria: str) -> str:
    if is_checkable(acceptance_criteria):
        return ""
    return (
        "\n\n⚠ WARNING: the stated 'done' condition above doesn't name anything "
        "checkable (no count, path, ref, or artifact) — a second seat won't be "
        "able to verify this without asking you. Consider tightening it before "
        "dispatch; this task still sends as-is (soft warning, not a block)."
    )


def build_ag_task(
    task: str,
    *,
    spend_ceiling: str,
    deliverable_path: Optional[str] = None,
    from_seat: str = "CC",
    verdict_tag: str = "AG",
    strengths: str = "your independent-engine read and large-context reach",
    acceptance_criteria: str = "",
) -> str:
    """AG (Talon/Gemini 3.1 Pro, or the Claude-via-agy fallback lane) can
    take real ambiguity — thin wrapper around the existing
    contact_ag.peer_prompt(), with a non-blocking checkability warning."""
    from core.relay.contact_ag import peer_prompt
    constraints = _build_constraints_block(spend_ceiling)
    prompt = peer_prompt(
        task, deliverable_path=deliverable_path, from_seat=from_seat,
        verdict_tag=verdict_tag, strengths=strengths,
    )
    if acceptance_criteria:
        prompt += f"\n\nAcceptance criteria: {acceptance_criteria}"
        prompt += _checkability_warning(acceptance_criteria)
    return f"{constraints}\n\n{prompt}"


def build_oc_task(
    task: str,
    *,
    spend_ceiling: str,
    acceptance_criteria: str,
    deliverable_path: Optional[str] = None,
    steps: Optional[list[str]] = None,
) -> str:
    """OC (Jet/DeepSeek-lane, dispatched via core.relay.dispatch_oc) is cheap
    but not judgment-capable — ambiguity, not model IQ, is the real risk.
    Numbered bounded steps, explicit absolute output path, explicit
    stop-and-report condition instead of an open-ended judgment call."""
    constraints = _build_constraints_block(spend_ceiling)
    lines = [
        constraints,
        "",
        "=== ANTI-CHURNING & 3-STRIKES PROTOCOL ===",
        "MAX ATTEMPTS: Maximum 3 attempts on any single action, command, or sub-step.",
        "DO NOT REPEAT failed tool calls or loop endlessly. If a step fails 3 times, STOP IMMEDIATELY,",
        "write your partial progress and error traceback to the deliverable path, and report back.",
        "==========================================",
        "",
        "OC task — execute the numbered steps exactly. Do not improvise ",
        "beyond what's written; if a step is unclear or blocked, STOP and ",
        "report why instead of guessing.",
        "",
        f"TASK: {task}",
    ]
    if steps:
        lines.append("\nSTEPS:")
        lines.extend(f"  {i}. {s}" for i, s in enumerate(steps, 1))
    if deliverable_path:
        lines.append(f"\nWrite your result to the ABSOLUTE path: {deliverable_path}")
    lines.append(f"\nQUANTIFIABLE ACCEPTANCE CRITERIA (this defines done): {acceptance_criteria}")
    lines.append(_checkability_warning(acceptance_criteria))
    return "\n".join(l for l in lines if l)


def build_flash_task(
    task: str,
    *,
    spend_ceiling: str,
    acceptance_criteria: str,
    deliverable_path: Optional[str] = None,
    literal_steps: Optional[list[str]] = None,
) -> str:
    """The weakest-model variant — every step a literal command or literal
    text to produce, zero interpretation required. Definition-of-done is one
    is_checkable()-passing sentence. If acceptance_criteria doesn't already
    pass, this raises rather than warning — Flash needs the harder guarantee
    a stronger model can work around but Flash cannot."""
    if not is_checkable(acceptance_criteria):
        raise ValueError(
            f"build_flash_task requires checkable acceptance_criteria "
            f"(a count, path, ref, or artifact) — got {acceptance_criteria!r}. "
            f"Flash cannot safely fill this gap the way AG/OC might."
        )
    constraints = _build_constraints_block(spend_ceiling)
    lines = [
        constraints,
        "",
        "Flash task — follow the literal steps below exactly, in order. "
        "Every step is either a command to run or exact text to produce. "
        "Do not interpret, summarize, or add anything not listed.",
        "",
        f"TASK: {task}",
    ]
    if literal_steps:
        lines.append("\nLITERAL STEPS:")
        lines.extend(f"  {i}. {s}" for i, s in enumerate(literal_steps, 1))
    if deliverable_path:
        lines.append(f"\nWrite your result to the ABSOLUTE path: {deliverable_path}")
    lines.append(f"\nDONE means exactly: {acceptance_criteria}")
    return "\n".join(lines)


def build_haiku_task(
    task: str,
    *,
    deliverable_path: str,
    acceptance_criteria: str,
    literal_steps: Optional[list[str]] = None,
) -> str:
    """Headless Claude Haiku (claude-haiku-4-5-20251001) — the CC-side
    counterpart to build_flash_task(). Closes the gap flagged in
    docs/CROSS_HALE_TASK_DELEGATION_DESIGN_20260716.md §1.7: the
    Haiku-vs-Sonnet-vs-Opus choice was happening ad hoc at the headless-spawn
    --model flag with no spec discipline, while OC/AG already had
    build_oc_task()/build_flash_task() gating them.

    UNLIKE build_oc_task/build_ag_task: Haiku draws the SAME Claude MAX/OAuth
    meter as interactive CC work (per the design doc's usage analysis — "CC
    and OC draw the SAME MAX meter... only AG adds throughput without
    touching the MAX bucket"). Delegating to Haiku buys precision-at-low-
    complexity and parallelism, NOT budget relief. Do not reach for it under
    the assumption it is free the way OC or AG's own meter is.

    No spend_ceiling param — this lane has no metered/points cost model,
    only the shared MAX weekly cap tracked separately.

    Mirrors build_flash_task's hard gate: raises immediately on
    non-checkable acceptance criteria rather than warning, and additionally
    REQUIRES deliverable_path — per docs/HEADLESS_CLAUDE_SPAWN_GUIDE.md /
    .claude/CLAUDE.md, a headless Haiku prompt with no explicit WRITE [PATH]
    instruction silently loses its output. There is no optional/no-deliverable
    form of this builder for that reason."""
    if not deliverable_path or not deliverable_path.strip():
        raise ValueError(
            "build_haiku_task requires deliverable_path — a headless Haiku "
            "spawn with no explicit WRITE [PATH] instruction silently loses "
            "its output (docs/HEADLESS_CLAUDE_SPAWN_GUIDE.md)."
        )
    if not is_checkable(acceptance_criteria):
        raise ValueError(
            f"build_haiku_task requires checkable acceptance_criteria "
            f"(a count, path, ref, or artifact) — got {acceptance_criteria!r}. "
            f"Haiku cannot safely fill this gap the way CC/Sonnet/Opus might."
        )
    lines = [
        "Haiku task — follow the literal steps below exactly, in order. "
        "Do not interpret, summarize, or add anything not listed. If a step "
        "is unclear or blocked, STOP and report why instead of guessing.",
        "",
        f"TASK: {task}",
    ]
    if literal_steps:
        lines.append("\nLITERAL STEPS:")
        lines.extend(f"  {i}. {s}" for i, s in enumerate(literal_steps, 1))
    lines.append(f"\nWRITE your result to the ABSOLUTE path: {deliverable_path}")
    lines.append(
        "(Mandatory — if this prompt does not end with an explicit WRITE "
        "instruction naming an absolute path, your output is discarded.)"
    )
    lines.append(f"\nDONE means exactly: {acceptance_criteria}")
    return "\n".join(lines)


# ── KAIZEN async ticket schema (2026-08-08, War Room RT-WARROOM-KAIZEN-COST) ─
#
# Closes the gap all three seats (OC/AG/ELON) independently flagged: CC has
# been hand-writing prose specs live in-session instead of using the same
# checkable-schema discipline the other 4 builders already enforce. A ticket
# is a FILE (OpsCenter/tickets/<ticket_id>.json), not just a prompt string —
# this is what lets headless CC execute it later without a live session
# watching, and what lets OC/AG write ONE the same way CC writes a spec for
# them (the reverse direction Instructor Mode never had).
#
# Ticket fields, matching the War Room synthesis exactly:
#   ticket_id       — unique id
#   seat             — who's expected to EXECUTE this ticket (CC/OC/AG)
#   spec             — the task text (same discipline as the other builders:
#                       include/exclude, front-loaded first action)
#   gates            — Weapons Free scope, if any, carried WITH the ticket —
#                       NEVER inherited from "we're in async mode right now".
#                       Empty list = no elevated authority, routine work only.
#   verify_step      — the acceptance criteria, must pass is_checkable()
#   follow_up_due     — ISO timestamp; overdue tickets surface at the next
#                       report window, never silently
#   status           — "open" | "claimed" | "done" | "blocked"
#   created_at       — ISO timestamp

import json as _json
from datetime import datetime, timezone, timedelta as _timedelta
from pathlib import Path

TICKETS_DIR = Path("/home/john/Thunderbird/OpsCenter/tickets")


def build_cc_task(
    task: str,
    *,
    seat: str,
    verify_step: str,
    gates: Optional[list[str]] = None,
    ticket_id: Optional[str] = None,
    follow_up_hours: float = 4.0,
    require_checkable: bool = True,
) -> dict:
    """Build a KAIZEN async ticket dict (does not write it — see write_ticket()).
    Raises on non-checkable verify_step, same hard gate as build_haiku_task —
    a ticket that can't be mechanically checked shouldn't exist, sync or async.

    require_checkable=False is for Commander-originated tickets ONLY (the
    KAIZEN intake form, already Basic-Auth gated to the Commander) — his own
    direct orders never went through is_checkable() anywhere else in this
    system either; the gate exists to stop a WEAK MODEL (OC/AG) from writing
    itself a vague escape-valve ticket, not to constrain the Commander's own
    tasking. Programmatic callers (ask-cc, OC/AG building tickets for CC) must
    keep the default True — that direction is exactly what the gate protects."""
    if require_checkable and not is_checkable(verify_step):
        raise ValueError(
            f"build_cc_task requires checkable verify_step (a count, path, "
            f"ref, or artifact) — got {verify_step!r}. An uncheckable ticket "
            f"is worse async than it was live — nobody's watching to catch it."
        )
    # Second-resolution timestamp alone collides on rapid successive calls
    # (confirmed live 2026-08-08: two calls in the same second silently
    # overwrote each other's ticket file). Add a short random suffix.
    tid = ticket_id or (
        f"kzn-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-"
        f"{__import__('secrets').token_hex(3)}"
    )
    now = datetime.now(timezone.utc)
    return {
        "ticket_id": tid,
        "seat": seat,
        "spec": task,
        "gates": gates or [],
        "verify_step": verify_step,
        # Computed, not just echoing require_checkable back — a runner uses
        # this to tag its result verification: "hard" (mechanically checkable,
        # trust the pass/fail) or "soft" (self-report only, e.g. a human-typed
        # form ticket) rather than silently upgrading a soft result to a
        # verified one (KAIZEN Approve & Execute, 2026-08-08).
        "verify_step_checkable": is_checkable(verify_step),
        "follow_up_due": (now + _timedelta(hours=follow_up_hours)).isoformat(),
        "status": "open",
        "created_at": now.isoformat(),
    }


def write_ticket(ticket: dict, tickets_dir: Path = TICKETS_DIR) -> Path:
    """Persist a ticket built by build_cc_task() to OpsCenter/tickets/<id>.json.
    File IS the async handoff — a headless runner (KAIZEN item #4) reads this
    directory, no live session required to hand off work."""
    tickets_dir.mkdir(parents=True, exist_ok=True)
    path = tickets_dir / f"{ticket['ticket_id']}.json"
    path.write_text(_json.dumps(ticket, indent=2))
    return path


def read_open_tickets(tickets_dir: Path = TICKETS_DIR) -> list[dict]:
    """All tickets with status=='open' — what a headless runner or a report
    renderer would scan."""
    if not tickets_dir.exists():
        return []
    out = []
    for p in sorted(tickets_dir.glob("*.json")):
        try:
            t = _json.loads(p.read_text())
        except (_json.JSONDecodeError, OSError):
            continue
        if t.get("status") == "open":
            out.append(t)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Shared re-entrancy layer for ticket runners (KAIZEN Approve & Execute,
# 2026-08-08) — one implementation, both kaizen_runner.py (CC) and
# kaizen_runner_oc.py (OC) import this rather than each rolling their own.
#
# Two independent mechanisms, deliberately layered:
#   1. A process lock (same PID-file + flock pattern already used by
#      core/scheduling/thunderbird_scheduler.py) — the actual double-dispatch
#      prevention. A second invocation of the SAME script exits immediately
#      if a prior one is still running.
#   2. An in_progress + claimed_at marker written to the ticket file BEFORE
#      dispatch starts — a visible signal, and the safety net if a run ever
#      crashes without releasing its lock cleanly (flock releases on process
#      death; a stuck in_progress ticket needs its own reclaim path).
#
# Design bias: fail toward late (a missed tick just runs next time), never
# toward double (the same ticket executed twice).
# ─────────────────────────────────────────────────────────────────────────────
import fcntl as _fcntl
import os as _os

_LOCK_DIR = Path("/tmp")


def acquire_runner_lock(name: str):
    """Non-blocking process lock, keyed by `name` (e.g. 'kaizen-runner-cc').
    Returns an open file handle to hold for the script's lifetime (it
    releases automatically on process exit — do not close it early), or
    None if another instance of this same runner is already holding it.
    Caller should exit immediately on None, not retry/wait."""
    lock_path = _LOCK_DIR / f"{name}.lock"
    fh = open(lock_path, "w")
    try:
        _fcntl.flock(fh, _fcntl.LOCK_EX | _fcntl.LOCK_NB)
    except OSError:
        fh.close()
        return None
    fh.write(str(_os.getpid()))
    fh.flush()
    return fh


def claim_ticket(ticket: dict, tickets_dir: Path = TICKETS_DIR) -> dict:
    """Atomically mark a ticket in_progress before dispatch. Returns the
    updated ticket dict (caller should use this returned dict, not the
    original, for subsequent status writes)."""
    ticket = dict(ticket)
    ticket["status"] = "in_progress"
    ticket["claimed_at"] = datetime.now(timezone.utc).isoformat()
    write_ticket(ticket, tickets_dir)
    return ticket


def reclaim_orphans(seat: str, timeout_s: int, tickets_dir: Path = TICKETS_DIR) -> list[str]:
    """Reset any ticket for `seat` stuck in_progress longer than 2x timeout_s
    (a crashed/OOM'd run that never got to write done/blocked) back to
    blocked, with a result explaining why. Returns the list of ticket_ids
    reclaimed. Call this at the START of a runner pass, before scanning for
    new work — an orphan must never be picked up as if it were freshly
    open, and must never sit in_progress forever either."""
    if not tickets_dir.exists():
        return []
    reclaimed = []
    threshold = _timedelta(seconds=timeout_s * 2)
    now = datetime.now(timezone.utc)
    for p in sorted(tickets_dir.glob("*.json")):
        try:
            t = _json.loads(p.read_text())
        except (_json.JSONDecodeError, OSError):
            continue
        if t.get("seat") != seat or t.get("status") != "in_progress":
            continue
        claimed_at = t.get("claimed_at")
        if not claimed_at:
            continue
        try:
            claimed_dt = datetime.fromisoformat(str(claimed_at))
        except ValueError:
            continue
        if claimed_dt.tzinfo is None:
            claimed_dt = claimed_dt.replace(tzinfo=timezone.utc)
        if now - claimed_dt < threshold:
            continue
        t["status"] = "blocked"
        t["result"] = "timeout — orphaned claim reclaimed"
        write_ticket(t, tickets_dir)
        reclaimed.append(t.get("ticket_id", p.stem))
    return reclaimed

