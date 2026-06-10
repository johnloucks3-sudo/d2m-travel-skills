#!/usr/bin/env python3
"""
test_silversea.py — Silversea portal connector test.

Verifies that the silversea_connector module loads, auth flow completes,
and booking data is parseable from a live session.

Usage:
    python3 scripts/test_silversea.py                     # live test (requires creds)
    python3 scripts/test_silversea.py --mock               # test with saved HTML fixture
    python3 scripts/test_silversea.py --list-bookings      # list-only, no enrichment

Credentials: config/portal_creds.json → silversea.email / silversea.password
"""
import argparse
import json
import re
import sys
from pathlib import Path

THUNDERBIRD = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(THUNDERBIRD))


def check_creds() -> dict:
    creds_path = THUNDERBIRD / "config" / "portal_creds.json"
    if not creds_path.exists():
        print("FAIL: portal_creds.json not found")
        sys.exit(1)
    creds = json.loads(creds_path.read_text()).get("silversea", {})
    email = creds.get("email", "")
    password = creds.get("password", "")
    if not email or not password:
        print("FAIL: silversea credentials missing in portal_creds.json")
        print("  Commander must add:")
        print('    "silversea": {')
        print('      "url": "https://my.silversea.com",')
        print('      "email": "<Commander\'s Silversea email>",')
        print('      "password": "<password>",')
        print('      "note": "Agency account — my.silversea.com, custom_usertype: Agency",')
        print('      "bookings": "McLeod 298475-25 (Silver Muse, PAID)"')
        print("    }")
        sys.exit(1)
    return creds


def test_mock_parse():
    """Test parser against saved validation fixture."""
    fixture = THUNDERBIRD / "validations" / "rssc_scrape" / "silversea_bookings_113628.json"
    if not fixture.exists():
        print(f"SKIP: no mock fixture at {fixture}")
        return

    data = json.loads(fixture.read_text())

    # Build a minimal mock HTML from the fixture's link array
    # The real fullText is truncated in storage, so we reconstruct booking context
    links_html = ""
    for link in data.get("links", []):
        href = link.get("href", "")
        text = link.get("text", "")
        links_html += f'<a href="{href}">{text}</a>\n'

    # Build a mock page body with Silversea nav structure
    mock_html = f"""
    <html>
    <body>
    <nav>
      <a href="https://my.silversea.com/">Home</a>
      <a href="https://my.silversea.com/MyBookings">BOOKINGS</a>
      <a href="#">johnloucks3@gmail.com Log out</a>
    </nav>
    <main>
      <h1>My Bookings</h1>
      <div class="booking-list">
        {links_html}
      </div>
    </main>
    </body>
    </html>
    """

    from core.ai_infra.intel_connectors.silversea_connector import _parse_bookings_page, _check_auth

    assert _check_auth(mock_html), "Auth check should pass on dashboard HTML"
    bookings = _parse_bookings_page(mock_html)
    print(f"MOCK PARSE: found {len(bookings)} booking(s)")

    codes = [b.get("booking_reference", "") for b in bookings]
    print(f"  Booking codes: {codes}")

    if "298475-25" in codes:
        print("  PASS: McLeod booking (298475-25) found")
    else:
        print("  WARN: Expected 298475-25 not found — checking fixture links for reference")

    # Validate link-extracted booking codes from fixture
    link_codes = set()
    for link in data.get("links", []):
        href = link.get("href", "")
        m = re.search(r"[?&]code=([\w\-]+)", href)
        if m:
            code = m.group(1)
            if re.match(r"^\d{5,6}-\d{2}$", code):
                link_codes.add(code)

    print(f"  Expected from fixture links: {sorted(link_codes)}")

    for b in bookings:
        ref = b.get("booking_reference", "?")
        print(f"  Booking {ref}:")
        for k, v in b.items():
            if k not in ("scraped_at",):
                print(f"    {k}: {v}")

    print("MOCK: OK")


def test_live_login(creds: dict, list_only: bool = False):
    """Test live login to my.silversea.com and scrape bookings."""
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

    from core.ai_infra.intel_connectors.silversea_connector import (
        SILVERSEA_LOGIN,
        SILVERSEA_BOOKINGS,
        _check_auth,
        _parse_bookings_page,
        _scrape_booking_detail,
    )

    email = creds["email"]
    password = creds["password"]

    print(f"LIVE TEST: logging in as {email}")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        ctx = browser.new_context(
            viewport={"width": 1440, "height": 900},
            locale="en-US",
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
            ),
        )
        page = ctx.new_page()

        print("  1. Loading login page...")
        page.goto(SILVERSEA_LOGIN, timeout=30000, wait_until="domcontentloaded")
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except PWTimeout:
            pass
        print(f"     Title: {page.title()}")

        print("  2. Filling credentials...")
        for sel in ["input[name='Email']", "input[name='email']", "input[id='Email']", "input[type='email']"]:
            if page.locator(sel).count() > 0:
                page.locator(sel).first.fill(email)
                print(f"     Filled email via: {sel}")
                break

        for sel in ["input[name='Password']", "input[name='password']", "input[id='Password']", "input[type='password']"]:
            if page.locator(sel).count() > 0:
                page.locator(sel).first.fill(password)
                print(f"     Filled password via: {sel}")
                break

        for sel in ["button[type='submit']", "input[type='submit']", "button:has-text('Sign In')", "button:has-text('Log In')", "button:has-text('Login')"]:
            if page.locator(sel).count() > 0:
                page.locator(sel).first.click()
                print(f"     Clicked submit via: {sel}")
                break

        try:
            page.wait_for_load_state("networkidle", timeout=20000)
        except PWTimeout:
            pass

        print("  3. Navigating to My Bookings...")
        page.goto(SILVERSEA_BOOKINGS, timeout=30000, wait_until="domcontentloaded")
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except PWTimeout:
            pass

        html = page.content()
        authed = _check_auth(html)

        if not authed:
            print("  FAIL: Auth check failed")
            print(f"  Page title: {page.title()}")
            print(f"  Page URL: {page.url}")
            browser.close()
            return False

        print("  PASS: Authenticated successfully")

        print("  4. Parsing bookings...")
        bookings = _parse_bookings_page(html)
        print(f"     Found {len(bookings)} booking(s)")

        for b in bookings:
            code = b.get("booking_reference", "?")
            print(f"     - {code}")
            for k, v in b.items():
                if k != "scraped_at":
                    print(f"         {k}: {v}")

        if not list_only and bookings:
            print("  5. Enriching with booking detail pages...")
            for b in bookings:
                code = b.get("booking_reference", "")
                if code:
                    print(f"     Fetching detail for {code}...")
                    detail = _scrape_booking_detail(page, code)
                    for k, v in detail.items():
                        if v and k not in ("booking_reference", "_detail_page_url"):
                            print(f"       {k}: {v}")
                            b[k] = v

        print("\n  FINAL STRUCTURED OUTPUT:")
        print(json.dumps(bookings, indent=2, default=str))

        screenshot_path = THUNDERBIRD / "output" / "silversea_test.png"
        page.screenshot(path=str(screenshot_path))
        print(f"\n  Screenshot saved: {screenshot_path}")

        browser.close()

    print("LIVE TEST: PASS")
    return True


def main():
    parser = argparse.ArgumentParser(description="Test Silversea portal connector")
    parser.add_argument("--mock", action="store_true", help="Test with saved HTML fixture only")
    parser.add_argument("--list-bookings", action="store_true", help="List-only, skip detail enrichment")
    args = parser.parse_args()

    if args.mock:
        print("=== SILVERSEA CONNECTOR TEST (MOCK MODE) ===")
        test_mock_parse()
        return

    print("=== SILVERSEA CONNECTOR TEST (LIVE) ===")

    creds = check_creds()
    print(f"Email: {creds['email']}")
    print(f"Password: {'*' * len(creds['password'])}")

    ok = test_live_login(creds, list_only=args.list_bookings)
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
