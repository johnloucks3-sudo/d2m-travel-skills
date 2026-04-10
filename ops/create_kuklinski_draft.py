#!/usr/bin/env python3
"""
Create Kuklinski draft using direct Gmail API
"""

import os
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from email.mime.text import MIMEText
import base64

# Load existing token
token_path = 'creds/gmail_token.json'
if not os.path.exists(token_path):
    print("❌ Gmail token not found")
    exit(1)

print("✅ Loading Gmail token")
with open(token_path, 'r') as f:
    token_data = json.load(f)

# Create credentials
creds = Credentials.from_authorized_user_info(token_data)

# Build service
try:
    service = build('gmail', 'v1', credentials=creds)
    print("✅ Gmail service built")
    
    # Read HTML content
    with open('drafts/commander_to_kyle_lifecycle_explanation.html', 'r') as f:
        html_content = f.read()
    
    print("✅ HTML content loaded")
    
    # Create message with HTML content
    message = MIMEText(html_content, 'html')
    message['to'] = 'kyle.kuklinski@gmail.com'
    message['from'] = 'd2mconcierge@gmail.com'
    message['subject'] = 'Your Panama Canal Cruise Planning Timeline & D2M Service Process'
    
    # Create draft
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    draft_body = {'message': {'raw': raw}}
    
    draft = service.users().drafts().create(userId='me', body=draft_body).execute()
    print(f"🎉 KUKLINSKI DRAFT CREATED SUCCESSFULLY!")
    print(f"   Draft ID: {draft['id']}")
    print(f"   Gmail URL: https://mail.google.com/mail/#drafts?compose={draft['id']}")
    print(f"   From: d2mconcierge@gmail.com")
    print(f"   To: kyle.kuklinski@gmail.com")
    print(f"   Subject: Your Panama Canal Cruise Planning Timeline & D2M Service Process")
    print("")
    print("✅ Please check johnloucks3@gmail.com drafts folder - draft should be visible")
    print("✅ WF-17 review can now be performed on the actual draft")
    
except HttpError as error:
    print(f"❌ Gmail API error: {error}")
    if error.resp.status == 401:
        print("   Token may need refresh")
    elif error.resp.status == 403:
        print("   Insufficient permissions")
    elif error.resp.status == 429:
        print("   Rate limited")
    
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()
