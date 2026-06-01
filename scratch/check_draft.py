#!/usr/bin/env python3
"""Simple script to check Gmail drafts"""

import os
import sys
from pathlib import Path

# Add paths for imports
thunderbird_dir = Path.home() / "Thunderbird"
sys.path.extend(
    [
        str(thunderbird_dir / "core" / "email"),
        str(thunderbird_dir / "core"),
        str(thunderbird_dir / "api"),
    ]
)

# Try to import the Gmail functions
try:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

    # Set up credentials
    token_file = thunderbird_dir / "gmail_token.json"
    if not token_file.exists():
        print(f"Token file not found: {token_file}")
        sys.exit(1)

    creds = Credentials.from_authorized_user_file(
        str(token_file), ["https://www.googleapis.com/auth/gmail.modify"]
    )

    # Build the service
    service = build("gmail", "v1", credentials=creds)

    # List drafts
    results = service.users().drafts().list(userId="me").execute()
    drafts = results.get("drafts", [])

    print(f"Found {len(drafts)} drafts")

    for draft in drafts:
        # Get full draft data
        draft_data = service.users().drafts().get(userId="me", id=draft["id"]).execute()
        message = draft_data["message"]

        headers = message.get("payload", {}).get("headers", [])
        subject = ""
        for header in headers:
            if header["name"].lower() == "subject":
                subject = header["value"]
                break

        snippet = message.get("snippet", "")

        # Check for the specific draft
        if (
            "Thuderbird WIng Open Code API COnfig" in snippet
            or "Thuderbird WIng Open Code API COnfig" in subject
        ):
            print(f"\n=== FOUND TARGET DRAFT ===")
            print(f"ID: {draft['id']}")
            print(f"Subject: {subject}")
            print(f"Snippet: {snippet}")

            # Try to get full body
            parts = message.get("payload", {}).get("parts", [])
            if parts:
                for part in parts:
                    if part.get("mimeType") == "text/plain" and "data" in part.get(
                        "body", {}
                    ):
                        body_data = part["body"]["data"]
                        import base64

                        body = base64.urlsafe_b64decode(body_data).decode("utf-8")
                        print(f"\nBody text:\n{body[:1000]}...")
                        break

            break
    else:
        print("\nTarget draft not found")

except Exception as e:
    print(f"Error: {e}")
    import traceback

    traceback.print_exc()
