"""
Cruise Intel — CruiseMapper (cruisemapper.com) Scraper
No JavaScript needed — static HTML.  Uses requests + BeautifulSoup.

Strategy:
  1. Fetch cruise-line page  → collect all /ships/ links
  2. For each ship page      → parse dated itinerary table
  3. Filter: year/months + Euro/Med/Arctic geo check
  4. Deduplicate by (ship_name_norm, departure_date)

CruiseMapper itinerary table row format:
  "2026 Apr 04"  |  "31 days, one-way from Barcelona to Rome"  |  "Barcelona"
"""
import argparse
import json
import re
import sys
import time
from datetime import datetime, date
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent))
from config import CRUISEMAPPER_JSON, CRUISEMAPPER_LINES
from utils import is_europe_med_arctic, norm_ship

BASE = 'https://www.cruisemapper.com'
HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}
REQUEST_DELAY = 1.2   # polite crawl delay (seconds)
REQUEST_TIMEOUT = 25


def _get(url: str) -> Optional[BeautifulSoup]:
    """Fetch URL, return BeautifulSoup or None on error."""
    try:
        time.sleep(REQUEST_DELAY)
        r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        return BeautifulSoup(r.text, 'html.parser')
    except Exception as e:
        print(f'  [cruisemapper] HTTP error {url}: {e}')
        return None


def _get_ship_urls(line_slug: str) -> list[str]:
    """
    Fetch a cruise-line page and return all unique /ships/ URLs found.
    CruiseMapper line page: /cruise-lines/{slug}
    Ship links appear in the ships table as anchors to /ships/{name}-{id}
    """
    url = f'{BASE}/cruise-lines/{line_slug}'
    soup = _get(url)
    if not soup:
        return []

    seen: set[str] = set()
    ships: list[str] = []
    for a in soup.find_all('a', href=True):
        href = str(a['href'])
        if '/ships/' in href:
            full = href if href.startswith('http') else f'{BASE}{href.split("?")[0]}'
            if full not in seen:
                seen.add(full)
                ships.append(full)
    return ships


def _parse_date(raw: str) -> Optional[date]:
    """Parse CruiseMapper date string: '2026 Apr 04'  →  date(2026, 4, 4)."""
    raw = raw.strip()
    for fmt in ('%Y %b %d', '%Y %B %d', '%b %d, %Y', '%B %d, %Y', '%Y-%m-%d'):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            pass
    return None


def _parse_ship_itineraries(ship_url: str, year: int, months: list[int]) -> list[dict]:
    """
    Fetch a ship page and extract dated voyages for target year/months.
    Looks for table rows whose first cell contains a year-matching date.
    """
    soup = _get(ship_url)
    if not soup:
        return []

    # Derive ship name from page title or first h1/h2
    ship_name = ''
    for tag in ('h1', 'h2', 'title'):
        el = soup.find(tag)
        if el:
            text = el.get_text(separator=' ', strip=True)
            # Strip trailing boilerplate like "cruises 2026 | CruiseMapper"
            text = re.sub(r'\s*[\|·\-].*', '', text).strip()
            text = re.sub(r'\s+cruises?\s*$', '', text, flags=re.IGNORECASE).strip()
            if text and len(text) > 3:
                ship_name = text
                break

    # Look for itinerary tables
    voyages: list[dict] = []
    date_re = re.compile(r'(\d{4})\s+([A-Za-z]{3,})\s+(\d{1,2})')

    # Walk all table rows anywhere on the page
    for row in soup.find_all('tr'):
        cells = [td.get_text(separator=' ', strip=True) for td in row.find_all(['td', 'th'])]
        if len(cells) < 2:
            continue

        m = date_re.match(cells[0])
        if not m:
            continue

        dep = _parse_date(cells[0])
        if not dep or dep.year != year or dep.month not in months:
            continue

        description = cells[1] if len(cells) > 1 else ''
        port = cells[2] if len(cells) > 2 else ''

        # Skip header rows
        if description.lower() in ('route', 'itinerary', 'cruise', 'destination'):
            continue

        # Extract duration: "31 days" or "14 nights"
        days_m = re.search(r'(\d+)\s*(?:days?|nights?)', description, re.I)
        days = days_m.group(1) if days_m else ''

        # Geo filter
        route_text = description + ' ' + port
        if not is_europe_med_arctic('', '', route_text):
            continue

        voyages.append({
            'departure_date': dep.isoformat(),
            'ship_name':      ship_name,
            'route':          description[:120],
            'port':           port,
            'days':           days,
            'cruise_line':    '',   # filled by caller
            'source_url':     ship_url,
        })

    return voyages


def scrape_cruisemapper(
    year: int,
    months: list[int],
    output_path: Path,
    lines: dict = None,
    verbose: bool = False,
) -> list[dict]:
    """
    Scrape CruiseMapper for all target luxury cruise lines.
    Returns list of voyage dicts for given year/months (Euro/Med/Arctic only).
    """
    if lines is None:
        lines = CRUISEMAPPER_LINES

    all_voyages: list[dict] = []
    seen: set[tuple] = set()   # (ship_norm, departure_date)

    for line_key, (slug, canonical_line) in lines.items():
        print(f'  [cruisemapper] {line_key}: fetching line page → {slug}', flush=True)
        ship_urls = _get_ship_urls(slug)
        if not ship_urls:
            print(f'  [cruisemapper]   no ships found for {line_key}')
            continue

        print(f'  [cruisemapper]   {len(ship_urls)} ships found', flush=True)
        line_voyages = 0

        for ship_url in ship_urls:
            voyages = _parse_ship_itineraries(ship_url, year, months)
            for v in voyages:
                v['cruise_line'] = canonical_line
                key = (norm_ship(v['ship_name']), v['departure_date'])
                if key not in seen:
                    seen.add(key)
                    all_voyages.append(v)
                    line_voyages += 1
            if verbose and voyages:
                for v in voyages:
                    print(f'    {v["departure_date"]}  {v["ship_name"][:20]:<20}  '
                          f'{v["days"]:>3}d  {v["route"][:55]}')

        if line_voyages:
            print(f'  [cruisemapper]   → {line_voyages} voyages in {year} months={months}')

    # Sort by departure date
    all_voyages.sort(key=lambda v: v['departure_date'])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(all_voyages, indent=2))
    print(f'  [cruisemapper] {len(all_voyages)} total sailings saved → {output_path}')
    return all_voyages


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Scrape CruiseMapper (cruisemapper.com)')
    parser.add_argument('--year',    type=int, default=2026)
    parser.add_argument('--months',  nargs='+', type=int, default=[10, 11])
    parser.add_argument('--output',  type=Path, default=CRUISEMAPPER_JSON)
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()

    print(f'[cruisemapper] Scraping {args.year} months={args.months} '
          f'({len(CRUISEMAPPER_LINES)} lines)')
    results = scrape_cruisemapper(
        year=args.year, months=args.months,
        output_path=args.output, verbose=args.verbose,
    )
    print(f'[cruisemapper] Done — {len(results)} sailings → {args.output}')
