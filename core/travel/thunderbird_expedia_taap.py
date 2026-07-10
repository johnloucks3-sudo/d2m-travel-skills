"""
Dreams2Memories Expedia TAAP Hotel Search MCP Module
=====================================================

Hotel search via Expedia EPS Rapid API (TAAP — Travel Agent Affiliate Program):
- Search hotel availability by destination, dates, and occupancy
- Get specific room rates for a property
- Returns agent-net pricing with D2M commission markup

Integrates with: travel_mcp_server.py
Dependencies: requests

API Docs: https://developers.expediagroup.com/docs/products/rapid
TAAP Program: https://www.expedia.com/taap
"""

import json
import logging
import requests
from typing import Optional
from pathlib import Path

from pydantic import Field
from mcp.server.fastmcp import FastMCP

# ============================================================================
# CONFIGURATION
# ============================================================================

logger = logging.getLogger(__name__)

THUNDERBIRD_DIR = Path.home() / "Thunderbird"

# D2M pricing constants
EUR_TO_USD = 1.09
STANDARD_MARKUP = 0.25
PREMIUM_MARKUP = 0.22


class ExpediaTAAPConfig:
    """Expedia EPS Rapid API / TAAP configuration.

    Register at: https://www.expedia.com/taap
    API key/secret from: https://developers.expediagroup.com/
    """
    API_KEY = ""
    API_SECRET = ""
    TAAP_ACCOUNT_ID = ""
    BASE_URL = "https://api.ean.com/v3"


# ============================================================================
# CREDENTIAL LOADER
# ============================================================================

def _load_expedia_credentials() -> tuple[str, str, str]:
    """Load Expedia TAAP credentials from file."""
    if ExpediaTAAPConfig.API_KEY:
        return (
            ExpediaTAAPConfig.API_KEY,
            ExpediaTAAPConfig.API_SECRET,
            ExpediaTAAPConfig.TAAP_ACCOUNT_ID,
        )

    cred_file = THUNDERBIRD_DIR / "expedia_credentials.json"
    if cred_file.exists():
        with open(cred_file, encoding="utf-8") as f:
            creds = json.load(f)
        ExpediaTAAPConfig.API_KEY = creds.get("api_key", "")
        ExpediaTAAPConfig.API_SECRET = creds.get("api_secret", "")
        ExpediaTAAPConfig.TAAP_ACCOUNT_ID = creds.get("taap_account_id", "")
        if creds.get("base_url"):
            ExpediaTAAPConfig.BASE_URL = creds["base_url"]
        return (
            ExpediaTAAPConfig.API_KEY,
            ExpediaTAAPConfig.API_SECRET,
            ExpediaTAAPConfig.TAAP_ACCOUNT_ID,
        )

    raise ValueError(
        "Expedia TAAP credentials not configured. "
        "Create ~/Thunderbird/expedia_credentials.json with "
        '{"api_key": "YOUR_KEY", "api_secret": "YOUR_SECRET", "taap_account_id": "YOUR_ACCOUNT_ID"}'
    )


# ============================================================================
# HELPERS
# ============================================================================

def _auth_headers() -> dict:
    """Build EPS Rapid API authentication headers."""
    api_key, api_secret, taap_account_id = _load_expedia_credentials()
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if taap_account_id:
        headers["Customer"] = taap_account_id
    return headers, (api_key, api_secret)


def _to_usd(amount: float, currency: str) -> float:
    """Convert amount to USD."""
    if currency.upper() == "EUR":
        return amount * EUR_TO_USD
    return float(amount)


def fmt_usd(amount) -> str:
    """Format numeric amount as USD string."""
    try:
        return f"${float(amount):,.2f}"
    except (ValueError, TypeError):
        return str(amount)


def _apply_markup(net_amount: float, currency: str = "USD", markup: float = STANDARD_MARKUP) -> dict:
    """Apply D2M markup to net price."""
    net_usd = _to_usd(net_amount, currency)
    client_price = net_usd * (1 + markup)
    return {
        "net_usd": fmt_usd(net_usd),
        "markup_pct": f"{markup * 100:.0f}%",
        "client_price_usd": fmt_usd(client_price),
        "net_raw": round(net_usd, 2),
        "client_raw": round(client_price, 2),
    }


def _stub_credentials_error(message: str) -> str:
    """Return a structured error for unconfigured credentials."""
    return json.dumps({
        "status": "credentials_required",
        "provider": "Expedia TAAP (EPS Rapid)",
        "message": message,
        "action": "Add credentials to ~/Thunderbird/expedia_credentials.json",
    })


def _extract_room_rates(rooms: list, currency: str) -> list:
    """Extract and format room rate summaries from EPS Rapid response."""
    room_summaries = []
    for room in rooms[:6]:
        rates = room.get("rates", [])
        for rate in rates[:3]:
            price = rate.get("price", {})
            totals = price.get("totals", {})
            net_obj = totals.get("inclusive", totals.get("exclusive", {}))
            net_amount = float(net_obj.get("value", net_obj.get("amount", 0)) or 0)
            pricing = _apply_markup(net_amount, currency)

            room_summaries.append({
                "room_name": room.get("room_name", room.get("description", "")),
                "bed_type": room.get("bed_groups", [{}])[0].get("description", "") if room.get("bed_groups") else "",
                "max_occupancy": room.get("occupancy", {}).get("max_allowed", {}).get("total"),
                "net_price": pricing["net_usd"],
                "client_price": pricing["client_price_usd"],
                "markup_pct": pricing["markup_pct"],
                "rate_id": rate.get("id", rate.get("rate_id", "")),
                "refundable": rate.get("refundable", None),
                "payment_type": rate.get("payment_type", ""),
                "cancel_penalties": [
                    cp.get("description", "")
                    for cp in rate.get("cancel_penalties", [])[:2]
                ],
            })
    return room_summaries


# ============================================================================
# CORE IMPLEMENTATION (importable directly — used by search_taap_hotels tool
# and by other orchestration modules, e.g. thunderbird_client_proposal.py)
# ============================================================================

async def search_taap_hotels_impl(
    destination: str,
    checkin: str,
    checkout: str,
    rooms: int = 1,
    guests: int = 2,
) -> dict:
    """Search Expedia TAAP (EPS Rapid API) for hotel availability.

    Returns agent-net pricing with D2M markup applied (25% standard).
    Each result includes name, address, star rating, double/suite room prices,
    images, amenities, booking URL, rating, reviews, and sample review snippets.
    """
    try:
        api_key, api_secret, taap_account_id = _load_expedia_credentials()
    except ValueError as e:
        return json.loads(_stub_credentials_error(str(e)))

    if not api_key:
        return json.loads(_stub_credentials_error(
            "API key is empty. Register at https://www.expedia.com/taap and "
            "get API credentials at https://developers.expediagroup.com/"
        ))

    try:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if taap_account_id:
            headers["Customer"] = taap_account_id

        params = {
            "destination": destination,
            "checkin": checkin,
            "checkout": checkout,
            "occupancy": f"{guests}",
            "rooms": rooms,
            "currency": "USD",
            "language": "en-US",
            "country_code": "US",
            "include": ["unavailable_reason", "sale_scenario", "promotions"],
            "filter": "expedia_collect",
            "rate_option": "net_rates",
            "sort_type": "preferred",
            "limit": 25,
        }

        resp = requests.get(
            f"{ExpediaTAAPConfig.BASE_URL}/properties/availability",
            headers=headers,
            auth=(api_key, api_secret),
            params=params,
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()

        # EPS Rapid may return list or dict with "data" key
        properties = data if isinstance(data, list) else data.get("data", data.get("properties", []))
        results = []

        for prop in properties[:20]:
            property_id = prop.get("property_id", prop.get("id", ""))
            currency = prop.get("currency", "USD")

            # Extract pricing tiers
            rooms_data = prop.get("rooms", [])
            room_rates = _extract_room_rates(rooms_data, currency)

            # Find double and suite prices
            double_price = None
            suite_price = None
            for rr in room_rates:
                name_lower = rr.get("room_name", "").lower()
                if not double_price and any(k in name_lower for k in ["double", "queen", "standard", "deluxe", "classic"]):
                    double_price = rr.get("client_price")
                if not suite_price and "suite" in name_lower:
                    suite_price = rr.get("client_price")

            # Fallback: use first room rate
            if not double_price and room_rates:
                double_price = room_rates[0].get("client_price")

            # Images
            images = prop.get("images", [])
            image_url = images[0].get("url", "") if images else ""

            # Amenities
            amenities = [
                a.get("name", a) if isinstance(a, dict) else str(a)
                for a in prop.get("amenities", [])[:10]
            ]

            # Reviews
            reviews = prop.get("reviews", {})
            review_count = reviews.get("total", reviews.get("count", 0))
            rating = reviews.get("rating", reviews.get("score", prop.get("rating", prop.get("star_rating"))))

            sample_reviews = [
                r.get("text", r.get("summary", ""))[:150]
                for r in reviews.get("reviews", [])[:3]
                if r.get("text") or r.get("summary")
            ]

            # Booking URL
            booking_url = prop.get("booking_url", f"https://www.expedia.com/hotel-search?destination={destination}")

            results.append({
                "name": prop.get("name", ""),
                "address": prop.get("address", {}).get("line_1", prop.get("street_address", "")),
                "city": prop.get("address", {}).get("city", prop.get("city", destination)),
                "star_rating": prop.get("star_rating", prop.get("category", "")),
                "price_double_room": double_price or "See rates",
                "price_suite": suite_price or "See rates",
                "image_url": image_url,
                "amenities": amenities,
                "booking_url": booking_url,
                "rating": rating,
                "review_count": review_count,
                "sample_reviews": sample_reviews,
                "property_id": property_id,
                "room_rates": room_rates[:6],
                "source": "expedia_taap",
            })

        return {
            "status": "success",
            "destination": destination,
            "checkin": checkin,
            "checkout": checkout,
            "rooms": rooms,
            "guests": guests,
            "total_results": len(results),
            "results": results,
            "pricing_note": "Prices shown are D2M client prices (net + 25% markup)",
        }

    except requests.HTTPError as e:
        logger.error("Expedia TAAP API HTTP error: %s", e)
        return {
            "status": "error",
            "provider": "Expedia TAAP",
            "http_status": e.response.status_code if e.response else None,
            "message": str(e),
        }
    except Exception as e:
        logger.error("Expedia TAAP search error: %s", e)
        return {"status": "error", "provider": "Expedia TAAP", "message": str(e)}


# ============================================================================
# TOOL REGISTRATION
# ============================================================================

def register_taap_tools(mcp: FastMCP):
    """Register Expedia TAAP hotel search tools with the MCP server."""

    @mcp.tool(
        name="search_taap_hotels",
        annotations={"title": "Search Hotels via Expedia TAAP (EPS Rapid)", "readOnlyHint": True},
    )
    async def search_taap_hotels(
        destination: str = Field(..., description="City, region, or airport code (e.g., 'Athens, Greece', 'ATH', 'Rome')"),
        checkin: str = Field(..., description="Check-in date (YYYY-MM-DD)"),
        checkout: str = Field(..., description="Check-out date (YYYY-MM-DD)"),
        rooms: int = Field(1, description="Number of rooms", ge=1, le=8),
        guests: int = Field(2, description="Number of guests per room", ge=1, le=8),
    ) -> str:
        """Search Expedia TAAP (EPS Rapid API) for hotel availability.

        Returns agent-net pricing with D2M markup applied (25% standard).
        Each result includes name, address, star rating, double/suite room prices,
        images, amenities, booking URL, rating, reviews, and sample review snippets.
        """
        result = await search_taap_hotels_impl(destination, checkin, checkout, rooms, guests)
        return json.dumps(result, indent=2)

    @mcp.tool(
        name="get_taap_hotel_rates",
        annotations={"title": "Get Expedia TAAP Room Rates for a Property", "readOnlyHint": True},
    )
    async def get_taap_hotel_rates(
        property_id: str = Field(..., description="EPS Rapid property ID from search results"),
        checkin: str = Field(..., description="Check-in date (YYYY-MM-DD)"),
        checkout: str = Field(..., description="Check-out date (YYYY-MM-DD)"),
        rooms: int = Field(1, description="Number of rooms", ge=1, le=8),
    ) -> str:
        """Get specific room rates for an Expedia TAAP property.

        Use property_id from search_taap_hotels results.
        Returns all available room types with agent-net and D2M client pricing.
        """
        try:
            api_key, api_secret, taap_account_id = _load_expedia_credentials()
        except ValueError as e:
            return _stub_credentials_error(str(e))

        if not api_key:
            return _stub_credentials_error("API key is empty.")

        try:
            headers = {
                "Accept": "application/json",
            }
            if taap_account_id:
                headers["Customer"] = taap_account_id

            params = {
                "checkin": checkin,
                "checkout": checkout,
                "rooms": rooms,
                "currency": "USD",
                "language": "en-US",
                "country_code": "US",
                "rate_option": "net_rates",
            }

            resp = requests.get(
                f"{ExpediaTAAPConfig.BASE_URL}/properties/{property_id}/rooms",
                headers=headers,
                auth=(api_key, api_secret),
                params=params,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            rooms_data = data if isinstance(data, list) else data.get("data", data.get("rooms", []))
            currency = "USD"
            room_rates = _extract_room_rates(rooms_data, currency)

            return json.dumps({
                "status": "success",
                "property_id": property_id,
                "checkin": checkin,
                "checkout": checkout,
                "rooms": rooms,
                "total_room_types": len(room_rates),
                "room_rates": room_rates,
                "pricing_note": "Client prices include 25% D2M markup on net agent rates",
            }, indent=2)

        except requests.HTTPError as e:
            logger.error("Expedia TAAP rates HTTP error: %s", e)
            return json.dumps({
                "status": "error",
                "provider": "Expedia TAAP",
                "http_status": e.response.status_code if e.response else None,
                "message": str(e),
            })
        except Exception as e:
            logger.error("Expedia TAAP rates error: %s", e)
            return json.dumps({"status": "error", "provider": "Expedia TAAP", "message": str(e)})
