#!/usr/bin/env python3
"""
Create Bryana onboarding Gmail draft from pre-processed HTML.
Commander adds recipient in Gmail review.
"""

import json, base64, sys
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

ROOT = Path("/home/john/Thunderbird")

html = (ROOT / "drafts/bryana_onboarding_gmailsafe.html").read_text(encoding="utf-8")

SUBJECT = "Access to training materials + Dani (compromise reached)"

# Build message — Commander will add recipient when reviewing
message = MIMEMultipart('alternative')
message['to'] = ''
message['from'] = 'd2mconcierge@gmail.com'
message['subject'] = SUBJECT

msg_html = MIMEText(html, 'html', 'utf-8')
message.attach(msg_html)

raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

# Load token
token_file = ROOT / "config/persona_gmail_token.json"
with open(token_file) as f:
    token_data = json.load(f)

creds = Credentials(
    token=token_data.get('token'),
    refresh_token=token_data.get('refresh_token'),
    token_uri=token_data.get('token_uri'),
    client_id=token_data.get('client_id'),
    client_secret=token_data.get('client_secret'),
    scopes=token_data.get('scopes', ['https://www.googleapis.com/auth/gmail.modify'])
)

if creds.expired and creds.refresh_token:
    creds.refresh(Request())

service = build('gmail', 'v1', credentials=creds)

draft_body = {'message': {'raw': raw}}

draft = service.users().drafts().create(userId='me', body=draft_body).execute()
print(f"Draft ID: {draft.get('id')}")
print(f"Subject: {SUBJECT}")
print(f"Label: THUNDERBIRD-Commander-Review (auto-applied)")
print(f"\nOpen in Gmail to add recipient:")
print(f"https://mail.google.com/mail/u/0/#drafts")
