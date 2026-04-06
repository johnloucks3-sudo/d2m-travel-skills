#!/usr/bin/env python3
"""
Google Sheets Tab Creator for Thunderbird OS
=============================================

Automatically creates all required tabs in your Google Sheet with proper headers.
Run this ONCE before running any sweeps or weekly reports.
"""

import gspread
from google.oauth2 import service_account
from pathlib import Path

# Configuration
SHEET_ID = "1GFjUe8RvP-GT4YHGn0DYv_BEAZGXlYfwEicFrm8ANuU"
SERVICE_ACCOUNT_FILE = Path.home() / "Thunderbird" / "credentials.json"

# Tab definitions with headers
TABS = {
    "Ship Intelligence": [
        "Cruise Line", "Ship", "Voyage", "Departure", "Days", 
        "Price", "Availability", "Scraped At"
    ],
    
    "Pricing Tracker": [
        "Cruise Line", "Ship", "Voyage ID", "Old Price", "New Price", 
        "Change %", "Priority", "Detected At"
    ],
    
    "Availability Alerts": [
        "Cruise Line", "Ship", "Voyage ID", "Suite Category", 
        "Remaining", "Priority", "Detected At"
    ],
    
    "Travel Advisories": [
        "Country", "Level", "Advisory", "Last Updated", "Scraped At"
    ],
    
    "Port Weather": [
        "Port", "Date", "High", "Low", "Conditions", "Wind", "Precipitation %"
    ],
    
    "World Intelligence": [
        "Title", "Source", "URL", "Published", "Relevance", "Category", "Scraped At"
    ],
    
    "Tech News Monitor": [
        "Date", "Title", "Source", "Category", "Priority", 
        "Relevance", "Keywords", "URL", "Summary"
    ]
}

def create_sheets_tabs():
    """Create all required tabs in Google Sheet"""
    
    print("="*70)
    print("THUNDERBIRD GOOGLE SHEETS TAB CREATOR")
    print("="*70)
    print(f"\nSheet ID: {SHEET_ID}")
    print(f"Creating {len(TABS)} tabs...\n")
    
    try:
        # Authenticate
        creds = service_account.Credentials.from_service_account_file(
            str(SERVICE_ACCOUNT_FILE),
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        gc = gspread.authorize(creds)
        
        # Open sheet
        sheet = gc.open_by_key(SHEET_ID)
        print(f"✅ Connected to sheet: {sheet.title}\n")
        
        # Get existing tab names
        existing_tabs = [ws.title for ws in sheet.worksheets()]
        
        # Create each tab
        for tab_name, headers in TABS.items():
            if tab_name in existing_tabs:
                print(f"⏭️  Skipping '{tab_name}' (already exists)")
            else:
                print(f"📝 Creating '{tab_name}'...")
                
                # Create worksheet
                worksheet = sheet.add_worksheet(
                    title=tab_name,
                    rows=1000,
                    cols=len(headers)
                )
                
                # Add headers
                worksheet.append_row(headers)
                
                # Format header row (Dreams2Memories blue)
                worksheet.format('1', {
                    "backgroundColor": {
                        "red": 0.12,
                        "green": 0.28,
                        "blue": 0.53
                    },
                    "horizontalAlignment": "CENTER",
                    "textFormat": {
                        "foregroundColor": {
                            "red": 1.0,
                            "green": 1.0,
                            "blue": 1.0
                        },
                        "fontSize": 11,
                        "bold": True
                    }
                })
                
                print(f"   ✅ Created with {len(headers)} columns")
        
        print("\n" + "="*70)
        print("✨ ALL TABS CREATED SUCCESSFULLY ✨")
        print("="*70)
        print(f"\nView your sheet at:")
        print(f"https://docs.google.com/spreadsheets/d/{SHEET_ID}")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("\nTroubleshooting:")
        print("1. Check that credentials.json exists at ~/Thunderbird/credentials.json")
        print("2. Verify the service account has access to the Google Sheet")
        print("3. Make sure the Sheet ID is correct")
        return False
    
    return True

if __name__ == "__main__":
    create_sheets_tabs()
