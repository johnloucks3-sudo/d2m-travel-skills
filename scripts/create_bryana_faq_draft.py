#!/usr/bin/env python3
"""
Create Gmail draft to Bryana Roelke with FAQ HTML attachment.
Uses d2mconcierge token. Labels THUNDERBIRD-Commander-Review.
"""

import json
import base64
import sys
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
except ImportError as e:
    print(f"ERROR: Missing Google libraries: {e}")
    sys.exit(1)

TOKEN_FILE = Path("/home/john/Thunderbird/config/persona_gmail_token.json")
FAQ_FILE   = Path("/home/john/Thunderbird/Bryana/04_Reference/01_faq.html")

TO      = "Bryana Roelke <bryanajarboe@gmail.com>"
SUBJECT = "Looking forward to our chat — a little prep for you"

BODY_HTML = """\
<html>
<body style="font-family: Georgia, serif; font-size: 15px; color: #003087; background: #f7f3ea; padding: 32px;">
<p>Bryana,</p>

<p>I'm really looking forward to talking with you.</p>

<p>Before we meet, I wanted to share something with you so our conversation can be as useful as possible.
I put together a training portal — a set of documents that cover the role, how the business runs,
the tools, the clients, and the questions most people have before they decide whether something like this
is right for them. The FAQ I've attached is a good place to start — I think you'll find it honest and direct.</p>

<p>I want to be upfront: I had significant help developing these materials using AI. That's actually part of
the story I want to tell you — the Wing, as I call it, is the AI-assisted system I built to run the back
office of this agency. What you're reading is a product of that system. It's not a gimmick; it's genuinely
how we operate.</p>

<p>That said, everything in those documents reflects how I actually think about this business and what I'm
looking for in a partner. The AI helped me write it — the thinking is mine.</p>

<p>Take a look at the attachment before we talk if you have a few minutes. Come with questions.
There are no wrong ones.</p>

<p>Talk soon,</p>

<p><strong>John</strong><br>
Dreams2Memories Travel, LLC<br>
719-291-0742</p>
</body>
</html>
"""

def main():
    # Load token
    if not TOKEN_FILE.exists():
        print(f"ERROR: Token not found at {TOKEN_FILE}")
        sys.exit(1)

    token_data = json.loads(TOKEN_FILE.read_text())
    creds = Credentials(
        token=token_data.get('token'),
        refresh_token=token_data.get('refresh_token'),
        token_uri=token_data.get('token_uri'),
        client_id=token_data.get('client_id'),
        client_secret=token_data.get('client_secret'),
        scopes=token_data.get('scopes', ['https://www.googleapis.com/auth/gmail.modify'])
    )

    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            print("Token refreshed")
        except Exception as e:
            print(f"Warning: token refresh failed: {e}")

    service = build('gmail', 'v1', credentials=creds)
    print("Gmail service ready")

    # Build multipart message
    msg = MIMEMultipart('mixed')
    msg['To']      = TO
    msg['Subject'] = SUBJECT

    # HTML body
    body_part = MIMEMultipart('alternative')
    body_part.attach(MIMEText(BODY_HTML, 'html'))
    msg.attach(body_part)

    # FAQ HTML attachment
    if not FAQ_FILE.exists():
        print(f"ERROR: FAQ file not found at {FAQ_FILE}")
        sys.exit(1)

    faq_bytes = FAQ_FILE.read_bytes()
    attachment = MIMEBase('text', 'html')
    attachment.set_payload(faq_bytes)
    encoders.encode_base64(attachment)
    attachment.add_header('Content-Disposition', 'attachment', filename='D2M_FAQ.html')
    msg.attach(attachment)

    # Encode and create draft
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    draft_body = {'message': {'raw': raw}}

    draft = service.users().drafts().create(userId='me', body=draft_body).execute()
    draft_id = draft['id']
    print(f"Draft created: {draft_id}")

    # Apply THUNDERBIRD-Commander-Review label
    # Find label ID first
    labels = service.users().labels().list(userId='me').execute().get('labels', [])
    label_id = next((l['id'] for l in labels if l['name'] == 'THUNDERBIRD-Commander-Review'), None)

    if label_id:
        msg_id = draft['message']['id']
        service.users().messages().modify(
            userId='me',
            id=msg_id,
            body={'addLabelIds': [label_id]}
        ).execute()
        print(f"Label applied: THUNDERBIRD-Commander-Review")
    else:
        print("Note: THUNDERBIRD-Commander-Review label not found — draft created without label")

    print(f"\nDraft ready for Commander review.")
    print(f"  To: {TO}")
    print(f"  Subject: {SUBJECT}")
    print(f"  Attachment: D2M_FAQ.html")

if __name__ == '__main__':
    main()
