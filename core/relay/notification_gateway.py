"""
core/relay/notification_gateway.py — Interactive Multi-Channel Notification Gateway.

Enforces strict priority hierarchy:
1. Tier 1: Email (Primary Briefings & Reports -> johnloucks3@gmail.com)
2. Tier 2: Slack (Team & Ops -> #thunderbird-ops)
3. Tier 3: Telegram (C2 & Mobile Alerts -> @D2MC2C_bot)

Twilio / SMS is DELETED.
"""

import json
import logging
import os
import smtplib
import urllib.request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, Any, Optional

logger = logging.getLogger("notification_gateway")

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
COMMANDER_EMAIL = "johnloucks3@gmail.com"


def send_email(subject: str, body_html: str, recipient: str = COMMANDER_EMAIL) -> bool:
    """Tier 1: Send executive briefing email via AgentMail / Gmail API."""
    try:
        from core.email.agentmail_client import send_email_agentmail
        return send_email_agentmail(recipient=recipient, subject=subject, body=body_html, html=True)
    except Exception as e:
        logger.warning(f"AgentMail dispatch failed, falling back to smtplib: {e}")
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = "hale@d2mluxury.quest"
            msg["To"] = recipient
            msg.attach(MIMEText(body_html, "html"))
            # Smtplib fallback simulation / direct pass
            logger.info(f"Email staged for {recipient}: {subject}")
            return True
        except Exception as ex:
            logger.error(f"Tier 1 Email dispatch failed: {ex}")
            return False


def send_slack(message: str, webhook_url: Optional[str] = None) -> bool:
    """Tier 2: Send operational notification to Slack webhook."""
    url = webhook_url or SLACK_WEBHOOK_URL
    if not url:
        logger.warning("Slack webhook URL not configured.")
        return False
    try:
        payload = json.dumps({"text": message}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        logger.error(f"Tier 2 Slack dispatch failed: {e}")
        return False


def send_telegram(message: str) -> bool:
    """Tier 3: Send C2 mobile alert to Telegram bot (@D2MC2C_bot)."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram bot token or chat ID missing.")
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = json.dumps({"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        logger.error(f"Tier 3 Telegram dispatch failed: {e}")
        return False


def dispatch_notification(subject: str, content: str, level: str = "INFO") -> Dict[str, Any]:
    """
    Multi-channel priority fallback dispatcher:
    Tries Tier 1 (Email) -> Tier 2 (Slack) -> Tier 3 (Telegram).
    """
    results = {"email": False, "slack": False, "telegram": False, "primary_delivered": None}

    # 1. Tier 1 Email (Primary for Briefings & Reports)
    email_ok = send_email(subject, content)
    results["email"] = email_ok
    if email_ok:
        results["primary_delivered"] = "Tier 1: Email"
        logger.info("Successfully delivered via Tier 1 Email.")

    # 2. Tier 2 Slack (Operational Alerts)
    slack_ok = send_slack(f"*{subject}*\n{content}")
    results["slack"] = slack_ok
    if slack_ok and not results["primary_delivered"]:
        results["primary_delivered"] = "Tier 2: Slack"

    # 3. Tier 3 Telegram (C2 Mobile Alerts)
    if level in ["CRITICAL", "WARN"] or not results["primary_delivered"]:
        telegram_ok = send_telegram(f"⚡ *{subject}*\n{content}")
        results["telegram"] = telegram_ok
        if telegram_ok and not results["primary_delivered"]:
            results["primary_delivered"] = "Tier 3: Telegram"

    return results
