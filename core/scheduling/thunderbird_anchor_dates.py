"""
Thunderbird Anchor Date Engine
Dreams2Memories Travel, LLC

Computes T-minus milestones from three anchor origins:
  - Booking Date (B): drives insurance windows, client qualification forms
  - Embark Date (E): drives most client care milestones
  - Final Payment Date (FPD): drives payment reminders
  - Disembark Date (D): drives post-trip follow-up

Also manages HARD dates from supplier invoices (dining opens, excursion opens, etc.)
and syncs everything to Google Calendar + EARA spreadsheet.

A3-Moreau (Operations) owns the daily scan.
"""

import os
import sys
import json
from datetime import datetime, timedelta, date
from typing import Optional

# Google API imports
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------

CREDENTIALS_PATH = os.path.join(os.path.dirname(__file__), "credentials.json")
EARA_SHEET_ID = "1GFjUe8RvP-GT4YHGn0DYv_BEAZGXlYfwEicFrm8ANuU"
CALENDAR_EMAIL = "jbzsolutionsllc@gmail.com"

SCOPES_SHEETS = ["https://www.googleapis.com/auth/spreadsheets"]
SCOPES_CALENDAR = ["https://www.googleapis.com/auth/calendar"]

# Anchor date definitions: (label, origin, offset_days, category, reminder_days)
# origin: 'E' = embark, 'D' = disembark, 'FPD' = final payment, 'B' = booking
# reminder_days: list of days before the anchor to fire calendar reminders

ANCHOR_TEMPLATE = [
    # BOOKING-DATE ANCHORS
    ("Insurance pre-existing window closes", "B", 15, "insurance", [3, 1]),

    # PAYMENT ANCHORS (relative to FPD)
    ("Payment reminder #1 (FPD-21)", "FPD", -21, "payment", [1]),
    ("Payment reminder #2 (FPD-14)", "FPD", -14, "payment", [1]),
    ("Goal: payment in hand (FPD-7)", "FPD", -7, "payment", [1]),
    ("FINAL PAYMENT DUE", "FPD", 0, "payment", [7, 3, 1]),
    ("Confirm payment received (FPD+7)", "FPD", 7, "payment", [1]),

    # EMBARK-DATE ANCHORS
    ("E-270: Passport validity check (6-month rule)", "E", -270, "documents", [7]),
    ("E-180: Insurance decision deadline", "E", -180, "insurance", [14, 7]),
    ("E-150: Guest Info Forms due", "E", -150, "documents", [14, 7]),
    ("E-120: Pre-trip call / planning session", "E", -120, "client_care", [14, 7]),
    ("E-90: All docs confirmed, ancillary bookings locked", "E", -90, "documents", [7]),
    ("E-30: Final itinerary PDF delivered", "E", -30, "deliverable", [7, 3]),
    ("E-30 to E-3: Operational window (flights, weather, State Dept, dining)", "E", -30, "operations", []),
    ("E-14: Bon Voyage package / final check-in", "E", -14, "client_care", [7, 3]),
    ("EMBARKATION DAY", "E", 0, "milestone", [14, 7, 3, 1]),

    # DISEMBARK-DATE ANCHORS
    ("DISEMBARKATION DAY", "D", 0, "milestone", []),
    ("D+7: Welcome Home email", "D", 7, "client_care", [1]),
    ("D+14: Review request (TripAdvisor, Google)", "D", 14, "client_care", [1]),
    ("D+30: Next trip conversation + commission audit", "D", 30, "business", [7, 1]),
]


# ---------------------------------------------------------------------------
# CORE: Compute anchors for a booking
# ---------------------------------------------------------------------------

def compute_anchors(
    booking_date: date,
    embark_date: date,
    disembark_date: date,
    final_payment_date: date,
    hard_dates: Optional[dict] = None,
    booking_label: str = "",
) -> list[dict]:
    """
    Compute all anchor dates for a booking.

    Args:
        booking_date: Date booking was made
        embark_date: Embarkation date
        disembark_date: Disembarkation date
        final_payment_date: Final payment due date
        hard_dates: Dict of {label: date} for supplier-specified dates
                    e.g. {"Specialty Dining Opens": date(2026, 5, 31)}
        booking_label: Human-readable booking identifier

    Returns:
        List of dicts with keys: label, date, category, origin, reminder_days, source, booking
    """
    origins = {
        "B": booking_date,
        "E": embark_date,
        "D": disembark_date,
        "FPD": final_payment_date,
    }

    anchors = []

    # Computed anchors from template
    for label, origin, offset, category, reminders in ANCHOR_TEMPLATE:
        base = origins[origin]
        anchor_date = base + timedelta(days=offset)
        anchors.append({
            "label": label,
            "date": anchor_date,
            "category": category,
            "origin": origin,
            "offset": offset,
            "reminder_days": reminders,
            "source": "computed",
            "booking": booking_label,
        })

    # Hard dates from invoices
    if hard_dates:
        for label, hdate in hard_dates.items():
            if isinstance(hdate, str):
                for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%d-%b-%y", "%m/%d/%Y"):
                    try:
                        hdate = datetime.strptime(hdate, fmt).date()
                        break
                    except ValueError:
                        continue
            anchors.append({
                "label": f"HARD: {label}",
                "date": hdate,
                "category": "supplier",
                "origin": "invoice",
                "offset": None,
                "reminder_days": [14, 7, 1],
                "source": "invoice",
                "booking": booking_label,
            })

    # Sort chronologically
    anchors.sort(key=lambda a: a["date"])
    return anchors


def anchors_due_in_window(anchors: list[dict], start: date, end: date) -> list[dict]:
    """Filter anchors to those falling within a date window."""
    return [a for a in anchors if start <= a["date"] <= end]


def scan_all_bookings_due(all_booking_anchors: dict, today: date = None) -> dict:
    """
    Scan all bookings for anchors due today, this week, next 2 weeks.
    Returns a report dict suitable for A3-Moreau briefing.

    Args:
        all_booking_anchors: {booking_label: [anchor_list]}
        today: Override for testing
    """
    if today is None:
        today = date.today()

    week_end = today + timedelta(days=7)
    two_week_end = today + timedelta(days=14)

    report = {
        "scan_date": today.isoformat(),
        "overdue": [],
        "due_today": [],
        "due_this_week": [],
        "due_next_week": [],
        "upcoming_14_days": [],
    }

    for booking_label, anchors in all_booking_anchors.items():
        for a in anchors:
            adate = a["date"]
            entry = {**a, "date": adate.isoformat()}

            if adate < today:
                # Only flag overdue if it's a milestone or payment
                if a["category"] in ("payment", "milestone", "documents", "deliverable"):
                    report["overdue"].append(entry)
            elif adate == today:
                report["due_today"].append(entry)
            elif today < adate <= week_end:
                report["due_this_week"].append(entry)
            elif week_end < adate <= two_week_end:
                report["due_next_week"].append(entry)

        # Also collect everything in 14-day window
        window = anchors_due_in_window(anchors, today, two_week_end)
        for a in window:
            entry = {**a, "date": a["date"].isoformat()}
            report["upcoming_14_days"].append(entry)

    return report


# ---------------------------------------------------------------------------
# GOOGLE SHEETS: Read bookings + write anchor dates
# ---------------------------------------------------------------------------

def _get_sheets_service():
    creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES_SHEETS)
    return build("sheets", "v4", credentials=creds)


def read_bookings_from_sheet(tab_name: str = "Booking Master B") -> list[dict]:
    """Read booking rows from EARA spreadsheet and return as list of dicts."""
    service = _get_sheets_service()
    result = service.spreadsheets().values().get(
        spreadsheetId=EARA_SHEET_ID,
        range=f"'{tab_name}'!A1:Z100",
    ).execute()
    rows = result.get("values", [])
    if not rows:
        return []
    headers = rows[0]
    bookings = []
    for row in rows[1:]:
        d = {}
        for i, h in enumerate(headers):
            d[h] = row[i] if i < len(row) else ""
        if d.get("Client_Name") and d.get("Start_Date"):
            bookings.append(d)
    return bookings


def _parse_date_flexible(s: str) -> Optional[date]:
    """Parse dates in various formats found in the EARA sheet."""
    if not s or s in ("Pending", "", "#NUM!"):
        return None
    for fmt in ("%Y-%m-%d", "%d-%b-%y", "%d-%b-%Y", "%m/%d/%Y", "%d%b%Y"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    return None


def compute_anchors_from_sheet_row(row: dict, hard_dates: Optional[dict] = None) -> list[dict]:
    """Compute anchors from a single EARA spreadsheet row."""
    embark = _parse_date_flexible(row.get("Start_Date", ""))
    disembark = _parse_date_flexible(row.get("End_Date", ""))
    fpd = _parse_date_flexible(row.get("Final_Payment_Date", ""))
    booking_date = _parse_date_flexible(row.get("Created_Date", ""))

    if not embark:
        return []

    # Defaults if missing
    if not disembark and embark:
        disembark = embark + timedelta(days=10)
    if not fpd and embark:
        fpd = embark - timedelta(days=90)
    if not booking_date:
        booking_date = date.today()

    client = row.get("Client_Name", "Unknown")
    conf = row.get("Confirmation_Number", "")
    supplier = row.get("Supplier", "")
    label = f"{client} | {supplier} {conf}".strip()

    return compute_anchors(booking_date, embark, disembark, fpd, hard_dates, label)


# ---------------------------------------------------------------------------
# GOOGLE CALENDAR: Create events with reminders
# ---------------------------------------------------------------------------

def _get_calendar_service():
    creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES_CALENDAR)
    return build("calendar", "v3", credentials=creds)


def _ensure_d2m_calendar(service) -> str:
    """Find or create the D2M Anchor Dates calendar. Return calendar ID."""
    cals = service.calendarList().list().execute()
    for c in cals.get("items", []):
        if c.get("summary") == "D2M Anchor Dates":
            return c["id"]

    # Create it
    cal = service.calendars().insert(body={
        "summary": "D2M Anchor Dates",
        "description": "Thunderbird OS — automated booking milestone calendar",
        "timeZone": "America/Denver",
    }).execute()
    cal_id = cal["id"]

    # Share with John's calendar email
    try:
        service.acl().insert(calendarId=cal_id, body={
            "role": "writer",
            "scope": {"type": "user", "value": CALENDAR_EMAIL},
        }).execute()
    except Exception as e:
        print(f"Warning: Could not share calendar with {CALENDAR_EMAIL}: {e}", file=sys.stderr)

    # Also share with personal email
    try:
        service.acl().insert(calendarId=cal_id, body={
            "role": "writer",
            "scope": {"type": "user", "value": "johnloucks3@gmail.com"},
        }).execute()
    except Exception as e:
        print(f"Warning: Could not share calendar with johnloucks3@gmail.com: {e}", file=sys.stderr)

    return cal_id


def sync_anchors_to_calendar(anchors: list[dict], booking_label: str = "") -> dict:
    """
    Push anchor dates to Google Calendar as all-day events with reminders.
    Returns summary of created/skipped events.
    """
    service = _get_calendar_service()
    cal_id = _ensure_d2m_calendar(service)

    created = 0
    skipped = 0

    # Get existing events to avoid duplicates (search by summary prefix)
    today_str = date.today().isoformat()

    for anchor in anchors:
        adate = anchor["date"]
        # Skip past dates
        if adate < date.today() - timedelta(days=7):
            skipped += 1
            continue

        summary = f"[{anchor['category'].upper()}] {anchor['label']}"
        if anchor["booking"]:
            summary += f" — {anchor['booking']}"

        # Color by category
        color_map = {
            "payment": "11",      # red
            "milestone": "9",     # blue
            "documents": "5",     # yellow
            "insurance": "6",     # orange
            "client_care": "2",   # green
            "deliverable": "10",  # dark green
            "supplier": "3",      # purple
            "operations": "8",    # graphite
            "business": "7",      # cyan
        }

        # Build reminders from anchor config
        reminder_overrides = []
        for days_before in anchor.get("reminder_days", []):
            reminder_overrides.append({
                "method": "popup",
                "minutes": days_before * 24 * 60,
            })
            reminder_overrides.append({
                "method": "email",
                "minutes": days_before * 24 * 60,
            })

        event_body = {
            "summary": summary,
            "description": (
                f"Booking: {anchor.get('booking', '')}\n"
                f"Category: {anchor['category']}\n"
                f"Source: {anchor['source']}\n"
                f"Origin: {anchor['origin']} {anchor.get('offset', '')}\n"
                f"\nGenerated by Thunderbird OS Anchor Date Engine"
            ),
            "start": {"date": adate.isoformat()},
            "end": {"date": (adate + timedelta(days=1)).isoformat()},
            "colorId": color_map.get(anchor["category"], "8"),
            "transparency": "transparent",  # Show as "Free" — reminders, not meetings
            "conferenceData": None,  # Explicitly suppress Google Meet link
            "reminders": {
                "useDefault": False,
                "overrides": reminder_overrides[:5],  # Calendar API max 5 reminders
            },
        }

        try:
            service.events().insert(calendarId=cal_id, body=event_body).execute()
            created += 1
        except Exception as e:
            print(f"Warning: Could not create event '{summary}': {e}", file=sys.stderr)
            skipped += 1

    return {
        "status": "success",
        "calendar_id": cal_id,
        "calendar_email": CALENDAR_EMAIL,
        "events_created": created,
        "events_skipped": skipped,
        "booking": booking_label,
    }


# ---------------------------------------------------------------------------
# A3 MOREAU DAILY BRIEFING
# ---------------------------------------------------------------------------

def generate_a3_briefing(all_booking_anchors: dict, today: date = None) -> str:
    """Generate A3-Moreau's daily operations briefing as formatted text."""
    report = scan_all_bookings_due(all_booking_anchors, today)

    lines = [
        "# A3-MOREAU OPERATIONS BRIEFING",
        f"## Date: {report['scan_date']}",
        "",
    ]

    if report["overdue"]:
        lines.append("### OVERDUE")
        for a in report["overdue"]:
            lines.append(f"- **{a['label']}** — {a['booking']} (was due {a['date']})")
        lines.append("")

    if report["due_today"]:
        lines.append("### DUE TODAY")
        for a in report["due_today"]:
            lines.append(f"- **{a['label']}** — {a['booking']}")
        lines.append("")

    if report["due_this_week"]:
        lines.append("### DUE THIS WEEK")
        for a in report["due_this_week"]:
            lines.append(f"- {a['date']}: {a['label']} — {a['booking']}")
        lines.append("")

    if report["due_next_week"]:
        lines.append("### NEXT WEEK")
        for a in report["due_next_week"]:
            lines.append(f"- {a['date']}: {a['label']} — {a['booking']}")
        lines.append("")

    if not any([report["overdue"], report["due_today"], report["due_this_week"], report["due_next_week"]]):
        lines.append("All clear — no anchors due in the next 14 days.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# KNOWN BOOKINGS: Hard-coded from invoice data we've already extracted
# ---------------------------------------------------------------------------

KNOWN_BOOKINGS = {
    "McLeod_Silversea_298475": {
        "client": "Erik McLeod & Melissa McGlasson",
        "supplier": "Silversea",
        "ship": "Silver Muse",
        "conf": "298475-25",
        "booking_date": date(2025, 3, 4),
        "embark_date": date(2026, 6, 23),
        "disembark_date": date(2026, 7, 3),
        "fpd": date(2026, 1, 24),
        "fpd_status": "PAID",
        "hard_dates": {
            "Specialty Dining Opens": date(2026, 2, 23),
            "Shore Excursions Available": date(2026, 1, 31),
            "Pre-cruise transfer Airport→Pier": date(2026, 6, 23),
            "Post-cruise transfer Pier→Airport": date(2026, 7, 3),
            "Blacklane transfer email arrives (~E-28)": date(2026, 5, 26),
            "Transfer cancel = 100%": date(2026, 6, 18),
            "Cancel penalty 25% begins": date(2026, 2, 23),
            "Cancel penalty 50% begins": date(2026, 3, 25),
            "Cancel penalty 75% begins": date(2026, 4, 24),
            "Cancel penalty 100% begins": date(2026, 5, 24),
        },
    },
    "Furlow_Regent_3071222": {
        "client": "John & Melissa Furlow",
        "supplier": "Regent",
        "ship": "SS Grandeur",
        "conf": "3071222",
        "booking_date": date(2025, 9, 10),
        "embark_date": date(2026, 8, 29),
        "disembark_date": date(2026, 9, 8),
        "fpd": date(2026, 4, 1),
        "fpd_status": "PENDING",
        "hard_dates": {
            "Shore Excursions Open": date(2026, 1, 31),
            "Specialty Dining Opens": date(2026, 5, 31),
            "Excursions/dining close (E-7)": date(2026, 8, 22),
            "Cancel penalty 15% begins": date(2026, 4, 1),
            "Cancel penalty 50% begins": date(2026, 5, 1),
            "Cancel penalty 75% begins": date(2026, 5, 31),
            "Cancel penalty 100% begins": date(2026, 6, 15),
            "Ancillary cancel 100% (hotels, land, air) E-90": date(2026, 6, 1),
            "Bedsonline transfer free cancel": date(2026, 8, 23),
            "Bedsonline hotel free cancel": date(2026, 8, 24),
            "Haymarket check-in": date(2026, 8, 27),
            "Regent included hotel night": date(2026, 8, 28),
        },
    },
    "***REMOVED-SECRET***": {
        "client": "Al Ely & Amy Darrow",
        "supplier": "Regent",
        "ship": "SS Grandeur",
        "conf": "3096289",
        "booking_date": date(2025, 11, 13),
        "embark_date": date(2026, 8, 29),
        "disembark_date": date(2026, 9, 8),
        "fpd": date(2026, 4, 1),
        "fpd_status": "PENDING",
        "hard_dates": {
            "Shore Excursions Open": date(2026, 1, 31),
            "Specialty Dining Opens": date(2026, 5, 31),
            "Excursions/dining close (E-7)": date(2026, 8, 22),
            "Cancel penalty 15% begins": date(2026, 4, 1),
            "Cancel penalty 50% begins": date(2026, 5, 1),
            "Cancel penalty 75% begins": date(2026, 5, 31),
            "Cancel penalty 100% begins": date(2026, 6, 15),
            "Ancillary cancel 100% (hotels, land, air) E-90": date(2026, 6, 1),
            "Bedsonline transfer free cancel": date(2026, 8, 23),
            "Bedsonline hotel free cancel": date(2026, 8, 24),
            "Ely/Darrow flight DFW→Helsinki": date(2026, 8, 26),
            "Haymarket check-in": date(2026, 8, 27),
            "Regent included hotel night": date(2026, 8, 28),
            "Ely/Darrow return Oslo→London→Dallas": date(2026, 9, 8),
        },
    },
    "Nichols_Regent_3078056": {
        "client": "Larry & Heidi Nichols",
        "supplier": "Regent",
        "ship": "SS Grandeur",
        "conf": "3078056",
        "booking_date": date(2025, 9, 26),
        "embark_date": date(2026, 8, 29),
        "disembark_date": date(2026, 9, 8),
        "fpd": date(2026, 4, 1),
        "fpd_status": "PENDING",
        "hard_dates": {
            "Shore Excursions Open": date(2026, 1, 31),
            "Specialty Dining Opens": date(2026, 5, 31),
            "Excursions/dining close (E-7)": date(2026, 8, 22),
            "Cancel penalty 15% begins": date(2026, 4, 1),
            "Cancel penalty 50% begins": date(2026, 5, 1),
            "Cancel penalty 75% begins": date(2026, 5, 31),
            "Cancel penalty 100% begins": date(2026, 6, 15),
            "Ancillary cancel 100% (hotels, land, air) E-90": date(2026, 6, 1),
            "Bedsonline transfer free cancel": date(2026, 8, 23),
            "Bedsonline hotel free cancel": date(2026, 8, 24),
            "Haymarket check-in": date(2026, 8, 27),
            "Regent included hotel night": date(2026, 8, 28),
            "Heidi Nichols birthday": date(2026, 8, 29),
        },
    },
    "Kuklinski1_Viking_9593880": {
        "client": "Kyle & Rosalie Kuklinski",
        "supplier": "Viking",
        "ship": "Viking Mars",
        "conf": "9593880",
        "booking_date": date(2026, 2, 7),
        "embark_date": date(2026, 12, 17),
        "disembark_date": date(2026, 12, 27),
        "fpd": date(2026, 3, 31),
        "fpd_status": "PENDING",
        "hard_dates": {
            "Cancel penalty 20% begins (E-119)": date(2026, 8, 20),
            "Cancel penalty 35% begins (E-89)": date(2026, 9, 19),
            "Cancel penalty 50% begins (E-69)": date(2026, 10, 9),
            "Cancel penalty 75% begins (E-49)": date(2026, 10, 29),
            "Cancel penalty 100% begins (E-29)": date(2026, 11, 18),
        },
    },
    "Kuklinski2_Viking_9593873": {
        "client": "Roger & Dr Nicholas Kuklinski",
        "supplier": "Viking",
        "ship": "Viking Mars",
        "conf": "9593873",
        "booking_date": date(2026, 2, 7),
        "embark_date": date(2026, 12, 17),
        "disembark_date": date(2026, 12, 27),
        "fpd": date(2026, 3, 31),
        "fpd_status": "PENDING",
        "hard_dates": {
            "Cancel penalty 20% begins (E-119)": date(2026, 8, 20),
            "Cancel penalty 35% begins (E-89)": date(2026, 9, 19),
            "Cancel penalty 50% begins (E-69)": date(2026, 10, 9),
            "Cancel penalty 75% begins (E-49)": date(2026, 10, 29),
            "Cancel penalty 100% begins (E-29)": date(2026, 11, 18),
        },
    },
    "Morton_Viking_9595029": {
        "client": "Joshua Morton & Erica Dodge",
        "supplier": "Viking",
        "ship": "Viking Mars",
        "conf": "9595029",
        "booking_date": date(2026, 2, 8),
        "embark_date": date(2026, 12, 17),
        "disembark_date": date(2026, 12, 27),
        "fpd": date(2026, 3, 31),
        "fpd_status": "PENDING",
        "hard_dates": {
            "Cancel penalty 20% begins (E-119)": date(2026, 8, 20),
            "Cancel penalty 35% begins (E-89)": date(2026, 9, 19),
            "Cancel penalty 50% begins (E-69)": date(2026, 10, 9),
            "Cancel penalty 75% begins (E-49)": date(2026, 10, 29),
            "Cancel penalty 100% begins (E-29)": date(2026, 11, 18),
        },
    },
    "McLeod_Regent_2984034": {
        "client": "Erik McLeod & Melissa McGlasson",
        "supplier": "Regent",
        "ship": "TBD",
        "conf": "2984034",
        "booking_date": date(2026, 1, 1),  # approximate
        "embark_date": date(2026, 12, 19),
        "disembark_date": date(2026, 12, 29),
        "fpd": date(2026, 9, 1),  # approximate — needs invoice
        "fpd_status": "UNKNOWN",
        "hard_dates": {},
    },
    "Loucks_Silversea_566910": {
        "client": "John & Susan Loucks",
        "supplier": "Silversea",
        "ship": "Silver Nova",
        "conf": "566910-25",
        "booking_date": date(2025, 12, 1),  # approximate
        "embark_date": date(2026, 4, 23),
        "disembark_date": date(2026, 5, 11),
        "fpd": date(2026, 2, 1),  # approximate — needs invoice
        "fpd_status": "UNKNOWN",
        "hard_dates": {},
    },
    "Loucks_Regent_3122006": {
        "client": "John & Susan Loucks",
        "supplier": "Regent",
        "ship": "TBD",
        "conf": "3122006",
        "booking_date": date(2026, 1, 1),  # approximate
        "embark_date": date(2026, 12, 29),
        "disembark_date": date(2027, 1, 14),
        "fpd": date(2026, 9, 30),  # approximate — needs invoice
        "fpd_status": "UNKNOWN",
        "hard_dates": {},
    },
    "Westbrook_Silversea_566904": {
        "client": "Ron & Linda Westbrook",
        "supplier": "Silversea",
        "ship": "Silver Nova",
        "conf": "566904-25",
        "booking_date": date(2025, 12, 1),  # approximate
        "embark_date": date(2026, 4, 23),
        "disembark_date": date(2026, 5, 11),
        "fpd": date(2026, 2, 1),  # approximate — needs invoice
        "fpd_status": "UNKNOWN",
        "hard_dates": {},
    },
    "McLeod_Regent_3112369": {
        "client": "Erik McLeod & Melissa McGlasson",
        "supplier": "Regent",
        "ship": "SS Prestige",
        "conf": "3112369",
        "booking_date": date(2025, 12, 31),
        "embark_date": date(2027, 12, 18),
        "disembark_date": date(2027, 12, 28),
        "fpd": date(2027, 9, 18),  # approximate E-90 — needs invoice
        "fpd_status": "UNKNOWN",
        "hard_dates": {
            "Option payment due": date(2026, 1, 5),
            "Shore Excursions Open (Concierge E-210)": date(2027, 5, 22),
            "Shore Excursions Open (all suites E-180)": date(2027, 6, 21),
        },
    },
    "McLeod_Princess_8X6PGQ": {
        "client": "Erik McLeod & Melissa McGlasson",
        "supplier": "Princess",
        "ship": "TBD",
        "conf": "8X6PGQ",
        "booking_date": date(2026, 1, 15),  # approximate
        "embark_date": date(2027, 3, 13),
        "disembark_date": date(2027, 3, 20),
        "fpd": date(2026, 12, 13),  # approximate E-90 — needs invoice
        "fpd_status": "UNKNOWN",
        "hard_dates": {},
    },
}


def compute_all_known_anchors() -> dict:
    """Compute anchors for all known bookings. Returns {booking_key: [anchors]}."""
    result = {}
    for key, bk in KNOWN_BOOKINGS.items():
        anchors = compute_anchors(
            booking_date=bk["booking_date"],
            embark_date=bk["embark_date"],
            disembark_date=bk["disembark_date"],
            final_payment_date=bk["fpd"],
            hard_dates=bk["hard_dates"],
            booking_label=f"{bk['client']} | {bk['supplier']} {bk['conf']}",
        )
        result[key] = anchors
    return result


# ---------------------------------------------------------------------------
# MCP TOOL REGISTRATION
# ---------------------------------------------------------------------------

def register_anchor_date_tools(mcp):
    """Register anchor date MCP tools."""

    @mcp.tool()
    async def compute_booking_anchors(booking_key: str = "", client_name: str = "") -> str:
        """Compute anchor dates for a specific booking or all bookings.

        Args:
            booking_key: Key from KNOWN_BOOKINGS (e.g. 'Furlow_Regent_3071222')
                        Leave empty for all bookings.
            client_name: Search by client name (partial match) if booking_key not known.
        """
        if booking_key and booking_key in KNOWN_BOOKINGS:
            bk = KNOWN_BOOKINGS[booking_key]
            anchors = compute_anchors(
                bk["booking_date"], bk["embark_date"], bk["disembark_date"],
                bk["fpd"], bk["hard_dates"],
                f"{bk['client']} | {bk['supplier']} {bk['conf']}",
            )
            return json.dumps({
                "booking": booking_key,
                "client": bk["client"],
                "anchor_count": len(anchors),
                "anchors": [
                    {**a, "date": a["date"].isoformat()}
                    for a in anchors
                ],
            }, indent=2)

        if client_name:
            matches = {
                k: v for k, v in KNOWN_BOOKINGS.items()
                if client_name.lower() in v["client"].lower()
            }
            if not matches:
                return json.dumps({"error": f"No booking found matching '{client_name}'"})
            results = {}
            for key, bk in matches.items():
                anchors = compute_anchors(
                    bk["booking_date"], bk["embark_date"], bk["disembark_date"],
                    bk["fpd"], bk["hard_dates"],
                    f"{bk['client']} | {bk['supplier']} {bk['conf']}",
                )
                results[key] = {
                    "client": bk["client"],
                    "anchor_count": len(anchors),
                    "anchors": [{**a, "date": a["date"].isoformat()} for a in anchors],
                }
            return json.dumps(results, indent=2)

        # All bookings
        all_anchors = compute_all_known_anchors()
        summary = {}
        for key, anchors in all_anchors.items():
            bk = KNOWN_BOOKINGS[key]
            summary[key] = {
                "client": bk["client"],
                "embark": bk["embark_date"].isoformat(),
                "fpd": bk["fpd"].isoformat(),
                "fpd_status": bk["fpd_status"],
                "total_anchors": len(anchors),
                "next_anchor": next(
                    (
                        {"label": a["label"], "date": a["date"].isoformat()}
                        for a in anchors if a["date"] >= date.today()
                    ),
                    None,
                ),
            }
        return json.dumps(summary, indent=2)

    @mcp.tool()
    async def scan_anchor_dates() -> str:
        """A3-Moreau daily scan: what anchor dates are due today, this week, next 2 weeks.
        Returns operations briefing with overdue items, today's actions, and upcoming milestones.
        """
        all_anchors = compute_all_known_anchors()
        briefing = generate_a3_briefing(all_anchors)
        return briefing

    @mcp.tool()
    async def sync_anchors_to_calendar(booking_key: str = "") -> str:
        """Push anchor dates to Google Calendar (D2M Anchor Dates calendar).
        Creates color-coded all-day events with reminders.
        Shared with jbzsolutionsllc@gmail.com and johnloucks3@gmail.com.

        Args:
            booking_key: Specific booking key, or empty for all bookings.
        """
        if booking_key and booking_key in KNOWN_BOOKINGS:
            bk = KNOWN_BOOKINGS[booking_key]
            anchors = compute_anchors(
                bk["booking_date"], bk["embark_date"], bk["disembark_date"],
                bk["fpd"], bk["hard_dates"],
                f"{bk['client']} | {bk['supplier']} {bk['conf']}",
            )
            result = sync_anchors_to_calendar_impl(anchors, booking_key)
            return json.dumps(result, indent=2)

        # All bookings
        all_results = {}
        for key, bk in KNOWN_BOOKINGS.items():
            anchors = compute_anchors(
                bk["booking_date"], bk["embark_date"], bk["disembark_date"],
                bk["fpd"], bk["hard_dates"],
                f"{bk['client']} | {bk['supplier']} {bk['conf']}",
            )
            all_results[key] = sync_anchors_to_calendar_impl(anchors, key)
        return json.dumps(all_results, indent=2)

    # Alias for the impl function to avoid name collision with MCP tool
    global sync_anchors_to_calendar_impl
    sync_anchors_to_calendar_impl = sync_anchors_to_calendar


# ---------------------------------------------------------------------------
# CLI for testing
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Thunderbird Anchor Date Engine")
    parser.add_argument("--scan", action="store_true", help="Run A3-Moreau daily scan")
    parser.add_argument("--booking", type=str, help="Compute anchors for specific booking key")
    parser.add_argument("--all", action="store_true", help="Show all bookings summary")
    parser.add_argument("--calendar", action="store_true", help="Sync to Google Calendar")
    parser.add_argument("--calendar-booking", type=str, help="Sync specific booking to calendar")

    args = parser.parse_args()

    if args.scan:
        all_anchors = compute_all_known_anchors()
        print(generate_a3_briefing(all_anchors), file=sys.stderr)

    elif args.booking:
        if args.booking in KNOWN_BOOKINGS:
            bk = KNOWN_BOOKINGS[args.booking]
            anchors = compute_anchors(
                bk["booking_date"], bk["embark_date"], bk["disembark_date"],
                bk["fpd"], bk["hard_dates"],
                f"{bk['client']} | {bk['supplier']} {bk['conf']}",
            )
            for a in anchors:
                status = "PAST" if a["date"] < date.today() else "    "
                print(f"{status} {a['date']} [{a['category']:12s}] {a['label']} ({a['source']})", file=sys.stderr)
        else:
            print(f"Unknown booking key: {args.booking}", file=sys.stderr)
            print(f"Available keys: {', '.join(KNOWN_BOOKINGS.keys())}", file=sys.stderr)

    elif args.all:
        for key, bk in KNOWN_BOOKINGS.items():
            anchors = compute_anchors(
                bk["booking_date"], bk["embark_date"], bk["disembark_date"],
                bk["fpd"], bk["hard_dates"],
                f"{bk['client']} | {bk['supplier']} {bk['conf']}",
            )
            future = [a for a in anchors if a["date"] >= date.today()]
            next_a = future[0] if future else None
            print(
                f"{key:40s} | {bk['client']:35s} | E:{bk['embark_date']} | "
                f"FPD:{bk['fpd']} ({bk['fpd_status']:7s}) | "
                f"Next: {next_a['date']} {next_a['label'][:40] if next_a else 'none'}",
                file=sys.stderr,
            )

    elif args.calendar or args.calendar_booking:
        bkey = args.calendar_booking or ""
        if bkey and bkey in KNOWN_BOOKINGS:
            bk = KNOWN_BOOKINGS[bkey]
            anchors = compute_anchors(
                bk["booking_date"], bk["embark_date"], bk["disembark_date"],
                bk["fpd"], bk["hard_dates"],
                f"{bk['client']} | {bk['supplier']} {bk['conf']}",
            )
            result = sync_anchors_to_calendar(anchors, bkey)
            print(json.dumps(result, indent=2), file=sys.stderr)
        elif not bkey:
            all_anchors = compute_all_known_anchors()
            for key, anchors in all_anchors.items():
                result = sync_anchors_to_calendar(anchors, key)
                print(json.dumps(result, indent=2), file=sys.stderr)
        else:
            print(f"Unknown booking key: {bkey}", file=sys.stderr)

    else:
        parser.print_help(sys.stderr)
