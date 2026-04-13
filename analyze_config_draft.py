#!/usr/bin/env python3
"""Get full draft content and extract config/wrapper code"""

import os
import sys
import base64
import re
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

    # Get the specific draft
    draft_id = "r3134777537703911806"
    draft_data = service.users().drafts().get(userId="me", id=draft_id).execute()
    message = draft_data["message"]

    # Extract full body
    def extract_full_body(part):
        text = ""
        if part.get("mimeType") == "text/plain" and "data" in part.get("body", {}):
            try:
                body_data = part["body"]["data"]
                text = base64.urlsafe_b64decode(body_data).decode(
                    "utf-8", errors="ignore"
                )
            except:
                pass
        elif part.get("mimeType") == "text/html" and "data" in part.get("body", {}):
            try:
                body_data = part["body"]["data"]
                html = base64.urlsafe_b64decode(body_data).decode(
                    "utf-8", errors="ignore"
                )
                # Extract text from HTML (simple approach)
                text = re.sub("<[^<]+?>", "", html)
                text = re.sub("\n\s*\n", "\n", text)
            except:
                pass
        elif part.get("parts"):
            for subpart in part.get("parts", []):
                text += extract_full_body(subpart)
        return text

    payload = message.get("payload", {})
    full_body = extract_full_body(payload)

    # Save to file for analysis
    output_file = thunderbird_dir / "opencode_api_config_draft.txt"
    with open(output_file, "w") as f:
        f.write(full_body)

    print(f"Full draft saved to: {output_file}")
    print(f"Content length: {len(full_body)} chars")

    # Extract code blocks
    json_match = re.search(
        r'\{[^{}]*"providers"[^{}]*\{[^{}]*\}[^{}]*\}', full_body, re.DOTALL
    )
    python_match = re.search(
        r'"""[\s\S]*?"""[\s\S]*?(def ask_claude[\s\S]*?)$', full_body, re.MULTILINE
    )

    if json_match:
        json_config = json_match.group(0)
        print("\n=== JSON CONFIG FOUND ===")
        print(json_config[:500] + "...")

    if python_match:
        python_code = python_match.group(0)
        print("\n=== PYTHON WRAPPER FOUND ===")
        print(python_code[:1000] + "...")

except Exception as e:
    print(f"Error: {e}")
    import traceback

    traceback.print_exc()
