#!/usr/bin/env python3
"""
centrav_session_auto_keepalive.py — Automated Centrav B2B Portal Session Keeper

Handles Centrav B2B portal re-authentication with intelligent fallback strategies:
1. Attempt automated login via Playwright (handles basic login)
2. If reCAPTCHA detected, fall back to semi-automated flow with browser hints
3. If OTP flow detected, pause for manual intervention
4. Save cookies to creds/centrav_cookies.json for downstream scrapers

Runs via systemd timer (thunderbird-portal-keepalive.timer).

Usage:
  python3 scripts/centrav_session_auto_keepalive.py              # Full auto+fallback
  python3 scripts/centrav_session_auto_keepalive.py --headless   # Fully headless (may fail on reCAPTCHA)
  python3 scripts/centrav_session_auto_keepalive.py --status     # Check only
  python3 scripts/centrav_session_auto_keepalive.py --force      # Force re-auth even if cookies valid
"""

import asyncio
import json
import logging
import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

THUNDERBIRD = Path("/home/john/Thunderbird")
CREDS_DIR = THUNDERBIRD / "creds"
CONFIG_FILE = THUNDERBIRD / "config" / "portal_creds.json"
LOG_FILE = THUNDERBIRD / "logs" / "centrav_keepalive.log"
COOKIE_FILE = CREDS_DIR / "centrav_cookies.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("centrav_keepalive")


def load_config() -> dict:
    """Load portal credentials from config."""
    try:
        return json.loads(CONFIG_FILE.read_text())
    except FileNotFoundError:
        log.error(f"Config file not found: {CONFIG_FILE}")
        sys.exit(1)


def load_cookies() -> list:
    """Load existing cookies from file."""
    if not COOKIE_FILE.exists():
        return []
    try:
        return json.loads(COOKIE_FILE.read_text())
    except Exception:
        return []


def save_cookies(cookies: list) -> bool:
    """Save cookies to file."""
    try:
        CREDS_DIR.mkdir(parents=True, exist_ok=True)
        COOKIE_FILE.write_text(json.dumps(cookies, indent=2))
        return True
    except Exception as e:
        log.error(f"Failed to save cookies: {e}")
        return False


def get_cookie_status(cookies: list) -> dict:
    """Check if cookies are still valid."""
    now = datetime.now(timezone.utc).timestamp()
    if not cookies:
        return {"status": "MISSING", "hours_left": None}

    soonest_expiry = None
    for c in cookies:
        exp = c.get("expires")
        if exp and exp > 0:
            if soonest_expiry is None or exp < soonest_expiry:
                soonest_expiry = exp

    if soonest_expiry is None:
        return {"status": "SESSION_ONLY", "hours_left": None}

    hours_left = (soonest_expiry - now) / 3600
    if hours_left < 0:
        return {"status": "EXPIRED", "hours_left": round(hours_left, 1)}
    elif hours_left < 1:
        return {"status": "STALE", "hours_left": round(hours_left, 1)}
    elif hours_left < 24:
        return {"status": "WARN", "hours_left": round(hours_left, 1)}
    else:
        return {"status": "OK", "hours_left": round(hours_left, 1)}


async def attempt_auto_login(page, email: str, password: str, headless: bool = False) -> list:
    """
    Attempt automated login to Centrav.

    Returns:
        - List of cookies if successful
        - Empty list if login failed or requires manual intervention (reCAPTCHA, OTP)
    """
    try:
        log.info("Navigating to Centrav login page...")
        await page.goto("https://www.centrav.com/login", wait_until="domcontentloaded", timeout=30000)

        # Check if reCAPTCHA is present
        recaptcha = await page.query_selector('iframe[src*="recaptcha"]')
        if recaptcha:
            log.warning("reCAPTCHA detected — cannot proceed in headless mode. Use manual login via CLI.")
            if headless:
                return []
            else:
                log.info("Opening browser for manual reCAPTCHA completion. Press Enter when done...")
                await page.pause()

        # Fill email
        log.info("Filling email field...")
        await page.fill('input[type="email"], input[name="email"]', email, timeout=5000)
        await page.wait_for_timeout(500)

        # Fill password
        log.info("Filling password field...")
        await page.fill('input[type="password"], input[name="password"]', password, timeout=5000)
        await page.wait_for_timeout(500)

        # Click submit
        log.info("Submitting login form...")
        submit_button = await page.query_selector('button[type="submit"], input[type="submit"]')
        if submit_button:
            await submit_button.click(timeout=5000)
        else:
            await page.press('input[type="password"]', 'Enter')

        # Wait for navigation to dashboard
        # Centrav may show OTP flow — check if we need to wait for manual entry
        try:
            await page.wait_for_url("**/dashboard**", timeout=15000)
            log.info("Login successful — dashboard loaded")
        except PlaywrightTimeoutError:
            # Check if we're on OTP page
            otp_input = await page.query_selector('input[type="text"][name*="otp"], input[type="text"][id*="otp"]')
            if otp_input:
                log.warning("OTP flow detected. Waiting for manual OTP entry (5 minutes timeout)...")
                if not headless:
                    await page.pause()
                try:
                    await page.wait_for_url("**/dashboard**", timeout=300000)
                    log.info("OTP accepted — dashboard loaded")
                except PlaywrightTimeoutError:
                    log.error("OTP entry timeout — login failed")
                    return []
            else:
                log.error("Login page navigation timeout")
                return []

        # Capture cookies
        raw_cookies = await page.context.cookies()
        cookies = [c for c in raw_cookies if "centrav" in c.get("domain", "")]
        log.info(f"Login successful — captured {len(cookies)} cookies")
        return cookies

    except Exception as e:
        log.error(f"Login failed: {e}")
        return []


async def run_auto_keepalive(headless: bool = False, force: bool = False) -> bool:
    """
    Main keepalive flow.

    Returns:
        True if successful, False if failed or requires manual intervention
    """
    # Load config and current cookies
    config = load_config()
    centrav_config = config.get("centrav", {})
    email = centrav_config.get("email", "")
    password = centrav_config.get("password", "")

    if not email or not password:
        log.error("Centrav credentials not found in config/portal_creds.json (centrav section)")
        return False

    # Check current cookie status
    cookies = load_cookies()
    status = get_cookie_status(cookies)
    log.info(f"Current cookie status: {status['status']} ({status.get('hours_left', '?')}h remaining)")

    if status["status"] == "OK" and not force:
        log.info("Cookies still valid — no refresh needed")
        return True

    log.info("Cookies expiring or missing — attempting auto-refresh...")

    # Attempt login
    async with async_playwright() as p:
        # Use Firefox for better reCAPTCHA handling (though still won't auto-solve)
        browser = await p.firefox.launch(headless=headless)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            fresh_cookies = await attempt_auto_login(page, email, password, headless=headless)
            if fresh_cookies:
                if save_cookies(fresh_cookies):
                    log.info("✓ Cookies saved successfully")
                    return True
                else:
                    log.error("Failed to save cookies")
                    return False
            else:
                log.warning("Auto-login failed — manual intervention required")
                return False
        finally:
            await context.close()
            await browser.close()


async def status_only() -> None:
    """Print cookie status only."""
    cookies = load_cookies()
    status = get_cookie_status(cookies)

    print("\n=== CENTRAV COOKIE STATUS ===")
    print(f"Status: {status['status']}")
    if status.get('hours_left') is not None:
        print(f"Hours remaining: {status['hours_left']}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Centrav B2B Portal Automated Session Keeper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Full auto + fallback to manual
  %(prog)s --headless         # Fully automated (may fail on reCAPTCHA/OTP)
  %(prog)s --status           # Check cookie status only
  %(prog)s --force            # Force re-auth even if cookies valid
  %(prog)s --headless --force # Force headless login attempt
        """
    )
    parser.add_argument("--headless", action="store_true",
                        help="Fully headless mode (skip manual intervention steps)")
    parser.add_argument("--status", action="store_true",
                        help="Print status only, no login attempt")
    parser.add_argument("--force", action="store_true",
                        help="Force re-authentication even if cookies still valid")

    args = parser.parse_args()

    if args.status:
        asyncio.run(status_only())
        return 0

    success = asyncio.run(run_auto_keepalive(headless=args.headless, force=args.force))
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
