#!/usr/bin/env python3
"""
amadeus_search.py — Amadeus flight and offer search via GDS API.

Credentials: creds/amadeus_credentials.json
             client_id + client_secret → OAuth2 client_credentials grant
             base_url: https://test.api.amadeus.com (test env confirmed 2026-06-14)
             Production: https://api.amadeus.com (swap base_url when approved)

Usage:
    from core.travel.amadeus_search import flight_offers, cheapest_date, city_search
    results = flight_offers("DEN", "FCO", "2026-12-17", adults=12)

Test confirmed: OAuth token retrieval working 2026-06-14.

Authority: SO-2026-05-04 §XII — expanded virtual realm.
"""

import json
import time
from pathlib import Path
from typing import Optional

import requests

ROOT = Path(__file__).parents[2]
CREDS_FILE = ROOT / "creds/amadeus_credentials.json"

_token_cache = {"token": None, "expires_at": 0.0}


def _load_creds() -> dict:
    return json.loads(CREDS_FILE.read_text())


def _get_token() -> str:
    if _token_cache["token"] and time.time() < _token_cache["expires_at"] - 60:
        return _token_cache["token"]
    creds = _load_creds()
    resp = requests.post(
        f"{creds['base_url']}/v1/security/oauth2/token",
        data={
            "grant_type": "client_credentials",
            "client_id": creds["client_id"],
            "client_secret": creds["client_secret"],
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    _token_cache["token"] = data["access_token"]
    _token_cache["expires_at"] = time.time() + data.get("expires_in", 1800)
    return _token_cache["token"]


def _base_url() -> str:
    return _load_creds()["base_url"]


def _headers() -> dict:
    return {"Authorization": f"Bearer {_get_token()}"}


def flight_offers(
    origin: str,
    destination: str,
    departure_date: str,
    adults: int = 1,
    return_date: Optional[str] = None,
    travel_class: str = "ECONOMY",
    max_results: int = 10,
    non_stop: bool = False,
    currency: str = "USD",
) -> list[dict]:
    """Search for flight offers via Amadeus Flight Offers Search v2.

    Args:
        origin: IATA airport code (e.g. "DEN")
        destination: IATA airport code (e.g. "FCO")
        departure_date: YYYY-MM-DD
        adults: Number of adult passengers
        return_date: YYYY-MM-DD for round trip (omit for one-way)
        travel_class: ECONOMY / PREMIUM_ECONOMY / BUSINESS / FIRST
        max_results: 1-250
        non_stop: True for direct flights only
        currency: ISO currency code

    Returns:
        List of offer dicts (price, itineraries, validating carrier, etc.)
    """
    params = {
        "originLocationCode": origin.upper(),
        "destinationLocationCode": destination.upper(),
        "departureDate": departure_date,
        "adults": adults,
        "travelClass": travel_class,
        "max": max_results,
        "currencyCode": currency,
    }
    if return_date:
        params["returnDate"] = return_date
    if non_stop:
        params["nonStop"] = "true"

    resp = requests.get(
        f"{_base_url()}/v2/shopping/flight-offers",
        headers=_headers(),
        params=params,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("data", [])


def cheapest_dates(
    origin: str,
    destination: str,
    departure_date: Optional[str] = None,
    duration: Optional[int] = None,
    one_way: bool = False,
    currency: str = "USD",
) -> list[dict]:
    """Flight Inspiration Search — find cheapest dates/destinations.

    Uses Amadeus /v1/shopping/flight-dates (cheapest dates for O&D pair).

    Returns:
        List of {type, origin, destination, departureDate, returnDate, price}
    """
    params = {
        "origin": origin.upper(),
        "destination": destination.upper(),
        "currencyCode": currency,
    }
    if departure_date:
        params["departureDate"] = departure_date
    if duration:
        params["duration"] = duration
    if one_way:
        params["oneWay"] = "true"

    resp = requests.get(
        f"{_base_url()}/v1/shopping/flight-dates",
        headers=_headers(),
        params=params,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("data", [])


def city_search(keyword: str, max_results: int = 5) -> list[dict]:
    """Search for city/airport codes by name keyword.

    Returns:
        List of {iataCode, name, address: {cityName, countryCode}}
    """
    resp = requests.get(
        f"{_base_url()}/v1/reference-data/locations",
        headers=_headers(),
        params={"keyword": keyword, "subType": "CITY,AIRPORT", "page[limit]": max_results},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("data", [])


def summarize_offer(offer: dict) -> dict:
    """Extract key facts from a flight offer object for Wing memos."""
    price = offer.get("price", {})
    carriers = offer.get("validatingAirlineCodes", [])
    itin = offer.get("itineraries", [{}])

    segments = []
    for it in itin:
        for seg in it.get("segments", []):
            dep = seg.get("departure", {})
            arr = seg.get("arrival", {})
            segments.append({
                "from": dep.get("iataCode"),
                "to": arr.get("iataCode"),
                "departs": dep.get("at"),
                "arrives": arr.get("at"),
                "carrier": seg.get("carrierCode"),
                "flight": seg.get("number"),
                "duration": seg.get("duration"),
                "stops": seg.get("numberOfStops", 0),
            })

    return {
        "total_price": price.get("grandTotal"),
        "base_price": price.get("base"),
        "currency": price.get("currency"),
        "validating_carriers": carriers,
        "segments": segments,
        "cabin": offer.get("travelerPricings", [{}])[0].get("fareDetailsBySegment", [{}])[0].get("cabin"),
    }


def wing_flight_brief(origin: str, destination: str, date: str, pax: int = 1, travel_class: str = "ECONOMY") -> str:
    """Return a concise Wing-format flight brief (3-5 best options) for Intel memos."""
    offers = flight_offers(origin, destination, date, adults=pax, travel_class=travel_class, max_results=5)
    if not offers:
        return f"No {travel_class} offers found for {origin}→{destination} on {date} ({pax} pax)."

    lines = [f"## Flight Brief — {origin}→{destination} · {date} · {pax} pax · {travel_class}\n"]
    for i, o in enumerate(offers, 1):
        s = summarize_offer(o)
        route = " → ".join(f"{sg['from']}{'-'+sg['to']}" for sg in s["segments"])
        stops = sum(sg.get("stops", 0) + (1 if j > 0 else 0) for j, sg in enumerate(s["segments"]))
        stop_label = "nonstop" if stops == 0 else f"{stops} stop{'s' if stops > 1 else ''}"
        lines.append(f"**[{i}] ${s['total_price']} {s['currency']}** — {route} · {stop_label} · {', '.join(s['validating_carriers'])}")

    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    # Quick test: DEN → FCO, 1 pax, economy
    args = sys.argv[1:]
    orig = args[0] if len(args) > 0 else "DEN"
    dest = args[1] if len(args) > 1 else "FCO"
    date = args[2] if len(args) > 2 else "2026-12-17"
    print(wing_flight_brief(orig, dest, date, pax=1))
