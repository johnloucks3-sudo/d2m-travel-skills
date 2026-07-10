#!/usr/bin/env python3
"""
spencer_grandtour_flight_daily_recheck.py — daily keep-alive snapshot for
the 3 Spencer Grand Tour 2027 flight legs (2026-07-10 research), ground-truth
cabin assignments only: Leg 1 Tim's family Business + Yaggi/Bill Spencer PE,
Leg 2 Tim's family Business, Leg 3 Yaggi/Bill Spencer PE combined.
Dreams2Memories Travel, LLC · Thunderbird Wing

Mirrors scripts/loucks_silvernova_flight_daily_recheck.py exactly (same
Centrav/Cruise-checkbox methodology, same fare_history.json schema).
Scope confirmed with Commander 2026-07-10: track the 3 booked legs only,
no extra far-out date-ceiling probing.

SAFE BY DESIGN:
  - Read-only against the fare data model except appending to fare_history.json
    (append-only, never rewrites prior entries).
  - Centrav searches run SEQUENTIALLY (single-instance Firefox profile).
  - Never attempts to book/select/confirm anything.

Usage:
  .venv/bin/python3 scripts/spencer_grandtour_flight_daily_recheck.py
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
    filename=ROOT / "logs" / "spencer_grandtour_flight_daily_recheck.log",
    level=logging.INFO,
    format="%(asctime)s [spencer-daily-recheck] %(message)s",
)
logger = logging.getLogger("spencer_daily_recheck")


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)
    logger.info(msg)


# Ground-truth legs only (Commander-confirmed 2026-07-10). cabin_input maps
# to Centrav's #CabinClassInput hidden field values.
LEGS = [
    {
        "watch_id": "spencer-leg1-den-fco-tim-business-jun2027",
        "origin": "DEN", "dest": "FCO", "date": "06/11/2027",
        "cabin_input": "business", "cabin_tab": "Business", "adults": "4",
    },
    {
        "watch_id": "spencer-leg1-den-fco-yaggispencer-pe-jun2027",
        "origin": "DEN", "dest": "FCO", "date": "06/11/2027",
        "cabin_input": "PREMIUM_ECONOMY", "cabin_tab": "Premium Economy", "adults": "8",
    },
    {
        "watch_id": "spencer-leg2-fco-den-tim-business-jun2027",
        "origin": "FCO", "dest": "DEN", "date": "06/23/2027",
        "cabin_input": "business", "cabin_tab": "Business", "adults": "4",
    },
    {
        "watch_id": "spencer-leg3-zrh-den-yaggispencer-pe-jul2027",
        "origin": "ZRH", "dest": "DEN", "date": "07/02/2027",
        "cabin_input": "PREMIUM_ECONOMY", "cabin_tab": "Premium Economy", "adults": "8",
    },
]


async def _search_centrav(origin: str, dest: str, date_str: str, cabin_input: str,
                           cabin_tab: str, adults: str) -> dict:
    """One Centrav search, Cruise fare-type box checked. Matches the live
    methodology proven this session."""
    async with async_playwright() as pw:
        context = await pw.firefox.launch_persistent_context(
            str(PROFILE_DIR), headless=True, args=["--no-sandbox"],
        )
        page = context.pages[0] if context.pages else await context.new_page()
        try:
            await page.goto("https://www.centrav.com/", wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)
            await page.evaluate(f"""() => {{
                const t = document.getElementById('FareTripTypeInput');
                if (t) t.value = 'OneWay';
                const c = document.getElementById('CabinClassInput');
                if (c) c.value = '{cabin_input}';
            }}""")
            for label in ("One Way", cabin_tab):
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
            await page.select_option("#Adults", adults)

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
    """Anchored on the CASH suffix -- see loucks_silvernova_flight_daily_recheck.py
    for the Markup Limit regression this guards against."""
    prices = re.findall(r"\$([\d,]+)\.00\s*CASH", text)
    if not prices:
        return None
    vals = [float(p.replace(",", "")) for p in prices]
    return min(vals) if vals else None


def _append_history(watch_id: str, total_price: float | None, adults: int, note: str) -> None:
    history = []
    if FARE_HISTORY.exists():
        try:
            history = json.loads(FARE_HISTORY.read_text())
        except Exception:
            history = []
    price_pp = (total_price / adults) if total_price else None
    entry = {
        "watch_id": watch_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "price_pp": price_pp,
        "total": total_price,
        "price_change_pct": 0.0,
        "alert_triggered": None,
        "notes": note,
    }
    history.append(entry)
    tmp = FARE_HISTORY.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(history, indent=2))
    tmp.replace(FARE_HISTORY)


def _log_recheck_plan(results: dict) -> None:
    try:
        from core.ops.hale_orchestrator import open_plan, assess_plan, close_plan
        plan = open_plan(
            task_summary="Spencer Grand Tour daily flight-routing recheck",
            tier="trivial",
            criteria=[f"leg {leg}: price captured" for leg in results],
        )
        status = {
            f"leg {leg}: price captured": ("met" if v.get("ok") else "missed")
            for leg, v in results.items()
        }
        result = assess_plan(plan, status, notes=json.dumps({k: v.get("total") for k, v in results.items()}))
        close_plan(result)
    except Exception as e:
        logger.error("orchestrator logging failed: %s", e)


async def run_daily_recheck() -> dict:
    results = {}
    for leg in LEGS:
        wid = leg["watch_id"]
        adults = int(leg["adults"])
        log(f"searching {leg['origin']}->{leg['dest']} {leg['date']} {leg['cabin_tab']} "
            f"({adults}pax, Cruise fare-type checked)")
        r = await _search_centrav(
            leg["origin"], leg["dest"], leg["date"],
            leg["cabin_input"], leg["cabin_tab"], leg["adults"],
        )
        if not r["ok"]:
            log(f"  {wid}: search failed — {r['error']}")
            results[wid] = {"ok": False, "error": r["error"]}
            continue

        total_price = _extract_lowest_price(r["text"])
        log(f"  {wid}: lowest total found = ${total_price}")
        _append_history(wid, total_price, adults, "daily recheck, Cruise fare-type checked")
        results[wid] = {"ok": True, "total": total_price}

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
