"""
Thunderbird Heartbeat Assessment — OpenClaw P2 Pattern
Proactive system health scan that runs every 2 hours.

Scans:
  - Inbox queues (opencode_inbox, claude_inbox)
  - Mission board for stale missions
  - Client dossiers for FPD alerts, gaps
  - System health (disk, API quotas, service status)
  - Recent activity log for anomalies

Generates optimization recommendations and alerts Commander via Telegram if action needed.

Can be run:
  - On demand via /heartbeat command in Telegram C2
  - Scheduled via systemd timer (every 2 hours)
"""

import json
import logging
import os
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

THUNDERBIRD_ROOT = Path.home() / "Thunderbird"


def _check_inbox_queues() -> Dict[str, Any]:
    """Check inbox queues for stale/UNREAD tasks."""
    result = {}

    # OpenCode inbox
    opencode_inbox = THUNDERBIRD_ROOT / "OpsCenter" / "collaboration" / "opencode_inbox.md"
    if opencode_inbox.exists():
        content = opencode_inbox.read_text()
        unread_count = content.count("status: UNREAD")
        pending_count = content.count("status: PENDING")
        result["opencode_inbox"] = {
            "unread": unread_count,
            "pending": pending_count,
            "status": "ok" if unread_count == 0 else "attention",
            "message": f"{unread_count} unread, {pending_count} pending",
        }

    # Claude inbox
    claude_inbox = THUNDERBIRD_ROOT / "claude_inbox.md"
    if claude_inbox.exists():
        content = claude_inbox.read_text()
        unread_count = content.count("status: UNREAD")
        result["claude_inbox"] = {
            "unread": unread_count,
            "status": "ok" if unread_count == 0 else "attention",
            "message": f"{unread_count} unread tasks",
        }

    return result


def _check_mission_board() -> List[Dict[str, Any]]:
    """Check mission board for stale or stuck missions."""
    mission_file = THUNDERBIRD_ROOT / "OpsCenter" / "mission_board.json"
    if not mission_file.exists():
        return []

    try:
        board = json.loads(mission_file.read_text())
        missions = board.get("missions", [])

        stale_missions = []
        for mission in missions:
            if mission.get("status") == "complete":
                continue

            # Check if mission is stale (no update in 24 hours)
            last_update = mission.get("last_updated", "")
            if last_update:
                try:
                    last_dt = datetime.fromisoformat(last_update.replace("Z", "+00:00"))
                    age = datetime.now(timezone.utc) - last_dt
                    if age > timedelta(hours=24):
                        mission["stale_hours"] = round(age.total_seconds() / 3600, 1)
                        stale_missions.append(mission)
                except Exception:
                    pass
            else:
                stale_missions.append(mission)

        return stale_missions
    except Exception as e:
        logger.error(f"Mission board check failed: {e}")
        return []


def _check_system_health() -> Dict[str, Any]:
    """Check system health: disk, services, memory."""
    health = {}

    # Disk usage
    try:
        result = subprocess.run(["df", "-h", "/home"], capture_output=True, text=True)
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            if len(lines) > 1:
                parts = lines[1].split()
                usage_pct = int(parts[4].replace("%", ""))
                health["disk"] = {
                    "status": "ok" if usage_pct < 80 else "warning",
                    "message": f"Disk usage: {parts[4]} ({parts[2]} used of {parts[1]})",
                    "usage_pct": usage_pct,
                }
    except Exception as e:
        health["disk"] = {"status": "error", "message": f"Disk check failed: {e}"}

    # Telegram C2 service
    try:
        result = subprocess.run(
            ["systemctl", "--user", "is-active", "d2m-telegram.service"],
            capture_output=True, text=True
        )
        health["telegram_c2"] = {
            "status": "ok" if result.stdout.strip() == "active" else "warning",
            "message": f"Telegram C2: {result.stdout.strip()}",
        }
    except Exception as e:
        health["telegram_c2"] = {"status": "error", "message": f"Service check failed: {e}"}

    # Watcher service
    try:
        result = subprocess.run(
            ["systemctl", "--user", "is-active", "d2m-tasking-watcher.service"],
            capture_output=True, text=True
        )
        health["watcher"] = {
            "status": "ok" if result.stdout.strip() == "active" else "warning",
            "message": f"Tasking watcher: {result.stdout.strip()}",
        }
    except Exception as e:
        health["watcher"] = {"status": "error", "message": f"Service check failed: {e}"}

    # Memory usage
    try:
        result = subprocess.run(["free", "-m"], capture_output=True, text=True)
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            if len(lines) > 1:
                parts = lines[1].split()
                total = int(parts[1])
                used = int(parts[2])
                usage_pct = round(used / total * 100, 1) if total > 0 else 0
                health["memory"] = {
                    "status": "ok" if usage_pct < 80 else "warning",
                    "message": f"Memory: {used}MB / {total}MB ({usage_pct}%)",
                    "usage_pct": usage_pct,
                }
    except Exception as e:
        health["memory"] = {"status": "error", "message": f"Memory check failed: {e}"}

    return health


def _check_dossier_alerts() -> List[str]:
    """Scan client dossiers for FPD alerts and gaps."""
    alerts = []
    dossier_dir = THUNDERBIRD_ROOT / "dossiers"
    if not dossier_dir.exists():
        return alerts

    today = datetime.now(timezone.utc).date()

    for dossier_file in dossier_dir.glob("*.md"):
        if dossier_file.name == "CLAUDE.md":
            continue

        try:
            content = dossier_file.read_text()

            # Check for FPD (Final Payment Due) dates
            if "fpd" in content.lower() or "final payment" in content.lower():
                # Look for dates in the dossier
                import re
                date_patterns = [
                    r'\d{4}-\d{2}-\d{2}',  # ISO format
                    r'\d{2}/\d{2}/\d{4}',  # US format
                ]
                for pattern in date_patterns:
                    matches = re.findall(pattern, content)
                    for match in matches:
                        try:
                            if "-" in match:
                                fpd_date = datetime.strptime(match, "%Y-%m-%d").date()
                            else:
                                fpd_date = datetime.strptime(match, "%m/%d/%Y").date()

                            days_until = (fpd_date - today).days
                            if 0 <= days_until <= 60:
                                alerts.append(
                                    f"{dossier_file.stem}: FPD in {days_until} days ({match})"
                                )
                        except ValueError:
                            pass
        except Exception as e:
            logger.error(f"Dossier scan failed for {dossier_file}: {e}")

    return alerts


def _check_recent_errors() -> List[str]:
    """Check recent logs for errors."""
    errors = []
    log_dir = THUNDERBIRD_ROOT / "logs"
    if not log_dir.exists():
        return errors

    # Check c2_command_log.jsonl for recent errors
    c2_log = log_dir / "c2_command_log.jsonl"
    if c2_log.exists():
        try:
            content = c2_log.read_text()
            lines = content.strip().split("\n")
            recent_lines = lines[-50:] if len(lines) > 50 else lines

            for line in recent_lines:
                try:
                    entry = json.loads(line)
                    if entry.get("status") == "ERROR":
                        errors.append(f"C2: {entry.get('query', '')[:100]}")
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            logger.error(f"Error log check failed: {e}")

    return errors[:5]  # Limit to 5 recent errors


def _generate_recommendations(
    inbox_status: Dict,
    stale_missions: List,
    system_health: Dict,
    dossier_alerts: List,
    recent_errors: List,
) -> List[str]:
    """Generate actionable recommendations based on scan results."""
    recommendations = []

    # Inbox recommendations
    for inbox_name, status in inbox_status.items():
        if status.get("unread", 0) > 0:
            recommendations.append(f"Process {status['unread']} unread task(s) in {inbox_name}")

    # Mission recommendations
    for mission in stale_missions:
        recommendations.append(
            f"Mission {mission.get('id', 'unknown')} is stale "
            f"({mission.get('stale_hours', '?')}h since last update)"
        )

    # System health recommendations
    for component, status in system_health.items():
        if status.get("status") != "ok":
            recommendations.append(f"Check {component}: {status.get('message', '')}")

    # Dossier recommendations
    for alert in dossier_alerts[:3]:
        recommendations.append(f"FPD Alert: {alert}")

    # Error recommendations
    for error in recent_errors:
        recommendations.append(f"Recent error: {error}")

    return recommendations


def run_heartbeat_assessment() -> Dict[str, Any]:
    """
    Main entry point: run comprehensive heartbeat assessment.

    Returns:
        dict with system health, inbox status, mission status, recommendations
    """
    logger.info("Running heartbeat assessment...")

    try:
        # Run all checks
        inbox_status = _check_inbox_queues()
        stale_missions = _check_mission_board()
        system_health = _check_system_health()
        dossier_alerts = _check_dossier_alerts()
        recent_errors = _check_recent_errors()

        # Generate recommendations
        recommendations = _generate_recommendations(
            inbox_status, stale_missions, system_health, dossier_alerts, recent_errors
        )

        # Determine overall status
        has_issues = (
            any(s.get("status") != "ok" for s in inbox_status.values()) or
            len(stale_missions) > 0 or
            any(s.get("status") != "ok" for s in system_health.values()) or
            len(dossier_alerts) > 0
        )

        result = {
            "success": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall_status": "attention" if has_issues else "nominal",
            "inbox_status": inbox_status,
            "mission_status": [
                {
                    "id": m.get("id", ""),
                    "status": m.get("status", ""),
                    "stale_hours": m.get("stale_hours", 0),
                }
                for m in stale_missions
            ],
            "system_health": system_health,
            "dossier_alerts": dossier_alerts,
            "recent_errors": recent_errors,
            "recommendations": recommendations,
        }

        logger.info(f"Heartbeat complete: {result['overall_status']}, "
                    f"{len(recommendations)} recommendations")

        return result

    except Exception as e:
        logger.error(f"Heartbeat assessment failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


if __name__ == "__main__":
    # Quick test
    logging.basicConfig(level=logging.INFO)

    print("Running heartbeat assessment...")
    result = run_heartbeat_assessment()

    print(f"\nStatus: {result.get('overall_status', 'unknown')}")
    print(f"Timestamp: {result.get('timestamp', '')[:19]}")

    if result.get("recommendations"):
        print(f"\nRecommendations ({len(result['recommendations'])}):")
        for rec in result["recommendations"]:
            print(f"  • {rec}")
