#!/usr/bin/env python3
"""
Booking Master Sheet Corrections
Source: output/commission_audit_opus.md (headless Opus, 2026-05-06)
Author: COS Hale — fix_booking_master.py

Steps:
  1. Backup "Booking Master" → "Booking_Master_BACKUP_YYYYMMDD"
  2. Build canonical name lookup from z_MIGRATED tabs
  3. Apply all PDF-sourced commission corrections + annotations
  4. Write correction log to output/booking_master_corrections_preview.md

Run:
  python3 scripts/fix_booking_master.py            # execute
  python3 scripts/fix_booking_master.py --dry-run  # preview only
"""

import sys
import json
from datetime import datetime
from pathlib import Path

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SHEET_ID = "1GFjUe8RvP-GT4YHGn0DYv_BEAZGXlYfwEicFrm8ANuU"
TAB = "Booking Master"
SVC_ACCT = str(Path(__file__).resolve().parent.parent / ".service_account_gemini.json")
AUDIT_TAG = f"[AUDIT {datetime.now().strftime('%Y-%m-%d')}]"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

DRY_RUN = "--dry-run" in sys.argv


def col_letter(n):
    """0-based column index → letter (A…Z, AA…)"""
    result = ""
    while True:
        result = chr(ord("A") + n % 26) + result
        n = n // 26 - 1
        if n < 0:
            break
    return result


def build_canonical_lookup(svc):
    """
    Build {conf_number: {client_name, supplier}} from z_MIGRATED tabs.
    Prefer Bucket (newest), fall back to B, then A.
    Skip rows with garbage client names from bad PDF parses.
    """
    GARBAGE = {
        "Unknown", "Pending", "VS", "Embarkation Date:", "",
        # Host agencies — should never be client names or suppliers
        "NEXION LLC", "Nexion LLC", "Nexion Llc", "NEXION",
        "Cruises & Tours Unlimited", "CRUISES & TOURS UNLIMITED",
        "Cruises and Tours Unlimited",
        # Cruise/supplier names that sometimes appear in client_name column
        "Viking", "VIKING", "Silversea", "SILVERSEA",
        "Regent Seven Seas Cruises", "REGENT SEVEN SEAS CRUISES",
        "Princess Cruises", "PRINCESS CRUISES", "Princess",
    }
    lookup = {}
    # Read in reverse priority order (A first so Bucket wins last)
    for tab in [
        "z_MIGRATED_Booking Master A",
        "z_MIGRATED_Booking Master B",
        "z_MIGRATED_Booking Master Bucket",
    ]:
        try:
            resp = svc.spreadsheets().values().get(
                spreadsheetId=SHEET_ID,
                range=f"'{tab}'!A:BJ",
            ).execute()
        except Exception as e:
            print(f"  Warn: could not read {tab}: {e}")
            continue
        rows = resp.get("values", [])
        if not rows:
            continue
        header = rows[0]
        h = {v: i for i, v in enumerate(header)}

        def g(row, key):
            return row[h[key]] if key in h and h[key] < len(row) else ""

        for row in rows[1:]:
            conf = g(row, "Confirmation_Number") or g(row, "Booking_ID")
            client = g(row, "Client_Name").strip()
            supplier = g(row, "Supplier").strip()
            if not conf:
                continue
            # Only store non-garbage entries (overwrite with each better tab)
            if client and client not in GARBAGE and "\n" not in client:
                existing = lookup.get(conf, {})
                existing["client_name"] = client
                if supplier and supplier not in GARBAGE:
                    existing["supplier"] = supplier
                lookup[conf] = existing

    return lookup


def read_sheet(svc):
    resp = svc.spreadsheets().values().get(
        spreadsheetId=SHEET_ID,
        range=f"'{TAB}'!A:BJ",
    ).execute()
    rows = resp.get("values", [])
    header = rows[0]
    col = {name: i for i, name in enumerate(header)}
    return header, rows[1:], col


def backup_sheet(svc):
    backup_name = f"Booking_Master_BACKUP_{datetime.now().strftime('%Y%m%d')}"
    # Get sheet ID
    meta = svc.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
    sheet_id = None
    for s in meta["sheets"]:
        if s["properties"]["title"] == TAB:
            sheet_id = s["properties"]["sheetId"]
            break
    if sheet_id is None:
        print(f"ERROR: Sheet '{TAB}' not found")
        sys.exit(1)

    # Check if backup already exists
    for s in meta["sheets"]:
        if s["properties"]["title"] == backup_name:
            print(f"  Backup already exists: {backup_name} — skipping")
            return

    body = {
        "requests": [{
            "duplicateSheet": {
                "sourceSheetId": sheet_id,
                "newSheetName": backup_name,
            }
        }]
    }
    svc.spreadsheets().batchUpdate(
        spreadsheetId=SHEET_ID, body=body
    ).execute()
    print(f"  ✅ Backup created: {backup_name}")


def main():
    creds = Credentials.from_service_account_file(SVC_ACCT, scopes=SCOPES)
    svc = build("sheets", "v4", credentials=creds)
    sheets = svc.spreadsheets().values()

    # ── Step 1: Backup ────────────────────────────────────────────────────
    if not DRY_RUN:
        print("Step 1: Backing up Booking Master...")
        backup_sheet(svc)
    else:
        print("Step 1: [DRY RUN] Skipping backup")

    # ── Step 2: Build canonical lookup from z_MIGRATED ───────────────────
    print("Step 2: Building canonical lookup from z_MIGRATED tabs...")
    lookup = build_canonical_lookup(svc)
    print(f"  {len(lookup)} booking records indexed")

    # ── Step 3: Read current sheet ────────────────────────────────────────
    print("Step 3: Reading Booking Master...")
    header, data_rows, col = read_sheet(svc)
    print(f"  {len(data_rows)} data rows, {len(header)} columns")

    # ── Step 4: Build correction set ─────────────────────────────────────
    updates = []   # list of {"range": ..., "values": [[val]]}
    log = []       # human-readable correction log

    def fix(data_row, col_name, new_val, reason):
        """Queue a cell update. data_row is 1-based data index (matches audit rows)."""
        sheet_row = data_row + 1  # header is row 1
        c = col[col_name]
        old_val = ""
        if data_row - 1 < len(data_rows) and c < len(data_rows[data_row - 1]):
            old_val = data_rows[data_row - 1][c]
        cell = f"'{TAB}'!{col_letter(c)}{sheet_row}"
        updates.append({"range": cell, "values": [[new_val]]})
        log.append({
            "row": data_row, "col": col_name,
            "old": old_val, "new": new_val, "reason": reason,
        })

    def note(data_row, text):
        """Append audit annotation to Notes cell."""
        sheet_row = data_row + 1
        c = col["Notes"]
        existing = ""
        if data_row - 1 < len(data_rows) and c < len(data_rows[data_row - 1]):
            existing = str(data_rows[data_row - 1][c]).strip()
        combined = (existing + " | " + AUDIT_TAG + " " + text).strip(" |")
        cell = f"'{TAB}'!{col_letter(c)}{sheet_row}"
        # Replace last notes update for same row if already queued
        for i, u in enumerate(updates):
            if u["range"] == cell:
                updates[i] = {"range": cell, "values": [[combined]]}
                return
        updates.append({"range": cell, "values": [[combined]]})
        log.append({
            "row": data_row, "col": "Notes",
            "old": existing[:60], "new": "(annotation appended)", "reason": text[:80],
        })

    def canonical_client(conf, fallback):
        return lookup.get(conf, {}).get("client_name", fallback)

    def canonical_supplier(conf, fallback):
        return lookup.get(conf, {}).get("supplier", fallback)

    # ─────────────────────────────────────────────────────────────────────
    # ROW 3: McLeod Silver Muse 298475-25
    # Supplier: use z_MIGRATED canonical
    # Commission: $3,884.40 → $2,594.54 (PDF: Silversea 16%+1% NCF)
    # D2M Share: $3,107.52 (80%) → $1,816.18 (70%, Nexion host)
    # ─────────────────────────────────────────────────────────────────────
    fix(3, "Client_Name", canonical_client("298475-25", "Erik McLeod & Melissa McGlasson"),
        "Canonical name from z_MIGRATED PDF extraction")
    fix(3, "Supplier", canonical_supplier("298475-25", "Silversea"),
        "Canonical supplier from z_MIGRATED")
    fix(3, "Commission", "$2,594.54",
        "PDF: Silversea direct 16%+1% NTB on commissionable $15,262 (not 15% of gross)")
    fix(3, "D2M Share", "$1,816.18",
        "70% of $2,594.54 — Nexion host = 70% split (was incorrectly at 80%)")
    note(3, "Commission $3,884.40→$2,594.54 (Silversea 16%+1% NCF on $15,262 commissionable). D2M split corrected 80%→70% (Nexion host). Host agency: NEXION LLC.")

    # ─────────────────────────────────────────────────────────────────────
    # ROW 4: Furlow 3071222 — Storied Scandinavia Aug 2026
    # Total_Cost: 9060 → $18,120 (sheet had single-pax; PDF = 2-pax total)
    # Commission: $2,718 → $2,287.90 (Nexion 15% on commissionable $15,186)
    # D2M Share: $2,174.40 (80%) → $1,601.53 (70%)
    # Amount_Paid: final pmt $15,486 RECEIVED — Commander confirmed
    # Balance_Due: → $0.00
    # ─────────────────────────────────────────────────────────────────────
    fix(4, "Supplier", canonical_supplier("3071222", "Regent Seven Seas Cruises"),
        "Canonical supplier from z_MIGRATED")
    fix(4, "Total_Cost", "$18,120.00",
        "PDF: $18,120 grand total (2-pax). Sheet had single-guest figure $9,060.")
    fix(4, "Commission", "$2,287.90",
        "PDF: Nexion LLC 15% on commissionable $15,186 ($7,593×2)")
    fix(4, "D2M Share", "$1,601.53",
        "70% of $2,287.90 — Nexion host = 70% split (was 80%)")
    fix(4, "Amount_Paid", "$18,120.00",
        "Final pmt $15,486 RECEIVED — Commander confirmed (9+ explicit confirmations)")
    fix(4, "Balance_Due", "$0.00",
        "PAID IN FULL per Commander confirmation")
    note(4, "Total $9,060→$18,120 (2-pax PDF total). Commission $2,718→$2,287.90 (Nexion 15% commissionable). D2M 80%→70% (Nexion). PAID IN FULL — final pmt $15,486 confirmed by Commander.")

    # ─────────────────────────────────────────────────────────────────────
    # ROW 5: Nichols 3078056 — WRONG trip name; wrong total; wrong commission
    # Trip_Name: "Season To Cheer — SS Prestige" → "SS Grandeur Storied Scandinavia"
    # Total_Cost: $16,398 → $18,896
    # Commission: $2,459.70 → $2,287.90
    # D2M Share: $1,967.76 → $1,601.53 (70%)
    # ─────────────────────────────────────────────────────────────────────
    fix(5, "Client_Name", canonical_client("3078056", "Larry W Nichols & Heidi Ann Nichols"),
        "Canonical name from z_MIGRATED")
    fix(5, "Supplier", canonical_supplier("3078056", "Regent Seven Seas Cruises"),
        "Canonical supplier from z_MIGRATED")
    fix(5, "Trip_Name", "SS Grandeur Storied Scandinavia Aug 29–Sep 8 2026",
        "PDF: BN 3078056 = Storied Scandinavia. Sheet had 'Season To Cheer SS Prestige' — copy-paste error from row 8.")
    fix(5, "Total_Cost", "$18,896.00",
        "PDF TA Invoice confirmed $18,896 grand total (was $16,398)")
    fix(5, "Commission", "$2,287.90",
        "PDF: Nexion LLC 15% on commissionable $15,186 ($7,593×2)")
    fix(5, "D2M Share", "$1,601.53",
        "70% of $2,287.90 — Nexion host = 70% split (was 80%)")
    note(5, "TRIP NAME CORRECTED: 3078056 = Storied Scandinavia Aug 2026 (was Season To Cheer SS Prestige). Total $16,398→$18,896 (PDF). Commission $2,459.70→$2,287.90 (Nexion 15% commissionable). D2M 80%→70%.")

    # ─────────────────────────────────────────────────────────────────────
    # ROW 6: Ely/Darrow 3096289 — commission and D2M share wrong
    # Commission: $3,096 → $2,685.90 (Nexion 15% on $8,953×2)
    # D2M Share: $2,167.20 → $1,880.13 (70%)
    # ─────────────────────────────────────────────────────────────────────
    fix(6, "Client_Name", canonical_client("3096289", "Al Ely & Amy Darrow"),
        "Canonical name from z_MIGRATED")
    fix(6, "Supplier", canonical_supplier("3096289", "Regent Seven Seas Cruises"),
        "Canonical supplier from z_MIGRATED")
    fix(6, "Commission", "$2,685.90",
        "PDF: Nexion LLC 15% on commissionable $17,906 ($8,953×2)")
    fix(6, "D2M Share", "$1,880.13",
        "70% of $2,685.90 — Nexion host")
    note(6, "Commission $3,096→$2,685.90 (Nexion 15% on commissionable $17,906, not 15% of gross). D2M 70%.")

    # ─────────────────────────────────────────────────────────────────────
    # ROW 7: McLeod 3112369 — Season To Cheer SS Prestige Dec 2027
    # Commission: $2,459.70 → $2,400.96 (C&TU 17% on $13,988 commissionable)
    # D2M Share: $1,967.76 (80%) → $1,920.77 (80%)
    # ─────────────────────────────────────────────────────────────────────
    fix(7, "Client_Name", canonical_client("3112369", "Erik Wiedenbach McLeod and Melissa Etola McGlasson"),
        "Canonical name from z_MIGRATED")
    fix(7, "Supplier", canonical_supplier("3112369", "Regent Seven Seas Cruises"),
        "Canonical supplier from z_MIGRATED")
    fix(7, "Commission", "$2,400.96",
        "PDF: C&TU 17% on commissionable $13,988 ($6,994×2)")
    fix(7, "D2M Share", "$1,920.77",
        "80% of $2,400.96 — C&TU host")
    note(7, "Commission $2,459.70→$2,400.96 (C&TU 17% on $13,988 commissionable). D2M 80%.")

    # ─────────────────────────────────────────────────────────────────────
    # ROW 8: McLeod 3114500 — Season To Cheer SS Prestige Dec 2027 (CONFIRMED BN)
    # Supplier: "Princess Cruises" → Regent Seven Seas Cruises (PDF confirmed)
    # Total_Cost: $6,462 → $15,098 (Princess fare misentry)
    # Commission: $969.30 → $2,179.96 (C&TU 17% on $12,688 commissionable)
    # D2M Share: $775.44 → $1,743.97 (80%)
    # ─────────────────────────────────────────────────────────────────────
    fix(8, "Client_Name", canonical_client("3114500", "MR ERIK WIEDENBACH MC LEOD"),
        "Canonical name from z_MIGRATED PDF extraction")
    fix(8, "Supplier", "Regent Seven Seas Cruises",
        "PDF TA Invoice: RSSC SS Prestige. z_MIGRATED Bucket confirms RSSC. Sheet had Princess Cruises — misentry.")
    fix(8, "Total_Cost", "$15,098.00",
        "PDF TA Invoice: $15,098 grand total. Was $6,462 (Princess fare value copied in error).")
    fix(8, "Commission", "$2,179.96",
        "PDF: C&TU 17% on commissionable $12,688 ($6,344×2)")
    fix(8, "D2M Share", "$1,743.97",
        "80% of $2,179.96 — C&TU host")
    note(8, "SUPPLIER CORRECTED: was Princess Cruises, is RSSC SS Prestige (PDF + z_MIGRATED Bucket). Total $6,462→$15,098 (PDF). Commission $969.30→$2,179.96 (C&TU 17% on $12,688). D2M 80%.")

    # ─────────────────────────────────────────────────────────────────────
    # ROW 9: Loucks 3122006 — Panama Canal SS Grandeur Dec 2026
    # Commission: $3,869.70 → $3,775.02 (C&TU 17% on $22,206 commissionable)
    # D2M Share: $3,095.76 → $3,020.02 (80%)
    # ─────────────────────────────────────────────────────────────────────
    fix(9, "Client_Name", "John Aldon Loucks & Susan Dee Loucks",
        "PDF: John & Susan Loucks (2-pax). Hardcoded — z_MIGRATED had incorrect title prefix.")
    fix(9, "Supplier", canonical_supplier("3122006", "Regent Seven Seas Cruises"),
        "Canonical supplier from z_MIGRATED")
    fix(9, "Commission", "$3,775.02",
        "PDF: C&TU 17% on commissionable $22,206 ($11,103×2)")
    fix(9, "D2M Share", "$3,020.02",
        "80% of $3,775.02 — C&TU host")
    note(9, "Commission $3,869.70→$3,775.02 (C&TU 17% on commissionable $22,206). D2M 80%.")

    # ─────────────────────────────────────────────────────────────────────
    # ROW 10: Morton/Dodge 9595029 — Viking Mars Panama Canal Dec 2026
    # Client_Name: "CRUISES & TOURS UNLIMITED" → correct client (from z_MIGRATED: JOSHUA MORTON)
    # Commission: $929.70 → $1,053.66 (Viking via C&TU 17%)
    # D2M Share: $743.76 → $842.93 (80%)
    # ─────────────────────────────────────────────────────────────────────
    fix(10, "Client_Name", canonical_client("9595029", "JOSHUA MORTON"),
        "PDF TA Invoice: Joshua Morton. z_MIGRATED confirms JOSHUA MORTON. Sheet had supplier name in client field.")
    fix(10, "Supplier", canonical_supplier("9595029", "Viking"),
        "Canonical supplier from z_MIGRATED")
    fix(10, "Commission", "$1,053.66",
        "PDF: Viking via C&TU 17% on $6,198 ($3,099×2)")
    fix(10, "D2M Share", "$842.93",
        "80% of $1,053.66 — C&TU host")
    note(10, "CLIENT CORRECTED: CRUISES & TOURS UNLIMITED→JOSHUA MORTON (PDF TA Invoice). Second traveler: Erica Dodge (from PDF). Commission $929.70→$1,053.66 (Viking 17% on $6,198). D2M 80%.")

    # ─────────────────────────────────────────────────────────────────────
    # ROW 11: Westbrook 566904-25 — NON-D2M (Interline Travel & Tour)
    # ROW 12: Loucks 566910-25 — NON-D2M (Interline Travel & Tour)
    # ─────────────────────────────────────────────────────────────────────
    note(11, "NON-D2M: PDF Cruise Confirmation shows Travel Agent = Interline Travel & Tour, not D2M. $10,800 paid. No D2M commission accrues. Flag for removal from D2M register.")
    note(12, "NON-D2M: Westbrook Silversea Silver Nova Apr 2026. Travel Agent = Interline Travel & Tour (not D2M). $10,800 paid. No D2M commission. Flag for removal from D2M register.")

    # ─────────────────────────────────────────────────────────────────────
    # ROWS 17, 18, 30, 31, 32, 33: Ancillary hotel/transfer — D2M Share blank
    # Populate at 70% of commission (consistent with parent Nexion/Storied Scandinavia)
    # ─────────────────────────────────────────────────────────────────────
    ancillaries = [
        (17, "$80.56",  "Ely Hotel Haymarket Stockholm (1095092)"),
        (18, "$11.81",  "Ely Transfer Hötorget Stockholm (1095091)"),
        (30, "$80.56",  "Furlow Hotel Haymarket Stockholm (1095075)"),
        (31, "$11.81",  "Furlow Transfer Hötorget Stockholm (1095074)"),
        (32, "$80.56",  "Nichols Hotel Haymarket Stockholm (1095090)"),
        (33, "$11.81",  "Nichols Transfer Hötorget Stockholm (1095089)"),
    ]
    for data_row, d2m_val, label in ancillaries:
        fix(data_row, "D2M Share", d2m_val,
            f"Populated blank D2M Share at 70% of commission (consistent with parent Nexion booking)")
        note(data_row, f"D2M Share populated at 70% of commission. Parent booking uses Nexion 70% split.")

    # ─────────────────────────────────────────────────────────────────────
    # ROW 21: McLeod/McGlasson 2984034 — Lesser Antilles Dec 2026 (canonical row)
    # Confirm FPD from Guest Statement; flag ESTIMATE; add host agency
    # ─────────────────────────────────────────────────────────────────────
    fix(21, "Supplier", canonical_supplier("2984034", "Regent Seven Seas Cruises"),
        "Canonical supplier from z_MIGRATED")
    fix(21, "Commission", "🟡 ESTIMATE $2,009.70",
        "No TA invoice in Drive. Estimate = 15% of grand total $13,398 via NEXION LLC (Guest Statement). Verify with Nexion.")
    fix(21, "Final_Payment_Date", "2026-07-22",
        "Guest Statement confirmed FPD 22-Jul-2026")
    note(21, "FPD 2026-07-22 per Guest Statement. Host: NEXION LLC. NO TA invoice — commission is 15%-of-total ESTIMATE. D2M split TBD (sheet uses 80%=$1,607.76; 70%=$1,406.79). Request TA invoice from Nexion for confirmation.")

    # ─────────────────────────────────────────────────────────────────────
    # ROW 2: NEXION LLC 2984034 placeholder ($0) — mark duplicate
    # ROW 22: NEXION LLC 2984034 exact duplicate — mark duplicate
    # ROW 26: NEXION LLC 2984034 no BN — mark duplicate
    # ─────────────────────────────────────────────────────────────────────
    fix(2, "Status", "🚩 DUPLICATE — see Row 21",
        "Zero-figure placeholder. Row 21 is canonical for BN 2984034.")
    note(2, "DUPLICATE zero-figure placeholder for BN 2984034. Row 21 has correct figures. Delete after Commander review.")

    fix(22, "Status", "🚩 DUPLICATE — see Row 21",
        "Exact duplicate of Row 21 (BN 2984034).")
    note(22, "DUPLICATE of Row 21 (BN 2984034). Same figures. Delete after Commander review.")

    fix(26, "Status", "🚩 DUPLICATE — see Row 21",
        "Duplicate of Row 21 (BN 2984034), missing Confirmation_Number.")
    fix(26, "Confirmation_Number", "2984034",
        "Added missing BN — matches NEXION/McGlasson booking")
    note(26, "DUPLICATE of Row 21 (BN 2984034). Missing Confirmation_Number (now added). Delete after Commander review.")

    # ─────────────────────────────────────────────────────────────────────
    # ROW 23: Kuklinski Kyle 9593880 (C&TU duplicate)
    # Fix figures to PDF values while it exists; mark as duplicate of row 16
    # ─────────────────────────────────────────────────────────────────────
    fix(23, "Client_Name", "Kyle Kuklinski & Rosalie Morton Kuklinski",
        "PDF: Kyle Kuklinski + Rosalie Morton. Hardcoded — z_MIGRATED Bucket had host agency in client field.")
    fix(23, "Commission", "$1,291.66",
        "PDF: Viking via C&TU 17% on $7,598 ($3,799×2)")
    fix(23, "D2M Share", "$1,033.33",
        "80% of $1,291.66 — C&TU host")
    fix(23, "Status", "🚩 DUPLICATE — see Row 16",
        "Kyle Kuklinski 9593880 canonical row is Row 16")
    note(23, "Commission $1,139.70→$1,291.66 (Viking 17%). DUPLICATE of Row 16 (Kyle Kuklinski 9593880). Consolidate and delete after Commander review.")

    # ─────────────────────────────────────────────────────────────────────
    # ROW 25: Kyle Kuklinski — missing BN; duplicate of row 16
    # ROW 28: Roger Kuklinski — missing BN; duplicate of row 15
    # ─────────────────────────────────────────────────────────────────────
    fix(25, "Confirmation_Number", "9593880",
        "Missing BN assigned — matches Kyle Kuklinski Viking Mars booking (BKG-584652 in z_MIGRATED)")
    fix(25, "Client_Name", "MR KYLE STANLEY KUKLINSKI & MS ROSALIE MORTON KUKLINSKI",
        "Full name from PDF/z_MIGRATED (hardcoded — z_MIGRATED Bucket had host agency in client field)")
    fix(25, "Commission", "$1,291.66",
        "PDF: Viking via C&TU 17% on $7,598")
    fix(25, "D2M Share", "$1,033.33",
        "80% of $1,291.66")
    fix(25, "Status", "🚩 DUPLICATE — see Row 16",
        "Row 16 is canonical for Kyle Kuklinski 9593880")
    note(25, "BN 9593880 assigned. Full name updated from z_MIGRATED. Commission $1,139.70→$1,291.66. DUPLICATE of Row 16. Delete after Commander review.")

    fix(28, "Confirmation_Number", "9593873",
        "Missing BN assigned — matches Roger Kuklinski Viking Mars booking (BKG-758577 in z_MIGRATED)")
    fix(28, "Client_Name", canonical_client("9593873", "MR ROGER DAVID KUKLINSKI & DR NICHOLAS JOHN KUKLINSKI"),
        "Full canonical name from z_MIGRATED BKG-758577")
    fix(28, "Commission", "$1,291.66",
        "PDF: Viking via C&TU 17% on $7,598")
    fix(28, "D2M Share", "$1,033.33",
        "80% of $1,291.66")
    fix(28, "Status", "🚩 DUPLICATE — see Row 15",
        "Row 15 is canonical for Roger Kuklinski 9593873")
    note(28, "BN 9593873 assigned. Full name updated from z_MIGRATED. Commission $1,139.70→$1,291.66. DUPLICATE of Row 15. Delete after Commander review.")

    # ─────────────────────────────────────────────────────────────────────
    # ROW 27: C&TU 3114500 — duplicate of row 8; fix figures, mark duplicate
    # ─────────────────────────────────────────────────────────────────────
    fix(27, "Commission", "$2,179.96",
        "PDF: C&TU 17% on commissionable $12,688 ($6,344×2)")
    fix(27, "D2M Share", "$1,743.97",
        "80% of $2,179.96 — C&TU host")
    fix(27, "Status", "🚩 DUPLICATE — see Row 8",
        "Row 8 is canonical for McLeod BN 3114500 (corrected)")
    note(27, "Commission $2,264.70→$2,179.96 (C&TU 17% commissionable). DUPLICATE of Row 8. Delete after Commander review.")

    # ─────────────────────────────────────────────────────────────────────
    # ROW 29: Morton 9595029 placeholder ($0) — populate from PDF, mark duplicate
    # ─────────────────────────────────────────────────────────────────────
    fix(29, "Total_Cost", "$6,198.00",
        "PDF TA Invoice: $6,198 grand total ($3,099×2)")
    fix(29, "Commission", "$1,053.66",
        "PDF: Viking via C&TU 17% on $6,198")
    fix(29, "D2M Share", "$842.93",
        "80% of $1,053.66")
    fix(29, "Status", "🚩 DUPLICATE — see Row 10",
        "Row 10 is canonical for Morton/Dodge 9595029 (corrected)")
    note(29, "Figures populated from PDF. DUPLICATE of Row 10 (Morton/Dodge 9595029). Delete after Commander review.")

    # ─────────────────────────────────────────────────────────────────────
    # ROW 19: ARCHIVED phantom — flag for deletion
    # ─────────────────────────────────────────────────────────────────────
    note(19, "PHANTOM ROW — no client, no booking number, no figures. Safe to delete.")

    # ─────────────────────────────────────────────────────────────────────
    # ROW 14: Princess 8X6PGQ — fix supplier to canonical; flag UNKNOWN commission
    # ─────────────────────────────────────────────────────────────────────
    fix(14, "Client_Name", "Erik McLeod & Melissa McGlasson",
        "PDF: passenger copy lists McLeod & McGlasson. Hardcoded — z_MIGRATED had garbled entry.")
    fix(14, "Supplier", "Princess Cruises",
        "Hardcoded — z_MIGRATED returned Nexion LLC (host agency) instead of cruise line. PDF confirms Princess Cruises.")
    fix(14, "Commission", "🟡 UNKNOWN",
        "Passenger copy only — no TA commission shown. Sheet estimate (15% of gross) likely overstated for Princess (~10% base). Request TA invoice from Nexion.")
    fix(14, "D2M Share", "🟡 UNKNOWN",
        "Depends on confirmed commission — TBD when TA invoice received")
    note(14, "Passenger copy only — no TA commission on file. Sheet used 15%-of-gross estimate; Princess base via Nexion is ~10%. Commission and D2M Share set to UNKNOWN pending TA invoice. Request from Nexion.")

    # ─────────────────────────────────────────────────────────────────────
    # Step 5: Write preview log
    # ─────────────────────────────────────────────────────────────────────
    preview_path = Path(__file__).resolve().parent.parent / "output" / "booking_master_corrections_preview.md"
    preview_path.parent.mkdir(exist_ok=True)

    lines = [
        f"# Booking Master Correction Log",
        f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M MT')} | Source: commission_audit_opus.md (Headless Opus)*",
        f"*Sheet: [{SHEET_ID}](https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit)*",
        f"*Mode: {'DRY RUN' if DRY_RUN else 'APPLIED'}*",
        "",
        f"| Row | Column | Old Value | New Value | Reason |",
        f"|-----|--------|-----------|-----------|--------|",
    ]
    for entry in log:
        if entry["col"] == "Notes":
            continue
        old = str(entry["old"])[:50]
        new = str(entry["new"])[:60]
        reason = entry["reason"][:80]
        lines.append(f"| {entry['row']} | {entry['col']} | `{old}` | `{new}` | {reason} |")

    lines += [
        "",
        "## Annotation Summary (Notes column updates)",
        "",
    ]
    for entry in log:
        if entry["col"] == "Notes":
            lines.append(f"- **Row {entry['row']}:** {entry['reason'][:120]}")

    preview_path.write_text("\n".join(lines))
    print(f"\nCorrection preview written to: {preview_path}")

    # ─────────────────────────────────────────────────────────────────────
    # Step 6: Execute (or dry-run)
    # ─────────────────────────────────────────────────────────────────────
    print(f"\n{len(updates)} cell updates queued across {len(set(e['row'] for e in log))} data rows")

    if DRY_RUN:
        print("\n[DRY RUN] No changes written. Remove --dry-run to apply.")
        print(f"Preview: {preview_path}")
        return

    print("\nExecuting batchUpdate...")
    body = {
        "valueInputOption": "USER_ENTERED",
        "data": updates,
    }
    resp = sheets.batchUpdate(spreadsheetId=SHEET_ID, body=body).execute()
    total = resp.get("totalUpdatedCells", "?")
    print(f"✅ Done. Cells updated: {total}")
    print(f"Sheet: https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit")
    print(f"Preview/log: {preview_path}")


if __name__ == "__main__":
    main()
