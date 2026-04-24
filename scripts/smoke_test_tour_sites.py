"""
Tour site smoke test — headless Playwright
Navigates to search results pages for each site, screenshots, reports bot-blocked vs accessible.
Usage: python3 scripts/smoke_test_tour_sites.py [--dest lisbon] [--date 2026-09-05]
"""

import asyncio
import argparse
import json
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path("/home/john/Thunderbird/core/travel/data")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


# Site definitions: name, search URL template, selectors that indicate real results
SITES = [
    {
        "name": "viator",
        "url": "https://www.viator.com/Lisbon/d538-ttd",
        "real_result_selectors": [
            "[data-testid='product-card']",
            ".product-listing",
            "article.result-card",
        ],
        "bot_indicators": ["captcha", "cf-challenge", "robot", "Access Denied"],
    },
    {
        "name": "getyourguide",
        "url": "https://www.getyourguide.com/lisbon-l42/",
        "real_result_selectors": [
            "[data-testid='activity-card']",
            ".activity-card",
            "article[data-id]",
            "[data-cy='activity-card']",
        ],
        "bot_indicators": ["captcha", "cf-challenge", "robot", "blocked"],
    },
    {
        "name": "klook",
        "url": "https://www.klook.com/en-US/search/?query=lisbon+tours",
        "real_result_selectors": [
            ".search-result-card",
            "[data-testid='search-result']",
            ".activity-card",
        ],
        "bot_indicators": ["captcha", "robot", "Access Denied", "403"],
    },
    {
        "name": "tourradar",
        "url": "https://www.tourradar.com/d/portugal",
        "real_result_selectors": [
            ".tour-card",
            "[data-testid='tour-card']",
            ".listing-card",
        ],
        "bot_indicators": ["captcha", "robot", "blocked"],
    },
    {
        "name": "tiqets",
        "url": "https://www.tiqets.com/en/lisbon-attractions-c63751/",
        "real_result_selectors": [
            ".product-card",
            "[data-testid='product']",
            ".venue-card",
        ],
        "bot_indicators": ["captcha", "robot", "blocked", "forbidden"],
    },
    {
        "name": "headout",
        "url": "https://www.headout.com/lisbon/",
        "real_result_selectors": [
            ".product-card",
            "[data-testid='experience-card']",
            ".tour-card",
        ],
        "bot_indicators": ["captcha", "robot", "blocked"],
    },
]


async def smoke_test_site(page, site: dict, date: str) -> dict:
    name = site["name"]
    url = site["url"]
    log(f"  Testing {name} → {url}")

    result = {
        "site": name,
        "url": url,
        "status": "unknown",
        "real_results_found": False,
        "bot_indicator_found": None,
        "result_count_estimate": 0,
        "screenshot": None,
        "page_title": None,
        "notes": "",
    }

    try:
        await page.goto(url, timeout=30000, wait_until="domcontentloaded")
        await asyncio.sleep(3)  # let JS settle

        # Grab page title
        result["page_title"] = await page.title()

        # Screenshot
        screenshot_path = OUTPUT_DIR / f"smoke_{name}_{date}.png"
        await page.screenshot(path=str(screenshot_path), full_page=False)
        result["screenshot"] = str(screenshot_path)

        # Check page text for bot indicators
        body_text = (await page.inner_text("body")).lower() if True else ""
        try:
            body_text = (await page.inner_text("body")).lower()
        except Exception:
            body_text = ""

        for indicator in site["bot_indicators"]:
            if indicator.lower() in body_text:
                result["bot_indicator_found"] = indicator
                result["status"] = "bot_blocked"
                result["notes"] = f"Bot indicator '{indicator}' found in page body"
                log(f"    BOT-BLOCKED: '{indicator}' detected")
                return result

        # Check for real result selectors
        for selector in site["real_result_selectors"]:
            try:
                count = await page.locator(selector).count()
                if count > 0:
                    result["real_results_found"] = True
                    result["result_count_estimate"] = count
                    result["status"] = "ok"
                    result["notes"] = f"Selector '{selector}' matched {count} elements"
                    log(f"    OK: {count} results via '{selector}'")
                    return result
            except Exception:
                pass

        # No bot indicators, no known result selectors — ambiguous
        result["status"] = "ambiguous"
        result["notes"] = "No bot indicators found, but no known result selectors matched. Check screenshot."
        log(f"    AMBIGUOUS — check screenshot: {screenshot_path.name}")

    except Exception as e:
        result["status"] = "error"
        result["notes"] = str(e)
        log(f"    ERROR: {e}")

    return result


async def run_smoke_tests(dest: str, date: str):
    from playwright.async_api import async_playwright

    log(f"Tour site smoke test | dest={dest} | date={date}")
    log(f"Sites: {[s['name'] for s in SITES]}")
    log("")

    results = []

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

        for site in SITES:
            page = await context.new_page()
            try:
                result = await smoke_test_site(page, site, date)
                results.append(result)
            finally:
                await page.close()

        await browser.close()

    # Summary
    log("")
    log("=" * 60)
    log("SMOKE TEST SUMMARY")
    log("=" * 60)
    for r in results:
        icon = {"ok": "✅", "bot_blocked": "❌", "ambiguous": "⚠️", "error": "💥"}.get(r["status"], "?")
        log(f"  {icon} {r['site']:15} {r['status']:12} {r['notes'][:60]}")

    # Save results
    out_file = OUTPUT_DIR / f"smoke_tour_sites_{date}.json"
    out_file.write_text(json.dumps({"tested_at": datetime.now().isoformat(), "results": results}, indent=2))
    log(f"\nResults saved: {out_file}")

    return results


def main():
    parser = argparse.ArgumentParser(description="Smoke test tour booking sites")
    parser.add_argument("--dest", default="lisbon", help="Destination name")
    parser.add_argument("--date", default="2026-09-05", help="Date (YYYY-MM-DD)")
    args = parser.parse_args()

    asyncio.run(run_smoke_tests(args.dest, args.date))


if __name__ == "__main__":
    main()
