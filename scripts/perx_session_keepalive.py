#!/usr/bin/env python3
"""
Perx Session Keepalive — Cookie Refresh for TA Rate Platform
=============================================================
Perx provides agent-rate pricing for Silversea. Cookies have a hardcoded
expiry of 2026-05-25 and need manual re-export. This script automates the
login flow via Playwright Chromium.

Usage:
    python3 scripts/perx_session_keepalive.py

Exit codes: 0 = OK, 1 = failed

Dreams2Memories Travel, LLC — Thunderbird Wing — Hale COS 2026-06-04
"""
import asyncio, json, logging, sys
from datetime import datetime, timezone
from pathlib import Path
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

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080}
        )
        page = await context.new_page()

        try:
            log.info("Navigating to perx.com...")
            await page.goto("https://www.perx.com", wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(3000)

            body = await page.evaluate("() => document.body.innerText")

            if "Sign Out" in body or "Logout" in body or "My Account" in body:
                log.info("Already logged in")
            else:
                log.info("Attempting login...")
                await page.goto(
                    "https://www.perx.com/account/login",
                    wait_until="networkidle", timeout=30000
                )
                await page.wait_for_timeout(2000)

                try:
                    await page.fill('input[type="email"], input[name="email"], input[name="login"]', EMAIL)
                    await page.fill('input[type="password"]', PASSWORD)
                    await page.click('button[type="submit"], input[type="submit"], .login-button')
                    await page.wait_for_load_state("networkidle", timeout=30000)
                    await page.wait_for_timeout(3000)
                except Exception as e:
                    log.warning(f"Standard login failed, trying alternate selector: {e}")
                    try:
                        await page.fill('input[id*="email"], input[id*="Email"]', EMAIL)
                        await page.fill('input[id*="password"], input[id*="Password"]', PASSWORD)
                        await page.get_by_role("button").filter(has_text="Sign").click()
                        await page.wait_for_load_state("networkidle", timeout=30000)
                        await page.wait_for_timeout(3000)
                    except Exception as e2:
                        log.error(f"All login attempts failed: {e2}")
                        body = await page.evaluate("() => document.body.innerText")
                        log.info(f"Page body: {body[:500]}")
                        return 1

            cookies = await context.cookies()
            perx_cookies = [c for c in cookies if "perx" in c.get("domain", "")]
            metadata = {
                "_account": EMAIL,
                "_password": PASSWORD,
                "_expires": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "cookies": perx_cookies,
            }
            COOKIE_FILE.write_text(json.dumps(metadata, indent=2))
            log.info(f"Exported {len(perx_cookies)} Perx cookies to {COOKIE_FILE.name}")

            expiry = None
            for c in perx_cookies:
                exp = c.get("expires") or c.get("expiry")
                if exp and exp > 0:
                    dt = datetime.fromtimestamp(exp, tz=timezone.utc)
                    if expiry is None or dt < expiry:
                        expiry = dt
            if expiry:
                log.info(f"Earliest cookie expiry: {expiry.strftime('%Y-%m-%d %H:%M UTC')}")

            return 0

        except Exception as e:
            log.error(f"Perx keepalive failed: {e}")
            return 1
        finally:
            await context.close()
            await browser.close()

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
