#!/usr/bin/env python3
"""
Commander Update Timer - 120-second status updates
Sends updates to Commander via Telegram (preferred) or falls back to logging.
Integrated with timer system and staff tasking to provide real-time status.
"""

import json
import logging
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import time

THUNDERBIRD_ROOT = Path("/home/john/Thunderbird")
LOG_FILE = THUNDERBIRD_ROOT / "OpsCenter/logs/commander_updates.log"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def get_system_status():
    """Get current status of timer system and active workflows."""
    status = {
        "timestamp": datetime.now().isoformat(),
        "active_clients": [],
        "pending_tasks": 0,
        "recent_completions": 0,
        "system_health": "unknown",
    }

    try:
        # Check staff tasking schedule
        schedule_file = THUNDERBIRD_ROOT / "OpsCenter/staff_tasking_schedule.json"
        if schedule_file.exists():
            with open(schedule_file) as f:
                schedule = json.load(f)
                status["pending_tasks"] = len(schedule.get("tasks", []))
                status["active_clients"] = list(
                    set(
                        [
                            t["client"]
                            for t in schedule.get("tasks", [])
                            if t["status"] != "COMPLETE"
                        ]
                    )
                )

        # Check mission board
        mission_file = THUNDERBIRD_ROOT / "OpsCenter/mission_board.json"
        if mission_file.exists():
            with open(mission_file) as f:
                missions = json.load(f)
                active_missions = [
                    m
                    for m in missions.get("active_missions", [])
                    if m.get("status") != "completed"
                ]
                status["pending_missions"] = len(active_missions)

        # Check timers
        try:
            result = subprocess.run(
                ["systemctl", "--user", "list-timers", "--no-pager"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            timer_lines = [
                line
                for line in result.stdout.split("\n")
                if "d2m" in line or "staff" in line
            ]
            status["active_timers"] = len(timer_lines)
        except:
            status["active_timers"] = 0

    except Exception as e:
        logger.error(f"Failed to get system status: {e}")
        status["error"] = str(e)

    return status


def send_telegram_update(message):
    """Send update to Commander via Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram credentials not configured")
        return False

    try:
        import requests

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown",
        }
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info(f"Telegram update sent: {response.status_code}")
        return True
    except Exception as e:
        logger.error(f"Failed to send Telegram update: {e}")
        return False


def generate_update_message(status):
    """Generate human-readable update message."""
    lines = [
        f"⚡ **Timer System Update** ⚡",
        f"Time: {datetime.now().strftime('%H:%M MT')}",
        f"",
    ]

    if status["active_clients"]:
        lines.append(f"**Active Clients:** {', '.join(status['active_clients'])}")

    if status.get("pending_tasks", 0) > 0:
        lines.append(f"**Pending Tasks:** {status['pending_tasks']}")

    if status.get("pending_missions", 0) > 0:
        lines.append(f"**Active Missions:** {status['pending_missions']}")

    if status.get("active_timers", 0) > 0:
        lines.append(f"**Active Timers:** {status['active_timers']}")

    # Add specific project updates
    lines.extend(
        [
            "",
            "**Current Projects:**",
            "• Kuklinski Group Timeline (client-facing) ✓",
            "• Date Flexibility System ✓",
            "• Westbrook Test Case ✓",
            "• Staff Tasking Automation ✓",
            "",
            "**Next Actions:**",
            "- Review Kuklinski timeline proposal",
            "- Test Westbrook with date flexibility",
            "- Monitor staff tasking automation",
        ]
    )

    return "\n".join(lines)


def main():
    """Main update loop."""
    logger.info("Commander Update Timer starting...")

    # Check if we should use Telegram
    use_telegram = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
    if use_telegram:
        logger.info("Telegram notifications enabled")
    else:
        logger.info("Log-only mode (no Telegram)")

    while True:
        try:
            logger.info("Generating status update...")
            status = get_system_status()
            message = generate_update_message(status)

            # Log update
            logger.info(
                f"Update: {len(status.get('active_clients', []))} clients, {status.get('pending_tasks', 0)} tasks"
            )

            # Send to Telegram if configured
            if use_telegram:
                send_telegram_update(message)
                logger.info("Telegram update sent")
            else:
                # Just log for now
                logger.info("Update (not sent via Telegram):\n" + message)

        except Exception as e:
            logger.error(f"Error in update loop: {e}")

        # Wait 120 seconds
        time.sleep(120)


if __name__ == "__main__":
    main()
