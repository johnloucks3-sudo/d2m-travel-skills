#!/usr/bin/env python3
"""
Trinity Monitor: Continuous monitoring of claude_outbox, tasking watcher, and opencode_inbox
"""

import time
import json
import subprocess
from pathlib import Path


def check_claude_outbox():
    """Check if claude_outbox has new content"""
    outbox_path = Path(
        "/home/john/Thunderbird/OpsCenter/collaboration/claude_outbox.md"
    )
    if not outbox_path.exists():
        return "❌ claude_outbox.md not found"

    # Check last modified time
    stat = outbox_path.stat()
    mod_time = stat.st_mtime
    size = stat.st_size

    return f"✅ Claude outbox: {size} bytes, modified {time.ctime(mod_time)}"


def check_tasking_watcher():
    """Check if tasking watcher service is running"""
    try:
        result = subprocess.run(
            ["systemctl", "--user", "is-active", "d2m-tasking-watcher.service"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            return "✅ Tasking watcher: ACTIVE"
        else:
            return "❌ Tasking watcher: INACTIVE"
    except:
        return "❌ Tasking watcher: CHECK FAILED"


def check_opencode_inbox():
    """Check opencode_inbox for unread tasks"""
    inbox_path = Path(
        "/home/john/Thunderbird/OpsCenter/collaboration/opencode_inbox.md"
    )
    if not inbox_path.exists():
        return "❌ opencode_inbox.md not found"

    # Count UNREAD tasks
    try:
        with open(inbox_path, "r") as f:
            content = f.read()
        unread_count = content.count("status: UNREAD")

        if unread_count > 0:
            return f"🔔 OpenCode inbox: {unread_count} UNREAD tasks"
        else:
            return "✅ OpenCode inbox: 0 unread tasks"
    except:
        return "❌ OpenCode inbox: READ ERROR"


def send_telegram_alert(message):
    """Send alert via Telegram"""
    from pathlib import Path as _Path
    if _Path("/home/john/Thunderbird/config/d2mc2c_client_mute").exists():
        return  # client/supplier push muted — SO 2026-05-05
    try:
        BOT_TOKEN = "***REMOVED-SECRET***"
        CHAT_ID = "7554895206"

        subprocess.run(
            [
                "curl",
                "-s",
                "-X",
                "POST",
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                "-d",
                f"chat_id={CHAT_ID}&text={message}",
            ],
            timeout=10,
        )
    except:
        pass  # Silent fail on telegram errors


def monitor_trinity():
    """Continuous monitoring loop"""
    print("🔍 Starting Trinity Monitor...")
    print("Monitoring: Claude Outbox + Tasking Watcher + OpenCode Inbox")
    print("Press Ctrl+C to stop\n")

    last_status = {}
    alert_cooldown = {}

    while True:
        try:
            # Check all three systems
            checks = {
                "claude_outbox": check_claude_outbox(),
                "tasking_watcher": check_tasking_watcher(),
                "opencode_inbox": check_opencode_inbox(),
            }

            # Print current status
            current_time = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n🕒 {current_time} - Trinity Status:")
            for system, status in checks.items():
                print(f"  {status}")

            # Check for changes and alert
            for system, status in checks.items():
                if system in last_status and last_status[system] != status:
                    # Cooldown to prevent spam
                    last_alert = alert_cooldown.get(system, 0)
                    if time.time() - last_alert > 300:  # 5 minutes cooldown
                        alert_msg = f"🔄 {system.upper()} STATUS CHANGE:\n{status}"
                        send_telegram_alert(alert_msg)
                        alert_cooldown[system] = time.time()

            last_status = checks
            time.sleep(30)  # Check every 30 seconds

        except KeyboardInterrupt:
            print("\n🛑 Trinity Monitor stopped")
            break
        except Exception as e:
            print(f"❌ Monitor error: {e}")
            time.sleep(60)


if __name__ == "__main__":
    monitor_trinity()
