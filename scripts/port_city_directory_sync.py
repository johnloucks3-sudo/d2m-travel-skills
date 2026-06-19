#!/usr/bin/env python3
"""
port_city_directory_sync.py — Build and populate the Port_City_Directory tab
in the Thunderbird Wing Booking Master Google Sheet.

Sources: cache/sheets_mirror/daily_itinerary*.json (4 files)
Target:  Port_City_Directory tab in sheet 1GFjUe8RvP-GT4YHGn0DYv_BEAZGXlYfwEicFrm8ANuU

Columns written:
  Port, Country, Voyages (booking IDs), Days Visited, Arrival, Departure,
  Google_Maps_Link, Wikimedia_Search, Highlights, Dining_Notes,
  Excursion_Notes, Dani_Notes, Last_Updated

Thunderbird Wing · Dreams2Memories Travel, LLC · 2026-06-19
"""

from __future__ import annotations

import json
import sys
import urllib.parse
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# ── project root on sys.path so we can import BookingMasterClient ──────────
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.booking.booking_master import BookingMasterClient, SHEETS_ID  # noqa: E402

# ── constants ──────────────────────────────────────────────────────────────

MIRROR_DIR = ROOT / "cache" / "sheets_mirror"
ITINERARY_FILES = [
    MIRROR_DIR / "daily_itinerary.json",
    MIRROR_DIR / "daily_itinerary_a.json",
    MIRROR_DIR / "daily_itinerary_b.json",
    MIRROR_DIR / "daily_itinerary_bucket.json",
]

TAB_NAME = "Port_City_Directory"

HEADERS = [
    "Port",
    "Country",
    "Voyages (booking IDs)",
    "Days Visited",
    "Arrival",
    "Departure",
    "Google_Maps_Link",
    "Wikimedia_Search",
    "Highlights",
    "Dining_Notes",
    "Excursion_Notes",
    "Dani_Notes",
    "Last_Updated",
]

# ── port → country mapping ─────────────────────────────────────────────────
# Keys are normalised (lowercase, stripped).  Values are display strings.
# Covers every port that actually appears in the itinerary mirrors.
PORT_COUNTRY: dict[str, str] = {
    # Sweden
    "stockholm, sweden": "Sweden",
    # Norway
    "oslo, norway": "Norway",
    "kristiansand, norway": "Norway",
    # Denmark
    "copenhagen, denmark": "Denmark",
    # Germany
    "berlin (warnemunde), germany": "Germany",
    # Japan
    "yokohama (tokyo), japan": "Japan",
    "tokyo (harumi), japan": "Japan",
    "tokyo, japan": "Japan",
    "aomori, japan": "Japan",
    "miyako, iwate, japan": "Japan",
    # USA / Hawaii
    "honolulu, hawaii": "USA (Hawaii)",
    "los angeles, california": "USA",
    "san diego, california": "USA",
    "newport beach, california": "USA",
    "miami, florida": "USA",
    "ft. lauderdale, florida": "USA",
    "west palm beach, florida": "USA",
    "seattle (washington), usa": "USA",
    "seattle (washington), united states of america": "USA",
    "seattle, washington": "USA",
    "juneau (alaska), usa": "USA (Alaska)",
    "ketchikan, usa": "USA (Alaska)",
    "kodiak island, alaska, usa": "USA (Alaska)",
    "sitka (alaska), usa": "USA (Alaska)",
    "wrangell, usa": "USA (Alaska)",
    # Mexico
    "acapulco, mexico": "Mexico",
    "cabo san lucas, mexico": "Mexico",
    "cabo san lucas": "Mexico",
    "mazatlan, mexico": "Mexico",
    "mazatlan": "Mexico",
    "puerto vallarta, mexico": "Mexico",
    "puerto vallarta": "Mexico",
    "cozumel, mexico": "Mexico",
    # Canada
    "victoria, canada": "Canada",
    # Caribbean — individual islands
    "basseterre, st kitts/nevis": "St. Kitts & Nevis",
    "charlotte amalie, st. thomas": "U.S. Virgin Islands",
    "roseau, dominica": "Dominica",
    "san juan, puerto rico": "Puerto Rico",
    "puerto plata, dominican republic": "Dominican Republic",
    "george town, grand cayman": "Cayman Islands",
    "tortola, british virgin islands": "British Virgin Islands",
    "st. john's, antigua": "Antigua",
    # Central America
    "belize city, belize": "Belize",
    "roatan, honduras": "Honduras",
    "puerto limon, costa rica": "Costa Rica",
    "puntarenas, costa rica": "Costa Rica",
    "puerto quetzal, guatemala": "Guatemala",
    # South America
    "cartagena, colombia": "Colombia",
    # Panama
    "colon, panama": "Panama",
    "panama city (fuerte amador)": "Panama",
    "panama canal transit": "Panama",
    "panama canal": "Panama",
}

# Port names that are "at sea" / transit — skip them
SEA_KEYWORDS = {
    "at sea",
    "baltic sea",
    "caribbean sea",
    "pacific ocean",
    "atlantic ocean",
    "straits of florida",
    "day at sea",
    "date line",
    "cruising",
    "sail the",
    "location",  # header artefact
}


def _is_sea_day(port: str) -> bool:
    """Return True if this is a sea day / transit / header artefact."""
    p = port.strip().lower()
    if not p:
        return True
    for kw in SEA_KEYWORDS:
        if kw in p:
            return True
    return False


def _canonical_port(port: str) -> str:
    """Return a normalised display name for deduplication."""
    # Keep original capitalisation but strip extra whitespace
    return " ".join(port.strip().split())


def _maps_link(port: str) -> str:
    return f"https://maps.google.com/?q={urllib.parse.quote_plus(port)}"


def _wiki_link(port: str) -> str:
    return (
        f"https://commons.wikimedia.org/wiki/Special:Search"
        f"?search={urllib.parse.quote_plus(port)}&ns6=1"
    )


def _infer_country(port: str) -> str:
    key = port.strip().lower()
    if key in PORT_COUNTRY:
        return PORT_COUNTRY[key]
    # Fallback: look for ", Country" suffix already embedded in name
    if ", " in port:
        candidate = port.rsplit(", ", 1)[-1].strip()
        # Accept if it looks like a country/state (not a city abbreviation)
        if len(candidate) > 3 and not any(c.isdigit() for c in candidate):
            return candidate
    return ""


# ── load JSON mirrors ──────────────────────────────────────────────────────

def load_itinerary_records() -> list[dict]:
    """Load all records from the 4 itinerary mirror files."""
    all_records: list[dict] = []
    for path in ITINERARY_FILES:
        if not path.exists():
            print(f"  ⚠  Missing mirror file: {path.name} — skipping")
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        records = data.get("records", [])
        print(f"  📄 {path.name}: {len(records)} records (tab: {data.get('tab', '?')})")
        all_records.extend(records)
    return all_records


def _get_port(rec: dict) -> str:
    """Return the port string from a record, handling both key variants."""
    return (rec.get("Port_Location") or rec.get("Port/Location") or "").strip()


def _get_day(rec: dict) -> str:
    return str(rec.get("Day_Number") or rec.get("Day Number") or "").strip()


def _get_arrive(rec: dict) -> str:
    return str(rec.get("Arrive") or rec.get("Docking Time") or "").strip()


def _get_depart(rec: dict) -> str:
    return str(rec.get("Depart") or rec.get("Departure Time") or "").strip()


# ── aggregate ──────────────────────────────────────────────────────────────

def aggregate_ports(records: list[dict]) -> list[dict]:
    """
    Deduplicate by canonical port name.
    Returns a list of port-dicts ready for sheet rows.
    """
    # port_key (lowercase) → aggregated info
    seen: dict[str, dict] = {}

    for rec in records:
        raw_port = _get_port(rec)
        if not raw_port or _is_sea_day(raw_port):
            continue

        canonical = _canonical_port(raw_port)
        key = canonical.lower()

        if key not in seen:
            seen[key] = {
                "port": canonical,
                "country": _infer_country(canonical),
                "booking_ids": set(),
                "days": set(),
                "arrival": _get_arrive(rec),
                "departure": _get_depart(rec),
            }

        entry = seen[key]
        bid = str(rec.get("Booking_ID", "")).strip()
        if bid:
            entry["booking_ids"].add(bid)
        day = _get_day(rec)
        if day:
            entry["days"].add(day)
        # Capture first non-empty arrival/departure we encounter
        if not entry["arrival"]:
            entry["arrival"] = _get_arrive(rec)
        if not entry["departure"]:
            entry["departure"] = _get_depart(rec)

    # Convert to list, sort by Country then Port
    rows = []
    for entry in seen.values():
        rows.append(entry)

    rows.sort(key=lambda r: (r["country"].lower() or "zzz", r["port"].lower()))
    return rows


# ── get-or-create worksheet ────────────────────────────────────────────────

def get_or_create_worksheet(spreadsheet, name: str):
    """Get worksheet by name; create it if absent."""
    try:
        return spreadsheet.worksheet(name)
    except Exception:
        # gspread raises WorksheetNotFound; catch broadly for safety
        ws = spreadsheet.add_worksheet(title=name, rows=500, cols=len(HEADERS))
        return ws


# ── main ───────────────────────────────────────────────────────────────────

def main():
    now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    print("=" * 60)
    print("Port_City_Directory Sync")
    print(f"Run: {now}")
    print("=" * 60)

    # 1. Load mirrors
    print("\n[1] Loading itinerary mirrors …")
    records = load_itinerary_records()
    print(f"    Total records: {len(records)}")

    # 2. Aggregate
    print("\n[2] Aggregating ports …")
    port_rows = aggregate_ports(records)
    print(f"    Unique ports (excluding sea days): {len(port_rows)}")

    # 3. Connect to sheet
    print("\n[3] Connecting to Google Sheets …")
    client = BookingMasterClient()
    spreadsheet = client._client().open_by_key(SHEETS_ID)
    print(f"    Spreadsheet: {spreadsheet.title}")

    # 4. Get or create tab
    print(f"\n[4] Getting/creating tab '{TAB_NAME}' …")
    ws = get_or_create_worksheet(spreadsheet, TAB_NAME)
    ws.clear()
    print("    Tab cleared.")

    # 5. Build rows
    print("\n[5] Building rows …")
    sheet_rows = [HEADERS]
    for entry in port_rows:
        voyages = ", ".join(sorted(entry["booking_ids"])) if entry["booking_ids"] else ""
        days_str = ", ".join(sorted(entry["days"], key=lambda d: int(d) if d.isdigit() else 0)) if entry["days"] else ""
        sheet_rows.append([
            entry["port"],
            entry["country"],
            voyages,
            days_str,
            entry["arrival"],
            entry["departure"],
            _maps_link(entry["port"]),
            _wiki_link(entry["port"]),
            "",   # Highlights — placeholder for manual enrichment
            "",   # Dining_Notes
            "",   # Excursion_Notes
            "",   # Dani_Notes
            now,
        ])

    # 6. Write to sheet
    print(f"\n[6] Writing {len(sheet_rows)} rows (1 header + {len(sheet_rows)-1} data) …")
    ws.update(sheet_rows, value_input_option="USER_ENTERED")
    print("    ✅ Write complete.")

    # 7. Format header row bold
    try:
        from gspread.utils import rowcol_to_a1
        ws.format("A1:M1", {
            "textFormat": {"bold": True},
            "backgroundColor": {"red": 0.0, "green": 0.19, "blue": 0.53},  # navy #003087
        })
        ws.format("A1:M1", {
            "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
            "backgroundColor": {"red": 0.0, "green": 0.19, "blue": 0.53},
        })
        print("    Header row formatted (navy/white).")
    except Exception as e:
        print(f"    ⚠  Header formatting skipped: {e}")

    # 8. Verify read-back
    print("\n[7] Verifying write …")
    written = ws.get_all_records()
    print(f"    Read-back: {len(written)} data rows confirmed in sheet.")

    # 9. Summary
    print("\n" + "=" * 60)
    print(f"DONE — {len(port_rows)} unique ports written to '{TAB_NAME}'")
    print("=" * 60)

    # Print port list
    print("\nPorts by Country:")
    current_country = None
    for entry in port_rows:
        if entry["country"] != current_country:
            current_country = entry["country"]
            print(f"\n  {current_country or '(no country)'}:")
        bids = ", ".join(sorted(entry["booking_ids"])) if entry["booking_ids"] else "—"
        print(f"    • {entry['port']}  [bookings: {bids}]")

    return len(port_rows)


if __name__ == "__main__":
    count = main()
    sys.exit(0)
