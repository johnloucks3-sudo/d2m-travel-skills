"""
Regent Seven Seas agent portal → intel_index connector.

AUTHENTICATION: Cookie injection (not headless login).
Akamai Bot Manager blocks headless Chromium at the CDN edge before the login
page renders. Firefox bypasses it because of Akamai's browser fingerprinting,
but headless Chromium cannot. Solution: inject a pre-authenticated session from
a real Firefox session into the Playwright context.

TO REFRESH COOKIES:
  1. Open Firefox on Chromebook
  2. Navigate to https://www.rssc.com/agent/dashboard/#myBookings
  3. Log in with jl3lovegrouptravel@gmail.com / Falcons4me!
  4. F12 → Application → Cookies → https://www.rssc.com
  5. Run: python3 scripts/export_regent_cookies.py
     OR manually copy all rows as JSON to creds/regent_cookies.json
  6. Format: list of {name, value, domain, path, expires, httpOnly, secure}

TWO ACCOUNTS:
  account_direct (jl3lovegrouptravel@gmail.com):
    Furlow 3071222, Ely 3096289, Nichols 3078056, McLeod Dec-2026 2984034
    cookies: creds/regent_cookies.json
  account_oa (johnloucks3@gmail.com):
    Loucks 3122006, McLeod Dec-2027 3114500
    cookies: creds/regent_cookies_oa.json

TTL: 24h
"""
import json
import logging
import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# The dashboard URL — where authenticated agents land after login
REGENT_DASHBOARD = "https://www.rssc.com/agent/dashboard/#myBookings"
REGENT_CRUISES   = "https://www.rssc.com/cruises"
REGENT_PROMO     = "https://www.rssc.com/offers"

_ROOT = Path(__file__).resolve().parents[3]
_PORTAL_CREDS = _ROOT / "config" / "portal_creds.json"


def _load_portal_creds() -> dict:
    if _PORTAL_CREDS.exists():
        try:
            return json.loads(_PORTAL_CREDS.read_text()).get("regent", {})
        except Exception:
            pass
    return {}


def _load_cookies(cookie_path: Path) -> list[dict]:
    """Load cookies from JSON file. Returns empty list if missing/malformed."""
    if not cookie_path.exists():
        logger.warning("regent: cookie file not found: %s", cookie_path)
        return []
    try:
        cookies = json.loads(cookie_path.read_text())
        if not isinstance(cookies, list):
            logger.warning("regent: cookie file is not a list: %s", cookie_path)
            return []
        return cookies
    except Exception as e:
        logger.error("regent: failed to parse cookie file %s: %s", cookie_path, e)
        return []


def _check_auth(page_html: str) -> bool:
    """Return True if the page content looks like an authenticated agent session."""
    auth_signals = [
        "myBookings",
        "agent-dashboard",
        "agentDashboard",
        "AGENTDASHBOARD",
        "My Bookings",
        "booking-list",
        "voyage-list",
        "Sign Out",
        "Logout",
    ]
    for sig in auth_signals:
        if sig.lower() in page_html.lower():
            return True
    return False


def _scrape_account(pw, cookies: list[dict], account_label: str, all_rows: list) -> bool:
    """
    Open a Playwright browser context with pre-injected cookies, navigate to
    the agent dashboard/cruises, and append scraped rows to all_rows.
    Returns True if auth succeeded, False if cookies appear stale.
    """
    from playwright.sync_api import TimeoutError as PWTimeout

    # Firefox bypasses Akamai Bot Manager fingerprinting; Chromium is blocked at CDN edge
    browser = pw.firefox.launch(headless=True)
    ctx = browser.new_context(
        viewport={"width": 1440, "height": 900},
        locale="en-US",
    )

    # Inject pre-authenticated cookies — only rssc.com cookies matter
    # Normalize sameSite: Playwright requires Strict|Lax|None (no empty string)
    _VALID_SS = {"Strict", "Lax", "None"}
    rssc_raw = [c for c in cookies if "rssc.com" in c.get("domain", "")]
    rssc_cookies = []
    for c in rssc_raw:
        nc = {k: v for k, v in c.items() if k != "sameSite"}
        if c.get("sameSite") in _VALID_SS:
            nc["sameSite"] = c["sameSite"]
        if nc.get("expires") == -1:
            del nc["expires"]
        rssc_cookies.append(nc)

    if not rssc_cookies:
        logger.warning("regent/%s: no rssc.com cookies found", account_label)
        browser.close()
        return False

    try:
        ctx.add_cookies(rssc_cookies)
    except Exception as e:
        logger.error("regent/%s: cookie injection failed: %s", account_label, e)
        browser.close()
        return False

    page = ctx.new_page()

    try:
        # Navigate directly to dashboard — no login form needed if cookies are fresh
        page.goto(REGENT_DASHBOARD, timeout=30000, wait_until="domcontentloaded")
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except PWTimeout:
            pass

        html = page.content()

        if not _check_auth(html):
            logger.warning(
                "regent/%s: dashboard auth check failed — cookies may be stale. "
                "Re-export from Firefox: https://www.rssc.com/agent/dashboard/#myBookings",
                account_label,
            )
            browser.close()
            return False

        logger.info("regent/%s: authenticated via cookie injection", account_label)

        # --- Scrape cruise inventory ---
        page.goto(REGENT_CRUISES, timeout=30000, wait_until="domcontentloaded")
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except PWTimeout:
            pass

        cruise_html = page.content()
        _parse_cruises(cruise_html, account_label, all_rows)

    except Exception as e:
        logger.error("regent/%s: scrape error: %s", account_label, e)
        browser.close()
        return False

    browser.close()
    return True


def _parse_cruises(html: str, source_label: str, all_rows: list) -> None:
    """Parse cruise data from page HTML into all_rows."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")

    # Try window.__STATE__ / window.__DATA__ embedded JSON first
    state_match = re.search(
        r"window\.__(?:STATE|DATA|INITIAL_STATE|NEXT_DATA)__\s*=\s*(\{.+?\});",
        html,
        re.DOTALL,
    )
    if state_match:
        try:
            state = json.loads(state_match.group(1))
            voyages = (
                state.get("cruises")
                or state.get("voyages")
                or state.get("sailings")
                or []
            )
            for v in voyages:
                row = {
                    "id": f"regent_{source_label}_{v.get('id', len(all_rows))}",
                    "ship": v.get("ship", v.get("shipName", "")),
                    "voyage_name": v.get("name", v.get("voyageName", "")),
                    "departure_date": v.get("departureDate", v.get("sailDate", "")),
                    "nights": v.get("nights", v.get("duration", "")),
                    "price_from": float(v.get("priceFrom", v.get("price", 0)) or 0),
                    "destination": v.get("destination", v.get("region", "")),
                    "itinerary": v.get("itinerary", ""),
                    "voyage_code": v.get("voyageCode", v.get("code", "")),
                    "source": f"regent_{source_label}",
                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                }
                all_rows.append(row)
            if voyages:
                return
        except Exception as e:
            logger.debug("regent: window state parse failed: %s", e)

    # Fallback: DOM card extraction
    cards = (
        soup.select("div[class*='cruise-card']")
        or soup.select("article[class*='cruise']")
        or soup.select("div[class*='voyage']")
        or soup.select("[data-testid*='cruise']")
        or soup.select("div[class*='sailing']")
    )

    def _text(el):
        return el.get_text(strip=True) if el else ""

    def _price(el):
        t = _text(el)
        cleaned = "".join(c for c in t if c.isdigit() or c == ".")
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    for card in cards:
        ship_el = card.select_one("[class*='ship']") or card.select_one("h3") or card.select_one("h2")
        price_el = card.select_one("[class*='price']") or card.select_one(".price")
        date_el = card.select_one("[class*='date']") or card.select_one(".date")
        nights_el = card.select_one("[class*='night']")
        dest_el = card.select_one("[class*='destination']") or card.select_one("[class*='region']")

        row = {
            "id": f"regent_{source_label}_card_{len(all_rows)}",
            "ship": _text(ship_el),
            "voyage_name": _text(dest_el),
            "departure_date": _text(date_el),
            "nights": _text(nights_el),
            "price_from": _price(price_el),
            "source": f"regent_{source_label}",
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        }
        all_rows.append(row)


def ingest_regent(con: sqlite3.Connection, upsert_rows, log_run, ttl: int) -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        logger.error("regent: playwright not installed: %s", e)
        log_run(con, "regent", "import_error", error=str(e))
        return

    creds = _load_portal_creds()
    acct_direct = creds.get("account_direct", {})
    acct_oa = creds.get("account_oa", {})

    direct_cookie_path = _ROOT / acct_direct.get("cookies", "creds/regent_cookies.json")
    oa_cookie_path = _ROOT / acct_oa.get("cookies", "creds/regent_cookies_oa.json")

    t0 = time.monotonic()
    all_rows: list[dict] = []

    with sync_playwright() as pw:
        # Account 1: direct (jl3lovegrouptravel) — Furlow, Ely, Nichols, McLeod Dec-2026
        direct_cookies = _load_cookies(direct_cookie_path)
        if direct_cookies:
            ok = _scrape_account(pw, direct_cookies, "direct", all_rows)
            if not ok:
                log_run(
                    con, "regent", "auth_stale",
                    error=(
                        "direct account cookies stale — re-export from Firefox at "
                        "https://www.rssc.com/agent/dashboard/#myBookings "
                        "(jl3lovegrouptravel@gmail.com)"
                    ),
                    elapsed=time.monotonic() - t0,
                )
        else:
            logger.info("regent: no direct-account cookies — skipping direct account")

        # Account 2: OA (johnloucks3) — Loucks, McLeod Dec-2027
        oa_cookies = _load_cookies(oa_cookie_path)
        if oa_cookies:
            _scrape_account(pw, oa_cookies, "oa", all_rows)
        else:
            logger.info("regent: no OA-account cookies — skipping OA account")

    elapsed = time.monotonic() - t0

    if all_rows:
        n = upsert_rows(
            con, "regent", "agent_inventory", all_rows, ttl,
            provenance=REGENT_DASHBOARD,
        )
        log_run(con, "regent", "inventory_refresh", rows_in=n, rows_out=n, elapsed=elapsed)
        logger.info("regent/agent_inventory: %d rows in %.1fs", n, elapsed)
    else:
        log_run(
            con, "regent", "inventory_empty",
            rows_in=0, rows_out=0, elapsed=elapsed,
            error="0 rows — cookies stale or portal structure changed",
        )
        logger.warning("regent: 0 rows in %.1fs — cookies need refresh", elapsed)
