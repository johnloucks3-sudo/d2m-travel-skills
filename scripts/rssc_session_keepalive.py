#!/usr/bin/env python3
"""
RSSC Session Keepalive — Regent Seven Seas Cookie Refresh (M-074 follow-on)
=============================================================================
Lightweight cookie refresh for both Regent accounts (D2M direct + OA).
Runs via systemd timer every 4 hours to ensure session cookies never expire.

Does NOT scrape booking data — only logs in, exports cookies, logs out.
This keeps the session warm so scraper scripts never hit a login gate.

Usage:
    python3 scripts/rssc_session_keepalive.py
    python3 scripts/rssc_session_keepalive.py --d2m-only
    python3 scripts/rssc_session_keepalive.py --oa-only

Exit codes: 0 = OK, 1 = partial failure, 2 = both accounts failed

Dreams2Memories Travel, LLC — Thunderbird Wing — Hale COS 2026-06-04
"""
import asyncio, json, os, sys, logging
from datetime import datetime, timezone
from pathlib import Path
from playwright.async_api import async_playwright

THUNDERBIRD = Path(__file__).resolve().parent.parent
CREDS_DIR = THUNDERBIRD / "creds"
LOG_DIR = THUNDERBIRD / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s RSSC-KEEPALIVE %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(str(LOG_DIR / "rssc_session_keepalive.log"), mode="a"),
    ],
)
log = logging.getLogger("rssc_keepalive")

D2M_EMAIL = "jl3lovegrouptravel@gmail.com"
D2M_PASSWORD = "Falcons4me!"
OA_EMAIL = "johnloucks3@gmail.com"
OA_PASSWORD = "Canal4me!"

LOGIN_URL = "https://www.rssc.com/agent/default.aspx"
COOKIE_FILES = {
    "d2m": CREDS_DIR / "regent_cookies.json",
    "oa": CREDS_DIR / "regent_cookies_oa.json",
}

async def login_and_export(browser, email: str, password: str, label: str) -> bool:
    """Log in to RSSC agent portal and export cookies. Returns True on success."""
    log.info(f"[{label}] Starting login for {email}")
    context = await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent=(
            "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"
        ),
    )
    page = await context.new_page()

    try:
        await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000)

        try:
            btn = await page.query_selector("#onetrust-accept-btn-handler")
            if btn:
                await btn.click()
                await page.wait_for_timeout(500)
        except:
            pass

        body = await page.evaluate("() => document.body.innerText")
        if "Logout" in body or "Return to dashboard" in body:
            log.info(f"[{label}] Already logged in — exporting cookies")
            cookies = await context.cookies()
            _save_cookies(label, cookies)
            log.info(f"[{label}] Exported {len(cookies)} cookies (already authenticated)")
            return True

        await page.fill(
            "#uxAgentHomePage_uxAgentRegister_uxLoginEmailAddressTextbox", email
        )
        await page.fill(
            "#uxAgentHomePage_uxAgentRegister_uxLoginPasswordTextbox", password
        )
        await page.check("#uxAgentHomePage_uxAgentRegister_uxRememberMeCheckbox")
        await page.click("#uxAgentHomePage_uxAgentRegister_uxLoginButton")
        await page.wait_for_load_state("networkidle", timeout=30000)

        body = await page.evaluate("() => document.body.innerText")
        if "incorrect" in body.lower():
            log.error(f"[{label}] Login failed — incorrect credentials")
            return False

        cookies = await context.cookies()
        _save_cookies(label, cookies)
        log.info(f"[{label}] Login OK — exported {len(cookies)} cookies")
        return True

    except Exception as e:
        log.error(f"[{label}] Login error: {e}")
        return False
    finally:
        await context.close()

def _save_cookies(label: str, cookies: list):
    path = COOKIE_FILES[label]
    path.write_text(json.dumps(cookies, indent=2))
    expiry = None
    for c in cookies:
        exp = c.get("expires") or c.get("expiry")
        if exp and exp > 0:
            dt = datetime.fromtimestamp(exp, tz=timezone.utc)
            if expiry is None or dt < expiry:
                expiry = dt
    if expiry:
        log.info(f"[{label}] Cookie expiry: {expiry.strftime('%Y-%m-%d %H:%M UTC')}")
    else:
        log.warning(f"[{label}] No expiring cookies found — session-only?")

async def main():
    d2m_only = "--d2m-only" in sys.argv
    oa_only = "--oa-only" in sys.argv

    results = {}
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        log.info("Browser launched (Firefox headless)")

        if not oa_only:
            results["d2m"] = await login_and_export(browser, D2M_EMAIL, D2M_PASSWORD, "d2m")
        if not d2m_only:
            results["oa"] = await login_and_export(browser, OA_EMAIL, OA_PASSWORD, "oa")

        await browser.close()

    success = sum(1 for v in results.values() if v)
    total = len(results)
    log.info(f"Results: {success}/{total} accounts refreshed")

    if success == 0:
        sys.exit(2)
    elif success < total:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
