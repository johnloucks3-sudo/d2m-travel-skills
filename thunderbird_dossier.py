"""
Thunderbird Trip Dossier Engine
Dreams2Memories Travel, LLC

Creates and manages TRIP-based dossiers on Google Drive.
Each dossier is a Google Doc organized by trip, with general trip info
and per-couple sections inside.

Trips:
  1. SS Grandeur Storied Scandinavia (Furlow, Ely/Darrow, Nichols)
  2. Silver Muse Rome→Venice (McLeod/McGlasson)
  3. Viking Mars Panama Canal (Kuklinski x2, Morton/Dodge)
  4. Silver Nova Yokohama→Seattle (Loucks, Westbrook)
  5. Regent Lesser Antilles Dec 2026 (McLeod/McGlasson)
  6. Regent Dec 2026 (Loucks)
  7. SS Prestige Season To Cheer Dec 2027 (McLeod/McGlasson)
  8. Princess Mexico Riviera Mar 2027 (McLeod/McGlasson)
"""

import os
import sys
import json
from datetime import date, timedelta
from typing import Optional

from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

from thunderbird_anchor_dates import KNOWN_BOOKINGS, compute_anchors

# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------

CREDENTIALS_PATH = os.path.join(os.path.dirname(__file__), "credentials.json")
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents",
]

SHARE_EMAILS = [
    "johnloucks3@gmail.com",
    "jbzsolutionsllc@gmail.com",
]

# ---------------------------------------------------------------------------
# TRIP DEFINITIONS — maps trips to their constituent bookings
# ---------------------------------------------------------------------------

TRIPS = {
    "Grandeur_Scandinavia_Aug2026": {
        "name": "SS Grandeur — Storied Scandinavia",
        "ship": "SS Grandeur (Regent Seven Seas)",
        "route": "Stockholm → Berlin → Copenhagen → Kristiansand → Oslo",
        "embark": date(2026, 8, 29),
        "disembark": date(2026, 9, 8),
        "embark_port": "Stockholm, Sweden",
        "disembark_port": "Oslo, Norway",
        "nights": 10,
        "bookings": ["Furlow_Regent_3071222", "***REMOVED-SECRET***", "Nichols_Regent_3078056"],
        "pre_cruise": {
            "hotel": "Haymarket by Scandic, Stockholm",
            "hotel_dates": "Aug 27-29 (night 1 client pays, night 2 Regent pays)",
            "transfers": "Private car ARN airport → Haymarket (Bedsonline)",
        },
        "general_notes": [
            "All 3 couples on same cruise — coordinate excursions and dining",
            "Itinerary change Jan 23: Copenhagen overnight moved to Sep 3, sea day replaced with Kristiansand",
            "Itinerary change Aug 8, 2025: Rostock replaced with additional Berlin day",
            "Shore excursions opened Jan 31, 2026",
            "Specialty dining opens May 31, 2026",
            "Excursions/dining close 7 days before sailing (Aug 22)",
        ],
    },
    "SilverMuse_Mediterranean_Jun2026": {
        "name": "Silver Muse — Rome to Venice",
        "ship": "Silver Muse (Silversea)",
        "route": "Civitavecchia → Naples → Giardini Naxos → Valletta → Kotor → Bari → Dubrovnik → Split → Zadar → Fusina (Venice)",
        "embark": date(2026, 6, 23),
        "disembark": date(2026, 7, 3),
        "embark_port": "Civitavecchia (Rome), Italy",
        "disembark_port": "Fusina (Venice), Italy",
        "nights": 10,
        "bookings": ["McLeod_Silversea_298475"],
        "pre_cruise": {
            "hotel": "Baglioni Hotel Regina, Rome",
            "hotel_dates": "Jun 18-23 (5 nights, client arranged)",
            "transfers": "Baglioni concierge limo FCO→hotel (~€100). FreeNow app hotel→Civitavecchia (~€140-160)",
        },
        "post_cruise": {
            "hotel": "PENDING — 3 options: Sina Centurion Palace, JW Marriott, NH Palazzo dei Dogi",
            "hotel_dates": "Jul 3-6 (3 nights)",
            "transfers": "Private water taxi hotel→VCE airport (~€140)",
        },
        "general_notes": [
            "Paid in full Jan 20, 2026",
            "Independent deviation — arriving 4 days early, Silversea Non-Use Credit ~$100/pp",
            "Business class Denver→Rome Jun 18, Venice→Denver via Toronto Jul 6",
            "Specialty dining opened Feb 23, 2026",
            "Shore excursions opened Jan 31, 2026",
            "Venice hotel decision STILL PENDING",
            "Airline record locators need consolidation (multiple PNRs)",
            "Guest Info Form: verify completed on my.silversea.com",
        ],
    },
    "VikingMars_PanamaCanal_Dec2026": {
        "name": "Viking Mars — Classic Panama Canal Passage",
        "ship": "Viking Mars (Viking)",
        "route": "Panama City (Fuerte Amador) → Panama Canal → Caribbean → Ft. Lauderdale",
        "embark": date(2026, 12, 17),
        "disembark": date(2026, 12, 27),
        "embark_port": "Panama City (Fuerte Amador)",
        "disembark_port": "Ft. Lauderdale, Florida",
        "nights": 10,
        "bookings": ["Kuklinski1_Viking_9593880", "Kuklinski2_Viking_9593873", "Morton_Viking_9595029"],
        "pre_cruise": {},
        "post_cruise": {},
        "general_notes": [
            "3 suites, 6 guests total — all family/friends traveling together",
            "ALL 6 Guest Information Forms NOT received",
            "ALL 6 declined travel protection",
            "Viking pre-existing condition window closed (15 days from deposit, deposits Feb 7-10)",
            "Trip Mate plan can still be purchased up to FPD (Mar 31)",
            "Disembark port changed from FLL to West Palm Beach",
            "E-check payment gets 2% discount (not eligible within 21 days of travel)",
            "SBC Vouchers: $100/pp available on all 3 bookings",
        ],
    },
    "SilverNova_Pacific_Apr2026": {
        "name": "Silver Nova — Yokohama to Seattle",
        "ship": "Silver Nova (Silversea)",
        "route": "Yokohama (Tokyo) → Pacific → Seattle",
        "embark": date(2026, 4, 23),
        "disembark": date(2026, 5, 11),
        "embark_port": "Yokohama (Tokyo), Japan",
        "disembark_port": "Seattle, Washington",
        "nights": 18,
        "bookings": ["Loucks_Silversea_566910", "Westbrook_Silversea_566904"],
        "pre_cruise": {},
        "post_cruise": {},
        "general_notes": [
            "John & Susan Loucks + Ron & Linda Westbrook on same sailing",
            "Westbrook insurance: OVERDUE (flagged Feb 17)",
            "FPD and exact invoice details needed for both bookings",
        ],
    },
    "Regent_LesserAntilles_Dec2026": {
        "name": "Regent — Lesser Antilles Journey",
        "ship": "TBD (Regent Seven Seas)",
        "route": "Lesser Antilles",
        "embark": date(2026, 12, 19),
        "disembark": date(2026, 12, 29),
        "embark_port": "TBD",
        "disembark_port": "TBD",
        "nights": 10,
        "bookings": ["McLeod_Regent_2984034"],
        "pre_cruise": {},
        "post_cruise": {},
        "general_notes": [
            "Erik McLeod & Melissa McGlasson second booking",
            "Invoice details needed — FPD approximate",
        ],
    },
    "Regent_Loucks_Dec2026": {
        "name": "Regent — Loucks Holiday Cruise",
        "ship": "TBD (Regent Seven Seas)",
        "route": "TBD",
        "embark": date(2026, 12, 29),
        "disembark": date(2027, 1, 14),
        "embark_port": "TBD",
        "disembark_port": "TBD",
        "nights": 16,
        "bookings": ["Loucks_Regent_3122006"],
        "pre_cruise": {},
        "post_cruise": {},
        "general_notes": [
            "John & Susan Loucks",
            "$25,798 total cost",
            "Invoice details needed — FPD approximate",
        ],
    },
    "Prestige_SeasonToCheer_Dec2027": {
        "name": "SS Prestige — Season To Cheer",
        "ship": "SS Prestige (Regent Seven Seas)",
        "route": "Lesser Antilles",
        "embark": date(2027, 12, 18),
        "disembark": date(2027, 12, 28),
        "embark_port": "TBD",
        "disembark_port": "TBD",
        "nights": 10,
        "bookings": ["McLeod_Regent_3112369"],
        "pre_cruise": {},
        "post_cruise": {},
        "general_notes": [
            "Erik McLeod & Melissa McGlasson — Concierge D suite",
            "Booked Dec 31, 2025 — option paid by Jan 5, 2026",
            "$16,398 total cost",
            "Nexion 70/30 split — D2M commission $1,967.76",
            "Shore excursions open: Concierge E-210 (May 22, 2027), all suites E-180 (Jun 21, 2027)",
            "FPD and exact invoice details needed",
        ],
    },
    "Princess_MexicoRiviera_Mar2027": {
        "name": "Princess — 7 Days Mexico Riviera",
        "ship": "TBD (Princess Cruises)",
        "route": "Mexico Riviera",
        "embark": date(2027, 3, 13),
        "disembark": date(2027, 3, 20),
        "embark_port": "TBD",
        "disembark_port": "TBD",
        "nights": 7,
        "bookings": ["McLeod_Princess_8X6PGQ"],
        "pre_cruise": {},
        "post_cruise": {},
        "general_notes": [
            "Erik McLeod & Melissa McGlasson",
            "$6,462 total cost",
            "Confirmation: 8X6PGQ",
            "Nexion split — D2M commission $775.44",
            "FPD and exact invoice details needed",
        ],
    },
}


# ---------------------------------------------------------------------------
# GOOGLE DRIVE / DOCS HELPERS
# ---------------------------------------------------------------------------

def _get_drive_service():
    creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)
    return build("drive", "v3", credentials=creds)


def _get_docs_service():
    creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)
    return build("docs", "v1", credentials=creds)


def _find_or_create_folder(drive_service, folder_name: str, parent_id: str = None) -> str:
    """Find or create a folder on Drive. Returns folder ID."""
    q = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        q += f" and '{parent_id}' in parents"
    results = drive_service.files().list(q=q, spaces="drive", fields="files(id,name)").execute()
    files = results.get("files", [])
    if files:
        return files[0]["id"]

    body = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_id:
        body["parents"] = [parent_id]
    folder = drive_service.files().create(body=body, fields="id").execute()
    folder_id = folder["id"]

    # Share with John
    for email in SHARE_EMAILS:
        try:
            drive_service.permissions().create(
                fileId=folder_id,
                body={"type": "user", "role": "writer", "emailAddress": email},
                sendNotificationEmail=False,
            ).execute()
        except Exception as e:
            print(f"Warning: Could not share folder with {email}: {e}", file=sys.stderr)

    return folder_id


def _share_file(drive_service, file_id: str):
    """Share a file with John's emails."""
    for email in SHARE_EMAILS:
        try:
            drive_service.permissions().create(
                fileId=file_id,
                body={"type": "user", "role": "writer", "emailAddress": email},
                sendNotificationEmail=False,
            ).execute()
        except Exception as e:
            print(f"Warning: Could not share with {email}: {e}", file=sys.stderr)


# ---------------------------------------------------------------------------
# DOSSIER DOCUMENT BUILDER
# ---------------------------------------------------------------------------

def _fmt_usd(amount) -> str:
    """Format USD amount."""
    if isinstance(amount, str):
        amount = amount.replace("$", "").replace(",", "")
        try:
            amount = float(amount)
        except ValueError:
            return amount
    return f"${amount:,.2f}"


def _build_dossier_content(trip_key: str) -> str:
    """Build the full dossier content as plain text for a Google Doc."""
    trip = TRIPS[trip_key]
    today = date.today()

    lines = []

    # ── HEADER ──
    lines.append("═" * 60)
    lines.append("DREAMS2MEMORIES TRAVEL, LLC")
    lines.append("TRIP DOSSIER")
    lines.append("═" * 60)
    lines.append("")
    lines.append(f"Trip: {trip['name']}")
    lines.append(f"Ship: {trip['ship']}")
    lines.append(f"Route: {trip['route']}")
    lines.append(f"Embarkation: {trip['embark'].strftime('%B %d, %Y')} — {trip['embark_port']}")
    lines.append(f"Disembarkation: {trip['disembark'].strftime('%B %d, %Y')} — {trip['disembark_port']}")
    lines.append(f"Duration: {trip['nights']} nights")
    lines.append(f"Last Updated: {today.strftime('%B %d, %Y')}")
    lines.append("")

    # ── 1. GENERAL TRIP NOTES ──
    lines.append("─" * 60)
    lines.append("1. GENERAL TRIP NOTES")
    lines.append("─" * 60)
    for note in trip.get("general_notes", []):
        lines.append(f"• {note}")
    lines.append("")

    # ── 2. PRE-CRUISE ARRANGEMENTS ──
    pre = trip.get("pre_cruise", {})
    if pre:
        lines.append("─" * 60)
        lines.append("2. PRE-CRUISE ARRANGEMENTS")
        lines.append("─" * 60)
        if pre.get("hotel"):
            lines.append(f"Hotel: {pre['hotel']}")
        if pre.get("hotel_dates"):
            lines.append(f"Dates: {pre['hotel_dates']}")
        if pre.get("transfers"):
            lines.append(f"Transfers: {pre['transfers']}")
        lines.append("")

    # ── 3. POST-CRUISE ARRANGEMENTS ──
    post = trip.get("post_cruise", {})
    if post:
        lines.append("─" * 60)
        lines.append("3. POST-CRUISE ARRANGEMENTS")
        lines.append("─" * 60)
        if post.get("hotel"):
            lines.append(f"Hotel: {post['hotel']}")
        if post.get("hotel_dates"):
            lines.append(f"Dates: {post['hotel_dates']}")
        if post.get("transfers"):
            lines.append(f"Transfers: {post['transfers']}")
        lines.append("")

    # ── PER-COUPLE SECTIONS ──
    for i, bk_key in enumerate(trip["bookings"], 1):
        bk = KNOWN_BOOKINGS.get(bk_key)
        if not bk:
            continue

        section_num = 3 + i
        lines.append("")
        lines.append("═" * 60)
        lines.append(f"{section_num}. CLIENT: {bk['client'].upper()}")
        lines.append("═" * 60)

        # Booking summary
        lines.append("")
        lines.append("BOOKING SUMMARY")
        lines.append(f"  Supplier:        {bk['supplier']}")
        lines.append(f"  Confirmation #:  {bk['conf']}")
        lines.append(f"  Ship:            {bk['ship']}")
        lines.append(f"  Booking Date:    {bk['booking_date'].strftime('%B %d, %Y')}")
        lines.append(f"  Embarkation:     {bk['embark_date'].strftime('%B %d, %Y')}")
        lines.append(f"  Disembarkation:  {bk['disembark_date'].strftime('%B %d, %Y')}")
        lines.append(f"  Final Payment:   {bk['fpd'].strftime('%B %d, %Y')} — {bk['fpd_status']}")
        lines.append("")

        # Anchor dates timeline
        anchors = compute_anchors(
            bk["booking_date"], bk["embark_date"], bk["disembark_date"],
            bk["fpd"], bk["hard_dates"],
            f"{bk['client']} | {bk['supplier']} {bk['conf']}",
        )

        lines.append("ANCHOR DATE TIMELINE")
        lines.append(f"{'Date':12s} {'Status':6s} {'Category':12s} {'Milestone'}")
        lines.append("-" * 70)
        for a in anchors:
            status = "PAST" if a["date"] < today else "    "
            src = "★" if a["source"] == "invoice" else " "
            lines.append(
                f"{a['date'].strftime('%Y-%m-%d'):12s} {status:6s} "
                f"[{a['category']:10s}] {src} {a['label']}"
            )
        lines.append("")
        lines.append("★ = HARD date from supplier invoice")
        lines.append("")

        # Hard dates from invoice (quick reference)
        if bk["hard_dates"]:
            lines.append("SUPPLIER HARD DATES (from invoice)")
            for label, hdate in sorted(bk["hard_dates"].items(), key=lambda x: x[1]):
                status = "PAST" if hdate < today else "    "
                lines.append(f"  {status} {hdate.strftime('%Y-%m-%d')} — {label}")
            lines.append("")

        # Tours & Excursions (placeholder)
        lines.append("TOURS & EXCURSIONS")
        lines.append("  [To be populated — shore excursion selections pending]")
        lines.append("")

        # Dining (placeholder)
        lines.append("DINING PLANNER")
        lines.append("  [To be populated — specialty dining reservations pending]")
        lines.append("")

        # Logistics & Transport
        lines.append("LOGISTICS & TRANSPORT")
        lines.append("  [Flights, transfers, and ground transport details]")
        lines.append("")

        # Insurance
        lines.append("INSURANCE STATUS")
        lines.append(f"  Status: {bk.get('fpd_status', 'Unknown')}")
        if "insurance" in str(bk.get("hard_dates", {})).lower():
            lines.append("  See hard dates above for insurance windows")
        lines.append("")

        # Documents
        lines.append("DOCUMENTS CHECKLIST")
        lines.append("  [ ] Passport verified (6-month validity)")
        lines.append("  [ ] Guest Information Form submitted")
        lines.append("  [ ] Travel insurance decision")
        lines.append("  [ ] Emergency contact provided")
        lines.append("  [ ] Final payment received")
        lines.append("  [ ] Dining selections made")
        lines.append("  [ ] Excursion selections made")
        lines.append("  [ ] Final itinerary delivered")
        lines.append("")

    # ── ANTICIPATION ENGINE LOG ──
    lines.append("═" * 60)
    lines.append(f"{section_num + 1}. ANTICIPATION ENGINE LOG")
    lines.append("═" * 60)
    lines.append("Content drip tracker — what has been sent to clients pre-trip.")
    lines.append("")
    lines.append(f"{'Date Sent':12s} {'T-minus':8s} {'Content':40s} {'Channel'}")
    lines.append("-" * 70)
    lines.append("  [No content sent yet]")
    lines.append("")

    # ── COMMUNICATION LOG ──
    lines.append("═" * 60)
    lines.append(f"{section_num + 2}. COMMUNICATION LOG")
    lines.append("═" * 60)
    lines.append("")
    lines.append(f"{'Date':12s} {'Type':8s} {'Summary'}")
    lines.append("-" * 70)
    lines.append("  [To be populated from Gmail thread analysis]")
    lines.append("")

    # ── REFERRAL TRACKING ──
    lines.append("═" * 60)
    lines.append(f"{section_num + 3}. REFERRAL TRACKING")
    lines.append("═" * 60)
    lines.append("")
    lines.append("  [No referrals tracked yet]")
    lines.append("")

    # ── FOOTER ──
    lines.append("─" * 60)
    lines.append("Generated by Thunderbird OS — Dreams2Memories Travel, LLC")
    lines.append(f"Dossier Version 1.0 | {today.strftime('%B %d, %Y')}")
    lines.append("─" * 60)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CREATE DOSSIER ON GOOGLE DRIVE
# ---------------------------------------------------------------------------

def create_trip_dossier(trip_key: str) -> dict:
    """
    Create a trip dossier on Google Drive.
    Saves locally first, then uploads to CLIENT_DOSSIERS/{trip_key}/ folder.
    Also saves a local copy in ~/Thunderbird/dossiers/.
    """
    if trip_key not in TRIPS:
        return {"error": f"Unknown trip key: {trip_key}", "available": list(TRIPS.keys())}

    trip = TRIPS[trip_key]
    content = _build_dossier_content(trip_key)

    # Save local copy
    local_dir = os.path.join(os.path.dirname(__file__), "dossiers")
    os.makedirs(local_dir, exist_ok=True)
    local_path = os.path.join(local_dir, f"DOSSIER_{trip_key}.md")
    with open(local_path, "w", encoding="utf-8") as f:
        f.write(content)

    # Upload to Drive using the existing thunderbird_drive upload pattern
    drive_service = _get_drive_service()

    # Find or create folder structure
    root_folder_id = _find_or_create_folder(drive_service, "CLIENT_DOSSIERS")
    trip_folder_id = _find_or_create_folder(drive_service, trip_key, root_folder_id)

    # Upload as a file (avoids quota issue with service account doc creation)
    from googleapiclient.http import MediaFileUpload
    file_name = f"DOSSIER — {trip['name']}.md"

    # Check if file already exists, update if so
    q = f"name='{file_name}' and '{trip_folder_id}' in parents and trashed=false"
    existing = drive_service.files().list(q=q, fields="files(id)").execute().get("files", [])

    if existing:
        # Update existing
        media = MediaFileUpload(local_path, mimetype="text/markdown")
        drive_service.files().update(
            fileId=existing[0]["id"],
            media_body=media,
        ).execute()
        file_id = existing[0]["id"]
    else:
        # Create new
        media = MediaFileUpload(local_path, mimetype="text/markdown")
        file_meta = {
            "name": file_name,
            "parents": [trip_folder_id],
        }
        uploaded = drive_service.files().create(
            body=file_meta,
            media_body=media,
            fields="id,webViewLink",
        ).execute()
        file_id = uploaded["id"]
        _share_file(drive_service, file_id)

    file_url = f"https://drive.google.com/file/d/{file_id}/view"
    folder_url = f"https://drive.google.com/drive/folders/{trip_folder_id}"

    return {
        "status": "success",
        "trip": trip_key,
        "trip_name": trip["name"],
        "file_id": file_id,
        "file_url": file_url,
        "folder_id": trip_folder_id,
        "folder_url": folder_url,
        "local_path": local_path,
        "bookings_included": len(trip["bookings"]),
        "clients": [KNOWN_BOOKINGS[bk]["client"] for bk in trip["bookings"] if bk in KNOWN_BOOKINGS],
    }


def create_all_dossiers() -> dict:
    """Create dossiers for all trips. Returns summary."""
    results = {}
    for trip_key in TRIPS:
        try:
            result = create_trip_dossier(trip_key)
            results[trip_key] = result
            print(f"Created: {trip_key} → {result.get('doc_url', 'ERROR')}", file=sys.stderr)
        except Exception as e:
            results[trip_key] = {"status": "error", "error": str(e)}
            print(f"FAILED: {trip_key} → {e}", file=sys.stderr)
    return results


# ---------------------------------------------------------------------------
# MCP TOOL REGISTRATION
# ---------------------------------------------------------------------------

def register_dossier_tools(mcp):
    """Register trip dossier MCP tools."""

    @mcp.tool()
    async def create_trip_dossier_tool(trip_key: str = "") -> str:
        """Create a trip dossier on Google Drive as a Google Doc.

        Each dossier contains:
        - General trip info (ship, route, dates, notes)
        - Pre/post cruise arrangements
        - Per-couple sections with booking details, anchor dates, checklists
        - Anticipation engine log, communication log, referral tracking

        Args:
            trip_key: Trip identifier. Available trips:
                - Grandeur_Scandinavia_Aug2026 (Furlow, Ely/Darrow, Nichols)
                - SilverMuse_Mediterranean_Jun2026 (McLeod/McGlasson)
                - VikingMars_PanamaCanal_Dec2026 (Kuklinski x2, Morton/Dodge)
                - SilverNova_Pacific_Apr2026 (Loucks, Westbrook)
                - Regent_LesserAntilles_Dec2026 (McLeod/McGlasson)
                - Regent_Loucks_Dec2026 (Loucks)
                - Prestige_SeasonToCheer_Dec2027 (McLeod/McGlasson)
                - Princess_MexicoRiviera_Mar2027 (McLeod/McGlasson)
                Leave empty to create ALL dossiers.
        """
        if trip_key and trip_key in TRIPS:
            result = create_trip_dossier(trip_key)
            return json.dumps(result, indent=2)

        if trip_key and trip_key not in TRIPS:
            return json.dumps({
                "error": f"Unknown trip: {trip_key}",
                "available": list(TRIPS.keys()),
            })

        # All dossiers
        results = create_all_dossiers()
        return json.dumps(results, indent=2, default=str)

    @mcp.tool()
    async def list_trip_dossiers() -> str:
        """List all available trip dossiers and their status."""
        summary = {}
        for key, trip in TRIPS.items():
            bookings_info = []
            for bk_key in trip["bookings"]:
                bk = KNOWN_BOOKINGS.get(bk_key, {})
                bookings_info.append({
                    "client": bk.get("client", "Unknown"),
                    "conf": bk.get("conf", ""),
                    "fpd_status": bk.get("fpd_status", "UNKNOWN"),
                })
            summary[key] = {
                "name": trip["name"],
                "ship": trip["ship"],
                "embark": trip["embark"].isoformat(),
                "disembark": trip["disembark"].isoformat(),
                "nights": trip["nights"],
                "bookings": bookings_info,
            }
        return json.dumps(summary, indent=2)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Thunderbird Trip Dossier Engine")
    parser.add_argument("--create", type=str, nargs="?", const="ALL",
                        help="Create dossier for trip key, or ALL")
    parser.add_argument("--list", action="store_true", help="List available trips")
    parser.add_argument("--preview", type=str, help="Preview dossier content without creating")

    args = parser.parse_args()

    if args.list:
        for key, trip in TRIPS.items():
            clients = [KNOWN_BOOKINGS[bk]["client"] for bk in trip["bookings"] if bk in KNOWN_BOOKINGS]
            print(
                f"{key:40s} | {trip['name']:40s} | "
                f"E:{trip['embark']} | {', '.join(clients)}",
                file=sys.stderr,
            )

    elif args.preview:
        if args.preview in TRIPS:
            print(_build_dossier_content(args.preview), file=sys.stderr)
        else:
            print(f"Unknown trip: {args.preview}", file=sys.stderr)
            print(f"Available: {', '.join(TRIPS.keys())}", file=sys.stderr)

    elif args.create:
        if args.create == "ALL":
            results = create_all_dossiers()
            print(json.dumps(results, indent=2, default=str), file=sys.stderr)
        elif args.create in TRIPS:
            result = create_trip_dossier(args.create)
            print(json.dumps(result, indent=2), file=sys.stderr)
        else:
            print(f"Unknown trip: {args.create}", file=sys.stderr)

    else:
        parser.print_help(sys.stderr)
