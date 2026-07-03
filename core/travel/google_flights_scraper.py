"""
Thunderbird Google Flights Scraper — Production Module
========================================================
Dreams2Memories Travel, LLC

Playwright Firefox headless scraper for Google Flights prices and price history.
Uses persistent Firefox profile for session stability.

Google Flights provides 90-day price history graphs — useful for trend analysis.

Function:
  search_google_flights(origin, dest, depart_date, adults=2) -> dict
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


def _parse_lowest(prices: list, lo: float = 50, hi: float = 25_000) -> Optional[float]:
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


async def search_google_flights(
    origin: str,
    dest: str,
    depart_date: str,
    adults: int = 2,
) -> dict:
    """Scrape Google Flights for one-way fares using Firefox persistent profile.

    Args:
        origin: IATA origin code (e.g. 'DEN')
        dest: IATA destination code (e.g. 'HNL')
        depart_date: Departure date YYYY-MM-DD
        adults: Number of adult travelers

    Returns:
        dict with: source, lowest_price, currency, airlines[], duration_min,
                   graph_data_available (bool), url, status, scraped_at
    """
    origin = origin.upper().strip()
    dest = dest.upper().strip()

    url = (
        f"https://www.google.com/travel/flights"
        f"?q=Flights+to+{dest}+from+{origin}+on+{depart_date}"
        f"&curr=USD"
    )

    result: dict = {
        "source": "google_flights",
        "origin": origin,
        "dest": dest,
        "depart_date": depart_date,
        "url": url,
        "lowest_price": None,
        "currency": "USD",
        "airlines": [],
        "duration_min": None,
        "stops": None,
        "graph_data_available": False,
        "status": "ok",
        "error": None,
        "scraped_at": datetime.now().isoformat(),
    }

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        result["status"] = "error"
        result["error"] = "playwright not installed"
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

            # Wait for results to load — Google Flights uses a dynamic SPA
            try:
                # Wait for either the price results or the "best flights" heading
                await page.wait_for_selector(
                    'div[role="listbox"], [class*="gws-flights"], [class*="UXVgdb"], '
                    '[class*="Rk10dc"], [aria-label*="results"]',
                    timeout=20_000,
                )
                await page.wait_for_timeout(3_000)
            except Exception:
                await page.wait_for_timeout(6_000)

            # Extract price data
            raw_prices = await page.evaluate("""() => {
                const prices = new Set();
                // Google Flights price elements
                const selectors = [
                    '[class*="FpEdX"]',    // price span
                    '[class*="YMlIz"]',    // price text
                    '[class*="Price"]',
                    '[class*="gws-flights-results"] [class*="price"]',
                    '[aria-label*="dollar"]',
                    'span[class*="price"]',
                ];
                for (const sel of selectors) {
                    document.querySelectorAll(sel).forEach(el => {
                        const t = (el.innerText || el.textContent || '').trim();
                        const m = t.match(/\\$[\\d,]+(\\.\\d{2})?/);
                        if (m) prices.add(m[0]);
                    });
                }
                // Fallback: any $ text in the flight results area
                const resultsArea = document.querySelector('[role="listbox"], [class*="results"], main');
                if (resultsArea) {
                    const text = resultsArea.innerText || resultsArea.textContent || '';
                    const matches = text.match(/\\$[\\d,]+/g);
                    if (matches) matches.forEach(m => prices.add(m));
                }
                return Array.from(prices).slice(0, 20);
            }""")

            # Extract airline names
            airlines = await page.evaluate("""() => {
                const names = new Set();
                document.querySelectorAll('[class*="airline"], [class*="carrier"], '
                    + '[aria-label*="airline"], [class*="I8N2Ac"]').forEach(el => {
                    const t = (el.innerText || el.textContent || '').trim();
                    if (t && t.length < 60 && !t.includes('$') && !t.includes('.')) names.add(t);
                });
                return Array.from(names).slice(0, 10);
            }""")

            # Detect if price history graph is available
            graph_available = await page.evaluate("""() => {
                const selectors = [
                    'canvas', 'svg[class*="chart"]', '[class*="chart"]',
                    '[class*="graph"]', '[aria-label*="price history"]',
                    '[class*="UXVgdb"]',
                ];
                for (const sel of selectors) {
                    const el = document.querySelector(sel);
                    if (el) return true;
                }
                return false;
            }""")

            # Fallback: full page text regex
            if not raw_prices:
                page_text = await page.inner_text("body")
                matches = re.findall(r'\$[\d,]+', page_text)
                raw_prices = list(dict.fromkeys(matches))[:15]

            lowest = _parse_lowest(raw_prices, lo=50, hi=25_000)

            result["lowest_price"] = lowest
            result["airlines"] = list(set(airlines))
            result["graph_data_available"] = bool(graph_available)
            result["duration_min"] = None  # Google Flights doesn't expose clean duration in DOM
            result["stops"] = None

            await context.close()

    except Exception as exc:
        logger.error("google_flights: search error %s->%s: %s", origin, dest, exc)
        result["status"] = "error"
        result["error"] = str(exc)

    return result


async def main():
    """CLI test."""
    import argparse

    parser = argparse.ArgumentParser(description="Google Flights scraper")
    parser.add_argument("origin", help="Origin IATA code")
    parser.add_argument("dest", help="Destination IATA code")
    parser.add_argument("depart_date", help="Departure date YYYY-MM-DD")
    parser.add_argument("--adults", type=int, default=2)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    result = await search_google_flights(
        origin=args.origin,
        dest=args.dest,
        depart_date=args.depart_date,
        adults=args.adults,
    )
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
