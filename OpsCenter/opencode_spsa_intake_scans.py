#!/usr/bin/env python3
"""
OpenCode SPSA Intake Scans
===========================
OpenCode's contributions to the daily SPSA intake process.
Scans for operational issues that need COS decision-making.

Runs as part of job_spsa_intake.py after system log and hale_state scans.
"""

import json
import logging
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger("opencode_intake")

ROOT = Path("/home/john/Thunderbird")
DEDUP_FILE = ROOT / "OpsCenter" / "spsa_dedup_state.json"


def _load_dedup() -> dict:
    try:
        if DEDUP_FILE.exists():
            return json.loads(DEDUP_FILE.read_text())
    except Exception:
        pass
    return {}


def _save_dedup(state: dict):
    try:
        DEDUP_FILE.write_text(json.dumps(state, indent=2, default=str))
    except Exception as e:
        logger.warning(f"Failed to save dedup state: {e}")


def _should_fire(alert_key: str, suppress_after: int = 3) -> bool:
    """
    Returns True if this alert should fire.
    Suppresses repeated alerts after suppress_after consecutive occurrences.
    Always fires on first occurrence and when threshold is crossed (escalation signal).
    """
    state = _load_dedup()
    entry = state.get(alert_key, {})
    count = entry.get("count", 0)
    now = datetime.now().isoformat()

    state[alert_key] = {
        "count": count + 1,
        "first_seen": entry.get("first_seen", now),
        "last_seen": now,
    }
    _save_dedup(state)

    if count == 0:
        return True   # first occurrence — fire
    if count == suppress_after:
        return True   # threshold crossing — fire once as escalation notice
    if count > suppress_after:
        return False  # suppress repeat noise
    return True       # within initial window


def _clear_alert(alert_key: str):
    """Clear dedup state when a condition resolves."""
    state = _load_dedup()
    if alert_key in state:
        del state[alert_key]
        _save_dedup(state)


def _hale_state_says_running(component: str) -> bool:
    """Check hale_state.json for a component's status before escalating."""
    try:
        state_file = ROOT / "hale_state.json"
        if state_file.exists():
            state = json.loads(state_file.read_text())
            health = state.get("system_health", state.get("wing_health", {}))
            for key, val in health.items():
                if component.lower() in key.lower() and "RUNNING" in str(val).upper():
                    return True
    except Exception:
        pass
    return False


def scan_opencode_health() -> list:
    """
    Scan OpenCode daemon health and resource usage.
    Cross-checks hale_state.json before flagging RED to prevent false alarms.
    Deduplicates: suppresses repeat alerts after 3 consecutive occurrences.
    """
    issues = []

    try:
        result = subprocess.run(
            ["systemctl", "--user", "status", "opencode.service"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            # Cross-check state file before declaring RED
            if _hale_state_says_running("opencode"):
                # State/process discrepancy — not a confirmed outage
                if _should_fire("opencode_state_discrepancy"):
                    issues.append({
                        "problem": "OpenCode state/process discrepancy",
                        "factors": [
                            "opencode.service not active via systemctl",
                            "hale_state.json indicates RUNNING — possible stale state",
                            "OpenCode may be running outside systemd (screen/tmux)",
                            "Investigate but do not treat as confirmed outage"
                        ],
                        "severity": "YELLOW",
                    })
            else:
                if _should_fire("opencode_daemon_down"):
                    issues.append({
                        "problem": "OpenCode daemon is not running",
                        "factors": [
                            "systemctl --user status opencode.service returned non-zero",
                            "hale_state.json does not confirm RUNNING status",
                            "OpenCode tasks cannot be dispatched or executed",
                            "Background AI operations are paused"
                        ],
                        "severity": "RED",
                    })
        else:
            logger.info("✅ OpenCode daemon is running")
            _clear_alert("opencode_daemon_down")
            _clear_alert("opencode_state_discrepancy")

    except Exception as e:
        logger.warning(f"Failed to check OpenCode status: {e}")

    # Check OpenCode task queue depth
    try:
        queue_file = ROOT / "OpsCenter" / "opencode_task_queue.json"
        if queue_file.exists():
            queue_data = json.loads(queue_file.read_text())
            pending_count = len(queue_data.get("pending_tasks", []))

            if pending_count > 20:
                issues.append({
                    "problem": f"OpenCode task queue backlog ({pending_count} pending)",
                    "factors": [
                        f"{pending_count} tasks queued waiting for execution",
                        "Queue depth exceeds threshold (20)",
                        "May indicate slow execution or task creation outpacing processing"
                    ],
                    "severity": "YELLOW",
                })
                logger.warning(f"⚠️ OpenCode queue backlog: {pending_count} tasks")

    except Exception as e:
        logger.warning(f"Failed to check OpenCode queue: {e}")

    return issues


def scan_auth_dependencies() -> list:
    """
    Scan authentication system dependencies (tokens, oauth, credentials).

    Returns:
        List of (problem, factors, severity) tuples if issues found, else []
    """
    issues = []

    # Check Claude OAuth token status
    try:
        token_file = Path.home() / ".claude" / ".credentials.json"
        if not token_file.exists():
            issues.append({
                "problem": "Claude OAuth credentials file missing",
                "factors": [
                    "~/.claude/.credentials.json does not exist or is inaccessible",
                    "Headless Claude spawning will fail",
                    "All Claude-dependent operations are blocked"
                ],
                "severity": "RED",
            })
        else:
            creds = json.loads(token_file.read_text())
            expires_at = creds.get("claudeAiOauth", {}).get("expiresAt")
            if expires_at:
                exp_time = datetime.fromisoformat(expires_at)
                if exp_time < datetime.now():
                    issues.append({
                        "problem": "Claude OAuth token is expired",
                        "factors": [
                            f"Token expired at {expires_at}",
                            "Token refresh daemon may be failing",
                            "Claude headless operations will fail with 401 Unauthorized"
                        ],
                        "severity": "RED",
                    })
                elif (exp_time - datetime.now()).total_seconds() < 3600:
                    issues.append({
                        "problem": "Claude OAuth token expiring within 1 hour",
                        "factors": [
                            f"Token expires at {expires_at}",
                            "Recommend token refresh daemon verification",
                            "May cause mid-operation failures if not refreshed"
                        ],
                        "severity": "YELLOW",
                    })

    except Exception as e:
        logger.warning(f"Failed to check Claude auth: {e}")

    # Check Drive/Sheets token
    try:
        drive_token = ROOT / "drive_token.json"
        if drive_token.exists():
            token_data = json.loads(drive_token.read_text())
            expiry = token_data.get("expiry")
            if expiry:
                exp_time = datetime.fromisoformat(expiry)
                if exp_time < datetime.now():
                    issues.append({
                        "problem": "Drive/Sheets OAuth token is expired",
                        "factors": [
                            f"Token expired at {expiry}",
                            "Google Drive operations will fail",
                            "Dossier syncs and Google Sheets cannot write"
                        ],
                        "severity": "YELLOW",
                    })

    except Exception as e:
        logger.warning(f"Failed to check Drive auth: {e}")

    return issues


def scan_external_api_health() -> list:
    """
    Scan health of external APIs and services.

    Returns:
        List of (problem, factors, severity) tuples if issues found, else []
    """
    issues = []

    # Check MCP Server health
    try:
        result = subprocess.run(
            ["systemctl", "--user", "status", "thunderbird-mcp.service"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            issues.append({
                "problem": "MCP Server is offline",
                "factors": [
                    "systemctl status thunderbird-mcp.service returned non-zero",
                    "MCP tools (flight search, hotel price, etc.) are unavailable",
                    "Client-facing operations may be impacted"
                ],
                "severity": "RED",
            })
        else:
            # Try to reach MCP server
            try:
                result = subprocess.run(
                    ["curl", "-s", "-m", "2", "http://localhost:8765/health"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode != 0:
                    issues.append({
                        "problem": "MCP Server health check failed",
                        "factors": [
                            "Service process exists but health endpoint unreachable",
                            "May indicate port binding issue or service hang",
                            "MCP tools are not responsive"
                        ],
                        "severity": "YELLOW",
                    })
            except Exception:
                pass

    except Exception as e:
        logger.warning(f"Failed to check MCP status: {e}")

    return issues


def scan_database_connections() -> list:
    """
    Scan database connection health (Redis, etc.).

    Returns:
        List of (problem, factors, severity) tuples if issues found, else []
    """
    issues = []

    # Check if Redis is available (if used)
    try:
        result = subprocess.run(
            ["redis-cli", "ping"],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode != 0 or "PONG" not in result.stdout:
            issues.append({
                "problem": "Redis connection unavailable",
                "factors": [
                    "redis-cli ping command failed or did not return PONG",
                    "Shared state and caching operations are affected",
                    "Multi-agent coordination may be degraded"
                ],
                "severity": "YELLOW",
            })
    except FileNotFoundError:
        logger.info("Redis not installed (expected in non-server setups)")
    except Exception as e:
        logger.warning(f"Failed to check Redis: {e}")

    return issues


def scan_storage_space() -> list:
    """
    Scan available storage space on key directories.

    Returns:
        List of (problem, factors, severity) tuples if issues found, else []
    """
    issues = []

    try:
        result = subprocess.run(
            ["df", str(ROOT)],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            if len(lines) > 1:
                parts = lines[1].split()
                if len(parts) >= 5:
                    use_percent = int(parts[4].rstrip("%"))
                    if use_percent > 90:
                        issues.append({
                            "problem": f"Thunderbird storage at {use_percent}% capacity",
                            "factors": [
                                f"Disk usage: {use_percent}% of available space",
                                "Log files and case archives may fill disk quickly",
                                "Risk of database corruption if disk becomes full"
                            ],
                            "severity": "YELLOW" if use_percent < 95 else "RED",
                        })

    except Exception as e:
        logger.warning(f"Failed to check storage: {e}")

    return issues


def run_all_opencode_scans() -> list:
    """
    Run all OpenCode intake scans and return findings.

    Returns:
        List of problem dicts with 'problem', 'factors', 'severity' keys
    """
    logger.info("=== OpenCode SPSA Intake Scans Starting ===")

    all_issues = []

    # Run each scan
    for scan_name, scan_func in [
        ("OpenCode Health", scan_opencode_health),
        ("Auth Dependencies", scan_auth_dependencies),
        ("External APIs", scan_external_api_health),
        ("Database Connections", scan_database_connections),
        ("Storage Space", scan_storage_space),
    ]:
        try:
            logger.info(f"Running: {scan_name}")
            issues = scan_func()
            all_issues.extend(issues)
            logger.info(f"  Found {len(issues)} issues")
        except Exception as e:
            logger.error(f"Scan failed: {scan_name}: {e}")

    logger.info(f"=== OpenCode Scans Complete: {len(all_issues)} issues ===")
    return all_issues


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - opencode_intake - %(levelname)s - %(message)s"
    )
    issues = run_all_opencode_scans()
    for issue in issues:
        print(f"[{issue['severity']}] {issue['problem']}")
        for factor in issue['factors']:
            print(f"  • {factor}")
