#!/usr/bin/env python3
"""
Perx Session Keepalive — Cookie Refresh for Interline Rate Platform
====================================================================
Perx provides interline (employee/industry) fares. Heavy discounts = TA rate signal.

Flow:
  1. HTTP fast-check: are existing cookies still valid on an authenticated endpoint?
  2. If valid → touch/save cookies and exit (no browser needed).
  3. If expired → Playwright CLEAN context (no stale cookies) → login form → save new cookies.

CRITICAL: Stale cookies must NOT be loaded into the Playwright context before navigating
to the login page — Perx redirects sessions-with-stale-cookies to a marketing page
instead of the login form. Clean context → login form appears.

Usage:
    python3 scripts/perx_session_keepalive.py

Dreams2Memories Travel, LLC — Thunderbird Wing — Hale/Intel 2026-06-08
"""
import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from playwright.async_api import async_playwright

THUNDERBIRD = Path(__file__).resolve().parent.parent
CREDS_DIR = THUNDERBIRD / "creds"
LOG_DIR = THUNDERBIRD / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s PERX-KEEPALIVE %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(str(LOG_DIR / "perx_session_keepalive.log"), mode="a"),
    ],
)
log = logging.getLogger("perx_keepalive")

EMAIL = "yodainva@gmail.com"
PASSWORD = "Falcons4me!"
COOKIE_FILE = CREDS_DIR / "perx_cookies.json"

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0.0.0"}


def _load_existing_cookies() -> list:
    if not COOKIE_FILE.exists():
        return []
    try:
        raw = json.loads(COOKIE_FILE.read_text(encoding="utf-8"))
        return raw if isinstance(raw, list) else raw.get("cookies", [])
    except Exception:
        return []


def _check_session_http(cookies: list) -> bool:
    """Return True if existing cookies are valid on an authenticated endpoint."""
    jar = {c["name"]: c["value"] for c in cookies if "perx" in c.get("domain", "")}
    if not jar.get("sessionid"):
        return False
    try:
        # /account/ redirects to /login/ when session is expired
        resp = requests.get(
            "https://www.perx.com/account/",
            cookies=jar,
            headers=HEADERS,
            allow_redirects=False,
            timeout=15,
        )
        # 200 = authenticated page loaded; 302 to /login/ = expired
        return resp.status_code == 200
    except Exception as exc:
        log.warning("HTTP session check failed: %s", exc)
        return False


def _save_cookies(cookies: list):
    # Save as raw list — consistent across all Thunderbird consumers
    COOKIE_FILE.write_text(json.dumps(cookies, indent=2, ensure_ascii=False), encoding="utf-8")
    perx_only = [c for c in cookies if "perx" in c.get("domain", "")]
    log.info("Saved %d Perx cookies to %s", len(perx_only), COOKIE_FILE.name)
    expiry = None
    for c in perx_only:
        exp = c.get("expires") or c.get("expiry")
        if exp and exp > 0:
            dt = datetime.fromtimestamp(exp, tz=timezone.utc)
            if expiry is None or dt < expiry:
                expiry = dt
    if expiry:
        log.info("Earliest cookie expiry: %s", expiry.strftime("%Y-%m-%d %H:%M UTC"))


async def _login_playwright() -> list:
    """
    Log in to Perx via a CLEAN Playwright context (no stale cookies).
    Returns the new cookies on success, [] on failure.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # DO NOT add existing cookies — stale cookies redirect to marketing page
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=HEADERS["User-Agent"],
        )
        page = await context.new_page()
        try:
            log.info("Navigating to Perx login form...")
            await page.goto("https://www.perx.com/account/login/", wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(2000)

            inputs = await page.evaluate(
                "() => Array.from(document.querySelectorAll('input')).map(i => i.name)"
            )
            log.info("Inputs on page: %s", inputs)

            if "username" not in inputs:
                body = await page.evaluate("() => document.body.innerText")
                log.error("Login form not found. URL=%s body=%s", page.url, body[:300])
                return []

            log.info("Dismissing cookie banner and opening login modal...")
            # Dismiss cookie consent if present
            try:
                await page.click('#onetrust-accept-btn-handler', timeout=5000)
                await page.wait_for_timeout(1000)
            except Exception:
                pass

            # Click "Log In" button to open the #login-modal
            await page.click('a[data-target="#login-modal"]', timeout=10000)
            await page.wait_for_timeout(1500)

            log.info("Filling login form in modal...")
            # Modal form fields are now visible
            await page.locator('#login-modal input[name="username"]').fill(EMAIL)
            await page.locator('#login-modal input[name="password"]').fill(PASSWORD)
            await page.locator('#login-modal button[type="submit"]').click()
            await page.wait_for_load_state("networkidle", timeout=30000)
            await page.wait_for_timeout(3000)

            post_url = page.url
            if "login" in post_url:
                body = await page.evaluate("() => document.body.innerText")
                if "invalid" in body.lower() or "incorrect" in body.lower():
                    log.error("Login rejected — credentials may be wrong")
                    return []

            log.info("Login successful, URL now: %s", post_url)
            cookies = await context.cookies()
            return [c for c in cookies if "perx" in c.get("domain", "")]

        except Exception as exc:
            log.error("Playwright login failed: %s", exc)
            return []
        finally:
            await context.close()
            await browser.close()


async def main():
    existing = _load_existing_cookies()

    # Fast path: HTTP check
    if existing:
        log.info("Checking existing session via HTTP (%d cookies)...", len(existing))
        if _check_session_http(existing):
            log.info("Session still valid — no login needed")
            _save_cookies(existing)
            return 0
        log.info("Session expired — proceeding to Playwright login")

    # Playwright login
    new_cookies = await _login_playwright()
    if not new_cookies:
        log.error("Login failed — no new cookies obtained")
        return 1

    _save_cookies(new_cookies)
    log.info("Perx session refreshed successfully")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
