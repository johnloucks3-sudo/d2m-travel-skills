#!/usr/bin/env python3
"""
Calendar OAuth — two-step tool.
Step 1: --url  → generates and prints the authorization URL (saves state to temp file)
Step 2: --code <redirect_url> → exchanges the auth code using saved state
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

OAUTH_CREDENTIALS_FILE = Path.home() / "Thunderbird" / "gmail_oauth_credentials.json"
CALENDAR_TOKEN_FILE = Path.home() / "Thunderbird" / "calendar_token.json"
CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar"]
STATE_FILE = Path(tempfile.gettempdir()) / "calendar_oauth_state.json"

from google_auth_oauthlib.flow import InstalledAppFlow


def cmd_url():
    """Generate auth URL and save flow state."""
    flow = InstalledAppFlow.from_client_secrets_file(
        str(OAUTH_CREDENTIALS_FILE), CALENDAR_SCOPES,
        redirect_uri="http://localhost:9999/"
    )

    auth_url, _ = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )

    # Save the flow's PKCE code_verifier and client config.
    # NOTE: google-auth-oauthlib stores the generated verifier on flow.code_verifier
    # (the Flow attribute), NOT on flow.oauth2session._client.code_verifier — the latter
    # is None at this point, which silently poisoned prior state files (verifier lost,
    # token exchange then impossible). Read flow.code_verifier with a defensive fallback.
    code_verifier = getattr(flow, "code_verifier", None) or getattr(
        flow.oauth2session._client, "code_verifier", None
    )
    if not code_verifier:
        print("ERROR: no PKCE code_verifier captured — aborting to avoid a poisoned state file.")
        return 1
    state = {
        "code_verifier": code_verifier,
        "client_config": flow.client_config,
        "redirect_uri": "http://localhost:9999/",
    }
    STATE_FILE.write_text(json.dumps(state))

    print(auth_url)
    return 0


def cmd_code(redirect_url):
    """Exchange auth code for token using saved state."""
    if not STATE_FILE.exists():
        print("No saved state. Run --url first.")
        return 1

    state = json.loads(STATE_FILE.read_text())

    # Recreate flow with saved state
    flow = InstalledAppFlow.from_client_secrets_file(
        str(OAUTH_CREDENTIALS_FILE), CALENDAR_SCOPES,
        redirect_uri=state["redirect_uri"]
    )

    # Restore code_verifier. InstalledAppFlow.fetch_token passes self.code_verifier
    # (the Flow attribute) to the token request, so restore it there — setting only the
    # oauth2session client attribute is not enough.
    flow.code_verifier = state["code_verifier"]
    flow.oauth2session._client.code_verifier = state["code_verifier"]

    # Exchange
    auth_response = redirect_url.replace("http://", "https://")
    flow.fetch_token(authorization_response=auth_response)

    if flow.credentials:
        CALENDAR_TOKEN_FILE.write_text(flow.credentials.to_json())
        print(f"Token saved to {CALENDAR_TOKEN_FILE}")
        print(f"Expiry: {flow.credentials.expiry}")
        print(f"Refresh token: {'✅' if flow.credentials.refresh_token else '❌'}")
        STATE_FILE.unlink(missing_ok=True)
        return 0
    else:
        print("Failed to get credentials.")
        return 1


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print(f"  {sys.argv[0]} --url           # Generate auth URL")
        print(f"  {sys.argv[0]} --code <URL>     # Exchange code for token")
        return 1

    cmd = sys.argv[1]

    if cmd == "--url":
        # Check if token already exists
        if CALENDAR_TOKEN_FILE.exists():
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            creds = Credentials.from_authorized_user_file(str(CALENDAR_TOKEN_FILE), CALENDAR_SCOPES)
            if creds and creds.valid:
                print("Token already valid.")
                return 0
            if creds and creds.expired and creds.refresh_token:
                print("Refreshing...")
                creds.refresh(Request())
                CALENDAR_TOKEN_FILE.write_text(creds.to_json())
                print("Refreshed.")
                return 0
        return cmd_url()

    elif cmd == "--code" and len(sys.argv) >= 3:
        return cmd_code(sys.argv[2])

    else:
        print("Unknown command.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
