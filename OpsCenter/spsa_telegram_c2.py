#!/usr/bin/env python3
"""
SPSA → Telegram C2 Bridge
Sends real-time RED case alerts to Commander with brief and recommendation
Attached to SPSA intake job for immediate escalation
"""

import json
import logging
import os
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("spsa_telegram")

ROOT = Path("/home/john/Thunderbird")
COMMANDER_ID = 7554895206


def _load_env() -> dict:
    """Load .env file into a dict."""
    env = {}
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def send_telegram_c2_alert(message: str, subject: str = "SPSA RED Alert"):
    """Send alert via Telegram C2 (Commander channel)."""
    import requests

    env = _load_env()
    token = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("TELEGRAM_C2_BOT_TOKEN") or env.get("TELEGRAM_BOT_TOKEN") or env.get("TELEGRAM_C2_BOT_TOKEN")
    chat_id = COMMANDER_ID

    if not token:
        logger.error("Telegram credentials not configured — alert not sent")
        return False

    text = f"<b>{subject}</b>\n{message}" if subject else message
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    try:
        resp = requests.post(url, json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
        }, timeout=10)

        if resp.status_code == 200:
            logger.info(f"✅ Telegram C2 alert sent: {message[:60]}")
            return True
        else:
            logger.error(f"Telegram alert failed: {resp.status_code} {resp.text[:200]}")
            return False
    except Exception as e:
        logger.error(f"Telegram alert failed: {e}")
        return False


def alert_red_cases():
    """Find and alert all RED SPSA cases since last alert."""
    from core.ops.thunderbird_spsa import get_active_cases

    try:
        red_cases = get_active_cases(severity='RED')

        if not red_cases:
            logger.info("No RED cases to alert")
            return

        for case in red_cases:
            # Check if we've already alerted this case
            alert_record = ROOT / "logs" / "spsa" / f"{case.case_id}_alerted.txt"
            if alert_record.exists():
                logger.info(f"Case {case.case_id} already alerted, skipping")
                continue

            # Format message
            message = f"""
<b>CASE:</b> {case.case_id}
<b>SEVERITY:</b> 🔴 RED
<b>SOURCE:</b> {case.source}

<b>PROBLEM:</b>
{case.problem_statement}

<b>FACTORS:</b>
{chr(10).join(f'• {f}' for f in case.factors[:3])}

<b>RECOMMENDED ACTION:</b>
{case.recommendation} — {case.recommendation_rationale}

<b>TIMELINE:</b> {case.timeline_hours}h
<b>RISK:</b> {case.risk_summary}

<i>Use /spsa {case.case_id} for full brief or /approve to accept recommendation</i>
""".strip()

            # Send alert
            if send_telegram_c2_alert(message, f"SPSA RED — {case.case_id}"):
                # Record that we alerted this case
                alert_record.parent.mkdir(parents=True, exist_ok=True)
                alert_record.write_text(f"Alerted at {datetime.now().isoformat()}")
                logger.info(f"✅ RED case {case.case_id} alerted to Commander")

    except Exception as e:
        logger.error(f"Failed to alert RED cases: {e}")


def handle_spsa_command(case_id: str) -> str:
    """
    Handle /spsa CASE_ID command — return full SPSA brief.
    Usage: /spsa SPSA-20260502-25089
    """
    from core.ops.thunderbird_spsa import load_case

    case = load_case(case_id)
    if not case:
        return f"❌ Case not found: {case_id}"

    return case.to_brief()


def handle_approve_command(case_id: str) -> str:
    """
    Handle /approve CASE_ID command — approve case and execute if LOW risk.
    Usage: /approve SPSA-20260502-25089
    """
    from core.ops.thunderbird_spsa import load_case, update_case_status, classify_risk

    case = load_case(case_id)
    if not case:
        return f"❌ Case not found: {case_id}"

    if case.status not in ["OPEN", "UNDER_REVIEW"]:
        return f"⚠️ Case {case_id} already in {case.status} state"

    # Mark as DECIDED
    update_case_status(case_id, "DECIDED", decision="Approved")

    # Check risk level
    risk = classify_risk(case)
    if risk == "LOW":
        update_case_status(case_id, "IMPLEMENTING")
        return f"""✅ **APPROVED & EXECUTING** (LOW RISK)

Case: {case_id}
Recommendation: {case.recommendation}
Timeline: {case.timeline_hours}h

Status: IMPLEMENTING
(COS will report completion when done)"""
    else:
        return f"""✅ **APPROVED** (MEDIUM/HIGH RISK — Awaiting execution)

Case: {case_id}
Recommendation: {case.recommendation}
Risk: {risk}
Timeline: {case.timeline_hours}h

Status: DECIDED
(COS will execute and report back)"""


if __name__ == "__main__":
    alert_red_cases()
