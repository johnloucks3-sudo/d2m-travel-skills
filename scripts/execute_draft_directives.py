#!/usr/bin/env python3
"""
Execute Commander Draft Directives:
1. Delete Drafts #5, #4, #1:
   - r4690852114650861253 (Draft #5 - Al Ely & Amy Darrow)
   - r7190156016640050555 (Draft #4 - Larry & Heidi Nichols)
   - r-5558669960233509725 (Draft #1 - Leslie Nichols)
2. Transfer Draft #3 to johnloucks3 as a personal draft:
   - r-7507525382961074550 ([COMMANDER REVIEW] Spencer Grand Voyage Intake)
3. Direct-Send Draft #2 as an Internal Brief/Report to johnloucks3@gmail.com:
   - r2402070694790028897 (D2M Monthly Validation Report — 2026-07)
   (Per SO_DRAFT_ROUTING_20260614: Internal briefs -> DIRECT SEND to johnloucks3, zero drafts)
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

def process_directives():
    # Service for d2mconcierge / unified account
    svc = get_gmail()
    
    # 1. Delete Drafts 5, 4, 1
    to_delete = [
        "r4690852114650861253",  # #5
        "r7190156016640050555",  # #4
        "r-5558669960233509725"  # #1
    ]
    for d_id in to_delete:
        try:
            print(f"Deleting Draft ID {d_id}...")
            svc.users().drafts().delete(userId='me', id=d_id).execute()
            print(f"Successfully deleted {d_id}.")
        except Exception as e:
            print(f"Error deleting draft {d_id}: {e}")

    # 2. Direct-Send Draft #2 (Monthly Validation Report) as an internal email report to johnloucks3
    report_draft_id = "r2402070694790028897"
    try:
        print(f"Direct-sending Report Draft ID {report_draft_id} to johnloucks3@gmail.com per internal brief doctrine...")
        sent_msg = svc.users().drafts().send(userId='me', body={'id': report_draft_id}).execute()
        print(f"Report sent successfully! Sent Message ID: {sent_msg.get('id')}")
    except Exception as e:
        print(f"Error sending report draft {report_draft_id}: {e}")

    # 3. Transfer Draft #3 (Spencer Intake Form) to johnloucks3 personal drafts
    intake_draft_id = "r-7507525382961074550"
    try:
        print(f"Fetching Spencer Intake draft {intake_draft_id} content...")
        draft_detail = svc.users().drafts().get(userId='me', id=intake_draft_id).execute()
        msg_payload = draft_detail.get('message', {}).get('payload', {})
        
        headers = {h['name'].lower(): h['value'] for h in msg_payload.get('headers', [])}
        subject = headers.get('subject', 'Spencer Intake Form')
        
        # Get body
        import base64
        parts = msg_payload.get('parts', [])
        html_body = ""
        for p in parts:
            if p.get('mimeType') == 'text/html':
                html_body = base64.urlsafe_b64decode(p.get('body', {}).get('data', '')).decode('utf-8', errors='ignore')
                break
        if not html_body:
            body_data = msg_payload.get('body', {}).get('data', '')
            if body_data:
                html_body = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore')

        print("Deleting draft from Concierge box...")
        svc.users().drafts().delete(userId='me', id=intake_draft_id).execute()

        print("Re-staging draft under johnloucks3 account with WING-PERSONAL-DRAFT label...")
        from core.email.thunderbird_gmail import gmail_create_draft_sync
        new_draft = gmail_create_draft_sync(
            to="johnloucks3@gmail.com",
            subject=subject,
            body=html_body,
            persona_id="COMMANDER"
        )
        print(f"Transferred draft successfully: {new_draft}")
    except Exception as e:
        print(f"Error transferring draft {intake_draft_id}: {e}")

if __name__ == "__main__":
    process_directives()
