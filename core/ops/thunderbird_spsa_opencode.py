#!/usr/bin/env python3
"""
SPSA ↔ OpenCode Integration
============================
High-level API for OpenCode to:
  - Create SPSA cases from operational findings
  - Query cases needing execution
  - Execute approved cases with action handlers
  - Log implementation results and lessons learned
"""

import json
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Callable, Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from thunderbird_spsa import (
    generate_case_id,
    intake_problem,
    load_case,
    get_active_cases,
    classify_risk,
    update_case_status,
    log_implementation_action,
    close_case,
    SPSACase,
)

logger = logging.getLogger("spsa_opencode")

ROOT = Path("/home/john/Thunderbird")


class OpenCodeSPSAError(Exception):
    """SPSA-OpenCode integration error."""
    pass


def create_case_from_opencode(
    problem: str,
    factors: List[str],
    options: List[Dict[str, str]],
    recommendation: Optional[str] = None,
    timeline_hours: float = 1.0,
    risk_summary: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Create SPSA case from OpenCode scan result.

    Args:
        problem: Problem statement (1-2 sentences)
        factors: List of contributing factors (3-5 bullets)
        options: List of dicts with 'name', 'description', 'tradeoff' keys
        recommendation: Recommended option name (optional; defaults to first option)
        timeline_hours: Estimated hours to resolve (default: 1.0)
        risk_summary: Risk assessment (optional)
        tags: List of tags for categorization (e.g., ['opencode', 'api', 'external'])

    Returns:
        Dict with 'case_id', 'severity', 'status' on success
        Dict with 'error' on failure

    Example:
        create_case_from_opencode(
            problem="Claude token refresh daemon inactive for 45 minutes",
            factors=[
                "systemd timer not in 'active (waiting)' state",
                "Last successful run was 3 hours ago",
                "Token expiry in ~2 hours without refresh"
            ],
            options=[
                {"name": "Restart daemon", "description": "systemctl --user restart claude-token-refresh.timer", "tradeoff": "5 min"},
                {"name": "Investigate logs", "description": "journalctl -u claude-token-refresh.timer -20", "tradeoff": "15+ min"},
            ],
            recommendation="Restart daemon",
            timeline_hours=0.25,
            risk_summary="LOW - safe service restart, no impact to running tasks",
            tags=["opencode", "auth", "daemon"]
        )
    """
    try:
        if not problem or not factors or not options:
            raise OpenCodeSPSAError("problem, factors, and options are required")

        if len(factors) < 2:
            raise OpenCodeSPSAError("Must provide at least 2 factors")

        if len(options) < 2:
            raise OpenCodeSPSAError("Must provide at least 2 options")

        # Validate options structure
        for opt in options:
            if not all(k in opt for k in ["name", "description", "tradeoff"]):
                raise OpenCodeSPSAError("Each option must have 'name', 'description', 'tradeoff'")

        # Use first option as recommendation if not specified
        if not recommendation:
            recommendation = options[0]["name"]

        # Create case via intake_problem function
        case = intake_problem(
            problem_statement=problem,
            factors=factors,
            options=options,
            recommendation=recommendation,
            recommendation_rationale=f"Recommended by OpenCode scan. Tags: {', '.join(tags) if tags else 'none'}",
            timeline_hours=timeline_hours,
            risk_summary=risk_summary or "Assessment pending",
            source="opencode",  # Mark as OpenCode-originated
        )

        logger.info(f"✅ Created case {case.case_id} from OpenCode scan")
        return {
            "case_id": case.case_id,
            "severity": case.severity,
            "status": case.status,
            "tags": tags or [],
        }

    except Exception as e:
        logger.error(f"Failed to create SPSA case from OpenCode: {e}")
        return {"error": str(e)}


def get_cases_for_opencode_execution(max_risk: str = "MEDIUM") -> List[SPSACase]:
    """
    Get SPSA cases that OpenCode can execute.

    Filters for:
    - Status: DECIDED (waiting for implementation)
    - Risk: LOW or MEDIUM (HIGH requires human decision)
    - Origin: opencode or scheduler (prefer self-created cases)

    Args:
        max_risk: Maximum risk level to auto-execute ("LOW" or "MEDIUM")

    Returns:
        List of SPSACase objects ready for execution
    """
    decided_cases = get_active_cases(severity=None)  # Get all active
    decided_cases = [c for c in decided_cases if c.status == "DECIDED"]

    executable = []
    risk_order = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}

    for case in decided_cases:
        case_risk = classify_risk(case)
        if risk_order.get(case_risk, 99) > risk_order.get(max_risk, 99):
            continue  # Too risky

        # Prefer OpenCode-originated cases, but accept any DECIDED case
        executable.append(case)

    return executable


def execute_case_with_handler(
    case_id: str,
    handler_func: Callable[[SPSACase], Dict[str, Any]],
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Execute a SPSA case using a provided handler function.

    Args:
        case_id: Case ID (e.g., "SPSA-20260502-25089")
        handler_func: Async or sync function that takes SPSACase and returns
                     {"success": bool, "result": str, "error": str (optional)}
        dry_run: If True, log actions but don't actually execute

    Returns:
        Dict with execution result and case status

    Example:
        def restart_token_daemon(case: SPSACase) -> Dict:
            import subprocess
            try:
                result = subprocess.run(
                    ["systemctl", "--user", "restart", "claude-token-refresh.timer"],
                    capture_output=True, text=True, timeout=30
                )
                return {"success": True, "result": result.stdout}
            except Exception as e:
                return {"success": False, "error": str(e)}

        result = execute_case_with_handler(
            case_id="SPSA-20260502-25089",
            handler_func=restart_token_daemon
        )
    """
    try:
        case = load_case(case_id)
        if not case:
            return {"error": f"Case not found: {case_id}"}

        if case.status != "DECIDED":
            return {"error": f"Case must be DECIDED for execution (current: {case.status})"}

        logger.info(f"Executing case {case_id}: {case.recommendation}")

        if dry_run:
            logger.info(f"[DRY RUN] Would execute: {case.recommendation}")
            return {
                "case_id": case_id,
                "dry_run": True,
                "recommendation": case.recommendation,
            }

        # Call handler function
        update_case_status(case_id, "IMPLEMENTING", decision=f"Executing: {case.recommendation}")
        handler_result = handler_func(case)

        if handler_result.get("success"):
            # Log successful action
            log_implementation_action(
                case_id=case_id,
                action=case.recommendation,
                action_description=handler_result.get("result", "Execution completed"),
                status="SUCCESS"
            )
            logger.info(f"✅ Case {case_id} executed successfully")
            return {
                "case_id": case_id,
                "status": "IMPLEMENTED",
                "result": handler_result.get("result", "Success"),
            }
        else:
            # Log failed action
            log_implementation_action(
                case_id=case_id,
                action=case.recommendation,
                action_description=handler_result.get("error", "Execution failed"),
                status="FAILED"
            )
            logger.error(f"❌ Case {case_id} execution failed: {handler_result.get('error')}")
            return {
                "case_id": case_id,
                "status": "FAILED",
                "error": handler_result.get("error", "Unknown error"),
            }

    except Exception as e:
        logger.error(f"Exception during case execution: {e}")
        return {"error": str(e)}


def report_case_outcome(
    case_id: str,
    outcome: str,
    lessons_learned: Optional[List[str]] = None,
    close_case_flag: bool = True,
) -> Dict[str, Any]:
    """
    Report outcome of executed case and optionally close it.

    Args:
        case_id: Case ID
        outcome: Brief outcome description (1-2 sentences)
        lessons_learned: List of lessons for future reference
        close_case_flag: If True, mark case as CLOSED

    Returns:
        Dict with case status after update
    """
    try:
        case = load_case(case_id)
        if not case:
            return {"error": f"Case not found: {case_id}"}

        # Update case with outcome
        case.outcome = outcome
        if lessons_learned:
            case.lessons_learned = lessons_learned

        # Save updated case
        case_file = Path(f"/home/john/Thunderbird/logs/spsa/{case_id}.json")
        case_file.parent.mkdir(parents=True, exist_ok=True)
        case_file.write_text(case.to_json())

        if close_case_flag:
            close_case(case_id, outcome=outcome)
            logger.info(f"✅ Case {case_id} closed with outcome: {outcome[:50]}...")
            return {
                "case_id": case_id,
                "status": "CLOSED",
                "outcome": outcome,
            }
        else:
            update_case_status(case_id, "COMPLETED")
            logger.info(f"✅ Case {case_id} marked completed")
            return {
                "case_id": case_id,
                "status": "COMPLETED",
                "outcome": outcome,
            }

    except Exception as e:
        logger.error(f"Failed to report outcome for {case_id}: {e}")
        return {"error": str(e)}
