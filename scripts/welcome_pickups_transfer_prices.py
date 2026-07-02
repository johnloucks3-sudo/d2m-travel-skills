#!/usr/bin/env python3
"""
welcome_pickups_transfer_prices.py — Zero-obstacle airport transfer pricing via Welcome Pickups.

welcomepickups.com is fully accessible with city-specific static HTML prices.
No auth, no cookies, no bot wall. Real transfer prices per city.

Covers all D2M client cruise ports:
  Mediterranean: Athens/Piraeus, Venice, Rome
  Baltic: Stockholm, Copenhagen, Helsinki, Tallinn, Oslo
  Caribbean/Panama: Panama City

Usage:
  .venv/bin/python scripts/welcome_pickups_transfer_prices.py --city athens
  .venv/bin/python scripts/welcome_pickups_transfer_prices.py --all-client-cities
  .venv/bin/python scripts/welcome_pickups_transfer_prices.py --list-cities

Dreams2Memories Travel, LLC · Thunderbird Wing · 2026-07-02
"""

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Welcome Pickups city slug → (display label, airport-taxi URL, airport-to-city URL)
CITY_MAP = {
    # Mediterranean — Silver Nova May 2027
    "athens":       ("Athens (ATH)",       "https://www.welcomepickups.com/athens/airport-taxi/",       "https://www.welcomepickups.com/athens/airport-to-city/"),
    "piraeus":      ("Piraeus Port",       "https://www.welcomepickups.com/piraeus/airport-taxi/",      "https://www.welcomepickups.com/piraeus/airport-to-city/"),
    "venice":       ("Venice (VCE)",       "https://www.welcomepickups.com/venice/airport-taxi/",       "https://www.welcomepickups.com/venice/airport-to-city/"),
    "rome":         ("Rome (FCO)",         "https://www.welcomepickups.com/rome/airport-taxi/",         "https://www.welcomepickups.com/rome/airport-to-city/"),
    "dubrovnik":    ("Dubrovnik (DBV)",    "https://www.welcomepickups.com/dubrovnik/airport-taxi/",    None),
    # Baltic — Regent Grandeur Aug 2026
    "stockholm":    ("Stockholm (ARN)",    "https://www.welcomepickups.com/stockholm/airport-taxi/",    "https://www.welcomepickups.com/stockholm/airport-to-city/"),
    "copenhagen":   ("Copenhagen (CPH)",   "https://www.welcomepickups.com/copenhagen/airport-taxi/",   "https://www.welcomepickups.com/copenhagen/airport-to-city/"),
    "helsinki":     ("Helsinki (HEL)",     "https://www.welcomepickups.com/helsinki/airport-taxi/",     "https://www.welcomepickups.com/helsinki/airport-to-city/"),
    "tallinn":      ("Tallinn (TLL)",      "https://www.welcomepickups.com/tallinn/airport-taxi/",      "https://www.welcomepickups.com/tallinn/airport-to-city/"),
    "oslo":         ("Oslo (OSL)",         "https://www.welcomepickups.com/oslo/airport-taxi/",         "https://www.welcomepickups.com/oslo/airport-to-city/"),
    # Caribbean/Panama — Viking Mars Dec 2026
    "panama-city":  ("Panama City (PTY)", "https://www.welcomepickups.com/panama-city/airport-taxi/",  None),
    "fort-lauderdale": ("Fort Lauderdale (FLL)", "https://www.welcomepickups.com/fort-lauderdale/airport-taxi/", None),
}

CLIENT_CITIES = [
    "athens", "piraeus", "venice",
    "stockholm", "copenhagen", "helsinki", "tallinn", "oslo",
    "panama-city",
]


def fetch_prices(city: str) -> dict:
    entry = CITY_MAP.get(city.lower())
    if not entry:
        return {"city": city, "error": f"No URL for city '{city}'"}

    label, taxi_url, city_url = entry
    results = {"city": city, "label": label, "checked_at": datetime.now(timezone.utc).isoformat()}

    for category, url in [("airport_taxi", taxi_url), ("airport_to_city", city_url)]:
        if not url:
            continue
        r = subprocess.run(
            ["curl", "-s", "-A", UA, "-L", "--max-time", "15", "--compressed", url],
            capture_output=True, timeout=20,
        )
        html = r.stdout.decode("utf-8", "replace")

        prices = []
        for m in re.finditer(r'[\$€£]\s*([\d,]+(?:\.\d{2})?)', html):
            try:
                v = float(m.group(1).replace(",", ""))
                if 5 <= v <= 500:
                    prices.append(v)
            except ValueError:
                pass
        prices = sorted(set(prices))

        results[category] = {
            "url": url,
            "price_count": len(prices),
            "min_usd": prices[0] if prices else None,
            "max_usd": prices[-1] if prices else None,
            "sample_prices": prices[:8],
            "status": "ok" if prices else "no_prices",
        }

    results["status"] = "ok" if any(
        results.get(k, {}).get("status") == "ok"
        for k in ("airport_taxi", "airport_to_city")
    ) else "no_prices"

    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", help="City slug (e.g. athens, stockholm)")
    parser.add_argument("--all-client-cities", action="store_true")
    parser.add_argument("--list-cities", action="store_true")
    args = parser.parse_args()

    if args.list_cities:
        print("Available cities:")
        for slug, (label, _, _) in sorted(CITY_MAP.items()):
            print(f"  {slug:20s} — {label}")
        return

    cities = CLIENT_CITIES if args.all_client_cities else [args.city] if args.city else []

    if not cities:
        parser.print_help()
        return

    results = []
    for city in cities:
        entry = CITY_MAP.get(city.lower())
        label = entry[0] if entry else city
        print(f"Fetching {label}...", end=" ", flush=True)
        result = fetch_prices(city)
        results.append(result)
        if result.get("status") == "ok":
            taxi = result.get("airport_taxi", {})
            city_data = result.get("airport_to_city", {})
            taxi_str = f"taxi ${taxi.get('min_usd', '?'):.0f}–${taxi.get('max_usd', '?'):.0f}" if taxi.get("status") == "ok" else ""
            city_str = f"  city ${city_data.get('min_usd', '?'):.0f}–${city_data.get('max_usd', '?'):.0f}" if city_data.get("status") == "ok" else ""
            print(f"{taxi_str}{city_str}")
        else:
            print(f"ERROR: {result.get('error', 'no prices found')}")

    out = ROOT / "OpsCenter" / "state" / "welcome_pickups_transfer_prices.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"\nSaved → {out}")


if __name__ == "__main__":
    main()
