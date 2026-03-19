"""
Dreams2Memories Flight Search MCP Module
=========================================

Flight search, comparison, and quote generation via Amadeus API:
- Search flights by origin/destination/dates (one-way, round-trip)
- Verify/re-price flight offers before quoting
- Airport/city code autocomplete
- Side-by-side flight comparison
- Branded PDF quote generation
- Gmail draft with quote attachment

Integrates with: travel_mcp_server.py
Dependencies: requests
API Docs: https://developers.amadeus.com/self-service
"""

import json
import logging
import time
import base64
import requests
from typing import Optional
from pathlib import Path
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

from pydantic import Field
from mcp.server.fastmcp import FastMCP
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

# FlightRadar24 unofficial lib (pip install FlightRadarAPI)
try:
    from FlightRadar24.api import FlightRadar24API
    FR24_AVAILABLE = True
except ImportError:
    FR24_AVAILABLE = False

# ============================================================================
# CONFIGURATION
# ============================================================================

logger = logging.getLogger(__name__)


class FlightAwareConfig:
    """FlightAware AeroAPI configuration.

    Get API key from https://flightaware.com/aeroapi/portal/
    Free dev tier: limited calls. Production: $0.002/query.
    """

    API_KEY = ""
    BASE_URL = "https://aeroapi.flightaware.com/aeroapi"


class FlightRadar24Config:
    """FlightRadar24 configuration (unofficial FlightRadarAPI library).

    No API key needed for unofficial lib.
    pip install FlightRadarAPI
    """
    pass


class AmadeusConfig:
    """Amadeus Self-Service API configuration.

    Get credentials from https://developers.amadeus.com/
    Free test tier: 500 calls/month.
    """

    CLIENT_ID = ""
    CLIENT_SECRET = ""

    # Switch to "https://api.amadeus.com" for production
    BASE_URL = "https://test.api.amadeus.com"

    # Cached OAuth2 token
    _token = None
    _token_expires = 0


THUNDERBIRD_DIR = Path.home() / "Thunderbird"


def _load_credentials() -> tuple[str, str]:
    """Load Amadeus API credentials from config file."""
    if AmadeusConfig.CLIENT_ID and AmadeusConfig.CLIENT_SECRET:
        return AmadeusConfig.CLIENT_ID, AmadeusConfig.CLIENT_SECRET

    cred_file = THUNDERBIRD_DIR / "amadeus_credentials.json"
    if cred_file.exists():
        with open(cred_file, encoding="utf-8") as f:
            creds = json.load(f)
        AmadeusConfig.CLIENT_ID = creds.get("client_id", "")
        AmadeusConfig.CLIENT_SECRET = creds.get("client_secret", "")
        if creds.get("base_url"):
            AmadeusConfig.BASE_URL = creds["base_url"]
        return AmadeusConfig.CLIENT_ID, AmadeusConfig.CLIENT_SECRET

    raise ValueError(
        "Amadeus credentials not configured. "
        "Create ~/Thunderbird/amadeus_credentials.json with "
        '{"client_id": "YOUR_KEY", "client_secret": "YOUR_SECRET"}'
    )


def _get_token() -> str:
    """Get OAuth2 access token, refreshing if expired."""
    now = time.time()
    if AmadeusConfig._token and now < AmadeusConfig._token_expires - 60:
        return AmadeusConfig._token

    client_id, client_secret = _load_credentials()
    resp = requests.post(
        f"{AmadeusConfig.BASE_URL}/v1/security/oauth2/token",
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    AmadeusConfig._token = data["access_token"]
    AmadeusConfig._token_expires = now + data.get("expires_in", 1799)
    return AmadeusConfig._token


def _auth_headers() -> dict:
    """Build authenticated request headers."""
    token = _get_token()
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


# ============================================================================
# CURRENCY HELPERS
# ============================================================================

EUR_TO_USD = 1.09
STANDARD_MARKUP = 0.25
PREMIUM_MARKUP = 0.22


def fmt_usd(amount) -> str:
    """Format a numeric amount as USD string."""
    try:
        val = float(amount)
        return f"${val:,.2f}"
    except (ValueError, TypeError):
        return str(amount)


def _apply_markup(net_amount: float, currency: str = "USD", markup: float = STANDARD_MARKUP) -> dict:
    """Convert to USD if needed and apply markup."""
    usd_net = net_amount
    if currency.upper() == "EUR":
        usd_net = net_amount * EUR_TO_USD

    client_price = usd_net * (1 + markup)
    return {
        "net_usd": fmt_usd(usd_net),
        "markup_pct": f"{markup * 100:.0f}%",
        "client_price_usd": fmt_usd(client_price),
        "net_raw": round(usd_net, 2),
        "client_raw": round(client_price, 2),
    }


# ============================================================================
# RESPONSE FORMATTING
# ============================================================================

def _format_flight_offers(data: dict) -> dict:
    """Extract key fields from Amadeus flight offers response."""
    raw_offers = data.get("data", [])
    dictionaries = data.get("dictionaries", {})
    carriers = dictionaries.get("carriers", {})
    aircraft = dictionaries.get("aircraft", {})

    offers = []
    for offer in raw_offers:
        itineraries = []
        for itin in offer.get("itineraries", []):
            segments = []
            for seg in itin.get("segments", []):
                segments.append({
                    "departure_airport": seg.get("departure", {}).get("iataCode"),
                    "departure_time": seg.get("departure", {}).get("at"),
                    "arrival_airport": seg.get("arrival", {}).get("iataCode"),
                    "arrival_time": seg.get("arrival", {}).get("at"),
                    "carrier": carriers.get(seg.get("carrierCode"), seg.get("carrierCode")),
                    "carrier_code": seg.get("carrierCode"),
                    "flight_number": f"{seg.get('carrierCode')}{seg.get('number')}",
                    "aircraft": aircraft.get(seg.get("aircraft", {}).get("code"), seg.get("aircraft", {}).get("code")),
                    "duration": seg.get("duration"),
                    "stops": seg.get("numberOfStops", 0),
                })
            itineraries.append({
                "duration": itin.get("duration"),
                "segments": segments,
                "stops": len(segments) - 1,
            })

        # Price breakdown
        price = offer.get("price", {})
        currency = price.get("currency", "USD")
        total = float(price.get("grandTotal", price.get("total", 0)))
        base = float(price.get("base", 0))

        # Traveler pricing for cabin class info
        cabin_class = "UNKNOWN"
        traveler_pricings = offer.get("travelerPricings", [])
        if traveler_pricings:
            fare_details = traveler_pricings[0].get("fareDetailsBySegment", [])
            if fare_details:
                cabin_class = fare_details[0].get("cabin", "UNKNOWN")

        pricing = _apply_markup(total, currency)

        offers.append({
            "offer_id": offer.get("id"),
            "source": offer.get("source"),
            "instant_ticketing": offer.get("instantTicketingRequired", False),
            "itineraries": itineraries,
            "cabin_class": cabin_class,
            "price": {
                "currency": currency,
                "base": fmt_usd(base) if currency == "USD" else f"{base:.2f} {currency}",
                "total": fmt_usd(total) if currency == "USD" else f"{total:.2f} {currency}",
                "total_raw": total,
                **pricing,
            },
            "validating_carrier": carriers.get(
                offer.get("validatingAirlineCodes", [""])[0],
                offer.get("validatingAirlineCodes", [""])[0]
            ),
            "booking_class": traveler_pricings[0].get("fareDetailsBySegment", [{}])[0].get("class", "") if traveler_pricings else "",
            "last_ticketing_date": offer.get("lastTicketingDate"),
            "seats_remaining": offer.get("numberOfBookableSeats"),
        })

    return {
        "total_offers": len(offers),
        "offers": offers,
        "carriers": carriers,
    }


def _format_comparison(offers: list) -> list:
    """Build side-by-side comparison rows from formatted offers."""
    rows = []
    for i, offer in enumerate(offers):
        outbound = offer.get("itineraries", [{}])[0] if offer.get("itineraries") else {}
        inbound = offer["itineraries"][1] if len(offer.get("itineraries", [])) > 1 else None

        out_segs = outbound.get("segments", [])
        origin = out_segs[0]["departure_airport"] if out_segs else "N/A"
        dest = out_segs[-1]["arrival_airport"] if out_segs else "N/A"
        dep_time = out_segs[0]["departure_time"] if out_segs else "N/A"
        arr_time = out_segs[-1]["arrival_time"] if out_segs else "N/A"

        row = {
            "option": i + 1,
            "offer_id": offer.get("offer_id"),
            "airline": offer.get("validating_carrier"),
            "route": f"{origin} -> {dest}",
            "departure": dep_time,
            "arrival": arr_time,
            "outbound_duration": outbound.get("duration", "N/A"),
            "outbound_stops": outbound.get("stops", 0),
            "cabin": offer.get("cabin_class"),
            "net_price": offer["price"].get("net_usd"),
            "client_price": offer["price"].get("client_price_usd"),
            "seats_remaining": offer.get("seats_remaining"),
            "last_ticketing": offer.get("last_ticketing_date"),
        }

        if inbound:
            in_segs = inbound.get("segments", [])
            row["return_departure"] = in_segs[0]["departure_time"] if in_segs else "N/A"
            row["return_arrival"] = in_segs[-1]["arrival_time"] if in_segs else "N/A"
            row["return_duration"] = inbound.get("duration", "N/A")
            row["return_stops"] = inbound.get("stops", 0)

        rows.append(row)

    return rows


# ============================================================================
# TOOL REGISTRATION
# ============================================================================

def register_flight_search_tools(mcp: FastMCP):
    """Register flight search tools with the MCP server."""

    @mcp.tool(
        name="search_flights",
        annotations={"title": "Search Flights (Amadeus)", "readOnlyHint": True},
    )
    async def search_flights(
        origin: str = Field(..., description="Origin airport IATA code (e.g. 'LAX', 'DEN', 'JFK')"),
        destination: str = Field(..., description="Destination airport IATA code (e.g. 'NRT', 'LHR', 'CDG')"),
        departure_date: str = Field(..., description="Departure date (YYYY-MM-DD)"),
        return_date: Optional[str] = Field(None, description="Return date (YYYY-MM-DD) for round-trip. Omit for one-way."),
        adults: int = Field(1, description="Number of adult passengers (1-9)"),
        children: int = Field(0, description="Number of child passengers 2-11 (0-8)"),
        infants: int = Field(0, description="Number of infant passengers under 2 (0-4)"),
        cabin_class: Optional[str] = Field(
            None,
            description="Cabin class filter: ECONOMY, PREMIUM_ECONOMY, BUSINESS, FIRST. Omit for all classes.",
        ),
        nonstop_only: bool = Field(False, description="Only return non-stop flights"),
        max_results: int = Field(10, description="Maximum number of offers to return (1-250)"),
        max_price: Optional[int] = Field(None, description="Maximum price per traveler in USD"),
        currency: str = Field("USD", description="Price currency code (default USD)"),
    ) -> str:
        """Search for flight offers via the Amadeus API.

        Returns flight options with pricing, stops, duration, cabin class, and carrier info.
        Prices include both net cost and client price with D2M markup applied.
        Use verify_flight_price to confirm pricing before quoting.
        """
        try:
            params = {
                "originLocationCode": origin.upper(),
                "destinationLocationCode": destination.upper(),
                "departureDate": departure_date,
                "adults": min(adults, 9),
                "max": min(max_results, 250),
                "currencyCode": currency.upper(),
            }

            if return_date:
                params["returnDate"] = return_date
            if children > 0:
                params["children"] = min(children, 8)
            if infants > 0:
                params["infants"] = min(infants, 4)
            if cabin_class:
                params["travelClass"] = cabin_class.upper()
            if nonstop_only:
                params["nonStop"] = "true"
            if max_price:
                params["maxPrice"] = max_price

            logger.info(f"Amadeus flight search: {origin} -> {destination} on {departure_date}")
            resp = requests.get(
                f"{AmadeusConfig.BASE_URL}/v2/shopping/flight-offers",
                headers=_auth_headers(),
                params=params,
                timeout=30,
            )

            if resp.status_code != 200:
                error_detail = resp.text[:1000]
                try:
                    error_json = resp.json()
                    errors = error_json.get("errors", [])
                    if errors:
                        error_detail = "; ".join(e.get("detail", e.get("title", "")) for e in errors)
                except Exception:
                    pass
                return json.dumps({
                    "error": f"Amadeus API error {resp.status_code}",
                    "detail": error_detail,
                }, indent=2)

            result = _format_flight_offers(resp.json())
            result["search"] = {
                "origin": origin.upper(),
                "destination": destination.upper(),
                "departure_date": departure_date,
                "return_date": return_date,
                "adults": adults,
                "cabin_class": cabin_class,
                "nonstop_only": nonstop_only,
            }
            return json.dumps(result, indent=2)

        except ValueError as e:
            return json.dumps({"error": str(e), "type": "config_error"}, indent=2)
        except requests.RequestException as e:
            logger.error(f"Amadeus request failed: {e}")
            return json.dumps({"error": str(e), "type": "request_error"}, indent=2)
        except Exception as e:
            logger.error(f"Flight search error: {e}")
            return json.dumps({"error": str(e), "type": "search_error"}, indent=2)

    @mcp.tool(
        name="verify_flight_price",
        annotations={"title": "Verify Flight Price (Amadeus)", "readOnlyHint": True},
    )
    async def verify_flight_price(
        flight_offer_json: str = Field(
            ...,
            description="JSON string of the flight offer object from search_flights results "
            "(the full offer object including itineraries and price).",
        ),
    ) -> str:
        """Re-verify flight offer pricing before quoting to a client.

        Flight prices are volatile. Always verify before creating a client quote.
        Pass the complete offer object from search_flights results.
        Returns confirmed pricing or updated price if changed.
        """
        try:
            offer = json.loads(flight_offer_json)

            payload = {
                "data": {
                    "type": "flight-offers-pricing",
                    "flightOffers": [offer],
                }
            }

            logger.info(f"Amadeus price verification for offer {offer.get('id', 'unknown')}")
            resp = requests.post(
                f"{AmadeusConfig.BASE_URL}/v1/shopping/flight-offers/pricing",
                headers=_auth_headers(),
                json=payload,
                timeout=30,
            )

            if resp.status_code != 200:
                error_detail = resp.text[:1000]
                try:
                    error_json = resp.json()
                    errors = error_json.get("errors", [])
                    if errors:
                        error_detail = "; ".join(e.get("detail", e.get("title", "")) for e in errors)
                except Exception:
                    pass
                return json.dumps({
                    "error": f"Amadeus pricing error {resp.status_code}",
                    "detail": error_detail,
                }, indent=2)

            data = resp.json().get("data", {})
            flight_offers = data.get("flightOffers", [])

            if not flight_offers:
                return json.dumps({"error": "No pricing returned — offer may have expired"}, indent=2)

            verified = flight_offers[0]
            price = verified.get("price", {})
            currency = price.get("currency", "USD")
            total = float(price.get("grandTotal", price.get("total", 0)))
            base = float(price.get("base", 0))

            pricing = _apply_markup(total, currency)

            # Fee breakdown
            fees = []
            for fee in price.get("fees", []):
                fees.append({
                    "type": fee.get("type"),
                    "amount": fee.get("amount"),
                })

            return json.dumps({
                "status": "verified",
                "offer_id": verified.get("id"),
                "price": {
                    "currency": currency,
                    "base": fmt_usd(base) if currency == "USD" else f"{base:.2f} {currency}",
                    "total": fmt_usd(total) if currency == "USD" else f"{total:.2f} {currency}",
                    **pricing,
                    "fees": fees,
                },
                "last_ticketing_date": verified.get("lastTicketingDate"),
                "seats_remaining": verified.get("numberOfBookableSeats"),
            }, indent=2)

        except json.JSONDecodeError as e:
            return json.dumps({"error": f"Invalid JSON: {str(e)}"}, indent=2)
        except ValueError as e:
            return json.dumps({"error": str(e), "type": "config_error"}, indent=2)
        except requests.RequestException as e:
            logger.error(f"Amadeus pricing failed: {e}")
            return json.dumps({"error": str(e), "type": "request_error"}, indent=2)
        except Exception as e:
            logger.error(f"Price verification error: {e}")
            return json.dumps({"error": str(e), "type": "pricing_error"}, indent=2)

    @mcp.tool(
        name="search_airports",
        annotations={"title": "Search Airports/Cities (Amadeus)", "readOnlyHint": True},
    )
    async def search_airports(
        keyword: str = Field(..., description="City or airport name to search (e.g. 'Tokyo', 'Denver', 'Charles de Gaulle')"),
        subtype: str = Field("AIRPORT,CITY", description="Type filter: AIRPORT, CITY, or both (comma-separated)"),
    ) -> str:
        """Search for airport and city IATA codes by name.

        Use this to find the correct IATA code before calling search_flights.
        Returns matching airports/cities with codes, names, and locations.
        """
        try:
            params = {
                "subType": subtype,
                "keyword": keyword,
                "page[limit]": 10,
                "view": "LIGHT",
            }

            logger.info(f"Amadeus airport search: '{keyword}'")
            resp = requests.get(
                f"{AmadeusConfig.BASE_URL}/v1/reference-data/locations",
                headers=_auth_headers(),
                params=params,
                timeout=15,
            )

            if resp.status_code != 200:
                return json.dumps({
                    "error": f"Amadeus API error {resp.status_code}",
                    "detail": resp.text[:500],
                }, indent=2)

            raw = resp.json().get("data", [])
            results = []
            for loc in raw:
                results.append({
                    "iata_code": loc.get("iataCode"),
                    "name": loc.get("name"),
                    "type": loc.get("subType"),
                    "city": loc.get("address", {}).get("cityName"),
                    "country": loc.get("address", {}).get("countryCode"),
                })

            return json.dumps({
                "keyword": keyword,
                "total": len(results),
                "locations": results,
            }, indent=2)

        except ValueError as e:
            return json.dumps({"error": str(e), "type": "config_error"}, indent=2)
        except requests.RequestException as e:
            logger.error(f"Amadeus airport search failed: {e}")
            return json.dumps({"error": str(e), "type": "request_error"}, indent=2)
        except Exception as e:
            logger.error(f"Airport search error: {e}")
            return json.dumps({"error": str(e), "type": "search_error"}, indent=2)

    @mcp.tool(
        name="compare_flights",
        annotations={"title": "Compare Flight Offers Side-by-Side", "readOnlyHint": True},
    )
    async def compare_flights(
        offers_json: str = Field(
            ...,
            description="JSON string — array of flight offer objects from search_flights results. "
            "Include 2-5 offers you want to compare side by side.",
        ),
    ) -> str:
        """Compare 2-5 flight offers side-by-side.

        Pass an array of offer objects from search_flights results.
        Returns a structured comparison table with route, timing, stops,
        cabin class, net price, and client price for each option.
        """
        try:
            offers = json.loads(offers_json)
            if not isinstance(offers, list) or len(offers) < 2:
                return json.dumps({"error": "Provide an array of 2-5 flight offers to compare"}, indent=2)

            offers = offers[:5]
            comparison = _format_comparison(offers)

            # Find best values
            prices = [row["price"].get("client_raw", float("inf")) if isinstance(row.get("price"), dict)
                      else float("inf") for row in offers]
            # Use the comparison rows instead
            best_price_idx = 0
            best_price = float("inf")
            fewest_stops = float("inf")
            fewest_stops_idx = 0

            for i, row in enumerate(comparison):
                # Parse client price
                price_str = row.get("client_price", "$999999")
                price_val = float(price_str.replace("$", "").replace(",", "")) if price_str.startswith("$") else float("inf")
                if price_val < best_price:
                    best_price = price_val
                    best_price_idx = i

                stops = row.get("outbound_stops", 99)
                if stops < fewest_stops:
                    fewest_stops = stops
                    fewest_stops_idx = i

            for i, row in enumerate(comparison):
                row["badges"] = []
                if i == best_price_idx:
                    row["badges"].append("BEST PRICE")
                if i == fewest_stops_idx:
                    row["badges"].append("FEWEST STOPS")

            return json.dumps({
                "comparison": comparison,
                "total_options": len(comparison),
                "recommendation": {
                    "best_price": comparison[best_price_idx]["option"],
                    "fewest_stops": comparison[fewest_stops_idx]["option"],
                },
            }, indent=2)

        except json.JSONDecodeError as e:
            return json.dumps({"error": f"Invalid JSON: {str(e)}"}, indent=2)
        except Exception as e:
            logger.error(f"Flight comparison error: {e}")
            return json.dumps({"error": str(e), "type": "compare_error"}, indent=2)

    # ====================================================================
    # PDF RENDERING + EMAIL QUOTE TOOLS
    # ====================================================================

    @mcp.tool(
        name="render_flight_quote_pdf",
        annotations={"title": "Render Flight Quote PDF (D2M Branded)", "readOnlyHint": False},
    )
    async def render_flight_quote_pdf(
        client_name: str = Field(..., description="Client name for the quote"),
        origin_city: str = Field(..., description="Origin city name (e.g. 'Denver')"),
        destination_city: str = Field(..., description="Destination city name (e.g. 'Tokyo')"),
        departure_date: str = Field(..., description="Departure date (human-readable, e.g. 'April 1, 2026')"),
        return_date: Optional[str] = Field(None, description="Return date (human-readable). Omit for one-way."),
        travelers: str = Field("2", description="Number of travelers (as string for display)"),
        flights_json: str = Field(
            ...,
            description="JSON array of flight option objects. Each must have: "
            "option (int), airline (str), cabin (str), client_price (str like '$1,234.00'), "
            "badges (array of str), seats_remaining (int or null), "
            "legs (array of {label, segments: [{dep_time, dep_airport, arr_time, arr_airport, "
            "duration, stops, flight_num}]})",
        ),
        comparison_json: Optional[str] = Field(
            None,
            description="JSON array of comparison row objects for the table. Each: "
            "option, airline, departure, arrival, duration, stops, cabin, client_price, is_pick (bool)",
        ),
        recommendation: Optional[str] = Field(
            None,
            description="Recommendation text paragraph for the client",
        ),
        notes: Optional[str] = Field(
            None,
            description="Important notes (e.g. 'Prices valid for 24 hours. Fares subject to change.')",
        ),
        output_filename: Optional[str] = Field(
            None,
            description="Output PDF filename. Defaults to ClientName_Route_MonYYYY.pdf",
        ),
    ) -> str:
        """Render a branded D2M flight quote PDF from flight comparison data.

        Generates a professional PDF with flight option cards, comparison table,
        recommendation, and D2M branding. Uses the flight_quote.html.j2 template.
        Returns the path to the generated PDF.
        """
        try:
            flights = json.loads(flights_json)
            comparison = json.loads(comparison_json) if comparison_json else None

            # Build output filename
            if not output_filename:
                safe_client = client_name.replace(" ", "_")
                safe_route = f"{origin_city}_{destination_city}".replace(" ", "_")
                month_year = datetime.now().strftime("%b%Y")
                output_filename = f"{safe_client}_{safe_route}_{month_year}.pdf"

            output_dir = THUNDERBIRD_DIR / "output"
            output_dir.mkdir(parents=True, exist_ok=True)
            pdf_path = output_dir / output_filename
            html_path = output_dir / output_filename.replace(".pdf", ".html")

            # Load and render Jinja2 template
            env = Environment(loader=FileSystemLoader(str(THUNDERBIRD_DIR / "templates")))
            template = env.get_template("flight_quote.html.j2")

            context = {
                "client_name": client_name,
                "origin_city": origin_city,
                "destination_city": destination_city,
                "departure_date": departure_date,
                "return_date": return_date,
                "travelers": travelers,
                "prepared_date": datetime.now().strftime("%B %d, %Y"),
                "flights": flights,
                "comparison": comparison,
                "recommendation": recommendation,
                "notes": notes or "Prices valid for 24 hours from quote date. Fares and availability subject to change. Taxes and fees included.",
            }

            html_content = template.render(context)

            # Save HTML for reference
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            # Render PDF via WeasyPrint
            HTML(string=html_content, base_url=str(THUNDERBIRD_DIR)).write_pdf(str(pdf_path))

            logger.info(f"Flight quote PDF rendered: {pdf_path}")
            return json.dumps({
                "status": "success",
                "pdf_path": str(pdf_path),
                "html_path": str(html_path),
                "client_name": client_name,
                "route": f"{origin_city} -> {destination_city}",
                "options_count": len(flights),
            }, indent=2)

        except json.JSONDecodeError as e:
            return json.dumps({"error": f"Invalid JSON: {str(e)}"}, indent=2)
        except Exception as e:
            logger.error(f"Flight quote PDF render error: {e}")
            return json.dumps({"error": str(e), "type": "render_error"}, indent=2)

    @mcp.tool(
        name="email_flight_quote",
        annotations={"title": "Email Flight Quote to Client", "readOnlyHint": False},
    )
    async def email_flight_quote(
        to_email: str = Field(..., description="Client email address"),
        client_name: str = Field(..., description="Client name for greeting"),
        origin_city: str = Field(..., description="Origin city"),
        destination_city: str = Field(..., description="Destination city"),
        departure_date: str = Field(..., description="Departure date (human-readable)"),
        return_date: Optional[str] = Field(None, description="Return date (human-readable)"),
        summary_json: str = Field(
            ...,
            description="JSON array of flight summary objects for the email body. Each: "
            "option (int), airline (str), departure (str), arrival (str), "
            "stops (int), cabin (str), client_price (str)",
        ),
        recommendation: Optional[str] = Field(None, description="Brief recommendation text"),
        pdf_path: Optional[str] = Field(
            None,
            description="Path to the flight quote PDF to attach. "
            "Use render_flight_quote_pdf first to generate it.",
        ),
        subject: Optional[str] = Field(
            None,
            description="Custom email subject. Defaults to 'Your Flight Options: City to City'",
        ),
    ) -> str:
        """Create a Gmail draft with flight quote summary and optional PDF attachment.

        Generates a branded HTML email body with a flight options summary table
        and attaches the PDF quote if provided. Creates a draft in Gmail
        (does NOT send automatically — you review and send).
        """
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build

            summary = json.loads(summary_json)

            # Build email subject
            if not subject:
                subject = f"Your Flight Options: {origin_city} to {destination_city}"

            # Build HTML email body
            route_str = f"{origin_city} to {destination_city}"
            dates_str = departure_date
            if return_date:
                dates_str += f" — returning {return_date}"

            rows_html = ""
            for opt in summary:
                stops_text = "Nonstop" if opt.get("stops", 0) == 0 else f"{opt['stops']} stop{'s' if opt['stops'] > 1 else ''}"
                rows_html += f"""
                <tr>
                    <td style="padding:10px 12px;border-bottom:1px solid #e9ecef;font-weight:600;">Option {opt.get('option', '')}</td>
                    <td style="padding:10px 12px;border-bottom:1px solid #e9ecef;">{opt.get('airline', '')}</td>
                    <td style="padding:10px 12px;border-bottom:1px solid #e9ecef;">{opt.get('departure', '')}</td>
                    <td style="padding:10px 12px;border-bottom:1px solid #e9ecef;">{opt.get('arrival', '')}</td>
                    <td style="padding:10px 12px;border-bottom:1px solid #e9ecef;">{stops_text}</td>
                    <td style="padding:10px 12px;border-bottom:1px solid #e9ecef;">{opt.get('cabin', '')}</td>
                    <td style="padding:10px 12px;border-bottom:1px solid #e9ecef;font-weight:700;color:#0d1b2e;">{opt.get('client_price', '')}</td>
                </tr>"""

            rec_html = ""
            if recommendation:
                rec_html = f"""
                <div style="margin:25px 0;padding:20px;background:#0d1b2e;color:#ffffff;border-radius:6px;border-left:4px solid #c9a84c;">
                    <strong style="color:#e8c97a;">Our Recommendation:</strong><br>
                    <span style="font-size:0.95em;line-height:1.6;">{recommendation}</span>
                </div>"""

            attachment_note = ""
            if pdf_path:
                attachment_note = "<p style='font-size:0.9em;color:#8a9ab5;margin-top:15px;'>See the attached PDF for the full detailed comparison with flight times and booking details.</p>"

            html_body = f"""
            <div style="font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;max-width:700px;margin:0 auto;color:#2c3e50;">
                <div style="background:linear-gradient(135deg,#0d1b2e,#152540);color:#ffffff;padding:35px 30px;text-align:center;border-bottom:3px solid #c9a84c;">
                    <h2 style="margin:0 0 5px;font-weight:300;font-size:1.6em;">Flight Options</h2>
                    <div style="color:#e8c97a;font-size:1.2em;font-weight:600;">{route_str}</div>
                    <div style="color:#8a9ab5;margin-top:10px;font-size:0.9em;">{dates_str}</div>
                </div>

                <div style="padding:25px 30px;">
                    <p>Hi {client_name},</p>
                    <p style="margin:15px 0;">Here are the flight options I've put together for your trip. Take a look and let me know which one speaks to you — or if you'd like me to explore other options.</p>

                    <table style="width:100%;border-collapse:collapse;font-size:0.85em;margin:20px 0;">
                        <thead>
                            <tr style="background:#0d1b2e;color:#ffffff;">
                                <th style="padding:10px 12px;text-align:left;">Option</th>
                                <th style="padding:10px 12px;text-align:left;">Airline</th>
                                <th style="padding:10px 12px;text-align:left;">Depart</th>
                                <th style="padding:10px 12px;text-align:left;">Arrive</th>
                                <th style="padding:10px 12px;text-align:left;">Stops</th>
                                <th style="padding:10px 12px;text-align:left;">Cabin</th>
                                <th style="padding:10px 12px;text-align:left;">Price/pp</th>
                            </tr>
                        </thead>
                        <tbody>{rows_html}
                        </tbody>
                    </table>

                    {rec_html}
                    {attachment_note}

                    <p style="margin-top:25px;">Warmly,<br><strong>John Loucks</strong><br>Dreams2Memories Travel, LLC<br>
                    <a href="mailto:johnloucks3@gmail.com" style="color:#c9a84c;">johnloucks3@gmail.com</a> | (719) 291-0742</p>
                </div>

                <div style="background:#0d1b2e;color:#8a9ab5;padding:20px;text-align:center;font-size:0.8em;border-top:3px solid #c9a84c;">
                    Dreams2Memories Travel, LLC | Monument, CO
                </div>
            </div>"""

            # Create Gmail draft via service account
            creds_path = THUNDERBIRD_DIR / "credentials.json"
            if not creds_path.exists():
                return json.dumps({
                    "error": "Google service account credentials not found at ~/Thunderbird/credentials.json",
                }, indent=2)

            scopes = ["https://www.googleapis.com/auth/gmail.modify"]
            credentials = service_account.Credentials.from_service_account_file(
                str(creds_path), scopes=scopes
            )
            # Delegate to John's Gmail account
            delegated = credentials.with_subject("johnloucks3@gmail.com")
            gmail_service = build("gmail", "v1", credentials=delegated)

            # Build MIME message
            msg = MIMEMultipart()
            msg["to"] = to_email
            msg["from"] = "johnloucks3@gmail.com"
            msg["subject"] = subject
            msg.attach(MIMEText(html_body, "html"))

            # Attach PDF if provided
            if pdf_path and Path(pdf_path).exists():
                with open(pdf_path, "rb") as f:
                    pdf_data = f.read()
                pdf_attachment = MIMEApplication(pdf_data, _subtype="pdf")
                pdf_attachment.add_header(
                    "Content-Disposition", "attachment",
                    filename=Path(pdf_path).name,
                )
                msg.attach(pdf_attachment)

            # Encode and create draft
            raw_msg = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
            draft = gmail_service.users().drafts().create(
                userId="me",
                body={"message": {"raw": raw_msg}},
            ).execute()

            draft_id = draft.get("id", "unknown")
            logger.info(f"Gmail draft created: {draft_id} for {to_email}")

            return json.dumps({
                "status": "draft_created",
                "draft_id": draft_id,
                "to": to_email,
                "subject": subject,
                "has_pdf_attachment": bool(pdf_path and Path(pdf_path).exists()),
                "message": f"Gmail draft ready for review. Open Gmail to review and send.",
            }, indent=2)

        except json.JSONDecodeError as e:
            return json.dumps({"error": f"Invalid JSON: {str(e)}"}, indent=2)
        except Exception as e:
            logger.error(f"Email flight quote error: {e}")
            return json.dumps({"error": str(e), "type": "email_error"}, indent=2)

    logger.info("Flight search tools registered (Amadeus)")

    # ====================================================================
    # FLIGHTAWARE AEROAPI TOOLS
    # ====================================================================

    def _load_flightaware_key() -> str:
        """Load FlightAware API key from config file or class."""
        if FlightAwareConfig.API_KEY:
            return FlightAwareConfig.API_KEY

        cred_file = THUNDERBIRD_DIR / "flightaware_credentials.json"
        if cred_file.exists():
            with open(cred_file, encoding="utf-8") as f:
                creds = json.load(f)
            FlightAwareConfig.API_KEY = creds.get("api_key", "")
            if creds.get("base_url"):
                FlightAwareConfig.BASE_URL = creds["base_url"]
            return FlightAwareConfig.API_KEY

        raise ValueError(
            "FlightAware API key not configured. "
            "Create ~/Thunderbird/flightaware_credentials.json with "
            '{"api_key": "YOUR_KEY"}'
        )

    def _fa_headers() -> dict:
        """Build FlightAware request headers."""
        return {
            "x-apikey": _load_flightaware_key(),
            "Accept": "application/json",
        }

    @mcp.tool(
        name="track_flight_flightaware",
        annotations={"title": "Track Flight (FlightAware)", "readOnlyHint": True},
    )
    async def track_flight_flightaware(
        flight_id: str = Field(..., description="Flight identifier — ICAO (e.g. 'UAL1234') or IATA (e.g. 'UA1234')"),
    ) -> str:
        """Track a specific flight using FlightAware AeroAPI.

        Returns real-time flight status including position, altitude, speed,
        departure/arrival times, gate info, and delays.
        """
        try:
            url = f"{FlightAwareConfig.BASE_URL}/flights/{flight_id}"
            resp = requests.get(url, headers=_fa_headers(), timeout=15)

            if resp.status_code != 200:
                return json.dumps({
                    "error": f"FlightAware API error {resp.status_code}",
                    "detail": resp.text[:500],
                }, indent=2)

            data = resp.json()
            flights = data.get("flights", [])

            results = []
            for f in flights[:5]:
                results.append({
                    "ident": f.get("ident"),
                    "ident_iata": f.get("ident_iata"),
                    "operator": f.get("operator"),
                    "aircraft_type": f.get("aircraft_type"),
                    "status": f.get("status"),
                    "origin": {
                        "code": f.get("origin", {}).get("code"),
                        "name": f.get("origin", {}).get("name"),
                        "city": f.get("origin", {}).get("city"),
                        "gate": f.get("gate_origin"),
                        "terminal": f.get("terminal_origin"),
                    },
                    "destination": {
                        "code": f.get("destination", {}).get("code"),
                        "name": f.get("destination", {}).get("name"),
                        "city": f.get("destination", {}).get("city"),
                        "gate": f.get("gate_destination"),
                        "terminal": f.get("terminal_destination"),
                    },
                    "departure_scheduled": f.get("scheduled_out"),
                    "departure_estimated": f.get("estimated_out"),
                    "departure_actual": f.get("actual_out"),
                    "arrival_scheduled": f.get("scheduled_in"),
                    "arrival_estimated": f.get("estimated_in"),
                    "arrival_actual": f.get("actual_in"),
                    "progress_percent": f.get("progress_percent"),
                    "route_distance_nm": f.get("route_distance"),
                    "filed_altitude": f.get("filed_altitude"),
                    "last_position": f.get("last_position"),
                })

            return json.dumps({
                "flight_id": flight_id,
                "total_results": len(results),
                "flights": results,
            }, indent=2)

        except ValueError as e:
            return json.dumps({"error": str(e), "type": "config_error"}, indent=2)
        except requests.RequestException as e:
            return json.dumps({"error": str(e), "type": "request_error"}, indent=2)
        except Exception as e:
            logger.error(f"FlightAware tracking error: {e}")
            return json.dumps({"error": str(e), "type": "tracking_error"}, indent=2)

    @mcp.tool(
        name="search_flights_flightaware",
        annotations={"title": "Search Flight Schedule (FlightAware)", "readOnlyHint": True},
    )
    async def search_flights_flightaware(
        origin: str = Field(..., description="Origin airport ICAO code (e.g. 'KDEN') or IATA (e.g. 'DEN')"),
        destination: str = Field(..., description="Destination airport ICAO code or IATA"),
        departure_date: Optional[str] = Field(None, description="Date filter YYYY-MM-DD (searches ±12h). Defaults to today."),
        airline: Optional[str] = Field(None, description="Airline ICAO code filter (e.g. 'UAL' for United)"),
        max_results: int = Field(15, description="Maximum results (1-50)"),
    ) -> str:
        """Search for flights between two airports via FlightAware.

        Returns scheduled and en-route flights with status, times, and aircraft.
        Useful for finding flight numbers, checking schedules, and monitoring routes.
        """
        try:
            params = {"max_pages": 1}
            if airline:
                params["airline"] = airline.upper()

            # Build date range if provided
            if departure_date:
                params["start"] = f"{departure_date}T00:00:00Z"
                params["end"] = f"{departure_date}T23:59:59Z"

            origin_code = origin.upper()
            dest_code = destination.upper()
            url = f"{FlightAwareConfig.BASE_URL}/airports/{origin_code}/flights/to/{dest_code}"

            resp = requests.get(url, headers=_fa_headers(), params=params, timeout=15)

            if resp.status_code != 200:
                return json.dumps({
                    "error": f"FlightAware API error {resp.status_code}",
                    "detail": resp.text[:500],
                }, indent=2)

            data = resp.json()
            flights = data.get("scheduled_arrivals", data.get("flights", []))

            results = []
            for f in flights[:max_results]:
                results.append({
                    "ident": f.get("ident"),
                    "ident_iata": f.get("ident_iata"),
                    "operator": f.get("operator"),
                    "aircraft_type": f.get("aircraft_type"),
                    "status": f.get("status"),
                    "departure_scheduled": f.get("scheduled_out") or f.get("scheduled_off"),
                    "arrival_scheduled": f.get("scheduled_in") or f.get("scheduled_on"),
                    "departure_actual": f.get("actual_out"),
                    "arrival_actual": f.get("actual_in"),
                    "filed_altitude": f.get("filed_altitude"),
                    "route_distance_nm": f.get("route_distance"),
                })

            return json.dumps({
                "origin": origin_code,
                "destination": dest_code,
                "date": departure_date or "today",
                "total_results": len(results),
                "flights": results,
            }, indent=2)

        except ValueError as e:
            return json.dumps({"error": str(e), "type": "config_error"}, indent=2)
        except requests.RequestException as e:
            return json.dumps({"error": str(e), "type": "request_error"}, indent=2)
        except Exception as e:
            logger.error(f"FlightAware search error: {e}")
            return json.dumps({"error": str(e), "type": "search_error"}, indent=2)

    @mcp.tool(
        name="get_airport_info_flightaware",
        annotations={"title": "Airport Info (FlightAware)", "readOnlyHint": True},
    )
    async def get_airport_info_flightaware(
        airport_code: str = Field(..., description="Airport ICAO (e.g. 'KDEN') or IATA (e.g. 'DEN') code"),
    ) -> str:
        """Get detailed airport information from FlightAware.

        Returns airport name, city, timezone, coordinates, delays, and weather.
        """
        try:
            code = airport_code.upper()
            url = f"{FlightAwareConfig.BASE_URL}/airports/{code}"
            resp = requests.get(url, headers=_fa_headers(), timeout=15)

            if resp.status_code != 200:
                return json.dumps({
                    "error": f"FlightAware API error {resp.status_code}",
                    "detail": resp.text[:500],
                }, indent=2)

            data = resp.json()
            return json.dumps({
                "airport_code": code,
                "name": data.get("name"),
                "city": data.get("city"),
                "state": data.get("state"),
                "country": data.get("country_code"),
                "timezone": data.get("timezone"),
                "latitude": data.get("latitude"),
                "longitude": data.get("longitude"),
                "elevation_ft": data.get("elevation"),
                "wiki_url": data.get("wiki_url"),
                "delays": data.get("airport_delays_list"),
            }, indent=2)

        except ValueError as e:
            return json.dumps({"error": str(e), "type": "config_error"}, indent=2)
        except requests.RequestException as e:
            return json.dumps({"error": str(e), "type": "request_error"}, indent=2)
        except Exception as e:
            logger.error(f"FlightAware airport info error: {e}")
            return json.dumps({"error": str(e), "type": "airport_error"}, indent=2)

    logger.info("FlightAware AeroAPI tools registered")

    # ====================================================================
    # FLIGHTRADAR24 TOOLS (unofficial lib — no API key needed)
    # ====================================================================

    if FR24_AVAILABLE:
        fr24 = FlightRadar24API()

        @mcp.tool(
            name="track_flight_fr24",
            annotations={"title": "Track Flight (FlightRadar24)", "readOnlyHint": True},
        )
        async def track_flight_fr24(
            flight_number: str = Field(..., description="Flight number to search (e.g. 'UA1234', 'BA456')"),
        ) -> str:
            """Track a live flight using FlightRadar24 real-time data.

            Returns current position, altitude, speed, aircraft type, and route.
            Free, no API key required. Best for live in-air tracking.
            """
            try:
                search = fr24.search(flight_number.upper())
                live_flights = search.get("live", [])
                schedule_flights = search.get("schedule", [])

                if not live_flights and not schedule_flights:
                    return json.dumps({
                        "flight_number": flight_number,
                        "status": "not_found",
                        "message": f"No results for '{flight_number}'. Try IATA format (e.g. UA1234).",
                    }, indent=2)

                results = {"flight_number": flight_number, "live": [], "scheduled": []}

                for lf in live_flights[:5]:
                    detail = lf.get("detail", {})
                    results["live"].append({
                        "id": lf.get("id"),
                        "label": lf.get("label"),
                        "lat": detail.get("lat"),
                        "lon": detail.get("lon"),
                        "alt": detail.get("alt"),
                        "speed": detail.get("spd"),
                        "heading": detail.get("hd"),
                        "aircraft": detail.get("ac_type"),
                        "origin": detail.get("orig"),
                        "destination": detail.get("dest"),
                        "route": detail.get("route"),
                    })

                for sf in schedule_flights[:5]:
                    detail = sf.get("detail", {})
                    results["scheduled"].append({
                        "id": sf.get("id"),
                        "label": sf.get("label"),
                        "origin": detail.get("orig"),
                        "destination": detail.get("dest"),
                        "schd_from": detail.get("schd_from"),
                        "schd_to": detail.get("schd_to"),
                    })

                return json.dumps(results, indent=2)

            except Exception as e:
                logger.error(f"FR24 tracking error: {e}")
                return json.dumps({"error": str(e), "type": "fr24_error"}, indent=2)

        @mcp.tool(
            name="get_airport_flights_fr24",
            annotations={"title": "Airport Live Flights (FlightRadar24)", "readOnlyHint": True},
        )
        async def get_airport_flights_fr24(
            airport_code: str = Field(..., description="Airport IATA code (e.g. 'DEN', 'JFK', 'LHR')"),
        ) -> str:
            """Get live arrivals and departures at an airport via FlightRadar24.

            Returns current inbound and outbound flights with real-time status.
            Free, no API key required.
            """
            try:
                airport = fr24.get_airport(airport_code.upper())
                details = fr24.get_airport_details(airport_code.upper())

                arrivals = details.get("airport", {}).get("pluginData", {}).get("schedule", {}).get("arrivals", {}).get("data", [])
                departures = details.get("airport", {}).get("pluginData", {}).get("schedule", {}).get("departures", {}).get("data", [])

                result = {
                    "airport": airport_code.upper(),
                    "arrivals": [],
                    "departures": [],
                }

                for arr in arrivals[:15]:
                    flight = arr.get("flight", {})
                    result["arrivals"].append({
                        "flight": flight.get("identification", {}).get("number", {}).get("default"),
                        "airline": flight.get("airline", {}).get("name"),
                        "origin": flight.get("airport", {}).get("origin", {}).get("code", {}).get("iata"),
                        "status": flight.get("status", {}).get("text"),
                        "scheduled": flight.get("time", {}).get("scheduled", {}).get("arrival"),
                        "estimated": flight.get("time", {}).get("estimated", {}).get("arrival"),
                        "aircraft": flight.get("aircraft", {}).get("model", {}).get("text"),
                    })

                for dep in departures[:15]:
                    flight = dep.get("flight", {})
                    result["departures"].append({
                        "flight": flight.get("identification", {}).get("number", {}).get("default"),
                        "airline": flight.get("airline", {}).get("name"),
                        "destination": flight.get("airport", {}).get("destination", {}).get("code", {}).get("iata"),
                        "status": flight.get("status", {}).get("text"),
                        "scheduled": flight.get("time", {}).get("scheduled", {}).get("departure"),
                        "estimated": flight.get("time", {}).get("estimated", {}).get("departure"),
                        "aircraft": flight.get("aircraft", {}).get("model", {}).get("text"),
                    })

                return json.dumps(result, indent=2)

            except Exception as e:
                logger.error(f"FR24 airport flights error: {e}")
                return json.dumps({"error": str(e), "type": "fr24_error"}, indent=2)

        @mcp.tool(
            name="get_most_tracked_fr24",
            annotations={"title": "Most Tracked Flights (FlightRadar24)", "readOnlyHint": True},
        )
        async def get_most_tracked_fr24() -> str:
            """Get the most tracked flights on FlightRadar24 right now.

            Returns trending flights that people are watching — useful for
            identifying notable flights, disruptions, or interesting aircraft.
            """
            try:
                most_tracked = fr24.get_most_tracked()
                results = []
                for item in most_tracked.get("data", [])[:15]:
                    results.append({
                        "flight": item.get("flight_id"),
                        "callsign": item.get("callsign"),
                        "squawk": item.get("squawk"),
                        "clicks": item.get("clicks"),
                        "origin": item.get("from"),
                        "destination": item.get("to"),
                        "aircraft": item.get("aircraft"),
                    })
                return json.dumps({"most_tracked": results}, indent=2)
            except Exception as e:
                logger.error(f"FR24 most tracked error: {e}")
                return json.dumps({"error": str(e), "type": "fr24_error"}, indent=2)

        logger.info("FlightRadar24 tools registered")
    else:
        logger.warning("FlightRadar24 not available — pip install FlightRadarAPI")


# ============================================================================
# STANDALONE TEST
# ============================================================================

if __name__ == "__main__":
    async def test_auth():
        """Quick auth test against Amadeus."""
        try:
            token = _get_token()
            print(f"Auth OK — token: {token[:20]}...")
        except Exception as e:
            print(f"Auth error: {e}")

    import asyncio
    asyncio.run(test_auth())
