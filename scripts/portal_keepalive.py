#!/usr/bin/env python3
"""
portal_keepalive.py — Portal Session Keeper
Keeps authenticated sessions warm for D2M travel portals.
Runs via systemd timer. Re-auths any portal whose cookies are stale or expiring.

Portals managed:
  - centrav        (creds/centrav_cookies.json)
  - agent_universe (creds/agent_universe_cookies.json)
  - room_res       (creds/room_res_cookies.json)
  - silversea      (creds/silversea_cookies.json)
  - seabourn       (creds/seabourn_cookies.json)
  - windstar       (creds/windstar_cookies.json)
  - princess       (creds/princess_cookies.json)
  - carnival       (creds/carnival_cookies.json)
  - kensington     (creds/kensington_cookies.json)
  - agentmax       (creds/agentmax_cookies.json)
  - globus         (creds/globus_cookies.json)
  - atlas          (creds/atlas_cookies.json)
  - explora        (creds/explora_cookies.json)

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
    return resp and "login" not in page.url.lower() and "agentprofiler" not in page.url.lower()


# ---------------------------------------------------------------------------
# Generic simple-login refreshers
# ---------------------------------------------------------------------------

async def refresh_simple_login(page, creds: dict, login_url: str, domain_filter: str, success_indicator: str = "") -> list:
    """Generic refresh for portals with standard email/username + password login forms."""
    log.info(f"Navigating to {login_url}...")
    await page.goto(login_url, wait_until="networkidle", timeout=30000)
    await page.wait_for_timeout(2000)

    email_val = creds.get("email") or creds.get("login") or ""
    password_val = creds.get("password") or ""

    if email_val:
        try:
            await page.fill('input[type="email"], input[name="email"], input[id*="email"]', email_val)
        except Exception:
            await page.fill('input[type="text"], input[name="login"], input[id*="login"]', email_val)
    else:
        login_val = creds.get("login", "")
        await page.fill('input[type="text"], input[name="login"]', login_val)

    await page.fill('input[type="password"]', password_val)
    await page.click('button[type="submit"], input[type="submit"]')
    await page.wait_for_load_state("networkidle", timeout=20000)
    await page.wait_for_timeout(2000)

    raw = await page.context.cookies()
    cookies = [c for c in raw if domain_filter in c.get("domain", "")]
    log.info(f"Captured {len(cookies)} cookies")
    return cookies


async def refresh_silversea(page, creds: dict) -> list:
    """Re-auth Silversea agency portal."""
    return await refresh_simple_login(
        page, creds,
        login_url="https://my.silversea.com/Account/Login",
        domain_filter="silversea",
    )


async def refresh_seabourn(page, creds: dict) -> list:
    """Re-auth Seabourn booking portal."""
    return await refresh_simple_login(
        page, creds,
        login_url="https://book2.seabourn.com",
        domain_filter="seabourn",
    )


async def refresh_windstar(page, creds: dict) -> list:
    """Re-auth Windstar advisor hub."""
    return await refresh_simple_login(
        page, creds,
        login_url="https://advisorhub.windstarcruises.com",
        domain_filter="windstar",
    )


async def refresh_princess(page, creds: dict) -> list:
    """Re-auth Princess booking portal."""
    return await refresh_simple_login(
        page, creds,
        login_url="https://book.princess.com",
        domain_filter="princess",
    )


async def refresh_carnival(page, creds: dict) -> list:
    """Re-auth Carnival CruisingPower."""
    return await refresh_simple_login(
        page, creds,
        login_url="https://secure.cruisingpower.com",
        domain_filter="cruisingpower",
    )


async def refresh_kensington(page, creds: dict) -> list:
    """Re-auth Kensington Tours FIT portal."""
    return await refresh_simple_login(
        page, creds,
        login_url="https://fit.kensingtontours.com",
        domain_filter="kensingtontours",
    )


async def refresh_agentmax(page, creds: dict) -> list:
    """Re-auth Allianz AgentMax."""
    return await refresh_simple_login(
        page, creds,
        login_url="https://www.agentmaxonline.com/agentmaxweb/agentportal/index.html",
        domain_filter="agentmaxonline",
    )


async def refresh_globus(page, creds: dict) -> list:
    """Re-auth Globus family portal."""
    return await refresh_simple_login(
        page, creds,
        login_url="https://accounts.globusfamily.com",
        domain_filter="globusfamily",
    )


async def refresh_atlas(page, creds: dict) -> list:
    """Re-auth Atlas Ocean Voyages agent portal."""
    return await refresh_simple_login(
        page, creds,
        login_url="https://agents.atlasoceanvoyages.com",
        domain_filter="atlasoceanvoyages",
    )


async def refresh_explora(page, creds: dict) -> list:
    """Re-auth Explora Journeys agent portal."""
    return await refresh_simple_login(
        page, creds,
        login_url="https://agent.explorajourneys.com",
        domain_filter="explorajourneys",
    )


async def ping_magtap(page, cookies: list) -> bool:
    """Ping MAGTAP dashboard — returns True if PHPSESSID is still valid."""
    await page.context.add_cookies(cookies)
    resp = await page.goto("https://tap.myagentgenie.com/dashboard", timeout=15000)
    return resp and "login" not in page.url.lower()


async def refresh_magtap(page, creds: dict) -> list:
    """Re-auth MAGTAP (Outside Agents TAP portal) via Google SSO login."""
    log.info("MAGTAP: navigating to login...")
    await page.goto("https://tap.myagentgenie.com", wait_until="networkidle", timeout=30000)
    await page.wait_for_timeout(2000)
    try:
        # MAGTAP uses Google OAuth — fill Google email/password
        await page.fill('input[type="email"]', creds.get("email", ""), timeout=5000)
        await page.click('button, input[type="submit"]', timeout=3000)
        await page.wait_for_timeout(1500)
        await page.fill('input[type="password"]', creds.get("password", ""), timeout=5000)
        await page.click('button, input[type="submit"]', timeout=3000)
        await page.wait_for_load_state("networkidle", timeout=20000)
    except Exception as e:
        log.warning(f"MAGTAP login attempt: {e}")
    raw = await page.context.cookies()
    cookies = [c for c in raw if "myagentgenie" in c.get("domain", "")]
    log.info(f"MAGTAP: captured {len(cookies)} cookies")
    return cookies


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
        "ping_fn": None,
        "refresh_fn": refresh_room_res,
        "description": "Room-res hotel booking",
    },
    "silversea": {
        "cookie_file": CREDS_DIR / "silversea_cookies.json",
        "creds_key": "silversea",
        "ping_fn": None,
        "refresh_fn": refresh_silversea,
        "description": "Silversea agency portal",
    },
    "seabourn": {
        "cookie_file": CREDS_DIR / "seabourn_cookies.json",
        "creds_key": "seabourn",
        "ping_fn": None,
        "refresh_fn": refresh_seabourn,
        "description": "Seabourn booking portal",
    },
    "windstar": {
        "cookie_file": CREDS_DIR / "windstar_cookies.json",
        "creds_key": "windstar",
        "ping_fn": None,
        "refresh_fn": refresh_windstar,
        "description": "Windstar advisor hub",
    },
    "princess": {
        "cookie_file": CREDS_DIR / "princess_cookies.json",
        "creds_key": "princess",
        "ping_fn": None,
        "refresh_fn": refresh_princess,
        "description": "Princess booking portal",
    },
    "carnival": {
        "cookie_file": CREDS_DIR / "carnival_cookies.json",
        "creds_key": "carnival_cruisingpower",
        "ping_fn": None,
        "refresh_fn": refresh_carnival,
        "description": "Carnival CruisingPower (Carnival/HAL/Costa)",
    },
    "kensington": {
        "cookie_file": CREDS_DIR / "kensington_cookies.json",
        "creds_key": "kensington_tours",
        "ping_fn": None,
        "refresh_fn": refresh_kensington,
        "description": "Kensington Tours FIT portal",
    },
    "agentmax": {
        "cookie_file": CREDS_DIR / "agentmax_cookies.json",
        "creds_key": "agentmax_allianz",
        "ping_fn": None,
        "refresh_fn": refresh_agentmax,
        "description": "Allianz AgentMax travel insurance",
    },
    "globus": {
        "cookie_file": CREDS_DIR / "globus_cookies.json",
        "creds_key": "globus",
        "ping_fn": None,
        "refresh_fn": refresh_globus,
        "description": "Globus Family (Globus/Cosmos/Monograms/Avalon)",
    },
    "atlas": {
        "cookie_file": CREDS_DIR / "atlas_cookies.json",
        "creds_key": "atlas_ocean",
        "ping_fn": None,
        "refresh_fn": refresh_atlas,
        "description": "Atlas Ocean Voyages agent portal",
    },
    "explora": {
        "cookie_file": CREDS_DIR / "explora_cookies.json",
        "creds_key": "explora_journeys",
        "ping_fn": None,
        "refresh_fn": refresh_explora,
        "description": "Explora Journeys agent portal",
    },
    "magtap": {
        "cookie_file": CREDS_DIR / "magtap_cookies.json",
        "creds_key": "magtap",
        "ping_fn": ping_magtap,
        "refresh_fn": refresh_magtap,
        "description": "Outside Agents TAP/MAGCRM/TESS/Odysseus portal",
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
