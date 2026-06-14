#!/usr/bin/env python3
"""
hotelbeds_hotel_search.py — Hotelbeds hotel availability and pricing.

Hotelbeds is a B2B hotel marketplace (wholesaler). Access via API key + secret.
Credentials: creds/hotelbeds_credentials.json
  api_key: ***REMOVED-SECRET*** (live key)
  api_secret: 87bd4dd67d
  base_url: https://api.test.hotelbeds.com (test env — swap for prod)

Auth: X-Api-Key header + X-Signature (SHA-256 HMAC of key+secret+epoch)

Coverage: 180,000+ properties worldwide. Strong in Europe, Asia, Caribbean.
D2M use cases: pre/post cruise hotel search for clients (Kuklinski Panama City/FLL, etc.)

Authority: SO-2026-05-04 §XII.
"""

import hashlib
import json
import time
from pathlib import Path
from typing import Optional

import requests

ROOT = Path(__file__).parents[2]
CREDS_FILE = ROOT / "creds/hotelbeds_credentials.json"


def _load_creds() -> dict:
    return json.loads(CREDS_FILE.read_text())


def _headers() -> dict:
    creds = _load_creds()
    ts = str(int(time.time()))
    sig_raw = creds["api_key"] + creds["api_secret"] + ts
    signature = hashlib.sha256(sig_raw.encode()).hexdigest()
    return {
        "Api-Key": creds["api_key"],
        "X-Signature": signature,
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
    }


def _base(path: str) -> str:
    return _load_creds()["base_url"] + path


def hotel_availability(
    destination_code: str,
    check_in: str,
    check_out: str,
    adults: int = 2,
    children: int = 0,
    rooms: int = 1,
    max_results: int = 20,
    min_category: int = 3,
) -> list[dict]:
    """Search hotel availability at a destination.

    Args:
        destination_code: Hotelbeds destination code (e.g. "PMY" for Panama City)
        check_in: YYYY-MM-DD
        check_out: YYYY-MM-DD
        adults: Adults per room
        children: Children per room
        rooms: Number of rooms
        max_results: Hotels to return (1-1000)
        min_category: Minimum star category (3-5)

    Returns:
        List of hotel dicts with rooms, rates, total price
    """
    payload = {
        "stay": {"checkIn": check_in, "checkOut": check_out},
        "occupancies": [{"rooms": rooms, "adults": adults, "children": children}],
        "destination": {"code": destination_code},
        "filter": {"minCategory": min_category, "maxRooms": max_results},
        "language": "ENG",
    }
    resp = requests.post(
        _base("/hotel-api/1.0/hotels"),
        headers=_headers(),
        json=payload,
        timeout=45,
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("hotels", {}).get("hotels", [])


def hotel_details(hotel_codes: list[int], language: str = "ENG") -> list[dict]:
    """Get detailed hotel info (amenities, images, location) for a list of hotel codes."""
    codes_str = ",".join(str(c) for c in hotel_codes)
    resp = requests.get(
        _base("/hotel-content-api/1.0/hotels"),
        headers=_headers(),
        params={"codes": codes_str, "language": language, "fields": "all"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("hotels", [])


def destinations_search(keyword: str, country_code: Optional[str] = None) -> list[dict]:
    """Look up Hotelbeds destination codes by keyword or country.

    Returns: List of {code, name, countryCode, isoCode, zones}
    """
    params = {"fields": "all", "language": "ENG", "from": 1, "to": 20}
    if country_code:
        params["countryCode"] = country_code.upper()

    resp = requests.get(
        _base("/hotel-content-api/1.0/locations/destinations"),
        headers=_headers(),
        params=params,
        timeout=30,
    )
    resp.raise_for_status()
    dests = resp.json().get("destinations", [])
    if keyword:
        kw = keyword.lower()
        # Hotelbeds name is nested: {"content": "City Name"} or plain string
        def get_name(d):
            n = d.get("name", "")
            return n.get("content", "") if isinstance(n, dict) else str(n)
        dests = [d for d in dests if kw in get_name(d).lower()]
    return dests


def summarize_hotel(hotel: dict) -> dict:
    """Extract Wing-relevant facts from a Hotelbeds hotel availability object."""
    min_rate = None
    room_types = []
    for room in hotel.get("rooms", []):
        for rate in room.get("rates", []):
            net = float(rate.get("net", 0))
            if min_rate is None or net < min_rate:
                min_rate = net
            room_types.append({
                "room": room.get("name"),
                "board": rate.get("boardName"),
                "net": net,
                "currency": rate.get("currency"),
                "cancellation": rate.get("cancellationPolicies", [{}])[0].get("amount"),
                "cancel_by": rate.get("cancellationPolicies", [{}])[0].get("from"),
                "rateType": rate.get("rateType"),
            })

    return {
        "code": hotel.get("code"),
        "name": hotel.get("name"),
        "category": hotel.get("categoryName"),
        "min_rate": min_rate,
        "currency": room_types[0]["currency"] if room_types else None,
        "rooms": room_types[:5],
    }


def wing_hotel_brief(destination_code: str, check_in: str, check_out: str,
                     adults: int = 2, rooms: int = 1, pax_label: str = "") -> str:
    """Return Wing-format hotel brief (top 5 options) for client memos."""
    hotels = hotel_availability(destination_code, check_in, check_out, adults=adults,
                                rooms=rooms, max_results=5, min_category=4)
    if not hotels:
        return f"No hotels found for {destination_code} {check_in}→{check_out}."

    nights = (
        __import__("datetime").datetime.strptime(check_out, "%Y-%m-%d") -
        __import__("datetime").datetime.strptime(check_in, "%Y-%m-%d")
    ).days

    pax = pax_label or f"{adults} adults"
    lines = [f"## Hotel Brief — {destination_code} · {check_in}→{check_out} ({nights}n) · {rooms} room(s) · {pax}\n"]
    for i, h in enumerate(hotels, 1):
        s = summarize_hotel(h)
        lines.append(f"**[{i}] {s['name']}** ({s['category']}) — from ${s['min_rate']:.0f} {s['currency']}/total")
        for r in s["rooms"][:2]:
            cancel = f"cancel by {r['cancel_by'][:10]}" if r.get("cancel_by") else "non-refund"
            lines.append(f"    • {r['room']} · {r['board']} · ${r['net']:.0f} · {cancel}")

    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    dest = sys.argv[1] if len(sys.argv) > 1 else "PMC"  # Panama City
    check_in = sys.argv[2] if len(sys.argv) > 2 else "2026-12-14"
    check_out = sys.argv[3] if len(sys.argv) > 3 else "2026-12-17"
    print(wing_hotel_brief(dest, check_in, check_out, adults=2, rooms=1))
