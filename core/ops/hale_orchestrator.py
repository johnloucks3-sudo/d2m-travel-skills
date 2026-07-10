"""
Hale Orchestrator — unified plan/compliance/initiative/evaluation ledger.

Generalizes the assess/verify contract from core/ci/repairs/schema.py and the
structured-input/durable-log shape from core/ops/three_voice_arbitration.py
into Hale's own operating loop. Never blocks or gates execution — this is a
ledger, not a runtime supervisor. See docs/superpowers/specs/2026-07-09-hale-orchestrator-design.md.
"""
from __future__ import annotations

import logging
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
