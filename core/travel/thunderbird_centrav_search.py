"""
Thunderbird Centrav B2B Flight Search — MCP Module
====================================================
Dreams2Memories Travel, LLC · M-038 CENTRAV

Playwright-based authenticated scraper for Centrav B2B portal.
No public API — session cookie auth + headless Chromium.

Session files:
  ~/Thunderbird/centrav_credentials.json      — email/password/cookie dict
  ~/Thunderbird/core/travel/data/centrav_session.json — playwright cookie list
  ~/Thunderbird/creds/centrav_cookies.json    — alternate cookie source

MCP tools:
  search_centrav_flights    — run B2B price search for a route/date/cabin
  check_centrav_session     — verify session validity (fast, no search)
  centrav_save_session      — store current browser cookies to disk
"""

import asyncio
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import Field
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────

THUNDERBIRD = Path.home() / "Thunderbird"
CREDS_PATH = THUNDERBIRD / "centrav_credentials.json"
SESSION_FILE = THUNDERBIRD / "core" / "travel" / "data" / "centrav_session.json"
ALT_COOKIES = THUNDERBIRD / "creds" / "centrav_cookies.json"
DATA_DIR = THUNDERBIRD / "core" / "travel" / "data"
OUTPUT_DIR = THUNDERBIRD / "output"
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Credentials ───────────────────────────────────────────────────────────────

def _load_creds() -> dict:
    if CREDS_PATH.exists():
        try:
            return json.loads(CREDS_PATH.read_text())
        except Exception:
            pass
    return {}

_CREDS = _load_creds()
CENTRAV_EMAIL = _CREDS.get("email", "")
CENTRAV_PASS = _CREDS.get("password", "")


def _build_playwright_cookies() -> list[dict]:
    """Merge cookies from all sources. Session file takes priority."""
    merged: dict[str, dict] = {}

    # 1. credentials file cookie dict (oldest)
    for name, value in _CREDS.get("cookies", {}).items():
        merged[name] = {
            "name": name,
            "value": value,
            "domain": ".centrav.com" if name.startswith("_g") else "www.centrav.com",
            "path": "/",
        }

    # 2. alt cookies file (medium)
    if ALT_COOKIES.exists():
        try:
            alt = json.loads(ALT_COOKIES.read_text())
            if isinstance(alt, list):
                for c in alt:
                    if c.get("name"):
                        merged[c["name"]] = {
                            "name": c["name"],
                            "value": c.get("value", ""),
                            "domain": c.get("domain", "www.centrav.com"),
                            "path": c.get("path", "/"),
                        }
        except Exception:
            pass

    # 3. session file (newest — highest priority)
    if SESSION_FILE.exists():
        try:
            sess = json.loads(SESSION_FILE.read_text())
            if isinstance(sess, list):
                for c in sess:
                    if c.get("name"):
                        merged[c["name"]] = {
                            "name": c["name"],
                            "value": c.get("value", ""),
                            "domain": c.get("domain", "www.centrav.com"),
                            "path": c.get("path", "/"),
                        }
        except Exception:
            pass

    return list(merged.values())


def _save_cookies(cookies: list[dict]) -> None:
    SESSION_FILE.write_text(json.dumps(cookies, indent=2))
    logger.info("centrav: session saved → %s", SESSION_FILE)


# ── Session check ─────────────────────────────────────────────────────────────

async def _check_session_live(context) -> bool:
    """Return True if saved cookies give authenticated access."""
    cookies = _build_playwright_cookies()
    if not cookies:
        return False
    try:
        await context.add_cookies(cookies)
    except Exception:
        return False

    page = await context.new_page()
    try:
        await page.goto(
            "https://www.centrav.com/",
            wait_until="domcontentloaded",
            timeout=25_000,
        )
        await page.wait_for_timeout(2_500)
        url = page.url
        text = (await page.inner_text("body")).lower()

        if "login" in url.lower():
            return False

        # Use button visibility to detect auth state reliably.
        # Both #MainLoginButton and #LogoutButton are in DOM on all pages —
        # one is visible, the other hidden based on auth state.
        try:
            logout_btn = page.locator("#LogoutButton")
            if await logout_btn.is_visible(timeout=2_000):
                return True
            login_btn = page.locator("#MainLoginButton")
            if await login_btn.is_visible(timeout=2_000):
                return False
        except Exception:
            pass

        # Last-resort text fallback
        if "log out" in text or "my account" in text:
            return True
        return False
    except Exception as exc:
        logger.warning("centrav: session check error: %s", exc)
        return False
    finally:
        await page.close()


async def _auto_login(context) -> bool:
    """
    Attempt to log in with credentials from centrav_credentials.json.
    On success, saves fresh cookies and returns True.
    """
    if not CENTRAV_EMAIL or not CENTRAV_PASS:
        logger.error("centrav: no credentials configured — cannot auto-login")
        return False

    page = await context.new_page()
    try:
        logger.info("centrav: attempting auto-login as %s", CENTRAV_EMAIL)
        await page.goto(
            "https://www.centrav.com/login",
            wait_until="domcontentloaded",
            timeout=25_000,
        )
        await page.wait_for_timeout(1_500)

        # Exact selectors from probed DOM (2026-05-28)
        await page.fill("#FormEmail", CENTRAV_EMAIL)
        await page.wait_for_timeout(300)
        await page.fill("#FormPassword", CENTRAV_PASS)
        await page.wait_for_timeout(300)
        await page.click("#MainLoginButton")
        await page.wait_for_timeout(4_500)

        url = page.url

        # Detect CAPTCHA before checking login result
        try:
            captcha = await page.query_selector(
                "iframe[src*='recaptcha'], .g-recaptcha, #rc-anchor-container, "
                "iframe[title*='challenge'], [class*='captcha']"
            )
            if captcha:
                logger.warning(
                    "centrav: CAPTCHA required — run "
                    "python3 scripts/centrav_flights.py --centrav-login to authenticate"
                )
                return False
        except Exception:
            pass

        # Check LogoutButton visibility — it only becomes visible after successful login
        try:
            logout_btn = page.locator("#LogoutButton")
            if await logout_btn.is_visible(timeout=3_000):
                fresh = await context.cookies()
                _save_cookies(fresh)
                logger.info("centrav: auto-login succeeded — session refreshed (%s)", url)
                return True
        except Exception:
            pass

        # Still on login page = failed
        if "login" in url.lower():
            logger.warning(
                "centrav: auto-login failed — still on login page. "
                "Run: python3 scripts/centrav_flights.py --centrav-login"
            )
            return False

        # Not on login page, logout button not visible — unknown state, optimistic save
        body = (await page.inner_text("body")).lower()
        if "sign up" not in body:
            fresh = await context.cookies()
            _save_cookies(fresh)
            logger.info("centrav: auto-login optimistic save (url=%s)", url)
            return True

        logger.warning("centrav: auto-login uncertain — url=%s", url)
        return False

    except Exception as exc:
        logger.error("centrav: auto-login error: %s", exc)
        return False
    finally:
        await page.close()


# ── Playwright helpers ────────────────────────────────────────────────────────

_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def _price_parse(raw: list[str], adults: int = 1) -> tuple[Optional[float], Optional[float]]:
    """Return (lowest_total, lowest_pp). Filters implausible values."""
    lowest = None
    for p in raw:
        try:
            val = float(re.sub(r"[^\d.]", "", str(p).replace(",", "")))
            if 40 < val < 25_000:
                if lowest is None or val < lowest:
                    lowest = val
        except (ValueError, TypeError):
            continue
    if lowest is None:
        return None, None
    pp = round(lowest / adults, 2) if adults > 0 else lowest
    return round(lowest, 2), pp


# ── Centrav search ────────────────────────────────────────────────────────────

_CABIN_INPUT = {
    "economy": "ECONOMY",
    "premium": "PREMIUM_ECONOMY",
    "business": "BUSINESS",
    "first": "FIRST",
}
_CABIN_TAB = {
    "economy": "Economy",
    "premium": "Premium Economy",
    "business": "Business",
    "first": "First",
}


async def _search_one_cabin(
    context,
    origin: str,
    dest: str,
    date_str: str,  # MM/DD/YYYY
    adults: int,
    cabin: str,
) -> dict:
    cabin_input = _CABIN_INPUT.get(cabin, "ECONOMY")
    cabin_tab = _CABIN_TAB.get(cabin, "Economy")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    screenshot = DATA_DIR / f"centrav_{cabin}_{origin}_{dest}_{ts}.png"

    page = await context.new_page()
    result: dict = {
        "source": "centrav_b2b",
        "cabin": cabin,
        "origin": origin,
        "dest": dest,
        "date": date_str,
        "adults": adults,
        "raw_prices": [],
        "airlines": [],
        "lowest_total": None,
        "lowest_pp": None,
        "status": "error",
        "screenshot": str(screenshot),
    }

    try:
        await page.goto(
            "https://www.centrav.com/",
            wait_until="domcontentloaded",
            timeout=30_000,
        )
        await page.wait_for_timeout(2_000)

        # Set hidden inputs
        await page.evaluate(f"""() => {{
            const t = document.getElementById('FareTripTypeInput');
            if (t) t.value = 'OneWay';
            const c = document.getElementById('CabinClassInput');
            if (c) c.value = '{cabin_input}';
        }}""")

        # Click One Way + cabin tab
        for label in ("One Way", cabin_tab):
            try:
                await page.click(f"text='{label}'", timeout=3_000)
            except Exception:
                pass
            await page.wait_for_timeout(200)

        # Flying From
        await page.click("#FareFlyingFrom")
        await page.fill("#FareFlyingFrom", "")
        await page.type("#FareFlyingFrom", origin, delay=80)
        await page.wait_for_timeout(1_800)
        try:
            await page.locator(".tt-suggestion").filter(has_text=origin).first.click(timeout=5_000)
        except Exception:
            try:
                await page.locator(".tt-suggestion").first.click(timeout=3_000)
            except Exception:
                await page.keyboard.press("ArrowDown")
                await page.keyboard.press("Enter")
        await page.wait_for_timeout(500)

        # Flying To
        await page.click("#FareFlyingTo")
        await page.fill("#FareFlyingTo", "")
        await page.type("#FareFlyingTo", dest, delay=80)
        await page.wait_for_timeout(1_800)
        try:
            await page.locator(".tt-suggestion").filter(has_text=dest).first.click(timeout=5_000)
        except Exception:
            try:
                visible = page.locator(".tt-suggestion").filter(visible=True).first
                await visible.click(timeout=3_000)
            except Exception:
                await page.keyboard.press("ArrowDown")
                await page.keyboard.press("Enter")
        await page.wait_for_timeout(500)

        # Date
        await page.click("#FareDepartureDate")
        await page.fill("#FareDepartureDate", date_str)
        await page.keyboard.press("Tab")
        await page.wait_for_timeout(400)

        # Adults
        await page.select_option("#Adults", str(adults))
        await page.wait_for_timeout(300)

        # Submit
        await page.click("button:has-text('SEARCH FOR FARES')")
        await page.wait_for_timeout(10_000)
        await page.screenshot(path=str(screenshot))

    except Exception as exc:
        logger.error("centrav: form error for %s %s→%s: %s", cabin, origin, dest, exc)
        try:
            await page.screenshot(path=str(screenshot))
        except Exception:
            pass
        result["error"] = str(exc)
        await page.close()
        return result

    # Extract prices
    raw = await page.evaluate("""() => {
        const out = [];
        const sels = ['[class*="price"]','[class*="fare"]','[class*="amount"]','td','span'];
        for (const sel of sels) {
            document.querySelectorAll(sel).forEach(el => {
                const t = (el.innerText || el.textContent || '').trim();
                if (/^\$[\d,]+$/.test(t)) out.push(t);
            });
            if (out.length > 3) break;
        }
        return [...new Set(out)].slice(0, 20);
    }""")

    if not raw:
        body = await page.inner_text("body")
        raw = list(dict.fromkeys(
            m for m in re.findall(r'\$[\d,]+', body)
            if 40 < int(m.replace("$", "").replace(",", "")) < 25_000
        ))[:15]

    airlines = await page.evaluate("""() => {
        const skip = new Set(['only','nonstop','stops','stop','filters','all','any',
            'sort','cabin','class','economy','premium','business','first']);
        const names = [];
        document.querySelectorAll('[class*="airline"],[class*="carrier"]').forEach(el => {
            const t = (el.innerText || el.textContent || '').trim();
            if (t && t.length > 2 && t.length < 60 && !t.includes('$')
                && !t.match(/^\d/) && !skip.has(t.toLowerCase())) {
                names.push(t);
            }
        });
        return [...new Set(names)].slice(0, 10);
    }""")

    await page.close()

    total, pp = _price_parse(raw, adults)
    result.update({
        "raw_prices": raw[:10],
        "airlines": airlines[:8],
        "lowest_total": total,
        "lowest_pp": pp,
        "status": "ok" if raw else "no_prices_found",
    })
    return result


# ── Public async entry points ─────────────────────────────────────────────────

async def run_centrav_search(
    origin: str,
    dest: str,
    depart_date: str,
    adults: int = 2,
    cabins: Optional[list[str]] = None,
) -> dict:
    """
    Full session-aware Centrav B2B search.
    Returns {auth_status, results: {cabin: {...}}, scraped_at}.
    """
    if cabins is None:
        cabins = ["economy", "premium", "business"]

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return {
            "auth_status": "playwright_missing",
            "error": "pip install playwright && playwright install chromium",
            "results": {},
        }

    dt = datetime.strptime(depart_date, "%Y-%m-%d")
    date_mdy = dt.strftime("%m/%d/%Y")

    output: dict = {
        "auth_status": "unknown",
        "origin": origin.upper(),
        "dest": dest.upper(),
        "depart_date": depart_date,
        "adults": adults,
        "scraped_at": datetime.now().isoformat(),
        "results": {},
    }

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled",
                  "--disable-dev-shm-usage"],
        )
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent=_UA,
            locale="en-US",
        )

        session_ok = await _check_session_live(context)
        if not session_ok:
            logger.info("centrav: session expired — attempting auto-login")
            session_ok = await _auto_login(context)

        output["auth_status"] = "authenticated" if session_ok else "session_expired"

        if not session_ok:
            output["error"] = (
                "Centrav session expired and auto-login failed. "
                "Re-authenticate manually: "
                "python3 scripts/centrav_flights.py --centrav-login --headless false"
            )
            await browser.close()
            return output

        for cabin in cabins:
            try:
                cabin_result = await _search_one_cabin(
                    context, origin.upper(), dest.upper(), date_mdy, adults, cabin
                )
                output["results"][cabin] = cabin_result
            except Exception as exc:
                output["results"][cabin] = {"status": "error", "error": str(exc)}

        # Persist fresh cookies
        try:
            fresh = await context.cookies()
            _save_cookies(fresh)
        except Exception:
            pass

        await browser.close()

    return output


async def check_session_only() -> dict:
    """Quick session validity check without running a search."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return {"valid": False, "error": "playwright not installed"}

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True,
                                           args=["--no-sandbox", "--disable-dev-shm-usage"])
        context = await browser.new_context(user_agent=_UA)
        valid = await _check_session_live(context)
        await browser.close()

    cookies = _build_playwright_cookies()
    return {
        "valid": valid,
        "cookies_loaded": len(cookies),
        "session_file_exists": SESSION_FILE.exists(),
        "checked_at": datetime.now().isoformat(),
    }


# ── Route / cabin helpers ─────────────────────────────────────────────────────

def _parse_route_codes(route: str) -> tuple[Optional[str], Optional[str]]:
    """Extract first two IATA codes from a route string like 'RIC → PTY' or 'COS->FLL (via DEN)'."""
    codes = re.findall(r'\b([A-Z]{3})\b', route.upper())
    if len(codes) >= 2:
        return codes[0], codes[1]
    return None, None


def _detect_cabin(watch: dict) -> str:
    """Infer cabin class from watch notes/label. Defaults to economy."""
    text = (watch.get("notes", "") + " " + watch.get("label", "")).lower()
    if "business" in text:
        return "business"
    if "premium" in text:
        return "premium"
    if "first class" in text:
        return "first"
    return "economy"


def _trust_id_days_remaining() -> int:
    """Return days until trustId expires from alt cookies file. -1 if not found."""
    try:
        if ALT_COOKIES.exists():
            for c in json.loads(ALT_COOKIES.read_text()):
                name = c.get("name", "")
                if name.startswith("trustId") and c.get("expires"):
                    exp = datetime.fromtimestamp(float(c["expires"]))
                    return max(0, (exp - datetime.now()).days)
    except Exception:
        pass
    return -1


# ── Flight watch cycle ────────────────────────────────────────────────────────

LAST_CHECK_FILE = THUNDERBIRD / "OpsCenter" / "fare_watches" / "last_check.json"


async def run_centrav_flight_watch_cycle() -> dict:
    """
    Run Centrav B2B price checks for all active flight fare watches.

    For each active watch with watch_type=="flight":
      - Parses origin/dest IATA codes from the route field
      - Runs run_centrav_search() for the detected cabin class
      - Calls check_fare() to record price and trigger threshold alerts

    Returns a summary dict written to OpsCenter/fare_watches/last_check.json.
    """
    # Inline import — thunderbird_fare_watch lives in same core/travel/ dir
    import sys as _sys
    _here = str(Path(__file__).parent)
    if _here not in _sys.path:
        _sys.path.insert(0, _here)
    from thunderbird_fare_watch import check_fare, _load_watches  # noqa: PLC0415

    watches = _load_watches()
    flight_watches = {
        wid: w for wid, w in watches.items()
        if w.get("watch_type") == "flight" and w.get("active", True)
    }

    started_at = datetime.now().isoformat()
    trust_days = _trust_id_days_remaining()
    warnings: list[str] = []
    if 0 <= trust_days <= 14:
        warnings.append(
            f"Centrav trustId expires in {trust_days} day(s). "
            "Re-login before it expires: "
            "python3 scripts/centrav_flights.py --centrav-login --headless false"
        )

    if not flight_watches:
        return {
            "status": "no_flight_watches",
            "started_at": started_at,
            "checked": 0,
            "alerts": [],
            "warnings": warnings,
            "results": {},
        }

    results: dict = {}
    alerts: list[dict] = []
    errors: list[dict] = []

    for watch_id, watch in flight_watches.items():
        route = watch.get("route", "")
        origin, dest = _parse_route_codes(route)

        if not origin or not dest:
            err = {"watch_id": watch_id, "error": f"Cannot parse route: '{route}'"}
            errors.append(err)
            results[watch_id] = {"status": "route_parse_error", **err}
            continue

        travel_date = watch.get("travel_date", "")
        passengers = watch.get("passengers", 2)
        cabin = _detect_cabin(watch)

        logger.info("centrav cycle: %s  %s→%s  %s  %s pax  cabin=%s",
                    watch_id, origin, dest, travel_date, passengers, cabin)

        try:
            search = await run_centrav_search(
                origin=origin,
                dest=dest,
                depart_date=travel_date,
                adults=passengers,
                cabins=[cabin],
            )

            if search.get("auth_status") != "authenticated":
                msg = search.get("error", "Session not authenticated — re-login required")
                errors.append({"watch_id": watch_id, "error": msg})
                results[watch_id] = {"status": "auth_error", "error": msg}
                warnings.append(f"Auth failed on {watch_id}: {msg}")
                break  # All subsequent watches will fail too

            cabin_data = search.get("results", {}).get(cabin, {})
            lowest_pp = cabin_data.get("lowest_pp")

            if lowest_pp is not None:
                fare_check = check_fare(watch_id, lowest_pp)
                results[watch_id] = {
                    "status": "ok",
                    "origin": origin,
                    "dest": dest,
                    "date": travel_date,
                    "cabin": cabin,
                    "passengers": passengers,
                    "lowest_pp": lowest_pp,
                    "fare_check": fare_check,
                }
                if fare_check.get("alert"):
                    alerts.append({
                        "watch_id": watch_id,
                        "label": watch.get("label"),
                        "alert": fare_check["alert"],
                        "price_pp": fare_check.get("price_pp"),
                    })
            else:
                results[watch_id] = {
                    "status": "no_price_found",
                    "origin": origin,
                    "dest": dest,
                    "date": travel_date,
                    "cabin": cabin,
                    "raw": cabin_data,
                }
                errors.append({
                    "watch_id": watch_id,
                    "error": f"No price extracted for {origin}→{dest} {cabin}",
                })

        except Exception as exc:
            logger.error("centrav cycle error %s: %s", watch_id, exc)
            errors.append({"watch_id": watch_id, "error": str(exc)})
            results[watch_id] = {"status": "error", "error": str(exc)}

    completed_at = datetime.now().isoformat()
    ok_count = sum(1 for r in results.values() if r.get("status") == "ok")

    summary = {
        "status": "complete",
        "started_at": started_at,
        "completed_at": completed_at,
        "watches_total": len(flight_watches),
        "watches_checked": ok_count,
        "watches_with_errors": len(errors),
        "alerts": alerts,
        "warnings": warnings,
        "errors": errors,
        "results": results,
    }

    # Persist for dashboard / next session
    try:
        LAST_CHECK_FILE.parent.mkdir(parents=True, exist_ok=True)
        LAST_CHECK_FILE.write_text(json.dumps(summary, indent=2))
    except Exception as exc:
        logger.warning("centrav cycle: could not write last_check.json: %s", exc)

    return summary


# ── MCP registration ──────────────────────────────────────────────────────────

def register_centrav_search_tools(mcp: FastMCP) -> None:

    @mcp.tool(
        name="search_centrav_flights",
        annotations={"title": "Centrav B2B Flight Search", "readOnlyHint": True},
    )
    async def search_centrav_flights(
        origin: str = Field(..., description="IATA origin airport code (e.g. DEN)"),
        destination: str = Field(..., description="IATA destination airport code (e.g. FLL)"),
        depart_date: str = Field(..., description="Departure date YYYY-MM-DD"),
        adults: int = Field(2, description="Number of adult travelers"),
        cabin: str = Field(
            "all",
            description="Cabin class: economy | premium | business | all (default: all)",
        ),
    ) -> str:
        """
        Search Centrav B2B portal for one-way fares.
        Returns B2B net pricing with airline options.
        Requires active Centrav session (check with check_centrav_session first).
        """
        cabin_lower = cabin.lower().strip()
        if cabin_lower == "all":
            cabins = ["economy", "premium", "business"]
        elif cabin_lower in _CABIN_INPUT:
            cabins = [cabin_lower]
        else:
            return json.dumps({"error": f"Unknown cabin: {cabin}. Use economy|premium|business|all"})

        try:
            result = await run_centrav_search(
                origin=origin,
                dest=destination,
                depart_date=depart_date,
                adults=adults,
                cabins=cabins,
            )
        except Exception as exc:
            return json.dumps({"error": str(exc), "type": "centrav_search_error"})

        # Build summary table
        if result.get("auth_status") == "authenticated" and result.get("results"):
            lines = [
                f"Centrav B2B: {origin.upper()} → {destination.upper()} | {depart_date} | {adults} pax",
                f"Auth: {result['auth_status']}",
                "",
                f"{'Cabin':<16} {'Net /pp':>10} {'Net total':>12} {'Airlines'}",
                "─" * 70,
            ]
            for cab, data in result["results"].items():
                pp = f"${data['lowest_pp']:,.2f}" if data.get("lowest_pp") else "n/a"
                tot = f"${data['lowest_total']:,.2f}" if data.get("lowest_total") else "n/a"
                airs = ", ".join(data.get("airlines", [])[:3]) or "—"
                label = _CABIN_TAB.get(cab, cab)
                lines.append(f"{label:<16} {pp:>10} {tot:>12}  {airs}")
            result["_summary"] = "\n".join(lines)

        return json.dumps(result, indent=2)

    @mcp.tool(
        name="check_centrav_session",
        annotations={"title": "Check Centrav B2B Session", "readOnlyHint": True},
    )
    async def check_centrav_session() -> str:
        """
        Verify whether saved Centrav cookies produce an authenticated session.
        Returns {valid, cookies_loaded, session_file_exists, checked_at}.
        If not valid, run: python3 scripts/centrav_flights.py --centrav-login --headless false
        """
        try:
            result = await check_session_only()
        except Exception as exc:
            result = {"valid": False, "error": str(exc)}
        return json.dumps(result, indent=2)

    @mcp.tool(
        name="centrav_run_flight_watches",
        annotations={"title": "Centrav Flight Watch Cycle", "readOnlyHint": False},
    )
    async def centrav_run_flight_watches() -> str:
        """
        Run Centrav B2B price checks for all active flight fare watches.
        Reads fare_watches.json, fetches live prices from Centrav B2B for every
        active flight watch, records history, and fires threshold alerts.
        Writes summary to OpsCenter/fare_watches/last_check.json.
        Returns JSON summary with prices, alerts, and errors.
        """
        try:
            result = await run_centrav_flight_watch_cycle()
        except Exception as exc:
            result = {"status": "error", "error": str(exc)}
        return json.dumps(result, indent=2)

    logger.info(
        "centrav: MCP tools registered — search_centrav_flights, "
        "check_centrav_session, centrav_run_flight_watches"
    )


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if "--watch-cycle" in sys.argv:
        result = asyncio.run(run_centrav_flight_watch_cycle())
        print(json.dumps(result, indent=2))
    elif "--check-session" in sys.argv:
        result = asyncio.run(check_session_only())
        print(json.dumps(result, indent=2))
    else:
        print(
            "Usage: python3 thunderbird_centrav_search.py "
            "[--watch-cycle | --check-session]"
        )
        sys.exit(1)
