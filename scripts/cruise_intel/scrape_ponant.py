#!/usr/bin/env python3
"""
Cruise Intel — Ponant.com Scraper
Navigates us.ponant.com/travel-in/[year]/[month], expands "See more voyages",
extracts and parses voyage cards, filters to Euro/Med/Arctic.
"""
import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime, date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import (
    GSTACK_BIN, PONANT_BASE_URL, OUTPUT_DIR,
    PONANT_RAW_JSON, PONANT_CLEAN_JSON,
    PONANT_TRANSATLANTIC_EXCEPTIONS, PONANT_EXCLUDE_PORTS,
    EUROPE_MED_KEYWORDS,
)
from utils import is_europe_med_arctic, is_ponant_excluded


MONTH_NAMES = {10: 'october', 11: 'november', 12: 'december',
               1: 'january', 2: 'february', 3: 'march'}


def gstack(cmd: list, timeout: int = 30) -> str:
    result = subprocess.run(
        [str(GSTACK_BIN)] + cmd,
        capture_output=True, text=True, timeout=timeout
    )
    return result.stdout.strip()


def expand_voyages(max_clicks: int = 8) -> int:
    """Click 'See more voyages' until it disappears. Returns click count."""
    clicks = 0
    for _ in range(max_clicks):
        js = """
var btn = Array.from(document.querySelectorAll('button, a'))
    .find(el => el.innerText && el.innerText.toLowerCase().includes('see more voyages'));
if(btn) { btn.click(); 'clicked'; } else { 'done'; }
"""
        result = gstack(['js', js])
        if result != 'clicked':
            break
        clicks += 1
        time.sleep(2)
    return clicks


def get_page_text() -> str:
    """Extract full visible text from page."""
    return gstack(['text'], timeout=60)


# ── Voyage card parser ─────────────────────────────────────────────────────────

def parse_ponant_page(text: str, month_name: str) -> list:
    """
    Parse Ponant travel-in page text into voyage dicts.
    Voyage blocks are split by the 'Discover' CTA button text.
    """
    # Strip nav header
    for marker in ('Filters 2', 'Sort by'):
        if marker in text:
            text = text[text.index(marker):]
            break

    # Strip footer
    for footer in ('Back to top', 'Useful links'):
        if footer in text:
            text = text[:text.index(footer)]
            break

    blocks = text.split('Discover')
    voyages = []

    for block in blocks[:-1]:
        block = block.strip()
        if not block or len(block) < 30:
            continue

        # Strip leading nav noise
        block = re.sub(r'^[0-9]+ cruises.*?Our selection', '', block, flags=re.DOTALL).strip()

        nights_m = re.search(r'(\d+)\s*nights', block)
        nights = nights_m.group(1) if nights_m else ''

        ship_m = re.search(
            r'aboard the ship\s*([^\n]+?)(?:\s*Next departure|\s*Offer)', block
        )
        ship = ship_m.group(1).strip() if ship_m else ''

        date_m = re.search(r'Next departure\s*(\d{2}/\d{2}/\d{2})', block)
        dep_raw = date_m.group(1) if date_m else ''

        from_m = re.search(r'From([A-Z][^T][^\n]*?)(?:To[A-Z]|$)', block, re.DOTALL)
        to_m   = re.search(r'To([A-Z][^\n]*?)(?:\d+\s*nights|$)', block, re.DOTALL)

        from_port = re.sub(r'\s*\(.*?\)', '', from_m.group(1).strip()).strip() if from_m else ''
        to_port   = re.sub(r'\s*\(.*?\)', '', to_m.group(1).strip()).strip() if to_m else ''

        price_m = re.search(r'From\s*\$([0-9,]+\.?\d*)\s*/person', block)
        price = '$' + price_m.group(1) if price_m else ''

        # Voyage name: first non-noise line
        name = ''
        for ln in (l.strip() for l in block.split('\n') if l.strip()):
            if (len(ln) > 5 and not re.match(
                r'^(Last cabins|Package included|In alliance|From\$|Offer|'
                r'From[A-Z]|To[A-Z]|\d+|aboard|Next|Discover)', ln
            )):
                name = ln
                break

        # Parse and format departure date
        dep_iso = ''
        if dep_raw:
            try:
                parts = dep_raw.split('/')
                m, d, y = int(parts[0]), int(parts[1]), 2000 + int(parts[2])
                dep_iso = date(y, m, d).isoformat()
            except Exception:
                dep_iso = dep_raw

        route = ''
        if from_port and to_port:
            route = (f'Round trip from {from_port}'
                     if from_port == to_port
                     else f'{from_port} to {to_port}')

        if ship and dep_iso:
            voyages.append({
                'name':           name,
                'ship':           ship,
                'departure_date': dep_iso,
                'nights':         nights,
                'from_port':      from_port,
                'to_port':        to_port,
                'route':          route or name,
                'price':          price,
                'source_month':   month_name,
            })

    return voyages


def clean_name(n: str) -> str:
    n = re.sub(r'^Filters\s+\d+.*?Our selection', '', n, flags=re.DOTALL).strip()
    n = re.sub(r'FromCallao.*', '', n).strip()
    n = re.sub(r'From[A-Z].*', '', n).strip()
    n = re.sub(r'\s+(Last cabins|Package included).*', '', n).strip()
    n = re.sub(r'\s+In alliance with.*', '', n).strip()
    return n[:80].strip()


def scrape_ponant(
    year: int,
    months: list,
    raw_output: Path,
    clean_output: Path,
    verbose: bool = False,
) -> list:
    """
    Scrape Ponant travel-in pages for given months.
    Returns filtered (Euro/Med/Arctic) voyage list.
    """
    if not GSTACK_BIN.exists():
        raise RuntimeError(f'gstack binary not found at {GSTACK_BIN}')

    all_voyages = []

    for month_num in months:
        month_name = MONTH_NAMES.get(month_num, str(month_num))
        url = PONANT_BASE_URL.format(year=year, month=month_name)
        print(f'  [ponant] Navigating to {url}')

        result = subprocess.run(
            [str(GSTACK_BIN), 'goto', url],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            print(f'  [ponant] Navigation failed for {month_name}')
            continue

        time.sleep(3)

        # Expand full listing
        clicks = expand_voyages()
        if verbose:
            print(f'  [ponant] Expanded voyages ({clicks} clicks)')
        if clicks:
            time.sleep(2)

        text = get_page_text()
        voyages = parse_ponant_page(text, month_name.capitalize())
        print(f'  [ponant] Parsed {len(voyages)} voyages for {month_name.capitalize()}')
        all_voyages.extend(voyages)

    # Save raw (all voyages)
    raw_output.parent.mkdir(parents=True, exist_ok=True)
    raw_output.write_text(json.dumps({'all': all_voyages}, indent=2))

    # Filter to Euro/Med/Arctic, clean names, add transatlantic exceptions
    filtered = []
    for v in all_voyages:
        if (is_europe_med_arctic(v['from_port'], v['to_port'], v['name'])
                and not is_ponant_excluded(v['from_port'], v['to_port'])):
            v['name'] = clean_name(v['name'])
            filtered.append(v)

    # Add hardcoded transatlantic exceptions (Europe-originating)
    for exc in PONANT_TRANSATLANTIC_EXCEPTIONS:
        dep_y = int(exc['departure_date'][:4])
        dep_m = int(exc['departure_date'][5:7])
        if dep_y == year and dep_m in months:
            filtered.append(exc)

    # Deduplicate by ship + date
    seen: set = set()
    deduped = []
    for v in filtered:
        key = (v.get('ship','').lower(), v.get('departure_date',''))
        if key not in seen:
            seen.add(key)
            deduped.append(v)

    print(f'  [ponant] {len(all_voyages)} total → {len(deduped)} Euro/Med/Arctic (after filter)')

    clean_output.write_text(json.dumps(deduped, indent=2))
    print(f'  [ponant] Saved clean → {clean_output}')
    return deduped


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Scrape Ponant.com travel-in pages')
    parser.add_argument('--year',         type=int, default=2026)
    parser.add_argument('--months',       nargs='+', type=int, default=[10, 11])
    parser.add_argument('--raw-output',   type=Path, default=PONANT_RAW_JSON)
    parser.add_argument('--clean-output', type=Path, default=PONANT_CLEAN_JSON)
    parser.add_argument('--verbose',      action='store_true')
    args = parser.parse_args()

    print(f'[ponant] Scraping {args.year} months={args.months}')
    results = scrape_ponant(
        year=args.year,
        months=args.months,
        raw_output=args.raw_output,
        clean_output=args.clean_output,
        verbose=args.verbose,
    )
    print(f'[ponant] Done — {len(results)} voyages written')
