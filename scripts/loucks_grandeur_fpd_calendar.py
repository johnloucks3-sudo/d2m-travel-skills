#!/usr/bin/env python3
"""
loucks_grandeur_fpd_calendar.py — Create calendar entry for Loucks Grandeur FPD payment.

Creates a hard calendar block on johnloucks3's personal calendar for Aug 1, 2026 FPD.
Booking: 3122006 | Ship: Seven Seas Grandeur | Amount: $24,798.00

Run: python3 scripts/loucks_grandeur_fpd_calendar.py
Run with --dry-run to preview without creating event.

Authority: MISSION-255 — Stage Commander calendar entry for Loucks Grandeur FPD Aug 1
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parents[1]


def get_calendar_service(cred_file: str = "creds/calendar_token.json"):
    """Build Google Calendar service from credentials."""
    sys.path.insert(0, str(ROOT))
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    cred_path = ROOT / cred_file
    if not cred_path.exists():
        raise FileNotFoundError(f"Credentials not found: {cred_path}")

    creds = Credentials.from_authorized_user_file(str(cred_path))
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        cred_path.write_text(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def get_johnloucks3_calendar_id(svc):
    """Find johnloucks3@gmail.com calendar ID."""
    calendars = svc.calendarList().list().execute()
    for cal in calendars.get("items", []):
        if "johnloucks3@gmail.com" in cal.get("id", ""):
            return cal["id"]
    # Fallback to primary if johnloucks3 found in primary
    primary = svc.calendarList().get(calendarId="primary").execute()
    if "johnloucks3@gmail.com" in primary.get("summary", ""):
        return "primary"
    return "primary"  # Default fallback


def event_exists(svc, calendar_id: str, date_str: str, summary_prefix: str) -> bool:
    """Check if event already exists on this date."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        time_min = dt.replace(tzinfo=timezone.utc).isoformat()
        time_max = dt.replace(hour=23, minute=59, second=59, tzinfo=timezone.utc).isoformat()

        events = svc.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
        ).execute()

        return any(summary_prefix.lower() in e.get("summary", "").lower()
                   for e in events.get("items", []))
    except Exception:
        return False


def create_fpd_event(svc, calendar_id: str, dry_run: bool = False) -> dict:
    """Create FPD calendar event for Loucks Grandeur."""

    event_date = "2026-08-01"
    summary = "🦅 LOUCKS GRANDEUR FPD — $24,798 DUE (Booking 3122006)"
    description = (
        "FINAL PAYMENT DUE — Regent Seven Seas Grandeur Panama Canal\n\n"
        "Booking: 3122006\n"
        "Ship: Seven Seas Grandeur\n"
        "Amount: $24,798.00\n"
        "Embarkation: Dec 29, 2026 (Miami)\n"
        "Disembarkation: Jan 14, 2027 (Los Angeles)\n"
        "Route: Miami → Grand Cayman → Cartagena → Panama Canal → Costa Rica → Guatemala → Acapulco → Cabo → San Diego → Los Angeles\n"
        "Cabin: 658 (Deck 6 - Concierge Suite E)\n"
        "Companions: Nancy & Ken Lyons (separate booking, same ship)\n\n"
        "Deferred alerts already armed (Jul 2: 30-day, Jul 25: 1-week)\n"
        "Source: dossier Loucks_Regent_Grandeur_3122006.md (verified portal Jun 10)\n"
        "Created: MISSION-255 stage calendar entry"
    )

    if dry_run:
        print(f"[DRY RUN] Would create event:")
        print(f"  Date: {event_date}")
        print(f"  Summary: {summary}")
        print(f"  Description: {description[:100]}...")
        return {}

    # Check if event already exists
    if event_exists(svc, calendar_id, event_date, "LOUCKS GRANDEUR"):
        print(f"✅ Event already exists for {event_date}. Skipping creation.")
        return {}

    event = {
        "summary": summary,
        "description": description,
        "start": {"date": event_date},
        "end": {"date": event_date},
        "colorId": "11",  # Red/tomato for financial deadline
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "email", "minutes": 24 * 60},  # Email day-before
            ],
        },
    }

    result = svc.events().insert(calendarId=calendar_id, body=event).execute()
    print(f"✅ Created calendar event:")
    print(f"   Date: {event_date}")
    print(f"   Summary: {summary}")
    print(f"   Event ID: {result.get('id')}")
    print(f"   Link: {result.get('htmlLink')}")
    return result


def main():
    dry_run = "--dry-run" in sys.argv

    if dry_run:
        print("=== LOUCKS GRANDEUR FPD CALENDAR ENTRY — DRY RUN ===\n")
    else:
        print("=== LOUCKS GRANDEUR FPD CALENDAR ENTRY ===\n")

    try:
        svc = get_calendar_service()
        calendar_id = get_johnloucks3_calendar_id(svc)

        print(f"Using calendar: {calendar_id}\n")

        result = create_fpd_event(svc, calendar_id, dry_run)

        if not dry_run and result:
            print(f"\n✅ MISSION-255 complete: Calendar entry staged for Commander")
        elif dry_run:
            print(f"\n✅ DRY RUN: Calendar entry ready to create")
        else:
            print(f"\n✅ Event already on calendar — no action needed")

        return 0

    except Exception as e:
        print(f"\n❌ ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
