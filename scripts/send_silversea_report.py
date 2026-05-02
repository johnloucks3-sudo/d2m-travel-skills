#!/usr/bin/env python3
"""
Silversea Spring 2027 Watch — Email Sender
Called by n8n Execute Command node. Reads HTML body from stdin, sends via Gmail API.
Uses creds/gmail_token.json (d2mconcierge@gmail.com OAuth).
"""

import json
import sys
import base64
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

TOKEN_FILE = Path("/home/john/Thunderbird/creds/gmail_token.json")
SEND_FROM = "d2mconcierge@gmail.com"
SEND_TO = "johnloucks3@gmail.com"
SUBJECT_PREFIX = "Silversea Spring 2027 Watch"


def send_html_email(subject: str, html_body: str) -> dict:
    """Send HTML email via Gmail API."""
    token_data = json.loads(TOKEN_FILE.read_text())
    creds = Credentials(
        token=token_data.get("token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri=token_data.get("token_uri"),
        client_id=token_data.get("client_id"),
        client_secret=token_data.get("client_secret"),
        scopes=token_data.get("scopes", ["https://www.googleapis.com/auth/gmail.modify"]),
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        # Persist refreshed token
        token_data["token"] = creds.token
        token_data["expiry"] = creds.expiry.isoformat() + "Z" if creds.expiry else None
        TOKEN_FILE.write_text(json.dumps(token_data))

    service = build("gmail", "v1", credentials=creds)

    msg = MIMEMultipart("alternative")
    msg["From"] = SEND_FROM
    msg["To"] = SEND_TO
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    result = service.users().messages().send(
        userId="me", body={"raw": raw}
    ).execute()
    return result


if __name__ == "__main__":
    # Read payload from JSON file (written by n8n Code node)
    if len(sys.argv) < 2:
        print("Usage: send_silversea_report.py <payload.json>", file=sys.stderr)
        sys.exit(1)

    payload_path = Path(sys.argv[1])
    if not payload_path.exists():
        print(f"ERROR: Payload file not found: {payload_path}", file=sys.stderr)
        sys.exit(1)

    payload = json.loads(payload_path.read_text())
    html = payload.get("html", "")
    subject = payload.get("subject", SUBJECT_PREFIX)

    if not html:
        print("ERROR: No HTML body in payload", file=sys.stderr)
        sys.exit(1)

    result = send_html_email(subject, html)
    print(f"SENT msgId={result.get('id', 'unknown')}")
