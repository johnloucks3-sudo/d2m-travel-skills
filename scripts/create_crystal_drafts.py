#!/usr/bin/env python3
"""Create both Crystal Cruises draft emails for Commander review."""

import json, base64, sys
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

TOKEN_FILE = Path("/home/john/Thunderbird/config/persona_gmail_token.json")
FROM_EMAIL = "d2mconcierge@gmail.com"
TO_EMAIL = "johnloucks3@gmail.com"

def get_service():
    with open(TOKEN_FILE) as f:
        td = json.load(f)
    creds = Credentials(
        token=td.get('token'),
        refresh_token=td.get('refresh_token'),
        token_uri=td.get('token_uri'),
        client_id=td.get('client_id'),
        client_secret=td.get('client_secret'),
        scopes=td.get('scopes', ['https://www.googleapis.com/auth/gmail.modify'])
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build('gmail', 'v1', credentials=creds)

def create_draft(service, html_path, subject):
    with open(html_path) as f:
        html_body = f.read()

    msg = MIMEMultipart('alternative')
    msg['to'] = TO_EMAIL
    msg['from'] = FROM_EMAIL
    msg['subject'] = subject
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    draft = service.users().drafts().create(
        userId='me', body={'message': {'raw': raw}}
    ).execute()

    print(f"  ✅ Draft created: {draft['id']} — \"{subject}\"")
    return draft

def main():
    service = get_service()
    print("Connected to Gmail.\n")

    create_draft(service,
        "/home/john/Thunderbird/output/crystal_v1_internal.html",
        "Crystal Cruises — Full-Spectrum Scan (Internal Wing)")
    create_draft(service,
        "/home/john/Thunderbird/output/crystal_v2_pro_bono.html",
        "Crystal Cruises — Company Profile & Market Analysis (Service Version)")

    print("\nBoth drafts created in d2mconcierge Gmail with THUNDERBIRD-Commander-Review label.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
