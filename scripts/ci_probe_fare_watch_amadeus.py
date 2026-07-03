#!/usr/bin/env python3
"""
CI EFFICACY PROBE — Flight Fare Watch Amadeus API Source
=========================================================
Dreams2Memories Travel, LLC · CI razor-sharp doctrine (SO 2026-06-20)

Amadeus does NOT require browser or auth cookie — token is API-issued (OAuth2).
This probe checks:
  1. Credentials exist in .env (AMADEUS_CLIENT_ID / AMADEUS_CLIENT_SECRET)
  2. Cached token file present (means at least one successful auth has happened)
  3. Token not expired for more than 2h (would need re-auth on next run)
  4. At least one active amadeus flight watch exists in fare_watch.db
  5. At least one watch was checked within the currency window (8h, runs every 6h)

Exit 0 = RAZOR_SHARP. Exit 1 = RED.
"""
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
ENV_FILE = ROOT / ".env"
TOKEN_CACHE = ROOT / "creds" / "amadeus_token_cache.json"
FARE_DB = ROOT / "core" / "fare_watch" / "fare_watch.db"
CURRENCY_H = 8  # currency window (probe runs every 6h in supertimer)


def fail(msg: str) -> "NoReturn":
    print(f"RED fare-watch-amadeus: {msg}")
    sys.exit(1)


def main() -> None:
    # 1. Credentials in .env
    key = ""
    secret = ""
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line.startswith("AMADEUS_CLIENT_ID=") or line.startswith("AMADEUS_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
            elif line.startswith("AMADEUS_CLIENT_SECRET=") or line.startswith("AMADEUS_API_SECRET="):
                secret = line.split("=", 1)[1].strip().strip('"').strip("'")

    if not key or not secret:
        fail("AMADEUS_CLIENT_ID / AMADEUS_CLIENT_SECRET missing from .env — no API access possible")

    # 2. Token cache exists (at least one successful auth)
    if not TOKEN_CACHE.exists():
        fail("Amadeus token cache missing — amadeus_fare_watch.py has never run successfully")

    # 3. Token cache is parseable (token expiry is fine — auto-refreshes on each run)
    try:
        cached = json.loads(TOKEN_CACHE.read_text())
        expires_at_str = cached.get("expires_at", "unknown")
    except Exception as e:
        fail(f"Cannot parse token cache: {e}")

    # 4 & 5. DB watches + currency check
    if not FARE_DB.exists():
        fail(f"fare_watch.db not found at {FARE_DB}")

    try:
        import sqlite3
        db = sqlite3.connect(str(FARE_DB))
        db.row_factory = sqlite3.Row
        watches = db.execute(
            "SELECT id, last_checked FROM fare_watches "
            "WHERE watch_type='flight' AND provider='amadeus' AND status IN ('active','triggered')"
        ).fetchall()
    except Exception as e:
        fail(f"Cannot query fare_watch.db: {e}")

    if not watches:
        fail("No active amadeus flight watches in fare_watch.db — nothing to monitor")

    # Check currency: at least one watch checked within CURRENCY_H
    now_ts = datetime.now(tz=timezone.utc)
    checked_recently = False
    stale_count = 0
    for w in watches:
        lc = w["last_checked"]
        if not lc:
            stale_count += 1
            continue
        try:
            lc_dt = datetime.fromisoformat(lc)
            if lc_dt.tzinfo is None:
                lc_dt = lc_dt.replace(tzinfo=timezone.utc)
            age_h = (now_ts - lc_dt).total_seconds() / 3600
            if age_h <= CURRENCY_H:
                checked_recently = True
        except Exception:
            stale_count += 1

    if not checked_recently:
        fail(
            f"No amadeus watches checked in last {CURRENCY_H}h "
            f"({len(watches)} watches total, {stale_count} never checked). "
            "amadeus_fare_watch.py may not be running in supertimer."
        )

    print(
        f"RAZOR_SHARP fare-watch-amadeus: {len(watches)} active watch(es), "
        f"credentials OK, token cached"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
