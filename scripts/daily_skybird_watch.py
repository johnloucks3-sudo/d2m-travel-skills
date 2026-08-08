#!/usr/bin/env python3
"""
daily_skybird_watch.py — Daily Skybird WINGS airfare watch.

Runs configured route scans (one-way / round-trip / multi-city), appends results
to a history file, and publishes an HTML scan page. Designed to run cheaply on a
daily timer (Haiku-tier friendly: one login + one API call per route).

Routes live in config at the bottom of this file (ROUTES). Add/edit freely.

Usage:
  python3 scripts/daily_skybird_watch.py                 # run all routes
  python3 scripts/daily_skybird_watch.py --routes outbound,return,multicity
  python3 scripts/daily_skybird_watch.py --dry
"""
import argparse
import datetime
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

import skybird_scan as sc

ROOT = pathlib.Path(__file__).resolve().parent.parent
HISTORY = ROOT / "data" / "airfare" / "skybird_history.jsonl"
REPORT = ROOT / "output" / "skybird_airfare_scan.html"

# ── CONFIGURED ROUTES (edit here) ───────────────────────────────────────────
ROUTES = [
    # ── Loucks — Silver Nova May 2027 ──────────────────────────────────────
    {"name": "silver-nova-outbound", "type": "oneway", "from": "DEN", "to": "VCE",
     "date": "2027-05-01", "cls": "Business", "adults": 2, "limit": 10},
    {"name": "silver-nova-return", "type": "oneway", "from": "ATH", "to": "DEN",
     "date": "2027-05-30", "cls": "Business", "adults": 2, "limit": 10},
    {"name": "silver-nova-multicity", "type": "multicity",
     "legs": "DEN|2027-05-01|VCE; ATH|2027-05-30|DEN",
     "cls": "Business", "adults": 2, "limit": 10},
    {"name": "silver-nova-muc-out", "type": "multicity",
     "legs": "DEN|2027-05-01|MUC; ATH|2027-05-30|DEN",
     "cls": "Business", "adults": 2, "limit": 5},
    {"name": "silver-nova-munich-both", "type": "multicity",
     "legs": "DEN|2027-05-01|MUC; ATH|2027-05-30|MUC",
     "cls": "Business", "adults": 2, "limit": 5},
    {"name": "silver-nova-icelandair", "type": "multicity",
     "legs": "DEN|2027-05-01|KEF; ATH|2027-05-30|DEN",
     "cls": "Business", "adults": 2, "limit": 5},
    # ── Loucks — Grandeur Panama Dec 2026 (2 new legs + returns) ───────────
    {"name": "grandeur-leg1-cos-iad", "type": "oneway", "from": "COS", "to": "IAD",
     "date": "2026-12-21", "cls": "Economy", "adults": 2, "limit": 10},
    {"name": "grandeur-leg1-cos-dca", "type": "oneway", "from": "COS", "to": "DCA",
     "date": "2026-12-21", "cls": "Economy", "adults": 2, "limit": 10},
    {"name": "grandeur-leg1-den-iad", "type": "oneway", "from": "DEN", "to": "IAD",
     "date": "2026-12-21", "cls": "Economy", "adults": 2, "limit": 10},
    {"name": "grandeur-leg1-den-dca", "type": "oneway", "from": "DEN", "to": "DCA",
     "date": "2026-12-21", "cls": "Economy", "adults": 2, "limit": 10},
    {"name": "grandeur-leg2-iad-mia", "type": "oneway", "from": "IAD", "to": "MIA",
     "date": "2026-12-27", "cls": "Economy", "adults": 2, "limit": 10},
    {"name": "grandeur-leg2-iad-fll", "type": "oneway", "from": "IAD", "to": "FLL",
     "date": "2026-12-27", "cls": "Economy", "adults": 2, "limit": 10},
    {"name": "grandeur-leg2-dca-mia", "type": "oneway", "from": "DCA", "to": "MIA",
     "date": "2026-12-27", "cls": "Economy", "adults": 2, "limit": 10},
    {"name": "grandeur-leg2-dca-fll", "type": "oneway", "from": "DCA", "to": "FLL",
     "date": "2026-12-27", "cls": "Economy", "adults": 2, "limit": 10},
    {"name": "grandeur-lax-cos", "type": "oneway", "from": "LAX", "to": "COS",
     "date": "2027-01-14", "cls": "Economy", "adults": 2, "limit": 10},
    {"name": "grandeur-sna-cos", "type": "oneway", "from": "SNA", "to": "COS",
     "date": "2027-01-14", "cls": "Economy", "adults": 2, "limit": 10},
    # ── Kuklinski — Viking Mars Panama Dec 2026 ────────────────────────────
    {"name": "kuklinski-ric-pty", "type": "oneway", "from": "RIC", "to": "PTY",
     "date": "2026-12-16", "cls": "Economy", "adults": 4, "limit": 10},
    {"name": "kuklinski-fll-ric", "type": "oneway", "from": "FLL", "to": "RIC",
     "date": "2026-12-27", "cls": "Economy", "adults": 4, "limit": 10},
    # ── Morton — RSW→PTY Dec 2026 ─────────────────────────────────────────
    {"name": "morton-rsw-pty", "type": "oneway", "from": "RSW", "to": "PTY",
     "date": "2026-12-16", "cls": "Economy", "adults": 2, "limit": 10},
    # ── McLeod — MIA→DEN Dec 2026 ─────────────────────────────────────────
    {"name": "mcleod-mia-den", "type": "oneway", "from": "MIA", "to": "DEN",
     "date": "2026-12-29", "cls": "Economy", "adults": 2, "limit": 10},
    # ── Spencer — European legs Jun/Jul 2027 ───────────────────────────────
    {"name": "spencer-den-fco-tim", "type": "oneway", "from": "DEN", "to": "FCO",
     "date": "2027-06-11", "cls": "Business", "adults": 4, "limit": 10},
    {"name": "spencer-den-fco-pe", "type": "oneway", "from": "DEN", "to": "FCO",
     "date": "2027-06-11", "cls": "Business", "adults": 8, "limit": 10},
    {"name": "spencer-fco-den-tim", "type": "oneway", "from": "FCO", "to": "DEN",
     "date": "2027-06-23", "cls": "Business", "adults": 4, "limit": 10},
    {"name": "spencer-zrh-den-pe", "type": "oneway", "from": "ZRH", "to": "DEN",
     "date": "2027-07-02", "cls": "Business", "adults": 8, "limit": 10},
]


def run_one(session, route):
    if route.get("type") == "multicity":
        legs = [dict(zip(("from", "date", "to"), [p.strip() for p in L.split("|")]))
                for L in route["legs"].split(";")]
        return sc.search(session, "", "", "", "", route["cls"], route.get("adults", 2),
                         limit=route.get("limit", 10), legs=legs)
    return sc.search(session, route["from"], route["to"], route["date"],
                     route.get("ret", ""), route["cls"], route.get("adults", 2),
                     limit=route.get("limit", 10), legs=None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--routes", default="", help="comma-separated route names to run (default: all)")
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    selected = [r for r in ROUTES if not args.routes or r["name"] in args.routes.split(",")]
    if args.dry:
        print("Routes:")
        for r in selected:
            print("  ", r["name"], r.get("type"), r.get("from") or r.get("legs"))
        return 0

    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    session = sc.login()
    today = datetime.date.today().isoformat()
    all_results = {}

    for route in selected:
        try:
            res = run_one(session, route)
            best = res[0] if res else None
            entry = {
                "ts": datetime.datetime.now().isoformat(),
                "route": route["name"],
                "query": {k: v for k, v in route.items() if k != "name"},
                "count": len(res),
                "best": {k: best.get(k) for k in
                         ("airline", "route", "price_pp", "price_n", "dep_dt", "arr_dt", "stops", "total_duration")
                         } if best else None,
                "results": res,
            }
            with open(HISTORY, "a") as f:
                f.write(json.dumps(entry) + "\n")
            all_results[route["name"]] = entry
            print(f"{route['name']}: {len(res)} flights · best "
                  f"${best['price_pp']:,.2f} pp {best['route']}" if best else f"{route['name']}: 0 flights")
        except Exception as e:
            print(f"{route['name']}: ERROR {e}")
            all_results[route["name"]] = {"ts": datetime.datetime.now().isoformat(), "error": str(e)}

    _render_report(all_results, today)
    print(f"\nHistory -> {HISTORY}\nReport  -> {REPORT}")
    return 0


def _render_report(all_results, today):
    rows = ""
    for name, e in all_results.items():
        if e.get("error"):
            rows += f"<tr><td>{name}</td><td colspan=5 style='color:#c00'>{e['error']}</td></tr>"
            continue
        b = e.get("best") or {}
        rows += (f"<tr><td>{name}</td><td>{b.get('airline','—')}</td><td>{b.get('route','—')}</td>"
                 f"<td>{b.get('stops','—')}</td><td>{b.get('dep_dt','—')}</td>"
                 f"<td>${b.get('price_pp',0):,.2f}</td></tr>")
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Skybird Airfare Scan — {today}</title>
<style>body{{font-family:Georgia,serif;background:#f7f3ea;color:#07076b;margin:2rem}}
h1{{color:#0000ff}}table{{border-collapse:collapse;width:100%;background:#fff}}
th,td{{border:1px solid #a8c4f0;padding:8px;text-align:left}}th{{background:#07076b;color:#fff}}
tr:nth-child(even){{background:#e8f1ff}}</style></head><body>
<h1>Skybird WINGS Airfare — Daily Scan</h1>
<p>Best fare per route · {today} · {datetime.datetime.now().strftime("%H:%M MT")} · live B2B (MyWingsBooking)</p>
<table><tr><th>Route</th><th>Airline</th><th>Itinerary</th><th>Stops</th><th>Dep</th><th>Best /pp</th></tr>{rows}</table>
<p style="color:#777">Prices per person, Business cabin unless noted. Verify at booking — fares move. Full detail in JSON history.</p>
</body></html>"""
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(html)


if __name__ == "__main__":
    sys.exit(main())
