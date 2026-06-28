#!/usr/bin/env python3
"""
VTG Ticker Scraper — fetches live FastDeal tables from vacationstogo.com
using Playwright (Chromium, JS-rendered) and writes:
  intel/vtg_structured_YYYYMMDD.txt   — all luxury lines (Regent/Silversea/Atlas/Explora/Ponant/PGC)
  intel/regent_vtg_YYYYMMDD.json
  intel/silversea_vtg_YYYYMMDD.json
  intel/atlas_vtg_YYYYMMDD.json

Cookies: reads creds/vtg_cookies.json (CFID/CFTOKEN/VTG/VTG_COOKIE).
Expiry detection: if deal count < 10 after render, cookies are expired → Telegram alert.

Run: python3 scripts/fetch_vtg_ticker.py [--dry-run] [--lines regent silversea atlas]
Timer: ExecStartPre in cruise-db-refresh.service (monthly, 1st 03:00 MT)
"""
import argparse, json, re, sys, time, urllib.request
from datetime import datetime
from pathlib import Path

ROOT   = Path("/home/john/Thunderbird")
INTEL  = ROOT / "intel"
CREDS  = ROOT / "creds" / "vtg_cookies.json"
TODAY  = datetime.now().strftime("%Y%m%d")
LOG    = ROOT / "logs" / "fetch_vtg_ticker.log"

# VTG line IDs (discovered 2026-06-28)
LINE_CONFIGS = {
    "Regent Seven Seas Cruises": {
        "stem":      "regent",
        "line_id":   18,
        "slug":      "regent_cruises",
        "vtg_key":   "Regent",
        "source_key": "regent_vtg",
    },
    "Silversea Cruises": {
        "stem":      "silversea",
        "line_id":   20,
        "slug":      "silversea_cruises",
        "vtg_key":   "Silversea",
        "source_key": "silversea_vtg",
    },
    "Atlas Ocean Voyages": {
        "stem":      "atlas",
        "line_id":   35,
        "slug":      "atlas_ocean_voyages",
        "vtg_key":   "Atlas Ocean Voyages",
        "source_key": "atlas_vtg",
    },
    "Explora Journeys": {
        "stem":      "explora",
        "line_id":   38,
        "slug":      "explora_journeys",
        "vtg_key":   "Explora Journeys",
        "source_key": "vtg",
    },
    "Oceania Cruises": {
        "stem":      "oceania",
        "line_id":   47,
        "slug":      "oceania_cruises",
        "vtg_key":   "Oceania",
        "source_key": "oceania_vtg",
    },
    "Crystal Cruises": {
        "stem":      "crystal",
        "line_id":   13,
        "slug":      "crystal_cruises",
        "vtg_key":   "Crystal",
        "source_key": "crystal_vtg",
    },
    "Paul Gauguin Cruises": {
        "stem":      "paul_gauguin",
        "line_id":   None,
        "slug":      "paul_gauguin_cruises",
        "vtg_key":   "Paul Gauguin",
        "source_key": "vtg",
    },
    "PONANT": {
        "stem":      "ponant",
        "line_id":   None,
        "slug":      "ponant_yacht_cruises",
        "vtg_key":   "Ponant",
        "source_key": "vtg",
    },
}

TICKER_URL = (
    "https://www.vacationstogo.com/ticker.cfm"
    "?l={lid}&r=0&mPct=40&jpw=50&source=cruisemm&csp=L7gL7g&nr=cus_L7g&mmz=1"
)

# FastDeal row pattern (same as parse_vtg in build_master_cruise_db.py)
LINE_NAMES = ["Regent", "Silversea", "Explora Journeys", "Atlas Ocean Voyages",
              "Atlas", "Paul Gauguin", "Ponant"]
LN_PAT = '|'.join(re.escape(l) for l in LINE_NAMES)
ROW_RE = re.compile(
    r'^#(\d+)\s+(\d+)\s+(.+?)\s+(' + LN_PAT + r')\s*/\s*(.+?)\s+'
    r'(?:5\.5|6)\s+\$([0-9,]+)\s+\$([0-9,]+)\s+(\d+)%\s+(.+)$'
)

REGION_MAP = [
    ("Mediterranean",   ["mediterranean","athens","barcelona","lisbon","rome","valletta",
                         "venice","istanbul","dubrovnik","palma","naples","marseille",
                         "sicily","malaga","santorini","mykonos","monte carlo","cannes"]),
    ("Caribbean",       ["caribbean","miami","san juan","barbados","st thomas","aruba",
                         "curacao","grenada","antigua","martinique","nassau","havana"]),
    ("Northern Europe", ["norway","bergen","fjord","helsinki","stockholm","copenhagen",
                         "amsterdam","hamburg","tallinn","southampton","edinburgh"]),
    ("Alaska",          ["alaska","juneau","ketchikan","sitka","glacier bay","skagway","seward"]),
    ("South America",   ["buenos aires","rio","montevideo","valparaiso","ushuaia",
                         "cartagena","callao","amazon","brazil","argentina","chile"]),
    ("Asia Pacific",    ["tokyo","osaka","hong kong","singapore","sydney","auckland",
                         "bali","vietnam","japan","south korea","shanghai","phuket"]),
    ("Middle East",     ["dubai","abu dhabi","muscat","doha","oman","uae","egypt","jordan"]),
    ("Indian Ocean",    ["maldives","mauritius","seychelles","zanzibar","sri lanka","india","colombo"]),
    ("World",           []),
]

def infer_region(route: str) -> str:
    r = route.lower()
    for region, kws in REGION_MAP:
        if kws and any(k in r for k in kws):
            return region
    return "World"


def load_cookies() -> dict:
    if not CREDS.exists():
        return {}
    return json.loads(CREDS.read_text())


def _send_telegram_alert(msg: str):
    """Page Commander via Telegram D2MC2C bot."""
    token_path = ROOT / "creds" / "telegram_bot_token.txt"
    if not token_path.exists():
        print(f"[TELEGRAM] {msg}")
        return
    token = token_path.read_text().strip()
    cmd_id = 7554895206
    payload = json.dumps({"chat_id": cmd_id, "text": msg, "parse_mode": "HTML"}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=8)
    except Exception as e:
        print(f"[TELEGRAM FAIL] {e}")


def discover_line_id(page, line_name: str) -> int | None:
    """Navigate to VTG cruise line page and extract ticker line ID from l= params."""
    cfg = LINE_CONFIGS.get(line_name, {})
    slug = cfg.get("slug")
    if not slug:
        return None
    try:
        page.goto(f"https://www.vacationstogo.com/cruise_lines/{slug}.cfm",
                  wait_until="domcontentloaded", timeout=15000)
        content = page.content()
        m = re.search(r'[?&]l=(\d+)', content)
        return int(m.group(1)) if m else None
    except Exception as e:
        print(f"  [warn] line ID discovery failed for {line_name}: {e}")
        return None


def scrape_line_ticker(page, line_id: int, line_name: str, dry_run: bool = False) -> list[str]:
    """
    Navigate to ticker page, wait for JS render, extract FastDeal rows as text lines.
    Returns list of raw text lines matching the vtg_structured format.
    """
    url = TICKER_URL.format(lid=line_id)
    print(f"  Fetching ticker l={line_id} for {line_name}…")
    if dry_run:
        print(f"  [DRY RUN] Would fetch: {url}")
        return []

    try:
        page.goto(url, wait_until="networkidle", timeout=25000)
    except Exception as e:
        print(f"  [warn] page load timeout for {line_name}: {e}")

    # Wait for deal rows to appear (look for FastDeal # text)
    try:
        page.wait_for_selector("text=FastDeal", timeout=8000)
    except Exception:
        pass  # may not find it — proceed with what we have

    content = page.content()

    # Extract deal rows from rendered HTML
    # VTG renders a table where each row has: FastDeal#, nights, date, route, line/ship, rating, prices, %
    # The text extraction approach: get all text and regex-match the row format
    text = page.evaluate("() => document.body.innerText")

    raw_lines = []
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
        # Normalize tabs/multiple spaces
        line = re.sub(r'\s+', ' ', line)
        # Check if it matches row format
        if ROW_RE.match(line):
            raw_lines.append(line)

    print(f"  → {len(raw_lines)} deal rows extracted")
    return raw_lines


def parse_row(raw: str, source_key: str, scraped_date: str) -> dict | None:
    m = ROW_RE.match(raw)
    if not m:
        return None
    fdeal, nights, before, ln, ship, orig, disc, pct, status = m.groups()

    LINE_CANONICAL = {
        "Regent":              "Regent Seven Seas Cruises",
        "Silversea":           "Silversea Cruises",
        "Atlas Ocean Voyages": "Atlas Ocean Voyages",
        "Atlas":               "Atlas Ocean Voyages",
        "Explora Journeys":    "Explora Journeys",
        "Paul Gauguin":        "Paul Gauguin Cruises",
        "Ponant":              "PONANT",
    }
    canonical = LINE_CANONICAL.get(ln, ln)

    dm = re.match(r'^(\w{3}\s+\d+(?:,\s*\d{4})?)\s*(.*)', before.strip())
    date_str = dm.group(1) if dm else ''
    route    = dm.group(2).strip() if dm else before.strip()
    yr_m = re.search(r'(\d{4})', date_str)
    year = int(yr_m.group(1)) if yr_m else 2026
    try:
        clean = re.sub(r',\s*\d{4}', '', date_str).strip()
        d = datetime.strptime(f"{clean} {year}", "%b %d %Y")
        iso_date = d.strftime("%Y-%m-%d")
    except Exception:
        iso_date = ''

    return {
        "line":       canonical,
        "ship":       ship.strip(),
        "departure":  iso_date,
        "date_str":   date_str,
        "nights":     int(nights),
        "from_port":  route[:40],
        "to_port":    "",
        "route":      route,
        "region":     infer_region(route),
        "price_disc": int(disc.replace(",", "")),
        "price_orig": int(orig.replace(",", "")),
        "discount":   int(pct),
        "suite":      "Suite" in status,
        "vtg_fd":     fdeal,
        "sources":    [source_key],
        "scraped":    scraped_date,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--lines", nargs="+",
                        choices=["regent", "silversea", "atlas", "explora", "ponant", "paul_gauguin"],
                        default=["regent", "silversea", "atlas"])
    args = parser.parse_args()

    INTEL.mkdir(parents=True, exist_ok=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)

    cookies = load_cookies()
    if not cookies:
        msg = ("⚠️ VTG fetch skipped — no cookies found at creds/vtg_cookies.json\n"
               "Action: log into vacationstogo.com in Firefox → export CFID/CFTOKEN/VTG cookies → save to creds/vtg_cookies.json")
        print(msg)
        _send_telegram_alert(msg)
        sys.exit(1)

    # Map stems to canonical line names
    stem_to_line = {cfg["stem"]: name for name, cfg in LINE_CONFIGS.items()}
    target_lines = [stem_to_line[s] for s in args.lines if s in stem_to_line]

    from playwright.sync_api import sync_playwright

    all_raw_lines: list[str] = []
    per_line_json: dict[str, list[dict]] = {}
    scraped_date = datetime.now().strftime("%Y-%m-%d")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36"
        )
        # Inject VTG cookies
        context.add_cookies([
            {"name": k, "value": v, "domain": ".vacationstogo.com", "path": "/"}
            for k, v in cookies.items()
        ])
        page = context.new_page()

        for line_name in target_lines:
            cfg = LINE_CONFIGS[line_name]
            stem = cfg["stem"]
            line_id = cfg["line_id"]

            # Discover line ID if unknown
            if line_id is None:
                print(f"Discovering line ID for {line_name}…")
                line_id = discover_line_id(page, line_name)
                if line_id:
                    print(f"  Found: l={line_id}")
                    # Update registry for future runs
                    cfg["line_id"] = line_id
                else:
                    print(f"  [warn] Could not discover line ID for {line_name} — skipping")
                    continue

            raw_lines = scrape_line_ticker(page, line_id, line_name, dry_run=args.dry_run)

            if len(raw_lines) < 5 and not args.dry_run:
                msg = (f"⚠️ VTG ticker returned only {len(raw_lines)} rows for {line_name} (l={line_id})\n"
                       f"VTG session cookies may be expired.\n"
                       f"Action: log into vacationstogo.com → export fresh cookies → creds/vtg_cookies.json\n"
                       f"URL: https://www.vacationstogo.com/ticker.cfm?l={line_id}&r=0&mPct=40&jpw=50&source=cruisemm&csp=L7gL7g&nr=cus_L7g&mmz=1")
                print(msg)
                _send_telegram_alert(msg)
                continue

            all_raw_lines.extend(raw_lines)
            records = [parse_row(r, cfg["source_key"], scraped_date) for r in raw_lines]
            records = [r for r in records if r is not None]
            per_line_json[stem] = records

        browser.close()

    if args.dry_run:
        print("Dry run complete — no files written.")
        return

    if not all_raw_lines and not per_line_json:
        msg = "⚠️ VTG fetch: zero rows scraped across all lines. Check cookies + ticker URLs."
        print(msg)
        _send_telegram_alert(msg)
        sys.exit(1)

    # Write combined structured txt (all lines)
    txt_path = INTEL / f"vtg_structured_{TODAY}.txt"
    with open(txt_path, "w") as f:
        f.write(f"# VACATIONSTOGO CRUISE INTEL — {scraped_date}\n")
        f.write(f"# Playwright scrape · {', '.join(args.lines)}\n")
        f.write(f"# Lines: {' · '.join(LINE_CONFIGS[n]['vtg_key'] for n in target_lines if n in LINE_CONFIGS)}\n\n")
        by_vtg_key: dict[str, list[str]] = {}
        for raw in all_raw_lines:
            m = ROW_RE.match(raw)
            if m:
                ln = m.group(4)
                by_vtg_key.setdefault(ln, []).append(raw)
        for vtg_key, rows in by_vtg_key.items():
            f.write(f"\n{'='*80}\n# {vtg_key} — {len(rows)} SAILINGS\n{'='*80}\n")
            for row in rows:
                f.write(row + "\n")
    print(f"Written: {txt_path.name} ({sum(len(v) for v in by_vtg_key.values())} rows)")

    # Write per-line JSON files
    for stem, records in per_line_json.items():
        out = INTEL / f"{stem}_vtg_{TODAY}.json"
        out.write_text(json.dumps(records, indent=2))
        print(f"Written: {out.name} ({len(records)} records)")

    total = sum(len(v) for v in per_line_json.values())
    print(f"Done. {total} total records across {len(per_line_json)} lines.")
    with open(LOG, "a") as f:
        f.write(f"{datetime.now().isoformat()} | {total} records | lines: {list(per_line_json.keys())}\n")


if __name__ == "__main__":
    main()
