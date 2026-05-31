#!/usr/bin/env python3
"""
Create Kuklinski flights draft — Viking Mars Panama Canal flight options email.
Uses persona_gmail_token.json (d2mconcierge).
WF-17: Creates draft only — does NOT send.
"""

import os
import sys
import json
import base64
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Add creds path
TOKEN_PATH = Path('/home/john/Thunderbird/config/persona_gmail_token.json')
HTML_PATH = Path('/home/john/Thunderbird/drafts/kuklinski_flights_20260530.html')

def main():
    # Verify dependencies
    if not TOKEN_PATH.exists():
        print(f"ERROR: Token not found at {TOKEN_PATH}")
        sys.exit(1)

    if not HTML_PATH.exists():
        print(f"ERROR: HTML not found at {HTML_PATH}")
        sys.exit(1)

    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError
    except ImportError:
        print("ERROR: google-auth libraries not installed. Run: pip install google-auth google-auth-oauthlib google-api-python-client")
        sys.exit(1)

    # Load token
    with open(TOKEN_PATH) as f:
        token_data = json.load(f)

    creds = Credentials(
        token=token_data.get('token'),
        refresh_token=token_data.get('refresh_token'),
        token_uri=token_data.get('token_uri'),
        client_id=token_data.get('client_id'),
        client_secret=token_data.get('client_secret'),
        scopes=token_data.get('scopes'),
    )

    # Refresh if expired
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        # Write back refreshed token
        token_data['token'] = creds.token
        with open(TOKEN_PATH, 'w') as f:
            json.dump(token_data, f, indent=2)
        print("Token refreshed and saved.")

    # Build Gmail service
    service = build('gmail', 'v1', credentials=creds)
    print("Gmail service connected — account: d2mconcierge@gmail.com")

    # Load HTML
    html_content = HTML_PATH.read_text()
    print(f"HTML loaded: {len(html_content)} chars")

    # Build MIME message (multipart/alternative for HTML)
    msg = MIMEMultipart('alternative')
    msg['To'] = 'kyle.kuklinski@gmail.com'
    msg['From'] = 'concierge@d2mluxury.quest'
    msg['Subject'] = 'Viking Mars — December Flights: Options & Your Call'

    # Plain text fallback
    plain = (
        "Kyle,\n\n"
        "Flights for Panama City are the next gap to close. This email covers fare data, "
        "my Dec 16 vs Dec 17 recommendation, and two questions I need your call on before "
        "I can lock in pricing for Kyle & Rosalie and Roger & Nick.\n\n"
        "Please view this email in an HTML-capable client for the full breakdown.\n\n"
        "Dani Moreau\n"
        "D2M Luxury Travel Concierge\n"
        "Dreams2Memories Travel, LLC\n"
        "concierge@d2mluxury.quest"
    )

    msg.attach(MIMEText(plain, 'plain'))
    msg.attach(MIMEText(html_content, 'html'))

    # Encode
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    draft_body = {'message': {'raw': raw}}

    try:
        draft = service.users().drafts().create(userId='me', body=draft_body).execute()
        draft_id = draft['id']
        print()
        print("=" * 60)
        print("DRAFT CREATED — WF-17 HOLD")
        print("=" * 60)
        print(f"Draft ID:  {draft_id}")
        print(f"To:        kyle.kuklinski@gmail.com")
        print(f"From:      concierge@d2mluxury.quest")
        print(f"Subject:   Viking Mars — December Flights: Options & Your Call")
        print(f"Account:   d2mconcierge@gmail.com")
        print(f"Status:    DRAFT ONLY — not sent")
        print(f"Review:    https://mail.google.com/mail/#drafts")
        print("=" * 60)
        print()
        print("Commander review required before send (WF-17).")
        return draft_id

    except HttpError as e:
        print(f"Gmail API error: {e}")
        if e.resp.status == 401:
            print("Token may need re-auth. Run reauth script.")
        sys.exit(1)


if __name__ == '__main__':
    main()
