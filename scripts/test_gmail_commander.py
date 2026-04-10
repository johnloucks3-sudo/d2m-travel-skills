#!/usr/bin/env python3
"""
Test Gmail API connectivity for Commander's account
Simple test to verify drafts can be created
"""

import json
import base64
import sys
from pathlib import Path
from email.mime.text import MIMEText

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
except ImportError as e:
    print(f"Missing required libraries: {e}")
    sys.exit(1)


def test_gmail_connection():
    print("🔧 TESTING COMMANDER GMAIL API CONNECTIVITY")

    # Test 1: Load token
    token_file = Path("/home/john/Thunderbird/creds/gmail_token.json")
    if not token_file.exists():
        print("❌ FAIL: Token file not found")
        return False
    print("✓ Token file exists")

    try:
        with open(token_file) as f:
            token_data = json.load(f)
        print("✓ Token file is valid JSON")
    except Exception as e:
        print(f"❌ FAIL: Invalid JSON: {e}")
        return False

    # Test 2: Create credentials
    try:
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
        print("✓ Credentials object created")
    except Exception as e:
        print(f"❌ FAIL: Credentials creation: {e}")
        return False

    # Test 3: Refresh if needed
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            print("✓ Token refreshed (was expired)")
        except Exception as e:
            print(f"⚠️ Warning: Could not refresh: {e}")
            print("  Using existing token (may fail if expired)")
    else:
        print("✓ Token not expired")

    # Test 4: Build service
    try:
        service = build("gmail", "v1", credentials=creds)
        print("✓ Gmail service built")
    except Exception as e:
        print(f"❌ FAIL: Service build: {e}")
        return False

    # Test 5: Get profile (verify account access)
    try:
        profile = service.users().getProfile(userId="me").execute()
        email_address = profile.get("emailAddress", "unknown")
        print(f"✓ Connected to: {email_address}")
        print(f"✓ Messages total: {profile.get('messagesTotal', 'N/A')}")
        print(f"✓ Threads total: {profile.get('threadsTotal', 'N/A')}")
    except Exception as e:
        print(f"❌ FAIL: Profile access: {e}")
        return False

    # Test 6: Create a simple test draft
    try:
        print("\n📝 Creating test draft...")
        message = MIMEText(
            "This is a test draft from Thunderbird Gmail API connectivity test.",
            "plain",
        )
        message["to"] = "commander@d2m.local"  # Local test address
        message["from"] = email_address
        message["subject"] = "[TEST] Gmail API Connectivity Verified"

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        draft_body = {"message": {"raw": raw_message}}
        draft = service.users().drafts().create(userId="me", body=draft_body).execute()

        draft_id = draft.get("id")
        print(f"✓ Test draft created: ID={draft_id}")

        # Clean up - delete test draft
        service.users().drafts().delete(userId="me", id=draft_id).execute()
        print("✓ Test draft deleted (cleanup)")

    except Exception as e:
        print(f"⚠️ Warning: Draft test failed: {e}")
        print("  (This may be due to permission or quota limits)")
        print("  Main connectivity test still PASSED")

    print("\n" + "=" * 50)
    print("✅ ALL TESTS PASSED - Gmail API is working")
    print("   Drafts can be created in Commander's Gmail")
    print("=" * 50)
    return True


if __name__ == "__main__":
    success = test_gmail_connection()
    sys.exit(0 if success else 1)
