"""
Thunderbird Kayak Flight Scraper — Production Module
=====================================================
Dreams2Memories Travel, LLC

Playwright Firefox headless scraper for Kayak.com flight prices.
Uses persistent Firefox profile for session stability (cookie reuse, CAPTCHA avoidance).

Function:
  search_kayak(origin, dest, depart_date, adults=2, cabin="economy") -> dict
"""

import asyncio
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────

THUNDERBIRD = Path.home() / "Thunderbird"
PROFILE_DIR = THUNDERBIRD / "core" / "travel" / "data" / "centrav_ff_profile"
DATA_DIR = THUNDERBIRD / "core" / "travel" / "data"
OUTPUT_DIR = THUNDERBIRD / "output"

# ── Cabin mapping ─────────────────────────────────────────────────────────────

_CABIN_MAP = {
    "economy": "e",
    "premium": "pe",
    "premium economy": "pe",
    "business": "b",
    "first": "b",
}


def _parse_lowest(prices: list, lo: float = 50, hi: float = 15_000) -> Optional[float]:
    """Extract lowest valid price from scraped strings."""
    lowest = None
    for p in prices:
        try:
            val = float(str(p).replace("$", "").replace(",", "").strip())
            if lo < val < hi:
                if lowest is None or val < lowest:
                    lowest = val
        except (ValueError, TypeError):
            continue
    return lowest


async def search_kayak(
    origin: str,
    dest: str,
    depart_date: str,
    adults: int = 2,
    cabin: str = "economy",
) -> dict:
    """Scrape Kayak for one-way fares using Firefox persistent profile.

    Args:
        origin: IATA origin code (e.g. 'DEN')
        dest: IATA destination code (e.g. 'HNL')
        depart_date: Departure date YYYY-MM-DD
        adults: Number of adult travelers
        cabin: 'economy', 'premium', 'business', or 'first'

    Returns:
        dict with: source, cabin, lowest_price, url, currency, airlines[],
                   duration_min, stops, status, scraped_at
    """
    cabin_code = _CABIN_MAP.get(cabin.lower(), "e")
    origin = origin.upper().strip()
    dest = dest.upper().strip()

    url = (
        f"https://www.kayak.com/flights/{origin}-{dest}/{depart_date}/{adults}adults"
        f"?sort=price_a&fs=cabin={cabin_code}"
    )

    result: dict = {
        "source": "kayak",
        "cabin": cabin.lower(),
        "origin": origin,
        "dest": dest,
        "depart_date": depart_date,
        "url": url,
        "lowest_price": None,
        "currency": "USD",
        "airlines": [],
        "duration_min": None,
        "stops": None,
        "status": "ok",
        "error": None,
        "scraped_at": datetime.now().isoformat(),
    }

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        result["status"] = "error"
        result["error"] = "playwright not installed — pip install playwright && playwright install firefox"
        return result

    try:
        async with async_playwright() as pw:
            context = await pw.firefox.launch_persistent_context(
                str(PROFILE_DIR),
                headless=True,
                args=["--no-sandbox"],
                viewport={"width": 1440, "height": 900},
                locale="en-US",
            )

            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=30_000)

            # Accept cookie banners
            for sel in [
                "#onetrust-accept-btn-handler",
                "button[data-testid='accept-cookies']",
                "button:has-text('Accept all')",
                "button:has-text('I Accept')",
            ]:
                try:
                    btn = page.locator(sel)
                    if await btn.is_visible(timeout=1_000):
                        await btn.click()
                        await page.wait_for_timeout(500)
                        break
                except Exception:
                    continue

            # Wait for results to render
            try:
                await page.wait_for_selector(
                    "[class*='price-text'], [class*='above-the-fold'], [data-resultid], [class*='resultInner']",
                    timeout=20_000,
                )
                await page.wait_for_timeout(2_000)
            except Exception:
                # Extended wait for slower loads
                await page.wait_for_timeout(5_000)

            # Close any modal dialogs
            for sel in [
                "button.close",
                "button[aria-label='Close']",
                "[class*='dialog'] button:has-text('\u00d7')",
                "[class*='modal'] [class*='close']",
                "button:has-text('\u2715')",
            ]:
                try:
                    btn = page.locator(sel)
                    if await btn.is_visible(timeout=500):
                        await btn.click()
                        await page.wait_for_timeout(300)
                except Exception:
                    continue

            # Extract prices from result cards (avoids UI element false reads)
            raw_prices = await page.evaluate("""() => {
                const cardSelectors = ['[data-resultid]', '[class*="resultInner"]', '[class*="above-the-fold"]'];
                let cards = [];
                for (const sel of cardSelectors) {
                    const found = document.querySelectorAll(sel);
                    if (found.length > 0) { cards = Array.from(found); break; }
                }
                const prices = [];
                const scope = cards.length > 0 ? cards : [document.body];
                for (const card of scope.slice(0, 10)) {
                    const text = card.innerText || card.textContent || '';
                    const matches = text.match(/\\$[\\d,]+(\\.\\d{2})?/g);
                    if (matches) matches.forEach(m => prices.push(m));
                }
                // Fallback
                if (prices.length === 0) {
                    document.querySelectorAll('[class*="price-text"]').forEach(el => {
                        const t = (el.innerText || el.textContent || '').trim();
                        if (/^\\$[\\d,]+$/.test(t)) prices.push(t);
                    });
                }
                return [...new Set(prices)].slice(0, 20);
            }""")

            # Extract airline names
            airlines = await page.evaluate("""() => {
                const names = [];
                document.querySelectorAll('[class*="carrier-name"], [class*="airline-name"], [class*="operatedBy"]').forEach(el => {
                    const t = (el.innerText || el.textContent || '').trim();
                    if (t && t.length < 60 && !t.includes('$')) names.push(t);
                });
                return [...new Set(names)].slice(0, 10);
            }""")

            # Fallback: extract from page text if no results from cards
            if not raw_prices:
                page_text = await page.inner_text("body")
                matches = re.findall(r'\$[\d,]+', page_text)
                raw_prices = list(dict.fromkeys(matches))[:15]

            lowest = _parse_lowest(raw_prices, lo=50, hi=15_000)

            result["lowest_price"] = lowest
            result["airlines"] = airlines

            # Try to extract duration (simplified)
            result["duration_min"] = None
            result["stops"] = None

            await context.close()

    except Exception as exc:
        logger.error("kayak: search error %s->%s %s: %s", origin, dest, cabin, exc)
        result["status"] = "error"
        result["error"] = str(exc)

    return result


async def main():
    """CLI test: python3 kayak_scraper.py DEN HNL 2026-08-15 --cabin economy"""
    import argparse

    parser = argparse.ArgumentParser(description="Kayak flight scraper")
    parser.add_argument("origin", help="Origin IATA code")
    parser.add_argument("dest", help="Destination IATA code")
    parser.add_argument("depart_date", help="Departure date YYYY-MM-DD")
    parser.add_argument("--adults", type=int, default=2, help="Number of adults")
    parser.add_argument("--cabin", default="economy", help="economy|premium|business")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    result = await search_kayak(
        origin=args.origin,
        dest=args.dest,
        depart_date=args.depart_date,
        adults=args.adults,
        cabin=args.cabin,
    )
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
