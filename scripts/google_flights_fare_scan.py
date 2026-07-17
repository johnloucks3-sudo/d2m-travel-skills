#!/usr/bin/env python3
"""
google_flights_fare_scan.py — second stateless flight-fare keepalive (2026-07-16).

Second of the two candidates found in the 2026-07-09 mega-build wave history
(Wave 3/4 travel-API research): Skyscanner ruled out both passes (sales-gated
enterprise partnership, no self-serve tier); Google Flights via the same
free RapidAPI account used for Kiwi was the other genuine stateless hit —
pure API key, no browser session/cookie to keep warm.

Quota: 150 req/month hard cap (tighter than Kiwi's 300). 2 routes/run,
every-other-day cadence = ~30 req/month, leaving most of the cap for
on-demand /flight-price calls.

Writes real prices into OpsCenter/fare_watches/google_flights_last_check.json
and merges into the main fare_watch registry for currently-degraded routes,
same pattern as kiwi_fare_scan.py.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
sys.path.insert(0, str(ROOT / "core/travel"))
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(str(ROOT / ".env"))

from thunderbird_google_flights_search import search_flights, cheapest_itinerary  # noqa: E402


def _strip_tokens(itin):
    """Drop Google's opaque pagination tokens (booking_token/next_token) —
    high-entropy base64 blobs that trip secret scanners despite containing
    only route metadata, not credentials. Not needed for price tracking."""
    if not itin:
        return itin
    return {k: v for k, v in itin.items() if k not in ("booking_token", "next_token")}

MAX_ROUTES_PER_RUN = 2
OUT_FILE = ROOT / "OpsCenter/fare_watches/google_flights_last_check.json"
MAIN_REGISTRY = ROOT / "OpsCenter/fare_watches/last_check.json"

# Pinned routes — real active client itineraries currently Centrav-degraded.
# COS-MIA confirmed via core/travel/data/fare_watches.json (Loucks Grandeur
# Panama Canal outbound, Dec 27 2026, 2 pax). RIC-PTY shared with Kiwi's scan
# as a deliberate cross-check (GDS-adjacent vs LCC-routing comparison).
ROUTES = [
    {
        "watch_id": "loucks-grandeur-panama-cos-fll-dec2026",
        "departure_id": "COS", "arrival_id": "MIA",
        "outbound_date": "2026-12-27", "adults": 2,
    },
    {
        "watch_id": "kuklinski-flights-ric-pty",
        "departure_id": "RIC", "arrival_id": "PTY",
        "outbound_date": "2026-12-17", "return_date": "2026-12-27", "adults": 4,
    },
]


def _merge_into_main_registry(watch_id: str, price: float) -> None:
    """Only replaces a known-degraded (auth_error/anansi) entry — never
    overwrites a route that already has a real Centrav/Amadeus price."""
    if not MAIN_REGISTRY.exists():
        return
    try:
        reg = json.loads(MAIN_REGISTRY.read_text())
    except Exception:
        return
    entry = reg.get("results", {}).get(watch_id)
    if not entry or entry.get("status") not in ("auth_error", "fallback"):
        return
    entry["google_flights_price_usd"] = price
    entry["google_flights_checked_at"] = datetime.now(timezone.utc).isoformat()
    entry["note"] = (entry.get("note", "") +
                     " | Google Flights real price also available (this run)").strip(" |")
    reg["results"][watch_id] = entry
    MAIN_REGISTRY.write_text(json.dumps(reg, indent=2))


def run() -> dict:
    out = {"started_at": datetime.now(timezone.utc).isoformat(), "routes": []}
    for r in ROUTES[:MAX_ROUTES_PER_RUN]:
        row = {"watch_id": r["watch_id"], "departure_id": r["departure_id"],
               "arrival_id": r["arrival_id"]}
        try:
            result = search_flights(
                r["departure_id"], r["arrival_id"], r["outbound_date"],
                return_date=r.get("return_date"), adults=r["adults"],
            )
            cheapest = _strip_tokens(cheapest_itinerary(result))
            row["status"] = "ok" if cheapest else "no_itineraries"
            row["cheapest"] = cheapest
            if cheapest:
                _merge_into_main_registry(r["watch_id"], cheapest.get("price"))
        except Exception as e:
            row["status"] = "error"
            row["error"] = str(e)[:200]
        out["routes"].append(row)
    out["completed_at"] = datetime.now(timezone.utc).isoformat()
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    result = run()
    for r in result["routes"]:
        if r["status"] == "ok":
            c = r["cheapest"]
            print(f"{r['watch_id']}: ${c.get('price')} USD")
        else:
            print(f"{r['watch_id']}: {r['status']} — {r.get('error', '')}")
