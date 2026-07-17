#!/usr/bin/env python3
"""
kiwi_fare_scan.py — stateless flight-fare keepalive (2026-07-16).

Commander: "figure out how to keep a flight fare scan alive" after Centrav's
session-cookie keepalive was retired as futile. Kiwi.com via RapidAPI
(core/travel/thunderbird_kiwi_search.py, built 2026-07-09 mega-build wave) is
the fix — pure API key, NO browser session/cookie/CAPTCHA to keep warm. It
literally cannot go stale the way Centrav did.

Quota discipline (RapidAPI free tier: 300 req/month hard cap): this scan
checks at most MAX_ROUTES_PER_RUN routes per run, once daily via
d2m-kiwi-fare-scan.timer — worst case 2 routes/day = 60/month, well under
cap, leaving headroom for on-demand /flight-price calls same month.

Writes real (not web-estimate) round-trip prices into
OpsCenter/fare_watches/kiwi_last_check.json, and — when a route is currently
degraded to an Anansi web-estimate fallback in the main fare_watch registry —
also merges a real Kiwi price into that route's entry so downstream readers
see live LCC/connecting pricing instead of a text-snippet guess.
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

from thunderbird_kiwi_search import search_roundtrip, cheapest_itinerary  # noqa: E402

MAX_ROUTES_PER_RUN = 2
OUT_FILE = ROOT / "OpsCenter/fare_watches/kiwi_last_check.json"
MAIN_REGISTRY = ROOT / "OpsCenter/fare_watches/last_check.json"

# Pinned routes — real active client itineraries currently Centrav-degraded.
# Slugs resolved live via place_autocomplete() 2026-07-16, not guessed.
ROUTES = [
    {
        "watch_id": "kuklinski-flights-ric-pty",
        "source": "richmond-virginia-united-states",
        "destination": "tocumen-international-panama-city-panama",
        "departure_date": "2026-12-17",
        "return_date": "2026-12-27",
        "adults": 4,
    },
    {
        "watch_id": "morton-dodge-flights-rsw-pty",
        "source": "fort-myers-florida-united-states",
        "destination": "tocumen-international-panama-city-panama",
        "departure_date": "2026-12-17",
        "return_date": "2026-12-27",
        "adults": 2,
    },
]


def _merge_into_main_registry(watch_id: str, cheapest: dict) -> None:
    """Replace an Anansi web-estimate fallback entry with a real Kiwi price,
    when that watch_id exists and is currently degraded. Never touches a
    watch that already has a real Centrav/Amadeus price."""
    if not MAIN_REGISTRY.exists():
        return
    try:
        reg = json.loads(MAIN_REGISTRY.read_text())
    except Exception:
        return
    entry = reg.get("results", {}).get(watch_id)
    if not entry or entry.get("source") != "anansi":
        return  # only replace known-degraded web-estimate entries
    entry["kiwi_price_usd"] = cheapest["price"]["amount"] if cheapest else None
    entry["kiwi_carrier"] = (cheapest.get("segments", [{}])[0].get("carrier")
                             if cheapest else None)
    entry["kiwi_checked_at"] = datetime.now(timezone.utc).isoformat()
    entry["note"] = ("FALLBACK — Centrav dead; Kiwi real LCC/connecting price "
                     "available alongside web-estimate (not B2B net fare)")
    reg["results"][watch_id] = entry
    MAIN_REGISTRY.write_text(json.dumps(reg, indent=2))


def run() -> dict:
    out = {"started_at": datetime.now(timezone.utc).isoformat(), "routes": []}
    for r in ROUTES[:MAX_ROUTES_PER_RUN]:
        row = {"watch_id": r["watch_id"], "source": r["source"], "destination": r["destination"]}
        try:
            result = search_roundtrip(
                r["source"], r["destination"], r["departure_date"], r["return_date"],
                adults=r["adults"],
            )
            cheapest = cheapest_itinerary(result)
            row["status"] = "ok" if cheapest else "no_itineraries"
            row["cheapest"] = cheapest
            row["itinerary_count"] = result.get("count", 0)
            if cheapest:
                _merge_into_main_registry(r["watch_id"], cheapest)
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
            print(f"{r['watch_id']}: ${c['price']['amount']} {c['price'].get('currency', 'USD')} "
                 f"({r['itinerary_count']} itineraries)")
        else:
            print(f"{r['watch_id']}: {r['status']} — {r.get('error', '')}")
