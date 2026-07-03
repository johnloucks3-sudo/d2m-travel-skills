#!/usr/bin/env python3
"""
tess_fare_watch_autoregister.py — Auto-register fare watches from TESS bookings.
FIX-10 2026-06-27 (Wing Exercise — BURNING HOT CI).

When a new booking is confirmed in TESS (air segment present), auto-creates a
fare watch entry in fare_watch.db so price tracking begins immediately without
manual registration.

Runs via supertimer daily. Compares TESS bookings against registered watches;
registers missing flight segments. Never duplicates an existing watch.

LOGIC:
  1. Pull all active TESS bookings with air segments
  2. Check fare_watch.db for each booking_ref
  3. If no watch exists: create one with provider=centrav + baseline=0 (needs first scan)
  4. Log new registrations to Telegram

Usage:
  .venv/bin/python scripts/tess_fare_watch_autoregister.py [--dry-run]
"""
import argparse
import json
import os
import sqlite3
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
DB_PATH = ROOT / "core" / "fare_watch" / "fare_watch.db"
TESS_DOSSIER_DIR = ROOT / "dossiers"
COMMANDER_ID = 7554895206


def log(m: str) -> None:
    print(f"[tess_autoregister] {m}", flush=True)


def _telegram(token: str, text: str) -> None:
    if not token:
        return
    try:
        data = urllib.parse.urlencode({"chat_id": COMMANDER_ID, "text": text}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage", data=data, method="POST"
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        log(f"Telegram failed: {e}")


def _load_token() -> str:
    token = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("TELEGRAM_D2MC2C_TOKEN", "")
    if not token:
        env = ROOT / ".env"
        if env.exists():
            for line in env.read_text().splitlines():
                if line.startswith("TELEGRAM_D2MC2C_TOKEN="):
                    token = line.split("=", 1)[1].strip().strip('"').strip("'")
    return token


def _get_existing_watch_booking_refs() -> set[str]:
    con = sqlite3.connect(str(DB_PATH))
    rows = con.execute(
        "SELECT booking_ref FROM fare_watches WHERE watch_type='flight' AND booking_ref != ''"
    ).fetchall()
    con.close()
    return {r[0] for r in rows}


def _register_watch(booking_ref: str, client: str, route: str, travel_date: str,
                    passengers: int, label: str, dry_run: bool) -> bool:
    watch_id = f"auto-{booking_ref}-{route.lower().replace(' ', '').replace('→', '-').replace('->', '-')}"
    watch_id = watch_id[:60]

    if dry_run:
        log(f"  DRY RUN — would register: {watch_id} ({route} {travel_date})")
        return True

    con = sqlite3.connect(str(DB_PATH))
    try:
        con.execute(
            """INSERT OR IGNORE INTO fare_watches
               (id, client, booking_ref, watch_type, label, provider, route, travel_date,
                passengers, current_price_pp, baseline_price_pp, notes, status)
               VALUES (?,?,?,'flight',?,?,?,?,?,0.0,0.0,?,?)""",
            (
                watch_id, client, booking_ref, label, "centrav", route, travel_date,
                passengers,
                "AUTO-REGISTERED from TESS booking. Baseline 0 — needs first Centrav scan.",
                "active",
            )
        )
        con.commit()
        log(f"  Registered: {watch_id}")
        return True
    except Exception as e:
        log(f"  Failed to register {watch_id}: {e}")
        return False
    finally:
        con.close()


def _scan_tess_bookings() -> list[dict]:
    """Scan dossier JSON files for air segment data. Returns list of flight records."""
    flights = []
    # Look in dossiers directory for JSON files with flight/air segment data
    for dossier in TESS_DOSSIER_DIR.glob("*.json"):
        try:
            data = json.loads(dossier.read_text())
            # Handle array or dict structures
            bookings = data if isinstance(data, list) else data.get("bookings", [])
            for booking in (bookings if isinstance(bookings, list) else []):
                seg_type = str(booking.get("type", "") or booking.get("segment_type", "")).lower()
                if "air" not in seg_type and "flight" not in seg_type:
                    continue
                ref = str(booking.get("booking_ref", "") or booking.get("id", ""))
                if not ref:
                    continue
                flights.append({
                    "booking_ref": ref,
                    "client": booking.get("client", dossier.stem),
                    "route": booking.get("route", booking.get("origin", "") + " → " + booking.get("dest", "")),
                    "travel_date": booking.get("travel_date", booking.get("departure_date", "")),
                    "passengers": int(booking.get("passengers", 2)),
                    "label": booking.get("label", f"{dossier.stem} — {ref}"),
                })
        except Exception:
            continue

    # Also check the structured TESS dossier sync files
    tess_sync = ROOT / "OpsCenter" / "tess_sync_latest.json"
    if tess_sync.exists():
        try:
            data = json.loads(tess_sync.read_text())
            for booking in data.get("bookings", []):
                if "air" in str(booking.get("type", "")).lower():
                    flights.append({
                        "booking_ref": str(booking.get("id", "")),
                        "client": booking.get("client_name", ""),
                        "route": booking.get("route", ""),
                        "travel_date": booking.get("travel_date", ""),
                        "passengers": int(booking.get("passengers", 2)),
                        "label": booking.get("description", ""),
                    })
        except Exception:
            pass

    return flights


def main() -> int:
    ap = argparse.ArgumentParser(description="Auto-register fare watches from TESS bookings")
    ap.add_argument("--dry-run", action="store_true", help="Report only, no DB writes")
    args = ap.parse_args()

    log("Scanning TESS bookings for unregistered flight segments...")
    existing_refs = _get_existing_watch_booking_refs()
    log(f"  {len(existing_refs)} booking refs already have watches")

    tess_flights = _scan_tess_bookings()
    log(f"  {len(tess_flights)} air segments found in TESS/dossiers")

    new_registrations = []
    for flight in tess_flights:
        ref = flight["booking_ref"]
        if not ref or ref in existing_refs:
            continue
        if not flight.get("route") or not flight.get("travel_date"):
            log(f"  SKIP {ref}: missing route or travel_date")
            continue
        log(f"  NEW: {ref} — {flight['route']} {flight['travel_date']}")
        ok = _register_watch(
            ref, flight["client"], flight["route"], flight["travel_date"],
            flight["passengers"], flight["label"], args.dry_run
        )
        if ok:
            new_registrations.append(flight)

    if new_registrations:
        token = _load_token()
        msg = (
            f"✈️ FARE WATCH AUTO-REGISTERED: {len(new_registrations)} new watches\n"
            + "\n".join(f"  • {f['route']} {f['travel_date']} (ref {f['booking_ref']})"
                       for f in new_registrations)
            + "\n\nBaseline = 0 until first Centrav scan."
        )
        _telegram(token, msg)
        log(f"Done — {len(new_registrations)} new watches registered")
    else:
        log("No new flight segments to register — all TESS air bookings already watched")

    return 0


if __name__ == "__main__":
    sys.exit(main())
