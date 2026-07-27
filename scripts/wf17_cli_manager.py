#!/usr/bin/env python3
"""
WF-17 Draft Review & One-Click Send Manager
===========================================
Provides clean CLI inspection, previewing, and optional one-click send
capabilities for client drafts sitting at the WF-17 gate in your Gmail account.
"""

import sys
import os
import json
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "api"))

from api.thunderbird_google_auth import get_gmail

def list_wf17_drafts():
    svc = get_gmail()
    res = svc.users().drafts().list(userId='me').execute()
    drafts = res.get('drafts', [])
    
    print(f"\n=======================================================")
    print(f"    WF-17 CLIENT DRAFT REVIEW & STAGING GATE (GMAIL)   ")
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

def send_draft_by_id(draft_id: str):
    svc = get_gmail()
    print(f"Executing Commander Send for Draft ID: {draft_id}...")
    res = svc.users().drafts().send(userId='me', body={'id': draft_id}).execute()
    print(f"Successfully sent! Sent Message ID: {res.get('id')}")
    return res

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WF-17 Draft Manager")
    parser.add_argument("--list", action="store_true", help="List all drafts pending at WF-17 gate")
    parser.add_argument("--send", type=str, help="Send draft by ID")
    parser.add_argument("--send-all-clients", action="store_true", help="Send all client-facing drafts")
    args = parser.parse_args()

    if args.send:
        send_draft_by_id(args.send)
    elif args.list or len(sys.argv) == 1:
        list_wf17_drafts()
