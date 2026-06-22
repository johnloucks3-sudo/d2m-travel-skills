#!/usr/bin/env python3
"""
ita_matrix.py — ITA Matrix flight search URL builder + Playwright scraper.

ITA Matrix (matrix.itasoftware.com, by Google) — the Wing's default flight
routing intelligence engine. No API, no auth. Drives headless Firefox.

IMPORTANT — Read before use:
  - Searches take 2–5 MINUTES in headless (ITA's matrix computation)
  - ITA rate-limits rapid repeats — space calls ≥75s apart
  - Premium fares (Business/First) aren't filed >~330 days out;
    for far-out searches use COACH or switch to Centrav
  - For far-out dates use Centrav; ITA = in-window fares + routing intel

Cabin codes: COACH / PREMIUM-COACH / BUSINESS / FIRST

Usage:
    from core.travel.ita_matrix import build_url, search_fare
    url = build_url("DEN", "VCE", "2026-12-16", cabin="BUSINESS", adults=2)
    fare = search_fare("DEN", "VCE", "2026-12-16", cabin="COACH")

CLI:
    python3 core/travel/ita_matrix.py DEN VCE 2026-12-16 COACH 2
    python3 core/travel/ita_matrix.py DEN VCE 2026-12-16 --url-only
    python3 core/travel/ita_matrix.py DEN VCE 2026-12-16 GRB 2026-09-14   # round-trip
"""
import asyncio
import base64
import json
import re

ITA_BASE = "https://matrix.itasoftware.com/flights?search="
RENDER_WAIT_S = 180      # ITA matrix computation: observed 2-5 min headless


def _slice(origin: str, dest: str, date: str) -> dict:
    return {
        "origin": [origin.upper()],
        "dest": [dest.upper()],
        "dates": {
            "searchDateType": "specific",
            "departureDate": date,          # YYYY-MM-DD
            "departureDateType": "depart",
            "departureDateModifier": "0",
            "departureDatePreferredTimes": [],
            "returnDateType": "depart",
            "returnDateModifier": "0",
            "returnDatePreferredTimes": [],
        },
    }


def build_url(origin: str, dest: str, date: str,
              cabin: str = "COACH", adults: int = 2,
              return_dest: str = None, return_date: str = None) -> str:
    """
    Build an ITA Matrix search URL.

    For one-way: origin/dest/date.
    For round-trip: also pass return_dest (usually = origin) and return_date.
    Returns a URL you can open in any browser or pass to search_fare().
    """
    if return_dest and return_date:
        trip_type = "round-trip"
        slices = [
            _slice(origin, dest, date),
            _slice(return_dest, origin, return_date),
        ]
    else:
        trip_type = "multi-city"  # ITA uses multi-city for one-way
        slices = [_slice(origin, dest, date)]

    payload = {
        "type": trip_type,
        "slices": slices,
        "options": {
            "cabin": cabin.upper(),
            "stops": "-1",
            "extraStops": "1",
            "allowAirportChanges": "true",
            "showOnlyAvailable": "true",
        },
        "pax": {"adults": str(adults)},
    }
    b64 = base64.b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    return f"{ITA_BASE}{b64}"


async def _poll_url(url: str, render_wait: int = RENDER_WAIT_S) -> int | None:
    """Navigate an ITA URL, wait for matrix to compute, return min per-person fare or None."""
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.firefox.launch(headless=True)
        try:
            pg = await (await b.new_context()).new_page()
            await pg.goto(url, wait_until="networkidle", timeout=60000)
            txt = ""
            for _ in range(render_wait // 5):
                await pg.wait_for_timeout(5000)
                txt = await pg.inner_text("body")
                if re.search(r"\$[0-9]{2,3}(?:,[0-9]{3})?", txt):
                    break
            else:
                txt = await pg.inner_text("body")
        except Exception as e:
            print(f"[ita_matrix poll error: {e}]")
            return None
        finally:
            await b.close()
    if "something went wrong" in txt.lower():
        return None
    fares = [int(m.replace(",", "")) for m in re.findall(r"\$([0-9]{2,3}(?:,[0-9]{3})?)", txt)]
    fares = [f for f in fares if 50 <= f <= 60000]
    return min(fares) if fares else None


def search_fare(origin: str, dest: str, date: str,
                cabin: str = "COACH", adults: int = 2,
                return_dest: str = None, return_date: str = None) -> dict:
    """
    Live fare search via ITA Matrix. Blocks 2–5 minutes while ITA computes.

    Returns {url, origin, dest, date, cabin, adults, min_fare, source}.
    min_fare is None if ITA returned no results or timed out.
    """
    url = build_url(origin, dest, date, cabin, adults, return_dest, return_date)
    min_fare = asyncio.run(_poll_url(url))
    return {
        "url": url,
        "origin": origin.upper(),
        "dest": dest.upper(),
        "date": date,
        "cabin": cabin,
        "adults": adults,
        "min_fare": min_fare,
        "source": "ita_matrix",
    }


def add_fare_watch(watch_id: str, origin: str, dest: str, date: str,
                   cabin: str = "COACH", adults: int = 2,
                   return_dest: str = None, return_date: str = None,
                   alert_low: float = None, alert_high: float = None) -> dict:
    """
    Register an ITA fare watch in the Wing's fare-watch store.
    The watch is polled by scripts/ita_fare_watch_poll.py (~1×/day).

    Returns the watch record that was saved.
    """
    import datetime
    from pathlib import Path

    store_path = Path("/home/john/Thunderbird/core/travel/data/fare_watches.json")
    store_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        store = json.loads(store_path.read_text()) if store_path.exists() else {"watches": []}
    except Exception:
        store = {"watches": []}
    if isinstance(store, list):
        store = {"watches": store}

    url = build_url(origin, dest, date, cabin, adults, return_dest, return_date)
    record = {
        "id": watch_id,
        "provider": "ITA",
        "origin": origin.upper(),
        "dest": dest.upper(),
        "date": date,
        "cabin": cabin,
        "adults": adults,
        "ita_url": url,
        "created": datetime.date.today().isoformat(),
        "baseline": None,
        "history": [],
    }
    if alert_low is not None:
        record["alert_low"] = alert_low
    if alert_high is not None:
        record["alert_high"] = alert_high

    # Remove existing watch with same id
    watches = store.get("watches", [])
    watches = [w for w in watches if w.get("id") != watch_id]
    watches.append(record)
    store["watches"] = watches
    store_path.write_text(json.dumps(store, indent=2))
    return record


if __name__ == "__main__":
    import sys

    args = sys.argv[1:]
    url_only = "--url-only" in args
    args = [a for a in args if a != "--url-only"]

    if len(args) < 3:
        print("Usage: ita_matrix.py ORIGIN DEST DATE [CABIN] [ADULTS]")
        print("       ita_matrix.py ORIGIN DEST OUTBOUND_DATE RETURN_DEST RETURN_DATE [CABIN] [ADULTS]")
        print("       Add --url-only to just print the URL")
        print("Cabin codes: COACH PREMIUM-COACH BUSINESS FIRST")
        sys.exit(1)

    origin, dest, date = args[0], args[1], args[2]

    # Detect round-trip: 5th arg looks like a date
    if len(args) >= 5 and re.match(r"\d{4}-\d{2}-\d{2}", args[4]):
        return_dest = args[3]
        return_date = args[4]
        cabin = args[5].upper() if len(args) > 5 else "COACH"
        adults = int(args[6]) if len(args) > 6 else 2
    else:
        return_dest = return_date = None
        cabin = args[3].upper() if len(args) > 3 else "COACH"
        adults = int(args[4]) if len(args) > 4 else 2

    url = build_url(origin, dest, date, cabin, adults, return_dest, return_date)
    print(f"ITA Matrix URL: {url}")

    if not url_only:
        print(f"\nSearching {origin}→{dest} {date} {cabin} ×{adults}...")
        print("(ITA Matrix takes 2–5 min to compute — please wait)")
        result = search_fare(origin, dest, date, cabin, adults, return_dest, return_date)
        fare = f"${result['min_fare']}" if result.get("min_fare") else "No fare returned"
        print(f"Min fare per person: {fare}")
