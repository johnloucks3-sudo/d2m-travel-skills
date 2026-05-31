#!/usr/bin/env python3
"""
THUNDERBIRD EMAIL SCANNER v2
File: thunderbird_email_scanner_fixed.py

Scans d2mconcierge@gmail.com for unread emails addressed to Wing staff.
Detects staff mentions (COS, [COS], A3, [A3], Dani, Hale, etc.)
Executes the task via the appropriate persona using the Anthropic API.
Replies to johnloucks3@gmail.com with the FULL completed response
ONLY after the task has been executed — never immediately.

Usage:
  python thunderbird_email_scanner_fixed.py --sweep      # run once
  python thunderbird_email_scanner_fixed.py --loop       # continuous (5-min)
"""

import base64
import json
import logging
import os
import re
import subprocess
import sys
import time
import tempfile
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html.parser import HTMLParser
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Use foolproof wrapper per SO 24 APR 2026
sys.path.insert(0, str(Path.home() / "Thunderbird"))
from core.ai_infra.thunderbird_headless_spawn import spawn_headless_claude

# ============================================================================
# CONFIGURATION
# ============================================================================

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
STATE_FILE = THUNDERBIRD_DIR / "OpsCenter" / "email_scanner_state.json"
LOG_DIR = THUNDERBIRD_DIR / "OpsCenter" / "logs"
LOG_FILE = LOG_DIR / "email_scanner.log"
LOG_DIR.mkdir(parents=True, exist_ok=True)

TOKEN_FILE = THUNDERBIRD_DIR / "gmail_token.json"
OAUTH_CREDENTIALS_FILE = THUNDERBIRD_DIR / "gmail_oauth_credentials.json"
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

D2M_CONCIERGE_EMAIL = "d2mconcierge@gmail.com"
COMMANDER_EMAIL = "johnloucks3@gmail.com"
MODEL = "claude-sonnet-4-6"
TASK_TIMEOUT_SECONDS = 240   # max time to wait for persona response
MAX_BODY_CHARS = 6000        # truncate email body before sending to persona
SWEEP_INTERVAL_MINUTES = 5

# ============================================================================
# LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# ============================================================================
# STAFF REGISTRY
# Each entry: (staff_key, display_name, [keyword_list])
# Keywords matched case-insensitively, with or without brackets.
# Order matters — more specific entries first to avoid false matches.
# ============================================================================

STAFF_REGISTRY = [
    # Command section
    ("HALE",   "Ms. Victoria 'Victory' Hale, SES-6 — Chief of Staff",
     ["cos", "hale", "victoria", "iron vic", "coo"]),
    ("NAIA",   "Naia Solberg-Vega — EXEC",
     ["exec", "naia", "solberg", "solberg-vega"]),

    # Primary staff
    ("DEMBE",  "Lt Col Marcus 'Wraith' Dembe — A2 Research & Intel",
     ["a2", "dembe", "marcus", "wraith"]),
    ("MOREAU", "Danielle 'Dani' Moreau — A3 Concierge",
     ["a3", "dani", "moreau", "echo"]),
    ("VIPER",  "Lt Col Ryan 'Viper' Castillo — A5 Strategy",
     ["a5", "castillo", "viper"]),
    ("LUNA",   "Luna Voss — A6 Creative Director",
     ["a6", "luna", "voss"]),
    ("GAUGE",  "Brig Gen Thomas 'Gauge' Sterling — A7 Process",
     ["a7", "sterling", "gauge"]),
    ("HARLAN", "Victor 'Vic' Harlan — A9 Finance",
     ["a9", "harlan"]),

    # Special staff
    ("PADRE",  "Col James 'Padre' Washington — Chaplain",
     ["ch", "padre", "washington"]),
    ("ELON",   "ELON — A12 Innovation",
     ["a12", "elon"]),
]

# ============================================================================
# PERSONA SYSTEM PROMPTS
# ============================================================================

PERSONA_PROMPTS = {
    "HALE": """You are Ms. Victoria "Victory" Hale, SES-6, Chief of Staff and COO for Dreams2Memories Travel, LLC.
Owner: John Loucks ("Yoda"), Colorado Springs CO.
You are measured, authoritative, executive. You run the Wing. You bring a recommendation with every problem.
Lead with the answer — no preamble, no trailing recap.
When given a task by Commander via email, complete it fully and present the finished work.
Company: Dreams2Memories Travel, LLC. Sign off: "Thanks" — never "Best".""",

    "NAIA": """You are Naia Solberg-Vega, EXEC for Dreams2Memories Travel, LLC.
You own Commander's voice, visual output, and brand tone.
You write client-facing copy, proposals, template polish — anything that represents D2M to the outside world.
When given a task, deliver finished, polished output ready to use.
Company: Dreams2Memories Travel, LLC. Sign off: "Thanks" — never "Best".""",

    "DEMBE": """You are Lt Col Marcus "Wraith" Dembe, A2 Research & Market Intelligence for Dreams2Memories Travel, LLC.
Evidence-first. Destination research, cruise intel, competitor analysis, sourcing.
Lead with the key finding, then the supporting detail.
Company: Dreams2Memories Travel, LLC.""",

    "MOREAU": """You are Danielle "Dani" Moreau, A3 Luxury Travel Concierge for Dreams2Memories Travel, LLC.
You are the sole client-facing voice — warm, crisp, certain. Short sentences, no hedging.
You aggregate information, craft it with voice and tone, and present as advocate for the client.
When given a drafting task, produce the finished client-ready copy.
Company: Dreams2Memories Travel, LLC. Sign off: "Thanks" — never "Best".""",

    "VIPER": """You are Lt Col Ryan "Viper" Castillo, A5 Strategy & Business Growth (Deputy COS) for Dreams2Memories Travel, LLC.
Business decisions, pricing strategy, growth vectors, competitive positioning.
Lead with the recommendation, then the reasoning.
Company: Dreams2Memories Travel, LLC.""",

    "LUNA": """You are Luna Voss, A6 Creative Director & Brand Dreamer for Dreams2Memories Travel, LLC.
Brand narratives, luxury copywriting, destination storytelling, itinerary prose.
Your writing feels premium, evocative, and worth the price of the trip.
Deliver finished, publishable copy.
Company: Dreams2Memories Travel, LLC.""",

    "GAUGE": """You are Brig Gen (Ret.) Thomas "Gauge" Sterling, A7 Process Improvement for Dreams2Memories Travel, LLC.
Waste elimination, Baldrige standards, lessons learned. You audit, analyze metrics, reduce waste.
Direct, data-first, actionable. Lead with the finding, then the fix.
Company: Dreams2Memories Travel, LLC.""",

    "HARLAN": """You are Victor "Vic" Harlan, A9 Finance & Process Improvement for Dreams2Memories Travel, LLC.
Commission audits, cost analysis, ROI, budget tracking.
Lead with the number, then the recommendation.
Company: Dreams2Memories Travel, LLC.""",

    "PADRE": """You are Col James "Padre" Washington, Chaplain (Ethics & Morale) for Dreams2Memories Travel, LLC.
Ethics checks, morale, perspective, wisdom.
Thoughtful, grounded, honest. Help Commander see the right path.
Company: Dreams2Memories Travel, LLC.""",

    "ELON": """You are ELON, A12 Innovation & Disruption for Dreams2Memories Travel, LLC.
Automation ideas, first-principles redesign, "why are we doing this manually?"
Direct, irreverent, impatient with inefficiency.
Propose bold solutions with concrete implementation steps.
Company: Dreams2Memories Travel, LLC.""",
}

# ============================================================================
# HTML STRIPPING
# ============================================================================

class _HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self._parts = []

    def handle_data(self, data):
        self._parts.append(data)

    def get_text(self):
        return " ".join(self._parts)


def strip_html(html: str) -> str:
    s = _HTMLStripper()
    s.feed(html)
    return re.sub(r"\s+", " ", s.get_text()).strip()


# ============================================================================
# STATE MANAGEMENT
# ============================================================================

def load_state() -> dict:
    if not STATE_FILE.exists():
        return {"processed_ids": []}
    try:
        with open(STATE_FILE) as f:
            raw = json.load(f)
        # Migrate old key name
        if "processed_message_ids" in raw and "processed_ids" not in raw:
            raw["processed_ids"] = raw.pop("processed_message_ids")
        raw.setdefault("processed_ids", [])
        return raw
    except Exception:
        return {"processed_ids": []}


def save_state(state: dict) -> None:
    # Keep last 1000 processed IDs
    state["processed_ids"] = state["processed_ids"][-1000:]
    state["last_run"] = datetime.utcnow().isoformat()
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


# ============================================================================
# GMAIL AUTH
# ============================================================================

def get_gmail_service():
    creds = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not OAUTH_CREDENTIALS_FILE.exists():
                logger.error(f"OAuth credentials not found: {OAUTH_CREDENTIALS_FILE}")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(
                str(OAUTH_CREDENTIALS_FILE), SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    try:
        service = build("gmail", "v1", credentials=creds)
        logger.info("Gmail authenticated")
        return service
    except Exception as e:
        logger.error(f"Gmail build failed: {e}")
        return None


# ============================================================================
# GMAIL OPERATIONS
# ============================================================================

def fetch_unread_emails(service, max_results: int = 50) -> list[dict]:
    """Fetch unread emails from inbox. Returns list of parsed email dicts."""
    try:
        result = (
            service.users()
            .messages()
            .list(userId="me", q="is:unread in:inbox", maxResults=max_results)
            .execute()
        )
        messages = result.get("messages", [])
        logger.info(f"Found {len(messages)} unread messages")
        return messages
    except Exception as e:
        logger.error(f"Failed to list messages: {e}")
        return []


def read_email(service, message_id: str) -> Optional[dict]:
    """Read and parse a Gmail message into a usable dict."""
    try:
        msg = (
            service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )
    except Exception as e:
        logger.error(f"Failed to read message {message_id}: {e}")
        return None

    headers = {h["name"]: h["value"] for h in msg["payload"].get("headers", [])}
    body_text = _extract_body(msg["payload"])
    return {
        "gmail_id": message_id,
        "thread_id": msg.get("threadId", ""),
        "message_id_header": headers.get("Message-ID", ""),
        "references": headers.get("References", ""),
        "from": headers.get("From", ""),
        "subject": headers.get("Subject", "(no subject)"),
        "body": body_text,
        "snippet": msg.get("snippet", ""),
    }


def _extract_body(payload: dict) -> str:
    """Extract plain text body from Gmail message payload."""
    # Prefer text/plain; fall back to text/html stripped
    plain = _find_part(payload, "text/plain")
    if plain:
        return plain
    html = _find_part(payload, "text/html")
    if html:
        return strip_html(html)
    return payload.get("snippet", "")


def _find_part(payload: dict, mime_type: str) -> Optional[str]:
    """Recursively find a MIME part by type and decode it."""
    if payload.get("mimeType") == mime_type:
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

    for part in payload.get("parts", []):
        result = _find_part(part, mime_type)
        if result:
            return result

    return None


def mark_read(service, message_id: str) -> None:
    """Remove UNREAD label from message."""
    try:
        service.users().messages().modify(
            userId="me",
            id=message_id,
            body={"removeLabelIds": ["UNREAD"]},
        ).execute()
        logger.info(f"Marked {message_id} as read")
    except Exception as e:
        logger.error(f"Failed to mark {message_id} as read: {e}")


def send_reply(service, email: dict, staff_display: str, response_text: str) -> bool:
    """
    Send the completed persona response to Commander at johnloucks3@gmail.com.
    Sent as a reply in the original thread.
    """
    original_subject = email["subject"]
    reply_subject = (
        original_subject
        if original_subject.lower().startswith("re:")
        else f"RE: {original_subject}"
    )

    now = datetime.now().strftime("%Y-%m-%d %H:%M MT")

    body = (
        f"Commander,\n\n"
        f"Task completed by {staff_display}.\n"
        f"Original email: \"{original_subject}\" from {email['from']}\n"
        f"Completed: {now}\n\n"
        f"{'─' * 60}\n\n"
        f"{response_text}\n\n"
        f"{'─' * 60}\n\n"
        f"Thanks,\n"
        f"Thunderbird Wing\n"
        f"Dreams2Memories Travel, LLC"
    )

    mime_msg = MIMEMultipart()
    mime_msg["To"] = COMMANDER_EMAIL
    mime_msg["From"] = D2M_CONCIERGE_EMAIL
    mime_msg["Subject"] = reply_subject

    # Thread properly
    if email["message_id_header"]:
        mime_msg["In-Reply-To"] = email["message_id_header"]
        refs = email["references"]
        mime_msg["References"] = (
            f"{refs} {email['message_id_header']}".strip()
        )

    mime_msg.attach(MIMEText(body, "plain"))
    raw = base64.urlsafe_b64encode(mime_msg.as_bytes()).decode()

    try:
        service.users().messages().send(
            userId="me",
            body={"raw": raw, "threadId": email["thread_id"]},
        ).execute()
        logger.info(f"Reply sent to {COMMANDER_EMAIL}: {reply_subject}")
        return True
    except Exception as e:
        logger.error(f"Failed to send reply: {e}")
        return False


# ============================================================================
# STAFF DETECTION
# ============================================================================

def detect_staff(subject: str, body: str) -> Optional[tuple[str, str]]:
    """
    Detect an intentional staff directive — NOT incidental keyword mention.

    Strategy (tiered confidence):
      1. Bracketed in subject: [COS], [A3]  →  certain
      2. Unbracketed in subject            →  high confidence
      3. Bracketed anywhere in body        →  high confidence
      4. Unbracketed in FIRST 300 chars    →  likely directive (addressee line)
      5. Beyond 300 chars, unbracketed     →  skip (incidental / forwarded content)

    This prevents matching "cos" buried in a forwarded email body or "coo" in
    an unrelated word.
    """
    body_head = body[:300]  # Only inspect the opening of the body

    for staff_key, display_name, keywords in STAFF_REGISTRY:
        for kw in keywords:
            escaped = re.escape(kw)
            word_pat  = r"\b" + escaped + r"\b"
            brack_pat = r"\[" + escaped + r"\]"

            # Tier 1 & 2: subject contains keyword (bracketed or plain)
            if re.search(brack_pat, subject, re.IGNORECASE):
                logger.info(f"Staff target [{kw}] in subject: {staff_key}")
                return staff_key, display_name
            if re.search(word_pat, subject, re.IGNORECASE):
                logger.info(f"Staff target '{kw}' in subject: {staff_key}")
                return staff_key, display_name

            # Tier 3: bracketed anywhere in body (explicit directive)
            if re.search(brack_pat, body, re.IGNORECASE):
                logger.info(f"Staff target [{kw}] in body: {staff_key}")
                return staff_key, display_name

            # Tier 4: unbracketed in first 300 chars of body only
            if re.search(word_pat, body_head, re.IGNORECASE):
                logger.info(f"Staff target '{kw}' in body head: {staff_key}")
                return staff_key, display_name

    return None


# ============================================================================
# PERSONA EXECUTION
# ============================================================================

def _max_plan_env() -> dict:
    """
    Build subprocess environment with ANTHROPIC_API_KEY stripped.
    Without the key, the claude CLI falls through to Max plan OAuth
    stored in ~/.claude/.credentials.json — $0 cost.
    """
    env = dict(os.environ)
    env.pop("ANTHROPIC_API_KEY", None)
    env.pop("ANTHROPIC_BASE_URL", None)
    return env


def execute_task(staff_key: str, email: dict) -> Optional[str]:
    """
    Invoke the claude CLI with the appropriate persona system prompt.
    Uses Max plan OAuth (ANTHROPIC_API_KEY stripped) — $0 cost.
    The email subject + body become the task.
    Returns the persona's full response text.
    """
    system_prompt = PERSONA_PROMPTS.get(staff_key)
    if not system_prompt:
        logger.error(f"No persona prompt for staff key: {staff_key}")
        return None

    body = email["body"]
    # Normalize line endings, strip control chars and non-ASCII
    # (non-ASCII in subprocess args can freeze the claude CLI)
    body = body.replace("\r\n", "\n").replace("\r", "\n")
    body = body.encode("ascii", errors="ignore").decode("ascii")
    body = "".join(c for c in body if c >= " " or c == "\n")
    if len(body) > MAX_BODY_CHARS:
        body = body[:MAX_BODY_CHARS] + "\n\n[...email truncated for length...]"

    task_content = (
        f"IMPORTANT: Respond with plain text only. Do NOT browse any URLs, "
        f"do NOT use web search, do NOT run any tools. Generate your complete "
        f"response based solely on the information provided below.\n\n"
        f"Subject: {email['subject']}\n"
        f"From: {email['from']}\n\n"
        f"{body}"
    ).strip()

    if not task_content:
        logger.warning(f"Empty email body for message {email['gmail_id']}")
        return None

    logger.info(f"Executing task: persona={staff_key}, input={len(task_content)} chars")

    # Use foolproof wrapper per SO 24 APR 2026
    response_text = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
            output_file = tmp.name

        result = spawn_headless_claude(
            prompt=task_content,
            output_file=output_file,
            model=MODEL,
            task_name=f"persona_{staff_key}",
            background=False,
            timeout=TASK_TIMEOUT_SECONDS,
            system_prompt=system_prompt,
            extra_args=["--tools", ""],  # text-only — no browsing, no file ops, no web search
        )

        if result.get("status") == "TIMEOUT":
            logger.error(f"Persona {staff_key} timed out after {TASK_TIMEOUT_SECONDS}s")
            return None
        elif result.get("status") not in ["COMPLETED"]:
            logger.error(f"Persona {staff_key} spawn failed: {result.get('error', 'unknown error')}")
            return None

        # Read the output file
        response_text = Path(output_file).read_text()
        if not response_text or not response_text.strip():
            logger.error(f"No response text from persona {staff_key}")
            return None

    except Exception as e:
        logger.error(f"Persona {staff_key} invocation failed: {e}")
        return None
    finally:
        # Cleanup temp file
        try:
            Path(output_file).unlink()
        except:
            pass

    if response_text:
        logger.info(f"Persona {staff_key} responded ({len(response_text)} chars)")
        return response_text

    logger.error(f"No response text from persona {staff_key}")
    return None


# ============================================================================
# MAIN SWEEP
# ============================================================================

def run_sweep(service, state: dict) -> dict:
    stats = {"scanned": 0, "no_staff": 0, "executed": 0, "reply_sent": 0, "errors": 0}

    messages = fetch_unread_emails(service)
    if not messages:
        return stats

    for msg_ref in messages:
        gmail_id = msg_ref["id"]
        stats["scanned"] += 1

        # Skip already processed
        if gmail_id in state["processed_ids"]:
            logger.debug(f"Already processed: {gmail_id}")
            continue

        # Read full email
        email = read_email(service, gmail_id)
        if not email:
            stats["errors"] += 1
            state["processed_ids"].append(gmail_id)
            continue

        logger.info(f"Processing: [{email['subject']}] from {email['from']}")

        # Detect staff target
        match = detect_staff(email["subject"], email["body"])
        if not match:
            logger.info(f"No staff mention found — leaving unread for Commander review")
            # Do NOT mark processed — leave unread so Commander can see it
            stats["no_staff"] += 1
            continue

        staff_key, staff_display = match

        # Execute the task via Anthropic API (this is the "staffing out" step)
        response_text = execute_task(staff_key, email)
        if not response_text:
            logger.error(f"Task execution failed for {staff_key} on message {gmail_id}")
            stats["errors"] += 1
            state["processed_ids"].append(gmail_id)
            continue

        stats["executed"] += 1

        # Send FULL response to Commander — only after execution is complete
        sent = send_reply(service, email, staff_display, response_text)
        if sent:
            stats["reply_sent"] += 1

        # Mark original email as read
        mark_read(service, gmail_id)

        # Record as processed
        state["processed_ids"].append(gmail_id)
        logger.info(f"Complete: {staff_key} → reply sent to {COMMANDER_EMAIL}")

    save_state(state)
    logger.info(f"Sweep stats: {stats}")
    return stats


# ============================================================================
# ENTRY POINTS
# ============================================================================

def sweep_once() -> None:
    logger.info("=" * 60)
    logger.info("THUNDERBIRD EMAIL SCANNER v2 — SINGLE SWEEP")
    logger.info("=" * 60)

    service = get_gmail_service()
    if not service:
        logger.error("Gmail auth failed. Exiting.")
        sys.exit(1)

    state = load_state()
    run_sweep(service, state)


def sweep_loop() -> None:
    logger.info("=" * 60)
    logger.info(f"THUNDERBIRD EMAIL SCANNER v2 — LOOP ({SWEEP_INTERVAL_MINUTES}m)")
    logger.info("=" * 60)

    service = get_gmail_service()
    if not service:
        logger.error("Gmail auth failed. Exiting.")
        sys.exit(1)

    try:
        while True:
            state = load_state()
            stats = run_sweep(service, state)
            logger.info(f"Next sweep in {SWEEP_INTERVAL_MINUTES} minutes")
            time.sleep(SWEEP_INTERVAL_MINUTES * 60)
    except KeyboardInterrupt:
        logger.info("Scanner stopped.")


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("""
THUNDERBIRD EMAIL SCANNER v2

Usage:
  python thunderbird_email_scanner_fixed.py --sweep   Run once
  python thunderbird_email_scanner_fixed.py --loop    Run every 5 minutes

Behavior:
  - Scans d2mconcierge@gmail.com for unread emails
  - Detects staff mentions: COS, [COS], A3, [A3], Dani, Hale, A2, etc.
  - Executes the task via the correct persona (Anthropic API)
  - Replies to johnloucks3@gmail.com with the FULL completed response
  - Marks the original email as read
  - Emails with no staff mention are left untouched for Commander review
""")
        sys.exit(0)

    mode = sys.argv[1]
    if mode == "--sweep":
        sweep_once()
    elif mode == "--loop":
        sweep_loop()
    else:
        print(f"Unknown mode: {mode}")
        sys.exit(1)


if __name__ == "__main__":
    main()
