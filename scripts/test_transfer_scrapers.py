"""
Transfer price scraper — Playwright multi-source
Primary: Kiwitaxi (confirmed accessible, static route URLs, all vehicle classes)
Secondary: Welcome Pickups (form-fill, cruise port specialist)

Routes: airport→hotel, hotel→cruise port, port→airport, ship→airport

Usage:
  python3 scripts/test_transfer_scrapers.py --route LIS-LISBON
  python3 scripts/test_transfer_scrapers.py --route LIS-LISBON --date 2026-09-05 --pax 2
  python3 scripts/test_transfer_scrapers.py --from "LIS Airport" --to "Lisbon city" --date 2026-09-05
  python3 scripts/test_transfer_scrapers.py --list-routes

Output JSON: core/travel/data/transfer_test_{ROUTE}_{DATE}.json
Screenshots: core/travel/data/transfer_{source}_{route}_{date}.png

Sources:
  kiwitaxi        — confirmed accessible, static URLs, all vehicle classes
  welcomepickups  — form-fill, cruise port coverage

Bot-blocked (do not use):
  viator          — transfers also bot-blocked
  klook           — 403
"""

import asyncio
import argparse
import json
import re
from pathlib import Path
from datetime import datetime, date

OUTPUT_DIR = Path("/home/john/Thunderbird/core/travel/data")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def fmt_price(s: str) -> float | None:
    if not s:
        return None
    cleaned = re.sub(r"[^\d.]", "", s.replace(",", ""))
    try:
        return float(cleaned)
    except ValueError:
        return None


# ─────────────────────────────────────────────────────────────
# KIWITAXI — pre-mapped D2M routes
# Pattern: kiwitaxi.com/en/{country}/{from-slug}-{to-slug}
# Find new routes: search on kiwitaxi.com and copy the result URL
# ─────────────────────────────────────────────────────────────
KIWITAXI_ROUTES = {
    # Portugal — Lisbon
    "LIS-LISBON":       ("Lisbon Airport → Lisbon city",        "https://kiwitaxi.com/en/portugal/humberto-delgado-airport-lisbon-oriente-train-station"),
    "LISBON-LIS":       ("Lisbon city → Lisbon Airport",        "https://kiwitaxi.com/en/portugal/lisbon-oriente-train-station-humberto-delgado-airport"),
    "LIS-SINTRA":       ("Lisbon Airport → Sintra",             "https://kiwitaxi.com/en/portugal/humberto-delgado-airport-sintra"),
    # Spain — Barcelona
    "BCN-BCN_PORT":     ("Barcelona Airport → Barcelona Port",   "https://kiwitaxi.com/en/spain/barcelona-airport-barcelona-cruise-terminal"),
    "BCN_PORT-BCN":     ("Barcelona Port → Barcelona Airport",   "https://kiwitaxi.com/en/spain/barcelona-cruise-terminal-barcelona-airport"),
    "BCN-CITY":         ("Barcelona Airport → Barcelona city",   "https://kiwitaxi.com/en/spain/barcelona-airport-barcelona-city-centre"),
    # Italy — Rome / Civitavecchia
    "FCO-ROME":         ("Rome Airport (FCO) → Rome city",       "https://kiwitaxi.com/en/italy/fiumicino-airport-rome-city-centre"),
    "FCO-CIVITA":       ("Rome Airport → Civitavecchia Port",    "https://kiwitaxi.com/en/italy/fiumicino-airport-civitavecchia"),
    "CIVITA-FCO":       ("Civitavecchia Port → Rome Airport",    "https://kiwitaxi.com/en/italy/civitavecchia-fiumicino-airport"),
    "CIVITA-ROME":      ("Civitavecchia Port → Rome city",       "https://kiwitaxi.com/en/italy/civitavecchia-rome-city-centre"),
    # Greece — Athens / Piraeus
    "ATH-PIRAEUS":      ("Athens Airport → Piraeus Port",        "https://kiwitaxi.com/en/greece/athens-airport-piraeus-port"),
    "PIRAEUS-ATH":      ("Piraeus Port → Athens Airport",        "https://kiwitaxi.com/en/greece/piraeus-port-athens-airport"),
    "ATH-ATHENS":       ("Athens Airport → Athens city",         "https://kiwitaxi.com/en/greece/athens-airport-athens-city-centre"),
    # France — Nice
    "NCE-NICE":         ("Nice Airport → Nice city",             "https://kiwitaxi.com/en/france/nice-airport-nice-city-centre"),
    "NCE-CANNES":       ("Nice Airport → Cannes",                "https://kiwitaxi.com/en/france/nice-airport-cannes"),
    # Norway — Bergen
    "BGO-BERGEN":       ("Bergen Airport → Bergen city",         "https://kiwitaxi.com/en/norway/bergen-airport-bergen-city-centre"),
    # Iceland — Reykjavik
    "KEF-REYKJAVIK":    ("Keflavik Airport → Reykjavik",         "https://kiwitaxi.com/en/iceland/keflavik-international-airport-reykjavik-city-centre"),
    # Caribbean — Port of Spain
    "POS-PORT":         ("POS Airport → Port of Spain",          "https://kiwitaxi.com/en/trinidad-and-tobago/piarco-international-airport-port-of-spain"),
    # Hawaii — Honolulu
    "HNL-WAIKIKI":      ("Honolulu Airport → Waikiki",           "https://kiwitaxi.com/en/united-states/honolulu-international-airport-waikiki"),
    # Mexico — Cancun
    "CUN-CANCUN":       ("Cancun Airport → Cancun Hotel Zone",   "https://kiwitaxi.com/en/mexico/cancun-airport-cancun-hotel-zone"),
}


def list_routes():
    print("\nPre-mapped transfer routes (--route KEY):\n")
    print(f"  {'Key':<20} {'Description'}")
    print(f"  {'-'*20} {'-'*45}")
    for key, (desc, url) in KIWITAXI_ROUTES.items():
        print(f"  {key:<20} {desc}")
    print("\nFor routes not listed, use --from and --to with form-fill mode.")


# ─────────────────────────────────────────────
# Kiwitaxi scraper
# ─────────────────────────────────────────────
async def scrape_kiwitaxi_url(page, route_key: str, desc: str, url: str, pax: int, date_str: str) -> dict:
    """Navigate directly to a Kiwitaxi route URL and extract all vehicle classes."""
    result = {
        "source": "kiwitaxi",
        "route": route_key,
        "description": desc,
        "url": url,
        "pax": pax,
        "date": date_str,
        "scraped_at": datetime.now().isoformat(),
        "duration_min": None,
        "transfers": [],
        "screenshot": None,
        "status": "unknown",
        "notes": "Prices are per vehicle (not per person). Fixed price regardless of date.",
    }

    log(f"  Kiwitaxi → {desc}")
    log(f"    URL: {url}")

    try:
        await page.goto(url + "#transfers", timeout=30000, wait_until="domcontentloaded")
        await asyncio.sleep(4)

        # Check for bot wall
        body_text = ""
        try:
            body_text = (await page.locator("body").inner_text()).lower()
        except Exception:
            pass
        if "access denied" in body_text or "403" in body_text or "blocked" in body_text:
            result["status"] = "bot_blocked"
            return result

        # Check for 404
        if "page not found" in body_text or "error 404" in body_text:
            result["status"] = "route_not_found"
            result["notes"] = f"Route URL 404 — update KIWITAXI_ROUTES with correct slug"
            return result

        screenshot_path = OUTPUT_DIR / f"transfer_kiwitaxi_{route_key.lower()}_{date_str}.png"
        await page.screenshot(path=str(screenshot_path))
        result["screenshot"] = str(screenshot_path)

        # Extract duration from route info
        try:
            dur_text = await page.locator("[class*='time']").first.inner_text()
            m = re.search(r"(\d+)\s*min", dur_text)
            if m:
                result["duration_min"] = int(m.group(1))
        except Exception:
            pass

        # Extract vehicle cards using JS — deduplicate by name+price
        cards = await page.evaluate("""
            () => {
                const results = [];
                const seen = new Set();
                const cards = document.querySelectorAll('.car-class-card');
                for (const card of cards) {
                    const text = card.innerText || '';
                    const lines = text.split('\\n').map(l => l.trim()).filter(l => l);
                    if (lines.length < 2) continue;

                    // Vehicle name: skip "Best Choice" badge line
                    let nameIdx = 0;
                    if (lines[0] === 'Best Choice') nameIdx = 1;
                    const name = lines[nameIdx];
                    if (!name || name.length > 40 || name === 'Choose a Car class') continue;

                    // Price
                    const priceMatch = text.match(/\\$(\\d+)/);
                    const price = priceMatch ? parseInt(priceMatch[1]) : null;
                    if (!price) continue;

                    const key = name + ':' + price;
                    if (seen.has(key)) continue;
                    seen.add(key);

                    // Pax capacity — numbers in the text (appears as standalone lines like "4", "7")
                    const numLines = lines.slice(nameIdx+1).filter(l => /^\\d+$/.test(l));
                    const pax_cap = numLines[0] ? parseInt(numLines[0]) : null;
                    const bags_cap = numLines[1] ? parseInt(numLines[1]) : null;

                    // Vehicle examples
                    const examples = lines.find(l => l.includes(',') && (l.includes('Toyota') || l.includes('Mercedes') || l.includes('BMW') || l.includes('Ford') || l.includes('Hyundai') || l.includes('Honda') || l.includes('Audi') || l.includes('VW') || l.includes('Volkswagen') || l.includes('Lexus')));

                    // Badge
                    const badge = lines[0] === 'Best Choice' ? 'Best Choice' : null;

                    results.push({
                        vehicle_class: name,
                        price_usd: price,
                        pax_capacity: pax_cap,
                        bags_capacity: bags_cap,
                        vehicle_examples: examples || null,
                        badge: badge,
                    });
                }
                return results;
            }
        """)

        result["transfers"] = sorted(cards, key=lambda x: x.get("price_usd") or 0)
        result["status"] = "ok" if cards else "no_results"
        log(f"    Extracted {len(cards)} vehicle classes")

    except Exception as e:
        result["status"] = "error"
        result["notes"] = str(e)
        log(f"    ERROR: {e}")

    return result


async def scrape_kiwitaxi_form(page, from_loc: str, to_loc: str, pax: int, date_str: str) -> dict:
    """Form-fill Kiwitaxi for routes not in the pre-map."""
    result = {
        "source": "kiwitaxi",
        "route": f"{from_loc}→{to_loc}",
        "description": f"{from_loc} → {to_loc}",
        "url": "https://kiwitaxi.com/",
        "pax": pax,
        "date": date_str,
        "scraped_at": datetime.now().isoformat(),
        "duration_min": None,
        "transfers": [],
        "screenshot": None,
        "status": "unknown",
        "notes": "Form-fill mode (route not in pre-map)",
    }

    log(f"  Kiwitaxi form-fill: {from_loc} → {to_loc}")

    try:
        await page.goto("https://kiwitaxi.com/", timeout=30000, wait_until="domcontentloaded")
        await asyncio.sleep(2)

        # From
        await page.locator("input.autocomplete-input").first.click()
        await page.locator("input.autocomplete-input").first.fill(from_loc)
        await asyncio.sleep(2)
        try:
            await page.locator("[class*='suggestion-item'], [class*='autocomplete'] div[class*='item']").first.click()
        except Exception:
            await page.get_by_text(from_loc[:10], exact=False).first.click()
        await asyncio.sleep(1)

        # To
        await page.locator("input.autocomplete-input").nth(1).click()
        await page.locator("input.autocomplete-input").nth(1).fill(to_loc)
        await asyncio.sleep(2)
        try:
            await page.locator("[class*='suggestion-item'], [class*='autocomplete'] div[class*='item']").first.click()
        except Exception:
            await page.get_by_text(to_loc[:10], exact=False).first.click()
        await asyncio.sleep(1)

        # Date — navigate calendar to target month
        await page.locator("input.datepicker-input").first.click()
        await asyncio.sleep(1)

        try:
            target = datetime.strptime(date_str, "%Y-%m-%d").date()
            today = date.today()
            months_ahead = (target.year - today.year) * 12 + (target.month - today.month)
            for _ in range(months_ahead):
                await page.evaluate("""
                    () => {
                        const icons = document.querySelectorAll('[class*="calendar-dropdown-header-icon"]:not([class*="disabled"])');
                        if (icons.length > 0) icons[icons.length-1].click();
                    }
                """)
                await asyncio.sleep(0.3)

            # Click target day
            day_str = str(target.day)
            await page.locator(f".calendar-day-table-day:not(.disabled)").get_by_text(day_str, exact=True).first.click()
            await asyncio.sleep(1)
        except Exception as e:
            log(f"    Date set error: {e}")

        # Submit
        await page.locator("button.app-button.primary").first.click()
        await asyncio.sleep(8)

        screenshot_path = OUTPUT_DIR / f"transfer_kiwitaxi_custom_{date_str}.png"
        await page.screenshot(path=str(screenshot_path))
        result["screenshot"] = str(screenshot_path)
        result["url"] = page.url

        # Check for 404/error
        if "page not found" in (await page.title()).lower() or page.url == "https://kiwitaxi.com/":
            result["status"] = "route_not_found"
            result["notes"] = "Form submit didn't navigate to results — try adding this route to KIWITAXI_ROUTES"
            return result

        # Extract (same as URL-based)
        try:
            dur_text = await page.locator("[class*='time']").first.inner_text()
            m = re.search(r"(\d+)\s*min", dur_text)
            if m:
                result["duration_min"] = int(m.group(1))
        except Exception:
            pass

        cards = await page.evaluate("""
            () => {
                const results = [];
                const seen = new Set();
                const cards = document.querySelectorAll('.car-class-card');
                for (const card of cards) {
                    const text = card.innerText || '';
                    const lines = text.split('\\n').map(l => l.trim()).filter(l => l);
                    if (lines.length < 2) continue;
                    let nameIdx = 0;
                    if (lines[0] === 'Best Choice') nameIdx = 1;
                    const name = lines[nameIdx];
                    if (!name || name.length > 40 || name === 'Choose a Car class') continue;
                    const priceMatch = text.match(/\\$(\\d+)/);
                    const price = priceMatch ? parseInt(priceMatch[1]) : null;
                    if (!price) continue;
                    const key = name + ':' + price;
                    if (seen.has(key)) continue;
                    seen.add(key);
                    const numLines = lines.slice(nameIdx+1).filter(l => /^\\d+$/.test(l));
                    results.push({
                        vehicle_class: name,
                        price_usd: price,
                        pax_capacity: numLines[0] ? parseInt(numLines[0]) : null,
                        bags_capacity: numLines[1] ? parseInt(numLines[1]) : null,
                        badge: lines[0] === 'Best Choice' ? 'Best Choice' : null,
                    });
                }
                return results;
            }
        """)

        result["transfers"] = sorted(cards, key=lambda x: x.get("price_usd") or 0)
        result["status"] = "ok" if cards else "no_results"
        log(f"    Extracted {len(cards)} vehicle classes")

    except Exception as e:
        result["status"] = "error"
        result["notes"] = str(e)
        log(f"    ERROR: {e}")

    return result


# ─────────────────────────────────────────────
# Welcome Pickups scraper (form-fill)
# ─────────────────────────────────────────────
async def scrape_welcomepickups(page, from_loc: str, to_loc: str, pax: int, date_str: str) -> dict:
    """Form-fill Welcome Pickups — best for European cruise port routes."""
    result = {
        "source": "welcomepickups",
        "route": f"{from_loc}→{to_loc}",
        "description": f"{from_loc} → {to_loc}",
        "url": "https://www.welcomepickups.com/",
        "pax": pax,
        "date": date_str,
        "scraped_at": datetime.now().isoformat(),
        "transfers": [],
        "screenshot": None,
        "status": "unknown",
        "notes": "Premium transfers — European airports and cruise ports",
    }

    log(f"  Welcome Pickups form-fill: {from_loc} → {to_loc}")

    try:
        await page.goto("https://www.welcomepickups.com/", timeout=30000, wait_until="domcontentloaded")
        await asyncio.sleep(3)

        # From field: id="downshift-0-input"
        from_inp = page.locator("#downshift-0-input, #downshift-2-input").first
        await from_inp.click()
        await from_inp.fill(from_loc)
        await asyncio.sleep(2)

        # Click first autocomplete suggestion
        try:
            await page.locator("[id^='downshift'][id$='item-0'], [class*='suggestion'] li, [role='option']").first.click()
            log("    From suggestion clicked")
        except Exception as e:
            log(f"    From autocomplete: {e}")
        await asyncio.sleep(1)

        # To field: id="downshift-1-input"
        to_inp = page.locator("#downshift-1-input, #downshift-3-input").first
        await to_inp.click()
        await to_inp.fill(to_loc)
        await asyncio.sleep(2)

        try:
            await page.locator("[id^='downshift'][id$='item-0'], [class*='suggestion'] li, [role='option']").first.click()
            log("    To suggestion clicked")
        except Exception as e:
            log(f"    To autocomplete: {e}")
        await asyncio.sleep(1)

        # Click Continue to proceed to date selection
        await page.get_by_role("button", name="Continue").first.click()
        await asyncio.sleep(3)

        screenshot_path = OUTPUT_DIR / f"transfer_welcomepickups_{date_str}.png"
        await page.screenshot(path=str(screenshot_path))
        result["screenshot"] = str(screenshot_path)
        result["url"] = page.url

        # Probe for vehicle results on whatever page we land on
        for sel in ["[class*='vehicle']","[class*='transfer-option']","[class*='car-type']","[class*='product-card']","[class*='offer']"]:
            try:
                c = await page.locator(sel).count()
                if c > 0:
                    t = (await page.locator(sel).first.inner_text()).strip()[:100]
                    log(f"    {c} × {sel}: {t[:60]}")
                    result["status"] = "ambiguous"
                    result["notes"] = f"Landed on: {page.url} — manual inspection needed"
                    break
            except Exception:
                pass

        if result["status"] == "unknown":
            result["status"] = "no_results"
            result["notes"] = "No vehicle results found — WP may require more form steps"

    except Exception as e:
        result["status"] = "error"
        result["notes"] = str(e)
        log(f"    ERROR: {e}")

    return result


# ─────────────────────────────────────────────
# Main runner
# ─────────────────────────────────────────────
async def run_tests(
    route_key: str | None,
    from_loc: str,
    to_loc: str,
    date_str: str,
    source: str,
    pax: int,
):
    from playwright.async_api import async_playwright

    # Determine route identifier for output file
    safe_route = (route_key or f"{from_loc}_{to_loc}").replace(" ", "_").replace("→", "-")

    results = {
        "route": safe_route,
        "from": from_loc,
        "to": to_loc,
        "date": date_str,
        "pax": pax,
        "scraped_at": datetime.now().isoformat(),
        "kiwitaxi": {},
        "welcomepickups": {},
    }

    # Merge with existing JSON
    out_file = OUTPUT_DIR / f"transfer_test_{safe_route}_{date_str}.json"
    if out_file.exists() and source != "all":
        try:
            existing = json.loads(out_file.read_text())
            for src_key in ["kiwitaxi", "welcomepickups"]:
                if src_key != source and existing.get(src_key):
                    results[src_key] = existing[src_key]
            log(f"  Merged existing data (preserving non-{source} sources)")
        except Exception as e:
            log(f"  Merge warning: {e}")

    log(f"Transfer scraper | {from_loc} → {to_loc} | {date_str} | {pax} pax | source={source}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled", "--disable-dev-shm-usage"],
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            ),
        )

        if source in ("all", "kiwitaxi"):
            page = await context.new_page()
            try:
                if route_key and route_key in KIWITAXI_ROUTES:
                    desc, url = KIWITAXI_ROUTES[route_key]
                    results["kiwitaxi"] = await scrape_kiwitaxi_url(page, route_key, desc, url, pax, date_str)
                else:
                    results["kiwitaxi"] = await scrape_kiwitaxi_form(page, from_loc, to_loc, pax, date_str)
            finally:
                await page.close()

        if source in ("all", "welcomepickups"):
            page = await context.new_page()
            try:
                results["welcomepickups"] = await scrape_welcomepickups(page, from_loc, to_loc, pax, date_str)
            finally:
                await page.close()

        await browser.close()

    # Save
    out_file.write_text(json.dumps(results, indent=2))
    log(f"\nSaved: {out_file}")

    # Print summary
    _print_summary(results)
    return results


def _print_summary(results: dict):
    from_loc = results.get("from", "?")
    to_loc = results.get("to", "?")
    date_str = results.get("date", "?")
    pax = results.get("pax", 2)

    print(f"\n{'='*65}")
    print(f"TRANSFER PRICES | {from_loc} → {to_loc} | {date_str} | {pax} pax")
    print(f"{'='*65}")

    kw = results.get("kiwitaxi", {})
    if kw.get("status") == "ok":
        transfers = kw.get("transfers", [])
        dur = f" | ~{kw['duration_min']} min" if kw.get("duration_min") else ""
        print(f"\nKiwitaxi (fixed price per vehicle{dur}):")
        print(f"  {'Vehicle Class':<22} {'Cap':>4}  {'$/vehicle':>10}  {'Examples'}")
        print(f"  {'-'*22} {'---':>4}  {'---------':>10}  {'-'*30}")
        for t in transfers:
            name = (t.get("vehicle_class") or "")[:21]
            pax_c = f"{t['pax_capacity']} pax" if t.get("pax_capacity") else "    "
            price = f"${t['price_usd']}" if t.get("price_usd") else "n/a"
            ex = (t.get("vehicle_examples") or "")[:35]
            badge = " ★" if t.get("badge") == "Best Choice" else "  "
            print(f"  {name:<22} {pax_c:>4}  {price:>10}{badge}  {ex}")

        # Highlight for D2M use cases
        for_2 = [t for t in transfers if t.get("pax_capacity") and t["pax_capacity"] >= 2]
        for_group = [t for t in transfers if t.get("pax_capacity") and t["pax_capacity"] >= 7]
        if for_2:
            cheapest_2 = for_2[0]
            print(f"\n  ✈ For 2 pax: {cheapest_2['vehicle_class']} @ ${cheapest_2['price_usd']}/vehicle (${cheapest_2['price_usd']/2:.0f}/person)")
        if for_group:
            print(f"  ✈ Group (7+): {for_group[0]['vehicle_class']} @ ${for_group[0]['price_usd']}/vehicle")

        print(f"\n  D2M markup (25%): multiply vehicle price × 1.25 for client quote")
        if for_2:
            net = for_2[0]["price_usd"]
            print(f"  Example (2-pax Comfort): ${net} net × 1.25 = ${net*1.25:.0f} client price")

    elif kw.get("status") == "route_not_found":
        print(f"\nKiwitaxi: ROUTE NOT FOUND — {kw.get('notes', '')}")
    elif kw.get("status") == "bot_blocked":
        print(f"\nKiwitaxi: BOT-BLOCKED")
    elif kw:
        print(f"\nKiwitaxi: {kw.get('status')} — {kw.get('notes', '')}")

    wp = results.get("welcomepickups", {})
    if wp.get("status") not in ("", "unknown", None):
        print(f"\nWelcome Pickups: {wp.get('status')} — {wp.get('notes', '')}")

    print()


def main():
    parser = argparse.ArgumentParser(description="Transfer price scraper — Kiwitaxi + Welcome Pickups")
    parser.add_argument("--route", help="Pre-mapped route key (e.g. LIS-LISBON). Use --list-routes to see all.")
    parser.add_argument("--from", dest="from_loc", help="Origin location (used for form-fill if --route not given)")
    parser.add_argument("--to", dest="to_loc", help="Destination location")
    parser.add_argument("--date", default="2026-09-05", help="Transfer date (YYYY-MM-DD)")
    parser.add_argument("--pax", type=int, default=2, help="Number of passengers (default: 2)")
    parser.add_argument("--source", default="kiwitaxi", choices=["all", "kiwitaxi", "welcomepickups"])
    parser.add_argument("--list-routes", action="store_true", help="List all pre-mapped routes and exit")
    args = parser.parse_args()

    if args.list_routes:
        list_routes()
        return

    route_key = args.route
    if route_key:
        if route_key not in KIWITAXI_ROUTES:
            print(f"Unknown route '{route_key}'. Use --list-routes to see options.")
            return
        desc, _ = KIWITAXI_ROUTES[route_key]
        parts = desc.split(" → ")
        from_loc = parts[0] if parts else route_key
        to_loc = parts[1] if len(parts) > 1 else route_key
    else:
        from_loc = args.from_loc
        to_loc = args.to_loc
        if not from_loc or not to_loc:
            parser.error("Provide either --route KEY or both --from and --to")

    asyncio.run(run_tests(route_key, from_loc, to_loc, args.date, args.source, args.pax))


if __name__ == "__main__":
    main()
