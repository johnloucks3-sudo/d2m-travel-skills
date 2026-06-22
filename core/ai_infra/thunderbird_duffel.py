#!/usr/bin/env python3
"""
thunderbird_duffel.py — Duffel flight search adapter for Thunderbird.
Duffel is the only self-serve NDC+GDS flight API available to independent advisors
without volume minimums. 300+ airlines, per-booking fee model.

Registration: https://duffel.com — free sandbox, then production approval.
Key: DUFFEL_API_KEY in .env
Docs: https://duffel.com/docs

Use cases:
- Spencer group DEN-FCO 12-pax air quote (MISSION-421)
- Routine routing research for clients (no manual airline group desk call)
- Price range checks for client proposals

Usage:
    from core.ai_infra.thunderbird_duffel import search_flights, get_offer_details

    # Search for flights
    offers = search_flights(
        origin="DEN", destination="FCO",
        departure_date="2026-10-15",
        passengers=12,
        cabin_class="business",
    )
    for offer in offers[:3]:
        print(f"{offer['airline']} — ${offer['total_amount']} {offer['currency']}")
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

_ENV = Path(__file__).parent.parent.parent / ".env"
_BASE_URL = "https://api.duffel.com"
_SANDBOX_URL = "https://api.duffel.com"


def _get_key() -> str:
    key = os.environ.get("DUFFEL_API_KEY", "")
    if not key:
        try:
            for line in _ENV.read_text().splitlines():
                if line.startswith("DUFFEL_API_KEY=") and not line.startswith("#"):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
        except Exception:
            pass
    return key


def _request(method: str, path: str, body: dict | None = None) -> dict:
    key = _get_key()
    if not key:
        raise ValueError("DUFFEL_API_KEY not set — register at https://duffel.com")

    url = f"{_BASE_URL}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Duffel-Version": "v2",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()[:500]
        raise RuntimeError(f"Duffel API error {e.code}: {error_body}")


def search_flights(
    origin: str,
    destination: str,
    departure_date: str,
    passengers: int = 1,
    cabin_class: str = "economy",
    return_date: str | None = None,
    max_results: int = 10,
) -> list[dict]:
    """
    Search for flights and return simplified offer list.

    Args:
        origin: IATA code (e.g. "DEN")
        destination: IATA code (e.g. "FCO")
        departure_date: ISO date (e.g. "2026-10-15")
        passengers: number of adult passengers
        cabin_class: "economy" | "premium_economy" | "business" | "first"
        return_date: ISO date for round trip (None = one-way)
        max_results: max offers to return

    Returns:
        List of simplified offer dicts:
        {offer_id, airline, airline_name, total_amount, currency, stops,
         departure_time, arrival_time, duration, segments}
    """
    slices = [{"origin": origin, "destination": destination, "departure_date": departure_date}]
    if return_date:
        slices.append({"origin": destination, "destination": origin, "departure_date": return_date})

    payload = {
        "data": {
            "slices": slices,
            "passengers": [{"type": "adult"} for _ in range(passengers)],
            "cabin_class": cabin_class,
            "max_connections": 1,
        }
    }

    # Step 1: Create offer request
    offer_request = _request("POST", "/air/offer_requests?return_offers=true", payload)
    offers_raw = offer_request.get("data", {}).get("offers", [])

    # Step 2: Simplify offers
    simplified = []
    for offer in offers_raw[:max_results]:
        slices_out = offer.get("slices", [])
        first_slice = slices_out[0] if slices_out else {}
        segments = first_slice.get("segments", [])
        first_seg = segments[0] if segments else {}
        last_seg = segments[-1] if segments else {}

        simplified.append({
            "offer_id": offer.get("id"),
            "airline": (first_seg.get("marketing_carrier") or {}).get("iata_code", "?"),
            "airline_name": (first_seg.get("marketing_carrier") or {}).get("name", "?"),
            "total_amount": offer.get("total_amount"),
            "currency": offer.get("total_currency"),
            "stops": len(segments) - 1,
            "departure_time": (first_seg.get("departing_at") or "")[:16],
            "arrival_time": (last_seg.get("arriving_at") or "")[:16],
            "duration": first_slice.get("duration"),
            "segments": [
                {
                    "flight": f"{(s.get('marketing_carrier') or {}).get('iata_code','?')}{s.get('marketing_carrier_flight_number','?')}",
                    "from": s.get("origin", {}).get("iata_code", "?"),
                    "to": s.get("destination", {}).get("iata_code", "?"),
                    "dep": (s.get("departing_at") or "")[:16],
                    "arr": (s.get("arriving_at") or "")[:16],
                }
                for s in segments
            ],
        })

    return simplified


def get_offer_details(offer_id: str) -> dict:
    """Get full details for a specific offer by ID."""
    result = _request("GET", f"/air/offers/{offer_id}")
    return result.get("data", {})


def create_order(offer_id: str, passengers: list[dict]) -> dict:
    """
    Book a flight. Commander gate required — Wing does not call this autonomously.

    Args:
        offer_id: Offer ID from search_flights()
        passengers: List of passenger dicts:
            [{
                "type": "adult",
                "given_name": "John",
                "family_name": "Loucks",
                "email": "johnloucks3@gmail.com",
                "phone_number": "+17192910742",
                "born_on": "1952-01-01",
                "title": "mr",
                "gender": "m",
                "passport": {"number": "...", "expires_on": "...", "country": "US"},
            }]
    """
    payload = {
        "data": {
            "type": "instant",
            "selected_offers": [offer_id],
            "passengers": passengers,
            "payments": [{"type": "balance", "currency": "USD", "amount": "0"}],
        }
    }
    result = _request("POST", "/air/orders", payload)
    return result.get("data", {})


def search_for_brief(
    origin: str,
    destination: str,
    departure_date: str,
    passengers: int,
    cabin_class: str = "economy",
) -> str:
    """Format flight search results as a plain-text brief for Commander."""
    try:
        offers = search_flights(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            passengers=passengers,
            cabin_class=cabin_class,
            max_results=5,
        )
    except Exception as e:
        return f"Duffel search error: {e}"

    if not offers:
        return f"No flights found: {origin}→{destination} on {departure_date} ({passengers} pax, {cabin_class})"

    lines = [f"FLIGHTS: {origin}→{destination} | {departure_date} | {passengers} pax | {cabin_class.upper()}"]
    for i, o in enumerate(offers, 1):
        stops = "nonstop" if o["stops"] == 0 else f"{o['stops']} stop(s)"
        lines.append(
            f"{i}. {o['airline_name']} ({o['airline']}) — ${o['total_amount']} {o['currency']} "
            f"| {stops} | dep {o['departure_time']} arr {o['arrival_time']}"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    key = _get_key()
    if not key:
        print("DUFFEL_API_KEY not set.")
        print("Register at: https://duffel.com")
        print("Then add DUFFEL_API_KEY=duffel_test_... to .env")
        sys.exit(1)

    print(f"Duffel API key configured: {key[:12]}...")
    print("\nExample: Spencer group DEN-FCO 12-pax business class")
    print("search_for_brief('DEN', 'FCO', '2026-10-15', 12, 'business')")
    result = search_for_brief("DEN", "FCO", "2026-10-15", 12, "business")
    print(result)
