#!/usr/bin/env python3
"""
Calendar OAuth — console-based flow.
User opens the URL in Chrome, grants access, copies the redirect URL back.
"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.scheduling.thunderbird_calendar_sync import (
    OAUTH_CREDENTIALS_FILE, CALENDAR_TOKEN_FILE, CALENDAR_SCOPES
)
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def main():
    if CALENDAR_TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(CALENDAR_TOKEN_FILE), CALENDAR_SCOPES)
        if creds and creds.valid:
            logger.info("Calendar token already exists and is valid.")
            return True
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing expired token...")
            creds.refresh(Request())
            CALENDAR_TOKEN_FILE.write_text(creds.to_json())
            logger.info("Refreshed and saved.")
            return True

    if not OAUTH_CREDENTIALS_FILE.exists():
        logger.error(f"OAuth credentials not found: {OAUTH_CREDENTIALS_FILE}")
        return False

    flow = InstalledAppFlow.from_client_secrets_file(
        str(OAUTH_CREDENTIALS_FILE), CALENDAR_SCOPES,
        redirect_uri="urn:ietf:wg:oauth:2.0:oob"
    )

    auth_url, _ = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )

    print("\n" + "=" * 70)
    print("  GOOGLE CALENDAR OAUTH — CONSOLE FLOW")
    print("=" * 70)
    print()
    print("  1. Open this URL in your Chrome browser:")
    print()
    print(f"  {auth_url}")
    print()
    print("  2. Sign in as johnloucks3@gmail.com")
    print()
    print("  3. Click 'Continue' to grant Calendar access")
    print()
    print("  4. After granting access, Google will show")
    print("     an error page (\"This site can't be reached\")")
    print()
    print("  5. COPY THE ENTIRE URL from Chrome's address bar")
    print("     and paste it here:")
    print()
    print("=" * 70)
    print()

    try:
        response_url = input("Paste the redirect URL here: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nAborted.")
        return False

    if not response_url:
        logger.error("No URL provided.")
        return False

    logger.info("Exchanging authorization code for token...")
    flow.fetch_token(authorization_response=response_url)

    if flow.credentials:
        CALENDAR_TOKEN_FILE.write_text(flow.credentials.to_json())
        logger.info(f"Calendar OAuth token saved to {CALENDAR_TOKEN_FILE}")
        return True
    else:
        logger.error("Failed to obtain credentials.")
        return False

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
