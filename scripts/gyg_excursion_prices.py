#!/usr/bin/env python3
"""
gyg_excursion_prices.py — GetYourGuide zero-obstacle excursion price lookup.

No auth, no cookies, no bot wall. Real prices in static HTML via simple curl+grep.
Covers all major cruise ports: Mediterranean, Baltic, Caribbean, Pacific.

Usage:
  .venv/bin/python scripts/gyg_excursion_prices.py --port athens
  .venv/bin/python scripts/gyg_excursion_prices.py --port rome
  .venv/bin/python scripts/gyg_excursion_prices.py --all-client-ports

Port codes map to GYG location slugs (curated for client voyages).

Dreams2Memories Travel, LLC · Thunderbird Wing · 2026-07-02
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# GYG search URL template — prices live in static HTML on search results
GYG_SEARCH = "https://www.getyourguide.com/s/?q=shore+excursion+{port}"

# Port display names for reporting
PORT_DISPLAY = {
    "athens": "Athens (Silver Nova)", "piraeus": "Piraeus", "santorini": "Santorini",
    "mykonos": "Mykonos", "kotor": "Kotor", "dubrovnik": "Dubrovnik", "venice": "Venice",
    "copenhagen": "Copenhagen (Grandeur)", "stockholm": "Stockholm", "helsinki": "Helsinki",
    "tallinn": "Tallinn", "riga": "Riga", "oslo": "Oslo",
    "panama": "Panama City (Kuklinski)", "cartagena": "Cartagena",
    "miami": "Miami", "barbados": "Barbados",
    "rome": "Rome/Civitavecchia", "lisbon": "Lisbon", "barcelona": "Barcelona",
}

# Search query templates — GYG returns port-specific static prices for all three
GYG_EXCURSION = "https://www.getyourguide.com/s/?q=shore+excursion+{port}"
GYG_TRANSFER  = "https://www.getyourguide.com/s/?q=airport+transfer+{port}"
GYG_MUSEUM    = "https://www.getyourguide.com/s/?q=museum+tickets+{port}"

PORT_MAP = {p: GYG_EXCURSION.format(port=p) for p in PORT_DISPLAY}

# Additional per-category maps (same ports, different query)
PORT_TRANSFER_MAP = {p: GYG_TRANSFER.format(port=p) for p in PORT_DISPLAY}
PORT_MUSEUM_MAP   = {p: GYG_MUSEUM.format(port=p) for p in PORT_DISPLAY}

CLIENT_PORTS = [
    "athens", "santorini", "mykonos", "kotor", "dubrovnik", "venice",
    "copenhagen", "stockholm", "helsinki", "tallinn", "oslo",
    "panama",
]

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def fetch_prices(port: str) -> dict:
    url = PORT_MAP.get(port.lower())
    if not url:
        return {"port": port, "error": f"No URL mapped for port '{port}'"}

    r = subprocess.run(
        ["curl", "-s", "-A", UA, "-L", "--max-time", "15", url],
        capture_output=True, text=True, timeout=20,
    )
    html = r.stdout

    # Extract prices from static HTML
    raw_prices = re.findall(r'\$\s*([\d,]+(?:\.\d{2})?)', html)
    prices = []
    for p in raw_prices:
        try:
            val = float(p.replace(",", ""))
            if 5 <= val <= 2000:  # sanity filter: excursion range
                prices.append(val)
        except ValueError:
            pass

    prices = sorted(set(prices))

    # Extract activity titles (heuristic: text near price patterns)
    titles = re.findall(r'"name"\s*:\s*"([^"]{10,80})"', html)[:10]

    return {
        "port": port,
        "url": url,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "price_count": len(prices),
        "min_pp": prices[0] if prices else None,
        "max_pp": prices[-1] if prices else None,
        "sample_prices": prices[:8],
        "sample_titles": titles[:5],
        "status": "ok" if prices else "no_prices",
    }


def fetch_category(port: str, category: str) -> dict:
    """Fetch prices for a specific category (excursion, transfer, museum) via GYG search."""
    if category == "transfer":
        url = PORT_TRANSFER_MAP.get(port.lower())
    elif category == "museum":
        url = PORT_MUSEUM_MAP.get(port.lower())
    else:
        url = PORT_MAP.get(port.lower())

    if not url:
        return {"port": port, "category": category, "error": f"No URL for port '{port}'"}

    result = fetch_prices(port)
    result["category"] = category
    result["url"] = url
    # Re-fetch with correct URL if it differs from excursion URL
    if url != PORT_MAP.get(port.lower()):
        r = subprocess.run(
            ["curl", "-s", "-A", UA, "-L", "--max-time", "15", url],
            capture_output=True, text=True, timeout=20,
        )
        raw_prices = re.findall(r'\$\s*([\d,]+(?:\.\d{2})?)', r.stdout)
        prices = []
        for p in raw_prices:
            try:
                val = float(p.replace(",", ""))
                if 5 <= val <= 2000:
                    prices.append(val)
            except ValueError:
                pass
        prices = sorted(set(prices))
        result.update({
            "url": url,
            "price_count": len(prices),
            "min_pp": prices[0] if prices else None,
            "max_pp": prices[-1] if prices else None,
            "sample_prices": prices[:8],
            "status": "ok" if prices else "no_prices",
        })
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", help="Port name (e.g. athens, rome, stockholm)")
    parser.add_argument("--all-client-ports", action="store_true")
    parser.add_argument("--list-ports", action="store_true")
    parser.add_argument("--category", choices=["excursion", "transfer", "museum"], default="excursion",
                        help="Price category (default: excursion)")
    args = parser.parse_args()

    if args.list_ports:
        print("Available ports:")
        for p in sorted(PORT_MAP.keys()):
            print(f"  {p}")
        return

    ports = CLIENT_PORTS if args.all_client_ports else [args.port] if args.port else []

    if not ports:
        parser.print_help()
        return

    results = []
    for port in ports:
        print(f"Fetching {port} ({args.category})...", end=" ", flush=True)
        result = fetch_category(port, args.category)
        results.append(result)
        if result.get("status") == "ok":
            print(f"${result['min_pp']:.0f}–${result['max_pp']:.0f}/pp  ({result['price_count']} prices)")
        else:
            print(f"ERROR: {result.get('error', 'no prices found')}")

    # Save output — category-namespaced
    out = ROOT / "OpsCenter" / "state" / f"gyg_{args.category}_prices.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"\nSaved → {out}")


if __name__ == "__main__":
    main()
