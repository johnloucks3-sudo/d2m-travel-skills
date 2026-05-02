#!/usr/bin/env python3
"""
SPSA Google Sheets Sync — Runs daily at 0645 MT
Exports closed SPSA cases to Google Sheet for trending analysis
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.ops.thunderbird_spsa import export_to_sheets_format, get_closed_cases_for_week
from core.ops.thunderbird_sheets import (
    update_spsa_sheet,
    get_spsa_sheet_id_from_config,
    save_spsa_sheet_id_to_config,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - spsa_sheets - %(levelname)s - %(message)s"
)
logger = logging.getLogger("spsa_sheets")

ROOT = Path("/home/john/Thunderbird")
SYNC_STATE = ROOT / "logs" / "spsa" / "sheets_sync_state.json"


def load_sync_state():
    """Load last sync timestamp."""
    if SYNC_STATE.exists():
        try:
            return json.loads(SYNC_STATE.read_text()).get("last_sync", "1970-01-01T00:00:00")
        except Exception:
            return "1970-01-01T00:00:00"
    return "1970-01-01T00:00:00"


def save_sync_state():
    """Save current sync timestamp."""
    SYNC_STATE.parent.mkdir(parents=True, exist_ok=True)
    SYNC_STATE.write_text(json.dumps({
        "last_sync": datetime.now().isoformat(),
        "note": "SPSA cases synced to Google Sheets"
    }, indent=2))


def main():
    logger.info("=== SPSA SHEETS SYNC JOB STARTING ===")

    try:
        # Get closed cases from past week
        closed_cases = get_closed_cases_for_week()
        logger.info(f"Found {len(closed_cases)} closed cases in past week")

        if not closed_cases:
            logger.info("No closed cases to sync")
            save_sync_state()
            return 0

        # Export to Sheets format
        rows = export_to_sheets_format()
        logger.info(f"Exported {len(rows)} total case rows")

        # Format for logging/reporting
        logger.info("Sample rows to sync:")
        for row in rows[-3:]:  # Last 3 rows
            logger.info(f"  {row['Case ID']}: {row['Problem'][:40]}... → {row['Status']}")

        # Sync to Google Sheets
        sheet_id = get_spsa_sheet_id_from_config()
        success = update_spsa_sheet(rows, sheet_id=sheet_id)

        if success:
            logger.info("✅ Successfully synced to Google Sheets")
            # If this was a new sheet creation, save the sheet ID
            if not sheet_id:
                from core.ops.thunderbird_sheets import get_or_create_spsa_sheet
                new_sheet_id = get_or_create_spsa_sheet()
                if new_sheet_id:
                    save_spsa_sheet_id_to_config(new_sheet_id)
                    logger.info(f"Saved new sheet ID: {new_sheet_id}")
        else:
            logger.warning("Failed to sync to Google Sheets, falling back to JSON export")
            # Fallback: save to JSON file for manual inspection
            export_path = ROOT / "output" / "spsa_export.json"
            export_path.parent.mkdir(parents=True, exist_ok=True)
            export_path.write_text(json.dumps(rows, indent=2, default=str))
            logger.info(f"Exported to JSON fallback: {export_path}")

        # Track sync state
        save_sync_state()
        logger.info("✅ Sync state updated")

        logger.info("=== SPSA SHEETS SYNC JOB COMPLETE ===")
        return 0

    except Exception as e:
        logger.error(f"Sheets sync failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit(main())
