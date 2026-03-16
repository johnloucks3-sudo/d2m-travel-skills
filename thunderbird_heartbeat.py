#!/usr/bin/env python3
"""
Thunderbird Persona Heartbeat System
======================================
Dreams2Memories Travel, LLC

Proactive scanning system where each persona heartbeat scans its domain
and delivers findings via SMS, Gmail draft, or Commander Review.

Delivery channels:
  - SMS: via T-Mobile gateway through Gmail (reuses payment_alerts pattern)
  - Gmail Draft: HTML-formatted draft for review
  - Commander Review: Gmail draft with THUNDERBIRD-Commander-Review label + SMS notify

Personas with heartbeats:
  - COS-EXEC (Hale + Solberg-Vega): every 30 min, 0600-2000
  - A3 Moreau: daily 0700 — Booking Ops
  - A9 Harlan: daily 0900 — Finance
  - A2 Dembe: daily 0630 — Intel
  - A6 Luna (EXEC creative): daily 1000 — Creative opportunities
  - A10 Ikeda: daily 0800 — Crisis/Logistics
  - CH Washington: weekly Friday 1500 — Wisdom/Morale

Usage:
  python thunderbird_heartbeat.py --cos-exec     # Run COS-EXEC now
  python thunderbird_heartbeat.py --daily        # Run all daily heartbeats
  python thunderbird_heartbeat.py --weekly       # Run CH weekly
  python thunderbird_heartbeat.py --all          # Run everything
  python thunderbird_heartbeat.py --status       # Show last heartbeat times
"""

import json
import logging
import re
import hashlib
import base64
import sys
import argparse
from datetime import datetime, date, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Optional

# ── Path setup ──────────────────────────────────────────────────────────────
THUNDERBIRD_DIR = Path(__file__).parent
sys.path.insert(0, str(THUNDERBIRD_DIR))

from thunderbird_gmail import _get_gmail_service, USER_EMAIL
from thunderbird_payment_alerts import DEADLINES, SMS_GATEWAY

# ── Configuration ───────────────────────────────────────────────────────────
DOSSIERS_DIR = THUNDERBIRD_DIR / "Dossiers"
STATE_FILE = THUNDERBIRD_DIR / "heartbeat_state.json"
LOG_FILE = THUNDERBIRD_DIR / "heartbeat.log"
API_COST_LOG = THUNDERBIRD_DIR / "api_cost_log.jsonl"
CALENDAR_TOKEN_FILE = THUNDERBIRD_DIR / "calendar_token.json"
CALENDAR_OAUTH_FILE = THUNDERBIRD_DIR / "gmail_oauth_credentials.json"
OWNER_EMAIL = "johnloucks3@gmail.com"
COMMANDER_REVIEW_LABEL = "THUNDERBIRD-Commander-Review"

# Calendar API scopes (read-only for heartbeat)
CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

# ── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr),
        logging.FileHandler(str(LOG_FILE), encoding="utf-8"),
    ],
)
logger = logging.getLogger("thunderbird_heartbeat")

# ── D2M HTML Style ──────────────────────────────────────────────────────────
D2M_HTML_STYLE = """
<style>
  body { font-family: 'Segoe UI', Arial, sans-serif; background: #0d1b2e; color: #e0e0e0; margin: 0; padding: 20px; }
  .container { max-width: 700px; margin: 0 auto; background: #152540; border-radius: 8px; padding: 24px; border: 1px solid #1e3358; }
  h1 { color: #c9a84c; font-size: 20px; margin-top: 0; border-bottom: 2px solid #c9a84c; padding-bottom: 8px; }
  h2 { color: #e8c97a; font-size: 16px; margin-top: 20px; }
  h3 { color: #c9a84c; font-size: 14px; margin-top: 16px; }
  .section { background: #1e3358; border-radius: 6px; padding: 14px; margin: 12px 0; }
  .urgent { border-left: 4px solid #ff4444; }
  .action { border-left: 4px solid #c9a84c; }
  .info { border-left: 4px solid #4488ff; }
  .ok { border-left: 4px solid #44cc44; }
  table { width: 100%; border-collapse: collapse; margin: 8px 0; }
  th { text-align: left; color: #c9a84c; padding: 6px 10px; border-bottom: 1px solid #1e3358; font-size: 13px; }
  td { padding: 6px 10px; border-bottom: 1px solid #1e3358; font-size: 13px; }
  .label { color: #8a9ab5; font-size: 12px; }
  .amount { color: #e8c97a; font-weight: bold; }
  .days-warn { color: #ffaa00; }
  .days-urgent { color: #ff4444; font-weight: bold; }
  .days-ok { color: #44cc44; }
  .footer { text-align: center; color: #8a9ab5; font-size: 11px; margin-top: 20px; padding-top: 12px; border-top: 1px solid #1e3358; }
  .persona { color: #c9a84c; font-weight: bold; }
  ul { margin: 4px 0; padding-left: 20px; }
  li { margin: 3px 0; font-size: 13px; }
</style>
"""


# ============================================================================
# STATE MANAGEMENT
# ============================================================================

def _load_state() -> dict:
    """Load heartbeat state file."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_state(state: dict):
    """Save heartbeat state file."""
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _item_hash(text: str) -> str:
    """Generate short hash for dedup key."""
    return hashlib.md5(text.encode()).hexdigest()[:8]


def _was_sent(state: dict, persona: str, trigger_type: str, item_id: str) -> bool:
    """Check if a specific heartbeat item was already sent today."""
    today = date.today().isoformat()
    key = f"{persona}_{trigger_type}_{today}_{item_id}"
    return key in state.get("sent_keys", {})


def _mark_sent(state: dict, persona: str, trigger_type: str, item_id: str):
    """Mark a heartbeat item as sent."""
    today = date.today().isoformat()
    key = f"{persona}_{trigger_type}_{today}_{item_id}"
    if "sent_keys" not in state:
        state["sent_keys"] = {}
    state["sent_keys"][key] = datetime.now().isoformat()


def _record_heartbeat(state: dict, persona: str):
    """Record that a heartbeat ran."""
    if "last_run" not in state:
        state["last_run"] = {}
    state["last_run"][persona] = datetime.now().isoformat()


def _prune_old_keys(state: dict, days: int = 3):
    """Remove sent_keys older than N days to keep state file small."""
    if "sent_keys" not in state:
        return
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    state["sent_keys"] = {
        k: v for k, v in state["sent_keys"].items()
        if k.split("_")[2] >= cutoff  # date is 3rd segment
    }


# ============================================================================
# DELIVERY CHANNELS
# ============================================================================

def _send_sms(message: str, subject: str = "D2M Heartbeat"):
    """Send SMS via T-Mobile gateway through Gmail."""
    try:
        service = _get_gmail_service()
        msg = MIMEText(message[:160])
        msg["to"] = SMS_GATEWAY
        msg["from"] = USER_EMAIL
        msg["subject"] = subject
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        service.users().messages().send(userId="me", body={"raw": raw}).execute()
        logger.info(f"SMS sent: {message[:80]}")
    except Exception as e:
        logger.error(f"SMS send failed: {e}")


def _create_html_draft(subject: str, html_body: str, label_name: Optional[str] = None) -> Optional[str]:
    """Create a Gmail draft with HTML body. Optionally apply a label."""
    try:
        service = _get_gmail_service()

        full_html = f"<html><head>{D2M_HTML_STYLE}</head><body><div class='container'>{html_body}</div></body></html>"

        message = MIMEMultipart("alternative")
        message["to"] = OWNER_EMAIL
        message["from"] = USER_EMAIL
        message["subject"] = subject

        # Plain text fallback
        plain_text = re.sub(r"<[^>]+>", "", html_body)
        plain_text = re.sub(r"\s+", " ", plain_text).strip()
        message.attach(MIMEText(plain_text[:5000], "plain"))
        message.attach(MIMEText(full_html, "html"))

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        draft_body = {"message": {"raw": raw}}

        draft = service.users().drafts().create(userId="me", body=draft_body).execute()
        draft_id = draft["id"]
        logger.info(f"Gmail draft created: {subject} (ID: {draft_id})")

        # Apply label if requested
        if label_name:
            _apply_label_to_draft(service, draft, label_name)

        return draft_id
    except Exception as e:
        logger.error(f"Gmail draft creation failed: {e}")
        return None


def _apply_label_to_draft(service, draft: dict, label_name: str):
    """Apply a label to a draft's underlying message. Creates label if needed."""
    try:
        # Find or create the label
        labels_resp = service.users().labels().list(userId="me").execute()
        label_id = None
        for lbl in labels_resp.get("labels", []):
            if lbl["name"] == label_name:
                label_id = lbl["id"]
                break

        if not label_id:
            new_label = service.users().labels().create(
                userId="me",
                body={"name": label_name, "labelListVisibility": "labelShow", "messageListVisibility": "show"}
            ).execute()
            label_id = new_label["id"]
            logger.info(f"Created label: {label_name}")

        # Apply to the draft's message
        msg_id = draft.get("message", {}).get("id")
        if msg_id:
            service.users().messages().modify(
                userId="me", id=msg_id,
                body={"addLabelIds": [label_id]}
            ).execute()
    except Exception as e:
        logger.warning(f"Could not apply label '{label_name}': {e}")


def _commander_review(subject: str, html_body: str, sms_notify: bool = True):
    """Create a Commander Review draft (labeled) and optionally SMS-notify."""
    draft_id = _create_html_draft(subject, html_body, label_name=COMMANDER_REVIEW_LABEL)
    if draft_id and sms_notify:
        _send_sms(f"Draft ready: {subject[:120]}", subject="D2M Commander Review")


# ============================================================================
# DOSSIER SCANNING HELPERS
# ============================================================================

def _read_all_dossiers() -> list[dict]:
    """Read all dossier files and return parsed info."""
    if not DOSSIERS_DIR.exists():
        logger.warning(f"Dossiers directory not found: {DOSSIERS_DIR}")
        return []

    dossiers = []
    for path in sorted(DOSSIERS_DIR.glob("*.md")):
        try:
            text = path.read_text(encoding="utf-8")
            dossiers.append({
                "path": path,
                "filename": path.name,
                "client": path.stem.split("_")[0],
                "text": text,
            })
        except Exception as e:
            logger.error(f"Failed to read dossier {path.name}: {e}")
    return dossiers


def _extract_unchecked_items(text: str) -> list[str]:
    """Extract unchecked [ ] action items from dossier text."""
    items = []
    for match in re.finditer(r"\[\s\]\s+(.*?)(?:\n|$)", text):
        items.append(match.group(1).strip())
    return items


def _extract_checked_items(text: str) -> list[str]:
    """Extract checked [x] action items."""
    items = []
    for match in re.finditer(r"\[x\]\s+(.*?)(?:\n|$)", text, re.IGNORECASE):
        items.append(match.group(1).strip())
    return items


def _extract_emails_from_dossier(text: str) -> list[str]:
    """Extract email addresses mentioned in a dossier."""
    return re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)


def _extract_embarkation_date(text: str) -> Optional[date]:
    """Extract embarkation date from dossier text."""
    months = {
        "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
        "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
        "January": 1, "February": 2, "March": 3, "April": 4, "June": 6,
        "July": 7, "August": 8, "September": 9, "October": 10,
        "November": 11, "December": 12,
    }
    # Look for EMBARKATION keyword near a date
    for match in re.finditer(r"(?:EMBARK\w*|embark\w*).*?(\w+)\s+(\d{1,2})(?:,?\s*(\d{4}))?", text):
        month_str, day_str, year_str = match.group(1), match.group(2), match.group(3)
        month = months.get(month_str)
        if month:
            year = int(year_str) if year_str else 2026
            try:
                return date(year, month, int(day_str))
            except ValueError:
                continue

    # Also try: "Aug 29 | EMBARKATION"
    for match in re.finditer(r"(\w+)\s+(\d{1,2})\s*\|?\s*(?:EMBARK\w*|embark\w*)", text):
        month_str, day_str = match.group(1), match.group(2)
        month = months.get(month_str)
        if month:
            try:
                return date(2026, month, int(day_str))
            except ValueError:
                continue
    return None


def _extract_destinations(text: str) -> list[str]:
    """Extract destination names from dossier header/title lines."""
    destinations = []
    # Pattern: "Scandinavia", "Panama Canal", "Japan", "Lesser Antilles", etc.
    for match in re.finditer(
        r"(?:Scandinavia|Panama Canal|Japan|Lesser Antilles|Mediterranean|Caribbean|Alaska|"
        r"Norway|Iceland|Greenland|Baltic|Greek Isles|Antarctica|Galapagos|Southeast Asia|"
        r"Australia|New Zealand|South Pacific|Adriatic|British Isles|French Polynesia|"
        r"Costa Rica|Fjords|Arctic|Amazon)",
        text, re.IGNORECASE
    ):
        dest = match.group(0)
        if dest not in destinations:
            destinations.append(dest)
    return destinations


def _extract_last_contact(text: str) -> Optional[date]:
    """Extract the most recent email date from EMAIL LOG section."""
    log_match = re.search(r"### EMAIL LOG.*?\n(.*?)(?=\n###|\Z)", text, re.DOTALL)
    if not log_match:
        return None

    log_text = log_match.group(1)
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
                dates.append(date(2026, month, int(day_str)))
            except ValueError:
                continue
    return max(dates) if dates else None


def _extract_flight_info(text: str) -> list[dict]:
    """Extract flight PNRs, flight numbers, and dates from dossier."""
    flights = []
    # PNR patterns: 6-char alphanumeric
    for match in re.finditer(r"PNR[:\s]+([A-Z0-9]{6})", text, re.IGNORECASE):
        flights.append({"type": "PNR", "value": match.group(1)})
    # Flight number patterns: AA1234, UA 456, etc.
    for match in re.finditer(r"\b([A-Z]{2})\s*(\d{1,4})\b", text):
        airline, number = match.group(1), match.group(2)
        if airline in ("AA", "UA", "DL", "WN", "AS", "B6", "NK", "F9", "HA", "SY",
                       "BA", "LH", "AF", "KL", "SK", "AY", "IB", "TK", "EK", "QR", "SQ"):
            flights.append({"type": "flight", "value": f"{airline}{number}"})
    return flights


def _extract_dob(text: str) -> Optional[str]:
    """Extract date of birth from dossier if present."""
    for match in re.finditer(r"(?:DOB|date of birth|birthday)[:\s]+(\w+\s+\d{1,2}(?:,?\s*\d{4})?)", text, re.IGNORECASE):
        return match.group(1)
    return None


def _items_due_soon(items: list[str], text: str) -> list[dict]:
    """Check unchecked items for date references that are due today or tomorrow."""
    today = date.today()
    tomorrow = today + timedelta(days=1)
    months = {
        "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
        "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
    }
    due_items = []
    for item in items:
        for match in re.finditer(r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2})", item):
            month_str, day_str = match.group(1), match.group(2)
            month = months.get(month_str)
            if month:
                try:
                    item_date = date(2026, month, int(day_str))
                    if item_date <= tomorrow:
                        due_items.append({"item": item, "date": item_date.isoformat(), "overdue": item_date < today})
                except ValueError:
                    continue
    return due_items


def _find_form_items(items: list[str]) -> list[str]:
    """Find unchecked items related to forms, documents, insurance, etc."""
    keywords = ["form", "guest info", "profile", "insurance", "travel protection",
                "passport", "visa", "document", "waiver"]
    result = []
    for item in items:
        lower = item.lower()
        if any(kw in lower for kw in keywords):
            result.append(item)
    return result


# ============================================================================
# CALENDAR HELPERS
# ============================================================================

def _get_calendar_service():
    """Get Google Calendar API service. Returns None if not configured."""
    if not CALENDAR_TOKEN_FILE.exists():
        logger.warning("calendar_token.json not found — skipping calendar scan")
        return None

    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build

        creds = Credentials.from_authorized_user_file(str(CALENDAR_TOKEN_FILE), CALENDAR_SCOPES)

        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            CALENDAR_TOKEN_FILE.write_text(creds.to_json())

        if not creds.valid:
            logger.warning("Calendar token invalid — skipping calendar scan")
            return None

        return build("calendar", "v3", credentials=creds)
    except Exception as e:
        logger.warning(f"Calendar service init failed: {e}")
        return None


def _get_upcoming_events(hours: int = 48) -> list[dict]:
    """Fetch calendar events in the next N hours."""
    service = _get_calendar_service()
    if not service:
        return []

    try:
        now = datetime.utcnow()
        time_min = now.isoformat() + "Z"
        time_max = (now + timedelta(hours=hours)).isoformat() + "Z"

        events_result = service.events().list(
            calendarId="primary",
            timeMin=time_min,
            timeMax=time_max,
            maxResults=20,
            singleEvents=True,
            orderBy="startTime"
        ).execute()

        events = []
        for event in events_result.get("items", []):
            start = event.get("start", {})
            start_str = start.get("dateTime", start.get("date", ""))
            events.append({
                "summary": event.get("summary", "(no title)"),
                "start": start_str,
                "description": event.get("description", ""),
                "location": event.get("location", ""),
            })
        return events
    except Exception as e:
        logger.warning(f"Calendar fetch failed: {e}")
        return []


# ============================================================================
# GMAIL SCAN HELPERS
# ============================================================================

def _search_recent_client_emails(client_emails: list[str], hours: int = 2) -> list[dict]:
    """Search Gmail for recent emails from known client addresses."""
    if not client_emails:
        return []

    try:
        service = _get_gmail_service()
        # Build query: from any client email, newer than N hours
        from_parts = " OR ".join(f"from:{email}" for email in client_emails[:10])
        query = f"({from_parts}) newer_than:{hours}h"

        results = service.users().messages().list(
            userId="me", q=query, maxResults=10
        ).execute()

        messages = results.get("messages", [])
        if not messages:
            return []

        summaries = []
        for msg_ref in messages:
            msg = service.users().messages().get(
                userId="me", id=msg_ref["id"],
                format="metadata", metadataHeaders=["From", "Subject", "Date"]
            ).execute()
            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            summaries.append({
                "from": headers.get("From", ""),
                "subject": headers.get("Subject", ""),
                "date": headers.get("Date", ""),
                "snippet": msg.get("snippet", ""),
            })
        return summaries
    except Exception as e:
        logger.warning(f"Gmail client email search failed: {e}")
        return []


# ============================================================================
# HEARTBEAT: COS-EXEC (every 30 min, 0600-2000)
# ============================================================================

def heartbeat_cos_exec() -> dict:
    """COS-EXEC synced heartbeat — Hale + Solberg-Vega.

    Scans calendar, dossier action items, Gmail, payment deadlines, overdue forms.
    """
    logger.info("=" * 60)
    logger.info("HEARTBEAT: COS-EXEC (Hale + Solberg-Vega)")
    logger.info("=" * 60)

    state = _load_state()
    today = date.today()
    now = datetime.now()
    findings = {"urgent_sms": [], "action_drafts": [], "fyi_items": []}

    # ── 1. Calendar scan (next 48 hours) ────────────────────────────────────
    try:
        events = _get_upcoming_events(hours=48)
        for event in events:
            start_str = event["start"]
            summary = event["summary"]

            # Check if event is in next 4 hours
            is_soon = False
            try:
                if "T" in start_str:
                    event_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                    hours_until = (event_dt.replace(tzinfo=None) - now).total_seconds() / 3600
                    is_soon = 0 < hours_until <= 4
            except (ValueError, TypeError):
                pass

            item = f"Calendar: {summary} at {start_str}"
            if is_soon:
                findings["urgent_sms"].append(f"Meeting in <4h: {summary[:80]}")
            else:
                findings["fyi_items"].append(item)

        logger.info(f"Calendar: {len(events)} events in next 48h")
    except Exception as e:
        logger.error(f"Calendar scan failed: {e}")

    # ── 2. Dossier action items due today/tomorrow ──────────────────────────
    try:
        dossiers = _read_all_dossiers()
        all_client_emails = []
        total_open = 0
        total_form_items = 0

        for d in dossiers:
            unchecked = _extract_unchecked_items(d["text"])
            total_open += len(unchecked)

            # Items with dates due soon
            due_items = _items_due_soon(unchecked, d["text"])
            for di in due_items:
                item_key = _item_hash(f"{d['client']}_{di['item']}")
                if not _was_sent(state, "cos", "due_item", item_key):
                    if di.get("overdue"):
                        findings["urgent_sms"].append(f"OVERDUE {d['client']}: {di['item'][:60]}")
                    else:
                        findings["action_drafts"].append(f"{d['client']}: {di['item']}")
                    _mark_sent(state, "cos", "due_item", item_key)

            # Form/document items
            form_items = _find_form_items(unchecked)
            total_form_items += len(form_items)
            for fi in form_items:
                findings["fyi_items"].append(f"{d['client']} form/doc: {fi}")

            # Collect client emails for Gmail scan
            emails = _extract_emails_from_dossier(d["text"])
            # Filter out known non-client emails
            client_emails = [e for e in emails if e != USER_EMAIL and "iam.gserviceaccount.com" not in e]
            all_client_emails.extend(client_emails)

        logger.info(f"Dossiers: {len(dossiers)} scanned, {total_open} open items, {total_form_items} form items")
    except Exception as e:
        logger.error(f"Dossier scan failed: {e}")
        dossiers = []
        all_client_emails = []

    # ── 3. Gmail inbox — recent client emails ───────────────────────────────
    try:
        recent_emails = _search_recent_client_emails(all_client_emails, hours=2)
        for email_info in recent_emails:
            item_key = _item_hash(f"{email_info['from']}_{email_info['subject']}")
            if not _was_sent(state, "cos", "client_email", item_key):
                findings["urgent_sms"].append(
                    f"Client mail: {email_info['from'].split('<')[0].strip()[:30]} - {email_info['subject'][:40]}"
                )
                _mark_sent(state, "cos", "client_email", item_key)
        logger.info(f"Gmail: {len(recent_emails)} recent client emails")
    except Exception as e:
        logger.error(f"Gmail scan failed: {e}")

    # ── 4. Payment deadlines within 14 days ─────────────────────────────────
    try:
        for d in DEADLINES:
            if d["amount"] in ("PAID", "TBD"):
                continue
            deadline = date.fromisoformat(d["date"])
            days_left = (deadline - today).days
            if 0 <= days_left <= 14:
                item_key = _item_hash(f"{d['client']}_{d['date']}")
                if days_left <= 1:
                    if not _was_sent(state, "cos", "payment_urgent", item_key):
                        findings["urgent_sms"].append(
                            f"PAY {'TODAY' if days_left == 0 else 'TOMORROW'}: {d['client']} {d['amount']}"
                        )
                        _mark_sent(state, "cos", "payment_urgent", item_key)
                elif days_left <= 7:
                    findings["action_drafts"].append(
                        f"Payment in {days_left}d: {d['client']} {d['cruise']} {d['amount']}"
                    )
                else:
                    findings["fyi_items"].append(
                        f"Payment in {days_left}d: {d['client']} {d['amount']}"
                    )
        logger.info("Payment deadlines scanned")
    except Exception as e:
        logger.error(f"Payment scan failed: {e}")

    # ── Deliver findings ────────────────────────────────────────────────────

    # Urgent items -> SMS (one combined message)
    if findings["urgent_sms"]:
        sms_text = " | ".join(findings["urgent_sms"])[:160]
        _send_sms(sms_text, "D2M COS-EXEC Alert")

    # Action items -> Gmail Draft + SMS notification
    if findings["action_drafts"]:
        html = "<h1>COS-EXEC Action Items</h1>"
        html += f"<p class='label'>Generated {now.strftime('%Y-%m-%d %H:%M MT')}</p>"
        for item in findings["action_drafts"]:
            html += f"<div class='section action'>{item}</div>"
        subject = f"COS-EXEC Actions — {today.strftime('%b %d')} ({len(findings['action_drafts'])} items)"
        _create_html_draft(subject, html)
        _send_sms(f"Draft ready: {subject[:120]}", "D2M COS-EXEC")

    # FYI items -> Commander Review
    if findings["fyi_items"]:
        html = "<h1>COS-EXEC Briefing</h1>"
        html += f"<p class='label'>Generated {now.strftime('%Y-%m-%d %H:%M MT')}</p>"

        if findings.get("urgent_sms"):
            html += "<h2>Urgent (SMS sent)</h2>"
            for item in findings["urgent_sms"]:
                html += f"<div class='section urgent'>{item}</div>"

        html += "<h2>Prep &amp; FYI</h2>"
        for item in findings["fyi_items"]:
            html += f"<div class='section info'>{item}</div>"

        _commander_review(
            f"COS-EXEC Briefing — {today.strftime('%b %d %H:%M')}",
            html,
            sms_notify=False  # Don't double-SMS if we already sent urgent
        )

    _record_heartbeat(state, "cos_exec")
    _prune_old_keys(state)
    _save_state(state)

    result = {
        "persona": "COS-EXEC",
        "timestamp": now.isoformat(),
        "urgent_count": len(findings["urgent_sms"]),
        "action_count": len(findings["action_drafts"]),
        "fyi_count": len(findings["fyi_items"]),
    }
    logger.info(f"COS-EXEC complete: {result}")
    return result


# ============================================================================
# HEARTBEAT: A3 MOREAU — Booking Ops (daily 0700)
# ============================================================================

def heartbeat_a3_moreau() -> dict:
    """A3 Moreau — Booking Operations morning summary."""
    logger.info("=" * 60)
    logger.info("HEARTBEAT: A3 MOREAU — Booking Ops")
    logger.info("=" * 60)

    state = _load_state()
    today = date.today()
    now = datetime.now()

    sections_html = []
    sms_parts = []

    # ── Payment pipeline ────────────────────────────────────────────────────
    try:
        payment_rows = []
        for d in DEADLINES:
            deadline = date.fromisoformat(d["date"])
            days_left = (deadline - today).days
            if d["amount"] in ("PAID", "TBD"):
                if d["amount"] == "PAID" and 0 <= days_left <= 60:
                    payment_rows.append({
                        "client": d["client"], "cruise": d["cruise"],
                        "amount": d["amount"], "days": days_left,
                        "status": "PAID", "note": d.get("note", ""),
                    })
                continue
            if days_left < -30:
                continue
            status = "OVERDUE" if days_left < 0 else "DUE" if days_left <= 7 else "UPCOMING"
            payment_rows.append({
                "client": d["client"], "cruise": d["cruise"],
                "amount": d["amount"], "days": days_left,
                "status": status, "date": d["date"],
            })

        if payment_rows:
            html = "<h2>Payment Pipeline</h2><table><tr><th>Client</th><th>Cruise</th><th>Amount</th><th>Days</th><th>Status</th></tr>"
            for r in sorted(payment_rows, key=lambda x: x["days"]):
                days_class = "days-urgent" if r["days"] <= 3 else "days-warn" if r["days"] <= 14 else "days-ok"
                html += f"<tr><td>{r['client']}</td><td>{r['cruise']}</td>"
                html += f"<td class='amount'>{r['amount']}</td>"
                html += f"<td class='{days_class}'>{r['days']}d</td>"
                html += f"<td>{r['status']}</td></tr>"
            html += "</table>"
            sections_html.append(html)

            due_soon = [r for r in payment_rows if r["status"] in ("DUE", "OVERDUE")]
            if due_soon:
                sms_parts.append(f"{len(due_soon)} payments due/overdue")
    except Exception as e:
        logger.error(f"A3 payment scan failed: {e}")

    # ── Dossier ops items ───────────────────────────────────────────────────
    try:
        dossiers = _read_all_dossiers()
        ops_keywords = ["shore excursion", "dining", "embark", "form", "transfer",
                        "hotel", "check-in", "document", "booking", "cabin", "suite",
                        "flight", "air", "reservation"]
        ops_items = []
        embark_info = []

        for d in dossiers:
            unchecked = _extract_unchecked_items(d["text"])
            embark_date = _extract_embarkation_date(d["text"])

            if embark_date:
                days_to_embark = (embark_date - today).days
                if days_to_embark >= 0:
                    embark_info.append({
                        "client": d["client"],
                        "embark": embark_date.isoformat(),
                        "days": days_to_embark,
                    })

            for item in unchecked:
                lower = item.lower()
                if any(kw in lower for kw in ops_keywords):
                    ops_items.append({"client": d["client"], "item": item})

        if embark_info:
            html = "<h2>Embarkation Countdown</h2><table><tr><th>Client</th><th>Embarkation</th><th>Days</th></tr>"
            for e in sorted(embark_info, key=lambda x: x["days"]):
                days_class = "days-urgent" if e["days"] <= 14 else "days-warn" if e["days"] <= 60 else "days-ok"
                html += f"<tr><td>{e['client']}</td><td>{e['embark']}</td><td class='{days_class}'>{e['days']}d</td></tr>"
            html += "</table>"
            sections_html.append(html)
            sms_parts.append(f"{len(embark_info)} active sailings")

        if ops_items:
            html = "<h2>Open Ops Items</h2><ul>"
            for oi in ops_items[:15]:
                html += f"<li><strong>{oi['client']}:</strong> {oi['item']}</li>"
            if len(ops_items) > 15:
                html += f"<li>... and {len(ops_items) - 15} more</li>"
            html += "</ul>"
            sections_html.append(html)
            sms_parts.append(f"{len(ops_items)} ops items open")
    except Exception as e:
        logger.error(f"A3 dossier scan failed: {e}")

    # ── Deliver ─────────────────────────────────────────────────────────────
    if sections_html:
        full_html = f"<h1>A3 Moreau — Morning Ops Brief</h1>"
        full_html += f"<p class='label'><span class='persona'>Dani Moreau</span> | {today.strftime('%A, %B %d %Y')} 0700</p>"
        full_html += "".join(sections_html)
        full_html += "<div class='footer'>Dreams2Memories Travel, LLC — Thunderbird OS</div>"

        _create_html_draft(
            f"A3 Ops Brief — {today.strftime('%b %d')}",
            full_html
        )

    if sms_parts:
        sms = f"A3 Morning: {' | '.join(sms_parts)}"
        _send_sms(sms[:160], "D2M A3 Ops")

    _record_heartbeat(state, "a3_moreau")
    _save_state(state)

    result = {"persona": "A3-Moreau", "timestamp": now.isoformat(), "sections": len(sections_html)}
    logger.info(f"A3 Moreau complete: {result}")
    return result


# ============================================================================
# HEARTBEAT: A9 HARLAN — Finance (daily 0900)
# ============================================================================

def heartbeat_a9_harlan() -> dict:
    """A9 Harlan — Finance cost tracking and commission overview."""
    logger.info("=" * 60)
    logger.info("HEARTBEAT: A9 HARLAN — Finance")
    logger.info("=" * 60)

    state = _load_state()
    today = date.today()
    now = datetime.now()

    sections_html = []
    sms_alert = False
    sms_parts = []

    # ── API cost analysis ───────────────────────────────────────────────────
    try:
        if API_COST_LOG.exists():
            costs_24h = {}
            costs_7d = {}
            total_24h = 0.0
            total_7d = 0.0
            cutoff_24h = (now - timedelta(hours=24)).isoformat()
            cutoff_7d = (now - timedelta(days=7)).isoformat()

            for line in API_COST_LOG.read_text(encoding="utf-8").strip().split("\n"):
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                ts = entry.get("timestamp", "")
                provider = entry.get("provider", "unknown")
                cost = float(entry.get("cost_usd", 0))

                if ts >= cutoff_7d:
                    costs_7d[provider] = costs_7d.get(provider, 0) + cost
                    total_7d += cost

                if ts >= cutoff_24h:
                    costs_24h[provider] = costs_24h.get(provider, 0) + cost
                    total_24h += cost

            html = "<h2>API Spend</h2>"
            html += "<table><tr><th>Provider</th><th>24h</th><th>7d</th></tr>"

            all_providers = sorted(set(list(costs_24h.keys()) + list(costs_7d.keys())))
            for provider in all_providers:
                c24 = costs_24h.get(provider, 0)
                c7d = costs_7d.get(provider, 0)
                warn = " class='days-urgent'" if c24 > 5.0 else ""
                html += f"<tr><td>{provider}</td><td{warn}>${c24:.4f}</td><td>${c7d:.4f}</td></tr>"
                if c24 > 5.0:
                    sms_alert = True
                    sms_parts.append(f"{provider} ${c24:.2f}/day")

            html += f"<tr><td><strong>TOTAL</strong></td><td><strong>${total_24h:.4f}</strong></td><td><strong>${total_7d:.4f}</strong></td></tr>"
            html += "</table>"
            sections_html.append(html)
        else:
            sections_html.append("<div class='section info'>No API cost log found.</div>")
    except Exception as e:
        logger.error(f"A9 cost scan failed: {e}")

    # ── Commission pipeline ─────────────────────────────────────────────────
    try:
        total_expected = 0.0
        commission_rows = []
        for d in DEADLINES:
            if d["amount"] in ("PAID", "TBD"):
                continue
            # Parse amount
            amount_str = d["amount"].replace("$", "").replace(",", "")
            try:
                amount = float(amount_str)
            except ValueError:
                continue
            deadline = date.fromisoformat(d["date"])
            days_left = (deadline - today).days
            if days_left >= 0:
                total_expected += amount
                commission_rows.append({
                    "client": d["client"],
                    "amount": d["amount"],
                    "date": d["date"],
                    "days": days_left,
                })

        if commission_rows:
            html = "<h2>Commission Pipeline</h2>"
            html += f"<div class='section action'><strong>Total expected revenue: <span class='amount'>${total_expected:,.2f}</span></strong></div>"
            html += "<table><tr><th>Client</th><th>Amount</th><th>Due</th></tr>"
            for r in sorted(commission_rows, key=lambda x: x["days"]):
                html += f"<tr><td>{r['client']}</td><td class='amount'>{r['amount']}</td><td>{r['date']} ({r['days']}d)</td></tr>"
            html += "</table>"
            sections_html.append(html)
    except Exception as e:
        logger.error(f"A9 commission scan failed: {e}")

    # ── Deliver ─────────────────────────────────────────────────────────────
    if sections_html:
        full_html = f"<h1>A9 Harlan — Finance Brief</h1>"
        full_html += f"<p class='label'><span class='persona'>Vic Harlan</span> | {today.strftime('%A, %B %d %Y')} 0900</p>"
        full_html += "".join(sections_html)
        full_html += "<div class='footer'>Dreams2Memories Travel, LLC — Thunderbird OS</div>"

        _create_html_draft(
            f"A9 Finance — {today.strftime('%b %d')}",
            full_html
        )

    if sms_alert:
        sms = f"A9 SPEND ALERT: {' | '.join(sms_parts)}"
        _send_sms(sms[:160], "D2M A9 Finance")

    _record_heartbeat(state, "a9_harlan")
    _save_state(state)

    result = {"persona": "A9-Harlan", "timestamp": now.isoformat(), "sms_alert": sms_alert}
    logger.info(f"A9 Harlan complete: {result}")
    return result


# ============================================================================
# HEARTBEAT: A2 DEMBE — Intel (daily 0630)
# ============================================================================

def heartbeat_a2_dembe() -> dict:
    """A2 Dembe — Intel prep for active destinations."""
    logger.info("=" * 60)
    logger.info("HEARTBEAT: A2 DEMBE — Intel")
    logger.info("=" * 60)

    state = _load_state()
    today = date.today()
    now = datetime.now()

    sections_html = []

    # ── Destination intel needs ─────────────────────────────────────────────
    try:
        dossiers = _read_all_dossiers()
        intel_needs = []

        for d in dossiers:
            embark_date = _extract_embarkation_date(d["text"])
            if not embark_date:
                continue
            days_to_embark = (embark_date - today).days
            if days_to_embark < 0 or days_to_embark > 90:
                continue

            destinations = _extract_destinations(d["text"])
            if destinations:
                intel_needs.append({
                    "client": d["client"],
                    "embark": embark_date.isoformat(),
                    "days": days_to_embark,
                    "destinations": destinations,
                })

        if intel_needs:
            html = "<h2>Destination Intel Needed (Embark within 90 days)</h2>"
            for item in sorted(intel_needs, key=lambda x: x["days"]):
                urgency = "urgent" if item["days"] <= 30 else "action" if item["days"] <= 60 else "info"
                dest_list = ", ".join(item["destinations"])
                html += f"<div class='section {urgency}'>"
                html += f"<strong>{item['client']}</strong> — {dest_list}<br>"
                html += f"<span class='label'>Embark {item['embark']} ({item['days']}d away)</span><br>"
                html += "Intel needed: weather, travel advisories, port events, local conditions"
                html += "</div>"
            sections_html.append(html)
        else:
            sections_html.append("<div class='section ok'>No sailings within 90 days requiring intel prep.</div>")
    except Exception as e:
        logger.error(f"A2 destination scan failed: {e}")

    # ── Deliver as Commander Review ─────────────────────────────────────────
    if sections_html:
        full_html = f"<h1>A2 Dembe — Intel Brief</h1>"
        full_html += f"<p class='label'><span class='persona'>Marcus Dembe</span> | {today.strftime('%A, %B %d %Y')} 0630</p>"
        full_html += "".join(sections_html)
        full_html += "<div class='footer'>Dreams2Memories Travel, LLC — Thunderbird OS</div>"

        _commander_review(
            f"A2 Intel — {today.strftime('%b %d')}",
            full_html,
            sms_notify=False
        )

    _record_heartbeat(state, "a2_dembe")
    _save_state(state)

    result = {"persona": "A2-Dembe", "timestamp": now.isoformat(), "intel_needs": len(sections_html)}
    logger.info(f"A2 Dembe complete: {result}")
    return result


# ============================================================================
# HEARTBEAT: A6 LUNA (EXEC Creative) — Creative (daily 1000)
# ============================================================================

def heartbeat_a6_luna() -> dict:
    """A6 Luna / EXEC Creative — creative deliverable opportunities."""
    logger.info("=" * 60)
    logger.info("HEARTBEAT: EXEC CREATIVE — Opportunities")
    logger.info("=" * 60)

    state = _load_state()
    today = date.today()
    now = datetime.now()

    sections_html = []

    try:
        dossiers = _read_all_dossiers()

        pre_trip = []
        post_trip = []
        proposals = []
        birthdays = []

        for d in dossiers:
            embark_date = _extract_embarkation_date(d["text"])

            if embark_date:
                days_to_embark = (embark_date - today).days
                destinations = _extract_destinations(d["text"])
                dest_str = ", ".join(destinations) if destinations else "TBD"

                # Pre-trip teaser: within 30 days of embarkation
                if 0 < days_to_embark <= 30:
                    pre_trip.append({
                        "client": d["client"],
                        "days": days_to_embark,
                        "destination": dest_str,
                    })

                # Post-trip thank you: within 7 days of return (assume 10-day cruise)
                approx_return = embark_date + timedelta(days=10)
                days_since_return = (today - approx_return).days
                if 0 <= days_since_return <= 7:
                    post_trip.append({
                        "client": d["client"],
                        "days_since": days_since_return,
                    })

            # Check for proposal/itinerary items
            unchecked = _extract_unchecked_items(d["text"])
            for item in unchecked:
                lower = item.lower()
                if any(kw in lower for kw in ["proposal", "itinerary", "brochure", "presentation"]):
                    proposals.append({"client": d["client"], "item": item})

            # Birthday scan
            dob = _extract_dob(d["text"])
            if dob:
                birthdays.append({"client": d["client"], "dob": dob})

        if pre_trip:
            html = "<h2>Pre-Trip Teaser Opportunities</h2>"
            for item in sorted(pre_trip, key=lambda x: x["days"]):
                html += f"<div class='section action'>"
                html += f"<strong>{item['client']}</strong> — {item['destination']}<br>"
                html += f"<span class='label'>Departs in {item['days']} days — send excitement builder!</span>"
                html += "</div>"
            sections_html.append(html)

        if post_trip:
            html = "<h2>Post-Trip Thank You</h2>"
            for item in post_trip:
                html += f"<div class='section action'>"
                html += f"<strong>{item['client']}</strong> — returned {item['days_since']}d ago<br>"
                html += "<span class='label'>Send thank-you + review request + photo book offer</span>"
                html += "</div>"
            sections_html.append(html)

        if proposals:
            html = "<h2>Creative Deliverables Needed</h2><ul>"
            for p in proposals:
                html += f"<li><strong>{p['client']}:</strong> {p['item']}</li>"
            html += "</ul>"
            sections_html.append(html)

        if birthdays:
            html = "<h2>Client Birthdays on File</h2><ul>"
            for b in birthdays:
                html += f"<li><strong>{b['client']}:</strong> {b['dob']}</li>"
            html += "</ul>"
            sections_html.append(html)

        if not sections_html:
            sections_html.append("<div class='section ok'>No creative deliverables flagged today.</div>")
    except Exception as e:
        logger.error(f"EXEC Creative scan failed: {e}")

    # ── Deliver as Commander Review ─────────────────────────────────────────
    full_html = "<h1>EXEC Creative — Opportunity Scan</h1>"
    full_html += f"<p class='label'><span class='persona'>Naia Solberg-Vega (Creative)</span> | {today.strftime('%A, %B %d %Y')} 1000</p>"
    full_html += "".join(sections_html)
    full_html += "<div class='footer'>Dreams2Memories Travel, LLC — Thunderbird OS</div>"

    _commander_review(
        f"Creative Opportunities — {today.strftime('%b %d')}",
        full_html,
        sms_notify=False
    )

    _record_heartbeat(state, "a6_luna")
    _save_state(state)

    result = {
        "persona": "EXEC-Creative",
        "timestamp": now.isoformat(),
        "pre_trip": len(pre_trip) if 'pre_trip' in dir() else 0,
        "post_trip": len(post_trip) if 'post_trip' in dir() else 0,
    }
    logger.info(f"EXEC Creative complete: {result}")
    return result


# ============================================================================
# HEARTBEAT: A10 IKEDA — Crisis/Logistics (daily 0800)
# ============================================================================

def heartbeat_a10_ikeda() -> dict:
    """A10 Ikeda — Flight monitoring and connection time analysis."""
    logger.info("=" * 60)
    logger.info("HEARTBEAT: A10 IKEDA — Logistics")
    logger.info("=" * 60)

    state = _load_state()
    today = date.today()
    now = datetime.now()

    sections_html = []
    sms_needed = False
    sms_parts = []

    try:
        dossiers = _read_all_dossiers()

        for d in dossiers:
            embark_date = _extract_embarkation_date(d["text"])
            if not embark_date:
                continue
            days_to_embark = (embark_date - today).days
            if days_to_embark < 0 or days_to_embark > 30:
                continue

            flights = _extract_flight_info(d["text"])
            if flights:
                html = f"<h3>{d['client']} — Embark in {days_to_embark}d</h3>"
                html += "<div class='section info'>"
                html += "<strong>Flight References:</strong><ul>"
                for f in flights:
                    html += f"<li>{f['type']}: {f['value']}</li>"
                html += "</ul>"

                # Check for connection warnings in dossier text
                if re.search(r"connect(?:ion|ing)", d["text"], re.IGNORECASE):
                    # Look for time patterns near "connection"
                    conn_matches = re.findall(r"(\d{1,2})[:\s]?(\d{2})?\s*(?:hr|hour|min)", d["text"], re.IGNORECASE)
                    if conn_matches:
                        html += "<strong>Connection times found — review manually</strong>"

                html += "</div>"
                sections_html.append(html)

            # Even without flight info, note the upcoming embarkation
            if not flights and days_to_embark <= 14:
                html = f"<div class='section action'>"
                html += f"<strong>{d['client']}</strong> — Embark in {days_to_embark}d — NO flight info in dossier"
                html += "</div>"
                sections_html.append(html)
                if days_to_embark <= 7:
                    sms_needed = True
                    sms_parts.append(f"{d['client']}: no flights, embark {days_to_embark}d")
    except Exception as e:
        logger.error(f"A10 logistics scan failed: {e}")

    # ── Deliver ─────────────────────────────────────────────────────────────
    full_html = "<h1>A10 Ikeda — Logistics Status</h1>"
    full_html += f"<p class='label'><span class='persona'>Tommy Ikeda</span> | {today.strftime('%A, %B %d %Y')} 0800</p>"

    if sections_html:
        full_html += "".join(sections_html)
    else:
        full_html += "<div class='section ok'>No flights within 30 days requiring monitoring.</div>"

    full_html += "<div class='footer'>Dreams2Memories Travel, LLC — Thunderbird OS</div>"

    _commander_review(
        f"A10 Logistics — {today.strftime('%b %d')}",
        full_html,
        sms_notify=sms_needed
    )

    if sms_needed and sms_parts:
        _send_sms(f"A10 ALERT: {' | '.join(sms_parts)}"[:160], "D2M A10 Logistics")

    _record_heartbeat(state, "a10_ikeda")
    _save_state(state)

    result = {"persona": "A10-Ikeda", "timestamp": now.isoformat(), "issues": len(sms_parts)}
    logger.info(f"A10 Ikeda complete: {result}")
    return result


# ============================================================================
# HEARTBEAT: CH WASHINGTON — Wisdom/Morale (weekly Friday 1500)
# ============================================================================

def heartbeat_ch_washington() -> dict:
    """CH Washington — Weekly reflection and morale check."""
    logger.info("=" * 60)
    logger.info("HEARTBEAT: CH WASHINGTON — Weekly Reflection")
    logger.info("=" * 60)

    state = _load_state()
    today = date.today()
    now = datetime.now()

    sections_html = []

    try:
        dossiers = _read_all_dossiers()
        total_open = 0
        total_checked = 0
        clients_silent = []

        for d in dossiers:
            unchecked = _extract_unchecked_items(d["text"])
            checked = _extract_checked_items(d["text"])
            total_open += len(unchecked)
            total_checked += len(checked)

            last_contact = _extract_last_contact(d["text"])
            if last_contact:
                days_silent = (today - last_contact).days
                if days_silent >= 14:
                    clients_silent.append({
                        "client": d["client"],
                        "days": days_silent,
                        "last": last_contact.isoformat(),
                    })

        # Progress section
        total_items = total_open + total_checked
        completion_pct = (total_checked / total_items * 100) if total_items > 0 else 0
        html = "<h2>Weekly Progress</h2>"
        html += f"<div class='section {'ok' if completion_pct > 50 else 'action'}'>"
        html += f"<strong>Action Items:</strong> {total_checked} completed / {total_open} remaining ({completion_pct:.0f}% done)<br>"
        html += f"<strong>Clients tracked:</strong> {len(dossiers)}"
        html += "</div>"
        sections_html.append(html)

        # Silent clients
        if clients_silent:
            html = "<h2>Clients Needing Attention</h2>"
            for c in sorted(clients_silent, key=lambda x: -x["days"]):
                urgency = "urgent" if c["days"] >= 21 else "action"
                html += f"<div class='section {urgency}'>"
                html += f"<strong>{c['client']}</strong> — {c['days']} days since last contact (last: {c['last']})"
                html += "</div>"
            sections_html.append(html)

        # Morale message
        html = "<h2>Chaplain's Word</h2>"
        html += "<div class='section ok'>"
        if completion_pct >= 70:
            html += "Strong week, Commander. The team is delivering. Keep the momentum — "
            html += "but remember to take a breath. Excellence sustained requires rest sustained."
        elif completion_pct >= 40:
            html += "Steady progress this week. Not every week is a sprint. "
            html += "Focus on the clients who need you most — the rest will follow."
        else:
            html += "Lot of open items piling up. That is not failure — it is information. "
            html += "Pick the three that matter most Monday morning and start there. "
            html += "One foot in front of the other."
        if clients_silent:
            html += f"<br><br>{len(clients_silent)} client(s) have gone quiet. "
            html += "A short check-in says more than a long silence."
        html += "</div>"
        sections_html.append(html)
    except Exception as e:
        logger.error(f"CH Washington scan failed: {e}")

    # ── Deliver as Commander Review ─────────────────────────────────────────
    full_html = "<h1>CH Washington — Weekly Reflection</h1>"
    full_html += f"<p class='label'><span class='persona'>Col James Washington</span> | {today.strftime('%A, %B %d %Y')} 1500</p>"
    full_html += "".join(sections_html)
    full_html += "<div class='footer'>Dreams2Memories Travel, LLC — Thunderbird OS</div>"

    _commander_review(
        f"Weekly Reflection — {today.strftime('%b %d')}",
        full_html,
        sms_notify=True
    )

    _record_heartbeat(state, "ch_washington")
    _save_state(state)

    result = {"persona": "CH-Washington", "timestamp": now.isoformat()}
    logger.info(f"CH Washington complete: {result}")
    return result


# ============================================================================
# MAIN ENTRY POINTS
# ============================================================================

def run_cos_exec_heartbeat() -> dict:
    """COS-EXEC synced heartbeat — every 30 min."""
    return heartbeat_cos_exec()


def run_daily_heartbeats() -> dict:
    """Runs A2 (0630), A3 (0700), A10 (0800), A9 (0900), A6 (1000) in sequence."""
    results = {}

    logger.info("=" * 70)
    logger.info("DAILY HEARTBEATS — Starting sequence")
    logger.info("=" * 70)

    for name, func in [
        ("A2-Dembe (0630)", heartbeat_a2_dembe),
        ("A3-Moreau (0700)", heartbeat_a3_moreau),
        ("A10-Ikeda (0800)", heartbeat_a10_ikeda),
        ("A9-Harlan (0900)", heartbeat_a9_harlan),
        ("EXEC-Creative (1000)", heartbeat_a6_luna),
    ]:
        try:
            results[name] = func()
        except Exception as e:
            logger.error(f"{name} FAILED: {e}", exc_info=True)
            results[name] = {"error": str(e)}

    logger.info("Daily heartbeats complete.")
    return results


def run_weekly_heartbeat() -> dict:
    """CH Washington — Friday only."""
    return heartbeat_ch_washington()


def run_all_heartbeats() -> dict:
    """Force run everything — for testing."""
    results = {}

    logger.info("=" * 70)
    logger.info("ALL HEARTBEATS — Force running everything")
    logger.info("=" * 70)

    results["cos_exec"] = heartbeat_cos_exec()
    results["daily"] = run_daily_heartbeats()
    results["weekly"] = heartbeat_ch_washington()

    logger.info("All heartbeats complete.")
    return results


def show_status():
    """Show last heartbeat run times."""
    state = _load_state()
    last_run = state.get("last_run", {})
    sent_keys = state.get("sent_keys", {})

    print("\nThunderbird Heartbeat Status")
    print("=" * 60)

    if last_run:
        print("\nLast Run Times:")
        print("-" * 40)
        for persona, timestamp in sorted(last_run.items()):
            try:
                dt = datetime.fromisoformat(timestamp)
                age = datetime.now() - dt
                age_str = f"{age.total_seconds() / 3600:.1f}h ago"
            except (ValueError, TypeError):
                age_str = "unknown"
            print(f"  {persona:20s}  {timestamp}  ({age_str})")
    else:
        print("\nNo heartbeats have run yet.")

    today_keys = [k for k in sent_keys if date.today().isoformat() in k]
    print(f"\nItems sent today: {len(today_keys)}")
    print(f"Total state keys: {len(sent_keys)}")
    print()


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Thunderbird Persona Heartbeat System — Dreams2Memories Travel"
    )
    parser.add_argument("--cos-exec", action="store_true", help="Run COS-EXEC heartbeat now")
    parser.add_argument("--daily", action="store_true", help="Run all daily heartbeats")
    parser.add_argument("--weekly", action="store_true", help="Run CH Washington weekly")
    parser.add_argument("--all", action="store_true", help="Run everything (testing)")
    parser.add_argument("--status", action="store_true", help="Show last heartbeat times")

    args = parser.parse_args()

    if args.status:
        show_status()
        return

    if args.cos_exec:
        result = run_cos_exec_heartbeat()
        print(json.dumps(result, indent=2))
        return

    if args.daily:
        result = run_daily_heartbeats()
        print(json.dumps(result, indent=2, default=str))
        return

    if args.weekly:
        result = run_weekly_heartbeat()
        print(json.dumps(result, indent=2))
        return

    if args.all:
        result = run_all_heartbeats()
        print(json.dumps(result, indent=2, default=str))
        return

    # No args — show help
    parser.print_help()
    print("\nExamples:")
    print("  python thunderbird_heartbeat.py --cos-exec     # Run COS-EXEC now")
    print("  python thunderbird_heartbeat.py --daily        # Run all daily heartbeats")
    print("  python thunderbird_heartbeat.py --weekly       # Run CH weekly")
    print("  python thunderbird_heartbeat.py --all          # Run everything")
    print("  python thunderbird_heartbeat.py --status       # Show last heartbeat times")


if __name__ == "__main__":
    main()
