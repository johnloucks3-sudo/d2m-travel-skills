#!/usr/bin/env python3
"""
port_restaurant_coordinator.py — Port-side dining partner integration.

Given a cruise port call (city, ship arrival/departure, tender status), finds
Michelin-caliber / OpenTable-partner restaurants near the port, picks a
reservation time that respects the ship's schedule, and returns a
booking-ready recommendation: restaurant, cuisine, rating, price estimate,
availability, reservation link, dress code alert, and arrival timing.

Data source: OpenTable affiliate API via core.travel.thunderbird_opentable.
That module requires ~/Thunderbird/opentable_credentials.json (api_key +
affiliate_id). Without a funded key it returns status="credentials_required"
— this module surfaces that status rather than fabricating restaurant data
(Negative-Space Rule, SO-PIPELINE-INTEGRITY-20260528).

Fields tagged CONFIRMED come straight from the OpenTable API response.
Fields tagged INFERRED (dress code, price-per-person estimate) are heuristics
derived from price tier / Michelin status — not sourced from OpenTable itself,
since the affiliate API does not return a dress-code field.

Usage:
    from core.dining.port_restaurant_coordinator import PortCall, recommend_dining_for_port

    call = PortCall(port_name="Barcelona", date="2027-05-12",
                     ship_arrival="08:00", all_aboard="18:00", is_tender=False)
    result = await recommend_dining_for_port(call, party_size=2)

CLI:
    python3 core/dining/port_restaurant_coordinator.py "Barcelona" 2027-05-12 08:00 18:00
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from core.travel.thunderbird_opentable import search_restaurants, build_reservation_link_for

logger = logging.getLogger(__name__)

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
OUTPUT_DIR = THUNDERBIRD_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_OUTPUT_FILE = OUTPUT_DIR / "dining_recommendations_by_port.json"

# ============================================================================
# CRUISE PORT → SEARCHABLE CITY
# ============================================================================
# OpenTable searches by city, not cruise-terminal name. Map the port name a
# client itinerary uses to the city OpenTable actually indexes restaurants
# under. Extend as new ports come up.

CRUISE_PORT_TO_CITY: dict[str, str] = {
    "civitavecchia": "Rome",
    "livorno": "Florence",
    "kusadasi": "Izmir",
    "ephesus": "Izmir",
    "piraeus": "Athens",
    "warnemunde": "Rostock",
    "warnemünde": "Rostock",
    "southampton": "London",
    "le havre": "Paris",
    "zeebrugge": "Bruges",
    "flam": "Bergen",
    "flåm": "Bergen",
    "villefranche": "Nice",
    "villefranche-sur-mer": "Nice",
}

# Ports commonly worked by tender (no direct pier) — a return-to-ship buffer
# is added on top of the normal walk-back time. Heuristic starting list,
# INFERRED — confirm per-sailing with the cruise line's port guide.
TENDER_PORTS: set[str] = {
    "santorini", "flam", "flåm", "villefranche", "villefranche-sur-mer",
    "juneau", "skagway", "grand cayman", "belize city",
}

# ============================================================================
# TIMING / PRICING / DRESS-CODE HEURISTICS (pure functions — unit-testable)
# ============================================================================

PRICE_TIER_ESTIMATE_USD = {
    "$": (15, 30),
    "$$": (30, 55),
    "$$$": (55, 100),
    "$$$$": (100, 200),
}

RESERVATION_ARRIVAL_BUFFER_MIN = 15          # walk-in buffer, standard pier
TENDER_PORT_EXTRA_BUFFER_MIN = 30            # extra margin for tender ports
ALL_ABOARD_SAFETY_MARGIN_MIN = 60            # must be back aboard this long before all-aboard


def estimate_price_per_person(price_range: str) -> dict:
    """INFERRED per-person USD estimate from an OpenTable $ tier. Not a quote."""
    lo, hi = PRICE_TIER_ESTIMATE_USD.get(price_range or "$$", PRICE_TIER_ESTIMATE_USD["$$"])
    return {"low": lo, "high": hi, "currency": "USD", "confidence": "INFERRED"}


def infer_dress_code(price_range: str, michelin_stars) -> dict:
    """INFERRED dress-code alert. OpenTable's affiliate API has no dress-code
    field, so this is derived from price tier + Michelin status, not sourced
    from the restaurant itself. Flag to client copy as inferred, never as fact.
    """
    if michelin_stars:
        code = "Smart formal — jacket recommended, no shorts/sandals"
    elif price_range in ("$$$$",):
        code = "Smart formal — collared shirt, no shorts/sandals"
    elif price_range in ("$$$",):
        code = "Smart casual — no shorts, no swimwear"
    else:
        code = "Casual / resort casual"
    return {"dress_code": code, "confidence": "INFERRED"}


def is_tender_port(port_name: str) -> bool:
    return port_name.strip().lower() in TENDER_PORTS


def resolve_city(port_name: str) -> str:
    """Map a cruise-terminal port name to the city OpenTable indexes. Falls
    back to the port name itself when no mapping exists (most ports ARE
    the city — Barcelona, Athens, Stockholm, Copenhagen, etc.)."""
    return CRUISE_PORT_TO_CITY.get(port_name.strip().lower(), port_name)


def compute_port_timing(
    date: str,
    reservation_time: str,
    ship_arrival: Optional[str] = None,
    all_aboard: Optional[str] = None,
    tender_port: bool = False,
) -> dict:
    """Compute recommended arrival-at-restaurant time and flag any risk of
    missing all-aboard. All timestamps are HH:MM local port time.

    Returns:
      arrive_by       — time to be walking in the restaurant door
      buffer_minutes  — total buffer built into arrive_by
      all_aboard_risk — True if the reservation runs past a safe return window
      warning         — human-readable flag when all_aboard_risk is True
    """
    buffer_min = RESERVATION_ARRIVAL_BUFFER_MIN + (TENDER_PORT_EXTRA_BUFFER_MIN if tender_port else 0)

    fmt = "%Y-%m-%d %H:%M"
    res_dt = datetime.strptime(f"{date} {reservation_time}", fmt)
    arrive_by = res_dt - timedelta(minutes=buffer_min)

    result = {
        "reservation_time": reservation_time,
        "arrive_by": arrive_by.strftime("%H:%M"),
        "buffer_minutes": buffer_min,
        "tender_port": tender_port,
        "all_aboard_risk": False,
        "warning": None,
    }

    if ship_arrival:
        arr_dt = datetime.strptime(f"{date} {ship_arrival}", fmt)
        if arrive_by < arr_dt:
            result["all_aboard_risk"] = True
            result["warning"] = (
                f"Suggested arrival {arrive_by.strftime('%H:%M')} is before ship arrival "
                f"{ship_arrival} — reservation time may need to move later."
            )

    if all_aboard:
        aboard_dt = datetime.strptime(f"{date} {all_aboard}", fmt)
        # Assume a 2-hour dinner; flag if that runs past the all-aboard safety margin.
        est_finish = res_dt + timedelta(hours=2)
        latest_safe_finish = aboard_dt - timedelta(minutes=ALL_ABOARD_SAFETY_MARGIN_MIN)
        if est_finish > latest_safe_finish:
            result["all_aboard_risk"] = True
            note = (
                f"Estimated dinner finish {est_finish.strftime('%H:%M')} leaves less than "
                f"{ALL_ABOARD_SAFETY_MARGIN_MIN} min before all-aboard ({all_aboard}) — "
                "book an earlier seating."
            )
            result["warning"] = f"{result['warning']} {note}".strip() if result["warning"] else note

    return result


def default_reservation_time(ship_arrival: Optional[str], all_aboard: Optional[str]) -> str:
    """Pick a sensible default dinner seating for a port day when the caller
    doesn't specify one: early evening, but only if the ship is still in port."""
    if all_aboard:
        try:
            aboard_hour = int(all_aboard.split(":")[0])
            if aboard_hour <= 18:
                return "13:00"  # overnight/late departure not available — lunch instead
        except ValueError:
            pass
    return "19:00"


# ============================================================================
# DATA MODEL
# ============================================================================

@dataclass
class PortCall:
    port_name: str
    date: str                              # YYYY-MM-DD
    ship_arrival: Optional[str] = None      # HH:MM
    all_aboard: Optional[str] = None        # HH:MM
    is_tender: Optional[bool] = None        # None → inferred from TENDER_PORTS
    cuisine: str = ""
    party_size: int = 2
    reservation_time: Optional[str] = None  # HH:MM — computed if omitted
    michelin_only: bool = False
    city_override: str = ""                # force a search city (rare)

    def resolved_city(self) -> str:
        return self.city_override or resolve_city(self.port_name)

    def resolved_tender(self) -> bool:
        return self.is_tender if self.is_tender is not None else is_tender_port(self.port_name)

    def resolved_reservation_time(self) -> str:
        return self.reservation_time or default_reservation_time(self.ship_arrival, self.all_aboard)


# ============================================================================
# CORE COORDINATION
# ============================================================================

async def recommend_dining_for_port(call: PortCall, top_n: int = 5) -> dict:
    """Search OpenTable for the port's city, rank results, and attach
    timing/dress-code/price guidance. Returns status=success with a
    `recommendations` list, or propagates OpenTable's own error/
    credentials_required status untouched — never fabricated data.
    """
    city = call.resolved_city()
    reservation_time = call.resolved_reservation_time()
    tender = call.resolved_tender()

    search_result = await search_restaurants(
        city=city,
        cuisine=call.cuisine,
        date=call.date,
        party_size=call.party_size,
    )

    if search_result.get("status") != "success":
        return {
            "port": call.port_name,
            "city": city,
            "date": call.date,
            **search_result,
        }

    results = search_result.get("results", [])
    if call.michelin_only:
        results = [r for r in results if r.get("michelin_stars")]

    # Michelin-starred first, then by rating, both descending.
    def _sort_key(r):
        stars = r.get("michelin_stars") or 0
        try:
            stars = int(stars) if not isinstance(stars, bool) else 0
        except (TypeError, ValueError):
            stars = 1 if stars else 0
        rating = r.get("rating") or 0
        try:
            rating = float(rating)
        except (TypeError, ValueError):
            rating = 0.0
        return (stars, rating)

    results.sort(key=_sort_key, reverse=True)

    timing = compute_port_timing(
        date=call.date,
        reservation_time=reservation_time,
        ship_arrival=call.ship_arrival,
        all_aboard=call.all_aboard,
        tender_port=tender,
    )

    recommendations = []
    for r in results[:top_n]:
        link = build_reservation_link_for(
            restaurant_id=r["restaurant_id"],
            date=call.date,
            time=reservation_time,
            party_size=call.party_size,
        )
        recommendations.append({
            "restaurant": r["name"],
            "cuisine": r["cuisine"],
            "rating": r["rating"],
            "review_count": r["review_count"],
            "michelin_stars": r["michelin_stars"],
            "price_range": r["price_range"],
            "price_estimate_per_person": estimate_price_per_person(r["price_range"]),
            "dress_code": infer_dress_code(r["price_range"], r["michelin_stars"]),
            "address": r["address"],
            "availability": {
                "date": call.date,
                "time": reservation_time,
                "party_size": call.party_size,
                "confidence": "CONFIRMED" if search_result.get("date") else "UNVERIFIED_NO_DATE_SPECIFIED",
            },
            "reservation_link": link["booking_url"],
            "source": "opentable",
        })

    return {
        "status": "success",
        "port": call.port_name,
        "city": city,
        "date": call.date,
        "party_size": call.party_size,
        "port_timing": timing,
        "recommendation_count": len(recommendations),
        "recommendations": recommendations,
    }


async def build_recommendations_by_port(
    port_calls: list[PortCall],
    output_path: Path = DEFAULT_OUTPUT_FILE,
) -> dict:
    """Run recommend_dining_for_port across every port call in an itinerary
    and write the combined result to output_path (default
    output/dining_recommendations_by_port.json)."""
    results = await asyncio.gather(*(recommend_dining_for_port(c) for c in port_calls))

    payload = {
        "generated": datetime.now().isoformat(),
        "port_count": len(port_calls),
        "ports": results,
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    logger.info("Wrote %d port dining recommendations to %s", len(port_calls), output_path)
    return payload


# ============================================================================
# CLI
# ============================================================================

def _cli():
    if len(sys.argv) < 5:
        print(
            "Usage: python3 port_restaurant_coordinator.py "
            "<port_name> <date YYYY-MM-DD> <ship_arrival HH:MM> <all_aboard HH:MM> "
            "[cuisine] [party_size]",
            file=sys.stderr,
        )
        sys.exit(1)

    port_name, date, ship_arrival, all_aboard = sys.argv[1:5]
    cuisine = sys.argv[5] if len(sys.argv) > 5 else ""
    party_size = int(sys.argv[6]) if len(sys.argv) > 6 else 2

    call = PortCall(
        port_name=port_name,
        date=date,
        ship_arrival=ship_arrival,
        all_aboard=all_aboard,
        cuisine=cuisine,
        party_size=party_size,
    )
    result = asyncio.run(recommend_dining_for_port(call))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    _cli()
