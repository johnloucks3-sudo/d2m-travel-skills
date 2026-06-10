#!/usr/bin/env python3
"""
Add Loucks Silver Nova May 2027 booking to Booking Master Sheet.
Source: Agency PDF 506101-26_Agency.pdf — ground truth as of 2026-06-10
D2M commission split: 80%

Run: python3 scripts/add_loucks_nova_may2027_to_sheet.py
"""

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import gspread
from google.oauth2 import service_account

SHEET_ID = "1GFjUe8RvP-GT4YHGn0DYv_BEAZGXlYfwEicFrm8ANuU"
TAB = "Booking Master"

_CRED_CANDIDATES = [
    ROOT / "creds" / "service_account.json",
    ROOT / ".service_account_gemini.json",
    ROOT / "credentials.json",
]

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Ground truth from Agency PDF 506101-26_Agency.pdf (2026-06-10)
# D2M commission = 80% of $5,517.18 = $4,413.74
NEW_ROW = {
    "Created_Date": "6/10/2026",
    "Client_Name": "John & Susan LOUCKS",
    "Booking_ID": "506101-26",
    "Client_Email": "yodainva@gmail.com",
    "Trip_Name": "Silver Nova Mediterranean May 2027",
    "Itinerary": "Venice → Adriatic → Athens (3 segments B2B2B)",
    "Start_Date": "5-May-27",
    "End_Date": "29-May-27",
    "Trip_Type": "Cruise",
    "Destination": "Mediterranean",
    "Supplier": "Silversea",
    "Confirmation_Number": "506101-26",
    "Status": "Confirmed",
    "Total_Cost": "$34,450.00",
    "Commission": "$5,517.18",
    "D2M Share": "$4,413.74",
    "Amount_Paid": "$8,612.50",
    "Balance_Due": "$25,837.50",
    "Payment_Due_Date": "12/6/2026",
    "Final_Payment_Date": "12/6/2026",
    "Travelers": "2",
    "Lead_Traveler": "Colonel John Aldon Loucks",
    "Phone": "719-291-0742",
    "Duration_Days": "24",
    "Ship_Name": "Silver Nova",
    "Stateroom_Category": "Superior Veranda",
    "Stateroom_Number": "8071",
    "Traveler_2_Name": "Ms Susan Dee Loucks",
    "Virtuoso_Amenities": "TLNHOSTED Distinctive Voyages",
    "Internal_Agent_Notes": (
        "Personal travel — Commander + Susie. "
        "3 voyages B2B2B: SN270505010 (May 5-15, 10N), SN270515007 (May 15-22, 7N), SN270522007 (May 22-29, 7N). "
        "Commission: 16% base + 1% new-to-brand on $32,454 commissionable. "
        "D2M 80% = $4,413.74. "
        "Agency: Cruises & Tours Unlimited, Jacksonville FL. "
        "Source: Agency PDF 506101-26_Agency.pdf verified 2026-06-10."
    ),
    "Pre_Cruise_Hotel": "Hilton Molino Stucky Venice (May 1-5, 4 nights) — NEEDS BOOKING",
    "Post_Cruise_Hotel": "Athens Gate Hotel (May 29-Jun 1, 3 nights) — NEEDS BOOKING",
}


def get_creds():
    for path in _CRED_CANDIDATES:
        if path.exists():
            print(f"Using credentials: {path}")
            return service_account.Credentials.from_service_account_file(
                str(path), scopes=SCOPES
            )
    raise FileNotFoundError(f"No service account credentials found. Tried: {_CRED_CANDIDATES}")


def main():
    creds = get_creds()
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(SHEET_ID)
    ws = sh.worksheet(TAB)

    headers = ws.row_values(1)
    print(f"Sheet has {len(headers)} columns, {ws.row_count} rows")

    # Check if already exists
    conf_col = headers.index("Confirmation_Number") + 1 if "Confirmation_Number" in headers else None
    if conf_col:
        existing = ws.col_values(conf_col)
        if "506101-26" in existing:
            print("WARNING: Booking 506101-26 already exists in sheet. Aborting to prevent duplicate.")
            sys.exit(1)

    # Build row aligned to header order
    row_values = [NEW_ROW.get(h, "") for h in headers]

    ws.append_row(row_values, value_input_option="USER_ENTERED")
    print(f"SUCCESS: Row appended for Loucks Silver Nova May 2027 (Booking 506101-26)")
    print(f"  Total Charge:   $34,450.00")
    print(f"  Commission:     $5,517.18  (agency total)")
    print(f"  D2M Share:      $4,413.74  (80%)")
    print(f"  Deposit PAID:   $8,612.50")
    print(f"  Balance Due:    $25,837.50 (FPD Dec 6, 2026)")


if __name__ == "__main__":
    main()
