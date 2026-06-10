#!/usr/bin/env python3
"""Create Bryana clarification Gmail draft — disregard first email."""

import json, base64
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

ROOT = Path("/home/john/Thunderbird")
html = (ROOT / "drafts/bryana_clarification_gmailsafe.html").read_text(encoding="utf-8")

SUBJECT = "One quick correction — please use the second email"

message = MIMEMultipart('alternative')
message['to'] = ''
message['from'] = 'd2mconcierge@gmail.com'
message['subject'] = SUBJECT

message.attach(MIMEText(html, 'html', 'utf-8'))
raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

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
draft = service.users().drafts().create(userId='me', body={'message': {'raw': raw}}).execute()
print(f"Draft ID: {draft.get('id')}")
print(f"Subject: {SUBJECT}")
print(f"Open in Gmail, add Bryana's address, then send:")
print(f"https://mail.google.com/mail/u/0/#drafts")
