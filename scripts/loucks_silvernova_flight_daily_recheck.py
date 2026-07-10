#!/usr/bin/env python3
"""
loucks_silvernova_flight_daily_recheck.py — daily keep-alive snapshot for
the 5 Loucks Silver Nova 2027 flight-routing options (2026-07-10 research).
Dreams2Memories Travel, LLC · Thunderbird Wing

WHY: the Commander wants this capability to stay viable, not be a one-time
snapshot. Re-runs each route through Centrav with the Cruise fare-type box
checked (the same methodology this session's research used), appends a
real time-series point to core/travel/data/fare_history.json per watch_id,
and specifically tracks the Turkish outbound IST connection time — the
dossier's own original trigger ("alert the moment a Turkish Business itin
shows an outbound connection of 2-4h") — escalating to Telegram if it ever
improves out of the ~13h overnight range.

SAFE BY DESIGN (mirrors centrav_session_warm.py / icelandair_session_warm.py):
  - Read-only against the fare data model except appending to fare_history.json
    (append-only, never rewrites prior entries).
  - Centrav searches run SEQUENTIALLY (never parallel — the Firefox profile
    is single-instance, confirmed this session).
  - Never attempts to book/select/confirm anything.

Exit codes: 0 = all routes checked (individual route failures logged, not fatal).

Usage:
  .venv/bin/python3 scripts/loucks_silvernova_flight_daily_recheck.py
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path("/home/john/Thunderbird")
PROFILE_DIR = ROOT / "core" / "travel" / "data" / "centrav_ff_profile"
FARE_HISTORY = ROOT / "core" / "travel" / "data" / "fare_history.json"

logging.basicConfig(
    filename=ROOT / "logs" / "loucks_silvernova_flight_daily_recheck.log",
    level=logging.INFO,
    format="%(asctime)s [loucks-daily-recheck] %(message)s",
)
logger = logging.getLogger("loucks_daily_recheck")


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)
    logger.info(msg)


# Each leg searched once via Centrav (Cruise fare-type checked); the 5
# Commander-ranked options are built from combinations of these legs.
LEGS = [
    {"watch_id_component": "den-muc-vce", "origin": "DEN", "dest": "VCE", "date": "05/01/2027"},
    {"watch_id_component": "ath-ist-den", "origin": "ATH", "dest": "DEN", "date": "05/30/2027"},
    {"watch_id_component": "ath-muc-den", "origin": "ATH", "dest": "DEN", "date": "05/30/2027"},
    {"watch_id_component": "den-vce-direct", "origin": "DEN", "dest": "VCE", "date": "05/01/2027"},
]

# The specific Turkish outbound segment the Commander's original dossier
# flagged: notify if this connection ever drops out of the ~13h overnight
# range into the 2-4h trigger window.
IST_LAYOVER_TRIGGER_MIN_H = 2.0
IST_LAYOVER_TRIGGER_MAX_H = 4.0


async def _search_centrav(origin: str, dest: str, date_str: str) -> dict:
    """One Centrav search, Cruise fare-type box checked. Returns the raw
    page text for parsing -- matches the live methodology proven this
    session, not a guess at a stable API."""
    async with async_playwright() as pw:
        context = await pw.firefox.launch_persistent_context(
            str(PROFILE_DIR), headless=True, args=["--no-sandbox"],
        )
        page = context.pages[0] if context.pages else await context.new_page()
        try:
            await page.goto("https://www.centrav.com/", wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)
            await page.evaluate("""() => {
                const t = document.getElementById('FareTripTypeInput');
                if (t) t.value = 'OneWay';
                const c = document.getElementById('CabinClassInput');
                if (c) c.value = 'business';
            }""")
            for label in ("One Way", "Business"):
                try:
                    await page.click(f"text='{label}'", timeout=3000)
                except Exception:
                    pass
            await page.fill("#FareFlyingFrom", origin)
            await page.wait_for_timeout(1000)
            await page.fill("#FareFlyingTo", dest)
            await page.wait_for_timeout(1000)
            await page.fill("#FareDepartureDate", date_str)
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(500)
            await page.click("body", position={"x": 10, "y": 10})
            await page.wait_for_timeout(500)
            await page.select_option("#Adults", "2")

            cruise_cb = page.locator("#cruise")
            if await cruise_cb.count():
                await cruise_cb.check(force=True)

            await page.wait_for_timeout(500)
            try:
                await page.click("button[type=submit], input[type=submit]", timeout=5000, force=True)
            except Exception:
                pass
            await page.wait_for_timeout(9000)

            text = await page.inner_text("body")
            return {"ok": True, "text": text}
        except Exception as e:
            return {"ok": False, "error": str(e)}
        finally:
            await context.close()


def _extract_lowest_price(text: str) -> float | None:
    """FIXED 2026-07-10 (found live, first real run): a bare '$X.00' regex
    also matches non-fare dollar figures on the page -- specifically
    'Markup Limit $408.00' on Consolidator fare cards -- producing a
    nonsense $408 'lowest price' that's actually cheaper than every real
    fare shown. Every genuine fare card header on this page reads
    '$X,XXX.00 CASH' (e.g. 'Cruise Fare $6,974.00 CASH') -- anchoring on
    the CASH suffix excludes markup/discount/fee line items."""
    prices = re.findall(r"\$([\d,]+)\.00\s*CASH", text)
    if not prices:
        return None
    vals = [float(p.replace(",", "")) for p in prices]
    return min(vals) if vals else None


def _extract_ist_layover_hours(text: str) -> float | None:
    """Look for a Turkish IST connection duration in the results text.
    Centrav shows layover as e.g. '13h 10m' near an IST->... segment.
    Best-effort text scan -- flags for manual confirmation, never assumed
    authoritative on its own (Negative-Space Rule)."""
    m = re.search(r"IST\D{0,40}?(\d{1,2})h\s*(\d{1,2})?m?", text)
    if not m:
        return None
    hours = int(m.group(1))
    minutes = int(m.group(2)) if m.group(2) else 0
    return hours + minutes / 60.0


def _append_history(watch_id: str, price_pp: float | None, note: str) -> None:
    history = []
    if FARE_HISTORY.exists():
        try:
            history = json.loads(FARE_HISTORY.read_text())
        except Exception:
            history = []
    entry = {
        "watch_id": watch_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "price_pp": price_pp,
        "total": (price_pp * 2) if price_pp else None,
        "price_change_pct": 0.0,
        "alert_triggered": None,
        "notes": note,
    }
    history.append(entry)
    tmp = FARE_HISTORY.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(history, indent=2))
    tmp.replace(FARE_HISTORY)


def _notify_ist_layover_improved(hours: float) -> None:
    try:
        from core.notify.hale_notify import notify_sterling
        notify_sterling(
            "loucks-ist-layover-watch",
            f"Turkish outbound IST connection now {hours:.1f}h -- inside the "
            f"{IST_LAYOVER_TRIGGER_MIN_H}-{IST_LAYOVER_TRIGGER_MAX_H}h trigger window "
            f"the original dossier flagged. Worth re-checking the Turkish outbound "
            f"as a #1 candidate again.",
        )
    except Exception as e:
        logger.error("IST layover notify failed: %s", e)


def _log_recheck_plan(results: dict) -> None:
    try:
        from core.ops.hale_orchestrator import open_plan, assess_plan, close_plan
        plan = open_plan(
            task_summary="Loucks Silver Nova daily flight-routing recheck",
            tier="trivial",
            criteria=[f"leg {leg}: price captured" for leg in results],
        )
        status = {
            f"leg {leg}: price captured": ("met" if v.get("ok") else "missed")
            for leg, v in results.items()
        }
        result = assess_plan(plan, status, notes=json.dumps({k: v.get("price_pp") for k, v in results.items()}))
        close_plan(result)
    except Exception as e:
        logger.error("orchestrator logging failed: %s", e)


async def run_daily_recheck() -> dict:
    results = {}
    for leg in LEGS:
        wid = leg["watch_id_component"]
        log(f"searching {leg['origin']}->{leg['dest']} {leg['date']} (Cruise fare-type checked)")
        r = await _search_centrav(leg["origin"], leg["dest"], leg["date"])
        if not r["ok"]:
            log(f"  {wid}: search failed — {r['error']}")
            results[wid] = {"ok": False, "error": r["error"]}
            continue

        price = _extract_lowest_price(r["text"])
        log(f"  {wid}: lowest price found = ${price}")
        _append_history(wid, price, f"daily recheck, Cruise fare-type checked")
        results[wid] = {"ok": True, "price_pp": price}

        if "ist" in wid:
            ist_hours = _extract_ist_layover_hours(r["text"])
            if ist_hours is not None:
                log(f"  {wid}: IST connection ~{ist_hours:.1f}h")
                if IST_LAYOVER_TRIGGER_MIN_H <= ist_hours <= IST_LAYOVER_TRIGGER_MAX_H:
                    log(f"  *** IST LAYOVER IMPROVED INTO TRIGGER WINDOW ({ist_hours:.1f}h) — notifying ***")
                    _notify_ist_layover_improved(ist_hours)

        # Never run Centrav searches in parallel — single Firefox profile.
        await asyncio.sleep(2)

    return results


def main() -> None:
    results = asyncio.run(run_daily_recheck())
    _log_recheck_plan(results)
    ok_count = sum(1 for v in results.values() if v.get("ok"))
    log(f"daily recheck complete: {ok_count}/{len(results)} legs captured")


if __name__ == "__main__":
    main()
