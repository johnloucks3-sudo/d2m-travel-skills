"""
Dreams2Memories Kiwi.com Flight Search Module
==============================================

Flight search via the Kiwi.com Flights API (RapidAPI-hosted, provider:
elis-lab-2 "kiwi-com-flights-api"). Self-serve, free-tier (300 req/month,
no payment method required) — signed up 2026-07-09 as a route around
Kayak/United's bot-defense/silent-block issues found the same session
(see output/wave_scan/wave3_20260709/08_travel_apis_deep.md and Wave 4
verified notes: Skyscanner is sales-gated, Kiwi's own Tequila portal
requires an affiliates@kiwi.com approval — this RapidAPI-hosted wrapper
has neither gate).

Key stored in .env as RAPIDAPI_KEY. Subscribed plan: Basic ($0/mo,
300 requests/month hard limit, 1000 req/hour rate limit).

Real endpoints confirmed live 2026-07-09 (curl-tested, not assumed):
  GET /api/v1/flights/search-oneway
  GET /api/v1/flights/search-roundtrip
  GET /api/v1/flights/multi-city
  GET /api/v1/flights/price-map
  GET /api/v1/flights/price-graph
  GET /api/v1/flights/price-calendar
  GET /api/v1/flights/nomad
  GET /api/v1/flights/seat-info
  GET /api/v1/places/autocomplete

NOTE ON SOURCE/DESTINATION FORMAT: this API takes slugs like
"denver-colorado-united-states", not IATA codes. Use place_autocomplete()
to resolve a free-text query to the correct slug before searching if
unsure — IATA-code-shaped guesses (e.g. "denver") may not match.
"""

import json
import os
import requests
from typing import Optional

from pydantic import Field
from mcp.server.fastmcp import FastMCP

RAPIDAPI_HOST = "kiwi-com-flights-api.p.rapidapi.com"
BASE_URL = f"https://{RAPIDAPI_HOST}/api/v1"


def _headers() -> dict:
    key = os.environ.get("RAPIDAPI_KEY", "")
    if not key:
        raise RuntimeError("RAPIDAPI_KEY not set in environment/.env")
    return {
        "Content-Type": "application/json",
        "x-rapidapi-host": RAPIDAPI_HOST,
        "x-rapidapi-key": key,
    }


def place_autocomplete(query: str) -> list[dict]:
    """Resolve a free-text place name to the slug this API expects."""
    r = requests.get(
        f"{BASE_URL}/places/autocomplete",
        params={"query": query},
        headers=_headers(),
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def search_oneway(
    source_slug: str,
    destination_slug: str,
    departure_date: str,
    adults: int = 1,
    currency: str = "USD",
    locale: str = "en",
) -> dict:
    """
    One-way flight search.
    source_slug/destination_slug: place slugs, e.g. "denver-colorado-united-states"
      (use place_autocomplete() first if unsure of the exact slug).
    departure_date: "YYYY-MM-DD" or a range "YYYY-MM-DD..YYYY-MM-DD".
    Returns the raw API response dict — top-level keys include
    "count" (int) and "itineraries" (list, each with price/segments/carrier).
    """
    r = requests.get(
        f"{BASE_URL}/flights/search-oneway",
        params={
            "source": source_slug,
            "destination": destination_slug,
            "departure_date": departure_date,
            "adults": adults,
            "currency": currency,
            "locale": locale,
        },
        headers=_headers(),
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def search_roundtrip(
    source_slug: str,
    destination_slug: str,
    departure_date: str,
    return_date: str,
    adults: int = 1,
    currency: str = "USD",
    locale: str = "en",
) -> dict:
    """Round-trip flight search. Same slug/date rules as search_oneway()."""
    r = requests.get(
        f"{BASE_URL}/flights/search-roundtrip",
        params={
            "source": source_slug,
            "destination": destination_slug,
            "departure_date": departure_date,
            "return_date": return_date,
            "adults": adults,
            "currency": currency,
            "locale": locale,
        },
        headers=_headers(),
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def cheapest_itinerary(search_result: dict) -> Optional[dict]:
    """Convenience: pull the cheapest itinerary out of a search response."""
    itins = search_result.get("itineraries", [])
    if not itins:
        return None
    return min(itins, key=lambda i: i.get("price", {}).get("amount", float("inf")))


def register_kiwi_search_tools(mcp: FastMCP):
    """Register Kiwi.com flight search tools with the MCP server."""

    @mcp.tool(
        name="search_kiwi_flights",
        annotations={"title": "Search Flights (Kiwi.com)", "readOnlyHint": True},
    )
    async def search_kiwi_flights(
        source: str = Field(..., description="Origin place slug, e.g. 'denver-colorado-united-states'. Use kiwi_place_autocomplete if unsure of the exact slug."),
        destination: str = Field(..., description="Destination place slug, e.g. 'chicago-illinois-united-states'."),
        departure_date: str = Field(..., description="Departure date YYYY-MM-DD, or a range 'YYYY-MM-DD..YYYY-MM-DD'."),
        return_date: Optional[str] = Field(None, description="Return date YYYY-MM-DD for round-trip. Omit for one-way."),
        adults: int = Field(1, description="Number of adult passengers"),
        currency: str = Field("USD", description="Price currency code (default USD)"),
    ) -> str:
        """Search flights via the Kiwi.com Flights API (RapidAPI-hosted, free tier).

        Third flight-data source alongside Amadeus (search_flights) and Centrav
        B2B (search_centrav_flights) — no scraping, no bot-wall, no browser
        automation. Best for catching LCC/connecting-flight routes the other
        two sources miss. Free tier: 300 requests/month, 1000/hour (hard cap).

        USAGE DISCIPLINE (Commander directive 2026-07-09): call this
        synchronously/on-demand only. Never wire it into a background sweep,
        headless probe, or automated loop — Amadeus/Centrav are the default
        sources when they're already working; this is the fallback/cross-check.

        Returns itinerary count and the cheapest option with full routing.
        """
        try:
            if return_date:
                result = search_roundtrip(source, destination, departure_date, return_date, adults, currency)
            else:
                result = search_oneway(source, destination, departure_date, adults, currency)
            cheapest = cheapest_itinerary(result)
            out = {"count": result.get("count", 0), "currency": currency}
            if cheapest:
                segs = cheapest["outbound"]["segments"]
                out["cheapest"] = {
                    "price": cheapest["price"]["amount"],
                    "currency": cheapest["price"]["currency"],
                    "carrier": segs[0]["carrier"]["name"],
                    "path": " -> ".join(
                        [segs[0]["source"]["station"]["code"]] + [s["destination"]["station"]["code"] for s in segs]
                    ),
                    "stops": len(segs) - 1,
                    "departure_local": segs[0]["source"].get("local_time"),
                }
            else:
                out["cheapest"] = None
            return json.dumps(out, indent=2, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool(
        name="kiwi_place_autocomplete",
        annotations={"title": "Kiwi.com Place Autocomplete", "readOnlyHint": True},
    )
    async def kiwi_place_autocomplete(
        query: str = Field(..., description="Free-text place name to resolve to a Kiwi.com place slug, e.g. 'Denver'"),
    ) -> str:
        """Resolve a free-text place name to the exact slug search_kiwi_flights expects."""
        try:
            return json.dumps(place_autocomplete(query), indent=2, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})


if __name__ == "__main__":
    # Smoke test — mirrors the live curl test run 2026-07-09.
    result = search_oneway(
        "denver-colorado-united-states",
        "chicago-illinois-united-states",
        "2026-08-15",
    )
    print(f"count={result.get('count')}")
    cheapest = cheapest_itinerary(result)
    if cheapest:
        segs = cheapest["outbound"]["segments"]
        path = " -> ".join(
            [segs[0]["source"]["station"]["code"]] + [s["destination"]["station"]["code"] for s in segs]
        )
        stops = f"{len(segs)-1} stop(s)" if len(segs) > 1 else "nonstop"
        print(
            f"cheapest: {segs[0]['carrier']['name']} {path} ({stops}) "
            f"${cheapest['price']['amount']} {cheapest['price']['currency']}"
        )
