import os
import logging
import gspread
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Template & PDF Generation
from jinja2 import Template
from weasyprint import HTML
import pdfkit

# Google APIs
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Gemini via OpenAI SDK
from openai import OpenAI

# ============================================================================
# 0. LOGGING CONFIGURATION
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/john/Thunderbird/itinerary_generation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# 1. CONFIGURATION
# ============================================================================
class Config:
    # --- GEMINI SETTINGS ---
    GEMINI_API_KEY = "***REMOVED-SECRET***"
    GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
    GEMINI_MODEL = "gemini-2.5-flash"

    # --- GOOGLE SHEETS & DRIVE IDs ---
    GOOGLE_SHEET_ID = "1GFjUe8RvP-GT4YHGn0DYv_BEAZGXlYfwEicFrm8ANuU"
    BOOKING_MASTER_TAB = "Booking Master"
    DAILY_ITINERARY_TAB = "Daily Itinerary"
    BACKUP_TABS = ["Daily Itinerary A", "Daily Itinerary Bucket"]

    ART_FOLDER_ID = "1V_iUoy5oXs8RxY5S4-2QSHTXueGircnQ" # Thunderbird Art Folder

    SERVICE_ACCOUNT_FILE = '/home/john/Thunderbird/credentials.json'

    # --- OUTPUT FOLDERS ---
    HTML_OUTPUT_FOLDER = r"/home/john/Thunderbird"
    PDF_OUTPUT_FOLDER = r"/home/john/Thunderbird"

    # --- TRAVEL AGENT INFO ---
    TRAVEL_AGENT_NAME = "Dreams2Memories Travel"
    TRAVEL_AGENT_EMAIL = "johnloucks3@gmail.com"
    TRAVEL_AGENT_PHONE = "(719)-291-0742"

    # --- EXTERNAL APIs ---
    PEXELS_KEY = "***REMOVED-SECRET***"
    UNSPLASH_KEY = "***REMOVED-SECRET***"

# ============================================================================
# 2. HTML TEMPLATE
# ============================================================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{{ client_name }}'s {{ trip_name }} Itinerary</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #2c3e50; background: #ecf0f1; }
        .container { max-width: 1000px; margin: 0 auto; background: white; box-shadow: 0 0 30px rgba(0,0,0,0.1); }
        .header { background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%); color: white; padding: 80px 50px; text-align: center; border-bottom: 5px solid #d4af37; }
        .header h1 { font-size: 2.8em; margin-bottom: 15px; font-weight: 300; }
        .header .subtitle { font-size: 1.3em; font-style: italic; margin: 15px 0; opacity: 0.95; }
        .header .meta { margin-top: 30px; font-size: 1em; opacity: 0.9; border-top: 1px solid rgba(255,255,255,0.3); padding-top: 20px; }
        .header .meta-item { display: inline-block; margin: 0 20px; }
        .booking-summary { background: #f8f9fa; padding: 40px 50px; border-bottom: 2px solid #e9ecef; display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 30px; text-align: center; }
        .summary-item .label { font-size: 0.9em; color: #7f8c8d; text-transform: uppercase; margin-bottom: 8px; }
        .summary-item .value { font-size: 1.4em; font-weight: bold; color: #2c3e50; }
        .ports-section { padding: 50px; }
        .ports-section h2 { text-align: center; font-size: 2em; margin-bottom: 40px; border-bottom: 3px solid #d4af37; padding-bottom: 15px; }
        .port-entry { margin-bottom: 50px; page-break-inside: avoid; border: 1px solid #ecf0f1; padding: 30px; border-radius: 8px; background: #fafbfc; }
        .port-header { display: flex; justify-content: space-between; margin-bottom: 25px; padding-bottom: 15px; border-bottom: 2px solid #d4af37; }
        .port-info h3 { font-size: 1.8em; margin-bottom: 8px; }
        .port-times { font-size: 0.95em; color: #7f8c8d; }
        .port-day { font-size: 1.1em; color: #d4af37; font-weight: bold; }
        .image-gallery { display: flex; gap: 20px; margin: 25px 0; }
        .image-wrapper { flex: 1; }
        .port-image { width: 100%; height: 300px; object-fit: cover; border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
        .image-credit { font-size: 0.85em; color: #95a5a6; text-align: right; margin-top: 8px; font-style: italic; }
        .romance-narrative { font-size: 1.1em; line-height: 1.8; color: #34495e; margin: 20px 0; padding: 20px; border-left: 5px solid #d4af37; background: white; }
        .description { font-size: 1em; line-height: 1.7; color: #555; margin: 15px 0; }
        .footer { background: #2c3e50; color: white; padding: 50px; text-align: center; border-top: 5px solid #d4af37; }
        .footer a { color: #d4af37; text-decoration: none; }
        @media print { body { background: white; } .container { box-shadow: none; max-width: 100%; } .port-entry { border: none; padding: 0 0 30px 0; } }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{{ client_name }}'s Cruise Itinerary</h1>
            <div class="subtitle">{{ trip_name }} | {{ supplier }}</div>
            <div class="meta">
                <div class="meta-item"><strong>{{ start_date }}</strong> to <strong>{{ end_date }}</strong></div>
                <div class="meta-item"><strong>{{ num_nights }}</strong> nights</div>
                <div class="meta-item"><strong>{{ num_ports }}</strong> ports</div>
            </div>
        </div>

        <div class="booking-summary">
            <div class="summary-item"><div class="label">Confirmation #</div><div class="value">{{ confirmation_number }}</div></div>
            <div class="summary-item"><div class="label">Travelers</div><div class="value">{{ travelers }}</div></div>
            <div class="summary-item"><div class="label">Trip Cost</div><div class="value">${{ total_cost }}</div></div>
        </div>

        <div class="ports-section">
            <h2>Your Ports of Call</h2>
            {% for port in ports %}
            <div class="port-entry">
                <div class="port-header">
                    <div class="port-info">
                        <h3>{{ port.port_location }}</h3>
                        <div class="port-times">📍 Arrive: {{ port.docking_time }} | Depart: {{ port.departure_time }}</div>
                    </div>
                    <div class="port-day">Day {{ port.day_number }}<br>{{ port.date }}</div>
                </div>

                <div class="image-gallery">
                    {% if port.image_url %}
                    <div class="image-wrapper">
                        <img src="{{ port.image_url }}" alt="Scenery" class="port-image">
                        <div class="image-credit">{{ port.image_credit }}</div>
                    </div>
                    {% endif %}

                    {% if port.image_url_2 %}
                    <div class="image-wrapper">
                        <img src="{{ port.image_url_2 }}" alt="Scenery" class="port-image">
                        <div class="image-credit">{{ port.image_credit_2 }}</div>
                    </div>
                    {% endif %}
                </div>

                <div class="romance-narrative">{{ port.romance_narrative }}</div>
                {% if port.description %}
                <div class="description"><strong>About {{ port.port_location }}:</strong> {{ port.description }}</div>
                {% endif %}
            </div>
            {% endfor %}
        </div>

        <div class="footer">
            <h3>Questions? Ready to Book?</h3>
            <p><strong>{{ travel_agent_name }}</strong></p>
            <p>📧 <a href="mailto:{{ travel_agent_email }}">{{ travel_agent_email }}</a> | 📞 {{ travel_agent_phone }}</p>
        </div>
    </div>
</body>
</html>
"""

# ============================================================================
# 3. GENERATORS & MANAGERS
# ============================================================================
class GeminiNarrativeGenerator:
    def __init__(self):
        self.client = OpenAI(api_key=Config.GEMINI_API_KEY, base_url=Config.GEMINI_BASE_URL)

    def generate_narrative(self, port_name: str, supplier: str, region_context: str, trip_name: str) -> str:
        is_sea_day = "sea" in port_name.lower() or "cruising" in port_name.lower()

        if is_sea_day:
            prompt = (
                f"Write a luxurious 3-sentence travel description for a day '{port_name}' with {supplier}. "
                f"Focus on the romance and beauty of sailing through the waters near {region_context} during a {trip_name}. "
                f"Emphasize the ocean views and shipboard luxury, and do not mention exploring a city."
            )
        else:
            prompt = f"Write a luxurious 3-sentence description for a cruise port stop at {port_name} with {supplier}."

        try:
            response = self.client.chat.completions.create(
                model=Config.GEMINI_MODEL, messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Gemini error for {port_name}: {e}")
            return f"Experience the magic of {port_name}."

class QuotaSavingImageManager:
    """Intelligently sources images to save API quotas and injects geographic context"""
    def __init__(self, google_sheets_client, drive_service):
        self.sheets = google_sheets_client
        self.drive = drive_service
        self.pexels_headers = {"Authorization": Config.PEXELS_KEY}
        self.unsplash_url = f"https://api.unsplash.com/search/photos?client_id={Config.UNSPLASH_KEY}"

    def _extract_valid_url(self, value):
        text = str(value).strip()
        return text if text.startswith("http") else None

    def fetch_images(self, port_name: str, sheet_row: Dict, region_context: str):
        # 1. Check if row already has VALID URLs
        existing_img = self._extract_valid_url(sheet_row.get('RomanceURL'))
        existing_img2 = self._extract_valid_url(sheet_row.get('ImageURL 2') or sheet_row.get('Image 2'))

        if existing_img or existing_img2:
            return existing_img, "Stored in Sheet", existing_img2, "Stored in Sheet"

        # 2. Check Google Drive Art Folder
        drive_url = self._search_drive(port_name)
        if drive_url:
            logger.info(f"Found Google Drive Art for {port_name}")
            return drive_url, "Thunderbird Art Folder", None, None

        # 3. Check Backup Tabs
        backup_url = self._search_backup_tabs(port_name)
        if backup_url:
            logger.info(f"Found Backup Tab Image for {port_name}")
            return backup_url, "Previous Itinerary", None, None

        # 4. Burn Quotas: Fetch APIs (Unsplash + Pexels) with context
        logger.info(f"Using APIs for {port_name} (Context: {region_context})")
        u_img, u_thumb, u_cred = self._fetch_unsplash(port_name, region_context)
        p_img, p_thumb, p_cred = self._fetch_pexels(port_name, region_context)

        return u_img, u_cred, p_img, p_cred

    def _search_drive(self, port_name: str):
        if not self.drive: return None
        try:
            query = f"'{Config.ART_FOLDER_ID}' in parents and name contains '{port_name}' and mimeType contains 'image/'"
            res = self.drive.files().list(q=query, fields="files(id)").execute()
            items = res.get('files', [])
            if items:
                return f"https://drive.google.com/uc?export=view&id={items[0]['id']}"
        except Exception as e:
            logger.error(f"Drive search error: {e}")
        return None

    def _search_backup_tabs(self, port_name: str):
        if not self.sheets: return None
        try:
            doc = self.sheets.open_by_key(Config.GOOGLE_SHEET_ID)
            for tab in Config.BACKUP_TABS:
                try:
                    records = doc.worksheet(tab).get_all_records()
                    for r in records:
                        if port_name.lower() in str(r.get('Port_Location', '')).lower():
                            valid_url = self._extract_valid_url(r.get('RomanceURL'))
                            if valid_url: return valid_url
                except: pass
        except: pass
        return None

    def _fetch_unsplash(self, port_name: str, region_context: str):
        try:
            is_sea = "sea" in port_name.lower() or "cruising" in port_name.lower()
            search = f"{region_context} ocean scenery" if is_sea else f"{port_name} beautiful travel"

            res = requests.get(f"{self.unsplash_url}&query={search}&per_page=1&orientation=landscape").json()
            if res.get('results'):
                photo = res['results'][0]
                return photo['urls']['regular'], photo['urls']['thumb'], f"Unsplash by {photo['user']['name']}"
        except Exception as e: logger.error(f"Unsplash error: {e}")
        return None, None, None

    def _fetch_pexels(self, port_name: str, region_context: str):
        try:
            is_sea = "sea" in port_name.lower() or "cruising" in port_name.lower()
            search = f"{region_context} coast" if is_sea else f"{port_name} scenery"

            res = requests.get("https://api.pexels.com/v1/search", headers=self.pexels_headers, params={"query": search, "per_page": 1, "orientation": "landscape"}).json()
            if res.get('photos'):
                photo = res['photos'][0]
                return photo['src']['large'], photo['src']['medium'], f"Pexels by {photo['photographer']}"
        except Exception as e: logger.error(f"Pexels error: {e}")
        return None, None, None

# ============================================================================
# 4. CORE SYSTEM
# ============================================================================
class GoogleServiceManager:
    def __init__(self):
        self.creds = service_account.Credentials.from_service_account_file(
            Config.SERVICE_ACCOUNT_FILE,
            scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        )
        self.sheets = gspread.authorize(self.creds)
        self.drive = build('drive', 'v3', credentials=self.creds)

class HTMLItineraryGenerator:
    def __init__(self):
        self.template = Template(HTML_TEMPLATE)

    def generate(self, booking: Dict, itinerary: List[Dict], output_path: str):
        formatted_ports = []
        for p in itinerary:
            formatted_ports.append({
                'port_location': p.get('Port_Location', ''),
                'docking_time': p.get('Docking Time', ''),
                'departure_time': p.get('Departure Time', ''),
                'day_number': p.get('Day Number', ''),
                'date': p.get('Date', ''),
                'description': p.get('Description', ''),
                'romance_narrative': p.get('Romance/Narrative', ''),
                'image_url': p.get('HTML_Image_1', ''),
                'image_credit': p.get('HTML_Credit_1', ''),
                'image_url_2': p.get('HTML_Image_2', ''),
                'image_credit_2': p.get('HTML_Credit_2', '')
            })

        vars = {
            'client_name': booking.get('Client_Name', 'Guest'),
            'trip_name': booking.get('Trip_Name', 'Cruise'),
            'supplier': booking.get('Supplier', 'Cruise Line'),
            'start_date': booking.get('Start_Date', ''),
            'end_date': booking.get('End_Date', ''),
            'num_nights': self._calc(booking.get('Start_Date', ''), booking.get('End_Date', '')),
            'num_ports': len(itinerary),
            'confirmation_number': booking.get('Confirmation_Number', ''),
            'travelers': booking.get('Travelers', ''),
            'total_cost': str(booking.get('Total_Cost', '0')).replace('$', ''),
            'ports': formatted_ports,
            'travel_agent_name': Config.TRAVEL_AGENT_NAME,
            'travel_agent_email': Config.TRAVEL_AGENT_EMAIL,
            'travel_agent_phone': Config.TRAVEL_AGENT_PHONE
        }
        with open(output_path, 'w', encoding='utf-8') as f: f.write(self.template.render(vars))

    def _calc(self, start, end):
        try: return (datetime.strptime(end, '%m/%d/%Y') - datetime.strptime(start, '%m/%d/%Y')).days
        except: return 0

class ItineraryFinishingPipeline:
    def __init__(self):
        self.services = GoogleServiceManager()
        self.narrative_gen = GeminiNarrativeGenerator()
        self.image_manager = QuotaSavingImageManager(self.services.sheets, self.services.drive)
        self.html_gen = HTMLItineraryGenerator()

    def run(self, booking_id: str):
        logger.info(f"Starting pipeline for: {booking_id}")
        doc = self.services.sheets.open_by_key(Config.GOOGLE_SHEET_ID)
        booking = next((r for r in doc.worksheet(Config.BOOKING_MASTER_TAB).get_all_records() if str(r.get('Booking_ID')) == booking_id), None)
        itinerary = [r for r in doc.worksheet(Config.DAILY_ITINERARY_TAB).get_all_records() if str(r.get('Booking_ID')) == booking_id]

        if not booking: return logger.error("Booking not found.")

        # Set up contextual memory
        trip_name = booking.get('Trip_Name', 'Cruise')
        last_real_port = trip_name

        for port in itinerary:
            p_name = port.get('Port_Location') or port.get('Port Location') or port.get('Port') or 'Unknown Port'

            # Update memory if this is a real city stop
            is_sea_day = "sea" in p_name.lower() or "cruising" in p_name.lower()
            if not is_sea_day:
                last_real_port = p_name

            region_context = last_real_port if is_sea_day else p_name

            # --- AI TEXT GEN ---
            if not port.get('Romance/Narrative'):
                logger.info(f"Generating narrative for {p_name} (Context: {region_context})...")
                port['Romance/Narrative'] = self.narrative_gen.generate_narrative(
                    p_name, booking.get('Supplier', 'Cruise Line'), region_context, trip_name
                )

            # --- QUOTA SAVING IMAGES ---
            img1, cred1, img2, cred2 = self.image_manager.fetch_images(p_name, port, region_context)
            port['HTML_Image_1'] = img1
            port['HTML_Credit_1'] = cred1
            port['HTML_Image_2'] = img2
            port['HTML_Credit_2'] = cred2

        h_path = os.path.join(Config.HTML_OUTPUT_FOLDER, f"{booking_id}.html")
        p_path = os.path.join(Config.PDF_OUTPUT_FOLDER, f"{booking_id}.pdf")

        self.html_gen.generate(booking, itinerary, h_path)

        # Fallback to pdfkit if weasyprint errors
        try: HTML(h_path).write_pdf(p_path)
        except: pdfkit.from_file(h_path, p_path)

        print(f"\n✅ SUCCESS!\nHTML: {h_path}\nPDF:  {p_path}")

# ============================================================================
# MCP TOOL REGISTRATION
# ============================================================================

def register_itinerary_pipeline_tools(mcp):
    """Register itinerary finishing pipeline tools with the MCP server."""
    from pydantic import Field as PydField

    @mcp.tool(
        name="run_itinerary_pipeline",
        annotations={"title": "Run Itinerary Finishing Pipeline", "readOnlyHint": False},
    )
    async def run_itinerary_pipeline(
        booking_id: str = PydField(..., description="Booking ID to generate itinerary for (e.g., '3071222-26')"),
    ) -> str:
        """Run the full itinerary finishing pipeline for a booking: fetch data from Sheets, generate Gemini narratives, source images (Drive/Sheets/Unsplash/Pexels), and produce HTML + PDF output."""
        import json as _json
        try:
            pipeline = ItineraryFinishingPipeline()
            pipeline.run(booking_id)

            h_path = os.path.join(Config.HTML_OUTPUT_FOLDER, f"{booking_id}.html")
            p_path = os.path.join(Config.PDF_OUTPUT_FOLDER, f"{booking_id}.pdf")

            return _json.dumps({
                "status": "success",
                "booking_id": booking_id,
                "html_file": h_path if os.path.exists(h_path) else None,
                "pdf_file": p_path if os.path.exists(p_path) else None,
            }, indent=2)
        except Exception as e:
            return _json.dumps({"error": str(e), "type": "pipeline_error"})

    logger.info("Itinerary Pipeline tools registered successfully")


if __name__ == "__main__":
    import sys
    ItineraryFinishingPipeline().run(sys.argv[1] if len(sys.argv) > 1 else "3071222-26")
