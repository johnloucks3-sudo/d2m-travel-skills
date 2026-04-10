#!/usr/bin/env python3
"""
Create draft from D2M account but CC Commander for visibility
"""

import json
import base64
import sys
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError as e:
    print(f"ERROR: Missing Google libraries: {e}")
    sys.exit(1)


def create_d2m_draft_with_cc():
    """Create draft from D2M account but CC Commander"""

    print("=== D2M DRAFT WITH COMMANDER CC ===")

    # Load D2M persona token
    token_file = Path("/home/john/Thunderbird/config/persona_gmail_token.json")
    if not token_file.exists():
        print(f"❌ D2M token file not found at {token_file}")
        sys.exit(1)

    try:
        with open(token_file) as f:
            token_data = json.load(f)
        print("✓ Loaded D2M persona token")
    except Exception as e:
        print(f"❌ ERROR reading token file: {e}")
        sys.exit(1)

    # Create credentials
    creds = Credentials(
        token=token_data.get("token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri=token_data.get("token_uri"),
        client_id=token_data.get("client_id"),
        client_secret=token_data.get("client_secret"),
        scopes=token_data.get(
            "scopes", ["https://www.googleapis.com/auth/gmail.modify"]
        ),
    )

    # Refresh if needed
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            print("✓ Token refreshed")
        except Exception as e:
            print(f"⚠️ Could not refresh token: {e}")

    # Build Gmail service
    try:
        service = build("gmail", "v1", credentials=creds)
        print("✓ Gmail service initialized for D2M account")
    except Exception as e:
        print(f"❌ ERROR building Gmail service: {e}")
        sys.exit(1)

    # Read HTML email body
    html_file = Path(
        "/home/john/Thunderbird/drafts/commander_to_kyle_lifecycle_explanation.html"
    )
    if not html_file.exists():
        print(f"❌ ERROR: HTML file not found at {html_file}")
        sys.exit(1)

    with open(html_file, "r", encoding="utf-8") as f:
        html_body = f.read()

    # Email parameters - FROM D2M, TO Kyle, CC Commander
    to_email = "kyle.kuklinski@gmail.com"
    cc_email = "johnloucks3@gmail.com"  # Commander CC'd for visibility
    from_email = "d2mconcierge@gmail.com"
    subject = "Your Panama Canal Cruise Planning Timeline & D2M Service Process"

    print(f"\n📧 Creating draft from D2M account:")
    print(f"  To: {to_email}")
    print(f"  CC: {cc_email} (Commander for visibility)")
    print(f"  From: {from_email}")
    print(f"  Subject: {subject}")

    # Build email message
    message = MIMEMultipart("alternative")
    message["to"] = to_email
    message["cc"] = cc_email  # CC Commander
    message["from"] = from_email
    message["subject"] = subject

    # Add HTML part
    msg_html = MIMEText(html_body, "html", "utf-8")
    message.attach(msg_html)

    # Encode message
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

    # Create draft via Gmail API
    try:
        draft_body = {"message": {"raw": raw_message}}

        draft = service.users().drafts().create(userId="me", body=draft_body).execute()

        draft_id = draft.get("id")
        message_id = draft.get("message", {}).get("id")

        print(f"\n✅ SUCCESS!")
        print(f"Draft created from D2M account")
        print(f"Draft ID: {draft_id}")
        print(f"Message ID: {message_id}")
        print(
            f"\n📋 Access draft at: https://mail.google.com/mail/u/0/#drafts?compose={message_id}"
        )
        print(f"\n👁️  Commander CC'd for visibility - will see in inbox when sent")

        return draft_id

    except HttpError as error:
        error_content = (
            error.content.decode("utf-8")
            if isinstance(error.content, bytes)
            else error.content
        )
        print(f"\n❌ Gmail API Error: {error.resp.status}")
        print(f"Details: {error_content}")
        return None
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        return None


if __name__ == "__main__":
    result = create_d2m_draft_with_cc()
    if result:
        print(f"\n🎯 Task completed. Draft ID: {result}")
        print("Commander: Check D2M Gmail account for this draft")
        sys.exit(0)
    else:
        print(f"\n💥 Task failed. No draft created.")
        sys.exit(1)
