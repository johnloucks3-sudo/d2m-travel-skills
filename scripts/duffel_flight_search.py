#!/usr/bin/env python3
"""
duffel_flight_search.py — NDC Flight Search via Duffel API
MISSION-421 · ELON (A12) · 2026-06-24

Searches Duffel sandbox for flight availability + pricing.
First use case: Spencer DEN-FCO 12-pax group air quote brief.

Usage:
    python3 scripts/duffel_flight_search.py \
        --origin DEN --destination FCO \
        --date 2027-08-15 \
        --passengers 12 \
        --cabin business

Requires: DUFFEL_API_KEY in .env (register at duffel.com — free sandbox)
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DUFFEL_API_BASE = "https://api.duffel.com"
DUFFEL_API_VERSION = "v2"


def get_api_key() -> str:
    key = os.environ.get("DUFFEL_API_KEY")
    if not key:
        env_file = ROOT / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("DUFFEL_API_KEY="):
                    key = line.split("=", 1)[1].strip()
                    break
    if not key:
        print("ERROR: DUFFEL_API_KEY not found in environment or .env")
        print("Register at https://duffel.com to get a free sandbox key.")
        sys.exit(1)
    return key


def search_flights(
    origin: str,
    destination: str,
    date: str,
    num_passengers: int,
    cabin: str = "economy",
    return_date: str = None,
) -> dict:
    """Submit an offer request to Duffel and return parsed results."""
    try:
        import httpx
    except ImportError:
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "httpx", "-q"])
        import httpx

    api_key = get_api_key()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Duffel-Version": DUFFEL_API_VERSION,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    passengers = [{"type": "adult"} for _ in range(num_passengers)]

    slices = [{"origin": origin, "destination": destination, "departure_date": date}]
    if return_date:
        slices.append({"origin": destination, "destination": origin, "departure_date": return_date})

    payload = {
        "data": {
            "slices": slices,
            "passengers": passengers,
            "cabin_class": cabin,
        }
    }

    print(f"Searching Duffel: {origin}→{destination} {date} | {num_passengers} pax | {cabin}")

    with httpx.Client(timeout=30) as client:
        resp = client.post(
            f"{DUFFEL_API_BASE}/air/offer_requests",
            headers=headers,
            json=payload,
        )

    if resp.status_code != 201:
        return {"error": resp.status_code, "detail": resp.text[:500]}

    offer_request = resp.json()["data"]
    offers = offer_request.get("offers", [])

    return summarize_offers(offers, origin, destination, date, num_passengers, cabin)


def summarize_offers(offers, origin, destination, date, pax, cabin) -> dict:
    """Distill raw Duffel offers into a D2M-usable brief."""
    if not offers:
        return {"summary": "No offers returned — sandbox may require live key.", "offers": []}

    results = []
    for offer in offers[:10]:  # top 10
        slices = offer.get("slices", [])
        segments = slices[0].get("segments", []) if slices else []
        first_seg = segments[0] if segments else {}
        last_seg = segments[-1] if segments else {}

        results.append({
            "airline": first_seg.get("operating_carrier", {}).get("name", "?"),
            "iata": first_seg.get("operating_carrier", {}).get("iata_code", "?"),
            "total_per_pax_usd": float(offer.get("total_amount", 0)),
            "total_all_pax_usd": float(offer.get("total_amount", 0)) * pax,
            "currency": offer.get("total_currency", "USD"),
            "stops": len(segments) - 1,
            "departs": first_seg.get("departing_at", ""),
            "arrives": last_seg.get("arriving_at", ""),
            "offer_id": offer.get("id", ""),
            "expires_at": offer.get("expires_at", ""),
        })

    results.sort(key=lambda x: x["total_per_pax_usd"])

    cheapest = results[0] if results else {}
    summary = (
        f"{len(offers)} offers found | "
        f"Best: {cheapest.get('airline')} {cheapest.get('iata')} "
        f"${cheapest.get('total_per_pax_usd', 0):.0f}/pax "
        f"(${cheapest.get('total_all_pax_usd', 0):.0f} total {pax} pax) | "
        f"{cheapest.get('stops', 0)} stops"
    )

    return {
        "query": {
            "origin": origin, "destination": destination,
            "date": date, "passengers": pax, "cabin": cabin
        },
        "summary": summary,
        "top_offers": results,
        "as_of": datetime.utcnow().isoformat() + "Z",
    }


def main():
    parser = argparse.ArgumentParser(description="Duffel NDC flight search")
    parser.add_argument("--origin", default="DEN")
    parser.add_argument("--destination", default="FCO")
    parser.add_argument("--date", default="2027-08-15")
    parser.add_argument("--return-date", default=None)
    parser.add_argument("--passengers", type=int, default=12)
    parser.add_argument("--cabin", choices=["economy", "premium_economy", "business", "first"], default="economy")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    result = search_flights(
        origin=args.origin,
        destination=args.destination,
        date=args.date,
        num_passengers=args.passengers,
        cabin=args.cabin,
        return_date=args.return_date,
    )

    if args.json or "error" in result:
        print(json.dumps(result, indent=2))
    else:
        print("\n=== DUFFEL FLIGHT SEARCH RESULTS ===")
        print(result["summary"])
        print(f"\nTop {min(5, len(result.get('top_offers', [])))} options:")
        for i, offer in enumerate(result.get("top_offers", [])[:5], 1):
            print(f"  {i}. {offer['airline']} ({offer['iata']}) "
                  f"${offer['total_per_pax_usd']:.0f}/pax · "
                  f"{offer['stops']} stop(s) · "
                  f"departs {offer['departs'][:16]}")
        print(f"\nAdd DUFFEL_API_KEY to .env to get live results.")


if __name__ == "__main__":
    main()
