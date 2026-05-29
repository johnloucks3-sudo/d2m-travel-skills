#!/usr/bin/env python3
"""
portal_keepalive.py — Portal Session Keeper
Keeps authenticated sessions warm for D2M travel portals.
Runs daily via cron. Re-auths any portal whose cookies are stale or expiring.

Portals managed:
  - centrav       (creds/centrav_cookies.json)
  - agent_universe (creds/agent_universe_cookies.json)
  - room_res      (creds/room_res_cookies.json)

Usage:
  python3 scripts/portal_keepalive.py              # check + refresh all
  python3 scripts/portal_keepalive.py --portal centrav  # one portal only
  python3 scripts/portal_keepalive.py --status     # print expiry report only
"""
import asyncio
import json
import logging
import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from playwright.async_api import async_playwright

THUNDERBIRD = Path("/home/john/Thunderbird")
CREDS_DIR = THUNDERBIRD / "creds"
CONFIG_FILE = THUNDERBIRD / "config" / "portal_creds.json"
LOG_FILE = THUNDERBIRD / "logs" / "portal_keepalive.log"

WARN_HOURS = 48   # flag cookies expiring within this many hours
STALE_HOURS = 1   # treat session as stale if expires within this many hours

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("portal_keepalive")


# ---------------------------------------------------------------------------
# Cookie utilities
# ---------------------------------------------------------------------------

def load_cookies(path: Path) -> list:
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text())
    except Exception:
        return []


def save_cookies(path: Path, cookies: list) -> None:
    path.write_text(json.dumps(cookies, indent=2))


def cookie_expiry_status(cookies: list) -> dict:
    """Return dict with soonest_expiry (Unix float), hours_left, status."""
    now = datetime.now(timezone.utc).timestamp()
    soonest = None
    for c in cookies:
        exp = c.get("expires")
        if exp and exp > 0:
            if soonest is None or exp < soonest:
                soonest = exp
    if soonest is None:
        return {"soonest_expiry": None, "hours_left": None, "status": "SESSION_ONLY"}
    hours_left = (soonest - now) / 3600
    if hours_left < 0:
        status = "EXPIRED"
    elif hours_left < STALE_HOURS:
        status = "STALE"
    elif hours_left < WARN_HOURS:
        status = "WARN"
    else:
        status = "OK"
    return {
        "soonest_expiry": soonest,
        "hours_left": round(hours_left, 1),
        "status": status,
        "expires_at": datetime.fromtimestamp(soonest, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }


# ---------------------------------------------------------------------------
# Portal definitions
# ---------------------------------------------------------------------------

def get_creds() -> dict:
    return json.loads(CONFIG_FILE.read_text())


async def refresh_centrav(page, creds: dict) -> list:
    """Re-auth Centrav and return fresh cookies."""
    log.info("Centrav: navigating to login...")
    await page.goto("https://www.centrav.com/login", wait_until="networkidle", timeout=30000)
    await page.fill('input[type="email"], input[name="email"]', creds["email"])
    await page.fill('input[type="password"], input[name="password"]', creds["password"])
    await page.click('button[type="submit"], input[type="submit"]')
    await page.wait_for_url("**/dashboard**", timeout=20000)
    raw = await page.context.cookies()
    # Filter to centrav.com only
    cookies = [c for c in raw if "centrav" in c.get("domain", "")]
    log.info(f"Centrav: captured {len(cookies)} cookies after re-auth")
    return cookies


async def refresh_agent_universe(page, creds: dict) -> list:
    """Re-auth Agent Universe and return fresh cookies."""
    log.info("Agent Universe: navigating to login...")
    await page.goto(
        "https://affiliateus.agentuniverse.com/?fromLogin=1",
        wait_until="networkidle",
        timeout=30000,
    )
    await page.get_by_role("textbox", name="Username or Email").fill(creds["email"])
    await page.get_by_role("textbox", name="Password").fill(creds["password"])
    await page.get_by_role("button", name="Sign In").click()
    await page.wait_for_url("**/agentuniverse.com/**", timeout=20000)
    await page.wait_for_load_state("networkidle", timeout=20000)
    raw = await page.context.cookies()
    cookies = [c for c in raw if "agentuniverse" in c.get("domain", "") or "travelleaders" in c.get("domain", "")]
    log.info(f"Agent Universe: captured {len(cookies)} cookies after re-auth")
    return cookies


async def refresh_room_res(page, creds: dict) -> list:
    """Re-auth room-res.com and return fresh cookies."""
    log.info("Room-res: navigating to login...")
    await page.goto("https://room-res.com/login", wait_until="networkidle", timeout=30000)
    # Try common selectors
    try:
        await page.fill('input[type="email"], input[name="email"], input[id*="email"]', creds["email"])
        await page.fill('input[type="password"]', creds["password"])
        await page.click('button[type="submit"], input[type="submit"]')
        await page.wait_for_load_state("networkidle", timeout=20000)
    except Exception as e:
        log.warning(f"Room-res login attempt failed: {e}")
    raw = await page.context.cookies()
    cookies = [c for c in raw if "room-res" in c.get("domain", "")]
    log.info(f"Room-res: captured {len(cookies)} cookies")
    return cookies


async def ping_centrav(page, cookies: list) -> bool:
    """Ping Centrav with saved cookies — returns True if still authenticated."""
    await page.context.add_cookies(cookies)
    resp = await page.goto("https://www.centrav.com/dashboard", timeout=15000)
    return resp and "login" not in page.url


async def ping_agent_universe(page, cookies: list) -> bool:
    """Ping Agent Universe — returns True if still authenticated."""
    await page.context.add_cookies(cookies)
    resp = await page.goto("https://affiliateus.agentuniverse.com/", timeout=15000)
    # If we get redirected to login, session is dead
    return resp and "login" not in page.url.lower() and "agentprofiler" not in page.url.lower()


# ---------------------------------------------------------------------------
# Portal registry
# ---------------------------------------------------------------------------

PORTALS = {
    "centrav": {
        "cookie_file": CREDS_DIR / "centrav_cookies.json",
        "creds_key": "centrav",
        "ping_fn": ping_centrav,
        "refresh_fn": refresh_centrav,
        "description": "Centrav B2B flight booking",
    },
    "agent_universe": {
        "cookie_file": CREDS_DIR / "agent_universe_cookies.json",
        "creds_key": "agent_universe",
        "ping_fn": ping_agent_universe,
        "refresh_fn": refresh_agent_universe,
        "description": "TLN Agent Universe (Cruise Complete, SNAP, Promotions)",
    },
    "room_res": {
        "cookie_file": CREDS_DIR / "room_res_cookies.json",
        "creds_key": "room_res",
        "ping_fn": None,  # analytics cookies only — no session ping needed
        "refresh_fn": refresh_room_res,
        "description": "Room-res hotel booking",
    },
}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def run(portals_to_check: list, status_only: bool) -> None:
    creds = get_creds()
    report = {}

    for name in portals_to_check:
        portal = PORTALS[name]
        cookies = load_cookies(portal["cookie_file"])
        status = cookie_expiry_status(cookies)
        report[name] = status
        log.info(f"{name}: {status['status']} | {status.get('hours_left', '?')}h left | {status.get('expires_at', 'session-only')}")

    if status_only:
        print("\n=== PORTAL SESSION STATUS ===")
        for name, s in report.items():
            print(f"  {name:20s} {s['status']:12s} {s.get('expires_at', 'session-only')}")
        return

    needs_refresh = [
        name for name in portals_to_check
        if report[name]["status"] in ("EXPIRED", "STALE", "SESSION_ONLY")
        and PORTALS[name]["refresh_fn"] is not None
        and PORTALS[name]["cookie_file"] is not None
    ]

    needs_warn = [
        name for name in portals_to_check
        if report[name]["status"] == "WARN"
    ]

    if needs_warn:
        log.warning(f"Cookies expiring soon (< {WARN_HOURS}h): {needs_warn}")

    if not needs_refresh:
        log.info("All portals OK — no refresh needed.")
        return

    log.info(f"Refreshing: {needs_refresh}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        for name in needs_refresh:
            portal = PORTALS[name]
            portal_creds = creds.get(portal["creds_key"], {})
            context = await browser.new_context()
            page = await context.new_page()
            try:
                fresh_cookies = await portal["refresh_fn"](page, portal_creds)
                if fresh_cookies:
                    save_cookies(portal["cookie_file"], fresh_cookies)
                    log.info(f"{name}: refreshed OK — {len(fresh_cookies)} cookies saved to {portal['cookie_file'].name}")
                else:
                    log.error(f"{name}: refresh returned no cookies — manual re-auth may be needed")
            except Exception as e:
                log.error(f"{name}: refresh FAILED — {e}")
            finally:
                await context.close()
        await browser.close()


def main():
    parser = argparse.ArgumentParser(description="D2M Portal Session Keepalive")
    parser.add_argument("--portal", choices=list(PORTALS.keys()), help="Refresh one portal only")
    parser.add_argument("--status", action="store_true", help="Print expiry status only, no refresh")
    args = parser.parse_args()

    portals = [args.portal] if args.portal else list(PORTALS.keys())
    asyncio.run(run(portals, args.status))


if __name__ == "__main__":
    main()
