"""
Tour price scraper — Playwright multi-source
GetYourGuide + TourRadar (consumer OTAs confirmed accessible)

Usage:
  python3 scripts/test_tour_scrapers.py --dest lisbon --date 2026-09-05
  python3 scripts/test_tour_scrapers.py --dest "lisbon" --query "food tour" --date 2026-09-05
  python3 scripts/test_tour_scrapers.py --dest lisbon --source getyourguide
  python3 scripts/test_tour_scrapers.py --dest lisbon --source tourradar

Output JSON: core/travel/data/tour_test_{DEST}_{DATE}.json
Screenshots: core/travel/data/tour_{source}_{dest}_{date}.png

Sources:
  getyourguide  — consumer OTA, day tours + excursions (confirmed accessible)
  tourradar     — consumer OTA, multi-day guided tours (confirmed accessible)
  viator        — BOT-BLOCKED (flagged, skip)
  klook         — BOT-BLOCKED (flagged, skip)
"""

import asyncio
import argparse
import json
import re
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path("/home/john/Thunderbird/core/travel/data")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def fmt_price(s: str) -> float | None:
    """Extract float from price string like '$39', '$1,234'."""
    if not s:
        return None
    cleaned = re.sub(r"[^\d.]", "", s.replace(",", ""))
    try:
        return float(cleaned)
    except ValueError:
        return None


# ─────────────────────────────────────────────
# GetYourGuide
# ─────────────────────────────────────────────
# Destination URL map — common D2M destinations
# Format: "slug-lNUM" from GYG URLs
GYG_DEST_MAP = {
    "lisbon": "lisbon-l42",
    "porto": "porto-l433",
    "paris": "paris-l16",
    "rome": "rome-l33",
    "barcelona": "barcelona-l45",
    "amsterdam": "amsterdam-l36",
    "london": "london-l13",
    "athens": "athens-l67",
    "santorini": "santorini-l2744",
    "mykonos": "mykonos-l2745",
    "dubrovnik": "dubrovnik-l2752",
    "reykjavik": "reykjavik-l181",
    "honolulu": "honolulu-l56256",
    "cancun": "cancun-l671",
    "venice": "venice-l37",
    "florence": "florence-l38",
    "amalfi": "amalfi-coast-l75479",
    "stockholm": "stockholm-l99",
    "copenhagen": "copenhagen-l103",
    "oslo": "oslo-l149",
    "bergen": "bergen-l3060",
    "bergen": "bergen-l3060",
    "trinidad": "port-of-spain-l10898",
    "cartagena": "cartagena-l2459",
}


async def scrape_getyourguide(page, dest: str, date: str, query: str = "") -> dict:
    """Scrape GetYourGuide for day tours/activities in a destination."""
    result = {
        "source": "getyourguide",
        "dest": dest,
        "query": query,
        "url": None,
        "scraped_at": datetime.now().isoformat(),
        "date_filter": date,
        "tours": [],
        "total_found_estimate": None,
        "screenshot": None,
        "status": "unknown",
        "notes": "",
    }

    # Build URL
    dest_slug = GYG_DEST_MAP.get(dest.lower())
    if dest_slug:
        url = f"https://www.getyourguide.com/{dest_slug}/"
    else:
        # Fallback: search URL
        search_q = query if query else dest
        url = f"https://www.getyourguide.com/s/?q={search_q.replace(' ', '+')}"

    result["url"] = url
    log(f"  GetYourGuide → {url}")

    try:
        await page.goto(url, timeout=30000, wait_until="domcontentloaded")
        await asyncio.sleep(4)

        # Check for bot wall
        body_text = ""
        try:
            body_text = await page.locator("body").inner_text()
        except Exception:
            pass

        if "access is temporarily restricted" in body_text.lower():
            result["status"] = "bot_blocked"
            result["notes"] = "GYG bot wall detected"
            log(f"    BOT-BLOCKED")
            return result

        # Screenshot
        screenshot_path = OUTPUT_DIR / f"tour_gyg_{dest}_{date}.png"
        await page.screenshot(path=str(screenshot_path))
        result["screenshot"] = str(screenshot_path)

        # Try to get total count from heading (e.g., "500+ results: Lisbon")
        try:
            count_text = await page.locator("text=/\\d+\\+? results/").first.inner_text()
            result["total_found_estimate"] = count_text.strip()
        except Exception:
            pass

        # Extract tour cards (article elements)
        articles = await page.locator("article").all()
        log(f"    Found {len(articles)} article cards")

        tours = []
        for art in articles:
            try:
                text_lines = (await art.inner_text()).strip().split("\n")
                text_lines = [l.strip() for l in text_lines if l.strip()]

                # URL from the link inside article
                link_el = art.locator("a[data-test-id='vertical-activity-card-link']").first
                tour_url = None
                try:
                    href = await link_el.get_attribute("href")
                    if href:
                        tour_url = f"https://www.getyourguide.com{href}" if href.startswith("/") else href
                        # Strip ranking params
                        tour_url = tour_url.split("?")[0]
                except Exception:
                    pass

                # Name from h3
                name = None
                try:
                    name = await art.locator("h3").first.inner_text()
                    name = name.strip()
                except Exception:
                    pass

                # Parse price — find $ amounts in text
                prices = []
                for line in text_lines:
                    p = fmt_price(line) if line.startswith("$") else None
                    if p and p > 0:
                        prices.append(p)

                lowest_price = min(prices) if prices else None
                original_price = max(prices) if len(prices) > 1 else None

                # Rating — look for pattern like "4.7"
                rating = None
                for line in text_lines:
                    m = re.match(r"^(\d\.\d)$", line)
                    if m:
                        rating = float(m.group(1))
                        break

                # Review count — look for pattern like "(20,842)"
                review_count = None
                for line in text_lines:
                    m = re.match(r"^\(([0-9,]+)\)$", line)
                    if m:
                        review_count = int(m.group(1).replace(",", ""))
                        break

                # Duration — look for "X hours", "X days", "X minutes"
                duration = None
                for line in text_lines:
                    if re.search(r"\d+[\s\-]+\d*\s*(hours?|days?|minutes?|hrs?|min)", line, re.IGNORECASE):
                        duration = line
                        break

                # Badge (Top pick, New activity, etc.)
                badge = None
                badge_keywords = ["top pick", "new activity", "bestseller", "likely to sell out"]
                for line in text_lines:
                    if line.lower() in badge_keywords:
                        badge = line
                        break

                if name:
                    tours.append({
                        "name": name,
                        "duration": duration,
                        "rating": rating,
                        "review_count": review_count,
                        "price_pp": lowest_price,
                        "original_price_pp": original_price if original_price != lowest_price else None,
                        "badge": badge,
                        "url": tour_url,
                    })

            except Exception as e:
                log(f"    Card parse error: {e}")
                continue

        result["tours"] = tours
        result["status"] = "ok" if tours else "no_results"
        log(f"    Extracted {len(tours)} tours")

    except Exception as e:
        result["status"] = "error"
        result["notes"] = str(e)
        log(f"    ERROR: {e}")

    return result


# ─────────────────────────────────────────────
# TourRadar
# ─────────────────────────────────────────────
TOURRADAR_DEST_MAP = {
    "portugal": "portugal",
    "lisbon": "portugal",  # TourRadar is country-level for multi-day
    "spain": "spain",
    "barcelona": "spain",
    "france": "france",
    "paris": "france",
    "italy": "italy",
    "rome": "italy",
    "greece": "greece",
    "athens": "greece",
    "santorini": "greece",
    "norway": "norway",
    "bergen": "norway",
    "iceland": "iceland",
    "reykjavik": "iceland",
    "hawaii": "hawaii",
    "honolulu": "hawaii",
    "colombia": "colombia",
    "cartagena": "colombia",
    "scandinavia": "scandinavia",
    "croatia": "croatia",
    "dubrovnik": "croatia",
    "netherlands": "netherlands",
    "amsterdam": "netherlands",
    "uk": "united-kingdom",
    "london": "united-kingdom",
}


async def scrape_tourradar(page, dest: str, date: str) -> dict:
    """Scrape TourRadar for multi-day guided tours to a destination."""
    result = {
        "source": "tourradar",
        "dest": dest,
        "url": None,
        "scraped_at": datetime.now().isoformat(),
        "date_filter": date,
        "tours": [],
        "total_found_estimate": None,
        "screenshot": None,
        "status": "unknown",
        "notes": "Multi-day guided tours (not day excursions)",
    }

    country = TOURRADAR_DEST_MAP.get(dest.lower(), dest.lower().replace(" ", "-"))
    url = f"https://www.tourradar.com/d/{country}"
    result["url"] = url
    log(f"  TourRadar → {url}")

    try:
        await page.goto(url, timeout=30000, wait_until="domcontentloaded")
        await asyncio.sleep(4)

        screenshot_path = OUTPUT_DIR / f"tour_tourradar_{dest}_{date}.png"
        await page.screenshot(path=str(screenshot_path))
        result["screenshot"] = str(screenshot_path)

        # Check for blocking
        body_text = ""
        try:
            body_text = await page.locator("body").inner_text()
        except Exception:
            pass

        if any(kw in body_text.lower() for kw in ["robot", "captcha", "blocked", "403"]):
            result["status"] = "bot_blocked"
            result["notes"] = "Bot indicator found"
            return result

        # .tour-card confirmed working from smoke test
        cards = await page.locator(".tour-card").all()
        log(f"    Found {len(cards)} .tour-card elements")

        # Try to get count text
        try:
            count_el = await page.locator("text=/\\d+ tours/").first.inner_text()
            result["total_found_estimate"] = count_el.strip()
        except Exception:
            pass

        tours = []
        for card in cards:
            try:
                text = (await card.inner_text()).strip()
                lines = [l.strip() for l in text.split("\n") if l.strip()]

                # Get tour URL
                tour_url = None
                try:
                    link = card.locator("a").first
                    href = await link.get_attribute("href")
                    if href:
                        tour_url = f"https://www.tourradar.com{href}" if href.startswith("/") else href
                except Exception:
                    pass

                # Name — typically the first non-badge, non-operator line
                name = lines[0] if lines else None

                # Price — look for $ or USD patterns
                price = None
                for line in lines:
                    m = re.search(r"\$[\d,]+", line)
                    if m:
                        price = fmt_price(m.group(0))
                        break

                # Duration — look for "X days"
                duration = None
                for line in lines:
                    if re.search(r"\d+\s*days?", line, re.I):
                        duration = line
                        break

                # Rating
                rating = None
                for line in lines:
                    m = re.match(r"^(\d\.\d)$", line)
                    if m:
                        rating = float(m.group(1))
                        break

                if name and len(name) > 5:
                    tours.append({
                        "name": name,
                        "duration": duration,
                        "rating": rating,
                        "price_pp": price,
                        "url": tour_url,
                    })

            except Exception as e:
                log(f"    Card parse error: {e}")
                continue

        result["tours"] = tours
        result["status"] = "ok" if tours else "no_results"
        log(f"    Extracted {len(tours)} tours")

    except Exception as e:
        result["status"] = "error"
        result["notes"] = str(e)
        log(f"    ERROR: {e}")

    return result


# ─────────────────────────────────────────────
# Main runner
# ─────────────────────────────────────────────
async def run_tests(dest: str, date: str, source: str = "all", query: str = ""):
    from playwright.async_api import async_playwright

    results = {
        "dest": dest,
        "query": query,
        "date": date,
        "scraped_at": datetime.now().isoformat(),
        "getyourguide": {},
        "tourradar": {},
    }

    # JSON merge — preserve existing data for sources we're not re-running
    safe_dest = dest.replace(" ", "_")
    out_file = OUTPUT_DIR / f"tour_test_{safe_dest}_{date}.json"
    if out_file.exists() and source != "all":
        try:
            existing = json.loads(out_file.read_text())
            for src_key in ["getyourguide", "tourradar"]:
                if src_key != source and existing.get(src_key):
                    results[src_key] = existing[src_key]
            log(f"  Merged existing data from {out_file.name} (preserving non-{source} sources)")
        except Exception as e:
            log(f"  Warning: could not load existing JSON for merge: {e}")

    log(f"Tour scraper | dest={dest} | date={date} | source={source}")
    if query:
        log(f"  query filter: {query}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ],
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            ),
        )

        if source in ("all", "getyourguide"):
            page = await context.new_page()
            try:
                results["getyourguide"] = await scrape_getyourguide(page, dest, date, query)
            finally:
                await page.close()

        if source in ("all", "tourradar"):
            page = await context.new_page()
            try:
                results["tourradar"] = await scrape_tourradar(page, dest, date)
            finally:
                await page.close()

        await browser.close()

    # Save
    out_file.write_text(json.dumps(results, indent=2))
    log(f"\nSaved: {out_file}")

    # Print summary
    print("\n" + "=" * 60)
    print(f"TOUR PRICES — {dest.upper()} | {date}")
    print("=" * 60)

    gyg = results.get("getyourguide", {})
    if gyg.get("status") == "ok":
        tours = gyg.get("tours", [])
        print(f"\nGetYourGuide ({gyg.get('total_found_estimate', '?')} total):")
        print(f"  {'Tour':<55} {'$/pp':>7}  {'Rating':>6}  {'Duration'}")
        print(f"  {'-'*55} {'-----':>7}  {'------':>6}  {'---------'}")
        for t in tours[:10]:
            name = (t.get("name") or "")[:54]
            price = f"${t['price_pp']:.0f}" if t.get("price_pp") else "  n/a"
            rating = f"{t['rating']:.1f}" if t.get("rating") else "  n/a"
            dur = (t.get("duration") or "")[:20]
            print(f"  {name:<55} {price:>7}  {rating:>6}  {dur}")
        if len(tours) > 10:
            print(f"  ... and {len(tours)-10} more")
    elif gyg.get("status") == "bot_blocked":
        print("\nGetYourGuide: BOT-BLOCKED")
    elif gyg:
        print(f"\nGetYourGuide: {gyg.get('status', 'unknown')} — {gyg.get('notes', '')}")

    tr = results.get("tourradar", {})
    if tr.get("status") == "ok":
        tours = tr.get("tours", [])
        print(f"\nTourRadar — Multi-day tours ({tr.get('total_found_estimate', '?')} total):")
        print(f"  {'Tour':<55} {'$/pp':>7}  {'Duration'}")
        print(f"  {'-'*55} {'-----':>7}  {'---------'}")
        for t in tours[:5]:
            name = (t.get("name") or "")[:54]
            price = f"${t['price_pp']:.0f}" if t.get("price_pp") else "  n/a"
            dur = (t.get("duration") or "")[:20]
            print(f"  {name:<55} {price:>7}  {dur}")
        if len(tours) > 5:
            print(f"  ... and {len(tours)-5} more")
    elif tr.get("status") == "bot_blocked":
        print("\nTourRadar: BOT-BLOCKED")
    elif tr:
        print(f"\nTourRadar: {tr.get('status', 'unknown')} — {tr.get('notes', '')}")

    print()
    return results


def main():
    parser = argparse.ArgumentParser(description="Tour price scraper — GetYourGuide + TourRadar")
    parser.add_argument("--dest", required=True, help="Destination (city or country)")
    parser.add_argument("--date", default="2026-09-05", help="Date (YYYY-MM-DD, used for output filename)")
    parser.add_argument("--source", default="all", choices=["all", "getyourguide", "tourradar"])
    parser.add_argument("--query", default="", help="Optional search query filter (e.g. 'food tour')")
    args = parser.parse_args()

    asyncio.run(run_tests(args.dest, args.date, args.source, args.query))


if __name__ == "__main__":
    main()
