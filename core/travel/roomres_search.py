#!/usr/bin/env python3
"""
roomres_search.py — Hotel search via Room-Res B2B portal API.

Auth: Bearer JWT captured from browser session.
Session file: ~/Downloads/roomres_session.json
  (Re-capture when token expires: python3 core/travel/_roomres_capture.py)

API endpoints (discovered 2026-06-22):
  POST aws-gateway/v2/autocomplete/getdestinations  — destination/hotel name search
  POST aws-gateway/v2/hotel/search                  — hotel list with live pricing
  POST api.roomresservices.com/v2/hotel/details/content — full hotel info by ID
  POST api.roomresservices.com/v2/hotel/details/rooms   — room breakdown by ID

Known IDs:
  agencyId: 3380
  userId: 188891 (from captured fixture)

Usage:
    from core.travel.roomres_search import search_hotels, get_rooms
    results = search_hotels("Venice", checkin="2026-12-16", checkout="2026-12-17")
    results = search_hotels("Marriott Venice", ...)   # hotel name also works
"""
import json
from datetime import datetime
from pathlib import Path

import requests

ROOT = Path(__file__).parents[2]
SESSION_FILE = Path.home() / "Downloads" / "roomres_session.json"
API_BASE = "https://api.roomresservices.com/v2"
AWS_BASE = (
    "https://sam045jz07.execute-api.ap-southeast-2.amazonaws.com"
    "/rrwebapi-prod/v2"
)
AUTOCOMPLETE_URL = f"{AWS_BASE}/autocomplete/getdestinations"
HOTEL_SEARCH_URL = f"{AWS_BASE}/hotel/search"
AGENCY_ID = 3380
USER_ID = 188891


def _load_token() -> str:
    if not SESSION_FILE.exists():
        raise RuntimeError(
            f"Room-Res session not found at {SESSION_FILE}. "
            "Re-capture via Firefox DevTools → Application → Local Storage → "
            "save {token: ...} to ~/Downloads/roomres_session.json"
        )
    d = json.loads(SESSION_FILE.read_text())
    token = d.get("ls", {}).get("token", "")
    if not token:
        raise RuntimeError("No token in session file — re-run capture script.")
    return token


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {_load_token()}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _base_payload() -> dict:
    return {"userId": USER_ID, "agencyId": AGENCY_ID}


def _fmt_date(d: str) -> str:
    """Convert YYYY-MM-DD to D-Mon-YYYY (Room-Res API format). Passthrough if already formatted."""
    if len(d) == 10 and d[4] == "-":
        return datetime.strptime(d, "%Y-%m-%d").strftime("%-d-%b-%Y")
    return d


def search_destinations(keyword: str) -> list[dict]:
    """Autocomplete — works for both city names ('Venice') and hotel names ('Marriott Venice').

    Returns list of {id, destination, num_hotels, category, latitude, longitude}.
    category='Hotels' results have id usable with hotel_search.
    category='Cities/Areas' results have id usable for destination-level hotel_search.
    """
    payload = {**_base_payload(), "keyword": keyword}
    r = requests.post(AUTOCOMPLETE_URL, headers=_headers(), json=payload, timeout=15)
    r.raise_for_status()
    resp = r.json()
    return resp.get("destinations", resp) if isinstance(resp, dict) else resp


def hotel_search(autocomplete_id: int, checkin: str, checkout: str,
                 adults: int = 2, children: int = 0,
                 page: int = 1, page_size: int = 10) -> list[dict]:
    """
    Search hotels by autocomplete_id (destination or hotel-specific) with live pricing.

    This is the main search endpoint — faster than the detail endpoints and includes
    inline net/ota pricing. Returns list of hotel dicts.

    Each hotel dict includes:
      id (= hotelFilterId for use in get_hotel_content / get_rooms)
      name, address, city, country, star_rating
      net: {description, total_price, ...}   — B2B net rate
      ota: {total_price, room_name, ...}     — retail rate (OTA parity)
      payAtHotel: {...} or None
    """
    payload = {
        **_base_payload(),
        "autocompleteId": autocomplete_id,
        "hotelFilterId": 0,
        "checkIn": _fmt_date(checkin),
        "checkOut": _fmt_date(checkout),
        "pageIndex": page,
        "pageSize": page_size,
        "rooms": [{"adults": adults, "children": children, "childages": []}],
    }
    r = requests.post(HOTEL_SEARCH_URL, headers=_headers(), json=payload, timeout=20)
    r.raise_for_status()
    body = r.json().get("body", r.json())
    return body.get("data", body) if isinstance(body, dict) else body


def get_hotel_content(hotel_filter_id: int, checkin: str = "01-Jan-2027",
                      checkout: str = "02-Jan-2027") -> dict:
    """Fetch full hotel info (description, images, facilities) for a known hotel ID."""
    payload = {
        **_base_payload(),
        "recommendationOnly": False,
        "autocompleteId": 0,
        "hotelFilterId": hotel_filter_id,
        "packaging": True,
        "checkIn": _fmt_date(checkin),
        "checkOut": _fmt_date(checkout),
        "providerId": 6,
        "maxPrice": 0, "minPrice": 0, "starRatings": [],
        "type": "net", "externalRef": "",
        "sortType": "low-to-high",
        "pageIndex": 1, "pageSize": 100,
        "rooms": [{"adults": 2, "children": 0, "childages": []}],
        "commissionViewId": 0, "commissionViewPercent": 0, "commissionViewTypeId": 0,
    }
    r = requests.post(f"{API_BASE}/hotel/details/content",
                      headers=_headers(), json=payload, timeout=20)
    r.raise_for_status()
    return r.json()


def get_rooms(hotel_filter_id: int, checkin: str, checkout: str,
              adults: int = 2, children: int = 0) -> dict:
    """
    Fetch room type breakdown and rates for a specific hotel.

    Returns raw API response: {body: {roomGroupsByType: [{name, cheapestPrice, ...}]}}
    Use hotel_search() for a quick price check; use this for full room-level detail.
    """
    payload = {
        **_base_payload(),
        "recommendationOnly": False,
        "autocompleteId": 0,
        "hotelFilterId": hotel_filter_id,
        "packaging": True,
        "checkIn": _fmt_date(checkin),
        "checkOut": _fmt_date(checkout),
        "providerId": 6,
        "maxPrice": 0, "minPrice": 0, "starRatings": [],
        "type": "net", "externalRef": "",
        "sortType": "low-to-high",
        "pageIndex": 1, "pageSize": 100,
        "rooms": [{"adults": adults, "children": children, "childages": []}],
        "commissionViewId": 0, "commissionViewPercent": 0, "commissionViewTypeId": 0,
    }
    r = requests.post(f"{API_BASE}/hotel/details/rooms",
                      headers=_headers(), json=payload, timeout=20)
    r.raise_for_status()
    return r.json()


def _extract_price(pricing_field) -> float | None:
    """Pull price from a net/ota/payAtHotel hotel search field."""
    if not pricing_field:
        return None
    if isinstance(pricing_field, dict):
        # price_per_night is the best per-night rate (used by both net and ota)
        p = pricing_field.get("price_per_night") or pricing_field.get("total")
        if p:
            return float(p)
    return None


def search_hotels(query: str, checkin: str, checkout: str,
                  adults: int = 2, children: int = 0,
                  max_results: int = 10) -> list[dict]:
    """
    Search hotels by destination or name with live rates. One-call interface.

    Args:
        query: Destination ("Venice") or hotel name ("Marriott Venice", "Danieli")
        checkin/checkout: "YYYY-MM-DD" or "16-Dec-2026" format
        adults/children: room occupancy

    Returns list of:
        {name, hotel_filter_id, address, city, star_rating,
         net_rate, ota_rate, checkin, checkout, source="room_res"}
    """
    matches = search_destinations(query)
    if not matches:
        return []

    # Pick best autocomplete result: prefer Hotels category for name searches,
    # else take first destination match
    hotel_matches = [m for m in matches if m.get("category") == "Hotels"]
    dest_matches = [m for m in matches if m.get("category") != "Hotels"]

    results = []
    seen_ids = set()

    # If hotel-specific matches, search each for its rates
    if hotel_matches:
        for hm in hotel_matches[:min(3, max_results)]:
            try:
                hotels = hotel_search(hm["id"], checkin, checkout, adults, children,
                                      page_size=5)
                for h in hotels:
                    if h["id"] not in seen_ids:
                        seen_ids.add(h["id"])
                        results.append(_format_hotel(h, checkin, checkout))
                        if len(results) >= max_results:
                            break
            except Exception as e:
                results.append({"name": hm.get("destination", "?"), "error": str(e),
                                 "source": "room_res"})

    # If no hotel-specific results, fall back to destination-level search
    if not results and dest_matches:
        try:
            hotels = hotel_search(dest_matches[0]["id"], checkin, checkout, adults,
                                  children, page_size=max_results)
            for h in hotels:
                if h["id"] not in seen_ids:
                    seen_ids.add(h["id"])
                    results.append(_format_hotel(h, checkin, checkout))
        except Exception as e:
            results.append({"destination": dest_matches[0].get("destination", "?"),
                            "error": str(e), "source": "room_res"})

    return results[:max_results]


def _format_hotel(h: dict, checkin: str, checkout: str) -> dict:
    net_rate = _extract_price(h.get("net"))
    ota_rate = _extract_price(h.get("ota"))
    return {
        "name": h.get("name", "?"),
        "hotel_filter_id": h.get("id"),
        "address": h.get("address", ""),
        "city": h.get("city", ""),
        "star_rating": h.get("star_rating"),
        "net_rate": net_rate,
        "ota_rate": ota_rate,
        "checkin": checkin,
        "checkout": checkout,
        "source": "room_res",
    }


if __name__ == "__main__":
    import sys
    query = sys.argv[1] if len(sys.argv) > 1 else "Danieli Venice"
    checkin = sys.argv[2] if len(sys.argv) > 2 else "2026-12-16"
    checkout = sys.argv[3] if len(sys.argv) > 3 else "2026-12-17"
    print(f"Room-Res search: '{query}' {checkin}→{checkout}")
    results = search_hotels(query, checkin, checkout)
    print(f"{len(results)} hotels")
    for h in results[:8]:
        if h.get("error"):
            print(f"  ERROR: {h['error'][:60]}")
            continue
        net = f"${h['net_rate']:.0f}" if h.get("net_rate") else "—"
        ota = f"${h['ota_rate']:.0f}" if h.get("ota_rate") else "—"
        stars = f"★{h['star_rating']}" if h.get("star_rating") else ""
        print(f"  {h['name']} {stars} — net:{net} ota:{ota} — {h.get('city','')}")
