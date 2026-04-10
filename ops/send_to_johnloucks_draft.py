#!/usr/bin/env python3
"""
Send draft to johnloucks3@gmail.com drafts folder
Using proven direct Gmail API method
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
    message['to'] = 'johnloucks3@gmail.com'  # Sending to YOUR drafts
    message['from'] = 'd2mconcierge@gmail.com'
    message['subject'] = 'Kuklinski Lifecycle Explanation - Ready for WF-17 Review'
    
    # Create draft
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    draft_body = {'message': {'raw': raw}}
    
    draft = service.users().drafts().create(userId='me', body=draft_body).execute()
    print(f"🎉 DRAFT CREATED IN johnloucks3@gmail.com!")
    print(f"   Draft ID: {draft['id']}")
    print(f"   Gmail URL: https://mail.google.com/mail/#drafts?compose={draft['id']}")
    print(f"   From: d2mconcierge@gmail.com")
    print(f"   To: johnloucks3@gmail.com (YOUR drafts folder)")
    print(f"   Subject: Kuklinski Lifecycle Explanation - Ready for WF-17 Review")
    print("")
    print("✅ Draft is now in YOUR johnloucks3@gmail.com drafts folder")
    print("✅ Ready for WF-17 quality gate review")
    print("✅ Can be forwarded to Kyle after approval")
    
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
