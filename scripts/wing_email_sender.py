#!/usr/bin/env python3
"""
Wing Email Sender — canonical direct-API send helper.
Full reference: docs/EMAIL_SEND_CANONICAL.md

Usage:
    from scripts.wing_email_sender import send_wing_email
    msg_id = send_wing_email("johnloucks3@gmail.com", "Subject", html)

    Or CLI:
    python3 scripts/wing_email_sender.py --to addr --subject "Subj" --html body.html
"""
import base64, sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

_TOKEN = Path("/home/john/Thunderbird/creds/johnloucks3_token.json")

def send_wing_email(to: str, subject: str, html_body: str, token_path: str = None) -> str:
    """Send HTML email via johnloucks3 Gmail. Returns message ID."""
    t = token_path or str(_TOKEN)
    creds = Credentials.from_authorized_user_file(t)
    service = build('gmail', 'v1', credentials=creds, cache_discovery=False)
    msg = MIMEMultipart('alternative')
    msg['To'] = to
    msg['From'] = 'johnloucks3@gmail.com'
    msg['Subject'] = subject
    msg.attach(MIMEText(html_body, 'html'))
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    result = service.users().messages().send(userId='me', body={'raw': raw}).execute()
    return result['id']

def create_wing_draft(to: str, subject: str, html_body: str, token_path: str = None) -> str:
    """Create Gmail draft (WF-17 flow for client products). Returns draft ID."""
    t = token_path or str(_TOKEN)
    creds = Credentials.from_authorized_user_file(t)
    service = build('gmail', 'v1', credentials=creds, cache_discovery=False)
    msg = MIMEMultipart('alternative')
    msg['To'] = to
    msg['From'] = 'johnloucks3@gmail.com'
    msg['Subject'] = subject
    msg.attach(MIMEText(html_body, 'html'))
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    result = service.users().drafts().create(userId='me', body={'message': {'raw': raw}}).execute()
    return result['id']

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Send wing email via johnloucks3')
    parser.add_argument('--to', default='johnloucks3@gmail.com')
    parser.add_argument('--subject', required=True)
    parser.add_argument('--html', required=True, help='Path to HTML file or inline HTML string')
    parser.add_argument('--draft', action='store_true', help='Create draft instead of sending')
    args = parser.parse_args()

    html = Path(args.html).read_text() if Path(args.html).exists() else args.html

    if args.draft:
        draft_id = create_wing_draft(args.to, args.subject, html)
        print(f"DRAFT: {draft_id}")
    else:
        msg_id = send_wing_email(args.to, args.subject, html)
        print(f"SENT: {msg_id}")
