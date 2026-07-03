"""
Thunderbird Fare Watch Logger — Structured JSON History
=========================================================
Dreams2Memories Travel, LLC

Logs daily fare scan results to a JSON file with trend tracking.
Falls back to JSON file storage when Google Sheets auth is unavailable.

Functions:
  log_fare_scan()       — record a new scan result
  get_trend()           — return price trend statistics for a watch
  export_to_sheets_csv() — export Fare History tab as CSV string
"""

import csv
import io
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────

THUNDERBIRD = Path.home() / "Thunderbird"
HISTORY_FILE = THUNDERBIRD / "core" / "travel" / "data" / "fare_watch_history.json"
DATA_DIR = HISTORY_FILE.parent
DATA_DIR.mkdir(parents=True, exist_ok=True)


# ── Data helpers ──────────────────────────────────────────────────────────────

def _load_history() -> dict:
    """Load the full history file. Returns {'scans': [], '_trends': {}}."""
    if HISTORY_FILE.exists():
        try:
            data = json.loads(HISTORY_FILE.read_text())
            if isinstance(data, dict) and "scans" in data:
                return data
        except (json.JSONDecodeError, Exception):
            pass
    return {"scans": [], "_trends": {}}


def _save_history(data: dict) -> None:
    """Write history file atomically."""
    tmp = HISTORY_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, default=str))
    tmp.rename(HISTORY_FILE)


def _update_trends(data: dict, watch_id: str, price_pp: float) -> None:
    """Update running trend summary for a watch_id."""
    trends = data.setdefault("_trends", {})
    if watch_id not in trends:
        trends[watch_id] = {
            "prices": [],
            "min": None,
            "max": None,
            "sum": 0.0,
            "count": 0,
        }
    t = trends[watch_id]
    t["prices"].append(price_pp)
    # Keep last 90 days of prices (max 90 entries for daily scans)
    if len(t["prices"]) > 90:
        t["prices"] = t["prices"][-90:]
    t["count"] = len(t["prices"])
    t["sum"] = sum(t["prices"])
    t["min"] = min(t["prices"]) if t["prices"] else None
    t["max"] = max(t["prices"]) if t["prices"] else None


# ── Public API ────────────────────────────────────────────────────────────────

def log_fare_scan(
    watch_id: str,
    route: str,
    source: str,
    cabin: str,
    best_price_pp: Optional[float],
    shortest_duration: Optional[int] = None,
    airline: Optional[str] = None,
    stops: Optional[int] = None,
    travel_date: Optional[str] = None,
    passengers: int = 2,
    url: Optional[str] = None,
    notes: str = "",
) -> dict:
    """Record a fare scan result to the JSON history file.

    Args:
        watch_id: Unique watch identifier
        route: Route string (e.g. 'DEN → HNL')
        source: Source name (e.g. 'amadeus', 'centrav', 'kayak', 'google_flights')
        cabin: Cabin class (e.g. 'economy', 'business')
        best_price_pp: Best price found per person (USD), or None if unavailable
        shortest_duration: Shortest flight duration in minutes (optional)
        airline: Airline name (optional)
        stops: Number of stops (optional)
        travel_date: Travel date YYYY-MM-DD (optional)
        passengers: Number of passengers
        url: Search URL for reference (optional)
        notes: Free-text notes (optional)

    Returns:
        The scan record dict that was appended.
    """
    record = {
        "watch_id": watch_id,
        "route": route,
        "source": source,
        "cabin": cabin,
        "best_price_pp": best_price_pp,
        "shortest_duration": shortest_duration,
        "airline": airline,
        "stops": stops,
        "travel_date": travel_date,
        "passengers": passengers,
        "url": url,
        "notes": notes,
        "scanned_at": datetime.now(timezone.utc).isoformat(),
    }

    data = _load_history()
    data["scans"].append(record)

    if best_price_pp is not None:
        _update_trends(data, watch_id, best_price_pp)

    _save_history(data)
    logger.info(
        "fare_log: %s | %s | %s | $%s/pp | source=%s",
        watch_id, route, cabin,
        f"{best_price_pp:.2f}" if best_price_pp else "N/A",
        source,
    )
    return record


def get_trend(watch_id: str) -> dict:
    """Return price trend statistics for a watched fare.

    Returns:
        dict with: watch_id, avg_30d, avg_90d (or since data), lowest, highest,
                   price_count, prices[] (last 90)
        If no data: returns empty trend with price_count=0
    """
    data = _load_history()
    trends = data.get("_trends", {})
    t = trends.get(watch_id, {"prices": [], "count": 0, "sum": 0.0, "min": None, "max": None})

    prices = t.get("prices", [])
    count = t.get("count", 0)

    result = {
        "watch_id": watch_id,
        "price_count": count,
        "lowest": t.get("min"),
        "highest": t.get("max"),
        "avg_30d": None,
        "avg_90d": None,
    }

    if count > 0 and prices:
        # Compute averages
        if count <= 30:
            result["avg_30d"] = round(t["sum"] / count, 2)
        else:
            last_30 = prices[-30:]
            result["avg_30d"] = round(sum(last_30) / len(last_30), 2)
        result["avg_90d"] = round(t["sum"] / count, 2)

    return result


def export_to_sheets_csv() -> str:
    """Export all fare history records as CSV string, ready for pasting.

    Columns: Timestamp, Watch ID, Route, Source, Cabin, Price/PP, Duration,
             Airline, Stops, Travel Date, Passengers, URL, Notes
    """
    data = _load_history()
    scans = data.get("scans", [])

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Timestamp", "Watch ID", "Route", "Source", "Cabin", "Price/PP",
        "Duration (min)", "Airline", "Stops", "Travel Date", "Passengers",
        "URL", "Notes",
    ])

    for rec in scans:
        writer.writerow([
            rec.get("scanned_at", ""),
            rec.get("watch_id", ""),
            rec.get("route", ""),
            rec.get("source", ""),
            rec.get("cabin", ""),
            rec.get("best_price_pp", ""),
            rec.get("shortest_duration", ""),
            rec.get("airline", ""),
            rec.get("stops", ""),
            rec.get("travel_date", ""),
            rec.get("passengers", ""),
            rec.get("url", ""),
            rec.get("notes", ""),
        ])

    return output.getvalue()


def get_all_watch_ids() -> list[str]:
    """Return sorted list of all watch IDs that have been scanned."""
    data = _load_history()
    ids = set()
    for rec in data.get("scans", []):
        wid = rec.get("watch_id")
        if wid:
            ids.add(wid)
    return sorted(ids)


def get_recent_scans(watch_id: Optional[str] = None, limit: int = 20) -> list[dict]:
    """Return most recent scan records, optionally filtered by watch_id."""
    data = _load_history()
    scans = data.get("scans", [])
    if watch_id:
        scans = [s for s in scans if s.get("watch_id") == watch_id]
    return scans[-limit:]


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fare Watch Logger")
    parser.add_argument("--trend", help="Show trend for a watch ID")
    parser.add_argument("--export-csv", action="store_true", help="Export as CSV")
    parser.add_argument("--list", action="store_true", help="List all watch IDs")
    parser.add_argument("--recent", help="Show recent scans for a watch ID")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    if args.list:
        for wid in get_all_watch_ids():
            print(wid)
    elif args.trend:
        t = get_trend(args.trend)
        print(json.dumps(t, indent=2))
    elif args.export_csv:
        print(export_to_sheets_csv())
    elif args.recent:
        scans = get_recent_scans(args.recent, limit=10)
        print(json.dumps(scans, indent=2, default=str))
    else:
        # Demo: log a sample scan
        rec = log_fare_scan(
            watch_id="test-demo",
            route="DEN > HNL",
            source="kayak",
            cabin="economy",
            best_price_pp=345.50,
            airline="United",
            travel_date="2026-08-15",
        )
        print(json.dumps(rec, indent=2, default=str))
