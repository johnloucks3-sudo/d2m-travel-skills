#!/usr/bin/env python3
"""
fare_watch_amadeus.py — Amadeus-powered flight fare monitor.

Replaces Centrav for all fare monitoring/trendline work. No browser, no cookies,
no daily re-auth. OAuth token auto-refreshes every call.

Centrav stays for: actual B2B group booking, net fares, beyond retail search windows.
Amadeus is for: trendlines, approximate fares, alerts, daily automated monitoring.

Routes pulled from: core/travel/data/fare_watches.json (same config Centrav uses)
Results written to: OpsCenter/fare_watches/last_check_amadeus.json
History appended to: OpsCenter/fare_watches/amadeus_history.json
Alerts: Telegram D2MC2C_bot → Commander

Usage:
  .venv/bin/python scripts/fare_watch_amadeus.py
  .venv/bin/python scripts/fare_watch_amadeus.py --dry-run
  .venv/bin/python scripts/fare_watch_amadeus.py --watch-id kuklinski-flights-ric-pty

Dreams2Memories Travel, LLC · Thunderbird Wing · 2026-07-02
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("fare_watch_amadeus")

# ── paths ──────────────────────────────────────────────────────────────────────
ENV_FILE = ROOT / ".env"
WATCHES_FILE = ROOT / "core" / "travel" / "data" / "fare_watches.json"
OUT_FILE = ROOT / "OpsCenter" / "fare_watches" / "last_check_amadeus.json"
HISTORY_FILE = ROOT / "OpsCenter" / "fare_watches" / "amadeus_history.json"
COMMANDER_ID = 7554895206

# ── Amadeus endpoints ──────────────────────────────────────────────────────────
AMADEUS_TOKEN_URL = "https://test.api.amadeus.com/v1/security/oauth2/token"
AMADEUS_OFFERS_URL = "https://test.api.amadeus.com/v2/shopping/flight-offers"


def _load_env() -> dict:
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
    env.update(os.environ)
    return env


def _get_amadeus_token(env: dict) -> str:
    client_id = env.get("AMADEUS_CLIENT_ID") or env.get("AMADEUS_API_KEY", "")
    client_secret = env.get("AMADEUS_CLIENT_SECRET", "")
    r = requests.post(
        AMADEUS_TOKEN_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data=f"grant_type=client_credentials&client_id={client_id}&client_secret={client_secret}",
        timeout=15,
    )
    r.raise_for_status()
    token = r.json().get("access_token")
    if not token:
        raise RuntimeError(f"Amadeus token failed: {r.text[:200]}")
    return token


def _tg_send(token: str, text: str) -> None:
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": COMMANDER_ID, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception as e:
        log.warning("Telegram send failed: %s", e)


def _search_flights(token: str, origin: str, dest: str, date: str, adults: int, cabin: str = "ECONOMY") -> dict:
    """Search Amadeus for flight offers. Returns lowest price and full result."""
    params = {
        "originLocationCode": origin,
        "destinationLocationCode": dest,
        "departureDate": date,
        "adults": adults,
        "max": 10,
        "currencyCode": "USD",
        "travelClass": cabin.upper(),
    }
    r = requests.get(
        AMADEUS_OFFERS_URL,
        headers={"Authorization": f"Bearer {token}"},
        params=params,
        timeout=20,
    )
    if r.status_code == 401:
        raise RuntimeError("Amadeus token expired mid-run")
    data = r.json()
    offers = data.get("data", [])
    if not offers:
        return {"status": "no_results", "origin": origin, "dest": dest, "date": date}

    prices = sorted(float(o["price"]["total"]) for o in offers)
    carriers = list({
        o["itineraries"][0]["segments"][0]["carrierCode"]
        for o in offers[:3]
    })

    return {
        "status": "ok",
        "origin": origin,
        "dest": dest,
        "date": date,
        "cabin": cabin,
        "adults": adults,
        "lowest_pp": round(prices[0] / adults, 2),
        "lowest_total": round(prices[0], 2),
        "highest_pp": round(prices[-1] / adults, 2),
        "carriers": carriers,
        "offer_count": len(offers),
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def _extract_flight_watches(watches_data: dict) -> list:
    """Pull flight-type watches from fare_watches.json config."""
    from datetime import date as date_type
    today = datetime.now(timezone.utc).date().isoformat()

    watches = watches_data if isinstance(watches_data, dict) else {}
    flight_watches = []
    for watch_id, w in watches.items():
        if w.get("watch_type") != "flight":
            continue
        if not w.get("active", True):
            continue

        # Parse route: "RIC → PTY" or "RIC->PTY"
        route = w.get("route", "")
        route_clean = route.replace("→", "->").replace(" ", "")
        parts = route_clean.split("->")
        origin = parts[0][:3].upper() if parts else None
        dest = parts[1][:3].upper() if len(parts) > 1 else None

        travel_date = w.get("travel_date") or w.get("date")

        # Skip past dates
        if travel_date and travel_date < today:
            log.debug("Skipping past watch %s (%s)", watch_id, travel_date)
            continue

        if not (origin and dest and travel_date):
            log.warning("Watch %s missing origin/dest/date — skipping", watch_id)
            continue

        flight_watches.append({
            "id": watch_id,
            "label": w.get("label", watch_id),
            "origin": origin,
            "dest": dest,
            "date": travel_date,
            "passengers": w.get("passengers", 2),
            "cabin": w.get("cabin", "economy"),
            "alert_threshold": w.get("alert_below"),
            "alert_above": w.get("alert_above"),
            "baseline_pp": w.get("baseline_price_pp") or w.get("current_price_pp"),
        })
    return flight_watches


def run(dry_run: bool = False, filter_id: str | None = None) -> dict:
    env = _load_env()
    tg_token = env.get("TELEGRAM_D2MC2C_TOKEN", "")

    log.info("Loading Amadeus token…")
    token = _get_amadeus_token(env)
    log.info("Token OK")

    watches_raw = json.loads(WATCHES_FILE.read_text()) if WATCHES_FILE.exists() else {}
    flight_watches = _extract_flight_watches(watches_raw)

    if filter_id:
        flight_watches = [w for w in flight_watches if w["id"] == filter_id]

    log.info("Running %d flight watches via Amadeus", len(flight_watches))

    results = {}
    alerts = []
    errors = []

    for w in flight_watches:
        wid = w["id"]
        log.info("Checking %s (%s→%s %s)…", wid, w["origin"], w["dest"], w["date"])
        try:
            result = _search_flights(
                token, w["origin"], w["dest"], w["date"],
                adults=w["passengers"], cabin=w["cabin"]
            )
            result["watch_id"] = wid
            result["label"] = w["label"]
            result["baseline_pp"] = w.get("baseline_pp")
            results[wid] = result

            lowest = result.get("lowest_pp", 0)
            threshold = w.get("alert_threshold")
            if threshold and lowest and lowest < threshold:
                msg = f"✈️ FARE DROP — {w['label']}\n{w['origin']}→{w['dest']} {w['date']}\n${lowest:.0f}/pp (threshold: ${threshold})"
                alerts.append(msg)
                log.info("ALERT: %s", msg)
                if not dry_run and tg_token:
                    _tg_send(tg_token, msg)
        except Exception as e:
            log.error("Watch %s failed: %s", wid, e)
            errors.append({"watch_id": wid, "error": str(e)})
            results[wid] = {"status": "error", "error": str(e), "watch_id": wid}

        time.sleep(0.4)  # gentle rate limiting

    summary = {
        "status": "complete",
        "provider": "amadeus",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "watches_total": len(flight_watches),
        "watches_ok": sum(1 for r in results.values() if r.get("status") == "ok"),
        "watches_error": len(errors),
        "alerts_fired": len(alerts),
        "results": results,
        "errors": errors,
    }

    if not dry_run:
        OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        OUT_FILE.write_text(json.dumps(summary, indent=2))
        log.info("Results → %s", OUT_FILE)

        # Append to history for trendlines
        history = []
        if HISTORY_FILE.exists():
            try:
                history = json.loads(HISTORY_FILE.read_text())
            except Exception:
                history = []
        history.append({
            "ts": summary["started_at"],
            "results": {k: {"lowest_pp": v.get("lowest_pp"), "carriers": v.get("carriers")}
                       for k, v in results.items() if v.get("status") == "ok"}
        })
        # Keep 90 days of history (90 daily runs)
        history = history[-90:]
        HISTORY_FILE.write_text(json.dumps(history, indent=2))
        log.info("History updated (%d snapshots)", len(history))

    # Print summary
    print(f"\n{'DRY RUN — ' if dry_run else ''}AMADEUS FARE WATCH RESULTS")
    print(f"{'─'*55}")
    for wid, r in results.items():
        if r.get("status") == "ok":
            print(f"  {r['label'][:40]:<40} ${r['lowest_pp']:>7.0f}/pp  {r['origin']}→{r['dest']}")
        else:
            print(f"  {wid:<40} ERROR: {r.get('error','?')[:40]}")
    print(f"{'─'*55}")
    print(f"  {summary['watches_ok']}/{summary['watches_total']} OK  |  {summary['alerts_fired']} alerts  |  {summary['watches_error']} errors")

    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--watch-id", help="Run a single watch by ID")
    args = parser.parse_args()
    try:
        run(dry_run=args.dry_run, filter_id=args.watch_id)
    except requests.exceptions.ConnectionError as e:
        # Amadeus test API is intermittently unreliable (connection reset).
        # Exit 0 so systemd does not fire OnFailure and cascade into an alert storm.
        # The timer will retry on the next scheduled run.
        log.warning("Amadeus API unreachable — soft-skipping this run: %s", e)
        sys.exit(0)
