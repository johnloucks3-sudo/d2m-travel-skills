"""
Transfer site smoke test — headless Playwright
Navigates to search/results pages for each site, screenshots, reports accessible vs blocked.
Test route: Lisbon Airport (LIS) → Lisbon city center (standard benchmark)

Usage: python3 scripts/smoke_test_transfer_sites.py
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path("/home/john/Thunderbird/core/travel/data")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TAG = "transfers"


def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


# Sites to smoke test — use a real Lisbon Airport → Lisbon city search where possible
SITES = [
    {
        "name": "kiwitaxi",
        "url": "https://kiwitaxi.com/Portugal/Lisbon/airport-LIS/to/Lisbon",
        "real_result_selectors": [
            "[class*='offer']",
            "[class*='vehicle']",
            "[class*='transfer']",
            "[class*='card']",
            "[class*='result']",
        ],
        "bot_indicators": ["captcha", "robot", "blocked", "403"],
        "notes": "Global transfer aggregator — price per vehicle",
    },
    {
        "name": "welcomepickups",
        "url": "https://www.welcomepickups.com/transfers/lisbon-airport-to-lisbon/",
        "real_result_selectors": [
            "[class*='vehicle']",
            "[class*='transfer-option']",
            "[class*='car-type']",
            "[class*='price']",
            "[class*='offer']",
        ],
        "bot_indicators": ["captcha", "robot", "blocked"],
        "notes": "Premium transfers, European ports, good cruise coverage",
    },
    {
        "name": "blacklane",
        "url": "https://www.blacklane.com/en/",
        "real_result_selectors": [
            "[class*='service']",
            "[class*='vehicle']",
            "[class*='booking']",
            "input[placeholder*='pickup']",
            "input[placeholder*='from']",
        ],
        "bot_indicators": ["captcha", "robot", "blocked"],
        "notes": "Luxury chauffeur — matches D2M client profile",
    },
    {
        "name": "gettransfer",
        "url": "https://gettransfer.com/en/search?from=Lisbon+Airport+(LIS)&to=Lisbon+City+Center&passengers=2&date=2026-09-05",
        "real_result_selectors": [
            "[class*='offer']",
            "[class*='transfer']",
            "[class*='carrier']",
            "[class*='result']",
            "[class*='price']",
        ],
        "bot_indicators": ["captcha", "robot", "blocked", "403"],
        "notes": "B2B-leaning aggregator, fixed-price transfers",
    },
    {
        "name": "jayride",
        "url": "https://www.jayride.com/airport-transfers/Lisbon-Airport-LIS/",
        "real_result_selectors": [
            "[class*='listing']",
            "[class*='transfer']",
            "[class*='vehicle']",
            "[class*='result']",
        ],
        "bot_indicators": ["captcha", "robot", "blocked"],
        "notes": "Airport transfer aggregator",
    },
    {
        "name": "getyourguide_transfers",
        "url": "https://www.getyourguide.com/lisbon-l42/transfers/",
        "real_result_selectors": [
            "article",
            "[class*='activity-card']",
        ],
        "bot_indicators": ["access is temporarily restricted", "robot"],
        "notes": "GYG transfer category — already confirmed accessible on main site",
    },
    {
        "name": "holidaytaxis",
        "url": "https://www.holidaytaxis.com/en/",
        "real_result_selectors": [
            "[class*='vehicle']",
            "[class*='transfer']",
            "[class*='result']",
            "input[name*='from']",
        ],
        "bot_indicators": ["captcha", "robot", "blocked"],
        "notes": "UK-based airport transfer specialist",
    },
    {
        "name": "rome2rio",
        "url": "https://www.rome2rio.com/s/Lisbon-Airport/Lisbon",
        "real_result_selectors": [
            "[class*='segment']",
            "[class*='route']",
            "[class*='result']",
            "[class*='mode']",
        ],
        "bot_indicators": ["captcha", "robot", "blocked"],
        "notes": "Route finder — shows all transport modes including taxi/transfer",
    },
]


async def smoke_test_site(page, site: dict, date: str) -> dict:
    name = site["name"]
    url = site["url"]
    log(f"  Testing {name} → {url[:80]}")

    result = {
        "site": name,
        "url": url,
        "status": "unknown",
        "real_results_found": False,
        "bot_indicator_found": None,
        "result_count_estimate": 0,
        "screenshot": None,
        "page_title": None,
        "notes": site.get("notes", ""),
    }

    try:
        await page.goto(url, timeout=30000, wait_until="domcontentloaded")
        await asyncio.sleep(4)

        result["page_title"] = await page.title()

        screenshot_path = OUTPUT_DIR / f"smoke_transfer_{name}_{date}.png"
        await page.screenshot(path=str(screenshot_path))
        result["screenshot"] = str(screenshot_path)

        # Check for bot indicators in body text
        body_text = ""
        try:
            body_text = (await page.inner_text("body")).lower()
        except Exception:
            pass

        for indicator in site["bot_indicators"]:
            if indicator.lower() in body_text:
                result["bot_indicator_found"] = indicator
                result["status"] = "bot_blocked"
                result["notes"] += f" | Bot indicator: '{indicator}'"
                log(f"    BOT-BLOCKED: '{indicator}' in page")
                return result

        # Check real result selectors
        for selector in site["real_result_selectors"]:
            try:
                count = await page.locator(selector).count()
                if count > 0:
                    result["real_results_found"] = True
                    result["result_count_estimate"] = count
                    result["status"] = "ok"
                    result["notes"] += f" | Selector '{selector}' matched {count} elements"
                    log(f"    OK: {count} elements via '{selector}'")
                    return result
            except Exception:
                pass

        result["status"] = "ambiguous"
        result["notes"] += " | No bot, no selector match — check screenshot"
        log(f"    AMBIGUOUS — check screenshot: {screenshot_path.name}")

    except Exception as e:
        result["status"] = "error"
        result["notes"] += f" | {e}"
        log(f"    ERROR: {e}")

    return result


async def run_smoke_tests(date: str = "2026-09-05"):
    from playwright.async_api import async_playwright

    log(f"Transfer site smoke test | route: LIS → Lisbon city | date={date}")
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
    log("=" * 65)
    log("SMOKE TEST SUMMARY — TRANSFER SITES")
    log("=" * 65)
    for r in results:
        icon = {"ok": "✅", "bot_blocked": "❌", "ambiguous": "⚠️", "error": "💥"}.get(r["status"], "?")
        title = (r.get("page_title") or "")[:35]
        log(f"  {icon} {r['site']:22} {r['status']:12}  \"{title}\"")

    out_file = OUTPUT_DIR / f"smoke_transfer_sites_{date}.json"
    out_file.write_text(json.dumps({"tested_at": datetime.now().isoformat(), "results": results}, indent=2))
    log(f"\nResults + screenshots saved to: {OUTPUT_DIR}")
    return results


if __name__ == "__main__":
    asyncio.run(run_smoke_tests())
