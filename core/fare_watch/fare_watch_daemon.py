#!/usr/bin/env python3
"""
fare_watch_daemon.py — Thunderbird Fare Watch Cron Daemon
==========================================================
Reads all active watches from SQLite, attempts live price lookup,
logs to fare_history, and prints alerts for threshold crossings.

Cron install:
    0 8 * * * /home/john/Thunderbird/.venv/bin/python3 \
              /home/john/Thunderbird/core/fare_watch/fare_watch_daemon.py \
              >> /home/john/Thunderbird/logs/fare_watch_daemon.log 2>&1

Usage:
    python3 fare_watch_daemon.py           # normal run
    python3 fare_watch_daemon.py --dry-run # read-only, no DB writes

Architecture:
    1. init_db() — ensure schema exists
    2. list_active() — pull all active/triggered watches
    3. For each watch:
       a. Attempt live price via flight-price skill (Centrav) for flights
       b. Cruise / hotel: log TOOL UNAVAILABLE — manual check needed
       c. update_fare() — write to DB (unless --dry-run)
    4. Print alert summary

Dependency: core/fare_watch/fare_watch_db.py (SQLite layer)
Caller:     cron / systemd timer
Alerts:     stdout (cron mails root); Telegram hook is optional extension
"""

import argparse
import json
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# ── path bootstrap ────────────────────────────────────────────────────────────
THUNDERBIRD = Path.home() / "Thunderbird"
sys.path.insert(0, str(THUNDERBIRD))

from core.fare_watch.fare_watch_db import (
    init_db,
    list_active,
    update_fare,
    get_alerts,
    summary_stats,
    migrate_from_json,
)

# ── logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("fare_daemon")

# ── constants ─────────────────────────────────────────────────────────────────
CENTRAV_SCRIPT = THUNDERBIRD / "scripts" / "centrav_flights.py"
VENV_PYTHON = THUNDERBIRD / ".venv" / "bin" / "python3"

# M-091: Schema-validated price intel for cruise lookups
try:
    from core.ai_infra.schema_price_intel import SchemaPriceAgent

    _SCHEMA_AGENT = SchemaPriceAgent(model="claude-haiku-4-5-20251001", timeout=30)
    _SCHEMA_AVAILABLE = True
except ImportError:
    _SCHEMA_AGENT = None
    _SCHEMA_AVAILABLE = False
    log.warning("SchemaPriceAgent not available — cruise price lookup disabled")


# ============================================================================
# PRICE LOOKUP — FLIGHTS
# ============================================================================

def _lookup_centrav(origin: str, dest: str, date: str, passengers: int) -> Optional[float]:
    """
    Attempt a Centrav B2B price lookup by shelling out to centrav_flights.py.
    Returns price_per_person in USD, or None if unavailable.
    """
    if not CENTRAV_SCRIPT.exists():
        return None
    python = VENV_PYTHON if VENV_PYTHON.exists() else sys.executable
    cmd = [
        str(python), str(CENTRAV_SCRIPT),
        "--origin", origin,
        "--dest", dest,
        "--date", date,
        "--travelers", str(passengers),
        "--json",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            log.warning(f"centrav_flights.py exited {result.returncode}: {result.stderr[:200]}")
            return None
        data = json.loads(result.stdout)
        # Expect {"price_pp": float, ...}
        return float(data["price_pp"]) if "price_pp" in data else None
    except (subprocess.TimeoutExpired, json.JSONDecodeError, KeyError, ValueError) as e:
        log.warning(f"Centrav lookup failed ({origin}→{dest} {date}): {e}")
        return None


def _parse_route(route: str):
    """
    Extract (origin, dest) IATA codes from a route string.
    Handles: 'RIC → PTY', 'DEN→FCO', 'RIC -> PTY', 'COS->FLL', 'RIC-PTY'
    Returns (origin, dest) or (None, None).
    """
    import re
    # Strip noise and find two IATA-ish tokens
    tokens = re.findall(r"\b([A-Z]{3})\b", route.upper())
    if len(tokens) >= 2:
        return tokens[0], tokens[1]
    return None, None


def get_live_price(watch: Dict[str, Any]) -> Optional[float]:
    """
    Attempt live price fetch. Returns float (price_pp) or None.
    Logs the reason when unavailable.
    """
    wtype = watch.get("watch_type", "")
    wid = watch["id"]

    if wtype == "flight":
        origin, dest = _parse_route(watch.get("route", ""))
        if not origin or not dest:
            log.warning(f"[{wid}] TOOL UNAVAILABLE — cannot parse route '{watch.get('route')}' — manual check needed")
            return None
        price = _lookup_centrav(origin, dest, watch["travel_date"], watch["passengers"])
        if price is None:
            log.warning(f"[{wid}] TOOL UNAVAILABLE — Centrav returned no price for {origin}→{dest} {watch['travel_date']} — manual check needed")
        return price

    elif wtype == "cruise":
        if _SCHEMA_AVAILABLE:
            try:
                response = _SCHEMA_AGENT.lookup_price(  # type: ignore[union-attr] — guarded by _SCHEMA_AVAILABLE
                    source=watch.get("provider", watch.get("label", "")),
                    query=f"{watch.get('route', '')} {watch.get('travel_date', '')} cabin pricing",
                )
                price_pp = response.get("list_price_per_person") or response.get("net_price_per_person")
                if price_pp:
                    log.info(f"[{wid}] Schema price intel: ${price_pp:,.0f}/pp")
                    return float(price_pp)
                log.warning(f"[{wid}] Schema agent returned no price — falling back to manual")
            except Exception as exc:
                log.warning(f"[{wid}] Schema price lookup failed: {exc} — manual check needed")
        else:
            log.warning(f"[{wid}] TOOL UNAVAILABLE — cruise price lookup requires SchemaPriceAgent — manual check needed")
        return None

    elif wtype == "hotel":
        log.warning(f"[{wid}] TOOL UNAVAILABLE — Hotelbeds credentials not configured — manual check needed")
        return None

    else:
        log.warning(f"[{wid}] TOOL UNAVAILABLE — unknown watch_type '{wtype}' — manual check needed")
        return None


# ============================================================================
# MAIN SWEEP
# ============================================================================

def run_sweep(dry_run: bool = False) -> Dict[str, Any]:
    """
    Full sweep:
      1. Ensure DB is ready (migrate from JSON if first run)
      2. Load all active watches
      3. Attempt price lookup for each
      4. Update DB (unless dry_run)
      5. Return summary dict
    """
    log.info("=" * 60)
    log.info(f"THUNDERBIRD FARE WATCH DAEMON — {datetime.now().isoformat()}")
    if dry_run:
        log.info("MODE: DRY RUN — no DB writes")
    log.info("=" * 60)

    # Ensure DB exists; if fare_watches table is empty, migrate from JSON
    init_db()
    stats_before = summary_stats()
    if stats_before["total_watches"] == 0:
        log.info("DB empty — running one-time migration from legacy JSON files...")
        migration = migrate_from_json()
        log.info(f"Migration: {migration}")

    watches = list_active()
    log.info(f"Active watches loaded: {len(watches)}")

    checked = 0
    skipped = 0
    alerts: list = []

    for watch in watches:
        wid = watch["id"]
        label = watch.get("label", wid)
        travel = watch.get("travel_date", "?")
        current = watch.get("current_price_pp", 0.0)

        # Skip departed
        try:
            if datetime.strptime(travel, "%Y-%m-%d") < datetime.now():
                log.info(f"[{wid}] SKIPPING — travel date {travel} is past")
                skipped += 1
                continue
        except ValueError:
            pass

        log.info(f"[{wid}] Checking: {label} (current ${current:,.0f}/pp, travel {travel})")

        live_price = get_live_price(watch)

        if live_price is None:
            skipped += 1
            continue

        log.info(f"[{wid}] Live price: ${live_price:,.2f}/pp (was ${current:,.0f}/pp)")

        if not dry_run:
            result = update_fare(
                watch_id=wid,
                fare=live_price,
                source="sweep",
            )
            if result.get("alert"):
                alerts.append({
                    "watch_id": wid,
                    "label": label,
                    "alert": result["alert"],
                    "price_pp": live_price,
                    "change_pct": result.get("change_pct"),
                    "travel_date": travel,
                })
                log.warning(f"[{wid}] ALERT: {result['alert']}")
        else:
            # Dry run: compute alert locally
            alert_below = watch.get("alert_below")
            alert_above = watch.get("alert_above")
            if alert_below and live_price < alert_below:
                alert_msg = f"PRICE DROP: ${live_price:,.0f}/pp below ${alert_below:,.0f}"
                log.warning(f"[{wid}] [DRY] ALERT: {alert_msg}")
                alerts.append({"watch_id": wid, "label": label, "alert": alert_msg})
            elif alert_above and live_price > alert_above:
                alert_msg = f"PRICE SPIKE: ${live_price:,.0f}/pp exceeds ${alert_above:,.0f}"
                log.warning(f"[{wid}] [DRY] ALERT: {alert_msg}")
                alerts.append({"watch_id": wid, "label": label, "alert": alert_msg})

        checked += 1

    # Pull any pre-existing DB alerts (watches already in triggered state)
    if not dry_run:
        db_alerts = get_alerts()
        for w in db_alerts:
            wid = w["id"]
            if not any(a["watch_id"] == wid for a in alerts):
                alerts.append({
                    "watch_id": wid,
                    "label": w.get("label", wid),
                    "alert": f"current ${w['current_price_pp']:,.0f}/pp vs alert_below=${w.get('alert_below','?')} / alert_above=${w.get('alert_above','?')}",
                    "travel_date": w.get("travel_date"),
                })

    # ── SUMMARY ──
    log.info("=" * 60)
    log.info(f"SWEEP COMPLETE: checked={checked}, skipped={skipped}, alerts={len(alerts)}")

    if alerts:
        log.warning("\n*** FARE ALERTS ***")
        for a in alerts:
            log.warning(f"  {a['watch_id']} | {a['alert']}")
    else:
        log.info("No threshold crossings detected.")

    stats_after = summary_stats() if not dry_run else stats_before
    log.info(f"DB stats: {json.dumps(stats_after)}")
    log.info("=" * 60)

    return {
        "checked": checked,
        "skipped": skipped,
        "alerts": alerts,
        "stats": stats_after,
        "dry_run": dry_run,
    }


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Thunderbird Fare Watch Daemon")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Read-only mode — no DB writes, just print what would happen"
    )
    parser.add_argument(
        "--migrate-only", action="store_true",
        help="Run JSON migration only, then exit"
    )
    args = parser.parse_args()

    if args.migrate_only:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
        init_db()
        result = migrate_from_json()
        print(json.dumps(result, indent=2))
        sys.exit(0)

    sweep_result = run_sweep(dry_run=args.dry_run)
    sys.exit(0 if not sweep_result["alerts"] else 1)
