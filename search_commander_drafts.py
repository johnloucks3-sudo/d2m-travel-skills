#!/usr/bin/env python3
"""Search commander Gmail drafts"""

import os
import sys
import base64
from pathlib import Path

thunderbird_dir = Path.home() / "Thunderbird"

try:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    # Use commander token file
    token_file = thunderbird_dir / "gmail_token_commander.json"
    if not token_file.exists():
        print(f"Commander token file not found: {token_file}")
        sys.exit(1)

    creds = Credentials.from_authorized_user_file(
        str(token_file), ["https://www.googleapis.com/auth/gmail.modify"]
    )

    service = build("gmail", "v1", credentials=creds)

    results = service.users().drafts().list(userId="me").execute()
    drafts = results.get("drafts", [])

    print(f"Found {len(drafts)} drafts in commander account")

    for draft in drafts[:20]:  # Check first 20
        draft_data = service.users().drafts().get(userId="me", id=draft["id"]).execute()
        message = draft_data["message"]

        headers = message.get("payload", {}).get("headers", [])
        subject = ""
        for header in headers:
            if header["name"].lower() == "subject":
                subject = header["value"]
                break

        snippet = message.get("snippet", "")

        # Look for OpenCode/API config
        if (
            "opencode" in snippet.lower()
            or "opencode" in subject.lower()
            or "api config" in snippet.lower()
        ):
            print(f"\n=== FOUND === ")
            print(f"ID: {draft['id']}")
            print(f"Subject: {subject}")
            print(f"Snippet: {snippet}")

            # Get body
            payload = message.get("payload", {})
            body = []

            def extract_body(part, body_list):
                if part.get("mimeType") == "text/plain" and "data" in part.get(
                    "body", {}
                ):
                    body_data = part["body"]["data"]
                    body_list.append(
                        base64.urlsafe_b64decode(body_data).decode(
                            "utf-8", errors="ignore"
                        )
                    )
                elif part.get("parts"):
                    for subpart in part["parts"]:
                        extract_body(subpart, body_list)

            if "parts" in payload:
                for part in payload["parts"]:
                    extract_body(part)
            elif "body" in payload and "data" in payload["body"]:
                body_data = payload["body"]["data"]
                body = base64.urlsafe_b64decode(body_data).decode(
                    "utf-8", errors="ignore"
                )

            if body:
                print(f"\nBody (first 2000 chars):\n{body[:2000]}...")

            break
    else:
        print("\nNo OpenCode/API config drafts found in first 20")

except Exception as e:
    print(f"Error: {e}")
    import traceback

    traceback.print_exc()
