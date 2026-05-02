#!/usr/bin/env python3
"""
Google Sheets API wrapper for Thunderbird SPSA operations.
Handles authentication, sheet creation, and data sync.
Uses OAuth2 token from drive_token.json (user account with Sheets access).
"""

import json
import logging
from pathlib import Path
from typing import Optional, List, Dict

import gspread
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

logger = logging.getLogger("thunderbird_sheets")

ROOT = Path.home() / "Thunderbird"
DRIVE_TOKEN_FILE = ROOT / "drive_token.json"
SHEETS_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]


def get_sheets_client():
    """Authenticate and return gspread client using OAuth2 user token."""
    if not DRIVE_TOKEN_FILE.exists():
        logger.error(f"Drive token file not found: {DRIVE_TOKEN_FILE}")
        return None

    try:
        # Load OAuth2 token from drive_token.json
        token_data = json.loads(DRIVE_TOKEN_FILE.read_text())
        creds = Credentials.from_authorized_user_info(token_data)

        # Refresh token if needed
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())

        return gspread.authorize(creds)
    except Exception as e:
        logger.error(f"Failed to authenticate with Google Sheets: {e}")
        return None


def get_or_create_spsa_sheet(sheet_title: str = "SPSA Cases") -> Optional[str]:
    """Get existing SPSA sheet or create new one.

    Returns sheet ID if successful, None on error.
    """
    client = get_sheets_client()
    if not client:
        return None

    try:
        # Try to find existing sheet
        for sheet in client.list_spreadsheet_files():
            if sheet["name"] == sheet_title:
                logger.info(f"Found existing sheet: {sheet['id']}")
                return sheet["id"]

        # Create new sheet
        logger.info(f"Creating new sheet: {sheet_title}")
        spreadsheet = client.create(sheet_title)
        sheet_id = spreadsheet.id
        logger.info(f"Created sheet: {sheet_id}")
        return sheet_id

    except Exception as e:
        logger.error(f"Failed to get/create sheet: {e}")
        return None


def update_spsa_sheet(rows: List[Dict], sheet_id: str = None, sheet_title: str = "SPSA Cases") -> bool:
    """Write SPSA case rows to Google Sheet.

    Args:
        rows: List of dicts with keys: Case ID, Severity, Source, Status, Problem, Decision, Outcome, Days to Close, Created, Closed
        sheet_id: Optional existing sheet ID
        sheet_title: Sheet name if creating new

    Returns:
        True if successful, False otherwise
    """
    if not rows:
        logger.info("No rows to sync")
        return True

    client = get_sheets_client()
    if not client:
        return False

    try:
        # Get or create sheet
        if not sheet_id:
            sheet_id = get_or_create_spsa_sheet(sheet_title)
        if not sheet_id:
            return False

        # Open spreadsheet
        spreadsheet = client.open_by_key(sheet_id)

        # Use first worksheet or create one
        try:
            worksheet = spreadsheet.worksheet("SPSA Data")
        except gspread.exceptions.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title="SPSA Data", rows=1000, cols=10)

        # Clear existing data
        worksheet.clear()

        # Write headers
        headers = ["Case ID", "Severity", "Source", "Status", "Problem", "Decision", "Outcome", "Days to Close", "Created", "Closed"]
        worksheet.append_row(headers)

        # Write rows
        for row in rows:
            data = [
                row.get("Case ID", ""),
                row.get("Severity", ""),
                row.get("Source", ""),
                row.get("Status", ""),
                row.get("Problem", ""),
                row.get("Decision", ""),
                row.get("Outcome", ""),
                row.get("Days to Close", ""),
                row.get("Created", ""),
                row.get("Closed", ""),
            ]
            worksheet.append_row(data)

        logger.info(f"✅ Synced {len(rows)} rows to Google Sheet: {sheet_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to update Google Sheet: {e}")
        return False


def get_spsa_sheet_id_from_config() -> Optional[str]:
    """Load SPSA sheet ID from config if saved."""
    config_file = ROOT / "config" / "spsa_sheets_config.json"
    if config_file.exists():
        try:
            config = json.loads(config_file.read_text())
            return config.get("sheet_id")
        except Exception:
            return None
    return None


def save_spsa_sheet_id_to_config(sheet_id: str) -> None:
    """Save SPSA sheet ID to config."""
    config_file = ROOT / "config" / "spsa_sheets_config.json"
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_file.write_text(json.dumps({"sheet_id": sheet_id}, indent=2))
    logger.info(f"Saved sheet ID to config: {sheet_id}")
