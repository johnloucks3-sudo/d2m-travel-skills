#!/usr/bin/env python3
"""
Perx.com Cruise Scraper — fetches luxury line sailings from perx.com search pages
using authenticated session cookies and writes:
  intel/regent_perx_YYYYMMDD.json
  intel/silversea_perx_YYYYMMDD.json
  intel/atlas_perx_YYYYMMDD.json

Cookies: reads creds/perx_cookies.json (list format — copy from browser devtools).
Session alert: if cookies are expired (<5 cards returned), Telegram alert is sent.

Run: python3 scripts/fetch_perx_sailings.py [--dry-run] [--lines regent silversea atlas]
Timer: ExecStartPre in cruise-db-refresh.service (monthly, 1st 03:00 MT)

Rate note: Perx uses Imperva — throttle to 1 req/s, requests are session-authenticated
so rate-based bans are unlikely, but don't hammer.
"""
import argparse, json, re, sys, time, urllib.request
from datetime import datetime
from pathlib import Path

ROOT   = Path("/home/john/Thunderbird")
INTEL  = ROOT / "intel"
CREDS  = ROOT / "creds" / "perx_cookies.json"
TODAY  = datetime.now().strftime("%Y%m%d")
LOG    = ROOT / "logs" / "fetch_perx_sailings.log"

LINE_CONFIGS = {
    "regent": {
        "line_id":    1595,
        "canonical":  "Regent Seven Seas Cruises",
        "source_key": "regent_perx",
    },
    "silversea": {
        "line_id":    1589,
        "canonical":  "Silversea Cruises",
        "source_key": "silversea_perx",
    },
    "atlas": {
        "line_id":    3921,
        "canonical":  "Atlas Ocean Voyages",
        "source_key": "atlas_perx",
    },
}

SEARCH_URL = (
    "https://www.perx.com/cruises/search/"
    "?cruise_line_id={line_id}&size=200&order_by=cabin_b%3A%3Adeparture_date"
)

REGION_MAP = [
    ("Mediterranean",   ["mediterranean","piraeus","athens","barcelona","lisbon","rome","civitavecchia",
                         "valletta","venice","istanbul","dubrovnik","marseille","palma","naples",
                         "malaga","santorini","mykonos","monte carlo","cannes","genoa","spain",
                         "italy","greece","portugal","france","sicily","turkey","croatia"]),
    ("Caribbean",       ["caribbean","miami","san juan","barbados","st thomas","st maarten","aruba",
                         "curacao","grenada","antigua","martinique","nassau","havana","montego bay"]),
    ("Baltic / Northern Europe", ["norway","bergen","fjord","helsinki","stockholm","copenhagen","amsterdam",
                         "hamburg","tallinn","riga","gdansk","southampton","dover","edinburgh",
                         "europe","baltic","scandinavia","british isles","ireland","scotland"]),
    ("Alaska",          ["alaska","juneau","ketchikan","sitka","glacier bay","skagway","seward"]),
    ("South America",   ["buenos aires","rio","montevideo","valparaiso","ushuaia","cartagena",
                         "callao","amazon","brazil","argentina","chile","peru","south america"]),
    ("Asia & Pacific",  ["tokyo","osaka","hong kong","singapore","sydney","auckland","bali","phuket",
                         "vietnam","japan","south korea","shanghai","china","asia","pacific"]),
    ("Indian Ocean / Africa", ["dubai","abu dhabi","muscat","doha","oman","uae","egypt","jordan","israel",
                         "maldives","mauritius","seychelles","zanzibar","sri lanka","india","colombo"]),
    ("Transatlantic",   ["transatlantic","trans-atlantic","crossing"]),
]

def infer_region(text: str) -> str:
    t = text.lower()
    for region, kws in REGION_MAP:
        if kws and any(k in t for k in kws):
            return region
    return "Other / World"


def load_cookies() -> str:
    if not CREDS.exists():
        return ""
    raw = json.loads(CREDS.read_text())
    if isinstance(raw, list):
        return '; '.join(f"{c['name']}={c['value']}" for c in raw)
    return '; '.join(f"{k}={v}" for k, v in raw.items())


def _send_telegram_alert(msg: str):
    token_path = ROOT / "creds" / "telegram_bot_token.txt"
    if not token_path.exists():
        print(f"[TELEGRAM] {msg}")
        return
    token = token_path.read_text().strip()
    payload = json.dumps({"chat_id": 7554895206, "text": msg, "parse_mode": "HTML"}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=payload, headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=8)
    except Exception as e:
        print(f"[TELEGRAM FAIL] {e}")


def _clean_price(s: str) -> int:
    m = re.search(r'[\d,]+(?:\.\d+)?', s.strip())
    if not m:
        return 0
    return int(float(m.group().replace(',', '')))


def _ship_from_href(href: str) -> str:
    """Extract ship name from URL slug: /cruises/line/seven-seas-voyager/... → 'Seven Seas Voyager'"""
    m = re.search(r'/cruises/[^/]+/([^/]+)/itineraries/', href)
    if not m:
        return ""
    slug = m.group(1)
    return slug.replace('-', ' ').title()


def parse_byline(byline_text: str, itin_href: str = "") -> tuple[str, str, str]:
    """Extract (from_port, to_port, ship) from byline.
    Patterns:
      'Lisbon, Portugal to Southampton, England - Seven Seas Voyager'
      'Round-trip - Piraeus (Athens), Greece - Seven Seas Splendor'
    Prefers ship extracted from itin_href URL when available.
    """
    text = re.sub(r'\s+', ' ', byline_text).strip()

    # Ship: prefer URL slug (more reliable)
    ship = _ship_from_href(itin_href) if itin_href else ""

    if not ship:
        # Fall back to last segment after ' - '
        parts = text.rsplit(' - ', 1)
        ship = parts[1].strip() if len(parts) > 1 else ""
        route_text = parts[0].strip()
    else:
        # Remove ship suffix from byline to get route portion
        ship_suffix = re.escape(' - ' + text.rsplit(' - ', 1)[-1]) if ' - ' in text else ''
        route_text = re.sub(ship_suffix + r'\s*$', '', text).strip() if ship_suffix else text

    if " to " in route_text.lower():
        idx = route_text.lower().index(" to ")
        from_port = route_text[:idx].strip()
        to_port = route_text[idx+4:].strip()
    elif "round-trip" in route_text.lower():
        port = re.sub(r'^round.?trip\s*-?\s*', '', route_text, flags=re.I).strip()
        from_port = port
        to_port = port
    else:
        from_port = route_text
        to_port = ""

    return from_port, to_port, ship


def parse_departure(itin_href: str) -> str:
    """Extract ISO date from href like /cruises/.../sailings/2026-07-20"""
    m = re.search(r'/sailings/(\d{4}-\d{2}-\d{2})', itin_href)
    return m.group(1) if m else ""


def parse_itinerary_id(div_id: str) -> str:
    """Extract numeric ID from '200487_details'"""
    m = re.match(r'^(\d+)_details$', div_id or "")
    return m.group(1) if m else ""


def scrape_line(stem: str, cfg: dict, cookie_str: str, dry_run: bool = False) -> list[dict]:
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        print("ERROR: beautifulsoup4 not installed. Run: pip install beautifulsoup4")
        sys.exit(1)

    line_id = cfg["line_id"]
    canonical = cfg["canonical"]
    source_key = cfg["source_key"]
    url = SEARCH_URL.format(line_id=line_id)
    scraped_date = datetime.now().strftime("%Y-%m-%d")

    print(f"  Fetching {canonical} (line_id={line_id})…")
    if dry_run:
        print(f"  [DRY RUN] Would fetch: {url}")
        return []

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
        "Cookie": cookie_str,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        msg = f"⚠️ Perx fetch FAILED for {canonical}: {e}"
        print(msg)
        _send_telegram_alert(msg)
        return []

    soup = BeautifulSoup(html, "html.parser")
    # Only take cards with an id attribute (skip price-only sub-rows)
    cards = [
        c for c in soup.find_all("div", class_=lambda cl: cl and "cruise-search-result" in cl)
        if c.get("id")
    ]
    print(f"  → {len(cards)} itinerary cards")

    if len(cards) < 3 and not dry_run:
        msg = (f"⚠️ Perx returned only {len(cards)} cards for {canonical}\n"
               f"Session may be expired. Refresh: copy cookies from perx.com → creds/perx_cookies.json\n"
               f"URL: {url}")
        print(msg)
        _send_telegram_alert(msg)

    records = []
    for card in cards:
        try:
            itin_id   = parse_itinerary_id(card.get("id", ""))
            nights    = int(card.get("data-nights", 0))

            itin_link = card.find("a", class_="itin-link")
            href      = itin_link["href"] if itin_link else ""
            departure = parse_departure(href)
            detail_url = f"https://www.perx.com{href}" if href else ""

            h3        = card.find("h3")
            route_name = h3.get_text(strip=True) if h3 else ""

            byline_el = card.find("p", class_="itin-byline")
            byline_txt = byline_el.get_text(separator=" ", strip=True) if byline_el else ""
            from_port, to_port, ship = parse_byline(byline_txt, href)

            list_el   = card.find("span", class_="list-price")
            your_el   = card.find("span", class_="your-price")
            price_orig = _clean_price(list_el.get_text()) if list_el else 0
            price_disc = _clean_price(your_el.get_text()) if your_el else 0
            # If only one price available, treat as your-price
            if price_disc == 0 and price_orig > 0:
                price_disc = price_orig
                price_orig = 0

            # Region: try h3 route name first, then ports
            region = infer_region(route_name + " " + from_port + " " + to_port)

            records.append({
                "line":         canonical,
                "ship":         ship,
                "departure":    departure,
                "nights":       nights,
                "route":        route_name,
                "from_port":    from_port[:60],
                "to_port":      to_port[:60],
                "region":       region,
                "price_orig":   price_orig,
                "price_disc":   price_disc,
                "itinerary_id": itin_id,
                "url":          detail_url,
                "sources":      [source_key],
                "scraped":      scraped_date,
            })
        except Exception as e:
            print(f"  [warn] parse error on card {card.get('id','?')}: {e}")
            continue

    time.sleep(1)  # polite throttle between lines
    return records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--lines", nargs="+",
                        choices=list(LINE_CONFIGS.keys()),
                        default=list(LINE_CONFIGS.keys()))
    args = parser.parse_args()

    INTEL.mkdir(parents=True, exist_ok=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)

    cookie_str = load_cookies()
    if not cookie_str:
        msg = ("⚠️ Perx fetch skipped — no cookies at creds/perx_cookies.json\n"
               "Export cookies from perx.com (logged in) → save to creds/perx_cookies.json")
        print(msg)
        _send_telegram_alert(msg)
        sys.exit(1)

    total = 0
    for stem in args.lines:
        cfg = LINE_CONFIGS[stem]
        records = scrape_line(stem, cfg, cookie_str, dry_run=args.dry_run)

        if args.dry_run:
            continue

        out = INTEL / f"{stem}_perx_{TODAY}.json"
        out.write_text(json.dumps(records, indent=2))
        print(f"  Written: {out.name} ({len(records)} records)")
        total += len(records)

    if not args.dry_run:
        print(f"\nDone. {total} total records across {len(args.lines)} lines.")
        with open(LOG, "a") as f:
            f.write(f"{datetime.now().isoformat()} | {total} records | lines: {args.lines}\n")


if __name__ == "__main__":
    main()
