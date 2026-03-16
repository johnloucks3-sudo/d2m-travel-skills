"""
Thunderbird Calendar Sync — Booking Milestone Events
Dreams2Memories Travel, LLC

Reads booking data from the "Booking Master B" tab of the EARA Google Sheet
and creates Google Calendar events for key milestones:
  - Final Payment Due (red, all-day)
  - Embarkation Day (blue, all-day)
  - Disembarkation Day (blue, all-day)
  - Document Deadline (yellow, 45 days before embarkation)

Deduplicates via calendar_sync_state.json to avoid creating duplicate events.

Auth strategy:
  - Calendar: OAuth 2.0 Desktop flow (separate token from Gmail)
    If calendar token doesn't exist, falls back to service account.
  - Sheets: Service account via gspread (same pattern as other modules)

Usage:
  python3 thunderbird_calendar_sync.py                # Sync all bookings
  python3 thunderbird_calendar_sync.py --dry-run      # Preview without creating events
  python3 thunderbird_calendar_sync.py --authorize     # One-time OAuth for Calendar
  python3 thunderbird_calendar_sync.py --status        # Show sync state
"""

import json
import logging
import sys
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Optional

import gspread
from google.oauth2 import service_account as sa_credentials
from google.oauth2.credentials import Credentials as OAuthCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
CREDENTIALS_FILE = THUNDERBIRD_DIR / "credentials.json"           # Service account
OAUTH_CREDENTIALS_FILE = THUNDERBIRD_DIR / "gmail_oauth_credentials.json"
CALENDAR_TOKEN_FILE = THUNDERBIRD_DIR / "calendar_token.json"     # Separate from Gmail
SYNC_STATE_FILE = THUNDERBIRD_DIR / "calendar_sync_state.json"

SHEET_ID = "1GFjUe8RvP-GT4YHGn0DYv_BEAZGXlYfwEicFrm8ANuU"
SHEET_TAB = "Booking Master B"

CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar"]
SHEETS_SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

# Calendar to write events to — John's primary
CALENDAR_ID = "primary"

# Timezone for all events
TIMEZONE = "America/Denver"

# Google Calendar colorId reference (for all-day events):
#   1=Lavender, 2=Sage, 3=Grape, 4=Flamingo, 5=Banana,
#   6=Tangerine, 7=Peacock, 8=Graphite, 9=Blueberry, 10=Basil, 11=Tomato
COLOR_FINAL_PAYMENT = "11"   # Tomato (red)
COLOR_EMBARKATION = "9"      # Blueberry (blue)
COLOR_DISEMBARKATION = "9"   # Blueberry (blue)
COLOR_DOCUMENT_DEADLINE = "5"  # Banana (yellow)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# AUTH: Calendar API
# ---------------------------------------------------------------------------

_calendar_service = None


def _get_calendar_service():
    """Return a cached Google Calendar API service.

    Strategy:
      1. Try OAuth token (calendar_token.json) — writes to John's personal calendar
      2. Fall back to service account (credentials.json) — writes to service account's calendar
    """
    global _calendar_service
    if _calendar_service is not None:
        return _calendar_service

    # Strategy 1: OAuth token
    if CALENDAR_TOKEN_FILE.exists():
        creds = OAuthCredentials.from_authorized_user_file(
            str(CALENDAR_TOKEN_FILE), CALENDAR_SCOPES
        )
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                CALENDAR_TOKEN_FILE.write_text(creds.to_json())
            except Exception as e:
                logger.warning(f"Calendar OAuth token refresh failed: {e}")
                creds = None

        if creds and creds.valid:
            _calendar_service = build("calendar", "v3", credentials=creds)
            logger.info("Calendar service: OAuth (personal calendar)")
            return _calendar_service

    # Strategy 2: Service account fallback
    if CREDENTIALS_FILE.exists():
        creds = sa_credentials.Credentials.from_service_account_file(
            str(CREDENTIALS_FILE), scopes=CALENDAR_SCOPES
        )
        _calendar_service = build("calendar", "v3", credentials=creds)
        logger.info("Calendar service: service account (shared calendar)")
        return _calendar_service

    raise RuntimeError(
        "No Calendar credentials found.\n"
        f"  Option 1: Run  python3 thunderbird_calendar_sync.py --authorize\n"
        f"  Option 2: Ensure service account file exists at {CREDENTIALS_FILE}"
    )


def authorize_calendar():
    """Run one-time OAuth 2.0 flow for Google Calendar access.

    Opens browser for consent, saves refresh token to calendar_token.json.
    """
    if not OAUTH_CREDENTIALS_FILE.exists():
        print(f"ERROR: OAuth credentials file not found: {OAUTH_CREDENTIALS_FILE}")
        print()
        print("This is the same OAuth client used for Gmail.")
        print("Download it from console.cloud.google.com > d2m-python-pipeline")
        print(f"Save as: {OAUTH_CREDENTIALS_FILE}")
        return False

    flow = InstalledAppFlow.from_client_secrets_file(
        str(OAUTH_CREDENTIALS_FILE), CALENDAR_SCOPES
    )
    creds = flow.run_local_server(port=0)
    CALENDAR_TOKEN_FILE.write_text(creds.to_json())
    print(f"Calendar authorization successful! Token saved to {CALENDAR_TOKEN_FILE}")
    return True


# ---------------------------------------------------------------------------
# AUTH: Google Sheets (service account via gspread)
# ---------------------------------------------------------------------------

def _get_sheets_client():
    """Return an authorized gspread client using the service account."""
    creds = sa_credentials.Credentials.from_service_account_file(
        str(CREDENTIALS_FILE),
        scopes=SHEETS_SCOPES,
    )
    return gspread.authorize(creds)


# ---------------------------------------------------------------------------
# SYNC STATE: Track created events to avoid duplicates
# ---------------------------------------------------------------------------

def _load_sync_state() -> dict:
    """Load the sync state from disk. Returns {event_key: {calendar_event_id, created_at}}."""
    if SYNC_STATE_FILE.exists():
        try:
            return json.loads(SYNC_STATE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Corrupt sync state file, starting fresh: {e}")
    return {}


def _save_sync_state(state: dict):
    """Persist sync state to disk."""
    SYNC_STATE_FILE.write_text(
        json.dumps(state, indent=2, default=str),
        encoding="utf-8",
    )


def _event_key(booking_id: str, milestone: str) -> str:
    """Generate a unique dedup key for a booking milestone."""
    return f"{booking_id}::{milestone}"


# ---------------------------------------------------------------------------
# DATE PARSING
# ---------------------------------------------------------------------------

def _parse_date(s: str) -> Optional[date]:
    """Parse dates in various formats from the EARA spreadsheet."""
    if not s or s.strip() in ("", "Pending", "#NUM!", "TBD", "N/A"):
        return None
    for fmt in ("%Y-%m-%d", "%d-%b-%y", "%d-%b-%Y", "%m/%d/%Y", "%d%b%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# READ BOOKINGS FROM GOOGLE SHEETS
# ---------------------------------------------------------------------------

def read_bookings() -> list[dict]:
    """Read all bookings from the Booking Master B tab.

    Returns list of dicts with raw spreadsheet column names as keys.
    Filters out rows missing Client_Name or Start_Date.
    """
    gc = _get_sheets_client()
    sheet = gc.open_by_key(SHEET_ID)
    ws = sheet.worksheet(SHEET_TAB)

    # get_all_records uses row 1 as headers
    records = ws.get_all_records()

    bookings = []
    for row in records:
        client = str(row.get("Client_Name", "")).strip()
        start = str(row.get("Start_Date", "")).strip()
        if client and start:
            bookings.append(row)

    logger.info(f"Read {len(bookings)} bookings from '{SHEET_TAB}'")
    return bookings


# ---------------------------------------------------------------------------
# BUILD MILESTONE EVENTS FROM A BOOKING ROW
# ---------------------------------------------------------------------------

def _build_milestones(row: dict) -> list[dict]:
    """Build calendar event dicts for a single booking row.

    Returns a list of milestone dicts, each with:
      key, summary, description, date, colorId
    """
    client = str(row.get("Client_Name", "Unknown")).strip()
    supplier = str(row.get("Supplier", "")).strip()
    conf = str(row.get("Confirmation_Number", "")).strip()
    ship = str(row.get("Ship", "")).strip()
    balance = str(row.get("Balance_Due", "")).strip()

    # Build booking identifier for dedup key
    booking_id = conf if conf else f"{client}_{supplier}"

    embark = _parse_date(str(row.get("Start_Date", "")))
    disembark = _parse_date(str(row.get("End_Date", "")))
    fpd = _parse_date(str(row.get("Final_Payment_Date", "")))

    label_parts = [client]
    if supplier:
        label_parts.append(supplier)
    if ship:
        label_parts.append(ship)
    if conf:
        label_parts.append(f"#{conf}")
    booking_label = " | ".join(label_parts)

    # Embarkation port — check several possible column names
    embark_port = ""
    for col in ("Embark_Port", "Embarkation_Port", "Departure_Port", "Port"):
        val = str(row.get(col, "")).strip()
        if val:
            embark_port = val
            break

    milestones = []

    # 1. Final Payment Due
    if fpd:
        amount_note = f"\nBalance Due: {balance}" if balance else ""
        milestones.append({
            "key": _event_key(booking_id, "final_payment"),
            "summary": f"FINAL PAYMENT DUE — {booking_label}",
            "description": (
                f"Final payment deadline for {client}.\n"
                f"Supplier: {supplier}\n"
                f"Confirmation: {conf}\n"
                f"Ship: {ship}"
                f"{amount_note}\n\n"
                f"Generated by Thunderbird OS Calendar Sync"
            ),
            "date": fpd,
            "colorId": COLOR_FINAL_PAYMENT,
        })

    # 2. Embarkation Day
    if embark:
        port_note = f" from {embark_port}" if embark_port else ""
        milestones.append({
            "key": _event_key(booking_id, "embarkation"),
            "summary": f"EMBARKATION — {booking_label}",
            "description": (
                f"Embarkation day for {client}{port_note}.\n"
                f"Ship: {ship}\n"
                f"Supplier: {supplier}\n"
                f"Confirmation: {conf}\n\n"
                f"Generated by Thunderbird OS Calendar Sync"
            ),
            "date": embark,
            "colorId": COLOR_EMBARKATION,
        })

    # 3. Disembarkation Day
    if disembark:
        milestones.append({
            "key": _event_key(booking_id, "disembarkation"),
            "summary": f"DISEMBARKATION — {booking_label}",
            "description": (
                f"Disembarkation day for {client}.\n"
                f"Ship: {ship}\n"
                f"Supplier: {supplier}\n"
                f"Confirmation: {conf}\n\n"
                f"Generated by Thunderbird OS Calendar Sync"
            ),
            "date": disembark,
            "colorId": COLOR_DISEMBARKATION,
        })

    # 4. Document Deadline (E-45)
    if embark:
        doc_deadline = embark - timedelta(days=45)
        milestones.append({
            "key": _event_key(booking_id, "document_deadline"),
            "summary": f"DOC DEADLINE (E-45) — {booking_label}",
            "description": (
                f"All travel documents must be confirmed for {client}.\n"
                f"45 days before embarkation ({embark.isoformat()}).\n"
                f"Ship: {ship}\n"
                f"Supplier: {supplier}\n"
                f"Confirmation: {conf}\n\n"
                f"Check: passports, visas, boarding forms, insurance.\n\n"
                f"Generated by Thunderbird OS Calendar Sync"
            ),
            "date": doc_deadline,
            "colorId": COLOR_DOCUMENT_DEADLINE,
        })

    return milestones


# ---------------------------------------------------------------------------
# CREATE CALENDAR EVENTS
# ---------------------------------------------------------------------------

def _create_all_day_event(service, milestone: dict) -> Optional[str]:
    """Create a single all-day calendar event. Returns the event ID or None."""
    event_date = milestone["date"]
    event_body = {
        "summary": milestone["summary"],
        "description": milestone["description"],
        "start": {
            "date": event_date.isoformat(),
            "timeZone": TIMEZONE,
        },
        "end": {
            "date": (event_date + timedelta(days=1)).isoformat(),
            "timeZone": TIMEZONE,
        },
        "colorId": milestone["colorId"],
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "popup", "minutes": 7 * 24 * 60},   # 7 days before
                {"method": "popup", "minutes": 3 * 24 * 60},   # 3 days before
                {"method": "popup", "minutes": 1 * 24 * 60},   # 1 day before
                {"method": "email", "minutes": 7 * 24 * 60},   # 7 days before
            ],
        },
    }

    try:
        event = service.events().insert(
            calendarId=CALENDAR_ID,
            body=event_body,
        ).execute()
        return event.get("id")
    except HttpError as e:
        logger.error(f"Calendar API error creating '{milestone['summary']}': {e}")
        # Retry once for transient errors
        if e.resp.status in (429, 500, 503):
            import time
            time.sleep(2)
            try:
                event = service.events().insert(
                    calendarId=CALENDAR_ID,
                    body=event_body,
                ).execute()
                return event.get("id")
            except HttpError:
                pass
        return None


# ---------------------------------------------------------------------------
# MAIN SYNC FUNCTION
# ---------------------------------------------------------------------------

def sync_bookings_to_calendar(dry_run: bool = False) -> dict:
    """Read bookings from Google Sheets and create calendar events for milestones.

    Deduplicates using calendar_sync_state.json — safe to call repeatedly.

    Args:
        dry_run: If True, log what would be created but don't touch the calendar.

    Returns:
        Summary dict with counts of created, skipped, and errored events.
    """
    # Read bookings
    bookings = read_bookings()
    if not bookings:
        return {
            "status": "no_bookings",
            "message": f"No valid bookings found in '{SHEET_TAB}'",
        }

    # Load sync state
    state = _load_sync_state()

    # Get calendar service (unless dry run)
    service = None
    if not dry_run:
        service = _get_calendar_service()

    created = 0
    skipped = 0
    errored = 0
    details = []

    for row in bookings:
        milestones = _build_milestones(row)
        for ms in milestones:
            key = ms["key"]

            # Skip if already synced
            if key in state:
                skipped += 1
                continue

            # Skip past dates (more than 7 days ago)
            if ms["date"] < date.today() - timedelta(days=7):
                skipped += 1
                continue

            if dry_run:
                details.append({
                    "action": "would_create",
                    "summary": ms["summary"],
                    "date": ms["date"].isoformat(),
                })
                created += 1
                continue

            # Create the event
            event_id = _create_all_day_event(service, ms)
            if event_id:
                state[key] = {
                    "calendar_event_id": event_id,
                    "created_at": datetime.now().isoformat(),
                    "summary": ms["summary"],
                    "date": ms["date"].isoformat(),
                }
                created += 1
                details.append({
                    "action": "created",
                    "summary": ms["summary"],
                    "date": ms["date"].isoformat(),
                    "event_id": event_id,
                })
                logger.info(f"  Created: {ms['summary']} ({ms['date']})")
            else:
                errored += 1
                details.append({
                    "action": "error",
                    "summary": ms["summary"],
                    "date": ms["date"].isoformat(),
                })

    # Persist state
    if not dry_run and created > 0:
        _save_sync_state(state)

    result = {
        "status": "success",
        "dry_run": dry_run,
        "bookings_processed": len(bookings),
        "events_created": created,
        "events_skipped": skipped,
        "events_errored": errored,
        "sync_state_file": str(SYNC_STATE_FILE),
        "details": details,
    }

    mode = "DRY RUN" if dry_run else "LIVE"
    logger.info(
        f"\n[{mode}] Sync complete: "
        f"{created} created, {skipped} skipped, {errored} errors "
        f"({len(bookings)} bookings processed)"
    )

    return result


def show_sync_status():
    """Print current sync state summary."""
    state = _load_sync_state()
    if not state:
        print("No events synced yet. Run:  python3 thunderbird_calendar_sync.py")
        return

    print(f"Calendar Sync State — {len(state)} events tracked")
    print(f"State file: {SYNC_STATE_FILE}")
    print("-" * 80)

    for key, info in sorted(state.items(), key=lambda x: x[1].get("date", "")):
        print(
            f"  {info.get('date', '?'):12s}  "
            f"{info.get('summary', key)[:60]:60s}  "
            f"[{info.get('calendar_event_id', '?')[:12]}]"
        )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    if "--authorize" in sys.argv:
        authorize_calendar()
    elif "--status" in sys.argv:
        show_sync_status()
    elif "--dry-run" in sys.argv:
        result = sync_bookings_to_calendar(dry_run=True)
        print(json.dumps(result, indent=2, default=str))
    else:
        result = sync_bookings_to_calendar(dry_run=False)
        print(json.dumps(result, indent=2, default=str))
