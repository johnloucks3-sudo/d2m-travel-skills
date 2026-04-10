#!/usr/bin/env python3
"""
THUNDERBIRD EMAIL SCANNER — FIXED VERSION
File: thunderbird_email_scanner_fixed.py
Author: Claude (fixing thunderbird_email_maintenance.py)
Date: 2026-04-07

PROBLEM FIXED:
- Original script tried HTTP JSON-RPC to non-existent port 8767
- New version uses Google API directly (proven in thunderbird_gmail.py)

ARCHITECTURE:
SWEEP → CLASSIFY → ROUTE & DRAFT → ARCHIVE (NO MCP DEPENDENCY)

Scans d2mconcierge@gmail.com for unread emails matching staff patterns.
Routes to appropriate inboxes (Hale, OpenCode, etc.).
Sends reply notification to johnloucks3@gmail.com.
"""

import json
import os
import sys
import logging
import time
import base64
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from email.mime.text import MIMEText

# ============================================================================
# CONFIGURATION
# ============================================================================

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
OPSCENTER_DIR = THUNDERBIRD_DIR / "OpsCenter"
EMAIL_CONDITIONING_DIR = THUNDERBIRD_DIR / "email_conditioning"

# State and logging
STATE_FILE = OPSCENTER_DIR / "email_scanner_state.json"
LOG_FILE = OPSCENTER_DIR / "logs" / "email_scanner.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

# Gmail accounts
D2M_CONCIERGE_EMAIL = "d2mconcierge@gmail.com"
COMMANDER_EMAIL = "johnloucks3@gmail.com"
CONCIERGE_SEND_AS = "concierge@d2mluxury.quest"

# Inbox destinations
GOOSE_INBOX = THUNDERBIRD_DIR / "OpsCenter" / "collaboration" / "goose_inbox.md"
CLAUDE_INBOX = THUNDERBIRD_DIR / "claude_inbox.md"
OPENCODE_INBOX = THUNDERBIRD_DIR / "OpsCenter" / "collaboration" / "opencode_inbox.md"

# Sweep config
SWEEP_INTERVAL_MINUTES = 5
DEDUP_WINDOW_SECONDS = 600
STATE_PRUNE_SIZE = 500

# OAuth
OAUTH_CREDENTIALS_FILE = THUNDERBIRD_DIR / "gmail_oauth_credentials.json"
TOKEN_FILE = THUNDERBIRD_DIR / "gmail_token.json"
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

# ============================================================================
# LOGGING SETUP
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
# STATE MANAGEMENT
# ============================================================================

def load_state() -> Dict[str, Any]:
    """Load dedup state from JSON file."""
    if not STATE_FILE.exists():
        return {"processed_message_ids": [], "last_run": None}
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load state: {e}. Using fresh state.")
        return {"processed_message_ids": [], "last_run": None}


def save_state(state: Dict[str, Any]) -> None:
    """Save dedup state to JSON file. Prune if needed."""
    if len(state["processed_message_ids"]) > STATE_PRUNE_SIZE:
        state["processed_message_ids"] = state["processed_message_ids"][-STATE_PRUNE_SIZE:]
        logger.info(f"Pruned processed_message_ids to {STATE_PRUNE_SIZE}")

    state["last_run"] = datetime.utcnow().isoformat()
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save state: {e}")


def is_processed(message_id: str, state: Dict[str, Any]) -> bool:
    """Check if message was already processed."""
    return message_id in state["processed_message_ids"]


def mark_processed(message_id: str, state: Dict[str, Any]) -> None:
    """Mark message as processed."""
    if message_id not in state["processed_message_ids"]:
        state["processed_message_ids"].append(message_id)

# ============================================================================
# GMAIL API AUTH & INTEGRATION
# ============================================================================

def get_gmail_service():
    """
    Get authenticated Gmail service.
    Uses OAuth flow with token caching.
    """
    creds = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not OAUTH_CREDENTIALS_FILE.exists():
                logger.error(f"OAuth credentials not found at {OAUTH_CREDENTIALS_FILE}")
                return None

            flow = InstalledAppFlow.from_client_secrets_file(
                OAUTH_CREDENTIALS_FILE, SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    try:
        service = build("gmail", "v1", credentials=creds)
        logger.info("Gmail service authenticated successfully")
        return service
    except Exception as e:
        logger.error(f"Failed to build Gmail service: {e}")
        return None


def gmail_search(service, query: str, max_results: int = 50) -> List[str]:
    """Search Gmail for messages matching query."""
    try:
        results = service.users().messages().list(
            userId="me",
            q=query,
            maxResults=max_results
        ).execute()

        messages = results.get("messages", [])
        message_ids = [m["id"] for m in messages]
        logger.info(f"Gmail search returned {len(message_ids)} messages")
        return message_ids
    except Exception as e:
        logger.error(f"Gmail search failed: {e}")
        return []


def gmail_read_message(service, message_id: str) -> Optional[Dict[str, Any]]:
    """Read full message content."""
    try:
        message = service.users().messages().get(
            userId="me",
            id=message_id,
            format="full"
        ).execute()

        headers = message["payload"].get("headers", [])
        header_dict = {h["name"]: h["value"] for h in headers}

        # Get body
        body = ""
        if "parts" in message["payload"]:
            for part in message["payload"]["parts"]:
                if part["mimeType"] == "text/plain":
                    data = part.get("body", {}).get("data", "")
                    if data:
                        body = base64.urlsafe_b64decode(data).decode("utf-8")
                    break
        else:
            data = message["payload"].get("body", {}).get("data", "")
            if data:
                body = base64.urlsafe_b64decode(data).decode("utf-8")

        return {
            "message_id": message_id,
            "sender": header_dict.get("From", ""),
            "subject": header_dict.get("Subject", ""),
            "body": body,
            "snippet": message.get("snippet", ""),
            "timestamp": header_dict.get("Date", ""),
            "labels": message.get("labelIds", []),
        }
    except Exception as e:
        logger.error(f"Failed to read message {message_id}: {e}")
        return None


def archive_email(service, message_id: str) -> bool:
    """Archive email by removing from INBOX."""
    try:
        service.users().messages().modify(
            userId="me",
            id=message_id,
            body={"removeLabelIds": ["INBOX"]}
        ).execute()
        logger.info(f"Archived message {message_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to archive message {message_id}: {e}")
        return False

# ============================================================================
# EMAIL CLASSIFICATION
# ============================================================================

STAFF_NAMES = {
    "HALE": ["victoria", "hale", "cos", "iron vic"],
    "DEMBE": ["marcus", "dembe", "a2", "wraith"],
    "MOREAU": ["dani", "moreau", "a3", "echo"],
    "VIPER": ["ryan", "castillo", "a5", "viper"],
    "LUNA": ["luna", "voss", "a6"],
    "GAUGE": ["thomas", "sterling", "a7", "gauge"],
    "HARLAN": ["victor", "harlan", "a9", "vic"],
    "PADRE": ["james", "washington", "ch"],
    "ELON": ["elon", "a12"],
    "NAIA": ["naia", "solberg", "exec", "commander's intent"],
}

def extract_staff_mention(email_body: str, email_subject: str) -> Optional[str]:
    """
    Extract staff mention from email.
    Returns staff key (HALE, DEMBE, etc.) or None.
    """
    combined = f"{email_subject} {email_body}".lower()

    for staff_key, names in STAFF_NAMES.items():
        for name in names:
            if re.search(r"\b" + re.escape(name) + r"\b", combined):
                logger.info(f"Detected staff mention: {staff_key}")
                return staff_key

    return None


def classify_email(email_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Classify email and determine routing.
    Returns: {"action": "task"|"draft"|"skip", "target_inbox": "claude"|"goose", "staff": "HALE"|...}
    """
    subject = email_data.get("subject", "").lower()
    body = email_data.get("body", "").lower()
    sender = email_data.get("sender", "").lower()

    # Skip patterns
    if any(x in subject for x in ["[noreply]", "[auto-reply]", "[out of office]"]):
        return {"action": "skip", "reason": "auto-reply or noreply"}

    # Extract staff mention
    staff = extract_staff_mention(body, subject)

    if not staff:
        return {"action": "skip", "reason": "no staff mention found"}

    # Route to appropriate inbox
    target_inbox = "claude" if staff in ["HALE", "NAIA"] else "goose"

    return {
        "action": "task",
        "target_inbox": target_inbox,
        "staff": staff,
        "sender": sender,
        "subject": subject,
        "message_id": email_data.get("message_id"),
    }


# ============================================================================
# INBOX WRITING
# ============================================================================

def write_task_to_inbox(inbox_path: Path, classification: Dict[str, Any]) -> bool:
    """Write task to appropriate inbox file."""
    try:
        task_entry = f"""
## TASK: EMAIL-SCAN-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}
status: UNREAD
from: Email Scanner
priority: P1
task: |
  **Staff Mention Detected: {classification['staff']}**
  From: {classification['sender']}
  Subject: {classification['subject']}
  Message ID: {classification['message_id']}

  Email detected and flagged for {classification['staff']}.
  Please review and task out as appropriate.

"""
        with open(inbox_path, "a") as f:
            f.write(task_entry)
        logger.info(f"Wrote task to {inbox_path.name}")
        return True
    except Exception as e:
        logger.error(f"Failed to write task: {e}")
        return False


# ============================================================================
# REPLY NOTIFICATION
# ============================================================================

def send_reply_notification(service, reply_to_email: str) -> bool:
    """Send notification to Commander that email was received and assigned."""
    try:
        message = MIMEText(
            "Email received and assigned to D2M staff for review.\n"
            "Status: Processing\n"
            "Check /home/john/Thunderbird/OpsCenter/collaboration/goose_inbox.md for task details."
        )
        message["to"] = reply_to_email
        message["from"] = D2M_CONCIERGE_EMAIL
        message["subject"] = "D2M Email Processing Confirmation"

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        service.users().messages().send(
            userId="me",
            body={"raw": raw_message}
        ).execute()

        logger.info(f"Sent reply notification to {reply_to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send reply notification: {e}")
        return False


# ============================================================================
# MAIN SWEEP LOGIC
# ============================================================================

def process_email_sweep(service, state: Dict[str, Any]) -> Dict[str, int]:
    """Main sweep logic."""
    stats = {"processed": 0, "skipped": 0, "archived": 0, "errors": 0}

    logger.info("Starting email sweep...")

    # Search for unread emails
    query = "is:unread"
    message_ids = gmail_search(service, query)

    if not message_ids:
        logger.info("No unread emails found.")
        return stats

    logger.info(f"Found {len(message_ids)} unread emails")

    for message_id in message_ids:
        # Check dedup
        if is_processed(message_id, state):
            logger.debug(f"Skipping {message_id}: already processed")
            stats["skipped"] += 1
            continue

        # Read email
        email_data = gmail_read_message(service, message_id)
        if not email_data:
            logger.warning(f"Failed to read {message_id}")
            stats["errors"] += 1
            continue

        # Classify
        classification = classify_email(email_data)

        if classification["action"] == "skip":
            logger.info(f"Skipping {message_id}: {classification.get('reason')}")
            stats["skipped"] += 1
            mark_processed(message_id, state)
            continue

        # Write to inbox
        inbox_path = CLAUDE_INBOX if classification["target_inbox"] == "claude" else GOOSE_INBOX
        if write_task_to_inbox(inbox_path, classification):
            # Send reply notification to Commander
            send_reply_notification(service, COMMANDER_EMAIL)

            # Archive the email
            if archive_email(service, message_id):
                stats["archived"] += 1

        mark_processed(message_id, state)
        stats["processed"] += 1

    # Save state
    save_state(state)

    logger.info(f"Sweep complete: {stats}")
    return stats


# ============================================================================
# ENTRY POINTS
# ============================================================================

def sweep_once() -> None:
    """Run a single email sweep."""
    logger.info("=" * 70)
    logger.info("EMAIL SCANNER — SINGLE SWEEP")
    logger.info("=" * 70)

    service = get_gmail_service()
    if not service:
        logger.error("Failed to get Gmail service. Exiting.")
        return

    state = load_state()
    stats = process_email_sweep(service, state)

    logger.info(f"Scan complete: {json.dumps(stats)}")


def sweep_loop() -> None:
    """Run email sweep in continuous loop."""
    logger.info("=" * 70)
    logger.info("EMAIL SCANNER — CONTINUOUS LOOP (5-minute interval)")
    logger.info("=" * 70)

    service = get_gmail_service()
    if not service:
        logger.error("Failed to get Gmail service. Exiting.")
        return

    try:
        while True:
            state = load_state()
            stats = process_email_sweep(service, state)

            if stats["processed"] > 0:
                logger.info(f"✓ Processed {stats['processed']} emails")

            logger.info(f"Next sweep in {SWEEP_INTERVAL_MINUTES} minutes...")
            time.sleep(SWEEP_INTERVAL_MINUTES * 60)

    except KeyboardInterrupt:
        logger.info("Sweep loop interrupted by user.")


def main():
    """Command-line interface."""
    if len(sys.argv) < 2:
        print("""
THUNDERBIRD EMAIL SCANNER — FIXED VERSION

USAGE:
  python thunderbird_email_scanner_fixed.py [MODE]

MODES:
  --sweep       Run a single email sweep (default)
  --loop        Run continuous sweep loop (5-minute intervals)

EXAMPLES:
  python thunderbird_email_scanner_fixed.py --sweep
  python thunderbird_email_scanner_fixed.py --loop
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
