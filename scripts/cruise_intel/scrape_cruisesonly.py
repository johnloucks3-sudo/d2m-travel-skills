"""
Cruise Intel — CruisesOnly (cruisesonly.com) Scraper
Uses gstack headless browser (JS rendering required).

⚠️ SITE STATUS: CruisesOnly is protected by Imperva/Incapsula bot detection (confirmed 2026-05-27).
Direct requests return a 212-byte JS challenge page. gstack sessions land on homepage (empty #root div,
app never hydrates). Resolution requires residential proxy or manual session-cookie injection.
This scraper will return 0 results until bypass is available.

Two-tier strategy:
  Tier 1 (preferred) — Search results page with date range:
    /results.do?clp=1&c={code}&d1=MM/DD/YYYY&d2=MM/DD/YYYY&sort=departuredate
    Gives: specific dated sailings with route + price

  Tier 2 (fallback) — Promotion landing page:
    /promotion/{slug}.do
    Gives: price context per ship/region (no specific departure dates — skipped)

CruisesOnly search result text format (Silversea, confirmed via gstack probe):
  "N Night Route Name"
  "Ship Name"
  "Departs: Port"
  "From: $X,XXX"
  "Departing: MMMM DD, YYYY"
"""
import argparse
import json
import re
import subprocess
import sys
import time
from datetime import date, datetime
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))
from config import CRUISESONLY_JSON, CRUISESONLY_LINES, GSTACK_BIN
from utils import is_europe_med_arctic, norm_ship


def _gstack(cmd: list, timeout: int = 60) -> str:
    """Run a gstack command, return stdout stripped."""
    result = subprocess.run(
        [str(GSTACK_BIN)] + cmd,
        capture_output=True, text=True, timeout=timeout,
    )
    return result.stdout.strip()


def _navigate(url: str, wait: float = 3.5) -> bool:
    """Navigate gstack to URL. Returns True on success."""
    result = subprocess.run(
        [str(GSTACK_BIN), 'goto', url],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        return False
    time.sleep(wait)
    return True


def _parse_date(s: str) -> Optional[date]:
    """Parse departure date strings from CruisesOnly results."""
    s = s.strip()
    for fmt in ('%B %d, %Y', '%b %d, %Y', '%m/%d/%Y', '%Y-%m-%d'):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def _parse_search_text(text: str) -> list[dict]:
    """
    Parse CruisesOnly search-results rendered text into voyage dicts.
    Handles both structured and semi-structured layouts.
    """
    voyages: list[dict] = []
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    # Pattern: "Departing [Month DD, YYYY]" or "Departing: [date]"
    dep_re = re.compile(
        r'(?:Departing|Departs|Departure)[:\s]+([A-Za-z]+ \d{1,2},? \d{4})',
        re.IGNORECASE,
    )
    nights_re = re.compile(r'(\d+)\s*(?:-?\s*Night|N\b)', re.IGNORECASE)
    price_re  = re.compile(r'\$\s*([\d,]+)', re.IGNORECASE)
    ship_re   = re.compile(
        r'\b(Silver\s+\w+|Seven Seas \w+|Seabourn \w+|Viking \w+|'
        r'Nautica|Riviera|Marina|Insignia|Regatta|Sirena|'
        r'Le \w+|L\'Austral|Ponant|Explora \w+|Crystal \w+|'
        r'Queen Mary 2|Queen Victoria|Queen Anne|Queen Elizabeth|'
        r'World Navigator|World Traveller|World Voyager|World Seeker|World Explorer|'
        r'Evrima|Scenic Eclipse|Scenic Eclipse II|'
        r'National Geographic \w+|Sea Bird|Sea Lion)',
        re.IGNORECASE,
    )

    i = 0
    while i < len(lines):
        line = lines[i]

        # Look for departure date line
        dep_m = dep_re.search(line)
        if not dep_m:
            i += 1
            continue

        dep_date = _parse_date(dep_m.group(1))
        if not dep_date:
            i += 1
            continue

        # Gather context window (5 lines before + 3 after)
        ctx_lines = lines[max(0, i - 5):i + 4]
        ctx = ' \n '.join(ctx_lines)

        # Extract nights
        nights_m = nights_re.search(ctx)
        nights = nights_m.group(1) if nights_m else ''

        # Extract price
        price_m = price_re.search(ctx)
        price = price_m.group(1).replace(',', '') if price_m else ''

        # Extract ship name
        ship_m = ship_re.search(ctx)
        ship = ship_m.group(0).strip() if ship_m else ''

        # Extract route — look for lines with "Night" + destination context
        route = ''
        for cl in ctx_lines:
            if nights and re.search(r'\d+\s*Night', cl, re.I):
                # Strip leading night count
                route = re.sub(r'^\d+\s*-?\s*Night\s*', '', cl, flags=re.I).strip()
                break

        # Port: line containing "Departs" or "From:"
        port = ''
        for cl in ctx_lines:
            pm = re.search(r'(?:Departs?|From)[:\s]+([A-Za-z][A-Za-z ,]+)', cl, re.I)
            if pm:
                cand = pm.group(1).strip().rstrip(',')
                # Reject price patterns
                if not re.match(r'\$', cand) and len(cand) > 2:
                    port = cand
                    break

        # Geo filter
        if not is_europe_med_arctic(port, '', route):
            i += 1
            continue

        voyages.append({
            'departure_date': dep_date.isoformat(),
            'ship_name':      ship,
            'route':          route[:120],
            'port':           port,
            'days':           nights,
            'price_usd':      price,
            'cruise_line':    '',
        })
        i += 1

    # Deduplicate
    seen: set[tuple] = set()
    deduped: list[dict] = []
    for v in voyages:
        key = (norm_ship(v['ship_name']), v['departure_date'])
        if key not in seen:
            seen.add(key)
            deduped.append(v)

    return deduped


def _scrape_line_search(
    line_key: str, slug: str, code: Optional[int],
    year: int, months: list[int],
    verbose: bool,
) -> list[dict]:
    """
    Attempt Tier 1 (search) for a given cruise line.
    Returns list of voyage dicts.
    """
    # Build date range for search URL
    m_min, m_max = min(months), max(months)
    d1 = f'{m_min:02d}/01/{year}'
    # Last day of last month — use day 30 as safe max
    d2 = f'{m_max:02d}/30/{year}'

    if code:
        url = (f'https://www.cruisesonly.com/results.do'
               f'?clp=1&c={code}&d1={d1}&d2={d2}&sort=departuredate')
    else:
        url = (f'https://www.cruisesonly.com/results.do'
               f'?clp=1&q={slug.replace("-", "+")}&d1={d1}&d2={d2}&sort=departuredate')

    print(f'  [cruisesonly] {line_key}: search → {url[:80]}...', flush=True)
    ok = _navigate(url, wait=4.0)
    if not ok:
        print(f'  [cruisesonly]   navigation failed')
        return []

    # Scroll to load more results
    _gstack(['js', 'window.scrollTo(0, document.body.scrollHeight)'], timeout=10)
    time.sleep(2)

    text = _gstack(['text'], timeout=60)
    if not text:
        print(f'  [cruisesonly]   empty page')
        return []

    voyages = _parse_search_text(text)

    # Assign cruise line name
    for v in voyages:
        if not v['cruise_line']:
            v['cruise_line'] = line_key

    # Filter to exact target months
    filtered = [v for v in voyages
                if _parse_date(v['departure_date']) and
                _parse_date(v['departure_date']).year == year and
                _parse_date(v['departure_date']).month in months]

    if verbose and filtered:
        for v in filtered:
            print(f'    {v["departure_date"]}  {v["ship_name"][:20]:<20}  '
                  f'{v["days"]:>3}n  {v["route"][:50]}  ${v["price_usd"]}')

    return filtered


def scrape_cruisesonly(
    year: int,
    months: list[int],
    output_path: Path,
    lines: dict = None,
    verbose: bool = False,
) -> list[dict]:
    """
    Scrape CruisesOnly for all target luxury cruise lines.
    Returns list of voyage dicts for given year/months (Euro/Med/Arctic only).
    """
    if not GSTACK_BIN.exists():
        raise RuntimeError(f'gstack binary not found at {GSTACK_BIN}')

    if lines is None:
        lines = CRUISESONLY_LINES

    all_voyages: list[dict] = []
    seen: set[tuple] = set()

    for line_key, (slug, code) in lines.items():
        voyages = _scrape_line_search(line_key, slug, code, year, months, verbose)
        for v in voyages:
            key = (norm_ship(v['ship_name']), v['departure_date'])
            if key not in seen:
                seen.add(key)
                all_voyages.append(v)
        if voyages:
            print(f'  [cruisesonly]   → {len(voyages)} sailings', flush=True)

    all_voyages.sort(key=lambda v: v['departure_date'])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(all_voyages, indent=2))
    print(f'  [cruisesonly] {len(all_voyages)} total sailings saved → {output_path}')
    return all_voyages


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Scrape CruisesOnly (cruisesonly.com)')
    parser.add_argument('--year',    type=int, default=2026)
    parser.add_argument('--months',  nargs='+', type=int, default=[10, 11])
    parser.add_argument('--output',  type=Path, default=CRUISESONLY_JSON)
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()

    print(f'[cruisesonly] Scraping {args.year} months={args.months}')
    results = scrape_cruisesonly(
        year=args.year, months=args.months,
        output_path=args.output, verbose=args.verbose,
    )
    print(f'[cruisesonly] Done — {len(results)} sailings → {args.output}')
