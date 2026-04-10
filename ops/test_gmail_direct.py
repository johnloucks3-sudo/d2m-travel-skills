#!/usr/bin/env python3
"""
Direct Gmail API test using existing token
Bypasses MCP wrapper issues
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
    print("❌ Gmail token not found at:", token_path)
    exit(1)

print("✅ Loading Gmail token from:", token_path)
with open(token_path, 'r') as f:
    token_data = json.load(f)

# Create credentials
creds = Credentials.from_authorized_user_info(token_data)

# Build service
try:
    service = build('gmail', 'v1', credentials=creds)
    print("✅ Gmail service built successfully")
    
    # Test list drafts to verify connectivity
    drafts = service.users().drafts().list(userId='me').execute()
    print(f"✅ Draft list test passed - {len(drafts.get('drafts', []))} drafts found")
    
    # Create test message
    message = MIMEText("This is a test draft created through direct Gmail API")
    message['to'] = 'kyle.kuklinski@gmail.com'
    message['from'] = 'd2mconcierge@gmail.com'
    message['subject'] = 'Test Draft - Direct API Debugging'
    
    # Create draft
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    draft_body = {'message': {'raw': raw}}
    
    draft = service.users().drafts().create(userId='me', body=draft_body).execute()
    print(f"✅ Draft created successfully!")
    print(f"   Draft ID: {draft['id']}")
    print(f"   Gmail URL: https://mail.google.com/mail/#drafts?compose={draft['id']}")
    print("   Please check johnloucks3@gmail.com drafts folder")
    
except HttpError as error:
    print(f"❌ Gmail API error: {error}")
    if error.resp.status == 401:
        print("   Token may need refresh - check OAuth validity")
    elif error.resp.status == 403:
        print("   Insufficient permissions - check API scopes")
    elif error.resp.status == 429:
        print("   Rate limited - try again later")
    
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()
