#!/usr/bin/env python3
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from pathlib import Path
import json
import sys

# Load creds
token_path = Path("/home/john/Thunderbird/creds/johnloucks3_token.json")
with open(token_path, "r") as f:
    creds_data = json.load(f)
creds = Credentials.from_authorized_user_info(
    creds_data, ["https://www.googleapis.com/auth/gmail.compose"]
)

service = build("gmail", "v1", credentials=creds)

# MD content
with open(
    "/home/john/Thunderbird/output/Drafts_for_Client_Lifecycle_Engagement.md", "r"
) as f:
    md_content = f.read()

# Message
message = MIMEMultipart("alternative")
message["to"] = "kyle.kuklinski@gmail.com"
message["subject"] = "Drafts for Client Lifecycle Engagement"
msg_text = MIMEText(md_content, "plain")
message.attach(msg_text)

raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
draft = (
    service.users()
    .drafts()
    .create(userId="me", body={"message": {"raw": raw}})
    .execute()
)

print("Draft created: https://mail.google.com/mail/u/0/#drafts/" + draft["id"])
