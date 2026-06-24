#!/usr/bin/env python3
"""
Stage Amy Darrow insurance follow-up to johnloucks3 Gmail drafts.
Uses OAuth credentials stored locally.
"""

import json
import base64
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

def load_johnloucks3_token():
    """Load and refresh the johnloucks3 Gmail OAuth token."""
    token_path = Path("/home/john/Thunderbird/gmail_token_johnloucks3_backup.json")

    if not token_path.exists():
        raise FileNotFoundError(f"johnloucks3 Gmail token not found at {token_path}")

    token_data = json.loads(token_path.read_text())

    # Create credentials from the token data
    creds = Credentials.from_authorized_user_info(token_data)

    # Refresh if expired
    if not creds.valid:
        creds.refresh(Request())
        # Save the refreshed token back
        token_path.write_text(json.dumps(creds.to_json(), indent=2))

    return creds

def create_draft(service, to_addr, subject, body_html):
    """Create a draft in Gmail."""
    message = MIMEMultipart('alternative')
    message['To'] = to_addr
    message['Subject'] = subject

    # Add plain text and HTML parts
    text_part = MIMEText(body_html.replace("<br>", "\n").replace("<p>", "").replace("</p>", "\n"), 'plain')
    html_part = MIMEText(body_html, 'html')
    message.attach(text_part)
    message.attach(html_part)

    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

    try:
        draft = service.users().drafts().create(
            userId='me',
            body={'message': {'raw': raw_message}}
        ).execute()
        return draft
    except Exception as e:
        print(f"Error creating draft: {e}")
        raise

def main():
    # Amy Darrow email content
    to_addr = "amy.darrow@me.com"
    subject = "Insurance for Your August Voyage — Quick Update Needed"

    body_html = """<html><body>
<p>Dear Amy,</p>

<p>I wanted to circle back on your travel insurance for the Grandeur in late August. We shared three solid options with you earlier this week, and I'm reaching out because we're at the 30-day window where your coverage needs to be finalized and locked in on your itinerary.</p>

<p>Here's what matters: if you've already purchased one of the plans we recommended, please send me the policy details and confirmation number. If you haven't yet, this is the time to do it—the 60-day waiting period on pre-existing conditions starts the moment you buy, and you need it cleared before August 25th.</p>

<p>The three options we discussed:</p>
<ul>
<li><strong>Seven Corners Annual:</strong> Solid all-around coverage, good for frequent travelers</li>
<li><strong>BCBS Multi-Trip Platinum:</strong> Strong medical and evacuation coverage</li>
<li><strong>IMG Patriot:</strong> Comprehensive with high limits</li>
</ul>

<p>Once you confirm coverage, I'll add it to the itinerary we'll send you about a month before departure.</p>

<p>Let me know what you've got or if you need me to walk through the options again.</p>

<p>Thanks,<br>
John<br>
Dreams2Memories Travel, LLC<br>
719-291-0742<br>
johnloucks3@gmail.com</p>
</body></html>"""

    # Load credentials and build service
    creds = load_johnloucks3_token()
    service = build('gmail', 'v1', credentials=creds)

    # Create the draft
    draft = create_draft(service, to_addr, subject, body_html)
    print(f"✅ Draft created successfully: {draft['id']}")
    print(f"   To: {to_addr}")
    print(f"   Subject: {subject}")
    print(f"   Location: Gmail drafts folder")

if __name__ == "__main__":
    main()
