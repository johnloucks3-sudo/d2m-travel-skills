#!/usr/bin/env python3
"""
Payment Deadline SMS Alerts
============================
Checks upcoming payment deadlines and sends SMS reminders.
Run daily via cron or systemd timer.

Sends alerts at: 14 days, 7 days, 3 days, 1 day before deadline.
"""
import json
import logging
import base64
import sys
from datetime import datetime, date
from email.mime.text import MIMEText
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from thunderbird_gmail import _get_gmail_service, USER_EMAIL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SMS_GATEWAY = "7192910742@tmomail.net"
ALERT_FILE = Path(__file__).parent / "payment_alerts_sent.json"

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


def _send_sms(message, subject="D2M Payment Alert"):
    service = _get_gmail_service()
    msg = MIMEText(message[:160])
    msg["to"] = SMS_GATEWAY
    msg["from"] = USER_EMAIL
    msg["subject"] = subject
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw}).execute()
    logger.info(f"SMS sent: {message[:80]}")


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
                _send_sms(msg)
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
            _send_sms(summary, "D2M Daily Summary")
            sent[f"summary_{today.isoformat()}"] = datetime.now().isoformat()
            alerts_sent += 1
        except Exception as e:
            logger.error(f"Failed to send daily summary: {e}")
        _save_sent(sent)

    logger.info(f"Payment alert check complete. {alerts_sent} alerts sent.")
    return alerts_sent


if __name__ == "__main__":
    check_and_alert()
