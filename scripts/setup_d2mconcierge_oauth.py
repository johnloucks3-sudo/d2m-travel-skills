#!/usr/bin/env python3
"""
Setup d2mconcierge OAuth — Initialize credentials for draft creation.
Guides user through browser-based authentication and saves token to ~/.credentials/d2mconcierge.json
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

def authenticate_d2mconcierge():
    """
    Authenticate d2mconcierge@gmail.com and save credentials.
    """
    CREDS_DIR.mkdir(exist_ok=True)

    # Use Google OAuth 2.0 client credentials
    # You can create these at: https://console.cloud.google.com/apis/credentials
    # 1. Create OAuth 2.0 Client ID (Desktop application)
    # 2. Download JSON
    # 3. Place in ~/.credentials/client_secrets.json

    client_secrets_file = CREDS_DIR / "client_secrets.json"

    if not client_secrets_file.exists():
        print("ERROR: client_secrets.json not found")
        print(f"Steps to set up:")
        print(f"1. Go to https://console.cloud.google.com/apis/credentials")
        print(f"2. Create OAuth 2.0 Client ID (Desktop application)")
        print(f"3. Download as JSON")
        print(f"4. Save to {client_secrets_file}")
        sys.exit(1)

    print(f"Authenticating d2mconcierge@gmail.com...")
    print(f"A browser window will open. Sign in with the d2mconcierge Gmail account.")

    flow = InstalledAppFlow.from_client_secrets_file(
        client_secrets_file,
        SCOPES
    )

    # Run local server for OAuth callback
    creds = flow.run_local_server(port=8080)

    # Save credentials to file
    token_data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes
    }

    with open(CREDS_FILE, "w") as f:
        json.dump(token_data, f, indent=2)

    CREDS_FILE.chmod(0o600)  # Restrict to user only

    print(f"✅ SUCCESS! Credentials saved to {CREDS_FILE}")
    print(f"d2mconcierge OAuth is now ready for draft creation.")
    print(f"You can now run: python3 scripts/create_gmail_draft_direct_v3.py --html <file> --to d2mconcierge@gmail.com --subject '<subject>'")

if __name__ == "__main__":
    authenticate_d2mconcierge()
