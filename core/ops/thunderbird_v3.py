import os, time, json, requests, logging, re
from pathlib import Path
from googleapiclient.discovery import build
from google.oauth2 import service_account
from pdf2image import convert_from_path
import pytesseract

# ============================================================================
# 1. ENVIRONMENT CONFIGURATION (ALL KEYS ARMED)
# ============================================================================
class Config:
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")  # nulled 2026-05-29 — GCP cap
    PEXELS_KEY = "***REMOVED-SECRET***"
    UNSPLASH_KEY = "***REMOVED-SECRET***"

    # NEW: Sniper Vision Keys
    GOOGLE_SEARCH_API_KEY = "***REMOVED-SECRET***"
    GOOGLE_CX_ID = "c521728142cd34117"

    SHEET_ID = "1GFjUe8RvP-GT4YHGn0DYv_BEAZGXlYfwEicFrm8ANuU"
    SERVICE_ACCOUNT_FILE = '/home/john/Thunderbird/credentials.json'

    INPUT_DIR = Path.home() / "Downloads/BookingPDFs"
    PROCESSED_DIR = Path.home() / "Documents/ProcessedPDFs"

# ============================================================================
# 2. THE MASTER DATA ENGINE (REGEX BASELINE + LLAMA)
# ============================================================================
def extract_master_data(text):
    baseline = {"Supplier": "Unknown", "Client_Name": "Unknown", "Total_Cost": 0.0, "Confirmation_Number": "Unknown", "Trip_Name": "Luxury Cruise"}

    if "REGENT" in text.upper() or "SEVEN SEAS" in text.upper(): baseline["Supplier"] = "Regent Seven Seas Cruises"
    elif "SILVERSEA" in text.upper(): baseline["Supplier"] = "Silversea"
    elif "VIKING" in text.upper(): baseline["Supplier"] = "Viking Cruises"

    baseline["Confirmation_Number"] = (re.search(r"(?:Reservation\s*#|BOOKING #:|Booking Number:|Booking Reference:)\s*([A-Z0-9-]+)", text, re.I) or ["", "Unknown"])[1]
    cost_match = re.search(r"(?:Total Fare|TOTAL CHARGE|Grand Total|Booking Total|Invoice Total)[^\d\$]*\$?([\d,]+\.\d{2})", text, re.I)
    baseline["Total_Cost"] = float(cost_match.group(1).replace(",", "")) if cost_match else 0.0

    # Groq ELIMINATED — using Claude Sonnet via Anthropic SDK ($0 on Max plan)
    prompt = f"""
    We already know: Supplier={baseline['Supplier']}, ID={baseline['Confirmation_Number']}, Cost={baseline['Total_Cost']}.
    Extract the REST of the MASTER BOOKING DATA from this text. Scrub "NEXION LLC" from names.
    Return a VALID JSON object exactly like this (use "Pending" if not found):
    {{
        "Client_Name": "Full Name",
        "Trip_Name": "Ship and Voyage Name",
        "Start_Date": "YYYY-MM-DD",
        "End_Date": "YYYY-MM-DD",
        "Email": "Client email",
        "Travelers": "Number of guests",
        "Flight_Info": "Flight details",
        "Hotel_Info": "Pre/post hotels",
        "Transfer_Info": "Transfers"
    }}
    TEXT: {text[:20000]}
    """
    try:
        import anthropic
        client = anthropic.Anthropic()
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",  # Haiku — JSON data extraction (SO-2026-03-25)
            max_tokens=600,
            system="You are a data extraction assistant. Return ONLY valid JSON, no explanation.",
            messages=[{"role": "user", "content": prompt}],
        )
        ai_data = json.loads(resp.content[0].text)

        ai_data["Supplier"] = baseline["Supplier"]
        ai_data["Confirmation_Number"] = baseline["Confirmation_Number"] if baseline["Confirmation_Number"] != "Unknown" else ai_data.get("Booking_ID", "Unknown")
        ai_data["Total_Cost"] = baseline["Total_Cost"]
        return ai_data
    except Exception as e:
        logging.error(f"⚠️ Master Extraction failed: {e}")
        return baseline

# ============================================================================
# 3. THE ITINERARY & VISION ENGINES
# ============================================================================
def extract_daily_itinerary(text, ship_name):
    # Groq ELIMINATED — using Claude Sonnet via Anthropic SDK ($0 on Max plan)
    prompt = f"""
    Extract the FULL daily itinerary. Ship Name is {ship_name}.
    CRITICAL INSTRUCTIONS:
    1. Invent a unique, poetic, sensory 2-sentence description for the 'Romance' field for EVERY DAY.
    2. Based on that Romance, create a 3-word 'Visual_Query' for image searching.
       - If it's a Port, use the landmark/vibe (e.g., "Berlin Brandenburg sunset").
       - If it's a Sea Day, just output the word "SEA".

    Format JSON strictly:
    {{
      "schedule": [
        {{ "Day": 1, "Date": "...", "Port": "...", "Arrive": "...", "Depart": "...", "Romance": "...", "Visual_Query": "..." }}
      ]
    }}
    TEXT: {text[:25000]}
    """
    try:
        import anthropic
        client = anthropic.Anthropic()
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            system="You are a data extraction assistant. Return ONLY valid JSON, no explanation.",
            messages=[{"role": "user", "content": prompt}],
        )
        return json.loads(resp.content[0].text).get("schedule", [])
    except Exception as e:
        logging.error(f"Itinerary Extraction failed: {e}")
        return []

def fetch_ship_sniper_photo(ship_name):
    """Hunts down the EXACT ship using Google Custom Search."""
    if not ship_name or ship_name == "Pending": return ""
    clean_name = ship_name.replace("Voyage", "").replace("-", " ").strip()

    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "q": f"{clean_name} luxury cruise ship exterior sailing",
        "cx": Config.GOOGLE_CX_ID,
        "key": Config.GOOGLE_SEARCH_API_KEY,
        "searchType": "image",
        "imgSize": "large",
        "num": 1
    }
    try:
        res = requests.get(url, params=params).json()
        if "items" in res and len(res["items"]) > 0:
            return res["items"][0]["link"]
    except Exception as e:
        logging.error(f"⚠️ Sniper Vision failed on {clean_name}: {e}")
    return ""

def fetch_port_visuals(visual_query):
    """Fetches Unsplash/Pexels for land destinations."""
    if not visual_query or "SEA" in visual_query.upper(): return "", ""
    try:
        u_res = requests.get(f"https://api.unsplash.com/search/photos?query={visual_query}&per_page=1", headers={"Authorization": f"Client-ID {Config.UNSPLASH_KEY}"}).json()
        u_img = u_res['results'][0]['urls']['regular'] if u_res.get('results') else ""

        p_res = requests.get(f"https://api.pexels.com/v1/search?query={visual_query}&per_page=1", headers={"Authorization": Config.PEXELS_KEY}).json()
        p_img = p_res['photos'][0]['src']['large'] if p_res.get('photos') else ""
        return u_img, p_img
    except:
        return "", ""

# ============================================================================
# 4. WAREHOUSE LOADING
# ============================================================================
def push_to_sheets(m_data, schedule, ship_img_url, file_name):
    creds = service_account.Credentials.from_service_account_file(Config.SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    service = build('sheets', 'v4', credentials=creds, cache_discovery=False)

    # --- MASTER HUB ---
    row_m = ["" for _ in range(49)]
    row_m[0] = f"file://{Config.PROCESSED_DIR}/{file_name}"  # Col A: Clean Link
    row_m[1] = time.strftime("%Y-%m-%d %H:%M:%S")            # Col B: Exact Time
    row_m[2] = m_data.get('Client_Name')
    row_m[3] = m_data.get('Confirmation_Number')
    row_m[4] = m_data.get('Email')
    row_m[5] = m_data.get('Trip_Name')
    row_m[7] = m_data.get('Start_Date')
    row_m[8] = m_data.get('End_Date')
    row_m[11] = m_data.get('Supplier')
    row_m[12] = m_data.get('Confirmation_Number')
    row_m[13] = "Confirmed"
    row_m[14] = m_data.get('Total_Cost')
    row_m[21] = m_data.get('Travelers')
    row_m[24] = m_data.get('Flight_Info')
    row_m[25] = m_data.get('Hotel_Info')
    row_m[26] = m_data.get('Transfer_Info')
    row_m[44] = f'=IMAGE("{ship_img_url}")' if ship_img_url else "" # Col AS: Master Ship Thumbnail

    service.spreadsheets().values().append(spreadsheetId=Config.SHEET_ID, range="'Booking Master'!A:A", valueInputOption="USER_ENTERED", body={"values": [row_m]}).execute()

    # --- DAILY ITINERARY ---
    itin_rows = []
    for day in schedule:
        v_query = day.get('Visual_Query', 'SEA')

        # Determine if we use Port APIs or the exact Ship Sniper photo
        if "SEA" in v_query.upper() or "CRUISING" in day.get('Port', '').upper():
            u_img, p_img = ship_img_url, ship_img_url  # Use ship photo for Sea Days
            v_query = f"Sniper Vision: {m_data.get('Trip_Name')} at Sea"
        else:
            u_img, p_img = fetch_port_visuals(v_query)
            # Failsafe: If APIs miss the port, fall back to the ship
            if not u_img and not p_img:
                u_img, p_img = ship_img_url, ship_img_url

        row_i = ["" for _ in range(16)]
        row_i[0] = m_data.get('Confirmation_Number')
        row_i[1] = day.get('Day')
        row_i[2] = day.get('Date')
        row_i[3] = day.get('Port')
        row_i[4] = day.get('Romance')
        row_i[5] = day.get('Arrive')
        row_i[6] = day.get('Depart')
        row_i[7] = v_query
        row_i[8] = day.get('Romance')
        row_i[9] = u_img
        row_i[10] = f'=IMAGE("{u_img}")' if u_img else ""
        row_i[11] = p_img
        row_i[12] = f'=IMAGE("{p_img}")' if p_img else ""
        row_i[13] = "Confirmed"
        row_i[14] = time.strftime("%H:%M:%S")

        itin_rows.append(row_i)

    if itin_rows:
        service.spreadsheets().values().append(spreadsheetId=Config.SHEET_ID, range="'Daily Itinerary'!A:A", valueInputOption="USER_ENTERED", body={"values": itin_rows}).execute()

# ============================================================================
# 5. WATCHDOG EXECUTION
# ============================================================================
# ============================================================================
# MCP TOOL REGISTRATION
# ============================================================================

def register_v3_tools(mcp):
    """Register V3 PDF extraction and booking parsing tools with the MCP server."""
    from pydantic import Field as PydField

    @mcp.tool(
        name="extract_booking_from_pdf",
        annotations={"title": "Extract Booking Data from PDF (V3 Engine)", "readOnlyHint": False},
    )
    async def extract_booking_from_pdf(
        pdf_path: str = PydField(..., description="Path to cruise booking PDF"),
        push_to_sheets: bool = PydField(True, description="Write extracted data to Google Sheets"),
    ) -> str:
        """Extract master booking data and daily itinerary from a cruise PDF using OCR + Groq LLM. Optionally pushes to Google Sheets."""
        import json as _json
        try:
            from pdf2image import convert_from_path
            import pytesseract

            images = convert_from_path(pdf_path)
            text = "".join([pytesseract.image_to_string(img) for img in images])

            master_data = extract_master_data(text)
            ship_name = master_data.get("Trip_Name", "Luxury Cruise Ship")
            ship_photo_url = fetch_ship_sniper_photo(ship_name)
            schedule = extract_daily_itinerary(text, ship_name)

            if push_to_sheets:
                push_to_sheets_fn = globals()["push_to_sheets"]
                push_to_sheets_fn(master_data, schedule, ship_photo_url, Path(pdf_path).name)

            return _json.dumps({
                "status": "success",
                "master_data": master_data,
                "itinerary_days": len(schedule),
                "ship_photo": ship_photo_url,
                "pushed_to_sheets": push_to_sheets,
            }, indent=2)
        except Exception as e:
            return _json.dumps({"error": str(e), "type": "pdf_extraction_error"})

    @mcp.tool(
        name="extract_master_booking_data",
        annotations={"title": "Extract Master Data from Text", "readOnlyHint": True},
    )
    async def extract_master_booking_data_tool(
        text: str = PydField(..., description="Raw text from a cruise booking document"),
    ) -> str:
        """Parse raw booking text using regex + Groq LLM to extract supplier, client, cost, dates, etc."""
        import json as _json
        try:
            result = extract_master_data(text)
            return _json.dumps({"status": "success", "data": result}, indent=2)
        except Exception as e:
            return _json.dumps({"error": str(e), "type": "extraction_error"})

    logging.info("V3 PDF Extraction tools registered successfully")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    Config.INPUT_DIR.mkdir(parents=True, exist_ok=True)
    Config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    logging.info("V9 ONLINE: SNIPER VISION ARMED.")

    while True:
        pdf_files = list(Config.INPUT_DIR.glob("*.pdf"))
        for pdf in pdf_files:
            logging.info(f"PROCESSING: {pdf.name}")
            try:
                images = convert_from_path(pdf)
                text = "".join([pytesseract.image_to_string(img) for img in images])

                master_data = extract_master_data(text)
                ship_name = master_data.get('Trip_Name', 'Luxury Cruise Ship')
                ship_photo_url = fetch_ship_sniper_photo(ship_name)
                schedule = extract_daily_itinerary(text, ship_name)
                push_to_sheets(master_data, schedule, ship_photo_url, pdf.name)

                pdf.rename(Config.PROCESSED_DIR / pdf.name)
                logging.info(f"SUCCESS: {master_data.get('Client_Name')} | {master_data.get('Supplier')}")
            except Exception as e:
                logging.error(f"FAILURE on {pdf.name}: {e}")
        time.sleep(5)
