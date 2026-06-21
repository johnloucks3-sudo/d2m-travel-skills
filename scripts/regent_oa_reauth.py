#!/usr/bin/env python3
"""
regent_oa_reauth.py — Regent Seven Seas OA portal re-authentication via Chrome CDP.

Connects to the live Chrome browser at port 9222, navigates to the Regent OA
login page, and waits for Commander to complete the login (incl. any CAPTCHA).
Once logged in, captures all rssc.com cookies and writes them to the canonical
cookie files for use by scraper scripts.

Usage:
  python3 scripts/regent_oa_reauth.py

After Commander logs in, script auto-detects the ASPXAUTH cookie, saves it,
and updates hale_state.json's credential status to 'OK'.

Prerequisites:
  Chrome must be running with --remote-debugging-port=9222
  playwright must be installed: pip install playwright && playwright install chromium
"""

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
CREDS_DIR = ROOT / "creds"
STATE_FILE = ROOT / "hale_state.json"

COOKIE_TARGETS = [
    CREDS_DIR / "regent_cookies_oa.json",
    CREDS_DIR / "regent_cookies.json",
]

REGENT_OA_LOGIN = "https://www.rssc.com/agent/login"
REGENT_OA_DOMAIN = "rssc.com"
CDP_URL = "http://localhost:9222"

POLL_INTERVAL = 3   # seconds between login-check polls
TIMEOUT_MINS = 10   # give up after this many minutes


def _cookie_to_playwright(c: dict) -> dict:
    """Convert CDP cookie format to Playwright JSON cookie format."""
    same_site_map = {0: "None", 1: "Lax", 2: "Strict", "None": "None", "Lax": "Lax", "Strict": "Strict"}
    return {
        "name": c.get("name", ""),
        "value": c.get("value", ""),
        "domain": c.get("domain", ""),
        "path": c.get("path", "/"),
        "expires": c.get("expires", -1),
        "httpOnly": c.get("httpOnly", False),
        "secure": c.get("secure", False),
        "sameSite": same_site_map.get(c.get("sameSite", "None"), "None"),
    }


async def wait_for_login(page) -> list[dict]:
    """Poll until ASPXAUTH cookie appears on the OA domain. Returns all rssc cookies."""
    print(f"\nWaiting for Commander to log in at {REGENT_OA_LOGIN}")
    print(f"Polling every {POLL_INTERVAL}s — timeout {TIMEOUT_MINS} min...")
    print("Press Ctrl+C to abort.\n")

    deadline = asyncio.get_event_loop().time() + (TIMEOUT_MINS * 60)

    while asyncio.get_event_loop().time() < deadline:
        try:
            cookies = await page.context.cookies()
            rssc = [c for c in cookies if "rssc.com" in c.get("domain", "")]
            has_auth = any(c["name"] == "ASP.NET_SessionId" or c["name"] == "ASPXAUTH" for c in rssc)
            if has_auth:
                auth_cookie = next((c for c in rssc if c["name"] == "ASPXAUTH"), None)
                if auth_cookie:
                    expiry_ts = auth_cookie.get("expires", 0)
                    expiry_dt = datetime.fromtimestamp(expiry_ts, tz=timezone.utc) if expiry_ts > 0 else None
                    print(f"✅ ASPXAUTH detected!")
                    if expiry_dt:
                        print(f"   Expires: {expiry_dt.isoformat()} ({int((expiry_dt - datetime.now(tz=timezone.utc)).total_seconds() / 3600)}h remaining)")
                    return rssc
        except Exception as e:
            print(f"  Poll error (retrying): {e}")

        await asyncio.sleep(POLL_INTERVAL)
        sys.stdout.write(".")
        sys.stdout.flush()

    print("\n\nTimeout — no login detected.")
    return []


def save_cookies(cookies: list[dict]) -> None:
    """Write cookies in Playwright format to all canonical target files."""
    playwright_cookies = [_cookie_to_playwright(c) for c in cookies]
    for target in COOKIE_TARGETS:
        target.write_text(json.dumps(playwright_cookies, indent=2))
        print(f"  Saved {len(playwright_cookies)} cookies → {target.name}")


def update_hale_state(aspxauth_expires_iso: str) -> None:
    """Update hale_state.json credential status for regent_oa."""
    if not STATE_FILE.exists():
        return
    try:
        state = json.loads(STATE_FILE.read_text())
        cred = state.setdefault("wing_health", {}).setdefault("credential_status", {}).setdefault("regent_oa", {})
        cred["status"] = "OK"
        cred["issue"] = None
        cred["expires"] = aspxauth_expires_iso
        cred["last_verified"] = datetime.now(tz=timezone.utc).isoformat()
        cred["keepalive_coverage"] = "portal_keepalive.timer"
        cred.pop("mitigation", None)
        state["_meta"]["last_updated"] = datetime.now(tz=timezone.utc).isoformat()
        STATE_FILE.write_text(json.dumps(state, indent=2))
        print("  Updated hale_state.json — regent_oa status: OK")
    except Exception as e:
        print(f"  hale_state.json update failed (non-fatal): {e}")


async def main():
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("ERROR: playwright not installed. Run: pip install playwright && playwright install chromium")
        sys.exit(1)

    print("=== Regent OA Re-Authentication ===")
    print(f"Connecting to Chrome at {CDP_URL}...")

    async with async_playwright() as pw:
        try:
            browser = await pw.chromium.connect_over_cdp(CDP_URL)
        except Exception as e:
            print(f"ERROR: Cannot connect to Chrome at {CDP_URL}")
            print(f"  {e}")
            print("\nMake sure Chrome is running with --remote-debugging-port=9222")
            print("Or run: python3 scripts/remote_auth.py")
            sys.exit(1)

        print(f"✅ Connected to Chrome ({len(browser.contexts)} context(s))")

        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await ctx.new_page()

        print(f"Navigating to {REGENT_OA_LOGIN}...")
        await page.goto(REGENT_OA_LOGIN)
        print("Page loaded. Complete login in the browser window (including any CAPTCHA).")

        cookies = await wait_for_login(page)
        if not cookies:
            print("No cookies captured. Exiting.")
            await browser.close()
            sys.exit(1)

        save_cookies(cookies)

        auth_cookie = next((c for c in cookies if c["name"] == "ASPXAUTH"), None)
        expiry_iso = ""
        if auth_cookie and auth_cookie.get("expires", 0) > 0:
            expiry_iso = datetime.fromtimestamp(
                auth_cookie["expires"], tz=timezone.utc
            ).isoformat()

        update_hale_state(expiry_iso)

        print(f"\n✅ Done — {len(cookies)} rssc.com cookies saved to {len(COOKIE_TARGETS)} files.")
        print("Regent OA session is fresh. Keepalive timer will maintain it.")
        print("Optionally also run: python3 scripts/regent_firefox_cookie_capture.py --check")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
