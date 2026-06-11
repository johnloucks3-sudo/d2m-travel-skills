#!/usr/bin/env python3
"""
systemd_alert_send.py — Telegram alert sender for thunderbird-alert@.service
Usage: python3 systemd_alert_send.py <unit_name>
Called by the OnFailure= template unit with %i (failed unit name).

P4a build: 2026-06-10 Sterling A7
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path
import urllib.request

THUNDERBIRD = Path("/home/john/Thunderbird")
LOG_FILE = THUNDERBIRD / "logs" / "service_alerts.log"


def _load_env() -> dict:
    """Load .env file into a dict."""
    env = {}
    env_path = THUNDERBIRD / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def main():
    unit_name = sys.argv[1] if len(sys.argv) > 1 else "unknown-unit"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Log to file always (fallback if Telegram fails)
    LOG_FILE.parent.mkdir(exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(f"SERVICE FAILURE: {unit_name} at {ts}\n")

    # Send Telegram
    env = _load_env()
    bot_token = env.get("TELEGRAM_C2_BOT_TOKEN", "")
    chat_id = env.get("TELEGRAM_COMMANDER_ID", "")

    if not bot_token or not chat_id:
        print(f"WARN: Missing Telegram credentials — logged to {LOG_FILE} only", file=sys.stderr)
        return

    msg = (
        f"[THUNDERBIRD ALERT] Service failed: {unit_name}\n"
        f"Time: {ts}\n"
        f"COO watchdog will attempt self-heal (max 3/hr). "
        f"Check: journalctl --user -xeu {unit_name}"
    )
    body = json.dumps({"chat_id": chat_id, "text": msg}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            if result.get("ok"):
                print(f"Alert sent for {unit_name}")
            else:
                print(f"Telegram error: {result}", file=sys.stderr)
    except Exception as exc:
        print(f"Telegram send failed: {exc}", file=sys.stderr)
        with open(LOG_FILE, "a") as f:
            f.write(f"  [Telegram send failed: {exc}]\n")


if __name__ == "__main__":
    main()
