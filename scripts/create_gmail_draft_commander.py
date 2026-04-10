#!/usr/bin/env python3
"""
Direct Gmail API draft creation for Commander's johnloucks3@gmail.com account
Creates draft for Kuklinski lifecycle email in Commander's draft folder
"""

import json
import base64
import sys
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Google API imports
try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError as e:
    print(f"ERROR: Missing Google libraries: {e}")
    print(
        "Install: pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client"
    )
    sys.exit(1)


def create_commander_draft():
    """Create Gmail draft in Commander's (johnloucks3@gmail.com) account"""

    print("=== COMMANDER GMAIL DRAFT CREATION ===")

    # Load token from creds/gmail_token.json (Commander's account)
    token_file = Path("/home/john/Thunderbird/creds/gmail_token.json")
    if not token_file.exists():
        print(f"❌ ERROR: Commander's token file not found at {token_file}")
        print(
            "  This token is for johnloucks3@gmail.com (expires: 2026-04-08 19:44 MT)"
        )
        sys.exit(1)

    try:
        with open(token_file) as f:
            token_data = json.load(f)
        print("✓ Loaded Commander's Gmail token")
    except Exception as e:
        print(f"❌ ERROR reading token file: {e}")
        sys.exit(1)

    # Create credentials object
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

    # Check token expiry
    expiry = token_data.get("expiry", "unknown")
    print(f"  Token expires: {expiry}")

    # Refresh if needed
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            print("✓ Token refreshed")
        except Exception as e:
            print(f"⚠️ Warning: Could not refresh token: {e}")
            print("  Will try with existing token (may fail if expired)")

    # Build Gmail service
    try:
        service = build("gmail", "v1", credentials=creds)
        print("✓ Gmail service initialized for johnloucks3@gmail.com")
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

    # Email parameters
    to_email = "kyle.kuklinski@gmail.com"
    subject = "Your Panama Canal Cruise Planning Timeline & D2M Service Process"
    from_email = "d2mconcierge@gmail.com"

    print(f"\n📧 Creating draft in Commander's Gmail:")
    print(f"  To: {to_email}")
    print(f"  From: {from_email} (via Commander's account)")
    print(f"  Subject: {subject}")

    # Build email message
    message = MIMEMultipart("alternative")
    message["to"] = to_email
    message["from"] = f"{from_email} via johnloucks3@gmail.com"
    message["subject"] = subject
    message["reply-to"] = from_email  # So replies go to D2M

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
        print(f"Draft created in Commander's Gmail (johnloucks3@gmail.com)")
        print(f"Draft ID: {draft_id}")
        print(f"Message ID: {message_id}")
        print(
            f"\n📋 Access draft at: https://mail.google.com/mail/u/0/#drafts?compose={message_id}"
        )
        print(f"\n💡 Commander: Check your Gmail drafts folder for this message")

        # Also list drafts to confirm
        try:
            drafts = (
                service.users().drafts().list(userId="me").execute().get("drafts", [])
            )
            print(f"\n📊 Current draft count: {len(drafts)}")
            for i, d in enumerate(drafts[-3:], 1):
                msg = service.users().drafts().get(userId="me", id=d["id"]).execute()
                subj = msg["message"].get("payload", {}).get("headers", {})
                if isinstance(subj, dict):
                    subj = subj.get("subject", "No subject")
                else:
                    subj = next(
                        (h["value"] for h in subj if h["name"] == "Subject"),
                        "No subject",
                    )
                print(f"  {i}. {subj[:50]}...")
        except Exception as e:
            print(f"⚠️ Could not list drafts: {e}")

        return draft_id

    except HttpError as error:
        error_content = (
            error.content.decode("utf-8")
            if isinstance(error.content, bytes)
            else error.content
        )
        print(f"\n❌ Gmail API Error: {error.resp.status}")
        print(f"Details: {error_content}")

        if error.resp.status == 401:
            print("\n🔑 Authentication failed")
            print("Possible causes:")
            print("  1. Token expired (expiry: {})".format(expiry))
            print("  2. Token revoked")
            print("  3. Insufficient scopes")
            print("\nFix: Run OAuth re-authorization:")
            print("  python api/thunderbird_google_auth.py --authorize-persona")
        elif error.resp.status == 403:
            print("\n🔒 Permission denied")
            print("Possible causes:")
            print("  1. Gmail API not enabled")
            print("  2. Account doesn't have Gmail access")
            print("  3. Wrong OAuth scopes")
        elif error.resp.status == 400:
            print("\n📝 Bad request")
            print("Possible causes:")
            print("  1. Invalid message format")
            print("  2. Missing required fields")
            print("  3. HTML content encoding issue")

        return None
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        return None


if __name__ == "__main__":
    result = create_commander_draft()
    if result:
        print(f"\n🎯 Task completed. Draft ID: {result}")
        sys.exit(0)
    else:
        print(f"\n💥 Task failed. No draft created.")
        sys.exit(1)
