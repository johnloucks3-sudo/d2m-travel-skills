#!/usr/bin/env python3
"""
Cruise Intel — Perx.com Scraper
Previously used the sail-personalize.com REST API backend.

⚠️  STATUS 2026-05-24: sail-personalize.com API returns HTTP 400 on ALL queries.
    Perx.com migrated to server-side rendering; individual sailing prices now require
    a registered/logged-in session. The API is effectively dead for unauthenticated use.

    RECOVERY OPTIONS (requires gstack):
      1. Log into perx.com with a test account via gstack, then capture network traffic
         to find the new authenticated API endpoint.
      2. Use CruiseDirect.com (same backend) — may have different auth requirements.
      3. Accept Perx as a dead source and use the cache from prior successful runs.

    LAST SUCCESSFUL SCRAPE: 2026-05-22 (before API change detected).
    Cache at: output/T2_PERX_COMBINED.json (currently empty — wiped by failed run).
"""
import argparse
import json
import sys
import time
from pathlib import Path

import requests

# Allow running from scripts/cruise_intel/ directly
sys.path.insert(0, str(Path(__file__).parent))
from config import (
    OUTPUT_DIR, PERX_JSON, PERX_API_URL, PERX_API_ORIGIN,
    PERX_API_REFERER, PERX_REGIONS,
)
from utils import is_europe_med_arctic, normalize_flag


def build_perx_payload(region_id: str, year: int, months: list[int]) -> dict:
    """
    Build the sail-personalize.com API payload for a given region and date range.
    Payload format captured from Perx.com network traffic (2026-05-24).
    """
    month_start = min(months)
    month_end = max(months)
    date_from = f"{year}-{month_start:02d}-01"
    date_to   = f"{year}-{month_end:02d}-30"

    return {
        "departure_date_from": date_from,
        "departure_date_to": date_to,
        "destination": region_id,
        "nights_min": 2,
        "nights_max": 120,
        "page": 1,
        "per_page": 1000,
        "sort": "departure_date",
        "currency": "USD",
    }


def parse_perx_response(raw: list, region_name: str) -> list:
    """Extract normalized records from sail-personalize.com API response."""
    records = []
    for item in raw:
        ship = (item.get('ship_name') or item.get('ship') or '').strip()
        dep  = (item.get('departure_date') or item.get('date') or '').strip()
        route = (item.get('itinerary_name') or item.get('route') or
                 item.get('name') or '').strip()
        line  = (item.get('cruise_line_name') or item.get('cruise_line') or '').strip()
        days  = str(item.get('nights') or item.get('days') or '').strip()

        if not ship or not dep:
            continue

        records.append({
            'ship': ship,
            'date': dep,
            'route': route,
            'cruise_line': line,
            'days': days,
            'region': region_name,
        })
    return records


def scrape_perx(year: int, months: list[int], output_path: Path,
                filter_region: bool = True, verbose: bool = False) -> list:
    """
    Query sail-personalize.com for all cruise lines in Euro/Med/Arctic regions.
    Returns combined, deduplicated list of sailings.
    """
    headers = {
        'Origin': PERX_API_ORIGIN,
        'Referer': PERX_API_REFERER,
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'User-Agent': ('Mozilla/5.0 (X11; Linux x86_64) '
                       'AppleWebKit/537.36 Chrome/124.0 Safari/537.36'),
    }

    all_raw: list = []
    for region in PERX_REGIONS:
        payload = build_perx_payload(region['region_id'], year, months)
        print(f"  [perx] Querying {region['name']}...", flush=True)

        try:
            resp = requests.post(PERX_API_URL, json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            # API may return dict with 'results' key or direct list
            raw_list = data if isinstance(data, list) else data.get('results', data.get('data', []))
            records = parse_perx_response(raw_list, region['name'])
            print(f"         → {len(records)} raw sailings")
            all_raw.extend(records)

        except requests.HTTPError as e:
            print(f"  [perx] HTTP {e.response.status_code} on {region['name']} — skipping")
        except Exception as e:
            print(f"  [perx] Error on {region['name']}: {e} — skipping")

        time.sleep(1)

    # Deduplicate: same ship + date + route (first 30 chars)
    seen: set = set()
    deduped: list = []
    for r in all_raw:
        key = (r['ship'].lower()[:30], r['date'][:12], r['route'][:30].lower())
        if key not in seen:
            seen.add(key)
            deduped.append(r)

    print(f"  [perx] {len(all_raw)} raw → {len(deduped)} deduplicated")

    # Optional: filter to Euro/Med/Arctic only
    if filter_region:
        filtered = [r for r in deduped
                    if is_europe_med_arctic('', '', r.get('route','') + ' ' + r.get('region',''))]
        print(f"  [perx] {len(filtered)} pass Euro/Med/Arctic region filter")
    else:
        filtered = deduped

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not filtered and output_path.exists():
        import json as _json
        cached = _json.loads(output_path.read_text())
        if cached:
            print(f'  [perx] WARNING: 0 results from API — keeping existing cache ({len(cached)} records)')
            return cached
    output_path.write_text(json.dumps(filtered, indent=2))
    print(f"  [perx] Saved → {output_path}")
    return filtered


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Scrape Perx.com via sail-personalize API')
    parser.add_argument('--year',    type=int, default=2026)
    parser.add_argument('--months',  nargs='+', type=int, default=[10, 11],
                        help='Month numbers (default: 10 11 for Oct/Nov)')
    parser.add_argument('--output',  type=Path, default=PERX_JSON)
    parser.add_argument('--no-filter', action='store_true',
                        help='Disable Euro/Med/Arctic region filter')
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()

    print(f"[perx] Scraping {args.year} months={args.months}")
    results = scrape_perx(
        year=args.year,
        months=args.months,
        output_path=args.output,
        filter_region=not args.no_filter,
        verbose=args.verbose,
    )
    print(f"[perx] Done — {len(results)} sailings written to {args.output}")
