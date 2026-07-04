# ============================================================
# ⚠️  PROTECTED FILE — THUNDERBIRD WING STANDING ORDER
# ============================================================
# DO NOT MODIFY this file without explicit authorization from
# Commander (John Loucks / Yoda) via Claude Code session.
#
# This file controls Commander email command detection.
# Unauthorized changes WILL break the COS tasking pipeline.
#
# Before ANY edit: read SO_EMAIL_SCANNER_PROTECT_20260608.md
# and confirm with Hale (Claude Code) before proceeding.
# ============================================================
"""
thunderbird_commander_inbox.py
===============================
Dreams2Memories Travel, LLC

Scans Commander's personal inbox (johnloucks3@gmail.com) for D2M-relevant emails.
Tasks them to the appropriate Wing persona, drafts replies, notifies COS.

Authentication:
  This module uses a SEPARATE OAuth token (gmail_token_commander.json) for
  johnloucks3@gmail.com — fully independent from d2mconcierge's gmail_token.json.
  If the token file does not exist, the module no-ops with a log warning.

Rules:
  - NEVER send FROM johnloucks3 — only READ
  - Draft replies land in d2mconcierge (send-as concierge@d2mluxury.quest)
  - Personal / non-D2M emails are SKIPPED entirely
  - COS is notified of EVERY tasked email via Telegram
  - gmail_token_commander.json missing → graceful no-op

Authorization (one-time setup):
  python3 thunderbird_commander_inbox.py --authorize
  (Requires gmail_oauth_credentials.json in ~/Thunderbird/)

Run modes:
  python3 thunderbird_commander_inbox.py --sweep      # Full sweep, print summary
  python3 thunderbird_commander_inbox.py --scan       # Scan only (no tasking)
  python3 thunderbird_commander_inbox.py --authorize  # Run OAuth flow for johnloucks3
"""

import base64
import json
import logging
import os
import re
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Audit trail (A2/A3) — defensive import; pipeline must never break ──────
_THUNDERBIRD_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_THUNDERBIRD_ROOT) not in sys.path:
    sys.path.insert(0, str(_THUNDERBIRD_ROOT))
try:
    from core.email.email_audit import record as _audit_record, already_done as _audit_already_done
except ImportError:  # pragma: no cover
    def _audit_record(*a, **k): return True   # type: ignore[misc]
    def _audit_already_done(*a, **k): return False  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

THUNDERBIRD_DIR = Path.home() / "Thunderbird"

# Separate token for johnloucks3@gmail.com (READ ONLY from Commander's personal inbox)
COMMANDER_TOKEN_FILE = THUNDERBIRD_DIR / "gmail_token_commander.json"
JL3_TOKEN_FILE = THUNDERBIRD_DIR / "creds" / "johnloucks3_token.json"
COMMANDER_EMAIL = "johnloucks3@gmail.com"
# OAuth credentials (same project as d2mconcierge — just different account scope)
OAUTH_CREDENTIALS_FILE = THUNDERBIRD_DIR / "gmail_oauth_credentials.json"

# Scopes — modify is needed to apply labels (tracking processed msgs); no send
COMMANDER_GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

# State tracking — avoid reprocessing
STATE_FILE = THUNDERBIRD_DIR / "commander_inbox_state.json"
LOG_FILE = THUNDERBIRD_DIR / "commander_inbox_log.json"

# Draft replies land in d2mconcierge, FROM concierge@d2mluxury.quest
D2M_FROM_ADDRESS = "concierge@d2mluxury.quest"

# Gmail label applied to processed msgs in johnloucks3 inbox
PROCESSED_LABEL = "THUNDERBIRD-Scanned"

# Max emails per sweep
MAX_PER_SWEEP = 15

# Telegram — route inbox sweep notifications to relay (D2M Channels), not D2MC2C
# D2MC2C = urgent Commander action only (SO). Inbox sweep is internal ops.
TELEGRAM_BOT_TOKEN = os.environ.get(
    "TELEGRAM_RELAY_TOKEN", os.environ.get("TELEGRAM_C2_BOT_TOKEN", os.environ.get("TELEGRAM_BOT_TOKEN", ""))
)
TELEGRAM_COMMANDER_ID = int(os.environ.get("TELEGRAM_RELAY_CHAT_ID", os.environ.get("TELEGRAM_COMMANDER_ID", "-5248121475")))

# Classification categories and their routing
CLASSIFICATION_ROUTING: Dict[str, Dict[str, str]] = {
    "commander_directive": {"persona": "COS", "label": "TASKING"},
    "client_inquiry": {"persona": "A3", "label": "CLIENT"},
    "booking_confirmation": {"persona": "A3", "label": "BOOKING"},
    "vendor_comm": {"persona": "COS", "label": "VENDOR"},
    "financial": {"persona": "A9", "label": "FINANCE"},
    "intel": {"persona": "A2", "label": "INTEL"},
    "personal": {"persona": None, "label": "SKIP"},
    "direct_command": {
        "persona": "A1",
        "tier": "COMMAND",
        "action": "cos_execute",
        "notify": True,
    },
}

# ⚠️ DANI AUTO-DRAFT & SUPPLIER SCANNING CONTROL
# Standing Order 2026-03-25: Dani was consuming 10%+ tokens/2h auto-drafting
# NATURAL INTERACTION (2026-05-02): Email tasking via forwarding + trigger phrases
# Scanning for: (1) Forwarded emails from johnloucks3, (2) Emails starting with "COS, " or "Hale, "
DANI_AUTO_DRAFT_ENABLED = False  # Deprecated (tier routing controls behavior now)
SUPPLIER_SCANNING_ENABLED = True  # Re-enabled for natural workflow

# Wing's own addresses — any email FROM these is self-send, never inbound client
# Fast-path: return "personal" immediately before any LLM call
_SELF_ADDRESSES = re.compile(
    r"(d2mconcierge@gmail\.com|concierge@d2mluxury\.quest|johnloucks3@gmail\.com"
    r"|d2m\.concierge@|dreams2memories@d2m-python-pipeline\.iam\.gserviceaccount\.com)",
    re.IGNORECASE,
)

# Noise patterns — fast-path skip before any LLM call
_NOISE_PATTERNS = re.compile(
    r"(no-?reply|noreply|newsletter|unsubscribe|@notification|"
    r"@mailer|donotreply|do-not-reply|@bounce|marketing@|"
    r"promotions?@|alerts?@|support@.*\.com$|receipts@|"
    r"group\d+@|@lawndoctor|@homedepot|@lowes|@bestbuy|@amazon|"
    r"@target|@walmart|@costco|@cvs|@walgreens|@fedex|@ups\.com|"
    r"@usps\.com|@irs\.gov|@dmv\.|deals@|offers@|savings@|coupons?@|"
    r"@cruisecritic|news@|info@|updates@|announcements@|media@|"
    r"@editor\.|@shared\d+\.ccsend\.com|@mailchimpapp\.com|@substack\.com|"
    r"@ccsend\.com|@messages\d+\.com|@notify\.|@email\.|"
    r"@eml\.|@editor\.thecoloradoflyover|@editor\.jointheflyover|"
    r"mail@tln\.messages2\.com|receipts@openrouter\.ai|"
    r"specials-businessclassguru\.com@|tpg@thepointsguy\.com|"
    r"jwoodcock@perx\.com|info@legalinsurrection\.com|"
    r"americanexpress@welcome\.americanexpress\.com|"
    r"warroomeditors@\d+\.mailchimpapp\.com|unitedcruises@email\.cruises\.united\.com|"
    r"trip@notify\.kayak\.com|specials@e\.windstarcruises\.com|"
    r"olivia@ceoflights\.com|news@news\.picassotravel\.com|"
    r"laureleegraham@\d+\.mailchimpapp\.com|hello@marketing\.cruisebound\.com)",
    re.IGNORECASE,
)

# ============================================================================
# OPTION C: STRUCTURED ROUTING — SUPPLIER vs CLIENT CLASSIFICATION
# ============================================================================

# Tier 1: SUPPLIER DOMAINS — Known travel vendors, systems, booking confirmations
# These get LIGHTWEIGHT auto-draft (template responses, low token cost)
SUPPLIER_DOMAINS = {
    # Cruise lines
    "silversea.com", "silverseamail.com",
    "rssc.com", "rsccdirect.com",
    "regent7seas.com", "regent.com", "seveneasrsc.com",
    "cunardline.com", "cunard.com",
    "oceaniacruises.com", "oceania.com",
    "seabourn.com", "seabournmail.com",
    "vikingcruises.com", "viking.com",
    "amawaterways.com", "ama.com",
    "ponant.com", "boquierports.com",
    # GDS / booking systems
    "tess.com", "tessintl.com",
    "amadeus.com", "amadeus-hospitality.com",
    "sabre.com", "sabresoap.com",
    "travelport.com", "galileo.com",
    "gds-systems.com",
    # Airlines
    "southwest.com", "swa.com",
    "united.com", "unitedcruises.com",
    "aa.com", "americanairlines.com",
    "delta.com", "deltaair.com",
    "alaskaair.com", "alaskaairlines.com",
    "frontier.com", "spirit.com",
    "lufthansa.com", "klm.com", "airfrance.com",
    # Hotels / Resorts
    "hyatt.com", "marriott.com", "hilton.com",
    "fourseasons.com", "ritzcarleton.com",
    "fairmont.com", "aman.com",
    "sixsenses.com", "belmond.com",
    # Excursions / Tours / Transfers
    "getyourguide.com", "viator.com",
    "klook.com", "civitatis.com",
    "kiwitaxi.com", "blacklane.com",
    "uber.com", "lyft.com",
    "shuttledirect.com", "rentalcars.com",
    # Payments / Invoicing
    "stripe.com", "paypal.com",
    "authorize.net", "square.com",
    # Insurance
    "insuremytrip.com", "travelinsurance.com",
    # Google / Automated alerts
    "google.com", "googledrive.com",
    "googlemail.com", "noreply.google.com",
    # Travel alerts
    "state.gov", "travel.state.gov",
    "cdc.gov", "who.int",
}

# Tier 1: KNOWN SUPPLIER SENDERS (service accounts, booking bots)
SUPPLIER_SENDERS = {
    "no-reply@silversea.com", "reservations@silversea.com",
    "confirmation@regent.com", "bookings@regent.com",
    "bookings@cunard.com", "confirmation@cunard.com",
    "reservations@viking.com", "confirmation@viking.com",
    "tess@tessintl.com", "system@tess.com",
    "no-reply@amadeus.com", "bookings@amadeus.com",
    "no-reply@stripe.com", "alerts@stripe.com",
    "noreply@google.com", "drive-shares-noreply@google.com",
    "no-reply@paypal.com", "service@paypal.com",
    "alerts@state.gov", "travel@state.gov",
}

# Tier 2: CLIENT INDICATORS — look for these patterns/domains in known client list
# (populated from dossiers at runtime)
CLIENT_ADDRESSES = set()  # Will be populated from dossier scan

# ============================================================================
# Known D2M-relevant senders / domains — always process regardless of subject
_D2M_DOMAINS = re.compile(
    r"(silversea|rssc|regent|cunard|oceania|seabourn|viking|ama"
    r"|ponant|amadeus|sabre|tess|gds|travelport|airline|air\s"
    r"|southwest|united|american|delta|alaska|frontier|spirit"
    r"|hotel|resort|hyatt|marriott|hilton|ike|fairmont|four\s*seasons"
    r"|ritz|aman|six\s*senses|d2mluxury|dreams2memories)",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# OAuth / Gmail service — johnloucks3
# ---------------------------------------------------------------------------

_commander_service = None


def _get_commander_gmail_service():
    """Return Gmail API service authenticated as johnloucks3@gmail.com.

    Uses gmail_token_commander.json — completely separate from d2mconcierge token.
    Returns None (with a warning) if the token file does not exist.
    """
    global _commander_service
    if _commander_service is not None:
        return _commander_service

    if not COMMANDER_TOKEN_FILE.exists():
        logger.warning(
            "Commander inbox scanner: gmail_token_commander.json not found. "
            "Run: python3 thunderbird_commander_inbox.py --authorize\n"
            f"Expected path: {COMMANDER_TOKEN_FILE}"
        )
        return None

    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        creds = Credentials.from_authorized_user_file(
            str(COMMANDER_TOKEN_FILE), COMMANDER_GMAIL_SCOPES
        )
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            COMMANDER_TOKEN_FILE.write_text(creds.to_json())
            logger.info("Commander Gmail token refreshed.")

        if not creds.valid:
            logger.warning(
                "Commander Gmail token invalid. "
                "Run: python3 thunderbird_commander_inbox.py --authorize"
            )
            return None

        _commander_service = build("gmail", "v1", credentials=creds)
        logger.info("Commander Gmail service authenticated (johnloucks3@gmail.com).")
        return _commander_service

    except Exception as e:
        logger.error(f"Commander Gmail service init failed: {e}")
        return None


def authorize_commander_gmail() -> bool:
    """Run one-time OAuth flow for johnloucks3@gmail.com.

    Saves token to gmail_token_commander.json (separate from d2mconcierge's token).
    """
    if not OAUTH_CREDENTIALS_FILE.exists():
        print(f"ERROR: OAuth credentials not found at {OAUTH_CREDENTIALS_FILE}")
        print("Download from Google Cloud Console → APIs & Services → Credentials.")
        return False

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow

        flow = InstalledAppFlow.from_client_secrets_file(
            str(OAUTH_CREDENTIALS_FILE), COMMANDER_GMAIL_SCOPES
        )
        creds = flow.run_local_server(port=0)
        COMMANDER_TOKEN_FILE.write_text(creds.to_json())
        print(f"Authorization successful. Token saved to {COMMANDER_TOKEN_FILE}")
        print("Account: johnloucks3@gmail.com (personal Commander inbox — READ ONLY)")
        return True
    except Exception as e:
        print(f"Authorization failed: {e}")
        return False


# ---------------------------------------------------------------------------
# Gmail helpers
# ---------------------------------------------------------------------------


def _decode_body(payload) -> str:
    """Extract body text from a Gmail message payload. Prefers text/plain."""

    def _find_part(p, mime_type):
        if p.get("mimeType") == mime_type and p.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(p["body"]["data"]).decode(
                "utf-8", errors="replace"
            )
        for part in p.get("parts", []):
            result = _find_part(part, mime_type)
            if result:
                return result
        return None

    plain = _find_part(payload, "text/plain")
    if plain:
        return plain

    html = _find_part(payload, "text/html")
    if html:
        # Strip HTML tags for preview
        text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
        text = re.sub(r"</(?:p|div|tr|li|h[1-6])>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", "", text)
        import html as html_mod

        text = html_mod.unescape(text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()
    return ""


def _extract_headers(headers: list) -> Dict[str, str]:
    keys = {"From", "To", "Subject", "Date", "Cc", "Message-ID", "Reply-To"}
    return {h["name"]: h["value"] for h in headers if h["name"] in keys}


def _extract_email_address(from_field: str) -> str:
    match = re.search(r"<([^>]+)>", from_field)
    return match.group(1).lower() if match else from_field.strip().lower()


def _extract_sender_name(from_field: str) -> str:
    match = re.match(r'^"?([^"<]+)"?\s*<', from_field)
    return match.group(1).strip() if match else from_field.split("@")[0]


def _get_or_create_label(service, label_name: str) -> Optional[str]:
    """Return label ID for label_name in johnloucks3, creating it if needed."""
    try:
        results = service.users().labels().list(userId="me").execute()
        for label in results.get("labels", []):
            if label["name"] == label_name:
                return label["id"]
        body = {
            "name": label_name,
            "labelListVisibility": "labelShow",
            "messageListVisibility": "show",
        }
        created = service.users().labels().create(userId="me", body=body).execute()
        logger.info(f"Created Gmail label in Commander inbox: {label_name}")
        return created["id"]
    except Exception as e:
        logger.warning(f"Label create/find failed ({label_name}): {e}")
        return None


def _apply_label(service, msg_id: str, label_id: str):
    """Apply a label to a message in johnloucks3."""
    try:
        service.users().messages().modify(
            userId="me",
            id=msg_id,
            body={"addLabelIds": [label_id]},
        ).execute()
    except Exception as e:
        logger.warning(f"Label apply failed ({msg_id}): {e}")


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------


def _load_state() -> Dict[str, Any]:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "processed_ids": [],
        "last_run": None,
        "stats": {"total": 0, "tasked": 0, "skipped": 0, "drafted": 0},
    }


def _save_state(state: Dict[str, Any]):
    if len(state["processed_ids"]) > 1000:
        state["processed_ids"] = state["processed_ids"][-1000:]
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _log_action(entry: Dict):
    log_data: List[Dict] = []
    if LOG_FILE.exists():
        try:
            log_data = json.loads(LOG_FILE.read_text())
        except Exception:
            pass
    log_data.append(entry)
    if len(log_data) > 500:
        log_data = log_data[-500:]
    LOG_FILE.write_text(json.dumps(log_data, indent=2))


# ---------------------------------------------------------------------------
# Email classification — Claude Sonnet (fast, cheap)
# ---------------------------------------------------------------------------


def _populate_client_addresses():
    """Scan dossier directory and populate CLIENT_ADDRESSES set."""
    global CLIENT_ADDRESSES
    try:
        for dossier_dir in [THUNDERBIRD_DIR / "dossiers", THUNDERBIRD_DIR / "Dossiers"]:
            if dossier_dir.exists():
                for dossier_file in dossier_dir.glob("*.json"):
                    try:
                        data = json.loads(dossier_file.read_text())
                        # Extract client email addresses from dossier
                        if "client_emails" in data:
                            for email in data["client_emails"]:
                                CLIENT_ADDRESSES.add(email.lower())
                        if "email" in data:
                            CLIENT_ADDRESSES.add(data["email"].lower())
                        if "emails" in data:
                            for email in data["emails"]:
                                CLIENT_ADDRESSES.add(email.lower())
                    except Exception:
                        pass
    except Exception as e:
        logger.warning(f"Failed to populate client addresses: {e}")


def _determine_email_tier(sender: str) -> str:
    """Determine which tier an email belongs to.

    Returns:
      "SUPPLIER" — known supplier domain/sender (Tier 1)
      "CLIENT"   — known client address (Tier 2)
      "INTAKE"   — everything else (Tier 3)
    """
    sender_lower = sender.lower()
    sender_domain = sender_lower.split("@")[-1] if "@" in sender_lower else ""

    # Tier 1: Supplier
    if sender_lower in SUPPLIER_SENDERS:
        return "SUPPLIER"

    for supplier_domain in SUPPLIER_DOMAINS:
        if sender_domain == supplier_domain or sender_lower.endswith("@" + supplier_domain):
            return "SUPPLIER"

    # Tier 2: Client
    if sender_lower in CLIENT_ADDRESSES:
        return "CLIENT"

    # Tier 3: Intake
    return "INTAKE"


def classify_email(subject: str, sender: str, body_preview: str) -> str:
    """Classify an email into a D2M routing category using Claude.

    Returns one of:
      commander_directive | client_inquiry | booking_confirmation | vendor_comm |
      financial | intel | personal

    Falls back to heuristics if Claude unavailable.
    """
    sender_lower = sender.lower()

    # Fast-path: self-send — our own outbound replies showing in inbox thread
    # EXCEPTION: subject starts with "COS, " or "Hale, " = Commander directive
    subject_lower_for_check = subject.lower()
    if subject_lower_for_check.startswith("cos, ") or subject_lower_for_check.startswith("hale, "):
        return "commander_directive"
    # ── Commander direct-command detection (HIGHEST PRIORITY — check before all other routing) ──
    # COS/COO/HALE/VIC followed by ANY non-letter separator (: -- - — space etc.)
    _CMD_RE = re.compile(r'^(cos|coo|hale|vic)\W', re.IGNORECASE)
    _subj_stripped = re.sub(r'^(re:|fwd:|fw:)\s*', '', subject.strip(), flags=re.IGNORECASE)
    if _CMD_RE.match(_subj_stripped):
        return "direct_command"

    # Body scan — prefix must be at the very start of the body
    if _CMD_RE.match(body_preview.strip()):
        return "direct_command"

    if _SELF_ADDRESSES.search(sender_lower):
        return "personal"

    # Fast-path: obvious noise/commercial → personal
    if _NOISE_PATTERNS.search(sender_lower):
        return "personal"

    # Fast-path: known D2M domains → at least vendor_comm
    is_d2m_domain = bool(_D2M_DOMAINS.search(sender_lower + " " + subject))

    # Fast-path keyword heuristics (no LLM needed for clear cases)
    subject_lower = subject.lower()
    body_lower = body_preview.lower()

    if any(
        kw in subject_lower
        for kw in (
            "booking confirmation",
            "reservation confirmed",
            "itinerary",
            "e-ticket",
            "e-document",
            "final documents",
            "cruise confirmation",
        )
    ):
        return "booking_confirmation"

    if any(
        kw in subject_lower
        for kw in (
            "commission",
            "invoice",
            "payment",
            "remittance",
            "statement",
            "override",
            "net rate",
            "override check",
        )
    ):
        return "financial"

    if any(
        kw in subject_lower
        for kw in (
            "travel advisory",
            "port closure",
            "hurricane",
            "strike",
            "visa",
            "entry requirement",
            "isw",
            "intel",
        )
    ):
        return "intel"

    # For ambiguous emails, call Claude
    try:
        from thunderbird_personas import _call_claude, CLAUDE_CMD

        system = (
            "You are an email classification engine for Dreams2Memories Travel, LLC, "
            "a luxury travel agency. Classify the email into EXACTLY ONE of these categories:\n"
            "  commander_directive — A directive or tasking from the Commander (John Loucks) "
            "to COS Hale or staff. Subject lines starting with 'COS, ' or 'Hale, '.\n"
            "  client_inquiry     — A client or prospect asking about travel, trips, bookings, or quotes\n"
            "  booking_confirmation — A confirmation, itinerary, e-ticket, or travel document from a TRAVEL vendor\n"
            "  vendor_comm        — Correspondence from TRAVEL INDUSTRY contacts ONLY: cruise lines, hotels, "
            "airlines, GDS systems, tour operators, excursion providers, transfer companies. "
            "NON-TRAVEL vendors (lawn care, retail, utilities, food delivery, home services, etc.) = personal\n"
            "  financial          — Commissions, invoices, payments, overrides, financial statements from travel vendors\n"
            "  intel              — Travel news, port advisories, visa alerts, industry updates, geopolitical events\n"
            "  personal           — Anything unrelated to the TRAVEL business: spam, retail, home services, "
            "newsletters from non-travel companies, automated commercial emails, lawn care, etc.\n\n"
            "IMPORTANT: If the sender is a non-travel business or the email is commercial/promotional "
            "with no travel relevance, ALWAYS classify as 'personal'.\n\n"
            "Reply with ONLY the category name — no explanation, no punctuation."
        )

        prompt = (
            f"From: {sender}\nSubject: {subject}\n\nBody preview:\n{body_preview[:800]}"
        )

        raw = _call_claude(system, prompt, max_tokens=20, model="haiku")
        category = raw.strip().lower().split()[0] if raw.strip() else "personal"

        # Validate against known categories
        if category in CLASSIFICATION_ROUTING:
            logger.debug(f"Claude classified '{subject[:50]}' as: {category}")
            return category

        # If Claude returned something unrecognized, fall through to heuristic
        logger.warning(
            f"Claude returned unknown category '{category}' — using heuristic"
        )

    except Exception as e:
        logger.warning(f"Claude classification failed ({e}) — using heuristic")

    # ── Final heuristic fallback ──
    if is_d2m_domain:
        return "vendor_comm"

    # Check body for client signals
    # Check if this is ACTUALLY a client inquiry vs promotional email
    # Look for client inquiry signals (direct questions, requests, personal details)
    client_inquiry_signals = any(
        kw in body_lower
        for kw in (
            "i want to book",
            "we are interested in",
            "looking for a quote",
            "can you help with",
            "do you have availability",
            "please send me",
            "i need a hotel",
            "we need flights",
            "our family wants to",
            "hello dani",
            "dear dani",
            "hi john",
            "dear john",
            "questions about",
            "can you recommend",
            "looking for recommendations",
            "what options",
            "would like to discuss",
            "can we schedule a call",
            "schedule a time",
        )
    )

    # Look for promotional/noise signals (newsletter, marketing, announcements)
    promotional_signals = any(
        kw in body_lower
        for kw in (
            "newsletter",
            "unsubscribe",
            "sneak peek",
            "suite secrets",
            "generational cruise",
            "sign up",
            "click here",
            "read more",
            "limited time",
            "special offer",
            "promotion",
            "sale",
            "discount",
            "announcement",
            "check out",
            "see what's new",
            "just announced",
            "introducing",
            "new product",
            "latest news",
            "exclusive access",
            "you're invited",
            "join us",
            "register now",
            "webinar",
            "event",
            "forward to a friend",
            "share with",
            "sponsored",
            "partner",
            "advertisement",
            "marketing email",
            "commercial message",
        )
    )

    # Only classify as client_inquiry if there are strong client signals AND no promotional signals
    if client_inquiry_signals and not promotional_signals:
        return "client_inquiry"

    # If it has travel keywords but also promotional signals, it's likely vendor_comm at best
    travel_keywords = any(
        kw in body_lower
        for kw in (
            "book",
            "trip",
            "cruise",
            "travel",
            "quote",
            "availability",
            "flight",
            "hotel",
            "excursion",
            "passport",
            "visa",
        )
    )
    if travel_keywords and not promotional_signals and is_d2m_domain:
        return "vendor_comm"

    return "personal"


def _classify_email(sender: str, subject: str, body_preview: str) -> str:
    """Wrapper with (sender, subject, body) argument order for verification scripts."""
    return classify_email(subject, sender, body_preview)


# ---------------------------------------------------------------------------
# Persona tasking — route to appropriate Wing member
# ---------------------------------------------------------------------------


def _task_to_persona(
    classification: str, sender_name: str, sender_email: str, subject: str, body: str,
    tier: str = "INTAKE"
) -> Optional[str]:
    """Call the appropriate persona to analyze the email and produce a draft reply.

    Returns the draft reply text, or None if no draft needed (e.g. intel routing).

    Args:
        classification: Email classification (client_inquiry, booking_confirmation, etc.)
        sender_name: Human-readable sender name
        sender_email: Sender email address
        subject: Email subject
        body: Email body
        tier: Email tier (SUPPLIER, CLIENT, INTAKE) — Option C routing

    OPTION C — Selective Dani Auto-Draft:
      - Tier 1 (SUPPLIER): Enable lightweight auto-draft (template responses)
      - Tier 2 (CLIENT): Dani LOCKED — no auto-draft (WF-17 gate applies)
      - Tier 3 (INTAKE): Skip (no response needed)
    """
    # ⚠️ OPTION C — Selective Dani Auto-Draft
    # SUPPLIER tier (Tier 1): Enable lightweight auto-draft for procedural responses
    # CLIENT tier (Tier 2): Keep Dani LOCKED per Standing Order 2026-03-25
    # INTAKE tier (Tier 3): No response (monitoring only)

    if tier in ("CLIENT", "INTAKE") and not DANI_AUTO_DRAFT_ENABLED:
        routing = CLASSIFICATION_ROUTING.get(classification, {})
        if routing.get("persona") == "A3":
            logger.info(
                f"[DANI LOCKED] Skipped auto-draft for {sender_email} — {subject[:60]} "
                f"(tier: {tier}, classification: {classification}). CLIENT/INTAKE tier requires manual review."
            )
            return None

    # Tier 1 (SUPPLIER): Allow lightweight auto-draft with template responses
    if tier == "SUPPLIER" and classification == "booking_confirmation":
        # For supplier confirmations, generate lightweight procedural response
        try:
            from thunderbird_personas import _call_claude, CLAUDE_CMD

            system = (
                "You are a luxury travel concierge generating lightweight procedural responses "
                "to TRAVEL SUPPLIER booking confirmations (airlines, hotels, cruises, etc.). "
                "Keep response brief (2-3 sentences), professional, thank-you style. "
                "Do NOT apologize. Do NOT ask questions. Just confirm receipt. "
                "Sign as: Dani Moreau, Luxury Travel Concierge, Dreams2Memories Travel"
            )
            prompt = f"Generate a brief reply to this booking confirmation:\n\n{body[:1500]}"

            raw = _call_claude(system, prompt, max_tokens=150, model="haiku")
            if raw.strip():
                logger.info(f"[TIER 1 SUPPLIER] Lightweight auto-draft generated for {sender_email}")
                return raw.strip()
        except Exception as e:
            logger.warning(f"Lightweight supplier draft generation failed: {e}")
            return None

    routing = CLASSIFICATION_ROUTING.get(classification, {})
    persona_id = routing.get("persona")

    if not persona_id:
        return None

    try:
        from thunderbird_personas import call_persona

        if persona_id == "A3":
            # Step 1: Get analysis from A3
            analysis_query = (
                f"Analyze this client email and provide your professional assessment:\n\n"
                f"From: {sender_name} ({sender_email})\n"
                f"Subject: {subject}\n\n"
                f"{body[:3000]}\n\n"
                "ANALYSIS INSTRUCTIONS:\n"
                "- Assess the client's needs, urgency, and emotional state\n"
                "- Identify any immediate action required\n"
                "- Note any booking references or trip details mentioned\n"
                "- Evaluate if this requires COS or Commander attention\n"
                "- Keep analysis concise (3-5 bullet points)\n"
                "- Your analysis will be reviewed by COS before you draft a reply"
            )
            analysis_result = call_persona("A3", analysis_query, max_tokens=400)
            analysis_text = analysis_result.get("answer", "").strip()

            # Step 2: Draft the reply using Dani engine with context
            try:
                from thunderbird_dani_engine import build_dani_context

                context_query = (
                    f"EMAIL from {sender_name} ({sender_email}):\n"
                    f"Subject: {subject}\n\n"
                    f"{body[:3000]}"
                )
                context = build_dani_context(context_query, is_commander=False)
                context += (
                    f"\n\nANALYSIS FROM A3:\n{analysis_text}\n\n"
                    "EMAIL RESPONSE RULES:\n"
                    "- You are responding to a client email. Use proper email formatting.\n"
                    "- Greeting, warm body, professional close.\n"
                    "- Sign as: Dani Moreau, Luxury Travel Concierge, Dreams2Memories Travel\n"
                    "- No emojis. If referencing John, say 'John Loucks, our owner' or 'John'.\n"
                    "- This draft goes through COS review before Commander sees it.\n"
                )
                draft_result = call_persona("A3", context, max_tokens=800)
                result = {
                    "answer": draft_result.get("answer", ""),
                    "analysis": analysis_text,
                }
            except Exception:
                # Fallback: direct Dani call without full engine context
                query = (
                    f"Draft a reply to this email:\n\n"
                    f"From: {sender_name} ({sender_email})\n"
                    f"Subject: {subject}\n\n"
                    f"{body[:2000]}\n\n"
                    "Sign as: Dani Moreau, Luxury Travel Concierge, Dreams2Memories Travel"
                )
                draft_result = call_persona("A3", query, max_tokens=800)
                result = {
                    "answer": draft_result.get("answer", ""),
                    "analysis": analysis_text,
                }

        elif persona_id == "COS":
            query = (
                f"Analyze this email from Commander's personal inbox and provide both analysis and draft reply:\n\n"
                f"From: {sender_name} ({sender_email})\n"
                f"Subject: {subject}\n\n"
                f"{body[:2500]}\n\n"
                "FORMAT YOUR RESPONSE AS:\n"
                "ANALYSIS: [Your professional assessment of D2M relevance, urgency, and recommended action]\n"
                "DRAFT: [The actual draft reply if warranted, signed as John Loucks, Dreams2Memories Travel]\n"
                "If no reply is needed, say so in the ANALYSIS section and omit DRAFT."
            )
            cos_result = call_persona(
                "COS", query, max_tokens=600, model_override="haiku"
            )
            # Extract analysis and draft from COS response
            cos_answer = cos_result.get("answer", "")
            if "ANALYSIS:" in cos_answer and "DRAFT:" in cos_answer:
                analysis_part = (
                    cos_answer.split("ANALYSIS:")[1].split("DRAFT:")[0].strip()
                )
                draft_part = cos_answer.split("DRAFT:")[1].strip()
                result = {"answer": draft_part, "analysis": analysis_part}
            else:
                # Fallback: treat entire response as draft
                result = {"answer": cos_answer, "analysis": "No analysis provided"}

        elif persona_id == "A9":
            query = (
                f"Financial email in Commander's inbox — analyze and recommend action.\n\n"
                f"From: {sender_name} ({sender_email})\n"
                f"Subject: {subject}\n\n"
                f"{body[:2500]}"
            )
            result = call_persona("A9", query, max_tokens=400, model_override="haiku")

        elif persona_id == "A2":
            query = (
                f"Intel email in Commander's inbox — assess D2M relevance and extract key points.\n\n"
                f"From: {sender_name} ({sender_email})\n"
                f"Subject: {subject}\n\n"
                f"{body[:2500]}"
            )
            result = call_persona("A2", query, max_tokens=400, model_override="haiku")

        else:
            return None

        # Handle different return formats
        if isinstance(result, dict) and "analysis" in result:
            # A3 returns both analysis and draft
            analysis = result.get("analysis", "")
            draft = result.get("answer", "")
            # Strip model attribution tags
            analysis = re.sub(r"\n\n---\n_.*?_$", "", analysis).strip()
            draft = re.sub(r"\n\n---\n_.*?_$", "", draft).strip()
            return (
                f"ANALYSIS:\n{analysis}\n\nDRAFT:\n{draft}"
                if analysis and draft
                else draft or analysis
            )
        else:
            # Other personas return just the answer
            answer = (
                result.get("answer", "") if isinstance(result, dict) else str(result)
            )
            # Strip model attribution tag
            answer = re.sub(r"\n\n---\n_.*?_$", "", answer).strip()
            return answer if answer else None

    except Exception as e:
        logger.error(f"Persona tasking failed ({persona_id}, {subject[:50]}): {e}")
        return None


# ---------------------------------------------------------------------------
# Draft creation — in d2mconcierge, FROM concierge@d2mluxury.quest
# ---------------------------------------------------------------------------


def _create_reply_draft(
    to_email: str, subject: str, body: str, thread_id: Optional[str] = None
) -> Optional[str]:
    """Create a draft reply in d2mconcierge (FROM concierge@d2mluxury.quest).

    NEVER sends from johnloucks3 — this draft lands in d2mconcierge for review.
    Returns the draft ID, or None on failure.
    """
    try:
        from thunderbird_gmail import _get_gmail_service

        service = _get_gmail_service()

        msg = MIMEMultipart("alternative")
        msg["To"] = to_email
        msg["From"] = D2M_FROM_ADDRESS
        msg["Subject"] = (
            f"Re: {subject}" if not subject.lower().startswith("re:") else subject
        )

        msg.attach(MIMEText(body, "plain"))

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
        draft_body: Dict[str, Any] = {"message": {"raw": raw}}
        if thread_id:
            draft_body["message"]["threadId"] = thread_id

        draft = service.users().drafts().create(userId="me", body=draft_body).execute()

        draft_id = draft.get("id", "unknown")
        logger.info(
            f"Draft created in d2mconcierge (FROM concierge@): draft={draft_id}"
        )
        return draft_id

    except Exception as e:
        logger.error(f"Draft creation failed ({subject[:50]}): {e}")
        return None


# ---------------------------------------------------------------------------
# COS Telegram notification
# ---------------------------------------------------------------------------


def _notify_cos(
    classification: str,
    sender: str,
    subject: str,
    persona_id: Optional[str],
    draft_id: Optional[str],
    persona_note: str,
):
    """Notify Commander/COS via Telegram about every tasked email."""
    try:
        import requests as _req

        category_icon = {
            "client_inquiry": "👤",
            "booking_confirmation": "📋",
            "vendor_comm": "🏢",
            "financial": "💰",
            "intel": "🔎",
            "personal": "⬛",
        }.get(classification, "📧")

        persona_line = (
            f"Tasked to: *{persona_id}*\n"
            if persona_id
            else "Persona: SKIP (personal)\n"
        )
        draft_line = f"Draft ID: `{draft_id}`\n" if draft_id else "Draft: none\n"
        note_preview = persona_note[:300] if persona_note else "(no analysis)"

        notice = (
            f"{category_icon} *COMMANDER INBOX — {classification.upper()}*\n\n"
            f"From: {sender}\n"
            f"Subject: {subject}\n\n"
            f"{persona_line}"
            f"{draft_line}\n"
            f"Analysis preview:\n_{note_preview}_"
        )

        _req.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": TELEGRAM_COMMANDER_ID,
                "text": notice,
                "parse_mode": "Markdown",
            },
            timeout=10,
        )
        logger.info(f"COS notified via Telegram: {classification} — {subject[:50]}")

    except Exception as e:
        logger.warning(f"Telegram notification failed: {e}")


# ---------------------------------------------------------------------------
# Task a single email
# ---------------------------------------------------------------------------


def task_email(
    msg_id: str,
    classification: str,
    subject: str,
    sender: str,
    sender_name: str,
    body: str,
    thread_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Process a classified email end-to-end using Option C routing.

    OPTION C — Structured Routing:
      Tier 1 (SUPPLIER): Lightweight auto-draft → d2mconcierge draft → COS review
      Tier 2 (CLIENT):   WF-17 gate → flag to COS for manual routing → no auto-draft
      Tier 3 (INTAKE):   Monitoring only → no action, no notify

    Steps:
      1. Determine tier (supplier/client/intake)
      2. For Tier 1: Task to persona for lightweight draft
      3. For Tier 2: Log for COS review, no draft
      4. For Tier 3: Skip entirely
      5. Create draft and notify COS
      6. Return action summary

    Returns dict with: msg_id, classification, tier, persona, draft_id, status
    """
    # Populate client addresses on first run
    global CLIENT_ADDRESSES
    if not CLIENT_ADDRESSES:
        _populate_client_addresses()

    # STEP 1: Determine tier
    tier = _determine_email_tier(sender)
    logger.info(f"[{tier:<8}] {sender} — {subject[:50]} (classification: {classification})")

    routing = CLASSIFICATION_ROUTING.get(classification, {})
    persona_id = routing.get("persona")

    result: Dict[str, Any] = {
        "msg_id": msg_id,
        "classification": classification,
        "tier": tier,
        "subject": subject,
        "sender": sender,
        "persona": persona_id,
        "draft_id": None,
        "persona_note": "",
        "status": "skipped",
    }

    # STEP 1.5: Commander directive — route to COS immediately, bypass tier
    if classification == "commander_directive":
        result["status"] = "cos_tasking"
        result["persona"] = "COS"
        logger.info(f"[COMMANDER DIRECTIVE] {sender} — {subject[:60]}")
        _notify_cos(
            classification=classification,
            sender=sender,
            subject=subject,
            persona_id="COS",
            draft_id=None,
            persona_note=f"⚡ COMMANDER DIRECTIVE\n\n"
                         f"Subject: {subject}\n\n"
                         f"Action: Route to Hale for immediate execution."
        )
        return result

    # ── COMMAND tier: Commander direct tasking via COS/COO/HALE prefix ──
    if classification == "direct_command":
        result["tier"] = "COMMAND"
        result["persona"] = "A1"
        # Pass full body (up to 500 words / ~3000 chars) — no truncation for command emails
        body_cmd = body[:3000] if len(body) > 3000 else body
        persona_note = _task_to_persona(
            "direct_command",
            sender_name,
            sender,
            subject,
            body_cmd,
            "COMMAND",
        )
        result["persona_note"] = persona_note or ""
        result["status"] = "cos_tasked"
        _notify_cos(
            classification="direct_command",
            sender=sender,
            subject=subject,
            persona_id="A1",
            draft_id=None,
            persona_note=persona_note or "",
        )
        return result

    # STEP 2: Tier 3 (INTAKE) — Skip entirely
    if tier == "INTAKE":
        result["status"] = "intake_monitoring"
        logger.info(f"[TIER 3 INTAKE] {sender} — No action, monitoring only")
        return result

    # STEP 3: Tier 2 (CLIENT) — WF-17 gate, no auto-draft
    if tier == "CLIENT":
        result["status"] = "client_wf17_gate"
        logger.info(f"[TIER 2 CLIENT] {sender} — Flagged for COS WF-17 review. No auto-draft.")
        # Notify COS that a client email is waiting for manual routing
        _notify_cos(
            classification=classification,
            sender=sender,
            subject=subject,
            persona_id=None,
            draft_id=None,
            persona_note=f"⚠️ CLIENT EMAIL REQUIRES MANUAL ROUTING (WF-17 GATE)\n\n"
                         f"From: {sender_name} ({sender})\n"
                         f"Subject: {subject}\n\n"
                         f"Action: Route to appropriate staff or reply manually.\n"
                         f"No auto-draft generated per WF-17 protocol."
        )
        return result

    # Skip personal/no-persona cases
    if not persona_id:
        result["status"] = "skipped_personal"
        return result

    # STEP 4: Task to persona
    persona_note = _task_to_persona(
        classification, sender_name, sender, subject, body, tier=tier
    )
    result["persona_note"] = persona_note or ""

    # STEP 5: Create draft for SUPPLIER tier if appropriate
    # NOTE: thread_id is from johnloucks3; drafts go to d2mconcierge — cross-account
    # thread linkage always 404s, so we omit thread_id here.
    draft_id = None
    if tier == "SUPPLIER" and classification == "booking_confirmation" and persona_note:
        draft_text = persona_note.strip()
        draft_id = _create_reply_draft(sender, subject, draft_text, None)
        result["draft_id"] = draft_id
        result["status"] = "tasked_supplier_drafted"
    elif tier == "SUPPLIER" and persona_note:
        result["status"] = "tasked_supplier_review"
    else:
        result["status"] = "tasked_to_persona"

    logger.info(f"[TASKED] {tier} tier → {persona_id}: {subject[:50]}")

    # STEP 6: Notify COS via Telegram — FINANCIAL tier only (vendor/intel/supplier silenced)
    if classification in ("financial",) or tier == "FINANCIAL":
        _notify_cos(
            classification=classification,
            sender=sender,
            subject=subject,
            persona_id=persona_id,
            draft_id=draft_id,
            persona_note=result["persona_note"],
        )

    return result


# ---------------------------------------------------------------------------
# Scan — read-only, returns classified emails
# ---------------------------------------------------------------------------


def scan_commander_inbox(hours_back: int = 4) -> List[Dict[str, Any]]:
    """Scan d2mconcierge inbox for command emails sent BY Commander (johnloucks3).

    SCOPE: ONLY emails FROM johnloucks3@gmail.com that have a COS/COO/HALE/Vic
    prefix in the subject line OR the first 100 words of the body.
    Everything else is ignored entirely — no classification, no routing.

    Uses d2mconcierge Gmail service (that is where Commander's sent emails land).

    Args:
        hours_back: How far back to look (default 4 hours)

    Returns:
        List of dicts — only direct_command emails, nothing else
    """
    # Use Commander's Gmail service (johnloucks3) — Commander self-sends commands here
    service = _get_commander_gmail_service()
    if not service:
        logger.warning(
            "Commander Gmail token not found — run: "
            "python3 thunderbird_commander_inbox.py --authorize"
        )
        return []

    state = _load_state()
    processed_ids = set(state.get("processed_ids", []))

    # Strict query: ONLY self-sends FROM Commander — no broad subject filters
    # that would catch every email in the world containing "COS"
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
    after_ts = int(cutoff.timestamp())
    # Exclude scanner's own reply emails (prevent feedback loop / snowball subjects)
    query = (
        f"in:inbox from:johnloucks3@gmail.com "
        f"after:{after_ts} "
        f"-label:{PROCESSED_LABEL} "
        f"-subject:\"✅\" -subject:\"📬\" -subject:\"WING-REPLY\""
    )

    try:
        results = (
            service.users()
            .messages()
            .list(userId="me", q=query, maxResults=MAX_PER_SWEEP)
            .execute()
        )
    except Exception as e:
        logger.error(f"Gmail search failed (d2mconcierge): {e}")
        return []

    messages = results.get("messages", [])
    if not messages:
        logger.info("Commander command scan: no new messages from johnloucks3.")
        return []

    logger.info(
        f"Commander command scan: {len(messages)} messages from johnloucks3 in last {hours_back}h"
    )

    # Command pattern: COS/COO/HALE/VIC followed by ANY non-letter separator
    # Matches: COS: COS-- COS- COS — HALE: HALE-- COO: COO-- Vic: etc.
    _CMD = re.compile(r'^(cos|coo|hale|vic)\W', re.IGNORECASE)

    found: List[Dict[str, Any]] = []

    for msg_stub in messages:
        msg_id = msg_stub["id"]

        if msg_id in processed_ids:
            continue

        try:
            msg = (
                service.users()
                .messages()
                .get(userId="me", id=msg_id, format="full")
                .execute()
            )
        except Exception as e:
            logger.warning(f"Message fetch failed ({msg_id}): {e}")
            continue

        headers = _extract_headers(msg.get("payload", {}).get("headers", []))
        subject = headers.get("Subject", "(no subject)")
        from_raw = headers.get("From", "")
        sender_addr = _extract_email_address(from_raw)
        sender_name = _extract_sender_name(from_raw)
        thread_id = msg.get("threadId")
        message_id_header = headers.get("Message-ID", "") or headers.get("Message-Id", "")

        # Skip scanner's own reply emails — prevents feedback loop
        if headers.get("X-WING-SCANNER"):
            logger.debug(f"Skipping scanner-generated email: {subject[:60]}")
            continue

        body = _decode_body(msg.get("payload", {}))

        # Skip Wing notification emails that lack X-WING-SCANNER but are self-generated
        # (dispatch_and_email.py sends "Directive logged" acks without the header).
        # ONE AND DONE fix (2026-07-04 — Sterling/A7): these self-generated briefs
        # frequently ship with subject "(no subject)" — the identifying text is in
        # the BODY, not the subject. Checking subject alone let the Wing's own
        # daily briefs (THUNDERBIRD COMMAND BRIEF, HALE Compressed Brief, Inbox
        # Digest, ✅ Answer acks) get misclassified as DIRECTION and re-tasked
        # onto the mission board every day it was sent (MISSION-1500/1507/1508/
        # 1528/1529, MISSION-1501/1502/1518 — same broadcast, new mission daily).
        _subj_lower = subject.lower()
        _body_lower = body[:300].lower()
        _noise_check = _subj_lower + " " + _body_lower
        _WING_NOISE_PATTERNS = (
            "directive logged as mission",
            "hale is executing",
            "✅ mission-",
            "❌ mission-",
            "mission-1",  # flood artifact: "MISSION-1NNN: MISSION-1NNN: ..."
            "thunderbird briefing",
            "thunderbird brief",
            "thunderbird eod",
            "thunderbird morning",
            "thunderbird command brief",
            "command brief",
            "compressed brief",
            "agentic intel digest",
            "inbox digest",
            "d2m fpd alert",
            "✅ answer:",
        )
        if any(p in _noise_check for p in _WING_NOISE_PATTERNS):
            logger.debug(f"Skipping Wing-generated noise email: {subject[:60]}")
            continue

        # ── Classification: TEST | QUESTION | CC | DIRECTION | INFORMATION ──
        # Every email FROM Commander is processed — no prefix filter.
        # Order matters: TEST and QUESTION checked before DIRECTION (action words overlap).
        subj_lower = subject.lower()
        body_lower = body[:500].lower()
        combined = subj_lower + " " + body_lower
        body_first_line = body.strip().split("\n")[0].lower()

        if re.search(r'\btest\b', combined):
            classification = "TEST"
        elif re.search(
            r'\?|'
            r'\b(what|how|why|where|when|who|which|can you|could you|'
            r'find out|look up|do you know|is there|are there|tell me|'
            r'what is|what are|how do|how does|how much|how many)\b',
            combined
        ):
            classification = "QUESTION"
        elif re.search(r'\b(fyi|cc|for your info|for your information|heads up|'
                       r'just so you know|keeping you in the loop)\b', body_first_line):
            classification = "CC"
        elif re.search(
            r'\b(do|fix|check|update|create|add|remove|send|call|book|cancel|'
            r'schedule|draft|build|deploy|run|move|change|set|enable|disable|'
            r'investigate|confirm|follow.?up|handle|task|action|priority)\b',
            combined
        ):
            classification = "DIRECTION"
        else:
            classification = "INFORMATION"

        logger.info(f"[{classification}] johnloucks3 — {subject[:60]}")

        found.append(
            {
                "msg_id": msg_id,
                "thread_id": thread_id,
                "message_id_header": message_id_header,
                "subject": subject,
                "sender": sender_addr,
                "sender_name": sender_name,
                "from_raw": from_raw,
                "classification": classification,
                "body": body,
                "body_preview": body[:1000],
            }
        )

    return found


# ---------------------------------------------------------------------------
# Full sweep — scan + task + draft + notify
# ---------------------------------------------------------------------------


def _send_email_to_commander(
    subject: str, body: str,
    thread_id: str = None, in_reply_to: str = None, original_subject: str = None
) -> bool:
    """Send/reply to Commander at johnloucks3. Replies in-thread when thread_id provided.

    X-WING-SCANNER header on every outbound so scan query can exclude our own emails.
    """
    import base64
    from email.mime.text import MIMEText
    try:
        from google.oauth2.credentials import Credentials as _Creds
        from google.auth.transport.requests import Request as _Req
        from googleapiclient.discovery import build as _build
        if not JL3_TOKEN_FILE.exists():
            logger.warning("JL3 token not found — cannot send email confirmation")
            return False
        creds = _Creds.from_authorized_user_info(
            json.loads(JL3_TOKEN_FILE.read_text())
        )
        if creds.expired and creds.refresh_token:
            creds.refresh(_Req())
            JL3_TOKEN_FILE.write_text(creds.to_json())
        svc = _build("gmail", "v1", credentials=creds)
        msg = MIMEText(body, "plain")
        msg["To"] = COMMANDER_EMAIL
        msg["From"] = COMMANDER_EMAIL
        # Thread reply: use Re: prefix and set headers so it lands in same thread
        if in_reply_to:
            msg["Subject"] = f"Re: {original_subject or subject}"
            msg["In-Reply-To"] = in_reply_to
            msg["References"] = in_reply_to
        else:
            msg["Subject"] = subject
        # Stamp so our scan query can exclude scanner-generated emails
        msg["X-WING-SCANNER"] = "true"
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        send_body = {"raw": raw}
        if thread_id:
            send_body["threadId"] = thread_id
        svc.users().messages().send(userId="me", body=send_body).execute()
        logger.info(f"Email sent: {msg['Subject'][:60]}")
        return True
    except Exception as e:
        logger.warning(f"Email send failed: {e}")
        return False


def _dispatch_question_and_reply(
    question_subject: str, question_body: str, msg_id: str = "",
    thread_id: str = None, in_reply_to: str = None
):
    """Dispatch question to Sonnet, reply in-thread with the actual answer.

    msg_id is the inbound Gmail message ID — used for audit trail idempotency.
    """
    # ── A3: Idempotency guard — don't double-reply if thread re-enters ──
    if msg_id and _audit_already_done(msg_id, "reply_sent"):
        logger.info(f"[QUESTION] SKIP reply for {msg_id[:12]} — already sent (audit)")
        return

    prompt = (
        f"You are Hale, COS of Thunderbird Wing, Dreams2Memories Travel.\n"
        f"Commander asked the following question via email. Answer it directly and completely.\n"
        f"Be concise — 3-10 sentences. No preamble. No 'Great question'. Just the answer.\n\n"
        f"Subject: {question_subject}\n\n"
        f"Question:\n{question_body[:2000]}\n\n"
        f"Respond with ONLY the answer. No JSON. Plain prose."
    )
    out_file = THUNDERBIRD_DIR / f"output/question_reply_{int(time.time())}.txt"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(
            [sys.executable,
             str(THUNDERBIRD_DIR / "OpsCenter/dispatch_and_email.py"),
             "--task", f"question-{int(time.time())}",
             "--output", str(out_file),
             "--prompt", prompt,
             "--model", "sonnet",
             "--timeout", "90",
             "--no-reply"],
            capture_output=True, text=True,
            cwd=str(THUNDERBIRD_DIR), timeout=100,
        )
        answer = out_file.read_text().strip() if out_file.exists() else ""
        if not answer:
            answer = "Wing researched this but could not produce a confident answer. Check the mission board for follow-up."
    except Exception as e:
        answer = f"Wing attempted to answer but hit an error: {e}"

    # ── A4: act → verify → record → (label already applied by caller on dispatch init) ──
    send_ok = _send_email_to_commander(
        subject=f"✅ Answer: {question_subject[:70]}",
        body=(
            f"{answer}\n\n"
            f"— Hale · {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
        ),
        thread_id=thread_id,
        in_reply_to=in_reply_to,
        original_subject=question_subject,
    )
    # Record to audit after verified send
    if msg_id:
        _audit_record(msg_id, "inbox", thread_id=thread_id,
                      classified_as="QUESTION",
                      action_taken="reply_sent",
                      outcome="ok" if send_ok else "failed",
                      detail=f"question_reply dispatch {'ok' if send_ok else 'failed'}")


def _send_telegram_confirmation(message: str):
    """Send Telegram confirmation to Commander — no email reply threading."""
    import subprocess as _sp
    try:
        _sp.run(
            [
                sys.executable,
                str(THUNDERBIRD_DIR / "OpsCenter/wing_page.py"),
                "--message", message,
                "--priority", "normal",
            ],
            capture_output=True, text=True, timeout=30,
            cwd=str(THUNDERBIRD_DIR),
        )
    except Exception as e:
        logger.warning(f"Telegram confirmation failed: {e}")


def run_commander_inbox_sweep(hours_back: float = 4) -> Dict[str, Any]:
    """Commander inbox sweep — every email FROM Commander gets classified and actioned.

    Classifications: TEST | DIRECTION | INFORMATION
    Confirmation: Telegram only — no email replies, no rethreading back to Commander.

    Args:
        hours_back: Lookback window (0.25 = 15 min for 2-min scanner)
    """
    logger.info("COMMANDER INBOX SWEEP — all emails from johnloucks3")

    emails = scan_commander_inbox(hours_back=hours_back)

    stats = {"direction": 0, "information": 0, "test": 0, "errors": 0}

    state = _load_state()
    processed_ids = set(state.get("processed_ids", []))

    label_service = _get_commander_gmail_service()
    processed_label_id = (
        _get_or_create_label(label_service, PROCESSED_LABEL) if label_service else None
    )

    for email in emails:
        msg_id = email["msg_id"]
        thread_id = email.get("thread_id")
        classification = email["classification"]
        subject = email["subject"]
        body_preview = email.get("body_preview", "")[:300]
        # Get Message-ID header for in-thread replies
        in_reply_to = email.get("message_id_header")  # set below in scan; fallback None

        # A4: per-email success flag — label applied ONLY after verified success
        _email_actioned_ok = False

        try:
            body_full = email.get("body", "")

            if classification == "DIRECTION":
                # Create mission + reply in-thread with mission ID (no ack, just result)

                # ── A3: Idempotency guard — skip duplicate mission creation ──
                if _audit_already_done(msg_id, "mission_created"):
                    logger.info(
                        f"  [DIRECTION] SKIP {msg_id[:12]} — mission already created (audit)"
                    )
                    _audit_record(msg_id, "inbox", classified_as="DIRECTION",
                                  outcome="skipped-duplicate",
                                  detail="mission_created already in audit trail")
                    _email_actioned_ok = True  # already handled; label it so we don't re-sweep
                else:
                    mission_desc = f"Commander email directive: {subject}. {body_preview[:200]}"
                    result = subprocess.run(
                        [sys.executable,
                         str(THUNDERBIRD_DIR / "OpsCenter/mission_board_sync.py"),
                         "add", subject[:120], mission_desc, "P1"],
                        capture_output=True, text=True,
                        cwd=str(THUNDERBIRD_DIR), timeout=30,
                    )
                    mission_id = ""
                    # ── A4: verify success before recording and labeling ──
                    if "Created:" in result.stdout:
                        mission_id = result.stdout.split("Created:")[-1].strip().split()[0]
                        # A3: record successful mission creation
                        _audit_record(msg_id, "inbox", thread_id=thread_id,
                                      classified_as="DIRECTION",
                                      action_taken="mission_created", outcome="ok",
                                      detail=f"mission_id={mission_id} subject={subject[:80]}")
                        _email_actioned_ok = True
                    else:
                        # Mission board call did not confirm creation — do NOT label, allow retry
                        logger.warning(
                            f"  [DIRECTION] mission_board_sync gave no 'Created:' for {msg_id[:12]} "
                            f"rc={result.returncode} stdout={result.stdout[:200]!r}"
                        )
                        _audit_record(msg_id, "inbox", thread_id=thread_id,
                                      classified_as="DIRECTION",
                                      action_taken="mission_created", outcome="failed",
                                      detail=f"no 'Created:' in stdout: {result.stdout[:200]!r}")
                        # _email_actioned_ok stays False → no label → next sweep retries

                    _send_telegram_confirmation(
                        f"⚡ DIRECTION\n📧 {subject[:80]}\n→ {mission_id or 'queued'} on board."
                    )
                    # No email ack — Telegram is sufficient; email acks were creating inbox noise
                stats["direction"] += 1

            elif classification == "QUESTION":
                # No ack — dispatch Sonnet, reply in-thread with the actual answer.
                # QUESTION reply is async; "success" here = dispatch thread started.
                # We do NOT guard with already_done for reply_sent because the async
                # thread records that after the actual send (see _dispatch_question_and_reply).
                # Label after initiating dispatch (prevents re-dispatching every sweep).
                _send_telegram_confirmation(
                    f"⚡ QUESTION\n📧 {subject[:80]}\n→ Researching now."
                )
                threading.Thread(
                    target=_dispatch_question_and_reply,
                    args=(subject, body_full, msg_id),
                    kwargs={"thread_id": thread_id, "in_reply_to": in_reply_to},
                    daemon=True,
                ).start()
                _email_actioned_ok = True  # dispatch initiated; label to prevent re-dispatch
                stats["information"] += 1

            elif classification == "CC":
                # Save to intel/ and send meaningful ack (SO_EMAIL_CLOSED_LOOP_20260625)
                cc_ts = int(time.time())
                cc_path = THUNDERBIRD_DIR / f"intel/cc_received_{cc_ts}.txt"
                cc_path.parent.mkdir(parents=True, exist_ok=True)
                cc_path.write_text(
                    f"Subject: {subject}\nFrom: {email.get('sender','?')}\n"
                    f"Received: {datetime.now(timezone.utc).isoformat()}\n\n"
                    f"{body_full[:3000]}",
                    encoding="utf-8"
                )
                _send_telegram_confirmation(
                    f"⚡ CC\n📧 {subject[:80]}\n→ Filed: intel/cc_received_{cc_ts}.txt"
                )

                # ── A3: Idempotency guard before sending ack ──
                if _audit_already_done(msg_id, "ack_sent"):
                    logger.info(f"  [CC] SKIP ack for {msg_id[:12]} — already sent")
                    _email_actioned_ok = True
                else:
                    # ── A4: act → verify (return value) → record → then label ──
                    ack_ok = _send_email_to_commander(
                        subject=f"✅ CC Logged: {subject[:70]}",
                        body=(
                            f"CC received and filed.\n\n"
                            f"What was noted: {subject}\n"
                            f"Where filed: intel/cc_received_{cc_ts}.txt\n"
                            f"Action: None identified — logged for reference. Reply if action needed.\n\n"
                            f"— Hale · {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
                        ),
                        thread_id=thread_id,
                        in_reply_to=in_reply_to,
                        original_subject=subject,
                    )
                    # Record to audit BEFORE applying label
                    _audit_record(msg_id, "inbox", thread_id=thread_id,
                                  classified_as="CC",
                                  action_taken="ack_sent",
                                  outcome="ok" if ack_ok else "failed",
                                  detail=f"cc_file=intel/cc_received_{cc_ts}.txt")
                    if ack_ok:
                        _email_actioned_ok = True
                    # If ack failed: _email_actioned_ok stays False → no label → retry next sweep
                stats["information"] += 1

            elif classification == "TEST":
                _send_telegram_confirmation(
                    f"⚡ TEST\n📧 {subject[:80]}\n→ Scanner live."
                )
                _email_actioned_ok = True
                stats["test"] += 1

            else:  # INFORMATION
                # Save to intel/ (SO_EMAIL_CLOSED_LOOP_20260625 — not just "logged", actually log it)
                info_ts = int(time.time())
                info_path = THUNDERBIRD_DIR / f"intel/email_forward_{info_ts}.txt"
                info_path.parent.mkdir(parents=True, exist_ok=True)
                info_path.write_text(
                    f"Subject: {subject}\nFrom: {email.get('sender','?')}\n"
                    f"Received: {datetime.now(timezone.utc).isoformat()}\n\n"
                    f"{body_full[:3000]}",
                    encoding="utf-8"
                )
                _send_telegram_confirmation(
                    f"⚡ INFORMATION\n📧 {subject[:80]}\n"
                    f"→ Saved: intel/email_forward_{info_ts}.txt"
                )
                _audit_record(msg_id, "inbox", thread_id=thread_id,
                              classified_as="INFORMATION",
                              action_taken=None, outcome="ok",
                              detail=f"filed=intel/email_forward_{info_ts}.txt")
                _email_actioned_ok = True
                stats["information"] += 1

            logger.info(f"  [{classification}] {subject[:60]} → confirmed")

            _log_action({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "msg_id": msg_id,
                "subject": subject,
                "sender": email["sender"],
                "classification": classification,
                "status": "actioned",
            })

        except Exception as e:
            logger.error(f"Sweep error for {msg_id}: {e}")
            _audit_record(msg_id, "inbox", classified_as=classification,
                          outcome="failed", detail=f"sweep exception: {e}")
            stats["errors"] += 1

        # ── A4: label ONLY after verified success — label-race fix ──
        # Previously: processed_ids.add() and _apply_label() were unconditional
        # (outside try/except), so a failed action still got labeled, preventing retry.
        if _email_actioned_ok:
            processed_ids.add(msg_id)
            if label_service and processed_label_id:
                _apply_label(label_service, msg_id, processed_label_id)

        time.sleep(0.3)

    state["processed_ids"] = list(processed_ids)
    state["last_run"] = datetime.now(timezone.utc).isoformat()
    state["stats"]["total"] += len(emails)
    _save_state(state)

    summary = {
        "status": "ok",
        "emails_scanned": len(emails),
        "tasked": stats["direction"],
        "drafted": 0,
        "direction": stats["direction"],
        "information": stats["information"],
        "test": stats["test"],
        "errors": stats["errors"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if emails:
        logger.info(
            f"Sweep complete: {len(emails)} emails | "
            f"DIRECTION={stats['direction']} INFO={stats['information']} "
            f"TEST={stats['test']} ERR={stats['errors']}"
        )
    return summary


# ---------------------------------------------------------------------------
# MCP tool registration
# ---------------------------------------------------------------------------


def register_commander_inbox_tools(mcp):
    """Register Commander inbox scanner MCP tools."""
    import json as _json

    @mcp.tool()
    async def scan_commander_inbox_tool(
        hours_back: int = 4,
    ) -> str:
        """Scan Commander's personal inbox (johnloucks3@gmail.com) for D2M-relevant emails.

        Reads and classifies recent emails without creating drafts or notifying COS.
        Use run_commander_inbox_sweep for the full pipeline.

        Args:
            hours_back: How many hours back to search (default 4)
        """
        results = scan_commander_inbox(hours_back=hours_back)
        return _json.dumps(
            {
                "emails_found": len(results),
                "emails": [
                    {
                        "msg_id": e["msg_id"],
                        "subject": e["subject"],
                        "sender": e["sender"],
                        "classification": e["classification"],
                        "body_preview": e["body_preview"][:300],
                    }
                    for e in results
                ],
            },
            indent=2,
        )

    @mcp.tool()
    async def run_commander_inbox_sweep_tool(
        hours_back: int = 4,
    ) -> str:
        """Full Commander inbox sweep: scan → classify → task to persona → draft → notify COS.

        Reads johnloucks3@gmail.com, identifies D2M-relevant emails, routes to appropriate
        Wing staff, creates reply drafts in d2mconcierge (FROM concierge@d2mluxury.quest),
        and notifies COS/Commander via Telegram.

        Personal / non-D2M emails are skipped. Never sends FROM Commander's address.

        Args:
            hours_back: Lookback window (default 4h — use 24 for a manual catch-up)
        """
        result = run_commander_inbox_sweep(hours_back=hours_back)
        return _json.dumps(result, indent=2)


# ---------------------------------------------------------------------------
# Briefing integration helper
# ---------------------------------------------------------------------------


def get_inbox_briefing_line() -> str:
    """Return a one-line summary for inclusion in the morning briefing.

    Reads from the last saved state — does NOT trigger a new sweep.
    """
    try:
        state = _load_state()
        stats = state.get("stats", {})
        last_run = state.get("last_run", "never")
        if last_run and last_run != "never":
            ts = datetime.fromisoformat(last_run).astimezone().strftime("%b %d %H:%M")
        else:
            ts = "never"

        token_status = "ACTIVE" if COMMANDER_TOKEN_FILE.exists() else "NO TOKEN"
        return (
            f"Commander Inbox ({token_status}): "
            f"{stats.get('total', 0)} scanned, "
            f"{stats.get('tasked', 0)} tasked, "
            f"{stats.get('drafted', 0)} drafted "
            f"(last run: {ts})"
        )
    except Exception:
        return "Commander Inbox: status unavailable"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if "--authorize" in sys.argv:
        success = authorize_commander_gmail()
        sys.exit(0 if success else 1)

    elif "--scan" in sys.argv:
        hours = (
            int(sys.argv[sys.argv.index("--scan") + 1])
            if (
                sys.argv.index("--scan") + 1 < len(sys.argv)
                and sys.argv[sys.argv.index("--scan") + 1].isdigit()
            )
            else 4
        )
        emails = scan_commander_inbox(hours_back=hours)
        print(f"\nFound {len(emails)} D2M-relevant emails in last {hours}h:\n")
        for e in emails:
            print(f"  [{e['classification']:<22}] {e['sender']} — {e['subject'][:60]}")

    elif "--sweep" in sys.argv:
        hours = (
            int(sys.argv[sys.argv.index("--sweep") + 1])
            if (
                sys.argv.index("--sweep") + 1 < len(sys.argv)
                and sys.argv[sys.argv.index("--sweep") + 1].isdigit()
            )
            else 4
        )
        result = run_commander_inbox_sweep(hours_back=hours)
        print(json.dumps(result, indent=2))

    else:
        print(__doc__)
        print("\nUsage:")
        print(
            "  python3 thunderbird_commander_inbox.py --authorize      # First-time OAuth"
        )
        print("  python3 thunderbird_commander_inbox.py --scan [hours]   # Scan only")
        print("  python3 thunderbird_commander_inbox.py --sweep [hours]  # Full sweep")
