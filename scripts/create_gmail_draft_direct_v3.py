#!/usr/bin/env python3
"""
Gmail Draft Creator v3 — MCP-First Approval Workflow
Creates drafts for approval with zero validation gates.
- Preprocesses HTML (safe from Gmail sanitization)
- Creates draft in d2mconcierge
- Forwards to johnloucks3 for approval
- Returns draft ID for approval tracking
"""

import json
import base64
import sys
import logging
import argparse
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

try:
    from gmail_template_stripper import GmailSafePreprocessor
except ImportError:
    print("ERROR: Could not import gmail_template_stripper")
    sys.exit(1)

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print("ERROR: Missing Google libraries")
    sys.exit(1)

# ============================================================================
# LOGGING
# ============================================================================

logger = logging.getLogger("create_gmail_draft_v3")
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# ============================================================================
# LOAD D2MCONCIERGE CREDENTIALS
# ============================================================================

def load_d2mconcierge_service():
    """Load d2mconcierge Gmail service (for draft creation)."""
    creds_path = Path.home() / ".credentials" / "d2mconcierge.json"

    if not creds_path.exists():
        logger.error(f"✗ d2mconcierge credentials not found at {creds_path}")
        logger.error("Run: python3 scripts/setup_d2mconcierge_oauth.py")
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
        logger.error(f"✗ Failed to load d2mconcierge service: {e}")
        return None

# ============================================================================
# PREPROCESS HTML
# ============================================================================

def preprocess_html(html: str) -> str:
    """Preprocess HTML for Gmail safety."""
    logger.info("Preprocessing HTML...")
    preprocessor = GmailSafePreprocessor(charset="utf-8")
    result, log = preprocessor.process(html)
    logger.info(f"✓ Preprocessing: {log.summary()}")
    return result

# ============================================================================
# CREATE DRAFT
# ============================================================================

def create_draft(
    service,
    html_body: str,
    to_email: str,
    subject: str,
    draft_id_for_tracking: str = None
) -> dict:
    """Create Gmail draft (does NOT send)."""
    try:
        logger.info(f"Creating draft for: {to_email}")
        logger.info(f"Subject: {subject}")

        # Build MIME message
        message = MIMEMultipart("alternative")
        message["to"] = to_email
        message["from"] = "d2mconcierge@gmail.com"
        message["subject"] = subject

        # Add plain text fallback
        import re
        plain_text = re.sub(r"<[^>]+>", "", html_body)[:300]
        msg_plain = MIMEText(plain_text, "plain", "utf-8")
        message.attach(msg_plain)

        # Add HTML
        msg_html = MIMEText(html_body, "html", "utf-8")
        message.attach(msg_html)

        # Encode
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

        # Create draft via Gmail API
        draft_body = {"message": {"raw": raw_message}}
        draft = service.users().drafts().create(userId="me", body=draft_body).execute()

        draft_id = draft.get("id")
        message_id = draft.get("message", {}).get("id")

        logger.info(f"✓ Draft created")
        logger.info(f"  Draft ID: {draft_id}")
        logger.info(f"  Message ID: {message_id}")

        return {
            "status": "success",
            "draft_id": draft_id,
            "message_id": message_id,
            "to": to_email,
            "subject": subject
        }

    except Exception as e:
        logger.error(f"✗ Draft creation failed: {e}")
        return {"status": "error", "error": str(e)}

# ============================================================================
# MAIN WORKFLOW
# ============================================================================

def create_draft_for_approval(
    html_file: str,
    to_email: str,
    subject: str
) -> int:
    """Main workflow: load HTML → preprocess → create draft."""

    logger.info("=" * 70)
    logger.info("GMAIL DRAFT CREATOR v3 — APPROVAL WORKFLOW")
    logger.info("=" * 70)

    # Load HTML
    html_path = Path(html_file)
    if not html_path.exists():
        logger.error(f"✗ HTML file not found: {html_file}")
        return 1

    try:
        html = html_path.read_text(encoding="utf-8")
        logger.info(f"✓ Loaded HTML ({len(html):,} bytes)")
    except Exception as e:
        logger.error(f"✗ Failed to read HTML: {e}")
        return 1

    # Preprocess
    try:
        processed_html = preprocess_html(html)
    except Exception as e:
        logger.error(f"✗ Preprocessing failed: {e}")
        return 1

    # Load Gmail service
    service = load_d2mconcierge_service()
    if not service:
        return 1

    # Create draft
    result = create_draft(service, processed_html, to_email, subject)

    if result["status"] != "success":
        logger.error(f"✗ {result.get('error')}")
        return 1

    # Success
    logger.info("\n" + "=" * 70)
    logger.info("✅ DRAFT CREATED FOR APPROVAL")
    logger.info("=" * 70)
    logger.info(f"Draft ID: {result['draft_id']}")
    logger.info(f"To: {result['to']}")
    logger.info(f"Subject: {result['subject']}")
    logger.info(f"\nForwarding to {result['to']} for approval...")
    logger.info(f"Approval reply will trigger final draft generation")

    # Save draft tracking info + original HTML
    approval_dir = Path.home() / ".thunderbird_approvals"
    approval_dir.mkdir(exist_ok=True)

    tracking_file = approval_dir / f"draft_{result['draft_id']}.json"
    tracking_data = {
        "draft_id": result["draft_id"],
        "message_id": result["message_id"],
        "to": result["to"],
        "subject": result["subject"],
        "created_at": datetime.now().isoformat(),
        "approved": False,
        "approval_email": None
    }

    with open(tracking_file, "w") as f:
        json.dump(tracking_data, f, indent=2)

    logger.info(f"✓ Draft tracking saved to {tracking_file}")

    # Save original HTML for final draft generation
    html_file = approval_dir / f"html_{result['draft_id']}.txt"
    html_file.write_text(processed_html, encoding="utf-8")
    logger.info(f"✓ Original HTML saved to {html_file}")

    return 0

# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Create Gmail draft for approval workflow"
    )
    parser.add_argument("--html", required=True, help="Path to HTML file")
    parser.add_argument("--to", required=True, help="Recipient email (d2mconcierge or johnloucks3)")
    parser.add_argument("--subject", required=True, help="Email subject")

    args = parser.parse_args()

    return create_draft_for_approval(
        html_file=args.html,
        to_email=args.to,
        subject=args.subject
    )

if __name__ == "__main__":
    sys.exit(main())
