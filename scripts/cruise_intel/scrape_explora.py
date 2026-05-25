"""
Cruise Intel — Explora Journeys (explorajourneys.com) Scraper
Uses the public sitemap (journey.sitemap.xml) to enumerate all sailings,
then fetches each journey page for og:description + price.

Coveo REST API is defunct (401) as of 2026-05-24 after site migration to Adobe Helix.
This scraper requires no auth and no reverse-engineering — pure public HTML.

Coverage: EXPLORA I (EX), EXPLORA II (EP) — Mediterranean, Northern Europe, Grand Journeys.
"""
import argparse
import json
import re
import sys
import time
from datetime import date, datetime
from pathlib import Path
from html import unescape

import requests

sys.path.insert(0, str(Path(__file__).parent))
from config import OUTPUT_DIR, EXPLORA_JSON
from utils import is_europe_med_arctic

EXPLORA_SITEMAP_URL = 'https://explorajourneys.com/int/en/journey.sitemap.xml'
EXPLORA_BASE = 'https://explorajourneys.com'

# Region slugs that qualify as Euro/Med/Arctic for Explora
EXPLORA_TARGET_REGIONS = {'med', 'nor', 'bri', 'ice', 'arc', 'bal', 'north'}

# Ship prefix in id-journey → ship name
EXPLORA_SHIP_MAP = {
    'EX': 'EXPLORA I',
    'EP': 'EXPLORA II',
    'E3': 'EXPLORA III',
    'E4': 'EXPLORA IV',
}

# Known 3-letter port codes in id-journey slugs → display name
EXPLORA_PORT_MAP = {
    'CVV': 'Civitavecchia (Rome)',
    'BCN': 'Barcelona',
    'PIR': 'Piraeus (Athens)',
    'IST': 'Istanbul',
    'AYT': 'Antalya',
    'FSA': 'Venice',
    'MLA': 'Valletta (Malta)',
    'LIS': 'Lisbon',
    'CDG': 'Paris (Le Havre)',
    'HAM': 'Hamburg',
    'CPH': 'Copenhagen',
    'OSL': 'Oslo',
    'STO': 'Stockholm',
    'HEL': 'Helsinki',
    'TLL': 'Tallinn',
    'RIX': 'Riga',
    'VNO': 'Vilnius',
    'REY': 'Reykjavik',
    'MRS': 'Marseille',
    'NCE': 'Nice',
    'GEN': 'Genoa',
    'NAP': 'Naples',
    'PAL': 'Palermo',
    'ATH': 'Athens',
    'DUB': 'Dubrovnik',
    'KOR': 'Kotor',
    'SPL': 'Split',
    'ZAD': 'Zadar',
    'VCE': 'Venice',
    'TRI': 'Trieste',
}

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (X11; Linux x86_64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,*/*',
    'Accept-Language': 'en-US,en;q=0.9',
}


def fetch_sitemap() -> list[dict]:
    """Fetch the Explora journey sitemap and return list of journey dicts."""
    resp = requests.get(EXPLORA_SITEMAP_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    urls = re.findall(r'<loc>(https://[^<]+)</loc>', resp.text)
    print(f'  [explora] Sitemap: {len(urls)} total journey URLs')

    journeys = []
    for url in urls:
        m = re.search(
            r'/destinations-globe/([^/]+)/journeys/'
            r'([^?]+)\?id-journey=([A-Z0-9]{2})(\d{8})([A-Z0-9]{3})([A-Z0-9]{3})',
            url
        )
        if not m:
            continue
        region, slug, ship_pfx, date_str, from_code, to_code = m.groups()
        journeys.append({
            'url': url,
            'region': region,
            'slug': slug,
            'ship_prefix': ship_pfx,
            'date_str': date_str,
            'from_code': from_code,
            'to_code': to_code,
        })
    return journeys


def filter_journeys(journeys: list, year: int, months: list) -> list:
    """Filter to target year/months and Euro/Med/Arctic regions."""
    filtered = []
    for j in journeys:
        # Date filter from id-journey
        try:
            dep_date = date(
                int(j['date_str'][:4]),
                int(j['date_str'][4:6]),
                int(j['date_str'][6:8]),
            )
        except ValueError:
            continue

        if dep_date.year != year or dep_date.month not in months:
            continue

        # Region filter — slug region OR port name geo check
        region = j['region'].lower()
        if not any(t in region for t in EXPLORA_TARGET_REGIONS):
            # Fallback: check port codes
            from_name = EXPLORA_PORT_MAP.get(j['from_code'], j['from_code'])
            to_name = EXPLORA_PORT_MAP.get(j['to_code'], j['to_code'])
            if not is_europe_med_arctic(from_name, to_name, ''):
                continue

        j['departure_date'] = dep_date.isoformat()
        filtered.append(j)

    return filtered


def fetch_journey_page(url: str) -> dict:
    """Fetch one journey page and extract og:description + price."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        return {'error': str(e)}

    html = resp.text

    # og:description: "Journey aboard SHIP for N nights sailing from PORT via PORTS. Departing DATE."
    desc_m = re.search(
        r'og:description[^>]+content="([^"]+)"',
        html,
    )
    description = unescape(desc_m.group(1)) if desc_m else ''

    # Price — first occurrence of "price":"NUMBER"
    price_m = re.search(r'"price"\s*:\s*"(\d+)"', html)
    price = price_m.group(1) if price_m else ''

    # Journey name from og:title or <title>
    title_m = re.search(r'og:title[^>]+content="([^"]+)"', html)
    if not title_m:
        title_m = re.search(r'<title>([^<]+)</title>', html)
    title = unescape(title_m.group(1)).strip() if title_m else ''

    return {
        'description': description,
        'price': price,
        'title': title,
    }


def parse_description(desc: str) -> dict:
    """
    Parse og:description into route fields.
    Format: "Journey aboard SHIP for N nights sailing from FROM via X, Y. Departing DATE."
    """
    parsed = {}

    # Ship name
    ship_m = re.search(r'aboard\s+(EXPLORA\s+(?:I{1,3}|IV|V))', desc, re.IGNORECASE)
    if ship_m:
        parsed['ship'] = ship_m.group(1).title()

    # Nights
    nights_m = re.search(r'for\s+(\d+)\s+nights?', desc, re.IGNORECASE)
    if nights_m:
        parsed['nights'] = nights_m.group(1)

    # From port
    from_m = re.search(r'sailing\s+from\s+([^.]+?)(?:\s+via|\s+\.|\s+Departing)', desc, re.IGNORECASE)
    if from_m:
        parsed['from_port'] = from_m.group(1).strip().rstrip(',')

    # Departure date
    date_m = re.search(r'Departing\s+(.+?)\.?\s*$', desc, re.IGNORECASE)
    if date_m:
        parsed['dep_date_str'] = date_m.group(1).strip()

    return parsed


def scrape_explora(
    year: int,
    months: list,
    output_path: Path,
    verbose: bool = False,
) -> list:
    """
    Scrape Explora Journeys via public sitemap + individual journey pages.
    Returns filtered (Euro/Med/Arctic) sailing list for year/months.
    """
    print('  [explora] Fetching sitemap...', flush=True)
    try:
        all_journeys = fetch_sitemap()
    except Exception as e:
        print(f'  [explora] Sitemap fetch FAILED: {e}')
        return []

    target = filter_journeys(all_journeys, year, months)
    print(f'  [explora] {len(target)} Euro/Med/Arctic sailings for {year} months {months}')

    records = []
    for i, j in enumerate(target, 1):
        print(f'  [explora] [{i}/{len(target)}] {j["departure_date"]} '
              f'{j["ship_prefix"]}  {j["from_code"]}→{j["to_code"]}', flush=True)

        page = fetch_journey_page(j['url'])
        if 'error' in page:
            print(f'  [explora]   FETCH ERROR: {page["error"]}')
            continue

        parsed = parse_description(page.get('description', ''))

        # Ship name: use parsed first, then map from ship_prefix
        ship = parsed.get('ship') or EXPLORA_SHIP_MAP.get(j['ship_prefix'], j['ship_prefix'])

        # From/to ports: use parsed from_port, fallback to code map
        from_port = parsed.get('from_port') or EXPLORA_PORT_MAP.get(j['from_code'], j['from_code'])
        to_port = EXPLORA_PORT_MAP.get(j['to_code'], j['to_code'])

        nights = parsed.get('nights') or ''
        # nights from URL slug: slug is like "cvvbcn-07-v11"
        if not nights:
            slug_nights = re.search(r'-(\d+)-v', j['slug'])
            if slug_nights:
                nights = slug_nights.group(1)

        # Route string
        if from_port.lower() == to_port.lower():
            route = f'Round trip from {from_port}'
        else:
            route = f'{from_port} to {to_port}'

        dep_date_obj = date.fromisoformat(j['departure_date'])

        record = {
            'cruise_line':    'Explora Journeys',
            'ship_name':      ship,
            'departure_date': j['departure_date'],
            'month':          dep_date_obj.strftime('%B'),
            'days':           nights,
            'route':          route[:120],
            'voyage_code':    j['url'].split('id-journey=')[-1],
            'from_port':      from_port,
            'to_port':        to_port,
            'price_usd_disc': page.get('price', ''),
            'price_usd_full': '',
            'voyage_name':    page.get('title', '')[:100],
            'destination':    j['region'],
        }
        records.append(record)

        if verbose:
            print(f'    {record["departure_date"]}  {ship:12s}  '
                  f'{nights:3s}n  ${record["price_usd_disc"]:>6s}  {route[:55]}')

        time.sleep(0.4)  # polite crawl delay

    # Deduplicate by voyage_code
    seen: set = set()
    deduped = []
    for r in records:
        key = r['voyage_code']
        if key not in seen:
            seen.add(key)
            deduped.append(r)

    deduped.sort(key=lambda x: x['departure_date'])
    print(f'  [explora] {len(records)} raw → {len(deduped)} deduplicated ({year} months {months})')

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(deduped, indent=2))
    print(f'  [explora] Saved → {output_path}')
    return deduped


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Scrape Explora Journeys (sitemap + page data)')
    parser.add_argument('--year',    type=int, default=2026)
    parser.add_argument('--months',  nargs='+', type=int, default=[10, 11])
    parser.add_argument('--output',  type=Path, default=EXPLORA_JSON)
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()

    print(f'[explora] Scraping {args.year} months={args.months}')
    results = scrape_explora(
        year=args.year,
        months=args.months,
        output_path=args.output,
        verbose=args.verbose,
    )
    print(f'[explora] Done — {len(results)} sailings → {args.output}')
