"""
Centrav B2B → intel_index connector.
Playwright session-health check + featured deal scrape.
TTL: 4h (session health), 8h (pricing)

Auth: session cookies from ~/Thunderbird/centrav_credentials.json
      and ~/Thunderbird/core/travel/data/centrav_session.json
"""
import json
import logging
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

THUNDERBIRD = Path("/home/john/Thunderbird")
CREDS_PATH = THUNDERBIRD / "centrav_credentials.json"
SESSION_FILE = THUNDERBIRD / "core" / "travel" / "data" / "centrav_session.json"

# Key cruise embarkation routes to spot-check pricing
SPOT_CHECK_ROUTES = [
    ("DEN", "MIA"),   # Denver → Miami (Regent/Silversea Caribbean hub)
    ("DEN", "FLL"),   # Denver → Fort Lauderdale
    ("DEN", "BCN"),   # Denver → Barcelona (Med cruises)
]


def _load_cookies() -> list[dict]:
    """Build playwright cookie list from credentials + session files."""
    cookies_dict: dict = {}

    if CREDS_PATH.exists():
        try:
            creds = json.loads(CREDS_PATH.read_text())
            for name, value in creds.get("cookies", {}).items():
                cookies_dict[name] = value
        except Exception as e:
            logger.warning("centrav: creds file read error: %s", e)

    if SESSION_FILE.exists():
        try:
            sess = json.loads(SESSION_FILE.read_text())
            if isinstance(sess, list):
                for c in sess:
                    if c.get("name"):
                        cookies_dict[c["name"]] = c.get("value", "")
        except Exception as e:
            logger.warning("centrav: session file read error: %s", e)

    result = []
    for name, value in cookies_dict.items():
        domain = ".centrav.com" if name.startswith("_g") else "www.centrav.com"
        result.append({"name": name, "value": value, "domain": domain, "path": "/"})
    return result


async def _check_and_scrape(cookies: list[dict]) -> dict:
    """Return {authenticated, deals, route_prices}."""
    from playwright.async_api import async_playwright

    output = {"authenticated": False, "deals": [], "route_prices": []}

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
        )
        if cookies:
            await ctx.add_cookies(cookies)

        page = await ctx.new_page()
        try:
            await page.goto("https://www.centrav.com/", wait_until="domcontentloaded", timeout=25_000)
            await page.wait_for_timeout(2_000)

            current_url = page.url
            page_text = await page.inner_text("body")

            # Detect auth state
            if "login" in current_url.lower():
                logger.info("centrav: session expired (redirected to login)")
            elif "logout" in page_text.lower() or "my account" in page_text.lower():
                output["authenticated"] = True
                logger.info("centrav: session valid ✓")
            elif await page.query_selector("#FareFlyingFrom"):
                output["authenticated"] = True
                logger.info("centrav: session valid (search form visible) ✓")
            else:
                logger.info("centrav: session status ambiguous, URL=%s", current_url)

            if output["authenticated"]:
                # Scrape featured deals / promotions from main page
                deal_selectors = [
                    ".deal-card", "[class*='deal']", "[class*='promo']",
                    "[class*='featured']", ".specials-item",
                ]
                for sel in deal_selectors:
                    cards = await page.query_selector_all(sel)
                    if cards:
                        for card in cards[:10]:
                            text = await card.inner_text()
                            if text.strip():
                                output["deals"].append(text.strip()[:300])
                        break

                # Quick spot-check: try to get pricing for DEN→MIA
                try:
                    origin_el = await page.query_selector("#FareFlyingFrom, input[name='from']")
                    dest_el = await page.query_selector("#FareFlyingTo, input[name='to']")
                    if origin_el and dest_el:
                        await origin_el.fill("DEN")
                        await dest_el.fill("MIA")
                        await page.wait_for_timeout(1_000)
                        # Check for autocomplete suggestions
                        suggestions = await page.query_selector_all(
                            "[class*='autocomplete'] li, [class*='dropdown'] li"
                        )
                        if suggestions:
                            await suggestions[0].click()
                        logger.debug("centrav: search form interacted")
                except Exception as e:
                    logger.debug("centrav: search form interaction skipped: %s", e)

        except Exception as e:
            logger.warning("centrav: page error: %s", e)
        finally:
            await page.close()
            await browser.close()

    return output


def ingest_centrav(con: sqlite3.Connection, upsert_rows, log_run, ttl: int) -> None:
    t0 = time.monotonic()

    try:
        import asyncio
    except ImportError as e:
        log_run(con, "centrav", "import_error", error=str(e))
        return

    try:
        from playwright.async_api import async_playwright  # noqa: F401
    except ImportError as e:
        logger.error("centrav: playwright not installed: %s", e)
        log_run(con, "centrav", "import_error", error=str(e))
        return

    cookies = _load_cookies()
    if not cookies:
        logger.warning("centrav: no cookies found — need to re-auth via browser")
        log_run(con, "centrav", "no_credentials",
                error="No session cookies found. Run: centrav-flights --centrav-login --headless false")
        return

    try:
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(_check_and_scrape(cookies))
        loop.close()
    except Exception as e:
        elapsed = time.monotonic() - t0
        logger.error("centrav: playwright error: %s", e)
        log_run(con, "centrav", "playwright_error", elapsed=elapsed, error=str(e))
        return

    elapsed = time.monotonic() - t0
    now = datetime.now(timezone.utc).isoformat()

    # Always record session health row
    health_row = {
        "id": "centrav_session_health",
        "authenticated": result["authenticated"],
        "cookie_count": len(cookies),
        "checked_at": now,
        "note": "Session valid" if result["authenticated"] else "Session expired — re-auth needed",
    }
    n_health = upsert_rows(con, "centrav", "session_health", [health_row], ttl,
                           provenance="https://www.centrav.com/")
    log_run(con, "centrav", "session_health_check",
            rows_in=n_health, rows_out=n_health, elapsed=elapsed,
            error="" if result["authenticated"] else "session_expired")

    if result["authenticated"] and result["deals"]:
        deal_rows = []
        for i, text in enumerate(result["deals"]):
            deal_rows.append({
                "id": f"centrav_deal_{i}",
                "text": text,
                "scraped_at": now,
            })
        n_deals = upsert_rows(con, "centrav", "featured_deals", deal_rows, ttl,
                              provenance="https://www.centrav.com/")
        log_run(con, "centrav", "deals_refresh", rows_in=n_deals, rows_out=n_deals, elapsed=elapsed)
        logger.info("centrav: %d deal rows, session=%s, %.1fs",
                    n_deals, result["authenticated"], elapsed)
    elif not result["authenticated"]:
        logger.warning("centrav: session expired — re-auth required")
        logger.warning("centrav: run: python3 scripts/centrav_flights.py --centrav-login --headless false")
    else:
        logger.info("centrav: session valid, 0 featured deals on page (%.1fs)", elapsed)
        log_run(con, "centrav", "no_deals", rows_in=0, rows_out=0, elapsed=elapsed)
