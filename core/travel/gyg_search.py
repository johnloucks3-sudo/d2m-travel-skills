#!/usr/bin/env python3
"""
gyg_search.py — GetYourGuide excursion and activity search for D2M clients.

STATUS: STUB — Partner credentials required.
  1. Apply to GYG Partner Program: https://partner.getyourguide.com/
  2. Get API key + partner access token
  3. Set GYG_API_KEY in .env or creds/getyourguide_credentials.json
  4. This wrapper is ready to activate.

GYG coverage: 100,000+ tours in 11,000+ destinations.
D2M use: Alternative to Viator for shore excursion research. Compare pricing.

Authority: SO-2026-05-04 §XII.
"""

import json
import os
from pathlib import Path
from typing import Optional

import requests

ROOT = Path(__file__).parents[2]
CREDS_FILE = ROOT / "creds/getyourguide_credentials.json"
API_BASE = "https://api.getyourguide.com/1"


def _get_key() -> str:
    key = os.environ.get("GYG_API_KEY", "")
    if not key and CREDS_FILE.exists():
        data = json.loads(CREDS_FILE.read_text())
        key = data.get("api_key", "")
    if not key:
        raise RuntimeError(
            "GYG_API_KEY not set.\n"
            "Apply: https://partner.getyourguide.com/\n"
            "Set key in creds/getyourguide_credentials.json or .env"
        )
    return key


def _headers() -> dict:
    return {
        "X-Access-Token": _get_key(),
        "Accept": "application/json",
    }


def search_tours(
    location_id: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    duration_min: Optional[int] = None,
    duration_max: Optional[int] = None,
    adults: int = 2,
    sort_by: str = "rating",
    limit: int = 20,
    currency: str = "USD",
) -> list[dict]:
    """Search for tours at a location.

    Args:
        location_id: GYG location ID (use location_lookup() to find)
        start_date: YYYY-MM-DD
        end_date: YYYY-MM-DD
        duration_min/max: Duration in minutes
        adults: Number of participants
        sort_by: rating / price / newest
        limit: Results to return (1-100)
        currency: ISO code

    Returns:
        List of tour/activity dicts
    """
    params = {
        "location_ids[]": location_id,
        "adults": adults,
        "sort_by": sort_by,
        "per_page": limit,
        "currency": currency,
    }
    if start_date:
        params["date_from"] = start_date
    if end_date:
        params["date_to"] = end_date
    if duration_min:
        params["duration_from"] = duration_min * 60
    if duration_max:
        params["duration_to"] = duration_max * 60

    resp = requests.get(f"{API_BASE}/activities", headers=_headers(), params=params, timeout=30)
    resp.raise_for_status()
    return resp.json().get("data", {}).get("activities", [])


def location_lookup(query: str) -> list[dict]:
    """Search for GYG location IDs by name."""
    resp = requests.get(
        f"{API_BASE}/locations",
        headers=_headers(),
        params={"q": query, "type": "city", "per_page": 5},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("data", {}).get("locations", [])


def wing_tour_brief(city: str, date: str, adults: int = 2) -> str:
    """Quick Wing-format tour brief comparing to cruise line prices."""
    locations = location_lookup(city)
    if not locations:
        return f"GYG: '{city}' not found."
    loc = locations[0]
    loc_id = loc.get("id")
    loc_name = loc.get("name", city)

    tours = search_tours(loc_id, start_date=date, end_date=date, adults=adults, limit=10)
    if not tours:
        return f"GYG: No tours found in {loc_name} for {date}."

    lines = [f"## GYG Tours — {loc_name} · {date} · {adults} pax\n"]
    for i, t in enumerate(tours[:10], 1):
        price = t.get("price", {}).get("values", {}).get("amount", "?")
        rating = t.get("reviews", {}).get("rating", "?")
        review_count = t.get("reviews", {}).get("count", 0)
        title = t.get("title", "?")
        duration = t.get("duration", {}).get("value", "?")
        unit = t.get("duration", {}).get("label", "")
        lines.append(f"**[{i}] {title}**")
        lines.append(f"    ${price}/person · ⭐ {rating} ({review_count} reviews) · {duration} {unit}")

    return "\n".join(lines)


if __name__ == "__main__":
    print("GYG stub — partner credentials required.")
    print("Apply at: https://partner.getyourguide.com/")
