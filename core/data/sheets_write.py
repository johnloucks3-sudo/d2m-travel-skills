#!/usr/bin/env python3
"""
sheets_write.py — Google Sheets read/write helpers for D2M Wing operations.

Covers commission tracking, FPD monitoring, client pipeline updates.
Auth: gmail_token.json (johnloucks3 account, confirmed 9-scope 2026-06-14)

Usage:
    from core.data.sheets_write import read_sheet, write_row, update_cell, append_row
    data = read_sheet(BOOKING_SHEET_ID, "Commission!A:F")

Known sheet IDs:
  Bookings-2026-01-22: 1sdN6ghvG2EgaqOxyq3V6TRRjKBFmNrqX0FUSY-9A9VI
  D2M_AI_Metrics:      16fuzoeD5WiR6loB7C2EbQJVbJ65admvrF_8oX8LBOd4
  EARA D2M:            1GFjUe8RvP-GT4YHGn0DYv_BEAZGXlYfwEicFrm8ANuU

Authority: SO-2026-05-04 §XII.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parents[2]

# Known sheet IDs
BOOKINGS_SHEET_ID = "1sdN6ghvG2EgaqOxyq3V6TRRjKBFmNrqX0FUSY-9A9VI"
AI_METRICS_SHEET_ID = "16fuzoeD5WiR6loB7C2EbQJVbJ65admvrF_8oX8LBOd4"


def _get_service():
    sys.path.insert(0, str(ROOT))
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from api.thunderbird_google_auth import TOKEN_FILE

    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE))
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN_FILE.write_text(creds.to_json())
    return build("sheets", "v4", credentials=creds)


def read_sheet(spreadsheet_id: str, range_: str) -> list[list]:
    """Read a range from a Google Sheet.

    Args:
        spreadsheet_id: Sheet ID
        range_: A1 notation range (e.g. "Sheet1!A:F" or "A1:Z100")

    Returns:
        List of rows (each row is a list of values)
    """
    svc = _get_service()
    result = svc.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=range_,
        valueRenderOption="UNFORMATTED_VALUE",
        dateTimeRenderOption="FORMATTED_STRING",
    ).execute()
    return result.get("values", [])


def write_row(spreadsheet_id: str, range_: str, values: list) -> dict:
    """Write a single row to a specific range.

    Args:
        spreadsheet_id: Sheet ID
        range_: A1 notation for the row start (e.g. "Sheet1!A5")
        values: List of cell values

    Returns:
        API response dict
    """
    svc = _get_service()
    body = {"values": [values]}
    result = svc.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=range_,
        valueInputOption="USER_ENTERED",
        body=body,
    ).execute()
    return result


def append_row(spreadsheet_id: str, range_: str, values: list) -> dict:
    """Append a row to the end of a data range.

    Args:
        spreadsheet_id: Sheet ID
        range_: Sheet/table range to append to (e.g. "Sheet1!A:Z")
        values: List of cell values for the new row

    Returns:
        API response dict with updated range
    """
    svc = _get_service()
    body = {"values": [values]}
    result = svc.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=range_,
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body=body,
    ).execute()
    return result


def update_cell(spreadsheet_id: str, cell: str, value) -> dict:
    """Update a single cell.

    Args:
        spreadsheet_id: Sheet ID
        cell: A1 notation (e.g. "Sheet1!B7")
        value: New cell value

    Returns:
        API response dict
    """
    return write_row(spreadsheet_id, cell, [value])


def batch_update(spreadsheet_id: str, updates: list[dict]) -> dict:
    """Write multiple ranges in one API call.

    Args:
        spreadsheet_id: Sheet ID
        updates: List of {range: "A1 notation", values: [[row1], [row2]...]}

    Returns:
        API response dict
    """
    svc = _get_service()
    body = {"valueInputOption": "USER_ENTERED", "data": updates}
    result = svc.spreadsheets().values().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body=body,
    ).execute()
    return result


def clear_range(spreadsheet_id: str, range_: str) -> dict:
    """Clear all values in a range (formatting preserved)."""
    svc = _get_service()
    return svc.spreadsheets().values().clear(
        spreadsheetId=spreadsheet_id,
        range=range_,
    ).execute()


# ── D2M-specific helpers ─────────────────────────────────────────────────────

def log_commission_entry(
    client: str,
    cruise_line: str,
    sail_date: str,
    booking_ref: str,
    gross_commission: float,
    d2m_share: float,
    status: str = "PENDING",
) -> dict:
    """Append a new commission entry to the Bookings tracking sheet."""
    from datetime import datetime
    row = [
        datetime.now().strftime("%Y-%m-%d"),
        client,
        cruise_line,
        sail_date,
        booking_ref,
        gross_commission,
        d2m_share,
        status,
    ]
    return append_row(BOOKINGS_SHEET_ID, "Commission!A:H", row)


def log_ai_metric(metric_name: str, value, notes: str = "") -> dict:
    """Append a metric entry to the D2M_AI_Metrics sheet."""
    from datetime import datetime
    row = [datetime.now().strftime("%Y-%m-%d %H:%M"), metric_name, value, notes]
    return append_row(AI_METRICS_SHEET_ID, "Metrics!A:D", row)


def get_open_fpds() -> list[dict]:
    """Read the Bookings sheet and return rows with unpaid FPDs."""
    rows = read_sheet(BOOKINGS_SHEET_ID, "Bookings!A:Z")
    if not rows:
        return []
    headers = rows[0]
    results = []
    for row in rows[1:]:
        row_dict = dict(zip(headers, row))
        if "FPD" in str(row_dict.get("Status", "")) or str(row_dict.get("FPD_Status", "")).upper() == "UNPAID":
            results.append(row_dict)
    return results


if __name__ == "__main__":
    # Quick test
    print("Reading Bookings sheet structure...")
    rows = read_sheet(BOOKINGS_SHEET_ID, "A1:Z3")
    for r in rows:
        print(r)
