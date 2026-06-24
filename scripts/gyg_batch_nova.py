#!/usr/bin/env python3
"""
Batch GYG scraper — Loucks Silver Nova May 2027, all 19 ports.
Single browser session. Sequential with throttle. Writes to OUTPUT_DIR.
"""

import asyncio
import json
import re
import time
from datetime import datetime
from pathlib import Path

OUTPUT_DIR = Path("/home/john/Thunderbird/core/travel/data")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTFILE = OUTPUT_DIR / f"gyg_nova_batch_{datetime.now().strftime('%Y%m%d_%H%M')}.json"

# Silver Nova ports — (key, gyg_slug_or_search, query, date, commander_note)
PORTS = [
    ("koper",      "koper-l1484",          "wine tasting food tour",      "2027-05-06", ""),
    ("zadar",      "zadar-l1375",           "wine food tasting maraschino", "2027-05-07", ""),
    ("split",      "split-l268",            "wine food tour gentle",       "2027-05-08", "booked Silversea SPL-B $79 — check cheaper equiv"),
    ("dubrovnik",  "dubrovnik-l2752",       "wine food gentle easy",       "2027-05-09", "PE booked $107 — check GYG"),
    ("bari",       "bari-l383",             "food tour wine gentle",       "2027-05-10", "PE booked $136 — check GYG"),
    ("kotor",      "kotor-l3327",           "wine food boat gentle",       "2027-05-11", "open — SEG or PE"),
    ("katakolon",  "katakolon-l8869",       "wine olive oil gentle",       "2027-05-13", "open"),
    ("gythion",    "gythio-l",              "wine olive food",             "2027-05-14", "SELF-GUIDED — walk+café"),
    ("athens",     "athens-l67",            "wine food tour easy",         "2027-05-15", "PE hopon booked $60"),
    ("paros",      "paros-l1478",           "beach wine gentle",           "2027-05-16", "open — rest day"),
    ("chania",     "chania-l1807",          "wine olive oil food culture", "2027-05-17", "booked Silversea $89 — check swap"),
    ("gythion2",   "gythio-l",              "wine cave boat",              "2027-05-18", "SELF-GUIDED — walk+café"),
    ("milos",      "milos-l3047",           "easy gentle food wine",       "2027-05-19", "open — ship day candidate"),
    ("kusadasi",   "kusadasi-l2734",        "wine ephesus gentle easy",    "2027-05-20", "SELF-GUIDED — walk"),
    ("mykonos",    "mykonos-l2745",         "wine food mezedes gentle",    "2027-05-21", "SELF-GUIDED — walk"),
    ("athens2",    "athens-l67",            "cape sounio wine food",       "2027-05-22", "PE Cape Sounio booked $161"),
    ("santorini",  "santorini-l2744",       "wine winery caldera oia",     "2027-05-23", "open — cable car"),
    ("nafplio",    "nafplio-l7244",         "wine nemea gentle easy",      "2027-05-24", "booked Silversea Corinth $99 — check Nemea wine"),
    ("bodrum",     "bodrum-l1442",          "boat cruise wine gentle",     "2027-05-26", "open — gulet style"),
    ("rhodes",     "rhodes-l1422",          "wine food gentle panoramic",  "2027-05-27", "SELF-GUIDED — medieval old town walk"),
    ("patmos",     "patmos-l89366",         "monastery cave gentle",       "2027-05-28", "booked Silversea $79 — GYG $35 found prev"),
]

GYG_DEST_MAP = {
    "koper":      "koper-l1484",
    "zadar":      "zadar-l1375",
    "split":      "split-l268",
    "dubrovnik":  "dubrovnik-l2752",
    "bari":       "bari-l383",
    "kotor":      "kotor-l3327",
    "katakolon":  "katakolon-l8869",
    "athens":     "athens-l67",
    "paros":      "paros-l1478",
    "chania":     "chania-l1807",
    "milos":      "milos-l3047",
    "kusadasi":   "kusadasi-l2734",
    "mykonos":    "mykonos-l2745",
    "santorini":  "santorini-l2744",
    "nafplio":    "nafplio-l7244",
    "bodrum":     "bodrum-l1442",
    "rhodes":     "rhodes-l1422",
    "patmos":     "patmos-l89366",
    "gythio":     None,   # tiny port — use search fallback
}


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def fmt_price(s):
    if not s:
        return None
    cleaned = re.sub(r"[^\d.]", "", str(s).replace(",", ""))
    try:
        return float(cleaned)
    except ValueError:
        return None


async def scrape_port(page, key, slug, query, date, note):
    result = {
        "key": key,
        "query": query,
        "date": date,
        "commander_note": note,
        "url": None,
        "scraped_at": datetime.now().isoformat(),
        "status": "unknown",
        "tours": [],
        "notes": "",
    }

    # Build URL
    if slug and slug.endswith("-l"):  # incomplete slug — search
        slug = None

    if slug:
        url = f"https://www.getyourguide.com/{slug}/"
    else:
        sq = f"{key} {query}".strip()
        url = f"https://www.getyourguide.com/s/?q={sq.replace(' ', '+')}"

    result["url"] = url
    log(f"  GYG → {key}: {url}")

    try:
        resp = await page.goto(url, timeout=30000, wait_until="domcontentloaded")
        await asyncio.sleep(5)

        status = resp.status if resp else None
        if status and status >= 400:
            result["status"] = "bot_blocked" if status in (403, 429, 503) else "http_error"
            result["notes"] = f"HTTP {status}"
            log(f"  BLOCKED {status} at {key}")
            return result

        # Extract activity cards
        cards = await page.query_selector_all("div[class*='activity-card'], article[class*='activity'], [data-testid*='activity']")
        if not cards:
            # fallback selectors
            cards = await page.query_selector_all("a[href*='/tours/'], .c-card, [class*='ActivityCard']")

        tours = []
        for card in cards[:20]:
            try:
                title_el = await card.query_selector("h3, h4, [class*='title'], [class*='name']")
                price_el = await card.query_selector("[class*='price'], [data-testid*='price'], span[class*='Price']")
                rating_el = await card.query_selector("[class*='rating'], [class*='stars'], [aria-label*='stars']")
                link_el = await card.query_selector("a[href]") or card

                title = await title_el.text_content() if title_el else ""
                price_raw = await price_el.text_content() if price_el else ""
                rating_raw = await rating_el.text_content() if rating_el else ""
                href = await link_el.get_attribute("href") if link_el else ""

                title = title.strip()
                price = fmt_price(price_raw)
                rating = rating_raw.strip()[:10]

                if title and (price or href):
                    tours.append({
                        "title": title[:120],
                        "price_pp": price,
                        "price_raw": price_raw.strip()[:30],
                        "rating": rating,
                        "url": ("https://www.getyourguide.com" + href) if href and href.startswith("/") else href,
                    })
            except Exception:
                continue

        result["tours"] = tours
        result["status"] = "ok" if tours else "no_results"
        result["total"] = len(tours)
        log(f"  {key}: {len(tours)} tours found")

    except Exception as e:
        result["status"] = "error"
        result["notes"] = str(e)[:200]
        log(f"  ERROR at {key}: {e}")

    return result


async def main():
    from playwright.async_api import async_playwright

    all_results = []
    log(f"Starting GYG batch — {len(PORTS)} ports")
    log(f"Output: {OUTFILE}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        )
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900},
        )
        page = await ctx.new_page()

        seen_keys = set()
        for key, slug, query, date, note in PORTS:
            # Deduplicate gythion (two calls, same result)
            base_key = key.rstrip("2")
            if base_key in seen_keys and key.endswith("2"):
                log(f"  {key}: reusing {base_key} result (same port)")
                # clone result with updated date/note
                prev = next((r for r in all_results if r["key"] == base_key), None)
                if prev:
                    cloned = dict(prev)
                    cloned["key"] = key
                    cloned["date"] = date
                    cloned["commander_note"] = note
                    all_results.append(cloned)
                continue

            res = await scrape_port(page, key, slug, query, date, note)
            all_results.append(res)
            seen_keys.add(key)

            # Throttle — avoid rate limiting
            await asyncio.sleep(4)

        await browser.close()

    # Write JSON
    OUTFILE.write_text(json.dumps(all_results, indent=2))
    log(f"\nDone. Results in: {OUTFILE}")

    # Print summary
    for r in all_results:
        status_icon = "✅" if r["status"] == "ok" else ("🚫" if "block" in r["status"] else "⚠️")
        n = len(r.get("tours", []))
        top = r["tours"][0]["title"][:60] if r.get("tours") else "—"
        top_p = f"${r['tours'][0]['price_pp']}" if r.get("tours") and r["tours"][0].get("price_pp") else ""
        print(f"{status_icon} {r['key']:12} | {n:2} tours | top: {top} {top_p}")


if __name__ == "__main__":
    asyncio.run(main())
