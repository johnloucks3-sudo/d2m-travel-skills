#!/usr/bin/env python3
"""
Create Gmail drafts in Commander's johnloucks3@gmail.com account with proper HTML formatting
Uses OAuth credentials from Google Keep note
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


def get_johnloucks3_token_path():
    """Get path for johnloucks3 OAuth token"""
    return Path("/home/john/Thunderbird/creds/johnloucks3_token.json")


def authenticate_johnloucks3():
    """Authenticate to johnloucks3@gmail.com using existing OAuth token"""

    print("=== JOHNLOUCKS3 GMAIL AUTHENTICATION ===")

    token_path = get_johnloucks3_token_path()

    if not token_path.exists():
        print(f"❌ ERROR: johnloucks3 token not found at {token_path}")
        print("Run the original script first to create token")
        sys.exit(1)

    # Load existing token
    try:
        with open(token_path, "r") as token_file:
            token_data = json.load(token_file)

        scopes = [
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.modify",
            "https://www.googleapis.com/auth/gmail.compose",
        ]

        creds = Credentials.from_authorized_user_info(token_data, scopes)

        # Check if token is expired and refresh if needed
        if creds.expired and creds.refresh_token:
            print("Token expired, refreshing...")
            creds.refresh(Request())
            # Save refreshed token
            token_data = {
                "token": creds.token,
                "refresh_token": creds.refresh_token,
                "token_uri": creds.token_uri,
                "client_id": creds.client_id,
                "client_secret": creds.client_secret,
                "scopes": creds.scopes,
                "expiry": creds.expiry.isoformat() if creds.expiry else None,
            }
            with open(token_path, "w") as token_file:
                json.dump(token_data, token_file, indent=2)
            print("✓ Token refreshed and saved")

        print("✓ Using existing johnloucks3 token")
        return creds

    except Exception as e:
        print(f"❌ ERROR loading token: {e}")
        sys.exit(1)


def create_johnloucks3_draft_corrected():
    """Create Gmail draft in Commander's johnloucks3@gmail.com account with proper HTML"""

    print("\n=== CREATING PROPERLY FORMATTED DRAFT ===")

    # Authenticate
    creds = authenticate_johnloucks3()
    if not creds:
        print("❌ Authentication failed")
        return None

    # Build Gmail service
    try:
        service = build("gmail", "v1", credentials=creds)

        # Verify account
        profile = service.users().getProfile(userId="me").execute()
        email_address = profile.get("emailAddress")
        print(f"✓ Authenticated as: {email_address}")
        if email_address != "johnloucks3@gmail.com":
            print(f"⚠️ WARNING: Logged in as {email_address}, not johnloucks3@gmail.com")

    except Exception as e:
        print(f"❌ ERROR building Gmail service: {e}")
        return None

    # Read PROPER HTML email body (not the .eml disguised as .html)
    html_file = Path(
        "/home/john/Thunderbird/drafts/TASK-0.5-kuklinski_group_welcome_draft.html"
    )

    if not html_file.exists():
        print(f"❌ ERROR: Proper HTML file not found at {html_file}")
        print(f"\nAvailable Kuklinski files:")
        for f in Path("/home/john/Thunderbird/drafts").glob("*kuklinski*"):
            print(f"  - {f.name} ({f.stat().st_size} bytes)")
        return None

    with open(html_file, "r", encoding="utf-8") as f:
        html_body = f.read()

    # Verify it's actual HTML
    if not html_body.strip().startswith("<!DOCTYPE html>"):
        print(f"⚠️ WARNING: File doesn't start with <!DOCTYPE html>")
        print(f"First 100 chars: {html_body[:100]}")

    # Email parameters
    to_email = "kyle.kuklinski@gmail.com"
    subject = "Welcome to Your Panama Canal Cruise Planning & D2M Service Timeline"
    from_email = "d2mconcierge@gmail.com"

    print(f"\n📧 Creating draft with proper HTML formatting:")
    print(f"  To: {to_email}")
    print(f"  From: {from_email} (via johnloucks3@gmail.com)")
    print(f"  Subject: {subject}")
    print(f"  HTML file: {html_file.name} ({len(html_body)} chars)")

    # Build email message
    message = MIMEMultipart("alternative")
    message["to"] = to_email
    message["from"] = f"{from_email} via johnloucks3@gmail.com"
    message["subject"] = subject
    message["reply-to"] = from_email  # So replies go to D2M

    # Add HTML part
    msg_html = MIMEText(html_body, "html", "utf-8")
    message.attach(msg_html)

    # Also add plain text fallback
    plain_text = """Welcome to Your Panama Canal Cruise Planning & D2M Service Timeline

Hi Kyle,

Following up on our recent conversation, I wanted to share how Dreams2Memories manages your Panama Canal cruise preparation through our comprehensive lifecycle system.

Our timeline ensures every detail is handled at the right time, from initial planning through post-cruise follow-up.

Best regards,
John Loucks
Dreams2Memories Travel, LLC"""

    msg_plain = MIMEText(plain_text, "plain", "utf-8")
    message.attach(msg_plain)

    # Encode message
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

    # Create draft via Gmail API
    try:
        draft_body = {"message": {"raw": raw_message}}

        draft = service.users().drafts().create(userId="me", body=draft_body).execute()

        draft_id = draft.get("id")
        message_id = draft.get("message", {}).get("id")

        print(
            f"\n✅ SUCCESS! Properly formatted draft created in Commander's johnloucks3@gmail.com"
        )
        print(f"Draft ID: {draft_id}")
        print(f"Message ID: {message_id}")
        print(
            f"\n📋 Access draft at: https://mail.google.com/mail/u/0/#drafts?compose={message_id}"
        )
        print(f"\n💡 Commander: Check your Gmail drafts folder")
        print(f"   This draft should preserve all HTML formatting")

        return draft_id

    except HttpError as error:
        error_content = (
            error.content.decode("utf-8")
            if isinstance(error.content, bytes)
            else error.content
        )
        print(f"\n❌ Gmail API Error: {error.resp.status}")
        print(f"Details: {error_content[:500]}")

        if error.resp.status == 400:
            print("\n📝 Bad request - possible HTML formatting issue")
            print("Check if HTML contains invalid characters or encoding")

        return None
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        return None


def main():
    """Main function to create properly formatted Kuklinski draft"""

    print("=== JOHNLOUCKS3 PROPER HTML DRAFT CREATOR ===\n")

    # Check if we have the token
    token_path = get_johnloucks3_token_path()
    if not token_path.exists():
        print(f"❌ Missing johnloucks3 token at {token_path}")
        print(f"Run first: python scripts/create_johnloucks3_draft.py")
        sys.exit(1)

    # Create the draft
    draft_id = create_johnloucks3_draft_corrected()

    if draft_id:
        print(f"\n🎯 Task completed. Draft ID: {draft_id}")
        sys.exit(0)
    else:
        print(f"\n💥 Task failed. No draft created.")
        sys.exit(1)


if __name__ == "__main__":
    main()
