"""
Dreams2Memories Google Flights Search Module
==============================================

Flight search via the "Google Flights" API (RapidAPI-hosted, provider:
DataCrawler, host google-flights2.p.rapidapi.com). Self-serve, free-tier
(150 req/month, 1000 req/hour, no payment method required) — subscribed
2026-07-09 as the fourth flight-data source, alongside Amadeus
(search_flights), Centrav B2B (search_centrav_flights), and Kiwi.com
(search_kiwi_flights / thunderbird_kiwi_search.py).

Why this path, not Google's own product: Google Flights has no public
self-serve consumer API. Same pattern as the Kiwi build the same session —
the identical data (scraped live from google.com/travel/flights) is hosted
self-serve on RapidAPI by a third-party wrapper. Uses the SAME RapidAPI
account/application key already in .env as RAPIDAPI_KEY (d2mtravel2026 /
d2mconcierge@gmail.com) — no new signup needed, just a new subscription on
the existing account. Subscribed plan: Basic ($0/mo, 150 requests/month
hard limit, 1000 req/hour rate limit) — confirmed "Total due today: Free",
no card required, on the actual RapidAPI checkout screen.

Advantage over Kiwi: this API takes plain IATA codes (DEN, ORD) directly,
not place slugs — no separate resolve-to-slug step needed for known
airports. searchAirport() is still provided for fuzzy/city-name lookups
(e.g. resolving "Denver" when the caller doesn't have the IATA code).

Real endpoints confirmed live 2026-07-09 (curl-tested, not assumed):
  GET /api/v1/searchFlights   (one-way when return_date omitted, round-trip
                                when supplied — same endpoint, one param)
  GET /api/v1/searchAirport
  GET /api/v1/getLanguages
  GET /api/v1/getLocations
  GET /api/v1/getCurrency
  GET /api/v1/checkServer

Response shape: {"status": bool, "message": str, "timestamp": int,
"data": {"itineraries": {"topFlights": [...], "otherFlights": [...]},
"priceHistory": ...}} for search; {"status", "message", "timestamp",
"data": [...]} for searchAirport/getLocations/etc.

Proven live 2026-07-09: DEN->ORD one-way 2026-08-15, $80, American AA 2771,
nonstop, 2h44m (topFlights[0]). Round-trip DEN->ORD 2026-08-15/2026-08-22,
$130, same nonstop outbound.
"""

import json
import os
import requests
from typing import Optional

from pydantic import Field
from mcp.server.fastmcp import FastMCP

RAPIDAPI_HOST = "google-flights2.p.rapidapi.com"
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


def search_airport(query: str) -> list[dict]:
    """Resolve a free-text city/airport name to IATA code(s) via searchAirport.
    Returns a list of place groups; each has a "list" of {id (IATA code),
    title, city, ...} entries. Only needed when the caller doesn't already
    know the IATA code — searchFlights takes IATA codes directly."""
    r = requests.get(
        f"{BASE_URL}/searchAirport",
        params={"query": query},
        headers=_headers(),
        timeout=15,
    )
    r.raise_for_status()
    return r.json().get("data", [])


def search_flights(
    departure_id: str,
    arrival_id: str,
    outbound_date: str,
    return_date: Optional[str] = None,
    travel_class: str = "ECONOMY",
    adults: int = 1,
    children: int = 0,
    infant_on_lap: int = 0,
    infant_in_seat: int = 0,
    show_hidden: int = 1,
    currency: str = "USD",
    language_code: str = "en-US",
    country_code: str = "US",
    search_type: str = "best",
) -> dict:
    """
    Flight search — one-way when return_date is omitted, round-trip when
    supplied (same endpoint, controlled by that one param).
    departure_id/arrival_id: IATA codes, e.g. "DEN", "ORD".
    outbound_date/return_date: "YYYY-MM-DD".
    travel_class: ECONOMY | PREMIUM_ECONOMY | BUSINESS | FIRST.
    search_type: "best" (balanced price/duration/convenience) or "cheap"
    (lowest cost, possibly longer layovers).
    Returns the raw API response dict — data.itineraries has "topFlights"
    and "otherFlights" (each a list of itinerary dicts with price/flights).
    """
    params = {
        "departure_id": departure_id,
        "arrival_id": arrival_id,
        "outbound_date": outbound_date,
        "travel_class": travel_class,
        "adults": adults,
        "children": children,
        "infant_on_lap": infant_on_lap,
        "infant_in_seat": infant_in_seat,
        "show_hidden": show_hidden,
        "currency": currency,
        "language_code": language_code,
        "country_code": country_code,
        "search_type": search_type,
    }
    if return_date:
        params["return_date"] = return_date
    r = requests.get(
        f"{BASE_URL}/searchFlights",
        params=params,
        headers=_headers(),
        timeout=60,
    )
    r.raise_for_status()
    return r.json()


def cheapest_itinerary(search_result: dict) -> Optional[dict]:
    """Convenience: pull the cheapest itinerary out of a search response
    (checks both topFlights and otherFlights). otherFlights can contain
    price: "unavailable" (string) instead of a number — those are excluded
    rather than crashing the min() comparison."""
    itins = search_result.get("data", {}).get("itineraries", {})
    all_itins = itins.get("topFlights", []) + itins.get("otherFlights", [])
    priced = [i for i in all_itins if isinstance(i.get("price"), (int, float))]
    if not priced:
        return None
    return min(priced, key=lambda i: i["price"])


def register_google_flights_tools(mcp: FastMCP):
    """Register Google Flights search tools with the MCP server."""

    @mcp.tool(
        name="search_google_flights",
        annotations={"title": "Search Flights (Google Flights)", "readOnlyHint": True},
    )
    async def search_google_flights_tool(
        departure_id: str = Field(..., description="Origin IATA code, e.g. 'DEN'. Use google_flights_search_airport if unsure of the code."),
        arrival_id: str = Field(..., description="Destination IATA code, e.g. 'ORD'."),
        outbound_date: str = Field(..., description="Departure date YYYY-MM-DD."),
        return_date: Optional[str] = Field(None, description="Return date YYYY-MM-DD for round-trip. Omit for one-way."),
        travel_class: str = Field("ECONOMY", description="ECONOMY | PREMIUM_ECONOMY | BUSINESS | FIRST"),
        adults: int = Field(1, description="Number of adult passengers"),
        currency: str = Field("USD", description="Price currency code (default USD)"),
        search_type: str = Field("best", description="'best' (balanced) or 'cheap' (lowest cost, may have longer layovers)"),
        list_all_top: bool = Field(False, description="If true, also return every itinerary in Google's 'top' (recommended) set, not just the single cheapest — use this to find a specific carrier/nonstop that isn't the lowest-price option."),
    ) -> str:
        """Search flights via the Google Flights API (RapidAPI-hosted, free tier).

        Fourth flight-data source alongside Amadeus (search_flights), Centrav
        B2B (search_centrav_flights), and Kiwi.com (search_kiwi_flights) — no
        scraping, no bot-wall, no browser automation. Takes plain IATA codes
        directly (no slug-resolution step). Free tier: 150 requests/month,
        1000/hour (hard cap).

        USAGE DISCIPLINE (same as Kiwi, Commander directive 2026-07-09): call
        this synchronously/on-demand only. Never wire it into a background
        sweep, headless probe, or automated loop — Amadeus/Centrav are the
        default sources when they're already working; this is a
        fallback/cross-check, and the 150/month cap is a hard limit.

        Returns itinerary counts and the cheapest option with full routing.
        """
        try:
            result = search_flights(
                departure_id, arrival_id, outbound_date, return_date,
                travel_class, adults, currency=currency, search_type=search_type,
            )
            itins = result.get("data", {}).get("itineraries", {})
            out = {
                "top_count": len(itins.get("topFlights", [])),
                "other_count": len(itins.get("otherFlights", [])),
                "currency": currency,
            }
            cheapest = cheapest_itinerary(result)
            if cheapest:
                segs = cheapest.get("flights", [])
                out["cheapest"] = {
                    "price": cheapest.get("price"),
                    "currency": currency,
                    "carrier": segs[0]["airline"] if segs else None,
                    "flight_number": segs[0].get("flight_number") if segs else None,
                    "path": " -> ".join(
                        [segs[0]["departure_airport"]["airport_code"]] +
                        [s["arrival_airport"]["airport_code"] for s in segs]
                    ) if segs else None,
                    "stops": cheapest.get("stops"),
                    "duration": cheapest.get("duration", {}).get("text"),
                    "departure_time": cheapest.get("departure_time"),
                    "arrival_time": cheapest.get("arrival_time"),
                }
            else:
                out["cheapest"] = None
            if list_all_top:
                top_flights = itins.get("topFlights", [])
                out["top_flights"] = [
                    {
                        "price": it.get("price"),
                        "carrier": it["flights"][0]["airline"] if it.get("flights") else None,
                        "flight_number": it["flights"][0].get("flight_number") if it.get("flights") else None,
                        "path": " -> ".join(
                            [it["flights"][0]["departure_airport"]["airport_code"]] +
                            [s["arrival_airport"]["airport_code"] for s in it["flights"]]
                        ) if it.get("flights") else None,
                        "stops": it.get("stops"),
                        "duration": it.get("duration", {}).get("text"),
                    }
                    for it in top_flights
                ]
            return json.dumps(out, indent=2, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool(
        name="google_flights_search_airport",
        annotations={"title": "Google Flights Airport Search", "readOnlyHint": True},
    )
    async def google_flights_search_airport_tool(
        query: str = Field(..., description="Free-text city/airport name to resolve to an IATA code, e.g. 'Denver'"),
    ) -> str:
        """Resolve a free-text city/airport name to the IATA code(s)
        search_google_flights expects. Only needed when the code isn't
        already known."""
        try:
            return json.dumps(search_airport(query), indent=2, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})


if __name__ == "__main__":
    # Smoke test — mirrors the live curl test run 2026-07-09.
    result = search_flights("DEN", "ORD", "2026-08-15")
    itins = result.get("data", {}).get("itineraries", {})
    print(f"status={result.get('status')} topFlights={len(itins.get('topFlights', []))} otherFlights={len(itins.get('otherFlights', []))}")
    cheapest = cheapest_itinerary(result)
    if cheapest:
        segs = cheapest.get("flights", [])
        path = " -> ".join(
            [segs[0]["departure_airport"]["airport_code"]] +
            [s["arrival_airport"]["airport_code"] for s in segs]
        )
        stops = f"{cheapest.get('stops')} stop(s)" if cheapest.get("stops") else "nonstop"
        print(
            f"cheapest: {segs[0]['airline']} {segs[0]['flight_number']} {path} ({stops}) "
            f"${cheapest['price']} USD, duration {cheapest.get('duration', {}).get('text')}"
        )
