"""
Cruise Intel — CruisesOnly (cruisesonly.com) Scraper
Uses requests for promotion pages (static HTML); gstack for search results (JS required).

⚠️ TIER 1 STATUS: CruisesOnly search (results.do) is protected by Imperva/Incapsula bot detection
(confirmed 2026-05-27). Direct requests return a 212-byte JS challenge page. gstack sessions land on
homepage (empty #root div, app never hydrates). Tier 1 returns 0 results until a residential proxy or
manual session-cookie injection is available.

✅ TIER 2 STATUS: Promotion landing pages (/promotion/{slug}.do?c={code}) serve static HTML — no JS
required, no bot detection. These pages work with plain requests. Confirmed via playwright MCP session
2026-05-27. Dates are month-level only (no specific day); departure_date is set to first-of-month and
flagged date_approx=true. Prices available for Silversea; other lines omit prices from promotion pages.

Two-tier strategy:
  Tier 1 (preferred, BLOCKED) — Search results page with date range:
    /results.do?clp=1&c={code}&d1=MM/DD/YYYY&d2=MM/DD/YYYY&sort=departuredate
    Gives: specific dated sailings with route + price
    Status: BLOCKED by Incapsula — requires residential proxy

  Tier 2 (active) — Promotion landing page:
    /promotion/{slug}.do?c={code}
    Gives: itinerary blocks with ship, route, port, month-level dates, price (Silversea only)
    Limitation: departure_date approximate (first of month); date_approx=True in output

Promotion page format (confirmed via playwright, 2026-05-27):
  "N Night Route Name"
  "Ship Name"
  "Departing from: Port, Country"
  "Sailing Dates: Month YYYY [• Month YYYY ...]"
  "Suite from" / "$" / "X,XXX" / "($NNN/" / "per" / "night)"

Manual playwright scrape performed 2026-05-27 → output/T2_CRUISESONLY.json (14 records).
Re-scrape: run scrape_cruisesonly.py --tier2 to refresh via requests on promotion pages.

CruisesOnly search result text format (Silversea, confirmed via gstack probe — for when Tier 1 unblocks):
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

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent))
from config import CRUISESONLY_JSON, CRUISESONLY_LINES, GSTACK_BIN
from utils import is_europe_med_arctic, norm_ship

BASE = 'https://www.cruisesonly.com'
PROMO_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.cruisesonly.com/',
}

# Promotion page slugs/codes (confirmed working 2026-05-27 via playwright)
PROMO_URLS: dict[str, tuple[str, Optional[int]]] = {
    'Silversea':     ('silversea-cruises',               50),
    'Seabourn':      ('seabourn-cruises',                48),
    'Regent':        ('regent-cruises',                  41),
    'Crystal':       ('crystal-cruises',                369),
    'Viking':        ('viking-ocean-cruises',           354),
    'Oceania':       ('oceania-cruises',                 67),
    'Ponant':        ('compagnie-du-ponant-cruises',    344),
    'Azamara':       ('azamara-cruises',                325),
}


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


# ── Tier 2: Promotion page scraper (requests, static HTML, no Incapsula) ─────

_MONTH_MAP = {
    'January':1,'February':2,'March':3,'April':4,'May':5,'June':6,
    'July':7,'August':8,'September':9,'October':10,'November':11,'December':12,
}

def _scrape_promo_page(
    line_key: str, slug: str, code: Optional[int],
    year: int, months: list[int],
    verbose: bool,
) -> list[dict]:
    """
    Tier 2: Fetch a CruisesOnly promotion page via requests (static HTML).
    Returns voyage dicts with month-level dates (date_approx=True).

    HTML structure (confirmed 2026-05-27):
      Cards: <li class="wth2-resultsCardLi">
        Ship:  <* class="wth2-shipName">
        Dates: <ul class="wth2-sailingListDates"><li class="wth2-sailingListDatesLi">Month YYYY</li>
        Route/nights: card text line matching "N Night Route Name"
        Port:  card text line matching "Departing from: Port, Country"
    """
    url = f'{BASE}/promotion/{slug}.do'
    if code:
        url += f'?c={code}'

    try:
        time.sleep(1.2)
        r = requests.get(url, headers=PROMO_HEADERS, timeout=25)
        r.raise_for_status()
    except Exception as e:
        print(f'  [cruisesonly/t2] {line_key}: HTTP error — {e}')
        return []

    soup = BeautifulSoup(r.text, 'html.parser')
    cards = soup.find_all('li', class_='wth2-resultsCardLi')
    if not cards:
        print(f'  [cruisesonly/t2] {line_key}: no result cards found (HTML structure changed?)')
        return []

    nights_re = re.compile(r'^(\d+)\s+Night\s+(.+)', re.I)
    price_re  = re.compile(r'\$([\d,]+)')

    voyages: list[dict] = []
    seen: set[tuple] = set()

    for card in cards:
        # Ship name
        ship_el = card.find(class_='wth2-shipName')
        ship = ship_el.get_text(strip=True) if ship_el else ''

        # Route and nights — scan card text lines for "N Night Route Name"
        route = ''
        nights = ''
        for line in card.get_text(separator='\n').split('\n'):
            nm = nights_re.match(line.strip())
            if nm:
                nights = nm.group(1)
                route = nm.group(2).strip()
                break

        # Departure port — search card text lines for "Departing from:"
        port = ''
        for line in card.get_text(separator='\n').split('\n'):
            pm = re.search(r'Departing from:\s*(.+)', line.strip(), re.I)
            if pm:
                port = pm.group(1).strip()
                break

        # Price — first $ amount in card text (Silversea provides this; others omit)
        card_text = card.get_text(separator=' ')
        price_m = price_re.search(card_text)
        price_val = price_m.group(1).replace(',', '') if price_m else ''

        # Sailing dates — <li class="wth2-sailingListDatesLi"> contains "Month YYYY"
        date_items = card.find_all('li', class_='wth2-sailingListDatesLi')
        for li in date_items:
            month_str = li.get_text(strip=True)
            mm = re.match(r'([A-Za-z]+)\s+(\d{4})$', month_str)
            if not mm:
                continue
            month_num = _MONTH_MAP.get(mm.group(1))
            if not month_num:
                continue
            yr = int(mm.group(2))
            if yr != year or month_num not in months:
                continue

            dep_date = date(yr, month_num, 1).isoformat()

            if not is_europe_med_arctic(port, '', route + ' ' + port):
                continue

            key = (norm_ship(ship), dep_date)
            if key in seen:
                continue
            seen.add(key)

            voyages.append({
                'departure_date': dep_date,
                'ship_name':      ship,
                'route':          route[:120],
                'port':           port,
                'days':           nights,
                'price_usd':      price_val,
                'cruise_line':    line_key,
                'date_approx':    True,
                'source':         'cruisesonly_promotion',
            })

    if verbose and voyages:
        for v in voyages:
            print(f'    {v["departure_date"]}* {v["ship_name"][:20]:<20}  '
                  f'{v["days"]:>3}n  {v["route"][:50]}')

    return voyages


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
    tier2_only: bool = False,
) -> list[dict]:
    """
    Scrape CruisesOnly for all target luxury cruise lines.
    Returns list of voyage dicts for given year/months (Euro/Med/Arctic only).

    tier2_only=True: skip Tier 1 (blocked by Incapsula), use promotion pages only.
    Default (tier2_only=False): attempts Tier 1 first; falls back to Tier 2 if 0 results.
    """
    if tier2_only:
        return _scrape_tier2(year, months, output_path, verbose)

    if not GSTACK_BIN.exists():
        print(f'  [cruisesonly] WARNING: gstack not found — falling back to Tier 2 (promotion pages)')
        return _scrape_tier2(year, months, output_path, verbose)

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

    if not all_voyages:
        print('  [cruisesonly] Tier 1 returned 0 results (likely Incapsula block) — falling back to Tier 2')
        return _scrape_tier2(year, months, output_path, verbose)

    all_voyages.sort(key=lambda v: v['departure_date'])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(all_voyages, indent=2))
    print(f'  [cruisesonly] {len(all_voyages)} total sailings saved → {output_path}')
    return all_voyages


def _scrape_tier2(
    year: int,
    months: list[int],
    output_path: Path,
    verbose: bool = False,
) -> list[dict]:
    """
    Tier 2: scrape all luxury line promotion pages via requests (static HTML).
    Dates are month-level approximations (first of month, date_approx=True).
    """
    all_voyages: list[dict] = []
    seen: set[tuple] = set()

    for line_key, (slug, code) in PROMO_URLS.items():
        print(f'  [cruisesonly/t2] {line_key}: promotion page → /promotion/{slug}.do', flush=True)
        voyages = _scrape_promo_page(line_key, slug, code, year, months, verbose)
        for v in voyages:
            key = (norm_ship(v['ship_name']), v['departure_date'])
            if key not in seen:
                seen.add(key)
                all_voyages.append(v)
        if voyages:
            print(f'  [cruisesonly/t2]   → {len(voyages)} sailings (dates approx)', flush=True)

    all_voyages.sort(key=lambda v: v['departure_date'])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(all_voyages, indent=2))
    print(f'  [cruisesonly/t2] {len(all_voyages)} total sailings saved → {output_path}')
    return all_voyages


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Scrape CruisesOnly (cruisesonly.com)')
    parser.add_argument('--year',      type=int, default=2026)
    parser.add_argument('--months',    nargs='+', type=int, default=[10, 11])
    parser.add_argument('--output',    type=Path, default=CRUISESONLY_JSON)
    parser.add_argument('--verbose',   action='store_true')
    parser.add_argument('--tier2',     action='store_true',
                        help='Use Tier 2 promotion pages only (bypass Tier 1 Incapsula block)')
    args = parser.parse_args()

    print(f'[cruisesonly] Scraping {args.year} months={args.months}'
          + (' [tier2/promotion]' if args.tier2 else ''))
    results = scrape_cruisesonly(
        year=args.year, months=args.months,
        output_path=args.output, verbose=args.verbose,
        tier2_only=args.tier2,
    )
    print(f'[cruisesonly] Done — {len(results)} sailings → {args.output}')
