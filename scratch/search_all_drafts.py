#!/usr/bin/env python3
"""Search all drafts for OpenCode config info"""

import os
import sys
import re
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

try:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

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

    # Search patterns
    patterns = [
        "Thuderbird",
        "Thunderbird",
        "Open Code",
        "OpenCode",
        "API Config",
        "API Config",
        "wing",
        "Wing",
    ]

    matches = []

    for draft in drafts[:30]:  # Limit to first 30 drafts for speed
        draft_data = service.users().drafts().get(userId="me", id=draft["id"]).execute()
        message = draft_data["message"]

        headers = message.get("payload", {}).get("headers", [])
        subject = ""
        for header in headers:
            if header["name"].lower() == "subject":
                subject = header["value"]
                break

        snippet = message.get("snippet", "")

        # Check for any match
        for pattern in patterns:
            if pattern.lower() in subject.lower() or pattern.lower() in snippet.lower():
                matches.append((draft["id"], subject, snippet))
                break

    if matches:
        print(f"\nFound {len(matches)} matching drafts:")
        for draft_id, subject, snippet in matches[:10]:  # Show first 10
            print(f"\n---")
            print(f"ID: {draft_id}")
            print(f"Subject: {subject}")
            print(f"Snippet: {snippet[:200]}...")

            # Get some body content
            draft_data = (
                service.users().drafts().get(userId="me", id=draft_id).execute()
            )
            message = draft_data["message"]
            parts = message.get("payload", {}).get("parts", [])
            if parts:
                for part in parts:
                    if part.get("mimeType") == "text/plain" and "data" in part.get(
                        "body", {}
                    ):
                        body_data = part["body"]["data"]
                        import base64

                        body = base64.urlsafe_b64decode(body_data).decode("utf-8")
                        print(f"\nBody preview:\n{body[:500]}...")
                        break
    else:
        print("\nNo drafts found with search patterns")

except Exception as e:
    print(f"Error: {e}")
    import traceback

    traceback.print_exc()
