#!/usr/bin/env python3
"""
OpenCode SPSA Case Monitor
===========================
Monitors SPSA case queue for cases that OpenCode can autonomously execute.
Runs as background task in OpenCode daemon.

Policies:
  - Monitor interval: 5 minutes
  - Auto-execute: LOW risk cases that are DECIDED
  - Escalate: MEDIUM risk cases for Commander decision
  - Skip: HIGH risk (requires human approval)
"""

import json
import logging
import subprocess
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.ops.thunderbird_spsa_opencode import (
    get_cases_for_opencode_execution,
    execute_case_with_handler,
    report_case_outcome,
    SPSACase,
)
from core.ops.thunderbird_spsa import classify_risk, load_case

logger = logging.getLogger("opencode_spsa_monitor")

ROOT = Path("/home/john/Thunderbird")
MONITOR_STATE = ROOT / "logs" / "spsa" / "opencode_monitor_state.json"


def get_handler_for_case(case: SPSACase) -> Optional[callable]:
    """
    Get appropriate execution handler for a case based on recommendation.

    Returns:
        Callable that takes SPSACase and returns {"success": bool, ...}
        or None if no handler available
    """

    rec = case.recommendation.lower()

    # Service restart patterns
    if "restart" in rec and "systemctl" in rec:
        def restart_handler(c: SPSACase) -> Dict[str, Any]:
            import re
            # Try to extract service name from recommendation
            match = re.search(r'systemctl.*?(\S+\.service|\S+\.timer)', c.recommendation)
            if match:
                service = match.group(1)
                try:
                    result = subprocess.run(
                        ["systemctl", "--user", "restart", service],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    if result.returncode == 0:
                        return {
                            "success": True,
                            "result": f"Restarted {service} successfully"
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"systemctl returned {result.returncode}: {result.stderr}"
                        }
                except Exception as e:
                    return {"success": False, "error": str(e)}
            return {"success": False, "error": "Could not extract service name"}

        return restart_handler

    # Token refresh patterns
    elif "token" in rec.lower() and ("refresh" in rec.lower() or "authenticate" in rec.lower()):
        def token_handler(c: SPSACase) -> Dict[str, Any]:
            try:
                # Run Claude token refresh
                result = subprocess.run(
                    ["systemctl", "--user", "restart", "claude-token-monitor.timer"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode == 0:
                    time.sleep(2)  # Let token refresh run
                    return {
                        "success": True,
                        "result": "Token refresh daemon restarted"
                    }
                return {"success": False, "error": "Failed to restart token daemon"}
            except Exception as e:
                return {"success": False, "error": str(e)}

        return token_handler

    # TESS authentication
    elif "tess" in rec.lower() and ("authenticate" in rec.lower() or "authorize" in rec.lower()):
        def tess_handler(c: SPSACase) -> Dict[str, Any]:
            try:
                result = subprocess.run(
                    ["python3", str(ROOT / "core" / "booking" / "thunderbird_tess.py"), "--authorize"],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                if result.returncode == 0:
                    return {
                        "success": True,
                        "result": "TESS re-authentication complete"
                    }
                return {
                    "success": False,
                    "error": f"TESS auth failed: {result.stderr}"
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

        return tess_handler

    # MCP server restart
    elif "mcp" in rec.lower() and "restart" in rec.lower():
        def mcp_handler(c: SPSACase) -> Dict[str, Any]:
            try:
                result = subprocess.run(
                    ["systemctl", "--user", "restart", "thunderbird-mcp.service"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode == 0:
                    time.sleep(3)  # Let MCP startup
                    return {
                        "success": True,
                        "result": "MCP server restarted successfully"
                    }
                return {"success": False, "error": "MCP restart failed"}
            except Exception as e:
                return {"success": False, "error": str(e)}

        return mcp_handler

    # No handler found
    return None


def execute_low_risk_case(case: SPSACase) -> bool:
    """
    Attempt to execute a LOW risk case.

    Returns:
        True if execution succeeded, False otherwise
    """
    logger.info(f"Attempting to execute LOW risk case {case.case_id}")

    handler = get_handler_for_case(case)
    if not handler:
        logger.warning(f"No handler available for recommendation: {case.recommendation}")
        return False

    result = execute_case_with_handler(case.case_id, handler)

    if result.get("status") == "IMPLEMENTED":
        logger.info(f"✅ Case {case.case_id} executed successfully")
        report_case_outcome(
            case_id=case.case_id,
            outcome=result.get("result", "Execution completed successfully"),
            lessons_learned=[
                f"Automated execution of {case.recommendation} succeeded",
                "Handler available for this category of issue",
            ],
            close_case_flag=True
        )
        return True
    else:
        logger.warning(f"❌ Case {case.case_id} execution failed: {result.get('error')}")
        return False


def monitor_cases():
    """
    Monitor SPSA case queue and execute eligible cases.

    Runs continuously, checking every 5 minutes for new cases to execute.
    """
    logger.info("=== OpenCode SPSA Case Monitor Started ===")

    while True:
        try:
            logger.debug("Polling SPSA case queue...")

            # Get cases eligible for execution
            executable_cases = get_cases_for_opencode_execution(max_risk="MEDIUM")

            if not executable_cases:
                logger.debug("No executable cases in queue")
            else:
                logger.info(f"Found {len(executable_cases)} executable cases")

                for case in executable_cases:
                    risk = classify_risk(case)

                    if risk == "LOW":
                        logger.info(f"Executing LOW risk case: {case.case_id}")
                        execute_low_risk_case(case)

                    elif risk == "MEDIUM":
                        logger.warning(
                            f"MEDIUM risk case waiting for Commander decision: {case.case_id}\n"
                            f"Problem: {case.problem_statement}\n"
                            f"Recommendation: {case.recommendation}"
                        )
                        # Could send alert to Commander here if desired

            # Save monitor state
            state_file = ROOT / "logs" / "spsa" / "opencode_monitor_state.json"
            state_file.parent.mkdir(parents=True, exist_ok=True)
            state_file.write_text(json.dumps({
                "last_check": datetime.now().isoformat(),
                "status": "active"
            }, indent=2))

            # Wait 5 minutes before next check
            time.sleep(300)

        except KeyboardInterrupt:
            logger.info("Monitor stopped by user")
            break
        except Exception as e:
            logger.error(f"Monitor error: {e}", exc_info=True)
            time.sleep(60)  # Shorter sleep on error


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - opencode_monitor - %(levelname)s - %(message)s"
    )

    # For testing: run one iteration
    import sys
    if "--test" in sys.argv:
        logger.info("Running in test mode (single iteration)")
        try:
            executable_cases = get_cases_for_opencode_execution()
            logger.info(f"Found {len(executable_cases)} executable cases")
            for case in executable_cases:
                logger.info(f"  {case.case_id}: {case.problem_statement[:50]}")
        except Exception as e:
            logger.error(f"Test failed: {e}")
    else:
        monitor_cases()
