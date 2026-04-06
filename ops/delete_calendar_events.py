#!/usr/bin/env python3
"""
delete_calendar_events.py
D2M Thunderbird — delete Google Calendar events by keyword/title match.

Usage:
    python3 delete_calendar_events.py "keyword"
    python3 delete_calendar_events.py "D2M" --calendar johnloucks3@gmail.com
    python3 delete_calendar_events.py "test" --dry-run

Auth:   Reads gmail_token.json from the same directory as this script.
        Run force_auth.py first if the token is missing or expired.
"""

import os
import sys
import argparse
from datetime import datetime, timezone

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# ── Config ────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE   = os.path.join(SCRIPT_DIR, "gmail_token.json")
SCOPES       = ["https://www.googleapis.com/auth/calendar"]
DEFAULT_CAL  = "johnloucks3@gmail.com"
MAX_RESULTS  = 250   # events to scan per search window

# ── Auth ──────────────────────────────────────────────────────────────────────
def get_credentials():
    if not os.path.exists(TOKEN_FILE):
        print(f"ERROR: Token file not found: {TOKEN_FILE}")
        print("Run force_auth.py first to generate it.")
        sys.exit(1)

    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if creds.expired and creds.refresh_token:
        print("Token expired — refreshing automatically...")
        creds.refresh(Request())
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
        print("Token refreshed and saved.")

    if not creds.valid:
        print("ERROR: Token is invalid. Re-run force_auth.py.")
        sys.exit(1)

    return creds

# ── Fetch events ──────────────────────────────────────────────────────────────
def fetch_matching_events(service, calendar_id, keyword):
    """Return all future events whose summary contains keyword (case-insensitive)."""
    now = datetime.now(timezone.utc).isoformat()
    matches = []
    page_token = None

    while True:
        result = service.events().list(
            calendarId=calendar_id,
            timeMin=now,
            maxResults=MAX_RESULTS,
            singleEvents=True,
            orderBy="startTime",
            pageToken=page_token,
        ).execute()

        for event in result.get("items", []):
            title = event.get("summary", "")
            if keyword.lower() in title.lower():
                matches.append(event)

        page_token = result.get("nextPageToken")
        if not page_token:
            break

    return matches

# ── Display helpers ───────────────────────────────────────────────────────────
def fmt_event(event, idx):
    title = event.get("summary", "(no title)")
    start = event.get("start", {})
    when  = start.get("dateTime") or start.get("date") or "unknown"
    eid   = event.get("id", "")
    return f"  [{idx+1}] {when[:16]}  |  {title}  (id: {eid[:12]}...)"

# ── Delete ────────────────────────────────────────────────────────────────────
def delete_events(service, calendar_id, events, dry_run):
    deleted = 0
    for event in events:
        title = event.get("summary", "(no title)")
        eid   = event["id"]
        if dry_run:
            print(f"  [DRY-RUN] Would delete: {title}")
        else:
            try:
                service.events().delete(calendarId=calendar_id, eventId=eid).execute()
                print(f"  ✓ Deleted: {title}")
                deleted += 1
            except Exception as e:
                print(f"  ✗ Failed to delete '{title}': {e}")
    return deleted

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Delete Google Calendar events by keyword")
    parser.add_argument("keyword",                   help="Title keyword to match (case-insensitive)")
    parser.add_argument("--calendar", "-c",          default=DEFAULT_CAL, help="Calendar ID")
    parser.add_argument("--dry-run",  "-n",          action="store_true",  help="Preview only, no deletion")
    parser.add_argument("--yes",      "-y",          action="store_true",  help="Skip confirmation prompt")
    args = parser.parse_args()

    print(f"\n🔑 Authenticating from {TOKEN_FILE}...")
    creds   = get_credentials()
    service = build("calendar", "v3", credentials=creds)

    print(f"\n🔍 Searching '{args.calendar}' for events matching: \"{args.keyword}\"")
    matches = fetch_matching_events(service, args.calendar, args.keyword)

    if not matches:
        print("  No matching events found.")
        return

    print(f"\n  Found {len(matches)} matching event(s):\n")
    for i, ev in enumerate(matches):
        print(fmt_event(ev, i))

    if args.dry_run:
        print("\n[DRY-RUN mode — nothing will be deleted]\n")
        delete_events(service, args.calendar, matches, dry_run=True)
        return

    if not args.yes:
        confirm = input(f"\n  Delete all {len(matches)} event(s)? [y/N] ").strip().lower()
        if confirm != "y":
            print("  Aborted — nothing deleted.")
            return

    print()
    count = delete_events(service, args.calendar, matches, dry_run=False)
    print(f"\n✅ Done — {count}/{len(matches)} event(s) deleted from {args.calendar}\n")

if __name__ == "__main__":
    main()
