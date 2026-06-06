"""
Viking Cruises agent portal → intel_index connector.
Uses Playwright (headless Chromium) with agent credentials.

Auth: portal_creds.json → viking.email / viking.password
Login: Azure B2C OAuth (login.viking.com) — TA account required.

⚠ TA ACCOUNT REQUIRED — READ THIS
═══════════════════════════════════════════════════════
Current creds (johnloucks3@gmail.com) are a consumer
account. Login redirects to /myjourney/no-active-booking
instead of the TA dashboard. Azure B2C validates the
account tier on auth — consumer creds will never reach
the TA portal regardless of password correctness.

To fix, Commander must register a proper TA account:
  1. Go to https://www.viking.com/travel-advisor
  2. Click "Register" / "Create Account"
  3. Use Nexion host agency credentials:
     - Host: Nexion / Travel Leaders
     - IATAN/CLIA: from Nexion (see Nexion profile)
     - Agency info: per Dreams2Memories Travel, LLC
  4. Verify via email link
  5. Update portal_creds.json → viking.email / viking.password
═══════════════════════════════════════════════════════

TTL: 24h
"""
import logging
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# Correct Travel Advisor portal URL (confirmed from browser history 2026-05-28)
# SSO login: login.viking.com → redirects to www.viking.com/travel-advisor
VIKING_LOGIN = "https://www.viking.com/travel-advisor"
VIKING_AVAIL = "https://www.viking.com/travel-advisor/search"
VIKING_BASE  = "https://www.viking.com"


def ingest_viking(con: sqlite3.Connection, upsert_rows, log_run, ttl: int) -> None:
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except ImportError as e:
        logger.error("viking: playwright not installed: %s", e)
        log_run(con, "viking", "import_error", error=str(e))
        return

    creds_path = Path(__file__).resolve().parents[3] / "config" / "portal_creds.json"
    email = "johnloucks3@gmail.com"
    password = "Falcons4me!"
    if creds_path.exists():
        import json
        try:
            data = json.loads(creds_path.read_text())
            viking = data.get("viking", {})
            email = viking.get("email", email)
            password = viking.get("password", password)
        except Exception:
            pass

    t0 = time.monotonic()
    all_rows = []

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                )
            )
            page = ctx.new_page()

            page.goto(VIKING_LOGIN, timeout=30000)
            page.wait_for_load_state("networkidle", timeout=20000)

            # Azure B2C login form — email field is logonIdentifier (text input), not email type
            for email_sel in [
                "input[name='logonIdentifier']", "input[id='logonIdentifier']",
                "input[type='email']", "input[name='email']", "input[type='text']",
            ]:
                if page.locator(email_sel).count() > 0:
                    page.locator(email_sel).first.press_sequentially(email, delay=50)
                    break

            for pw_sel in ["input[type='password']", "input[name='password']", "input[id='password']"]:
                if page.locator(pw_sel).count() > 0:
                    page.locator(pw_sel).first.press_sequentially(password, delay=50)
                    break

            for submit_sel in [
                "button[type='submit']",
                "input[type='submit']",
                "button:has-text('Sign in')",
                "button:has-text('Log In')",
                "button:has-text('Continue')",
            ]:
                if page.locator(submit_sel).count() > 0:
                    page.click(submit_sel)
                    break

            try:
                page.wait_for_load_state("networkidle", timeout=15000)
            except PWTimeout:
                pass

            page.goto(VIKING_AVAIL, timeout=30000)
            try:
                page.wait_for_load_state("networkidle", timeout=20000)
            except PWTimeout:
                pass

            # Viking uses React — try intercepting embedded state or extracting cards
            html = page.content()
            from bs4 import BeautifulSoup
            import json as _json
            import re

            soup = BeautifulSoup(html, "html.parser")

            # Check for embedded JSON state (next.js or Redux)
            for pattern in [
                r"window\.__(?:STATE|INITIAL_STATE|DATA)__\s*=\s*(\{.+?\});",
                r"<script id=\"__NEXT_DATA__\"[^>]*>(\{.+?\})</script>",
            ]:
                m = re.search(pattern, html, re.DOTALL)
                if m:
                    try:
                        state = _json.loads(m.group(1))
                        # Traverse common state shapes
                        cruises = (
                            state.get("cruises", [])
                            or state.get("voyages", [])
                            or state.get("sailings", [])
                            or state.get("props", {}).get("pageProps", {}).get("cruises", [])
                        )
                        for c in cruises:
                            row = {
                                "id": f"viking_{c.get('id', c.get('voyageCode', len(all_rows)))}",
                                "ship": c.get("ship", c.get("shipName", "")),
                                "voyage_name": c.get("name", c.get("title", "")),
                                "departure_date": c.get("departureDate", c.get("sailDate", "")),
                                "nights": c.get("nights", c.get("duration", "")),
                                "price_from": float(c.get("priceFrom", c.get("price", 0)) or 0),
                                "destination": c.get("destination", c.get("region", "")),
                                "voyage_code": c.get("voyageCode", c.get("code", "")),
                                "embarkation": c.get("embarkation", c.get("portFrom", "")),
                                "disembarkation": c.get("disembarkation", c.get("portTo", "")),
                                "source": "viking_portal",
                                "scraped_at": datetime.now(timezone.utc).isoformat(),
                            }
                            all_rows.append(row)
                        if all_rows:
                            break
                    except Exception as e:
                        logger.debug("viking: state parse failed: %s", e)

            # Card-based fallback
            if not all_rows:
                cards = (
                    soup.select("div[class*='voyage-card']")
                    or soup.select("div[class*='cruise-card']")
                    or soup.select("article[class*='cruise']")
                    or soup.select("[data-testid*='voyage']")
                )
                for card in cards:
                    def _text(sel):
                        el = card.select_one(sel)
                        return el.get_text(strip=True) if el else ""

                    ship = (
                        _text("[class*='ship']")
                        or _text("h3")
                        or _text("h2")
                    )
                    price_raw = _text("[class*='price']") or _text(".price")
                    price_clean = "".join(c for c in price_raw if c.isdigit() or c == ".")
                    try:
                        price = float(price_clean)
                    except ValueError:
                        price = 0.0

                    row = {
                        "id": f"viking_card_{len(all_rows)}",
                        "ship": ship,
                        "departure_date": _text("[class*='date']") or _text(".date"),
                        "nights": _text("[class*='night']"),
                        "price_from": price,
                        "destination": _text("[class*='destination']") or _text("[class*='region']"),
                        "source": "viking_portal",
                        "scraped_at": datetime.now(timezone.utc).isoformat(),
                    }
                    all_rows.append(row)

            browser.close()

    except Exception as e:
        elapsed = time.monotonic() - t0
        log_run(con, "viking", "portal_error", error=str(e), elapsed=elapsed)
        logger.error("viking portal failed: %s", e)
        return

    elapsed = time.monotonic() - t0
    if all_rows:
        n = upsert_rows(
            con, "viking", "agent_inventory", all_rows, ttl,
            provenance=VIKING_AVAIL,
        )
        log_run(con, "viking", "inventory_refresh", rows_in=n, rows_out=n, elapsed=elapsed)
        logger.info("viking/agent_inventory: %d rows in %.1fs", n, elapsed)
    else:
        log_run(con, "viking", "inventory_empty", rows_in=0, rows_out=0, elapsed=elapsed,
                error="No rows scraped — login may have failed or page structure changed")
        logger.warning("viking: 0 rows in %.1fs — check portal login", elapsed)
