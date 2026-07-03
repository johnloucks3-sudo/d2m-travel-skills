#!/usr/bin/env python3
"""
Run CruiseMapper scrape for all luxury lines, 2026+2027, all months.
Bypasses the euro/med/arctic geo filter to capture worldwide luxury sailings.
Output: intel/cruisemapper_live.json
"""
import json, re, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'cruise_intel'))
from config import CRUISEMAPPER_LINES
from scrape_cruisemapper import _get, _get_ship_urls, _parse_date
from utils import norm_ship

OUT = Path('/home/john/Thunderbird/intel/cruisemapper_live.json')
YEARS = [2026, 2027]


def parse_ship_all_dates(ship_url, years):
    """Like _parse_ship_itineraries but no geo filter, multi-year."""
    soup = _get(ship_url)
    if not soup:
        return []

    ship_name = ''
    for tag in ('h1', 'h2', 'title'):
        el = soup.find(tag)
        if el:
            text = el.get_text(separator=' ', strip=True)
            text = re.sub(r'\s*[\|·\-].*', '', text).strip()
            text = re.sub(r'\s+cruises?\s*$', '', text, flags=re.IGNORECASE).strip()
            if text and len(text) > 3:
                ship_name = text
                break

    voyages = []
    date_re = re.compile(r'(\d{4})\s+([A-Za-z]{3,})\s+(\d{1,2})')
    for row in soup.find_all('tr'):
        cells = [td.get_text(separator=' ', strip=True) for td in row.find_all(['td', 'th'])]
        if len(cells) < 2:
            continue
        if not date_re.match(cells[0]):
            continue
        dep = _parse_date(cells[0])
        if not dep or dep.year not in years:
            continue
        description = cells[1] if len(cells) > 1 else ''
        port = cells[2] if len(cells) > 2 else ''
        if description.lower() in ('route', 'itinerary', 'cruise', 'destination'):
            continue
        days_m = re.search(r'(\d+)\s*(?:days?|nights?)', description, re.I)
        days = days_m.group(1) if days_m else ''
        voyages.append({
            'departure_date': dep.isoformat(),
            'ship_name':      ship_name,
            'route':          description[:120],
            'port':           port,
            'days':           days,
            'cruise_line':    '',
            'source_url':     ship_url,
        })
    return voyages


def main():
    all_voyages = []
    seen = set()
    total_lines = len(CRUISEMAPPER_LINES)

    for idx, (line_key, line_cfg) in enumerate(CRUISEMAPPER_LINES.items(), 1):
        slug, canonical_line = line_cfg[0], line_cfg[1]
        opts = line_cfg[2] if len(line_cfg) > 2 else {}
        ship_includes = [s.lower() for s in opts.get('ship_includes', [])]

        print(f'[{idx}/{total_lines}] {line_key}: {slug}', flush=True)
        ship_urls_raw = _get_ship_urls(slug)
        # Deduplicate by stripping anchor fragments
        ship_urls = list(dict.fromkeys(u.split('#')[0] for u in ship_urls_raw))
        print(f'  {len(ship_urls)} ships', flush=True)
        line_count = 0

        for ship_url in ship_urls:
            voyages = parse_ship_all_dates(ship_url, YEARS)
            for v in voyages:
                if ship_includes and not any(inc in v['ship_name'].lower() for inc in ship_includes):
                    continue
                v['cruise_line'] = canonical_line
                key = (norm_ship(v['ship_name']), v['departure_date'])
                if key not in seen:
                    seen.add(key)
                    all_voyages.append(v)
                    line_count += 1

        if line_count:
            print(f'  → {line_count} voyages added', flush=True)

    all_voyages.sort(key=lambda v: v['departure_date'])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(all_voyages, indent=2))
    print(f'\nDone — {len(all_voyages)} total sailings → {OUT}')


if __name__ == '__main__':
    main()
