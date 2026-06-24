#!/usr/bin/env python3
"""
wing_sms.py — Wing → Commander via WhatsApp (primary) or SMS fallback

Channel priority (2026-06-22):
  1. WhatsApp sandbox (+14155238886 → +17192910742) — no carrier registration needed, live now
  2. SMS (+17195815364 → +17192910742) — blocked pending A2P 10DLC registration (~1-3 days)
  3. SMS toll-free (+18776118189) — blocked pending TFV (~5-15 days)

Commander directive 2026-06-19: macro awareness via Google Messages.
WhatsApp delivers to Google Messages on Android — same UX, no app switch needed.

Commander phone: 719-291-0742 (work cell + personal cell, cleared for all comms)

Format: one-glance readable without unlocking:
  🚨P0 [source]: problem in one sentence. Action done. Need: [one ask if any]

Usage:
    from core.comms.wing_sms import send_sms, sms_page

    send_sms("🚨P0 Portal: Regent session dead. Auto-heal failed. Login needed: portal.rssc.com")
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
WHATSAPP_SANDBOX = "+14155238886"

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


def _twilio_post(from_addr: str, to_addr: str, body: str, env: dict) -> bool:
    """Low-level Twilio Messages.json POST. Returns True on queued/sent."""
    sid = env.get("TWILIO_ACCOUNT_SID", "")
    token = env.get("TWILIO_AUTH_TOKEN", "")
    if not sid or not token:
        log.error("Twilio credentials not found in .env")
        return False
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    data = urllib.parse.urlencode({"From": from_addr, "To": to_addr, "Body": body}).encode()
    creds = b64encode(f"{sid}:{token}".encode()).decode()
    try:
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Authorization", f"Basic {creds}")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read())
        status = result.get("status", "")
        sid_out = result.get("sid", "?")
        log.info(f"Twilio {from_addr}→{to_addr}: {sid_out} ({status})")
        return status not in ("failed", "undelivered")
    except urllib.error.HTTPError as e:
        body_err = e.read().decode()
        log.error(f"Twilio HTTP {e.code}: {body_err[:200]}")
        return False
    except Exception as e:
        log.error(f"Twilio send error: {e}")
        return False


def send_sms(message: str, to: str = COMMANDER_PHONE) -> bool:
    """Send message to Commander. WhatsApp primary, SMS fallback.

    WhatsApp bypasses A2P 10DLC carrier registration (active 2026-06-22).
    SMS fallback re-enabled automatically once 10DLC registration clears.
    """
    env = _load_env()

    # Primary: WhatsApp sandbox (no carrier registration needed)
    wa_from = f"whatsapp:{WHATSAPP_SANDBOX}"
    wa_to = f"whatsapp:{to}"
    if _twilio_post(wa_from, wa_to, message, env):
        return True

    # Fallback: SMS (blocked by 10DLC until registered, kept for auto-recovery)
    log.warning("WhatsApp failed — falling back to SMS")
    from_num = env.get("TWILIO_SMS_NUMBER", "+17195815364")
    return _twilio_post(from_num, to, message, env)


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
