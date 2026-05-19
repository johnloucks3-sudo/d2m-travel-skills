#!/usr/bin/env python3
"""
Telegram Gateway Health Check
Dreams2Memories Travel, LLC

Comprehensive health monitoring to eliminate false "green" reports.
Checks: process status, API connectivity, message flow, bot responsiveness.
"""

import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("/home/john/Thunderbird/logs/telegram_health.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("tg_health")

# Config
THUNDERBIRD = Path("/home/john/Thunderbird")
OPS = THUNDERBIRD / "OpsCenter"
LOG_DIR = THUNDERBIRD / "logs"

# Bot tokens from env
TELEGRAM_D2MC2C_TOKEN = os.environ.get(
    "TELEGRAM_D2MC2C_TOKEN", "***REMOVED-SECRET***"
)
TELEGRAM_DANI_TOKEN = os.environ.get(
    "TELEGRAM_DANI_TOKEN", "***REMOVED-SECRET***"
)


def check_gateway_process() -> dict:
    """Check if gateway process is running and healthy."""
    try:
        result = subprocess.run(
            ["systemctl", "--user", "status", "thunderbird-telegram-gw.service"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        return {
            "running": "active (running)" in result.stdout,
            "output": result.stdout.strip(),
            "healthy": result.returncode == 0 and "active (running)" in result.stdout,
        }
    except Exception as e:
        return {"running": False, "error": str(e), "healthy": False}


def check_bot_api(bot_token: str, bot_name: str) -> dict:
    """Test Telegram API connectivity for a bot."""
    try:
        url = f"https://api.telegram.org/bot{bot_token}/getMe"
        result = subprocess.run(
            ["curl", "-s", url], capture_output=True, text=True, timeout=10
        )

        response = json.loads(result.stdout) if result.stdout.strip() else {}
        return {
            "responsive": response.get("ok", False),
            "username": response.get("result", {}).get("username", ""),
            "healthy": response.get("ok", False),
        }
    except Exception as e:
        return {"responsive": False, "error": str(e), "healthy": False}


def check_message_flow(bot_token: str, bot_name: str) -> dict:
    """Test end-to-end message flow by sending a test message."""
    test_message = f"🔧 Health check {datetime.now().strftime('%H:%M:%S')}"

    try:
        # Send message
        send_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        send_cmd = [
            "curl",
            "-s",
            "-X",
            "POST",
            send_url,
            "-d",
            f"chat_id=7554895206&text={test_message}",
        ]

        send_result = subprocess.run(
            send_cmd, capture_output=True, text=True, timeout=15
        )
        send_response = (
            json.loads(send_result.stdout) if send_result.stdout.strip() else {}
        )

        message_id = (
            send_response.get("result", {}).get("message_id")
            if send_response.get("ok")
            else None
        )

        return {
            "send_ok": send_response.get("ok", False),
            "message_id": message_id,
            "healthy": send_response.get("ok", False),
        }

    except Exception as e:
        return {"send_ok": False, "error": str(e), "healthy": False}


def check_stuck_tasks() -> dict:
    """Check for stuck tasks in inboxes."""
    try:
        # Check claude_inbox for UNREAD tasks
        claude_inbox = THUNDERBIRD / "claude_inbox.md"
        if claude_inbox.exists():
            with open(claude_inbox, "r") as f:
                content = f.read()
            stuck_claude = content.count("status: UNREAD")
        else:
            stuck_claude = 0

        # Check opencode_inbox for UNREAD tasks
        opencode_inbox = OPS / "collaboration" / "opencode_inbox.md"
        if opencode_inbox.exists():
            with open(opencode_inbox, "r") as f:
                content = f.read()
            stuck_opencode = content.count("status: UNREAD")
        else:
            stuck_opencode = 0

        return {
            "stuck_claude": stuck_claude,
            "stuck_opencode": stuck_opencode,
            "total_stuck": stuck_claude + stuck_opencode,
            "healthy": (stuck_claude + stuck_opencode)
            < 5,  # More than 5 stuck = unhealthy
        }

    except Exception as e:
        return {"error": str(e), "healthy": False}


def main():
    """Run comprehensive health check."""
    log.info("🔍 Running Telegram health check")

    health_report = {
        "timestamp": datetime.now().isoformat(),
        "gateway": check_gateway_process(),
        "bots": {},
        "stuck_tasks": check_stuck_tasks(),
        "overall_healthy": True,
    }

    # Check each bot
    bots = {
        "d2mc2c": TELEGRAM_D2MC2C_TOKEN,
        "dani": TELEGRAM_DANI_TOKEN,
    }

    for bot_name, token in bots.items():
        api_health = check_bot_api(token, bot_name)
        flow_health = check_message_flow(token, bot_name)

        health_report["bots"][bot_name] = {
            "api": api_health,
            "message_flow": flow_health,
            "healthy": api_health["healthy"] and flow_health["healthy"],
        }

        if not health_report["bots"][bot_name]["healthy"]:
            health_report["overall_healthy"] = False

    # Check gateway health
    if not health_report["gateway"]["healthy"]:
        health_report["overall_healthy"] = False

    # Check stuck tasks
    if not health_report["stuck_tasks"]["healthy"]:
        health_report["overall_healthy"] = False

    # Log results
    log.info(
        f"Health check complete: {'✅ HEALTHY' if health_report['overall_healthy'] else '❌ UNHEALTHY'}"
    )

    # Save report
    report_file = LOG_DIR / "telegram_health_report.json"
    with open(report_file, "w") as f:
        json.dump(health_report, f, indent=2)

    return health_report["overall_healthy"]


if __name__ == "__main__":
    try:
        healthy = main()
        sys.exit(0 if healthy else 1)
    except Exception as e:
        log.error(f"Health check failed: {e}")
        sys.exit(1)
