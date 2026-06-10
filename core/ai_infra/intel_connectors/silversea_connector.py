"""
Silversea (my.silversea.com) → intel_index connector.

AUTHENTICATION: Standard forms login (email + password).
my.silversea.com is an ASP.NET MVC portal — NOT the Gatsby SPA at silversea.com.
Commander's user type is 'Agency' (confirmed from DataLayer custom_usertype).

NO dedicated TA agent portal exists. Silversea uses a consumer portal with
Agency accounts for travel advisors. Bookings are managed via:
  1. my.silversea.com (Agency account — per-booking guest access)
  2. Perx Travel interline portal for TA rates
  3. Email-based changes via tradereservations@silversea.com

CREDENTIALS: portal_creds.json → silversea.email / silversea.password
TTL: 24h

BOOKINGS ON FILE (Commander's Agency account):
  - 298475-25: McLeod/McGlasson — Silver Muse, Jun 23–Jul 3, 2026 (PAID)
  - 566910-25: Loucks/Loucks — Silver Nova, Tokyo→Seattle, Apr 23–May 8 2026 (COMPLETE)
"""
import json
import logging
import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

SILVERSEA_BASE = "https://my.silversea.com"
SILVERSEA_LOGIN = "https://my.silversea.com/Account/Login"
SILVERSEA_BOOKINGS = "https://my.silversea.com/MyBookings"
SILVERSEA_PROFILE = "https://my.silversea.com/profile/account"
SILVERSEA_ACTIVITIES = "https://my.silversea.com/activities2"

_ROOT = Path(__file__).resolve().parents[3]
_PORTAL_CREDS = _ROOT / "config" / "portal_creds.json"


def _load_portal_creds() -> dict:
    if _PORTAL_CREDS.exists():
        try:
            return json.loads(_PORTAL_CREDS.read_text()).get("silversea", {})
        except Exception:
            pass
    return {}


def _check_auth(page_html: str) -> bool:
    auth_signals = [
        "MyBookings",
        "Log out",
        "Logout",
        "BOOKINGS",
        "mybookings",
        "Create Booking",
        "Modify",
        "Agency",
    ]
    for sig in auth_signals:
        if sig.lower() in page_html.lower():
            return True
    return False


def _parse_bookings_page(html: str) -> list[dict]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    bookings = []

    # Extract booking codes from Modify/Activities links
    # Pattern: /bookings/modify?code=298475-25 or /activities2/#/298475-25
    booking_codes = set()
    for a_tag in soup.find_all("a", href=True):
        href = str(a_tag.get("href", ""))
        m = re.search(r"[?&]code=([\w\-]+)", href)
        if m:
            booking_codes.add(m.group(1))
        m = re.search(r"/activities2/#/([\w\-]+)", href)
        if m:
            booking_codes.add(m.group(1))

    # Try embedded JSON state (ASP.NET MVC may have serialized models)
    for script in soup.find_all("script"):
        if script.string:
            # Look for JSON model data embedded in Razor views
            for pattern in [
                r"window\.__INITIAL_STATE__\s*=\s*(\{.+?\});",
                r"var\s+bookingData\s*=\s*(\{.+?\});",
                r"var\s+model\s*=\s*(\{.+?\});",
                r"var\s+bookings\s*=\s*(\[.+?\]);",
            ]:
                m = re.search(pattern, script.string, re.DOTALL)
                if m:
                    try:
                        data = json.loads(m.group(1))
                        if isinstance(data, list):
                            raw_bookings = data
                        elif isinstance(data, dict):
                            raw_bookings = (
                                data.get("bookings", [])
                                or data.get("Bookings", [])
                                or data.get("model", [])
                                or data.get("data", [])
                            )
                        else:
                            raw_bookings = []

                        for b in raw_bookings:
                            booking = {
                                "booking_reference": b.get("code", b.get("Code", b.get("bookingCode", ""))),
                                "ship": b.get("ship", b.get("Ship", b.get("shipName", ""))),
                                "voyage_code": b.get("voyage", b.get("Voyage", b.get("voyageCode", ""))),
                                "departure_date": b.get("departure", b.get("Departure", b.get("sailDate", ""))),
                                "return_date": b.get("return", b.get("Return", b.get("endDate", ""))),
                                "duration_nights": b.get("duration", b.get("Duration", b.get("nights", ""))),
                                "cabin": b.get("cabin", b.get("Cabin", b.get("suite", ""))),
                                "status": b.get("status", b.get("Status", "")),
                                "payment_status": b.get("payment", b.get("Payment", "")),
                                "guests": b.get("guests", b.get("Guests", b.get("passengers", []))),
                                "source": "silversea_portal",
                                "scraped_at": datetime.now(timezone.utc).isoformat(),
                            }
                            # Clean date formats
                            for date_field in ["departure_date", "return_date"]:
                                val = booking.get(date_field, "")
                                if isinstance(val, str):
                                    val = val.replace("T00:00:00", "").replace("T00:00:00Z", "")
                                    if re.match(r"^\d{4}-\d{2}-\d{2}$", val[:10]):
                                        booking[date_field] = val[:10]
                            bookings.append(booking)
                        if bookings:
                            return bookings
                    except Exception:
                        continue

    # DOM-based extraction: find booking cards / rows
    # Common Silversea pattern: each booking is a <div class="booking-row"> or <tr>
    booking_rows = (
        soup.select("[class*='booking-row']")
        or soup.select("tr[class*='booking']")
        or soup.select("div[class*='voyage-card']")
        or soup.select("[data-booking-code]")
        or soup.select(".booking-item, .booking-card, [class*='booking_']")
    )

    for row in booking_rows:
        code_el = row.select_one("[class*='code'], [class*='booking-code'], .booking-id, [data-booking-code]")
        code = code_el.get_text(strip=True) if code_el else ""
        if not code:
            code_attr = row.get("data-booking-code", "")
            if code_attr:
                code = code_attr

        if not code and booking_codes:
            code = next(iter(booking_codes)) if len(booking_codes) == 1 else ""

        def _txt(sel):
            el = row.select_one(sel)
            return el.get_text(strip=True) if el else ""

        booking = {
            "booking_reference": code,
            "ship": _txt("[class*='ship']") or _txt("[class*='vessel']"),
            "departure_date": _txt("[class*='date']") or _txt("[class*='sail']") or _txt("[class*='depart']"),
            "duration_nights": _txt("[class*='night']") or _txt("[class*='duration']"),
            "cabin": _txt("[class*='cabin']") or _txt("[class*='suite']") or _txt("[class*='category']"),
            "status": _txt("[class*='status']") or _txt("[class*='state']"),
            "destination": _txt("[class*='destination']") or _txt("[class*='region']") or _txt("[class*='itinerary']"),
            "guests": _txt("[class*='guest']") or _txt("[class*='name']") or _txt("[class*='passenger']"),
            "source": "silversea_portal",
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        }
        bookings.append(booking)

    # Filter out non-booking codes (e.g., Create Booking links, other routes)
    booking_codes = {c for c in booking_codes if re.match(r"^\d{5,6}-\d{2}$", c)}

    # Always create entries for each unique booking code found in links
    # This ensures we capture bookings even if DOM structure is opaque
    if booking_codes:
        existing_codes = {b.get("booking_reference", "") for b in bookings}
        for code in sorted(booking_codes):
            if code not in existing_codes:
                bookings.append({
                    "booking_reference": code,
                    "source": "silversea_portal",
                    "_extracted_from": "page_links",
                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                })

    # If DOM extraction yielded nothing, return booking codes as minimal entries
    if not bookings and booking_codes:
        for code in sorted(booking_codes):
            bookings.append({
                "booking_reference": code,
                "source": "silversea_portal",
                "scraped_at": datetime.now(timezone.utc).isoformat(),
                "_note": "Extracted from page links — full details require booking detail scrape",
            })

    return bookings


def _scrape_booking_detail(page, booking_code: str) -> dict:
    """Navigate to a specific booking's detail page and extract data."""
    detail_url = f"{SILVERSEA_BASE}/bookings/modify?code={booking_code}"
    detail: dict = {"booking_reference": booking_code}

    try:
        page.goto(detail_url, timeout=30000, wait_until="domcontentloaded")
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass

        html = page.content()
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")

        detail["_detail_page_url"] = detail_url

        # Extract page title / heading
        h1 = soup.find("h1")
        if h1:
            detail["title"] = h1.get_text(strip=True)

        # Look for booking summary in definition lists or structured tables
        for dl in soup.find_all("dl"):
            terms = dl.find_all("dt")
            defs = dl.find_all("dd")
            for dt, dd in zip(terms, defs):
                key = dt.get_text(strip=True).lower()
                val = dd.get_text(strip=True)
                if "ship" in key or "vessel" in key:
                    detail["ship"] = val
                elif "voyage" in key:
                    detail["voyage_code"] = val
                elif "date" in key or "sail" in key or "depart" in key:
                    detail["departure_date"] = val
                elif "duration" in key or "night" in key:
                    detail["duration_nights"] = val
                elif "cabin" in key or "suite" in key or "category" in key:
                    detail["cabin"] = val
                elif "status" in key or "state" in key:
                    detail["status"] = val
                elif "payment" in key or "balance" in key or "paid" in key:
                    detail["payment_status"] = val

        # Look for tabular data
        for table in soup.find_all("table"):
            headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]
            for tr in table.find_all("tr")[1:]:
                cells = tr.find_all("td")
                for h, td in zip(headers, cells):
                    val = td.get_text(strip=True)
                    if "passenger" in h or "guest" in h or "name" in h:
                        if "guests" not in detail:
                            detail["guests"] = []
                        detail["guests"].append(val)
                    elif "cabin" in h or "suite" in h:
                        detail["cabin"] = val
                    elif "status" in h:
                        detail["status"] = val
                    elif "amount" in h or "total" in h or "price" in h:
                        detail["total_amount"] = val

    except Exception as e:
        logger.debug("silversea: detail scrape failed for %s: %s", booking_code, e)

    return detail


def ingest_silversea(con: sqlite3.Connection, upsert_rows, log_run, ttl: int) -> None:
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except ImportError as e:
        logger.error("silversea: playwright not installed: %s", e)
        log_run(con, "silversea", "import_error", error=str(e))
        return

    creds = _load_portal_creds()
    email = creds.get("email", "")
    password = creds.get("password", "")

    if not email or not password:
        log_run(
            con, "silversea", "auth_missing",
            error="No credentials in portal_creds.json → silversea.email / silversea.password",
        )
        logger.warning("silversea: no credentials configured — Commander must provide")
        return

    t0 = time.monotonic()
    all_bookings: list[dict] = []

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                ],
            )
            ctx = browser.new_context(
                viewport={"width": 1440, "height": 900},
                locale="en-US",
                user_agent=(
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
                ),
            )
            page = ctx.new_page()

            # --- Step 1: Navigate to login ---
            page.goto(SILVERSEA_LOGIN, timeout=30000, wait_until="domcontentloaded")
            try:
                page.wait_for_load_state("networkidle", timeout=15000)
            except PWTimeout:
                pass

            # --- Step 2: Fill login form ---
            for email_sel in [
                "input[name='Email']",
                "input[name='email']",
                "input[id='Email']",
                "input[id='email']",
                "input[type='email']",
                "input[name='Username']",
                "input[id='Username']",
                "input[name='username']",
            ]:
                if page.locator(email_sel).count() > 0:
                    page.locator(email_sel).first.fill(email)
                    break

            for pw_sel in [
                "input[name='Password']",
                "input[name='password']",
                "input[id='Password']",
                "input[id='password']",
                "input[type='password']",
            ]:
                if page.locator(pw_sel).count() > 0:
                    page.locator(pw_sel).first.fill(password)
                    break

            for submit_sel in [
                "button[type='submit']",
                "input[type='submit']",
                "button:has-text('Sign In')",
                "button:has-text('Log In')",
                "button:has-text('Login')",
                "button:has-text('Continue')",
                "input[value*='Sign']",
                "input[value*='Log']",
            ]:
                if page.locator(submit_sel).count() > 0:
                    page.locator(submit_sel).first.click()
                    break

            try:
                page.wait_for_load_state("networkidle", timeout=20000)
            except PWTimeout:
                pass

            # --- Step 3: Navigate to My Bookings ---
            page.goto(SILVERSEA_BOOKINGS, timeout=30000, wait_until="domcontentloaded")
            try:
                page.wait_for_load_state("networkidle", timeout=15000)
            except PWTimeout:
                pass

            html = page.content()

            if not _check_auth(html):
                logger.warning(
                    "silversea: auth check failed — login may have failed or "
                    "credentials are incorrect"
                )
                browser.close()
                log_run(
                    con, "silversea", "auth_failed",
                    error="Login failed — check silversea credentials in portal_creds.json",
                    elapsed=time.monotonic() - t0,
                )
                return

            logger.info("silversea: authenticated as %s", email)

            # --- Step 4: Parse bookings list ---
            bookings_list = _parse_bookings_page(html)
            logger.info("silversea: found %d booking references", len(bookings_list))

            # --- Step 5: Enrich with detail pages ---
            for b in bookings_list:
                code = b.get("booking_reference", "")
                if code:
                    detail = _scrape_booking_detail(page, code)
                    b.update({k: v for k, v in detail.items() if v and k != "booking_reference"})

            all_bookings = bookings_list
            browser.close()

    except Exception as e:
        elapsed = time.monotonic() - t0
        log_run(con, "silversea", "portal_error", error=str(e), elapsed=elapsed)
        logger.error("silversea portal failed: %s", e)
        return

    elapsed = time.monotonic() - t0

    if all_bookings:
        n = upsert_rows(
            con, "silversea", "agent_bookings", all_bookings, ttl,
            provenance=SILVERSEA_BOOKINGS,
        )
        log_run(
            con, "silversea", "bookings_refresh",
            rows_in=n, rows_out=n, elapsed=elapsed,
        )
        logger.info("silversea/agent_bookings: %d rows in %.1fs", n, elapsed)
    else:
        log_run(
            con, "silversea", "bookings_empty",
            rows_in=0, rows_out=0, elapsed=elapsed,
            error="0 rows — login failed or portal structure changed",
        )
        logger.warning("silversea: 0 rows in %.1fs — check portal login", elapsed)
