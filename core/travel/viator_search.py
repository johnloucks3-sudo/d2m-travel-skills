#!/usr/bin/env python3
"""
viator_search.py — Viator (TripAdvisor) excursion search for D2M clients.

STATUS: STUB — API key required.
  1. Join Viator Partner Program: https://partnerresources.viator.com/
  2. Get API key → set VIATOR_API_KEY in .env or creds/viator_credentials.json
  3. This wrapper is ready to activate.

Viator coverage: 300,000+ tours and activities worldwide.
D2M use: Kuklinski Panama Canal shore excursions (Dec 2026), pre/post activities.
Compare against cruise-line excursions — typically 35-50% cheaper.

Authority: SO-2026-05-04 §XII.
"""

import json
import os
from pathlib import Path
from typing import Optional

import requests

ROOT = Path(__file__).parents[2]
CREDS_FILE = ROOT / "creds/viator_credentials.json"
API_BASE = "https://api.viator.com/partner"


def _get_key() -> str:
    key = os.environ.get("VIATOR_API_KEY", "")
    if not key and CREDS_FILE.exists():
        data = json.loads(CREDS_FILE.read_text())
        key = data.get("api_key", "")
    if not key:
        raise RuntimeError(
            "VIATOR_API_KEY not set.\n"
            "1. Join: https://partnerresources.viator.com/\n"
            "2. Set key in creds/viator_credentials.json or .env"
        )
    return key


def _headers() -> dict:
    return {
        "exp-api-key": _get_key(),
        "Accept": "application/json;version=2.0",
        "Content-Type": "application/json",
    }


def search_products(
    destination_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tag_ids: Optional[list[int]] = None,
    max_results: int = 20,
    sort_by: str = "REVIEW_AVG_RATING",
    currency: str = "USD",
) -> list[dict]:
    """Search Viator products at a destination.

    Args:
        destination_id: Viator destination ref (e.g. "3766" for Panama City)
        start_date: YYYY-MM-DD availability start
        end_date: YYYY-MM-DD availability end
        tag_ids: Optional tag filter (e.g. 21972 = shore excursions)
        max_results: 1-50 per page
        sort_by: REVIEW_AVG_RATING / PRICE / POPULARITY
        currency: ISO currency code

    Returns:
        List of product dicts from Viator API v2
    """
    payload = {
        "filtering": {"destination": destination_id},
        "sorting": {"sort": sort_by, "order": "DESCENDING"},
        "pagination": {"start": 1, "count": max_results},
        "currency": currency,
    }
    if start_date and end_date:
        payload["filtering"]["dateRange"] = {"from": start_date, "to": end_date}
    if tag_ids:
        payload["filtering"]["tags"] = tag_ids

    resp = requests.post(f"{API_BASE}/products/search", headers=_headers(), json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json().get("products", [])


def get_availability(product_code: str, travel_date: str, pax: int = 2, currency: str = "USD") -> dict:
    """Check availability and pricing for a specific product on a date."""
    payload = {
        "productCode": product_code,
        "travelDate": travel_date,
        "paxMix": [{"ageBand": "ADULT", "numberOfTravelers": pax}],
        "currency": currency,
    }
    resp = requests.post(f"{API_BASE}/availability/schedules/check", headers=_headers(), json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def destination_lookup(search_term: str) -> list[dict]:
    """Search for Viator destination IDs by name."""
    resp = requests.get(
        f"{API_BASE}/v1/taxonomy/destinations",
        headers=_headers(),
        params={"searchTerm": search_term, "startIndex": 0, "count": 10},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("data", {}).get("destinations", [])


def shore_excursion_search(port_city: str, date: str, pax: int = 2, max_results: int = 10) -> str:
    """Wing convenience: shore excursion brief for a cruise port."""
    dest_results = destination_lookup(port_city)
    if not dest_results:
        return f"Destination '{port_city}' not found in Viator."
    dest_id = str(dest_results[0].get("destinationId", ""))
    dest_name = dest_results[0].get("destinationName", port_city)

    products = search_products(
        dest_id,
        start_date=date,
        end_date=date,
        tag_ids=[21972],
        max_results=max_results,
        sort_by="POPULARITY",
    )

    lines = [f"## Viator Shore Excursions — {dest_name} · {date} · {pax} pax\n"]
    for i, p in enumerate(products[:max_results], 1):
        price = p.get("pricing", {}).get("summary", {}).get("fromPrice", "?")
        rating = p.get("reviews", {}).get("combinedAverageRating", "?")
        title = p.get("title", "?")
        code = p.get("productCode", "?")
        lines.append(f"**[{i}] {title}**")
        lines.append(f"    Code: {code} · From ${price}/person · ⭐ {rating}")

    return "\n".join(lines) if products else f"No shore excursions found for {dest_name} on {date}."


if __name__ == "__main__":
    print("Viator stub — API key required. Set in creds/viator_credentials.json.")
    print("Test: python3 -c \"from core.travel.viator_search import shore_excursion_search; print(shore_excursion_search('Panama City', '2026-12-18', pax=6))\"")
