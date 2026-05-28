"""
Regent Seven Seas agent portal → intel_index connector.
Uses Playwright (headless Chromium) with agent credentials.
Creds: jlelovegrouptravel@gmail.com / Falcons4me!
TTL: 24h
"""
import logging
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

REGENT_PORTAL = "https://www.rssc.com/travel-agents"
REGENT_LOGIN  = "https://www.rssc.com/login"
REGENT_AVAIL  = "https://www.rssc.com/cruises"


def ingest_regent(con: sqlite3.Connection, upsert_rows, log_run, ttl: int) -> None:
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except ImportError as e:
        logger.error("regent: playwright not installed: %s", e)
        log_run(con, "regent", "import_error", error=str(e))
        return

    # Load creds from portal_creds.json if present, else use defaults
    creds_path = Path(__file__).resolve().parents[3] / "config" / "portal_creds.json"
    email = "jlelovegrouptravel@gmail.com"
    password = "Falcons4me!"
    if creds_path.exists():
        import json
        try:
            data = json.loads(creds_path.read_text())
            regent = data.get("regent", {})
            email = regent.get("email", email)
            password = regent.get("password", password)
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

            # Navigate to login
            page.goto(REGENT_LOGIN, timeout=30000)
            page.wait_for_load_state("networkidle", timeout=20000)

            # Fill login form — try multiple selectors
            for email_sel in ["input[name='email']", "input[type='email']", "#email", "#username"]:
                if page.locator(email_sel).count() > 0:
                    page.fill(email_sel, email)
                    break

            for pw_sel in ["input[name='password']", "input[type='password']", "#password"]:
                if page.locator(pw_sel).count() > 0:
                    page.fill(pw_sel, password)
                    break

            for submit_sel in ["button[type='submit']", "input[type='submit']", "button:has-text('Sign In')", "button:has-text('Login')"]:
                if page.locator(submit_sel).count() > 0:
                    page.click(submit_sel)
                    break

            try:
                page.wait_for_load_state("networkidle", timeout=15000)
            except PWTimeout:
                pass

            # Navigate to availability/cruises page
            page.goto(REGENT_AVAIL, timeout=30000)
            try:
                page.wait_for_load_state("networkidle", timeout=20000)
            except PWTimeout:
                pass

            # Scrape cruise listings — Regent uses a dynamic React/Angular UI
            # Try to grab cards from page content
            html = page.content()

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")

            cards = (
                soup.select("div[class*='cruise-card']")
                or soup.select("article[class*='cruise']")
                or soup.select("div[class*='voyage']")
                or soup.select("[data-testid*='cruise']")
            )

            # Also try JSON-LD or window.__STATE__ embedded data
            import json as _json
            import re
            state_match = re.search(r"window\.__(?:STATE|DATA|INITIAL_STATE)__\s*=\s*(\{.+?\});", html, re.DOTALL)
            if state_match:
                try:
                    state = _json.loads(state_match.group(1))
                    voyages = (
                        state.get("cruises", [])
                        or state.get("voyages", [])
                        or state.get("sailings", [])
                    )
                    for v in voyages:
                        row = {
                            "id": f"regent_{v.get('id', len(all_rows))}",
                            "ship": v.get("ship", v.get("shipName", "")),
                            "voyage_name": v.get("name", v.get("voyageName", "")),
                            "departure_date": v.get("departureDate", v.get("sailDate", "")),
                            "nights": v.get("nights", v.get("duration", "")),
                            "price_from": float(v.get("priceFrom", v.get("price", 0)) or 0),
                            "destination": v.get("destination", v.get("region", "")),
                            "itinerary": v.get("itinerary", ""),
                            "voyage_code": v.get("voyageCode", v.get("code", "")),
                            "source": "regent_portal",
                            "scraped_at": datetime.now(timezone.utc).isoformat(),
                        }
                        all_rows.append(row)
                except Exception as e:
                    logger.debug("regent: window state parse failed: %s", e)

            # Fallback card extraction
            if not all_rows:
                for card in cards:
                    ship_el = card.select_one("[class*='ship']") or card.select_one("h3") or card.select_one("h2")
                    price_el = card.select_one("[class*='price']") or card.select_one(".price")
                    date_el = card.select_one("[class*='date']") or card.select_one(".date")
                    nights_el = card.select_one("[class*='night']")
                    dest_el = card.select_one("[class*='destination']") or card.select_one("[class*='region']")

                    def _text(el):
                        return el.get_text(strip=True) if el else ""

                    def _price(el):
                        t = _text(el)
                        cleaned = "".join(c for c in t if c.isdigit() or c == ".")
                        try:
                            return float(cleaned)
                        except ValueError:
                            return 0.0

                    row = {
                        "id": f"regent_card_{len(all_rows)}",
                        "ship": _text(ship_el),
                        "voyage_name": _text(dest_el),
                        "departure_date": _text(date_el),
                        "nights": _text(nights_el),
                        "price_from": _price(price_el),
                        "source": "regent_portal",
                        "scraped_at": datetime.now(timezone.utc).isoformat(),
                    }
                    all_rows.append(row)

            browser.close()

    except Exception as e:
        elapsed = time.monotonic() - t0
        log_run(con, "regent", "portal_error", error=str(e), elapsed=elapsed)
        logger.error("regent portal failed: %s", e)
        return

    elapsed = time.monotonic() - t0
    if all_rows:
        n = upsert_rows(
            con, "regent", "agent_inventory", all_rows, ttl,
            provenance=REGENT_AVAIL,
        )
        log_run(con, "regent", "inventory_refresh", rows_in=n, rows_out=n, elapsed=elapsed)
        logger.info("regent/agent_inventory: %d rows in %.1fs", n, elapsed)
    else:
        log_run(con, "regent", "inventory_empty", rows_in=0, rows_out=0, elapsed=elapsed,
                error="No rows scraped — login may have failed or page structure changed")
        logger.warning("regent: 0 rows in %.1fs — check portal login", elapsed)
