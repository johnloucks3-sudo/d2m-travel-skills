#!/usr/bin/env python3
"""
centrav-flights — Centrav B2B Flight Search CLI
================================================
Dreams2Memories Travel, LLC · A2 Intelligence Tool

Usage:
    centrav-flights --origin MXP --dest BCN --date 2026-06-01 --travelers 2
    centrav-flights --origin JFK --dest LHR --date 2026-06-15 --travelers 2 --cabin business
    centrav-flights --origin JFK --dest LHR --date 2026-06-15 --travelers 2 --headless false

Options:
    --origin        IATA origin airport code
    --dest          IATA destination airport code
    --date          Departure date YYYY-MM-DD
    --travelers     Number of adult travelers (default: 2)
    --cabin         Cabin class: economy | premium | business (default: all)
    --headless      Run browser headless true|false (default: true)
    --centrav-login Run interactive Centrav CAPTCHA login flow
    --output        Output file path (default: auto-generated timestamp)

Auth:
    Session cookies: ~/Thunderbird/core/travel/data/centrav_session.json
    Credentials: ~/Thunderbird/centrav_credentials.json
    Re-auth: centrav-flights --centrav-login --headless false
"""

import asyncio
import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    from playwright.async_api import async_playwright, Page, BrowserContext
except ImportError:
    print("ERROR: playwright not installed. Run: pip install playwright && playwright install chromium")
    sys.exit(1)

THUNDERBIRD = Path.home() / "Thunderbird"
CREDS_PATH = THUNDERBIRD / "centrav_credentials.json"
SESSION_FILE = THUNDERBIRD / "core" / "travel" / "data" / "centrav_session.json"
DATA_DIR = THUNDERBIRD / "core" / "travel" / "data"
OUTPUT_DIR = THUNDERBIRD / "output"
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

if CREDS_PATH.exists():
    _creds = json.loads(CREDS_PATH.read_text())
    CENTRAV_EMAIL = _creds.get("email", "johnloucks3@gmail.com")
    CENTRAV_PASS = _creds.get("password", "")
    _raw_cookies = _creds.get("cookies", {})
    CENTRAV_COOKIES_DICT = _raw_cookies
else:
    CENTRAV_EMAIL = "johnloucks3@gmail.com"
    CENTRAV_PASS = ""
    CENTRAV_COOKIES_DICT = {}


def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def log(msg: str):
    print(f"[{_ts()}] {msg}", flush=True)


def _parse_lowest(prices: list, lo: float = 50, hi: float = 20_000) -> float | None:
    lowest = None
    for p in prices:
        try:
            raw = str(p).replace("$", "").replace(",", "").strip()
            val = float(re.sub(r'[^\d.]', '', raw))
            if lo < val < hi:
                if lowest is None or val < lowest:
                    lowest = val
        except (ValueError, TypeError):
            continue
    return lowest


# ── Session management ────────────────────────────────────────────────────────

def _build_playwright_cookies() -> list[dict]:
    """Build playwright cookie list from all available saved cookies."""
    cookies = []

    # Try session file first (most recent)
    if SESSION_FILE.exists():
        try:
            sess = json.loads(SESSION_FILE.read_text())
            if isinstance(sess, list):
                for c in sess:
                    # Ensure mandatory fields
                    cookie = {
                        "name": c.get("name", ""),
                        "value": c.get("value", ""),
                        "domain": c.get("domain", "www.centrav.com"),
                        "path": c.get("path", "/"),
                    }
                    if cookie["name"]:
                        cookies.append(cookie)
        except Exception:
            pass

    # Supplement with credentials file cookies (may have trustId which is critical)
    creds_session_names = {c["name"] for c in cookies}
    for name, value in CENTRAV_COOKIES_DICT.items():
        if name not in creds_session_names:
            cookies.append({
                "name": name,
                "value": value,
                "domain": ".centrav.com" if name.startswith("_g") else "www.centrav.com",
                "path": "/",
            })

    return cookies


async def _check_session(context) -> bool:
    """Return True if saved cookies produce an authenticated Centrav session."""
    cookies = _build_playwright_cookies()
    if not cookies:
        log("  Centrav — no saved cookies found")
        return False

    page = await context.new_page()
    try:
        await context.add_cookies(cookies)
        await page.goto("https://www.centrav.com/", wait_until="domcontentloaded", timeout=25_000)
        await page.wait_for_timeout(2_500)

        # Check for authenticated state — logout button or user menu
        logout = await page.query_selector("#LogoutButton")
        user_menu = await page.query_selector("[class*='user-menu'], [class*='account-menu'], [class*='UserMenu']")
        search_form = await page.query_selector("#FareFlyingFrom, #FareFlyingTo")

        # If we see the search form without a redirect to login, we're authenticated
        current_url = page.url
        if logout or user_menu:
            log("  Centrav — session valid (logout button found) ✓")
            await page.close()
            return True
        if search_form and "login" not in current_url.lower():
            log("  Centrav — session valid (search form accessible) ✓")
            await page.close()
            return True
        if "login" in current_url.lower():
            log("  Centrav — session expired (redirected to login)")
            await page.close()
            return False

        # Ambiguous — take screenshot and check page text
        page_text = await page.inner_text("body")
        if "logout" in page_text.lower() or "my account" in page_text.lower():
            log("  Centrav — session valid (text check) ✓")
            await page.close()
            return True

        log(f"  Centrav — session check ambiguous, URL: {current_url}")
        await page.close()
        return False

    except Exception as e:
        log(f"  Centrav — session check error: {e}")
        try:
            await page.close()
        except Exception:
            pass
        return False


async def _interactive_login(context, headless: bool) -> bool:
    """Launch visible browser for CAPTCHA-gated Centrav login."""
    if headless:
        log("  Centrav — CAPTCHA required. Run: centrav-flights --centrav-login --headless false")
        return False

    log("  Centrav — launching visible browser for CAPTCHA solve...")
    page = await context.new_page()
    try:
        await page.goto("https://www.centrav.com/login", wait_until="domcontentloaded", timeout=30_000)
        await page.wait_for_timeout(1_500)
        await page.fill("#FormEmail", CENTRAV_EMAIL, timeout=5_000)
        await page.fill("#FormPassword", CENTRAV_PASS, timeout=5_000)
        log("  Centrav — credentials pre-filled.")
        log("  Centrav — SOLVE the CAPTCHA in the browser, then click Login.")
        log("  Centrav — waiting up to 120s...")
    except Exception as e:
        log(f"  Centrav — pre-fill failed: {e}. Fill credentials manually.")

    for _ in range(60):
        await page.wait_for_timeout(2_000)
        if "login" not in page.url.lower():
            break
    else:
        log("  Centrav — login timeout.")
        await page.close()
        return False

    log(f"  Centrav — login success: {page.url}")
    cookies = await context.cookies()
    SESSION_FILE.write_text(json.dumps(cookies, indent=2))
    log(f"  Centrav — session saved → {SESSION_FILE}")
    await page.close()
    return True


# ── Centrav search ────────────────────────────────────────────────────────────

async def search_centrav(
    context,
    origin: str,
    dest: str,
    depart_date: str,
    adults: int,
    cabin: str,
) -> dict:
    """Search Centrav B2B portal for one-way fares."""
    cabin_val = {"economy": "ECONOMY", "premium": "PREMIUM_ECONOMY", "business": "BUSINESS"}.get(cabin, "ECONOMY")
    cabin_tab = {"economy": "Economy", "premium": "Premium Economy", "business": "Business"}.get(cabin, "Economy")
    dt = datetime.strptime(depart_date, "%Y-%m-%d")
    date_str = dt.strftime("%m/%d/%Y")

    page = await context.new_page()
    screenshot_path = DATA_DIR / f"centrav_{cabin}_{origin}_{dest}_{depart_date}.png"

    try:
        await page.goto("https://www.centrav.com/", wait_until="domcontentloaded", timeout=30_000)
        await page.wait_for_timeout(2_000)
        log(f"  Centrav [{cabin}] — homepage loaded: {page.url}")

        # Set hidden inputs
        await page.evaluate(f"""() => {{
            const t = document.getElementById('FareTripTypeInput');
            if (t) t.value = 'OneWay';
            const c = document.getElementById('CabinClassInput');
            if (c) c.value = '{cabin_val}';
        }}""")

        # Click UI tabs
        try:
            await page.click("text='One Way'", timeout=3_000)
        except Exception:
            pass
        await page.wait_for_timeout(200)
        try:
            await page.click(f"text='{cabin_tab}'", timeout=3_000)
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
        log(f"  Centrav [{cabin}] — submitting search {origin}→{dest} {date_str}")
        await page.click("button:has-text('SEARCH FOR FARES')")
        await page.wait_for_timeout(10_000)
        await page.screenshot(path=str(screenshot_path))

    except Exception as e:
        log(f"  Centrav [{cabin}] form error: {e}")
        try:
            await page.screenshot(path=str(screenshot_path))
        except Exception:
            pass

    # Extract prices
    raw_prices = await page.evaluate("""() => {
        const prices = [];
        const selectors = [
            '[class*="price"]', '[class*="fare"]', '[class*="amount"]',
            '[class*="cost"]', '[class*="total"]', 'td', 'span',
        ];
        for (const sel of selectors) {
            document.querySelectorAll(sel).forEach(el => {
                const t = (el.innerText || el.textContent || '').trim();
                const m = t.match(/^\\$[\\d,]+$/);
                if (m) prices.push(m[0]);
            });
            if (prices.length > 3) break;
        }
        return [...new Set(prices)].slice(0, 20);
    }""")

    airlines = await page.evaluate("""() => {
        const skip = new Set(['only','nonstop','stops','stop','filters','all','any',
            'sort','cabin','class','economy','premium','business','first']);
        const names = [];
        document.querySelectorAll('[class*="airline"],[class*="carrier"]').forEach(el => {
            const t = (el.innerText || el.textContent || '').trim();
            if (t && t.length > 2 && t.length < 60 && !t.includes('$')
                && !t.match(/^\\d/) && !skip.has(t.toLowerCase())) {
                names.push(t);
            }
        });
        return [...new Set(names)].slice(0, 10);
    }""")

    if not raw_prices:
        page_text = await page.inner_text("body")
        matches = re.findall(r'\$[\d,]+', page_text)
        raw_prices = list(dict.fromkeys(
            m for m in matches if 50 < int(m.replace('$', '').replace(',', '')) < 20_000
        ))[:15]

    lowest = _parse_lowest(raw_prices)
    current_url = page.url
    await page.close()

    return {
        "source": "centrav_b2b",
        "cabin": cabin,
        "origin": origin,
        "dest": dest,
        "url": current_url,
        "adults": adults,
        "depart_date": depart_date,
        "raw_prices": raw_prices[:10],
        "lowest_price_pp": round(lowest / adults, 2) if lowest else None,
        "total_lowest": lowest,
        "airlines_found": airlines[:8],
        "screenshot": str(screenshot_path),
        "status": "ok" if raw_prices else "no_prices_found",
    }


# ── Kayak baseline ────────────────────────────────────────────────────────────

async def search_kayak(
    context,
    origin: str,
    dest: str,
    depart_date: str,
    adults: int,
    cabin: str,
) -> dict:
    """Scrape Kayak as pricing baseline."""
    cabin_kk = {"economy": "e", "premium": "pe", "business": "b"}.get(cabin, "e")
    url = (
        f"https://www.kayak.com/flights/{origin}-{dest}/{depart_date}/{adults}adults"
        f"?sort=price_a&fs=cabin={cabin_kk}"
    )
    log(f"  Kayak [{cabin}] → {origin}→{dest}")

    page = await context.new_page()
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=50_000)

        for sel in [
            "#onetrust-accept-btn-handler",
            "button[data-testid='accept-cookies']",
            "button:has-text('Accept all')",
            "button:has-text('I Accept')",
        ]:
            try:
                await page.click(sel, timeout=4_000)
                await page.wait_for_timeout(500)
                break
            except Exception:
                pass

        try:
            await page.wait_for_selector(
                "[class*='price-text'], [data-resultid], [class*='resultInner']",
                timeout=35_000,
            )
        except Exception:
            await page.wait_for_timeout(12_000)

        await page.wait_for_timeout(2_000)

        # Close modals
        for close_sel in ["button.close", "button[aria-label='Close']"]:
            try:
                await page.click(close_sel, timeout=1_500)
                await page.wait_for_timeout(400)
            except Exception:
                pass

        raw_prices = await page.evaluate("""() => {
            const prices = [];
            const cardSelectors = ['[data-resultid]', '[class*="resultInner"]', '[class*="above-the-fold"]'];
            let cards = [];
            for (const sel of cardSelectors) {
                cards = Array.from(document.querySelectorAll(sel));
                if (cards.length > 0) break;
            }
            const scope = cards.length > 0 ? cards : [document.body];
            for (const card of scope.slice(0, 10)) {
                card.querySelectorAll('[class*="price-text"], [class*="price"]').forEach(el => {
                    const t = (el.innerText || el.textContent || '').trim();
                    if (/^\\$[\\d,]+$/.test(t)) prices.push(t);
                });
            }
            if (prices.length === 0) {
                document.querySelectorAll('[class*="price-text"]').forEach(el => {
                    const t = (el.innerText || el.textContent || '').trim();
                    if (/^\\$[\\d,]+$/.test(t)) prices.push(t);
                });
            }
            return [...new Set(prices)].slice(0, 20);
        }""")

        airlines = await page.evaluate("""() => {
            const names = [];
            document.querySelectorAll('[class*="carrier-name"],[class*="airline-name"]').forEach(el => {
                const t = (el.innerText || el.textContent || '').trim();
                if (t && t.length < 60 && !t.includes('$')) names.push(t);
            });
            return [...new Set(names)].slice(0, 10);
        }""")

        if not raw_prices:
            page_text = await page.inner_text("body")
            matches = re.findall(r'\$[\d,]+', page_text)
            raw_prices = list(dict.fromkeys(matches))[:15]

        lowest = _parse_lowest(raw_prices, lo=50, hi=15_000)

        # Sanity gate: cabin filter leaks — if premium/business < economy*0.85, flag it
        screenshot_path = DATA_DIR / f"kayak_{cabin}_{origin}_{dest}_{depart_date}.png"
        await page.screenshot(path=str(screenshot_path), full_page=False)
        await page.close()

        return {
            "source": "kayak",
            "cabin": cabin,
            "origin": origin,
            "dest": dest,
            "url": url,
            "adults": adults,
            "depart_date": depart_date,
            "raw_prices": raw_prices[:10],
            "lowest_price_pp": round(lowest / adults, 2) if lowest else None,
            "total_lowest": lowest,
            "airlines_found": airlines[:8],
            "screenshot": str(screenshot_path),
            "status": "ok" if raw_prices else "no_prices_found",
        }
    except Exception as e:
        log(f"  Kayak [{cabin}] ERROR: {e}")
        try:
            await page.close()
        except Exception:
            pass
        return {"source": "kayak", "cabin": cabin, "origin": origin, "dest": dest,
                "status": "error", "error": str(e)}


# ── Main run ──────────────────────────────────────────────────────────────────

async def run_search(
    origin: str,
    dest: str,
    depart_date: str,
    travelers: int,
    cabin_filter: str | None,
    headless: bool,
) -> dict:
    """Run Centrav + Kayak search for one route."""
    cabins = ["economy", "premium", "business"] if not cabin_filter else [cabin_filter]
    log(f"\n{'═' * 60}")
    log(f"ROUTE: {origin} → {dest} | {depart_date} | {travelers} adults | {', '.join(cabins)}")
    log(f"{'═' * 60}")

    result = {
        "route": f"{origin}-{dest}",
        "origin": origin,
        "dest": dest,
        "depart_date": depart_date,
        "travelers": travelers,
        "scraped_at": datetime.now().isoformat(),
        "centrav": {},
        "kayak": {},
        "centrav_auth": "unknown",
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled",
                  "--disable-dev-shm-usage"],
        )
        context: BrowserContext = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="en-US",
        )

        # Centrav auth check
        log("\n── Centrav B2B Auth ───────────────────────────────────────")
        session_ok = await _check_session(context)

        if not session_ok:
            login_ok = await _interactive_login(context, headless=headless)
            session_ok = login_ok

        result["centrav_auth"] = "authenticated" if session_ok else "failed"

        # Centrav searches
        if session_ok:
            log(f"\n── Centrav B2B Search: {origin} → {dest} ──────────────────")
            for cabin in cabins:
                result["centrav"][cabin] = await search_centrav(
                    context, origin, dest, depart_date, travelers, cabin
                )
        else:
            log("  Centrav — auth failed, skipping B2B search")
            for cabin in cabins:
                result["centrav"][cabin] = {
                    "source": "centrav_b2b", "cabin": cabin,
                    "status": "auth_failed — run: centrav-flights --centrav-login --headless false",
                    "lowest_price_pp": None, "total_lowest": None,
                }

        # Kayak baseline
        log(f"\n── Kayak Baseline: {origin} → {dest} ──────────────────────")
        for cabin in cabins:
            result["kayak"][cabin] = await search_kayak(
                context, origin, dest, depart_date, travelers, cabin
            )
            await asyncio.sleep(1)

        await browser.close()

    return result


def _pct_diff(centrav_pp: float | None, kayak_pp: float | None) -> str:
    if centrav_pp is None or kayak_pp is None or kayak_pp == 0:
        return "n/a"
    diff = ((kayak_pp - centrav_pp) / kayak_pp) * 100
    sign = "+" if diff > 0 else ""
    return f"{sign}{diff:.1f}%"


def _format_result(result: dict) -> str:
    """Format a single route result as a readable text block."""
    route = result.get("route", "?")
    date = result.get("depart_date", "?")
    travelers = result.get("travelers", 2)
    auth = result.get("centrav_auth", "unknown")

    lines = []
    lines.append(f"\nROUTE: {route} | {date} | {travelers} pax | Centrav auth: {auth}")
    lines.append("─" * 70)

    header = f"{'Cabin':<16} {'Centrav /pp':>12} {'Kayak /pp':>12} {'Savings':>10} {'Advantage':>12}"
    lines.append(header)
    lines.append("─" * 70)

    all_savings = []
    cabin_labels = {"economy": "Economy", "premium": "Prem Economy", "business": "Business"}

    for cabin in ["economy", "premium", "business"]:
        cv_data = result.get("centrav", {}).get(cabin, {})
        kk_data = result.get("kayak", {}).get(cabin, {})

        cv_pp = cv_data.get("lowest_price_pp")
        kk_pp = kk_data.get("lowest_price_pp")

        cv_str = f"${cv_pp:,.2f}" if cv_pp else "n/a"
        kk_str = f"${kk_pp:,.2f}" if kk_pp else "n/a"

        pct = _pct_diff(cv_pp, kk_pp)
        try:
            pct_val = float(pct.rstrip('%')) if pct != "n/a" else None
        except ValueError:
            pct_val = None

        if pct_val is not None and pct_val > 0:
            advantage = "✓ Centrav"
            all_savings.append(pct_val)
        elif pct_val is not None and pct_val < 0:
            advantage = "✗ Kayak"
        else:
            advantage = "—"

        lines.append(
            f"{cabin_labels.get(cabin, cabin):<16} {cv_str:>12} {kk_str:>12} {pct:>10} {advantage:>12}"
        )

        # Airlines
        cv_airlines = cv_data.get("airlines_found", [])
        kk_airlines = kk_data.get("airlines_found", [])
        if kk_airlines:
            lines.append(f"  Airlines ({cabin}): {', '.join(kk_airlines[:4])}")

    avg_saving = sum(all_savings) / len(all_savings) if all_savings else None
    if avg_saving is not None:
        lines.append(f"\n  Avg Centrav advantage on this route: {avg_saving:.1f}%")

    return "\n".join(lines)


async def centrav_login_flow(headless: bool):
    """Standalone interactive login to save session."""
    log("=== Centrav B2B Login Flow ===")
    log(f"Email: {CENTRAV_EMAIL}")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        ok = await _interactive_login(context, headless=headless)
        await browser.close()

    if ok:
        log(f"✅ Session saved → {SESSION_FILE}")
        log("Run centrav-flights normally now — cookies will be used automatically.")
    else:
        log("❌ Login failed. Try again with: centrav-flights --centrav-login --headless false")


# ── CLI entry ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Centrav B2B Flight Search CLI — D2M Intelligence Tool"
    )
    parser.add_argument("--origin", default="MXP", help="IATA origin code")
    parser.add_argument("--dest", default="BCN", help="IATA destination code")
    parser.add_argument("--date", default="2026-06-01", help="Departure date YYYY-MM-DD")
    parser.add_argument("--travelers", type=int, default=2, help="Number of adults")
    parser.add_argument("--cabin", choices=["economy", "premium", "business"],
                        default=None, help="Cabin class (default: all)")
    parser.add_argument("--headless", type=lambda x: x.lower() != "false",
                        default=True, help="Headless browser (default: true)")
    parser.add_argument("--centrav-login", action="store_true",
                        help="Run interactive Centrav login flow")
    parser.add_argument("--output", default=None, help="Output file path")

    args = parser.parse_args()

    if args.centrav_login:
        asyncio.run(centrav_login_flow(headless=args.headless))
        return

    result = asyncio.run(run_search(
        origin=args.origin.upper(),
        dest=args.dest.upper(),
        depart_date=args.date,
        travelers=args.travelers,
        cabin_filter=args.cabin,
        headless=args.headless,
    ))

    print(_format_result(result))

    # Save JSON
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_json = OUTPUT_DIR / f"centrav_{args.origin}_{args.dest}_{args.date}_{ts}.json"
    out_json.write_text(json.dumps(result, indent=2))
    log(f"\nJSON saved → {out_json}")


if __name__ == "__main__":
    main()
