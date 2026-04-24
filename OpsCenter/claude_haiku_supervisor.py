#!/usr/bin/env python3
"""
Haiku Supervisor Daemon — Claude Operation Quality Control
===========================================================
Monitors headless Claude invocations, detects failures, and owns token health.
Runs every 15 minutes via systemd timer. No silent fallbacks — all failures visible.

Key responsibilities:
1. Monitor token state (expiry, refresh health)
2. Scan watcher log for recent Claude invocations
3. Analyze per-invocation logs for failure signatures
4. Detect patterns (auth errors, credit, timeouts, logic failures)
5. Alert Commander on issues
6. Learn and report on operational trends

Supervisor is Haiku (cost-conscious) but runs continuously and owns reliability.
"""

import os
import re
import sys
import json
import logging
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [HAIKU SUPERVISOR] - %(message)s",
    handlers=[
        logging.FileHandler("/home/john/Thunderbird/logs/haiku_supervisor.log"),
        logging.StreamHandler(sys.stdout),
    ],
)

# Paths
BASE = Path("/home/john/Thunderbird")
WATCHER_LOG = BASE / "logs" / "inbox_watcher.log"
INVOKE_LOG_DIR = BASE / "logs"
TOKEN_CREDS = Path.home() / ".claude" / ".credentials.json"
WING_COMMS = BASE / "OpsCenter" / "collaboration" / "wing_comms.md"
PATTERNS_DB = BASE / "OpsCenter" / ".supervisor_patterns.json"
HALE_STATE = BASE / "hale_state.json"

# Supervisor's own state
SUPERVISOR_STATE = BASE / "OpsCenter" / ".supervisor_state.json"


def load_patterns_db():
    """Load historical pattern database."""
    if PATTERNS_DB.exists():
        try:
            return json.loads(PATTERNS_DB.read_text())
        except Exception as e:
            logging.warning(f"Could not load patterns DB: {e}")
    return {
        "total_invocations": 0,
        "failures": [],
        "auth_errors": 0,
        "credit_errors": 0,
        "timeouts": 0,
        "logic_errors": 0,
        "last_30_min": [],
    }


def save_patterns_db(db):
    """Persist pattern database."""
    try:
        PATTERNS_DB.write_text(json.dumps(db, indent=2))
    except Exception as e:
        logging.error(f"Could not save patterns DB: {e}")


def check_token_health():
    """Check if token is valid and not expiring soon."""
    try:
        if not TOKEN_CREDS.exists():
            return False, "Token file missing"

        creds = json.loads(TOKEN_CREDS.read_text())
        token_data = creds.get("claudeAiOauth", {})
        expires_at = token_data.get("expiresAt")

        if not expires_at:
            return False, "No expiresAt in token"

        now_ms = int(datetime.now().timestamp() * 1000)
        time_until_expiry_ms = expires_at - now_ms

        if time_until_expiry_ms < 0:
            return False, f"Token expired {abs(time_until_expiry_ms) // 60000} min ago"

        if time_until_expiry_ms < (15 * 60 * 1000):  # Less than 15 min
            return False, f"Token expiring in {time_until_expiry_ms // 60000} min (CRITICAL)"

        return True, f"Token valid for {time_until_expiry_ms // 60000} min"

    except Exception as e:
        return False, f"Token check failed: {e}"


def get_recent_invocations(minutes=20):
    """Extract recent Claude invocations from watcher log."""
    cutoff = datetime.now() - timedelta(minutes=minutes)
    invocations = []

    try:
        log_text = WATCHER_LOG.read_text()
        # Parse lines like: "2026-04-23 05:30:01,593 - [WATCHER V7] - Spawning Claude headless model=claude-opus-4-6 → log: /path/to/log"
        lines = log_text.split("\n")

        for line in lines:
            if "Spawning Claude headless" in line:
                # Try to extract timestamp and log path
                match = re.search(
                    r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", line
                )
                if match:
                    ts_str = match.group(1)
                    ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                    if ts >= cutoff:
                        log_match = re.search(r"→ log: (.+)$", line)
                        if log_match:
                            log_path = log_match.group(1).strip()
                            invocations.append(
                                {
                                    "timestamp": ts,
                                    "log_path": log_path,
                                    "model": (
                                        "opus"
                                        if "claude-opus" in line
                                        else "sonnet"
                                        if "claude-sonnet" in line
                                        else "haiku"
                                    ),
                                }
                            )
    except Exception as e:
        logging.error(f"Could not parse watcher log: {e}")

    return invocations


def analyze_invocation_log(log_path):
    """Analyze a single invocation log for failure signatures."""
    issues = []

    try:
        if not Path(log_path).exists():
            return None, "Log file missing"

        log_text = Path(log_path).read_text()

        # Check for specific failure signatures
        failure_sigs = {
            "credit_error": [
                "402",
                "credit",
                "balance",
                "insufficient",
                "insufficient_balance",
            ],
            "auth_error": ["401", "unauthorized", "token", "expired"],
            "timeout": ["timeout", "timed out", ">10 min"],
            "logic_error": ["traceback", "exception", "error:", "failed"],
            "empty_response": ["empty", "no output", "no content"],
        }

        for sig_type, patterns in failure_sigs.items():
            if any(p.lower() in log_text.lower() for p in patterns):
                issues.append(sig_type)

        # Check execution time (if logged)
        if "Traceback" in log_text or "Error" in log_text:
            issues.append("execution_error")

        return (
            issues if issues else None,
            f"{len(issues)} issue(s) detected" if issues else "OK",
        )

    except Exception as e:
        return None, f"Could not analyze log: {e}"


def alert_commander(severity, message, context=None):
    """Post alert to wing_comms for Commander visibility."""
    try:
        # Read existing content
        existing = WING_COMMS.read_text() if WING_COMMS.exists() else ""

        # Build alert block
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        alert = f"\n## ⚠️ [{severity.upper()}] Supervisor Alert — {timestamp}\n"
        alert += f"{message}\n"

        if context:
            alert += f"\n**Context:**\n"
            for key, val in context.items():
                alert += f"- {key}: {val}\n"

        # Append to wing_comms
        new_content = existing.rstrip() + "\n" + alert

        WING_COMMS.write_text(new_content)
        logging.info(f"Alerted Commander [{severity}]: {message}")

    except Exception as e:
        logging.error(f"Could not post alert: {e}")


def run_supervisor_pass():
    """Single pass: check token, analyze recent invocations, update patterns."""

    logging.info("=" * 60)
    logging.info("SUPERVISOR PASS START")
    logging.info("=" * 60)

    # 1. Token Health Check
    token_ok, token_msg = check_token_health()
    logging.info(f"Token health: {token_msg}")

    if not token_ok:
        alert_commander("critical", f"Token health issue: {token_msg}")

    # 2. Load patterns
    patterns = load_patterns_db()

    # 3. Get recent invocations (last 20 min)
    invocations = get_recent_invocations(minutes=20)
    logging.info(f"Recent invocations: {len(invocations)}")

    # 4. Analyze each invocation
    failures_this_pass = []
    for inv in invocations:
        log_path = inv["log_path"]
        issues, status = analyze_invocation_log(log_path)

        logging.info(
            f"  {inv['timestamp'].strftime('%H:%M:%S')} - {inv['model']:6} - {status}"
        )

        if issues:
            failures_this_pass.append(
                {
                    "timestamp": inv["timestamp"].isoformat(),
                    "log_path": log_path,
                    "model": inv["model"],
                    "issues": issues,
                }
            )

            # Update pattern counters
            for issue in issues:
                if issue == "credit_error":
                    patterns["credit_errors"] += 1
                elif issue == "auth_error":
                    patterns["auth_errors"] += 1
                elif issue == "timeout":
                    patterns["timeouts"] += 1
                elif issue == "logic_error":
                    patterns["logic_errors"] += 1

    # 5. Alert if failures detected in this pass
    if failures_this_pass:
        alert_context = {
            "failures_this_pass": len(failures_this_pass),
            "failure_types": list(set(f for inv in failures_this_pass for f in inv["issues"])),
        }
        alert_commander(
            "warning",
            f"Detected {len(failures_this_pass)} invocation failure(s) in last 20 min",
            alert_context,
        )

    # 6. Update patterns and state
    patterns["total_invocations"] += len(invocations)
    patterns["failures"].extend(failures_this_pass)
    # Keep last 100 failures
    patterns["failures"] = patterns["failures"][-100:]
    patterns["last_30_min"] = failures_this_pass

    save_patterns_db(patterns)

    # 7. Log summary
    logging.info(f"Failures detected: {len(failures_this_pass)}")
    logging.info(
        f"Total tracked: {patterns['total_invocations']} invocations, {len(patterns['failures'])} failures"
    )
    logging.info(
        f"Pattern breakdown: auth={patterns['auth_errors']} credit={patterns['credit_errors']} timeout={patterns['timeouts']}"
    )
    logging.info("SUPERVISOR PASS COMPLETE")
    logging.info("=" * 60)


def main():
    logging.info("Haiku Supervisor starting")
    try:
        run_supervisor_pass()
    except Exception as e:
        logging.error(f"Supervisor pass failed: {e}", exc_info=True)
        alert_commander("critical", f"Supervisor itself encountered error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
