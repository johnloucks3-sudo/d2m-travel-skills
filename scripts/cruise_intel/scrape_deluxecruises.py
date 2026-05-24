#!/usr/bin/env python3
"""
Cruise Intel — deluxecruises.com Scraper
Navigates JS-rendered monthly cruise listing pages via gstack Chromium.
Covers 9 luxury lines; output saved to T2_EXERCISE_DEMBE_CRUISE_INTELLIGENCE.json.

URL pattern: https://www.deluxecruises.com/{line}/cruises/{month}-{year}.htm

Run manually (gstack session required):
    python3 scrape_deluxecruises.py --year 2026 --months 10 11

SP-T2-1: Run gstack network inspection before scraping any new OTA.
SP-T2-4: 3 URL attempts max per page → declare non-viable after 3 failures.
"""
import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import (
    GSTACK_BIN, OUTPUT_DIR, DELUXE_JSON,
    MONTH_MAP,
)
from utils import parse_date, norm_ship

# 9 luxury lines covered by deluxecruises.com
DELUXE_LINES = [
    'silversea',
    'regent-seven-seas',
    'seabourn',
    'oceania',
    'crystal',
    'azamara',
    'windstar',
    'ponant',
    'paul-gauguin',
]

DELUXE_BASE_URL = 'https://www.deluxecruises.com/{line}/cruises/{month}-{year}.htm'


def gstack(cmd: list, timeout: int = 30) -> str:
    result = subprocess.run(
        [str(GSTACK_BIN)] + cmd,
        capture_output=True, text=True, timeout=timeout
    )
    return result.stdout.strip()


def goto_with_retry(url: str, retries: int = 3) -> bool:
    """SP-T2-4: max 3 attempts per URL."""
    for attempt in range(1, retries + 1):
        result = subprocess.run(
            [str(GSTACK_BIN), 'goto', url],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            time.sleep(2)
            return True
        print(f'    attempt {attempt}/{retries} failed for {url}')
        time.sleep(1)
    return False


def get_page_text() -> str:
    return gstack(['text'], timeout=60)


# ── Voyage card parser ────────────────────────────────────────────────────────

def parse_deluxe_page(text: str, line: str, month: str, year: int) -> list:
    """
    Parse deluxecruises.com monthly listing page text into voyage dicts.
    Page structure varies slightly by line but consistently includes:
    - Ship name line
    - Departure date (formats: 'Oct 18, 2026', '18 Oct 2026')
    - Duration (N nights / N days)
    - Route description
    - Voyage code (optional)
    """
    voyages = []

    # Normalize cruise line name from slug
    line_display = line.replace('-', ' ').title()
    if line_display == 'Regent Seven Seas':
        line_display = 'Regent Seven Seas Cruises'

    # Strip nav/header noise above first cruise card
    for marker in ('Filter', 'Sort By', 'Results', 'cruises found'):
        if marker.lower() in text.lower():
            idx = text.lower().index(marker.lower())
            text = text[idx:]
            break

    # Split on common voyage card delimiters
    # deluxecruises uses "View Details" or "Book Now" as card terminators
    blocks = re.split(r'(?:View Details|Book Now|Enquire)', text, flags=re.IGNORECASE)

    for block in blocks[:-1]:
        block = block.strip()
        if len(block) < 40:
            continue

        # Ship name — look for known ship patterns or title-case lines
        ship = ''
        ship_m = re.search(
            r'(?:Ship[:\s]+|Vessel[:\s]+|aboard\s+)([A-Z][^\n]{3,40})', block
        )
        if ship_m:
            ship = ship_m.group(1).strip()
        else:
            # Fallback: first non-noise title-case line
            for ln in (l.strip() for l in block.split('\n') if l.strip()):
                if re.match(r'^[A-Z][a-z]', ln) and len(ln) > 4 and len(ln) < 50:
                    if not re.match(r'^(From|To|Depart|Arrive|Price|Book)', ln):
                        ship = ln
                        break

        # Departure date
        date_str = ''
        date_m = re.search(
            r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4})',
            block, re.IGNORECASE
        )
        if not date_m:
            date_m = re.search(
                r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4})',
                block, re.IGNORECASE
            )
        if date_m:
            date_str = date_m.group(1).strip()

        # Duration
        days = ''
        days_m = re.search(r'(\d+)\s*(?:nights?|days?)', block, re.IGNORECASE)
        if days_m:
            days = days_m.group(1)

        # Route
        route = ''
        route_m = re.search(
            r'(?:From\s+)([A-Z][^(\n]{5,60})(?:\s+to\s+([A-Z][^(\n]{3,40}))?',
            block
        )
        if route_m:
            from_port = route_m.group(1).strip()
            to_port   = route_m.group(2).strip() if route_m.group(2) else ''
            route = f'{from_port} to {to_port}' if to_port else from_port

        # Voyage code (alphanumeric, 6-10 chars)
        voyage_code = ''
        code_m = re.search(r'\b([A-Z]{2,4}\d{4,6}[A-Z]?)\b', block)
        if code_m:
            voyage_code = code_m.group(1)

        if ship and date_str:
            d_obj = parse_date(date_str)
            dep_iso = d_obj.isoformat() if d_obj else date_str
            voyages.append({
                'cruise_line':  line_display,
                'ship_name':    ship,
                'ship_norm':    norm_ship(ship),
                'date_str':     dep_iso,
                'month':        month,
                'days':         days,
                'route':        route[:100],
                'voyage_code':  voyage_code,
                'source_line':  line,
            })

    return voyages


def scrape_deluxecruises(
    year: int,
    months: list,
    output_path: Path,
    lines: list = None,
    verbose: bool = False,
) -> list:
    """
    Scrape deluxecruises.com for all 9 luxury lines across requested months.
    Returns list of voyage dicts; saves to output_path.
    """
    if not GSTACK_BIN.exists():
        raise RuntimeError(f'gstack binary not found at {GSTACK_BIN}')

    if lines is None:
        lines = DELUXE_LINES

    month_names = {v: k for k, v in MONTH_MAP.items()}  # num→abbrev
    all_voyages = []
    skipped_urls = []

    for line in lines:
        for month_num in months:
            month_name = {
                1: 'january', 2: 'february', 3: 'march', 4: 'april',
                5: 'may', 6: 'june', 7: 'july', 8: 'august',
                9: 'september', 10: 'october', 11: 'november', 12: 'december',
            }.get(month_num, str(month_num))
            month_display = month_name.capitalize()

            url = DELUXE_BASE_URL.format(line=line, month=month_name, year=year)
            print(f'  [deluxe] {line} / {month_display} → {url}')

            if not goto_with_retry(url):
                print(f'  [deluxe] SKIPPED after 3 attempts (SP-T2-4): {url}')
                skipped_urls.append(url)
                continue

            text = get_page_text()

            # Quick viability check — page has cruise content
            if not re.search(r'\d+\s*nights?', text, re.IGNORECASE):
                if verbose:
                    print(f'    no cruise data found (may be empty month)')
                continue

            voyages = parse_deluxe_page(text, line, month_display, year)
            if verbose:
                print(f'    parsed {len(voyages)} voyages')
            all_voyages.extend(voyages)
            time.sleep(1)  # polite delay between pages

    # Deduplicate by (ship_norm, date)
    seen: set = set()
    deduped = []
    for v in all_voyages:
        key = (v.get('ship_norm', ''), v.get('date_str', ''))
        if key not in seen:
            seen.add(key)
            deduped.append(v)

    print(f'  [deluxe] {len(all_voyages)} raw → {len(deduped)} deduplicated voyages')
    if skipped_urls:
        print(f'  [deluxe] {len(skipped_urls)} URLs skipped (SP-T2-4 — 3-attempt limit)')

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(deduped, indent=2))
    print(f'  [deluxe] Saved → {output_path}')
    return deduped


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Scrape deluxecruises.com luxury line monthly pages (gstack required)',
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--year',     type=int,   default=2026)
    parser.add_argument('--months',   nargs='+',  type=int, default=[10, 11],
                        help='Month numbers (default: 10 11)')
    parser.add_argument('--lines',    nargs='+',  default=None,
                        help=f'Lines to scrape (default: all 9). Options: {DELUXE_LINES}')
    parser.add_argument('--output',   type=Path,  default=DELUXE_JSON)
    parser.add_argument('--verbose',  action='store_true')
    args = parser.parse_args()

    print(f'[deluxe] Scraping {args.year} months={args.months}')
    if not GSTACK_BIN.exists():
        print(f'ERROR: gstack binary not found at {GSTACK_BIN}')
        print('Run: cd ~/.claude/skills/gstack && ./setup')
        sys.exit(1)

    results = scrape_deluxecruises(
        year=args.year,
        months=args.months,
        output_path=args.output,
        lines=args.lines,
        verbose=args.verbose,
    )
    print(f'[deluxe] Done — {len(results)} voyages written to {args.output}')
