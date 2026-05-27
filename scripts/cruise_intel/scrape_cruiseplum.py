"""
Cruise Intel — CruisePlum (cruiseplum.com) Scraper
Uses gstack headless browser with authenticated session.

CruisePlum requires login to access full search results (403 without auth).
Credentials: env vars CRUISEPLUM_USER / CRUISEPLUM_PASS  OR
             file ~/.config/d2m/cruiseplum.env  (USER=... / PASS=... lines)

Search strategy:
  1. Navigate to login page
  2. Fill credentials + submit
  3. Navigate to search with target date range + region filters
  4. Scroll to load all results
  5. Parse resulting table / listings

CruisePlum listing format (from account search):
  Ship Name · Cruise Line
  Route / Itinerary Name
  Departing: Port  Arriving: Port
  N nights  |  DD Month YYYY  |  from $X,XXX (out-the-door pricing)
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import date, datetime
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))
from config import (
    CRUISEPLUM_JSON, CRUISEPLUM_CREDS_FILE, GSTACK_BIN,
)
from utils import is_europe_med_arctic, norm_ship

# CruisePlum URLs
CRUISEPLUM_LOGIN_URL  = 'https://www.cruiseplum.com/login'
CRUISEPLUM_SEARCH_URL = 'https://www.cruiseplum.com/search'


def _load_creds() -> tuple[str, str]:
    """
    Load CruisePlum credentials.
    Priority: env vars → ~/.config/d2m/cruiseplum.env → raise RuntimeError
    """
    user = os.environ.get('CRUISEPLUM_USER', '')
    passwd = os.environ.get('CRUISEPLUM_PASS', '')
    if user and passwd:
        return user, passwd

    if CRUISEPLUM_CREDS_FILE.exists():
        cfg: dict[str, str] = {}
        for line in CRUISEPLUM_CREDS_FILE.read_text().splitlines():
            if '=' in line and not line.startswith('#'):
                k, _, v = line.partition('=')
                cfg[k.strip().upper()] = v.strip().strip('"\'')
        user   = cfg.get('USER', '')
        passwd = cfg.get('PASS', '') or cfg.get('PASSWORD', '')
        if user and passwd:
            return user, passwd

    raise RuntimeError(
        'CruisePlum credentials not found.\n'
        'Set env vars CRUISEPLUM_USER + CRUISEPLUM_PASS, or create:\n'
        f'  {CRUISEPLUM_CREDS_FILE}\n'
        'with lines:\n  USER=your@email.com\n  PASS=yourpassword'
    )


def _gstack(cmd: list, timeout: int = 60) -> str:
    """Run a gstack command, return stdout stripped."""
    result = subprocess.run(
        [str(GSTACK_BIN)] + cmd,
        capture_output=True, text=True, timeout=timeout,
    )
    return result.stdout.strip()


def _navigate(url: str, wait: float = 3.0) -> bool:
    """Navigate to URL. Returns True on success."""
    result = subprocess.run(
        [str(GSTACK_BIN), 'goto', url],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        return False
    time.sleep(wait)
    return True


def _login(username: str, password: str) -> bool:
    """
    Log in to CruisePlum.
    Uses gstack fill + click — works on standard email/password form.
    Returns True if login appears successful.
    """
    print('  [cruiseplum] Navigating to login page...', flush=True)
    if not _navigate(CRUISEPLUM_LOGIN_URL, wait=3.0):
        print('  [cruiseplum] Failed to load login page')
        return False

    # Take snapshot to find form selectors
    snap = _gstack(['snapshot', '-i'], timeout=15)

    # Try common email/password selectors (CruisePlum uses standard HTML forms)
    email_selectors    = ['input[type=email]', 'input[name=email]', 'input[id*=email]',
                          'input[placeholder*=email]', '#email', '.email input']
    password_selectors = ['input[type=password]', 'input[name=password]',
                          'input[id*=password]', '#password', '.password input']
    submit_selectors   = ['button[type=submit]', 'input[type=submit]',
                          'button.login', 'button.sign-in', '[data-testid*=login]',
                          'form button']

    def _try_fill(selectors: list[str], value: str) -> bool:
        for sel in selectors:
            result = subprocess.run(
                [str(GSTACK_BIN), 'fill', sel, value],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                return True
        return False

    def _try_click(selectors: list[str]) -> bool:
        for sel in selectors:
            result = subprocess.run(
                [str(GSTACK_BIN), 'click', sel],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                return True
        return False

    print('  [cruiseplum] Filling credentials...', flush=True)
    if not _try_fill(email_selectors, username):
        print('  [cruiseplum] WARNING: could not fill email field — trying anyway')
    time.sleep(0.5)
    if not _try_fill(password_selectors, password):
        print('  [cruiseplum] WARNING: could not fill password field — trying anyway')
    time.sleep(0.5)

    print('  [cruiseplum] Submitting login...', flush=True)
    _try_click(submit_selectors)
    time.sleep(4.0)

    # Verify: check current URL or page text
    current_url = _gstack(['url'], timeout=10)
    page_text   = _gstack(['text'], timeout=30)

    if 'login' in current_url.lower() and 'error' in page_text.lower():
        print('  [cruiseplum] Login appears to have failed (still on login page with errors)')
        return False

    if 'login' not in current_url.lower():
        print(f'  [cruiseplum] Login succeeded → {current_url[:60]}')
        return True

    # Might still be on login page but without error — treat as success and continue
    print(f'  [cruiseplum] Login status uncertain (URL: {current_url[:60]}), proceeding...')
    return True


def _build_search_url(year: int, months: list[int]) -> str:
    """
    Build CruisePlum search URL with date range.
    Tries common URL parameter patterns.
    """
    m_min, m_max = min(months), max(months)
    d_from = f'{year}-{m_min:02d}-01'
    d_to   = f'{year}-{m_max:02d}-30'
    # CruisePlum uses various param names — try the most common
    return (
        f'{CRUISEPLUM_SEARCH_URL}'
        f'?departureFrom={d_from}&departureTo={d_to}'
        f'&region=europe&region=mediterranean&region=arctic'
    )


def _parse_date(s: str) -> Optional[date]:
    """Parse date string variants from CruisePlum listings."""
    s = s.strip()
    for fmt in ('%d %b %Y', '%B %d, %Y', '%b %d, %Y', '%Y-%m-%d',
                '%d/%m/%Y', '%m/%d/%Y', '%d %B %Y'):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    # Try "DD Month YYYY" with spaces
    m = re.match(r'(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})', s)
    if m:
        try:
            return datetime.strptime(f'{m.group(1)} {m.group(2)} {m.group(3)}', '%d %B %Y').date()
        except ValueError:
            pass
    return None


def _parse_cruiseplum_text(text: str, year: int, months: list[int]) -> list[dict]:
    """
    Parse CruisePlum search results text into voyage dicts.
    CruisePlum shows rich per-sailing detail; we extract key fields.
    """
    voyages: list[dict] = []
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    # Date pattern: "DD Month YYYY" or "Month DD, YYYY"
    date_re  = re.compile(
        r'\b(\d{1,2})\s+(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|'
        r'Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|'
        r'Nov(?:ember)?|Dec(?:ember)?)\s+(\d{4})\b',
        re.IGNORECASE,
    )
    price_re  = re.compile(r'\$\s*([\d,]+)')
    nights_re = re.compile(r'(\d+)\s*(?:-?\s*nights?|n\b)', re.IGNORECASE)
    ship_re   = re.compile(
        r'\b(Silver\s+\w+|Seven Seas \w+|Seabourn \w+|Viking \w+|'
        r'Nautica|Riviera|Marina|Insignia|Regatta|Sirena|'
        r'Le \w+|L\'Austral|Explora \w+|Crystal \w+|SeaDream [I]+|'
        r'Queen Mary 2|Queen Victoria|Queen Anne|Queen Elizabeth|'
        r'World Navigator|World Traveller|World Voyager|World Seeker|World Explorer|'
        r'Evrima|Scenic Eclipse|Scenic Eclipse II|'
        r'National Geographic \w+|Sea Bird|Sea Lion)',
        re.IGNORECASE,
    )

    i = 0
    while i < len(lines):
        line = lines[i]
        dm = date_re.search(line)
        if not dm:
            i += 1
            continue

        dep_str = f'{dm.group(1)} {dm.group(2)} {dm.group(3)}'
        dep = _parse_date(dep_str)
        if not dep or dep.year != year or dep.month not in months:
            i += 1
            continue

        # Context window
        ctx_lines = lines[max(0, i - 6):i + 5]
        ctx = ' \n '.join(ctx_lines)

        nights_m = nights_re.search(ctx)
        nights = nights_m.group(1) if nights_m else ''

        price_m = price_re.search(ctx)
        price = price_m.group(1).replace(',', '') if price_m else ''

        ship_m = ship_re.search(ctx)
        ship = ship_m.group(0).strip() if ship_m else ''

        # Route: look for line with "-" or "to" pattern between port names
        route = ''
        for cl in ctx_lines:
            if re.search(r'\b\w+\s+to\s+\w+|[A-Z][a-z]+\s*[-–]\s*[A-Z]', cl):
                route = cl
                break

        # Geo filter
        if not is_europe_med_arctic('', '', ctx):
            i += 1
            continue

        voyages.append({
            'departure_date': dep.isoformat(),
            'ship_name':      ship,
            'route':          route[:120],
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


def scrape_cruiseplum(
    year: int,
    months: list[int],
    output_path: Path,
    username: str = '',
    password: str = '',
    verbose: bool = False,
) -> list[dict]:
    """
    Scrape CruisePlum for Oct/Nov 2026 European luxury sailings.
    Requires valid account credentials.
    """
    if not GSTACK_BIN.exists():
        raise RuntimeError(f'gstack binary not found at {GSTACK_BIN}')

    # Load credentials
    if not (username and password):
        username, password = _load_creds()

    print(f'  [cruiseplum] Logging in as {username}...', flush=True)
    if not _login(username, password):
        print('  [cruiseplum] Login failed — aborting scrape')
        return []

    # Navigate to search
    search_url = _build_search_url(year, months)
    print(f'  [cruiseplum] Searching: {search_url[:80]}...', flush=True)
    if not _navigate(search_url, wait=5.0):
        print('  [cruiseplum] Search navigation failed')
        return []

    # Scroll to trigger lazy loading
    for _ in range(3):
        _gstack(['js', 'window.scrollTo(0, document.body.scrollHeight)'], timeout=10)
        time.sleep(1.5)

    text = _gstack(['text'], timeout=90)
    if not text:
        print('  [cruiseplum] Empty search results page')
        return []

    if verbose:
        print(f'  [cruiseplum] Page text: {len(text)} chars')

    voyages = _parse_cruiseplum_text(text, year, months)
    voyages.sort(key=lambda v: v['departure_date'])

    if verbose and voyages:
        for v in voyages:
            print(f'    {v["departure_date"]}  {v["ship_name"][:20]:<20}  '
                  f'{v["days"]:>3}n  {v["route"][:50]}  ${v["price_usd"]}')

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(voyages, indent=2))
    print(f'  [cruiseplum] {len(voyages)} sailings saved → {output_path}')
    return voyages


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Scrape CruisePlum (cruiseplum.com) — requires login',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            'Credentials (priority order):\n'
            '  1. --username / --password CLI args\n'
            '  2. Env vars CRUISEPLUM_USER + CRUISEPLUM_PASS\n'
            f'  3. File ~/.config/d2m/cruiseplum.env  (USER=... / PASS=...)\n'
        ),
    )
    parser.add_argument('--year',      type=int, default=2026)
    parser.add_argument('--months',    nargs='+', type=int, default=[10, 11])
    parser.add_argument('--output',    type=Path, default=CRUISEPLUM_JSON)
    parser.add_argument('--username',  default='')
    parser.add_argument('--password',  default='')
    parser.add_argument('--verbose',   action='store_true')
    args = parser.parse_args()

    print(f'[cruiseplum] Scraping {args.year} months={args.months}')
    results = scrape_cruiseplum(
        year=args.year, months=args.months,
        output_path=args.output,
        username=args.username, password=args.password,
        verbose=args.verbose,
    )
    print(f'[cruiseplum] Done — {len(results)} sailings → {args.output}')
