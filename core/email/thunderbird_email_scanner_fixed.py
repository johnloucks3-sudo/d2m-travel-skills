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
ROUTING_LOG = OPSCENTER_DIR / "logs" / "email_routing.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
ROUTING_LOG.parent.mkdir(parents=True, exist_ok=True)

# Gmail accounts
D2M_CONCIERGE_EMAIL = "d2mconcierge@gmail.com"
COMMANDER_EMAIL = "johnloucks3@gmail.com"
CONCIERGE_SEND_AS = "concierge@d2mluxury.quest"

# Inbox destinations
WING_COMMS = THUNDERBIRD_DIR / "OpsCenter" / "collaboration" / "wing_comms.md"
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
        state["processed_message_ids"] = state["processed_message_ids"][
            -STATE_PRUNE_SIZE:
        ]
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
        results = (
            service.users()
            .messages()
            .list(userId="me", q=query, maxResults=max_results)
            .execute()
        )

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
        message = (
            service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )

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
            userId="me", id=message_id, body={"removeLabelIds": ["INBOX"]}
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
    "HALE": [
        "victoria",
        "hale",
        "cos",
        "iron vic",
        r"\[cos\]",
        "coo",
        r"\[coo\]",
        "a3",
    ],
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
            # Special handling for bracketed terms like [cos] or [coo]
            if name.startswith("[") and name.endswith("]"):
                # For bracketed terms, look for exact match with brackets
                pattern = r"\[" + re.escape(name[1:-1]) + r"\]"
            else:
                # For regular terms, use word boundaries
                pattern = r"\b" + re.escape(name) + r"\b"

            if re.search(pattern, combined, re.IGNORECASE):
                logger.info(f"Detected staff mention: {staff_key}")
                return staff_key

    return None


def classify_email(email_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Classify email and determine routing.
    Returns: {"action": "task"|"draft"|"skip", "target_inbox": "wing_comms"|"claude"|"opencode", "staff": "HALE"|...}
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

    # Route to appropriate inbox - HALE/NAIA go to wing_comms, others to opencode
    if staff in ["HALE", "NAIA"]:
        target_inbox = "wing_comms"
    else:
        target_inbox = "opencode"

    return {
        "action": "task",
        "target_inbox": target_inbox,
        "staff": staff,
        "sender": sender,
        "subject": subject,
        "message_id": email_data.get("message_id"),
        "body_preview": body[:500] if body else "",
    }


# ============================================================================
# DEDUPLICATION & INBOX WRITING
# ============================================================================


def check_duplicate_task(sender: str, subject: str, staff: str) -> bool:
    """
    Check if a similar task already exists in claude_inbox.md
    Returns True if duplicate found, False otherwise.
    """
    try:
        if not CLAUDE_INBOX.exists():
            return False

        with open(CLAUDE_INBOX, "r") as f:
            content = f.read()

        # Check for similar email tasks in claude_inbox
        search_patterns = [
            f"Subject: {subject[:100]}",  # First 100 chars of subject
            f"Message ID: {staff}",
            f"From: {sender}",
        ]

        # If any of these patterns exist in claude_inbox, it's likely a duplicate
        for pattern in search_patterns:
            if pattern in content:
                logger.info(f"Duplicate task detected for pattern: {pattern[:50]}...")
                return True

        return False
    except Exception as e:
        logger.error(f"Deduplication check failed: {e}")
        return False


def write_wing_comms_task(classification: Dict[str, Any]) -> bool:
    """Write task to wing_comms.md file with proper format."""
    try:
        task_id = f"WC-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-EMAIL-{classification['staff']}"

        task_entry = f"""
---
msg_id: {task_id}
msg_type: ALERT
from: Email Scanner
priority: P1
to: {classification["staff"]}
submitted_at: {datetime.utcnow().strftime("%Y-%m-%d %H:%M MT")}
content: |
  **Email Detected — Staff Mention: {classification["staff"]}**
  
  **From:** {classification["sender"]}
  **Subject:** {classification["subject"]}
  **Message ID:** {classification["message_id"]}
  
  **Body Preview:**
  {classification["body_preview"][:300]}...
  
  **Action Required:** Email flagged for {classification["staff"]}. Please review and task out as appropriate.
  **Scanner Status:** Processed & Routed to wing_comms

---
"""
        with open(WING_COMMS, "a") as f:
            f.write(task_entry)
        logger.info(f"Wrote task to wing_comms.md for {classification['staff']}")
        return True
    except Exception as e:
        logger.error(f"Failed to write to wing_comms: {e}")
        return False


def write_opencode_task(classification: Dict[str, Any]) -> bool:
    """Write task to opencode_inbox.md file."""
    try:
        task_entry = f"""
---
## TASK: EMAIL-SCAN-{datetime.utcnow().strftime("%Y%m%d%H%M%S")}
status: UNREAD
from: Email Scanner
priority: P1
task: |
  **Staff Mention Detected: {classification["staff"]}**
  From: {classification["sender"]}
  Subject: {classification["subject"]}
  Message ID: {classification["message_id"]}
  Body Preview: {classification["body_preview"][:200]}...

  Email detected and flagged for {classification["staff"]}.
  Please review and task out as appropriate.

---
"""
        with open(OPENCODE_INBOX, "a") as f:
            f.write(task_entry)
        logger.info(f"Wrote task to opencode_inbox.md for {classification['staff']}")
        return True
    except Exception as e:
        logger.error(f"Failed to write task to opencode: {e}")
        return False


def write_claude_task(classification: Dict[str, Any]) -> bool:
    """Write task to claude_inbox.md file with deduplication check."""
    # First check for duplicates
    if check_duplicate_task(
        classification["sender"], classification["subject"], classification["staff"]
    ):
        logger.info(
            f"Duplicate task skipped for {classification['staff']} - {classification['subject'][:50]}..."
        )
        return False

    try:
        task_entry = f"""
---
## TASK: EMAIL-SCAN-{datetime.utcnow().strftime("%Y%m%d%H%M%S")}
status: UNREAD
from: Email Scanner
priority: P1
task: |
  **Staff Mention Detected: {classification["staff"]}**
  From: {classification["sender"]}
  Subject: {classification["subject"]}
  Message ID: {classification["message_id"]}
  Body Preview: {classification["body_preview"][:200]}...

  Email detected and flagged for {classification["staff"]}.
  Please review and task out as appropriate.

---
"""
        with open(CLAUDE_INBOX, "a") as f:
            f.write(task_entry)
        logger.info(f"Wrote task to claude_inbox.md for {classification['staff']}")
        return True
    except Exception as e:
        logger.error(f"Failed to write task to claude: {e}")
        return False


def log_routing_decision(
    classification: Dict[str, Any], success: bool, action: str
) -> None:
    """Log routing decision to routing log file."""
    try:
        log_entry = f"{datetime.utcnow().isoformat()} | {classification['staff']} | {classification['target_inbox']} | {classification['subject'][:100]}... | {action} | {'SUCCESS' if success else 'FAILED'}\n"

        with open(ROUTING_LOG, "a") as f:
            f.write(log_entry)

        logger.debug(
            f"Routing logged: {classification['staff']} → {classification['target_inbox']}"
        )
    except Exception as e:
        logger.error(f"Failed to log routing decision: {e}")

    try:
        task_entry = f"""
---
## TASK: EMAIL-SCAN-{datetime.utcnow().strftime("%Y%m%d%H%M%S")}
status: UNREAD
from: Email Scanner
priority: P1
task: |
  **Staff Mention Detected: {classification["staff"]}**
  From: {classification["sender"]}
  Subject: {classification["subject"]}
  Message ID: {classification["message_id"]}
  Body Preview: {classification["body_preview"][:200]}...

  Email detected and flagged for {classification["staff"]}.
  Please review and task out as appropriate.

---
"""
        with open(CLAUDE_INBOX, "a") as f:
            f.write(task_entry)
        logger.info(f"Wrote task to claude_inbox.md for {classification['staff']}")
        return True
    except Exception as e:
        logger.error(f"Failed to write task to claude: {e}")
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
            userId="me", body={"raw": raw_message}
        ).execute()

        logger.info(f"Sent reply notification to {reply_to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send reply notification: {e}")
        return False


# ============================================================================
# MAIN SWEEP LOGIC
# ============================================================================


def process_email_sweep(
    service, state: Dict[str, Any], search_all: bool = False
) -> Dict[str, int]:
    """Main sweep logic."""
    stats = {"processed": 0, "skipped": 0, "archived": 0, "errors": 0}

    logger.info(
        "Starting email sweep..."
        + (" (ALL emails since March 31)" if search_all else " (unread only)")
    )

    # Search for emails
    query = "after:2026/03/31"
    if not search_all:
        query += " is:unread"

    message_ids = gmail_search(service, query, max_results=100 if search_all else 50)

    if not message_ids:
        logger.info("No emails found.")
        return stats

    logger.info(
        f"Found {len(message_ids)} emails"
        + (" since March 31" if search_all else " (unread)")
    )

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

        # Route to appropriate inbox with logging
        success = False
        action = "skipped"

        if classification["action"] == "task":
            if classification["target_inbox"] == "wing_comms":
                success = write_wing_comms_task(classification)
                action = "wing_comms"
            elif classification["target_inbox"] == "claude":
                success = write_claude_task(classification)
                action = "claude"
            elif classification["target_inbox"] == "opencode":
                success = write_opencode_task(classification)
                action = "opencode"

            # Log routing decision
            log_routing_decision(classification, success, action)

            if success:
                # Send reply notification to Commander
                send_reply_notification(service, COMMANDER_EMAIL)

                # Archive the email
                if archive_email(service, message_id):
                    stats["archived"] += 1

                stats["processed"] += 1
            else:
                stats["errors"] += 1

        mark_processed(message_id, state)

    # Save state
    save_state(state)

    logger.info(f"Sweep complete: {stats}")
    return stats


# ============================================================================
# ENTRY POINTS
# ============================================================================


def sweep_once(search_all: bool = False) -> None:
    """Run a single email sweep."""
    logger.info("=" * 70)
    logger.info(
        "EMAIL SCANNER — SINGLE SWEEP"
        + (" (ALL emails since March 31)" if search_all else "")
    )
    logger.info("=" * 70)

    service = get_gmail_service()
    if not service:
        logger.error("Failed to get Gmail service. Exiting.")
        return

    state = load_state()
    stats = process_email_sweep(service, state, search_all=search_all)

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
  --sweep       Run a single email sweep (unread only, default)
  --sweep-all   Run sweep on ALL emails since March 31
  --loop        Run continuous sweep loop (5-minute intervals)

EXAMPLES:
  python thunderbird_email_scanner_fixed.py --sweep
  python thunderbird_email_scanner_fixed.py --sweep-all
  python thunderbird_email_scanner_fixed.py --loop
""")
        sys.exit(0)

    mode = sys.argv[1]

    if mode == "--sweep":
        sweep_once(search_all=False)
    elif mode == "--sweep-all":
        sweep_once(search_all=True)
    elif mode == "--loop":
        sweep_loop()
    else:
        print(f"Unknown mode: {mode}")
        sys.exit(1)


if __name__ == "__main__":
    main()
