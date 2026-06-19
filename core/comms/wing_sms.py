#!/usr/bin/env python3
"""
wing_sms.py — Wing → Commander via Twilio SMS (Google Messages)

Commander directive 2026-06-19: macro awareness via Google Messages.
SMS lands in Google Messages on Android — no app switch needed.

Credentials already in .env:
  TWILIO_ACCOUNT_SID=ACdc4e7b2beacb84b18c8b49ab8c8369cb
  TWILIO_AUTH_TOKEN=...
  TWILIO_SMS_NUMBER=+18776118189

Commander phone: 719-291-0742 (work cell + personal cell, cleared for all comms)

SMS format is even shorter than Telegram — one-glance readable without unlocking:
  🚨P0 [source]: problem in one sentence. Action done. Need: [one ask if any]

Usage:
    from core.comms.wing_sms import send_sms, sms_page

    send_sms("🚨P0 Portal: Regent session dead. Auto-heal failed. Login needed: portal.rssc.com")

    sms_page(
        problem="Regent portal dead",
        action="Auto-heal failed x2",
        need="Login at portal.rssc.com",
        level="P0",
    )
"""
from __future__ import annotations

import json
import logging
import os
import urllib.parse
import urllib.request
from base64 import b64encode
from pathlib import Path

THUNDERBIRD = Path(__file__).parent.parent.parent
COMMANDER_PHONE = "+17192910742"

log = logging.getLogger("wing-sms")


def _load_env() -> dict:
    env = dict(os.environ)
    env_file = THUNDERBIRD / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def send_sms(message: str, to: str = COMMANDER_PHONE) -> bool:
    """Send raw SMS text to Commander. Returns True on success."""
    env = _load_env()
    sid = env.get("TWILIO_ACCOUNT_SID", "")
    token = env.get("TWILIO_AUTH_TOKEN", "")
    from_num = env.get("TWILIO_SMS_NUMBER", "+18776118189")

    if not sid or not token:
        log.error("Twilio credentials not found in .env")
        return False

    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    data = urllib.parse.urlencode({"From": from_num, "To": to, "Body": message}).encode()
    creds = b64encode(f"{sid}:{token}".encode()).decode()

    try:
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Authorization", f"Basic {creds}")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read())
        if result.get("status") in ("queued", "sent", "delivered"):
            log.info(f"SMS sent: {result['sid']}")
            return True
        log.warning(f"SMS unexpected status: {result.get('status')}")
        return True  # still sent, just not yet delivered
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        log.error(f"Twilio HTTP {e.code}: {body[:200]}")
        return False
    except Exception as e:
        log.error(f"SMS send error: {e}")
        return False


def sms_page(
    problem: str,
    action: str = "",
    need: str = "",
    level: str = "P1",
    source: str = "Hale",
) -> bool:
    """
    Send a concise 5-part macro page via SMS.
    Designed to be one-glance readable on a lock screen.
    """
    emoji = {"P0": "🚨", "P1": "⚠️", "P2": "ℹ️"}.get(level, "📋")
    parts = [f"{emoji}{level} {source}: {problem}"]
    if action:
        parts.append(f"Done: {action}")
    if need:
        parts.append(f"Need: {need}")
    message = " | ".join(parts)
    # Keep under 320 chars (2 SMS segments)
    if len(message) > 320:
        message = message[:317] + "..."
    return send_sms(message)


def sms_5part(
    problem: str,
    discussion: str = "",
    options: list[str] | None = None,
    action: str = "",
    next_steps: str = "",
    level: str = "P1",
    source: str = "Hale",
) -> bool:
    """
    Full 5-part format via SMS (multi-segment, for decisions that need context).
    Use for P0 situations where Commander needs full picture on his phone.
    """
    emoji = {"P0": "🚨", "P1": "⚠️", "P2": "ℹ️"}.get(level, "📋")
    lines = [f"{emoji} {level} — {source}"]
    lines.append(f"1. {problem}")
    if discussion:
        lines.append(f"2. {discussion}")
    if options:
        for i, opt in enumerate(options, 1):
            lines.append(f"   {opt}")
    if action:
        lines.append(f"4. Done: {action}")
    if next_steps:
        lines.append(f"5. Need: {next_steps}")
    return send_sms("\n".join(lines))


if __name__ == "__main__":
    import sys
    msg = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Wing SMS test — Google Messages live."
    ok = send_sms(msg)
    print("✅ Sent" if ok else "❌ Failed")
