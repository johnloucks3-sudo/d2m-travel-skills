"""
core/staffing/delegation_outcomes.py — the Wing's delegation/verification ledger.

Commander directive 2026-07-29 (Wing Oversight, Delegation & Transparency):
CC is now primary orchestrator of CC/OC/AG and must delegate aggressively
under a halved Claude budget. The gap this closes: core/staffing/
integrity_check.py's cc_integrity_double_check() — the exact tool that (per
the Commander's account) caught Gemini Flash (AG's lighter fallback tier,
not the default Gemini 3.1 Pro) dropping a state during the 2026-07-28
night 8-Sector Wing Exercise — had ZERO callers anywhere in the repo before
this module existed. It worked when invoked, but nothing invoked it as a
habit and nothing recorded its verdict. Same story for
core/relay/delegation_wiring.py's certify_mission(): its one call site
(OpsCenter/mission_board_sync.py cmd_complete) just returns a string on
DelegationError — a blocked certification vanishes the moment the terminal
scrolls.

This module is the durable spine every verification/certification/dispatch
point in the Wing writes to. Modeled directly on two proven idioms already
in this repo rather than inventing a new one:
  - core/ops/hale_orchestrator.py's PlanStore / ledger_stats() — append-only,
    fcntl-locked, HTML-comment-delimited blocks in hale_decisions.md, plus a
    stats-dict + one-line renderer for the daily brief.
  - core/silver/gate.py's Verdict/_log() — JSONL ledger + a human-readable
    "CHIEF X" line echoed into hale_decisions.md so a human scanning the
    decision log sees the machine record and the narrative side by side.

Soft guidance only (Commander directive — delegation is a default, not a
ceiling): record_outcome() never raises, and nothing here blocks a caller.
Accountability is retrospective, via rollup_stats().
"""
from __future__ import annotations

import fcntl
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

ROOT = Path("/home/john/Thunderbird")
OUTCOME_LOG = ROOT / "OpsCenter" / "delegation_outcomes.jsonl"
HALE_DECISIONS = ROOT / "hale_decisions.md"

ERROR_LOG = ROOT / "logs" / "delegation_outcomes_errors.log"
ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
logger = logging.getLogger("delegation_outcomes")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    _h = logging.FileHandler(ERROR_LOG)
    _h.setFormatter(logging.Formatter("%(asctime)s [WING-OPS] %(levelname)s: %(message)s"))
    logger.addHandler(_h)

SEATS = ("CC", "OC", "AG")
DISPATCH_MODES = ("sync", "async_poll", "self")
ACTIONS = ("delegated", "self_executed", "integrity_check", "certification", "reconciliation")
VERDICTS = ("PASS", "DISCREPANCY", "UNVERIFIED", "BLOCKED", "DROPPED", "STALLED", "PENDING", "FAILED")

# Verdicts that mean "something real went wrong" — these are what
# page_commander() is for; PASS/PENDING never page.
FAILURE_VERDICTS = ("DISCREPANCY", "UNVERIFIED", "BLOCKED", "DROPPED", "STALLED", "FAILED")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Outcome:
    ts: str
    seat: str
    action: str
    verdict: str
    ticket_id: str = ""
    task_type: str = ""
    dispatch_mode: str = "self"
    discrepancy_detail: str = ""
    certified_by: str = ""
    verified_by: str = ""
    follow_up_due: Optional[str] = None
    reconciled: bool = False
    self_execute_rationale: str = ""
    routing_recommendation: str = ""

    def as_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


def _append_jsonl(row: dict, path: Optional[Path] = None) -> None:
    target = path or OUTCOME_LOG
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "a") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def _mirror_to_decisions(row: dict, path: Optional[Path] = None) -> None:
    """Echo one line into hale_decisions.md, same convention as gate.py's
    CHIEF SILVER lines — a human reading the decision log sees both
    interleaved. Best-effort: a mirror failure never masks a real verdict."""
    target = path or HALE_DECISIONS
    detail = f" ({row['discrepancy_detail'][:160]})" if row.get("discrepancy_detail") else ""
    line = (f"\n- **CHIEF WING-OPS** [{row['ts'][:16]}Z] {row['action']} "
            f"{row['seat']} ({row.get('ticket_id') or 'adhoc'}) → {row['verdict']}{detail}")
    try:
        with target.open("a") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write(line + "\n")
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except Exception as exc:
        logger.error("mirror to hale_decisions.md failed: %s", exc)


def record_outcome(
    *,
    seat: str,
    action: str,
    verdict: str,
    ticket_id: str = "",
    task_type: str = "",
    dispatch_mode: str = "self",
    discrepancy_detail: str = "",
    certified_by: str = "",
    verified_by: str = "",
    follow_up_due: Optional[str] = None,
    reconciled: bool = False,
    self_execute_rationale: str = "",
    routing_recommendation: str = "",
    outcome_path: Optional[Path] = None,
    decisions_path: Optional[Path] = None,
) -> dict:
    """Append one outcome row. Never raises — a logging failure must never
    mask or block the real verdict the caller already has (same contract as
    hale_orchestrator.close_plan())."""
    if seat not in SEATS:
        logger.warning("record_outcome: unknown seat %r (allowed %s)", seat, SEATS)
    row = Outcome(
        ts=_now_iso(), seat=seat, action=action, verdict=verdict,
        ticket_id=ticket_id, task_type=task_type, dispatch_mode=dispatch_mode,
        discrepancy_detail=discrepancy_detail, certified_by=certified_by,
        verified_by=verified_by, follow_up_due=follow_up_due, reconciled=reconciled,
        self_execute_rationale=self_execute_rationale,
        routing_recommendation=routing_recommendation,
    ).as_dict()
    try:
        _append_jsonl(row, path=outcome_path)
    except Exception as exc:
        logger.error("record_outcome write failed: %s", exc)
    _mirror_to_decisions(row, path=decisions_path)
    return row


def _read_rows(path: Optional[Path] = None) -> list[dict]:
    target = path or OUTCOME_LOG
    if not target.exists():
        return []
    rows = []
    for line in target.read_text(errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    return rows


def outstanding(dispatch_mode: str = "async_poll", older_than_hours: float = 0,
                path: Optional[Path] = None) -> list[dict]:
    """Rows dispatched-but-unreconciled past their follow_up_due. This is the
    OC-side equivalent of AG marking a state complete when it wasn't — the
    failure mode where a ticket was silently dropped is otherwise invisible
    because nothing distinguishes 'still working' from 'never picked up'."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=older_than_hours)
    out = []
    seen_latest: dict[str, dict] = {}
    for row in _read_rows(path):
        if row.get("dispatch_mode") != dispatch_mode or row.get("action") != "delegated":
            continue
        tid = row.get("ticket_id") or ""
        if not tid:
            continue
        # last "delegated" row per ticket wins (re-dispatch / SLA-extend supersedes)
        if tid not in seen_latest or row["ts"] > seen_latest[tid]["ts"]:
            seen_latest[tid] = row
    # a ticket is only "outstanding" if nothing later (reconciliation, re-dispatch
    # marked reconciled) has closed it out
    reconciled_ids = {r["ticket_id"] for r in _read_rows(path)
                       if r.get("action") == "reconciliation" and r.get("reconciled")}
    for tid, row in seen_latest.items():
        if tid in reconciled_ids or row.get("reconciled"):
            continue
        due = row.get("follow_up_due")
        if due and due <= cutoff.isoformat():
            out.append(row)
    return out


def rollup_stats(since_days: int = 1, path: Optional[Path] = None) -> dict:
    """Same idiom as hale_orchestrator.ledger_stats() — the honest cut for the
    daily brief. Real counts, not vibes."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=since_days)).isoformat()
    rows = [r for r in _read_rows(path) if r.get("ts", "") >= cutoff]
    stats = {
        "since_days": since_days, "total": len(rows),
        "by_seat": {s: 0 for s in SEATS},
        "self_execute_count": 0, "delegate_count": 0,
        "self_execute_unjustified": 0,
        "verified_pass": 0, "discrepancies_caught": 0, "unverified": 0,
        "blocked_certifications": 0, "certified_pass": 0,
        "unreconciled_oc": 0, "follow_up_overdue": 0,
        "dropped": 0,
    }
    for r in rows:
        if r.get("seat") in stats["by_seat"]:
            stats["by_seat"][r["seat"]] += 1
        action, verdict = r.get("action"), r.get("verdict")
        if action == "self_executed":
            stats["self_execute_count"] += 1
            if r.get("routing_recommendation") and not r.get("self_execute_rationale"):
                stats["self_execute_unjustified"] += 1
        elif action == "delegated":
            stats["delegate_count"] += 1
        elif action == "integrity_check":
            if verdict == "PASS":
                stats["verified_pass"] += 1
            elif verdict == "DISCREPANCY":
                stats["discrepancies_caught"] += 1
            elif verdict == "UNVERIFIED":
                stats["unverified"] += 1
        elif action == "certification":
            if verdict == "PASS":
                stats["certified_pass"] += 1
            elif verdict == "BLOCKED":
                stats["blocked_certifications"] += 1
        elif action == "reconciliation" and verdict == "DROPPED":
            stats["dropped"] += 1
    outstanding_now = outstanding("async_poll", older_than_hours=0, path=path)
    stats["unreconciled_oc"] = len(outstanding_now)
    stats["follow_up_overdue"] = len(outstanding_now)
    return stats


def rollup_line(since_days: int = 1, path: Optional[Path] = None) -> str:
    s = rollup_stats(since_days, path=path)
    seats = " · ".join(f"{k}:{v}" for k, v in s["by_seat"].items())
    return (f"{s['total']} outcomes/{since_days}d — {seats} | "
            f"self-exec:{s['self_execute_count']} (unjustified:{s['self_execute_unjustified']}) · "
            f"delegated:{s['delegate_count']} | verified-PASS:{s['verified_pass']} · "
            f"discrepancies:{s['discrepancies_caught']} · unverified:{s['unverified']} | "
            f"certified:{s['certified_pass']} · blocked:{s['blocked_certifications']} | "
            f"OC unreconciled:{s['unreconciled_oc']} · dropped:{s['dropped']}")


def page_commander(problem: str, discussion: str = "", action: str = "",
                    next_steps: str = "", source: str = "CHIEF WING-OPS") -> bool:
    """Real-time page for a failure verdict — the mechanical fix for 'AG
    marked it complete when it wasn't, and I only found out because CC
    happened to mention it.' Reuses the existing disciplined paging lane
    (P1, one-and-done dedup) rather than inventing a new channel — same
    pattern as silver/gate.py's _page_hold(). Best-effort; never raises."""
    try:
        from core.comms.wing_page import send_page, P1
        return send_page(
            problem=problem, discussion=discussion, action=action,
            next_steps=next_steps, level=P1, source=source,
        )
    except Exception as exc:
        logger.error("page_commander failed: %s", exc)
        return False
