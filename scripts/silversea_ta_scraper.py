#!/usr/bin/env python3
"""
silversea_ta_scraper.py — Silversea TA Portal Scraper
=======================================================
Loads persisted session cookies, checks health, scrapes voyage pricing
and availability from my.silversea.com.

Falls back to full OIDC login if session expired.

Usage:
    python3 scripts/silversea_ta_scraper.py --check          # session health only
    python3 scripts/silversea_ta_scraper.py --voyages        # scrape voyage list
    python3 scripts/silversea_ta_scraper.py --voyage <id>    # scrape single voyage pricing
    python3 scripts/silversea_ta_scraper.py --bookings       # scrape my bookings
"""
import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log = logging.getLogger("silversea_scraper")

COOKIE_FILE = Path.home() / ".playwright" / "cookies_silversea.json"
CREDS_FILE = ROOT / "config" / "portal_creds.json"
INTEL_FILE = ROOT / "scraping_intel" / "silversea.json"
OUTPUT_DIR = ROOT / "output" / "silversea"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://my.silversea.com"
VOYAGES_URL = f"{BASE_URL}/Voyages"
BOOKINGS_URL = f"{BASE_URL}/MyBookings"


def load_cookies() -> list:
    if not COOKIE_FILE.exists():
        log.error(f"Cookie file not found: {COOKIE_FILE}")
        return []
    return json.loads(COOKIE_FILE.read_text())


def load_creds() -> dict:
    creds = json.loads(CREDS_FILE.read_text())
    return creds.get("silversea", {})


def save_cookies(page) -> None:
    """Persist current browser cookies back to file."""
    cookies = page.context.cookies()
    COOKIE_FILE.write_text(json.dumps(cookies, indent=2))
    log.info(f"Cookies saved → {COOKIE_FILE}")


def check_session_health(page) -> bool:
    """Return True if session is valid (not redirected to login)."""
    page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)
    time.sleep(2)
    url = page.url
    if "/Account/Login" in url or "/signin" in url or "/login" in url:
        log.warning(f"Session expired — redirected to: {url}")
        return False
    content = page.content()
    if "My Bookings" in content or "Welcome" in content or "Dashboard" in content or "my.silversea" in url:
        log.info("Session HEALTHY ✅")
        return True
    log.warning(f"Session state unclear. URL: {url}")
    return False


def do_oidc_login(page) -> bool:
    """Attempt full OIDC login flow with email/password."""
    creds = load_creds()
    email = creds.get("email", "")
    password = creds.get("password", "")
    if not email or not password:
        log.error("No credentials found in portal_creds.json silversea entry")
        return False

    log.info("Attempting OIDC login flow...")
    page.goto(f"{BASE_URL}/Account/Login", wait_until="domcontentloaded", timeout=30000)
    time.sleep(3)

    # Handle possible email input field (OIDC step 1 — enter email)
    try:
        email_input = page.locator("input[type='email'], input[name='email'], input[id*='email'], input[placeholder*='email' i]").first
        if email_input.is_visible(timeout=5000):
            email_input.fill(email)
            log.info(f"Filled email: {email}")
            # Look for Next/Continue button
            next_btn = page.locator("button[type='submit'], input[type='submit'], button:has-text('Next'), button:has-text('Continue')").first
            if next_btn.is_visible(timeout=3000):
                next_btn.click()
                time.sleep(2)
    except Exception as e:
        log.warning(f"Email step: {e}")

    # Password field
    try:
        pwd_input = page.locator("input[type='password']").first
        if pwd_input.is_visible(timeout=5000):
            pwd_input.fill(password)
            log.info("Filled password")
            submit = page.locator("button[type='submit'], input[type='submit'], button:has-text('Sign In'), button:has-text('Login'), button:has-text('Log In')").first
            if submit.is_visible(timeout=3000):
                submit.click()
                log.info("Clicked submit")
                time.sleep(5)
    except Exception as e:
        log.warning(f"Password step: {e}")

    # Check result
    time.sleep(3)
    url = page.url
    if "/Account/Login" in url or "/signin" in url:
        log.error(f"Login failed — still on login page: {url}")
        return False

    log.info(f"Login appears successful. URL: {url}")
    save_cookies(page)
    return True


def discover_selectors(page) -> dict:
    """Probe the page DOM to find voyage card selectors."""
    log.info("Discovering selectors...")
    candidates = {
        "voyage_cards": [".voyage-card", ".cruise-card", ".voyage-item", "[data-voyage-id]", ".voyage-listing__item"],
        "price": [".price__amount", ".price-from", "[data-price]", ".fare", ".starting-price", ".price"],
        "departure": [".departure-date", "[data-departure]", ".date", ".voyage-date"],
        "ship": [".ship-name", "[data-ship]", ".ship"],
        "duration": [".duration", "[data-nights]", ".nights"],
        "availability": [".availability", ".cabins-available", "[data-available]", ".avail"],
    }
    found = {}
    for key, selectors in candidates.items():
        for sel in selectors:
            try:
                count = page.locator(sel).count()
                if count > 0:
                    found[key] = {"selector": sel, "count": count}
                    log.info(f"  {key}: '{sel}' → {count} elements")
                    break
            except Exception:
                continue
    return found


def scrape_voyages(page) -> list:
    """Scrape voyage listing from TA portal."""
    log.info(f"Navigating to {VOYAGES_URL}")
    page.goto(VOYAGES_URL, wait_until="networkidle", timeout=45000)
    time.sleep(3)

    # Take screenshot for debugging
    screenshot_path = OUTPUT_DIR / f"voyages_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    page.screenshot(path=str(screenshot_path))
    log.info(f"Screenshot → {screenshot_path}")

    # Discover what's on the page
    selectors = discover_selectors(page)

    # Extract page HTML for analysis
    html_path = OUTPUT_DIR / f"voyages_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    html_path.write_text(page.content())
    log.info(f"HTML saved → {html_path}")

    # Try to extract voyage data
    voyages = []
    card_sel = selectors.get("voyage_cards", {}).get("selector")
    if not card_sel:
        log.warning("No voyage card selector found — check HTML output for DOM structure")
        return voyages

    cards = page.locator(card_sel).all()
    log.info(f"Found {len(cards)} voyage cards")

    for i, card in enumerate(cards[:50]):  # cap at 50
        try:
            voyage = {"index": i}
            price_sel = selectors.get("price", {}).get("selector")
            dep_sel = selectors.get("departure", {}).get("selector")
            ship_sel = selectors.get("ship", {}).get("selector")
            dur_sel = selectors.get("duration", {}).get("selector")

            if price_sel:
                try:
                    voyage["price"] = card.locator(price_sel).first.inner_text(timeout=2000).strip()
                except Exception:
                    pass
            if dep_sel:
                try:
                    voyage["departure"] = card.locator(dep_sel).first.inner_text(timeout=2000).strip()
                except Exception:
                    pass
            if ship_sel:
                try:
                    voyage["ship"] = card.locator(ship_sel).first.inner_text(timeout=2000).strip()
                except Exception:
                    pass
            if dur_sel:
                try:
                    voyage["duration"] = card.locator(dur_sel).first.inner_text(timeout=2000).strip()
                except Exception:
                    pass

            # Try full text as fallback
            try:
                voyage["raw_text"] = card.inner_text(timeout=2000).strip()[:300]
            except Exception:
                pass

            voyages.append(voyage)
        except Exception as e:
            log.warning(f"Card {i} error: {e}")

    return voyages


def scrape_bookings(page) -> dict:
    """Scrape my bookings page."""
    log.info(f"Navigating to {BOOKINGS_URL}")
    page.goto(BOOKINGS_URL, wait_until="networkidle", timeout=45000)
    time.sleep(3)

    screenshot_path = OUTPUT_DIR / f"bookings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    page.screenshot(path=str(screenshot_path))
    log.info(f"Screenshot → {screenshot_path}")

    html_path = OUTPUT_DIR / f"bookings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    html_path.write_text(page.content())
    log.info(f"HTML saved → {html_path}")

    return {"screenshot": str(screenshot_path), "html": str(html_path), "url": page.url}


def run(args):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log.error("playwright not installed. Run: pip install playwright && playwright install chromium")
        sys.exit(1)

    cookies = load_cookies()
    if not cookies:
        log.error("No cookies loaded — cannot proceed")
        sys.exit(1)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--disable-extensions",
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900},
            locale="en-US",
        )

        # Inject cookies
        # Playwright requires cookies to have specific domain format
        playwright_cookies = []
        for c in cookies:
            pc = {
                "name": c["name"],
                "value": c["value"],
                "domain": c.get("domain", ".silversea.com"),
                "path": c.get("path", "/"),
                "httpOnly": c.get("httpOnly", False),
                "secure": c.get("secure", False),
            }
            if c.get("expires", -1) != -1:
                pc["expires"] = int(c["expires"])
            if c.get("sameSite"):
                pc["sameSite"] = c["sameSite"]
            playwright_cookies.append(pc)

        context.add_cookies(playwright_cookies)
        log.info(f"Loaded {len(playwright_cookies)} cookies")

        page = context.new_page()

        # Check session health
        healthy = check_session_health(page)
        if not healthy:
            log.info("Attempting auto-login...")
            if not do_oidc_login(page):
                log.error("Login failed. Manual intervention required.")
                browser.close()
                sys.exit(1)

        result = {}

        if args.check:
            result = {"session": "healthy" if healthy else "refreshed_via_login", "url": page.url}

        elif args.voyages:
            voyages = scrape_voyages(page)
            result = {"count": len(voyages), "voyages": voyages}
            out_file = OUTPUT_DIR / f"voyages_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            out_file.write_text(json.dumps(result, indent=2))
            log.info(f"Voyages saved → {out_file}")

        elif args.bookings:
            result = scrape_bookings(page)

        browser.close()

    print(json.dumps(result, indent=2))
    return result


def main():
    parser = argparse.ArgumentParser(description="Silversea TA Portal Scraper")
    parser.add_argument("--check", action="store_true", help="Session health check only")
    parser.add_argument("--voyages", action="store_true", help="Scrape voyage listing")
    parser.add_argument("--voyage", type=str, help="Scrape single voyage by ID")
    parser.add_argument("--bookings", action="store_true", help="Scrape my bookings")
    args = parser.parse_args()

    if not any([args.check, args.voyages, args.voyage, args.bookings]):
        args.check = True  # default to health check

    run(args)


if __name__ == "__main__":
    main()
