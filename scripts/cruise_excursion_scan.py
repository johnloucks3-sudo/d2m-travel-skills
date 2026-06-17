#!/usr/bin/env python3
"""
cruise_excursion_scan.py — guaranteed-return-to-ship excursion scanner for the
Loucks Silver Nova May 2027 voyage (booking 506101-26).

HARD CONSTRAINTS (Commander 2026-06-17):
  1. ONLY tours that MEET AT THE PORT/TENDER and carry a GUARANTEED RETURN TO SHIP.
     Sources: Shore Excursions Group (SEG) + ToursByLocals (TBL) — both guarantee
     return-to-ship + pier meet, so the source satisfies the filter.
  2. Search scope = the experience WE PICKED per port (e.g. Koper = Lipizzaner),
     PLUS one food/wine alternative. NOT every tour type.
  3. ZERO BASELINE — not anchored to the Silversea prices; rank fresh by value.
  4. All 21 itinerary ports (booked pick where booked, recommended pick where open).

Per port it scrapes the provider port page, keeps only tours matching the picked
experience keywords OR food/wine keywords, and returns best-value guaranteed
options. Ports with no provider page = coverage gap (reported).

Built 2026-06-17 by Hale (COS). Run standalone or via the weekly watch.
"""
import asyncio
import json
import re
from datetime import datetime
from pathlib import Path

THUNDERBIRD = Path("/home/john/Thunderbird")
OUT = THUNDERBIRD / "core" / "travel" / "data" / "loucks_cruise_excursions.json"
LOG = THUNDERBIRD / "logs" / "cruise_excursion_scan.log"
SEG = "https://www.shoreexcursionsgroup.com"

FOOD_KW = ["food", "wine", "winery", "olive oil", "tasting", "taste", "culinary",
           "gastronom", "cooking", "meze", "ouzo", "vineyard", "lunch", "brewery"]

# date, port label, SEG slug|None, tender?, picked-experience keywords
ITINERARY = [
    ("2027-05-06", "Koper",            "koper-shore-excursions",     False, ["lipizz", "lipica", "stud", "horse"]),
    ("2027-05-07", "Zadar",            "zadar-shore-excursions",     False, ["zadar", "old town", "walking", "panoram"]),
    ("2027-05-08", "Split",            "split-shore-excursions",     False, ["diocletian", "palace", "old town"]),
    ("2027-05-09", "Dubrovnik",        "dubrovnik-shore-excursions", False, ["panoram", "old town", "cavtat", "walking"]),
    ("2027-05-10", "Bari",             "bari-shore-excursions",      False, ["bari", "old town", "street"]),
    ("2027-05-11", "Kotor",            "kotor-shore-excursions",     False, ["budva", "kotor", "panoram", "coast", "bay"]),
    ("2027-05-13", "Katakolon",        "katakolon-shore-excursions", False, ["olympia"]),
    ("2027-05-14", "Gythion",          "gythion-shore-excursions",   True,  ["olive", "estate", "mani", "village"]),
    ("2027-05-15", "Athens (Piraeus)", "athens-shore-excursions",   False, ["athens", "acropolis", "plaka", "city"]),
    ("2027-05-16", "Paros",            "paros-shore-excursions",     True,  ["paros", "beach", "village", "naoussa"]),
    ("2027-05-17", "Crete (Souda)",    "chania-crete-shore-excursions",    False, ["chania", "winery", "olive", "cretan"]),
    ("2027-05-18", "Gythion",          "gythion-shore-excursions",   True,  ["diros", "cave", "mystras"]),
    ("2027-05-19", "Milos",            "milos-shore-excursions",     True,  ["milos", "island", "sarakiniko", "boat", "catamaran"]),
    ("2027-05-20", "Kusadasi",         "kusadasi-shore-excursions",  False, ["ephesus"]),
    ("2027-05-21", "Mykonos",          "mykonos-shore-excursions",   True,  ["mykonos", "panoram", "town", "beach"]),
    ("2027-05-22", "Athens (Piraeus)", "athens-shore-excursions",   False, ["sounio", "poseidon", "cape", "athens"]),
    ("2027-05-23", "Santorini",        "santorini-shore-excursions", True,  ["oia", "winery", "santorini", "caldera"]),
    ("2027-05-24", "Nafplion",         "nafplion-shore-excursions",  False, ["corinth", "canal", "mycenae", "nafplio"]),
    ("2027-05-26", "Bodrum",           "bodrum-turkey-excursions",    False, ["gulet", "boat", "coast", "cruise", "bodrum"]),
    ("2027-05-27", "Rhodes",           "rhodes-shore-excursions",    False, ["lindos", "rhodes", "panoram", "filerimos", "old town"]),
    ("2027-05-28", "Patmos",           "patmos-shore-excursions",    True,  ["monaster", "apocalyp", "patmos", "cave"]),
]


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
    tok, chat = env.get("TELEGRAM_C2_BOT_TOKEN", ""), env.get("TELEGRAM_COMMANDER_ID", "")
    if not tok or not chat:
        log("WARN: missing Telegram creds — alert logged only")
        return
    import urllib.request
    body = json.dumps({"chat_id": chat, "text": msg, "disable_web_page_preview": True}).encode()
    try:
        urllib.request.urlopen(urllib.request.Request(
            f"https://api.telegram.org/bot{tok}/sendMessage", data=body,
            headers={"Content-Type": "application/json"}), timeout=20)
        log("Telegram alert sent")
    except Exception as e:
        log(f"WARN: Telegram send failed: {e}")


def best_picked_price(port_rec: dict):
    pk = [t for t in port_rec.get("tours", []) if t.get("match") == "picked" and t.get("price_pp")]
    return min((t["price_pp"] for t in pk), default=None)


def parse_price(text: str):
    sale = re.search(r"Sale Price:\s*\$([\d,]+(?:\.\d+)?)", text)
    price = re.search(r"Price:\s*\$([\d,]+(?:\.\d+)?)", text)
    def f(m):
        return float(m.group(1).replace(",", "")) if m else None
    sv, lv = f(sale), f(price)
    return (sv if sv is not None else lv), lv


def bucket(name: str, picked_kw):
    nl = name.lower()
    if any(k in nl for k in picked_kw):
        return "picked"
    if any(k in nl for k in FOOD_KW):
        return "food/wine"
    return None


async def scrape_seg(page, slug: str, picked_kw):
    url = f"{SEG}/port/{slug}"
    try:
        resp = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)
        if resp and resp.status >= 400:
            return {"status": f"http_{resp.status}", "url": url, "tours": []}
        raw = await page.evaluate(r"""() => {
          const anchors = [...document.querySelectorAll("a[href*='/tour/']")];
          const seen = new Set(); const out = [];
          for (const a of anchors) {
            const href = (a.getAttribute('href')||'').split('?')[0];
            if (!href || seen.has(href)) continue; seen.add(href);
            let el = a, cont = a;
            for (let i=0;i<6&&el;i++){ if(/\$\s?\d/.test(el.innerText||'')){cont=el;break;} el=el.parentElement; }
            out.push({href, text: (cont.innerText||'').trim()});
          }
          return out;
        }""")
    except Exception as e:
        return {"status": f"error:{str(e)[:60]}", "url": url, "tours": []}

    tours = []
    for r in raw:
        text = r.get("text", "")
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if not lines:
            continue
        name = lines[0]
        if len(name) < 4 or "$" not in text:
            continue
        b = bucket(name, picked_kw)
        if not b:
            continue  # SCOPE: keep only picked-experience or food/wine matches
        sale, listp = parse_price(text)
        if sale is None:
            continue
        size = next((l.split(":", 1)[1].strip() for l in lines if l.upper().startswith("EXCURSION SIZE")), None)
        etype = next((l.split(":", 1)[1].strip() for l in lines if l.upper().startswith("EXCURSION TYPE")), None)
        reviews = next((int(re.search(r"(\d+)", l).group(1)) for l in lines if "review" in l.lower() and re.search(r"\d", l)), None)
        href = r["href"]
        tours.append({
            "name": name, "price_pp": sale,
            "list_price_pp": listp if listp != sale else None,
            "match": b, "size": size, "type": etype, "reviews": reviews,
            "guaranteed_return": True, "meets_at_port": True, "provider": "SEG",
            "url": f"{SEG}{href}" if href.startswith("/") else href,
        })
    tours.sort(key=lambda t: t["price_pp"])
    return {"status": "ok" if tours else "no_match", "url": url, "tours": tours}


# SEG-gap ports -> ToursByLocals /tours/{country}/{city}. TBL = private guided,
# return-to-ship guaranteed, but PRICED PER GROUP / quote-on-request (not in listing).
TBL_GAPS = {
    "Gythion":  ("greece", "gythio"),
    "Paros":    ("greece", "paros"),
    "Milos":    ("greece", "milos"),
    "Nafplion": ("greece", "nafplio"),
    "Patmos":   ("greece", "patmos"),
}
TBL = "https://www.toursbylocals.com"


async def scrape_tbl(page, country: str, city: str, picked_kw):
    """Coverage pass for SEG-gap ports. TBL prices are quote-based, so we capture
    the matching private tour (name/url/duration), not a clean per-person price."""
    url = f"{TBL}/tours/{country}/{city}"
    try:
        resp = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(4)
        if resp and resp.status >= 400:
            return {"status": f"http_{resp.status}", "url": url, "tours": []}
        raw = await page.evaluate(r"""() => {
          const out=[]; const seen=new Set();
          for (const a of document.querySelectorAll("a[href*='/tour-details/']")){
            const href=(a.getAttribute('href')||'').split('?')[0];
            if(!href||seen.has(href))continue;seen.add(href);
            const cont=a.closest('div,li,article')||a;
            out.push({href, text:(cont.innerText||'').trim()});
          }
          return out;
        }""")
    except Exception as e:
        return {"status": f"error:{str(e)[:60]}", "url": url, "tours": []}
    tours = []
    for r in raw:
        lines = [l.strip() for l in r["text"].split("\n") if l.strip()]
        name = next((l for l in lines if not l.lower().startswith("your guide") and len(l) > 8), None)
        if not name:
            continue
        b = bucket(name, picked_kw)
        if not b:
            continue
        dur = next((l for l in lines if re.search(r"\d+\s*(hours?|days?)", l, re.I)), None)
        href = r["href"]
        tours.append({
            "name": name, "match": b, "duration": dur, "price_pp": None,
            "price_note": "private/quote (per group)",
            "guaranteed_return": True, "meets_at_port": True, "provider": "ToursByLocals",
            "url": href if href.startswith("http") else f"{TBL}{href}",
        })
    return {"status": "ok" if tours else "no_match", "url": url, "tours": tours}


async def main():
    from playwright.async_api import async_playwright
    results = {"scanned_at": datetime.now().isoformat(),
               "sources": ["Shore Excursions Group", "ToursByLocals (gap ports, quote-priced)"],
               "constraint": "meets-at-port + guaranteed return-to-ship; picked experience + food/wine; zero baseline",
               "ports": []}
    # Prior run (for price-drop / new-coverage diff)
    prev = {}
    if OUT.exists():
        try:
            for pr in json.loads(OUT.read_text()).get("ports", []):
                prev[pr["port"] + pr["date"]] = {"status": pr.get("status"),
                                                 "best": best_picked_price(pr)}
        except Exception:
            prev = {}

    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-blink-features=AutomationControlled"])
        ctx = await b.new_context(user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        page = await ctx.new_page()
        for date, label, slug, tender, kw in ITINERARY:
            if not slug:
                results["ports"].append({"date": date, "port": label, "tender": tender, "status": "no_slug", "tours": []})
                continue
            res = await scrape_seg(page, slug, kw)
            # Fall back to ToursByLocals where SEG has no page / no match
            if res["status"] != "ok" and label in TBL_GAPS:
                country, city = TBL_GAPS[label]
                tbl = await scrape_tbl(page, country, city, kw)
                if tbl["status"] == "ok":
                    res = tbl
            picked = [t for t in res["tours"] if t["match"] == "picked"]
            food = [t for t in res["tours"] if t["match"] == "food/wine"]
            prov = res["tours"][0]["provider"] if res["tours"] else "—"
            best_p = (f"${picked[0]['price_pp']:.0f}" if picked and picked[0]["price_pp"] else
                      ("quote" if picked else "—"))
            log(f"{date} {label}: {res['status']} [{prov}] — picked {len(picked)} (best {best_p}), food {len(food)}")
            results["ports"].append({"date": date, "port": label, "tender": tender,
                                     "picked_kw": kw, **res})
            await asyncio.sleep(2)
        await b.close()
    # Diff vs prior run → alert on price drops (>=$5) or newly-found coverage
    alerts = []
    for pr in results["ports"]:
        key = pr["port"] + pr["date"]
        new_best = best_picked_price(pr)
        old = prev.get(key, {})
        old_best, old_status = old.get("best"), old.get("status")
        if new_best is not None and old_best is not None and new_best <= old_best - 5:
            alerts.append(f"• {pr['date'][5:]} {pr['port']}: now ${new_best:.0f} (was ${old_best:.0f})")
        elif new_best is not None and old_status not in (None, "ok") and old_best is None and key in prev:
            alerts.append(f"• {pr['date'][5:]} {pr['port']}: NEW guaranteed option ${new_best:.0f} (was none)")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2))
    ok = [p for p in results["ports"] if p["status"] == "ok"]
    gaps = [p for p in results["ports"] if p["status"] != "ok"]
    log(f"Saved → {OUT}")
    log(f"COVERAGE: {len(ok)}/{len(results['ports'])} ports matched. "
        f"Still-gap: {', '.join(p['port'] for p in gaps) or 'none'}")

    if alerts and prev:  # don't alert on the very first run (no prior)
        telegram("\U0001F6DF GUARANTEED-RETURN EXCURSION WATCH — Loucks Silver Nova May 2027\n"
                 "Cheaper/new guaranteed-return options vs last scan:\n\n" + "\n".join(alerts)
                 + "\n\nFull table: dossier · booking 506101-26.")
    else:
        log("No price drops / new coverage vs last run — no alert.")
    return results


if __name__ == "__main__":
    asyncio.run(main())
