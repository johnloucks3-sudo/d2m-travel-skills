"""
Dreams2Memories Unified Quote Renderer
=======================================

Renders branded D2M quote PDFs for all product types:
flight, hotel, tour, cruise.

Uses d2m_quote.html.j2 unified Jinja2 template.
Integrates with: travel_mcp_server.py
"""

import json
import logging
import base64
from typing import Optional
from pathlib import Path
from datetime import datetime

from pydantic import Field
from mcp.server.fastmcp import FastMCP
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML as WeasyHTML

logger = logging.getLogger(__name__)

THUNDERBIRD_DIR = Path(__file__).parent
OUTPUT_DIR = THUNDERBIRD_DIR / "output"
LOGO_FILE = THUNDERBIRD_DIR / "Agency_Logo.png"
HEADSHOT_FILE = THUNDERBIRD_DIR / "John_Headshot.jpg"
SLOGAN = "D2M Travel, Curating the experience of a lifetime"


def _logo_base64() -> str:
    if LOGO_FILE.exists():
        data = LOGO_FILE.read_bytes()
        b64 = base64.b64encode(data).decode("utf-8")
        suffix = LOGO_FILE.suffix.lower()
        mime = "image/png" if suffix == ".png" else "image/jpeg"
        return f"data:{mime};base64,{b64}"
    return ""


def _headshot_base64() -> str:
    if HEADSHOT_FILE.exists():
        data = HEADSHOT_FILE.read_bytes()
        b64 = base64.b64encode(data).decode("utf-8")
        suffix = HEADSHOT_FILE.suffix.lower()
        mime = "image/jpeg" if suffix in (".jpg", ".jpeg") else "image/png"
        return f"data:{mime};base64,{b64}"
    return ""


def render_quote_html(quote_type: str, context: dict) -> str:
    """Render unified quote HTML from d2m_quote.html.j2 template."""
    env = Environment(loader=FileSystemLoader(str(THUNDERBIRD_DIR / "templates")))
    template = env.get_template("d2m_quote.html.j2")

    context["quote_type"] = quote_type
    context["logo_uri"] = _logo_base64()
    context["headshot_uri"] = _headshot_base64()
    context["slogan"] = SLOGAN
    if "prepared_date" not in context:
        context["prepared_date"] = datetime.now().strftime("%B %d, %Y")

    return template.render(context)


def render_quote_pdf(quote_type: str, context: dict, output_filename: str) -> tuple:
    """Render quote to HTML + PDF. Returns (pdf_path, html_path)."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = OUTPUT_DIR / output_filename
    html_path = OUTPUT_DIR / output_filename.replace(".pdf", ".html")

    html_content = render_quote_html(quote_type, context)

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    WeasyHTML(string=html_content, base_url=str(THUNDERBIRD_DIR)).write_pdf(str(pdf_path))

    return pdf_path, html_path


def _default_filename(client_name: str, label: str, quote_type: str) -> str:
    safe_client = client_name.replace(" ", "_")
    safe_label = label.replace(" ", "_").replace(",", "")
    month_year = datetime.now().strftime("%b%Y")
    return f"{safe_client}_{safe_label}_{quote_type.title()}_{month_year}.pdf"


def register_quote_tools(mcp: FastMCP):

    @mcp.tool(
        name="render_quote_pdf",
        annotations={"title": "Render Unified D2M Quote PDF (Flight/Hotel/Tour/Cruise)", "readOnlyHint": False},
    )
    async def render_quote_pdf_tool(
        quote_type: str = Field(
            ...,
            description="Quote type: 'flight', 'hotel', 'tour', or 'cruise'",
        ),
        client_name: str = Field(..., description="Client name"),
        options_json: str = Field(
            ...,
            description="JSON array of option objects. Structure depends on quote_type:\n"
            "FLIGHT: option, airline, cabin, client_price, badges[], seats_remaining, "
            "legs[{label, segments[{dep_time, dep_airport, arr_time, arr_airport, duration, stops, flight_num}]}]\n"
            "HOTEL: option, name, category, zone, room, board, per_night_client, client_total, cancellation, badges[]\n"
            "TOUR: option, name, source, type, duration, rating, client_price, short_description, pictures[], badges[], consumer_price, savings\n"
            "CRUISE: option, ship, stateroom_category, stateroom_number, deck, embark_date, disembark_date, "
            "embark_port, disembark_port, ports[], inclusions, client_price, deposit, badges[]",
        ),
        comparison_json: Optional[str] = Field(
            None,
            description="JSON array of comparison row objects. Include is_pick (bool) to highlight recommended row. "
            "Columns vary by type — see d2m_quote.html.j2 template.",
        ),
        destination: Optional[str] = Field(None, description="Destination (hotel/tour/cruise)"),
        origin_city: Optional[str] = Field(None, description="Origin city (flight)"),
        destination_city: Optional[str] = Field(None, description="Destination city (flight)"),
        departure_date: Optional[str] = Field(None, description="Departure date (flight)"),
        return_date: Optional[str] = Field(None, description="Return date (flight, optional)"),
        check_in: Optional[str] = Field(None, description="Check-in date (hotel)"),
        check_out: Optional[str] = Field(None, description="Check-out date (hotel)"),
        nights: Optional[int] = Field(None, description="Number of nights (hotel/cruise)"),
        travel_dates: Optional[str] = Field(None, description="Travel dates string (tour)"),
        sailing_dates: Optional[str] = Field(None, description="Sailing dates string (cruise)"),
        cruise_line: Optional[str] = Field(None, description="Cruise line name (cruise)"),
        itinerary_name: Optional[str] = Field(None, description="Itinerary name (cruise)"),
        travelers: str = Field("2", description="Number of travelers"),
        recommendation: Optional[str] = Field(None, description="Recommendation text"),
        notes: Optional[str] = Field(None, description="Important notes/disclaimers"),
        output_filename: Optional[str] = Field(None, description="Output PDF filename"),
    ) -> str:
        """Render a branded D2M quote PDF for any product type.

        One unified template for flights, hotels, tours, and cruises.
        Generates a professional PDF with option cards, comparison table,
        recommendation, logo, headshot, and full D2M branding.
        """
        try:
            if quote_type not in ("flight", "hotel", "tour", "cruise"):
                return json.dumps({"error": f"Invalid quote_type: {quote_type}. Use flight/hotel/tour/cruise."})

            options = json.loads(options_json)
            comparison = json.loads(comparison_json) if comparison_json else None

            # Build context
            context = {
                "client_name": client_name,
                "options": options,
                "comparison": comparison,
                "travelers": travelers,
                "recommendation": recommendation,
            }

            # Type-specific context
            if quote_type == "flight":
                context["origin_city"] = origin_city or ""
                context["destination_city"] = destination_city or ""
                context["departure_date"] = departure_date or ""
                context["return_date"] = return_date
                label = f"{origin_city or ''}_{destination_city or ''}"
                default_notes = "Prices valid for 24 hours from quote date. Fares and availability subject to change. Taxes and fees included."
            elif quote_type == "hotel":
                context["destination"] = destination or ""
                context["check_in"] = check_in or ""
                context["check_out"] = check_out or ""
                context["nights"] = nights or 1
                label = (destination or "").split(",")[0]
                default_notes = "Rates subject to availability and may change. Cancellation policies apply as noted. All prices include taxes and fees."
            elif quote_type == "tour":
                context["destination"] = destination or ""
                context["travel_dates"] = travel_dates or ""
                label = (destination or "").split(",")[0]
                default_notes = "Prices valid for 48 hours. Availability subject to change. All prices per person unless noted."
            elif quote_type == "cruise":
                context["destination"] = destination or ""
                context["sailing_dates"] = sailing_dates or ""
                context["nights"] = nights
                context["cruise_line"] = cruise_line or ""
                context["itinerary_name"] = itinerary_name
                label = cruise_line or (destination or "").split(",")[0]
                default_notes = "Pricing subject to change until deposit is received. Port order and times may be adjusted by the cruise line. Travel insurance strongly recommended."

            context["notes"] = notes or default_notes

            if not output_filename:
                output_filename = _default_filename(client_name, label, quote_type)

            pdf_path, html_path = render_quote_pdf(quote_type, context, output_filename)

            logger.info(f"Unified quote PDF rendered: {pdf_path}")
            return json.dumps({
                "status": "success",
                "quote_type": quote_type,
                "pdf_path": str(pdf_path),
                "html_path": str(html_path),
                "client_name": client_name,
                "options_count": len(options),
                "has_comparison": comparison is not None,
                "has_logo": LOGO_FILE.exists(),
                "has_headshot": HEADSHOT_FILE.exists(),
            }, indent=2)

        except json.JSONDecodeError as e:
            return json.dumps({"error": f"Invalid JSON: {str(e)}"}, indent=2)
        except Exception as e:
            logger.error(f"Quote PDF render error: {e}")
            return json.dumps({"error": str(e), "type": "render_error"}, indent=2)

    logger.info("Unified quote render tools registered (flight/hotel/tour/cruise)")
