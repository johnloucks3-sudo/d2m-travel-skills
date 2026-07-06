#!/usr/bin/env python3
"""
lifecycle_search_scheduler.py — Lifecycle-TP-triggered autonomous search scheduler.

Phase 1 of docs/AUTONOMOUS_SEARCH_CAPABILITY_PLAN.md. Distinct from the existing
03:00 MT continuous route fare-watch (scripts/daily_airfare_scan.py, fare_watch_amadeus.py,
fare_watch_centrav.py) which re-checks a fixed watch list every day regardless of any
touchpoint. This scheduler instead fires a search N days before a specific client
lifecycle touchpoint (TP) is due, using config/lifecycle_search_config.json.

Phase 1 scope: flights only (per plan). Reuses the existing Amadeus search function
(scripts/fare_watch_amadeus.py) rather than reimplementing search.

Config: config/lifecycle_search_config.json
Output: search_queue/{client}_{date}_{type}.json  (raw result, written even on failure)
Log:    hale_review_queue.md  (append-mode)

Usage:
  .venv/bin/python scripts/lifecycle_search_scheduler.py                # run for today
  .venv/bin/python scripts/lifecycle_search_scheduler.py --date 2026-06-03   # simulate a date
  .venv/bin/python scripts/lifecycle_search_scheduler.py --dry-run       # log triggers, no search calls

Dreams2Memories Travel, LLC · Thunderbird Wing · Phase 1 build 2026-07-06
"""

import argparse
import json
import logging
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("lifecycle_search_scheduler")

CONFIG_FILE = ROOT / "config" / "lifecycle_search_config.json"
QUEUE_DIR = ROOT / "search_queue"
REVIEW_QUEUE_FILE = ROOT / "hale_review_queue.md"


def _load_config() -> dict:
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"Lifecycle search config not found: {CONFIG_FILE}")
    return json.loads(CONFIG_FILE.read_text())


def _trigger_date(due: str, trigger_days_before: int) -> date:
    due_date = datetime.strptime(due, "%Y-%m-%d").date()
    return due_date - timedelta(days=trigger_days_before)


def _run_flight_search(routes: list, departure_date: str, adults: int) -> dict:
    """Fire flight search via the existing Amadeus function. Never raises — returns a
    result dict with status ok/error so a queue entry is always written."""
    try:
        from fare_watch_amadeus import _load_env, _get_amadeus_token, _search_flights
    except ImportError as e:
        return {"status": "error", "error": f"import failure: {e}", "results": []}

    try:
        env = _load_env()
        token = _get_amadeus_token(env)
    except Exception as e:
        return {"status": "error", "error": f"auth failure: {e}", "results": []}

    results = []
    any_ok = False
    for route in routes:
        origin, dest = route["origin"], route["dest"]
        try:
            r = _search_flights(token, origin, dest, departure_date, adults)
            results.append(r)
            if r.get("status") == "ok":
                any_ok = True
        except Exception as e:
            results.append({"status": "error", "origin": origin, "dest": dest, "error": str(e)})

    return {"status": "ok" if any_ok else "partial_fail", "results": results}


def _write_queue_entry(client: str, run_date: date, search_type: str, payload: dict) -> Path:
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    out_path = QUEUE_DIR / f"{client.lower()}_{run_date.isoformat()}_{search_type}.json"
    out_path.write_text(json.dumps(payload, indent=2, default=str))
    return out_path


def _append_review_queue(client: str, tp: str, search_type: str, status: str,
                          out_path: Path, flagged: str = "") -> None:
    ts = datetime.now(timezone.utc).isoformat()
    line = f"| {ts} | {client} | {tp} | {search_type} | {status} | {out_path} | {flagged} |\n"
    is_new = not REVIEW_QUEUE_FILE.exists()
    with REVIEW_QUEUE_FILE.open("a") as f:
        if is_new:
            f.write("# Hale Review Queue\n\n")
            f.write("Autonomous search results awaiting Hale review. "
                    "Populated by scripts/lifecycle_search_scheduler.py.\n\n")
            f.write("| Timestamp (UTC) | Client | TP | Type | Status | File | Flagged |\n")
            f.write("|---|---|---|---|---|---|---|\n")
        f.write(line)


def run(run_date: date, dry_run: bool = False) -> dict:
    config = _load_config()
    fired = []

    for client_cfg in config.get("clients", []):
        client = client_cfg["client"]
        for search in client_cfg.get("searches", []):
            if not search.get("search_trigger"):
                continue
            if search.get("type") != "flights":
                # Phase 1 scope is flights only per the plan.
                continue

            trig_date = _trigger_date(search["due"], search["trigger_days_before"])
            if trig_date != run_date:
                continue

            tp = search["tp"]
            log.info("TRIGGER FIRED: %s / %s (due %s, trigger %s)", client, tp, search["due"], trig_date)

            if dry_run:
                fired.append({"client": client, "tp": tp, "trigger_date": str(trig_date), "dry_run": True})
                continue

            result = _run_flight_search(search["routes"], search["departure_date"], search["adults"])
            payload = {
                "client": client,
                "tp": search["tp"],
                "search_id": search["id"],
                "type": "flights",
                "due": search["due"],
                "trigger_date": str(trig_date),
                "run_date": str(run_date),
                "routes": search["routes"],
                "departure_date": search["departure_date"],
                "adults": search["adults"],
                "search_result": result,
            }
            out_path = _write_queue_entry(client, run_date, "flights", payload)

            status = "DONE" if result["status"] == "ok" else ("FLAGGED" if result["status"] == "partial_fail" else "FAIL")
            flagged = result.get("error", "") if result["status"] == "error" else ""
            _append_review_queue(client, tp, "flights", status, out_path, flagged)

            fired.append({"client": client, "tp": tp, "trigger_date": str(trig_date),
                          "status": status, "output": str(out_path)})

    if not fired:
        log.info("No triggers due for %s", run_date)

    return {"run_date": str(run_date), "fired": fired}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="Simulate scheduler run for this date (YYYY-MM-DD). Default: today.")
    ap.add_argument("--dry-run", action="store_true", help="Log triggers without calling search or writing queue files.")
    args = ap.parse_args()

    run_date = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else date.today()
    result = run(run_date, dry_run=args.dry_run)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
