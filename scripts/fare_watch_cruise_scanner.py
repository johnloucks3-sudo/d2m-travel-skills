#!/usr/bin/env python3
"""
Cruise Fare Watch Scanner — Norway/Scandinavia 2027 Monitoring
================================================================
Scans Perx, Odysseus, and CruiseComplete for luxury cruise pricing.
Compares against configured alert thresholds and notifies Commander via Telegram.

Target: Norway/Scandinavia July–August 2027
Ships: Silversea Silver Dawn, Seabourn Quest, Regent Seven Seas Voyager
Route: Copenhagen → Southampton (or similar fjord routes)
Duration: 10–18 days

Uses Chrome CDP (port 9222) to connect to authenticated browser sessions.
Commander must be logged into Perx, Odysseus, and CruiseComplete beforehand.

Usage:
    python3 scripts/fare_watch_cruise_scanner.py [--watch-id <id>] [--source perx|odysseus|cruisecomplete]
    python3 scripts/fare_watch_cruise_scanner.py --list

Dreams2Memories Travel, LLC — Thunderbird Wing — Hale/Dembe 2026-06-09
"""

import asyncio
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, List, Any

import requests
from playwright.async_api import async_playwright

TB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TB))

DATA_DIR = TB / "data"
LOGS_DIR = TB / "logs"
CREDS_DIR = TB / "creds"
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

FARE_WATCHES_FILE = DATA_DIR / "fare_watches.json"
LAST_CHECK_FILE = DATA_DIR / "fare_watches" / "last_check_cruise.json"
LAST_CHECK_FILE.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s CRUISE-SCAN %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(str(LOGS_DIR / "fare_watch_cruise_scanner.log"), mode="a"),
    ],
)
log = logging.getLogger("cruise_scan")

COMMANDER_ID = 7554895206
ENV_FILE = TB / ".env"


def _load_telegram_token() -> str:
    """Load Telegram token from environment or .env file."""
    token = os.environ.get("TELEGRAM_D2MC2C_TOKEN", "")
    if not token and ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line.startswith("TELEGRAM_D2MC2C_TOKEN="):
                token = line.split("=", 1)[1].strip().strip('"').strip("'")
    return token


def _send_telegram(token: str, text: str) -> bool:
    """Send alert message to Commander via Telegram."""
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": COMMANDER_ID, "text": text, "parse_mode": "HTML"},
            timeout=15,
        )
        return resp.ok
    except Exception as exc:
        log.error("Telegram send failed: %s", exc)
        return False


def _load_fare_watches() -> List[Dict[str, Any]]:
    """Load fare watches from data/fare_watches.json."""
    if not FARE_WATCHES_FILE.exists():
        return []
    try:
        data = json.loads(FARE_WATCHES_FILE.read_text())
        return data.get("watches", [])
    except Exception as exc:
        log.error("Failed to load fare watches: %s", exc)
        return []


def _find_watch(watch_id: str) -> Optional[Dict[str, Any]]:
    """Find a specific watch by ID."""
    watches = _load_fare_watches()
    return next((w for w in watches if w.get("id") == watch_id), None)


def _save_last_check(results: Dict[str, Any]):
    """Save scan results to last_check_cruise.json."""
    LAST_CHECK_FILE.write_text(json.dumps(results, indent=2))


# ── Chrome CDP Connection ─────────────────────────────────────────────────────

async def _connect_chrome_cdp():
    """Connect to Chrome via CDP on port 9222."""
    try:
        async with async_playwright() as p:
            browser = await p.chromium.connect_over_cdp("http://localhost:9222")
            return browser
    except Exception as exc:
        log.error("Failed to connect to Chrome CDP: %s", exc)
        return None


async def _find_browser_tab(browser, keyword: str = None) -> Optional[Any]:
    """Find an open browser tab matching keyword (or any non-extension tab)."""
    if not browser or not browser.contexts:
        return None

    context = browser.contexts[0]
    pages = context.pages

    for page in pages:
        url = page.url
        if not url.startswith("http") or "extension" in url:
            continue
        if keyword and keyword.lower() in url.lower():
            return page

    # Return last http tab if no keyword match
    for page in reversed(pages):
        url = page.url
        if url.startswith("http") and "extension" not in url:
            return page

    return None


# ── Perx Scraper ────────────────────────────────────────────────────────────

async def scrape_perx_norway_pricing(browser) -> Dict[str, Any]:
    """
    Navigate Perx to search for Norway/Scandinavia cruises and extract pricing.
    Requires: Perx login session already open in browser.
    """
    results = {"source": "perx", "sailings": [], "errors": [], "status": "OK"}

    page = await _find_browser_tab(browser, "perx")
    if not page:
        log.warning("No Perx tab found in browser")
        results["status"] = "NO_TAB"
        return results

    try:
        # Navigate to search for Norway cruises
        log.info("Searching Perx for Norway/Scandinavia cruises...")
        await page.goto(
            "https://www.perx.com/cruises/search/?q=norway+scandinavia&date_from=2027-07-15&date_to=2027-08-20",
            wait_until="networkidle",
            timeout=60000,
        )
        await asyncio.sleep(3)

        # Extract all sailing cards
        content = await page.content()
        text = await page.evaluate("() => document.body.innerText")

        # Parse HTML for sailing containers
        sailings = []

        # Look for patterns like "Silver Dawn ... $10,400" or similar
        price_pattern = r'\$\s*([\d,]+(?:\.\d{2})?)'

        # Split by potential sailing cards (heuristic: lines with ship names + prices)
        for line in text.split('\n'):
            line = line.strip()
            if any(ship in line for ship in ['Silver Dawn', 'Seabourn Quest', 'Seven Seas Voyager']):
                # This line likely contains a sailing; look for prices nearby
                ship_name = next(s for s in ['Silver Dawn', 'Seabourn Quest', 'Seven Seas Voyager'] if s in line)
                prices = re.findall(price_pattern, line)

                if prices:
                    price_str = prices[0].replace(",", "")
                    try:
                        price = float(price_str)
                        sailings.append({
                            "ship": ship_name,
                            "price_pp": price,
                            "source": "perx",
                            "extracted_from": line[:150],
                        })
                        log.info(f"  Perx: {ship_name} → ${price:,.0f}pp")
                    except ValueError:
                        pass

        results["sailings"] = sailings
        results["status"] = "OK" if sailings else "NO_PRICES"

    except Exception as exc:
        log.error("Perx scrape failed: %s", exc)
        results["status"] = "ERROR"
        results["errors"].append(str(exc))

    return results


# ── Odysseus Scraper ────────────────────────────────────────────────────────

async def scrape_odysseus_norway_pricing(browser) -> Dict[str, Any]:
    """
    Navigate Odysseus/TESS to search for Norway/Scandinavia cruises and extract pricing.
    Requires: Odysseus login session already open in browser.
    """
    results = {"source": "odysseus", "sailings": [], "errors": [], "status": "OK"}

    page = await _find_browser_tab(browser, "odysseus")
    if not page:
        log.warning("No Odysseus tab found in browser")
        results["status"] = "NO_TAB"
        return results

    try:
        log.info("Searching Odysseus for Norway/Scandinavia cruises...")
        # Odysseus search pattern (adjust URL as needed based on actual Odysseus interface)
        await page.goto(
            "https://www.odysseus.travel/search?destination=norway&startDate=2027-07-15&endDate=2027-08-20",
            wait_until="networkidle",
            timeout=60000,
        )
        await asyncio.sleep(3)

        text = await page.evaluate("() => document.body.innerText")

        sailings = []
        price_pattern = r'\$\s*([\d,]+(?:\.\d{2})?)'

        for line in text.split('\n'):
            line = line.strip()
            if any(ship in line for ship in ['Silver Dawn', 'Seabourn Quest', 'Seven Seas Voyager']):
                ship_name = next(s for s in ['Silver Dawn', 'Seabourn Quest', 'Seven Seas Voyager'] if s in line)
                prices = re.findall(price_pattern, line)

                if prices:
                    price_str = prices[0].replace(",", "")
                    try:
                        price = float(price_str)
                        sailings.append({
                            "ship": ship_name,
                            "price_pp": price,
                            "source": "odysseus",
                            "extracted_from": line[:150],
                        })
                        log.info(f"  Odysseus: {ship_name} → ${price:,.0f}pp")
                    except ValueError:
                        pass

        results["sailings"] = sailings
        results["status"] = "OK" if sailings else "NO_PRICES"

    except Exception as exc:
        log.error("Odysseus scrape failed: %s", exc)
        results["status"] = "ERROR"
        results["errors"].append(str(exc))

    return results


# ── CruiseComplete Scraper ──────────────────────────────────────────────────

async def scrape_cruisecomplete_norway_pricing(browser) -> Dict[str, Any]:
    """
    Navigate CruiseComplete to search for Norway/Scandinavia cruises and extract pricing.
    Requires: CruiseComplete login session already open in browser.
    """
    results = {"source": "cruisecomplete", "sailings": [], "errors": [], "status": "OK"}

    page = await _find_browser_tab(browser, "cruisecomplete")
    if not page:
        log.warning("No CruiseComplete tab found in browser")
        results["status"] = "NO_TAB"
        return results

    try:
        log.info("Searching CruiseComplete for Norway/Scandinavia cruises...")
        # CruiseComplete search pattern (adjust as needed)
        await page.goto(
            "https://www.cruisecomplete.travel/search?destination=scandinavia&month=july2027",
            wait_until="networkidle",
            timeout=60000,
        )
        await asyncio.sleep(3)

        text = await page.evaluate("() => document.body.innerText")

        sailings = []
        price_pattern = r'\$\s*([\d,]+(?:\.\d{2})?)'

        for line in text.split('\n'):
            line = line.strip()
            if any(ship in line for ship in ['Silver Dawn', 'Seabourn Quest', 'Seven Seas Voyager']):
                ship_name = next(s for s in ['Silver Dawn', 'Seabourn Quest', 'Seven Seas Voyager'] if s in line)
                prices = re.findall(price_pattern, line)

                if prices:
                    price_str = prices[0].replace(",", "")
                    try:
                        price = float(price_str)
                        sailings.append({
                            "ship": ship_name,
                            "price_pp": price,
                            "source": "cruisecomplete",
                            "extracted_from": line[:150],
                        })
                        log.info(f"  CruiseComplete: {ship_name} → ${price:,.0f}pp")
                    except ValueError:
                        pass

        results["sailings"] = sailings
        results["status"] = "OK" if sailings else "NO_PRICES"

    except Exception as exc:
        log.error("CruiseComplete scrape failed: %s", exc)
        results["status"] = "ERROR"
        results["errors"].append(str(exc))

    return results


# ── Alert Logic ─────────────────────────────────────────────────────────────

def _check_alerts(scraped_results: List[Dict], watch: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Compare scraped prices against watch alert thresholds.
    Returns list of triggered alerts.
    """
    alerts = []
    alert_below = watch.get("alert_below", 9999999)
    alert_above = watch.get("alert_above", 0)
    baseline = watch.get("baseline_price_pp", 10000)

    for result_set in scraped_results:
        for sailing in result_set.get("sailings", []):
            price = sailing.get("price_pp")
            ship = sailing.get("ship", "Unknown")
            source = sailing.get("source", "unknown")

            if price is None:
                continue

            # Check thresholds
            if price < alert_below:
                pct_change = ((price - baseline) / baseline) * 100
                alerts.append({
                    "type": "PRICE_DROP",
                    "ship": ship,
                    "price_pp": price,
                    "baseline": baseline,
                    "change_pct": pct_change,
                    "source": source,
                    "message": f"🚨 PRICE DROP: {ship} at {source.upper()} — ${price:,.0f}pp (baseline ${baseline:,.0f}) — {pct_change:+.1f}%",
                })
                log.warning("ALERT: Price drop detected for %s at %s: $%,.0f", ship, source, price)

            elif price > alert_above:
                pct_change = ((price - baseline) / baseline) * 100
                alerts.append({
                    "type": "PRICE_SPIKE",
                    "ship": ship,
                    "price_pp": price,
                    "baseline": baseline,
                    "change_pct": pct_change,
                    "source": source,
                    "message": f"📈 PRICE SPIKE: {ship} at {source.upper()} — ${price:,.0f}pp (baseline ${baseline:,.0f}) — {pct_change:+.1f}%",
                })
                log.warning("ALERT: Price spike detected for %s at %s: $%,.0f", ship, source, price)

    return alerts


def _build_telegram_message(watch: Dict[str, Any], alerts: List[Dict], results: List[Dict]) -> str:
    """Build formatted Telegram alert message."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M MT")
    lines = [
        f"🚢 <b>CRUISE FARE ALERT — {len(alerts)} triggered</b>",
        f"<i>Watch: {watch.get('label', 'Unknown')}</i>",
        f"<i>{now}</i>",
        "",
    ]

    for alert in alerts:
        lines.append(alert.get("message", str(alert)))

    lines.append("")
    lines.append(f"<i>Scanned: {', '.join(set(r.get('source', 'unknown').upper() for r in results if r.get('sailings')))}</i>")
    lines.append("<i>— A2 Dembe / Hale · Thunderbird Cruise Fare Watch</i>")

    return "\n".join(lines)


# ── Main Scan Runner ────────────────────────────────────────────────────────

async def run_cruise_fare_watch_cycle(watch_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Run complete cruise fare watch scan cycle.
    Connects to Chrome, scrapes all three sources, checks alerts, sends Telegram.
    """
    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "watches_checked": 0,
        "watches_total": 0,
        "alerts": [],
        "errors": [],
        "warnings": [],
        "sources": {"perx": None, "odysseus": None, "cruisecomplete": None},
    }

    # Load target watches
    watches = _load_fare_watches()

    # Filter to cruise watches (and optionally by ID)
    cruise_watches = [w for w in watches if w.get("watch_type") == "cruise" and "norway" in w.get("id", "").lower()]
    if watch_id:
        cruise_watches = [w for w in cruise_watches if w.get("id") == watch_id]

    if not cruise_watches:
        result["warnings"].append("No cruise watches matching criteria (norway-scandinavia-* required)")
        return result

    result["watches_total"] = len(cruise_watches)

    # Connect to Chrome
    browser = await _connect_chrome_cdp()
    if not browser:
        result["errors"].append("Failed to connect to Chrome CDP (port 9222)")
        log.error("Chrome CDP connection failed — is port 9222 open?")
        return result

    try:
        # Scrape all three sources in parallel
        log.info("Starting concurrent scrapes from Perx, Odysseus, CruiseComplete...")

        perx_results = await scrape_perx_norway_pricing(browser)
        odysseus_results = await scrape_odysseus_norway_pricing(browser)
        cruisecomplete_results = await scrape_cruisecomplete_norway_pricing(browser)

        result["sources"]["perx"] = perx_results.get("status")
        result["sources"]["odysseus"] = odysseus_results.get("status")
        result["sources"]["cruisecomplete"] = cruisecomplete_results.get("status")

        scraped_results = [perx_results, odysseus_results, cruisecomplete_results]

        # Check each watch against scraped prices
        for watch in cruise_watches:
            watch_id = watch.get("id")
            log.info("Checking watch: %s", watch_id)

            alerts = _check_alerts(scraped_results, watch)

            if alerts:
                result["alerts"].extend([{
                    "watch_id": watch_id,
                    "label": watch.get("label"),
                    **alert
                } for alert in alerts])

                # Send Telegram alert
                token = _load_telegram_token()
                if token:
                    msg = _build_telegram_message(watch, alerts, scraped_results)
                    sent = _send_telegram(token, msg)
                    log.info("Telegram alert sent: %s", sent)
                else:
                    log.warning("No TELEGRAM_D2MC2C_TOKEN — alerts logged only")

            result["watches_checked"] += 1

        # Log any source-specific errors
        for source, src_results in {"perx": perx_results, "odysseus": odysseus_results, "cruisecomplete": cruisecomplete_results}.items():
            if src_results.get("errors"):
                for err in src_results["errors"]:
                    result["errors"].append(f"{source}: {err}")

    finally:
        # Clean up
        try:
            if browser:
                await browser.close()
        except Exception:
            pass

    # Save results
    _save_last_check(result)

    return result


# ── CLI Interface ────────────────────────────────────────────────────────────

async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Cruise Fare Watch Scanner")
    parser.add_argument("--watch-id", help="Specific watch ID to check")
    parser.add_argument("--list", action="store_true", help="List all cruise watches")
    parser.add_argument("--source", choices=["perx", "odysseus", "cruisecomplete"], help="Test specific source only")
    args = parser.parse_args()

    if args.list:
        watches = _load_fare_watches()
        cruise_watches = [w for w in watches if w.get("watch_type") == "cruise"]
        for w in cruise_watches:
            print(f"  {w['id']:40s}  {w['label']}")
        return

    log.info("Cruise fare watch cycle starting")
    result = await run_cruise_fare_watch_cycle(watch_id=args.watch_id)

    # Print summary
    print(json.dumps(result, indent=2, default=str))

    ok = result.get("watches_checked", 0)
    total = result.get("watches_total", 0)
    n_alerts = len(result.get("alerts", []))
    n_errors = len(result.get("errors", []))

    log.info(
        "Cycle complete: %d/%d checked, %d alert(s), %d error(s)",
        ok, total, n_alerts, n_errors,
    )

    if n_errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
