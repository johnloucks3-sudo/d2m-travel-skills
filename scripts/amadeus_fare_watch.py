#!/usr/bin/env python3
"""
amadeus_fare_watch.py — Amadeus Flight Offers Search API integration.
FIX-9 2026-06-27 (Wing Exercise — BURNING HOT CI).
Updated 2026-06-28: added --run-all mode for supertimer invocation.

Amadeus free developer tier: 2,000 calls/month, no auth cookies, no reCAPTCHA.
Provides a structurally independent flight price source — no browser, no session.

ENV SETUP:
  .env must contain:
    AMADEUS_CLIENT_ID=...
    AMADEUS_CLIENT_SECRET=...

USAGE (single search):
  .venv/bin/python scripts/amadeus_fare_watch.py --origin DEN --dest GRB --date 2026-09-06 --return-date 2026-09-14
  .venv/bin/python scripts/amadeus_fare_watch.py --origin DEN --dest VCE --date 2027-04-30 --cabin BUSINESS

USAGE (supertimer / run all active amadeus watches from DB):
  .venv/bin/python scripts/amadeus_fare_watch.py          # no args = run-all
  .venv/bin/python scripts/amadeus_fare_watch.py --run-all
"""
import argparse
import json
import os
import re
import sqlite3
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
ENV_FILE = ROOT / ".env"
TOKEN_CACHE = ROOT / "creds" / "amadeus_token_cache.json"
FARE_DB = ROOT / "core" / "fare_watch" / "fare_watch.db"
ALERT_DEDUP_FILE = ROOT / "OpsCenter" / "state" / "amadeus_fare_alert_dedup.json"
AMADEUS_AUTH = "https://test.api.amadeus.com/v1/security/oauth2/token"
AMADEUS_SEARCH = "https://test.api.amadeus.com/v2/shopping/flight-offers"


def _load_alert_dedup() -> dict:
    if ALERT_DEDUP_FILE.exists():
        try:
            return json.loads(ALERT_DEDUP_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_alert_dedup(dedup: dict) -> None:
    ALERT_DEDUP_FILE.parent.mkdir(parents=True, exist_ok=True)
    ALERT_DEDUP_FILE.write_text(json.dumps(dedup, indent=2), encoding="utf-8")


# ── credentials ──────────────────────────────────────────────────────────────

def _load_env() -> tuple[str, str]:
    # M5: prefer Infisical (loud-fails on rotation) → os.environ → .env file (fallback chain).
    try:
        from core.secrets.infisical_client import get_secret
        key = get_secret("AMADEUS_CLIENT_ID") or get_secret("AMADEUS_API_KEY") or ""
        secret = get_secret("AMADEUS_CLIENT_SECRET") or get_secret("AMADEUS_API_SECRET") or ""
        if key and secret:
            return key, secret
    except Exception:
        pass
    key = os.environ.get("AMADEUS_CLIENT_ID", "") or os.environ.get("AMADEUS_API_KEY", "")
    secret = os.environ.get("AMADEUS_CLIENT_SECRET", "") or os.environ.get("AMADEUS_API_SECRET", "")
    if not key and ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line.startswith("AMADEUS_CLIENT_ID=") or line.startswith("AMADEUS_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
            elif line.startswith("AMADEUS_CLIENT_SECRET=") or line.startswith("AMADEUS_API_SECRET="):
                secret = line.split("=", 1)[1].strip().strip('"').strip("'")
    return key, secret


def _get_token(key: str, secret: str) -> str:
    if TOKEN_CACHE.exists():
        try:
            cached = json.loads(TOKEN_CACHE.read_text())
            if datetime.fromisoformat(cached["expires_at"]) > datetime.now():
                return cached["token"]
        except Exception:
            pass

    data = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": key,
        "client_secret": secret,
    }).encode()
    req = urllib.request.Request(AMADEUS_AUTH, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = json.loads(resp.read())

    token = body["access_token"]
    expires_at = (datetime.now() + timedelta(seconds=int(body.get("expires_in", 1740)) - 60)).isoformat()
    TOKEN_CACHE.parent.mkdir(exist_ok=True)
    TOKEN_CACHE.write_text(json.dumps({"token": token, "expires_at": expires_at}, indent=2))
    return token


# ── search ────────────────────────────────────────────────────────────────────

def search_flights(origin: str, dest: str, depart_date: str,
                   return_date: str = None, adults: int = 2,
                   cabin: str = "ECONOMY") -> dict:
    key, secret = _load_env()
    if not key or not secret:
        return {
            "status": "no_credentials",
            "error": (
                "AMADEUS_CLIENT_ID / AMADEUS_CLIENT_SECRET not set in .env. "
                "Register at https://developers.amadeus.com/register (free). "
                "Add AMADEUS_CLIENT_ID and AMADEUS_CLIENT_SECRET to .env."
            ),
        }

    try:
        token = _get_token(key, secret)
        params = {
            "originLocationCode": origin.upper(),
            "destinationLocationCode": dest.upper(),
            "departureDate": depart_date,
            "adults": adults,
            "travelClass": cabin.upper(),
            "currencyCode": "USD",
            "max": 5,
        }
        if return_date:
            params["returnDate"] = return_date

        url = AMADEUS_SEARCH + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read())

        offers = body.get("data", [])
        if not offers:
            return {"status": "no_results", "origin": origin, "dest": dest, "date": depart_date}

        prices = []
        for offer in offers:
            total = float(offer["price"]["grandTotal"])
            pp = total / adults
            prices.append(pp)

        best_pp = min(prices)
        return {
            "status": "ok",
            "source": "amadeus",
            "origin": origin,
            "dest": dest,
            "depart_date": depart_date,
            "return_date": return_date,
            "adults": adults,
            "cabin": cabin,
            "best_fare_pp": best_pp,
            "offers_checked": len(offers),
            "checked_at": datetime.now().isoformat(),
        }

    except Exception as e:
        return {"status": "error", "error": str(e)}


# ── DB helpers ────────────────────────────────────────────────────────────────

def _parse_route(route: str) -> tuple[str, str]:
    """Extract (origin_iata, dest_iata) from route like 'DEN → GRB (RT ...)'."""
    m = re.search(r'\b([A-Z]{3})\s*[→\-]\s*([A-Z]{3})\b', route)
    if m:
        return m.group(1), m.group(2)
    raise ValueError(f"Cannot parse IATA codes from route: {route!r}")


def _parse_return_date(route: str, notes: str, depart_year: str = "") -> str | None:
    """Try to find return date in route/notes string."""
    # Pattern: "Return Sep 14 2026" in notes (with 4-digit year — most specific)
    m = re.search(r'\bReturn\s+([A-Za-z]{3})\s+(\d{1,2})\s+(\d{4})\b', notes, re.IGNORECASE)
    if m:
        try:
            return datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}", "%b %d %Y").strftime("%Y-%m-%d")
        except ValueError:
            pass

    # Pattern: "(RT ... / Sep 14 return)" in route — use depart_year as the year
    m = re.search(r'/\s*([A-Za-z]{3})\s+(\d{1,2})\s+return\)', route, re.IGNORECASE)
    if m and depart_year:
        try:
            return datetime.strptime(f"{m.group(1)} {m.group(2)} {depart_year}", "%b %d %Y").strftime("%Y-%m-%d")
        except ValueError:
            pass

    return None


def _is_business(label: str, notes: str) -> bool:
    for text in (label, notes):
        if re.search(r'\bbusiness\b', text, re.IGNORECASE):
            return True
    return False


def _send_telegram_alert(msg: str) -> None:
    try:
        bot_token = None
        chat_id = None
        if ENV_FILE.exists():
            for line in ENV_FILE.read_text().splitlines():
                line = line.strip()
                if line.startswith("TELEGRAM_BOT_TOKEN="):
                    bot_token = line.split("=", 1)[1].strip().strip('"').strip("'")
                elif line.startswith("TELEGRAM_CHAT_ID=") or line.startswith("COMMANDER_TELEGRAM_ID="):
                    chat_id = line.split("=", 1)[1].strip().strip('"').strip("'")
        if not bot_token or not chat_id:
            # Try wing pager
            try:
                wing_page = ROOT / "scripts" / "wing_page.py"
                if wing_page.exists():
                    import subprocess
                    subprocess.run(
                        [sys.executable, str(wing_page), msg[:4000]],
                        timeout=10, capture_output=True
                    )
            except Exception:
                pass
            return
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = urllib.parse.urlencode({"chat_id": chat_id, "text": msg[:4096], "parse_mode": "Markdown"}).encode()
        req = urllib.request.Request(url, data=data, method="POST")
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass


# ── run-all mode ──────────────────────────────────────────────────────────────

def run_all_watches() -> int:
    """Query DB for active amadeus flight watches and price each one."""
    if not FARE_DB.exists():
        print(f"[amadeus] fare_watch.db not found at {FARE_DB}")
        return 1

    db = sqlite3.connect(str(FARE_DB))
    db.row_factory = sqlite3.Row

    watches = db.execute(
        "SELECT * FROM fare_watches WHERE watch_type='flight' AND provider='amadeus' "
        "AND status IN ('active','triggered')"
    ).fetchall()

    if not watches:
        print("[amadeus] No active amadeus flight watches in DB")
        return 0

    print(f"[amadeus] Running {len(watches)} active amadeus watch(es)")

    alerts = []
    errors = []
    now_iso = datetime.now().isoformat()

    for w in watches:
        wid = w["id"]
        try:
            origin, dest = _parse_route(w["route"])
        except ValueError as e:
            errors.append(f"{wid}: {e}")
            continue

        depart_date = w["travel_date"]
        return_date = _parse_return_date(w["route"], w["notes"], depart_date[:4])
        adults = w["passengers"]
        cabin = "BUSINESS" if _is_business(w["label"], w["notes"]) else "ECONOMY"

        print(f"  [{wid}] {origin}→{dest} {depart_date} {cabin} {adults}pax", end=" ... ", flush=True)
        result = search_flights(origin, dest, depart_date, return_date=return_date,
                                adults=adults, cabin=cabin)

        if result["status"] == "no_credentials":
            print("NO CREDS")
            errors.append(f"{wid}: no credentials")
            break  # no point continuing

        if result["status"] == "no_results":
            print("no results")
            errors.append(f"{wid}: no Amadeus results (too far out or limited route coverage)")
            db.execute(
                "UPDATE fare_watches SET last_checked=? WHERE id=?",
                (now_iso, wid)
            )
            db.commit()
            continue

        if result["status"] == "error":
            print(f"ERROR: {result['error'][:80]}")
            errors.append(f"{wid}: {result['error'][:80]}")
            continue

        new_pp = result["best_fare_pp"]
        prev_pp = w["current_price_pp"]
        baseline = w["baseline_price_pp"]
        alert_below = w["alert_below"]
        alert_above = w["alert_above"]
        pct_change = ((new_pp - prev_pp) / prev_pp * 100) if prev_pp else 0

        alert_triggered = None
        if alert_below and new_pp <= alert_below:
            alert_triggered = f"BELOW ${alert_below:.0f} — BUY SIGNAL"
        elif alert_above and new_pp >= alert_above:
            alert_triggered = f"ABOVE ${alert_above:.0f} — URGENCY"

        print(f"${new_pp:.0f}/pp ({pct_change:+.1f}%) {'⚡ ' + alert_triggered if alert_triggered else ''}")

        # Update DB
        new_note = w["notes"]
        if f"{now_iso[:10]}:" not in new_note:
            new_note += (f" | {now_iso[:10]}: Amadeus ${new_pp:.0f}/pp {cabin.capitalize()} "
                         f"{origin}→{dest}")
        db.execute(
            "UPDATE fare_watches SET current_price_pp=?, last_checked=?, notes=?, "
            "status=? WHERE id=?",
            (new_pp, now_iso, new_note,
             "triggered" if alert_triggered else w["status"], wid)
        )
        db.execute(
            "INSERT INTO fare_history (watch_id, fare, change_pct, source, alert_triggered, notes) "
            "VALUES (?,?,?,?,?,?)",
            (wid, new_pp, pct_change, "sweep", alert_triggered, "source:amadeus")
        )
        db.commit()

        if alert_triggered:
            alerts.append({
                "id": wid,
                "label": w["label"],
                "prev": prev_pp,
                "new": new_pp,
                "pct": pct_change,
                "trigger": alert_triggered,
            })

    # Report — one-and-done (Commander 2026-07-04: "same quotes each day...
    # I only need to see it once until it changes"). alert_triggered above is
    # a LEVEL check (still below/above threshold), which stays true run after
    # run for a stable fare — same bug class fixed today in perx_intel_monitor.py.
    # Only actually send when the triggering price has moved since the last
    # alert for that watch id.
    if alerts:
        dedup = _load_alert_dedup()
        new_alerts = []
        for a in alerts:
            last = dedup.get(str(a["id"]), {}).get("last_price")
            if last is None or abs(last - a["new"]) >= 1.0:
                new_alerts.append(a)

        if new_alerts:
            lines = ["⚡ *FARE ALERT — Amadeus*"]
            for a in new_alerts:
                lines.append(
                    f"• *{a['label'][:60]}*\n"
                    f"  ${a['prev']:.0f} → ${a['new']:.0f}/pp ({a['pct']:+.1f}%) — {a['trigger']}"
                )
                dedup[str(a["id"])] = {"last_price": a["new"], "ts": now_iso}
            lines.append("_CHIEF SILVER — verified this run, new price since last alert_")
            msg = "\n".join(lines)
            print("\n" + msg)
            _send_telegram_alert(msg)
            _save_alert_dedup(dedup)
        else:
            print(f"\n{len(alerts)} watch(es) still past threshold, price unchanged since last alert — no re-send")
        return 2  # rc=2 = alerts found (supertimer allowed_rcs includes 2)

    if errors:
        for e in errors:
            print(f"  [!] {e}")
        return 1  # at least one errored

    return 0


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description="Amadeus flight fare search / watch runner")
    ap.add_argument("--run-all", action="store_true",
                    help="Run all active amadeus watches from fare_watch.db (default when no args given)")
    ap.add_argument("--origin")
    ap.add_argument("--dest")
    ap.add_argument("--date", help="Departure YYYY-MM-DD")
    ap.add_argument("--return-date", help="Return YYYY-MM-DD for round-trip")
    ap.add_argument("--adults", type=int, default=2)
    ap.add_argument("--cabin", default="ECONOMY")
    args = ap.parse_args()

    # No-args (supertimer) and explicit --run-all both run all watches
    if args.run_all or not any([args.origin, args.dest, args.date]):
        return run_all_watches()

    # Single-route search mode
    if not args.origin or not args.dest or not args.date:
        ap.error("--origin, --dest, and --date are all required for single-route search")

    result = search_flights(
        args.origin, args.dest, args.date,
        return_date=args.return_date,
        adults=args.adults,
        cabin=args.cabin,
    )
    print(json.dumps(result, indent=2))
    if result["status"] == "ok":
        print(f"\nBest fare: ${result['best_fare_pp']:.2f}/pp ({args.cabin})")
        return 0
    elif result["status"] == "no_credentials":
        print("\n[amadeus] Setup required — see script header for instructions.")
        return 2
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
