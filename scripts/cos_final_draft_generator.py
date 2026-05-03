#!/usr/bin/env python3
"""
COS Final Draft Generator
Triggered by approval monitor when draft is approved.
Generates final Gmail draft in d2mconcierge Drafts folder.
Sends notification email to johnloucks3.
"""

import json
import sys
import logging
import argparse
from pathlib import Path
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import base64

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
except ImportError:
    print("ERROR: Missing Google libraries")
    sys.exit(1)

# ============================================================================
# LOGGING
# ============================================================================

logger = logging.getLogger("cos_final_draft_generator")
logger.setLevel(logging.DEBUG)

log_file = Path.home() / ".thunderbird_approvals" / "generator.log"
log_file.parent.mkdir(exist_ok=True)

if not logger.handlers:
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

# ============================================================================
# LOAD D2MCONCIERGE SERVICE
# ============================================================================

def load_d2mconcierge_service():
    """Load d2mconcierge Gmail service."""
    creds_path = Path.home() / ".credentials" / "d2mconcierge.json"

    if not creds_path.exists():
        logger.error(f"✗ d2mconcierge credentials not found at {creds_path}")
        return None

    try:
        with open(creds_path) as f:
            token_data = json.load(f)

        creds = Credentials(
            token=token_data.get("token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri=token_data.get("token_uri"),
            client_id=token_data.get("client_id"),
            client_secret=token_data.get("client_secret"),
            scopes=["https://www.googleapis.com/auth/gmail.modify"]
        )

        if creds.expired and creds.refresh_token:
            logger.info("Refreshing d2mconcierge token...")
            creds.refresh(Request())

        service = build("gmail", "v1", credentials=creds)
        logger.info("✓ d2mconcierge Gmail service ready")
        return service

    except Exception as e:
        logger.error(f"✗ Failed to load service: {e}")
        return None

# ============================================================================
# CREATE FINAL DRAFT
# ============================================================================

def create_final_draft(service, html_body: str, to_email: str, subject: str) -> dict:
    """Create final Gmail draft in d2mconcierge Drafts folder."""
    try:
        logger.info(f"Creating final draft")
        logger.info(f"  To: {to_email}")
        logger.info(f"  Subject: {subject}")

        # Build MIME message
        message = MIMEMultipart("alternative")
        message["to"] = to_email
        message["from"] = "d2mconcierge@gmail.com"
        message["subject"] = subject

        # Plain text fallback
        import re
        plain_text = re.sub(r"<[^>]+>", "", html_body)[:300]
        msg_plain = MIMEText(plain_text, "plain", "utf-8")
        message.attach(msg_plain)

        # HTML part (with all formatting intact)
        msg_html = MIMEText(html_body, "html", "utf-8")
        message.attach(msg_html)

        # Encode
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

        # Create draft
        draft_body = {"message": {"raw": raw_message}}
        draft = service.users().drafts().create(userId="me", body=draft_body).execute()

        draft_id = draft.get("id")
        message_id = draft.get("message", {}).get("id")

        logger.info(f"✓ Final draft created")
        logger.info(f"  Draft ID: {draft_id}")
        logger.info(f"  Message ID: {message_id}")

        return {
            "status": "success",
            "draft_id": draft_id,
            "message_id": message_id
        }

    except Exception as e:
        logger.error(f"✗ Draft creation failed: {e}")
        return {"status": "error", "error": str(e)}

# ============================================================================
# SEND NOTIFICATION EMAIL
# ============================================================================

def send_approval_notification(service, to_email: str, draft_id: str, subject: str) -> bool:
    """Send notification email to Commander."""
    try:
        logger.info(f"Sending approval notification to {to_email}...")

        # Build notification email
        notification_subject = f"✅ Draft Ready for Editing: {subject}"
        notification_body = f"""
Your draft has been approved and is now ready for editing in Gmail.

Draft Details:
  Subject: {subject}
  Draft ID: {draft_id}

Next Steps:
1. Open Gmail
2. Go to Drafts folder
3. Open the draft: "{subject}"
4. Edit content as needed
5. Click Send when ready

The draft is in your d2mconcierge account and fully formatted. All images, colors, and styling are preserved.

—COS (Chief of Staff)
Dreams2Memories Travel, LLC
"""

        # Build MIME message
        message = MIMEMultipart("alternative")
        message["to"] = to_email
        message["from"] = "d2mconcierge@gmail.com"
        message["subject"] = notification_subject

        msg_text = MIMEText(notification_body, "plain", "utf-8")
        message.attach(msg_text)

        # Encode and send
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

        # Send directly (not as draft)
        send_body = {"raw": raw_message}
        service.users().messages().send(userId="me", body=send_body).execute()

        logger.info(f"✓ Notification sent to {to_email}")
        return True

    except Exception as e:
        logger.error(f"✗ Failed to send notification: {e}")
        return False

# ============================================================================
# MAIN WORKFLOW
# ============================================================================

def generate_final_draft(draft_id: str, to_email: str, subject: str) -> int:
    """Main workflow: generate final draft on approval."""

    logger.info("=" * 70)
    logger.info("FINAL DRAFT GENERATOR")
    logger.info("=" * 70)
    logger.info(f"Processing approved draft: {draft_id}")

    # Load Gmail service
    service = load_d2mconcierge_service()
    if not service:
        return 1

    # Get draft tracking data
    tracking_file = Path.home() / ".thunderbird_approvals" / f"draft_{draft_id}.json"
    if not tracking_file.exists():
        logger.error(f"✗ Draft tracking file not found: {tracking_file}")
        return 1

    try:
        with open(tracking_file) as f:
            draft_data = json.load(f)
    except Exception as e:
        logger.error(f"✗ Failed to read draft data: {e}")
        return 1

    # Get original HTML from stored file
    html_file = Path.home() / ".thunderbird_approvals" / f"html_{draft_id}.txt"
    if not html_file.exists():
        logger.error(f"✗ Original HTML not found: {html_file}")
        return 1

    try:
        html_body = html_file.read_text(encoding="utf-8")
        logger.info(f"✓ Loaded original HTML ({len(html_body):,} bytes)")
    except Exception as e:
        logger.error(f"✗ Failed to read HTML: {e}")
        return 1

    # Create final draft
    result = create_final_draft(service, html_body, draft_data["to"], draft_data["subject"])

    if result["status"] != "success":
        logger.error(f"✗ {result.get('error')}")
        return 1

    # Send notification
    if not send_approval_notification(service, to_email, draft_id, subject):
        logger.warning("⚠️  Notification send failed, but draft was created")

    # Update tracking
    draft_data["final_draft_generated"] = True
    draft_data["final_draft_generated_at"] = datetime.now().isoformat()
    draft_data["final_draft_id"] = result["draft_id"]

    with open(tracking_file, "w") as f:
        json.dump(draft_data, f, indent=2)

    logger.info("\n" + "=" * 70)
    logger.info("✅ FINAL DRAFT GENERATED")
    logger.info("=" * 70)
    logger.info(f"Draft ID: {result['draft_id']}")
    logger.info(f"Notification sent to: {to_email}")
    logger.info(f"Ready for editing in Gmail Drafts folder")

    return 0

# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Generate final draft on approval")
    parser.add_argument("--draft-id", required=True, help="Draft ID")
    parser.add_argument("--to", required=True, help="Recipient email")
    parser.add_argument("--subject", required=True, help="Email subject")

    args = parser.parse_args()

    return generate_final_draft(
        draft_id=args.draft_id,
        to_email=args.to,
        subject=args.subject
    )

if __name__ == "__main__":
    sys.exit(main())
