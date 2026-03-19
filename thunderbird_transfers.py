"""
Dreams2Memories Ground Transfers MCP Module
===========================================

Ground transfer search via partner APIs:
- Welcome Pickups (premium airport transfers, Mediterranean/Europe focus)
- Mozio (global ground transport aggregator)
- Blacklane (luxury chauffeur, global coverage)

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

EUR_TO_USD = 1.09


class WelcomePickupsConfig:
    """Welcome Pickups partner API configuration.

    Get credentials from https://www.welcomepickups.com/partners/
    """
    API_KEY = ""
    BASE_URL = "https://api.welcomepickups.com/v3"


class MozioConfig:
    """Mozio ground transport API configuration.

    Get credentials from https://www.mozio.com/en-us/partners/
    """
    API_KEY = ""
    BASE_URL = "https://api.mozio.com/v2"


class BlacklaneConfig:
    """Blacklane luxury chauffeur partner API configuration.

    Get credentials from https://www.blacklane.com/en/corporate/partner-program/
    """
    API_KEY = ""
    BASE_URL = "https://partner.blacklane.com/api"


# ============================================================================
# CREDENTIAL LOADERS
# ============================================================================

def _load_welcome_pickups_credentials() -> str:
    """Load Welcome Pickups API key from credentials file."""
    if WelcomePickupsConfig.API_KEY:
        return WelcomePickupsConfig.API_KEY

    cred_file = THUNDERBIRD_DIR / "welcome_pickups_credentials.json"
    if cred_file.exists():
        with open(cred_file, encoding="utf-8") as f:
            creds = json.load(f)
        WelcomePickupsConfig.API_KEY = creds.get("api_key", "")
        return WelcomePickupsConfig.API_KEY

    raise ValueError(
        "Welcome Pickups credentials not configured. "
        "Create ~/Thunderbird/welcome_pickups_credentials.json with "
        '{"api_key": "YOUR_KEY"}'
    )


def _load_mozio_credentials() -> str:
    """Load Mozio API key from credentials file."""
    if MozioConfig.API_KEY:
        return MozioConfig.API_KEY

    cred_file = THUNDERBIRD_DIR / "mozio_credentials.json"
    if cred_file.exists():
        with open(cred_file, encoding="utf-8") as f:
            creds = json.load(f)
        MozioConfig.API_KEY = creds.get("api_key", "")
        return MozioConfig.API_KEY

    raise ValueError(
        "Mozio credentials not configured. "
        "Create ~/Thunderbird/mozio_credentials.json with "
        '{"api_key": "YOUR_KEY"}'
    )


def _load_blacklane_credentials() -> str:
    """Load Blacklane API key from credentials file."""
    if BlacklaneConfig.API_KEY:
        return BlacklaneConfig.API_KEY

    cred_file = THUNDERBIRD_DIR / "blacklane_credentials.json"
    if cred_file.exists():
        with open(cred_file, encoding="utf-8") as f:
            creds = json.load(f)
        BlacklaneConfig.API_KEY = creds.get("api_key", "")
        return BlacklaneConfig.API_KEY

    raise ValueError(
        "Blacklane credentials not configured. "
        "Create ~/Thunderbird/blacklane_credentials.json with "
        '{"api_key": "YOUR_KEY"}'
    )


# ============================================================================
# HELPERS
# ============================================================================

def _to_usd(amount: float, currency: str) -> float:
    """Convert amount to USD."""
    if currency.upper() == "EUR":
        return amount * EUR_TO_USD
    return float(amount)


def _stub_credentials_error(provider: str, message: str) -> str:
    """Return a structured error for unconfigured credentials."""
    filename = provider.lower().replace(" ", "_").replace("-", "_") + "_credentials.json"
    return json.dumps({
        "status": "credentials_required",
        "provider": provider,
        "message": message,
        "action": f"Add API key to ~/Thunderbird/{filename}",
    })


def _format_transfer_result(
    provider: str,
    vehicle_type: str,
    price_raw: float,
    currency: str,
    duration_minutes,
    booking_url: str,
    cancellation_policy: str,
    image_url: str,
    rating,
    customer_reviews: list,
    extra: dict = None,
) -> dict:
    """Standardize a transfer result dict."""
    price_usd = _to_usd(price_raw, currency)
    result = {
        "provider": provider,
        "vehicle_type": vehicle_type,
        "price": {
            "eur": f"€{price_raw:,.2f}" if currency.upper() == "EUR" else None,
            "usd": f"${price_usd:,.2f}",
            "currency_original": currency.upper(),
            "amount_original": price_raw,
        },
        "duration_minutes": duration_minutes,
        "booking_url": booking_url,
        "cancellation_policy": cancellation_policy,
        "image_url": image_url,
        "rating": rating,
        "customer_reviews": customer_reviews[:3] if customer_reviews else [],
    }
    if extra:
        result.update(extra)
    return result


# ============================================================================
# TOOL REGISTRATION
# ============================================================================

def register_transfer_tools(mcp: FastMCP):
    """Register ground transfer search tools with the MCP server."""

    @mcp.tool(
        name="search_welcome_pickups",
        annotations={"title": "Search Welcome Pickups Transfers", "readOnlyHint": True},
    )
    async def search_welcome_pickups(
        pickup_location: str = Field(..., description="Pickup location (e.g., 'Athens International Airport', 'Piraeus Port')"),
        dropoff_location: str = Field(..., description="Drop-off location (e.g., 'Hotel Grande Bretagne, Athens')"),
        date: str = Field(..., description="Transfer date (YYYY-MM-DD)"),
        passengers: int = Field(2, description="Number of passengers", ge=1, le=16),
    ) -> str:
        """Search Welcome Pickups for premium airport/port transfers.

        Welcome Pickups specializes in pre-booked transfers across Europe and
        the Mediterranean — ideal for cruise clients arriving at Greek, Spanish,
        Italian, or Turkish ports.

        Returns vehicle options with EUR and USD pricing, duration, cancellation
        policy, and customer review snippets.
        """
        try:
            api_key = _load_welcome_pickups_credentials()
        except ValueError as e:
            return _stub_credentials_error("Welcome Pickups", str(e))

        if not api_key:
            return _stub_credentials_error(
                "Welcome Pickups",
                "API key is empty. Register at https://www.welcomepickups.com/partners/"
            )

        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }

            payload = {
                "pickup": pickup_location,
                "dropoff": dropoff_location,
                "pickup_date": date,
                "passengers": passengers,
                "currency": "EUR",
            }

            resp = requests.post(
                f"{WelcomePickupsConfig.BASE_URL}/transfers/search",
                headers=headers,
                json=payload,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            transfers = data.get("transfers", data.get("results", []))
            results = []

            for t in transfers[:10]:
                price_raw = float(t.get("price", t.get("total_price", 0)) or 0)
                currency = t.get("currency", "EUR")
                reviews_raw = t.get("reviews", [])
                review_snippets = [
                    r.get("text", r.get("comment", ""))[:120]
                    for r in reviews_raw[:3]
                    if r.get("text") or r.get("comment")
                ]

                results.append(_format_transfer_result(
                    provider="Welcome Pickups",
                    vehicle_type=t.get("vehicle_type", t.get("vehicle_class", "Standard")),
                    price_raw=price_raw,
                    currency=currency,
                    duration_minutes=t.get("duration_minutes", t.get("estimated_duration")),
                    booking_url=t.get("booking_url", t.get("url", "")),
                    cancellation_policy=t.get("cancellation_policy", "Free cancellation up to 24 hours before pickup"),
                    image_url=t.get("image_url", t.get("vehicle_image", "")),
                    rating=t.get("rating", t.get("average_rating")),
                    customer_reviews=review_snippets,
                    extra={"transfer_id": t.get("id", t.get("transfer_id"))},
                ))

            return json.dumps({
                "status": "success",
                "pickup": pickup_location,
                "dropoff": dropoff_location,
                "date": date,
                "passengers": passengers,
                "total_results": len(results),
                "results": results,
            }, indent=2)

        except requests.HTTPError as e:
            logger.error("Welcome Pickups API HTTP error: %s", e)
            return json.dumps({
                "status": "error",
                "provider": "Welcome Pickups",
                "http_status": e.response.status_code if e.response else None,
                "message": str(e),
            })
        except Exception as e:
            logger.error("Welcome Pickups search error: %s", e)
            return json.dumps({"status": "error", "provider": "Welcome Pickups", "message": str(e)})

    @mcp.tool(
        name="search_mozio_transfers",
        annotations={"title": "Search Mozio Ground Transport", "readOnlyHint": True},
    )
    async def search_mozio_transfers(
        pickup_location: str = Field(..., description="Pickup address or airport code (e.g., 'LAX', 'Miami International Airport')"),
        dropoff_location: str = Field(..., description="Drop-off address or hotel name"),
        date: str = Field(..., description="Transfer date (YYYY-MM-DD)"),
        passengers: int = Field(2, description="Number of passengers", ge=1, le=16),
    ) -> str:
        """Search Mozio for global ground transport options.

        Mozio aggregates 800+ transfer providers worldwide — taxis, shuttles,
        private cars, and luxury vehicles. Good for any destination globally,
        especially US airports and international hubs.

        Returns vehicle options with USD pricing, duration, cancellation
        policy, and customer review snippets.
        """
        try:
            api_key = _load_mozio_credentials()
        except ValueError as e:
            return _stub_credentials_error("Mozio", str(e))

        if not api_key:
            return _stub_credentials_error(
                "Mozio",
                "API key is empty. Register at https://www.mozio.com/en-us/partners/"
            )

        try:
            headers = {
                "API-KEY": api_key,
                "Accept": "application/json",
                "Content-Type": "application/json",
            }

            payload = {
                "start_address": pickup_location,
                "end_address": dropoff_location,
                "pickup_datetime": f"{date}T12:00:00",
                "num_passengers": passengers,
                "currency": "USD",
                "campaign": "d2m_luxury_travel",
            }

            resp = requests.post(
                f"{MozioConfig.BASE_URL}/search/",
                headers=headers,
                json=payload,
                timeout=20,
            )
            resp.raise_for_status()
            data = resp.json()

            # Mozio may return a search_id for async polling
            search_id = data.get("search_id")
            results_raw = data.get("results", [])

            # If async, try polling once
            if search_id and not results_raw:
                import time
                time.sleep(3)
                poll_resp = requests.get(
                    f"{MozioConfig.BASE_URL}/search/{search_id}/poll/",
                    headers=headers,
                    timeout=15,
                )
                if poll_resp.status_code == 200:
                    results_raw = poll_resp.json().get("results", [])

            results = []
            for t in results_raw[:10]:
                price_raw = float(t.get("total_price", t.get("price", 0)) or 0)
                currency = t.get("currency", "USD")
                reviews_raw = t.get("reviews", [])
                review_snippets = [
                    r.get("text", r.get("comment", ""))[:120]
                    for r in reviews_raw[:3]
                    if r.get("text") or r.get("comment")
                ]

                results.append(_format_transfer_result(
                    provider=t.get("provider_name", "Mozio Partner"),
                    vehicle_type=t.get("vehicle_type", t.get("category", "Standard")),
                    price_raw=price_raw,
                    currency=currency,
                    duration_minutes=t.get("duration", t.get("duration_minutes")),
                    booking_url=t.get("booking_url", ""),
                    cancellation_policy=t.get("cancellation_policy", "Check provider policy"),
                    image_url=t.get("image", t.get("vehicle_image_url", "")),
                    rating=t.get("rating", t.get("provider_rating")),
                    customer_reviews=review_snippets,
                    extra={
                        "result_id": t.get("result_id", t.get("id")),
                        "search_id": search_id,
                    },
                ))

            return json.dumps({
                "status": "success",
                "pickup": pickup_location,
                "dropoff": dropoff_location,
                "date": date,
                "passengers": passengers,
                "search_id": search_id,
                "total_results": len(results),
                "results": results,
            }, indent=2)

        except requests.HTTPError as e:
            logger.error("Mozio API HTTP error: %s", e)
            return json.dumps({
                "status": "error",
                "provider": "Mozio",
                "http_status": e.response.status_code if e.response else None,
                "message": str(e),
            })
        except Exception as e:
            logger.error("Mozio search error: %s", e)
            return json.dumps({"status": "error", "provider": "Mozio", "message": str(e)})

    @mcp.tool(
        name="search_blacklane_transfers",
        annotations={"title": "Search Blacklane Luxury Chauffeur", "readOnlyHint": True},
    )
    async def search_blacklane_transfers(
        pickup_location: str = Field(..., description="Pickup location (airport code, hotel, or address)"),
        dropoff_location: str = Field(..., description="Drop-off location (hotel, airport, or address)"),
        date: str = Field(..., description="Transfer date (YYYY-MM-DD)"),
        passengers: int = Field(2, description="Number of passengers", ge=1, le=7),
    ) -> str:
        """Search Blacklane for luxury chauffeur transfers worldwide.

        Blacklane is the premium tier — professional chauffeurs, fixed prices,
        free wait time. Ideal for D2M luxury clients at Silversea/Regent level.
        Available in 300+ cities globally.

        Returns vehicle classes with EUR and USD pricing, duration, free
        cancellation policy, and customer review snippets.
        """
        try:
            api_key = _load_blacklane_credentials()
        except ValueError as e:
            return _stub_credentials_error("Blacklane", str(e))

        if not api_key:
            return _stub_credentials_error(
                "Blacklane",
                "API key is empty. Register at https://www.blacklane.com/en/corporate/partner-program/"
            )

        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }

            payload = {
                "pickup": {"address": pickup_location},
                "dropoff": {"address": dropoff_location},
                "pickup_at": f"{date}T12:00:00Z",
                "passengers": passengers,
                "currency": "EUR",
            }

            resp = requests.post(
                f"{BlacklaneConfig.BASE_URL}/rides/quotes",
                headers=headers,
                json=payload,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            quotes = data.get("quotes", data.get("rides", data.get("results", [])))
            results = []

            for q in quotes[:10]:
                price_raw = float(
                    q.get("price", {}).get("amount", 0)
                    if isinstance(q.get("price"), dict)
                    else q.get("price", q.get("total_price", 0)) or 0
                )
                currency = (
                    q.get("price", {}).get("currency", "EUR")
                    if isinstance(q.get("price"), dict)
                    else q.get("currency", "EUR")
                )

                reviews_raw = q.get("reviews", [])
                review_snippets = [
                    r.get("text", r.get("comment", ""))[:120]
                    for r in reviews_raw[:3]
                    if r.get("text") or r.get("comment")
                ]

                results.append(_format_transfer_result(
                    provider="Blacklane",
                    vehicle_type=q.get("vehicle_class", q.get("class", q.get("category", "Business Class"))),
                    price_raw=price_raw,
                    currency=currency,
                    duration_minutes=q.get("duration_minutes", q.get("estimated_duration_minutes")),
                    booking_url=q.get("booking_url", "https://www.blacklane.com/"),
                    cancellation_policy=q.get("cancellation_policy", "Free cancellation up to 1 hour before pickup"),
                    image_url=q.get("vehicle_image", q.get("image_url", "")),
                    rating=q.get("rating", 4.8),
                    customer_reviews=review_snippets,
                    extra={"quote_id": q.get("id", q.get("quote_id"))},
                ))

            return json.dumps({
                "status": "success",
                "pickup": pickup_location,
                "dropoff": dropoff_location,
                "date": date,
                "passengers": passengers,
                "total_results": len(results),
                "results": results,
                "note": "Blacklane: fixed prices, professional chauffeurs, free 60-min wait at airports",
            }, indent=2)

        except requests.HTTPError as e:
            logger.error("Blacklane API HTTP error: %s", e)
            return json.dumps({
                "status": "error",
                "provider": "Blacklane",
                "http_status": e.response.status_code if e.response else None,
                "message": str(e),
            })
        except Exception as e:
            logger.error("Blacklane search error: %s", e)
            return json.dumps({"status": "error", "provider": "Blacklane", "message": str(e)})
