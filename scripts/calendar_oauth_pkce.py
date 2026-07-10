#!/usr/bin/env python3
"""
Calendar OAuth — PKCE-safe console flow.
Creates the flow, generates URL, user authorizes in Chrome,
pastes the redirect URL back, same flow object exchanges the code.
"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def main():
    OAUTH_CREDENTIALS_FILE = Path.home() / "Thunderbird" / "gmail_oauth_credentials.json"
    CALENDAR_TOKEN_FILE = Path.home() / "Thunderbird" / "calendar_token.json"
    CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar"]

    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    if CALENDAR_TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(CALENDAR_TOKEN_FILE), CALENDAR_SCOPES)
        if creds and creds.valid:
            print("Calendar token already exists and is valid.")
            return True
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired token...")
            creds.refresh(Request())
            CALENDAR_TOKEN_FILE.write_text(creds.to_json())
            print("Refreshed and saved.")
            return True

    from google_auth_oauthlib.flow import InstalledAppFlow

    flow = InstalledAppFlow.from_client_secrets_file(
        str(OAUTH_CREDENTIALS_FILE), CALENDAR_SCOPES,
        redirect_uri="http://localhost:9999/"
    )

    auth_url, _ = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )

    print("\n" + "=" * 70)
    print("  GOOGLE CALENDAR OAUTH — COPY REDIRECT URL")
    print("=" * 70)
    print()
    print("  1. COPY this entire URL:")
    print()
    print(f"  {auth_url}")
    print()
    print("  2. Open Chrome and PASTE it in the address bar")
    print()
    print("  3. Sign in as johnloucks3@gmail.com if needed")
    print()
    print("  4. Click 'Continue' to grant Calendar access")
    print()
    print("  5. Chrome will show 'This site can't be reached'")
    print("     (because localhost:9999 doesn't exist)")
    print()
    print("  6. COPY THE ENTIRE URL from Chrome's address bar")
    print()
    print("  7. PASTE it below and press Enter:")
    print("=" * 70)
    print()

    try:
        response_url = input("Paste redirect URL: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nAborted.")
        return False

    if not response_url:
        print("No URL provided.")
        return False

    # OAuth library requires https — swap it
    auth_response = response_url.replace("http://", "https://")

    print("Exchanging code for token...")
    flow.fetch_token(authorization_response=auth_response)

    if flow.credentials:
        CALENDAR_TOKEN_FILE.write_text(flow.credentials.to_json())
        print(f"Token saved to {CALENDAR_TOKEN_FILE}")
        print(f"Expiry: {flow.credentials.expiry}")
        print(f"Refresh token: {'✅' if flow.credentials.refresh_token else '❌'}")
        return True
    else:
        print("Failed to obtain credentials.")
        return False

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
