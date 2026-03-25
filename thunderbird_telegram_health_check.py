#!/usr/bin/env python3
"""
Telegram C2 Health Check & Auto-Recovery
Monitors the service and alerts if down, with remote restart capability
"""
import subprocess
import sys
import json
from datetime import datetime

TELEGRAM_C2_SERVICE = "thunderbird-telegram-c2.service"
COMMANDER_ID = 7554895206

def check_service_status():
    """Check if Telegram C2 service is running"""
    try:
        result = subprocess.run(
            ["systemctl", "--user", "is-active", TELEGRAM_C2_SERVICE],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0, result.stdout.strip()
    except Exception as e:
        return False, str(e)

def get_service_details():
    """Get full service status details"""
    try:
        result = subprocess.run(
            ["systemctl", "--user", "status", TELEGRAM_C2_SERVICE, "--no-pager"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.stdout
    except Exception as e:
        return f"Error: {e}"

def restart_service():
    """Restart the Telegram C2 service"""
    try:
        result = subprocess.run(
            ["systemctl", "--user", "restart", TELEGRAM_C2_SERVICE],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)

def send_telegram_alert(message):
    """Send alert to Commander via Telegram C2 bot"""
    # This would use the MCP bot API to send a message to the Commander
    # For now, log it
    with open("/tmp/telegram_health_alerts.log", "a") as f:
        f.write(f"[{datetime.now().isoformat()}] {message}\n")

def main():
    is_running, status = check_service_status()

    if is_running:
        print(f"✅ Telegram C2 service is ACTIVE")
        return 0
    else:
        print(f"❌ Telegram C2 service is DOWN: {status}")
        print("\n📋 Full status:")
        print(get_service_details())

        # Attempt auto-recovery
        print("\n🔧 Attempting auto-recovery...")
        success, output = restart_service()

        if success:
            print("✅ Service restarted successfully")
            send_telegram_alert(f"🚨 Telegram C2 was DOWN. Auto-restarted at {datetime.now().isoformat()}")
            return 0
        else:
            print(f"❌ Failed to restart service:\n{output}")
            send_telegram_alert(f"🚨 CRITICAL: Telegram C2 DOWN + restart failed. Manual intervention required. Output: {output}")
            return 1

if __name__ == "__main__":
    sys.exit(main())
