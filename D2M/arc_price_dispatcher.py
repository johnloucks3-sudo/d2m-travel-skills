#!/usr/bin/env python3
"""
arc_price_dispatcher.py
Dreams2Memories Travel — Thunderbird Wing
ARC Price Intelligence Dispatcher — Option C Auto-Execute

Runs automatically on SEARCH_WINDOW_OPEN events from d2m_lifecycle_scheduler.py.
Detects ARC type from touchpoint arc field, extracts route params from arc_search_params,
spawns the appropriate scraper subprocess, caches results, posts to wing_comms.

Can also run standalone:
  python3 arc_price_dispatcher.py --client kuklinski --arc ARC1-A
  python3 arc_price_dispatcher.py --client kuklinski --arc ARC2-A
  python3 arc_price_dispatcher.py --client all --arc-type arc1
  python3 arc_price_dispatcher.py --list-pending   # Show ARC TPs with search windows opening soon

Architecture:
  1. Scheduler fires SEARCH_WINDOW_OPEN on tp.search_start date
  2. _fire_search_window_open() calls dispatch_arc(client_data, tp_data)
  3. Dispatcher spawns this script as background subprocess (non-blocking)
  4. This script: runs scrapers → writes results → posts to wing_comms + claude_inbox
  5. A2 Dembe picks up wing_comms task → validates top-3 options
  6. A9 Vic applies markup math → clears for Dani
  7. Dani crafts ARC-B email → WF-17 gate → Commander sends

Standing Order 2026-04-17: COS Hale COO authority. Auto-execute approved for all ARCs.
"""

import argparse
import asyncio
import json
import logging
import os
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

THUNDERBIRD_ROOT = Path("/home/john/Thunderbird")
DATA_DIR         = THUNDERBIRD_ROOT / "core" / "travel" / "data"
SCRIPTS_DIR      = THUNDERBIRD_ROOT / "scripts"
CLIENTS_DIR      = THUNDERBIRD_ROOT / "D2M" / "clients"
WING_COMMS       = THUNDERBIRD_ROOT / "OpsCenter" / "collaboration" / "wing_comms.md"
CLAUDE_INBOX     = THUNDERBIRD_ROOT / "claude_inbox.md"
LOG_FILE         = THUNDERBIRD_ROOT / "logs" / "arc_dispatcher.log"

DATA_DIR.mkdir(parents=True, exist_ok=True)

COMMANDER_EMAIL  = "johnloucks3@gmail.com"
CONCIERGE_EMAIL  = "d2mconcierge@gmail.com"

# Markup rates — CLAUDE.md §4
MARKUP_STANDARD  = 0.25   # hotels/cruises
MARKUP_SLH       = 0.22   # premium/SLH properties

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("arc_dispatcher")


# ── Entry Points ──────────────────────────────────────────────────────────────

def dispatch_arc(client_data: dict, tp_data: dict, dry_run: bool = False) -> str:
    """
    Called by d2m_lifecycle_scheduler._fire_search_window_open().
    Launches this script as a background subprocess so the scheduler doesn't block.
    Returns the path to the results file (will be written async).
    """
    tp = tp_data["tp"]
    arc = tp.get("arc", "")
    client_id = tp_data["client_id"]
    tp_id = tp.get("id", "UNKNOWN")

    if not arc or not arc.startswith("arc"):
        log.warning(f"dispatch_arc called on non-ARC touchpoint {tp_id} — skipping")
        return ""

    params = tp.get("arc_search_params")
    if not params:
        log.warning(f"No arc_search_params on {tp_id} — posting manual task instead")
        _post_manual_task(tp_data)
        return ""

    # Results file path
    today_str = date.today().isoformat()
    results_file = DATA_DIR / f"arc_{client_id}_{tp_id}_{today_str}.json"

    if dry_run:
        log.info(f"[DRY RUN] Would dispatch {arc} for {client_id} {tp_id}")
        log.info(f"[DRY RUN] Results would go to {results_file}")
        return str(results_file)

    # Spawn background subprocess (non-blocking)
    cmd = [
        sys.executable, __file__,
        "--client", client_id,
        "--arc", tp_id,
        "--results-file", str(results_file),
    ]
    log.info(f"  Spawning ARC dispatcher: {' '.join(cmd)}")

    log_path = LOG_FILE.parent / f"arc_{client_id}_{tp_id}_{today_str}.log"
    with open(log_path, "w") as log_out:
        subprocess.Popen(
            cmd,
            stdout=log_out,
            stderr=log_out,
            start_new_session=True,
        )

    _post_dispatched_notice(tp_data, results_file, log_path)
    return str(results_file)


# ── ARC Runners ───────────────────────────────────────────────────────────────

def run_arc_search(client_id: str, tp_id: str, results_file: Path):
    """Main execution — called when running as subprocess."""
    # Load touchpoint data
    tp_data = _load_tp(client_id, tp_id)
    if not tp_data:
        log.error(f"Could not load touchpoint {tp_id} for client {client_id}")
        sys.exit(1)

    tp = tp_data["tp"]
    params = tp.get("arc_search_params", {})
    arc_type = tp.get("arc", "")

    log.info(f"═══ ARC Dispatcher — {client_id} {tp_id} [{arc_type}] ═══")
    log.info(f"  Results file: {results_file}")

    results = {
        "client_id": client_id,
        "tp_id": tp_id,
        "arc_type": arc_type,
        "dispatched_at": datetime.now().isoformat(),
        "status": "in_progress",
        "searches": {},
        "results_file": str(results_file),
    }

    try:
        if arc_type == "arc1":
            results["searches"] = asyncio.run(_run_arc1(params, tp_data))
        elif arc_type == "arc2":
            results["searches"] = asyncio.run(_run_arc2(params, tp_data))
        elif arc_type == "arc3":
            results["searches"] = asyncio.run(_run_arc3(params, tp_data))
        else:
            log.error(f"Unknown arc_type: {arc_type}")
            results["status"] = "error"
            results["error"] = f"Unknown arc_type: {arc_type}"
            results_file.write_text(json.dumps(results, indent=2))
            return

        results["status"] = "complete"
        results["completed_at"] = datetime.now().isoformat()

    except Exception as e:
        log.error(f"Arc dispatch failed: {e}", exc_info=True)
        results["status"] = "error"
        results["error"] = str(e)

    results_file.write_text(json.dumps(results, indent=2))
    log.info(f"  Results written → {results_file}")

    _post_results_to_wing(tp_data, results)


# ── ARC1: Airfare + Hotel ─────────────────────────────────────────────────────

async def _run_arc1(params: dict, tp_data: dict) -> dict:
    """Run flight scrapers + hotel search for ARC1."""
    searches = {"flights": [], "hotel": None, "markup": {}}

    # ── Flights ──
    flight_segments = params.get("flights", [])
    if not flight_segments:
        log.warning("ARC1: No flight segments in arc_search_params.flights")

    for seg in flight_segments:
        origin  = seg.get("origin", "")
        dest    = seg.get("dest", "")
        dep_date = seg.get("date", "")
        adults  = seg.get("adults", 1)
        label   = seg.get("label", f"{origin}→{dest}")

        if not origin or not dest or not dep_date:
            log.warning(f"ARC1 flight segment missing required fields: {seg}")
            continue

        log.info(f"  Running flight scraper: {origin}→{dest} {dep_date} {adults}pax")

        # Output file from the scraper script
        flight_out = DATA_DIR / f"airline_test_{origin}_{dest}_{dep_date}.json"

        # Run Skiplagged + Kayak (most reliable, not bot-blocked)
        # Skip Expedia/CheapTickets (bot-blocked). Centrav only if session exists.
        centrav_session = DATA_DIR / "centrav_session.json"
        sources = ["skiplagged", "kayak"]
        if centrav_session.exists():
            sources.append("centrav")

        seg_results = {"label": label, "origin": origin, "dest": dest,
                       "date": dep_date, "adults": adults, "sources": {}}

        for source in sources:
            cmd = [
                sys.executable,
                str(SCRIPTS_DIR / "test_airline_scrapers.py"),
                "--origin", origin,
                "--dest", dest,
                "--date", dep_date,
                "--source", source,
                "--headless", "true",
            ]
            log.info(f"    Scraping {source} ({origin}→{dest})")
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                if proc.returncode == 0 and flight_out.exists():
                    data = json.loads(flight_out.read_text())
                    seg_results["sources"][source] = data.get(source, {})
                else:
                    log.warning(f"    {source} scraper returned {proc.returncode}")
                    seg_results["sources"][source] = {"status": "error", "stderr": proc.stderr[-200:]}
            except subprocess.TimeoutExpired:
                log.warning(f"    {source} timed out after 120s")
                seg_results["sources"][source] = {"status": "timeout"}
            except Exception as e:
                log.error(f"    {source} error: {e}")
                seg_results["sources"][source] = {"status": "error", "error": str(e)}

        # Best economy price across sources
        eco_prices = []
        for src_data in seg_results["sources"].values():
            eco = src_data.get("economy", {})
            pp = eco.get("lowest_price_pp")
            if pp:
                eco_prices.append(pp)
        seg_results["best_economy_pp"] = min(eco_prices) if eco_prices else None

        # A9 markup (standard 25%)
        if seg_results["best_economy_pp"]:
            net = seg_results["best_economy_pp"] * adults
            seg_results["net_total"] = net
            seg_results["client_price"] = round(net * (1 + MARKUP_STANDARD), 2)
            seg_results["markup_pct"] = MARKUP_STANDARD

        searches["flights"].append(seg_results)

    # ── Hotel ──
    hotel_params = params.get("hotel")
    if hotel_params:
        searches["hotel"] = await _run_hotel_search(hotel_params)
    else:
        log.info("  ARC1: No hotel params — skipping hotel search")
        searches["hotel"] = {"status": "skipped", "reason": "no hotel params configured"}

    return searches


async def _run_hotel_search(hotel_params: dict) -> dict:
    """Run Bedsonline hotel search (portal or API)."""
    cred_file = THUNDERBIRD_ROOT / "hotelbeds_credentials.json"

    if not cred_file.exists():
        log.warning("  Hotel: hotelbeds_credentials.json not found — skipping hotel search")
        return {
            "status": "pending_credentials",
            "message": "Bedsonline credentials not configured. Commander: add to hotelbeds_credentials.json.",
            "action_required": "Add Bedsonline portal username/password to ~/Thunderbird/hotelbeds_credentials.json",
        }

    try:
        creds = json.loads(cred_file.read_text())
    except Exception as e:
        log.error(f"  Hotel: Failed to load credentials: {e}")
        return {"status": "error", "error": str(e)}

    city         = hotel_params.get("city", "")
    country      = hotel_params.get("country", "")
    checkin      = hotel_params.get("checkin", "")
    checkout     = hotel_params.get("checkout", "")
    rooms        = hotel_params.get("rooms", 1)
    notes        = hotel_params.get("notes", "")

    # Portal mode (Playwright) — Commander has Bedsonline login
    if creds.get("portal_username") and creds.get("portal_password"):
        return await _hotel_portal_search(creds, city, country, checkin, checkout, rooms, notes)

    # API mode (APITude key/secret)
    if creds.get("api_key") and creds.get("api_secret"):
        return _hotel_api_search(creds, city, country, checkin, checkout, rooms)

    return {
        "status": "pending_credentials",
        "message": "hotelbeds_credentials.json exists but has no valid credentials (need portal_username+portal_password or api_key+api_secret).",
        "action_required": "Fill in credentials. See ~/Thunderbird/hotelbeds_credentials.json.template",
    }


async def _hotel_portal_search(creds: dict, city: str, country: str,
                                checkin: str, checkout: str, rooms: int, notes: str) -> dict:
    """Search Bedsonline portal via Playwright stealth."""
    try:
        from playwright.async_api import async_playwright
        from playwright_stealth import Stealth  # type: ignore
    except ImportError:
        return {"status": "error", "error": "playwright or playwright-stealth not installed"}

    screenshot_path = DATA_DIR / f"bedsonline_{city.lower().replace(' ', '_')}_{checkin}.png"
    results = {
        "source": "bedsonline_portal",
        "city": city,
        "country": country,
        "checkin": checkin,
        "checkout": checkout,
        "rooms": rooms,
        "notes": notes,
        "hotels": [],
        "screenshot": str(screenshot_path),
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        )
        page = await context.new_page()
        await Stealth().apply_stealth(page)

        try:
            # Login
            log.info("  Bedsonline: Logging in...")
            await page.goto("https://app.bedsonline.com/auth/login",
                            wait_until="domcontentloaded", timeout=30_000)
            await page.wait_for_timeout(2_000)

            await page.fill('input[name="username"], input[type="email"], #username',
                            creds["portal_username"], timeout=10_000)
            await page.fill('input[name="password"], input[type="password"], #password',
                            creds["portal_password"], timeout=10_000)
            await page.press('input[name="password"], input[type="password"], #password', "Enter")
            await page.wait_for_timeout(4_000)

            if "login" in page.url.lower():
                log.error("  Bedsonline: Login failed — still on login page")
                results["status"] = "login_failed"
                await page.screenshot(path=str(screenshot_path))
                await browser.close()
                return results

            log.info(f"  Bedsonline: Logged in — {page.url}")

            # Search
            search_url = (
                f"https://app.bedsonline.com/accommodation"
                f"?destination={city.replace(' ', '%20')}"
                f"&checkIn={checkin}&checkOut={checkout}&rooms={rooms}"
            )
            await page.goto(search_url, wait_until="domcontentloaded", timeout=30_000)
            await page.wait_for_timeout(5_000)

            await page.screenshot(path=str(screenshot_path))

            # Extract hotel names + prices
            hotels_raw = await page.evaluate("""() => {
                const hotels = [];
                const cards = document.querySelectorAll('[class*="hotel-card"], [class*="property-card"], [class*="result-item"], [class*="hotel-item"]');
                cards.forEach(card => {
                    const name = card.querySelector('[class*="hotel-name"], h2, h3, [class*="title"]');
                    const price = card.querySelector('[class*="price"], [class*="rate"], [class*="amount"]');
                    const stars = card.querySelector('[class*="star"], [class*="rating"]');
                    if (name) {
                        hotels.push({
                            name: name.innerText.trim(),
                            price: price ? price.innerText.trim() : null,
                            stars: stars ? stars.innerText.trim() : null,
                        });
                    }
                });
                // Fallback: grab all price+name combos
                if (hotels.length === 0) {
                    document.querySelectorAll('[class*="price"]').forEach(el => {
                        const t = el.innerText.trim();
                        if (t.includes('€') || t.includes('$') || t.includes('USD')) {
                            hotels.push({name: 'Unknown', price: t, stars: null});
                        }
                    });
                }
                return hotels.slice(0, 10);
            }""")

            results["hotels"] = hotels_raw
            results["status"] = "ok" if hotels_raw else "no_results"
            results["url"] = page.url

            log.info(f"  Bedsonline: Found {len(hotels_raw)} hotels in {city}")

        except Exception as e:
            log.error(f"  Bedsonline portal error: {e}", exc_info=True)
            results["status"] = "error"
            results["error"] = str(e)
            try:
                await page.screenshot(path=str(screenshot_path))
            except Exception:
                pass

        await browser.close()

    return results


def _hotel_api_search(creds: dict, city: str, country: str,
                       checkin: str, checkout: str, rooms: int) -> dict:
    """Search Hotelbeds API (when api_key + api_secret available)."""
    try:
        import requests
        import hashlib
        import time as time_mod

        api_key    = creds["api_key"]
        api_secret = creds["api_secret"]
        base_url   = creds.get("base_url", "https://api.hotelbeds.com")

        timestamp = str(int(time_mod.time()))
        signature = hashlib.sha256(f"{api_key}{api_secret}{timestamp}".encode()).hexdigest()

        headers = {
            "Api-key": api_key,
            "X-Signature": signature,
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
        }

        payload = {
            "stay": {"checkIn": checkin, "checkOut": checkout},
            "occupancies": [{"rooms": rooms, "adults": 2, "children": 0}],
            "destination": {"code": city[:3].upper()},
            "filter": {"maxHotels": 10, "minCategory": 4},
        }

        resp = requests.post(
            f"{base_url}/hotel-api/1.0/hotels",
            json=payload,
            headers=headers,
            timeout=30,
        )

        if resp.ok:
            data = resp.json()
            hotels = data.get("hotels", {}).get("hotels", [])
            return {
                "source": "hotelbeds_api",
                "city": city,
                "checkin": checkin,
                "checkout": checkout,
                "rooms": rooms,
                "hotels": [
                    {
                        "name": h.get("name", ""),
                        "code": h.get("code", ""),
                        "category": h.get("categoryCode", ""),
                        "min_rate": h.get("minRate", 0),
                        "currency": h.get("currency", "EUR"),
                    }
                    for h in hotels[:10]
                ],
                "status": "ok",
            }
        else:
            return {"source": "hotelbeds_api", "status": "error",
                    "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}

    except Exception as e:
        return {"source": "hotelbeds_api", "status": "error", "error": str(e)}


# ── ARC2: Shore Excursions ────────────────────────────────────────────────────

async def _run_arc2(params: dict, tp_data: dict) -> dict:
    """Run tour scrapers for each port."""
    ports = params.get("ports", [])
    pax   = params.get("pax", 2)
    query = params.get("query", "shore excursion group")

    if not ports:
        log.warning("ARC2: No ports in arc_search_params.ports")
        return {"status": "error", "error": "No ports configured"}

    results = {"ports": [], "pax": pax}

    for port in ports:
        dest  = port.get("dest", port.get("name", "").lower().replace(" ", "-").replace(",", ""))
        name  = port.get("name", dest)
        date_ = port.get("date", "")

        log.info(f"  ARC2: Scraping tours for {name} ({dest})")

        out_file = DATA_DIR / f"tour_test_{dest}_{date_}.json"
        cmd = [
            sys.executable,
            str(SCRIPTS_DIR / "test_tour_scrapers.py"),
            "--dest", dest,
            "--date", date_,
            "--query", query,
        ]

        port_result = {"name": name, "dest": dest, "date": date_, "sources": {}}

        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if proc.returncode == 0 and out_file.exists():
                data = json.loads(out_file.read_text())
                port_result["sources"] = data
                port_result["status"] = "ok"
            else:
                port_result["status"] = "error"
                port_result["stderr"] = proc.stderr[-200:]
        except subprocess.TimeoutExpired:
            port_result["status"] = "timeout"
        except Exception as e:
            port_result["status"] = "error"
            port_result["error"] = str(e)

        results["ports"].append(port_result)

    return results


# ── ARC3: Transfers ───────────────────────────────────────────────────────────

async def _run_arc3(params: dict, tp_data: dict) -> dict:
    """Run transfer scrapers for all configured routes."""
    routes = params.get("routes", [])
    pax    = params.get("pax", 2)

    if not routes:
        log.warning("ARC3: No routes in arc_search_params.routes")
        return {"status": "error", "error": "No routes configured"}

    results = {"routes": [], "pax": pax}

    for route_spec in routes:
        route      = route_spec.get("route", "")
        label      = route_spec.get("label", route)
        date_      = route_spec.get("date", "")
        pax_route  = route_spec.get("pax", pax)

        log.info(f"  ARC3: Scraping transfer — {label} ({route})")

        out_file = DATA_DIR / f"transfer_test_{route}_{date_}.json"
        cmd = [
            sys.executable,
            str(SCRIPTS_DIR / "test_transfer_scrapers.py"),
            "--route", route,
            "--date", date_,
            "--pax", str(pax_route),
        ]

        route_result = {"label": label, "route": route, "date": date_, "pax": pax_route}

        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if proc.returncode == 0 and out_file.exists():
                data = json.loads(out_file.read_text())
                route_result["data"] = data
                route_result["status"] = "ok"

                # A9 markup
                best = _extract_best_transfer_price(data)
                if best:
                    route_result["net_price"] = best
                    route_result["client_price"] = round(best * (1 + MARKUP_STANDARD), 2)
                    route_result["markup_pct"] = MARKUP_STANDARD
            else:
                route_result["status"] = "error"
                route_result["stderr"] = proc.stderr[-200:]
        except subprocess.TimeoutExpired:
            route_result["status"] = "timeout"
        except Exception as e:
            route_result["status"] = "error"
            route_result["error"] = str(e)

        results["routes"].append(route_result)

    return results


def _extract_best_transfer_price(data: dict) -> float | None:
    """Extract best (lowest) transfer price from scraper output."""
    prices = []
    for src_data in data.values():
        if isinstance(src_data, dict):
            for vehicle in src_data.get("vehicles", {}).values():
                p = vehicle.get("price")
                if p:
                    try:
                        prices.append(float(str(p).replace("$", "").replace(",", "")))
                    except (ValueError, TypeError):
                        pass
    return min(prices) if prices else None


# ── Wing Comms Integration ────────────────────────────────────────────────────

def _post_dispatched_notice(tp_data: dict, results_file: Path, log_path: Path):
    """Post 'search dispatched' notice immediately to wing_comms."""
    tp = tp_data["tp"]
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    arc = tp.get("arc", "").upper()
    client = tp_data["client_name"]

    msg = (
        f"\n---\n"
        f"**[COS HALE — ARC DISPATCHER — {ts}]**\n"
        f"## 🔍 {arc} SEARCH DISPATCHED — {client}\n"
        f"**TP:** {tp.get('id')} — {tp.get('label')}\n"
        f"**Client:** {client}\n"
        f"**Status:** Scraper running in background\n"
        f"**Results file:** `{results_file}`\n"
        f"**Dispatcher log:** `{log_path}`\n"
        f"**A2 Dembe:** Stand by for structured results. Will post to wing_comms on completion.\n"
        f"**A9 Vic:** Markup validation queued (25% standard / 22% SLH). Check results file when ready.\n"
        f"**ETA:** 5–15 minutes depending on source count.\n"
    )
    with open(WING_COMMS, "a") as f:
        f.write(msg)


def _post_results_to_wing(tp_data: dict, results: dict):
    """Post structured search results to wing_comms and claude_inbox when scraper completes."""
    tp = tp_data["tp"]
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    arc = tp.get("arc", "").upper()
    client = tp_data["client_name"]
    status = results.get("status", "unknown")
    searches = results.get("searches", {})

    # Build summary
    summary_lines = [f"**Arc type:** {arc}", f"**Status:** {status}"]

    if arc.lower() == "arc1":
        # Flights summary
        for seg in searches.get("flights", []):
            label = seg.get("label", "")
            best  = seg.get("best_economy_pp")
            net   = seg.get("net_total")
            client_price = seg.get("client_price")
            summary_lines.append(
                f"  - **Flight {label}:** "
                + (f"Best eco ${best:,.2f}/pp · Net ${net:,.2f} · Client ${client_price:,.2f}"
                   if best else "No prices found")
            )

        # Hotel summary
        hotel = searches.get("hotel", {})
        hotel_status = hotel.get("status", "unknown")
        if hotel_status == "ok":
            hotels = hotel.get("hotels", [])[:3]
            summary_lines.append(f"  - **Hotels found:** {len(hotel.get('hotels', []))} options")
            for h in hotels:
                summary_lines.append(f"      - {h.get('name', '?')} — {h.get('price', h.get('min_rate', 'N/A'))}")
        elif hotel_status == "pending_credentials":
            summary_lines.append(f"  - **Hotel:** {hotel.get('action_required', 'Credentials needed')}")
        else:
            summary_lines.append(f"  - **Hotel:** {hotel_status}")

    elif arc.lower() == "arc2":
        for port in searches.get("ports", []):
            p_name = port.get("name", "")
            p_status = port.get("status", "?")
            summary_lines.append(f"  - **{p_name}:** {p_status}")

    elif arc.lower() == "arc3":
        for route in searches.get("routes", []):
            label = route.get("label", route.get("route", "?"))
            client_price = route.get("client_price")
            r_status = route.get("status", "?")
            summary_lines.append(
                f"  - **{label}:** "
                + (f"Client ${client_price:,.2f}" if client_price else r_status)
            )

    summary = "\n".join(summary_lines)

    wing_msg = (
        f"\n---\n"
        f"**[COS HALE — ARC RESULTS — {ts}]**\n"
        f"## ✅ {arc} SEARCH COMPLETE — {client}\n"
        f"**TP:** {tp.get('id')} — {tp.get('label')}\n"
        f"**Results file:** `{results.get('results_file', 'N/A')}`\n\n"
        f"{summary}\n\n"
        f"**A2 Dembe action:** Review results file → select top 3 options (value / recommended / luxury) "
        f"→ post A2 summary to claude_inbox for Dani.\n"
        f"**A9 Vic action:** Validate markup math before Dani drafts {arc}-B email.\n"
        f"**Dani action:** Await A2+A9 handoff → craft {arc}-B email → WF-17 gate.\n"
    )

    inbox_msg = (
        f"\n---\n"
        f"**[LIFECYCLE — ARC RESULTS — {ts}]**\n"
        f"## {arc} SEARCH RESULTS READY — {client}\n"
        f"**TP:** {tp.get('id')} — {tp.get('label')}\n"
        f"**Results file:** `{results.get('results_file', 'N/A')}`\n"
        f"{summary}\n\n"
        f"**A2 Dembe:** Extract top-3 options (value/recommended/luxury). "
        f"Post selections to wing_comms for Dani pickup.\n"
        f"**Next step:** {tp.get('id', '').replace('-A', '-B').replace('ARC', 'Send ARC')} email — "
        f"Dani drafts once A2+A9 clear.\n"
    )

    with open(WING_COMMS, "a") as f:
        f.write(wing_msg)
    with open(CLAUDE_INBOX, "a") as f:
        f.write(inbox_msg)

    log.info(f"  Results posted to wing_comms and claude_inbox")


def _post_manual_task(tp_data: dict):
    """Fallback: post a manual research task when no arc_search_params configured."""
    tp = tp_data["tp"]
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    arc = tp.get("arc", "").upper()
    client = tp_data["client_name"]

    msg = (
        f"\n---\n"
        f"**[COS HALE — ARC RESEARCH NEEDED — {ts}]**\n"
        f"## ⚠️ {arc} — CONFIGURE arc_search_params TO ENABLE AUTO-EXECUTE\n"
        f"**Client:** {client}\n"
        f"**TP:** {tp.get('id')} — {tp.get('label')}\n"
        f"**Issue:** arc_search_params not set on this touchpoint — cannot auto-run scrapers.\n"
        f"**Action:** Edit `D2M/clients/{tp_data['client_id']}_touchpoints.json` — "
        f"add arc_search_params to TP {tp.get('id')}.\n"
        f"See ARC1/ARC2/ARC3 param schema in `D2M/arc_price_dispatcher.py`.\n"
    )

    with open(WING_COMMS, "a") as f:
        f.write(msg)


# ── Data Helpers ──────────────────────────────────────────────────────────────

def _load_tp(client_id: str, tp_id: str) -> dict | None:
    """Load a specific touchpoint for a client."""
    # Try both possible file names
    candidates = [
        CLIENTS_DIR / f"{client_id}_touchpoints.json",
        CLIENTS_DIR / f"{client_id}_profile.json",
    ]
    for f in candidates:
        if not f.exists():
            continue
        try:
            data = json.loads(f.read_text())
            for tp in data.get("touchpoints", []):
                if tp.get("id") == tp_id:
                    return {
                        "client_id": data.get("client_id", client_id),
                        "client_name": data.get("client_name", client_id),
                        "client_email": data.get("client_email", ""),
                        "tp": tp,
                    }
        except Exception as e:
            log.error(f"Failed to load {f}: {e}")
    return None


def _list_pending_arcs():
    """List all ARC touchpoints with search_start within the next 30 days."""
    from datetime import timedelta
    today = date.today()
    cutoff = today + timedelta(days=30)

    for json_file in sorted(CLIENTS_DIR.glob("*_touchpoints.json")):
        try:
            data = json.loads(json_file.read_text())
            client = data.get("client_name", json_file.stem)
            for tp in data.get("touchpoints", []):
                arc = tp.get("arc", "")
                if not arc.startswith("arc"):
                    continue
                ss = tp.get("search_start", "")
                if not ss:
                    print(f"  ⚠  {client} {tp['id']} {arc} — no search_start configured")
                    continue
                try:
                    ss_date = datetime.strptime(ss, "%Y-%m-%d").date()
                except ValueError:
                    continue
                if today <= ss_date <= cutoff:
                    params_ok = "✓" if tp.get("arc_search_params") else "⚠ no params"
                    print(f"  {ss_date}  {client}  {tp['id']} [{arc}] — {params_ok}")
        except Exception as e:
            print(f"  Error reading {json_file}: {e}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="D2M ARC Price Dispatcher — auto-execute on SEARCH_WINDOW_OPEN")
    parser.add_argument("--client",        type=str, help="Client ID (e.g. kuklinski)")
    parser.add_argument("--arc",           type=str, help="TP ID to run (e.g. ARC1-A)")
    parser.add_argument("--results-file",  type=str, help="Output JSON path (used by subprocess mode)")
    parser.add_argument("--list-pending",  action="store_true", help="List ARCs opening in next 30 days")
    parser.add_argument("--dry-run",       action="store_true", help="Preview without scraping")
    args = parser.parse_args()

    if args.list_pending:
        print(f"\nARC touchpoints with search windows opening in next 30 days ({date.today().isoformat()}):\n")
        _list_pending_arcs()
        return

    if not args.client or not args.arc:
        parser.print_help()
        sys.exit(1)

    results_file = Path(args.results_file) if args.results_file else (
        DATA_DIR / f"arc_{args.client}_{args.arc}_{date.today().isoformat()}.json"
    )

    if args.dry_run:
        tp_data = _load_tp(args.client, args.arc)
        if not tp_data:
            print(f"Touchpoint {args.arc} not found for client {args.client}")
            sys.exit(1)
        params = tp_data["tp"].get("arc_search_params", {})
        print(f"\n[DRY RUN] Would run {args.arc} for {tp_data['client_name']}")
        print(f"  Arc type: {tp_data['tp'].get('arc', 'N/A')}")
        print(f"  Params: {json.dumps(params, indent=4)}")
        print(f"  Results would go to: {results_file}")
        return

    run_arc_search(args.client, args.arc, results_file)


if __name__ == "__main__":
    main()
