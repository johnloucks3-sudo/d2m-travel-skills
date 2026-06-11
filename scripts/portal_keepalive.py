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
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

from playwright.async_api import async_playwright

# ---------------------------------------------------------------------------
# Alert chain — Telegram to Commander when self-heal fails 3x
# ---------------------------------------------------------------------------

FAIL_STATE_FILE = Path("/home/john/Thunderbird/logs/portal_fail_counts.json")
ALERT_THRESHOLD = 3  # consecutive failures before Telegram alert

def _load_fail_counts() -> dict:
    if FAIL_STATE_FILE.exists():
        try:
            return json.loads(FAIL_STATE_FILE.read_text())
        except Exception:
            pass
    return {}

def _save_fail_counts(counts: dict) -> None:
    FAIL_STATE_FILE.parent.mkdir(exist_ok=True)
    FAIL_STATE_FILE.write_text(json.dumps(counts, indent=2))

def _send_telegram_alert(message: str) -> None:
    """Send alert to Commander via D2MC2C bot."""
    try:
        env_file = Path("/home/john/Thunderbird/config/telegram_gw.env")
        token = None
        chat_id = None
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("TELEGRAM_D2MC2C_TOKEN="):
                    token = line.split("=", 1)[1].strip()
                elif line.startswith("TELEGRAM_COMMANDER_ID="):
                    chat_id = line.split("=", 1)[1].strip()
        if not token or not chat_id:
            return
        payload = urllib.parse.urlencode({
            "chat_id": chat_id,
            "text": f"🔴 THUNDERBIRD ALERT\n{message}",
            "parse_mode": "HTML",
        }).encode()
        urllib.request.urlopen(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=payload,
            timeout=10,
        )
    except Exception as exc:
        log.warning(f"Telegram alert send failed: {exc}")

def record_portal_failure(portal_name: str) -> None:
    counts = _load_fail_counts()
    counts[portal_name] = counts.get(portal_name, 0) + 1
    _save_fail_counts(counts)
    if counts[portal_name] >= ALERT_THRESHOLD:
        _send_telegram_alert(
            f"Portal <b>{portal_name}</b> has failed to refresh "
            f"{counts[portal_name]} consecutive times.\n"
            f"Manual re-authentication may be required.\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M MDT')}"
        )
        log.error(f"{portal_name}: ALERT SENT — {counts[portal_name]} consecutive failures")

def record_portal_success(portal_name: str) -> None:
    counts = _load_fail_counts()
    if counts.pop(portal_name, None) is not None:
        _save_fail_counts(counts)
        log.info(f"{portal_name}: failure counter reset after successful refresh")

THUNDERBIRD = Path("/home/john/Thunderbird")
CREDS_DIR = THUNDERBIRD / "creds"
CONFIG_FILE = THUNDERBIRD / "config" / "portal_creds.json"
LOG_FILE = THUNDERBIRD / "logs" / "portal_keepalive.log"

WARN_HOURS = 48   # flag cookies expiring within this many hours
STALE_HOURS = 4   # treat session as stale if expires within this many hours

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
        data = json.loads(path.read_text())
        # Handle nested format: {"_account": ..., "cookies": [...]}
        if isinstance(data, dict) and "cookies" in data:
            return data["cookies"]
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []


def save_cookies(path: Path, cookies: list) -> None:
    path.write_text(json.dumps(cookies, indent=2))


def cookie_expiry_status(cookies: list, auth_cookie_names: list = None, auth_domain: str = None) -> dict:
    """Return session health based on the auth-gate cookie, not the longest-lived one.

    Bug fixed 2026-06-11 (Sterling/A7): prior logic used the longest-lived cookie.
    This masked expired session cookies behind long-lived analytics cookies (e.g.
    _GRECAPTCHA from google.com, 4296h) or tracking beacons, reporting OK when the
    actual session was dead.

    Priority order:
      1. Named auth cookies (auth_cookie_names) scoped to auth_domain — exact match.
      2. Cookies that are httpOnly=True AND from auth_domain — likely auth tokens.
      3. Shortest-expiring non-ephemeral cookie from auth_domain only.
      4. Shortest-expiring non-ephemeral cookie across all domains (legacy fallback).

    Cookies with expiry > 10 years from now are treated as tracking beacons and
    skipped in all passes (they are never session auth tokens).
    """
    now = datetime.now(timezone.utc).timestamp()
    TEN_YEARS = 10 * 365 * 24 * 3600
    # Pre-epoch stale timestamps (< year 2000) are corrupt stored cookies — ignore.
    EPOCH_2000 = 946684800.0

    def _is_beacon(exp):
        """True if expiry looks like a long-lived tracking beacon, not a session token."""
        return exp is not None and exp > (now + TEN_YEARS)

    def _domain_match(cookie_domain, target_domain):
        if not target_domain:
            return True
        d = cookie_domain.lstrip(".")
        t = target_domain.lstrip(".")
        return d == t or d.endswith("." + t)

    # Pass 1: named auth cookies on auth_domain
    if auth_cookie_names and auth_domain:
        for c in cookies:
            name = c.get("name", "")
            exp = c.get("expires")
            if name.upper() in [n.upper() for n in auth_cookie_names]:
                if _domain_match(c.get("domain", ""), auth_domain):
                    if exp is None or exp <= 0:
                        # Session cookie (no persistent expiry) — treat as unknown/stale
                        return {"soonest_expiry": None, "hours_left": None, "status": "SESSION_ONLY",
                                "auth_cookie": name}
                    hours_left = (exp - now) / 3600
                    status = "EXPIRED" if hours_left < 0 else (
                        "STALE" if hours_left < STALE_HOURS else (
                        "WARN" if hours_left < WARN_HOURS else "OK"
                    ))
                    return {
                        "soonest_expiry": exp,
                        "hours_left": round(hours_left, 1),
                        "status": status,
                        "expires_at": datetime.fromtimestamp(exp, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                        "auth_cookie": name,
                    }

    # Pass 2: httpOnly cookies from auth_domain (likely session tokens)
    http_only_exp = None
    http_only_name = None
    if auth_domain:
        for c in cookies:
            if not c.get("httpOnly"):
                continue
            if not _domain_match(c.get("domain", ""), auth_domain):
                continue
            exp = c.get("expires")
            if not exp or exp < EPOCH_2000 or _is_beacon(exp):
                continue
            if http_only_exp is None or exp < http_only_exp:
                http_only_exp = exp
                http_only_name = c.get("name", "?")

    if http_only_exp is not None:
        hours_left = (http_only_exp - now) / 3600
        status = "EXPIRED" if hours_left < 0 else (
            "STALE" if hours_left < STALE_HOURS else (
            "WARN" if hours_left < WARN_HOURS else "OK"
        ))
        return {
            "soonest_expiry": http_only_exp,
            "hours_left": round(hours_left, 1),
            "status": status,
            "expires_at": datetime.fromtimestamp(http_only_exp, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "auth_cookie": http_only_name,
        }

    # Pass 3: shortest-expiring non-beacon from auth_domain
    domain_exp = None
    domain_name = None
    if auth_domain:
        for c in cookies:
            if not _domain_match(c.get("domain", ""), auth_domain):
                continue
            exp = c.get("expires")
            if not exp or exp < EPOCH_2000 or _is_beacon(exp):
                continue
            if domain_exp is None or exp < domain_exp:
                domain_exp = exp
                domain_name = c.get("name", "?")

    if domain_exp is not None:
        hours_left = (domain_exp - now) / 3600
        status = "EXPIRED" if hours_left < 0 else (
            "STALE" if hours_left < STALE_HOURS else (
            "WARN" if hours_left < WARN_HOURS else "OK"
        ))
        return {
            "soonest_expiry": domain_exp,
            "hours_left": round(hours_left, 1),
            "status": status,
            "expires_at": datetime.fromtimestamp(domain_exp, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "auth_cookie": domain_name,
        }

    # Pass 4: legacy fallback — shortest non-beacon across all domains
    fallback_exp = None
    fallback_name = None
    for c in cookies:
        exp = c.get("expires")
        if not exp or exp < EPOCH_2000 or _is_beacon(exp):
            continue
        if fallback_exp is None or exp < fallback_exp:
            fallback_exp = exp
            fallback_name = c.get("name", "?")

    if fallback_exp is None:
        return {"soonest_expiry": None, "hours_left": None, "status": "SESSION_ONLY"}

    hours_left = (fallback_exp - now) / 3600
    status = "EXPIRED" if hours_left < 0 else (
        "STALE" if hours_left < STALE_HOURS else (
        "WARN" if hours_left < WARN_HOURS else "OK"
    ))
    return {
        "soonest_expiry": fallback_exp,
        "hours_left": round(hours_left, 1),
        "status": status,
        "expires_at": datetime.fromtimestamp(fallback_exp, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "auth_cookie": fallback_name,
    }


# ---------------------------------------------------------------------------
# Portal definitions
# ---------------------------------------------------------------------------

def get_creds() -> dict:
    return json.loads(CONFIG_FILE.read_text())


async def _dismiss_overlays(page) -> None:
    """Dismiss common cookie consent banners and modals before interacting with forms."""
    overlay_selectors = [
        'button[id*="accept"], button[class*="accept"]',
        'button[id*="consent"], button[class*="consent"]',
        'button[id*="agree"], button[class*="agree"]',
        'button[id*="close"], button[class*="close"]',
        'button[aria-label*="close"], button[aria-label*="Close"]',
        '[class*="cookie"] button, [id*="cookie"] button',
        '[class*="gdpr"] button, [id*="gdpr"] button',
        '[class*="modal"] button[class*="close"]',
        '[class*="overlay"] button[class*="close"]',
    ]
    for sel in overlay_selectors:
        try:
            btn = page.locator(sel).first
            if await btn.is_visible(timeout=500):
                await btn.click(timeout=1000)
                await page.wait_for_timeout(300)
                break
        except Exception:
            pass
    # Also try Escape key
    try:
        await page.keyboard.press("Escape")
    except Exception:
        pass
    await page.wait_for_timeout(500)


async def _fill_login_form(page, email_val: str, password_val: str) -> None:
    """Fill email/username + password — tries multiple selectors, falls back to force=True."""
    email_selectors = [
        'input[type="email"]',
        'input[name="email"]',
        'input[id*="email"]',
        'input[name="username"]',
        'input[id*="username"]',
        'input[type="text"]',
    ]
    filled = False
    for sel in email_selectors:
        try:
            loc = page.locator(sel).first
            if await loc.count() > 0:
                await loc.fill(email_val, timeout=5000)
                filled = True
                break
        except Exception:
            try:
                loc = page.locator(sel).first
                await loc.fill(email_val, timeout=3000, force=True)
                filled = True
                break
            except Exception:
                pass
    if not filled:
        raise RuntimeError(f"Could not fill email field for user: {email_val[:20]}...")

    pw_loc = page.locator('input[type="password"]').first
    await pw_loc.fill(password_val, timeout=5000)


async def refresh_centrav(page, creds: dict) -> list:
    """Re-auth Centrav and return fresh cookies."""
    log.info("Centrav: navigating to login...")
    await page.goto("https://www.centrav.com/login", wait_until="networkidle", timeout=30000)
    await _dismiss_overlays(page)
    await _fill_login_form(page, creds["email"], creds["password"])
    await page.click('button[type="submit"], input[type="submit"]')
    await page.wait_for_load_state("networkidle", timeout=25000)
    raw = await page.context.cookies()
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
    await _dismiss_overlays(page)
    try:
        await page.get_by_role("textbox", name="Username or Email").fill(creds["email"])
        await page.get_by_role("textbox", name="Password").fill(creds["password"])
        await page.get_by_role("button", name="Sign In").click()
    except Exception:
        await _fill_login_form(page, creds["email"], creds["password"])
        await page.click('button[type="submit"], input[type="submit"]')
    await page.wait_for_load_state("networkidle", timeout=25000)
    await page.wait_for_timeout(2000)
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
    await page.wait_for_timeout(1500)
    await _dismiss_overlays(page)

    email_val = creds.get("email") or creds.get("login") or ""
    password_val = creds.get("password") or ""

    await _fill_login_form(page, email_val, password_val)
    try:
        await page.click('button[type="submit"], input[type="submit"]', timeout=5000)
    except Exception:
        await page.keyboard.press("Enter")
    await page.wait_for_load_state("networkidle", timeout=25000)
    await page.wait_for_timeout(2000)

    raw = await page.context.cookies()
    cookies = [c for c in raw if domain_filter in c.get("domain", "")]
    log.info(f"Captured {len(cookies)} cookies")
    return cookies


async def refresh_silversea(page, creds: dict) -> list:
    """Re-auth Silversea agency portal.
    MyBookings → OAuth redirect → /account/logon form.
    Login inputs: #email-input-login + #password-input-login
    """
    log.info("Silversea: navigating to login...")
    # Use domcontentloaded — OAuth redirect loop never settles to networkidle
    await page.goto("https://my.silversea.com/MyBookings", wait_until="domcontentloaded", timeout=30000)
    # Wait for the redirect to settle and login form to appear
    try:
        await page.wait_for_selector('#email-input-login', timeout=15000)
    except Exception:
        await page.wait_for_timeout(5000)
    await _dismiss_overlays(page)
    try:
        await page.fill('#email-input-login', creds.get("email", ""), timeout=8000)
        await page.fill('#password-input-login', creds.get("password", ""), timeout=5000)
    except Exception:
        await _fill_login_form(page, creds.get("email", ""), creds.get("password", ""))
    await page.click('button[type="submit"], input[type="submit"]', timeout=5000)
    try:
        await page.wait_for_load_state("networkidle", timeout=20000)
    except Exception:
        await page.wait_for_timeout(5000)
    raw = await page.context.cookies()
    cookies = [c for c in raw if "silversea" in c.get("domain", "")]
    log.info(f"Silversea: captured {len(cookies)} cookies")
    return cookies


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
    # Try both known URLs — agent subdomain DNS has been intermittent
    for url in ["https://travel.explorajourneys.com/login", "https://www.explorajourneys.com/us/en/travel-agents"]:
        try:
            return await refresh_simple_login(
                page, creds,
                login_url=url,
                domain_filter="explorajourneys",
            )
        except Exception:
            continue
    return []


async def refresh_regent(page, creds: dict) -> list:
    """Re-auth Regent Seven Seas portal.
    rssc.com SPA: all inputs are CSS-hidden. Use JS dispatch to submit.
    Fields: #account-email, #account-password
    """
    log.info("Regent: navigating to login...")
    await page.goto("https://www.rssc.com/agent/dashboard/#myBookings", wait_until="networkidle", timeout=30000)
    await page.wait_for_timeout(3000)

    email = creds.get("email", "")
    password = creds.get("password", "")
    if not email or not password:
        log.error("Regent: missing email/password credentials")
        return []

    try:
        # All fields are CSS-hidden — fill with force=True, submit via JS
        await page.locator('#account-email').first.fill(email, force=True, timeout=5000)
        await page.locator('#account-password, input[type="password"]').first.fill(
            password, force=True, timeout=5000
        )
        # Trigger React-compatible change events + submit via JS
        await page.evaluate("""() => {
            const email = document.querySelector('#account-email');
            const pw = document.querySelector('#account-password') || document.querySelector('input[type="password"]');
            if (email) email.dispatchEvent(new Event('input', {bubbles: true}));
            if (email) email.dispatchEvent(new Event('change', {bubbles: true}));
            if (pw) pw.dispatchEvent(new Event('input', {bubbles: true}));
            if (pw) pw.dispatchEvent(new Event('change', {bubbles: true}));
            const btn = document.querySelector('button[type="submit"]');
            if (btn) btn.click();
        }""")
        await page.wait_for_load_state("networkidle", timeout=25000)
        await page.wait_for_timeout(2000)
    except Exception as e:
        log.warning(f"Regent login attempt failed: {e}")
        return []

    raw = await page.context.cookies()
    cookies = [c for c in raw if "rssc" in c.get("domain", "")]
    log.info(f"Regent: captured {len(cookies)} cookies")
    return cookies


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


async def refresh_perx(page, creds: dict) -> list:
    """Re-auth Perx.com ground transfers portal."""
    log.info("Perx: navigating to login...")
    await page.goto("https://www.perx.com/login", wait_until="networkidle", timeout=30000)
    await _dismiss_overlays(page)
    try:
        await page.fill('input[type="email"], input[name="email"]', creds.get("email", ""), timeout=8000)
        await page.fill('input[type="password"]', creds.get("password", ""), timeout=5000)
        await page.click('button[type="submit"], input[type="submit"]', timeout=5000)
        await page.wait_for_load_state("networkidle", timeout=25000)
    except Exception as e:
        log.warning(f"Perx login attempt: {e}")
    raw = await page.context.cookies()
    cookies = [c for c in raw if "perx" in c.get("domain", "")]
    log.info(f"Perx: captured {len(cookies)} cookies")
    return cookies


# ---------------------------------------------------------------------------
# Portal registry
# ---------------------------------------------------------------------------

PORTALS = {
    "centrav": {
        "cookie_file": CREDS_DIR / "centrav_cookies.json",
        "creds_key": "centrav",
        "creds_field": None,
        "ping_fn": ping_centrav,
        "refresh_fn": refresh_centrav,
        "browser_type": "chromium",
        "description": "Centrav B2B flight booking",
        "auth_cookie_names": ["laravel_session"],   # A7 2026-06-11: verified auth gate
        "auth_domain": "centrav.com",
    },
    "agent_universe": {
        "cookie_file": CREDS_DIR / "agent_universe_cookies.json",
        "creds_key": "agent_universe",
        "creds_field": None,
        "ping_fn": ping_agent_universe,
        "refresh_fn": refresh_agent_universe,
        "browser_type": "chromium",
        "description": "TLN Agent Universe (Cruise Complete, SNAP, Promotions)",
    },
    "room_res": {
        "cookie_file": CREDS_DIR / "room_res_cookies.json",
        "creds_key": "room_res",
        "creds_field": None,
        "ping_fn": None,
        "refresh_fn": refresh_room_res,
        "browser_type": "chromium",
        "description": "Room-res hotel booking",
    },
    "silversea": {
        "cookie_file": CREDS_DIR / "silversea_cookies.json",
        "creds_key": "silversea",
        "creds_field": None,
        "ping_fn": None,
        "refresh_fn": refresh_silversea,
        "browser_type": "chromium",
        "description": "Silversea agency portal",
    },
    "seabourn": {
        "cookie_file": CREDS_DIR / "seabourn_cookies.json",
        "creds_key": "seabourn",
        "creds_field": None,
        "ping_fn": None,
        "refresh_fn": refresh_seabourn,
        "browser_type": "chromium",
        "description": "Seabourn booking portal",
    },
    "windstar": {
        "cookie_file": CREDS_DIR / "windstar_cookies.json",
        "creds_key": "windstar",
        "creds_field": None,
        "ping_fn": None,
        "refresh_fn": refresh_windstar,
        "browser_type": "chromium",
        "description": "Windstar advisor hub",
    },
    "princess": {
        "cookie_file": CREDS_DIR / "princess_cookies.json",
        "creds_key": "princess",
        "creds_field": None,
        "ping_fn": None,
        "refresh_fn": refresh_princess,
        "browser_type": "chromium",
        "description": "Princess booking portal",
    },
    "carnival": {
        "cookie_file": CREDS_DIR / "carnival_cookies.json",
        "creds_key": "carnival_cruisingpower",
        "creds_field": None,
        "ping_fn": None,
        "refresh_fn": refresh_carnival,
        "browser_type": "chromium",
        "description": "Carnival CruisingPower (Carnival/HAL/Costa)",
    },
    "kensington": {
        "cookie_file": CREDS_DIR / "kensington_cookies.json",
        "creds_key": "kensington_tours",
        "creds_field": None,
        "ping_fn": None,
        "refresh_fn": refresh_kensington,
        "browser_type": "chromium",
        "description": "Kensington Tours FIT portal",
    },
    "agentmax": {
        "cookie_file": CREDS_DIR / "agentmax_cookies.json",
        "creds_key": "agentmax_allianz",
        "creds_field": None,
        "ping_fn": None,
        "refresh_fn": refresh_agentmax,
        "browser_type": "chromium",
        "description": "Allianz AgentMax travel insurance",
    },
    "globus": {
        "cookie_file": CREDS_DIR / "globus_cookies.json",
        "creds_key": "globus",
        "creds_field": None,
        "ping_fn": None,
        "refresh_fn": refresh_globus,
        "browser_type": "chromium",
        "description": "Globus Family (Globus/Cosmos/Monograms/Avalon)",
    },
    "atlas": {
        "cookie_file": CREDS_DIR / "atlas_cookies.json",
        "creds_key": "atlas_ocean",
        "creds_field": None,
        "ping_fn": None,
        "refresh_fn": refresh_atlas,
        "browser_type": "chromium",
        "description": "Atlas Ocean Voyages agent portal",
    },
    "explora": {
        "cookie_file": CREDS_DIR / "explora_cookies.json",
        "creds_key": "explora_journeys",
        "creds_field": None,
        "ping_fn": None,
        "refresh_fn": refresh_explora,
        "browser_type": "chromium",
        "description": "Explora Journeys agent portal",
    },
    "magtap": {
        "cookie_file": CREDS_DIR / "magtap_cookies.json",
        "creds_key": "magtap",
        "creds_field": None,
        "ping_fn": ping_magtap,
        "refresh_fn": refresh_magtap,
        "browser_type": "chromium",
        "description": "Outside Agents TAP/MAGCRM/TESS/Odysseus portal",
    },
    "regent_direct": {
        "cookie_file": CREDS_DIR / "regent_cookies.json",
        "creds_key": "regent",
        "creds_field": "direct_account",
        "ping_fn": None,
        "refresh_fn": refresh_regent,
        "browser_type": "firefox",
        "description": "Regent Seven Seas direct D2M account (Ely, Furlow, Nichols, McLeod)",
        "auth_cookie_names": ["ASPXAUTH"],   # A7 2026-06-11: verified auth gate (httpOnly, www.rssc.com)
        "auth_domain": "rssc.com",
    },
    "regent_oa": {
        "cookie_file": CREDS_DIR / "regent_cookies_oa.json",
        "creds_key": "regent",
        "creds_field": "oa_account",
        "ping_fn": None,
        "refresh_fn": refresh_regent,
        "browser_type": "firefox",
        "description": "Regent Seven Seas OA account (Loucks, McLeod bookings)",
        "auth_cookie_names": ["ASPXAUTH"],   # A7 2026-06-11: verified auth gate (httpOnly, www.rssc.com)
        "auth_domain": "rssc.com",
    },
    "perx": {
        "cookie_file": CREDS_DIR / "perx_cookies.json",
        "creds_key": "perx",
        "creds_field": None,
        "ping_fn": None,
        "refresh_fn": refresh_perx,
        "browser_type": "chromium",
        "description": "Perx interline rates — industry/employee fares; heavy discounts = TA rates incoming signal",
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
        # Pass auth_cookie_names + auth_domain if defined — ensures we check the
        # actual session gate, not long-lived analytics/tracking beacons. A7 2026-06-11.
        status = cookie_expiry_status(
            cookies,
            auth_cookie_names=portal.get("auth_cookie_names"),
            auth_domain=portal.get("auth_domain"),
        )
        report[name] = status
        auth_label = f" [{status.get('auth_cookie', '?')}]" if status.get("auth_cookie") else ""
        log.info(f"{name}: {status['status']}{auth_label} | {status.get('hours_left', '?')}h left | {status.get('expires_at', 'session-only')}")

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
        # Group portals by browser type
        chromium_portals = [n for n in needs_refresh if PORTALS[n].get("browser_type", "chromium") == "chromium"]
        firefox_portals = [n for n in needs_refresh if PORTALS[n].get("browser_type") == "firefox"]

        # Launch chromium browser
        chromium_browser = None
        if chromium_portals:
            chromium_browser = await p.chromium.launch(headless=True)

        # Launch firefox browser
        firefox_browser = None
        if firefox_portals:
            firefox_browser = await p.firefox.launch(headless=True)

        try:
            # Refresh chromium portals
            for name in chromium_portals:
                portal = PORTALS[name]
                portal_creds = creds.get(portal["creds_key"], {})
                # Handle creds_field for nested credential structures
                if portal.get("creds_field"):
                    portal_creds = portal_creds.get(portal["creds_field"], {})
                context = await chromium_browser.new_context()
                page = await context.new_page()
                try:
                    fresh_cookies = await portal["refresh_fn"](page, portal_creds)
                    if fresh_cookies:
                        save_cookies(portal["cookie_file"], fresh_cookies)
                        log.info(f"{name}: refreshed OK — {len(fresh_cookies)} cookies saved to {portal['cookie_file'].name}")
                        record_portal_success(name)
                    else:
                        log.error(f"{name}: refresh returned no cookies — manual re-auth may be needed")
                        record_portal_failure(name)
                except Exception as e:
                    log.error(f"{name}: refresh FAILED — {e}")
                    record_portal_failure(name)
                finally:
                    await context.close()

            # Refresh firefox portals
            for name in firefox_portals:
                portal = PORTALS[name]
                portal_creds = creds.get(portal["creds_key"], {})
                # Handle creds_field for nested credential structures
                if portal.get("creds_field"):
                    portal_creds = portal_creds.get(portal["creds_field"], {})
                context = await firefox_browser.new_context()
                page = await context.new_page()
                try:
                    fresh_cookies = await portal["refresh_fn"](page, portal_creds)
                    if fresh_cookies:
                        save_cookies(portal["cookie_file"], fresh_cookies)
                        log.info(f"{name}: refreshed OK — {len(fresh_cookies)} cookies saved to {portal['cookie_file'].name}")
                        record_portal_success(name)
                    else:
                        log.error(f"{name}: refresh returned no cookies — manual re-auth may be needed")
                        record_portal_failure(name)
                except Exception as e:
                    log.error(f"{name}: refresh FAILED — {e}")
                    record_portal_failure(name)
                finally:
                    await context.close()

        finally:
            if chromium_browser:
                await chromium_browser.close()
            if firefox_browser:
                await firefox_browser.close()


def main():
    parser = argparse.ArgumentParser(description="D2M Portal Session Keepalive")
    parser.add_argument("--portal", choices=list(PORTALS.keys()), help="Refresh one portal only")
    parser.add_argument("--status", action="store_true", help="Print expiry status only, no refresh")
    args = parser.parse_args()

    portals = [args.portal] if args.portal else list(PORTALS.keys())
    asyncio.run(run(portals, args.status))


if __name__ == "__main__":
    main()
