#!/usr/bin/env python3
"""
Payment Deadline Alerts (Telegram C2)
======================================
Checks upcoming payment deadlines and sends Telegram reminders.
Run daily via cron or systemd timer.

Sends alerts at: 14 days, 7 days, 3 days, 1 day before deadline.
(Replaced tmomail SMS gateway with Telegram C2 bot 2026-03-31.)
"""
import json
import logging
import os
import sys
from datetime import datetime, date
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

THUNDERBIRD_DIR = Path(__file__).parent.parent
ALERT_FILE = THUNDERBIRD_DIR / "payment_alerts_sent.json"

# ── Compatibility stub — SMS_GATEWAY removed 2026-03-31 (replaced by Telegram) ──
# Kept here so legacy imports (thunderbird_heartbeat.py) don't crash
SMS_GATEWAY = None  # was: tmomail SMS gateway — now Telegram C2

# ── Payment deadlines (from THUNDERBIRD_MASTER_PLAN Key Deadlines) ──
# Viking 3 suites total $21,244 — amounts below are per-booking estimates
DEADLINES = [
    # Viking Panama Canal — FPD Mar 31, 2026
    {"client": "Kuklinski (Kyle & Rosalie)", "cruise": "Viking Mars", "conf": "9593880", "date": "2026-03-31", "amount": "$7,548"},
    {"client": "Kuklinski (Roger & Nick)", "cruise": "Viking Mars", "conf": "9593873", "date": "2026-03-31", "amount": "$7,548"},
    {"client": "Morton (Josh & Erica)", "cruise": "Viking Mars", "conf": "9595029", "date": "2026-03-31", "amount": "$6,148"},
    # Regent Scandinavia — FPD Apr 1, 2026
    {"client": "Furlow (John & Melissa)", "cruise": "Regent Grandeur", "conf": "3071222", "date": "2026-04-01", "amount": "$15,486"},
    {"client": "Ely/Darrow (Al & Amy)", "cruise": "Regent Grandeur", "conf": "3096289", "date": "2026-04-01", "amount": "$16,640"},
    {"client": "Nichols (Larry & Heidi)", "cruise": "Regent Grandeur", "conf": "3078056", "date": "2026-04-01", "amount": "$14,986"},
    # McLeod Silversea — PAID (monitoring only)
    {"client": "McLeod (Erik & Melissa)", "cruise": "Silver Muse", "conf": "298475-25", "date": "2026-06-23", "amount": "PAID", "note": "embark date monitor"},
    # McLeod Regent Lesser Antilles — FPD TBD (~Sep 2026)
    {"client": "McLeod (Erik & Melissa)", "cruise": "Regent Grandeur", "conf": "2984034", "date": "2026-07-22", "amount": "$12,393.15", "note": "Lesser Antilles Dec 19-29, Suite 863"},
    # Loucks personal — Silver Nova Apr 23 (already paid?)
    {"client": "Loucks (John & Susan)", "cruise": "Silver Nova", "conf": "566910-25", "date": "2026-04-23", "amount": "PAID", "note": "embark date monitor"},
    # Loucks Regent Panama Canal — FPD TBD (~Sep 2026)
    {"client": "Loucks (John & Susan)", "cruise": "Regent Panama Canal", "conf": "3122006", "date": "2026-09-30", "amount": "TBD", "note": "confirm FPD with Regent"},
    # Westbrook — Silver Nova (same sailing as Loucks)
    {"client": "Westbrook (Ron & Linda)", "cruise": "Silver Nova", "conf": "566904-25", "date": "2026-04-23", "amount": "PAID", "note": "embark date monitor"},
]

ALERT_DAYS = [14, 7, 3, 1]


def _load_sent():
    if ALERT_FILE.exists():
        return json.loads(ALERT_FILE.read_text(encoding="utf-8"))
    return {}


def _save_sent(sent):
    ALERT_FILE.write_text(json.dumps(sent, indent=2), encoding="utf-8")


def _load_env() -> dict:
    """Load .env file into a dict."""
    env = {}
    env_file = THUNDERBIRD_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def _send_telegram_alert(message, subject="D2M Payment Alert"):
    """Send alert via Telegram C2 bot (replaced tmomail SMS 2026-03-31)."""
    import requests
    env = _load_env()
    token = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("TELEGRAM_C2_BOT_TOKEN") or env.get("TELEGRAM_BOT_TOKEN") or env.get("TELEGRAM_C2_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_COMMANDER_ID") or env.get("TELEGRAM_COMMANDER_ID")
    if not token or not chat_id:
        logger.error("Telegram credentials not configured — alert not sent")
        return
    text = f"<b>{subject}</b>\n{message}" if subject else message
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        resp = requests.post(url, json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
        }, timeout=10)
        if resp.status_code == 200:
            logger.info(f"Telegram alert sent: {message[:80]}")
        else:
            logger.error(f"Telegram alert failed: {resp.status_code} {resp.text[:200]}")
    except Exception as e:
        logger.error(f"Telegram alert failed: {e}")


def check_and_alert():
    today = date.today()
    sent = _load_sent()
    alerts_sent = 0

    for d in DEADLINES:
        # Skip PAID and TBD entries for payment alerts
        if d["amount"] in ("PAID", "TBD"):
            continue

        deadline = date.fromisoformat(d["date"])
        days_left = (deadline - today).days

        if days_left < 0:
            continue

        if days_left in ALERT_DAYS:
            key = f"{d['client']}_{d['date']}_{days_left}d"
            if key in sent:
                continue

            if days_left == 1:
                msg = f"TOMORROW: {d['client']} {d['cruise']} {d['amount']} due {d['date']}"
            else:
                msg = f"{days_left}d: {d['client']} {d['cruise']} {d['amount']} due {d['date']}"

            try:
                _send_telegram_alert(msg)
                sent[key] = datetime.now().isoformat()
                alerts_sent += 1
            except Exception as e:
                logger.error(f"Failed to send alert for {d['client']}: {e}")

    _save_sent(sent)

    # Daily summary if any deadlines within 14 days
    upcoming = [d for d in DEADLINES if 0 <= (date.fromisoformat(d["date"]) - today).days <= 14]
    if upcoming and f"summary_{today.isoformat()}" not in sent:
        total_due = len(upcoming)
        nearest = min(upcoming, key=lambda x: date.fromisoformat(x["date"]))
        days_to_nearest = (date.fromisoformat(nearest["date"]) - today).days
        summary = f"D2M: {total_due} payments due within 14d. Next: {nearest['client']} in {days_to_nearest}d"
        try:
            _send_telegram_alert(summary, "D2M Daily Summary")
            sent[f"summary_{today.isoformat()}"] = datetime.now().isoformat()
            alerts_sent += 1
        except Exception as e:
            logger.error(f"Failed to send daily summary: {e}")
        _save_sent(sent)

    logger.info(f"Payment alert check complete. {alerts_sent} alerts sent.")
    return alerts_sent


if __name__ == "__main__":
    check_and_alert()

# AGENTS DOCUMENTATION
# - Updated to enforce free-model guardrail for OpenRouter.
# - See docs/AGENTS_MODEL_GUIDE.md for allowed models and usage.
