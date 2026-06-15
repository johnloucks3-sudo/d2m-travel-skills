#!/usr/bin/env python3
"""
ita_fare_watch_poll.py — Login-free flight fare watcher via ITA Matrix.
MISSION-206. Polls each provider=="ITA" watch's stored ita_url (LOW-FREQUENCY —
ITA rate-limits rapid repeats; run ~1x/day), reads the matrix-min per-person fare,
auto-seeds baselines, appends a trend point, and flags drop/spike alerts.

SAFE BY DESIGN: a throttled / empty poll SKIPS the watch — it never overwrites a
baseline or appends a bad history point. So a failed run today is harmless; the
next fresh run seeds it.

Usage:
  .venv/bin/python scripts/ita_fare_watch_poll.py            # poll all ITA watches
  .venv/bin/python scripts/ita_fare_watch_poll.py --id <watch_id>
  .venv/bin/python scripts/ita_fare_watch_poll.py --brief    # print brief block only
"""
import asyncio, json, re, sys, argparse, os
from pathlib import Path

# Date is injected (Date.now is unavailable in some harnesses); fall back to system.
import datetime
TODAY = datetime.date.today().isoformat()

ROOT = Path("/home/john/Thunderbird")

# Lock file: abort immediately if another instance is already running.
# Prevents concurrent Firefox spawns (which cause SIGSEGV on resource contention).
_LOCK = ROOT / "logs" / "ita_fare_watch.lock"
if _LOCK.exists():
    _lock_pid = None
    try:
        _lock_pid = int(_LOCK.read_text().strip())
    except Exception:
        pass
    _running = False
    if _lock_pid:
        try:
            os.kill(_lock_pid, 0)   # signal 0 = just check existence
            _running = True
        except (ProcessLookupError, PermissionError):
            pass
    if _running:
        print(f"SKIP: ita_fare_watch already running (PID {_lock_pid})")
        sys.exit(0)
    else:
        _LOCK.unlink(missing_ok=True)  # stale lock from crashed run
try:
    _LOCK.write_text(str(os.getpid()))
    import atexit
    atexit.register(lambda: _LOCK.unlink(missing_ok=True))
except Exception:
    pass
CFG = ROOT / "data" / "fare_watches.json"
SPACING_S = 75          # space polls to stay under ITA's rate limit
RENDER_WAIT_S = 180     # let the matrix compute — observed 2-5min in headless (was 24, too short)
ALERT_BAND = 0.10       # ±10% auto bands when seeding


def load():
    d = json.loads(CFG.read_text())
    if isinstance(d, list):
        return d, d, "list"
    key = next((k for k in ("watches", "fare_watches") if k in d), None)
    cont = d[key] if key else d
    return d, cont, ("list" if isinstance(cont, list) else "dict")


def watches(cont):
    return cont if isinstance(cont, list) else list(cont.values())


async def poll_url(url):
    """Navigate an ITA URL, return matrix-min per-person fare (int) or None.
    Uses element-based waiting — exits as soon as fare rows appear (up to RENDER_WAIT_S).
    ITA Matrix takes 2-5 min in headless; fixed sleep was too short and caused silent skips.
    """
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.firefox.launch(headless=True)
        try:
            pg = await (await b.new_context()).new_page()
            await pg.goto(url, wait_until="networkidle", timeout=60000)
            # Wait for fare content: poll every 5s up to RENDER_WAIT_S
            txt = ""
            for _ in range(RENDER_WAIT_S // 5):
                await pg.wait_for_timeout(5000)
                txt = await pg.inner_text("body")
                if re.search(r"\$[0-9]{2,3}(?:,[0-9]{3})?", txt):
                    break  # fares appeared — done waiting
            else:
                txt = await pg.inner_text("body")  # final read on timeout
        except Exception as e:
            print(f"    poll error: {e}")
            return None
        finally:
            await b.close()
    if "something went wrong" in txt.lower():
        return None
    fares = [int(m.replace(",", "")) for m in re.findall(r"\$([0-9]{2,3}(?:,[0-9]{3})?)", txt)]
    fares = [f for f in fares if 50 <= f <= 60000]
    return min(fares) if fares else None


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id"); ap.add_argument("--brief", action="store_true")
    args = ap.parse_args()

    doc, cont, mode = load()
    ita = [w for w in watches(cont)
           if isinstance(w, dict) and w.get("provider") == "ITA" and w.get("ita_url")
           and (not args.id or w.get("id") == args.id)]

    report = []
    for i, w in enumerate(ita):
        if not args.brief:
            print(f"[{i+1}/{len(ita)}] {w.get('label')}")
        fare = await poll_url(w["ita_url"])
        if fare is None:
            report.append((w, None, "skip (no result / throttled)"))
            if not args.brief:
                print("    → skipped (throttled/empty) — baseline untouched")
        else:
            base = w.get("baseline_price_pp")
            if not base:                       # auto-seed
                w["baseline_price_pp"] = fare
                w["alert_below"] = round(fare * (1 - ALERT_BAND), 2)
                w["alert_above"] = round(fare * (1 + ALERT_BAND), 2)
                base = fare
            w["current_price_pp"] = fare
            w.setdefault("history", []).append({"date": TODAY, "fare": fare})
            sig = ""
            if w.get("alert_below") and fare <= w["alert_below"]:
                sig = "🔔 DROP — book signal"
            elif w.get("alert_above") and fare >= w["alert_above"]:
                sig = "🔔 SPIKE — lock signal"
            report.append((w, fare, sig or "ok"))
            if not args.brief:
                print(f"    → ${fare}/pp (base ${base}) {sig}")
        if i < len(ita) - 1:
            await asyncio.sleep(SPACING_S)     # throttle spacing

    CFG.write_text(json.dumps(doc, indent=1))

    # brief block
    def spark(h):
        v = [x["fare"] for x in (h or [])][-7:]
        if len(v) < 2: return ""
        lo, hi = min(v), max(v); rng = (hi - lo) or 1
        bars = "▁▂▃▄▅▆▇"
        s = "".join(bars[int((x - lo) / rng * 6)] for x in v)
        arrow = "↓" if v[-1] < v[0] else ("↑" if v[-1] > v[0] else "→")
        return f"{s} {arrow}${abs(v[-1]-v[0])}"
    print("\n=== FARE WATCH — BRIEF BLOCK ===")
    for w, fare, sig in report:
        cur = f"${w.get('current_price_pp')}" if w.get("current_price_pp") else "—"
        print(f"• {w.get('label')}: {cur}/pp  {spark(w.get('history'))}  {sig if sig!='ok' else ''}".rstrip())


if __name__ == "__main__":
    asyncio.run(main())
