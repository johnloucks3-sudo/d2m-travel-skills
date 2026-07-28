#!/usr/bin/env python3
"""
fare_watch_failover_poll.py — Fare watch polling with autonomous engine failover
==================================================================================

Replaces manual single-engine polling (ita_fare_watch_poll.py) with automatic
cascade failover across Kiwi → Google Flights → ITA Matrix → Centrav.

FEATURES:
- Autonomous cascade: when primary engine fails, automatically tries next
- Health tracking: persists engine status (rate-limits, bot-blocks, timeouts)
- Auto-blacklist: dead engines skip for 24 hours
- Rate limiting: per-engine dedup (don't re-query same route same hour)
- Alert integration: fires Telegram alerts when price crosses threshold
- Safe polling: rotation with MAX_PER_RUN limit (no timeouts)

USAGE:
    # Run immediately (poll all active watches, max 2 per run)
    python3 scripts/fare_watch_failover_poll.py

    # Poll specific watch
    python3 scripts/fare_watch_failover_poll.py --id watch_001

    # Dry-run (show what would poll, send no alerts)
    python3 scripts/fare_watch_failover_poll.py --dry-run

    # Health report (show engine health status)
    python3 scripts/fare_watch_failover_poll.py --health-report

SYSTEMD:
    # Enable and start
    sudo systemctl enable thunderbird-fare-watch-failover.service
    sudo systemctl start thunderbird-fare-watch-failover.service

    # View logs
    journalctl -u thunderbird-fare-watch-failover.service -f
"""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

# Add project root to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from core.travel.fare_watch_failover_integration import FareWatchFailoverAdapter, WatchPriceResult
from core.travel.search_engine_failover import SearchEngineFailover, EngineStatus

# Paths
FARE_WATCHES_JSON = ROOT / "core" / "travel" / "data" / "fare_watches.json"
FAILOVER_LOG = ROOT / "logs" / "fare_watch_failover_poll.log"
STATE_FILE = ROOT / "logs" / "fare_watch_failover_state.json"
ALERT_STATE = ROOT / "logs" / "fare_watch_failover_alert_state.json"
HEALTH_REPORT = ROOT / "logs" / "search_engine_health_report.json"

# Config
MAX_PER_RUN = 2  # Rotation: max watches per poll run
ALERT_BAND = 0.10  # ±10% auto-band when seeding baseline
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_D2MC2C_TOKEN", "")
COMMANDER_ID = int(os.environ.get("TELEGRAM_COMMANDER_ID", "7554895206"))

def _log(msg: str) -> None:
    """Log to console and file."""
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        FAILOVER_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(FAILOVER_LOG, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass

def load_state() -> Dict:
    """Load previous poll state."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {}

def save_state(state: Dict) -> None:
    """Persist poll state."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str))

def load_alert_state() -> Dict:
    """Load alert dedup state (what was last-alerted)."""
    if ALERT_STATE.exists():
        try:
            return json.loads(ALERT_STATE.read_text())
        except Exception:
            pass
    return {}

def save_alert_state(state: Dict) -> None:
    """Persist alert state."""
    ALERT_STATE.parent.mkdir(parents=True, exist_ok=True)
    ALERT_STATE.write_text(json.dumps(state, indent=2, default=str))

def should_alert(watch: Dict, new_price: float, alert_state: Dict) -> bool:
    """Check if a price change warrants an alert (threshold crossing + dedup)."""
    watch_id = watch.get("id")
    baseline = watch.get("baseline_price_pp")
    alert_below = watch.get("alert_below")
    alert_above = watch.get("alert_above")

    if not baseline:
        return False

    # Check threshold crossing
    below_threshold = alert_below and new_price < alert_below
    above_threshold = alert_above and new_price > alert_above

    if not (below_threshold or above_threshold):
        return False

    # Check dedup: only alert if price changed from last-alerted value
    last_alerted = alert_state.get(watch_id, {}).get("last_alerted_price")
    if last_alerted and abs(new_price - last_alerted) < 1.0:  # within $1
        return False

    return True

def send_alert(watch: Dict, new_price: float, old_price: Optional[float]) -> bool:
    """Send Telegram alert (if dry-run, return True without sending)."""
    watch_id = watch.get("id")
    label = watch.get("label", watch_id)

    if old_price:
        change_pct = ((new_price - old_price) / old_price) * 100
        msg = f"🚨 FARE ALERT — {label}\nWas: ${old_price:.0f} | Now: ${new_price:.0f}\nChange: {change_pct:+.1f}%"
    else:
        msg = f"🚨 FARE ALERT — {label}\nBaseline: ${new_price:.0f}"

    if not TELEGRAM_BOT_TOKEN:
        _log(f"[ALERT] (no Telegram token) {label}: {msg}")
        return False

    try:
        import urllib.request, urllib.error
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = json.dumps({"chat_id": COMMANDER_ID, "text": msg}).encode()
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            if data.get("ok"):
                _log(f"[ALERT] Sent to Telegram: {label}")
                return True
            else:
                _log(f"[ALERT] Telegram error: {data.get('description')}")
                return False
    except Exception as e:
        _log(f"[ALERT] Failed to send: {e}")
        return False

def health_report(fo: SearchEngineFailover) -> None:
    """Print engine health status report."""
    print("\n=== SEARCH ENGINE HEALTH REPORT ===\n")
    for engine, record in fo.health_state.items():
        status = record.status.value
        is_blacklisted = record.is_blacklisted()
        blacklist_marker = " [BLACKLISTED]" if is_blacklisted else ""
        print(f"{engine.value:15} | {status:15} | Failures: {record.consecutive_failures:2} | Fetch: {record.last_fetch_time:6.1f}s{blacklist_marker}")
        if is_blacklisted:
            print(f"                 └─ Until: {record.blacklist_until}")
    print()

async def main():
    parser = argparse.ArgumentParser(description="Fare watch polling with cascade failover")
    parser.add_argument("--id", help="Poll single watch by ID")
    parser.add_argument("--all", action="store_true", help="Poll all watches (ignores MAX_PER_RUN)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would poll, send no alerts")
    parser.add_argument("--health-report", action="store_true", help="Print health status and exit")
    args = parser.parse_args()

    # Initialize
    adapter = FareWatchFailoverAdapter()
    fo = adapter.failover

    if args.health_report:
        health_report(fo)
        return

    # Load state
    state = load_state()
    alert_state = load_alert_state()

    _log(f"[START] Fare watch polling with {len(adapter.watches)} watches active")

    # Determine which watches to poll
    if args.id:
        watches_to_poll = [adapter.watches.get(args.id)] if args.id in adapter.watches else []
    elif args.all:
        watches_to_poll = [w for w in adapter.watches.values() if w.get("active", True)]
    else:
        # Rotation: MAX_PER_RUN per run
        active = [w for w in adapter.watches.values() if w.get("active", True)]
        if len(active) > MAX_PER_RUN:
            start_idx = state.get("next_rotation_index", 0) % len(active)
            watches_to_poll = (active[start_idx:] + active[:start_idx])[:MAX_PER_RUN]
            next_idx = (start_idx + len(watches_to_poll)) % len(active)
            state["next_rotation_index"] = next_idx
            _log(f"[ROTATION] Polling {len(watches_to_poll)}/{len(active)} watches (idx {start_idx}→{next_idx})")
        else:
            watches_to_poll = active

    # Poll each watch
    results = {}
    for watch in watches_to_poll:
        watch_id = watch.get("id")
        label = watch.get("label", watch_id)

        _log(f"[POLL] {label}")
        result = adapter.get_watch_price(watch_id)

        if result.success:
            _log(f"✓ {label}: ${result.price_per_person:.0f} ({result.engine_used.value}, {result.fetch_time_seconds:.1f}s)")

            # Check for alert
            old_price = watch.get("baseline_price_pp")
            if should_alert(watch, result.price_per_person, alert_state):
                if not args.dry_run:
                    send_alert(watch, result.price_per_person, old_price)
                alert_state[watch_id] = {
                    "last_alerted_price": result.price_per_person,
                    "last_alerted_time": datetime.now(timezone.utc).isoformat()
                }
        else:
            _log(f"✗ {label}: {result.error_message} (tried: {[e.value for e in result.engines_tried]})")

        results[watch_id] = result

    # Persist state
    save_state(state)
    save_alert_state(alert_state)

    # Summary
    successful = sum(1 for r in results.values() if r.success)
    _log(f"[SUMMARY] {successful}/{len(results)} watches polled successfully")

if __name__ == "__main__":
    asyncio.run(main())
