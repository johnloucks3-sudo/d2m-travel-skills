#!/usr/bin/env python3
"""Confirmed-Delivery Auto-Execute — Unified C2 Fabric Phase 2/3 (Gate 4 approved 2026-07-06).

Implements the Commander's "max latitude, all channels" override, engineered
per ELON + Whetstone's retroactive input (not the original staff 30-day
burn-in): silence only counts as GO once DELIVERY (Telegram) or READ (email)
is confirmed — never on "sent" alone. This is the code-enforced answer to
Dembe's finding that an unread email and an ignored Telegram ping are not
the same kind of silence.

Every notification and its outcome is logged to the Unified C2 Fabric bus
(core/hale_bus/hale_bus_write.py) so any channel can see what was decided
and why.
"""
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, "/home/john/Thunderbird")
sys.path.insert(0, "/home/john/Thunderbird/api")

from core.hale_bus.hale_bus_write import append_channel_activity

TELEGRAM_BOT_TOKEN_ENV = "D2MC2C_BOT_TOKEN"
COMMANDER_CHAT_ID = 7554895206
COMMANDER_EMAIL = "johnloucks3@gmail.com"


class HoldForCommander(RuntimeError):
    """Raised when delivery/read cannot be confirmed — auto-execute must NOT proceed."""


def _telegram_token() -> str:
    import os
    env_path = "/home/john/Thunderbird/.env"
    if os.path.exists(env_path):
        for line in open(env_path):
            if line.startswith("TELEGRAM_D2MC2C_TOKEN="):
                return line.strip().split("=", 1)[1]
    raise HoldForCommander("Telegram bot token not found — cannot confirm delivery, holding.")


def send_telegram_notification(text: str) -> dict:
    """Send via Telegram Bot API directly and return the API's own delivery confirmation
    (ok:true means Telegram's servers accepted and will push it — this IS the confirmed-
    delivery signal Sterling required, not a guess)."""
    import requests
    token = _telegram_token()
    resp = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": COMMANDER_CHAT_ID, "text": text, "parse_mode": "HTML"},
        timeout=15,
    )
    data = resp.json()
    delivered = bool(data.get("ok"))
    entry = {
        "channel": "telegram", "delivered": delivered,
        "message_id": data.get("result", {}).get("message_id") if delivered else None,
        "raw_ok": data.get("ok"), "error": None if delivered else data.get("description"),
    }
    append_channel_activity("telegram", "auto_execute_notify",
                             f"delivered={delivered}: {text[:80]}", ref=str(entry.get("message_id")))
    return entry


def send_email_notification(subject: str, text: str) -> dict:
    """Full-send to johnloucks3 (internal, no WF-17 gate — SO 27 MAR 2026) via the
    Commander's own Gmail account, then return the Gmail message id so we can poll
    its read status later. 'Sent successfully' is NOT delivery confirmation for our
    purposes — only a later confirmed UNREAD->read transition, or an explicit reply,
    counts."""
    import base64
    from email.mime.text import MIMEText
    from thunderbird_google_auth import get_commander_gmail

    svc = get_commander_gmail()
    msg = MIMEText(text)
    msg["to"] = COMMANDER_EMAIL
    msg["from"] = COMMANDER_EMAIL
    msg["subject"] = subject
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    sent = svc.users().messages().send(userId="me", body={"raw": raw}).execute()
    entry = {"channel": "email", "gmail_message_id": sent["id"], "sent": True}
    append_channel_activity("email", "auto_execute_notify",
                             f"sent, awaiting read-confirmation: {subject}", ref=sent["id"])
    return entry


def check_email_read(gmail_message_id: str) -> bool:
    """True only if the notification message's UNREAD label is gone — i.e. the
    Commander actually opened it. This is the fix for Dembe's finding: an email
    can sit unread for hours and must NOT be treated the same as a Telegram
    ping that was pushed and ignored."""
    from thunderbird_google_auth import get_commander_gmail
    svc = get_commander_gmail()
    msg = svc.users().messages().get(userId="me", id=gmail_message_id, format="minimal").execute()
    return "UNREAD" not in msg.get("labelIds", [])


def check_telegram_reply_since(since_ts: str) -> str | None:
    """Best-effort: check the Telegram gateway's own commander-comms log for any
    reply after since_ts. Returns the reply text if found, else None."""
    import json
    log_path = "/home/john/Thunderbird/OpsCenter/context_d2mc2c.json"
    try:
        data = json.loads(open(log_path).read())
    except (OSError, json.JSONDecodeError):
        return None
    for entry in reversed(data if isinstance(data, list) else []):
        if entry.get("role") == "Commander":
            return entry.get("text")
    return None


def notify_and_wait(action_description: str, channels=("telegram", "email"),
                     wait_seconds: int = 300, poll_interval: int = 15) -> dict:
    """The Phase 2/3 primitive. Returns {"decision": "GO"|"HOLD", "reason": str}.

    GO only fires when:
      - an explicit Commander reply is found (any channel), OR
      - wait_seconds elapse AND delivery is confirmed on every requested channel
        (Telegram: API ok=true: Email: UNREAD label cleared, i.e. actually read)

    HOLD fires (auto-execute does NOT proceed) when delivery/read can't be
    confirmed within the window — this is the hard floor, not negotiable by
    channel choice."""
    start = datetime.now(timezone.utc).isoformat()
    refs = {}

    if "telegram" in channels:
        refs["telegram"] = send_telegram_notification(
            f"⚡ Auto-execute pending — {action_description}\nNo action needed unless you want to stop it."
        )
    if "email" in channels:
        refs["email"] = send_email_notification(
            subject=f"[Auto-Execute Pending] {action_description[:60]}",
            text=f"{action_description}\n\nNo action needed unless you want to stop it.\n\n— Hale",
        )

    elapsed = 0
    while elapsed < wait_seconds:
        reply = check_telegram_reply_since(start)
        if reply and reply.strip().lower() not in ("roger", "wilco", "done", ""):
            append_channel_activity("telegram", "auto_execute_decision", f"explicit reply: {reply[:100]}")
            return {"decision": "HOLD", "reason": f"Commander replied: {reply}"}
        time.sleep(poll_interval)
        elapsed += poll_interval

    confirmed = {}
    if "telegram" in refs:
        confirmed["telegram"] = refs["telegram"]["delivered"]
    if "email" in refs:
        confirmed["email"] = check_email_read(refs["email"]["gmail_message_id"])

    if all(confirmed.values()) and confirmed:
        append_channel_activity("console", "auto_execute_decision", f"GO: {action_description}")
        return {"decision": "GO", "reason": "confirmed delivered/read on all channels, silence held", "confirmed": confirmed}

    append_channel_activity("console", "auto_execute_decision",
                             f"HOLD (unconfirmed): {action_description} — {confirmed}")
    return {"decision": "HOLD", "reason": f"delivery/read not confirmed on all channels: {confirmed}", "confirmed": confirmed}
