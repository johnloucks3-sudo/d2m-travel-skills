"""
Bedsonline (app.bedsonline.com) → intel_index connector.
Playwright login + hotel availability scrape for cruise destination cities.
TTL: 24h

Auth: hotelbeds_credentials.json → portal_username / portal_password
"""
import json
import logging
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

THUNDERBIRD = Path("/home/john/Thunderbird")
CREDS_PATH = THUNDERBIRD / "hotelbeds_credentials.json"

# Key cruise port cities to scrape hotel rates for (embark/disembark)
DESTINATION_CITIES = [
    ("Miami", "US"),
    ("Fort Lauderdale", "US"),
    ("Barcelona", "ES"),
    ("Rome", "IT"),
    ("Amsterdam", "NL"),
    ("Lisbon", "PT"),
]

PORTAL_URL = "https://app.bedsonline.com"


def _load_creds() -> dict:
    if CREDS_PATH.exists():
        try:
            return json.loads(CREDS_PATH.read_text())
        except Exception as e:
            logger.warning("bedsonline: creds read error: %s", e)
    return {}


async def _login_and_scrape(username: str, password: str) -> dict:
    """Login to Bedsonline portal and scrape hotel availability/rates."""
    from playwright.async_api import async_playwright

    output = {"authenticated": False, "hotels": []}

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
        )
        page = await ctx.new_page()
        try:
            await page.goto(PORTAL_URL, wait_until="domcontentloaded", timeout=30_000)
            await page.wait_for_timeout(2_000)

            # Dismiss cookie consent banner if present (blocks form access).
            # Use JS evaluate — query_selector() doesn't support :has-text() pseudo-selectors.
            try:
                clicked = await page.evaluate("""
                    () => {
                        const labels = ['Allow all', 'Accept all', 'Allow selection', 'Accept'];
                        const btns = Array.from(document.querySelectorAll('button'));
                        for (const label of labels) {
                            const btn = btns.find(b => b.textContent.trim() === label);
                            if (btn) { btn.click(); return label; }
                        }
                        return null;
                    }
                """)
                if clicked:
                    await page.wait_for_timeout(1_500)
                    logger.debug("bedsonline: dismissed cookie banner ('%s')", clicked)
            except Exception as e:
                logger.debug("bedsonline: cookie dismiss skipped: %s", e)

            current_url = page.url
            logger.debug("bedsonline: landed on %s", current_url)

            # Check if already authenticated (dashboard visible)
            page_text = await page.inner_text("body")
            if any(kw in page_text.lower() for kw in ("search hotels", "my bookings", "dashboard")):
                output["authenticated"] = True
                logger.info("bedsonline: already authenticated ✓")
            else:
                await page.wait_for_timeout(1_000)
                # Use locator API for React-controlled inputs (supports triple_click + type)
                user_loc = page.locator("input[placeholder='Username']").first
                pass_loc = page.locator("input[placeholder='Password']").first

                user_visible = await user_loc.is_visible()
                pass_visible = await pass_loc.is_visible()

                if user_visible and pass_visible:
                    # click to focus, press_sequentially triggers React onChange on each keystroke
                    await user_loc.click()
                    await page.keyboard.press("Control+a")
                    await user_loc.press_sequentially(username, delay=50)
                    await page.wait_for_timeout(300)
                    await pass_loc.click()
                    await page.keyboard.press("Control+a")
                    await pass_loc.press_sequentially(password, delay=50)
                    await page.wait_for_timeout(500)

                    login_btn = page.get_by_role("button", name="Login")
                    if await login_btn.is_visible():
                        await login_btn.click()
                    else:
                        await page.keyboard.press("Enter")

                    await page.wait_for_timeout(4_000)
                    await page.wait_for_load_state("domcontentloaded")

                    post_url = page.url
                    post_text = await page.inner_text("body")

                    auth_urls = ("/main", "/dashboard", "/hotel-search", "/home")
                    auth_kws = ("search hotels", "my bookings", "dashboard", "top picks", "our top picks")
                    if any(post_url.endswith(u) or u in post_url for u in auth_urls):
                        output["authenticated"] = True
                        logger.info("bedsonline: login successful ✓ (url=%s)", post_url)
                    elif any(kw in post_text.lower() for kw in auth_kws):
                        output["authenticated"] = True
                        logger.info("bedsonline: login successful ✓ (content match)")
                    elif "error" in post_text.lower() or "invalid" in post_text.lower():
                        logger.warning("bedsonline: login error — credentials may be wrong")
                    elif "login" in post_url.lower():
                        logger.warning("bedsonline: login failed (still on login page)")
                    else:
                        # Ambiguous — try to navigate to search
                        try:
                            await page.goto(f"{PORTAL_URL}/hotel-search", wait_until="domcontentloaded", timeout=15_000)
                            await page.wait_for_timeout(2_000)
                            nav_text = await page.inner_text("body")
                            if "login" not in page.url.lower() and "error" not in nav_text.lower():
                                output["authenticated"] = True
                                logger.info("bedsonline: authenticated (navigation test) ✓")
                        except Exception:
                            pass
                else:
                    logger.warning("bedsonline: login form not found on %s", page.url)
                    # Try common login paths
                    for login_path in ["/login", "/auth/login", "/user/login"]:
                        try:
                            await page.goto(PORTAL_URL + login_path,
                                            wait_until="domcontentloaded", timeout=15_000)
                            await page.wait_for_timeout(1_500)
                            user_el2 = await page.query_selector("input[type='text'], input[name='username']")
                            pass_el2 = await page.query_selector("input[type='password']")
                            if user_el2 and pass_el2:
                                logger.info("bedsonline: found login form at %s", login_path)
                                await user_el2.fill(username)
                                await pass_el2.fill(password)
                                await page.keyboard.press("Enter")
                                await page.wait_for_timeout(4_000)
                                if "login" not in page.url.lower():
                                    output["authenticated"] = True
                                    logger.info("bedsonline: login via %s ✓", login_path)
                                break
                        except Exception:
                            continue

            # If authenticated, scrape hotel listings for key cities
            if output["authenticated"]:
                for city, country in DESTINATION_CITIES[:3]:  # limit to 3 cities per run
                    try:
                        hotels = await _scrape_city_hotels(page, city, country)
                        output["hotels"].extend(hotels)
                        logger.debug("bedsonline/%s: %d hotels", city, len(hotels))
                    except Exception as e:
                        logger.debug("bedsonline/%s: scrape error: %s", city, e)

        except Exception as e:
            logger.warning("bedsonline: playwright error: %s", e)
        finally:
            await page.close()
            await browser.close()

    return output


async def _scrape_city_hotels(page, city: str, country: str) -> list[dict]:
    """Attempt to pull hotel listings for a given city from the current session."""
    hotels = []

    # Try navigating to search with city pre-filled
    search_url = (
        f"{PORTAL_URL}/hotel-search?destination={city.replace(' ', '+')}&country={country}"
    )
    try:
        await page.goto(search_url, wait_until="domcontentloaded", timeout=20_000)
        await page.wait_for_timeout(3_000)
    except Exception:
        return hotels

    # Multi-selector hotel card extraction
    card_selectors = [
        ".hotel-card", "[class*='hotel-item']", "[class*='property-card']",
        "[class*='result-item']", "article[class*='hotel']",
    ]
    cards = []
    for sel in card_selectors:
        cards = await page.query_selector_all(sel)
        if cards:
            break

    # Fallback: JSON-LD
    if not cards:
        import json as _json
        scripts = await page.query_selector_all("script[type='application/ld+json']")
        for script in scripts:
            try:
                data = _json.loads(await script.inner_text())
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if item.get("@type") in ("Hotel", "LodgingBusiness"):
                        hotels.append({
                            "city": city,
                            "name": item.get("name", ""),
                            "price_from": 0,
                            "rating": item.get("starRating", {}).get("ratingValue", ""),
                            "url": item.get("url", ""),
                        })
            except Exception:
                pass
        return hotels[:10]

    now_str = datetime.now(timezone.utc).isoformat()
    for card in cards[:15]:
        try:
            name_el = (
                await card.query_selector("[class*='name'], [class*='title'], h3, h2")
            )
            price_el = (
                await card.query_selector("[class*='price'], [class*='rate'], [class*='cost']")
            )
            stars_el = (
                await card.query_selector("[class*='star'], [class*='rating']")
            )

            name = (await name_el.inner_text()).strip() if name_el else ""
            price_text = (await price_el.inner_text()).strip() if price_el else ""
            stars_text = (await stars_el.inner_text()).strip() if stars_el else ""

            if not name:
                continue

            # Parse price
            import re
            price_m = re.search(r"[\$€£]?\s*([\d,]+(?:\.\d{1,2})?)", price_text)
            price = float(price_m.group(1).replace(",", "")) if price_m else 0.0

            hotels.append({
                "city": city,
                "country": country,
                "name": name,
                "price_from": price,
                "stars": stars_text,
                "scraped_at": now_str,
            })
        except Exception:
            continue

    return hotels


def ingest_bedsonline(con: sqlite3.Connection, upsert_rows, log_run, ttl: int) -> None:
    t0 = time.monotonic()

    try:
        import asyncio
        from playwright.async_api import async_playwright  # noqa: F401
    except ImportError as e:
        logger.error("bedsonline: playwright not installed: %s", e)
        log_run(con, "bedsonline", "import_error", error=str(e))
        return

    creds = _load_creds()
    username = creds.get("portal_username", "")
    password = creds.get("portal_password", "")

    if not username or not password:
        logger.warning("bedsonline: no credentials found in %s", CREDS_PATH)
        log_run(con, "bedsonline", "no_credentials",
                error=f"Missing portal_username or portal_password in {CREDS_PATH}")
        return

    try:
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(_login_and_scrape(username, password))
        loop.close()
    except Exception as e:
        elapsed = time.monotonic() - t0
        logger.error("bedsonline: error: %s", e)
        log_run(con, "bedsonline", "playwright_error", elapsed=elapsed, error=str(e))
        return

    elapsed = time.monotonic() - t0
    now = datetime.now(timezone.utc).isoformat()

    # Session health row
    health_row = {
        "id": "bedsonline_session_health",
        "authenticated": result["authenticated"],
        "checked_at": now,
        "note": "Login successful" if result["authenticated"] else "Login failed",
    }
    upsert_rows(con, "bedsonline", "session_health", [health_row], ttl,
                provenance=PORTAL_URL)
    log_run(con, "bedsonline", "session_health_check",
            rows_in=1, rows_out=1, elapsed=elapsed,
            error="" if result["authenticated"] else "login_failed")

    if result["hotels"]:
        hotel_rows = []
        for i, h in enumerate(result["hotels"]):
            hotel_rows.append({
                "id": f"bedsonline_{h.get('city', 'city').replace(' ', '_').lower()}_{i}",
                "scraped_at": now,
                **h,
            })
        n = upsert_rows(con, "bedsonline", "hotel_rates", hotel_rows, ttl,
                        provenance=PORTAL_URL)
        log_run(con, "bedsonline", "rates_refresh", rows_in=n, rows_out=n, elapsed=elapsed)
        logger.info("bedsonline/hotel_rates: %d rows in %.1fs", n, elapsed)
    elif result["authenticated"]:
        log_run(con, "bedsonline", "no_hotels", rows_in=0, rows_out=0, elapsed=elapsed,
                error="Authenticated but no hotel rows scraped — page structure may have changed")
        logger.warning("bedsonline: authenticated but 0 hotel rows (%.1fs)", elapsed)
    else:
        logger.warning("bedsonline: login failed — check credentials in %s", CREDS_PATH)
