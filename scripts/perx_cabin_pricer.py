#!/usr/bin/env python3
"""
Perx Cabin Pricer — Sailing-Specific Price Capture by Cabin Category
=====================================================================
Uses XvfbDriver (headful Firefox) to navigate Perx sailing detail pages
and extract per-cabin-category interline prices.

Perx uses JavaScript-rendered pages — server-side HTTP can't get sailing/cabin data.
This script drives a real browser to find and parse the pricing tables.

Target sailings:
  - Seven Seas Grandeur — Dec 29, 2026 — Concierge D, Concierge E, Balcony
  - Silver Nova — May 5 (10n), May 15 (7n), May 22 (7n), 2027 — Balcony/Veranda + Suite

Output:
  - data/perx_cabin_prices.json  — structured price history
  - Printed summary for AM brief ingestion

Usage:
    python3 scripts/perx_cabin_pricer.py
    python3 scripts/perx_cabin_pricer.py --watch-id grandeur-dec29-2026
    python3 scripts/perx_cabin_pricer.py --brief   # brief-format output for morning brief

Dreams2Memories Travel, LLC — Thunderbird Wing — Intel/Hale 2026-06-08
"""

import argparse
import asyncio
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

TB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TB))

from core.ai_infra.xvfb_driver import XvfbDriver  # noqa: E402

CREDS_DIR = TB / "creds"
DATA_DIR = TB / "data"
LOG_DIR = TB / "logs"
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

CABIN_PRICE_FILE = DATA_DIR / "perx_cabin_prices.json"
WATCHES_FILE = DATA_DIR / "perx_intel_watches.json"
PERX_COOKIE_FILE = CREDS_DIR / "perx_cookies.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s PERX-CABIN %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(str(LOG_DIR / "perx_cabin_pricer.log"), mode="a"),
    ],
)
log = logging.getLogger("perx_cabin")

# ── Watched sailings ──────────────────────────────────────────────────────────

SAILING_TARGETS = [
    {
        "id": "grandeur-dec29-2026",
        "label": "Seven Seas Grandeur — Dec 29, 2026",
        "perx_search_url": (
            "https://www.perx.com/cruises/search/"
            "?q=seven+seas+grandeur&date_from=2026-12-25&date_to=2026-12-31"
        ),
        "ship_slug": "seven-seas-grandeur",
        "cruise_line_slug": "regent-seven-seas-cruises",
        "target_date": "2026-12-29",
        "cabin_targets": ["Concierge D", "Concierge E", "Balcony", "Deluxe"],
        "pax": 2,
        "pax_note": "per person, double occupancy",
    },
    {
        "id": "silver-nova-may05-2027",
        "label": "Silver Nova — May 5, 2027 (10 nights)",
        "perx_search_url": (
            "https://www.perx.com/cruises/search/"
            "?q=silver+nova&date_from=2027-05-01&date_to=2027-05-12"
        ),
        "ship_slug": "silver-nova",
        "cruise_line_slug": "silversea-cruises",
        "target_date": "2027-05-05",
        "nights": 10,
        "cabin_targets": ["Balcony", "Classic Veranda", "Veranda", "Suite", "Silver Suite", "Deluxe"],
        "pax": 2,
        "pax_note": "per person, double occupancy",
    },
    {
        "id": "silver-nova-may15-2027",
        "label": "Silver Nova — May 15, 2027 (7 nights)",
        "perx_search_url": (
            "https://www.perx.com/cruises/search/"
            "?q=silver+nova&date_from=2027-05-13&date_to=2027-05-20"
        ),
        "ship_slug": "silver-nova",
        "cruise_line_slug": "silversea-cruises",
        "target_date": "2027-05-15",
        "nights": 7,
        "cabin_targets": ["Balcony", "Classic Veranda", "Veranda", "Suite", "Silver Suite", "Deluxe"],
        "pax": 2,
        "pax_note": "per person, double occupancy",
    },
    {
        "id": "silver-nova-may22-2027",
        "label": "Silver Nova — May 22, 2027 (7 nights)",
        "perx_search_url": (
            "https://www.perx.com/cruises/search/"
            "?q=silver+nova&date_from=2027-05-20&date_to=2027-05-30"
        ),
        "ship_slug": "silver-nova",
        "cruise_line_slug": "silversea-cruises",
        "target_date": "2027-05-22",
        "nights": 7,
        "cabin_targets": ["Balcony", "Classic Veranda", "Veranda", "Suite", "Silver Suite", "Deluxe"],
        "pax": 2,
        "pax_note": "per person, double occupancy",
    },
]


# ── Cookie loader ─────────────────────────────────────────────────────────────

def _load_perx_cookies() -> list:
    if not PERX_COOKIE_FILE.exists():
        return []
    raw = json.loads(PERX_COOKIE_FILE.read_text())
    return raw if isinstance(raw, list) else raw.get("cookies", [])


# ── Price history ─────────────────────────────────────────────────────────────

def _load_history() -> dict:
    if CABIN_PRICE_FILE.exists():
        try:
            return json.loads(CABIN_PRICE_FILE.read_text())
        except Exception:
            pass
    return {}


def _save_history(history: dict):
    CABIN_PRICE_FILE.write_text(json.dumps(history, indent=2))


def _record_price(history: dict, sailing_id: str, cabin: str, price: float, route: str = "") -> dict:
    key = f"{sailing_id}_{cabin.lower().replace(' ', '_')}"
    now = datetime.now(timezone.utc).isoformat()
    if key not in history:
        history[key] = {
            "sailing_id": sailing_id,
            "cabin": cabin,
            "route": route,
            "baseline_price": price,
            "prices": [],
            "last_checked": now,
        }
    history[key]["prices"].append({"ts": now, "price": price})
    history[key]["last_checked"] = now
    if len(history[key]["prices"]) > 90:
        history[key]["prices"] = history[key]["prices"][-90:]
    return history


# ── Browser scraper ───────────────────────────────────────────────────────────

async def scrape_sailing_prices(target: dict, cookies: list) -> list[dict]:
    """
    Navigate to the Perx search results for a sailing, click into the detail page,
    and extract cabin-category prices.

    Returns list of: {cabin, price_pp, route, departure_date, source_url}
    """
    results = []

    async with XvfbDriver(display_num=98, profile_dir=str(TB / "state" / "perx_cabin")) as drv:
        # Load Perx cookies
        for c in cookies:
            try:
                await drv.page.context.add_cookies([{
                    "name": c["name"],
                    "value": c["value"],
                    "domain": c.get("domain", "www.perx.com").lstrip("."),
                    "path": c.get("path", "/"),
                }])
            except Exception:
                pass

        # Navigate to search results
        log.info("Navigating to search: %s", target["perx_search_url"])
        await drv.navigate(target["perx_search_url"])
        await asyncio.sleep(5)  # let JS render

        page = drv.page
        url = page.url
        log.info("Landed at: %s", url)

        # Find sailing cards / links on the search results page
        # Try multiple selectors Perx might use
        sailing_links = []

        for selector in [
            'a[href*="/sailings/"]',
            'a[href*="/itineraries/"]',
            '.cruise-card a',
            '.sailing-result a',
            'a[href*="grandeur"]',
            'a[href*="silver-nova"]',
        ]:
            els = await page.query_selector_all(selector)
            for el in els:
                href = await el.get_attribute("href")
                if href and ("sailing" in href or "itinerary" in href):
                    full = f"https://www.perx.com{href}" if href.startswith("/") else href
                    if full not in sailing_links:
                        sailing_links.append(full)

        log.info("Found %d sailing links", len(sailing_links))

        # Filter to target ship/date
        target_date = target.get("target_date", "")
        ship_slug = target.get("ship_slug", "")
        filtered = [
            lnk for lnk in sailing_links
            if ship_slug in lnk or (target_date and target_date in lnk)
        ]
        if not filtered:
            filtered = sailing_links[:3]  # try first 3

        for link in filtered[:3]:
            log.info("Checking sailing page: %s", link)
            await drv.navigate(link)
            await asyncio.sleep(4)

            content = await page.content()
            text = await page.evaluate("document.body.innerText")

            # Look for cabin pricing table
            cabin_results = _parse_cabin_prices(text, content, target["cabin_targets"])
            for r in cabin_results:
                r["source_url"] = link
                r["sailing_id"] = target["id"]
                results.append(r)

            if cabin_results:
                log.info("Found %d cabin prices at %s", len(cabin_results), link)
                break

        # If still no results, check the current page (search results page may show pricing)
        if not results:
            text = await page.evaluate("document.body.innerText")
            content = await page.content()
            cabin_results = _parse_cabin_prices(text, content, target["cabin_targets"])
            for r in cabin_results:
                r["source_url"] = url
                r["sailing_id"] = target["id"]
                results.append(r)

    return results


def _parse_cabin_prices(text: str, html: str, cabin_targets: list[str]) -> list[dict]:
    """
    Extract cabin category prices from page text / HTML.
    Handles multiple Perx layout patterns.
    """
    results = []
    now = datetime.now(timezone.utc).isoformat()

    # Pattern 1: "Cabin Name ... $X,XXX" or "$X,XXX ... Cabin Name" within ~200 chars
    price_re = re.compile(r'\$\s*([\d,]+(?:\.\d{2})?)')

    for cabin in cabin_targets:
        # Case-insensitive search
        cabin_lower = cabin.lower()
        text_lower = text.lower()

        positions = [m.start() for m in re.finditer(re.escape(cabin_lower), text_lower)]
        for pos in positions:
            # Look for price within 300 chars of cabin mention
            window = text[max(0, pos - 50): pos + 300]
            prices = price_re.findall(window)
            for p_str in prices:
                try:
                    price = float(p_str.replace(",", ""))
                    if 200 <= price <= 50000:  # sanity range for cruise cabin pp
                        results.append({
                            "cabin": cabin,
                            "price_pp": price,
                            "ts": now,
                            "context": window[:100].strip(),
                        })
                        break
                except ValueError:
                    pass

    # Pattern 2: HTML table rows with cabin names
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL | re.IGNORECASE)
    for row in rows:
        row_text = re.sub(r'<[^>]+>', ' ', row)
        row_text = re.sub(r'\s+', ' ', row_text).strip()
        row_lower = row_text.lower()
        for cabin in cabin_targets:
            if cabin.lower() in row_lower:
                prices = price_re.findall(row_text)
                for p_str in prices:
                    try:
                        price = float(p_str.replace(",", ""))
                        if 200 <= price <= 50000:
                            # Check not already captured
                            existing = [r for r in results if r["cabin"] == cabin]
                            if not existing:
                                results.append({
                                    "cabin": cabin,
                                    "price_pp": price,
                                    "ts": now,
                                    "context": row_text[:100],
                                })
                    except ValueError:
                        pass

    return results


# ── Main runner ───────────────────────────────────────────────────────────────

async def run_cabin_price_watch(watch_ids: list[str] | None = None, brief_mode: bool = False):
    cookies = _load_perx_cookies()
    if not cookies:
        log.error("No Perx cookies found — run perx_session_keepalive.py first")
        return {}

    history = _load_history()
    summary = {}

    targets = SAILING_TARGETS
    if watch_ids:
        targets = [t for t in SAILING_TARGETS if t["id"] in watch_ids]

    for target in targets:
        log.info("Checking: %s", target["label"])
        try:
            prices = await scrape_sailing_prices(target, cookies)
        except Exception as exc:
            log.error("Error scraping %s: %s", target["id"], exc)
            prices = []

        if prices:
            for p in prices:
                history = _record_price(
                    history, target["id"], p["cabin"], p["price_pp"],
                    route=target.get("label", "")
                )
            summary[target["id"]] = {
                "label": target["label"],
                "prices": prices,
                "status": "OK",
            }
            log.info("  %s: %d cabin prices captured", target["id"], len(prices))
        else:
            # Return last known prices from history
            last_known = {}
            for key, rec in history.items():
                if rec.get("sailing_id") == target["id"] and rec.get("prices"):
                    last_known[rec["cabin"]] = rec["prices"][-1]["price"]
            summary[target["id"]] = {
                "label": target["label"],
                "prices": [],
                "last_known": last_known,
                "status": "NO_DATA" if not last_known else "CACHED",
            }
            log.warning("  %s: no live data — %s", target["id"], "returning cached" if last_known else "no history")

    _save_history(history)

    if brief_mode:
        _print_brief(summary)

    return summary


def _print_brief(summary: dict):
    """Print AM brief format for ingestion."""
    print("\n=== PERX CABIN PRICES (Interline — TA Rate Signal) ===")
    print(f"As of {datetime.now().strftime('%Y-%m-%d %H:%M MT')}\n")

    for sid, data in summary.items():
        print(f"  {data['label']}")
        prices = data.get("prices") or []
        last_known = data.get("last_known", {})

        # Find pax_note for this sailing
        target_meta = next((t for t in SAILING_TARGETS if t["id"] == sid), {})
        pax_note = target_meta.get("pax_note", "per person, double occupancy")
        nights = target_meta.get("nights")
        nights_str = f" · {nights}n" if nights else ""

        if prices:
            for p in prices:
                print(f"    {p['cabin']:25s}  ${p['price_pp']:,.0f}  [{pax_note}{nights_str}]  [LIVE]")
        elif last_known:
            for cabin, price in last_known.items():
                print(f"    {cabin:25s}  ${price:,.0f}  [{pax_note}{nights_str}]  [cached]")
        else:
            print("    No data available")

        # Signal check vs baseline
        for key, rec in _load_history().items():
            if rec.get("sailing_id") == sid and len(rec.get("prices", [])) >= 2:
                baseline = rec["baseline_price"]
                current = rec["prices"][-1]["price"]
                pct = ((current - baseline) / baseline) * 100
                if pct <= -15:
                    signal = "⚠️ WATCH" if pct > -25 else ("🚨 SIGNAL" if pct > -35 else "🔴 URGENT")
                    print(f"    {signal}: {rec['cabin']} down {abs(pct):.1f}% — TA rate may be imminent")
        print()


def _print_status(summary: dict):
    """Simple status output."""
    for sid, data in summary.items():
        status = data["status"]
        n = len(data.get("prices", []))
        cached = len(data.get("last_known", {}))
        print(f"  {data['label']}: {status} ({n} live, {cached} cached)")


def main():
    parser = argparse.ArgumentParser(description="Perx Cabin Price Monitor")
    parser.add_argument("--watch-id", help="Specific sailing ID to check")
    parser.add_argument("--brief", action="store_true", help="Output AM brief format")
    parser.add_argument("--list", action="store_true", help="List watched sailings")
    args = parser.parse_args()

    if args.list:
        for t in SAILING_TARGETS:
            print(f"  {t['id']:35s}  {t['label']}")
            print(f"    Cabins: {', '.join(t['cabin_targets'])}")
        return

    watch_ids = [args.watch_id] if args.watch_id else None
    summary = asyncio.run(run_cabin_price_watch(watch_ids=watch_ids, brief_mode=args.brief))
    if not args.brief:
        _print_status(summary)


if __name__ == "__main__":
    main()
