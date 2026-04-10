#!/usr/bin/env python3
"""
Verify Gmail draft was actually created in Commander's account
"""

import json
from datetime import datetime
from pathlib import Path

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print("ERROR: Google libraries not installed")
    exit(1)


def verify_draft():
    print("=== GMAIL DRAFT VERIFICATION ===")

    # Load token
    token_file = Path("/home/john/Thunderbird/creds/gmail_token.json")
    if not token_file.exists():
        print("❌ Token file not found")
        return False

    with open(token_file) as f:
        token_data = json.load(f)

    print(f"Token expiry: {token_data.get('expiry')}")

    # Create credentials with proper expiry handling
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

    # Manually set expiry if it's a string
    expiry_str = token_data.get("expiry")
    if expiry_str and isinstance(expiry_str, str):
        try:
            from datetime import datetime, timezone

            expiry_dt = datetime.fromisoformat(
                expiry_str.replace("Z", "+00:00")
            ).replace(tzinfo=None)
            creds.expiry = expiry_dt
            print("✓ Converted string expiry to datetime")
        except Exception as e:
            print(f"⚠️ Could not parse expiry: {e}")

    # Refresh if expired
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            print("✓ Token refreshed")
        except Exception as e:
            print(f"⚠️ Could not refresh token: {e}")

    # Build service
    try:
        service = build("gmail", "v1", credentials=creds)
        print("✓ Gmail service built")
    except Exception as e:
        print(f"❌ Failed to build service: {e}")
        return False

    # List drafts
    try:
        drafts = service.users().drafts().list(userId="me").execute()
        draft_count = len(drafts.get("drafts", []))
        print(f"✓ Found {draft_count} drafts total")

        if draft_count > 0:
            # Get the most recent draft
            latest_draft_id = drafts["drafts"][0]["id"]
            draft_details = (
                service.users().drafts().get(userId="me", id=latest_draft_id).execute()
            )

            headers = draft_details["message"].get("payload", {}).get("headers", [])
            subject = next(
                (h["value"] for h in headers if h["name"] == "Subject"), "No subject"
            )
            to = next((h["value"] for h in headers if h["name"] == "To"), "Unknown")

            print(f"📧 Latest draft:")
            print(f"   To: {to}")
            print(f"   Subject: {subject}")

            if "Kuklinski" in subject or "Panama Canal" in subject:
                print("✅ SUCCESS: Kuklinski draft found!")
                return True
            else:
                print("⚠️  Latest draft is not Kuklinski email")

        return False

    except HttpError as e:
        print(f"❌ Gmail API error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    success = verify_draft()
    if not success:
        print("\n❌ DRAFT VERIFICATION FAILED")
        print("The script may have reported success but no draft was found")
        print("Please check your Gmail drafts folder manually")
        exit(1)
    else:
        print("\n✅ VERIFICATION SUCCESSFUL")
        print("Commander should see the draft in Gmail")
        exit(0)
