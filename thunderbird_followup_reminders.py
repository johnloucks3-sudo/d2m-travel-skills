"""
Thunderbird Client Follow-Up Reminders
========================================
Scans dossiers for client inactivity and generates follow-up suggestions.
Dani (A3) drafts the suggestion, Harlan (A9) flags overdue financials.

Run daily after morning briefing. Sends Telegram alert summary of clients needing attention.

Usage:
    from thunderbird_followup_reminders import scan_and_remind
    scan_and_remind()
"""

import json
import logging
import os
import re
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
DOSSIERS_DIR = THUNDERBIRD_DIR / "Dossiers"
STATE_FILE = THUNDERBIRD_DIR / "followup_state.json"

# Inactivity thresholds
WARN_DAYS = 7       # Flag at 7 days
URGENT_DAYS = 14    # Urgent at 14 days
OVERDUE_DAYS = 21   # Critical at 21 days

# Patterns to extract dates from dossier email logs
DATE_PATTERNS = [
    r"\*\*Mar\s+(\d+)",   # **Mar 6 — ...
    r"\*\*Feb\s+(\d+)",
    r"\*\*Jan\s+(\d+)",
    r"\*\*Apr\s+(\d+)",
]


def _parse_last_contact(dossier_text: str) -> Optional[date]:
    """Extract the most recent email date from a dossier's EMAIL LOG section."""
    # Find the EMAIL LOG section
    log_match = re.search(r"### EMAIL LOG.*?\n(.*?)(?=\n###|\Z)", dossier_text, re.DOTALL)
    if not log_match:
        return None

    log_text = log_match.group(1)

    # Extract all dates mentioned (format: **Mon DD — ...)
    months = {
        "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
        "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
    }

    dates = []
    for match in re.finditer(r"\*\*(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d+)", log_text):
        month_str, day_str = match.group(1), match.group(2)
        month = months.get(month_str)
        if month:
            try:
                # Assume current year
                d = date(2026, month, int(day_str))
                dates.append(d)
            except ValueError:
                continue

    return max(dates) if dates else None


def _parse_open_actions(dossier_text: str) -> list[str]:
    """Extract unchecked action items from dossier."""
    actions = []
    for match in re.finditer(r"\d+\.\s+\[ \]\s+\*\*(.*?)\*\*", dossier_text):
        actions.append(match.group(1))
    return actions


def _parse_payment_info(dossier_text: str) -> Optional[dict]:
    """Extract final payment date and amount if present."""
    fpd_match = re.search(r"FINAL PAYMENT.*?\$([0-9,]+).*?by\s+(.*?)[\s|]", dossier_text, re.IGNORECASE)
    if not fpd_match:
        fpd_match = re.search(r"Final Payment.*?(\w+ \d+,? \d{4}).*?\$([0-9,]+)", dossier_text, re.IGNORECASE)

    # Simpler: look for FPD pattern
    amount_match = re.search(r"\$([0-9,]+(?:\.\d{2})?)", dossier_text)
    date_match = re.search(r"(Apr|Mar|May|Jun)\s+\d+", dossier_text)

    return None  # Best effort, payment alerts handle this separately


def _extract_client_name(filename: str) -> str:
    """Extract readable client name from dossier filename."""
    # Furlow_Regent_3071222.md -> Furlow
    # Loucks_Personal_SilverNova_Japan.md -> Loucks
    name = filename.replace(".md", "").split("_")[0]
    return name


def scan_dossiers() -> list[dict]:
    """Scan all dossiers and return clients needing follow-up."""
    if not DOSSIERS_DIR.exists():
        logger.warning(f"Dossiers directory not found: {DOSSIERS_DIR}")
        return []

    today = date.today()
    results = []

    for dossier_file in sorted(DOSSIERS_DIR.glob("*.md")):
        text = dossier_file.read_text(encoding="utf-8")
        client = _extract_client_name(dossier_file.name)
        last_contact = _parse_last_contact(text)
        open_actions = _parse_open_actions(text)

        if last_contact is None:
            continue

        days_silent = (today - last_contact).days

        if days_silent >= WARN_DAYS:
            priority = "CRITICAL" if days_silent >= OVERDUE_DAYS else \
                       "URGENT" if days_silent >= URGENT_DAYS else "WARN"

            results.append({
                "client": client,
                "file": dossier_file.name,
                "last_contact": last_contact.isoformat(),
                "days_silent": days_silent,
                "priority": priority,
                "open_actions": open_actions[:3],  # Top 3
                "action_count": len(open_actions),
            })

    # Sort by days silent (most overdue first)
    results.sort(key=lambda r: -r["days_silent"])
    return results


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


def _send_telegram_alert(message: str, subject: str = "D2M Follow-Up"):
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


def scan_and_remind() -> dict:
    """Main entry point. Scan dossiers and send reminders for inactive clients."""
    results = scan_dossiers()
    state = _load_state()
    today_str = date.today().isoformat()

    # Don't send more than one alert summary per day
    if state.get("last_summary_date") == today_str:
        logger.info("Already sent today's follow-up summary. Skipping alert.")
        return {"scanned": len(results), "alert_sent": False, "clients": results}

    if not results:
        logger.info("No clients need follow-up. All clear.")
        return {"scanned": 0, "sms_sent": False, "clients": []}

    # Build summary
    critical = [r for r in results if r["priority"] == "CRITICAL"]
    urgent = [r for r in results if r["priority"] == "URGENT"]
    warn = [r for r in results if r["priority"] == "WARN"]

    parts = []
    if critical:
        names = ", ".join(r["client"] for r in critical[:3])
        parts.append(f"CRIT({len(critical)}): {names}")
    if urgent:
        names = ", ".join(r["client"] for r in urgent[:3])
        parts.append(f"URG({len(urgent)}): {names}")
    if warn:
        parts.append(f"WARN: {len(warn)} clients")

    alert_msg = f"D2M Follow-Up: {' | '.join(parts)}"

    try:
        _send_telegram_alert(alert_msg)
        state["last_summary_date"] = today_str
        state["last_results"] = [
            {"client": r["client"], "days": r["days_silent"], "priority": r["priority"]}
            for r in results
        ]
        _save_state(state)
        return {"scanned": len(results), "alert_sent": True, "clients": results}
    except Exception as e:
        logger.error(f"Failed to send follow-up alert: {e}")
        return {"scanned": len(results), "alert_sent": False, "error": str(e), "clients": results}


def _load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {}


def _save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


if __name__ == "__main__":
    results = scan_dossiers()
    if results:
        print(f"\n{'='*60}")
        print(f"FOLLOW-UP SCAN — {date.today()}")
        print(f"{'='*60}")
        for r in results:
            emoji = {"CRITICAL": "🔴", "URGENT": "🟡", "WARN": "🟢"}[r["priority"]]
            print(f"\n{emoji} {r['priority']} — {r['client']} ({r['days_silent']}d silent)")
            print(f"   Last contact: {r['last_contact']}")
            if r['open_actions']:
                print(f"   Open items: {', '.join(r['open_actions'][:3])}")
    else:
        print("All clients recently contacted. No follow-ups needed.")
