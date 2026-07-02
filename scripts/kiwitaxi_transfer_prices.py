#!/usr/bin/env python3
"""
kiwitaxi_transfer_prices.py — KiwiTaxi site health check + global transfer price benchmark.

KiwiTaxi.com is zero-obstacle (200 OK, no bot wall) but uses dynamic pricing for
specific routes. This script confirms site availability and extracts the global price
range visible in static HTML ($9–$3,000+). For port-specific transfer quotes, use:
  scripts/gyg_excursion_prices.py --port <port> --category transfer

For actual booking: kiwitaxi.com → enter route manually (no login required).

Usage:
  .venv/bin/python scripts/kiwitaxi_transfer_prices.py
  .venv/bin/python scripts/kiwitaxi_transfer_prices.py --verify

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
KIWITAXI_URL = "https://kiwitaxi.com/"


def check_site() -> dict:
    r = subprocess.run(
        ["curl", "-s", "-A", UA, "-L", "--max-time", "15",
         "-w", "\n%{http_code} %{size_download}", KIWITAXI_URL],
        capture_output=True, text=True, timeout=20,
    )
    parts = r.stdout.rsplit("\n", 1)
    html = parts[0] if len(parts) == 2 else r.stdout
    meta = parts[1].strip() if len(parts) == 2 else ""

    status_code = int(meta.split()[0]) if meta else 0
    body_size = int(meta.split()[1]) if meta and len(meta.split()) > 1 else 0

    raw_prices = re.findall(r'[\$€£]\s*([\d,]+(?:\.\d{2})?)', html)
    prices = []
    for p in raw_prices:
        try:
            val = float(p.replace(",", ""))
            if 5 <= val <= 10000:
                prices.append(val)
        except ValueError:
            pass
    prices = sorted(set(prices))

    accessible = status_code == 200 and body_size > 50000

    return {
        "source": "kiwitaxi.com",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "http_status": status_code,
        "body_bytes": body_size,
        "accessible": accessible,
        "price_count": len(prices),
        "global_price_range_usd": {
            "min": prices[0] if prices else None,
            "max": prices[-1] if prices else None,
            "samples": prices[:10],
        },
        "note": "Global benchmark only. Port-specific: use gyg_excursion_prices.py --category transfer",
        "booking_url": "https://kiwitaxi.com/",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true", help="Confirm site is accessible")
    args = parser.parse_args()

    result = check_site()

    if result["accessible"]:
        r = result["global_price_range_usd"]
        print(f"KiwiTaxi: ✅ ACCESSIBLE ({result['body_bytes']:,} bytes)")
        print(f"  Global transfer price range: ${r['min']}–${r['max']}")
        print(f"  Sample prices: {r['samples']}")
        print(f"  Port-specific quotes → gyg_excursion_prices.py --category transfer")
    else:
        print(f"KiwiTaxi: ❌ NOT ACCESSIBLE (HTTP {result['http_status']}, {result['body_bytes']} bytes)")

    out = ROOT / "OpsCenter" / "state" / "kiwitaxi_transfer_prices.json"
    out.write_text(json.dumps(result, indent=2))
    print(f"\nSaved → {out}")


if __name__ == "__main__":
    main()
