#!/usr/bin/env python3
"""flight_route_visuals_refresh.py — Track B workflow integration.

Injects the three dataviz components (route map SVG, fare heatmap, diverging
price-trend chart — see docs/DATAVIZ_FLIGHT_CHARTS_SPEC_20260710.md) into the
existing per-trip flight-option artifacts, reading the same data files the
daily recheck scripts already write to:
  - core/travel/data/fare_watches.json   (route, baseline_price_pp, current_price_pp)
  - core/travel/data/fare_history.json   (per-day price snapshots)

Idempotent: inserts between HTML comment markers and replaces on every run,
so this can run after every daily recheck (loucks_silvernova_flight_daily_recheck.py,
spencer_grandtour_flight_daily_recheck.py) without growing the file or
touching the existing trend chart / pick tables already in those artifacts
(no regression — this only appends a new section).

Run: python3 scripts/flight_route_visuals_refresh.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
sys_path_note = None  # (no sys.path hack needed — run from ROOT or via absolute imports below)

import sys
sys.path.insert(0, str(ROOT))

from core.dataviz.great_circle_map import render_route_map  # noqa: E402

FARE_WATCHES = ROOT / "core" / "travel" / "data" / "fare_watches.json"
FARE_HISTORY = ROOT / "core" / "travel" / "data" / "fare_history.json"
HEATMAP_JS = ROOT / "app" / "static" / "js" / "dataviz" / "fare_heatmap.js"
TREND_JS = ROOT / "app" / "static" / "js" / "dataviz" / "price_trend_chart.js"

START_MARK = "<!-- D2M-DATAVIZ-START (scripts/flight_route_visuals_refresh.py — do not hand-edit, regenerated) -->"
END_MARK = "<!-- D2M-DATAVIZ-END -->"


def _load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def _parse_route(route: str) -> tuple[str, str] | None:
    """'DEN>VCE' or 'DEN→VCE' -> ('DEN','VCE')."""
    if not route:
        return None
    for sep in ("→", ">"):
        if sep in route:
            o, d = route.split(sep, 1)
            return o.strip().upper(), d.strip().upper()
    return None


def _history_points(history: list[dict], watch_id: str) -> list[dict]:
    pts = [e for e in history if e.get("watch_id") == watch_id and e.get("price_pp")]
    pts.sort(key=lambda e: e["timestamp"])
    return [{"date": e["timestamp"][:10], "price_pp": e["price_pp"]} for e in pts]


def build_section(
    trip_label: str,
    legs: list[dict],  # [{"watch_id":..., "label":..., "origin":..., "dest":...}]
    watches: dict,
    history: list[dict],
    trend_watch_id: str,
    heatmap_js_src: str,
    trend_js_src: str,
    mode: str = "light",
) -> str:
    """legs entries whose origin/dest are known render a route map; others skip."""
    route_maps_html = []
    seen_pairs = set()
    for leg in legs:
        pair = (leg["origin"], leg["dest"])
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        result = render_route_map(leg["origin"], leg["dest"], width=420, height=240, title=f"{leg['origin']} → {leg['dest']}")
        route_maps_html.append(f'<div style="display:inline-block;margin:8px;">{result.svg}</div>')

    # heatmap: rows = leg label, cols = recent dates present in history, cells = price
    cells = []
    all_dates = set()
    for leg in legs:
        pts = _history_points(history, leg["watch_id"])
        for p in pts:
            all_dates.add(p["date"])
            cells.append({"row": leg["label"], "col": p["date"], "price": p["price_pp"], "meta": f"{leg['origin']}→{leg['dest']}"})
    cols = sorted(all_dates)
    rows = [leg["label"] for leg in legs]
    heatmap_data = {"rows": rows, "cols": cols, "rowLabel": "Route", "colLabel": "Date", "cells": cells, "currency": "$", "mode": mode}

    # trend: single primary watch, baseline = fare_watches.json baseline_price_pp
    # if present, else earliest captured price in history (documented fallback).
    trend_pts = _history_points(history, trend_watch_id)
    watch_entry = watches.get(trend_watch_id, {})
    baseline = watch_entry.get("baseline_price_pp")
    if baseline is None and trend_pts:
        baseline = trend_pts[0]["price_pp"]
    trend_label = watch_entry.get("label", trend_watch_id)
    trend_data = {"points": trend_pts, "baseline_price_pp": baseline, "label": trend_label, "currency": "$"}

    heatmap_json = json.dumps(heatmap_data)
    trend_json = json.dumps(trend_data)
    uid = re.sub(r"[^a-z0-9]+", "-", trip_label.lower()).strip("-")

    return f'''{START_MARK}
<div class="card">
  <h2>Great Circle Route Maps — {trip_label}</h2>
  <div>{''.join(route_maps_html) or '<p class="empty-note">No route coordinate data available.</p>'}</div>
</div>

<div class="card">
  <h2>Fare Comparison — {trip_label}</h2>
  <div id="d2m-heatmap-{uid}"></div>
</div>

<div class="card">
  <h2>Price Trend vs Baseline — {trend_label}</h2>
  <div class="chart-wrap" style="height:280px;"><canvas id="d2m-trend-{uid}"></canvas></div>
  <div id="d2m-trend-table-{uid}"></div>
</div>


<script>
/* app/static/js/dataviz/fare_heatmap.js — inlined so this artifact stays a
   single portable file (synced to Drive, opened outside the repo). */
{heatmap_js_src}
</script>
<script>
/* app/static/js/dataviz/price_trend_chart.js — inlined, see above. */
{trend_js_src}
</script>
<script>
(function() {{
  var heatmapData = {heatmap_json};
  var trendData = {trend_json};
  if (window.D2MFareHeatmap) {{
    D2MFareHeatmap.render(document.getElementById('d2m-heatmap-{uid}'), heatmapData);
  }}
  if (window.D2MPriceTrend) {{
    D2MPriceTrend.render(
      document.getElementById('d2m-trend-{uid}'),
      document.getElementById('d2m-trend-table-{uid}'),
      trendData
    );
  }}
}})();
</script>
{END_MARK}'''


def inject(artifact: Path, section_html: str) -> None:
    if not artifact.exists():
        print(f"SKIP (not found): {artifact}")
        return
    html = artifact.read_text()
    pattern = re.compile(re.escape(START_MARK) + r".*?" + re.escape(END_MARK), re.DOTALL)
    if pattern.search(html):
        new_html = pattern.sub(section_html.replace("\\", "\\\\"), html)
    elif "</body>" in html:
        new_html = html.replace("</body>", section_html + "\n</body>")
    else:
        new_html = html + "\n" + section_html
    artifact.write_text(new_html)
    print(f"injected dataviz section into {artifact}")


def main() -> None:
    watches = _load_json(FARE_WATCHES, {})
    history = _load_json(FARE_HISTORY, [])
    heatmap_js_src = HEATMAP_JS.read_text().replace("</script>", "<\\/script>")
    trend_js_src = TREND_JS.read_text().replace("</script>", "<\\/script>")

    # --- Loucks Silver Nova 2027 ---
    silvernova_legs = [
        {"watch_id": "den-muc-vce", "label": "DEN→MUC→VCE (outbound)", "origin": "DEN", "dest": "VCE"},
        {"watch_id": "den-vce-direct", "label": "DEN→VCE (direct)", "origin": "DEN", "dest": "VCE"},
        {"watch_id": "ath-ist-den", "label": "ATH→IST→DEN (return)", "origin": "ATH", "dest": "DEN"},
        {"watch_id": "ath-muc-den", "label": "ATH→MUC→DEN (return)", "origin": "ATH", "dest": "DEN"},
    ]
    section = build_section(
        "Loucks Silver Nova 2027",
        silvernova_legs,
        watches,
        history,
        trend_watch_id="den-muc-vce",
        heatmap_js_src=heatmap_js_src,
        trend_js_src=trend_js_src,
    )
    inject(ROOT / "output" / "loucks_silvernova_2027_flight_options.html", section)

    # --- Spencer Grand Tour 2027 ---
    spencer_legs_raw = {k: v for k, v in watches.items() if k.startswith("spencer-")}
    spencer_legs = []
    for wid, entry in spencer_legs_raw.items():
        pair = _parse_route(entry.get("route", ""))
        if not pair:
            continue
        spencer_legs.append({"watch_id": wid, "label": entry.get("label", wid), "origin": pair[0], "dest": pair[1]})
    if spencer_legs:
        primary = next((l["watch_id"] for l in spencer_legs if "leg1" in l["watch_id"] and "tim-business" in l["watch_id"]), spencer_legs[0]["watch_id"])
        section2 = build_section(
            "Spencer Grand Tour 2027",
            spencer_legs,
            watches,
            history,
            trend_watch_id=primary,
            heatmap_js_src=heatmap_js_src,
            trend_js_src=trend_js_src,
        )
        inject(ROOT / "output" / "spencer_grandtour_2027_flight_options.html", section2)
    else:
        print("no spencer-* watches found in fare_watches.json — skipped")


if __name__ == "__main__":
    main()
