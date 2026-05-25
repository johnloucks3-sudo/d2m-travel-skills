"""
Cruise Intel — SeaDream Yacht Club (seadream.com) Scraper
Uses gstack headless browser to load destination pages and extract voyage entries
via text parsing. No hidden API — pure server-rendered HTML.

Sources:
  - seadream.com/voyages/destinations/mediterranean
  - seadream.com/voyages/destinations/scandinavia-northern-europe

Coverage: SeaDream I and SeaDream II — 112 guests each.
Med season runs Oct–Dec. No Northern Europe in Oct/Nov.
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
from config import OUTPUT_DIR, SEADREAM_JSON, GSTACK_BIN
from utils import is_europe_med_arctic

SEADREAM_DEST_URLS = {
    'Mediterranean': 'https://seadream.com/voyages/destinations/mediterranean',
    'Northern Europe': 'https://seadream.com/voyages/destinations/scandinavia-northern-europe',
}

MONTH_SHORT = {
    'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
    'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12,
}


def gstack(cmd: list, timeout: int = 45) -> str:
    """Run a gstack command, return stdout."""
    result = subprocess.run(
        [str(GSTACK_BIN)] + cmd,
        capture_output=True, text=True, timeout=timeout
    )
    return result.stdout.strip()


def parse_date_str(s: str) -> date | None:
    """Parse 'Oct 10, 2026' or 'Oct 10 2026' into a date object."""
    s = s.strip()
    for fmt in ('%b %d, %Y', '%b %d %Y', '%B %d, %Y', '%B %d %Y'):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def parse_seadream_page(text: str, region_name: str) -> list:
    """
    Extract voyage entries from SeaDream destination page text.
    SeaDream listing format (per Dembe probe):
      {ID} | {Name} | {Departure Date} to {End Date} | {Route} | {N} Nights
    Also handles plain text blocks where date patterns appear with surrounding context.
    """
    voyages = []
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    # Pattern 1: Pipe-delimited rows (observed in Dembe probe)
    pipe_pattern = re.compile(
        r'(\d+\w*)\s*\|\s*(.+?)\s*\|\s*'
        r'(\w+ \d+,? \d{4})\s+to\s+(\w+ \d+,? \d{4})\s*\|\s*(.+?)\s*\|\s*(\d+)\s*Nights?',
        re.IGNORECASE
    )

    for line in lines:
        m = pipe_pattern.search(line)
        if m:
            voyage_id = m.group(1).strip()
            name = m.group(2).strip()
            dep_raw = m.group(3).strip()
            arr_raw = m.group(4).strip()
            route = m.group(5).strip()
            nights = m.group(6).strip()

            dep_date = parse_date_str(dep_raw)
            arr_date = parse_date_str(arr_raw)

            if dep_date:
                voyages.append({
                    'voyage_id':       voyage_id,
                    'name':            name,
                    'departure_date':  dep_date.isoformat(),
                    'arrival_date':    arr_date.isoformat() if arr_date else '',
                    'nights':          nights,
                    'route':           route,
                    'region':          region_name,
                })
            continue

    # Pattern 2: Date + context block (fallback — extract date lines and surrounding text)
    if not voyages:
        date_pattern = re.compile(
            r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*'
            r'\s+\d{1,2},?\s+\d{4})',
            re.IGNORECASE
        )
        i = 0
        while i < len(lines):
            line = lines[i]
            m = date_pattern.search(line)
            if not m:
                i += 1
                continue

            dep_date = parse_date_str(m.group(1))
            if not dep_date:
                i += 1
                continue

            # Gather context: 2 lines before + 4 lines after
            ctx = lines[max(0, i - 2):min(len(lines), i + 5)]
            ctx_text = ' | '.join(ctx)

            # Try to find the arrival date
            arr_dates = date_pattern.findall(ctx_text)
            arr_date = None
            if len(arr_dates) >= 2:
                arr_date = parse_date_str(arr_dates[1])

            # Extract nights
            nights_m = re.search(r'(\d+)\s*Nights?', ctx_text, re.IGNORECASE)
            nights = nights_m.group(1) if nights_m else ''

            # Extract voyage name (non-date, non-noise line before the date)
            name = ''
            for prev_line in reversed(lines[max(0, i - 3):i]):
                if (len(prev_line) > 5 and
                        not date_pattern.search(prev_line) and
                        not re.match(r'^\d+$', prev_line) and
                        'Book' not in prev_line and
                        'Night' not in prev_line):
                    name = prev_line
                    break

            # Extract route (line after date block)
            route = ''
            for next_line in lines[i + 1:min(len(lines), i + 5)]:
                if (len(next_line) > 5 and
                        not date_pattern.search(next_line) and
                        'Night' not in next_line and
                        'Book' not in next_line):
                    route = next_line
                    break

            voyages.append({
                'voyage_id':      '',
                'name':           name,
                'departure_date': dep_date.isoformat(),
                'arrival_date':   arr_date.isoformat() if arr_date else '',
                'nights':         nights,
                'route':          route or name,
                'region':         region_name,
            })
            i += 3  # Skip ahead past this block

    return voyages


def scrape_seadream(
    year: int,
    months: list,
    output_path: Path,
    verbose: bool = False,
) -> list:
    """
    Scrape SeaDream destination pages for voyages in given year/months.
    Returns Euro/Med sailings only.
    """
    if not GSTACK_BIN.exists():
        raise RuntimeError(f'gstack binary not found at {GSTACK_BIN}')

    all_voyages = []

    for region_name, url in SEADREAM_DEST_URLS.items():
        print(f'  [seadream] Loading {region_name}: {url}', flush=True)

        result = subprocess.run(
            [str(GSTACK_BIN), 'goto', url],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            print(f'  [seadream] Navigation failed for {region_name}')
            continue

        time.sleep(3)

        text = gstack(['text'], timeout=60)
        if not text:
            print(f'  [seadream] Empty text for {region_name}')
            continue

        voyages = parse_seadream_page(text, region_name)
        print(f'  [seadream] Parsed {len(voyages)} raw voyages from {region_name}')

        # Filter to target year/months + Euro/Med geographic filter
        filtered = []
        geo_rejected = 0
        for v in voyages:
            try:
                d = date.fromisoformat(v['departure_date'])
                if d.year != year or d.month not in months:
                    continue
                # Exclude transatlantic / Caribbean routes leaving Europe
                route = v.get('route', '')
                if not is_europe_med_arctic('', '', route):
                    geo_rejected += 1
                    continue
                v['month'] = d.strftime('%B')
                v['ship_name'] = (
                    'SeaDream II' if v['voyage_id'].startswith('2')
                    else 'SeaDream I' if v['voyage_id'].startswith('1')
                    else 'SeaDream'
                )
                filtered.append(v)
            except ValueError:
                pass

        if geo_rejected:
            print(f'  [seadream] {geo_rejected} non-Euro/Med voyages excluded by geo filter')
        print(f'  [seadream] {len(filtered)} in {year} months {months}')
        all_voyages.extend(filtered)

    # Deduplicate by voyage_id or (ship + date)
    seen: set = set()
    deduped = []
    for v in all_voyages:
        key = (v.get('voyage_id', '') or
               (v.get('ship_name', '').lower() + v['departure_date']))
        if key not in seen:
            seen.add(key)
            deduped.append(v)

    if verbose and deduped:
        for v in deduped:
            print(f'    {v["departure_date"]}  {v.get("ship_name",""):12s}  '
                  f'{v["nights"]:3s}n  {v["route"][:60]}')

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(deduped, indent=2))
    print(f'  [seadream] {len(deduped)} sailings saved → {output_path}')
    return deduped


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Scrape SeaDream Yacht Club (seadream.com)')
    parser.add_argument('--year',    type=int, default=2026)
    parser.add_argument('--months',  nargs='+', type=int, default=[10, 11])
    parser.add_argument('--output',  type=Path, default=SEADREAM_JSON)
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()

    print(f'[seadream] Scraping {args.year} months={args.months}')
    results = scrape_seadream(
        year=args.year,
        months=args.months,
        output_path=args.output,
        verbose=args.verbose,
    )
    print(f'[seadream] Done — {len(results)} sailings → {args.output}')
