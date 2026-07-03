#!/usr/bin/env python3
"""
Consumer Price Fetcher — writes price_ind/price_ts/price_src into output/cruises.db.

Status per partner line:
  1. Crystal Cruises       — LIVE. Sitemap → _next/data slug → USD price. No auth.
  2. Regent Seven Seas     — PENDING. 403 on plain HTTP. Playwright + RSSC booking engine needed.
  3. Silversea Cruises     — PENDING. JS-rendered. Playwright needed.
  4. Atlas Ocean Voyages   — PENDING. Playwright needed to capture API endpoint.
  5. Explora Journeys      — PENDING. Playwright needed to capture API endpoint.

Usage:
  python3 scripts/fetch_consumer_prices.py --line "Crystal Cruises" --limit 50 --dry-run
  python3 scripts/fetch_consumer_prices.py --line "Crystal Cruises"
  python3 scripts/fetch_consumer_prices.py --all --dry-run

Writes: UPDATE cruises SET price_ind=?, price_ts=?, price_src=? WHERE id=?
"""
import argparse, json, sqlite3, time, re, urllib.request, urllib.parse
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path("/home/john/Thunderbird/output/cruises.db")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.crystalcruises.com/",
}

# Crystal Cruises — ship code → canonical ship name mapping
CRYSTAL_SHIP_CODES = {
    'cse': 'Crystal Serenity',
    'csy': 'Crystal Symphony',
    'cgr': 'Crystal Grandeur',
}

# Next.js build ID — update when Crystal redeploys (check /sitemap.xml redirect)
CRYSTAL_BUILD_ID = '3.11.3'


# ── Crystal Cruises ──────────────────────────────────────────────────────────

def _crystal_get_all_slugs() -> list:
    """Fetch all Crystal cruise slugs from their sitemap."""
    url = 'https://www.crystalcruises.com/sitemap-0.xml'
    req = urllib.request.Request(url, headers=HEADERS)
    r = urllib.request.urlopen(req, timeout=15)
    content = r.read().decode('utf-8', errors='ignore')
    cruise_urls = re.findall(
        r'<loc>(https://www\.crystalcruises\.com/cruises/([^<]+))</loc>', content
    )
    return [slug for _, slug in cruise_urls]


def _crystal_fetch_price(slug: str) -> dict | None:
    """
    Fetch voyage detail for one Crystal slug. Returns dict with price_ind, departure, ship, etc.
    Returns None on failure.
    """
    url = (f'https://www.crystalcruises.com/_next/data/{CRYSTAL_BUILD_ID}'
           f'/cruises/{slug}.json?slug={slug}')
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        r = urllib.request.urlopen(req, timeout=15)
        data = json.loads(r.read())
    except Exception as e:
        print(f'  FETCH ERR {slug}: {e}')
        return None

    result = data.get('pageProps', {}).get('result', {})
    if not result:
        return None

    # Extract voyage metadata
    embark_date = result.get('embarkDate', '')
    if embark_date:
        embark_date = str(embark_date)[:10]  # ISO date only
    ship_name = result.get('ship', '')
    duration = result.get('duration', 0)
    embark_city = result.get('embarkCity', '')
    debark_city = result.get('debarkCity', '')

    # Find minimum USD price across all cabin categories
    prices = result.get('price', [])
    usd_prices = [
        p['priceSum'] for p in prices
        if p.get('currency') == 'USD' and p.get('priceSum') and p['priceSum'] > 0
    ]

    if not usd_prices:
        return None

    min_price = min(usd_prices)
    return {
        'slug': slug,
        'ship': ship_name,
        'departure': embark_date,
        'nights': duration,
        'from_port': embark_city,
        'route': f'{embark_city} to {debark_city}',
        'price_ind': float(min_price),
        'price_src': 'crystalcruises.com',
    }


def fetch_crystal(limit: int = 999, dry_run: bool = False) -> int:
    """Fetch all Crystal prices and update DB. Returns count updated."""
    print('[crystal] Fetching sitemap...', flush=True)
    slugs = _crystal_get_all_slugs()
    print(f'[crystal] Found {len(slugs)} cruise slugs in sitemap', flush=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    updated = 0
    skipped = 0
    for i, slug in enumerate(slugs[:limit], 1):
        result = _crystal_fetch_price(slug)
        if not result:
            skipped += 1
            time.sleep(0.5)
            continue

        ts = datetime.now(timezone.utc).isoformat()
        price = result['price_ind']
        departure = result['departure']
        ship = result['ship']

        # Match to DB row by line + ship + departure date
        ship_word = ship.split()[-1] if ship.strip() else ''
        if not ship_word or not departure:
            skipped += 1
            continue
        row = conn.execute(
            "SELECT id FROM cruises WHERE line='Crystal Cruises' "
            "AND ship LIKE ? AND departure LIKE ? LIMIT 1",
            (f'%{ship_word}%', f'{departure}%')
        ).fetchone()

        if row:
            print(f'[{i}/{len(slugs)}] {ship} {departure} → ${price:,.0f} pp  (id={row["id"]})', flush=True)
            if not dry_run:
                conn.execute(
                    "UPDATE cruises SET price_ind=?, price_ts=?, price_src=? WHERE id=?",
                    (price, ts, result['price_src'], row['id'])
                )
            updated += 1
        else:
            print(f'[{i}/{len(slugs)}] {ship} {departure} → ${price:,.0f} pp  (no DB match)', flush=True)
            skipped += 1

        time.sleep(1)  # polite delay — 1 req/s

    if not dry_run:
        conn.commit()
    conn.close()

    print(f'[crystal] Done — {updated} updated, {skipped} skipped', flush=True)
    return updated


# ── Dispatch registry ────────────────────────────────────────────────────────

FETCHERS = {
    'Crystal Cruises': fetch_crystal,
    # 'Regent Seven Seas Cruises': fetch_rssc,   # PENDING — Playwright needed
    # 'Silversea Cruises':         fetch_silversea,  # PENDING
    # 'Atlas Ocean Voyages':       fetch_atlas,      # PENDING
    # 'Explora Journeys':          fetch_explora,    # PENDING
}


def run(line_filter: str = None, limit: int = 999, dry_run: bool = False):
    if not DB_PATH.exists():
        print(f'ERROR: DB not found at {DB_PATH}')
        return

    lines_to_run = [line_filter] if line_filter else list(FETCHERS.keys())

    for line in lines_to_run:
        fetcher = FETCHERS.get(line)
        if not fetcher:
            print(f'[{line}] No fetcher available yet — Playwright session needed to capture API endpoint.')
            continue
        fetcher(limit=limit, dry_run=dry_run)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Fetch consumer prices for cruise DB partner lines')
    ap.add_argument('--line', default=None, help='Filter to one cruise line')
    ap.add_argument('--limit', type=int, default=999)
    ap.add_argument('--all', action='store_true', dest='all_lines')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    run(
        line_filter=args.line,
        limit=args.limit if not args.all_lines else 99999,
        dry_run=args.dry_run,
    )
