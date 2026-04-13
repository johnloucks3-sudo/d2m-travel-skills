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

    for draft in drafts[:30]:  # Check first 30
        draft_data = service.users().drafts().get(userId="me", id=draft["id"]).execute()
        message = draft_data["message"]

        headers = message.get("payload", {}).get("headers", [])
        subject = ""
        for header in headers:
            if header["name"].lower() == "subject":
                subject = header["value"]
                break

        snippet = message.get("snippet", "").lower()
        subject_lower = subject.lower()

        # Look for various spellings
        search_terms = [
            "thuderbird",
            "thunderbird",
            "opencode",
            "open code",
            "api config",
            "wing",
        ]
        found = False
        for term in search_terms:
            if term in snippet or term in subject_lower:
                found = True
                break

        if found:
            print(f"\n=== FOUND === ")
            print(f"ID: {draft['id']}")
            print(f"Subject: {subject}")
            print(f"Snippet: {snippet}")

            # Get body - simple approach
            payload = message.get("payload", {})
            body_text = ""

            # Helper function
            def get_body_from_part(part):
                body = ""
                if part.get("mimeType") == "text/plain" and "data" in part.get(
                    "body", {}
                ):
                    try:
                        body_data = part["body"]["data"]
                        body = base64.urlsafe_b64decode(body_data).decode(
                            "utf-8", errors="ignore"
                        )
                    except:
                        pass
                elif part.get("parts"):
                    for subpart in part.get("parts", []):
                        body += get_body_from_part(subpart)
                return body

            if "parts" in payload:
                for part in payload["parts"]:
                    body_text += get_body_from_part(part)
            elif "body" in payload and "data" in payload["body"]:
                try:
                    body_data = payload["body"]["data"]
                    body_text = base64.urlsafe_b64decode(body_data).decode(
                        "utf-8", errors="ignore"
                    )
                except:
                    pass

            if body_text:
                print(f"\nBody (first 3000 chars):\n{body_text[:3000]}...")

            break
    else:
        print("\nNo matching drafts found in first 30")

except Exception as e:
    print(f"Error: {e}")
    import traceback

    traceback.print_exc()
