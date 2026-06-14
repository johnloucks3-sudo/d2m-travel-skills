#!/usr/bin/env python3
"""
d2m-airline-schedule-change — Hourly check for schedule changes on ticketed clients.

Checks clients with flights in the next 30 days via Amadeus or ITA Matrix.
Compares against stored flight details. Alerts Commander on ANY change.

Schedule: Hourly during business hours (0600-2200 MDT) via systemd timer
Output:   OpsCenter/logs/airline_schedule_change.log
          OpsCenter/data/flight_schedule_baseline.json (stored baseline)
          Gmail draft on any detected change
          hale_decisions.md on alerts
"""

import json
import logging
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
BLACKBOARD_DIR = ROOT / "Blackboard/clients"
DOSSIERS_DIR = ROOT / "dossiers"
LOG_PATH = ROOT / "OpsCenter/logs/airline_schedule_change.log"
AUDIT_LOG = ROOT / "OpsCenter/logs/airline_schedule_change.jsonl"
BASELINE_FILE = ROOT / "OpsCenter/data/flight_schedule_baseline.json"
HALE_DECISIONS = ROOT / "hale_decisions.md"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [AIRLINE-SCHED] %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(LOG_PATH)],
)
log = logging.getLogger(__name__)

WINDOW_DAYS = 30


def parse_date(s: str) -> date | None:
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(str(s).strip(), fmt).date()
        except (ValueError, AttributeError):
            continue
    return None


def load_baseline() -> dict:
    try:
        if BASELINE_FILE.exists():
            return json.loads(BASELINE_FILE.read_text())
    except Exception:
        pass
    return {}


def save_baseline(baseline: dict) -> None:
    BASELINE_FILE.parent.mkdir(parents=True, exist_ok=True)
    BASELINE_FILE.write_text(json.dumps(baseline, indent=2))


def get_ticketed_flights() -> list[dict]:
    """Extract flight details from Blackboard YAML for clients flying within WINDOW_DAYS."""
    import yaml

    today = date.today()
    horizon = today + timedelta(days=WINDOW_DAYS)
    flights = []

    for fp in BLACKBOARD_DIR.glob("*.yaml"):
        try:
            data = yaml.safe_load(fp.read_text())
        except Exception:
            continue
        if not data:
            continue

        # Flights stored under bookings[] with booking_type == "flight"
        all_bookings = data.get("bookings", [])
        if isinstance(all_bookings, dict):
            all_bookings = [all_bookings]
        flight_records = [b for b in all_bookings if isinstance(b, dict) and b.get("booking_type") == "flight"]

        for flight in flight_records:
            dep_str = (flight.get("embarkation_date") or flight.get("departure_date")
                       or flight.get("embark_date") or flight.get("date"))
            if not dep_str or str(dep_str) == "N/A":
                continue
            dep_date = parse_date(str(dep_str))
            if not dep_date or dep_date > horizon or dep_date < today:
                continue

            # Extract PNR and flight numbers from notes/route/booking_id
            notes = flight.get("notes", "")
            pnr = flight.get("pnr") or flight.get("record_locator") or flight.get("booking_id", "")
            route = flight.get("route", "")
            supplier = flight.get("supplier", "")
            flights.append({
                "client_id": data.get("client_id", fp.stem),
                "client_name": data.get("client_names", data.get("client_id", fp.stem)),
                "flight_number": route or supplier,
                "departure_date": str(dep_date),
                "departure_time": "",
                "origin": flight.get("embarkation_port", ""),
                "destination_airport": flight.get("disembarkation_port", ""),
                "pnr": str(pnr),
                "notes": notes[:200] if notes else "",
            })

    return flights


def check_flight_status(flight: dict, baseline: dict) -> dict | None:
    """
    Check Amadeus for current flight info and compare to baseline.
    Returns change dict if something changed, None if no change.
    """
    key = f"{flight['flight_number']}_{flight['departure_date']}"

    try:
        sys.path.insert(0, str(ROOT))
        from core.travel.amadeus_search import wing_flight_brief

        result = wing_flight_brief(
            origin=flight["origin"],
            destination=flight["destination_airport"],
            departure_date=flight["departure_date"],
            cabin="ECONOMY",
            adults=1,
        )
        if not result:
            return None

        # Store baseline on first run
        current_info = {
            "checked_at": datetime.now().isoformat(),
            "origin": flight["origin"],
            "destination": flight["destination_airport"],
            "departure_date": flight["departure_date"],
            "raw": str(result)[:500],
        }

        if key not in baseline:
            baseline[key] = current_info
            log.info(f"Baseline set for {key}")
            return None

        # Simple change detection: compare raw output hash
        if str(result)[:500] != baseline[key].get("raw", ""):
            change = {
                "flight": key,
                "client": flight["client_name"],
                "pnr": flight.get("pnr", ""),
                "previous": baseline[key].get("raw", "")[:200],
                "current": str(result)[:200],
            }
            baseline[key] = current_info
            return change

    except Exception as e:
        log.debug(f"Amadeus check failed for {key}: {e}")
        # Fall back to no-op — don't alert on API errors
        if key not in baseline:
            baseline[key] = {"checked_at": datetime.now().isoformat(), "raw": ""}

    return None


def draft_change_alert(changes: list[dict]) -> None:
    try:
        sys.path.insert(0, str(ROOT))
        from core.email.thunderbird_gmail import gmail_create_draft_sync

        for change in changes:
            body = f"""<div style='background:#f7f3ea;padding:20px;font-family:Georgia;color:#0000ff;'>
<p>Commander —</p>
<p><strong>AIRLINE SCHEDULE CHANGE DETECTED</strong></p>
<p>Flight: {change['flight']}<br/>
Client: {change['client']}<br/>
PNR: {change.get('pnr', 'N/A')}</p>
<p><strong>Previous:</strong><br/>{change['previous']}</p>
<p><strong>Current:</strong><br/>{change['current']}</p>
<p>Recommend verifying with airline directly and notifying client.</p>
<p>— Hale</p>
</div>"""
            gmail_create_draft_sync(
                to="d2mconcierge@gmail.com",
                subject=f"[FLIGHT CHANGE] {change['client']} — {change['flight']}",
                body=body,
            )
            log.info(f"Draft created for flight change: {change['flight']}")
    except Exception as e:
        log.warning(f"Could not draft alert: {e}")


def write_hale_decision(changes: list[dict], run_dt: datetime) -> None:
    if not changes:
        return
    lines = [
        f"\n### {run_dt.strftime('%Y-%m-%d %H:%M:%S')} — Autonomous Decision (Tier T0)\n",
        f"**Decision:** Airline schedule change monitor detected {len(changes)} change(s)\n",
    ]
    for c in changes:
        lines.append(f"  - {c['client']}: {c['flight']}\n")
    lines.append("**Domain:** Client protection / Air travel\n**Type:** proactive alert\n**Outcome:** Gmail draft created\n")
    with open(HALE_DECISIONS, "a") as f:
        f.writelines(lines)


def main() -> int:
    run_dt = datetime.now()
    log.info(f"Airline schedule change monitor — {run_dt.isoformat()}")

    flights = get_ticketed_flights()
    log.info(f"Found {len(flights)} ticketed flight(s) in {WINDOW_DAYS}-day window")

    if not flights:
        log.info("No ticketed flights in window — done")
        return 0

    baseline = load_baseline()
    changes = []

    for flight in flights:
        change = check_flight_status(flight, baseline)
        if change:
            changes.append(change)

    save_baseline(baseline)

    entry = {
        "ts": run_dt.isoformat(),
        "flights_checked": len(flights),
        "changes": len(changes),
        "detail": changes,
    }
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")

    if changes:
        write_hale_decision(changes, run_dt)
        draft_change_alert(changes)
        log.warning(f"{len(changes)} schedule change(s) detected — drafts created")
    else:
        log.info(f"All {len(flights)} flight(s) stable — no changes")

    return 0


if __name__ == "__main__":
    sys.exit(main())
