"""
Add / upsert Loucks Silver Nova May 2027 row to Booking Master Sheet.
Booking ref: 506101-26 | Silversea confirmation received: 2026-06-10
Run: python3 /home/john/Thunderbird/scripts/add_loucks_nova_may2027_to_sheet.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import gspread
from google.oauth2 import service_account

SHEETS_ID = "1GFjUe8RvP-GT4YHGn0DYv_BEAZGXlYfwEicFrm8ANuU"
TAB = "Booking Master"
CRED_PATH = Path("/home/john/Thunderbird/.service_account_gemini.json")
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

ROW = {
    "Created_Date": "7/2/2026",
    "Client_Name": "John & Susan Loucks",
    "Booking_ID": "506101-26",
    "Client_Email": "johnloucks3@gmail.com",
    "Trip_Name": "Silversea Silver Nova Mediterranean May 2027",
    "Itinerary": "Venice (Fusina) → Adriatic Coast → Athens (Piraeus) | 3 segments B2B2B",
    "Start_Date": "5-May-27",
    "End_Date": "29-May-27",
    "Trip_Type": "Cruise",
    "Destination": "Mediterranean — Adriatic, Greek Islands, Turkey",
    "Supplier": "Silversea",
    "Confirmation_Number": "506101-26",
    "Status": "Confirmed",
    "Total_Cost": "$34,450.00",
    "Commission": "$5,517.18",
    "D2M Share": "$4,413.74",
    "Amount_Paid": "$8,612.50",
    "Balance_Due": "$25,837.50",
    "Payment_Due_Date": "6-Dec-26",
    "Final_Payment_Date": "6-Dec-26",
    "Travelers": "2",
    "Lead_Traveler": "Colonel John Aldon Loucks",
    "Phone": "719-291-0742",
    "Duration_Days": "24",
    "Ship_Name": "Silver Nova",
    "Stateroom_Category": "Superior Veranda",
    "Stateroom_Number": "8071",
    "Traveler_2_Name": "Ms Susan Dee Loucks",
    "Virtuoso_Amenities": "TLNHOSTED Distinctive Voyages x2",
    "LEG 3: Embarkation_Details": "May 5, 2027 — Fusina (Venice) | 7:00 PM departure",
    "LEG 3: Ship_Name": "Silver Nova",
    "LEG 3: Disembarkation_Details": "May 29, 2027 — Athens (Piraeus)",
    "Insurance_Status": "Pending — Allianz Annual Premier (pre-existing waiver open until FPD)",
    "Internal_Agent_Notes": (
        "WF-17 exception — Commander as client. Dani authorized to send lifecycle emails "
        "to johnloucks3@gmail.com + susanna.loucks@gmail.com with 24hr advance preview. "
        "Silversea official confirmation email received 2026-06-10 "
        "(guestconfirmation@silversea.com). Guest name on booking: COLONEL JOHN ALDON LOUCKS. "
        "Agency: Cruises & Tours Unlimited, Jacksonville FL. "
        "Wire: BofA ABA 026009593 / SWIFT BOFAUS3N / Acct 003603984188 / Ref 506101-26."
    ),
    "Passport_Details": "John: expires 02/01/2030 | Susan: expires 04/10/2031",
    "Visas_Required": "None — Greece, Croatia, Slovenia, Montenegro, Turkey (port-only) all visa-free for US passport",
}


def main():
    creds = service_account.Credentials.from_service_account_file(
        str(CRED_PATH), scopes=SCOPES
    )
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(SHEETS_ID)
    ws = sh.worksheet(TAB)

    headers = ws.row_values(1)

    # Check for existing row by Booking_ID
    booking_col = headers.index("Booking_ID") + 1 if "Booking_ID" in headers else None
    existing_row_idx = None
    if booking_col:
        col_values = ws.col_values(booking_col)
        for i, val in enumerate(col_values[1:], start=2):
            if val.strip() == "506101-26":
                existing_row_idx = i
                print(f"Found existing row at row {i} — will update.")
                break

    # Build row data aligned to headers
    row_data = []
    for h in headers:
        row_data.append(ROW.get(h, ""))

    if existing_row_idx:
        ws.update(f"A{existing_row_idx}", [row_data])
        print(f"Updated row {existing_row_idx}.")
    else:
        ws.append_row(row_data, value_input_option="USER_ENTERED")
        print("Appended new row.")

    print("Done — Loucks Silver Nova 506101-26 in Booking Master.")


if __name__ == "__main__":
    main()
