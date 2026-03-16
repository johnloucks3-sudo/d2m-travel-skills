#!/usr/bin/env python3
"""Create Gmail HTML drafts for the 3 Dani validation emails."""
import base64
import json
from pathlib import Path
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Load OAuth credentials
token_path = Path.home() / "Thunderbird/token.json"
creds_data = json.loads(token_path.read_text())
creds = Credentials.from_authorized_user_info(creds_data)
service = build('gmail', 'v1', credentials=creds)

output_dir = Path.home() / "Thunderbird/output/validation_emails"

emails = [
    {
        "file": "Furlow_Validation_Mar2026.html",
        "to": "john.furlow@tpf.org",
        "cc": "missy.furlow@gmail.com",
        "subject": "Your Scandinavia Voyage — Quick Review Before Final Payment",
    },
    {
        "file": "Ely_Validation_Mar2026.html",
        "to": "al.ely58@gmail.com",
        "cc": "amy.darrow@me.com",
        "subject": "Your Scandinavia Voyage — Quick Review Before Final Payment",
    },
    {
        "file": "Nichols_Validation_Mar2026.html",
        "to": "larry.nichols4811@gmail.com",
        "cc": "heidi.nichols1@yahoo.com",
        "subject": "Your Scandinavia Voyage — Quick Review Before Final Payment",
    },
]

for email in emails:
    html_content = (output_dir / email["file"]).read_text(encoding="utf-8")

    msg = MIMEText(html_content, "html")
    msg["to"] = email["to"]
    msg["cc"] = email["cc"]
    msg["subject"] = email["subject"]
    msg["from"] = "johnloucks3@gmail.com"

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    draft = service.users().drafts().create(
        userId="me",
        body={"message": {"raw": raw}}
    ).execute()

    print(f"✓ {email['file'].replace('_Validation_Mar2026.html', '')}: Draft ID {draft['id']}")
    print(f"  → To: {email['to']} (CC: {email['cc']})")

print("\nAll 3 HTML drafts created in Gmail.")
