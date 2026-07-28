#!/usr/bin/env python3
"""
Airline Scraper Test — DEN → HNL, 2 Passengers, All Cabin Classes
================================================================
Scrapers: Skiplagged + Kayak + Expedia + CheapTickets + Centrav
Route: Denver (DEN) → Honolulu (HNL)
Pax: 2 adults
Classes: Economy, Premium Economy, Business/First
Date: ~3 weeks out (configurable)

Usage:
    python3 test_airline_scrapers.py
    python3 test_airline_scrapers.py --date 2026-05-15
    python3 test_airline_scrapers.py --headless false
    python3 test_airline_scrapers.py --source skiplagged
    python3 test_airline_scrapers.py --source kayak
    python3 test_airline_scrapers.py --source expedia
    python3 test_airline_scrapers.py --source cheaptickets
    python3 test_airline_scrapers.py --source centrav
"""

import asyncio
import argparse
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from playwright.async_api import async_playwright, Page, BrowserContext

# ── Config ──────────────────────────────────────────────────────────────────

ORIGIN = "COS"
DEST = "MSN"
ADULTS = 2
DEFAULT_DEPART = "2026-09-07"

# Centrav agent credentials (B2B portal — agent account only)
import json
from pathlib import Path

CREDS_PATH = Path.home() / "Thunderbird" / "centrav_credentials.json"
if CREDS_PATH.exists():
    creds = json.loads(CREDS_PATH.read_text())
    CENTRAV_EMAIL = creds["email"]
    CENTRAV_PASS = creds["password"]
    CENTRAV_COOKIES = creds.get("cookies", {})
else:
    CENTRAV_EMAIL = "johnloucks3@gmail.com"
    CENTRAV_PASS = "Falcons4me!"
    CENTRAV_COOKIES = {}

OUTPUT_DIR = Path(__file__).parent.parent / "core" / "travel" / "data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def log(msg: str):
    print(f"[{_ts()}] {msg}", flush=True)


def _parse_lowest(prices: list, lo: float = 50, hi: float = 20_000) -> float | None:
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


def _sanity_check(cabin: str, price_pp: float | None, ref: dict[str, float | None]) -> str:
    """Flag obviously wrong prices (e.g. premium < economy)."""
    if price_pp is None:
        return "n/a"
    eco = ref.get("economy")
    prem = ref.get("premium")
    if cabin == "premium" and eco and price_pp < eco * 0.85:
        return f"${price_pp:,.2f} ⚠ suspect"
    if cabin == "first" and prem and price_pp < prem * 0.85:
        return f"${price_pp:,.2f} ⚠ suspect"
    return f"${price_pp:,.2f}"


# ── Skiplagged Scraper ────────────────────────────────────────────────────────

async def scrape_skiplagged(
    page: Page,
    origin: str,
    dest: str,
    depart_date: str,
    adults: int,
    cabin: str,
) -> dict:
    """Scrape Skiplagged for one-way fares.

    Note: cabin filter is client-side UI — all cabins show economy inventory.
    Best for: hidden-city economy lowest-price floor.
    """
    cabin_sl = {"economy": "economy", "premium": "premium", "first": "business"}.get(cabin, "economy")
    url = (
        f"https://skiplagged.com/flights/{origin}/{dest}/{depart_date}"
        f"?adults={adults}&cabin={cabin_sl}"
    )
    log(f"  Skiplagged [{cabin}] → {url}")

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=45_000)
        try:
            await page.wait_for_selector(
                "[class*='trip-summary'], [data-testid*='trip'], .trip, [class*='flight-row']",
                timeout=25_000,
            )
        except Exception:
            log(f"  Skiplagged [{cabin}] — no flight cards, trying price extraction")

        await page.wait_for_timeout(3_000)

        raw_text = await page.evaluate("""() => {
            const prices = [];
            const selectors = ['[class*="price"]','[class*="cost"]','[class*="fare"]','[class*="amount"]','strong'];
            for (const sel of selectors) {
                document.querySelectorAll(sel).forEach(el => {
                    const t = el.innerText || el.textContent || '';
                    if (t.includes('$') && /\\$[\\d,]+/.test(t)) {
                        prices.push(t.trim().split('\\n')[0]);
                    }
                });
                if (prices.length > 0) break;
            }
            return prices.slice(0, 20);
        }""")

        airlines = await page.evaluate("""() => {
            const names = [];
            const selectors = ['[class*="airline"]','[class*="carrier"]','[class*="operator"]'];
            for (const sel of selectors) {
                document.querySelectorAll(sel).forEach(el => {
                    const t = (el.innerText || el.textContent || '').trim();
                    if (t && t.length < 60) names.push(t);
                });
                if (names.length > 0) break;
            }
            return [...new Set(names)].slice(0, 10);
        }""")

        lowest_price = _parse_lowest(raw_text)
        screenshot_path = OUTPUT_DIR / f"skiplagged_{cabin}_{depart_date}.png"
        await page.screenshot(path=str(screenshot_path), full_page=False)

        return {
            "source": "skiplagged",
            "cabin": cabin,
            "url": url,
            "adults": adults,
            "depart_date": depart_date,
            "raw_prices": raw_text[:10],
            "lowest_price_pp": lowest_price,
            "total_lowest": round(lowest_price * adults, 2) if lowest_price else None,
            "airlines_found": airlines[:8],
            "screenshot": str(screenshot_path),
            "status": "ok" if raw_text else "no_prices_found",
        }

    except Exception as e:
        log(f"  Skiplagged [{cabin}] ERROR: {e}")
        return {"source": "skiplagged", "cabin": cabin, "url": url, "status": "error", "error": str(e)}


# ── Kayak Scraper ─────────────────────────────────────────────────────────────

async def scrape_kayak(
    page: Page,
    origin: str,
    dest: str,
    depart_date: str,
    adults: int,
    cabin: str,
) -> dict:
    """Scrape Kayak for one-way fares.

    URL: kayak.com/flights/{O}-{D}/{DATE}/{N}adults?sort=price_a&fs=cabin={c}
    cabin codes: e=economy, pe=premium economy, b=business
    Prices extracted only from within result cards (avoids UI element false reads).
    """
    cabin_kk = {"economy": "e", "premium": "pe", "first": "b"}.get(cabin, "e")
    url = (
        f"https://www.kayak.com/flights/{origin}-{dest}/{depart_date}/{adults}adults"
        f"?sort=price_a&fs=cabin={cabin_kk}"
    )
    log(f"  Kayak [{cabin}] → {url}")

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=50_000)

        for sel in ["#onetrust-accept-btn-handler", "button[data-testid='accept-cookies']",
                    "button:has-text('Accept all')", "button:has-text('I Accept')"]:
            try:
                await page.click(sel, timeout=4_000)
                await page.wait_for_timeout(500)
                break
            except Exception:
                pass

        try:
            await page.wait_for_selector(
                "[class*='price-text'], [class*='above-the-fold'], [data-resultid], [class*='resultInner']",
                timeout=35_000,
            )
        except Exception:
            log(f"  Kayak [{cabin}] — extended wait...")
            await page.wait_for_timeout(12_000)

        await page.wait_for_timeout(2_000)

        # Dismiss modal popups that cover results (Kayak frequently shows upsell modals)
        for close_sel in [
            "button.close", "button[aria-label='Close']", "[class*='dialog'] button:has-text('×')",
            "[class*='modal'] [class*='close']", "button:has-text('✕')",
        ]:
            try:
                await page.click(close_sel, timeout=1_500)
                await page.wait_for_timeout(400)
            except Exception:
                pass

        # Extract prices ONLY from within result card containers to avoid UI artifacts
        raw_prices = await page.evaluate("""() => {
            const prices = [];
            // Try to find result cards first (more targeted)
            const cardSelectors = ['[data-resultid]', '[class*="resultInner"]', '[class*="above-the-fold"]'];
            let cards = [];
            for (const sel of cardSelectors) {
                cards = Array.from(document.querySelectorAll(sel));
                if (cards.length > 0) break;
            }
            const scope = cards.length > 0 ? cards : [document.body];
            for (const card of scope.slice(0, 10)) {
                card.querySelectorAll('[class*="price-text"], [class*="price"]').forEach(el => {
                    const t = (el.innerText || el.textContent || '').trim();
                    if (/^\\$[\\d,]+$/.test(t)) prices.push(t);
                });
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

        airlines = await page.evaluate("""() => {
            const names = [];
            document.querySelectorAll('[class*="carrier-name"], [class*="airline-name"], [class*="operatedBy"]').forEach(el => {
                const t = (el.innerText || el.textContent || '').trim();
                if (t && t.length < 60 && !t.includes('$')) names.push(t);
            });
            return [...new Set(names)].slice(0, 10);
        }""")

        if not raw_prices:
            page_text = await page.inner_text("body")
            matches = re.findall(r'\$[\d,]+', page_text)
            raw_prices = list(dict.fromkeys(matches))[:15]

        lowest_price = _parse_lowest(raw_prices, lo=50, hi=15_000)
        screenshot_path = OUTPUT_DIR / f"kayak_{cabin}_{depart_date}.png"
        await page.screenshot(path=str(screenshot_path), full_page=False)

        return {
            "source": "kayak",
            "cabin": cabin,
            "url": url,
            "adults": adults,
            "depart_date": depart_date,
            "raw_prices": raw_prices[:10],
            "lowest_price_pp": round(lowest_price / adults, 2) if lowest_price else None,
            "total_lowest": lowest_price,
            "airlines_found": airlines[:8],
            "screenshot": str(screenshot_path),
            "status": "ok" if raw_prices else "no_prices_found",
        }

    except Exception as e:
        log(f"  Kayak [{cabin}] ERROR: {e}")
        return {"source": "kayak", "cabin": cabin, "url": url, "status": "error", "error": str(e)}


# ── Google Flights Scraper ────────────────────────────────────────────────────

async def scrape_expedia(
    page: Page,
    origin: str,
    dest: str,
    depart_date: str,
    adults: int,
    cabin: str,
) -> dict:
    """Scrape Expedia for one-way fares (replaces Google Flights).

    Expedia uses a URL-based search format with explicit cabin class — no form-fill needed.
    URL: expedia.com/Flights-Search?trip=oneway&leg1=from:O,to:D,departure:MM/DD/YYYYTANYT
         &passengers=adults:N&options=cabinclass:economy&mode=search

    cabin values: economy / premiumeconomy / business / first
    """
    cabin_ex = {
        "economy": "economy",
        "premium": "premiumeconomy",
        "first": "business",
    }.get(cabin, "economy")

    dt = datetime.strptime(depart_date, "%Y-%m-%d")
    ex_date = dt.strftime("%m/%d/%Y")  # MM/DD/YYYY

    url = (
        f"https://www.expedia.com/Flights-Search?trip=oneway"
        f"&leg1=from%3A{origin}%2Cto%3A{dest}%2Cdeparture%3A{ex_date}TANYT"
        f"&passengers=adults%3A{adults}%2Cchildren%3A0"
        f"&options=cabinclass%3A{cabin_ex}&mode=search"
    )
    log(f"  Expedia [{cabin}] → {url}")

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=55_000)

        # Dismiss cookie/consent banners
        for sel in [
            "#onetrust-accept-btn-handler",
            "button[data-stid='accept-cookies']",
            "button:has-text('Accept')",
            "button:has-text('I Accept')",
        ]:
            try:
                await page.click(sel, timeout=4_000)
                await page.wait_for_timeout(500)
                break
            except Exception:
                pass

        # Wait for result cards
        try:
            await page.wait_for_selector(
                "[data-test-id='offer-listing'], [class*='uitk-card'], "
                "[class*='flight-module'], [class*='listing-container']",
                timeout=40_000,
            )
        except Exception:
            log(f"  Expedia [{cabin}] — extended wait...")
            await page.wait_for_timeout(15_000)

        await page.wait_for_timeout(2_000)

        raw_prices = await page.evaluate("""() => {
            const prices = [];
            // Expedia price elements
            const selectors = [
                '[data-test-id="price-summary"]',
                '[class*="price-lockup"]',
                '[class*="uitk-lockup-price"]',
                '[class*="price-column"]',
                '[class*="total-price"]',
            ];
            for (const sel of selectors) {
                document.querySelectorAll(sel).forEach(el => {
                    const t = (el.innerText || el.textContent || '').trim();
                    const m = t.match(/^\\$[\\d,]+/);
                    if (m) prices.push(m[0]);
                });
                if (prices.length > 3) break;
            }
            // Fallback: any $NNN+ text in the results area
            if (prices.length === 0) {
                document.querySelectorAll('[class*="result"], [class*="listing"]').forEach(el => {
                    const t = (el.innerText || el.textContent || '').trim();
                    const matches = t.match(/\\$[\\d,]+/g) || [];
                    prices.push(...matches);
                });
            }
            return [...new Set(prices)].slice(0, 20);
        }""")

        airlines = await page.evaluate("""() => {
            const names = [];
            document.querySelectorAll(
                '[data-test-id="airline-name"], [class*="carrier-name"], [class*="airline"]'
            ).forEach(el => {
                const t = (el.innerText || el.textContent || '').trim();
                if (t && t.length < 60 && !t.includes('$')) names.push(t);
            });
            return [...new Set(names)].slice(0, 10);
        }""")

        if not raw_prices:
            page_text = await page.inner_text("body")
            matches = re.findall(r'\$[\d,]+', page_text)
            raw_prices = list(dict.fromkeys(
                m for m in matches if 50 < int(m.replace('$', '').replace(',', '')) < 25_000
            ))[:15]

        lowest_price = _parse_lowest(raw_prices, lo=50, hi=25_000)
        screenshot_path = OUTPUT_DIR / f"expedia_{cabin}_{depart_date}.png"
        await page.screenshot(path=str(screenshot_path), full_page=False)

        return {
            "source": "expedia",
            "cabin": cabin,
            "url": url,
            "adults": adults,
            "depart_date": depart_date,
            "raw_prices": raw_prices[:10],
            "lowest_price_pp": round(lowest_price / adults, 2) if lowest_price else None,
            "total_lowest": lowest_price,
            "airlines_found": airlines[:8],
            "screenshot": str(screenshot_path),
            "status": "ok" if raw_prices else "no_prices_found",
        }

    except Exception as e:
        log(f"  Expedia [{cabin}] ERROR: {e}")
        return {"source": "expedia", "cabin": cabin, "url": url, "status": "error", "error": str(e)}


# ── CheapTickets Scraper ──────────────────────────────────────────────────────

async def scrape_cheaptickets(
    page: Page,
    origin: str,
    dest: str,
    depart_date: str,
    adults: int,
    cabin: str,
) -> dict:
    """Scrape CheapTickets for one-way fares.

    CheapTickets (Booking Holdings / Orbitz family) uses URL-based search.
    URL: cheaptickets.com/Flights/OneWay?departureAirport=X&arrivalAirport=Y&
         departureDate=YYYY-MM-DD&adults=N&cabinClass={class}
    cabin values: Economy, PremiumEconomy, Business, First
    """
    cabin_ct = {
        "economy": "Economy",
        "premium": "PremiumEconomy",
        "first": "Business",
    }.get(cabin, "Economy")

    url = (
        f"https://www.cheaptickets.com/Flights/OneWay"
        f"?departureAirport={origin}&arrivalAirport={dest}"
        f"&departureDate={depart_date}&adults={adults}&cabinClass={cabin_ct}"
    )
    log(f"  CheapTickets [{cabin}] → {url}")

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=50_000)

        for sel in ["#onetrust-accept-btn-handler", "button[data-stid='accept-cookies']",
                    "button:has-text('Accept')"]:
            try:
                await page.click(sel, timeout=4_000)
                await page.wait_for_timeout(500)
                break
            except Exception:
                pass

        try:
            await page.wait_for_selector(
                "[data-test-id='offer-listing'], [class*='uitk-card'], [class*='price-lockup']",
                timeout=35_000,
            )
        except Exception:
            log(f"  CheapTickets [{cabin}] — extended wait...")
            await page.wait_for_timeout(12_000)

        await page.wait_for_timeout(2_000)

        raw_prices = await page.evaluate("""() => {
            const prices = [];
            const selectors = [
                '[data-test-id="price-summary"]',
                '[class*="price-lockup"]',
                '[class*="uitk-lockup-price"]',
                '[class*="price"]',
            ];
            for (const sel of selectors) {
                document.querySelectorAll(sel).forEach(el => {
                    const t = (el.innerText || el.textContent || '').trim();
                    if (/^\\$[\\d,]+/.test(t)) prices.push(t.split('\\n')[0].trim());
                });
                if (prices.length > 3) break;
            }
            return [...new Set(prices)].slice(0, 20);
        }""")

        airlines = await page.evaluate("""() => {
            const names = [];
            document.querySelectorAll('[data-test-id="airline-name"], [class*="carrier"]').forEach(el => {
                const t = (el.innerText || el.textContent || '').trim();
                if (t && t.length < 60 && !t.includes('$')) names.push(t);
            });
            return [...new Set(names)].slice(0, 10);
        }""")

        if not raw_prices:
            page_text = await page.inner_text("body")
            matches = re.findall(r'\$[\d,]+', page_text)
            raw_prices = list(dict.fromkeys(matches))[:15]

        lowest_price = _parse_lowest(raw_prices, lo=50, hi=20_000)
        screenshot_path = OUTPUT_DIR / f"cheaptickets_{cabin}_{depart_date}.png"
        await page.screenshot(path=str(screenshot_path), full_page=False)

        return {
            "source": "cheaptickets",
            "cabin": cabin,
            "url": url,
            "adults": adults,
            "depart_date": depart_date,
            "raw_prices": raw_prices[:10],
            "lowest_price_pp": round(lowest_price / adults, 2) if lowest_price else None,
            "total_lowest": lowest_price,
            "airlines_found": airlines[:8],
            "screenshot": str(screenshot_path),
            "status": "ok" if raw_prices else "no_prices_found",
        }

    except Exception as e:
        log(f"  CheapTickets [{cabin}] ERROR: {e}")
        return {"source": "cheaptickets", "cabin": cabin, "url": url, "status": "error", "error": str(e)}


# ── Centrav Scraper (B2B Agent Portal) ───────────────────────────────────────
#
# Centrav login uses Google reCAPTCHA v2 (image challenge), which blocks
# fully-headless automation. Strategy:
#   1. Fast path: load saved session cookies → skip login entirely
#   2. Slow path: launch visible browser, pre-fill creds, pause for human
#      to solve CAPTCHA, then auto-continue with search & extraction
#
# Run once with --centrav-login to create the session file, then all
# subsequent --source centrav runs use the cookie cache silently.

CENTRAV_SESSION_FILE = OUTPUT_DIR / "centrav_session.json"


async def _centrav_check_session(page: Page) -> bool:
    """Return True if saved cookies produce a valid authenticated session."""
    if not CENTRAV_SESSION_FILE.exists():
        return False
    try:
        cookies = json.loads(CENTRAV_SESSION_FILE.read_text())
        await page.context.add_cookies(cookies)
        await page.goto("https://www.centrav.com/", wait_until="domcontentloaded", timeout=20_000)
        await page.wait_for_timeout(2_000)
        # Authenticated pages contain logout button; login page does not
        logout = await page.query_selector("#LogoutButton")
        if logout:
            log("  Centrav — session cookie valid ✓")
            return True
        log("  Centrav — session cookie expired, need re-login")
        return False
    except Exception as e:
        log(f"  Centrav — session check error: {e}")
        return False


async def _centrav_interactive_login(context, headless: bool) -> bool:
    """Open a visible browser, pre-fill credentials, wait for human CAPTCHA solve.

    Returns True on success and saves cookies to CENTRAV_SESSION_FILE.
    """
    if headless:
        log("  Centrav — CAPTCHA required. Re-run with --headless false to solve interactively.")
        log("  Centrav — OR: python3 test_airline_scrapers.py --centrav-login (visible browser)")
        return False

    log("  Centrav — launching visible browser for CAPTCHA solve...")
    page = await context.new_page()
    await page.goto("https://www.centrav.com/login", wait_until="domcontentloaded", timeout=30_000)
    await page.wait_for_timeout(1_500)

    # Pre-fill credentials so user only needs to solve CAPTCHA + click Login
    try:
        await page.fill("#FormEmail", CENTRAV_EMAIL, timeout=5_000)
        await page.fill("#FormPassword", CENTRAV_PASS, timeout=5_000)
        log("  Centrav — credentials pre-filled. Solve the CAPTCHA in the browser window,")
        log("  Centrav — then click Login. Waiting up to 120s...")
    except Exception as e:
        log(f"  Centrav — could not pre-fill: {e}. Fill manually and click Login.")

    # Poll until redirected away from login page (max 120s)
    for _ in range(60):
        await page.wait_for_timeout(2_000)
        if "login" not in page.url.lower():
            break
    else:
        log("  Centrav — timed out waiting for login.")
        await page.close()
        return False

    log(f"  Centrav — login successful, URL: {page.url}")

    # Save cookies
    cookies = await context.cookies()
    CENTRAV_SESSION_FILE.write_text(json.dumps(cookies, indent=2))
    log(f"  Centrav — session saved → {CENTRAV_SESSION_FILE}")
    await page.close()
    return True


async def _centrav_search_and_extract(
    page: Page,
    origin: str,
    dest: str,
    depart_date: str,
    adults: int,
    cabin: str,
    cabin_cv: str,
) -> dict:
    """Fill Centrav homepage search form and extract prices from results."""

    # Cabin label mapping: homepage tab text
    cabin_tab = {
        "economy": "Economy",
        "premium": "Premium Economy",
        "first": "Business",
    }.get(cabin, "Economy")

    # Date format: MM/DD/YYYY
    dt = datetime.strptime(depart_date, "%Y-%m-%d")
    date_str = dt.strftime("%m/%d/%Y")

    screenshot_path = OUTPUT_DIR / f"centrav_search_{cabin}_{depart_date}.png"

    try:
        # Cabin class value mapping for hidden CabinClassInput
        cabin_val = {
            "economy": "ECONOMY",
            "premium": "PREMIUM_ECONOMY",
            "first": "BUSINESS",
        }.get(cabin, "ECONOMY")

        # ── Load homepage (search form is here) ──────────────────────────────
        await page.goto("https://www.centrav.com/", wait_until="domcontentloaded", timeout=30_000)
        await page.wait_for_timeout(2_000)
        log(f"  Centrav [{cabin}] — homepage loaded: {page.url}")

        # ── Set hidden inputs directly (trip type + cabin class) ─────────────
        # NOTE: still hardcoded one-way (diagnostic script, not wired to any
        # fare watch). The production path — core/travel/thunderbird_
        # centrav_search.py::run_centrav_search — now supports
        # trip_type="roundtrip"; port that fix here if this script is ever
        # promoted beyond ad hoc diagnostics.
        await page.evaluate(f"""() => {{
            const tripInput = document.getElementById('FareTripTypeInput');
            if (tripInput) tripInput.value = 'OneWay';
            const cabinInput = document.getElementById('CabinClassInput');
            if (cabinInput) cabinInput.value = '{cabin_val}';
        }}""")
        # Also click the One Way and cabin buttons to update visible UI state
        await page.click("text='One Way'")
        await page.wait_for_timeout(300)
        await page.click(f"text='{cabin_tab}'")
        await page.wait_for_timeout(300)

        # ── Flying From — type slowly to trigger autocomplete ────────────────
        await page.click("#FareFlyingFrom")
        await page.fill("#FareFlyingFrom", "")
        await page.type("#FareFlyingFrom", origin, delay=80)
        await page.wait_for_timeout(1_800)
        # Filter by origin code text so we don't pick a hidden dropdown from a prior field
        try:
            await page.locator(".tt-suggestion").filter(has_text=origin).first.click(timeout=5_000)
            log(f"  Centrav [{cabin}] — Flying From selected via dropdown")
        except Exception:
            try:
                await page.locator(".tt-suggestion").first.click(timeout=3_000)
                log(f"  Centrav [{cabin}] — Flying From selected (first suggestion)")
            except Exception:
                await page.keyboard.press("ArrowDown")
                await page.keyboard.press("Enter")
                log(f"  Centrav [{cabin}] — Flying From selected via keyboard")
        await page.wait_for_timeout(500)

        # ── Flying To — same approach ────────────────────────────────────────
        await page.click("#FareFlyingTo")
        await page.fill("#FareFlyingTo", "")
        await page.type("#FareFlyingTo", dest, delay=80)
        await page.wait_for_timeout(1_800)
        # Filter by dest code so we don't pick the now-hidden Flying From dropdown
        try:
            await page.locator(".tt-suggestion").filter(has_text=dest).first.click(timeout=5_000)
            log(f"  Centrav [{cabin}] — Flying To selected via dropdown")
        except Exception:
            try:
                # Grab visible suggestions only — Flying From dropdown is now hidden
                visible_sug = page.locator(".tt-suggestion").filter(visible=True).first
                await visible_sug.click(timeout=3_000)
                log(f"  Centrav [{cabin}] — Flying To selected (visible suggestion)")
            except Exception:
                await page.keyboard.press("ArrowDown")
                await page.keyboard.press("Enter")
                log(f"  Centrav [{cabin}] — Flying To selected via keyboard")
        await page.wait_for_timeout(500)

        # ── Departure Date ───────────────────────────────────────────────────
        await page.click("#FareDepartureDate")
        await page.fill("#FareDepartureDate", date_str)
        await page.keyboard.press("Tab")
        await page.wait_for_timeout(400)

        # ── Adults ───────────────────────────────────────────────────────────
        await page.select_option("#Adults", str(adults))
        await page.wait_for_timeout(300)

        # ── Screenshot before submit ─────────────────────────────────────────
        pre_path = OUTPUT_DIR / f"centrav_preflight_{cabin}_{depart_date}.png"
        await page.screenshot(path=str(pre_path))
        log(f"  Centrav [{cabin}] — form filled, submitting...")

        # ── Submit ───────────────────────────────────────────────────────────
        await page.click("button:has-text('SEARCH FOR FARES')")

        # ── Wait for results ─────────────────────────────────────────────────
        await page.wait_for_timeout(10_000)
        await page.screenshot(path=str(screenshot_path))
        log(f"  Centrav [{cabin}] — results page: {page.url}")

    except Exception as e:
        log(f"  Centrav [{cabin}] form-fill error: {e}")
        try:
            await page.screenshot(path=str(screenshot_path))
        except Exception:
            pass

    # ── Extract prices ────────────────────────────────────────────────────────
    # Regex was whole-dollar-only — could never match Centrav's actual
    # per-fare-card totals ("Published Fare $514.40"), which always carry
    # cents; only the coarser Fare Matrix summary cells (whole dollars) ever
    # matched. See hale_decisions.md 2026-07-09 Centrav scraper bug entry.
    raw_prices = await page.evaluate("""() => {
        const prices = [];
        const selectors = [
            '[class*="price"]', '[class*="fare"]', '[class*="amount"]',
            '[class*="cost"]', '[class*="total"]', 'td', 'span',
        ];
        for (const sel of selectors) {
            document.querySelectorAll(sel).forEach(el => {
                const t = (el.innerText || el.textContent || '').trim();
                const m = t.match(/^\\$[\\d,]+(?:\\.\\d{2})?$/);
                if (m) prices.push(m[0]);
            });
            if (prices.length > 3) break;
        }
        return [...new Set(prices)].slice(0, 20);
    }""")

    airlines = await page.evaluate("""() => {
        const SKIP = new Set(['only','nonstop','stops','stop','filters','all','any','sort','cabin','class','economy','premium','business','first']);
        const names = [];
        document.querySelectorAll('[class*="airline"], [class*="carrier"], [class*="Airline"], [class*="Carrier"]').forEach(el => {
            const t = (el.innerText || el.textContent || '').trim();
            if (t && t.length > 3 && t.length < 60 && !t.includes('$') && !t.match(/^\\d/)
                && !SKIP.has(t.toLowerCase())) {
                names.push(t);
            }
        });
        return [...new Set(names)].slice(0, 10);
    }""")

    if not raw_prices:
        page_text = await page.inner_text("body")
        matches = re.findall(r'\$[\d,]+', page_text)
        raw_prices = list(dict.fromkeys(
            m for m in matches if 50 < int(m.replace('$', '').replace(',', '')) < 20_000
        ))[:15]

    lowest_price = _parse_lowest(raw_prices, lo=50, hi=20_000)

    return {
        "source": "centrav",
        "cabin": cabin,
        "url": page.url,
        "adults": adults,
        "depart_date": depart_date,
        "raw_prices": raw_prices[:10],
        "lowest_price_pp": round(lowest_price / adults, 2) if lowest_price else None,
        "total_lowest": lowest_price,
        "airlines_found": airlines[:8],
        "screenshot": str(screenshot_path),
        "status": "ok" if raw_prices else "no_prices_found",
    }


async def scrape_centrav(
    page: Page,
    origin: str,
    dest: str,
    depart_date: str,
    adults: int,
    cabin: str,
    headless: bool = True,
) -> dict:
    """Scrape Centrav (B2B agent portal) for one-way fares.

    Authentication flow (reCAPTCHA on login page):
      - Fast path: reuse saved session cookies (CENTRAV_SESSION_FILE)
      - Slow path: visible browser, pre-fill creds, human solves CAPTCHA

    Run `python3 test_airline_scrapers.py --centrav-login --headless false`
    once to create the session file. All future runs use cookies silently.
    """
    cabin_cv = {
        "economy": "Economy",
        "premium": "Premium Economy",
        "first": "Business",
    }.get(cabin, "Economy")

    log(f"  Centrav [{cabin}] → checking session...")

    try:
        # Fast path: valid session cookie
        session_ok = await _centrav_check_session(page)

        if not session_ok:
            # Slow path: need human to solve CAPTCHA
            login_ok = await _centrav_interactive_login(page.context, headless=headless)
            if not login_ok:
                return {
                    "source": "centrav", "cabin": cabin,
                    "status": "captcha_required — run --centrav-login --headless false",
                    "url": "https://www.centrav.com/login",
                }
            # Reload page with fresh session
            await page.goto("https://www.centrav.com/", wait_until="domcontentloaded", timeout=20_000)

        return await _centrav_search_and_extract(page, origin, dest, depart_date, adults, cabin, cabin_cv)

    except Exception as e:
        log(f"  Centrav [{cabin}] ERROR: {e}")
        screenshot_path = OUTPUT_DIR / f"centrav_error_{cabin}_{depart_date}.png"
        try:
            await page.screenshot(path=str(screenshot_path))
        except Exception:
            screenshot_path = None
        return {
            "source": "centrav", "cabin": cabin, "status": "error", "error": str(e),
            "screenshot": str(screenshot_path) if screenshot_path else None,
        }


# ── Main ─────────────────────────────────────────────────────────────────────

SOURCES = ["skiplagged", "kayak", "expedia", "cheaptickets", "centrav"]

async def run_tests(depart_date: str, headless: bool = True, source: str = "all", browser_type: str = "firefox"):
    log(f"=== Airline Scraper Test: {ORIGIN} → {DEST} ===")
    log(f"Date: {depart_date}  |  Adults: {ADULTS}  |  Headless: {headless}  |  Source: {source}")
    log(f"Sources: Skiplagged · Kayak · Expedia · CheapTickets · Centrav")
    log(f"Cabins:  Economy · Premium Economy · Business/First")
    log("")

    cabins = ["economy", "premium", "first"]
    results = {
        "route": f"{ORIGIN}-{DEST}",
        "depart_date": depart_date,
        "adults": ADULTS,
        "scraped_at": datetime.now().isoformat(),
        "skiplagged": {},
        "kayak": {},
        "expedia": {},
        "cheaptickets": {},
        "centrav": {},
    }

    # Merge with existing JSON so partial --source runs don't wipe other sources
    out_file = OUTPUT_DIR / f"airline_test_{ORIGIN}_{DEST}_{depart_date}.json"
    if out_file.exists() and source != "all":
        try:
            existing = json.loads(out_file.read_text())
            for src_key in ["skiplagged", "kayak", "expedia", "cheaptickets", "centrav"]:
                if src_key != source and existing.get(src_key):
                    results[src_key] = existing[src_key]
            log(f"  Merged existing data from {out_file.name} (preserving non-{source} sources)")
        except Exception as e:
            log(f"  Warning: could not load existing JSON for merge: {e}")

    async with async_playwright() as p:
        _browser_engine = p.firefox if browser_type == "firefox" else p.chromium
        _launch_args = [] if browser_type == "firefox" else [
            "--no-sandbox",
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
        ]
        _user_agent = (
            "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0"
            if browser_type == "firefox"
            else "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                 "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        browser = await _browser_engine.launch(
            headless=headless,
            args=_launch_args,
        )
        context: BrowserContext = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent=_user_agent,
            java_script_enabled=True,
            locale="en-US",
        )

        def _want(s: str) -> bool:
            return source == "all" or source == s

        if _want("skiplagged"):
            log("── Skiplagged ─────────────────────────────────────")
            for cabin in cabins:
                page = await context.new_page()
                results["skiplagged"][cabin] = await scrape_skiplagged(
                    page, ORIGIN, DEST, depart_date, ADULTS, cabin)
                await page.close()

        if _want("kayak"):
            log("\n── Kayak ──────────────────────────────────────────")
            for cabin in cabins:
                page = await context.new_page()
                results["kayak"][cabin] = await scrape_kayak(
                    page, ORIGIN, DEST, depart_date, ADULTS, cabin)
                await page.close()
            # Kayak sanity gate: cabin filter leaks economy prices into premium/first rows.
            # If premium or first is cheaper than economy * 0.85, use economy as price floor.
            eco_kk = results["kayak"].get("economy", {}).get("lowest_price_pp")
            if eco_kk:
                for upper_cabin in ["premium", "first"]:
                    kk_data = results["kayak"].get(upper_cabin, {})
                    pp = kk_data.get("lowest_price_pp")
                    if pp and pp < eco_kk * 0.85:
                        log(f"  ⚠ Kayak {upper_cabin}: ${pp:.2f}/pp < economy ${eco_kk:.2f}/pp — cabin filter leaked. Flooring to economy.")
                        kk_data["lowest_price_pp"] = eco_kk
                        kk_data["total_lowest"] = round(eco_kk * ADULTS, 2)
                        kk_data["sanity_corrected"] = True

        if _want("expedia"):
            log("\n── Expedia ─────────────────────────────────────────")
            for cabin in cabins:
                page = await context.new_page()
                results["expedia"][cabin] = await scrape_expedia(
                    page, ORIGIN, DEST, depart_date, ADULTS, cabin)
                await page.close()

        if _want("cheaptickets"):
            log("\n── CheapTickets ───────────────────────────────────")
            for cabin in cabins:
                page = await context.new_page()
                results["cheaptickets"][cabin] = await scrape_cheaptickets(
                    page, ORIGIN, DEST, depart_date, ADULTS, cabin)
                await page.close()

        if _want("centrav"):
            log("\n── Centrav (B2B) ──────────────────────────────────")
            for cabin in cabins:
                page = await context.new_page()
                results["centrav"][cabin] = await scrape_centrav(
                    page, ORIGIN, DEST, depart_date, ADULTS, cabin, headless=headless)
                await page.close()

        await browser.close()

    # ── Summary Table ──
    log("\n" + "═" * 120)
    log(f"RESULTS: {ORIGIN} → {DEST}  |  {depart_date}  |  {ADULTS} adults")
    log("═" * 120)

    # Build per-source pp prices for sanity check
    def _pp(src_data: dict, cabin: str) -> float | None:
        return src_data.get(cabin, {}).get("lowest_price_pp")

    cabin_labels = {"economy": "Economy", "premium": "Premium Economy", "first": "First/Business"}

    fmt = "{:<18}  {:>14}  {:>12}  {:>15}  {:>14}  {:>12}"
    log(fmt.format("Cabin", "Skiplagged /pp", "Kayak /pp", "Expedia /pp", "CheapTkts /pp", "Centrav /pp"))
    log("-" * 95)

    for cabin in cabins:
        sl_pp  = _pp(results["skiplagged"], cabin)
        kk_pp  = _pp(results["kayak"], cabin)
        ex_pp  = _pp(results["expedia"], cabin)
        ct_pp  = _pp(results["cheaptickets"], cabin)
        cv_pp  = _pp(results["centrav"], cabin)

        def _disp(v: float | None) -> str:
            return f"${v:,.2f}" if v else "n/a"

        log(fmt.format(
            cabin_labels[cabin],
            _disp(sl_pp),
            _disp(kk_pp),
            _disp(ex_pp),
            _disp(ct_pp),
            _disp(cv_pp),
        ))

    log("")

    # Total cost row
    log(fmt.format("Cabin", "SL Total", "Kayak Total", "Expedia Total", "CT Total", "CV Total"))
    log("-" * 95)
    for cabin in cabins:
        def _tot(key: str) -> str:
            t = results[key].get(cabin, {}).get("total_lowest")
            return f"${t:,.2f}" if t else "n/a"
        log(fmt.format(
            cabin_labels[cabin],
            _tot("skiplagged"), _tot("kayak"), _tot("expedia"),
            _tot("cheaptickets"), _tot("centrav"),
        ))

    log("")

    # Status
    for cabin in cabins:
        sl = results["skiplagged"].get(cabin, {}).get("status", "—")
        kk = results["kayak"].get(cabin, {}).get("status", "—")
        ex = results["expedia"].get(cabin, {}).get("status", "—")
        ct = results["cheaptickets"].get(cabin, {}).get("status", "—")
        cv = results["centrav"].get(cabin, {}).get("status", "—")
        log(f"  {cabin_labels[cabin]}: SL={sl} KK={kk} EX={ex} CT={ct} CV={cv}")

    log("")

    # Airlines
    for cabin in cabins:
        al = (
            results["skiplagged"].get(cabin, {}).get("airlines_found", [])
            or results["kayak"].get(cabin, {}).get("airlines_found", [])
            or results["expedia"].get(cabin, {}).get("airlines_found", [])
            or results["centrav"].get(cabin, {}).get("airlines_found", [])
        )
        if al:
            log(f"  {cabin_labels[cabin]} airlines: {', '.join(al[:6])}")

    # Save
    out_file.write_text(json.dumps(results, indent=2))
    log(f"\nResults → {out_file}")

    return results


async def centrav_login_flow(browser_type: str = "firefox"):
    """One-time interactive Centrav login to save session cookies.

    Launches a VISIBLE browser, pre-fills credentials, waits for you to
    solve the reCAPTCHA and click Login, then saves cookies to:
      core/travel/data/centrav_session.json

    Usage: python3 test_airline_scrapers.py --centrav-login
    """
    log("=== Centrav One-Time Login ===")
    log(f"Browser: {browser_type} | Session will be saved to: {CENTRAV_SESSION_FILE}")
    async with async_playwright() as p:
        _browser_engine = p.firefox if browser_type == "firefox" else p.chromium
        _user_agent = (
            "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0"
            if browser_type == "firefox"
            else "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                 "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        browser = await _browser_engine.launch(
            headless=False,
            args=[] if browser_type == "firefox" else ["--no-sandbox"],
        )
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent=_user_agent,
        )
        page = await context.new_page()
        await page.goto("https://www.centrav.com/login", wait_until="domcontentloaded", timeout=30_000)
        await page.wait_for_timeout(1_500)

        try:
            await page.fill("#FormEmail", CENTRAV_EMAIL, timeout=5_000)
            await page.fill("#FormPassword", CENTRAV_PASS, timeout=5_000)
            log("Credentials pre-filled. Solve the CAPTCHA in the browser, then click Login.")
        except Exception:
            log("Could not pre-fill credentials. Fill them manually, then click Login.")

        log("Waiting up to 120 seconds for you to complete login...")
        for _ in range(60):
            await page.wait_for_timeout(2_000)
            if "login" not in page.url.lower():
                break
        else:
            log("Timed out. Try again.")
            await browser.close()
            return

        log(f"Login success! URL: {page.url}")
        cookies = await context.cookies()
        CENTRAV_SESSION_FILE.write_text(json.dumps(cookies, indent=2))
        log(f"Session saved → {CENTRAV_SESSION_FILE}")
        log("You can now run --source centrav in headless mode.")
        await browser.close()


def main():
    global ORIGIN, DEST
    parser = argparse.ArgumentParser(description="Airline scraper: multi-source, any route")
    parser.add_argument("--date", default=DEFAULT_DEPART, help="Departure date YYYY-MM-DD")
    parser.add_argument("--origin", default=ORIGIN, help="Origin IATA code (default: DEN)")
    parser.add_argument("--dest", default=DEST, help="Destination IATA code (default: HNL)")
    parser.add_argument("--headless", default="true", choices=["true", "false"])
    parser.add_argument(
        "--source",
        default="all",
        choices=["all"] + SOURCES,
        help="Run a single source (default: all)",
    )
    parser.add_argument(
        "--centrav-login",
        action="store_true",
        help="One-time interactive Centrav login to save session cookies",
    )
    parser.add_argument(
        "--browser",
        default="firefox",
        choices=["firefox", "chromium"],
        help="Browser engine to use (default: firefox — better bot evasion)",
    )
    args = parser.parse_args()
    ORIGIN = args.origin.upper()
    DEST = args.dest.upper()

    if args.centrav_login:
        asyncio.run(centrav_login_flow(browser_type=args.browser))
    else:
        asyncio.run(run_tests(args.date, headless=args.headless.lower() == "true", source=args.source, browser_type=args.browser))


if __name__ == "__main__":
    main()
