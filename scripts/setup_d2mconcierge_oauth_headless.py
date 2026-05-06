#!/usr/bin/env python3
"""
Headless OAuth Setup for d2mconcierge
Works in environments without browser/display.
User opens auth URL manually, provides code back to script.
"""

import os
import json
import sys
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
CREDS_DIR = Path.home() / ".credentials"
CREDS_FILE = CREDS_DIR / "d2mconcierge.json"
CLIENT_SECRETS_FILE = CREDS_DIR / "client_secrets.json"

def authenticate_d2mconcierge_headless():
    """
    Headless OAuth authentication for d2mconcierge.
    User opens auth URL manually and provides auth code.
    """
    CREDS_DIR.mkdir(exist_ok=True)

    if not CLIENT_SECRETS_FILE.exists():
        print("ERROR: client_secrets.json not found")
        print(f"Expected location: {CLIENT_SECRETS_FILE}")
        sys.exit(1)

    print("\n" + "="*70)
    print("d2mconcierge OAuth Setup (Headless Mode)")
    print("="*70)
    print("\nSteps:")
    print("1. A URL will be printed below")
    print("2. Open it in your browser on ANOTHER machine")
    print("3. Sign in with d2mconcierge@gmail.com")
    print("4. Click 'Allow'")
    print("5. Copy the authorization code from the page")
    print("6. Paste it back here")
    print("\n" + "="*70 + "\n")

    flow = InstalledAppFlow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        SCOPES
    )

    # Generate auth URL (no browser)
    auth_url, state = flow.authorization_url(prompt='consent')

    print(f"📱 OPEN THIS URL IN YOUR BROWSER:\n")
    print(f"{auth_url}\n")
    print("="*70)
    print("\nAfter signing in and clicking 'Allow', you'll see an authorization code.")
    print("Copy it and paste below:\n")

    auth_code = input("Enter authorization code: ").strip()

    if not auth_code:
        print("ERROR: No authorization code provided")
        sys.exit(1)

    # Exchange code for tokens
    try:
        creds = flow.fetch_token(code=auth_code)
    except Exception as e:
        print(f"ERROR: Failed to exchange authorization code: {e}")
        sys.exit(1)

    # Save credentials
    token_data = {
        "token": creds.get("access_token"),
        "refresh_token": creds.get("refresh_token"),
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": creds.get("client_id"),
        "client_secret": creds.get("client_secret"),
        "scopes": SCOPES
    }

    with open(CREDS_FILE, "w") as f:
        json.dump(token_data, f, indent=2)

    CREDS_FILE.chmod(0o600)

    print("\n" + "="*70)
    print("✅ SUCCESS!")
    print("="*70)
    print(f"Credentials saved to: {CREDS_FILE}")
    print("\nYou can now create drafts with:")
    print(f"  python3 /home/john/Thunderbird/scripts/create_gmail_draft_direct_v3.py \\")
    print(f"    --html <file> --to johnloucks3@gmail.com --subject '[DRAFT] Title'")
    print("="*70 + "\n")

if __name__ == "__main__":
    authenticate_d2mconcierge_headless()
