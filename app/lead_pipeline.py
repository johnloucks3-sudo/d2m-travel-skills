"""
D2M web lead pipeline — capture → Telegram alert → draft spawn
Self-contained: no core/ imports, works from web app context.
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

COMMANDER_ID = 7554895206
ENV_FILE = Path("/home/john/Thunderbird/.env")
WORKER_SCRIPT = Path("/home/john/Thunderbird/scripts/web_lead_draft_worker.py")
OUTPUT_DIR = Path("/home/john/Thunderbird/output")
LOG_DIR = Path("/home/john/Thunderbird/logs")


def _load_tg_token() -> str:
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if line.startswith("TELEGRAM_C2_BOT_TOKEN="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return os.environ.get("TELEGRAM_C2_BOT_TOKEN", "")


def _tg_send(text: str) -> None:
    token = _load_tg_token()
    if not token:
        logger.warning("lead_pipeline: no Telegram token, alert not sent")
        return
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": COMMANDER_ID, "text": text, "parse_mode": "HTML"},
            timeout=8,
        )
        if not r.json().get("ok"):
            logger.warning("Telegram send failed: %s", r.text[:200])
    except Exception as exc:
        logger.warning("Telegram send exception: %s", exc)


def notify_soft_lead(lead: dict) -> None:
    """Notify Commander of a soft lead (name/email captured in chat)."""
    name = lead.get("name") or "—"
    email = lead.get("email") or "—"
    msg = (
        f"📋 <b>D2M Web Lead — New Contact</b>\n\n"
        f"<b>Name:</b> {name}\n"
        f"<b>Email:</b> {email}\n"
        f"<b>Source:</b> Dani chat\n\n"
        f"Lead logged. Staff will follow up."
    )
    _tg_send(msg)


def notify_rfp(lead: dict) -> None:
    """Notify Commander of a pricing request (RFP). High priority."""
    name = lead.get("name") or "—"
    email = lead.get("email") or "—"
    cruise = lead.get("cruise_interest") or "—"
    party = lead.get("party") or "—"
    cabin = lead.get("cabin_preference") or "—"
    window = lead.get("travel_window") or "—"
    budget = lead.get("budget_signal") or "—"

    msg = (
        f"🔥 <b>PRICING REQUEST — 2hr SLA</b>\n\n"
        f"<b>Name:</b> {name}\n"
        f"<b>Email:</b> {email}\n"
        f"<b>Cruise:</b> {cruise}\n"
        f"<b>Party:</b> {party}\n"
        f"<b>Cabin:</b> {cabin}\n"
        f"<b>Window:</b> {window}\n"
        f"<b>Budget signal:</b> {budget}\n\n"
        f"Staff is drafting proposal. Draft will appear in Commander-Review."
    )
    _tg_send(msg)


def notify_intake_form(data: dict) -> None:
    """Notify Commander of a Request-a-Voyage form submission."""
    name = data.get("name") or "—"
    email = data.get("email") or "—"
    dest = data.get("destination") or "—"
    window = data.get("travel_window") or "—"
    budget = data.get("budget") or "—"
    party = data.get("party_size") or "—"
    comments = (data.get("comments") or "")[:300]

    msg = (
        f"📝 <b>D2M Request-a-Voyage Form</b>\n\n"
        f"<b>Name:</b> {name}\n"
        f"<b>Email:</b> {email}\n"
        f"<b>Destination:</b> {dest}\n"
        f"<b>Window:</b> {window}\n"
        f"<b>Budget:</b> {budget}\n"
        f"<b>Party:</b> {party}\n"
    )
    if comments:
        msg += f"\n<b>Comments:</b> {comments}"
    _tg_send(msg)


def spawn_draft_worker(lead: dict, conversation_context: str = "") -> str:
    """
    Spawn detached draft worker. Returns lead_id for tracking.
    Worker: drafts proposal email → Gmail Commander-Review → Telegram completion alert.
    """
    lead_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    lead_file = OUTPUT_DIR / f"web_lead_{lead_id}.json"
    payload = {**lead, "lead_id": lead_id, "conversation_context": conversation_context}
    lead_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    log_file = LOG_DIR / f"web_lead_{lead_id}.log"

    if not WORKER_SCRIPT.exists():
        logger.error("Draft worker script not found: %s", WORKER_SCRIPT)
        return lead_id

    try:
        subprocess.Popen(
            ["python3", str(WORKER_SCRIPT), str(lead_file)],
            start_new_session=True,
            stdout=open(log_file, "w"),
            stderr=subprocess.STDOUT,
        )
        logger.info("Draft worker spawned for lead %s", lead_id)
    except Exception as exc:
        logger.error("Failed to spawn draft worker: %s", exc)

    return lead_id
