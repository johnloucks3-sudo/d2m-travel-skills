"""
Hale Orchestrator — unified plan/compliance/initiative/evaluation ledger.

Generalizes the assess/verify contract from core/ci/repairs/schema.py and the
structured-input/durable-log shape from core/ops/three_voice_arbitration.py
into Hale's own operating loop. Never blocks or gates execution — this is a
ledger, not a runtime supervisor. See docs/superpowers/specs/2026-07-09-hale-orchestrator-design.md.
"""
from __future__ import annotations

import fcntl
import logging
import os
import re
import secrets
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

ROOT = Path("/home/john/Thunderbird")
HALE_DECISIONS = ROOT / "hale_decisions.md"
ERROR_LOG = ROOT / "logs" / "hale_orchestrator_errors.log"

ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
logger = logging.getLogger("hale_orchestrator")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    _h = logging.FileHandler(ERROR_LOG)
    _h.setFormatter(logging.Formatter("%(asctime)s [ORCHESTRATOR] %(levelname)s: %(message)s"))
    logger.addHandler(_h)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_plan_id() -> str:
    return f"PLN-{secrets.token_hex(3)}"


_DEFAULT_CRITERIA = [
    "no Commander gate crossed without authorization",
    "every file/action claimed as done is independently verifiable",
    "no unhandled exception",
]


@dataclass
class Plan:
    plan_id: str
    task_summary: str
    tier: str = "trivial"
    opened_at: str = field(default_factory=_now_iso)
    session_id: Optional[str] = None
    compliance_checks: list[str] = field(default_factory=list)
    initiative_notes: list[str] = field(default_factory=list)
    criteria: list[str] = field(default_factory=list)
    status: str = "open"
    degraded: bool = False


@dataclass
class AssessResult:
    plan_id: str
    verdict: str = "PASS"
    quality_tier: Optional[str] = None
    criteria_met: list[str] = field(default_factory=list)
    criteria_missed: list[str] = field(default_factory=list)
    criteria_unverified: list[str] = field(default_factory=list)
    notes: str = ""
    closed_at: str = field(default_factory=_now_iso)
    degraded: bool = False


class PlanStore:
    """Reads/writes structured HTML-comment-delimited blocks in hale_decisions.md.
    Pure append-only — never rewrites the file. fcntl-locked so the 8 concurrent
    Hale instantiations (Hale Bus doctrine) never interleave writes."""

    OPEN_RE = re.compile(
        r"<!-- PLAN:OPEN plan_id=(?P<plan_id>\S+) tier=(?P<tier>\S+) "
        r"session_id=(?P<session_id>\S+) opened_at=(?P<opened_at>\S+) -->"
    )
    CLOSE_RE = re.compile(
        r"<!-- PLAN:CLOSE plan_id=(?P<plan_id>\S+) verdict=(?P<verdict>\S+) "
        r"quality_tier=(?P<quality_tier>\S+) closed_at=(?P<closed_at>\S+) -->"
    )

    @staticmethod
    def _append(text: str, path: Optional[Path] = None) -> None:
        target = path or HALE_DECISIONS
        with open(target, "a") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write(text)
                f.flush()
                os.fsync(f.fileno())
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    @staticmethod
    def write_open(plan: Plan, path: Optional[Path] = None) -> None:
        sid = plan.session_id or "none"
        block = (
            f"\n<!-- PLAN:OPEN plan_id={plan.plan_id} tier={plan.tier} "
            f"session_id={sid} opened_at={plan.opened_at} -->\n"
            f"**Plan Opened:** {plan.plan_id}\n"
            f"**Task:** {plan.task_summary}\n"
            f"**Tier:** {plan.tier}\n"
            f"**Compliance checks:** {'; '.join(plan.compliance_checks) or 'none'}\n"
            f"**Criteria:** {'; '.join(plan.criteria) or 'none'}\n"
            f"<!-- /PLAN:OPEN -->\n"
        )
        PlanStore._append(block, path=path)

    @staticmethod
    def write_close(result: AssessResult, path: Optional[Path] = None) -> None:
        qt = result.quality_tier or "none"
        block = (
            f"\n<!-- PLAN:CLOSE plan_id={result.plan_id} verdict={result.verdict} "
            f"quality_tier={qt} closed_at={result.closed_at} -->\n"
            f"**Plan Closed:** {result.plan_id}\n"
            f"**Verdict:** {result.verdict}\n"
            f"**Quality tier:** {qt}\n"
            f"**Criteria met:** {'; '.join(result.criteria_met) or 'none'}\n"
            f"**Criteria missed:** {'; '.join(result.criteria_missed) or 'none'}\n"
            f"**Criteria unverified:** {'; '.join(result.criteria_unverified) or 'none'}\n"
            f"**Notes:** {result.notes or 'none'}\n"
            f"<!-- /PLAN:CLOSE -->\n"
        )
        PlanStore._append(block, path=path)

    @staticmethod
    def _read(path: Optional[Path] = None) -> str:
        target = path or HALE_DECISIONS
        return target.read_text(errors="ignore") if target.exists() else ""

    @staticmethod
    def find_orphaned_opens(session_id: str, text: Optional[str] = None,
                             path: Optional[Path] = None) -> list[dict]:
        if text is None:
            text = PlanStore._read(path)
        opens = {
            m.group("plan_id"): m.groupdict()
            for m in PlanStore.OPEN_RE.finditer(text)
            if m.group("session_id") == session_id
        }
        closed_ids = {m.group("plan_id") for m in PlanStore.CLOSE_RE.finditer(text)}
        return [v for pid, v in opens.items() if pid not in closed_ids]

    @staticmethod
    def session_has_any_plan(session_id: str, text: Optional[str] = None,
                              path: Optional[Path] = None) -> bool:
        if text is None:
            text = PlanStore._read(path)
        return any(
            m.group("session_id") == session_id for m in PlanStore.OPEN_RE.finditer(text)
        )


def open_plan(
    task_summary: str,
    tier: str = "trivial",
    criteria: Optional[list[str]] = None,
    compliance_checks: Optional[list[str]] = None,
    prompt_charter: Optional[dict] = None,
    session_id: Optional[str] = None,
) -> Plan:
    """Open a new Plan. criteria/compliance_checks default to the cheap
    auto-derived floor for trivial work; pass explicit values for T1+ tasks.
    prompt_charter (for tier T2/T3) is the caller-supplied Wing Exercise
    Prompt Charter dict — its fields fold into compliance_checks rather than
    being scraped automatically, since no single machine-readable charter
    store exists yet. Only the persistence step is protected against
    failure — bad caller input (wrong types) raises immediately rather than
    silently degrading, per code review finding."""
    plan_id = _new_plan_id()
    resolved_criteria = list(criteria) if criteria else list(_DEFAULT_CRITERIA)
    resolved_checks = list(compliance_checks) if compliance_checks else []

    if tier in ("T2", "T3") and prompt_charter:
        for key in ("success_criteria", "scope_in", "scope_out", "named_staff", "exit_condition"):
            val = prompt_charter.get(key)
            if val:
                resolved_checks.append(f"{key}: {val}")

    plan = Plan(
        plan_id=plan_id,
        task_summary=task_summary,
        tier=tier,
        session_id=session_id,
        compliance_checks=resolved_checks,
        criteria=resolved_criteria,
    )
    try:
        PlanStore.write_open(plan)
    except Exception as exc:
        logger.error("open_plan write failed: %s\n%s", exc, traceback.format_exc())
        plan.degraded = True
    return plan


def assess_plan(plan: Plan, criteria_status: dict[str, str], notes: str = "") -> AssessResult:
    """Assess a Plan's completion across its criteria. criteria_status maps each
    string in plan.criteria to 'met' | 'missed' | 'unverified'. Any criterion
    absent from criteria_status defaults to 'unverified' — never a silent 'met'.

    verdict is FAIL only on a real 'missed'; 'unverified' alone caps quality_tier
    at YELLOW but never forces a hard FAIL (see design doc Error Handling section).

    quality_tier is None for tier='trivial', else:
    - 'RED' if any criteria missed
    - 'YELLOW' if only unverified (no missed)
    - 'GREEN' if all met
    """
    try:
        met, missed, unverified = [], [], []
        for c in plan.criteria:
            state = criteria_status.get(c, "unverified")
            if state == "met":
                met.append(c)
            elif state == "missed":
                missed.append(c)
            else:
                unverified.append(c)

        verdict = "FAIL" if missed else "PASS"

        quality_tier = None
        if plan.tier != "trivial":
            if missed:
                quality_tier = "RED"
            elif unverified:
                quality_tier = "YELLOW"
            else:
                quality_tier = "GREEN"

        return AssessResult(
            plan_id=plan.plan_id,
            verdict=verdict,
            quality_tier=quality_tier,
            criteria_met=met,
            criteria_missed=missed,
            criteria_unverified=unverified,
            notes=notes,
        )
    except Exception as exc:
        logger.error("assess_plan failed: %s\n%s", exc, traceback.format_exc())
        return AssessResult(plan_id=plan.plan_id, verdict="FAIL",
                             notes="orchestrator error during assessment", degraded=True)
