"""
Dreams2Memories Excursions Search MCP Module
=============================================

Shore excursion and activity search via partner APIs:
- Viator Partner API (tours/activities, 8-12% commission)
- GetYourGuide Integrator API (tours/activities, 8-12% commission)
- Shore Excursions Group API (cruise-focused, 8% commission)

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

# D2M commission rates
VIATOR_COMMISSION_LOW = 0.08
VIATOR_COMMISSION_HIGH = 0.12
GYG_COMMISSION_LOW = 0.08
GYG_COMMISSION_HIGH = 0.12
SEG_COMMISSION = 0.08

EUR_TO_USD = 1.09


class ViatorConfig:
    """Viator Partner API configuration.

    Get credentials from https://partnerresources.viator.com/
    """
    API_KEY = ""
    BASE_URL = "https://api.viator.com/partner"


class GetYourGuideConfig:
    """GetYourGuide Integrator API configuration.

    Get credentials from https://partner.getyourguide.com/
    """
    API_KEY = ""
    BASE_URL = "https://api.getyourguide.com/1"


class ShoreExcursionsConfig:
    """Shore Excursions Group API configuration.

    Get credentials from https://www.shoreexcursionsgroup.com/partners
    """
    API_KEY = ""
    AGENT_ID = ""
    BASE_URL = "https://api.shoreexcursionsgroup.com/v1"


# ============================================================================
# CREDENTIAL LOADERS
# ============================================================================

def _load_viator_credentials() -> str:
    """Load Viator API key from credentials file."""
    if ViatorConfig.API_KEY:
        return ViatorConfig.API_KEY

    cred_file = THUNDERBIRD_DIR / "viator_credentials.json"
    if cred_file.exists():
        with open(cred_file, encoding="utf-8") as f:
            creds = json.load(f)
        ViatorConfig.API_KEY = creds.get("api_key", "")
        return ViatorConfig.API_KEY

    raise ValueError(
        "Viator credentials not configured. "
        "Create ~/Thunderbird/viator_credentials.json with "
        '{"api_key": "YOUR_KEY"}'
    )


def _load_gyg_credentials() -> str:
    """Load GetYourGuide API key from credentials file."""
    if GetYourGuideConfig.API_KEY:
        return GetYourGuideConfig.API_KEY

    cred_file = THUNDERBIRD_DIR / "getyourguide_credentials.json"
    if cred_file.exists():
        with open(cred_file, encoding="utf-8") as f:
            creds = json.load(f)
        GetYourGuideConfig.API_KEY = creds.get("api_key", "")
        return GetYourGuideConfig.API_KEY

    raise ValueError(
        "GetYourGuide credentials not configured. "
        "Create ~/Thunderbird/getyourguide_credentials.json with "
        '{"api_key": "YOUR_KEY"}'
    )


def _load_seg_credentials() -> tuple[str, str]:
    """Load Shore Excursions Group credentials from file."""
    if ShoreExcursionsConfig.API_KEY:
        return ShoreExcursionsConfig.API_KEY, ShoreExcursionsConfig.AGENT_ID

    cred_file = THUNDERBIRD_DIR / "shore_excursions_credentials.json"
    if cred_file.exists():
        with open(cred_file, encoding="utf-8") as f:
            creds = json.load(f)
        ShoreExcursionsConfig.API_KEY = creds.get("api_key", "")
        ShoreExcursionsConfig.AGENT_ID = creds.get("agent_id", "")
        return ShoreExcursionsConfig.API_KEY, ShoreExcursionsConfig.AGENT_ID

    raise ValueError(
        "Shore Excursions Group credentials not configured. "
        "Create ~/Thunderbird/shore_excursions_credentials.json with "
        '{"api_key": "YOUR_KEY", "agent_id": "YOUR_AGENT_ID"}'
    )


# ============================================================================
# HELPERS
# ============================================================================

def _commission_estimate(price_usd: float, rate_low: float, rate_high: float) -> dict:
    """Calculate commission range for a given price."""
    return {
        "low": f"${price_usd * rate_low:,.2f}",
        "high": f"${price_usd * rate_high:,.2f}",
        "rate_range": f"{int(rate_low * 100)}-{int(rate_high * 100)}%",
    }


def _to_usd(amount: float, currency: str) -> float:
    """Convert amount to USD."""
    if currency.upper() == "EUR":
        return amount * EUR_TO_USD
    return amount


def _stub_credentials_error(provider: str, message: str) -> str:
    """Return a structured error for unconfigured credentials."""
    return json.dumps({
        "status": "credentials_required",
        "provider": provider,
        "message": message,
        "action": f"Add API key to ~/Thunderbird/{provider.lower().replace(' ', '_')}_credentials.json",
    })


# ============================================================================
# TOOL REGISTRATION
# ============================================================================

def register_excursion_tools(mcp: FastMCP):
    """Register shore excursion and activity search tools with the MCP server."""

    @mcp.tool(
        name="search_viator_excursions",
        annotations={"title": "Search Viator Tours & Activities", "readOnlyHint": True},
    )
    async def search_viator_excursions(
        destination: str = Field(..., description="Destination city or region (e.g., 'Athens', 'Barcelona')"),
        date: str = Field(..., description="Activity date (YYYY-MM-DD)"),
        keywords: str = Field("", description="Optional keyword filter (e.g., 'food tour', 'sunset cruise')"),
    ) -> str:
        """Search Viator Partner API for tours and activities at a destination.

        Returns results with D2M commission estimates (8-12%).
        Each result includes name, description, price, duration, booking URL,
        image, rating, review count, and commission estimate.
        """
        try:
            api_key = _load_viator_credentials()
        except ValueError as e:
            return _stub_credentials_error("Viator", str(e))

        if not api_key:
            return _stub_credentials_error(
                "Viator",
                "API key is empty. Register at https://partnerresources.viator.com/"
            )

        try:
            headers = {
                "exp-api-key": api_key,
                "Accept": "application/json;version=2.0",
                "Accept-Language": "en-US",
            }

            # Viator product search endpoint
            payload = {
                "filtering": {
                    "destination": destination,
                    "tags": [],
                },
                "sorting": {
                    "sort": "TRAVELER_RATING",
                    "order": "DESCENDING",
                },
                "pagination": {
                    "start": 1,
                    "count": 20,
                },
                "currency": "USD",
            }

            if keywords:
                payload["filtering"]["searchTerm"] = keywords

            if date:
                payload["filtering"]["startDate"] = date
                payload["filtering"]["endDate"] = date

            resp = requests.post(
                f"{ViatorConfig.BASE_URL}/products/search",
                headers=headers,
                json=payload,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            products = data.get("products", [])
            results = []

            for p in products[:20]:
                pricing = p.get("pricing", {})
                summary = pricing.get("summary", {})
                from_price = summary.get("fromPrice", 0)
                currency = pricing.get("currency", "USD")
                price_usd = _to_usd(float(from_price or 0), currency)

                images = p.get("images", [])
                image_url = ""
                if images:
                    variants = images[0].get("variants", [])
                    if variants:
                        image_url = variants[0].get("url", "")

                reviews = p.get("reviews", {})

                results.append({
                    "name": p.get("title", ""),
                    "description": p.get("description", "")[:400],
                    "price_per_person_usd": f"${price_usd:,.2f}" if price_usd else "See booking page",
                    "duration": p.get("duration", {}).get("fixedDurationInMinutes", "Varies"),
                    "booking_url": f"https://www.viator.com/tours/{p.get('productCode', '')}" if p.get("productCode") else "",
                    "image_url": image_url,
                    "rating": reviews.get("combinedAverageRating"),
                    "review_count": reviews.get("totalReviews", 0),
                    "commission_estimate": _commission_estimate(price_usd, VIATOR_COMMISSION_LOW, VIATOR_COMMISSION_HIGH),
                    "product_code": p.get("productCode"),
                    "source": "viator",
                })

            return json.dumps({
                "status": "success",
                "destination": destination,
                "date": date,
                "keywords": keywords,
                "total_results": len(results),
                "results": results,
                "commission_note": "Viator agent commission: 8-12% of client price",
            }, indent=2)

        except requests.HTTPError as e:
            logger.error("Viator API HTTP error: %s", e)
            return json.dumps({
                "status": "error",
                "provider": "Viator",
                "http_status": e.response.status_code if e.response else None,
                "message": str(e),
            })
        except Exception as e:
            logger.error("Viator search error: %s", e)
            return json.dumps({"status": "error", "provider": "Viator", "message": str(e)})

    @mcp.tool(
        name="search_getyourguide_excursions",
        annotations={"title": "Search GetYourGuide Tours & Activities", "readOnlyHint": True},
    )
    async def search_getyourguide_excursions(
        destination: str = Field(..., description="Destination city or region (e.g., 'Rome', 'Tokyo')"),
        date: str = Field(..., description="Activity date (YYYY-MM-DD)"),
        keywords: str = Field("", description="Optional keyword filter (e.g., 'cooking class', 'wine tour')"),
    ) -> str:
        """Search GetYourGuide Integrator API for tours and activities.

        Returns results with D2M commission estimates (8-12%).
        Each result includes name, description, price, duration, booking URL,
        image, rating, review count, and commission estimate.
        """
        try:
            api_key = _load_gyg_credentials()
        except ValueError as e:
            return _stub_credentials_error("GetYourGuide", str(e))

        if not api_key:
            return _stub_credentials_error(
                "GetYourGuide",
                "API key is empty. Register at https://partner.getyourguide.com/"
            )

        try:
            headers = {
                "X-Requested-With": "XMLHttpRequest",
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
            }

            params = {
                "q": destination + (f" {keywords}" if keywords else ""),
                "currency": "USD",
                "limit": 20,
            }

            if date:
                params["date_from"] = date
                params["date_to"] = date

            resp = requests.get(
                f"{GetYourGuideConfig.BASE_URL}/activities",
                headers=headers,
                params=params,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            activities = data.get("data", {}).get("activities", [])
            results = []

            for act in activities[:20]:
                price_obj = act.get("price", {})
                from_price = float(price_obj.get("value", 0) or 0)
                currency = price_obj.get("currency", "USD")
                price_usd = _to_usd(from_price, currency)

                pictures = act.get("pictures", [])
                image_url = pictures[0].get("url", "") if pictures else ""

                results.append({
                    "name": act.get("title", ""),
                    "description": act.get("abstract", "")[:400],
                    "price_per_person_usd": f"${price_usd:,.2f}" if price_usd else "See booking page",
                    "duration": act.get("duration", "Varies"),
                    "booking_url": act.get("url", ""),
                    "image_url": image_url,
                    "rating": act.get("rating", {}).get("average"),
                    "review_count": act.get("rating", {}).get("count", 0),
                    "commission_estimate": _commission_estimate(price_usd, GYG_COMMISSION_LOW, GYG_COMMISSION_HIGH),
                    "activity_id": act.get("activity_id"),
                    "source": "getyourguide",
                })

            return json.dumps({
                "status": "success",
                "destination": destination,
                "date": date,
                "keywords": keywords,
                "total_results": len(results),
                "results": results,
                "commission_note": "GetYourGuide partner commission: 8-12% of client price",
            }, indent=2)

        except requests.HTTPError as e:
            logger.error("GetYourGuide API HTTP error: %s", e)
            return json.dumps({
                "status": "error",
                "provider": "GetYourGuide",
                "http_status": e.response.status_code if e.response else None,
                "message": str(e),
            })
        except Exception as e:
            logger.error("GetYourGuide search error: %s", e)
            return json.dumps({"status": "error", "provider": "GetYourGuide", "message": str(e)})

    @mcp.tool(
        name="search_shore_excursions_group",
        annotations={"title": "Search Shore Excursions Group", "readOnlyHint": True},
    )
    async def search_shore_excursions_group(
        destination: str = Field(..., description="Port city or destination (e.g., 'Santorini', 'Dubrovnik')"),
        ship: str = Field("", description="Ship name for cruise-specific excursions (optional)"),
        date: str = Field("", description="Port call date (YYYY-MM-DD, optional)"),
    ) -> str:
        """Search Shore Excursions Group API for cruise port excursions.

        Cruise-specialist provider with excursions at 300+ ports worldwide.
        Returns results with D2M commission estimate (8%).
        Each result includes name, description, price, duration, booking URL,
        image, rating, review count, and commission estimate.
        """
        try:
            api_key, agent_id = _load_seg_credentials()
        except ValueError as e:
            return _stub_credentials_error("Shore Excursions Group", str(e))

        if not api_key:
            return _stub_credentials_error(
                "Shore Excursions Group",
                "API key is empty. Register at https://www.shoreexcursionsgroup.com/partners"
            )

        try:
            headers = {
                "X-API-Key": api_key,
                "Accept": "application/json",
            }
            if agent_id:
                headers["X-Agent-ID"] = agent_id

            params = {
                "destination": destination,
                "limit": 20,
            }
            if ship:
                params["ship"] = ship
            if date:
                params["date"] = date

            resp = requests.get(
                f"{ShoreExcursionsConfig.BASE_URL}/excursions",
                headers=headers,
                params=params,
                timeout=15,
            )

            # Handle 404 gracefully — SEG API endpoint may differ
            if resp.status_code == 404:
                return json.dumps({
                    "status": "endpoint_not_found",
                    "provider": "Shore Excursions Group",
                    "message": (
                        "The Shore Excursions Group API endpoint returned 404. "
                        "The partner API path may differ from the stub. "
                        "Contact SEG partner support at https://www.shoreexcursionsgroup.com/partners "
                        "for the correct API base URL and endpoint paths."
                    ),
                    "attempted_url": f"{ShoreExcursionsConfig.BASE_URL}/excursions",
                })

            resp.raise_for_status()
            data = resp.json()

            excursions = data.get("excursions", data.get("data", []))
            results = []

            for exc in excursions[:20]:
                price = float(exc.get("price", exc.get("price_per_person", 0)) or 0)
                currency = exc.get("currency", "USD")
                price_usd = _to_usd(price, currency)

                results.append({
                    "name": exc.get("name", exc.get("title", "")),
                    "description": exc.get("description", "")[:400],
                    "price_per_person_usd": f"${price_usd:,.2f}" if price_usd else "See booking page",
                    "duration": exc.get("duration", "Varies"),
                    "booking_url": exc.get("booking_url", exc.get("url", "")),
                    "image_url": exc.get("image_url", exc.get("image", "")),
                    "rating": exc.get("rating"),
                    "review_count": exc.get("review_count", exc.get("reviews", 0)),
                    "commission_estimate": _commission_estimate(price_usd, SEG_COMMISSION, SEG_COMMISSION),
                    "excursion_id": exc.get("id", exc.get("excursion_id")),
                    "source": "shore_excursions_group",
                })

            return json.dumps({
                "status": "success",
                "destination": destination,
                "ship": ship or None,
                "date": date or None,
                "total_results": len(results),
                "results": results,
                "commission_note": "Shore Excursions Group agent commission: 8% of client price",
            }, indent=2)

        except requests.HTTPError as e:
            logger.error("Shore Excursions Group API HTTP error: %s", e)
            return json.dumps({
                "status": "error",
                "provider": "Shore Excursions Group",
                "http_status": e.response.status_code if e.response else None,
                "message": str(e),
            })
        except Exception as e:
            logger.error("Shore Excursions Group search error: %s", e)
            return json.dumps({"status": "error", "provider": "Shore Excursions Group", "message": str(e)})
