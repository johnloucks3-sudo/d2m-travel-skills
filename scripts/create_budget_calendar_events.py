#!/usr/bin/env python3
"""Create calendar events for Budget minivan rental."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.scheduling.thunderbird_calendar_sync import _get_calendar_service
from googleapiclient.errors import HttpError
from datetime import datetime, timedelta
import pytz

TIMEZONE = "America/Denver"
CALENDAR_ID = "primary"  # John's primary calendar

def create_timed_event(service, summary, description, start_dt, end_dt, location=""):
    """Create a timed (not all-day) calendar event."""
    event_body = {
        "summary": summary,
        "description": description,
        "location": location,
        "start": {
            "dateTime": start_dt.isoformat(),
            "timeZone": TIMEZONE,
        },
        "end": {
            "dateTime": end_dt.isoformat(),
            "timeZone": TIMEZONE,
        },
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "popup", "minutes": 1440},    # 1 day before
                {"method": "popup", "minutes": 120},      # 2 hours before
            ],
        },
    }
    try:
        event = service.events().insert(calendarId=CALENDAR_ID, body=event_body).execute()
        print(f"✅ Created: {summary}")
        print(f"   Link: {event.get('htmlLink')}")
        return event.get("id")
    except HttpError as e:
        print(f"❌ Error creating '{summary}': {e}")
        return None

def main():
    service = _get_calendar_service()

    tz = pytz.timezone(TIMEZONE)

    # Event 1: Pick up
    create_timed_event(
        service,
        "🚗 Pick up Budget Minivan — COS Airport",
        "Budget Rent A Car — Reservation #49527585US2\nChrysler Pacifica or similar\nPhone: (719) 597-1271\nUnlimited mileage\nTotal: $1,193.25",
        tz.localize(datetime(2026, 7, 17, 12, 0)),
        tz.localize(datetime(2026, 7, 17, 13, 0)),
        location="7770 Milton E Proby Pkwy, Colorado Springs, CO 80916"
    )

    # Event 2: Drop off
    create_timed_event(
        service,
        "🚗 Return Budget Minivan — COS Airport",
        "Budget Rent A Car — Reservation #49527585US2\nDrop off by 12:00 PM\nPhone: (719) 597-1271\nLocation open 7AM-Midnight",
        tz.localize(datetime(2026, 7, 26, 12, 0)),
        tz.localize(datetime(2026, 7, 26, 13, 0)),
        location="7770 Milton E Proby Pkwy, Colorado Springs, CO 80916"
    )

if __name__ == "__main__":
    main()
