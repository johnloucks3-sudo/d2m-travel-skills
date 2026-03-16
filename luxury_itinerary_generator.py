#!/usr/bin/env python3
"""
GOLD STANDARD BRIEF GENERATOR - Python Edition v2.0
Generates luxury travel itineraries from Google Docs/Sheets and exports as PDF

SETUP:
1. Install dependencies: pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client weasyprint
2. Set up Google Cloud credentials: https://cloud.google.com/docs/authentication/client-credentials
3. Place credentials.json in the same directory as this script
4. Update CONFIG section below with your Google Doc/Sheet IDs
5. Run: python luxury_itinerary_generator.py

FIRST RUN:
- Will open browser to authorize Google API access
- Saves token.pickle for future runs (no re-auth needed)
"""

import os
import json
import pickle
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Google API imports
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.auth.oauthlib.flow import InstalledAppFlow
from google.api_core.exceptions import GoogleAPIError
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# PDF generation
from weasyprint import HTML, CSS
from io import BytesIO

# ============================================
# CONFIGURATION - EDIT THIS SECTION
# ============================================

CONFIG = {
    # Google Cloud credentials file (download from Google Cloud Console)
    "CREDENTIALS_FILE": "credentials.json",
    
    # Google Docs ID containing client/trip data
    # Format: https://docs.google.com/document/d/{GOOGLE_DOC_ID}/edit
    "GOOGLE_DOC_ID": "",
    
    # Google Sheet ID containing client data (alternative to Doc)
    # Format: https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/edit
    "GOOGLE_SHEET_ID": "",
    
    # Where to save PDFs (~ = user's home, Documents folder)
    "OUTPUT_FOLDER": str(Path.home() / "Documents" / "Luxury_Itineraries"),
    
    # Google API scopes (don't change unless you know what you're doing)
    "SCOPES": ["https://www.googleapis.com/auth/documents.readonly",
               "https://www.googleapis.com/auth/spreadsheets.readonly"]
}

# ============================================
# GOOGLE API AUTHENTICATION
# ============================================

def authenticate_google():
    """Authenticate with Google API using OAuth 2.0"""
    creds = None
    
    # Load existing token if available
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)
    
    # If no valid credentials, get new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CONFIG["CREDENTIALS_FILE"]):
                raise FileNotFoundError(
                    f"❌ {CONFIG['CREDENTIALS_FILE']} not found.\n"
                    "Download from: https://cloud.google.com/docs/authentication/client-credentials"
                )
            
            flow = InstalledAppFlow.from_client_secrets_file(
                CONFIG["CREDENTIALS_FILE"], CONFIG["SCOPES"]
            )
            creds = flow.run_local_server(port=0)
        
        # Save token for future use
        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)
    
    return creds

# ============================================
# DATA EXTRACTION FROM GOOGLE DOCS
# ============================================

def extract_from_google_doc(doc_id: str) -> Dict:
    """Extract client data from a Google Doc"""
    try:
        creds = authenticate_google()
        docs_service = build("docs", "v1", credentials=creds)
        
        document = docs_service.documents().get(documentId=doc_id).execute()
        content = document.get('body', {}).get('content', [])
        
        # Parse document text
        text = ""
        for element in content:
            if 'paragraph' in element:
                for run in element.get('paragraph', {}).get('elements', []):
                    if 'textRun' in run:
                        text += run['textRun']['content']
        
        # Extract key-value pairs (format: "Field: Value")
        data = {}
        for line in text.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                data[key.strip()] = value.strip()
        
        return data
    
    except HttpError as error:
        print(f"❌ Google Docs API error: {error}")
        return {}

# ============================================
# DATA EXTRACTION FROM GOOGLE SHEETS
# ============================================

def extract_from_google_sheet(sheet_id: str, sheet_name: str = "Sheet1") -> List[Dict]:
    """Extract client data from a Google Sheet"""
    try:
        creds = authenticate_google()
        sheets_service = build("sheets", "v4", credentials=creds)
        
        # Get values from sheet
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=f"{sheet_name}!A:Z"
        ).execute()
        
        values = result.get('values', [])
        if len(values) < 2:
            raise ValueError("Sheet must have headers in first row and data below")
        
        headers = values[0]
        data_list = []
        
        # Convert rows to dict
        for row in values[1:]:
            row_data = {}
            for i, header in enumerate(headers):
                if i < len(row):
                    row_data[header] = row[i]
            data_list.append(row_data)
        
        return data_list
    
    except HttpError as error:
        print(f"❌ Google Sheets API error: {error}")
        return []

# ============================================
# HTML TEMPLATE
# ============================================

def generate_html(data: Dict) -> str:
    """Generate luxury itinerary HTML"""
    
    # Validate required fields
    required = ["Client_Name", "Trip_Name", "Itinerary_Summary", "Start_Date", "End_Date"]
    for field in required:
        if field not in data or not data[field]:
            raise ValueError(f"Missing required field: {field}")
    
    # Parse days if provided as JSON string
    days = data.get("days", [])
    if isinstance(days, str):
        try:
            days = json.loads(days)
        except:
            days = []
    
    # HTML Template
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Luxury Itinerary — {escape_html(data.get('Client_Name', ''))}</title>
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;500;600;700;800;900&family=Inter:wght@200;300;400;500;600;700&family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;1,400&display=swap" rel="stylesheet">
    <style>
        /* ========== PRINT & RESET ========== */
        @page {{ margin: 0; size: letter; }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }}
        
        /* ========== COLOR PALETTE ========== */
        :root {{
            --navy-primary: #1a2744;
            --navy-dark: #0d1a30;
            --navy-light: #2e6b8a;
            --gold-primary: #c9a84c;
            --gold-accent: #e8d9c3;
            --teal-accent: #2a8b96;
            --emerald-accent: #1f6b4e;
            --amber-accent: #b8860b;
            --slate-accent: #556b7f;
            --cream-bg: #faf8f2;
            --cream-light: #f5f2ed;
            --text-primary: #2c2c2c;
            --text-secondary: #5a5a5a;
            --confirmation-green: #27ae60;
            --confirmation-light: #e8f5e9;
        }}
        
        /* ========== BASE TYPOGRAPHY ========== */
        body {{
            font-family: 'Inter', sans-serif;
            background-color: var(--cream-bg);
            color: var(--text-primary);
            line-height: 1.8;
            font-size: 15px;
            margin: 0;
            padding: 0;
            font-weight: 400;
        }}
        
        /* ========== MASTER WRAPPER ========== */
        .master-bg {{
            background-color: var(--cream-bg);
            width: 100%;
            min-height: 100%;
            padding-bottom: 2px;
        }}
        
        /* ========== COVER PAGE ========== */
        .cover {{
            background: linear-gradient(135deg, var(--navy-primary) 0%, var(--navy-dark) 50%, var(--navy-light) 100%);
            color: white;
            text-align: center;
            padding: 90px 20px;
            position: relative;
            overflow: hidden;
        }}
        
        .cover::before {{
            content: '';
            position: absolute;
            top: -50%;
            right: -10%;
            width: 400px;
            height: 400px;
            background: rgba(201, 168, 76, 0.03);
            border-radius: 50%;
            z-index: 0;
        }}
        
        .cover::after {{
            content: '';
            position: absolute;
            bottom: -30%;
            left: -5%;
            width: 300px;
            height: 300px;
            background: rgba(201, 168, 76, 0.02);
            border-radius: 50%;
            z-index: 0;
        }}
        
        .cover-content {{
            position: relative;
            z-index: 1;
            max-width: 800px;
            margin: 0 auto;
        }}
        
        .cover-ornament {{
            color: var(--gold-primary);
            font-size: 28px;
            letter-spacing: 16px;
            margin-bottom: 35px;
            font-family: 'Playfair Display', serif;
            font-weight: 400;
        }}
        
        .cover .guests {{
            font-family: 'Cormorant Garamond', serif;
            font-size: 18px;
            font-style: italic;
            color: rgba(255, 255, 255, 0.75);
            margin-bottom: 20px;
            letter-spacing: 1px;
        }}
        
        .cover h1 {{
            font-family: 'Playfair Display', serif;
            font-size: 56px;
            font-weight: 800;
            margin: 0 0 12px 0;
            line-height: 1.15;
            letter-spacing: -1px;
        }}
        
        .cover h1 .gold {{
            color: var(--gold-primary);
            display: block;
            font-size: 48px;
            font-weight: 700;
            margin-top: 8px;
        }}
        
        .cover .subtitle {{
            font-family: 'Cormorant Garamond', serif;
            font-size: 26px;
            font-style: italic;
            color: rgba(255, 255, 255, 0.8);
            margin: 30px 0;
            font-weight: 400;
            line-height: 1.4;
        }}
        
        .cover .dates {{
            font-size: 13px;
            letter-spacing: 4px;
            text-transform: uppercase;
            color: rgba(255, 255, 255, 0.6);
            border-top: 2px solid rgba(201, 168, 76, 0.4);
            border-bottom: 2px solid rgba(201, 168, 76, 0.4);
            padding: 20px 0;
            margin-top: 35px;
            font-weight: 500;
        }}
        
        /* ========== SECTION HEADERS ========== */
        .section-header {{
            padding: 55px 24px 25px;
            text-align: center;
            max-width: 900px;
            margin: 0 auto;
            background-color: var(--cream-bg);
        }}
        
        .section-header .section-number {{
            font-size: 11px;
            letter-spacing: 4px;
            text-transform: uppercase;
            color: var(--gold-primary);
            margin-bottom: 12px;
            font-weight: 600;
        }}
        
        .section-header h2 {{
            font-family: 'Playfair Display', serif;
            font-size: 36px;
            color: var(--navy-primary);
            margin-bottom: 10px;
            font-weight: 700;
            letter-spacing: -0.5px;
        }}
        
        .section-header .section-sub {{
            font-family: 'Cormorant Garamond', serif;
            font-size: 18px;
            font-style: italic;
            color: var(--text-secondary);
            font-weight: 400;
        }}
        
        .divider {{
            width: 80px;
            height: 2px;
            background: linear-gradient(90deg, transparent, var(--gold-primary), transparent);
            margin: 22px auto 45px;
        }}
        
        /* ========== QUICK REFERENCE CARDS ========== */
        .quick-ref {{
            max-width: 900px;
            margin: 0 auto;
            padding: 0 24px 50px;
            background-color: var(--cream-bg);
        }}
        
        .ref-grid {{
            width: 100%;
            border-spacing: 18px;
            border-collapse: separate;
        }}
        
        .ref-card {{
            background: white;
            border-radius: 12px;
            padding: 28px;
            border-top: 4px solid var(--navy-primary);
            vertical-align: top;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06), 0 1px 3px rgba(0, 0, 0, 0.04);
        }}
        
        .ref-card.air {{
            border-top-color: var(--teal-accent);
        }}
        
        .ref-card.hotel {{
            border-top-color: var(--amber-accent);
        }}
        
        .ref-card.transport {{
            border-top-color: var(--slate-accent);
        }}
        
        .ref-card.tours {{
            border-top-color: var(--emerald-accent);
        }}
        
        .ref-card-header {{
            display: flex;
            align-items: center;
            margin-bottom: 16px;
        }}
        
        .ref-icon {{
            font-size: 24px;
            width: 48px;
            height: 48px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-right: 12px;
            flex-shrink: 0;
        }}
        
        .ref-card h4 {{
            font-size: 10px;
            letter-spacing: 2.5px;
            text-transform: uppercase;
            color: var(--text-secondary);
            margin-bottom: 8px;
            font-weight: 700;
        }}
        
        .ref-card .ref-name {{
            font-family: 'Playfair Display', serif;
            font-size: 18px;
            font-weight: 600;
            color: var(--navy-primary);
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        
        .ref-card .ref-detail {{
            font-size: 13px;
            color: var(--text-secondary);
            line-height: 1.7;
            font-weight: 400;
        }}
        
        .status-badge {{
            display: inline-flex;
            align-items: center;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 1.5px;
            text-transform: uppercase;
            padding: 4px 10px;
            border-radius: 20px;
            gap: 4px;
            flex-shrink: 0;
            background: var(--confirmation-light);
            color: var(--confirmation-green);
            box-shadow: inset 0 0 12px rgba(39, 174, 96, 0.1);
        }}
        
        .status-badge::before {{
            content: '✓';
            font-weight: 900;
        }}
        
        /* ========== DAILY CHRONICLE ========== */
        .day-section {{
            max-width: 900px;
            margin: 0 auto;
            padding: 0 24px 50px;
            background-color: var(--cream-bg);
        }}
        
        .day-entry {{
            background: white;
            border-radius: 14px;
            margin-bottom: 35px;
            overflow: hidden;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06), 0 1px 3px rgba(0, 0, 0, 0.04);
            border-left: 4px solid var(--gold-primary);
        }}
        
        .day-header {{
            background: linear-gradient(135deg, var(--navy-primary) 0%, var(--navy-light) 100%);
            padding: 28px 24px;
            color: white;
            display: flex;
            align-items: center;
            gap: 24px;
        }}
        
        .day-number {{
            font-family: 'Playfair Display', serif;
            font-size: 48px;
            font-weight: 800;
            min-width: 70px;
            line-height: 1;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.2);
        }}
        
        .day-number::after {{
            content: '';
            display: block;
            width: 50px;
            height: 2px;
            background: var(--gold-primary);
            margin-top: 8px;
        }}
        
        .day-meta {{
            flex: 1;
        }}
        
        .day-meta .day-location {{
            font-family: 'Cormorant Garamond', serif;
            font-size: 26px;
            font-style: italic;
            opacity: 0.95;
            font-weight: 400;
            line-height: 1.3;
        }}
        
        .day-body {{
            padding: 28px;
        }}
        
        .day-body p {{
            margin-bottom: 20px;
            line-height: 1.9;
            color: var(--text-secondary);
            font-weight: 400;
        }}
        
        .logistics-box {{
            background: linear-gradient(135deg, var(--cream-light) 0%, rgba(201, 168, 76, 0.04) 100%);
            border-left: 4px solid var(--teal-accent);
            border-radius: 10px;
            padding: 20px 24px;
            margin-bottom: 25px;
            font-size: 13px;
        }}
        
        .logistics-box h5 {{
            font-size: 10px;
            letter-spacing: 2.5px;
            text-transform: uppercase;
            color: var(--teal-accent);
            margin-bottom: 12px;
            font-weight: 700;
        }}
        
        .log-row {{
            display: flex;
            padding: 8px 0;
            border-bottom: 1px solid rgba(42, 139, 150, 0.1);
            align-items: flex-start;
            gap: 20px;
        }}
        
        .log-row:last-child {{
            border-bottom: none;
        }}
        
        .log-label {{
            font-weight: 600;
            color: var(--navy-primary);
            width: 35%;
            flex-shrink: 0;
            font-size: 12px;
            letter-spacing: 0.5px;
        }}
        
        .log-value {{
            color: var(--text-secondary);
            flex: 1;
            font-weight: 400;
        }}
        
        /* ========== FOOTER ========== */
        .doc-footer {{
            background: linear-gradient(135deg, var(--navy-primary) 0%, var(--navy-dark) 100%);
            color: rgba(255, 255, 255, 0.7);
            text-align: center;
            padding: 45px 24px;
            font-size: 12px;
            margin-top: 60px;
        }}
        
        .doc-footer .footer-gold {{
            color: var(--gold-primary);
            font-family: 'Playfair Display', serif;
            font-size: 20px;
            margin-bottom: 15px;
            font-weight: 600;
            letter-spacing: 2px;
        }}
        
        .doc-footer p {{
            margin: 6px 0;
            font-weight: 400;
        }}
        
        .doc-footer p:last-child {{
            font-size: 11px;
            opacity: 0.5;
            margin-top: 12px;
        }}
    </style>
</head>
<body>
<div class="master-bg">

    <!-- COVER PAGE -->
    <div class="cover">
        <div class="cover-content">
            <div class="cover-ornament">✦ ✦ ✦</div>
            <div class="cover guests">{escape_html(data.get('Client_Name', ''))}</div>
            <h1>{escape_html(data.get('Trip_Name', '')).replace(r'(\d+-Day)', r'<span class="gold">\1</span>')}</h1>
            <div class="subtitle">{escape_html(data.get('Itinerary_Summary', ''))}</div>
            <div class="dates">{escape_html(data.get('Start_Date', ''))} – {escape_html(data.get('End_Date', ''))}</div>
        </div>
    </div>

    <!-- SECTION I: QUICK REFERENCE -->
    <div class="section-header">
        <div class="section-number">Section I</div>
        <h2>Quick Reference & Confirmations</h2>
        <div class="section-sub">All booking numbers and key contacts at a glance</div>
    </div>
    <div class="divider"></div>

    <div class="quick-ref">
        <table class="ref-grid">
            <tr>
                <td class="ref-card air confirmed">
                    <div class="ref-card-header">
                        <div class="ref-icon">✈️</div>
                        <div>
                            <h4>Aerial Logistics</h4>
                            <div class="ref-name">Flight Status <span class="status-badge confirmed">Confirmed</span></div>
                        </div>
                    </div>
                    <div class="ref-detail">{(data.get('Air_Details', '')).replace(chr(10), '<br>')}</div>
                </td>
                <td class="ref-card hotel confirmed">
                    <div class="ref-card-header">
                        <div class="ref-icon">🏨</div>
                        <div>
                            <h4>Accommodations</h4>
                            <div class="ref-name">Base Property <span class="status-badge confirmed">Confirmed</span></div>
                        </div>
                    </div>
                    <div class="ref-detail">{(data.get('Hotel_Details', '')).replace(chr(10), '<br>')}</div>
                </td>
            </tr>
            <tr>
                <td class="ref-card transport confirmed">
                    <div class="ref-card-header">
                        <div class="ref-icon">🚗</div>
                        <div>
                            <h4>Transportation</h4>
                            <div class="ref-name">Ground Transfer <span class="status-badge confirmed">Confirmed</span></div>
                        </div>
                    </div>
                    <div class="ref-detail">{(data.get('Transfer_Details', '')).replace(chr(10), '<br>')}</div>
                </td>
                <td class="ref-card tours confirmed">
                    <div class="ref-card-header">
                        <div class="ref-icon">🏛️</div>
                        <div>
                            <h4>Curated Tours</h4>
                            <div class="ref-name">Excursions <span class="status-badge confirmed">Confirmed</span></div>
                        </div>
                    </div>
                    <div class="ref-detail">{(data.get('Tour_Details', '')).replace(chr(10), '<br>')}</div>
                </td>
            </tr>
        </table>
    </div>

    <!-- SECTION II: DAILY CHRONICLE -->
    <div class="section-header">
        <div class="section-number">Section II</div>
        <h2>The Daily Chronicle</h2>
        <div class="section-sub">Your day-by-day itinerary</div>
    </div>
    <div class="divider"></div>

    <div class="day-section">
"""
    
    # Add day entries
    if days:
        for idx, day in enumerate(days, 1):
            day_num = day.get('dayNumber', idx)
            location = escape_html(day.get('location', 'Location TBD'))
            logistics = (day.get('logistics', 'To be finalized')).replace('\n', '<br>')
            romance = (day.get('romance', '')).replace('\n', '<br><br>')
            
            html += f"""
        <div class="day-entry">
            <div class="day-header">
                <div class="day-number">{str(day_num).zfill(2)}</div>
                <div class="day-meta">
                    <div class="day-location">{location}</div>
                </div>
            </div>
            <div class="day-body">
                <div class="logistics-box">
                    <h5>📋 Logistics & Details</h5>
                    <div class="log-row">
                        <span class="log-label">Timing & Info</span>
                        <span class="log-value">{logistics}</span>
                    </div>
                </div>
                <p>{romance}</p>
            </div>
        </div>
"""
    
    html += """
    </div>

    <!-- FOOTER -->
    <div class="doc-footer">
        <div class="footer-gold">✦ Bon Voyage ✦</div>
        <p>Prepared Exclusively For: """ + escape_html(data.get('Client_Name', '')) + """</p>
        <p>All information subject to change. Curated with precision for your luxury travel experience.</p>
    </div>

</div>
</body>
</html>
"""
    
    return html

# ============================================
# PDF GENERATION
# ============================================

def generate_pdf(html_content: str, output_path: str) -> bool:
    """Generate PDF from HTML using WeasyPrint"""
    try:
        # Ensure output directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Generate PDF
        HTML(string=html_content).write_pdf(output_path)
        return True
    except Exception as e:
        print(f"❌ PDF generation error: {e}")
        return False

# ============================================
# UTILITY FUNCTIONS
# ============================================

def escape_html(text: str) -> str:
    """Escape HTML special characters"""
    if not text:
        return ""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;"))

# ============================================
# MAIN EXECUTION
# ============================================

def main():
    """Main execution function"""
    
    print("=" * 60)
    print("GOLD STANDARD BRIEF GENERATOR - Python Edition")
    print("=" * 60)
    
    # Verify configuration
    if not CONFIG["GOOGLE_DOC_ID"] and not CONFIG["GOOGLE_SHEET_ID"]:
        print("❌ ERROR: No GOOGLE_DOC_ID or GOOGLE_SHEET_ID configured")
        print("   Update CONFIG section in this script with your Google Doc/Sheet ID")
        sys.exit(1)
    
    # Create output directory
    output_folder = Path(CONFIG["OUTPUT_FOLDER"])
    output_folder.mkdir(parents=True, exist_ok=True)
    print(f"📁 Output folder: {output_folder}")
    
    # Authenticate with Google
    print("\n🔐 Authenticating with Google API...")
    try:
        creds = authenticate_google()
        print("✅ Authentication successful")
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        sys.exit(1)
    
    # Extract data
    print("\n📖 Extracting client data...")
    data_list = []
    
    if CONFIG["GOOGLE_DOC_ID"]:
        print(f"   From Google Doc: {CONFIG['GOOGLE_DOC_ID'][:20]}...")
        data = extract_from_google_doc(CONFIG["GOOGLE_DOC_ID"])
        if data:
            data_list.append(data)
    
    if CONFIG["GOOGLE_SHEET_ID"]:
        print(f"   From Google Sheet: {CONFIG['GOOGLE_SHEET_ID'][:20]}...")
        data_list.extend(extract_from_google_sheet(CONFIG["GOOGLE_SHEET_ID"]))
    
    if not data_list:
        print("❌ No data extracted from Google Doc/Sheet")
        sys.exit(1)
    
    print(f"✅ Extracted data for {len(data_list)} client(s)")
    
    # Generate PDFs
    print("\n📄 Generating PDFs...")
    success_count = 0
    
    for idx, data in enumerate(data_list, 1):
        try:
            client_name = data.get("Client_Name", f"Client_{idx}")
            print(f"\n   [{idx}/{len(data_list)}] {client_name}...")
            
            # Generate HTML
            html = generate_html(data)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"LUXURY_BRIEF_{client_name.replace(' ', '_')}_{timestamp}.pdf"
            output_path = output_folder / filename
            
            # Create PDF
            if generate_pdf(html, str(output_path)):
                print(f"       ✅ Generated: {filename}")
                print(f"       📍 Location: {output_path}")
                success_count += 1
            else:
                print(f"       ❌ Failed to generate PDF")
        
        except Exception as e:
            print(f"       ❌ Error: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print(f"COMPLETE: {success_count}/{len(data_list)} PDFs generated successfully")
    print(f"📁 Output folder: {output_folder}")
    print("=" * 60)
    
    if success_count == len(data_list):
        print("✅ All itineraries generated!")
        return 0
    else:
        print(f"⚠️  {len(data_list) - success_count} itinerary(ies) failed")
        return 1

if __name__ == "__main__":
    exit(main())
