#!/usr/bin/env python3
"""
THUNDERBIRD OS v2.0: DREAMS2MEMORIES LUXURY ITINERARY GENERATOR
Warm, personal, responsive HTML + PDF generation from Google Sheets
Integration with new frontend template for luxury confirmations
"""

import os, time, json, requests, logging, base64
from pathlib import Path
from datetime import datetime
from jinja2 import Template
from weasyprint import HTML, CSS
import gspread
from google.oauth2 import service_account
from googleapiclient.discovery import build
from openai import OpenAI
from pdf2image import convert_from_path
import pytesseract

# ============================================================================
# 1. CONFIGURATION (DREAMS2MEMORIES BRANDING)
# ============================================================================
class Config:
    # API Keys (from your existing setup)
    GEMINI_API_KEY = "***REMOVED-SECRET***"
    GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
   # Use 1.5 Flash for text logic to minimize input/output costs
    GEMINI_TEXT_MODEL = "models/gemini-1.5-flash"
    # Use Nano Banana 2 (3.1 Flash Image) for premium yet cheap visuals
    GEMINI_IMAGE_MODEL = "models/gemini-3.1-flash-image"
    GROQ_KEY = "***REMOVED-SECRET***"

    # Image Search
    GOOGLE_SEARCH_API_KEY = "***REMOVED-SECRET***"
    GOOGLE_CX_ID = "c521728142cd34117"
    PEXELS_KEY = "***REMOVED-SECRET***"
    ART_FOLDER_ID = "1V_iUoy5oXs8RxY5S4-2QSHTXueGircnQ"

    # AGENCY BRANDING - UPDATE THESE WITH YOUR ACTUAL URLS
    # Local file paths for now (will be converted to URLs for web)
    LOGO_PATH = Path.home() / "Thunderbird" / "Agency_Logo.png"
    AGENT_PHOTO_PATH = Path.home() / "Thunderbird" / "John_Headshot.jpg"
    
    AGENT_NAME = "John Loucks"
    AGENT_PHONE = "(719) 291-0742"
    AGENT_EMAIL = "johnloucks3@gmail.com"
    AGENCY_WEBSITE = "www.d2mtravel.luxury"

    # Google Sheets
    SHEET_ID = "1GFjUe8RvP-GT4YHGn0DYv_BEAZGXlYfwEicFrm8ANuU"
    SERVICE_ACCOUNT_FILE = Path.home() / 'Thunderbird' / 'credentials.json'
    MASTER_TAB = "Booking Master"
    DAILY_TAB = "Daily Itinerary"

    # Output Directories
    INPUT_DIR = Path.home() / "Downloads" / "BookingPDFs"
    PROCESSED_DIR = Path.home() / "Documents" / "ProcessedPDFs"
    OUTPUT_DIR = Path.home() / "Documents" / "Luxury_Itineraries"
    TEMP_DIR = Path.home() / "Documents" / ".dreams2m_temp"

logging.basicConfig(level=logging.INFO, format='⚡ %(message)s')
logger = logging.getLogger(__name__)

# ============================================================================
# 2. IMAGE UTILITIES (TITAN ART -> SNIPER VISION -> PEXELS)
# ============================================================================
def encode_image_to_base64(file_path: Path) -> str:
    """Convert image file to base64 for embedding in HTML."""
    try:
        with open(file_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    except Exception as e:
        logger.error(f"Failed to encode image {file_path}: {e}")
        return ""

def get_image_data_url(file_path: Path, mime_type: str = "image/png") -> str:
    """Create data URL for embedding image directly in HTML."""
    b64 = encode_image_to_base64(file_path)
    return f"data:{mime_type};base64,{b64}" if b64 else ""

def get_drive_service():
    creds = service_account.Credentials.from_service_account_file(
        str(Config.SERVICE_ACCOUNT_FILE),
        scopes=['https://www.googleapis.com/auth/drive.readonly']
    )
    return build('drive', 'v3', credentials=creds)

def find_curated_art(port_name: str) -> str:
    """Search Google Drive for curated Titan_Art images."""
    service = get_drive_service()
    search_term = f"Titan_Art_{port_name}"
    query = f"'{Config.ART_FOLDER_ID}' in parents and name contains '{search_term}'"
    try:
        results = service.files().list(q=query, fields="files(id, webContentLink, name)").execute()
        files = results.get('files', [])
        if files:
            logger.info(f"🎨 Found curated art: {files[0]['name']}")
            return files[0].get('webContentLink')
    except Exception as e:
        logger.debug(f"Drive search failed: {e}")
    return None

def get_best_image(query: str, port_name: str) -> str:
    """Image hierarchy: Curated Art -> Sniper Vision -> Pexels."""
    art = find_curated_art(port_name)
    if art: return art

    logger.info(f"🎯 Searching for: {port_name}")
    search_url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "q": f"{port_name} luxury travel photography {query}",
        "cx": Config.GOOGLE_CX_ID, "key": Config.GOOGLE_SEARCH_API_KEY,
        "searchType": "image", "imgSize": "huge", "num": 1
    }
    try:
        res = requests.get(search_url, params=params, timeout=10).json()
        if 'items' in res and res['items']:
            return res['items'][0]['link']
    except Exception as e:
        logger.debug(f"Search failed: {e}")

    # Pexels Fallback
    headers = {"Authorization": Config.PEXELS_KEY}
    try:
        res = requests.get(
            f"https://api.pexels.com/v1/search?query={query}&per_page=1",
            headers=headers, timeout=10
        ).json()
        if 'photos' in res and res['photos']:
            return res['photos'][0]['src']['large2x']
    except Exception as e:
        logger.debug(f"Pexels failed: {e}")

    return "https://images.unsplash.com/photo-1548574505-5e239809ee19"

# ============================================================================
# 3. SHEETS DATA EXTRACTION
# ============================================================================
def get_master_and_daily_rows(client_name: str):
    """Extract master booking and daily itinerary data from Sheets."""
    creds = service_account.Credentials.from_service_account_file(
        str(Config.SERVICE_ACCOUNT_FILE),
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    gc = gspread.authorize(creds)
    doc = gc.open_by_key(Config.SHEET_ID)

    # Get Master row
    m_ws = doc.worksheet(Config.MASTER_TAB)
    m_vals = m_ws.get_all_values()
    m_headers = m_vals[0]
    m_rec = [dict(zip(m_headers, r)) for r in m_vals[1:]]
    master_row = next(
        (r for r in m_rec if client_name.lower() in str(r.get('Client_Name', '')).lower()),
        None
    )

    if not master_row:
        logger.error(f"Client '{client_name}' not found in Master tab")
        return None, None

    logger.info(f"✅ Found master booking for {master_row.get('Client_Name')}")

    # Get Daily rows
    d_ws = doc.worksheet(Config.DAILY_TAB)
    d_vals = d_ws.get_all_values()
    d_headers = d_vals[0]

    d_rec = []
    for i, r in enumerate(d_vals[1:]):
        row_dict = dict(zip(d_headers, r))
        row_dict['__sheet_row__'] = i + 2  # Track for updates
        d_rec.append(row_dict)

    daily_rows = [
        r for r in d_rec
        if str(r.get('Confirmation_Number')) == str(master_row.get('Confirmation_Number'))
    ]

    logger.info(f"✅ Found {len(daily_rows)} itinerary days")
    return master_row, daily_rows, d_ws, d_headers

# ============================================================================
# 4. AI CONTENT GENERATION (NARRATIVE + IMAGES)
# ============================================================================
def generate_narratives_and_images(master_row, daily_rows, d_ws, d_headers):
    """Generate Romance_Narrative and fetch Image_1_URL for each day."""
    client = OpenAI(api_key=Config.GEMINI_API_KEY, base_url=Config.GEMINI_BASE_URL)

    for i, day in enumerate(daily_rows):
        row_idx = day['__sheet_row__']
        port = day.get('Port_Location', 'Destination')

        # Generate narrative if missing
        if not day.get('Romance_Narrative') or "luxury" not in day.get('Romance_Narrative', '').lower():
            logger.info(f"✍ Generating narrative for Day {day.get('Day')}: {port}...")
            prompt = f"Write 3-4 luxury travel sentences about {port}, emphasizing sensory details and emotional connection. Prose only. No introduction."
            try:
                res = client.chat.completions.create(
                    model=Config.GEMINI_MODEL,
                    messages=[{"role": "user", "content": prompt}]
                )
                narrative = res.choices[0].message.content.strip()
                day['Romance_Narrative'] = narrative
                # Update sheet
                d_ws.update_cell(row_idx, d_headers.index('Romance_Narrative') + 1, narrative)
                logger.info(f"✅ Narrative saved")
            except Exception as e:
                logger.error(f"Narrative generation failed: {e}")

        # Fetch image if missing
        if not day.get('Image_1_URL'):
            logger.info(f"🎨 Fetching image for {port}...")
            romance_short = day.get('Romance_Short', 'luxury travel')
            img_url = get_best_image(romance_short, port)
            day['Image_1_URL'] = img_url
            # Update sheet
            d_ws.update_cell(row_idx, d_headers.index('Image_1_URL') + 1, img_url)
            logger.info(f"✅ Image saved")

    return daily_rows

# ============================================================================
# 5. HTML GENERATION (WITH EMBEDDED IMAGES)
# ============================================================================
def load_html_template() -> str:
    """Load the Dreams2Memories HTML template."""
    template_path = Path(__file__).parent / "dreams2memories_itinerary.html"
    if not template_path.exists():
        logger.error(f"Template not found: {template_path}")
        return None
    with open(template_path, 'r') as f:
        return f.read()

def generate_html_itinerary(master_row, daily_rows) -> str:
    """Generate final HTML with Jinja2 templating."""
    template_html = load_html_template()
    if not template_html:
        return None

    # Prepare image URLs (use base64 data URLs for self-contained HTML)
    logo_url = get_image_data_url(Config.LOGO_PATH, "image/png")
    agent_photo_url = get_image_data_url(Config.AGENT_PHOTO_PATH, "image/jpeg")

    # If data URLs fail, use local file paths
    if not logo_url:
        logo_url = f"file:///{Config.LOGO_PATH}"
    if not agent_photo_url:
        agent_photo_url = f"file:///{Config.AGENT_PHOTO_PATH}"

    # Render template
    template = Template(template_html)
    html_content = template.render(
        Client_Name=master_row.get('Client_Name', 'Traveler'),
        Trip_Name=master_row.get('Trip_Name', 'Luxury Cruise'),
        Supplier=master_row.get('Supplier', 'Cruise Line'),
        Start_Date=master_row.get('Start_Date', ''),
        End_Date=master_row.get('End_Date', ''),
        Flight_Info=master_row.get('Flight_Info', 'Details to follow'),
        Hotel_Info=master_row.get('Hotel_Info', 'Confirmed'),
        Transfer_Info=master_row.get('Transfer_Info', 'Arranged'),
        Tour_Info=master_row.get('Tour_Info', 'Curated'),
        Weather_Forecast=master_row.get('Weather_Forecast', ''),
        AI_Uncategorized_Notes=master_row.get('AI_Uncategorized_Notes', ''),
        Outbound_Flight=master_row.get('Outbound_Flight', ''),
        Port_Arrival=master_row.get('Port_Arrival', ''),
        Cabin_Number=master_row.get('Cabin_Number', ''),
        Transfer_Details=master_row.get('Transfer_Details', ''),
        Return_Flight=master_row.get('Return_Flight', ''),
        Dining_Prefs=master_row.get('Dining_Prefs', ''),
        Special_Requests=master_row.get('Special_Requests', ''),
        Gratuity_Rate=master_row.get('Gratuity_Rate', '$15-16 per person per day'),
        Dining_Schedule=master_row.get('Dining_Schedule', ''),
        days=daily_rows,
        LOGO_URL=logo_url,
        AGENT_PHOTO_URL=agent_photo_url,
        AGENT_NAME=Config.AGENT_NAME,
        AGENT_PHONE=Config.AGENT_PHONE,
        AGENT_EMAIL=Config.AGENT_EMAIL
    )

    return html_content

# ============================================================================
# 6. PDF GENERATION (WEASYPRINT)
# ============================================================================
def generate_pdf_from_html(html_content: str, output_path: Path):
    """Convert HTML to PDF using WeasyPrint."""
    try:
        # PDF-specific CSS for print optimization
        pdf_css = CSS(string="""
            @page { size: A4; margin: 0; }
            body { margin: 0; padding: 0; }
        """)
        HTML(string=html_content).write_pdf(output_path)
        logger.info(f"✅ PDF saved: {output_path}")
        return True
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        return False

# ============================================================================
# 7. MAIN GENERATION WORKFLOW
# ============================================================================
def generate_itinerary():
    """Main workflow: Extract data -> Generate content -> Output HTML + PDF."""
    client_name = input("Enter client name (exact from Sheet): ").strip()

    # Extract data
    result = get_master_and_daily_rows(client_name)
    if not result[0]:
        return

    master_row, daily_rows, d_ws, d_headers = result

    # Generate narratives and fetch images
    daily_rows = generate_narratives_and_images(master_row, daily_rows, d_ws, d_headers)

    # Generate HTML
    logger.info("🎨 Rendering HTML template...")
    html_content = generate_html_itinerary(master_row, daily_rows)
    if not html_content:
        logger.error("Failed to generate HTML")
        return

    # Save outputs
    Config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    sanitized_name = client_name.replace(' ', '_').replace('/', '-')

    # HTML output
    html_path = Config.OUTPUT_DIR / f"ITINERARY_{sanitized_name}.html"
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    logger.info(f"✅ HTML saved: {html_path}")

    # PDF output
    pdf_path = Config.OUTPUT_DIR / f"ITINERARY_{sanitized_name}.pdf"
    generate_pdf_from_html(html_content, pdf_path)

    logger.info(f"\n✨ MASTERPIECE COMPLETE ✨")
    logger.info(f"📄 Open HTML for interactive version: {html_path}")
    logger.info(f"📕 Print/email PDF version: {pdf_path}")

# ============================================================================
# 8. MAIN MENU
# ============================================================================
if __name__ == "__main__":
    Config.INPUT_DIR.mkdir(parents=True, exist_ok=True)

    while True:
        print("\n" + "="*60)
        print("   DREAMS2MEMORIES: THUNDERBIRD OS v2.0")
        print("   Luxury Itinerary Generation System")
        print("="*60)
        print("[1] Generate New Itinerary (HTML + PDF)")
        print("[2] Process PDFs & Extract Booking Data")
        print("[3] Exit")
        print("="*60)

        choice = input("\nSelect option: ").strip()

        if choice == '1':
            generate_itinerary()
        elif choice == '2':
            # Placeholder for PDF processing (from your original script)
            print("PDF processing module coming soon...")
        elif choice == '3':
            print("Goodbye!")
            break
        else:
            print("Invalid selection. Try again.")
