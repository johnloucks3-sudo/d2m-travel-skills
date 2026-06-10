"""
Room-Res.com hotel rate connector using XvfbDriver (headful Firefox via Xvfb).

Exports:
  room_res_login(driver) -> bool
  room_res_search_rates(driver, property_name, check_in, check_out) -> list[dict]
  dump_form(driver) -> dict

Credentials: config/portal_creds.json → room_res key
Cookie cache: creds/room_res_cookies.json
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

ROOM_RES_URL = "https://room-res.com"

_ROOT = Path(__file__).resolve().parents[3]
_CREDS_PATH = _ROOT / "config" / "portal_creds.json"
_COOKIE_PATH = _ROOT / "creds" / "room_res_cookies.json"


# ── Credential helpers ──────────────────────────────────────────────

def _load_creds() -> dict:
    """Return the room_res dict from portal_creds.json, or empty."""
    if not _CREDS_PATH.exists():
        logger.warning("room_res: creds file not found: %s", _CREDS_PATH)
        return {}
    try:
        data = json.loads(_CREDS_PATH.read_text())
        return data.get("room_res", {})
    except Exception as e:
        logger.error("room_res: creds parse error: %s", e)
        return {}


# ── Form inspector (for unknown selectors) ─────────────────────────

async def dump_form(driver) -> dict:
    """Enumerate all <input>, <button>, <select>, <form> elements on the page.

    Returns a dict with keys: inputs, buttons, selects, forms.
    Each entry contains tag name, type, name, id, placeholder, class,
    and text content where applicable.
    """
    js = """
    () => {
        const result = { inputs: [], buttons: [], selects: [], forms: [] };

        document.querySelectorAll('input').forEach(el => {
            result.inputs.push({
                tag: 'input',
                type: el.type,
                name: el.name,
                id: el.id,
                placeholder: el.placeholder,
                class: el.className,
                autocomplete: el.autocomplete,
                value: el.value ? el.value.substring(0, 40) : '',
                visible: el.offsetParent !== null
            });
        });

        document.querySelectorAll('button').forEach(el => {
            result.buttons.push({
                tag: 'button',
                type: el.type,
                name: el.name,
                id: el.id,
                class: el.className,
                text: (el.textContent || '').trim().substring(0, 60),
                visible: el.offsetParent !== null
            });
        });

        document.querySelectorAll('select').forEach(el => {
            result.selects.push({
                tag: 'select',
                name: el.name,
                id: el.id,
                class: el.className,
                options: Array.from(el.options).map(o => ({
                    value: o.value,
                    text: o.text
                })),
                visible: el.offsetParent !== null
            });
        });

        document.querySelectorAll('form').forEach(el => {
            const action = el.action || '';
            result.forms.push({
                tag: 'form',
                id: el.id,
                name: el.name,
                class: el.className,
                action: action.substring(0, 120),
                method: el.method,
                inputs: Array.from(el.querySelectorAll('input, button, select')).length
            });
        });

        return result;
    }
    """
    try:
        result = await driver.evaluate(js)
    except Exception as e:
        logger.error("room_res: dump_form failed: %s", e)
        result = {"error": str(e)}

    logger.info(
        "room_res: form dump — %d inputs, %d buttons, %d selects, %d forms",
        len(result.get("inputs", [])),
        len(result.get("buttons", [])),
        len(result.get("selects", [])),
        len(result.get("forms", [])),
    )
    return result


# ── Auth helpers ───────────────────────────────────────────────────

async def _dismiss_cookie_banner(driver) -> None:
    """Click cookie consent if present — Room-Res may vary by region."""
    js = """
    () => {
        const labels = ['Allow all', 'Accept all', 'Allow', 'Accept', 'I agree',
                        'Allow all cookies', 'Accept all cookies', 'OK'];
        const btns = Array.from(document.querySelectorAll('button, a'));
        for (const label of labels) {
            const btn = btns.find(b =>
                (b.textContent || '').trim().toLowerCase() === label.toLowerCase()
            );
            if (btn) { btn.click(); return label; }
        }
        return null;
    }
    """
    try:
        clicked = await driver.evaluate(js)
        if clicked:
            await driver.page.wait_for_timeout(1500)
            logger.debug("room_res: dismissed cookie banner ('%s')", clicked)
    except Exception:
        pass


async def _check_auth(driver) -> bool:
    """Return True if the current page looks authenticated."""
    try:
        text = await driver.evaluate(
            "document.body?.innerText?.toLowerCase() ?? ''"
        )
    except Exception:
        return False

    auth_signals = [
        "logout", "sign out", "my account", "dashboard",
        "search hotel", "book hotel", "my bookings",
        "welcome", "profile", "agency",
    ]
    for sig in auth_signals:
        if sig in text:
            return True
    return False


async def _load_cookies(driver) -> bool:
    """Load persisted cookies into the driver context. Returns True on success."""
    if not _COOKIE_PATH.exists():
        logger.info("room_res: no cookie cache at %s", _COOKIE_PATH)
        return False
    try:
        await driver.load_cookies(_COOKIE_PATH)
        logger.info("room_res: loaded cookies from %s", _COOKIE_PATH)
        return True
    except Exception as e:
        logger.warning("room_res: cookie load error: %s", e)
        return False


async def _save_cookies(driver) -> None:
    """Persist current session cookies to disk."""
    try:
        await driver.save_cookies(_COOKIE_PATH)
        logger.info("room_res: saved cookies to %s", _COOKIE_PATH)
    except Exception as e:
        logger.warning("room_res: cookie save error: %s", e)


# ── Login ──────────────────────────────────────────────────────────

async def room_res_login(driver) -> bool:
    """Authenticate to room-res.com.

    Strategy:
      1. Try cookie restore first (fast path).
      2. Navigate to login page.
      3. Dump form if login fields aren't obvious.
      4. Fill credentials via common selectors.
      5. Submit and verify.

    Returns True if authenticated by the end.
    """
    creds = _load_creds()
    username = creds.get("username", "")
    email = creds.get("email", "")
    password = creds.get("password", "")
    login_cred = username or email

    if not login_cred or not password:
        logger.error("room_res: missing credentials in %s", _CREDS_PATH)
        return False

    page = driver.page

    # ── Step 1: Try cookie restore ──
    await _load_cookies(driver)
    await driver.navigate(ROOM_RES_URL, wait_until="domcontentloaded", timeout=30_000)
    await page.wait_for_timeout(2000)

    if await _check_auth(driver):
        logger.info("room_res: authenticated via cookie cache")
        return True

    # ── Step 2: Navigate to login ──
    # Common login path patterns
    login_paths = ["/login", "/auth/login", "/signin", "/user/login"]
    login_found = False
    for path in login_paths:
        try:
            await driver.navigate(
                f"{ROOM_RES_URL}{path}",
                wait_until="domcontentloaded",
                timeout=15_000,
            )
            await page.wait_for_timeout(1500)
            # Check if there are login inputs on this page
            has_inputs = await page.evaluate(
                "document.querySelector('input[type=\"email\"]') || "
                "document.querySelector('input[type=\"text\"]')"
            )
            if has_inputs:
                login_found = True
                break
        except Exception:
            continue

    if not login_found:
        # Maybe we're already on the right page — try base URL
        await driver.navigate(ROOM_RES_URL, wait_until="domcontentloaded", timeout=15_000)
        await page.wait_for_timeout(2000)

    await _dismiss_cookie_banner(driver)

    # ── Step 3: Enumerate form elements for debugging ──
    form_state = await dump_form(driver)
    logger.debug("room_res: login page form state: %s", json.dumps(form_state, default=str)[:500])

    # ── Step 4: Fill credentials ──
    filled = await _fill_login_form(page, login_cred, password)
    if not filled:
        logger.error("room_res: could not locate login form fields")
        logger.info("room_res: form dump follows — see dump_form() output above")
        return False

    # ── Step 5: Submit ──
    await page.wait_for_timeout(2000)

    # Try clicking any visible submit button
    submit_clicked = await page.evaluate("""
        () => {
            const btns = Array.from(document.querySelectorAll(
                'button[type="submit"], input[type="submit"], button:has-text("Login"), '
                + 'button:has-text("Sign In"), button:has-text("Log In")'
            ));
            const visible = btns.find(b => b.offsetParent !== null);
            if (visible) { visible.click(); return true; }
            return false;
        }
    """)

    if not submit_clicked:
        # Press Enter on the last input as fallback
        await page.keyboard.press("Enter")

    # ── Step 6: Wait for post-login navigation ──
    await page.wait_for_timeout(4000)
    try:
        await page.wait_for_load_state("domcontentloaded", timeout=15_000)
    except Exception:
        pass

    # ── Step 7: Verify ──
    authenticated = await _check_auth(driver)
    if authenticated:
        logger.info("room_res: login successful ✓")
        await _save_cookies(driver)
    else:
        await _save_cookies(driver)  # save whatever we got for debugging
        current_url = page.url
        title = await page.title()
        logger.warning(
            "room_res: login may have failed — url=%s title=%s",
            current_url, title,
        )

    return authenticated


async def _fill_login_form(page, login_cred: str, password: str) -> bool:
    """Attempt to locate and fill username/email + password fields.

    Returns True if at least the password field was found and filled.
    """
    # Priority-ordered selector lists for username and password
    username_selectors = [
        "input[type='email']",
        "input[name='email']",
        "input[id*='email']",
        "input[placeholder*='email' i]",
        "input[placeholder*='username' i]",
        "input[name='username']",
        "input[id*='username']",
        "input[autocomplete='username']",
        "input[type='text']",
    ]

    password_selectors = [
        "input[type='password']",
        "input[name='password']",
        "input[id*='password']",
        "input[placeholder*='password' i]",
        "input[autocomplete='current-password']",
    ]

    user_field = None
    pass_field = None

    for sel in username_selectors:
        el = await page.query_selector(sel)
        if el and await el.is_visible():
            user_field = el
            break

    for sel in password_selectors:
        el = await page.query_selector(sel)
        if el and await el.is_visible():
            pass_field = el
            break

    if not pass_field:
        logger.warning("room_res: no password field found on login page")
        return False

    # Fill fields
    if user_field:
        await user_field.click()
        await page.keyboard.press("Control+a")
        await user_field.fill(login_cred)
        logger.debug("room_res: filled username/email field")
    else:
        logger.warning("room_res: no username field found — filling password only")

    await pass_field.click()
    await page.keyboard.press("Control+a")
    await pass_field.fill(password)
    logger.debug("room_res: filled password field")

    return True


# ── Rate search ────────────────────────────────────────────────────

async def room_res_search_rates(
    driver,
    property_name: str,
    check_in: str,
    check_out: str,
) -> list[dict]:
    """Navigate to hotel search, find *property_name*, and extract rate data.

    Args:
        driver: Active XvfbDriver instance (must be authenticated).
        property_name: Hotel name (e.g. "Westin Kierland Villas").
        check_in: Start date in YYYY-MM-DD format.
        check_out: End date in YYYY-MM-DD format.

    Returns:
        List of rate dicts with keys: room_type, rate_description,
        currency, total_price, nightly_price, availability, scraped_at.
    """
    page = driver.page
    rates: list[dict] = []

    # Navigate to search page — try common paths
    search_paths = ["/search", "/hotels", "/hotel-search", "/booking/search"]
    search_found = False
    for path in search_paths:
        try:
            await driver.navigate(
                f"{ROOM_RES_URL}{path}",
                wait_until="domcontentloaded",
                timeout=20_000,
            )
            await page.wait_for_timeout(2000)
            # Check if page looks like a search page
            page_text = await page.evaluate("document.body?.innerText?.toLowerCase() ?? ''")
            if any(kw in page_text for kw in ("search", "hotel", "destination", "check-in", "check in", "checkin")):
                search_found = True
                break
        except Exception:
            continue

    if not search_found:
        # Try base URL — maybe already on search
        logger.info("room_res: no explicit search path found, using base URL")
        try:
            await driver.navigate(ROOM_RES_URL, wait_until="domcontentloaded", timeout=15_000)
            await page.wait_for_timeout(2000)
        except Exception:
            pass

    await _dismiss_cookie_banner(driver)

    # Dump the form so we understand the search page layout
    form_state = await dump_form(driver)
    logger.debug("room_res: search page form state: %s", json.dumps(form_state, default=str)[:800])

    # ── Fill search form ──
    await _fill_search_form(page, property_name, check_in, check_out)

    # Click the search/Go button
    search_clicked = await page.evaluate("""
        () => {
            const labels = ['Search', 'Go', 'Find', 'Search Hotels', 'Check Availability',
                            'View Rates', 'Submit', 'OK'];
            const btns = Array.from(document.querySelectorAll(
                'button, input[type="submit"], a[class*="btn"], a[class*="search"]'
            ));
            for (const label of labels) {
                const btn = btns.find(b =>
                    (b.textContent || b.value || '').trim().toLowerCase() === label.toLowerCase()
                );
                if (btn && btn.offsetParent !== null) {
                    btn.click();
                    return true;
                }
            }
            return false;
        }
    """)

    if not search_clicked:
        await page.keyboard.press("Enter")

    await page.wait_for_timeout(4000)
    try:
        await page.wait_for_load_state("domcontentloaded", timeout=20_000)
    except Exception:
        pass

    # ── Extract rate data ──
    await page.wait_for_timeout(2000)
    rates = await _extract_rates(page, property_name)

    return rates


async def _fill_search_form(
    page,
    property_name: str,
    check_in: str,
    check_out: str,
) -> None:
    """Fill destination/property, check-in, check-out fields on the search page."""
    # -- Property / destination --
    dest_selectors = [
        "input[placeholder*='destination' i]",
        "input[placeholder*='hotel' i]",
        "input[placeholder*='property' i]",
        "input[placeholder*='city' i]",
        "input[name*='destination' i]",
        "input[id*='destination' i]",
        "input[name*='search' i]",
        "input[id*='search' i]",
        "input[type='text']",
    ]
    dest_field = None
    for sel in dest_selectors:
        el = await page.query_selector(sel)
        if el and await el.is_visible():
            dest_field = el
            break

    if dest_field:
        await dest_field.click()
        await page.keyboard.press("Control+a")
        await dest_field.fill(property_name)
        logger.debug("room_res: filled destination '%s'", property_name)
        await page.wait_for_timeout(1000)
    else:
        logger.warning("room_res: no destination/property field found")

    # -- Check-in date --
    checkin_selectors = [
        "input[placeholder*='check-in' i]",
        "input[placeholder*='check in' i]",
        "input[placeholder*='checkin' i]",
        "input[placeholder*='arrival' i]",
        "input[name*='checkin' i]",
        "input[name*='arrival' i]",
        "input[id*='checkin' i]",
        "input[id*='arrival' i]",
    ]
    cin_field = None
    for sel in checkin_selectors:
        el = await page.query_selector(sel)
        if el and await el.is_visible():
            cin_field = el
            break

    if cin_field:
        await cin_field.click()
        await page.keyboard.press("Control+a")
        await cin_field.fill(check_in)
        logger.debug("room_res: filled check-in '%s'", check_in)
        await page.wait_for_timeout(500)
    else:
        logger.warning("room_res: no check-in field found")

    # -- Check-out date --
    checkout_selectors = [
        "input[placeholder*='check-out' i]",
        "input[placeholder*='check out' i]",
        "input[placeholder*='checkout' i]",
        "input[placeholder*='departure' i]",
        "input[name*='checkout' i]",
        "input[name*='departure' i]",
        "input[id*='checkout' i]",
        "input[id*='departure' i]",
    ]
    cout_field = None
    for sel in checkout_selectors:
        el = await page.query_selector(sel)
        if el and await el.is_visible():
            cout_field = el
            break

    if cout_field:
        await cout_field.click()
        await page.keyboard.press("Control+a")
        await cout_field.fill(check_out)
        logger.debug("room_res: filled check-out '%s'", check_out)
        await page.wait_for_timeout(500)
    else:
        logger.warning("room_res: no check-out field found")


async def _extract_rates(page, property_name: str) -> list[dict]:
    """Parse rate/availability data from the search results page."""
    now_str = datetime.now(timezone.utc).isoformat()
    rates: list[dict] = []

    html = ""
    try:
        html = await page.content()
    except Exception:
        pass

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")

    # Strategy 1: Look for embedded JSON (window.__STATE__, etc.)
    state_pattern = re.compile(
        r"window\.__(?:STATE|DATA|INITIAL_STATE|NEXT_DATA|REACT_QUERY)__\s*=\s*(\{.+?\});",
        re.DOTALL,
    )
    state_match = state_pattern.search(html)
    if state_match:
        try:
            state = json.loads(state_match.group(1))
            rates = _parse_state_rates(state, property_name, now_str)
            if rates:
                logger.info("room_res: extracted %d rates from window state", len(rates))
                return rates
        except Exception as e:
            logger.debug("room_res: window state parse failed: %s", e)

    # Strategy 2: DOM-based extraction from result cards
    card_selectors = [
        "div[class*='room-card']",
        "div[class*='rate-card']",
        "div[class*='hotel-card']",
        "div[class*='result-card']",
        "div[class*='property-card']",
        "div[class*='listing']",
        "div[class*='result-item']",
        "tr[class*='rate']",
        "li[class*='room']",
        "[data-testid*='room']",
        "[data-testid*='rate']",
        "[data-testid*='result']",
    ]

    cards = []
    for sel in card_selectors:
        found = soup.select(sel)
        if found:
            cards = found
            break

    # Fallback: look for any div containing price-like text near the property name
    if not cards:
        price_pattern = re.compile(r"[\$€£]\s*\d+(?:,\d{3})*(?:\.\d{2})?")
        price_containers = soup.find_all(string=price_pattern)
        # Collect parent containers
        seen = set()
        for text_node in price_containers[:20]:
            parent = text_node.parent
            if parent and parent not in seen:
                seen.add(parent)
                cards.append(parent)

    for card in cards[:30]:
        try:
            rate = _parse_rate_card(card, property_name, now_str)
            if rate and rate.get("total_price", 0) > 0:
                rates.append(rate)
        except Exception:
            continue

    if not rates:
        logger.warning("room_res: no rate cards extracted from DOM")

    return rates


def _parse_state_rates(state: dict, property_name: str, now_str: str) -> list[dict]:
    """Attempt to extract rate data from embedded application state."""
    rates: list[dict] = []

    # Try common state paths for hotel booking portals
    candidates = (
        state.get("results")
        or state.get("hotels")
        or state.get("rooms")
        or state.get("rates")
        or state.get("data")
        or state.get("props", {}).get("pageProps", {}).get("results")
        or state.get("props", {}).get("pageProps", {}).get("hotels")
    )

    if isinstance(candidates, dict):
        candidates = [candidates]
    if not isinstance(candidates, list):
        return rates

    for item in candidates:
        if isinstance(item, dict):
            name = (
                item.get("name")
                or item.get("hotelName")
                or item.get("propertyName")
                or item.get("title")
                or ""
            )
            if property_name.lower() not in name.lower():
                continue

            nights = item.get("nights", item.get("duration", 1))
            price = float(item.get("totalPrice", item.get("price", item.get("rate", 0))) or 0)
            currency = item.get("currency", "USD")

            # Room types / rate breakdowns
            rooms = item.get("rooms", item.get("roomTypes", item.get("ratePlans", [])))
            if rooms and isinstance(rooms, list):
                for room in rooms:
                    rp = float(room.get("totalPrice", room.get("price", room.get("rate", 0))) or 0)
                    rates.append({
                        "room_type": room.get("name", room.get("roomType", room.get("type", ""))),
                        "rate_description": room.get("description", room.get("plan", "")),
                        "currency": room.get("currency", currency),
                        "total_price": rp,
                        "nightly_price": round(rp / max(nights, 1), 2) if nights else rp,
                        "nights": nights,
                        "availability": room.get("availability", room.get("status", "available")),
                        "scraped_at": now_str,
                    })
            else:
                rates.append({
                    "room_type": item.get("roomType", ""),
                    "rate_description": item.get("rateDescription", item.get("plan", "")),
                    "currency": currency,
                    "total_price": price,
                    "nightly_price": round(price / max(nights, 1), 2) if nights else price,
                    "nights": nights,
                    "availability": item.get("availability", "available"),
                    "scraped_at": now_str,
                })

    return rates


def _parse_rate_card(card, property_name: str, now_str: str) -> dict | None:
    """Parse a single DOM card/element for hotel rate data."""
    from bs4 import BeautifulSoup

    card_text = card.get_text(separator=" ", strip=True)
    if not card_text:
        return None

    # Only process cards mentioning the property
    if property_name.lower() not in card_text.lower():
        return None

    # Extract price
    price_pattern = re.compile(r"([\$€£])\s*([\d,]+(?:\.\d{2})?)")
    price_matches = price_pattern.findall(card_text)
    prices = []
    for sym, val in price_matches:
        try:
            prices.append(float(val.replace(",", "")))
        except ValueError:
            continue

    total_price = max(prices) if prices else 0.0

    # Extract room type
    room_el = (
        card.select_one("[class*='room']")
        or card.select_one("[class*='type']")
        or card.select_one("h3")
        or card.select_one("h4")
    )
    room_type = room_el.get_text(strip=True) if room_el else ""

    # Extract rate description
    rate_el = (
        card.select_one("[class*='rate']")
        or card.select_one("[class*='plan']")
        or card.select_one("[class*='desc']")
    )
    rate_desc = rate_el.get_text(strip=True) if rate_el else ""

    # Extract availability
    avail_el = (
        card.select_one("[class*='avail']")
        or card.select_one("[class*='status']")
    )
    availability = avail_el.get_text(strip=True) if avail_el else "available"

    # Extract nights
    nights_match = re.search(r"(\d+)\s*(?:night|day)", card_text, re.IGNORECASE)
    nights = int(nights_match.group(1)) if nights_match else 1

    if total_price <= 0:
        return None

    return {
        "room_type": room_type,
        "rate_description": rate_desc,
        "currency": "USD",
        "total_price": total_price,
        "nightly_price": round(total_price / max(nights, 1), 2),
        "nights": nights,
        "availability": availability,
        "scraped_at": now_str,
    }


# ── Standalone entry point ─────────────────────────────────────────

async def main() -> None:
    """CLI entry point: login and search for a property."""
    import argparse, sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from core.ai_infra.xvfb_driver import XvfbDriver

    parser = argparse.ArgumentParser(description="Room-Res.com rate scraper")
    parser.add_argument("--property", default="Westin Kierland Villas",
                        help="Property name to search for")
    parser.add_argument("--check-in", default="2026-07-01",
                        help="Check-in date (YYYY-MM-DD)")
    parser.add_argument("--check-out", default="2026-07-08",
                        help="Check-out date (YYYY-MM-DD)")
    parser.add_argument("--display", type=int, default=99,
                        help="Xvfb display number")
    parser.add_argument("--dump", action="store_true",
                        help="Dump form state and exit without searching")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    profile_dir = Path("/tmp/room_res_profile")
    profile_dir.mkdir(parents=True, exist_ok=True)

    async with XvfbDriver(display_num=args.display, profile_dir=profile_dir) as driver:
        ok = await room_res_login(driver)
        if not ok:
            logger.error("room_res: login failed — aborting")
            await driver.screenshot("/tmp/room_res_login_fail.png")
            return

        if args.dump:
            form_state = await dump_form(driver)
            print(json.dumps(form_state, indent=2, default=str))
            return

        rates = await room_res_search_rates(
            driver,
            property_name=args.property,
            check_in=args.check_in,
            check_out=args.check_out,
        )

        if rates:
            print(f"\nFound {len(rates)} rate(s) for '{args.property}':\n")
            for r in rates:
                print(
                    f"  Room: {r.get('room_type', 'N/A'):40s}  "
                    f"Rate: {r.get('rate_description', ''):30s}  "
                    f"Total: {r.get('currency', 'USD')} {r.get('total_price', 0):>8.2f}  "
                    f"Nightly: {r.get('currency', 'USD')} {r.get('nightly_price', 0):>7.2f}"
                )
        else:
            print(f"\nNo rates found for '{args.property}'")
            await driver.screenshot("/tmp/room_res_no_rates.png")

        await driver.screenshot("/tmp/room_res_result.png")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
