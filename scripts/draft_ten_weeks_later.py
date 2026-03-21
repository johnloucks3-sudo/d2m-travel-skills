#!/usr/bin/env python3
"""Create Gmail draft for Ten Weeks Later email.

Reads the rendered HTML, wraps it properly for Gmail MIME multipart,
and saves as a draft in d2mconcierge@gmail.com.

From: Dani Moreau (Dreams2Memories Travel) <concierge@d2mluxury.quest>
To:   johnloucks3@gmail.com  (Commander review — swap to distribution list before send)
"""

import base64
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

ROOT = Path.home() / "Thunderbird"
TOKEN_PATH = ROOT / "gmail_token.json"
HTML_PATH  = ROOT / "output" / "validation_emails" / "D2M_TenWeeksLater_Mar2026.html"

SUBJECT   = "10 weeks ago I sent you a letter. Here\u2019s what happened."
FROM_ADDR = "Dani Moreau (Dreams2Memories Travel) <concierge@d2mluxury.quest>"
TO_ADDR   = "johnloucks3@gmail.com"   # Commander review copy

# ── Auth ──────────────────────────────────────────────────────────────────────
creds = Credentials.from_authorized_user_file(str(TOKEN_PATH))
service = build("gmail", "v1", credentials=creds)

# ── Build MIME ────────────────────────────────────────────────────────────────
html_body = HTML_PATH.read_text(encoding="utf-8")

msg = MIMEMultipart("alternative")
msg["Subject"] = SUBJECT
msg["From"]    = FROM_ADDR
msg["To"]      = TO_ADDR
msg["Reply-To"] = "johnloucks3@gmail.com"

# Plain-text fallback (stripped down)
plain = (
    "Ten weeks ago, around December 17th, I sent you a letter about a new chapter.\n\n"
    "Here is a progress report.\n\n"
    "-- Dani Moreau, Dreams2Memories Travel\n"
    "concierge@d2mluxury.quest"
)
msg.attach(MIMEText(plain, "plain", "utf-8"))
msg.attach(MIMEText(html_body, "html", "utf-8"))

# ── Create draft ──────────────────────────────────────────────────────────────
raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
draft = service.users().drafts().create(
    userId="me",
    body={"message": {"raw": raw}},
).execute()

draft_id = draft.get("id", "?")
print(f"\u2713 Gmail draft created")
print(f"  Draft ID : {draft_id}")
print(f"  Subject  : {SUBJECT}")
print(f"  To       : {TO_ADDR}")
print(f"  From     : {FROM_ADDR}")
print(f"  HTML size: {len(html_body):,} chars")
