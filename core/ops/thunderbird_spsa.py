#!/usr/bin/env python3
"""
SPSA — Standard Problem Solving Approach Engine
Integrated operational problem-solving framework for D2M.

Workflow:
1. Scan Overwatch/Judge for RED+YELLOW flags
2. Intake problem → structure via SPSA brief
3. Generate options, recommend solution
4. Submit to Commander for decision (Telegram for RED, daily digest for YELLOW)
5. Implement with risk-based gate
6. Document and close case

Architecture:
- Intake engine: Flag → SPSA brief
- Decision gate: Risk-based escalation
- Archive: JSON (local) + Google Sheets (trending)
- Integration: Telegram (alerts), Morning brief, EOD summary, Weekly deep dive
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict
import hashlib

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - spsa - %(levelname)s - %(message)s"
)
logger = logging.getLogger("spsa")

# Paths
ROOT = Path("/home/john/Thunderbird")
SPSA_LOG_DIR = ROOT / "logs" / "spsa"
SPSA_LOG_DIR.mkdir(parents=True, exist_ok=True)
ACTIVE_CASES_FILE = SPSA_LOG_DIR / "active_cases.json"

# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class SPSACase:
    """SPSA Case record"""
    case_id: str
    timestamp_created: str
    severity: str  # RED, YELLOW, GREEN
    source: str  # overwatch, judge, manual, incubator, mcp, scheduler, dani

    problem_statement: str
    factors: List[str]  # Root causes + contributing factors

    options: List[Dict[str, str]]  # [{name, description, tradeoff}, ...]
    recommendation: str
    recommendation_rationale: str
    timeline_hours: int
    risk_summary: str

    status: str  # OPEN, UNDER_REVIEW, DECIDED, IMPLEMENTING, CLOSED
    decision: Optional[str] = None  # Approved, Modified, Rejected
    decision_notes: Optional[str] = None

    implemented_actions: Optional[List[str]] = None
    outcome: Optional[str] = None
    lessons_learned: Optional[str] = None
    timestamp_closed: Optional[str] = None

    def to_brief(self) -> str:
        """Format as SPSA Brief"""
        brief = f"""CASE ID: {self.case_id}
STATUS: {self.status}
SEVERITY: {self.severity}

═══════════════════════════════════════════════════════════════

DEFINE THE PROBLEM
{self.problem_statement}

DISCUSS FACTORS BEARING ON THE PROBLEM
"""
        for factor in self.factors:
            brief += f"• {factor}\n"

        brief += "\nGENERATE OPTIONS FOR SOLUTION\n"
        for i, opt in enumerate(self.options, 1):
            brief += f"{i}. {opt['name']} — {opt['description']}\n   Trade-off: {opt['tradeoff']}\n"

        brief += f"\nRECOMMEND A SOLUTION\nOption {self._get_recommended_option_num()} is best because: {self.recommendation_rationale}\nTimeline: {self.timeline_hours}h | Risk: {self.risk_summary}\n"

        if self.decision:
            brief += f"\n═══════════════════════════════════════════════════════════════\n\nDECISION\n☑ {self.decision}\n"
            if self.decision_notes:
                brief += f"Notes: {self.decision_notes}\n"

        if self.implemented_actions:
            brief += "\nIMPLEMENTATION\n"
            for i, action in enumerate(self.implemented_actions, 1):
                brief += f"Action {i}: {action}\n"

        if self.timestamp_closed:
            brief += f"\n═══════════════════════════════════════════════════════════════\n\nCLOSED: {self.timestamp_closed}\n"
            if self.outcome:
                brief += f"Outcome: {self.outcome}\n"
            if self.lessons_learned:
                brief += f"Lessons Learned: {self.lessons_learned}\n"

        brief += "\n— Hale, COS | D2M Travel"
        return brief

    def _get_recommended_option_num(self) -> int:
        """Extract option number from recommendation"""
        for i, opt in enumerate(self.options, 1):
            if opt['name'] in self.recommendation:
                return i
        return 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON storage"""
        return asdict(self)


# ============================================================================
# SPSA INTAKE & ANALYSIS
# ============================================================================

def generate_case_id() -> str:
    """Generate unique case ID: SPSA-YYYYMMDD-NNNNN"""
    now = datetime.now()
    date_str = now.strftime("%Y%m%d")
    # Use hash of timestamp to create pseudo-random suffix
    timestamp_ms = str(int(now.timestamp() * 1000))
    hash_suffix = hashlib.md5(timestamp_ms.encode()).hexdigest()[:5].upper()
    return f"SPSA-{date_str}-{hash_suffix}"


def intake_problem(
    severity: str,
    source: str,
    problem_statement: str,
    factors: List[str],
    options: List[Dict[str, str]],
    recommendation: str,
    recommendation_rationale: str,
    timeline_hours: int = 1,
    risk_summary: str = "Low"
) -> SPSACase:
    """
    Intake a problem and create SPSA case.

    Args:
        severity: RED, YELLOW, GREEN
        source: Where problem came from (overwatch, judge, manual, etc.)
        problem_statement: Concise 1-2 sentence problem
        factors: List of root causes/contributing factors
        options: List of dicts: {name, description, tradeoff}
        recommendation: Recommended option name
        recommendation_rationale: Why this option
        timeline_hours: Estimated implementation time
        risk_summary: Risk level/summary

    Returns:
        SPSACase object
    """
    case = SPSACase(
        case_id=generate_case_id(),
        timestamp_created=datetime.now().isoformat(),
        severity=severity,
        source=source,
        problem_statement=problem_statement,
        factors=factors,
        options=options,
        recommendation=recommendation,
        recommendation_rationale=recommendation_rationale,
        timeline_hours=timeline_hours,
        risk_summary=risk_summary,
        status="OPEN",
    )

    logger.info(f"Intake: {case.case_id} ({severity} from {source})")
    _save_case(case)
    return case


def _save_case(case: SPSACase):
    """Save case to JSON log"""
    case_file = SPSA_LOG_DIR / f"{case.case_id}.json"
    case_file.write_text(json.dumps(case.to_dict(), indent=2, default=str))
    logger.info(f"Saved: {case_file}")


def load_case(case_id: str) -> Optional[SPSACase]:
    """Load case from JSON"""
    case_file = SPSA_LOG_DIR / f"{case_id}.json"
    if not case_file.exists():
        return None
    data = json.loads(case_file.read_text())
    return SPSACase(**data)


def get_active_cases(severity: Optional[str] = None) -> List[SPSACase]:
    """Get all active cases, optionally filtered by severity"""
    active = []
    for case_file in SPSA_LOG_DIR.glob("SPSA-*.json"):
        data = json.loads(case_file.read_text())
        case = SPSACase(**data)
        if case.status in ["OPEN", "UNDER_REVIEW", "DECIDED", "IMPLEMENTING"]:
            if severity is None or case.severity == severity:
                active.append(case)
    return sorted(active, key=lambda c: c.timestamp_created, reverse=True)


# ============================================================================
# DECISION GATE
# ============================================================================

def classify_risk(case: SPSACase) -> str:
    """
    Classify risk level for approval gate.

    Returns: "LOW", "MEDIUM", "HIGH"
    """
    # LOW: < 30 min, reversible, no data change, no config change
    # MEDIUM: 30 min - 2 hours, config change, user-facing impact
    # HIGH: > 2 hours, destructive, financial impact, database change

    if case.timeline_hours < 0.5 and "reversible" in case.risk_summary.lower():
        return "LOW"
    elif case.timeline_hours <= 2 and "config" in case.risk_summary.lower():
        return "MEDIUM"
    else:
        return "HIGH"


def needs_approval(case: SPSACase) -> bool:
    """
    Risk-based escalation: does this need Commander approval?

    - LOW: No (I implement, report after)
    - MEDIUM: Yes (Telegram brief, wait for OK)
    - HIGH: Yes (SPSA brief, formal decision gate)
    """
    risk = classify_risk(case)
    return risk in ["MEDIUM", "HIGH"]


# ============================================================================
# IMPLEMENTATION & CLOSURE
# ============================================================================

def update_case_status(
    case_id: str,
    status: str,
    decision: Optional[str] = None,
    decision_notes: Optional[str] = None
):
    """Update case status (DECIDED, IMPLEMENTING, CLOSED)"""
    case = load_case(case_id)
    if not case:
        logger.error(f"Case not found: {case_id}")
        return

    case.status = status
    if decision:
        case.decision = decision
    if decision_notes:
        case.decision_notes = decision_notes

    _save_case(case)
    logger.info(f"Updated {case_id}: status={status}")


def close_case(
    case_id: str,
    outcome: str,
    lessons_learned: Optional[str] = None
):
    """Close case with outcome and lessons"""
    case = load_case(case_id)
    if not case:
        logger.error(f"Case not found: {case_id}")
        return

    case.status = "CLOSED"
    case.timestamp_closed = datetime.now().isoformat()
    case.outcome = outcome
    case.lessons_learned = lessons_learned

    _save_case(case)
    logger.info(f"Closed {case_id}: {outcome}")


def log_implementation_action(case_id: str, action: str):
    """Log a verbalized implementation action"""
    case = load_case(case_id)
    if not case:
        logger.error(f"Case not found: {case_id}")
        return

    if case.implemented_actions is None:
        case.implemented_actions = []

    case.implemented_actions.append(action)
    _save_case(case)


# ============================================================================
# ARCHIVE & TRENDING (Google Sheets integration)
# ============================================================================

def get_closed_cases_for_week() -> List[SPSACase]:
    """Get all cases closed in the last 7 days (for weekly summary)"""
    closed = []
    cutoff = datetime.now() - timedelta(days=7)

    for case_file in SPSA_LOG_DIR.glob("SPSA-*.json"):
        data = json.loads(case_file.read_text())
        case = SPSACase(**data)
        if case.status == "CLOSED" and case.timestamp_closed:
            closed_date = datetime.fromisoformat(case.timestamp_closed)
            if closed_date >= cutoff:
                closed.append(case)

    return sorted(closed, key=lambda c: c.timestamp_closed, reverse=True)


def export_to_sheets_format() -> List[Dict[str, Any]]:
    """
    Export all cases to Google Sheets format.
    Each row: Case ID, Severity, Status, Problem, Decision, Outcome, Days to Close
    """
    rows = []
    for case_file in SPSA_LOG_DIR.glob("SPSA-*.json"):
        data = json.loads(case_file.read_text())
        case = SPSACase(**data)

        days_to_close = None
        if case.timestamp_closed:
            created = datetime.fromisoformat(case.timestamp_created)
            closed = datetime.fromisoformat(case.timestamp_closed)
            days_to_close = (closed - created).days

        rows.append({
            "Case ID": case.case_id,
            "Severity": case.severity,
            "Source": case.source,
            "Status": case.status,
            "Problem": case.problem_statement[:100],  # Truncate for readability
            "Decision": case.decision or "Pending",
            "Outcome": case.outcome or "-",
            "Days to Close": days_to_close or "-",
            "Created": case.timestamp_created[:10],  # Date only
            "Closed": case.timestamp_closed[:10] if case.timestamp_closed else "-",
        })

    return rows


# ============================================================================
# EXAMPLE: Test SPSA with scheduler syntax error case
# ============================================================================

def example_scheduler_syntax_fix():
    """
    Example SPSA case: Scheduler syntax error in thunderbird_payment_alerts.py
    (This was the real issue we just fixed)
    """
    case = intake_problem(
        severity="RED",
        source="manual",
        problem_statement="thunderbird-scheduler.service fails to start: SyntaxError in thunderbird_payment_alerts.py line 161 (invalid Unicode character U+2011 in comment)",
        factors=[
            "Comment block at EOF not properly formatted as Python comments",
            "Non-breaking hyphen (U+2011) used instead of regular hyphen",
            "Scheduler import fails → entire daily task pipeline blocked",
            "Impact: Morning brief doesn't generate, intel sweeps don't run, all timers offline"
        ],
        options=[
            {
                "name": "Fix comment formatting",
                "description": "Convert invalid comment block to proper Python comments, replace Unicode hyphen",
                "tradeoff": "2 minutes, zero risk, immediately restores service"
            },
            {
                "name": "Comment out entire block",
                "description": "Remove documentation entirely to get past syntax error",
                "tradeoff": "1 minute, loses documentation, need to re-add later"
            },
            {
                "name": "Move documentation to separate file",
                "description": "Extract comments to docs/AGENTS_MODEL_GUIDE.md, clean up source file",
                "tradeoff": "10 minutes, better long-term, maintains docs"
            }
        ],
        recommendation="Fix comment formatting",
        recommendation_rationale="Fastest path to restore critical service with zero risk. Re-enables entire scheduler pipeline immediately.",
        timeline_hours=0.1,  # 6 minutes
        risk_summary="Low — syntax fix only, no logic change"
    )

    return case


if __name__ == "__main__":
    # Test intake
    case = example_scheduler_syntax_fix()
    print("\n" + case.to_brief() + "\n")
    print(f"Risk level: {classify_risk(case)}")
    print(f"Needs approval: {needs_approval(case)}")
