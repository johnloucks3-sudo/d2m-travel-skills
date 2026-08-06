#!/usr/bin/env python3
"""
Daily Airfare Scan — Master Pipeline
=====================================
Dreams2Memories Travel, LLC · Commander directive 2026-06-28

Runs at 03:00 MT every day.  Scans all watched flight routes across
multiple sources and regenerates the airfare dashboard.

Install (crontab -e):
  0 3 * * * cd /home/john/Thunderbird && .venv/bin/python scripts/daily_airfare_scan.py >> logs/daily_airfare_scan.log 2>&1

Sources (THE TWO ENGINES — Commander directive 2026-08-06):
  - Centrav B2B (via thunderbird_centrav_search — rides the bsk-tab live session)
  - Skybird Travel WINGS (via skybird_scan — headless GDS Sabre, no browser)

Exit codes:
  0 = all sources OK
  1 = partial failure (some sources failed)
  2 = total failure (all sources failed)

Flags:
  --source centrav | skybird  — run single source only
  --dry-run                   — log what would be done, don't execute
  --verbose                   — debug logging
"""

import argparse
import asyncio
import json
import logging
import os
import signal
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Ensure core/travel is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "core" / "travel"))

logger = logging.getLogger("daily_airfare_scan")

# ── Paths ─────────────────────────────────────────────────────────────────────

THUNDERBIRD = Path(__file__).resolve().parent.parent
WATCHES_FILE = THUNDERBIRD / "core" / "travel" / "data" / "fare_watches.json"
LOGS_DIR = THUNDERBIRD / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR = THUNDERBIRD / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DASHBOARD_FILE = OUTPUT_DIR / "airfare_dashboard.html"

# ── Import pipeline modules ───────────────────────────────────────────────────

def _import_modules():
    """Lazy-import pipeline modules. Returns (fare_logger, kayak, google, centrav)."""
    from core.travel import fare_watch_logger
    from core.travel import kayak_scraper
    from core.travel import thunderbird_google_flights_search as google_flights_mod
    import importlib
    centrav = importlib.import_module("core.travel.thunderbird_centrav_search")
    return fare_watch_logger, kayak_scraper, google_flights_mod, centrav


def _load_watches() -> list[dict]:
    """Load active flight fare watches from JSON."""
    if not WATCHES_FILE.exists():
        logger.warning("Watches file not found: %s", WATCHES_FILE)
        return []

    try:
        data = json.loads(WATCHES_FILE.read_text())
        watches = []
        for wid, w in data.items():
            if isinstance(w, dict) and w.get("watch_type") == "flight" and w.get("active", True):
                w["id"] = wid
                watches.append(w)
        logger.info("Loaded %d active flight watches", len(watches))
        return watches
    except (json.JSONDecodeError, Exception) as exc:
        logger.error("Failed to load watches: %s", exc)
        return []


def _kill_playwright():
    """Kill any remaining Playwright node processes to prevent hangs."""
    try:
        result = subprocess.run(
            ["pkill", "-f", "playwright/driver"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            logger.info("  cleaned %s playwright processes", result.stdout.strip())
    except subprocess.TimeoutExpired:
        pass
    except Exception:
        pass


def _parse_route(route: str) -> tuple[Optional[str], Optional[str]]:
    """Extract origin and dest IATA codes from route string."""
    import re
    codes = re.findall(r"[A-Z]{3}", route.upper())
    if len(codes) >= 2:
        return codes[0], codes[1]
    return None, None


def _infer_cabin(watch: dict) -> str:
    """Infer cabin class from watch label/notes. Defaults to economy."""
    label = (watch.get("label", "") + " " + watch.get("notes", "")).lower()
    if "business" in label or "business" in watch.get("cabin", ""):
        return "business"
    if "premium" in label:
        return "premium"
    if "first" in label:
        return "first"
    return watch.get("cabin", "economy")


# Plausibility floor per cabin (per-passenger, USD) — real bug found 2026-07-07:
# Kayak returned "business class" DEN->VCE / ATH->DEN at $199-$681/pp (a real
# international business fare is $2,000+) and the naive min() below let that
# garbage number silently overwrite Centrav's real $2,719-$2,801/pp price in
# fare_watches.json's current_price_pp -- Commander caught this from the
# client-facing data ("BS data in here") before the Wing did. These floors
# are deliberately conservative (well under the cheapest real fare anyone
# would see) -- the goal is only to catch obvious scraper garbage, not to
# second-guess a genuinely cheap real fare.
CABIN_PRICE_FLOOR_PP = {
    "economy": 80.0,
    "premium": 400.0,
    "business": 900.0,
    "first": 1800.0,
}


def _is_plausible_price(price_pp: float, cabin: str) -> bool:
    floor = CABIN_PRICE_FLOOR_PP.get(cabin, CABIN_PRICE_FLOOR_PP["economy"])
    return price_pp >= floor


# ── Source runners ────────────────────────────────────────────────────────────

_AMADEUS_DEAD_LOGGED = False  # module-level: log the fast-fail notice once per run, not once per route


async def _scan_amadeus(watch: dict, adults: int) -> Optional[dict]:
    """Amadeus Self-Service API PERMANENTLY RETIRED 2026-07-17 (confirmed:
    test.api.amadeus.com / api.amadeus.com no longer resolve in public DNS,
    traced to Amadeus's own authoritative nameservers; independently verified
    against tripgic.com's migration-guide page, real schema.org metadata,
    published 2026-06-04 — "the Amadeus self-service API portal shuts down on
    July 17, 2026"). This is external and permanent, not a local bug — do not
    remove this function (Enterprise API access may restore it later), but
    fast-fail with a short timeout instead of waiting out a full connect
    timeout on every one of 19 routes, every night, forever.

    2026-07-16 fix (superseded by the above, kept for when Amadeus access
    returns): the prior version imported core.travel.amadeus_search, a module
    that never existed — every run silently skipped Amadeus and fell back to
    session-gated Centrav + browser scrapers. Fixed to call the real REST
    logic thunderbird_flight_search.py's MCP tool uses directly."""
    global _AMADEUS_DEAD_LOGGED
    if not watch.get("travel_date"):
        logger.debug("amadeus: no travel_date for %s — skipping", watch.get("id"))
        return None
    try:
        from thunderbird_flight_search import AmadeusConfig, _auth_headers, _format_flight_offers
        import requests as _requests
    except ImportError as exc:
        logger.warning("thunderbird_flight_search not available — skipping Amadeus: %s", exc)
        return None

    if not _AMADEUS_DEAD_LOGGED:
        logger.warning(
            "amadeus: Self-Service API retired by Amadeus 2026-07-17 (confirmed "
            "DNS + vendor docs) — attempting anyway with a short timeout in "
            "case Enterprise access has since been provisioned; expect failures"
        )
        _AMADEUS_DEAD_LOGGED = True

    origin, dest = _parse_route(watch.get("route", ""))
    if not origin or not dest:
        logger.warning("amadeus: cannot parse route %s", watch.get("route"))
        return None

    try:
        params = {
            "originLocationCode": origin,
            "destinationLocationCode": dest,
            "departureDate": watch.get("travel_date", ""),
            "adults": min(adults, 9),
            "max": 10,
            "currencyCode": "USD",
            "travelClass": _infer_cabin(watch).upper(),
        }
        resp = _requests.get(
            f"{AmadeusConfig.BASE_URL}/v2/shopping/flight-offers",
            headers=_auth_headers(), params=params, timeout=8,  # fast-fail: host is retired
        )
        if resp.status_code != 200:
            logger.warning("amadeus: %s for %s — %s", resp.status_code, watch.get("id"), resp.text[:200])
            return {"best_price_pp": None, "airline": None, "raw": {"status": resp.status_code}}

        formatted = _format_flight_offers(resp.json())
        offers = formatted.get("offers", [])
        if not offers:
            return {"best_price_pp": None, "airline": None, "raw": formatted}
        best = min(offers, key=lambda o: o.get("price", {}).get("total_raw", float("inf")))
        first_seg = (best.get("itineraries", [{}])[0].get("segments", [{}])[0])
        return {
            "best_price_pp": round(best["price"]["total_raw"] / max(adults, 1), 2),
            "airline": first_seg.get("carrier") or best.get("validating_carrier"),
            "raw": formatted,
        }
    except Exception as exc:
        logger.warning("amadeus: error for %s: %s", watch.get("id"), exc)
        return None


async def _scan_centrav(watch: dict, centrav_mod) -> Optional[dict]:
    """Run Centrav B2B search."""
    if not watch.get("travel_date"):
        logger.debug("centrav: no travel_date for %s — skipping", watch.get("id"))
        return None
    origin, dest = _parse_route(watch.get("route", ""))
    if not origin or not dest:
        return None

    try:
        result = await centrav_mod.run_centrav_search(
            origin=origin,
            dest=dest,
            depart_date=watch.get("travel_date", ""),
            adults=watch.get("passengers", 2),
            cabins=[_infer_cabin(watch)],
        )
        cabin_data = result.get("results", {}).get(_infer_cabin(watch), {})
        if cabin_data and cabin_data.get("status") == "ok":
            return {
                "best_price_pp": cabin_data.get("lowest_pp"),
                "airline": (cabin_data.get("airlines") or [None])[0],
                "raw": result,
            }
        if result.get("auth_status") == "session_expired":
            logger.warning("centrav: auth expired for %s — continuing", watch.get("id"))
        return {"best_price_pp": None, "airline": None, "raw": result}
    except Exception as exc:
        logger.warning("centrav: error for %s: %s", watch.get("id"), exc)
        return None


async def _scan_skybird(watch: dict) -> Optional[dict]:
    """Run Skybird Travel WINGS (GDS Sabre B2B) headless scan.

    Headless, requests-only — no browser, no CAPTCHA. One login + one search
    per route. Multi-city watches use the semicolon ';' legs syntax.
    """
    if not watch.get("travel_date"):
        logger.debug("skybird: no travel_date for %s — skipping", watch.get("id"))
        return None
    origin, dest = _parse_route(watch.get("route", ""))
    if not origin or not dest:
        return None

    try:
        sys.path.insert(0, str(THUNDERBIRD / "scripts"))
        import skybird_scan as sk

        ret = watch.get("return_date", "")
        cabin = _infer_cabin(watch).title()
        adults = watch.get("passengers", 2)
        legs = None
        if ";" in watch.get("route", ""):
            legs = []
            for leg in watch["route"].split(";"):
                codes = [x for x in leg.strip().upper().split() if len(x) == 3]
                if len(codes) >= 2:
                    legs.append({"from": codes[0], "to": codes[1],
                                 "date": watch.get("travel_date", "")})
        s = sk.login()
        flights = sk.search(s, origin, dest, watch.get("travel_date", ""),
                            ret, cabin, adults=adults, legs=legs, limit=10)
        if not flights:
            return {"best_price_pp": None, "airline": None, "raw": {"flights": []}}
        prices = [f.get("price_pp") for f in flights if f.get("price_pp")]
        best = min(prices) if prices else None
        best_flight = next((f for f in flights if f.get("price_pp") == best), flights[0])
        return {
            "best_price_pp": best,
            "airline": best_flight.get("airline"),
            "raw": {"flights": flights[:10], "count": len(flights)},
        }
    except Exception as exc:
        logger.warning("skybird: error for %s: %s", watch.get("id"), exc)
        return None


async def _scan_kayak(watch: dict, kayak_mod) -> Optional[dict]:
    """Run Kayak consumer price check."""
    if not watch.get("travel_date"):
        logger.debug("kayak: no travel_date for %s — skipping", watch.get("id"))
        return None
    origin, dest = _parse_route(watch.get("route", ""))
    if not origin or not dest:
        return None

    try:
        result = await kayak_mod.search_kayak(
            origin=origin,
            dest=dest,
            depart_date=watch.get("travel_date", ""),
            adults=watch.get("passengers", 2),
            cabin=_infer_cabin(watch),
        )
        if result.get("status") == "ok":
            return {
                "best_price_pp": result.get("lowest_price"),
                "airline": (result.get("airlines") or [None])[0],
                "raw": result,
            }
        return {"best_price_pp": None, "airline": None, "raw": result}
    except Exception as exc:
        logger.warning("kayak: error for %s: %s", watch.get("id"), exc)
        return None


async def _scan_google(watch: dict, google_mod) -> Optional[dict]:
    """Run Google Flights price check via RapidAPI (sync wrapped in thread)."""
    if not watch.get("travel_date"):
        logger.debug("google: no travel_date for %s — skipping", watch.get("id"))
        return None
    origin, dest = _parse_route(watch.get("route", ""))
    if not origin or not dest:
        return None

    try:
        result = await asyncio.to_thread(
            google_mod.search_flights,
            departure_id=origin,
            arrival_id=dest,
            outbound_date=watch.get("travel_date", ""),
            adults=watch.get("passengers", 2),
            travel_class={"economy": "ECONOMY", "premium": "PREMIUM_ECONOMY", "business": "BUSINESS", "first": "FIRST"}.get(_infer_cabin(watch), "ECONOMY"),
        )
        cheapest = google_mod.cheapest_itinerary(result)
        if cheapest:
            segs = cheapest.get("flights", [])
            price = cheapest.get("price")
            airline = segs[0].get("airline") if segs else None
            return {
                "best_price_pp": price,
                "airline": airline,
                "raw": {
                    "cheapest": cheapest,
                    "top_count": len(result.get("data", {}).get("itineraries", {}).get("topFlights", [])),
                },
            }
        return {"best_price_pp": None, "airline": None, "raw": result}
    except Exception as exc:
        logger.warning("google_flights: error for %s: %s", watch.get("id"), exc)
        return None


# ── Dashboard generator ───────────────────────────────────────────────────────

def _generate_dashboard(all_results: list[dict]):
    """Regenerate the HTML dashboard with latest scan data."""
    import shutil

    template = DASHBOARD_FILE
    if not template.exists():
        logger.error("Dashboard template not found at %s — cannot regenerate", template)
        return

    # Build JSON data block for dashboard
    watches_json = []
    for r in all_results:
        watch = r.get("watch", {})
        prices = r.get("prices", {})
        centrav_ok = r.get("centrav_ok", False)

        watch_entry = {
            "watch_id": watch.get("id", ""),
            "route": watch.get("route", ""),
            "source": prices.get("source", ""),
            "cabin": prices.get("cabin", _infer_cabin(watch)),
            "best_price_pp": prices.get("best_price_pp"),
            "baseline_price_pp": watch.get("baseline_price_pp", 0),
            "duration_min": prices.get("duration_min"),
            "airline": prices.get("airline"),
            "stops": prices.get("stops"),
            "travel_date": watch.get("travel_date", ""),
            "url": prices.get("url", ""),
            "centrav_url": r.get("centrav_url", ""),
            "centrav_ok": centrav_ok,
            "price_history": prices.get("history", []),
        }
        watches_json.append(watch_entry)

    dashboard_data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_as_of": datetime.now(timezone.utc).isoformat(),
        "watches": watches_json,
    }

    # Read existing HTML, inject JSON
    html = template.read_text(encoding="utf-8")
    import re

    # Replace the DASHBOARD_DATA assignment
    new_assign = "const DASHBOARD_DATA = " + json.dumps(dashboard_data, indent=2, default=str, ensure_ascii=False) + ";"
    html = re.sub(
        r"const DASHBOARD_DATA\s*=\s*\{[^;]*\};",
        new_assign,
        html,
        flags=re.DOTALL,
    )

    DASHBOARD_FILE.write_text(html, encoding="utf-8")
    logger.info("Dashboard regenerated → %s", DASHBOARD_FILE)


# ── Pipeline ──────────────────────────────────────────────────────────────────

async def run_pipeline(source_filter: Optional[str] = None, dry_run: bool = False) -> int:
    """Execute the daily airfare scan pipeline.

    Returns exit code: 0=all ok, 1=partial, 2=total failure.
    """
    logger.info("=" * 60)
    logger.info("DAILY AIRFARE SCAN — %s", datetime.now().isoformat())
    logger.info("=" * 60)

    # Check if running headless
    is_headless = not sys.stdin.isatty()
    logger.info("Environment: %s", "headless (cron)" if is_headless else "interactive")

    # Import modules
    try:
        fare_logger, kayak_mod, google_mod, centrav_mod = _import_modules()
        from core.intel.thunderbird_intel_telegram import send_telegram
    except Exception as exc:
        logger.error("Failed to import pipeline modules: %s", exc)
        return 2

    # Load watches
    watches = _load_watches()
    if not watches:
        logger.warning("No active flight watches found")
        return 0

    # Filter by source if specified. Skybird = TOP CI, sole default (Commander
    # directive 2026-08-06: "Skybird is the #1 choice. Use for all fare scans").
    # Fully headless (GDS Sabre), proven one-way/RT/multi-city. Centrav remains
    # available via --source centrav for deliberate read-only cross-checks.
    sources = ["skybird"]
    if source_filter:
        if source_filter not in sources:
            logger.error("Unknown source: %s (choose: %s)", source_filter, ", ".join(sources))
            return 2
        sources = [source_filter]

    all_results = []
    alerts = []
    total_watches = len(watches)
    ok_count = 0
    error_count = 0

    for watch in watches:
        wid = watch.get("id", "unknown")
        wid = watch.get("id", "unknown")
        route = watch.get("route", "")
        logger.info("── Scanning %s (%s) ──", wid, route)

        watch_result = {
            "watch": watch,
            "prices": {},
            "centrav_ok": False,
            "centrav_url": None,
            "errors": [],
        }

        # Run each source in parallel for this watch
        tasks = {}

        if dry_run:
            logger.info("  [dry-run] Would scan %s across %d sources", wid, len(sources))
            continue

        if "centrav" in sources:
            tasks["centrav"] = _scan_centrav(watch, centrav_mod)
        if "skybird" in sources:
            tasks["skybird"] = _scan_skybird(watch)

        results = {}
        if tasks:
            for src, task in tasks.items():
                try:
                    results[src] = await asyncio.wait_for(task, timeout=120)
                except asyncio.TimeoutError:
                    logger.warning("  ⏱ %s timed out after 120s for %s", src, wid)
                    results[src] = {"best_price_pp": None, "airline": None, "error": "timeout"}
                    _kill_playwright()
                except Exception as exc:
                    results[src] = {"best_price_pp": None, "airline": None, "error": str(exc)}

        # Process results
        best_price_pp = None
        best_source = None
        best_airline = None
        cabin = _infer_cabin(watch)
        rejected_implausible = []

        for src, data in results.items():
            if data and data.get("best_price_pp") is not None:
                pp = data["best_price_pp"]
                if not _is_plausible_price(pp, cabin):
                    rejected_implausible.append((src, pp))
                    logger.warning(
                        "  ⚠ REJECTED implausible %s price from %s for %s: $%s/pp "
                        "(floor for %s is $%s/pp) — scraper bug, not a real fare",
                        cabin, src, wid, pp, cabin, CABIN_PRICE_FLOOR_PP.get(cabin),
                    )
                    continue
                if best_price_pp is None or pp < best_price_pp:
                    best_price_pp = pp
                    best_source = src
                    best_airline = data.get("airline")

        if rejected_implausible:
            watch_result["rejected_implausible_prices"] = rejected_implausible

            # Log to history
            try:
                fare_logger.log_fare_scan(
                    watch_id=f"{wid}-{src}",
                    route=route,
                    source=src,
                    cabin=_infer_cabin(watch),
                    best_price_pp=data.get("best_price_pp") if data else None,
                    airline=data.get("airline") if data else None,
                    travel_date=watch.get("travel_date"),
                    passengers=watch.get("passengers", 2),
                )
            except Exception as exc:
                logger.warning("  fare_log error: %s", exc)

            # Track Centrav status
            if src == "centrav" and data:
                raw = data.get("raw", {})
                watch_result["centrav_ok"] = raw.get("auth_status") == "authenticated"
                watch_result["centrav_url"] = "https://www.centrav.com/"

        if best_price_pp is not None:
            ok_count += 1
            logger.info("  ✓ Best: $%s/pp from %s (%s)", best_price_pp, best_source, best_airline or "?")

            # Threshold crossing check
            try:
                alert_below = watch.get("alert_below")
                alert_above = watch.get("alert_above")
                if alert_below and best_price_pp <= alert_below:
                    msg = f"PRICE DROP: {wid} — ${best_price_pp:.0f}/pp (below ${alert_below:.0f})"
                    alerts.append(msg)
                    logger.info("  🚨 %s", msg)
                elif alert_above and best_price_pp >= alert_above:
                    msg = f"PRICE RISE: {wid} — ${best_price_pp:.0f}/pp (above ${alert_above:.0f})"
                    alerts.append(msg)
                    logger.info("  🚨 %s", msg)
            except Exception as exc:
                logger.debug("threshold check error: %s", exc)
        else:
            error_count += 1
            logger.warning("  ✗ No prices found for %s", wid)

        watch_result["prices"] = {
            "best_price_pp": best_price_pp,
            "source": best_source,
            "airline": best_airline,
            "cabin": _infer_cabin(watch),
        }
        all_results.append(watch_result)

    # Summary
    scanned = ok_count + error_count
    logger.info("=" * 60)
    logger.info("SCAN COMPLETE: %d/%d OK, %d errors", ok_count, scanned, error_count)
    logger.info("=" * 60)

    # Generate dashboard (even if partial failures)
    if not dry_run and all_results:
        try:
            _generate_dashboard(all_results)
        except Exception as exc:
            logger.error("Dashboard generation failed: %s", exc)

    # Telegram summary
    if not dry_run:
        try:
            scanned = ok_count + error_count
            # Build summary in chunks (Telegram 4096 limit)
            lines = [f"✈️ Airfare Scan — {datetime.now().strftime('%b %d')}"]
            lines.append(f"{ok_count}/{scanned} OK, {error_count} errors")
            if alerts:
                lines.append("")
                lines.append("🚨 ALERTS:")
                lines.extend(alerts[:5])
                if len(alerts) > 5:
                    lines.append(f"... and {len(alerts)-5} more")
            if ok_count > 0:
                lines.append("")
                # Best deals: top 5 cheapest
                priced = [(r["prices"]["best_price_pp"], r["watch"].get("route","")) for r in all_results if r["prices"].get("best_price_pp")]
                priced.sort()
                lines.append("Best deals:")
                for pp, rt in priced[:5]:
                    lines.append(f"  ${pp:.0f}  {rt}")
            msg = "\n".join(lines)
            send_telegram(msg, parse_mode="HTML")
        except Exception as exc:
            logger.warning("Telegram summary failed: %s", exc)

    # Exit code
    if error_count == 0 and ok_count > 0:
        return 0
    elif ok_count > 0:
        return 1  # partial
    else:
        return 2  # total


def _cleanup():
    """One-time cleanup: kill any lingering Playwright processes."""
    _kill_playwright()
    logger.info("Playwright processes cleaned up")


def main():
    parser = argparse.ArgumentParser(
        description="Daily Airfare Scan Pipeline — 03:00 MT cron job"
    )
    parser.add_argument(
        "--source",
        choices=["centrav", "skybird"],
        help="Run a single source only (default: all)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Log what would be done")
    parser.add_argument("--verbose", action="store_true", help="Debug logging")
    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    exit_code = asyncio.run(
        asyncio.wait_for(
            run_pipeline(source_filter=args.source, dry_run=args.dry_run),
            timeout=1800,
        )
    )

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
