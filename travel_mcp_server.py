"""
Dreams2Memories Travel Automation MCP Server
============================================

Comprehensive MCP server for luxury travel itinerary automation:
- PDF data extraction and parsing
- Excel workbook synchronization
- Image generation and insertion (Stable Diffusion)
- Client itinerary creation from templates
- Booking data consolidation
- Live luxury cruise voyage & cabin scraping (Playwright Stealth)

Transport: stdio (local), SSE (legacy), or Streamable HTTP (production)

Streamable HTTP is the production transport — stateless, load-balancer friendly,
and the MCP standard replacing SSE (deprecated April 2026).
"""
from thunderbird_ship_intel import register_ship_intel_tools
from thunderbird_world_intel import register_world_intel_tools
from thunderbird_ship_compare import register_comparison_tools
from thunderbird_drive import register_drive_tools
from thunderbird_browser import register_browser_tools
from thunderbird_weekly_report import register_weekly_report_tools
from thunderbird_tech_monitor import register_tech_monitor_tools
from thunderbird_v3 import register_v3_tools
from itinerary_finishing_pipeline import register_itinerary_pipeline_tools
from thunderbird_hotel_search import register_hotel_search_tools
from thunderbird_flight_search import register_flight_search_tools
from thunderbird_gmail import register_gmail_tools
from thunderbird_tour_search import register_tour_search_tools
from thunderbird_fare_watch import register_fare_watch_tools
from thunderbird_personas import register_persona_tools
from thunderbird_sms import register_sms_tools
from thunderbird_evernote import register_evernote_tools
from thunderbird_whatsapp import register_whatsapp_tools
from thunderbird_quote_render import register_quote_tools
from thunderbird_star_protocol import register_star_protocol_tools
from thunderbird_dani_email import register_dani_email_tools
from thunderbird_keep import register_keep_tools
from thunderbird_dining import register_dining_tools
from thunderbird_anchor_dates import register_anchor_date_tools
from thunderbird_dossier import register_dossier_tools
from thunderbird_outside_agents import register_outside_agents_tools
from thunderbird_morning_briefing import register_briefing_tools
from thunderbird_x_osint import register_x_osint_tools
from d2m_client_materials import register_client_materials_tools
from thunderbird_trip_architect import register_trip_architect_tools
from thunderbird_commission_recon import register_commission_recon_tools
from thunderbird_survey import register_survey_tools
from thunderbird_competitive_surveillance import register_surveillance_tools
from thunderbird_price_monitor import register_price_monitor_tools
from thunderbird_email_intel import register_email_intel_tools
from thunderbird_tess import register_tess_tools
from thunderbird_shared_memory import register_memory_tools
from thunderbird_crewai import register_crewai_tools
from thunderbird_a2a import register_a2a_tools
from thunderbird_airline_monitor import register_airline_monitor_tools
from thunderbird_intel_crew import register_intel_crew_tools
from thunderbird_innovation_scanner import register_innovation_tools, run_daily_scan, run_weekly_scan, get_digest_for_briefing
from thunderbird_auto_enrich import register_auto_enrich_tools
from thunderbird_tasks import register_tasks_tools
from thunderbird_files_api import register_files_api_tools
from thunderbird_skills_api import register_skills_tools
from thunderbird_excursions import register_excursion_tools
from thunderbird_transfers import register_transfer_tools
from thunderbird_opentable import register_opentable_tools
from thunderbird_expedia_taap import register_taap_tools
from thunderbird_worldfactbook import register_worldfactbook_tools
from thunderbird_learning import register_learning_tools
from thunderbird_conversation_learner import register_conversation_learner_tools
from thunderbird_sss import register_sss_tools
from thunderbird_dossier_scanner import register_dossier_scanner_tools
from thunderbird_email_classifier import register_email_classifier_tools
from thunderbird_academic_scanner import register_academic_scanner_tools
from thunderbird_voice_ledger import register_voice_ledger_tools
from thunderbird_recipient_profiles import register_recipient_profile_tools
from thunderbird_commander_inbox import register_commander_inbox_tools
from thunderbird_health import register_health_tools
from thunderbird_session_checkpoint import register_checkpoint_tools
from thunderbird_bulletin import register_bulletin_tools
from thunderbird_info_delta import register_info_delta_tools
from thunderbird_temporal_memory import register_temporal_tools
from thunderbird_dani_voice import register_dani_voice_tools
from thunderbird_model_router import register_router_tools
from thunderbird_a2a_protocol import register_a2a_protocol_tools
from thunderbird_grant_compiler import register_grant_tools
from thunderbird_mcp_connector import register_connector_tools
import json
import logging
import asyncio
import os
from pathlib import Path
from datetime import datetime
import re
from typing import Optional, List, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict
from mcp.server.fastmcp import FastMCP

# New Imports for Web Scraping
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

# Initialize MCP server
mcp = FastMCP("dreams2memories_travel_mcp")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# DATA MODELS
# ============================================================================

class CruisePortStop(BaseModel):
    """Model for cruise port information"""
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')

    port_name: str = Field(..., description="Port name (e.g., 'Yokohama', 'Seattle')", min_length=1)
    date: str = Field(..., description="ISO date (YYYY-MM-DD)")
    arrival_time: Optional[str] = Field(None, description="Arrival time (HH:MM 24-hour format)")
    departure_time: Optional[str] = Field(None, description="Departure time (HH:MM 24-hour format)")
    description: Optional[str] = Field(None, description="Port description or highlights")
    shore_excursions: Optional[List[str]] = Field(default_factory=list, description="Available excursions")

class ShoreExcursion(BaseModel):
    """Model for shore excursion details"""
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')

    excursion_id: str = Field(..., description="Unique excursion ID")
    port: str = Field(..., description="Port where excursion operates")
    name: str = Field(..., description="Excursion name")
    price: float = Field(..., description="Price per person", ge=0)
    duration_hours: float = Field(..., description="Duration in hours", ge=0.5)
    status: str = Field("available", description="Status: available, waitlisted, cancelled")
    description: Optional[str] = Field(None, description="Excursion description")

class SpecialtyDining(BaseModel):
    """Model for specialty dining reservations"""
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')

    restaurant: str = Field(..., description="Restaurant name")
    date: str = Field(..., description="Reservation date (YYYY-MM-DD)")
    time: str = Field(..., description="Reservation time (HH:MM 24-hour)")
    party_size: int = Field(..., description="Number of guests", ge=1, le=10)
    notes: Optional[str] = Field(None, description="Special requests or notes")

class CruiseBooking(BaseModel):
    """Model for complete cruise booking"""
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')

    booking_id: str = Field(..., description="Booking confirmation number")
    cruise_line: str = Field(..., description="Cruise line (e.g., 'Silversea')")
    ship_name: str = Field(..., description="Ship name")
    voyage_start: str = Field(..., description="Voyage start date (YYYY-MM-DD)")
    voyage_end: str = Field(..., description="Voyage end date (YYYY-MM-DD)")
    total_cost: float = Field(..., description="Total cost in USD", ge=0)
    paid_in_full: bool = Field(False, description="Whether payment is complete")
    passengers: List[str] = Field(default_factory=list, description="Passenger names")
    travel_agent: Optional[str] = Field(None, description="Travel agent name and contact")
    ports: List[CruisePortStop] = Field(default_factory=list, description="Port itinerary")
    excursions: List[ShoreExcursion] = Field(default_factory=list, description="Booked excursions")
    dining_reservations: List[SpecialtyDining] = Field(default_factory=list, description="Specialty dining")

class ItineraryGenerationRequest(BaseModel):
    """Request model for itinerary generation"""
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')

    booking_id: str = Field(..., description="Reference booking ID")
    client_name: str = Field(..., description="Client name for personalization")
    format: str = Field("pdf", description="Output format: 'pdf' or 'google_docs'")
    include_images: bool = Field(True, description="Generate and include images")
    image_style: str = Field("luxury_travel", description="Image style: 'luxury_travel', 'adventure', 'cultural'")
    template_type: str = Field("standard", description="Template: 'standard', 'luxury', 'adventure'")

# ============================================================================
# PDF EXTRACTION TOOLS
# ============================================================================

@mcp.tool(
    name="extract_pdf_booking_details",
    annotations={"title": "Extract Booking Details from PDF", "readOnlyHint": True}
)
async def extract_pdf_booking_details(
    pdf_path: str = Field(..., description="Path to PDF file (e.g., '/uploads/Silver_Nova_Confirmation.pdf')")
) -> str:
    """Extract structured booking data from cruise confirmation PDF."""
    try:
        logger.info(f"Extracting booking details from: {pdf_path}")
        result = {
            "status": "success",
            "message": f"PDF extraction initiated for {pdf_path}",
            "requires_implementation": "PyPDF2 or pdfplumber integration needed",
        }
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error extracting PDF: {str(e)}")
        return json.dumps({"error": str(e), "type": "extraction_error"})

@mcp.tool(
    name="extract_pdf_itinerary",
    annotations={"title": "Extract Port Itinerary from PDF", "readOnlyHint": True}
)
async def extract_pdf_itinerary(
    pdf_path: str = Field(..., description="Path to itinerary PDF"),
    page_range: Optional[str] = Field(None, description="Page range (e.g., '1-5') or 'all'")
) -> str:
    """Extract detailed port-by-port itinerary from PDF."""
    logger.info(f"Extracting itinerary from {pdf_path} (pages: {page_range or 'all'})")
    result = {
        "status": "initiated",
        "file": pdf_path,
        "pages": page_range or "all",
        "requires_implementation": "PDF text/table extraction and NLP parsing"
    }
    return json.dumps(result, indent=2)

# ============================================================================
# EXCEL SYNCHRONIZATION TOOLS
# ============================================================================

@mcp.tool(
    name="sync_booking_to_excel",
    annotations={"title": "Sync Booking Data to Excel", "readOnlyHint": False}
)
async def sync_booking_to_excel(
    excel_path: str = Field(..., description="Path to Excel workbook"),
    booking_data: str = Field(..., description="JSON string of CruiseBooking data"),
    sheet_name: str = Field("Booking Master", description="Target sheet name"),
    overwrite_existing: bool = Field(False, description="Overwrite existing data")
) -> str:
    """Synchronize booking data to Excel workbook."""
    try:
        booking_json = json.loads(booking_data)
        logger.info(f"Syncing booking {booking_json.get('booking_id')} to {excel_path}")
        result = {
            "status": "initiated",
            "excel_file": excel_path,
            "target_sheet": sheet_name,
            "booking_id": booking_json.get("booking_id"),
            "requires_implementation": "openpyxl integration for Excel writing"
        }
        return json.dumps(result, indent=2)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON: {str(e)}"})

@mcp.tool(
    name="read_excel_booking_data",
    annotations={"title": "Read Booking Data from Excel", "readOnlyHint": True}
)
async def read_excel_booking_data(
    excel_path: str = Field(..., description="Path to Excel workbook"),
    sheet_name: str = Field("Booking Master", description="Sheet to read")
) -> str:
    """Read structured booking data from Excel workbook."""
    logger.info(f"Reading {sheet_name} from {excel_path}")
    result = {
        "status": "initiated",
        "file": excel_path,
        "sheet": sheet_name,
        "requires_implementation": "openpyxl integration for Excel reading"
    }
    return json.dumps(result, indent=2)

# ============================================================================
# IMAGE GENERATION & DOCUMENT TOOLS
# ============================================================================

@mcp.tool(name="generate_itinerary_images")
async def generate_itinerary_images(
    booking_data: str = Field(..., description="JSON string of CruiseBooking data"),
    ports: Optional[List[str]] = Field(None, description="Specific ports to generate images for, or 'all'"),
    image_style: str = Field("luxury_travel", description="Style: 'luxury_travel', 'adventure', 'cultural', 'romantic'"),
    api_source: str = Field("stability_ai", description="Image source: 'stability_ai' or 'local_stable_diffusion'")
) -> str:
    """Generate professional images for each cruise port using Stable Diffusion."""
    try:
        booking_json = json.loads(booking_data)
        booking_id = booking_json.get("booking_id", "unknown")
        logger.info(f"Generating images for booking {booking_id} with style '{image_style}'")
        result = {
            "status": "initiated",
            "booking_id": booking_id,
            "image_style": image_style,
            "api_source": api_source,
            "requires_implementation": "Stability AI API or local Stable Diffusion integration"
        }
        return json.dumps(result, indent=2)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON: {str(e)}"})

@mcp.tool(name="insert_images_to_pdf")
async def insert_images_to_pdf(
    pdf_path: str = Field(..., description="Path to template PDF"),
    images_mapping: str = Field(..., description="JSON: {'port_name': 'image_path', ...}"),
    output_path: str = Field(..., description="Output PDF path")
) -> str:
    """Insert generated images into PDF itinerary template."""
    logger.info(f"Inserting images into PDF: {pdf_path}")
    return json.dumps({"status": "initiated", "template_pdf": pdf_path, "output_pdf": output_path}, indent=2)

@mcp.tool(name="insert_images_to_google_docs")
async def insert_images_to_google_docs(
    doc_id: str = Field(..., description="Google Doc ID"),
    images_mapping: str = Field(..., description="JSON: {'port_name': 'image_path', ...}"),
    image_width_pixels: int = Field(600, description="Image width in pixels", ge=200, le=1200)
) -> str:
    """Insert generated images into Google Docs itinerary."""
    logger.info(f"Inserting images into Google Doc: {doc_id}")
    return json.dumps({"status": "initiated", "doc_id": doc_id, "image_width": image_width_pixels}, indent=2)

@mcp.tool(name="generate_itinerary_from_template")
async def generate_itinerary_from_template(
    booking_data: str = Field(..., description="JSON string of CruiseBooking data"),
    client_name: str = Field(..., description="Client name for personalization"),
    output_format: str = Field("pdf", description="Output: 'pdf', 'google_docs', or 'both'"),
    template_type: str = Field("standard", description="Template: 'standard', 'luxury', 'adventure'"),
    include_images: bool = Field(True, description="Generate and include custom images"),
    image_style: str = Field("luxury_travel", description="Image style for generation")
) -> str:
    """Generate complete personalized itinerary from booking data."""
    try:
        booking_json = json.loads(booking_data)
        booking_id = booking_json.get("booking_id", "unknown")
        logger.info(f"Generating {template_type} itinerary for {client_name} ({booking_id})")
        return json.dumps({
            "status": "initiated",
            "client": client_name,
            "booking_id": booking_id,
            "template": template_type,
            "format": output_format
        }, indent=2)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON: {str(e)}"})

@mcp.tool(name="consolidate_booking_sources")
async def consolidate_booking_sources(
    pdf_path: Optional[str] = Field(None, description="Path to confirmation PDF"),
    excel_path: Optional[str] = Field(None, description="Path to Excel workbook"),
    gmail_labels: Optional[List[str]] = Field(None, description="Gmail labels to search for confirmations"),
    booking_id: Optional[str] = Field(None, description="Booking ID to filter results")
) -> str:
    """Consolidate booking data from multiple sources (PDFs, Excel, Gmail)."""
    logger.info("Consolidating booking data from multiple sources")
    sources = []
    if pdf_path: sources.append(f"PDF: {pdf_path}")
    if excel_path: sources.append(f"Excel: {excel_path}")
    if gmail_labels: sources.append(f"Gmail labels: {', '.join(gmail_labels)}")

    return json.dumps({
        "status": "initiated",
        "sources": sources or "none specified",
        "booking_id_filter": booking_id
    }, indent=2)

# ============================================================================
# LIVE WEB SCRAPING TOOLS (PLAYWRIGHT + STEALTH V2)
# ============================================================================

@mcp.tool(
    name="search_live_cruise_voyages",
    annotations={
        "title": "Live Search Cruise Voyages (Stealth)",
        "readOnlyHint": True
    }
)
async def search_live_cruise_voyages(
    url: str = Field(..., description="Target URL to search, e.g., 'https://www.silversea.com/find-a-cruise.html'")
) -> str:
    """Scrapes live luxury cruise voyage information using a stealth browser."""
    logger.info(f"Launching Stealth Playwright to search voyages at: {url}")
    try:
        # V2 SYNTAX: Automatically applies stealth to the entire context
        async with Stealth().use_async(async_playwright()) as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            # Rate limit fix: Slight delay to prevent hammering the server
            await asyncio.sleep(3)

            # Navigate and wait for the page to load
            await page.goto(url, wait_until="networkidle", timeout=45000)

            # Scroll to trigger lazy-loaded elements
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(3000)

            content = await page.evaluate("document.body.innerText")
            await browser.close()

            return json.dumps({
                "status": "success",
                "url": url,
                "raw_data_snippet": content[:6000]
            }, indent=2)

    except Exception as e:
        logger.error(f"Playwright error: {str(e)}")
        return json.dumps({"error": str(e), "type": "scraping_error"})


@mcp.tool(
    name="check_cabin_availability",
    annotations={
        "title": "Check Live Cabin Availability (Stealth)",
        "readOnlyHint": True
    }
)
async def check_cabin_availability(
    voyage_url: str = Field(..., description="Direct URL to the specific cruise voyage page")
) -> str:
    """Scrapes a specific voyage page to find available cabin categories and pricing."""
    logger.info(f"Checking live cabin availability via Stealth for: {voyage_url}")
    try:
        async with Stealth().use_async(async_playwright()) as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            # Rate limit fix: Slight delay
            await asyncio.sleep(3)

            await page.goto(voyage_url, wait_until="networkidle", timeout=45000)

            content = await page.evaluate("document.body.innerText")
            await browser.close()

            return json.dumps({
                "status": "success",
                "url": voyage_url,
                "availability_data_snippet": content[:6000]
            }, indent=2)

    except Exception as e:
        logger.error(f"Playwright error: {str(e)}")
        return json.dumps({"error": str(e), "type": "scraping_error"})
# ============================================================================
# REGISTER THUNDERBIRD INTELLIGENCE TOOLS — Profile-Aware Loader
# ============================================================================
#
# MCP_PROFILE env var controls which tool groups load. This directly controls
# how many tool schemas Claude sees per turn — the primary driver of cache reads.
#
# Profiles:
#   core   — ~25 essential tools. Comms, dossiers, personas, learning, inbox.
#   intel  — core + all research/monitoring tools (~40 tools)
#   travel — core + all booking/search/excursion tools (~50 tools)
#   ops    — core + reporting, billing, reconciliation, automation (~45 tools)
#   full   — everything (default, backward-compatible)
#
# Usage: MCP_PROFILE=intel claude  OR use the `cc` wrapper: cc intel
# ============================================================================

MCP_PROFILE = os.environ.get("MCP_PROFILE", "full").lower()
_VALID_PROFILES = {"core", "intel", "travel", "ops", "full"}
if MCP_PROFILE not in _VALID_PROFILES:
    logger.warning(f"Unknown MCP_PROFILE={MCP_PROFILE!r} — defaulting to 'full'")
    MCP_PROFILE = "full"

logger.info(f"MCP profile: {MCP_PROFILE}")

# ── CORE — always loaded (every profile) ─────────────────────────────────────
_CORE_LOADERS = [
    register_drive_tools, register_gmail_tools, register_keep_tools,
    register_dossier_tools, register_tasks_tools, register_memory_tools,
    register_sss_tools, register_persona_tools, register_learning_tools,
    register_commander_inbox_tools, register_checkpoint_tools, register_router_tools,
    register_dani_email_tools, register_quote_tools, register_dani_voice_tools,
    register_voice_ledger_tools, register_health_tools, register_info_delta_tools,
    register_temporal_tools, register_conversation_learner_tools,
    register_recipient_profile_tools, register_email_classifier_tools,
    register_dossier_scanner_tools, register_bulletin_tools, register_anchor_date_tools,
    register_briefing_tools,
]

# ── INTEL additions ───────────────────────────────────────────────────────────
_INTEL_LOADERS = [
    register_ship_intel_tools, register_world_intel_tools, register_tech_monitor_tools,
    register_x_osint_tools, register_academic_scanner_tools, register_surveillance_tools,
    register_price_monitor_tools, register_email_intel_tools, register_airline_monitor_tools,
    register_intel_crew_tools, register_innovation_tools, register_a2a_tools,
    register_crewai_tools,
]

# ── TRAVEL additions ──────────────────────────────────────────────────────────
_TRAVEL_LOADERS = [
    register_hotel_search_tools, register_flight_search_tools, register_tour_search_tools,
    register_fare_watch_tools, register_excursion_tools, register_transfer_tools,
    register_opentable_tools, register_dining_tools, register_taap_tools,
    register_tess_tools, register_trip_architect_tools, register_worldfactbook_tools,
    register_outside_agents_tools, register_comparison_tools,
    register_itinerary_pipeline_tools, register_auto_enrich_tools,
    register_client_materials_tools, register_v3_tools,
]

# ── OPS additions ─────────────────────────────────────────────────────────────
_OPS_LOADERS = [
    register_commission_recon_tools, register_survey_tools, register_weekly_report_tools,
    register_files_api_tools, register_skills_tools, register_evernote_tools,
    register_star_protocol_tools, register_browser_tools, register_sms_tools,
    register_whatsapp_tools,
]

# ── Build active loader list ──────────────────────────────────────────────────
_active_loaders = list(_CORE_LOADERS)
if MCP_PROFILE in ("intel", "full"):
    _active_loaders += _INTEL_LOADERS
if MCP_PROFILE in ("travel", "full"):
    _active_loaders += _TRAVEL_LOADERS
if MCP_PROFILE in ("ops", "full"):
    _active_loaders += _OPS_LOADERS

# Deduplicate (some loaders may appear in multiple groups)
_seen = set()
_deduped = []
for _fn in _active_loaders:
    if _fn not in _seen:
        _seen.add(_fn)
        _deduped.append(_fn)

for _fn in _deduped:
    try:
        _fn(mcp)
    except Exception as _e:
        logger.warning(f"Tool loader {_fn.__name__} failed: {_e}")

logger.info(f"Profile '{MCP_PROFILE}': {len(_deduped)} tool modules loaded")

# ── Wave 4 — try-block modules ────────────────────────────────────────────────
# connector always loaded (MCP connector infra — core need)
try:
    register_connector_tools(mcp)
except Exception as e:
    logger.warning(f"MCP connector tools not available: {e}")

# remaining wave 4 based on profile
if MCP_PROFILE in ("intel", "full"):
    try:
        register_a2a_protocol_tools(mcp)
    except Exception as e:
        logger.warning(f"A2A protocol tools not available: {e}")

if MCP_PROFILE in ("ops", "full"):
    try:
        register_grant_tools(mcp)
    except Exception as e:
        logger.warning(f"Grant compiler tools not available: {e}")

if MCP_PROFILE in ("travel", "full"):
    try:
        from thunderbird_guest_forms import register_guest_form_tools
        register_guest_form_tools(mcp)
    except Exception as e:
        logger.warning(f"Guest form tools not available: {e}")

if MCP_PROFILE in ("ops", "full"):
    try:
        from thunderbird_reconciliation import register_reconciliation_tools
        register_reconciliation_tools(mcp)
    except Exception as e:
        logger.warning(f"Reconciliation tools not available: {e}")

    try:
        from thunderbird_product_intake import register_product_intake_tools
        register_product_intake_tools(mcp)
    except Exception as e:
        logger.warning(f"Product intake tools not available: {e}")

# thunderbird_bulletin: registered above (hard import — line 74)

# ── Dani Hardening Tools (data confidence, pre-send, conversation state, response library) ──

@mcp.tool(
    name="presend_evaluate",
    annotations={"title": "Pre-Send Email Evaluator", "readOnlyHint": True},
)
async def presend_evaluate(body: str, subject: str = "", recipient: str = "") -> str:
    """Evaluate a draft email for leaks (commission, personas, jargon) before sending."""
    from thunderbird_presend_evaluator import evaluate_draft
    result = evaluate_draft(body, subject, recipient, is_client_facing=True)
    return result.to_cos_report()


@mcp.tool(
    name="conversation_detect_phase",
    annotations={"title": "Detect Conversation Phase", "readOnlyHint": True},
)
async def conversation_detect_phase(message: str, is_first_message: bool = False) -> str:
    """Detect client conversation phase (GREETING/DISCOVERY/INFORMATION/etc)."""
    from thunderbird_conversation_state import detect_and_guide
    guidance = detect_and_guide(message, is_first_message=is_first_message)
    return guidance.to_injection_block()


@mcp.tool(
    name="response_library_list",
    annotations={"title": "List Response Templates", "readOnlyHint": True},
)
async def response_library_list() -> str:
    """List all available structured response templates for Dani."""
    from thunderbird_response_library import list_templates
    import json
    return json.dumps(list_templates(), indent=2)


@mcp.tool(
    name="response_library_select",
    annotations={"title": "Select Response Template", "readOnlyHint": True},
)
async def response_library_select(query: str, phase_hint: str = "") -> str:
    """Select the best response template for a client query."""
    from thunderbird_response_library import select_template
    tmpl = select_template(query, phase_hint=phase_hint)
    if tmpl:
        return tmpl.to_injection_block()
    return "No matching template found for this query."


@mcp.tool(
    name="data_confidence_report",
    annotations={"title": "Data Confidence Report", "readOnlyHint": True},
)
async def data_confidence_report(client: str, query: str = "") -> str:
    """Generate a data confidence report for a client query."""
    from thunderbird_data_confidence import build_confidence_report
    report = build_confidence_report(query=query, client=client)
    return report.to_injection_block()


# ── Context Engineering Tools (Week 2 · 23 MAR 2026) ────────────────────────

@mcp.tool(
    name="load_context_pack",
    annotations={"title": "Load Context Pack for Document Generation", "readOnlyHint": True},
)
async def load_context_pack(
    client_tier: str,
    context_keywords: str = "",
    voice_count: int = 5,
    doc_type: str = "email",
) -> str:
    """Load the full context pack for a client document — voice examples + learning principles.

    Call this BEFORE drafting any client-facing document (email, proposal, itinerary,
    trip validation). The returned context block should be injected into your draft.

    Args:
        client_tier: Relationship tier — "personal" | "client" | "vendor" | "internal" | "family" | "friend"
        context_keywords: Comma-separated keywords matching the document context
                          e.g. "proposal, friend tier, opening paragraph"
                          e.g. "payment reminder, final payment"
                          e.g. "itinerary, narrative, day-by-day"
        voice_count: Number of voice examples to load (default 5)
        doc_type: Document type for context filtering — "email" | "proposal" | "itinerary" | "validation"
    """
    import json
    from pathlib import Path
    import sys as _sys

    context_dir = Path(__file__).parent / "context_engineering"
    if str(context_dir) not in _sys.path:
        _sys.path.insert(0, str(context_dir))

    try:
        from context_packs import load_voice_examples, load_learning_principles

        # Map "friend" tier to "personal" for voice_examples lookup
        tier_map = {"friend": "personal", "vip": "client", "standard": "client",
                    "prospect": "client", "family": "personal"}
        lookup_tier = tier_map.get(client_tier.lower(), client_tier.lower())

        voice_examples = load_voice_examples(tier=lookup_tier, count=voice_count)
        keywords = [k.strip() for k in context_keywords.split(",") if k.strip()]
        if not keywords:
            keywords = [doc_type, client_tier]
        principles = load_learning_principles(context_keywords=keywords)

        lines = [
            f"== CONTEXT PACK — {doc_type.upper()} / {client_tier.upper()} TIER ==",
            f"Loaded: {len(voice_examples)} voice examples, {len(principles)} learning principles",
            "",
        ]

        if voice_examples:
            lines.append("== COMMANDER'S ACTUAL VOICE (match this style exactly) ==")
            for i, ex in enumerate(voice_examples, 1):
                lines += [
                    f"[Example {i} — {ex.tier} tier, score {ex.score}]",
                    f"Subject: {ex.subject}",
                    ex.body[:350] + ("..." if len(ex.body) > 350 else ""),
                    "",
                ]

        if principles:
            lines.append("== EDIT PRINCIPLES (apply BEFORE you write — not after) ==")
            for p in principles:
                lines.append(f"• [{p.context}] {p.principle}")
                if p.example_before and p.example_after:
                    lines.append(f"  Before: {p.example_before}")
                    lines.append(f"  After:  {p.example_after}")
            lines.append("")

        lines += [
            "== BRAND RULES (non-negotiable) ==",
            "• Company: Dreams2Memories Travel, LLC — NEVER 'Love Group Travel'",
            "• Sign-off: 'Thanks' or 'Thank you' — NEVER 'Best'",
            "• Stationery: cream paper (#f7f3ea), bright blue ink (#0000ff), Georgia serif",
            "• One CTA per email. Lead with the destination, not the transaction.",
        ]

        return "\n".join(lines)

    except Exception as e:
        return f"Context pack load failed: {e}. Fallback: use Commander voice (short, warm, certain). Sign off: Thanks."


@mcp.tool(
    name="capture_edit_diff",
    annotations={"title": "Capture Commander Edit — Learning Compiler", "readOnlyHint": False},
)
async def capture_edit_diff(
    original: str,
    edited: str,
    context: str,
    doc_type: str = "email",
) -> str:
    """Capture the diff between a generated document and Commander's edit. Injects a new learning principle.

    Call this whenever Commander edits a draft before sending. The learning compiler
    extracts the principle and adds it to learning_principles.json so the next draft
    is better before Commander sees it.

    Args:
        original: The AI-generated text (before Commander's edit)
        edited: The Commander's edited version (what was actually sent)
        context: Context description — e.g., "friend tier, proposal narrative, opening paragraph"
        doc_type: "email" | "proposal" | "itinerary" | "validation"
    """
    import json
    import difflib
    from pathlib import Path
    from datetime import datetime

    principles_file = Path(__file__).parent / "config" / "learning_principles.json"

    try:
        # Compute a human-readable diff
        orig_lines = original.splitlines()
        edit_lines = edited.splitlines()
        diff = list(difflib.unified_diff(orig_lines, edit_lines, lineterm="", n=1))
        diff_summary = "\n".join(diff[:20]) if diff else "No structural diff — minor wording change"

        # Load existing principles
        data = json.loads(principles_file.read_text()) if principles_file.exists() else {"meta": {}, "principles": []}
        existing = data.get("principles", [])
        next_id = f"LP{len(existing) + 1:03d}"

        # Build new principle entry (direction heuristic from diff)
        removed = [l[1:] for l in diff if l.startswith("-") and not l.startswith("---")]
        added   = [l[1:] for l in diff if l.startswith("+") and not l.startswith("+++")]

        if len(added) < len(removed):
            direction = "tighten"
        elif any(word in " ".join(added).lower() for word in ["warm", "feel", "love", "excited", "looking forward"]):
            direction = "soften"
        elif any(word in " ".join(added).lower() for word in ["you", "your", context.split(",")[0].strip().lower()]):
            direction = "personalize"
        else:
            direction = "adjust"

        example_before = " ".join(removed[:1]).strip()[:200] if removed else original[:120]
        example_after  = " ".join(added[:1]).strip()[:200] if added else edited[:120]

        new_principle = {
            "id": next_id,
            "context": context,
            "principle": f"[Auto-captured {datetime.utcnow().strftime('%d %b %Y')}] Commander edited this {doc_type}. "
                         f"Direction: {direction}. See before/after for the pattern.",
            "direction": direction,
            "example_before": example_before,
            "example_after": example_after,
            "extracted_from": f"Commander edit — {datetime.utcnow().strftime('%d %b %Y')}",
            "confidence": 0.75,
            "auto_captured": True,
        }

        existing.append(new_principle)
        data["principles"] = existing
        data.setdefault("meta", {})["total_principles"] = len(existing)
        data["meta"]["last_updated"] = datetime.utcnow().isoformat()

        principles_file.write_text(json.dumps(data, indent=2))

        return json.dumps({
            "status": "captured",
            "principle_id": next_id,
            "direction": direction,
            "context": context,
            "total_principles": len(existing),
            "message": f"Learning compiler: principle {next_id} added. Next similar {doc_type} will reflect this before Commander sees it.",
        })

    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


# ── Hotel Guide PDF Render ─────────────────────────────────────────────────

@mcp.tool(
    name="render_hotel_guide_pdf",
    annotations={"title": "Render Hotel Guide PDF", "readOnlyHint": False},
)
async def render_hotel_guide_pdf(
    client_name: str,
    destination: str,
    travel_dates: str,
    nights: int,
    guests: int,
    hotels_json: str,
    budget: str = "",
    comparison_json: str = "[]",
    logistics_json: str = "{}",
) -> str:
    """Render a D2M-branded hotel guide PDF from structured data.

    Args:
        client_name: Client name (e.g., "Nancy & Ken Lyons")
        destination: City/region (e.g., "Athens")
        travel_dates: Date range string (e.g., "August 8-12, 2026")
        nights: Number of nights
        guests: Number of guests
        hotels_json: JSON array of hotel objects (name, stars, neighborhood, description, rates, etc.)
        budget: Optional budget string (pre-formatted)
        comparison_json: Optional JSON array of comparison rows
        logistics_json: Optional JSON object with transport/notes
    """
    import json as _json
    from pathlib import Path
    sys_path = str(Path(__file__).parent / "templates")
    if sys_path not in sys.path:
        sys.path.insert(0, sys_path)
    from d2m_hotel_guide_schema import (
        HotelGuideContext, DocMeta, HotelCard, PriceBox, RoomRate,
        Badge, Landmark, Cancellation, CompRow, Recommendation,
        Transport, Logistics, render_to_pdf,
    )

    doc = DocMeta(
        client_name=client_name,
        destination=destination,
        travel_dates=travel_dates,
        nights=nights,
        guests=guests,
        budget=budget,
    )

    hotels_data = _json.loads(hotels_json)
    hotels = []
    for h in hotels_data:
        rates = [RoomRate(**r) for r in h.get("rates", [])]
        badges = [Badge(**b) for b in h.get("badges", [])]
        landmarks = [Landmark(**lm) for lm in h.get("landmarks", [])]
        cancel = Cancellation(**h["cancellation"]) if h.get("cancellation") else None
        price_box = PriceBox(**h.get("price_box", {}))
        hotels.append(HotelCard(
            name=h["name"],
            stars=h.get("stars", 5),
            neighborhood=h.get("neighborhood", ""),
            description=h.get("description", ""),
            photos=h.get("photos", []),
            badges=badges,
            price_box=price_box,
            rates=rates,
            landmarks=landmarks,
            cancellation=cancel,
        ))

    comparison = [CompRow(**c) for c in _json.loads(comparison_json)]
    logi_data = _json.loads(logistics_json)
    logistics = None
    if logi_data:
        logistics = Logistics(
            transport=[Transport(**t) for t in logi_data.get("transport", [])],
            notes=logi_data.get("notes", []),
            footnotes=logi_data.get("footnotes", []),
        )

    ctx = HotelGuideContext(doc=doc, hotels=hotels, comparison=comparison, logistics=logistics)

    safe_name = client_name.replace(" ", "_").replace("&", "and")
    output_path = Path.home() / "Thunderbird" / "output" / f"{safe_name}_{destination}_Hotel_Guide.pdf"
    render_to_pdf(ctx, output_path)
    return f"Hotel guide PDF rendered: {output_path}"


# ============================================================================
# INNOVATION SCANNER — INLINE MCP TOOLS
# ============================================================================

@mcp.tool(
    name="innovation_daily_scan",
    annotations={"title": "Innovation Daily Scan", "readOnlyHint": False},
)
async def innovation_daily_scan() -> str:
    """Run a quick daily innovation scan across Reddit, GitHub, HN, and tech blogs.
    Scans hot/trending posts and returns top findings with D2M relevance scoring."""
    result = run_daily_scan()
    return json.dumps({
        "status": "complete",
        "scan_type": "daily",
        "findings": len(result.findings),
        "sources_scanned": result.sources_scanned,
        "top_5": [
            {"title": f.title, "source": f.source, "url": f.url,
             "category": f.category, "relevance": f.relevance, "score": f.score}
            for f in result.top_findings[:5]
        ],
        "digest_path": str(Path.home() / "Thunderbird" / "intel" / "daily_innovation_digest.md"),
    }, indent=2)


@mcp.tool(
    name="innovation_weekly_scan",
    annotations={"title": "Innovation Weekly Deep Scan", "readOnlyHint": False},
)
async def innovation_weekly_scan() -> str:
    """Run a deep weekly innovation scan — all sources, full competitor analysis.
    Typically scheduled Sunday mornings but can be triggered on demand."""
    result = run_weekly_scan()
    return json.dumps({
        "status": "complete",
        "scan_type": "weekly",
        "findings": len(result.findings),
        "sources_scanned": result.sources_scanned,
        "top_10": [
            {"title": f.title, "source": f.source, "url": f.url,
             "category": f.category, "relevance": f.relevance,
             "priority": f.priority, "score": f.score}
            for f in result.top_findings[:10]
        ],
        "report_path": str(Path.home() / "Thunderbird" / "intel" / "weekly_innovation_report.md"),
    }, indent=2)


@mcp.tool(
    name="innovation_briefing_digest",
    annotations={"title": "Innovation Briefing Digest", "readOnlyHint": True},
)
async def innovation_briefing_digest(max_items: int = 5) -> str:
    """Get a compact innovation digest for injection into the morning briefing.
    Returns top findings formatted for COS morning brief consumption."""
    digest = get_digest_for_briefing(max_items=max_items)
    if not digest:
        return json.dumps({"status": "empty", "message": "No innovation digest available. Run daily scan first."})
    return json.dumps({"status": "ok", "digest": digest})


# ============================================================================
# SHELL EXEC TOOL
# ============================================================================

import subprocess
import os

# SECURITY: Disabled 2026-03-20 — arbitrary command execution exposed via unauthenticated endpoint
# SHELL_LOG = os.path.expanduser("~/Thunderbird/logs/shell_exec.log")
#
# @mcp.tool(
#     name="shell_exec",
#     annotations={
#         "title": "Execute Shell Command",
#         "readOnlyHint": False,
#         "destructiveHint": True,
#         "idempotentHint": False,
#         "openWorldHint": True,
#     },
# )
# async def shell_exec(
#     command: str = Field(..., description="Bash command to execute on the local machine"),
#     working_dir: Optional[str] = Field(None, description="Working directory (default: ~/Thunderbird)"),
#     timeout: int = Field(30, description="Timeout in seconds (1-300)", ge=1, le=300),
# ) -> str:
#     """Execute an arbitrary bash command on the local machine.
#     Logs every invocation to ~/Thunderbird/logs/shell_exec.log."""
#     cwd = os.path.expanduser(working_dir or "~/Thunderbird")
#     start = datetime.now()
#
#     os.makedirs(os.path.dirname(SHELL_LOG), exist_ok=True)
#     with open(SHELL_LOG, "a", encoding="utf-8") as log_file:
#         log_file.write(f"[{start.isoformat()}] CWD={cwd} CMD={command}\n")
#
#     try:
#         result = subprocess.run(
#             command, shell=True, cwd=cwd,
#             capture_output=True, text=True, timeout=timeout,
#         )
#         elapsed = (datetime.now() - start).total_seconds()
#         return json.dumps({
#             "stdout": result.stdout,
#             "stderr": result.stderr,
#             "exit_code": result.returncode,
#             "elapsed_seconds": elapsed,
#             "command": command,
#             "cwd": cwd,
#         }, indent=2)
#     except subprocess.TimeoutExpired:
#         return json.dumps({"error": f"Command timed out after {timeout}s", "command": command, "cwd": cwd}, indent=2)
#     except Exception as e:
#         return json.dumps({"error": str(e), "command": command, "cwd": cwd}, indent=2)


# ============================================================================
# SERVER INITIALIZATION
# ============================================================================
# This MUST be the final block in the file to ensure tools are read first!

if __name__ == "__main__":
    import sys

    # Print server info to stderr — stdout is reserved for MCP JSON-RPC
    def log(msg=""):
        print(msg, file=sys.stderr)

    log("=" * 70)
    log("Dreams2Memories Travel Automation MCP Server")
    log("=" * 70)
    log("\nAvailable Tools:")
    log("  PDF Extraction:")
    log("    - extract_pdf_booking_details")
    log("    - extract_pdf_itinerary")
    log("\n  Excel Synchronization:")
    log("    - sync_booking_to_excel")
    log("    - read_excel_booking_data")
    log("\n  Image Generation:")
    log("    - generate_itinerary_images")
    log("    - insert_images_to_pdf")
    log("    - insert_images_to_google_docs")
    log("\n  Itinerary Generation:")
    log("    - generate_itinerary_from_template")
    log("\n  Data Consolidation:")
    log("    - consolidate_booking_sources")
    log("\n  Live Web Search:")
    log("    - search_live_cruise_voyages")
    log("    - check_cabin_availability")
    log("\n  Hotel Search (Hotelbeds/Bedsonline):")
    log("    - search_hotels")
    log("    - check_hotel_rates")
    log("    - get_hotel_details")
    log("    - bedsonline_browse_search")
    log("    - bedsonline_browse_interact")
    log("    - compare_hotels")
    log("    - render_hotel_quote_pdf")
    log("    - email_hotel_quote")
    log("\n  Flight Search (Amadeus):")
    log("    - search_flights")
    log("    - verify_flight_price")
    log("    - search_airports")
    log("    - compare_flights")
    log("    - render_flight_quote_pdf")
    log("    - email_flight_quote")
    log("\n  Gmail:")
    log("    - gmail_search_messages")
    log("    - gmail_read_message")
    log("    - gmail_read_thread")
    log("    - gmail_list_drafts")
    log("    - gmail_create_draft")
    log("    - gmail_send_draft")
    log("    - gmail_send_email")
    log("    - gmail_update_draft")
    log("    - gmail_delete_draft")
    log("    - gmail_get_profile")
    log("\n  Tours & Activities:")
    log("    - search_tours (Amadeus)")
    log("    - search_tours_musement")
    log("    - browse_tour_portal (ProjectExpedition/TAAP/Viator TA)")
    log("    - scrape_consumer_tour_prices (Expedia/Viator public)")
    log("    - scrape_tour_content (Fodor's/Rick Steves)")
    log("    - compare_tours")
    log("    - render_tour_quote_pdf")
    log("    - email_tour_quote")
    log("\n  SMS Notifications:")
    log("    - send_sms_notification")
    log("\n  Evernote Mirror:")
    log("    - mirror_to_evernote")
    log("\n  WhatsApp (Twilio):")
    log("    - send_whatsapp")
    # Parse transport mode from CLI args
    # --http / --streamable-http → Streamable HTTP (production, recommended)
    # --sse                      → Legacy SSE (deprecated April 2026)
    # (default)                  → stdio (Claude CLI local)
    transport = "stdio"
    host = "127.0.0.1"  # SECURITY: localhost only — cloudflared handles external access
    port = int(os.environ.get("PORT", 8765))
    for arg in sys.argv[1:]:
        if arg in ("--http", "--streamable-http"):
            transport = "streamable-http"
        elif arg == "--sse":
            transport = "sse"
        elif arg.startswith("--port="):
            port = int(arg.split("=", 1)[1])
        elif arg.startswith("--host="):
            host = arg.split("=", 1)[1]

    if transport != "stdio":
        # Set host/port on the FastMCP settings for SSE/HTTP
        mcp.settings.host = host
        mcp.settings.port = port

        # Streamable HTTP production settings:
        # - stateless_http: no server-side session state → works behind load balancers
        # - json_response: plain JSON instead of SSE streams for simple responses
        if transport == "streamable-http":
            mcp.settings.stateless_http = True
            mcp.settings.json_response = True

        # Update DNS rebinding protection to allow tunnel hostnames.
        # FastMCP auto-enables this with localhost-only defaults (MCP SDK 1.26+),
        # but cloudflared forwards requests with the original Host header
        # (e.g., mcp.d2mluxury.quest), which gets rejected as 421.
        from mcp.server.transport_security import TransportSecuritySettings
        mcp.settings.transport_security = TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=[
                "127.0.0.1:*", "localhost:*", "[::1]:*",
                "mcp.d2mluxury.quest",       # cloudflared tunnel
                "192.168.1.198:*",               # LAN IP
                "100.69.222.124:*",          # Tailscale IP
            ],
            allowed_origins=[
                "http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*",
                "https://mcp.d2mluxury.quest",
                "http://192.168.1.198:*",        # LAN
                "http://100.69.222.124:*",   # Tailscale
            ],
        )

    mode_str = f"{transport} transport"
    if transport != "stdio":
        mode_str += f" on {host}:{port}"
        if transport == "streamable-http":
            mode_str += f"  endpoint: /mcp"

    if transport == "sse":
        log(f"\n  *** WARNING: SSE transport is deprecated (April 2026) ***")
        log(f"  *** Use --http for Streamable HTTP (production standard) ***")

    log(f"\n{'=' * 70}")
    log(f"Starting MCP server ({mode_str})...")
    log("=" * 70 + "\n")

    # Run the server
    mcp.run(transport=transport)
