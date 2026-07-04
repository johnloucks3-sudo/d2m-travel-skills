#!/usr/bin/env python3
"""
primary_router.py — keep D2M internal mail in johnloucks3's PRIMARY tab.

The johnloucks3 token holds gmail.modify (not settings scope), so a true Gmail
filter can't be created programmatically. Same end result: on each run, find
recent d2mconcierge->johnloucks3 messages that Gmail filed under a category tab
and strip the category label so they fall back to Primary.

Run on a timer (primary-router.timer, every 5 min). Commander directive 2026-07-04.
"""
from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

TOKEN = Path("/home/john/Thunderbird/creds/johnloucks3_token.json")
CATS = ["CATEGORY_PERSONAL", "CATEGORY_PROMOTIONS", "CATEGORY_SOCIAL",
        "CATEGORY_UPDATES", "CATEGORY_FORUMS"]


def main(window="newer_than:2d"):
    creds = Credentials.from_authorized_user_file(str(TOKEN))
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN.write_text(creds.to_json())
    svc = build("gmail", "v1", credentials=creds)
    q = f"from:d2mconcierge@gmail.com {window} (category:personal OR category:promotions OR category:social OR category:updates)"
    msgs = svc.users().messages().list(userId="me", q=q, maxResults=50).execute().get("messages", [])
    moved = 0
    for m in msgs:
        full = svc.users().messages().get(userId="me", id=m["id"], format="minimal").execute()
        remove = [c for c in CATS if c in full.get("labelIds", [])]
        if remove:
            svc.users().messages().modify(userId="me", id=m["id"],
                                          body={"removeLabelIds": remove}).execute()
            moved += 1
    print(f"primary_router: moved {moved} d2mconcierge message(s) to Primary")


if __name__ == "__main__":
    main()
