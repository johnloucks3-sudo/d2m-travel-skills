#!/usr/bin/env python3
"""
sheets_pull.py — Mirror key Google Sheets tabs to local Thunderbird cache.

Pulls live Sheets data to cache/sheets_mirror/*.json
Runs every 4h via backup_bot. Agents read local mirrors for zero-API-call access.

Tabs mirrored:
  Daily Itinerary     → daily_itinerary.json
  Intel_Log           → intel_log.json (latest 500 rows)
  World Intelligence  → world_intelligence.json
  Tech News Monitor   → tech_news.json
  Pricing Tracker     → pricing_tracker.json
  Clients             → clients.json
  Registry_Clients    → registry_clients.json
  Fare Log            → fare_log.json
  Action_Tracker      → action_tracker.json
  Ship Intelligence   → ship_intelligence.json
  Reference_Suppliers → reference_suppliers.json
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
sys.path.insert(0, str(ROOT))
from core.booking.booking_master import BookingMasterClient

MIRROR_DIR = ROOT / "cache/sheets_mirror"
MIRROR_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("sheets_pull")

# Tab name → local file, optional row limit
TABS = [
    ("Daily Itinerary",         "daily_itinerary.json",         None),
    ("Daily Itinerary Bucket",  "daily_itinerary_bucket.json",  None),
    ("Daily Itinerary A",       "daily_itinerary_a.json",       None),
    ("Daily Itinerary B",       "daily_itinerary_b.json",       None),
    ("Intel_Log",               "intel_log.json",               500),  # latest 500 only
    ("World Intelligence",      "world_intelligence.json",      None),
    ("Tech News Monitor",       "tech_news.json",               200),
    ("Pricing Tracker",         "pricing_tracker.json",         None),
    ("Clients",                 "clients.json",                 None),
    ("Registry_Clients",        "registry_clients.json",        None),
    ("Fare Log",                "fare_log.json",                None),
    ("Action_Tracker",          "action_tracker.json",          None),
    ("Ship Intelligence",       "ship_intelligence.json",       None),
    ("Reference_Suppliers",     "reference_suppliers.json",     None),
    ("Availability Alerts",     "availability_alerts.json",     None),
    ("Port Weather",            "port_weather.json",            None),
    ("Travel Advisories",       "travel_advisories.json",       None),
]


def _pull_tab(spreadsheet, tab_name: str, max_rows: int | None) -> list[dict]:
    try:
        sh = spreadsheet.worksheet(tab_name)
        rows = sh.get_all_values()
        if not rows:
            return []
        headers = rows[0]
        data_rows = rows[1:]
        if max_rows:
            data_rows = data_rows[-max_rows:]  # latest N rows
        records = []
        for row in data_rows:
            if any(cell.strip() for cell in row):  # skip blank rows
                rec = {}
                for i, h in enumerate(headers):
                    rec[h or f"col_{i}"] = row[i] if i < len(row) else ""
                records.append(rec)
        return records
    except Exception as e:
        log.warning("Failed to pull %s: %s", tab_name, e)
        return []


def main() -> int:
    log.info("sheets_pull starting")
    bmc = BookingMasterClient()
    ws = bmc._worksheet()
    spreadsheet = ws.spreadsheet

    manifest = {
        "pulled_at": datetime.now(tz=timezone.utc).isoformat(),
        "tabs": {},
    }

    for tab_name, filename, max_rows in TABS:
        records = _pull_tab(spreadsheet, tab_name, max_rows)
        out = MIRROR_DIR / filename
        out.write_text(json.dumps({
            "tab": tab_name,
            "pulled_at": manifest["pulled_at"],
            "row_count": len(records),
            "records": records,
        }, indent=2, ensure_ascii=False))
        manifest["tabs"][tab_name] = {"file": filename, "rows": len(records)}
        log.info("Pulled %s: %d rows → %s", tab_name, len(records), filename)

    # Write manifest
    (MIRROR_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2))
    log.info("sheets_pull complete — %d tabs mirrored", len(TABS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
