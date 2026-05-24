#!/usr/bin/env python3
"""
Cruise Intel — OAT.com Scraper
Uses gstack headless Chromium to visit OAT trip pages and extract Oct/Nov departures.
SP-T2-4: 3 URL attempts max per trip → declare non-viable.
"""
import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from config import GSTACK_BIN, OAT_BASE_URL, OAT_EURO_TRIPS, OUTPUT_DIR, OAT_JSON
from utils import progress


def gstack(cmd: list, timeout: int = 30) -> str:
    """Run a gstack command and return stdout."""
    result = subprocess.run(
        [str(GSTACK_BIN)] + cmd,
        capture_output=True, text=True, timeout=timeout
    )
    return result.stdout.strip()


def goto(url: str, retries: int = 3) -> bool:
    """Navigate to URL. Returns True on success. SP-T2-4: max 3 attempts."""
    for attempt in range(retries):
        r = subprocess.run(
            [str(GSTACK_BIN), 'goto', url],
            capture_output=True, text=True, timeout=30
        )
        if r.returncode == 0:
            return True
        time.sleep(2)
    return False


def click_month_button(month: str) -> bool:
    """Click the departure month accordion button on an OAT trip page."""
    js = f"""
var btns = document.querySelectorAll('button');
var found = false;
for(var i=0; i<btns.length; i++) {{
  var txt = btns[i].innerText.trim();
  if(txt.startsWith('{month}') && (txt.includes('From') || txt.includes('Sold Out'))
     && !txt.includes('Close')) {{
    btns[i].click();
    found = true;
    break;
  }}
}}
found ? 'clicked' : 'not_found';
"""
    return gstack(['js', js]) == 'clicked'


def extract_month_section(month: str) -> str:
    """Extract page text section around the expanded month accordion."""
    js = f"""
var allText = document.body.innerText;
var idx = allText.indexOf('{month}');
var section = (idx >= 0) ? allText.substring(idx, idx + 1500) : '';
JSON.stringify(section);
"""
    raw = gstack(['js', js])
    try:
        return json.loads(raw)
    except Exception:
        return raw


def parse_departures(section: str, month: str) -> list:
    """Extract departure records from OAT accordion section text."""
    results = []
    month_abbr = 'Oct' if month == 'October' else 'Nov'
    pattern = re.findall(
        r'(?:Oct|Nov)\s+(\d{1,2})\s*\n(\d{1,2})\s*\n([^\n]+)',
        section
    )
    for day, duration, route in pattern:
        results.append({
            'date_str': f'{month_abbr} {day}, 2026',
            'days': duration,
            'route': route.strip(),
            'month': month,
        })
    return results


def get_ship_from_page() -> str:
    """Extract ship name from OAT trip page."""
    js = "document.body.innerText.substring(0, 800)"
    page_text = gstack(['js', js])
    m = re.search(
        r'(?:M/V|M\.V\.|MV|S/V|S\.V\.|SV|SS)\s+([A-Za-z\s]+?)(?:\n|Days|Group)',
        page_text
    )
    if m:
        return m.group(0).strip()
    return 'OAT Small Ship'


def scrape_oat(year: int, months: list, output_path: Path,
               verbose: bool = False) -> list:
    """
    Visit all OAT Euro/Med/Arctic trip pages and extract Oct/Nov departures.
    Returns list of departure records.
    """
    month_names = {10: 'October', 11: 'November'}
    target_months = [month_names[m] for m in months if m in month_names]

    all_results = []
    pages_checked = 0
    trips_found = 0
    total = len(OAT_EURO_TRIPS)

    print(f"  [oat] Checking {total} European/Med/Arctic OAT trips...")

    for i, (region, slug, name) in enumerate(OAT_EURO_TRIPS):
        url = (f"{OAT_BASE_URL}/{region}/{slug}"
               f"/availabledatesandprices?step=0")
        progress(i + 1, total, name)

        if not goto(url):
            if verbose:
                print(f'\n  [oat] SKIP (failed to load): {name}')
            continue

        time.sleep(3)
        pages_checked += 1

        # Check if page mentions any target month at all
        page_text = gstack(['js', 'document.body.innerText'])

        trip_records = []
        for month in target_months:
            if month not in page_text:
                continue
            if not click_month_button(month):
                continue
            time.sleep(2)
            section = extract_month_section(month)
            records = parse_departures(section, month)
            if records:
                ship = get_ship_from_page()
                for r in records:
                    trip_records.append({
                        'cruise_line': 'Overseas Adventure Travel',
                        'ship_name': ship,
                        'trip_name': name,
                        'departure_date': r['date_str'],
                        'days': r['days'],
                        'route': r['route'],
                        'month': r['month'],
                        'region': region,
                        'url_slug': slug,
                    })

        if trip_records:
            trips_found += 1
            all_results.extend(trip_records)

    print(f"\n  [oat] {pages_checked}/{total} pages checked, "
          f"{trips_found} trips with data, {len(all_results)} total departures")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(all_results, indent=2))
    print(f"  [oat] Saved → {output_path}")
    return all_results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Scrape OAT.com trip departures')
    parser.add_argument('--year',    type=int, default=2026)
    parser.add_argument('--months',  nargs='+', type=int, default=[10, 11])
    parser.add_argument('--output',  type=Path, default=OAT_JSON)
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()

    if not GSTACK_BIN.exists():
        print(f'ERROR: gstack browse binary not found at {GSTACK_BIN}')
        print('Run: cd ~/.claude/skills/gstack && ./setup')
        sys.exit(1)

    print(f"[oat] Scraping OAT {args.year} months={args.months}")
    results = scrape_oat(
        year=args.year,
        months=args.months,
        output_path=args.output,
        verbose=args.verbose,
    )
    print(f"[oat] Done — {len(results)} departures")
