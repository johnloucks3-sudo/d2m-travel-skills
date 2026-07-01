#!/usr/bin/env python3
"""CI probe — Google Drive MX integration (client-affecting).
Efficacy check: OAuth token valid (auto-refresh attempted) + Drive API files().list() succeeds.
Uses drive_token.json from Thunderbird root.
Exit 0 = GREEN, exit 1 = RED.
"""
import sys
import json
from pathlib import Path

ID = "gdrive-mx"
TOKEN_FILE = Path.home() / "Thunderbird" / "drive_token.json"


def fail(m):
    print(f"RED {ID}: {m}")
    sys.exit(1)


def main():
    # Check token file exists
    if not TOKEN_FILE.exists():
        fail(f"drive_token.json not found at {TOKEN_FILE}")

    try:
        token_data = json.loads(TOKEN_FILE.read_text())
    except (json.JSONDecodeError, OSError) as e:
        fail(f"Cannot read drive_token.json: {e}")

    if not token_data.get("refresh_token"):
        fail("drive_token.json missing refresh_token — cannot auto-renew")

    # Attempt import of google-auth (available in .venv)
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError
    except ImportError as e:
        fail(f"google-auth/googleapiclient not available: {e}")

    # Load credentials
    try:
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE))
    except Exception as e:
        fail(f"Cannot load credentials from drive_token.json: {e}")

    # Refresh if expired or expiring
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                # Persist refreshed token
                TOKEN_FILE.write_text(creds.to_json())
            except Exception as e:
                fail(f"Token refresh failed: {e}")
        else:
            fail("Token invalid and cannot be refreshed (no refresh_token)")

    # Efficacy: actually call the Drive API
    try:
        service = build("drive", "v3", credentials=creds, cache_discovery=False)
        result = service.files().list(pageSize=1, fields="files(id,name)").execute()
        files = result.get("files", [])
        # Success even if 0 files returned — API call worked
        print(f"GREEN {ID}: Drive API reachable, token valid, list returned {len(files)} item(s)")
        sys.exit(0)
    except HttpError as e:
        fail(f"Drive API error {e.resp.status}: {e}")
    except Exception as e:
        fail(f"Drive API call failed: {e}")


if __name__ == "__main__":
    main()
