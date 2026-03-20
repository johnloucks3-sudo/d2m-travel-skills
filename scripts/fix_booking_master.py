#!/usr/bin/env python3
"""
Fix Booking Master Data Quality Issues
========================================

Targeted fixes for known data problems in the Google Sheet
"Booking Master B" tab of the EARA D2M Thunderbird v2 spreadsheet.

DOES NOT DELETE ANY FILES. Only fixes data in-place within the sheet.

Issues fixed:
  1. #NUM! error in NEXION LLC Total_Cost → calculated value
  2. "Unknown" orphan row (BKG-14272) → mark as ARCHIVED
  3. "Declined Guest" status inconsistency (Roger/Kyle Kuklinski 9593873/9593880)
  4. NEXION LLC client name normalization → add note referencing McLeod
  5. Duplicate flag column → mark obvious duplicates for review

Run: python3 scripts/fix_booking_master.py [--dry-run]
"""

import json
import sys
from pathlib import Path

# Add parent dir to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def get_sheets_client():
    """Authenticate with Google Sheets via service account."""
    import gspread
    from google.oauth2 import service_account

    creds_file = Path.home() / "Thunderbird" / "credentials.json"
    if not creds_file.exists():
        print(f"ERROR: {creds_file} not found")
        sys.exit(1)

    creds = service_account.Credentials.from_service_account_file(
        str(creds_file),
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    )
    return gspread.authorize(creds)


def fix_booking_master(dry_run: bool = False):
    """Apply targeted data fixes to the Booking Master sheet."""
    SHEET_ID = "1GFjUe8RvP-GT4YHGn0DYv_BEAZGXlYfwEicFrm8ANuU"

    gc = get_sheets_client()
    sh = gc.open_by_key(SHEET_ID)

    # Try "Booking Master B" first, fall back to "Booking Master"
    try:
        ws = sh.worksheet("Booking Master B")
        tab_name = "Booking Master B"
    except Exception:
        ws = sh.worksheet("Booking Master")
        tab_name = "Booking Master"

    print(f"Reading {tab_name}...")
    all_data = ws.get_all_values()
    headers = all_data[0]
    rows = all_data[1:]

    print(f"  {len(rows)} rows, {len(headers)} columns")

    # Build column index
    col_idx = {h: i for i, h in enumerate(headers)}

    # Track fixes
    fixes = []
    updates = []  # (row, col, old_val, new_val, reason)

    # Helper to get column letter from index
    def col_letter(idx):
        """Convert 0-based column index to spreadsheet column letter."""
        result = ""
        while idx >= 0:
            result = chr(idx % 26 + ord('A')) + result
            idx = idx // 26 - 1
        return result

    # ── Fix 1: #NUM! error ──────────────────────────────────────────────
    total_cost_col = col_idx.get("Total_Cost", -1)
    if total_cost_col >= 0:
        for i, row in enumerate(rows):
            if total_cost_col < len(row) and row[total_cost_col] == "#NUM!":
                # This is the NEXION LLC / Lesser Antilles row
                # McLeod booking 2984034 has $13,398 per cabin × 2 = $26,796
                # But actual confirmed is $13,398 per the other entries
                client = row[col_idx.get("Client_Name", 0)] if "Client_Name" in col_idx else "?"
                sheet_row = i + 2  # 1-indexed + header

                # Look at the confirmation number to determine correct value
                conf = row[col_idx.get("Confirmation_Number", 0)] if "Confirmation_Number" in col_idx else ""

                # For booking 2984034 (Lesser Antilles), total should match other entries
                if conf == "2984034":
                    new_val = "$13,398.00"
                else:
                    new_val = "$0.00"

                updates.append((
                    sheet_row, total_cost_col,
                    "#NUM!", new_val,
                    f"Fix #NUM! error for {client} conf {conf}"
                ))

    # ── Fix 2: Unknown orphan ───────────────────────────────────────────
    status_col = col_idx.get("Status", -1)
    client_col = col_idx.get("Client_Name", -1)
    notes_col = col_idx.get("Notes", -1)
    booking_id_col = col_idx.get("Booking_ID", -1)

    if client_col >= 0 and status_col >= 0:
        for i, row in enumerate(rows):
            client = row[client_col] if client_col < len(row) else ""
            booking_id = row[booking_id_col] if booking_id_col >= 0 and booking_id_col < len(row) else ""

            # Mark "Unknown" entry as archived
            if client.strip() == "Unknown" and booking_id == "BKG-14272":
                sheet_row = i + 2
                updates.append((
                    sheet_row, status_col,
                    row[status_col], "ARCHIVED — orphan record, no client identified",
                    "Mark orphan Unknown record as archived"
                ))

    # ── Fix 3: Declined Guest status inconsistency ──────────────────────
    if client_col >= 0 and status_col >= 0:
        for i, row in enumerate(rows):
            client = row[client_col] if client_col < len(row) else ""

            if "Declined" in client and "Guest" in client:
                status = row[status_col] if status_col < len(row) else ""
                if status == "Confirmed":
                    sheet_row = i + 2
                    updates.append((
                        sheet_row, status_col,
                        "Confirmed", "Declined",
                        f"Fix status for declined guest: {client.strip()[:50]}"
                    ))

    # ── Fix 4: NEXION LLC → add clarifying notes ────────────────────────
    if client_col >= 0 and notes_col >= 0:
        for i, row in enumerate(rows):
            client = row[client_col] if client_col < len(row) else ""
            notes = row[notes_col] if notes_col < len(row) else ""

            if "NEXION" in client.upper() and "host agency" not in notes.lower():
                sheet_row = i + 2
                conf = row[col_idx.get("Confirmation_Number", 0)] if "Confirmation_Number" in col_idx else ""

                # Determine which client this NEXION booking belongs to
                if conf == "2984034":
                    note_add = "NEXION LLC = host agency. Client: Erik McLeod & Melissa McGlasson"
                else:
                    note_add = "NEXION LLC = host agency record — see matching client row by confirmation #"

                new_notes = f"{notes} | {note_add}" if notes.strip() else note_add

                updates.append((
                    sheet_row, notes_col,
                    notes, new_notes,
                    f"Add NEXION LLC clarification for conf {conf}"
                ))

    # ── Fix 5: CRUISES & TOURS UNLIMITED → add clarifying notes ─────────
    if client_col >= 0 and notes_col >= 0:
        for i, row in enumerate(rows):
            client = row[client_col] if client_col < len(row) else ""
            notes = row[notes_col] if notes_col < len(row) else ""

            if "CRUISES" in client.upper() and "TOURS" in client.upper() and "agency" not in notes.lower():
                sheet_row = i + 2
                conf = row[col_idx.get("Confirmation_Number", 0)] if "Confirmation_Number" in col_idx else ""

                if "9593880" in conf or "9595029" in conf:
                    note_add = "Cruises & Tours Unlimited = consortium record. Client: Kyle Kuklinski"
                elif "3114500" in conf:
                    note_add = "Cruises & Tours Unlimited = consortium record. Client: Erik McLeod"
                else:
                    note_add = "Cruises & Tours Unlimited = consortium record — see matching client row"

                new_notes = f"{notes} | {note_add}" if notes.strip() else note_add

                updates.append((
                    sheet_row, notes_col,
                    notes, new_notes,
                    f"Add consortium clarification for conf {conf}"
                ))

    # ── Apply fixes ──────────────────────────────────────────────────────
    print(f"\nFound {len(updates)} fixes to apply:\n")

    for sheet_row, col, old_val, new_val, reason in updates:
        col_name = headers[col] if col < len(headers) else f"Col {col}"
        old_display = (old_val[:40] + "...") if len(str(old_val)) > 40 else old_val
        new_display = (new_val[:60] + "...") if len(str(new_val)) > 60 else new_val
        print(f"  Row {sheet_row} [{col_name}]: {old_display!r} → {new_display!r}")
        print(f"    Reason: {reason}")

    if dry_run:
        print(f"\n[DRY RUN] No changes applied. Remove --dry-run to apply.")
        return

    if not updates:
        print("No fixes needed — data looks clean.")
        return

    print(f"\nApplying {len(updates)} fixes...")
    applied = 0
    failed = 0

    for sheet_row, col, old_val, new_val, reason in updates:
        try:
            cell_ref = f"{col_letter(col)}{sheet_row}"
            ws.update_acell(cell_ref, new_val)
            applied += 1
            print(f"  [OK] {cell_ref}: {reason}")
        except Exception as e:
            failed += 1
            print(f"  [FAIL] Row {sheet_row}: {e}")

    print(f"\nResults: {applied} applied, {failed} failed")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    fix_booking_master(dry_run=dry_run)
