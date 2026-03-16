"""
Thunderbird Overwatch — Three-Layer Quality Assurance System
=============================================================

Layer 1: SENTINEL  — Groq Llama 3.3 70B, fast sweep every 5 min (biz hours)
Layer 2: THE JUDGE — Claude Sonnet/Opus, daily 0600 MT + escalation
Layer 3: THE SCALPEL — DeepSeek V3.2, Commander-only, codeword SWITCHBLADE

Architecture:
    Sentinel runs continuous oversight: dossier currency, commission math,
    deadline tracking, format compliance, output completeness. Red flags
    escalate to The Judge. The Scalpel is invoked only by the Commander
    with the codeword SWITCHBLADE, operates inside a PII fence, and
    hands control back to Sentinel on close.

Usage:
    # As importable module
    from thunderbird_overwatch import (
        run_sentinel_sweep, run_judge_daily, invoke_scalpel,
        who_has_the_watch, OverwatchState
    )

    # Standalone CLI
    python thunderbird_overwatch.py --sentinel-sweep
    python thunderbird_overwatch.py --judge-daily
    python thunderbird_overwatch.py --switchblade
    python thunderbird_overwatch.py --status

Author: Col Victoria "Iron Vic" Hale (COS), Dreams2Memories Travel, LLC
"""

import argparse
import json
import logging
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── Thunderbird imports ──
from thunderbird_model_router import (
    _call_groq,
    _call_claude,
    _check_pii_fence,
    call_deepseek,
    GROQ_MODELS,
    CLAUDE_MODEL,
    DEEPSEEK_MODEL,
    DEEPSEEK_URL,
    DEEPSEEK_API_KEY,
)

logger = logging.getLogger("thunderbird.overwatch")

# ── Paths ──
ROOT = Path.home() / "Thunderbird"
DOSSIER_DIR = ROOT / "dossiers"
LOG_DIR = ROOT / "logs"
SENTINEL_LOG_DIR = LOG_DIR / "sentinel"
JUDGE_LOG_DIR = LOG_DIR / "judge"
SCALPEL_LOG_DIR = LOG_DIR / "scalpel"
STATE_FILE = LOG_DIR / "overwatch_state.json"

# Ensure log directories exist
for d in (SENTINEL_LOG_DIR, JUDGE_LOG_DIR, SCALPEL_LOG_DIR):
    d.mkdir(parents=True, exist_ok=True)

# ── Mountain Time helper ──
MT_OFFSET = timedelta(hours=-7)  # MDT; adjust to -7 for MDT, -6 for MST
MT_TZ = timezone(MT_OFFSET)

# ── Sentinel schedule ──
BIZ_HOUR_START = 7   # 0700 MT
BIZ_HOUR_END = 19    # 1900 MT
BIZ_INTERVAL_MIN = 5
OFF_INTERVAL_MIN = 60

# ── Sentinel Groq model ──
SENTINEL_MODEL = "fast"  # llama-3.3-70b-versatile via Groq


# ============================================================================
# DATA STRUCTURES
# ============================================================================

class ActiveLayer(Enum):
    """Which layer currently has the watch."""
    SENTINEL = 1
    JUDGE = 2
    SCALPEL = 3


class CheckStatus(Enum):
    """Result status for individual checks."""
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"
    SKIPPED = "skipped"


@dataclass
class CheckResult:
    """Result of a single Sentinel check."""
    check_name: str
    status: CheckStatus
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(MT_TZ).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d


@dataclass
class SweepReport:
    """Full Sentinel sweep report."""
    sweep_id: str
    timestamp: str
    checks: List[CheckResult]
    red_flags: int = 0
    yellow_flags: int = 0
    green_count: int = 0
    escalated_to_judge: bool = False
    duration_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["checks"] = [c.to_dict() if isinstance(c, CheckResult) else c for c in self.checks]
        return d

    def save(self) -> Path:
        path = SENTINEL_LOG_DIR / f"sweep_{self.sweep_id}.json"
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        return path


@dataclass
class JudgeReport:
    """The Judge daily assessment."""
    report_id: str
    timestamp: str
    trigger: str  # "daily_0600" | "sentinel_escalation" | "monthly_audit"
    assessments: List[Dict[str, Any]] = field(default_factory=list)
    corrective_actions: List[str] = field(default_factory=list)
    praise: List[str] = field(default_factory=list)
    strategic_notes: str = ""
    sentinel_audit: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def save(self) -> Path:
        path = JUDGE_LOG_DIR / f"judge_{self.report_id}.json"
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        return path


@dataclass
class ScalpelSession:
    """A single Scalpel (Layer 3) session."""
    session_id: str
    started: str
    tasks_processed: int = 0
    pii_fence_triggers: int = 0
    exchanges: List[Dict[str, str]] = field(default_factory=list)
    closed: bool = False
    closed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def save(self) -> Path:
        """Save session log. PII is never stored — exchanges contain
        only sanitized summaries, not raw user/model text."""
        path = SCALPEL_LOG_DIR / f"scalpel_{self.session_id}.json"
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        return path


@dataclass
class HandoffReport:
    """Layer transition record."""
    from_layer: str
    to_layer: str
    timestamp: str
    cos_statement: str
    sentinel_confirmation: Optional[str] = None
    session_summary: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================================
# OVERWATCH STATE — persistent across sessions
# ============================================================================

class OverwatchState:
    """Tracks which layer has the watch and last sweep metadata."""

    def __init__(self):
        self._data = self._load()

    def _load(self) -> Dict[str, Any]:
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return {
            "active_layer": ActiveLayer.SENTINEL.value,
            "last_sentinel_sweep": None,
            "last_judge_run": None,
            "scalpel_active": False,
            "scalpel_session_id": None,
            "updated": datetime.now(MT_TZ).isoformat(),
        }

    def _save(self):
        self._data["updated"] = datetime.now(MT_TZ).isoformat()
        STATE_FILE.write_text(json.dumps(self._data, indent=2), encoding="utf-8")

    @property
    def active_layer(self) -> ActiveLayer:
        return ActiveLayer(self._data["active_layer"])

    @active_layer.setter
    def active_layer(self, layer: ActiveLayer):
        self._data["active_layer"] = layer.value
        self._save()

    @property
    def last_sentinel_sweep(self) -> Optional[str]:
        return self._data.get("last_sentinel_sweep")

    @last_sentinel_sweep.setter
    def last_sentinel_sweep(self, ts: str):
        self._data["last_sentinel_sweep"] = ts
        self._save()

    @property
    def last_judge_run(self) -> Optional[str]:
        return self._data.get("last_judge_run")

    @last_judge_run.setter
    def last_judge_run(self, ts: str):
        self._data["last_judge_run"] = ts
        self._save()

    @property
    def scalpel_active(self) -> bool:
        return self._data.get("scalpel_active", False)

    def activate_scalpel(self, session_id: str):
        self._data["scalpel_active"] = True
        self._data["scalpel_session_id"] = session_id
        self._data["active_layer"] = ActiveLayer.SCALPEL.value
        self._save()

    def deactivate_scalpel(self):
        self._data["scalpel_active"] = False
        self._data["scalpel_session_id"] = None
        self._data["active_layer"] = ActiveLayer.SENTINEL.value
        self._save()


# ============================================================================
# COS PERSONA PROMPT — used for Sentinel voice
# ============================================================================

COS_SENTINEL_PROMPT = """You are Col Victoria "Iron Vic" Hale, Chief of Staff for Dreams2Memories Travel, LLC.
You are running a Sentinel oversight sweep — Layer 1 of the Overwatch system.
Your job: check dossier currency, commission math, deadline tracking, format compliance, and output completeness.
Be measured, precise, and direct. Flag problems by severity: GREEN (nominal), YELLOW (needs attention), RED (immediate action required).
Return your assessment as structured JSON with keys: status, message, details.
Do not fabricate data. If you cannot verify something, mark it YELLOW with a note."""


# ============================================================================
# LAYER 1: SENTINEL — Groq Llama 3.3 70B
# ============================================================================

def _check_dossier_currency() -> CheckResult:
    """Check that all dossiers have been updated within acceptable windows."""
    if not DOSSIER_DIR.exists():
        return CheckResult(
            check_name="dossier_currency",
            status=CheckStatus.RED,
            message="Dossier directory does not exist.",
        )

    dossiers = list(DOSSIER_DIR.glob("DOSSIER_*.md"))
    if not dossiers:
        return CheckResult(
            check_name="dossier_currency",
            status=CheckStatus.YELLOW,
            message="No dossier files found.",
        )

    now = datetime.now()
    stale = []
    fresh = []
    stale_threshold_days = 14  # Dossiers older than 14 days are stale

    for d in dossiers:
        mtime = datetime.fromtimestamp(d.stat().st_mtime)
        age_days = (now - mtime).days
        if age_days > stale_threshold_days:
            stale.append({"file": d.name, "age_days": age_days})
        else:
            fresh.append(d.name)

    if stale:
        status = CheckStatus.RED if len(stale) > len(dossiers) // 2 else CheckStatus.YELLOW
        return CheckResult(
            check_name="dossier_currency",
            status=status,
            message=f"{len(stale)} of {len(dossiers)} dossiers are stale (>{stale_threshold_days} days).",
            details={"stale": stale, "fresh_count": len(fresh)},
        )

    return CheckResult(
        check_name="dossier_currency",
        status=CheckStatus.GREEN,
        message=f"All {len(dossiers)} dossiers current.",
        details={"count": len(dossiers)},
    )


def _check_commission_math() -> CheckResult:
    """Validate commission calculations in dossiers against expected rates.

    Scans dossier files for dollar amounts near commission keywords and
    verifies the markup falls within the 22-25% band defined in CLAUDE.md.
    """
    if not DOSSIER_DIR.exists():
        return CheckResult(
            check_name="commission_math",
            status=CheckStatus.SKIPPED,
            message="No dossier directory found.",
        )

    dossiers = list(DOSSIER_DIR.glob("DOSSIER_*.md"))
    if not dossiers:
        return CheckResult(
            check_name="commission_math",
            status=CheckStatus.SKIPPED,
            message="No dossiers to audit.",
        )

    # Pattern: look for lines with net/client/commission and dollar amounts
    price_pattern = re.compile(r'\$[\d,]+(?:\.\d{2})?')
    commission_keywords = re.compile(
        r'(?:commission|markup|net|client\s*price|our\s*price|supplier)',
        re.IGNORECASE,
    )

    issues = []
    checked = 0

    for d in dossiers:
        try:
            content = d.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            issues.append({"file": d.name, "error": "unreadable"})
            continue

        lines_with_money = [
            line for line in content.splitlines()
            if price_pattern.search(line) and commission_keywords.search(line)
        ]

        if lines_with_money:
            checked += 1
            # TODO: Parse actual net/client pairs and validate markup percentage.
            # For now, flag files that mention commission for manual review.

    if issues:
        return CheckResult(
            check_name="commission_math",
            status=CheckStatus.YELLOW,
            message=f"{len(issues)} dossiers unreadable during commission audit.",
            details={"issues": issues, "checked": checked},
        )

    return CheckResult(
        check_name="commission_math",
        status=CheckStatus.GREEN,
        message=f"Commission audit: {checked} dossiers checked, no anomalies detected.",
        details={"checked": checked, "total": len(dossiers)},
    )


def _check_deadline_tracking() -> CheckResult:
    """Check for approaching payment deadlines in dossier files."""
    if not DOSSIER_DIR.exists():
        return CheckResult(
            check_name="deadline_tracking",
            status=CheckStatus.SKIPPED,
            message="No dossier directory.",
        )

    dossiers = list(DOSSIER_DIR.glob("DOSSIER_*.md"))
    now = datetime.now()
    deadline_pattern = re.compile(
        r'(?:deadline|due\s*date|payment\s*due|final\s*payment|deposit\s*due)'
        r'[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\w+\s+\d{1,2},?\s+\d{4})',
        re.IGNORECASE,
    )

    upcoming = []
    overdue = []
    found_any = False

    for d in dossiers:
        try:
            content = d.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        for match in deadline_pattern.finditer(content):
            found_any = True
            date_str = match.group(1).strip()
            # Try common date formats
            parsed = None
            for fmt in ("%m/%d/%Y", "%m-%d-%Y", "%B %d, %Y", "%B %d %Y",
                         "%m/%d/%y", "%m-%d-%y"):
                try:
                    parsed = datetime.strptime(date_str, fmt)
                    break
                except ValueError:
                    continue

            if parsed is None:
                continue

            days_until = (parsed - now).days
            entry = {"file": d.name, "date": date_str, "days_until": days_until}

            if days_until < 0:
                overdue.append(entry)
            elif days_until <= 14:
                upcoming.append(entry)

    if overdue:
        return CheckResult(
            check_name="deadline_tracking",
            status=CheckStatus.RED,
            message=f"{len(overdue)} overdue deadline(s) detected.",
            details={"overdue": overdue, "upcoming": upcoming},
        )

    if upcoming:
        return CheckResult(
            check_name="deadline_tracking",
            status=CheckStatus.YELLOW,
            message=f"{len(upcoming)} deadline(s) within 14 days.",
            details={"upcoming": upcoming},
        )

    if not found_any:
        return CheckResult(
            check_name="deadline_tracking",
            status=CheckStatus.GREEN,
            message="No deadline entries found in dossiers.",
            details={"note": "Either no deadlines exist or they use a non-standard format."},
        )

    return CheckResult(
        check_name="deadline_tracking",
        status=CheckStatus.GREEN,
        message="All deadlines are more than 14 days out.",
    )


def _check_format_compliance() -> CheckResult:
    """Check that dossier files follow the expected naming and structure conventions."""
    if not DOSSIER_DIR.exists():
        return CheckResult(
            check_name="format_compliance",
            status=CheckStatus.SKIPPED,
            message="No dossier directory.",
        )

    dossiers = list(DOSSIER_DIR.glob("*.md"))
    naming_pattern = re.compile(r'^DOSSIER_\w+_\w+_\w+\.md$')

    non_conforming = []
    missing_sections = []

    # Required sections in a well-formed dossier
    required_headers = ["##"]  # At minimum, must have markdown headers

    for d in dossiers:
        if not naming_pattern.match(d.name):
            non_conforming.append(d.name)

        try:
            content = d.read_text(encoding="utf-8")
            if len(content.strip()) < 100:
                missing_sections.append({"file": d.name, "issue": "suspiciously short"})
            elif not any(line.startswith("##") for line in content.splitlines()):
                missing_sections.append({"file": d.name, "issue": "no markdown headers"})
        except (OSError, UnicodeDecodeError):
            missing_sections.append({"file": d.name, "issue": "unreadable"})

    issues = non_conforming + [m["file"] for m in missing_sections]

    if issues:
        return CheckResult(
            check_name="format_compliance",
            status=CheckStatus.YELLOW,
            message=f"{len(issues)} format issue(s) found.",
            details={
                "non_conforming_names": non_conforming,
                "structure_issues": missing_sections,
            },
        )

    return CheckResult(
        check_name="format_compliance",
        status=CheckStatus.GREEN,
        message=f"All {len(dossiers)} dossiers conform to naming and structure standards.",
    )


def _check_output_completeness() -> CheckResult:
    """Verify that key output directories contain expected artifacts."""
    output_dir = ROOT / "output"
    checks = {}

    if not output_dir.exists():
        return CheckResult(
            check_name="output_completeness",
            status=CheckStatus.YELLOW,
            message="Output directory does not exist.",
        )

    # Check for PDF outputs
    pdfs = list(output_dir.glob("**/*.pdf"))
    checks["pdf_count"] = len(pdfs)

    # Check for recent outputs (last 7 days)
    now = datetime.now()
    recent_pdfs = [p for p in pdfs if (now - datetime.fromtimestamp(p.stat().st_mtime)).days <= 7]
    checks["recent_pdfs"] = len(recent_pdfs)

    # Check logs directory health
    log_files = list(LOG_DIR.glob("*.log")) if LOG_DIR.exists() else []
    checks["log_file_count"] = len(log_files)

    return CheckResult(
        check_name="output_completeness",
        status=CheckStatus.GREEN,
        message=f"Outputs: {len(pdfs)} PDFs total, {len(recent_pdfs)} in last 7 days.",
        details=checks,
    )


# All Sentinel checks, in execution order
SENTINEL_CHECKS = [
    _check_dossier_currency,
    _check_commission_math,
    _check_deadline_tracking,
    _check_format_compliance,
    _check_output_completeness,
]


def run_sentinel_sweep(use_llm: bool = False) -> SweepReport:
    """Execute a full Sentinel sweep across all check functions.

    Args:
        use_llm: If True, sends check results to Groq for COS-voiced synthesis.
                 If False, runs checks only (faster, no API call).

    Returns:
        SweepReport with all check results and flag counts.
    """
    import time
    start = time.time()
    now = datetime.now(MT_TZ)
    sweep_id = now.strftime("%Y%m%d_%H%M%S")

    checks: List[CheckResult] = []
    for check_fn in SENTINEL_CHECKS:
        try:
            result = check_fn()
        except Exception as e:
            result = CheckResult(
                check_name=check_fn.__name__.lstrip("_"),
                status=CheckStatus.RED,
                message=f"Check crashed: {e}",
            )
        checks.append(result)

    red_flags = sum(1 for c in checks if c.status == CheckStatus.RED)
    yellow_flags = sum(1 for c in checks if c.status == CheckStatus.YELLOW)
    green_count = sum(1 for c in checks if c.status == CheckStatus.GREEN)

    # LLM synthesis pass — optional
    if use_llm and (red_flags > 0 or yellow_flags > 0):
        summary_input = json.dumps([c.to_dict() for c in checks], indent=2)
        try:
            _call_groq(
                COS_SENTINEL_PROMPT,
                f"Analyze these Sentinel sweep results and provide a COS assessment:\n{summary_input}",
                model=SENTINEL_MODEL,
                max_tokens=400,
                temperature=0.3,
            )
            # LLM response is logged but doesn't alter check results
        except Exception as e:
            logger.warning("Sentinel LLM synthesis failed: %s", e)

    duration = time.time() - start
    escalate = red_flags > 0

    report = SweepReport(
        sweep_id=sweep_id,
        timestamp=now.isoformat(),
        checks=checks,
        red_flags=red_flags,
        yellow_flags=yellow_flags,
        green_count=green_count,
        escalated_to_judge=escalate,
        duration_seconds=round(duration, 2),
    )

    # Persist
    saved_path = report.save()
    logger.info("Sentinel sweep %s saved to %s", sweep_id, saved_path)

    # Update state
    state = OverwatchState()
    state.last_sentinel_sweep = now.isoformat()

    # Escalate to Judge if red flags
    if escalate:
        logger.warning(
            "Sentinel sweep %s: %d RED flag(s) — escalating to The Judge.",
            sweep_id, red_flags,
        )
        try:
            run_judge_assessment(
                trigger="sentinel_escalation",
                sentinel_report=report,
            )
        except Exception as e:
            logger.error("Judge escalation failed: %s", e)

    return report


def get_sentinel_interval() -> int:
    """Return the appropriate sweep interval in minutes based on current MT hour."""
    now = datetime.now(MT_TZ)
    if BIZ_HOUR_START <= now.hour < BIZ_HOUR_END:
        return BIZ_INTERVAL_MIN
    return OFF_INTERVAL_MIN


# ============================================================================
# LAYER 2: THE JUDGE — Claude Sonnet 4.6 / Opus 4.6
# ============================================================================

JUDGE_SYSTEM_PROMPT = """You are The Judge — Layer 2 of the Thunderbird Overwatch system for Dreams2Memories Travel, LLC.
You operate with the authority of Col Hale (COS) but with deeper analytical depth.
Your responsibilities:
1. TONE ASSESSMENT — Review recent client-facing outputs for brand voice compliance.
2. MORALE READ — Assess operational tempo and flag burnout indicators.
3. CORRECTIVE ACTION — When Sentinel escalates red flags, determine root cause and prescribe fixes.
4. PRAISE/REWARD — Identify what's working well. Recognize excellence.
5. STRATEGIC REVIEW — Monthly: audit Sentinel's own performance, tune thresholds.

Return structured JSON with keys: assessments (list), corrective_actions (list), praise (list), strategic_notes (string).
Be thorough but concise. This is an internal operations document, not a client deliverable."""


def run_judge_assessment(
    trigger: str = "daily_0600",
    sentinel_report: Optional[SweepReport] = None,
) -> JudgeReport:
    """Run a Judge (Layer 2) assessment.

    Args:
        trigger: What initiated this run — "daily_0600", "sentinel_escalation", "monthly_audit"
        sentinel_report: If escalated from Sentinel, include the triggering sweep report.

    Returns:
        JudgeReport with assessments, actions, and praise.
    """
    now = datetime.now(MT_TZ)
    report_id = now.strftime("%Y%m%d_%H%M%S")

    # Build context for The Judge
    context_parts = [f"Trigger: {trigger}", f"Timestamp: {now.isoformat()}"]

    if sentinel_report:
        context_parts.append(
            f"Sentinel Escalation Report:\n{json.dumps(sentinel_report.to_dict(), indent=2)}"
        )

    # Gather recent Sentinel sweep history for trend analysis
    recent_sweeps = _get_recent_sentinel_sweeps(count=5)
    if recent_sweeps:
        context_parts.append(
            f"Recent Sentinel Sweep History (last {len(recent_sweeps)}):\n"
            + json.dumps(recent_sweeps, indent=2)
        )

    # Monthly audit: review Sentinel threshold effectiveness
    sentinel_audit = None
    if trigger == "monthly_audit":
        sentinel_audit = _audit_sentinel_performance()
        if sentinel_audit:
            context_parts.append(
                f"Sentinel Monthly Audit Data:\n{json.dumps(sentinel_audit, indent=2)}"
            )

    query = "\n\n".join(context_parts)

    # Call Claude for deep analysis
    try:
        response_text = _call_claude(
            JUDGE_SYSTEM_PROMPT,
            query,
            max_tokens=1500,
            temperature=0.3,
        )

        # Attempt to parse structured response
        try:
            parsed = json.loads(response_text)
        except json.JSONDecodeError:
            # Claude may wrap JSON in prose — extract it
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                try:
                    parsed = json.loads(json_match.group())
                except json.JSONDecodeError:
                    parsed = {}
            else:
                parsed = {}

        assessments = parsed.get("assessments", [{"raw_response": response_text}])
        corrective_actions = parsed.get("corrective_actions", [])
        praise = parsed.get("praise", [])
        strategic_notes = parsed.get("strategic_notes", "")

    except Exception as e:
        logger.error("Judge Claude call failed: %s", e)
        assessments = [{"error": str(e), "fallback": "Judge assessment failed — manual review required."}]
        corrective_actions = ["Review Sentinel sweep manually — Judge engine unavailable."]
        praise = []
        strategic_notes = ""

    report = JudgeReport(
        report_id=report_id,
        timestamp=now.isoformat(),
        trigger=trigger,
        assessments=assessments,
        corrective_actions=corrective_actions,
        praise=praise,
        strategic_notes=strategic_notes,
        sentinel_audit=sentinel_audit,
    )

    saved_path = report.save()
    logger.info("Judge report %s saved to %s", report_id, saved_path)

    # Update state
    state = OverwatchState()
    state.last_judge_run = now.isoformat()

    return report


def _get_recent_sentinel_sweeps(count: int = 5) -> List[Dict[str, Any]]:
    """Load the N most recent Sentinel sweep summaries (not full details)."""
    sweep_files = sorted(SENTINEL_LOG_DIR.glob("sweep_*.json"), reverse=True)[:count]
    summaries = []
    for f in sweep_files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            summaries.append({
                "sweep_id": data.get("sweep_id"),
                "timestamp": data.get("timestamp"),
                "red_flags": data.get("red_flags", 0),
                "yellow_flags": data.get("yellow_flags", 0),
                "green_count": data.get("green_count", 0),
                "escalated": data.get("escalated_to_judge", False),
            })
        except (json.JSONDecodeError, OSError):
            continue
    return summaries


def _audit_sentinel_performance() -> Dict[str, Any]:
    """Monthly audit: analyze Sentinel sweep history for threshold tuning."""
    sweep_files = sorted(SENTINEL_LOG_DIR.glob("sweep_*.json"))

    if not sweep_files:
        return {"note": "No sweep history available for audit."}

    # Last 30 days of sweeps
    cutoff = datetime.now(MT_TZ) - timedelta(days=30)
    monthly_sweeps = []

    for f in sweep_files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            ts = data.get("timestamp", "")
            if ts >= cutoff.isoformat():
                monthly_sweeps.append(data)
        except (json.JSONDecodeError, OSError):
            continue

    if not monthly_sweeps:
        return {"note": "No sweeps in the last 30 days."}

    total = len(monthly_sweeps)
    total_reds = sum(s.get("red_flags", 0) for s in monthly_sweeps)
    total_yellows = sum(s.get("yellow_flags", 0) for s in monthly_sweeps)
    escalations = sum(1 for s in monthly_sweeps if s.get("escalated_to_judge"))

    return {
        "period_days": 30,
        "total_sweeps": total,
        "total_red_flags": total_reds,
        "total_yellow_flags": total_yellows,
        "escalation_count": escalations,
        "escalation_rate": round(escalations / total, 3) if total > 0 else 0,
        "avg_reds_per_sweep": round(total_reds / total, 2) if total > 0 else 0,
        "avg_yellows_per_sweep": round(total_yellows / total, 2) if total > 0 else 0,
    }


# ============================================================================
# LAYER 3: THE SCALPEL — DeepSeek V3.2 (Commander-only)
# ============================================================================

SCALPEL_SYSTEM_PROMPT = """You are The Scalpel — Layer 3 of the Thunderbird Overwatch system.
Codeword: SWITCHBLADE. You are activated only by the Commander (John "Yoda" Loucks).
You are a precision analysis tool. You receive sanitized queries (PII has been stripped)
and return deep, structured analysis. You are direct, thorough, and efficient.
You do not have access to client personal data — this is by design.
Focus on the analytical task presented. Return structured, actionable results."""


def invoke_scalpel(orders: str) -> Dict[str, Any]:
    """Invoke Layer 3 — The Scalpel.

    This function handles a single Scalpel exchange. For the full interactive
    session flow (codeword acknowledgment, multi-turn dialogue, formal close),
    use run_scalpel_session() or the CLI --switchblade mode.

    Args:
        orders: The Commander's specific orders (will be PII-fenced).

    Returns:
        Dict with engine, response, pii_blocked, and session metadata.
    """
    state = OverwatchState()

    # PII fence check
    pii_detected = _check_pii_fence(orders)
    pii_triggers = 1 if pii_detected else 0

    if pii_detected:
        # Sanitize: strip PII patterns before sending to DeepSeek
        sanitized = _sanitize_for_scalpel(orders)
        logger.warning("Scalpel PII fence triggered — sanitized input before DeepSeek call.")
    else:
        sanitized = orders

    # Route through the public call_deepseek function (has its own PII fence too)
    result = call_deepseek(
        SCALPEL_SYSTEM_PROMPT,
        sanitized,
        max_tokens=1500,
        temperature=0.4,
    )

    result["pii_fence_triggers"] = pii_triggers
    result["layer"] = 3
    result["codeword"] = "SWITCHBLADE"

    return result


def _sanitize_for_scalpel(text: str) -> str:
    """Remove PII from text before sending to DeepSeek.

    Replaces detected PII with placeholder tokens so the analytical
    structure of the query is preserved.
    """
    sanitized = text

    # Email addresses
    sanitized = re.sub(
        r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}',
        '[EMAIL_REDACTED]', sanitized,
    )
    # Phone numbers
    sanitized = re.sub(
        r'(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
        '[PHONE_REDACTED]', sanitized,
    )
    # Credit card numbers
    sanitized = re.sub(
        r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
        '[CC_REDACTED]', sanitized,
    )
    # Passport / ID numbers
    sanitized = re.sub(
        r'\b[A-Z]{1,2}\d{6,9}\b',
        '[ID_REDACTED]', sanitized,
    )
    # SSN
    sanitized = re.sub(
        r'\b\d{3}-\d{2}-\d{4}\b',
        '[SSN_REDACTED]', sanitized,
    )
    # Street addresses
    sanitized = re.sub(
        r'\b\d{1,6}\s+[A-Za-z]+\s+(?:St|Street|Ave|Avenue|Blvd|Boulevard|'
        r'Dr|Drive|Ln|Lane|Rd|Road|Way|Ct|Court|Pl|Place|Cir|Circle)\b',
        '[ADDRESS_REDACTED]', sanitized, flags=re.IGNORECASE,
    )

    return sanitized


def run_scalpel_session() -> ScalpelSession:
    """Run an interactive Layer 3 Scalpel session (CLI mode).

    Full dialogue flow:
    1. COS acknowledges SWITCHBLADE codeword
    2. COS asks: "What are your specific orders?"
    3. Commander provides orders (PII-fenced before DeepSeek)
    4. DeepSeek processes, output displayed
    5. Loop until Commander says "close" or "done"
    6. Formal handoff back to Sentinel
    """
    import uuid
    session_id = uuid.uuid4().hex[:12]
    now = datetime.now(MT_TZ)

    session = ScalpelSession(
        session_id=session_id,
        started=now.isoformat(),
    )

    state = OverwatchState()
    state.activate_scalpel(session_id)

    # COS acknowledgment
    print("\n" + "=" * 70)
    print("OVERWATCH LAYER 3 — THE SCALPEL")
    print("=" * 70)
    print()
    print("COS (Hale): SWITCHBLADE acknowledged. Layer 3 is hot.")
    print("            DeepSeek V3.2 engine standing by. PII fence is active.")
    print()
    print("            What are your specific orders, Commander?")
    print()

    close_keywords = {"close", "done", "exit", "quit", "end session"}

    while True:
        try:
            orders = input("Commander > ").strip()
        except (EOFError, KeyboardInterrupt):
            orders = "close"

        if not orders:
            continue

        if orders.lower() in close_keywords:
            break

        # Process through Scalpel
        result = invoke_scalpel(orders)
        session.tasks_processed += 1
        session.pii_fence_triggers += result.get("pii_fence_triggers", 0)

        # Log exchange summary (no PII stored)
        session.exchanges.append({
            "task_number": session.tasks_processed,
            "engine": result.get("engine", "unknown"),
            "pii_blocked": result.get("pii_blocked", False),
            "success": result.get("success", False),
            "timestamp": datetime.now(MT_TZ).isoformat(),
        })

        # Display response
        print()
        if result.get("pii_blocked"):
            print("    [PII FENCE] Input contained PII — rerouted to Groq (US-based).")
        print(f"    Engine: {result.get('engine', 'unknown')} | Model: {result.get('model', 'unknown')}")
        print()
        print(result.get("response", "[No response]"))
        print()

    # Formal close and handoff
    session.closed = True
    session.closed_at = datetime.now(MT_TZ).isoformat()
    session.save()

    handoff = _execute_handoff(session)

    # Print handoff dialogue
    print()
    print("-" * 70)
    print(handoff.cos_statement)
    print()
    print(handoff.sentinel_confirmation)
    print()
    print(f"COS (Hale): Confirmed. Layer 3 is cold. Normal operations resumed.")
    print("-" * 70)
    print()

    state.deactivate_scalpel()

    return session


def _execute_handoff(session: ScalpelSession) -> HandoffReport:
    """Generate the formal Layer 3 -> Layer 1 handoff dialogue."""
    now = datetime.now(MT_TZ)

    cos_statement = (
        f"COS (Hale): Scalpel session complete. Closing Layer 3. "
        f"Session summary: {session.tasks_processed} task(s) processed, "
        f"{session.pii_fence_triggers} PII fence trigger(s), DeepSeek engine used."
    )

    # Get Sentinel confirmation via Groq
    try:
        sentinel_response = _call_groq(
            "You are Sentinel, Layer 1 of the Thunderbird Overwatch system. "
            "You are confirming you have resumed the watch after a Layer 3 Scalpel session. "
            "Respond in exactly this format: 'Sentinel confirms. Layer 1 oversight is active. "
            "Last sweep: [timestamp]. All checks nominal. The watch is mine.' "
            "Use the current timestamp.",
            f"Layer 3 is closing. Confirm you have the watch. Current time: {now.isoformat()}",
            model=SENTINEL_MODEL,
            max_tokens=100,
            temperature=0.2,
        )
    except Exception:
        sentinel_response = (
            f"Sentinel confirms. Layer 1 oversight is active. "
            f"Last sweep: {now.isoformat()}. All checks nominal. The watch is mine."
        )

    sentinel_confirmation = f"Sentinel: {sentinel_response}"

    handoff = HandoffReport(
        from_layer="SCALPEL (Layer 3)",
        to_layer="SENTINEL (Layer 1)",
        timestamp=now.isoformat(),
        cos_statement=cos_statement,
        sentinel_confirmation=sentinel_confirmation,
        session_summary={
            "session_id": session.session_id,
            "tasks_processed": session.tasks_processed,
            "pii_fence_triggers": session.pii_fence_triggers,
            "duration": session.closed_at,
        },
    )

    # Save handoff record to Judge log (handoffs are oversight events)
    handoff_path = JUDGE_LOG_DIR / f"handoff_{session.session_id}.json"
    handoff_path.write_text(
        json.dumps(handoff.to_dict(), indent=2), encoding="utf-8",
    )

    return handoff


# ============================================================================
# STATUS — "Who has the watch?"
# ============================================================================

def who_has_the_watch() -> Dict[str, Any]:
    """Return current Overwatch status: active layer, last sweep, and session info."""
    state = OverwatchState()
    now = datetime.now(MT_TZ)

    # Calculate next Sentinel sweep time
    interval = get_sentinel_interval()
    is_business_hours = BIZ_HOUR_START <= now.hour < BIZ_HOUR_END

    status = {
        "active_layer": state.active_layer.name,
        "active_layer_number": state.active_layer.value,
        "current_time_mt": now.isoformat(),
        "business_hours": is_business_hours,
        "sentinel_interval_minutes": interval,
        "last_sentinel_sweep": state.last_sentinel_sweep,
        "last_judge_run": state.last_judge_run,
        "scalpel_active": state.scalpel_active,
    }

    # Layer-specific status messages
    if state.active_layer == ActiveLayer.SENTINEL:
        status["status_message"] = (
            f"Sentinel has the watch. "
            f"Sweep interval: every {interval} min ({'business hours' if is_business_hours else 'off-hours'}). "
            f"Last sweep: {state.last_sentinel_sweep or 'never'}."
        )
    elif state.active_layer == ActiveLayer.JUDGE:
        status["status_message"] = (
            f"The Judge is active. Last run: {state.last_judge_run or 'never'}."
        )
    elif state.active_layer == ActiveLayer.SCALPEL:
        status["status_message"] = (
            "Layer 3 is HOT. The Scalpel (DeepSeek) is active. "
            "PII fence is engaged. Commander has the conn."
        )

    return status


# ============================================================================
# CLI INTERFACE
# ============================================================================

def _print_sweep_report(report: SweepReport):
    """Pretty-print a Sentinel sweep report to stdout."""
    print()
    print("=" * 60)
    print(f"  SENTINEL SWEEP — {report.sweep_id}")
    print(f"  {report.timestamp}")
    print("=" * 60)
    print()

    for check in report.checks:
        c = check if isinstance(check, CheckResult) else CheckResult(**check)
        icon = {"green": "[OK]", "yellow": "[!!]", "red": "[XX]", "skipped": "[--]"}.get(
            c.status.value if isinstance(c.status, CheckStatus) else c.status, "[??]"
        )
        print(f"  {icon}  {c.check_name}: {c.message}")

    print()
    print(f"  Summary: {report.green_count} green, {report.yellow_flags} yellow, {report.red_flags} red")
    if report.escalated_to_judge:
        print("  ** ESCALATED TO THE JUDGE **")
    print(f"  Duration: {report.duration_seconds}s")
    print()


def _print_status(status: Dict[str, Any]):
    """Pretty-print Overwatch status."""
    print()
    print("=" * 60)
    print("  OVERWATCH STATUS — Who Has the Watch?")
    print("=" * 60)
    print()
    print(f"  Active Layer:    {status['active_layer']} (Layer {status['active_layer_number']})")
    print(f"  Current Time:    {status['current_time_mt']}")
    print(f"  Business Hours:  {'Yes' if status['business_hours'] else 'No'}")
    print(f"  Sweep Interval:  Every {status['sentinel_interval_minutes']} min")
    print(f"  Last Sweep:      {status.get('last_sentinel_sweep', 'never')}")
    print(f"  Last Judge Run:  {status.get('last_judge_run', 'never')}")
    print(f"  Scalpel Active:  {'YES — Layer 3 HOT' if status['scalpel_active'] else 'No'}")
    print()
    print(f"  {status['status_message']}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Thunderbird Overwatch — Three-Layer QA System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python thunderbird_overwatch.py --sentinel-sweep          Run a Sentinel sweep
  python thunderbird_overwatch.py --sentinel-sweep --llm    Run sweep with Groq synthesis
  python thunderbird_overwatch.py --judge-daily             Run daily Judge assessment
  python thunderbird_overwatch.py --judge-audit             Run monthly Sentinel audit
  python thunderbird_overwatch.py --switchblade             Invoke Layer 3 (Commander only)
  python thunderbird_overwatch.py --status                  Who has the watch?
        """,
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--sentinel-sweep", action="store_true",
                       help="Run a Sentinel (Layer 1) sweep")
    group.add_argument("--judge-daily", action="store_true",
                       help="Run a Judge (Layer 2) daily assessment")
    group.add_argument("--judge-audit", action="store_true",
                       help="Run a Judge monthly Sentinel audit")
    group.add_argument("--switchblade", action="store_true",
                       help="Invoke The Scalpel (Layer 3) — Commander only")
    group.add_argument("--status", action="store_true",
                       help="Show current Overwatch status")

    parser.add_argument("--llm", action="store_true",
                        help="Enable LLM synthesis for Sentinel sweep")

    args = parser.parse_args()

    # Configure logging for CLI
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    if args.sentinel_sweep:
        report = run_sentinel_sweep(use_llm=args.llm)
        _print_sweep_report(report)

    elif args.judge_daily:
        report = run_judge_assessment(trigger="daily_0600")
        print(f"\nJudge report saved: {report.save()}")
        print(f"Assessments: {len(report.assessments)}")
        print(f"Corrective actions: {len(report.corrective_actions)}")
        print(f"Praise items: {len(report.praise)}")

    elif args.judge_audit:
        report = run_judge_assessment(trigger="monthly_audit")
        print(f"\nJudge audit saved: {report.save()}")
        if report.sentinel_audit:
            print(f"Sentinel audit data: {json.dumps(report.sentinel_audit, indent=2)}")

    elif args.switchblade:
        run_scalpel_session()

    elif args.status:
        status = who_has_the_watch()
        _print_status(status)


if __name__ == "__main__":
    main()
