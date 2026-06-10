"""
Centrav B2B connector using XvfbDriver (headful Firefox in Xvfb).
Bypasses Akamai / reCAPTCHA by presenting a real X11 desktop.

Exports:
  async def centrav_login(driver: XvfbDriver) -> bool
  async def centrav_search(driver: XvfbDriver, routes: list) -> list[dict]
  async def centrav_logout(driver: XvfbDriver) -> None
  def session_health() -> tuple[bool, list[str]]

Dreams2Memories Travel, LLC — Thunderbird Wing
"""

import json
import logging
import re
import time
from base64 import urlsafe_b64decode
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.ai_infra.xvfb_driver import XvfbDriver

logger = logging.getLogger(__name__)

THUNDERBIRD = Path("/home/john/Thunderbird")
CREDS_PATH = THUNDERBIRD / "centrav_credentials.json"
SESSION_FILE = THUNDERBIRD / "core" / "travel" / "data" / "centrav_session.json"
GMAIL_TOKEN_PATH = THUNDERBIRD / "gmail_token_commander.json"

CENTRAV_LOGIN_URL = "https://www.centrav.com/login"
CENTRAV_HOME_URL = "https://www.centrav.com/"

OTP_POLL_INTERVAL_S = 8
OTP_MAX_WAIT_S = 120

# ── Session health ─────────────────────────────────────────────────────

def session_health() -> tuple[bool, list[str]]:
    """Check if Centrav session cookies are still fresh.

    Returns:
        (all_valid, list_of_expired_names)
    """
    if not SESSION_FILE.exists():
        return False, ["no session file"]

    try:
        cookies = json.loads(SESSION_FILE.read_text())
        if not isinstance(cookies, list):
            return False, ["invalid session file format"]
    except Exception as e:
        return False, [f"parse error: {e}"]

    now_ts = datetime.now(timezone.utc).timestamp()
    expired = []
    for c in cookies:
        exp = c.get("expires", -1)
        if exp and exp > 0 and exp < now_ts:
            expired.append(c.get("name", "?"))

    auth_names = {"laravel_session", "XSRF-TOKEN"}
    expired_auth = [n for n in expired if n in auth_names]
    return len(expired_auth) == 0, expired


# ── Gmail OTP polling (copied verbatim from scripts/centrav_reauth.py) ──

def _get_gmail_service():
    """Build Gmail API client using commander token."""
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
    except ImportError:
        logger.warning("google-auth not installed — Gmail OTP polling unavailable")
        return None

    if not GMAIL_TOKEN_PATH.exists():
        logger.warning("Gmail token not found at %s", GMAIL_TOKEN_PATH)
        return None

    try:
        token_data = json.loads(GMAIL_TOKEN_PATH.read_text())
        creds = Credentials(
            token=token_data.get("token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=token_data.get("client_id"),
            client_secret=token_data.get("client_secret"),
            scopes=token_data.get("scopes"),
        )
        if creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
            token_data["token"] = creds.token
            GMAIL_TOKEN_PATH.write_text(json.dumps(token_data, indent=2))

        return build("gmail", "v1", credentials=creds, cache_discovery=False)
    except Exception as e:
        logger.warning("Gmail service build failed: %s", e)
        return None


def _extract_otp_from_body(body: str) -> str | None:
    patterns = [
        r"(?:code|verification|otp)[:\s]+(\d{6})",
        r"\b(\d{6})\b",
    ]
    for pat in patterns:
        m = re.search(pat, body, re.IGNORECASE)
        if m:
            return m.group(1)
    return None


def _decode_gmail_body(payload: dict) -> str:
    mime_type = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data", "")
    if body_data:
        return urlsafe_b64decode(body_data + "==").decode("utf-8", errors="replace")
    for part in payload.get("parts", []):
        text = _decode_gmail_body(part)
        if text:
            return text
    return ""


def _poll_gmail_for_otp(service, timeout_s: int = OTP_MAX_WAIT_S) -> str | None:
    logger.info("Polling Gmail for Centrav OTP (up to %ss)...", timeout_s)
    start = time.monotonic()
    seen_ids: set[str] = set()

    while time.monotonic() - start < timeout_s:
        try:
            result = (
                service.users()
                .messages()
                .list(
                    userId="me",
                    q="from:centrav newer_than:5m subject:code OR subject:verification OR subject:login",
                    maxResults=5,
                )
                .execute()
            )
            msgs = result.get("messages", [])
            for msg_ref in msgs:
                mid = msg_ref["id"]
                if mid in seen_ids:
                    continue
                seen_ids.add(mid)
                msg = (
                    service.users()
                    .messages()
                    .get(userId="me", id=mid, format="full")
                    .execute()
                )
                body = _decode_gmail_body(msg.get("payload", {}))
                snippet = msg.get("snippet", "")
                combined = f"{snippet} {body}"
                otp = _extract_otp_from_body(combined)
                if otp:
                    logger.info("OTP found: %s (message id: %s)", otp, mid)
                    return otp

            if not msgs:
                broad = (
                    service.users()
                    .messages()
                    .list(userId="me", q="from:centrav newer_than:5m", maxResults=3)
                    .execute()
                )
                for msg_ref in broad.get("messages", []):
                    mid = msg_ref["id"]
                    if mid in seen_ids:
                        continue
                    seen_ids.add(mid)
                    msg = (
                        service.users()
                        .messages()
                        .get(userId="me", id=mid, format="full")
                        .execute()
                    )
                    body = _decode_gmail_body(msg.get("payload", {}))
                    otp = _extract_otp_from_body(f"{msg.get('snippet','')} {body}")
                    if otp:
                        logger.info("OTP found (broad search): %s", otp)
                        return otp

        except Exception as e:
            logger.warning("Gmail poll error: %s", e)

        elapsed = round(time.monotonic() - start)
        logger.info("No OTP yet (%ss elapsed) — waiting %ss...", elapsed, OTP_POLL_INTERVAL_S)
        time.sleep(OTP_POLL_INTERVAL_S)

    logger.warning("OTP poll timed out after %ss", timeout_s)
    return None


# ── Cookie persistence ─────────────────────────────────────────────────

def _save_cookies(cookies: list[dict]) -> None:
    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    SESSION_FILE.write_text(json.dumps(cookies, indent=2))
    logger.info("Saved %d cookies → %s", len(cookies), SESSION_FILE)

    if CREDS_PATH.exists():
        try:
            creds = json.loads(CREDS_PATH.read_text())
            creds["cookies"] = {c["name"]: c["value"] for c in cookies}
            creds["_last_exported"] = datetime.now(timezone.utc).isoformat()
            CREDS_PATH.write_text(json.dumps(creds, indent=2))
            logger.info("Updated cookies in %s", CREDS_PATH)
        except Exception as e:
            logger.warning("Could not update %s: %s", CREDS_PATH, e)


# ── Async login ────────────────────────────────────────────────────────

async def centrav_login(driver: XvfbDriver) -> bool:
    """Full Centrav login flow via Xvfb headful Firefox.

    Steps:
      1. Navigate to /login
      2. Fill credentials
      3. Submit (Akamai / reCAPTCHA bypassed by Xvfb + headful Firefox)
      4. Handle OTP email MFA if triggered
      5. Save session cookies

    Args:
        driver: An active XvfbDriver instance (inside the async with block).

    Returns:
        True if authenticated, False otherwise.
    """
    XvfbDriver = driver  # already imported via caller

    # ── Load credentials ───────────────────────────────────────────────
    if not CREDS_PATH.exists():
        logger.error("Credentials not found at %s", CREDS_PATH)
        return False
    try:
        creds = json.loads(CREDS_PATH.read_text())
        email = creds["email"]
        password = creds["password"]
    except Exception as e:
        logger.error("Could not load credentials: %s", e)
        return False

    # ── Gmail service (optional) ───────────────────────────────────────
    gmail_service = _get_gmail_service()

    # ── Step 1: Navigate to login ──────────────────────────────────────
    logger.info("Navigating to %s", CENTRAV_LOGIN_URL)
    info = await driver.navigate(CENTRAV_LOGIN_URL, timeout=45_000)
    logger.info("Landed on: %s", info["url"])

    # Check for bot-block
    body_text = (await driver.evaluate("document.body?.innerText?.toLowerCase() ?? ''")) or ""
    if any(s in body_text for s in ["access denied", "cloudflare", "ray id", "checking your browser"]):
        logger.error("Bot-block detected before login")
        await driver.screenshot(str(THUNDERBIRD / "output" / "centrav_xvfb_blocked.png"))
        return False

    # ── Step 2: Fill credentials ───────────────────────────────────────
    try:
        await driver.page.fill("#FormEmail", email)
        await driver.page.fill("#FormPassword", password)
        logger.info("Credentials filled (%s)", email)
    except Exception as e:
        logger.error("Could not fill credential fields: %s", e)
        await driver.screenshot(str(THUNDERBIRD / "output" / "centrav_xvfb_fill_fail.png"))
        return False

    # ── Step 3: Submit ─────────────────────────────────────────────────
    try:
        await driver.page.click("#MainLoginButton, [type='submit']")
        logger.info("Form submitted — waiting for redirect...")
        await driver.page.wait_for_timeout(3_500)
    except Exception as e:
        logger.warning("Submit click issue: %s — pressing Enter", e)
        await driver.page.keyboard.press("Enter")
        await driver.page.wait_for_timeout(3_500)

    # ── Step 4: Detect post-submit state ───────────────────────────────
    url_after = driver.page.url
    body_after = (await driver.evaluate("document.body?.innerText?.toLowerCase() ?? ''")) or ""

    logger.info("Post-submit URL: %s", url_after)

    otp_signals = [
        "check your email", "verification code", "enter the code",
        "email code", "6-digit", "one-time", "sent to your email",
    ]
    on_otp_screen = any(s in body_after for s in otp_signals)

    auth_signals = ["logout", "my account", "dashboard", "search flights", "flying from"]
    already_auth = any(s in body_after for s in auth_signals)
    if "login" not in url_after.lower() and not on_otp_screen:
        already_auth = True

    if already_auth and not on_otp_screen:
        logger.info("Authenticated directly (no MFA required this session)")
        cookies = await driver.context.cookies()
        _save_cookies(cookies)
        return True

    if on_otp_screen:
        logger.info("Email MFA screen detected — fetching OTP...")
        await driver.screenshot(str(THUNDERBIRD / "output" / "centrav_xvfb_mfa_screen.png"))

        otp = None
        if gmail_service:
            otp = _poll_gmail_for_otp(gmail_service)
        if not otp:
            logger.warning("Gmail poll failed or unavailable — falling back to manual entry")
            otp = input("Enter the 6-digit OTP from your email (johnloucks3@gmail.com): ").strip()

        if not otp or not re.match(r"^\d{6}$", otp):
            logger.error("Invalid OTP '%s'", otp)
            return False

        logger.info("Entering OTP: %s", otp)
        try:
            otp_selectors = [
                "input[name='code']", "input[name='otp']", "input[name='token']",
                "input[type='number']", "input[placeholder*='code']",
                "input[placeholder*='Code']", "input[maxlength='6']",
            ]
            filled_otp = False
            for sel in otp_selectors:
                try:
                    el = await driver.page.query_selector(sel)
                    if el and await el.is_visible():
                        await el.fill(otp)
                        filled_otp = True
                        logger.info("OTP filled via selector: %s", sel)
                        break
                except Exception:
                    continue

            if not filled_otp:
                await driver.page.keyboard.type(otp, delay=80)
                filled_otp = True
                logger.info("OTP typed via keyboard (fallback)")

            await driver.page.wait_for_timeout(500)

            submit_selectors = ["[type='submit']", "button[name='verify']", "button"]
            submitted = False
            for sel in submit_selectors:
                try:
                    btn = await driver.page.query_selector(sel)
                    if btn and await btn.is_visible():
                        await btn.click()
                        submitted = True
                        break
                except Exception:
                    continue
            if not submitted:
                await driver.page.keyboard.press("Enter")
        except Exception as e:
            logger.error("OTP entry failed: %s", e)
            await driver.screenshot(str(THUNDERBIRD / "output" / "centrav_xvfb_otp_fail.png"))
            return False

        await driver.page.wait_for_timeout(3_500)

        url_final = driver.page.url
        body_final = (await driver.evaluate("document.body?.innerText?.toLowerCase() ?? ''")) or ""
        logger.info("Post-OTP URL: %s", url_final)

        if "login" not in url_final.lower() and any(s in body_final for s in auth_signals + ["logout"]):
            logger.info("Authenticated after OTP")
            cookies = await driver.context.cookies()
            _save_cookies(cookies)
            return True
        elif "login" not in url_final.lower():
            logger.info("Likely authenticated (redirected off login)")
            cookies = await driver.context.cookies()
            _save_cookies(cookies)
            return True
        else:
            logger.error("Still on login page after OTP. URL=%s", url_final)
            await driver.screenshot(str(THUNDERBIRD / "output" / "centrav_xvfb_otp_rejected.png"))
            return False

    logger.error("Unknown post-submit state. URL=%s", url_after)
    await driver.screenshot(str(THUNDERBIRD / "output" / "centrav_xvfb_unknown.png"))
    try:
        dump = await driver.evaluate("""() => ({
            title: document.title,
            inputs: Array.from(document.querySelectorAll('input')).map(i => ({
                id: i.id, name: i.name, type: i.type, value: (i.value || '').substring(0, 20)
            })),
            buttons: Array.from(document.querySelectorAll('button')).map(b => ({
                id: b.id, text: (b.innerText || '').trim().substring(0, 30)
            })),
            text: (document.body.innerText || '').substring(0, 500)
        })""")
        logger.info("Post-submit DOM:\n%s", json.dumps(dump, indent=2, default=str))
    except Exception as e:
        logger.error("DOM dump failed: %s", e)
    return False


# ── Async search ───────────────────────────────────────────────────────

async def centrav_search(driver: XvfbDriver, routes: list) -> list[dict]:
    """Search Centrav for the given routes.

    Each route is a dict like::

        {"origin": "DEN", "dest": "MIA", "cabin": "Economy", "date": "2026-09-15"}

    The connector attempts to use the search form on the Centrav home page.
    Returns a list of result dicts with keys: origin, dest, cabin, date,
    price, airline, flight_numbers, dep_time, arr_time, duration, raw_html.

    Args:
        driver: An active XvfbDriver instance (inside the async with block).
        routes: List of route dicts to search.

    Returns:
        List of parsed flight results.
    """
    results: list[dict] = []

    # Try loading saved session cookies first
    if SESSION_FILE.exists():
        try:
            cookies = json.loads(SESSION_FILE.read_text())
            if isinstance(cookies, list):
                await driver.context.add_cookies(cookies)
                logger.info("Loaded %d session cookies", len(cookies))
        except Exception as e:
            logger.warning("Could not load session cookies: %s", e)

    for route in routes:
        origin = route.get("origin", "")
        dest = route.get("dest", "")
        cabin = route.get("cabin", "Economy")
        date = route.get("date", "")

        logger.info("Searching %s → %s (%s) on %s", origin, dest, cabin, date)

        try:
            await driver.navigate(CENTRAV_HOME_URL, timeout=30_000)

            # Fill search form
            try:
                origin_el = await driver.page.query_selector("#FareFlyingFrom, input[name='from']")
                dest_el = await driver.page.query_selector("#FareFlyingTo, input[name='to']")
                if not origin_el or not dest_el:
                    logger.warning("Search form not found for %s→%s", origin, dest)
                    continue

                await origin_el.click()
                await origin_el.fill("")
                await origin_el.fill(origin)
                await driver.page.wait_for_timeout(1_000)

                await dest_el.click()
                await dest_el.fill("")
                await dest_el.fill(dest)
                await driver.page.wait_for_timeout(1_000)

                # Handle autocomplete
                suggestions = await driver.page.query_selector_all(
                    "[class*='autocomplete'] li, [class*='dropdown'] li"
                )
                if suggestions:
                    await suggestions[0].click()

                # Set cabin class
                cabin_selectors = [
                    f"select[name='cabin']",
                    f"#FareCabinClass",
                ]
                for sel in cabin_selectors:
                    el = await driver.page.query_selector(sel)
                    if el:
                        await el.select_option(cabin)
                        break

                # Set date
                date_el = await driver.page.query_selector("#FareDepartDate, input[name='departDate'], input[type='date']")
                if date_el:
                    await date_el.fill(date)
                    await driver.page.wait_for_timeout(500)

                # Submit
                search_btn = await driver.page.query_selector(
                    "#FormSubmitButton, [type='submit'], button:has-text('Search'), button:has-text('Find')"
                )
                if search_btn:
                    await search_btn.click()
                else:
                    await driver.page.keyboard.press("Enter")

                await driver.page.wait_for_timeout(5_000)

                # Wait for results (network idle or specific result selector)
                try:
                    await driver.page.wait_for_selector(
                        "[class*='result'], [class*='fare'], .flight-card, table[class*='results']",
                        timeout=15_000,
                    )
                except Exception:
                    pass

            except Exception as e:
                logger.warning("Search form interaction failed for %s→%s: %s", origin, dest, e)
                await driver.screenshot(
                    str(THUNDERBIRD / "output" / f"centrav_search_fail_{origin}_{dest}_{date}.png")
                )
                continue

            # Extract results
            page_text = (await driver.evaluate("document.body?.innerText ?? ''")) or ""
            html = (await driver.evaluate("document.body?.innerHTML ?? ''")) or ""

            # Check for auth redirect
            if "login" in driver.page.url.lower():
                logger.warning("Session expired during search — login page detected")
                continue

            prices = _parse_price_lines(page_text, origin, dest, cabin, date)
            results.extend(prices)

            logger.info("  Found %d price entries for %s→%s", len(prices), origin, dest)

            await driver.screenshot(
                str(THUNDERBIRD / "output" / f"centrav_search_{cabin}_{origin}_{dest}_{date}.png")
            )

        except Exception as e:
            logger.error("Search error for %s→%s: %s", origin, dest, e)
            continue

    return results


async def centrav_logout(driver: XvfbDriver) -> None:
    """Navigate to Centrav logout and save cookies."""
    try:
        await driver.navigate(CENTRAV_LOGIN_URL, timeout=15_000)
    except Exception:
        pass
    cookies = await driver.context.cookies()
    if cookies:
        _save_cookies(cookies)


# ── Internal helpers ───────────────────────────────────────────────────

def _parse_price_lines(
    text: str,
    origin: str,
    dest: str,
    cabin: str,
    date: str,
) -> list[dict]:
    """Simple text-based price extractor from Centrav results page.

    Look for common fare presentation patterns like:
        DENVER (DEN) to MIAMI (MIA)   $450.00
        DL 1234  08:00  11:30  $450.00
    """
    lines = text.split("\n")
    results: list[dict] = []
    price_pattern = re.compile(r"\$[\d,]+\.?\d*")

    header_found = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue

        # Detect header
        if origin.upper() in stripped.upper() and dest.upper() in stripped.upper():
            header_found = True

        if not header_found:
            continue

        prices = price_pattern.findall(stripped)
        if not prices:
            continue

        price_clean = prices[0].replace(",", "")
        try:
            price_val = float(price_clean.replace("$", ""))
        except ValueError:
            continue

        result = {
            "origin": origin,
            "dest": dest,
            "cabin": cabin,
            "date": date,
            "price": price_val,
            "raw_line": stripped[:300],
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        }
        results.append(result)

        # Cap at 20 results per route
        if len(results) >= 20:
            break

    return results


# ── Smoke test ─────────────────────────────────────────────────────────

async def _smoke_test():
    """Run a quick smoke test: login + search a spot-check route."""
    logger.info("=" * 60)
    logger.info("Centrav Xvfb Connector — Smoke Test")
    logger.info("=" * 60)

    health_ok, expired = session_health()
    if health_ok:
        logger.info("Session cookies VALID (%d total)", len(expired) + 1)
    else:
        logger.warning("Session expired: %s", ", ".join(expired))

    async with XvfbDriver(display_num=100, headless=False) as driver:
        auth_ok = await centrav_login(driver)
        if not auth_ok:
            logger.error("Login failed — aborting")
            return False

        results = await centrav_search(driver, [
            {"origin": "DEN", "dest": "MIA", "cabin": "Economy", "date": "2026-09-15"},
        ])

        logger.info("\nResults:")
        for r in results[:10]:
            logger.info("  %s→%s  $%s  %s", r["origin"], r["dest"], r["price"], r.get("raw_line", ""))

    logger.info("Smoke test complete — %d results", len(results))
    return True


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    import asyncio
    asyncio.run(_smoke_test())


if __name__ == "__main__":
    main()
