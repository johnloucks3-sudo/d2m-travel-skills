#!/usr/bin/env python3
"""
RESTAGE D2MCONCIERGE DRAFTS TO JOHNLOUCKS3 & INBOX
=================================================
Authority: SO-REPORTING-2026 & Commander Directive (2026-07-28)

Tasks:
1. Fetch all 36 drafts from d2mconcierge@gmail.com.
2. For Internal Reports/Briefs (To: johnloucks3@gmail.com): Send directly to johnloucks3 INBOX.
3. For Client Product Drafts (To: client emails or johnloucks3 review): Restage in johnloucks3 DRAFTS with label 'THUNDERBIRD-Commander-Review'.
4. Delete processed drafts from d2mconcierge.
"""

import email
import email.parser
import email.utils
import base64
import sys
import os
import json
import logging
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

ROOT = Path("/home/john/Thunderbird")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "api"))
sys.path.insert(0, str(ROOT / "core"))

from core.email.thunderbird_gmail import _get_wing_gmail_service, _get_commander_gmail_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s [RESTAGE-DRAFTS]: %(message)s")
logger = logging.getLogger("RestageDrafts")

def process_d2m_drafts():
    logger.info("Connecting to Gmail services...")
    svc_d2m = _get_wing_gmail_service()
    svc_jl = _get_commander_gmail_service()
    
    if not svc_d2m or not svc_jl:
        logger.error("Failed to acquire Gmail services!")
        return

    # List drafts in d2mconcierge
    res = svc_d2m.users().drafts().list(userId='me').execute()
    drafts = res.get('drafts', [])
    logger.info(f"Found {len(drafts)} drafts in d2mconcierge@gmail.com.")
    
    # Get or create THUNDERBIRD-Commander-Review label in johnloucks3
    jl_labels = svc_jl.users().labels().list(userId='me').execute().get('labels', [])
    review_label_id = None
    for lbl in jl_labels:
        if lbl['name'] == 'THUNDERBIRD-Commander-Review':
            review_label_id = lbl['id']
            break
    if not review_label_id:
        new_lbl = svc_jl.users().labels().create(userId='me', body={
            'name': 'THUNDERBIRD-Commander-Review',
            'labelListVisibility': 'labelShow',
            'messageListVisibility': 'show'
        }).execute()
        review_label_id = new_lbl['id']
        logger.info(f"Created label 'THUNDERBIRD-Commander-Review' (ID: {review_label_id})")

    restaged_count = 0
    inbox_sent_count = 0
    cleaned_count = 0

    for d in drafts:
        draft_id = d['id']
        try:
            detail = svc_d2m.users().drafts().get(userId='me', id=draft_id).execute()
            msg = detail.get('message', {})
            payload = msg.get('payload', {})
            headers = {h['name'].lower(): h['value'] for h in payload.get('headers', [])}
            
            subject = headers.get('subject', 'No Subject')
            to_addr = headers.get('to', '')
            
            # Skip system error logs or duplicates
            if "RUNTIMEERROR" in subject.upper() or "POLICY GATE" in subject.upper():
                logger.info(f"Cleaning error draft '{subject}' (ID: {draft_id})...")
                svc_d2m.users().drafts().delete(userId='me', id=draft_id).execute()
                cleaned_count += 1
                continue

            # Extract body
            parts = payload.get('parts', [])
            body_html = ""
            body_plain = ""
            if parts:
                for p in parts:
                    data = p.get('body', {}).get('data', '')
                    if data:
                        decoded = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                        if p.get('mimeType') == 'text/html':
                            body_html = decoded
                        elif p.get('mimeType') == 'text/plain':
                            body_plain = decoded
            else:
                data = payload.get('body', {}).get('data', '')
                if data:
                    body_html = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')

            # Decision logic: Internal Report -> Send to johnloucks3 INBOX; Client Product -> Restage in jl3 DRAFTS
            is_internal_report = any(kw in subject.upper() for kw in [
                "INTEL", "DECISION INBOX", "POSITION PAPER", "VALIDATION REPORT", "FALLBACK PLAN", "TEST", "WARN", "DASHBOARD"
            ])
            
            new_msg = MIMEMultipart("alternative")
            new_msg["Subject"] = subject
            if is_internal_report or "johnloucks3" in to_addr:
                new_msg["To"] = "johnloucks3@gmail.com"
            else:
                new_msg["To"] = to_addr if to_addr else "johnloucks3@gmail.com"

            new_msg.attach(MIMEText(body_plain if body_plain else "Please view HTML.", "plain"))
            new_msg.attach(MIMEText(body_html if body_html else "<p>No content</p>", "html"))
            raw_b64 = base64.urlsafe_b64encode(new_msg.as_bytes()).decode("utf-8")

            if is_internal_report:
                # Send directly to johnloucks3 INBOX
                svc_jl.users().messages().send(userId='me', body={'raw': raw_b64}).execute()
                logger.info(f"✅ Delivered Internal Report directly to johnloucks3 INBOX: '{subject}'")
                inbox_sent_count += 1
            else:
                # Restage in johnloucks3 DRAFTS
                draft_res = svc_jl.users().drafts().create(userId='me', body={'message': {'raw': raw_b64}}).execute()
                created_msg_id = draft_res.get('message', {}).get('id')
                if created_msg_id and review_label_id:
                    svc_jl.users().messages().batchModify(userId='me', body={
                        'ids': [created_msg_id],
                        'addLabelIds': [review_label_id]
                    }).execute()
                logger.info(f"✅ Restaged Client Draft in johnloucks3 DRAFTS: '{subject}'")
                restaged_count += 1

            # Delete old draft from d2mconcierge
            svc_d2m.users().drafts().delete(userId='me', id=draft_id).execute()
            cleaned_count += 1

        except Exception as e:
            logger.error(f"Error processing draft ID {draft_id}: {e}")

    logger.info("=========================================")
    logger.info(f"DRAFT RESTAGING SUMMARY:")
    logger.info(f"- Restaged to jl3 Drafts: {restaged_count}")
    logger.info(f"- Delivered to jl3 Inbox: {inbox_sent_count}")
    logger.info(f"- Cleaned from d2mconcierge: {cleaned_count}")
    logger.info("=========================================")

if __name__ == "__main__":
    process_d2m_drafts()
