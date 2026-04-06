"""
Dreams2Memories OpenTable Restaurant MCP Module
===============================================

Restaurant search and reservation link generation via OpenTable Affiliate API:
- Search restaurants by city, cuisine, party size, and date
- Generate direct deep-link reservation URLs for client proposals
- Returns Michelin stars, ratings, reviews, and price range

Integrates with: travel_mcp_server.py
Dependencies: requests
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


class OpenTableConfig:
    """OpenTable Affiliate/Partner API configuration.

    Production: https://platform.opentable.com/
    Sandbox:    https://platform.otqa.com/

    Register at: https://www.opentable.com/affiliates
    """
    API_KEY = ""
    AFFILIATE_ID = ""
    BASE_URL = "https://platform.opentable.com"   # switch to otqa.com for sandbox
    RESERVATION_DEEPLINK = "https://www.opentable.com/booking/experiences-availability"


# ============================================================================
# CREDENTIAL LOADER
# ============================================================================

def _load_opentable_credentials() -> tuple[str, str]:
    """Load OpenTable API key and affiliate ID from credentials file."""
    if OpenTableConfig.API_KEY:
        return OpenTableConfig.API_KEY, OpenTableConfig.AFFILIATE_ID

    cred_file = THUNDERBIRD_DIR / "opentable_credentials.json"
    if cred_file.exists():
        with open(cred_file, encoding="utf-8") as f:
            creds = json.load(f)
        OpenTableConfig.API_KEY = creds.get("api_key", "")
        OpenTableConfig.AFFILIATE_ID = creds.get("affiliate_id", "")
        if creds.get("base_url"):
            OpenTableConfig.BASE_URL = creds["base_url"]
        return OpenTableConfig.API_KEY, OpenTableConfig.AFFILIATE_ID

    raise ValueError(
        "OpenTable credentials not configured. "
        "Create ~/Thunderbird/opentable_credentials.json with "
        '{"api_key": "YOUR_KEY", "affiliate_id": "YOUR_AFFILIATE_ID"}'
    )


# ============================================================================
# HELPERS
# ============================================================================

def _build_reservation_link(restaurant_id: str, date: str, time: str, party_size: int, affiliate_id: str) -> str:
    """Build OpenTable direct reservation deep-link URL."""
    from urllib.parse import urlencode

    params = {
        "rid": restaurant_id,
        "restref": restaurant_id,
        "lang": "en-US",
        "ref": "affiliate",
        "afid": affiliate_id or "d2m",
        "covers": party_size,
        "dateTime": f"{date}T{time}",
    }
    return f"{OpenTableConfig.RESERVATION_DEEPLINK}?{urlencode(params)}"


def _stub_credentials_error(provider: str, message: str) -> str:
    """Return a structured error for unconfigured credentials."""
    return json.dumps({
        "status": "credentials_required",
        "provider": provider,
        "message": message,
        "action": "Add credentials to ~/Thunderbird/opentable_credentials.json",
    })


# ============================================================================
# TOOL REGISTRATION
# ============================================================================

def register_opentable_tools(mcp: FastMCP):
    """Register OpenTable restaurant search and reservation tools with the MCP server."""

    @mcp.tool(
        name="search_opentable_restaurants",
        annotations={"title": "Search OpenTable Restaurants", "readOnlyHint": True},
    )
    async def search_opentable_restaurants(
        city: str = Field(..., description="City to search in (e.g., 'Athens', 'Rome', 'New York')"),
        cuisine: str = Field("", description="Cuisine type filter (e.g., 'Greek', 'Italian', 'Seafood')"),
        date: str = Field("", description="Reservation date (YYYY-MM-DD, optional for availability filter)"),
        party_size: int = Field(2, description="Number of diners", ge=1, le=20),
    ) -> str:
        """Search OpenTable affiliate API for restaurants in a city.

        Returns up to 20 results with name, cuisine, price range, address,
        Michelin stars (if applicable), ratings, sample reviews, and a
        direct booking deep-link URL for each restaurant.

        Use get_opentable_reservation_link for a specific restaurant/time.
        """
        try:
            api_key, affiliate_id = _load_opentable_credentials()
        except ValueError as e:
            return _stub_credentials_error("OpenTable", str(e))

        if not api_key:
            return _stub_credentials_error(
                "OpenTable",
                "API key is empty. Register at https://www.opentable.com/affiliates"
            )

        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }

            params = {
                "city": city,
                "covers": party_size,
                "limit": 20,
                "sort": "popularity",
            }
            if cuisine:
                params["cuisine"] = cuisine
            if date:
                params["date"] = date

            resp = requests.get(
                f"{OpenTableConfig.BASE_URL}/restaurants/availability",
                headers=headers,
                params=params,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            restaurants = data.get("restaurants", data.get("data", []))
            results = []

            for r in restaurants[:20]:
                rid = str(r.get("rid", r.get("id", r.get("restaurant_id", ""))))

                # Build reservation deep-link
                booking_url = _build_reservation_link(
                    restaurant_id=rid,
                    date=date or "",
                    time="19:00",
                    party_size=party_size,
                    affiliate_id=affiliate_id,
                )

                # Extract sample reviews
                reviews_raw = r.get("reviews", r.get("review_highlights", []))
                sample_reviews = [
                    rev.get("text", rev.get("comment", ""))[:150]
                    for rev in reviews_raw[:3]
                    if rev.get("text") or rev.get("comment")
                ]

                results.append({
                    "name": r.get("name", ""),
                    "cuisine": r.get("cuisine_type", r.get("cuisine", cuisine or "")),
                    "price_range": r.get("price", r.get("price_range", r.get("price_level", "$$"))),
                    "address": r.get("address", {}).get("street", r.get("street_address", "")),
                    "city": r.get("address", {}).get("city", city),
                    "booking_url": booking_url,
                    "image_url": r.get("profile_image", r.get("image_url", r.get("image", ""))),
                    "rating": r.get("overall_rating", r.get("rating", r.get("avg_rating"))),
                    "review_count": r.get("review_count", r.get("num_reviews", 0)),
                    "michelin_stars": r.get("michelin_stars", r.get("awards", {}).get("michelin_stars")),
                    "sample_reviews": sample_reviews,
                    "restaurant_id": rid,
                    "source": "opentable",
                })

            return json.dumps({
                "status": "success",
                "city": city,
                "cuisine_filter": cuisine or None,
                "date": date or None,
                "party_size": party_size,
                "total_results": len(results),
                "results": results,
            }, indent=2)

        except requests.HTTPError as e:
            logger.error("OpenTable API HTTP error: %s", e)
            return json.dumps({
                "status": "error",
                "provider": "OpenTable",
                "http_status": e.response.status_code if e.response else None,
                "message": str(e),
            })
        except Exception as e:
            logger.error("OpenTable search error: %s", e)
            return json.dumps({"status": "error", "provider": "OpenTable", "message": str(e)})

    @mcp.tool(
        name="get_opentable_reservation_link",
        annotations={"title": "Get OpenTable Reservation Deep-Link", "readOnlyHint": True},
    )
    async def get_opentable_reservation_link(
        restaurant_id: str = Field(..., description="OpenTable restaurant ID (rid) from search results"),
        date: str = Field(..., description="Reservation date (YYYY-MM-DD)"),
        time: str = Field(..., description="Preferred reservation time (HH:MM, 24-hour, e.g. '19:30')"),
        party_size: int = Field(2, description="Number of diners", ge=1, le=20),
    ) -> str:
        """Generate a direct OpenTable reservation deep-link for a specific restaurant, date, time, and party size.

        Use this after search_opentable_restaurants to build a clickable booking
        link for client proposals and dossiers. No API call required — link is
        constructed from the affiliate deep-link template.
        """
        try:
            _, affiliate_id = _load_opentable_credentials()
        except ValueError as e:
            # Fallback: generate link with empty affiliate ID
            affiliate_id = ""
            logger.warning("OpenTable credentials not loaded for link generation: %s", e)

        booking_url = _build_reservation_link(
            restaurant_id=restaurant_id,
            date=date,
            time=time,
            party_size=party_size,
            affiliate_id=affiliate_id,
        )

        return json.dumps({
            "status": "success",
            "restaurant_id": restaurant_id,
            "date": date,
            "time": time,
            "party_size": party_size,
            "booking_url": booking_url,
            "note": (
                "Direct reservation link. Share with client or embed in proposal. "
                "Client clicks link and completes booking on OpenTable."
            ),
        }, indent=2)
