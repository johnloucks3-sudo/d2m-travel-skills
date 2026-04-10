#!/usr/bin/env python3
"""
Create PROPER Gmail draft with extracted HTML from MIME content
Extracts HTML from base64-encoded .eml file and creates clean draft
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

    token_path = get_johnloucks3_token_path()

    if not token_path.exists():
        print(f"❌ ERROR: johnloucks3 token not found at {token_path}")
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

        return creds

    except Exception as e:
        print(f"❌ ERROR loading token: {e}")
        sys.exit(1)


def extract_html_from_mime(mime_file_path):
    """Extract HTML content from MIME .eml file with base64 encoding"""

    try:
        with open(mime_file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # The HTML part is base64 encoded after the boundary
        if "base64" in content:
            parts = content.split("base64")
            if len(parts) > 1:
                # Get everything after 'base64' line
                encoded_part = parts[1].strip()
                # Decode base64 to get actual HTML
                decoded_html = base64.b64decode(encoded_part).decode("utf-8")
                return decoded_html

        # If no base64 found, try to extract HTML directly
        if "<!DOCTYPE html>" in content:
            # Extract from the DOCTYPE onwards
            html_start = content.find("<!DOCTYPE html>")
            return content[html_start:]

        # If all else fails, return as is
        return content

    except Exception as e:
        print(f"❌ ERROR extracting HTML from MIME: {e}")
        return None


def create_proper_lifecycle_draft():
    """Create Gmail draft with properly extracted HTML content"""

    print("=== CREATING PROPER LIFECYCLE DRAFT ===")

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

    except Exception as e:
        print(f"❌ ERROR building Gmail service: {e}")
        return None

    # Extract HTML from the MIME file
    mime_file = Path(
        "/home/john/Thunderbird/drafts/commander_to_kyle_lifecycle_explanation.html"
    )

    if not mime_file.exists():
        print(f"❌ ERROR: MIME file not found at {mime_file}")
        return None

    html_body = extract_html_from_mime(mime_file)

    if not html_body:
        print("❌ Could not extract HTML content from MIME file")
        return None

    print(f"✓ Extracted HTML content: {len(html_body)} characters")

    # Email parameters
    to_email = "kyle.kuklinski@gmail.com"
    subject = "Your Panama Canal Cruise Planning Timeline & D2M Service Process"
    from_email = "d2mconcierge@gmail.com"

    print(f"\n📧 Creating draft with extracted HTML:")
    print(f"  To: {to_email}")
    print(f"  From: {from_email} (via johnloucks3@gmail.com)")
    print(f"  Subject: {subject}")

    # Build email message
    message = MIMEMultipart("alternative")
    message["to"] = to_email
    message["from"] = f"{from_email} via johnloucks3@gmail.com"
    message["subject"] = subject
    message["reply-to"] = from_email  # So replies go to D2M

    # Add HTML part (extracted from MIME)
    msg_html = MIMEText(html_body, "html", "utf-8")
    message.attach(msg_html)

    # Add plain text fallback
    plain_text = """Your Panama Canal Cruise Planning Timeline & D2M Service Process

Hi Kyle,

Following up on our recent conversation about your Panama Canal cruise preparation. This email explains our comprehensive timeline and service process.

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

        print(f"\n✅ SUCCESS! Proper lifecycle draft created in johnloucks3@gmail.com")
        print(f"Draft ID: {draft_id}")
        print(f"Message ID: {message_id}")
        print(
            f"\n📋 Access draft at: https://mail.google.com/mail/u/0/#drafts?compose={message_id}"
        )
        print(f"\n💡 Commander: Check your Gmail drafts folder")
        print(f"   This should preserve all HTML formatting correctly")

        return draft_id

    except HttpError as error:
        error_content = (
            error.content.decode("utf-8")
            if isinstance(error.content, bytes)
            else error.content
        )
        print(f"\n❌ Gmail API Error: {error.resp.status}")
        print(f"Details: {error_content[:500]}")
        return None
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        return None


def main():
    """Main function to create properly formatted lifecycle draft"""

    print("=== PROPER LIFECYCLE DRAFT CREATOR ===\n")

    # Create the draft
    draft_id = create_proper_lifecycle_draft()

    if draft_id:
        print(f"\n🎯 Task completed. Draft ID: {draft_id}")
        sys.exit(0)
    else:
        print(f"\n💥 Task failed. No draft created.")
        sys.exit(1)


if __name__ == "__main__":
    main()
