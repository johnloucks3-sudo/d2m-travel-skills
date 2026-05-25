"""
Cruise Intel — HX Expeditions (travelhx.com) Scraper
Uses Next.js __NEXT_DATA__ JSON embedded in the main cruise listing page.
Single GET request — no JavaScript execution required.
Note: hxexpeditions.com redirects to travelhx.com (rebranded 2023).
"""
import argparse
import json
import re
import sys
import time
from datetime import date
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from config import OUTPUT_DIR, HX_JSON, EUROPE_MED_KEYWORDS
from utils import is_europe_med_arctic, normalize_flag

HX_BASE_URL = "https://www.travelhx.com/en/cruises/"

# Arctic/European destination slugs to include
HX_TARGET_SLUGS = {
    'svalbard-cruises', 'norway-cruises', 'iceland-cruises',
    'europe-cruises', 'british-isles-cruises', 'greenland-cruises',
    'arctic-cruises', 'northern-europe-cruises', 'spitsbergen-cruises',
}

# Ships in HX fleet (for normalization)
HX_SHIPS = {
    'MS FRAM':          'MS Fram',
    'MS FRIDTJOF NANSEN': 'MS Fridtjof Nansen',
    'MS KONG HAROLD':   'MS Kong Harald',
    'MS ROALD AMUNDSEN': 'MS Roald Amundsen',
    'MS SPITSBERGEN':   'MS Spitsbergen',
    'MS OTTO SVERDRUP':  'MS Otto Sverdrup',
    'MS TROLLFJORD':    'MS Trollfjord',
    'MS VESTERÅLEN':    'MS Vesterålen',
}


def fetch_next_data(url: str = HX_BASE_URL) -> dict:
    """Fetch HX cruises page and extract __NEXT_DATA__ JSON."""
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (X11; Linux x86_64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/124.0 Safari/537.36'
        ),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()

    # Extract __NEXT_DATA__ from script tag
    m = re.search(
        r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
        resp.text, re.DOTALL
    )
    if not m:
        raise ValueError('__NEXT_DATA__ script tag not found in HX page')

    return json.loads(m.group(1))


def extract_voyages(next_data: dict) -> list:
    """Navigate Next.js data structure to find voyage metadata array."""
    props = next_data.get('props', {})
    page_props = props.get('pageProps', {})

    # Try multiple known paths in HX data structure
    for key in ('voyageMetadata', 'voyages', 'cruises', 'expeditions'):
        if key in page_props:
            return page_props[key]

    # Deep search: look for array of objects with departureDates
    def deep_find(obj, depth=0):
        if depth > 5:
            return None
        if isinstance(obj, list) and obj and isinstance(obj[0], dict):
            if 'departureDates' in obj[0] or 'departure_dates' in obj[0]:
                return obj
        if isinstance(obj, dict):
            for v in obj.values():
                result = deep_find(v, depth + 1)
                if result is not None:
                    return result
        return None

    return deep_find(page_props) or []


def normalize_hx_ship(raw: str) -> str:
    upper = raw.upper().strip()
    for k, v in HX_SHIPS.items():
        if k in upper:
            return v
    # Title-case as fallback
    return raw.strip().title() if raw else ''


def parse_voyage(v: dict, year: int, months: list) -> list:
    """
    Parse one HX voyage object into normalized record(s).
    A single voyage may have multiple departure dates — emit one record per date.
    """
    name = (v.get('name') or v.get('title') or v.get('voyageName') or '').strip()
    duration = v.get('duration') or v.get('nights') or v.get('days') or ''
    price_eur = v.get('price') or v.get('startingPrice') or ''
    slug = (v.get('cruiseCard', {}) or {}).get('slug', '') or v.get('slug', '')

    # Ship: may be single string or list of ship objects
    ship_raw = v.get('ships') or v.get('ship') or []
    if isinstance(ship_raw, list) and ship_raw:
        first = ship_raw[0]
        ship = normalize_hx_ship(
            first.get('name', '') if isinstance(first, dict) else str(first)
        )
    elif isinstance(ship_raw, str):
        ship = normalize_hx_ship(ship_raw)
    else:
        ship = ''

    # Destination slugs for geographic filtering
    dest_slugs = set(v.get('destinationSlugs') or v.get('destinations') or [])

    # Departure dates
    dates_raw = v.get('departureDates') or v.get('dates') or []
    if isinstance(dates_raw, str):
        dates_raw = [dates_raw]

    records = []
    for dep in dates_raw:
        dep_str = str(dep).strip()[:10]  # Take YYYY-MM-DD prefix
        try:
            d_obj = date.fromisoformat(dep_str)
        except ValueError:
            continue

        if d_obj.year != year or d_obj.month not in months:
            continue

        # Geographic filter: destination slugs OR name keywords
        is_target = (
            bool(dest_slugs & HX_TARGET_SLUGS) or
            is_europe_med_arctic('', '', name + ' ' + ' '.join(dest_slugs))
        )
        if not is_target:
            continue

        booking_codes = (v.get('cruiseCard', {}) or {}).get('bookingCodes') or []
        code = booking_codes[0] if booking_codes else ''

        records.append({
            'cruise_line':     'HX Expeditions',
            'ship_name':       ship,
            'departure_date':  dep_str,
            'month':           d_obj.strftime('%B'),
            'days':            str(duration),
            'route':           name,
            'voyage_code':     code,
            'price_eur':       str(price_eur),
            'slug':            slug,
        })

    return records


def scrape_hx(
    year: int,
    months: list,
    output_path: Path,
    verbose: bool = False,
) -> list:
    """
    Scrape HX Expeditions via Next.js __NEXT_DATA__ JSON.
    Returns filtered (Euro/Arctic) sailing list for the given year/months.
    """
    print(f'  [hx] Fetching {HX_BASE_URL}', flush=True)
    try:
        next_data = fetch_next_data()
    except Exception as e:
        print(f'  [hx] FETCH FAILED: {e}')
        return []

    voyages_raw = extract_voyages(next_data)
    print(f'  [hx] Found {len(voyages_raw)} total voyage objects in __NEXT_DATA__')

    results = []
    for v in voyages_raw:
        if not isinstance(v, dict):
            continue
        records = parse_voyage(v, year, months)
        results.extend(records)

    # Deduplicate: ship + date
    seen: set = set()
    deduped = []
    for r in results:
        key = (r['ship_name'].lower()[:30], r['departure_date'])
        if key not in seen:
            seen.add(key)
            deduped.append(r)

    print(f'  [hx] {len(results)} raw → {len(deduped)} deduplicated (Euro/Arctic, {year} {months})')

    if verbose and deduped:
        for r in deduped:
            print(f'    {r["departure_date"]}  {r["ship_name"]:25s}  {r["route"][:60]}')

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(deduped, indent=2))
    print(f'  [hx] Saved → {output_path}')
    return deduped


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Scrape HX Expeditions (travelhx.com)')
    parser.add_argument('--year',    type=int, default=2026)
    parser.add_argument('--months',  nargs='+', type=int, default=[10, 11])
    parser.add_argument('--output',  type=Path, default=HX_JSON)
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()

    print(f'[hx] Scraping {args.year} months={args.months}')
    results = scrape_hx(
        year=args.year,
        months=args.months,
        output_path=args.output,
        verbose=args.verbose,
    )
    print(f'[hx] Done — {len(results)} sailings → {args.output}')
