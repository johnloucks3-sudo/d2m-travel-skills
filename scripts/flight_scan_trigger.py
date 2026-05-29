#!/usr/bin/env python3
"""
Flight Scan Trigger — Auto-Register Fare Watches When TP 1.2 Enters Window
===========================================================================
Dreams2Memories Travel, LLC | scripts/flight_scan_trigger.py

Scans all active clients for TP 1.2 (Airfare Watch, E-210 to E-180).
When a client enters the window, creates a fare watch entry in
~/Thunderbird/data/fare_watches.json so the daily centrav fare scan
picks it up automatically.

Also creates TP 1.3 (Hotel Options) reminder in wing_comms.md.

Usage:
    python3 scripts/flight_scan_trigger.py          # Scan + register
    python3 scripts/flight_scan_trigger.py --dry-run
    python3 scripts/flight_scan_trigger.py --status  # Show registered watches
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import date, datetime
from pathlib import Path

import yaml

THUNDERBIRD = Path.home() / "Thunderbird"
sys.path.insert(0, str(THUNDERBIRD))
sys.path.insert(0, str(THUNDERBIRD / "core" / "booking"))
sys.path.insert(0, str(THUNDERBIRD / "core" / "travel"))

from thunderbird_tp_scheduler import scan_dossiers, generate_schedule, TPStatus

TRIGGER_LOG = THUNDERBIRD / "storage" / "flight_trigger_log.jsonl"
WING_COMMS = THUNDERBIRD / "OpsCenter" / "collaboration" / "wing_comms.md"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s FLIGHT-TRIGGER %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(str(THUNDERBIRD / "logs" / "flight_scan_trigger.log"), mode="a"),
    ],
)
logger = logging.getLogger("flight_trigger")

SKIP_FILES = {"CLAUDE.md", "DOSSIER_Regent_Tips_Guide.md", "DANI_TESTER_BRIEFINGS.md"}


def _load_trigger_log() -> set[str]:
    """Return set of client names already registered."""
    registered = set()
    if TRIGGER_LOG.exists():
        for line in TRIGGER_LOG.read_text().splitlines():
            try:
                e = json.loads(line)
                if e.get("status") == "registered":
                    registered.add(e["client"])
            except Exception:
                pass
    return registered


def _append_trigger_log(entry: dict) -> None:
    TRIGGER_LOG.parent.mkdir(parents=True, exist_ok=True)
    with TRIGGER_LOG.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def _get_hub_airport(dossier_path: Path) -> str:
    """Try to extract departure airport from dossier body."""
    try:
        text = dossier_path.read_text(encoding="utf-8")
        # Look for airport codes in flight section
        m = re.search(r"\b([A-Z]{3})\s*[→\->]\s*([A-Z]{3})\b", text)
        if m:
            return m.group(1)
        # Fallback: check frontmatter hub field
        fm_m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
        if fm_m:
            fm = yaml.safe_load(fm_m.group(1)) or {}
            hub = fm.get("hub_airport", fm.get("home_airport", ""))
            if hub:
                return str(hub).upper()
    except Exception:
        pass
    return "DEN"  # Colorado Springs default hub


def register_fare_watches(dry_run: bool = False) -> list[dict]:
    try:
        from thunderbird_fare_watch import add_watch, _load_watches
    except ImportError as exc:
        logger.error(f"Cannot import thunderbird_fare_watch: {exc}")
        return []

    today = date.today()
    registered_clients = _load_trigger_log()
    existing_watches = _load_watches()
    results = []

    records = scan_dossiers()
    for rec in records:
        if not rec.is_schedulable:
            continue

        schedule = generate_schedule(rec, today)
        # Find TP 1.2
        tp_12 = next((tp for tp in schedule if tp.tp_id == "1.2"), None)
        tp_13 = next((tp for tp in schedule if tp.tp_id == "1.3"), None)

        if not tp_12:
            continue

        # Only trigger when IN_WINDOW or DUE
        if tp_12.status not in (TPStatus.IN_WINDOW, TPStatus.DUE, TPStatus.OVERDUE):
            continue

        watch_id = f"{rec.client.lower().replace(' ', '-')}-flights"

        # Skip if already registered
        if rec.client in registered_clients or watch_id in existing_watches:
            logger.info(f"Watch already registered for {rec.client}")
            continue

        # Read dossier for extra info
        fm = {}
        try:
            text = rec.path.read_text(encoding="utf-8")
            m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
            if m:
                fm = yaml.safe_load(m.group(1)) or {}
        except Exception:
            pass

        hub = _get_hub_airport(rec.path)
        # Embarkation port airport — crude heuristic
        ship_port = "PTY"  # Panama Canal default; override per cruise line
        cruise_line = rec.cruise_line or ""
        if "regent" in cruise_line.lower() or "silversea" in cruise_line.lower():
            # European sailings
            ship_port = "ARN"  # Stockholm default for Scandinavia
        elif "viking" in cruise_line.lower():
            ship_port = "PTY"  # Panama

        # Build route string
        departure_str = rec.departure.isoformat() if rec.departure else "TBD"
        route = f"{hub}→{ship_port}"
        label = f"{rec.client} — {rec.ship or 'cruise'} · {rec.cruise_line or ''}"

        entry = {
            "ts": datetime.now().isoformat(),
            "client": rec.client,
            "watch_id": watch_id,
            "route": route,
            "departure": departure_str,
            "tp_deadline": tp_12.deadline.isoformat() if tp_12.deadline else None,
            "status": "registered",
        }

        if dry_run:
            entry["status"] = "dry_run"
            print(
                f"  [DRY-RUN] {rec.client}: fare watch '{watch_id}'\n"
                f"    Route: {route} · Departure: {departure_str}\n"
                f"    TP 1.2 deadline: {entry['tp_deadline']}"
            )
        else:
            try:
                add_watch(
                    watch_id=watch_id,
                    watch_type="flight",
                    label=label,
                    provider="centrav",
                    route=route,
                    travel_date=departure_str,
                    current_price_pp=0.0,  # No baseline yet — first run establishes it
                    passengers=2,
                    notes=f"Auto-registered by flight_scan_trigger.py · TP 1.2 window open",
                )
                logger.info(f"Registered fare watch: {watch_id} ({route})")
                print(f"  ✅ {rec.client}: fare watch '{watch_id}' registered ({route})")

                # Wing comms notification
                WING_COMMS.parent.mkdir(parents=True, exist_ok=True)
                with WING_COMMS.open("a") as f:
                    f.write(
                        f"\n## FLIGHT TRIGGER — {today.isoformat()}\n"
                        f"- {rec.client} entered TP 1.2 window\n"
                        f"- Fare watch registered: `{watch_id}` ({route})\n"
                        f"- TP 1.2 deadline: {entry['tp_deadline']}\n"
                        f"- A2 Dembe: begin airfare research\n"
                    )
                    if tp_13 and tp_13.status in (TPStatus.IN_WINDOW, TPStatus.DUE):
                        f.write(f"- A2 Dembe: TP 1.3 hotel research window also open\n")

            except Exception as exc:
                entry["status"] = "error"
                entry["error"] = str(exc)
                logger.error(f"Watch registration failed {rec.client}: {exc}")

        _append_trigger_log(entry)
        results.append(entry)

    return results


def print_status() -> None:
    try:
        from thunderbird_fare_watch import _load_watches
        watches = _load_watches()
        print(f"\nRegistered fare watches: {len(watches)}")
        for wid, w in watches.items():
            print(f"  {wid}: {w.get('route','?')} · {w.get('travel_date','?')}")
    except ImportError:
        print("Cannot load thunderbird_fare_watch module")


def main() -> None:
    p = argparse.ArgumentParser(description="Flight Scan Trigger — auto-register fare watches")
    p.add_argument("--dry-run", action="store_true", help="Preview only")
    p.add_argument("--status", action="store_true", help="Show registered watches")
    args = p.parse_args()

    if args.status:
        print_status()
        return

    print(f"\nFlight Scan Trigger — {date.today().isoformat()}")
    if args.dry_run:
        print("MODE: DRY-RUN\n")

    results = register_fare_watches(dry_run=args.dry_run)
    registered = [r for r in results if r.get("status") == "registered"]
    dry = [r for r in results if r.get("status") == "dry_run"]
    errors = [r for r in results if r.get("status") == "error"]

    if args.dry_run:
        print(f"\n{len(dry)} watch(es) would be registered.")
    else:
        print(f"\n{len(registered)} watch(es) registered, {len(errors)} errors.")


if __name__ == "__main__":
    main()
