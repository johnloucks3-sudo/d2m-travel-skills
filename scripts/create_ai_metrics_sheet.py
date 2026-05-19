import sys
import gspread
from pathlib import Path

# Add Thunderbird root to path to import api
sys.path.append("/home/john/Thunderbird")
from api.thunderbird_google_auth import get_credentials

def main():
    try:
        # Get authenticated credentials
        creds = get_credentials()
        # Authorize gspread
        client = gspread.authorize(creds)

        # Create sheet
        sheet_name = "D2M_AI_Metrics"
        sh = client.create(sheet_name)
        
        # Configure headers
        headers = [
            "Timestamp", "Messages", "CostUSD", "CostPerMsg", 
            "BudgetStatus", "FreeTier", "Session%", "Weekly%", 
            "Sonnet%", "Daily$", "Monthly$", "Credits$"
        ]
        
        # Select first sheet (usually 'Sheet1')
        worksheet = sh.sheet1
        worksheet.append_row(headers)
        
        sheet_id = sh.id
        print(f"SUCCESS: Sheet '{sheet_name}' created.")
        print(f"Sheet ID: {sheet_id}")
        print(f"URL: {sh.url}")
        
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
