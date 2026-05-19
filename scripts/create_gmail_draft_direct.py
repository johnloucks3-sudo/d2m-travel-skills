#!/usr/bin/env python3
"""
Direct Gmail API draft creation using existing token
Creates draft for Kyle Kuklinski lifecycle email
"""

import json
import base64
import sys
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Google API imports
try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError as e:
    print(f"ERROR: Missing Google libraries: {e}")
    print("Install: pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client")
    sys.exit(1)

def create_draft_with_token():
    """Create Gmail draft using OAuth token"""

    # Load token
    token_file = Path("/home/john/Thunderbird/config/persona_gmail_token.json")
    if not token_file.exists():
        print(f"ERROR: Token file not found at {token_file}")
        sys.exit(1)

    with open(token_file) as f:
        token_data = json.load(f)

    # Create credentials object from token data
    creds = Credentials(
        token=token_data.get('token'),
        refresh_token=token_data.get('refresh_token'),
        token_uri=token_data.get('token_uri'),
        client_id=token_data.get('client_id'),
        client_secret=token_data.get('client_secret'),
        scopes=token_data.get('scopes', ['https://www.googleapis.com/auth/gmail.modify'])
    )

    # Refresh if needed (token may be expired)
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            print("✓ Token refreshed")
        except Exception as e:
            print(f"Warning: Could not refresh token: {e}")

    # Build Gmail service
    try:
        service = build('gmail', 'v1', credentials=creds)
        print("✓ Gmail service initialized")
    except Exception as e:
        print(f"ERROR building Gmail service: {e}")
        sys.exit(1)

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--html', required=True)
    parser.add_argument('--to', required=True)
    parser.add_argument('--subject', required=True)
    args = parser.parse_args()
    
    with open(args.html, 'r') as f:
        html_body = f.read()

    print(f"\nCreating draft:")
    print(f"  To: {args.to}")
    print(f"  From: d2mconcierge@gmail.com")
    print(f"  Subject: {args.subject}")

    from_email = "d2mconcierge@gmail.com"
    
    # Build email message
    message = MIMEMultipart('alternative')
    message['to'] = args.to
    message['from'] = from_email
    message['subject'] = args.subject

    # Add HTML part
    msg_html = MIMEText(html_body, 'html', 'utf-8')
    message.attach(msg_html)

    # Encode message
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

    # Create draft via Gmail API
    try:
        draft_body = {
            'message': {
                'raw': raw_message
            }
        }

        draft = service.users().drafts().create(userId='me', body=draft_body).execute()

        print(f"\n✅ SUCCESS!")
        print(f"Draft created successfully")
        print(f"Draft ID: {draft.get('id')}")
        print(f"Message ID: {draft.get('message', {}).get('id')}")
        print(f"\nAccess draft at: https://mail.google.com/mail/?ui=2&view=cm&fs=1&tf=0&to={args.to}")

        return 0

    except HttpError as error:
        error_content = error.content.decode('utf-8') if isinstance(error.content, bytes) else error.content
        print(f"\n❌ Gmail API Error: {error.resp.status}")
        print(f"Details: {error_content}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(create_draft_with_token())
