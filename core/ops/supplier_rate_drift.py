#!/usr/bin/env python3
"""
d2m-supplier-rate-drift — 4x daily cross-reference of booked vs current cruise rates.
Alerts on rebook opportunities (current < booked).
Schedule: 08:00, 12:00, 16:00, 20:00 MDT
"""
import json
import logging
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, date
from pathlib import Path

THUNDERBIRD = Path("/home/john/Thunderbird")
DOSSIERS_DIR = THUNDERBIRD / "dossiers"
LOG_FILE = THUNDERBIRD / "logs" / "supplier_rate_drift.log"
BOT_TOKEN = os.environ.get("TELEGRAM_C2_BOT_TOKEN", "***REMOVED-SECRET***")
COMMANDER_ID = os.environ.get("TELEGRAM_COMMANDER_ID", "7554895206")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)
log = logging.getLogger(__name__)


def tg(msg: str):
    try:
        payload = json.dumps({"chat_id": COMMANDER_ID, "text": msg}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data=payload, headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=15)
    except Exception as e:
        log.warning(f"Telegram send failed: {e}")


def load_active_bookings() -> list[dict]:
    """Load cruise bookings from Blackboard YAML with total_amount > 0."""
    import yaml
    bookings = []
    today = date.today()
    bb_dir = THUNDERBIRD / "Blackboard" / "clients"
    if not bb_dir.exists():
        return bookings
    for f in bb_dir.glob("*.yaml"):
        try:
            data = yaml.safe_load(f.read_text())
        except Exception as e:
            log.debug(f"Skip {f.name}: {e}")
            continue
        if not data:
            continue
        all_bookings = data.get("bookings", [])
        if isinstance(all_bookings, dict):
            all_bookings = [all_bookings]
        for b in all_bookings:
            if not isinstance(b, dict):
                continue
            if b.get("booking_type") != "cruise":
                continue
            sail_str = b.get("embarkation_date") or b.get("departure_date")
            if not sail_str or str(sail_str) in ("N/A", "TBD"):
                continue
            try:
                sd = date.fromisoformat(str(sail_str)[:10])
            except ValueError:
                continue
            if sd <= today:
                continue
            booked_rate = b.get("total_amount") or b.get("paid_amount") or 0
            if not booked_rate or float(booked_rate) <= 0:
                continue
            bookings.append({
                "client": data.get("client_names", data.get("client_id", f.stem)),
                "cruise_line": b.get("supplier", ""),
                "ship": b.get("ship") or b.get("voyage_name", ""),
                "booking_id": b.get("booking_id", ""),
                "sail_date": str(sd),
                "booked_rate": float(booked_rate),
                "cabin_cat": b.get("cabin_category", ""),
            })
    return bookings


def check_current_rate(booking: dict) -> float | None:
    """Attempt to get current rate via fare_watch. Returns None if unavailable."""
    try:
        sys.path.insert(0, str(THUNDERBIRD))
        from core.travel.thunderbird_fare_watch import get_current_rate
        return get_current_rate(
            cruise_line=booking["cruise_line"],
            sail_date=booking["sail_date"],
            cabin_cat=booking["cabin_cat"],
        )
    except Exception as e:
        log.debug(f"Rate check unavailable for {booking['client']}: {e}")
        return None


def main():
    log.info("=== Supplier Rate Drift check starting ===")
    bookings = load_active_bookings()
    log.info(f"Active bookings with rates: {len(bookings)}")

    opportunities = []
    for b in bookings:
        current = check_current_rate(b)
        if current is None:
            continue
        drift_pct = ((b["booked_rate"] - current) / b["booked_rate"]) * 100
        if drift_pct > 5:  # >5% cheaper now
            opportunities.append({
                "client": b["client"],
                "cruise_line": b["cruise_line"],
                "sail_date": b["sail_date"],
                "booked": b["booked_rate"],
                "current": current,
                "savings_pct": drift_pct,
            })
            log.info(f"Rebook opp: {b['client']} — {drift_pct:.1f}% cheaper")

    if opportunities:
        lines = []
        for o in opportunities[:5]:
            lines.append(
                f"  {o['client']} ({o['sail_date']}): "
                f"${o['booked']:.0f} → ${o['current']:.0f} ({o['savings_pct']:.1f}% savings)"
            )
        tg(
            f"RATE DRIFT — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            f"{len(opportunities)} rebook opportunities:\n" + "\n".join(lines)
        )
    else:
        log.info(f"No drift opportunities found (checked {len(bookings)} bookings).")

    log.info("=== Supplier Rate Drift check complete ===")


if __name__ == "__main__":
    main()
