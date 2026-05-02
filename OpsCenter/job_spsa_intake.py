#!/usr/bin/env python3
"""
SPSA Daily Intake Job — Scans for RED+YELLOW flags and creates cases
Runs via systemd timer at 0630 MT and 1800 MT
Feeds SPSA case pipeline for decision framework
"""

import json
import logging
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.ops.thunderbird_spsa import intake_problem, get_active_cases
from opencode_spsa_intake_scans import run_all_opencode_scans

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - spsa_intake - %(levelname)s - %(message)s"
)
logger = logging.getLogger("spsa_intake")

ROOT = Path("/home/john/Thunderbird")


def scan_system_logs_for_errors() -> list:
    """Scan recent systemd logs for ERROR/FAILED events"""
    issues = []
    try:
        # Get last 2 hours of logs (covers both intake windows)
        cmd = [
            "journalctl", "--user", "--since", "2 hours ago",
            "--priority", "err",
            "--no-pager", "-n", "100"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

        if result.returncode == 0 and result.stdout:
            lines = result.stdout.split('\n')
            for line in lines:
                if 'ERROR' in line or 'FAILED' in line or 'error' in line:
                    # Extract service/unit name if possible
                    if '(' in line and ')' in line:
                        start = line.rfind('(')
                        end = line.rfind(')')
                        service = line[start+1:end]
                    else:
                        service = "unknown"

                    issues.append({
                        'type': 'system_error',
                        'service': service,
                        'timestamp': datetime.now().isoformat(),
                        'source': 'systemd_logs',
                        'message': line[:200]
                    })
    except Exception as e:
        logger.warning(f"Failed to scan systemd logs: {e}")

    return issues


def scan_hale_state_for_blockers() -> list:
    """Scan hale_state.json for task blockers and system health issues"""
    issues = []
    state_file = ROOT / "hale_state.json"

    if not state_file.exists():
        return issues

    try:
        state = json.loads(state_file.read_text())

        # Check for MCP offline
        wing_health = state.get("wing_health", {})
        if "ERROR" in wing_health.get("mcp_server", ""):
            issues.append({
                'type': 'system_health',
                'component': 'mcp_server',
                'timestamp': datetime.now().isoformat(),
                'source': 'hale_state',
                'severity': 'RED',
                'message': 'MCP server offline — blocks all integrations'
            })

        # Check for open tasks with errors
        open_tasks = state.get("open_tasks", [])
        for task in open_tasks:
            if isinstance(task, dict) and 'error' in task:
                issues.append({
                    'type': 'task_error',
                    'task': task.get('name', 'unknown'),
                    'error': task.get('error'),
                    'timestamp': datetime.now().isoformat(),
                    'source': 'hale_state',
                    'severity': 'YELLOW'
                })

        # Check TESS auth
        financial = state.get("financial_pulse", {})
        if "error" in financial.get("raw_snippet", "").lower():
            issues.append({
                'type': 'auth_required',
                'component': 'tess',
                'timestamp': datetime.now().isoformat(),
                'source': 'hale_state',
                'severity': 'YELLOW',
                'message': 'TESS authentication required'
            })

    except Exception as e:
        logger.warning(f"Failed to scan hale_state: {e}")

    return issues


def scan_mission_board_for_red() -> list:
    """Scan mission_board.json for RED priority items"""
    issues = []
    board_file = ROOT / "OpsCenter" / "mission_board.json"

    if not board_file.exists():
        return issues

    try:
        board = json.loads(board_file.read_text())
        missions = board.get("missions", [])

        for mission in missions:
            if mission.get("priority") == "RED" and mission.get("status") != "RESOLVED":
                issues.append({
                    'type': 'mission_red',
                    'mission_id': mission.get('id'),
                    'title': mission.get('title'),
                    'description': mission.get('description'),
                    'timestamp': datetime.now().isoformat(),
                    'source': 'mission_board',
                    'severity': 'RED'
                })

    except Exception as e:
        logger.warning(f"Failed to scan mission board: {e}")

    return issues


def issues_to_spsa_cases(issues: list) -> list:
    """Convert discovered issues into SPSA cases"""
    cases = []

    for issue in issues:
        try:
            issue_type = issue.get('type')
            severity = issue.get('severity', 'YELLOW')

            # Map issue types to SPSA cases
            if issue_type == 'system_error':
                case = intake_problem(
                    severity=severity,
                    source='incubator',
                    problem_statement=f"Service error: {issue.get('service')} is failing",
                    factors=[
                        f"Error from systemd logs at {issue['timestamp'][:19]}",
                        f"Impact: {issue['service']} unavailable",
                    ],
                    options=[
                        {
                            "name": "Restart service",
                            "description": f"systemctl --user restart {issue['service']}",
                            "tradeoff": "5 minutes, immediate recovery"
                        },
                        {
                            "name": "Manual debug and fix",
                            "description": "Investigate root cause in logs and fix underlying issue",
                            "tradeoff": "30+ minutes, addresses root cause"
                        }
                    ],
                    recommendation="Restart service",
                    recommendation_rationale="Fastest recovery path. If issue recurs, escalate to manual debug.",
                    timeline_hours=0.1,
                    risk_summary="Low — service restart is reversible"
                )
                cases.append(case)

            elif issue_type == 'system_health':
                component = issue.get('component')
                case = intake_problem(
                    severity='RED',
                    source='incubator',
                    problem_statement=f"{component.upper()} is offline",
                    factors=[
                        f"Detected in hale_state.json at {issue['timestamp'][:19]}",
                        f"Impact: All integrations depending on {component} are blocked",
                    ],
                    options=[
                        {
                            "name": "Restart service",
                            "description": f"systemctl --user restart thunderbird-mcp.service",
                            "tradeoff": "5 minutes"
                        },
                        {
                            "name": "Investigate root cause",
                            "description": "Check service logs and systemd status",
                            "tradeoff": "30+ minutes"
                        }
                    ],
                    recommendation="Restart service",
                    recommendation_rationale="MCP is critical path. Fast recovery + debug after.",
                    timeline_hours=0.2,
                    risk_summary="Medium — blocks client-facing systems"
                )
                cases.append(case)

            elif issue_type == 'task_error':
                case = intake_problem(
                    severity='YELLOW',
                    source='incubator',
                    problem_statement=f"Task '{issue.get('task')}' errored: {issue.get('error')}",
                    factors=[
                        f"Error detected in hale_state.open_tasks at {issue['timestamp'][:19]}",
                        f"Task unable to complete: {issue.get('error')}",
                    ],
                    options=[
                        {
                            "name": "Retry task",
                            "description": "Clear error state and re-run task",
                            "tradeoff": "10 minutes"
                        },
                        {
                            "name": "Investigate and fix",
                            "description": "Understand error root cause and apply fix",
                            "tradeoff": "30+ minutes"
                        }
                    ],
                    recommendation="Retry task",
                    recommendation_rationale="Transient errors often self-resolve. If recurring, escalate to debug.",
                    timeline_hours=0.25,
                    risk_summary="Low — isolated task failure"
                )
                cases.append(case)

            elif issue_type == 'auth_required':
                case = intake_problem(
                    severity='YELLOW',
                    source='incubator',
                    problem_statement=f"Authentication required: {issue.get('component').upper()}",
                    factors=[
                        f"Auth token expired or missing for {issue.get('component')}",
                        f"Detected at {issue['timestamp'][:19]}",
                        "Impact: Financial data collection and reporting offline"
                    ],
                    options=[
                        {
                            "name": "Re-authenticate",
                            "description": f"Run: python3 thunderbird_tess.py --authorize",
                            "tradeoff": "5-10 minutes, restores data collection"
                        },
                        {
                            "name": "Defer until next window",
                            "description": "Wait for next scheduled auth check",
                            "tradeoff": "24 hours delay in financial reporting"
                        }
                    ],
                    recommendation="Re-authenticate",
                    recommendation_rationale="Financial data is mission-critical. Re-auth restores pipeline.",
                    timeline_hours=0.15,
                    risk_summary="Medium — delays reporting but not client-blocking"
                )
                cases.append(case)

            elif issue_type == 'mission_red':
                case = intake_problem(
                    severity='RED',
                    source='judge',
                    problem_statement=f"Mission RED: {issue.get('title')}",
                    factors=[
                        f"Mission board flagged as RED at {issue['timestamp'][:19]}",
                        f"Description: {issue.get('description')[:100]}",
                    ],
                    options=[
                        {
                            "name": "Escalate to Commander",
                            "description": "Send full mission brief to Commander for decision",
                            "tradeoff": "Immediate, requires Commander action"
                        },
                        {
                            "name": "Investigate and recommend",
                            "description": "Deep dive into mission, develop options, recommend approach",
                            "tradeoff": "30+ minutes, provides structured decision framework"
                        }
                    ],
                    recommendation="Investigate and recommend",
                    recommendation_rationale="Structured SPSA approach provides better decision data than raw escalation.",
                    timeline_hours=1.0,
                    risk_summary="High — RED missions block operations"
                )
                cases.append(case)

            elif issue_type == 'opencode_scan':
                problem = issue.get('problem')
                factors = issue.get('factors', [])
                severity = issue.get('severity', 'YELLOW')

                case = intake_problem(
                    severity=severity,
                    source='opencode',
                    problem_statement=problem,
                    factors=factors if factors else ["OpenCode scan result"],
                    options=[
                        {
                            "name": "Address immediately",
                            "description": "Execute fix or mitigation recommended by OpenCode",
                            "tradeoff": "Varies by problem (minutes to hours)"
                        },
                        {
                            "name": "Defer and monitor",
                            "description": "Keep on watch list, address in next maintenance window",
                            "tradeoff": "Risk may escalate, temporary workaround may be needed"
                        }
                    ],
                    recommendation="Address immediately" if severity == 'RED' else "Address immediately",
                    recommendation_rationale=f"OpenCode identified this as {severity} priority.",
                    timeline_hours=0.5 if severity == 'RED' else 2.0,
                    risk_summary=f"OpenCode severity: {severity}"
                )
                cases.append(case)

        except Exception as e:
            logger.error(f"Failed to create SPSA case for issue {issue}: {e}")

    return cases


def main():
    """Run SPSA intake job"""
    logger.info("=== SPSA INTAKE JOB STARTING ===")

    all_issues = []

    # Scan all sources
    logger.info("Scanning systemd logs...")
    all_issues.extend(scan_system_logs_for_errors())

    logger.info("Scanning hale_state for blockers...")
    all_issues.extend(scan_hale_state_for_blockers())

    logger.info("Scanning mission board for RED items...")
    all_issues.extend(scan_mission_board_for_red())

    # OpenCode intake scans
    logger.info("Running OpenCode intake scans...")
    try:
        opencode_issues = run_all_opencode_scans()
        # Convert OpenCode format to standard issue format
        for oc_issue in opencode_issues:
            all_issues.append({
                'type': 'opencode_scan',
                'severity': oc_issue.get('severity', 'YELLOW'),
                'problem': oc_issue.get('problem', ''),
                'factors': oc_issue.get('factors', []),
                'timestamp': datetime.now().isoformat()
            })
        logger.info(f"OpenCode scans found {len(opencode_issues)} issues")
    except Exception as e:
        logger.warning(f"OpenCode scans failed: {e}")

    logger.info(f"Found {len(all_issues)} potential issues")

    if not all_issues:
        logger.info("No issues detected. All systems green.")
        return 0

    # Convert to SPSA cases
    logger.info("Converting issues to SPSA cases...")
    cases = issues_to_spsa_cases(all_issues)

    logger.info(f"Created {len(cases)} SPSA cases")

    # Get active cases for summary
    red_cases = [c for c in cases if c.severity == 'RED']
    yellow_cases = [c for c in cases if c.severity == 'YELLOW']

    logger.info(f"Summary: {len(red_cases)} RED, {len(yellow_cases)} YELLOW")

    # Log case details
    for case in cases:
        logger.info(f"  {case.case_id}: {case.severity} | {case.problem_statement[:50]}")

    # Alert Commander on RED cases
    if red_cases:
        logger.info(f"Alerting Commander on {len(red_cases)} RED cases...")
        try:
            from spsa_telegram_c2 import alert_red_cases
            alert_red_cases()
        except Exception as e:
            logger.warning(f"Failed to send Telegram alerts: {e}")

    logger.info("=== SPSA INTAKE JOB COMPLETE ===")
    return 0


if __name__ == "__main__":
    exit(main())
