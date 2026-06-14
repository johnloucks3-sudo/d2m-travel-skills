#!/usr/bin/env python3
"""
thunderbird-weather-disruption — Monitor weather/strikes/disruptions for active client travel.

Checks all clients with travel within a 14-day forward window.
Uses Perplexity to scan for weather, strikes, political disruption at ports/airports.
Auto-drafts proactive client reach-out email if disruption detected.

Schedule: Every 2 hours via systemd timer
Output:   OpsCenter/logs/weather_disruption.log
          Gmail draft (d2mconcierge) if disruption detected
          hale_decisions.md on alerts
"""

import json
import logging
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
DOSSIERS_DIR = ROOT / "dossiers"
BLACKBOARD_DIR = ROOT / "Blackboard/clients"
LOG_PATH = ROOT / "OpsCenter/logs/weather_disruption.log"
AUDIT_LOG = ROOT / "OpsCenter/logs/weather_disruption.jsonl"
HALE_DECISIONS = ROOT / "hale_decisions.md"
ALERT_CACHE = ROOT / "OpsCenter/data/weather_alert_cache.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [WEATHER-DISRUPTION] %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(LOG_PATH)],
)
log = logging.getLogger(__name__)

WINDOW_DAYS = 14  # Monitor clients departing within this many days


def parse_date(s: str) -> date | None:
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(str(s).strip(), fmt).date()
        except (ValueError, AttributeError):
            continue
    return None


def get_active_clients() -> list[dict]:
    """Find clients with travel in the next WINDOW_DAYS days."""
    today = date.today()
    horizon = today + timedelta(days=WINDOW_DAYS)
    active = []

    import yaml
    for fp in BLACKBOARD_DIR.glob("*.yaml"):
        try:
            data = yaml.safe_load(fp.read_text())
        except Exception:
            continue
        if not data:
            continue

        bookings = data.get("bookings", [])
        if isinstance(bookings, dict):
            bookings = [bookings]

        for booking in bookings:
            if not isinstance(booking, dict):
                continue
            dep_str = booking.get("embarkation_date") or booking.get("departure_date") or booking.get("embark_date") or booking.get("start_date")
            ret_str = booking.get("disembarkation_date") or booking.get("return_date") or booking.get("disembark_date") or booking.get("end_date")
            if not dep_str:
                continue
            dep_date = parse_date(str(dep_str))
            ret_date = parse_date(str(ret_str)) if ret_str else None

            # In window if departing within WINDOW_DAYS OR currently traveling
            if dep_date and dep_date <= horizon:
                if ret_date and ret_date < today:
                    continue  # Already returned
                ports = booking.get("ports", []) or []
                if isinstance(ports, str):
                    ports = [ports]
                airports = [booking.get("departure_airport", ""), booking.get("arrival_airport", "")]
                active.append({
                    "client_id": data.get("client_id", fp.stem),
                    "client_name": data.get("name", data.get("client_name", fp.stem)),
                    "departure_date": str(dep_date) if dep_date else None,
                    "return_date": str(ret_date) if ret_date else None,
                    "ports": [p for p in ports if p],
                    "airports": [a for a in airports if a],
                    "destination": booking.get("destination") or booking.get("region", ""),
                    "ship": booking.get("ship", ""),
                })
    return active


def check_disruptions(clients: list[dict]) -> list[dict]:
    """Run Perplexity intel sweep for disruptions at client destinations."""
    if not clients:
        return []

    try:
        sys.path.insert(0, str(ROOT))
        from core.search.perplexity_search import search
    except ImportError:
        log.warning("Perplexity search not available — skipping disruption check")
        return []

    alerts = []
    load_cache()

    for client in clients:
        destinations = list(client.get("ports", [])) + [client.get("destination", "")]
        destinations = [d for d in destinations if d]
        if not destinations:
            continue

        query_dest = ", ".join(destinations[:3])
        query = (
            f"Travel disruptions, severe weather, port closures, airline strikes, "
            f"political unrest at {query_dest} in the next 7 days. "
            f"Today is {date.today()}. Return only CONFIRMED disruptions, not forecasts."
        )

        try:
            result = search(query, max_tokens_per_page=500)
            if not result:
                continue

            # Simple heuristic: look for disruption keywords
            disruption_keywords = [
                "canceled", "cancelled", "closure", "closed", "strike", "storm",
                "hurricane", "typhoon", "flooding", "evacuation", "warning",
                "alert", "disruption", "delay", "suspended", "halted",
            ]
            result_lower = result.lower()
            found_keywords = [k for k in disruption_keywords if k in result_lower]

            if found_keywords and not is_already_alerted(client["client_id"], destinations):
                alerts.append({
                    "client_id": client["client_id"],
                    "client_name": client["client_name"],
                    "departure_date": client["departure_date"],
                    "destinations": destinations,
                    "keywords": found_keywords,
                    "intel": result[:800],
                })
                mark_alerted(client["client_id"], destinations)
                log.warning(f"DISRUPTION: {client['client_name']} @ {query_dest} — {found_keywords}")
            else:
                log.info(f"Clear: {client['client_name']} @ {query_dest}")
        except Exception as e:
            log.warning(f"Perplexity error for {client['client_name']}: {e}")

    save_cache()
    return alerts


_alert_cache: dict = {}


def load_cache() -> None:
    global _alert_cache
    try:
        if ALERT_CACHE.exists():
            _alert_cache = json.loads(ALERT_CACHE.read_text())
    except Exception:
        _alert_cache = {}


def save_cache() -> None:
    ALERT_CACHE.parent.mkdir(parents=True, exist_ok=True)
    ALERT_CACHE.write_text(json.dumps(_alert_cache, indent=2))


def is_already_alerted(client_id: str, destinations: list) -> bool:
    key = f"{client_id}:{','.join(sorted(destinations))}"
    if key not in _alert_cache:
        return False
    alerted_date = _alert_cache[key]
    try:
        return (date.today() - date.fromisoformat(alerted_date)).days < 1
    except Exception:
        return False


def mark_alerted(client_id: str, destinations: list) -> None:
    key = f"{client_id}:{','.join(sorted(destinations))}"
    _alert_cache[key] = str(date.today())


def draft_disruption_alert(alerts: list[dict]) -> None:
    try:
        sys.path.insert(0, str(ROOT))
        from core.email.thunderbird_gmail import gmail_create_draft_sync

        for alert in alerts:
            body = f"""<div style='background:#f7f3ea;padding:20px;font-family:Georgia;color:#0000ff;'>
<p>Commander —</p>
<p><strong>TRAVEL DISRUPTION ALERT — {alert['client_name']}</strong></p>
<p>Departure: {alert['departure_date']}<br/>
Destinations: {', '.join(alert['destinations'])}</p>
<p><strong>Intel:</strong><br/>{alert['intel']}</p>
<p>Recommend proactive client reach-out. Draft available on request.</p>
<p>— Hale</p>
</div>"""
            gmail_create_draft_sync(
                to="d2mconcierge@gmail.com",
                subject=f"[DISRUPTION ALERT] {alert['client_name']} — {', '.join(alert['destinations'][:2])}",
                body=body,
            )
            log.info(f"Draft created for {alert['client_name']}")
    except Exception as e:
        log.warning(f"Could not draft alert: {e}")


def write_hale_decision(alerts: list[dict], run_dt: datetime) -> None:
    if not alerts:
        return
    lines = [
        f"\n### {run_dt.strftime('%Y-%m-%d %H:%M:%S')} — Autonomous Decision (Tier T0)\n",
        f"**Decision:** Weather/disruption monitor found {len(alerts)} alert(s)\n",
    ]
    for a in alerts:
        lines.append(f"  - {a['client_name']}: {', '.join(a['destinations'])} — {a['keywords']}\n")
    lines.append("**Domain:** Client protection / Travel intel\n**Type:** proactive alert\n**Outcome:** Gmail draft created\n")
    with open(HALE_DECISIONS, "a") as f:
        f.writelines(lines)


def main() -> int:
    run_dt = datetime.now()
    log.info(f"Weather disruption monitor — {run_dt.isoformat()}")

    clients = get_active_clients()
    log.info(f"Found {len(clients)} client(s) in {WINDOW_DAYS}-day travel window")

    if not clients:
        log.info("No active travel — done")
        return 0

    alerts = check_disruptions(clients)

    entry = {
        "ts": run_dt.isoformat(),
        "clients_checked": len(clients),
        "alerts": len(alerts),
        "detail": alerts,
    }
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")

    if alerts:
        write_hale_decision(alerts, run_dt)
        draft_disruption_alert(alerts)
        log.warning(f"{len(alerts)} disruption alert(s) — drafts created")
    else:
        log.info(f"All {len(clients)} active client(s) clear — no disruptions")

    return 0


if __name__ == "__main__":
    sys.exit(main())
