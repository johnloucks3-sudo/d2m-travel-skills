#!/usr/bin/env python3
"""
List Staged Drafts in d2mconcierge Account
==========================================
Interrogates the d2mconcierge@gmail.com account for all pending drafts
(including WF-17 client-facing drafts and internal briefs).
"""

import sys
import os
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "api"))

from api.thunderbird_google_auth import get_gmail
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

def list_concierge_drafts():
    concierge_token = ROOT / "creds" / "d2mconcierge_token.json"
    if not concierge_token.exists():
        print(f"Concierge token missing at {concierge_token}!")
        return
        
    creds = Credentials.from_authorized_user_file(str(concierge_token))
    svc = build('gmail', 'v1', credentials=creds)
    
    res = svc.users().drafts().list(userId='me').execute()
    drafts = res.get('drafts', [])
    
    print(f"\n=======================================================")
    print(f"   D2MCONCIERGE GMAIL ACCOUNT — PENDING DRAFT QUEUE   ")
    print(f"=======================================================")
    print(f" Total Staged Drafts Pending Review: {len(drafts)}\n")
    
    for idx, d in enumerate(drafts, 1):
        draft_id = d['id']
        detail = svc.users().drafts().get(userId='me', id=draft_id).execute()
        msg = detail.get('message', {})
        headers = {h['name'].lower(): h['value'] for h in msg.get('payload', {}).get('headers', [])}
        
        to_email = headers.get('to', '(No Recipient)')
        subject = headers.get('subject', '(No Subject)')
        snippet = msg.get('snippet', '')[:70]
        
        print(f" [{idx:2d}] DRAFT ID: {draft_id}")
        print(f"      TO:      {to_email}")
        print(f"      SUBJECT: {subject}")
        print(f"      SNIPPET: {snippet}...\n")

if __name__ == "__main__":
    list_concierge_drafts()
