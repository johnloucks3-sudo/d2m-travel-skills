#!/usr/bin/env python3
"""
fpd_calendar_alerts.py — Create Google Calendar events for all open FPDs and deferred alerts.

Reads hale_state.json and creates calendar events in johnloucks3 calendar for:
  - All FPDs with due dates (30-day warning + day-of)
  - All deferred_alerts with trigger_date
  - McLeod/Loucks/Lyons payment deadlines

Run: python3 scripts/fpd_calendar_alerts.py
Run with --dry-run to preview without creating events.

Authority: SO-2026-05-04 §XII — Calendar operations authorized.
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).parents[1]
STATE_FILE = ROOT / "hale_state.json"
CALENDAR_ID = "primary"  # johnloucks3 primary calendar


def get_calendar_service():
    sys.path.insert(0, str(ROOT))
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    creds = Credentials.from_authorized_user_file(str(ROOT / "creds/calendar_token.json"))
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        (ROOT / "creds/calendar_token.json").write_text(creds.to_json())
    return build("calendar", "v3", credentials=creds)


def event_exists(svc, date_str: str, summary_prefix: str) -> bool:
    """Check if a calendar event with this summary prefix already exists on this date."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    time_min = dt.replace(tzinfo=timezone.utc).isoformat()
    time_max = (dt + timedelta(days=1)).replace(tzinfo=timezone.utc).isoformat()
    events = svc.events().list(
        calendarId=CALENDAR_ID,
        timeMin=time_min,
        timeMax=time_max,
        q=summary_prefix[:30],
        singleEvents=True,
    ).execute()
    return any(summary_prefix[:20].lower() in e.get("summary", "").lower()
               for e in events.get("items", []))


def create_event(svc, summary: str, date_str: str, description: str, color_id: str = "11", dry_run: bool = False) -> dict:
    """Create an all-day calendar event."""
    if dry_run:
        print(f"  [DRY RUN] {date_str}: {summary}")
        return {}

    event = {
        "summary": summary,
        "description": description,
        "start": {"date": date_str},
        "end": {"date": date_str},
        "colorId": color_id,  # 11=tomato/red, 6=tangerine/orange, 9=blueberry, 5=banana/yellow
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "popup", "minutes": 9 * 60},   # 9am popup
                {"method": "email", "minutes": 24 * 60},  # day-before email
            ],
        },
    }
    result = svc.events().insert(calendarId=CALENDAR_ID, body=event).execute()
    print(f"  ✅ Created: {date_str}: {summary}")
    return result


def main():
    dry_run = "--dry-run" in sys.argv
    if dry_run:
        print("=== FPD Calendar Alerts — DRY RUN ===\n")
    else:
        print("=== FPD Calendar Alerts ===\n")

    state = json.loads(STATE_FILE.read_text())

    if not dry_run:
        svc = get_calendar_service()

    created = 0
    skipped = 0

    # ── Deferred alerts ─────────────────────────────────────────────────────
    print("Deferred alerts from hale_state.json:")
    for alert in state.get("deferred_alerts", []):
        trigger_date = alert.get("trigger_date", "")
        message = alert.get("message", "")
        client = alert.get("client", "")
        priority = alert.get("priority", "P2")
        amount = alert.get("amount")

        if not trigger_date or not message:
            continue

        color = "11" if priority == "P0" else "6" if priority == "P1" else "5"
        amount_str = f" — ${amount:,.2f}" if amount else ""
        summary = f"🦅 {priority}: {client}{amount_str}"
        desc = f"{message}\n\nSource: hale_state.json deferred_alerts\nAlert ID: {alert.get('id','?')}"

        if not dry_run and event_exists(svc, trigger_date, summary[:25]):
            print(f"  ⏭ Skip (exists): {trigger_date}: {summary}")
            skipped += 1
            continue

        if dry_run:
            print(f"  [DRY RUN] {trigger_date} ({priority}): {summary}")
        else:
            create_event(svc, summary, trigger_date, desc, color)
            created += 1

        # Also create a 30-day warning if the trigger is >30 days out
        try:
            dt = datetime.strptime(trigger_date, "%Y-%m-%d")
            today = datetime.now()
            days_out = (dt - today).days
            if days_out > 30 and amount:
                warn_date = (dt - timedelta(days=30)).strftime("%Y-%m-%d")
                warn_summary = f"🦅 30d WARN: {client}{amount_str}"
                warn_desc = f"30-day warning: {message}\n\nFinal trigger: {trigger_date}"
                if dry_run:
                    print(f"  [DRY RUN] {warn_date} (30d warn): {warn_summary}")
                elif not event_exists(svc, warn_date, warn_summary[:25]):
                    create_event(svc, warn_summary, warn_date, warn_desc, "5")
                    created += 1
        except ValueError:
            pass

    # ── Open tasks with dates ────────────────────────────────────────────────
    print("\nKey mission deadlines:")
    task_dates = {
        "2026-06-17": ("🦅 P0: Kuklinski air fare watch", "A2 Dembe: Run fare watch for Kuklinski Panama Canal Dec 17. Check DEN/CO Springs to Panama City + FLL return."),
        "2026-06-17": ("🦅 P0: Kuklinski hotel 3+3 search", "A2 Dembe: Run 3-night pre/post hotel search for Kyle, Roger, Josh (Panama City + Fort Lauderdale)."),
        "2026-07-15": ("🦅 P0: Kuklinski lifecycle UNHOLD", "Release Kuklinski lifecycle drafts: Welcome TP0.5, Specialty Dining TP4.1, Excursion TP4.2, Pre-Departure TP4.3. Commander order 2026-06-04."),
        "2026-08-02": ("🦅 P1: Kuklinski excursion window opens", "Viking portal excursion booking window opens today for Viking Mars Panama Canal Dec 17."),
        "2026-09-18": ("🦅 P2: Kuklinski dining window opens", "Viking portal specialty dining opens T-90 for Dec 17 departure."),
        "2026-06-23": ("🦅 P0: McLeod DEPARTURE Silver Muse", "Erik McLeod + party depart on Silver Muse Mediterranean. T-0. Verify all logistics complete."),
    }

    for date_str, (summary, desc) in task_dates.items():
        if dry_run:
            print(f"  [DRY RUN] {date_str}: {summary}")
        elif not event_exists(svc, date_str, summary[:25]):
            priority = "11" if "P0" in summary else "6" if "P1" in summary else "5"
            create_event(svc, summary, date_str, desc, priority)
            created += 1
        else:
            print(f"  ⏭ Skip (exists): {date_str}: {summary}")
            skipped += 1

    print(f"\n{'[DRY RUN] Would create' if dry_run else 'Done —'} {created} events created, {skipped} skipped.")
    print("Calendar: johnloucks3 primary (confirmed 2026-06-14)")


if __name__ == "__main__":
    main()
