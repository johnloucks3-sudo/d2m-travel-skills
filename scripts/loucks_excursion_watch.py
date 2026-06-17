#!/usr/bin/env python3
"""
loucks_excursion_watch.py — weekly value-watch for the 3 ports still booked on
Silversea for the Loucks Silver Nova May 2027 voyage (booking 506101-26):

    Koper (Lipica / Lipizzaner)  · Silversea $149 pp
    Nafplion (Ancient Corinth + Corinth Canal) · Silversea $99 pp
    Patmos (Monastery of St John + Cave of the Apocalypse) · Silversea $79 pp

For each port it reuses the fixed GetYourGuide scraper (test_tour_scrapers.py),
finds the best LIKE-FOR-LIKE 3rd-party option, and compares it to:
  (a) the Silversea baseline, and
  (b) the best price seen on the previous run (state file).
It alerts the Commander on Telegram only when a NEW cheaper / better-value
option appears (improvement over last alert). It always logs.

The other two ports (Split, Crete) already have confirmed cheaper GYG swaps and
are not watched here.

Built 2026-06-17 by Hale (COS). Cadence: weekly via systemd user timer.
Mobility note: John prefers low-distance/seated; rating>=4.5 + short duration
preferred. Patmos GYG results are contaminated by "St. John, USVI" — filtered by
requiring 'patmos' in the tour URL.
"""
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
import urllib.request

THUNDERBIRD = Path("/home/john/Thunderbird")
sys.path.insert(0, str(THUNDERBIRD / "scripts"))
from test_tour_scrapers import run_tests  # noqa: E402  (the fixed GYG scraper)

STATE = THUNDERBIRD / "OpsCenter" / "loucks_excursion_watch.json"
LOG = THUNDERBIRD / "logs" / "loucks_excursion_watch.log"

# Port -> baseline + matching rules.
#   ss  = Silversea booked price per person (the number to beat)
#   kw  = keywords that make a 3rd-party tour a like-for-like match
#   url_must = substring required in the tour URL (anti-contamination)
PORTS = {
    "Koper": {
        "date": "2027-05-06", "ss": 149,
        "kw": ["lipica", "lipizz", "stud farm", "horse"],
        "url_must": None, "exp": "Lipizzaner stud farm",
    },
    "Nafplion": {
        "date": "2027-05-24", "ss": 99,
        "kw": ["corinth", "canal", "mycenae"],
        "url_must": None, "exp": "Ancient Corinth + Corinth Canal",
    },
    "Patmos": {
        "date": "2027-05-28", "ss": 79,
        "kw": ["patmos", "apocalyp", "monaster"],
        "url_must": "patmos", "exp": "Monastery of St John + Cave",
    },
}


def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    LOG.parent.mkdir(exist_ok=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def load_env() -> dict:
    env = {}
    p = THUNDERBIRD / ".env"
    if p.exists():
        for ln in p.read_text().splitlines():
            ln = ln.strip()
            if ln and not ln.startswith("#") and "=" in ln:
                k, _, v = ln.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def telegram(msg: str):
    env = load_env()
    tok = env.get("TELEGRAM_C2_BOT_TOKEN", "")
    chat = env.get("TELEGRAM_COMMANDER_ID", "")
    if not tok or not chat:
        log("WARN: missing Telegram creds — alert logged only")
        return
    body = json.dumps({"chat_id": chat, "text": msg, "disable_web_page_preview": True}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{tok}/sendMessage",
        data=body, headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=20)
        log("Telegram alert sent")
    except Exception as e:
        log(f"WARN: Telegram send failed: {e}")


def best_match(tours: list, cfg: dict):
    """Return the cheapest like-for-like tour dict, or None."""
    pool = []
    for t in tours:
        name = (t.get("name") or "").lower()
        url = (t.get("url") or "").lower()
        price = t.get("price_pp")
        if not price or t.get("per_group_price"):
            continue
        if cfg["url_must"] and cfg["url_must"] not in url:
            continue
        if not any(k in name for k in cfg["kw"]):
            continue
        pool.append(t)
    if not pool:
        return None
    pool.sort(key=lambda t: t["price_pp"])
    return pool[0]


async def scan_port(port: str, cfg: dict) -> dict:
    """Scrape one port and return {status, best:{...}|None}."""
    try:
        res = await run_tests(port, cfg["date"], "getyourguide",
                              " ".join(cfg["kw"][:3]))
    except Exception as e:
        log(f"{port}: scraper error: {e}")
        return {"status": "error", "best": None}
    gyg = res.get("getyourguide", {})
    status = gyg.get("status", "unknown")
    if status != "ok":
        log(f"{port}: GYG status={status} ({gyg.get('notes','')}) — no value read")
        return {"status": status, "best": None}
    bm = best_match(gyg.get("tours", []), cfg)
    if not bm:
        log(f"{port}: no like-for-like match in {len(gyg.get('tours', []))} tours")
    return {"status": "ok", "best": bm}


async def main():
    state = {}
    if STATE.exists():
        try:
            state = json.loads(STATE.read_text())
        except Exception:
            state = {}

    alerts = []
    run_ts = datetime.now().isoformat()
    for port, cfg in PORTS.items():
        out = await scan_port(port, cfg)
        prev = state.get(port, {})
        rec = {
            "last_run": run_ts,
            "status": out["status"],
            "silversea_pp": cfg["ss"],
            "best_price": prev.get("best_price"),
            "best_name": prev.get("best_name"),
            "best_url": prev.get("best_url"),
            "last_alert_price": prev.get("last_alert_price"),
        }
        bm = out["best"]
        if bm:
            price = bm["price_pp"]
            rec["best_price"] = price
            rec["best_name"] = bm.get("name")
            rec["best_url"] = bm.get("url")
            rec["best_rating"] = bm.get("rating")
            rec["best_duration"] = bm.get("duration")
            log(f"{port}: best like-for-like ${price:.0f} — {bm.get('name','')[:50]} "
                f"(Silversea ${cfg['ss']})")
            # Alert when cheaper than Silversea AND improved vs last alert
            cheaper_than_ss = price < cfg["ss"]
            prev_alert = prev.get("last_alert_price")
            improved = prev_alert is None or price < prev_alert - 0.01
            if cheaper_than_ss and improved:
                save = cfg["ss"] - price
                alerts.append(
                    f"• {port} ({cfg['exp']}): ${price:.0f} pp vs Silversea ${cfg['ss']} "
                    f"— save ~${save:.0f} pp\n    {bm.get('name','')[:60]}\n    {bm.get('url','')}"
                )
                rec["last_alert_price"] = price
        state[port] = rec

    STATE.write_text(json.dumps(state, indent=2))
    log(f"State saved → {STATE}")

    if alerts:
        msg = ("\U0001F985 EXCURSION VALUE WATCH — Loucks Silver Nova May 2027\n"
               "Cheaper/better-value 3rd-party options found vs your Silversea bookings:\n\n"
               + "\n".join(alerts)
               + "\n\nGYG = guest-arranged (no tender priority). Booking 506101-26.")
        telegram(msg)
    else:
        log("No new cheaper/better-value options this run — no alert.")


if __name__ == "__main__":
    asyncio.run(main())
