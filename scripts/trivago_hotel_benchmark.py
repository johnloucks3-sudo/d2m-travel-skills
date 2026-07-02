#!/usr/bin/env python3
"""
trivago_hotel_benchmark.py — Trivago site health + global hotel price benchmark.

Trivago.com is zero-obstacle (200 OK, 327KB, no bot wall). City-specific search
results are JS-rendered, but the static HTML contains embedded price benchmarks
showing the hotel price tier ($120–$393/night typical luxury range).

This script confirms Trivago is accessible and extracts the embedded price signals.
For specific property pricing:
  - Visit hotel's own website directly (no login, accurate rates)
  - For luxury tier: Regent/Silversea recommended hotels typically $300–$500+/night

Hotels this covers (pre/post cruise):
  - At Six Stockholm (Grandeur Aug 2026)
  - Copenhagen Marriott area / Nimb Hotel
  - Athens Syntagma area (Silver Nova May 2027)
  - Venice (Silver Nova embarkation)

Usage:
  .venv/bin/python scripts/trivago_hotel_benchmark.py
  .venv/bin/python scripts/trivago_hotel_benchmark.py --city stockholm

Note: --city flag shows city in output label only; actual prices are global benchmarks
embedded in Trivago static HTML (same tier regardless of city).

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

# Client cities (pre/post cruise hotels)
CITIES = {
    "stockholm":    "Stockholm (Grandeur Aug 2026 — pre/post)",
    "copenhagen":   "Copenhagen (Grandeur Aug 2026 — embark)",
    "helsinki":     "Helsinki (Grandeur Aug 2026)",
    "athens":       "Athens (Silver Nova May 2027 — depart)",
    "venice":       "Venice (Silver Nova May 2027 — embark)",
    "miami":        "Miami (Kuklinski Viking Mars Dec 2026 — post)",
    "fort-lauderdale": "Fort Lauderdale (Kuklinski — pre)",
}


def check_trivago(city: str = None) -> dict:
    city_label = CITIES.get(city, city) if city else "Global benchmark"

    r = subprocess.run(
        ["curl", "-s", "-A", UA, "-L", "--max-time", "15",
         "-w", "\n%{http_code} %{size_download}",
         "https://www.trivago.com/"],
        capture_output=True, text=True, timeout=20,
    )
    parts = r.stdout.rsplit("\n", 1)
    html = parts[0] if len(parts) == 2 else r.stdout
    meta = parts[1].strip() if len(parts) == 2 else ""

    status_code = int(meta.split()[0]) if meta else 0
    body_size = int(meta.split()[1]) if meta and len(meta.split()) > 1 else 0

    raw_prices = re.findall(r'[\$€£]\s*([\d,]+)', html)
    prices = []
    for p in raw_prices:
        try:
            val = float(p.replace(",", ""))
            if 50 <= val <= 5000:
                prices.append(val)
        except ValueError:
            pass
    prices = sorted(set(prices))

    accessible = status_code == 200 and body_size > 100000

    return {
        "source": "trivago.com",
        "city": city_label,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "http_status": status_code,
        "body_bytes": body_size,
        "accessible": accessible,
        "price_count": len(prices),
        "hotel_price_benchmark_usd": {
            "min": prices[0] if prices else None,
            "max": prices[-1] if prices else None,
            "samples": prices[:12],
        },
        "note": "Prices are global static benchmarks embedded in Trivago HTML — NOT city-specific. "
                "City-specific hotel search requires browser. For luxury pre/post cruise hotels, "
                "visit property website directly for accurate rates.",
        "hotel_gap": "City-specific hotel pricing requires browser or hotel direct site. "
                     "This is the one remaining zero-obstacle gap in D2M pricing stack.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", choices=list(CITIES.keys()), help="City label for context")
    parser.add_argument("--list-cities", action="store_true")
    args = parser.parse_args()

    if args.list_cities:
        print("Client cities:")
        for c, label in CITIES.items():
            print(f"  {c:20s} — {label}")
        return

    result = check_trivago(args.city)

    if result["accessible"]:
        r = result["hotel_price_benchmark_usd"]
        city_str = f" ({result['city']})" if args.city else ""
        print(f"Trivago: ✅ ACCESSIBLE ({result['body_bytes']:,} bytes){city_str}")
        print(f"  Hotel price tier (global benchmark): ${r['min']}–${r['max']}/night")
        print(f"  Sample prices: {r['samples']}")
        print(f"  ⚠️  City-specific pricing requires browser or hotel direct site")
    else:
        print(f"Trivago: ❌ NOT ACCESSIBLE (HTTP {result['http_status']})")

    out = ROOT / "OpsCenter" / "state" / "trivago_hotel_benchmark.json"
    out.write_text(json.dumps(result, indent=2))
    print(f"\nSaved → {out}")


if __name__ == "__main__":
    main()
