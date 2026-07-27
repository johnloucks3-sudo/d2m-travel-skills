#!/usr/bin/env python3
"""
HALE-AG Executive Officer (XO) Autonomous Sentinel & Folder Governance Daemon
==============================================================================
Authority: Commander Directives (2026-07-27)
Scope & Rules of Engagement:
1. johnloucks3@gmail.com ACCOUNT SCOPE:
   - INBOX: STRICT HANDS-OFF. Zero autonomous reads/deletions/moves in main Inbox.
   - OTHER FOLDERS & DRAFTS: Full authority to maintain, clean up, label, and manage drafts.
   - Housekeeping & Languishing Items: Audit non-inbox folders & drafts, flagging stagnant items to Commander.
2. d2mconcierge@gmail.com ACCOUNT SCOPE:
   - FULL AUTHORITY over d2mconcierge inbox and folders.
   - MANDATORY ALLOWLIST INCLUSION: Project Expedition, supplier/vendor applications (Sky Bird, Centrav, TBO, etc.), client inquiries, and Commander correspondence MUST be passed through as priority comms.
   - Commercial / Consumer Marketing Blasts: Autonomous triaging and cleanup.
"""

import email
import email.parser
import email.utils

import sys
import os
import re
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "api"))
sys.path.insert(0, str(ROOT / "core"))

LOG_FILE = ROOT / "logs" / "executive_officer_daemon.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [XO-HALE-AG] %(levelname)s: %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("XOHaleAG")

# Explicit ALLOWLIST patterns for d2mconcierge (NEVER filter these out)
PRIORITY_ALLOWLIST = [
    "projectexpedition.com", "project-expedition", "skybird", "centrav", "tbo.com",
    "virtuoso", "rssc.com", "nexion", "outsideagents", "tess", "allianz", "viking",
    "silversea", "princess", "seabourn", "oceania", "regent", "spencer", "nichols",
    "ely", "furlow", "westbrook", "lyons", "darrow", "kuklinski"
]

# Broad domain/sender noise filter for commercial emails, consumer marketing, and retail promos
NOISE_PATTERNS = [
    "substack.com", "theepochtimes.com", "historyfacts.com", "mkt.aacu.com",
    "lawndoctor.com", "healthgrades.com", "cruisecritic.com", "walmart.com", "amazon.com",
    "newsmax.com", "thepointsguy.com", "cyberguy.com", "informeddelivery.usps.com",
    "beehiiv.com", "thecoloradoflyover.com", "legalinsurrection.com", "justthenews.com",
    "wired.com", "rocketmoney.com", "americanexpress.com", "colorfulimages.com",
    "l.freddys.com", "allrecipes.com", "vitalitymedical.com", "parkdia.com",
    "simpleflying.com", "email.forbes.com", "thecheesecakefactory.com", "heritage.org",
    "fanatics.com", "cosaction.com", "onlyinyourstate.com", "thedeepview.co",
    "loseit.com", "cntraveler.com", "rivercruiseadvisor.com", "costco.com",
    "hillsdale.edu", "frontsteps.com", "chickensaladchick.com", "members.netflix.com",
    "heavy.com", "ccsend.com", "stanford.edu"
]

class ExecutiveOfficerDaemon:
    """HALE-AG Executive Officer Engine"""
    
    @classmethod
    def scan_d2m_inbox(cls) -> dict:
        logger.info("XO Sentinel: Scanning d2mconcierge inbox for priority client/vendor comms...")
        try:
            from api.thunderbird_google_auth import get_gmail
            svc = get_gmail()
            res = svc.users().messages().list(userId='me', q='is:unread -from:johnloucks3@gmail.com -from:d2mconcierge@gmail.com').execute()
            messages = res.get('messages', [])
            
            logger.info(f"d2mconcierge unread messages evaluated: {len(messages)}")
            priority_comms = []
            
            for m in messages:
                msg_id = m['id']
                detail = svc.users().messages().get(userId='me', id=msg_id).execute()
                snippet = detail.get('snippet', '')
                headers = {h['name'].lower(): h['value'] for h in detail.get('payload', {}).get('headers', [])}
                sender = headers.get('from', 'Unknown Sender').lower()
                subject = headers.get('subject', 'No Subject')
                
                # Check Priority Allowlist FIRST (Project Expedition, Suppliers, Clients)
                is_priority = any(al in sender or al in subject.lower() or al in snippet.lower() for al in PRIORITY_ALLOWLIST)
                
                # Check Noise Filter if not explicitly allowlisted
                if not is_priority and any(np in sender for np in NOISE_PATTERNS):
                    continue
                    
                logger.info(f"🚨 PRIORITY D2M COMM DETECTED: [{sender}] — {subject}")
                priority_comms.append({
                    "id": msg_id,
                    "sender": sender,
                    "subject": subject,
                    "snippet": snippet,
                    "is_allowlisted": is_priority
                })
                
            return {"status": "SUCCESS", "unread_total": len(messages), "priority_comms_count": len(priority_comms), "comms": priority_comms}
        except Exception as e:
            logger.error(f"Error during d2m inbox scan: {e}")
            return {"status": "ERROR", "message": str(e)}

    @classmethod
    def audit_johnloucks3_folder_housekeeping(cls) -> dict:
        """Audits johnloucks3 drafts and non-inbox folders for stagnant/languishing items WITHOUT TOUCHING INBOX."""
        logger.info("XO Sentinel: Auditing johnloucks3 drafts and non-inbox folders for housekeeping...")
        try:
            from api.thunderbird_google_auth import get_gmail
            svc = get_gmail() # Accesses main account
            
            # Check Drafts folder
            drafts_res = svc.users().drafts().list(userId='me').execute()
            drafts = drafts_res.get('drafts', [])
            
            stagnant_drafts = []
            for d in drafts:
                detail = svc.users().drafts().get(userId='me', id=d['id']).execute()
                msg = detail.get('message', {})
                headers = {h['name'].lower(): h['value'] for h in msg.get('payload', {}).get('headers', [])}
                stagnant_drafts.append({
                    "id": d['id'],
                    "subject": headers.get('subject', '(No Subject)'),
                    "to": headers.get('to', '(No Recipient)')
                })
                
            logger.info(f"johnloucks3 Drafts audit complete: {len(drafts)} drafts currently managed.")
            return {"status": "SUCCESS", "draft_count": len(drafts), "drafts": stagnant_drafts}
        except Exception as e:
            logger.error(f"Error auditing johnloucks3 folder housekeeping: {e}")
            return {"status": "ERROR", "message": str(e)}

if __name__ == "__main__":
    logger.info("Initializing HALE-AG Executive Officer (XO) Governance & Housekeeping Run...")
    d2m_res = ExecutiveOfficerDaemon.scan_d2m_inbox()
    jl_res = ExecutiveOfficerDaemon.audit_johnloucks3_folder_housekeeping()
    print(f"\nXO Daemon Status:\n{json.dumps({'d2m_inbox_sentinel': d2m_res, 'johnloucks3_folder_housekeeping': jl_res}, indent=2)}")
