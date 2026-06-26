#!/usr/bin/env python3
"""
DeluxeCruises.com scraper — per-ship calendar pages
URL pattern: /{line}/{ship}/cruises-{year}/calendar.htm
Output: intel/deluxecruises_live.json

No Seabourn (Commander directive 2026-06-26).
"""
import json, re, time, sys
from pathlib import Path
from datetime import datetime

import requests
from bs4 import BeautifulSoup

OUT = Path('/home/john/Thunderbird/intel/deluxecruises_live.json')
BASE = 'https://www.deluxecruises.com/'
YEARS = [2026, 2027]

COOKIES = {
    '_ga': 'GA1.2.1609209430.1780273929',
    '_gid': 'GA1.2.2001137614.1782490385',
    'chatbase_anon_id': '3692ee7d-a5af-4462-a2d1-44b527c39716',
}
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

# No lines excluded — all luxury/ultra-luxury lines included
SKIP_LINES = set()

# Map URL prefix → canonical cruise line name
LINE_MAP = {
    'silversea': 'Silversea Cruises',
    'regent': 'Regent Seven Seas Cruises',
    'cunard': 'Cunard',
    'oceania': 'Oceania Cruises',
    'crystal': 'Crystal Cruises',
    'paul-gauguin': 'Paul Gauguin Cruises',
    'seadream': 'SeaDream Yacht Club',
    'ritz-carlton': 'Ritz-Carlton Yacht Collection',
    'four-seasons': 'Four Seasons Yachts',
    'ponant': 'PONANT',
    'windstar': 'Windstar Cruises',
    'lindblad-expeditions': 'Lindblad Expeditions',
}

MONTH_MAP = {
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
    'january': 1, 'february': 2, 'march': 3, 'april': 4, 'june': 6,
    'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12,
}


def parse_dep_date(date_str: str) -> str:
    """Convert 'January 9-25 2026' or 'February 26 March 12 2026' → ISO date of departure."""
    # Normalize whitespace
    s = re.sub(r'\s+', ' ', date_str.strip())
    # Try: "Month Day[-...] Year"  →  get first month + first day number
    m = re.match(r'([A-Za-z]+)\s+(\d{1,2}).*?(\d{4})', s)
    if not m:
        return ''
    month_str = m.group(1).lower()[:9]
    day = int(m.group(2))
    year = int(m.group(3))
    month = MONTH_MAP.get(month_str, 0)
    if not month:
        return ''
    return f'{year}-{month:02d}-{day:02d}'


def parse_calendar(url_path: str, line_name: str, ship_from_url: str) -> list:
    """Fetch a calendar.htm page and extract voyages."""
    url = BASE + url_path
    try:
        r = requests.get(url, headers=HEADERS, cookies=COOKIES, timeout=20)
    except Exception as e:
        print(f'  ERROR fetching {url_path}: {e}', flush=True)
        return []

    if r.status_code != 200:
        return []

    soup = BeautifulSoup(r.content, 'html.parser')

    # Extract ship name from page title / h1
    ship_name = ''
    for tag in ('h1', 'h2', 'title'):
        el = soup.find(tag)
        if el:
            text = re.sub(r'\s+', ' ', el.get_text()).strip()
            # Remove "Silversea Cruises 2026 Silver Nova Itinerary 2026..." → grab ship name
            m = re.search(r'(Silver [A-Za-z]+|Seven Seas [A-Za-z]+|Crystal [A-Za-z]+|'
                          r'Queen [A-Za-z ]+|Oceania [A-Za-z]+|Regent [A-Za-z]+|'
                          r'Seabourn [A-Za-z]+|World [A-Za-z]+|Seadream [A-Za-z ]+|'
                          r'Le [A-Za-z ]+|Ponant [A-Za-z]+|Windstar [A-Za-z]+|'
                          r'National Geographic [A-Za-z]+)', text, re.I)
            if m:
                ship_name = m.group(1).strip()
                break

    if not ship_name:
        # Fall back to URL slug, e.g. "silver-nova" → "Silver Nova"
        ship_name = ship_from_url.replace('-', ' ').title()

    voyages = []
    for t in soup.find_all('table'):
        for row in t.find_all('tr'):
            cells = [td.get_text(separator=' ', strip=True) for td in row.find_all(['td', 'th'])]
            if len(cells) < 3:
                continue

            date_cell = cells[1] if len(cells) > 1 else ''
            days_cell = cells[2] if len(cells) > 2 else ''
            route_cell = cells[3] if len(cells) > 3 else ''

            # Skip header rows
            if date_cell.lower() in ('departure', 'departure date', 'date', ''):
                continue

            # Date must contain a month name
            if not re.search(r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)', date_cell, re.I):
                continue

            dep_iso = parse_dep_date(date_cell)
            if not dep_iso:
                continue

            # Days
            days_m = re.search(r'(\d+)', days_cell)
            days = int(days_m.group(1)) if days_m else 0

            # Route: strip voyage codes
            route = re.sub(r'\bVoyage\s+[A-Z0-9]+\b', '', route_cell).strip()
            route = re.sub(r'\s+', ' ', route)

            # Skip Seabourn
            if 'seabourn' in ship_name.lower() or 'seabourn' in line_name.lower():
                continue

            voyages.append({
                'departure_date': dep_iso,
                'ship_name': ship_name,
                'route': route[:120],
                'cruise_line': line_name,
                'days': str(days),
                'source': 'deluxecruises',
            })
    return voyages


def collect_calendar_links() -> list:
    """Fetch homepage and collect all /{line}/{ship}/cruises-{year}/calendar.htm links."""
    r = requests.get(BASE, headers=HEADERS, cookies=COOKIES, timeout=20)
    soup = BeautifulSoup(r.content, 'html.parser')

    links = []
    seen = set()
    for a in soup.find_all('a', href=True):
        href = a['href'].strip()
        # Match pattern: {line}/{ship}/cruises-{year}/calendar.htm
        m = re.match(r'^([a-z][a-z0-9-]+)/([a-z][a-z0-9_-]+)/cruises-(\d{4})/calendar\.htm$', href)
        if not m:
            continue
        line_slug, ship_slug, year_str = m.group(1), m.group(2), m.group(3)
        year = int(year_str)
        if year not in YEARS:
            continue
        # Skip Seabourn
        if line_slug in SKIP_LINES or 'seabourn' in ship_slug:
            continue
        if href not in seen:
            seen.add(href)
            line_name = LINE_MAP.get(line_slug, line_slug.replace('-', ' ').title())
            links.append((href, line_name, ship_slug, year))

    return links


def main():
    print(f'[deluxecruises] Collecting calendar links from homepage...', flush=True)
    links = collect_calendar_links()
    print(f'[deluxecruises] Found {len(links)} calendar pages across {len(set(l[3] for l in links))} years', flush=True)

    all_voyages = []
    seen_keys = set()

    for i, (url_path, line_name, ship_slug, year) in enumerate(links, 1):
        print(f'[{i}/{len(links)}] {line_name} / {ship_slug} {year}', flush=True)
        voyages = parse_calendar(url_path, line_name, ship_slug)
        added = 0
        for v in voyages:
            key = (v['ship_name'].lower()[:30], v['departure_date'])
            if key not in seen_keys:
                seen_keys.add(key)
                all_voyages.append(v)
                added += 1
        if added:
            print(f'  → {added} voyages added', flush=True)
        time.sleep(0.5)  # polite delay

    all_voyages.sort(key=lambda v: v['departure_date'])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(all_voyages, indent=2))
    print(f'\n[deluxecruises] Done — {len(all_voyages)} total voyages → {OUT}', flush=True)


if __name__ == '__main__':
    main()
