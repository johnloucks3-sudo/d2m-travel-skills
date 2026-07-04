#!/usr/bin/env python3
"""
inbox_restore.py — keep D2M internal mail (d2mconcierge -> johnloucks3) visible
in johnloucks3's Inbox.

Diagnosis (2026-07-04): d2mconcierge->johnloucks3 mail was arriving with a
CATEGORY_* label but WITHOUT the INBOX label — i.e. Gmail was archiving it on
arrival, not just mis-filing it to a tab. The prior fix attempt
(primary_router.py, reverted same day) tried to strip the CATEGORY label via
messages.modify; that failed because Gmail's classifier reasserts category
labels asynchronously. Adding INBOX back does NOT get reasserted-away the same
way (verified live 2026-07-04) — it's a stable label add within the existing
gmail.modify scope (no settings.basic / filter needed).

Run on a timer, same cadence as the old primary-router.timer (every 5 min).
"""
from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

TOKEN = Path("/home/john/Thunderbird/creds/johnloucks3_token.json")


def main(window="newer_than:2d"):
    creds = Credentials.from_authorized_user_file(str(TOKEN))
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN.write_text(creds.to_json())
    svc = build("gmail", "v1", credentials=creds)
    q = f"from:d2mconcierge@gmail.com {window} -in:inbox -in:trash -in:spam"
    msgs = svc.users().messages().list(userId="me", q=q, maxResults=50).execute().get("messages", [])
    restored = 0
    for m in msgs:
        full = svc.users().messages().get(userId="me", id=m["id"], format="minimal").execute()
        if "INBOX" not in full.get("labelIds", []):
            svc.users().messages().modify(
                userId="me", id=m["id"], body={"addLabelIds": ["INBOX"]}
            ).execute()
            restored += 1
    print(f"inbox_restore: restored {restored} d2mconcierge message(s) to Inbox")


if __name__ == "__main__":
    main()
