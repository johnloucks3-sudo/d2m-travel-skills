"""
Thunderbird OS — Z Fold6 Daily Connectivity Test
==================================================
Dreams2Memories Travel, LLC

Runs at 08:00 MDT daily. Verifies Commander's phone is reachable.
4-tier escalation: Telegram → Email → SMS (Twilio) → Conservation Mode

Usage:
  python3 thunderbird_zfold_test.py          # Run test
  python3 thunderbird_zfold_test.py --force  # Force all channels
"""

import json
import logging
import sys
import time
import base64
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path

THUNDERBIRD_DIR = Path(__file__).parent.parent
LOG_DIR = THUNDERBIRD_DIR / "logs"
LOG_FILE = LOG_DIR / "zfold_test.log"
STATE_FILE = THUNDERBIRD_DIR / "zfold_test_state.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr),
        logging.FileHandler(str(LOG_FILE), encoding="utf-8"),
    ],
)
logger = logging.getLogger("zfold_test")


def _load_env() -> dict:
    env = {}
    env_file = THUNDERBIRD_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def test_telegram() -> bool:
    """Send test message via Telegram, verify delivery."""
    try:
        import requests
        env = _load_env()
        token = env.get("TELEGRAM_BOT_TOKEN")
        chat_id = env.get("TELEGRAM_COMMANDER_ID")
        if not token or not chat_id:
            logger.error("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_COMMANDER_ID")
            return False

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        now = datetime.now().strftime("%H:%M MT")
        resp = requests.post(url, json={
            "chat_id": chat_id,
            "text": f"📱 Z Fold6 Daily Check — {now}\nAll systems operational.",
            "parse_mode": "HTML",
        }, timeout=15)

        if resp.status_code == 200:
            data = resp.json()
            if data.get("ok"):
                logger.info("Telegram test: PASS")
                return True
        logger.warning(f"Telegram test: FAIL (status {resp.status_code})")
        return False
    except Exception as e:
        logger.error(f"Telegram test error: {e}")
        return False


def test_email() -> bool:
    """Send test email to Commander."""
    try:
        sys.path.insert(0, str(THUNDERBIRD_DIR))
        from thunderbird_google_auth import get_credentials
        from googleapiclient.discovery import build

        creds = get_credentials()
        service = build("gmail", "v1", credentials=creds)

        now = datetime.now().strftime("%Y-%m-%d %H:%M MT")
        msg = MIMEText(f"Z Fold6 connectivity test — {now}\nTelegram channel was unreachable. Email fallback activated.")
        msg["to"] = "johnloucks3@gmail.com"
        msg["from"] = "d2mconcierge@gmail.com"
        msg["subject"] = f"[D2M] Z Fold6 Check — Telegram Down ({now})"
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        service.users().messages().send(userId="me", body={"raw": raw}).execute()
        logger.info("Email fallback: SENT")
        return True
    except Exception as e:
        logger.error(f"Email fallback failed: {e}")
        return False


def test_sms() -> bool:
    """Send SMS via Twilio (replaced tmomail.net 2026-04-01)."""
    try:
        from twilio.rest import Client
        client = Client("ACdc4e7b2beacb84b18c8b49ab8c8369cb", "***REMOVED-SECRET***")
        msg = client.messages.create(
            from_="+18776118189",
            to="+17192910742",
            body="D2M ALERT: TG+Email down. Check YOGA. -Thunderbird",
        )
        logger.info("SMS fallback (Twilio): SENT sid=%s", msg.sid)
        return True
    except Exception as e:
        logger.error("SMS fallback (Twilio) failed: %s", e)
        return False


def enter_conservation_mode():
    """All channels failed — reduce system load, wait for manual intervention."""
    logger.critical("ALL CHANNELS FAILED — entering conservation mode")
    state = {
        "status": "conservation_mode",
        "entered_at": datetime.now().isoformat(),
        "reason": "All notification channels unreachable",
        "action": "Reduced timer frequency. Awaiting Commander manual check.",
    }
    STATE_FILE.write_text(json.dumps(state, indent=2))


def run_connectivity_test(force_all: bool = False) -> dict:
    """Run 4-tier connectivity test."""
    logger.info("=" * 50)
    logger.info("Z FOLD6 CONNECTIVITY TEST — %s", datetime.now().strftime("%Y-%m-%d %H:%M"))
    logger.info("=" * 50)

    result = {
        "timestamp": datetime.now().isoformat(),
        "telegram": None,
        "email": None,
        "sms": None,
        "overall": "UNKNOWN",
    }

    # Tier 1: Telegram
    tg_ok = test_telegram()
    result["telegram"] = "PASS" if tg_ok else "FAIL"

    if tg_ok and not force_all:
        result["overall"] = "GREEN"
        result["email"] = "SKIPPED"
        result["sms"] = "SKIPPED"
        _save_state(result)
        return result

    # Tier 2: Email (Telegram failed or force mode)
    logger.warning("Telegram failed — escalating to email")
    email_ok = test_email()
    result["email"] = "PASS" if email_ok else "FAIL"

    if email_ok and not force_all:
        result["overall"] = "YELLOW"
        result["sms"] = "SKIPPED"
        _save_state(result)
        return result

    # Tier 3: SMS via Twilio (Email also failed)
    logger.warning("Email failed — escalating to SMS")
    sms_ok = test_sms()
    result["sms"] = "PASS" if sms_ok else "FAIL"

    if sms_ok:
        result["overall"] = "YELLOW"
        _save_state(result)
        return result

    # Tier 4: All failed — conservation mode
    result["overall"] = "RED"
    enter_conservation_mode()
    _save_state(result)
    return result


def _save_state(result: dict):
    """Save test results to state file."""
    STATE_FILE.write_text(json.dumps(result, indent=2))
    logger.info(f"Result: {result['overall']}")


if __name__ == "__main__":
    force = "--force" in sys.argv
    result = run_connectivity_test(force_all=force)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["overall"] in ("GREEN", "YELLOW") else 1)
