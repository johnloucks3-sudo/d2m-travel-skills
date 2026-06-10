#!/usr/bin/env python3
"""Generate fare watch HTML preview for morning brief."""
import json, asyncio, sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / "Thunderbird"))
from core.travel.thunderbird_centrav_search import run_centrav_search

WATCHES = json.loads((Path.home() / "Thunderbird/core/travel/data/fare_watches.json").read_text())

IDS = {
    "silver-out": "loucks-silver-nova-may2027-outbound",
    "silver-ret": "loucks-silver-nova-may2027-return",
    "cos-fll": "loucks-grandeur-panama-cos-fll-dec2026",
    "sna-cos": "loucks-grandeur-panama-sna-cos-jan2027",
    "grb-out": "loucks-den-grb-sep2026",
    "grb-ret": "loucks-grb-den-sep2026",
}

def w(id):
    return WATCHES.get(id, {})

def pct(cp, bp):
    if not bp:
        return 0
    return ((cp - bp) / bp) * 100

async def refresh():
    r1 = await run_centrav_search("DEN", "VCE", "2027-04-30", adults=2, cabins=["business"])
    r2 = await run_centrav_search("ATH", "DEN", "2027-06-01", adults=2, cabins=["business"])
    b1 = r1.get("results", {}).get("business", {}).get("lowest_total", 0)
    b2 = r2.get("results", {}).get("business", {}).get("lowest_total", 0)
    if b1:
        WATCHES[IDS["silver-out"]]["current_price_pp"] = b1 / 2
    if b2:
        WATCHES[IDS["silver-ret"]]["current_price_pp"] = b2 / 2
    return b1, b2

b1, b2 = asyncio.run(refresh())

so = w(IDS["silver-out"])
sr = w(IDS["silver-ret"])
co = w(IDS["cos-fll"])
sc = w(IDS["sna-cos"])
go = w(IDS["grb-out"])
gr = w(IDS["grb-ret"])

def badge(cp, bp, ab):
    p = pct(cp, bp)
    if ab and cp and cp <= ab:
        return '<span class="badge badge-red">BREACH</span>', p
    return '<span class="badge badge-green">OK</span>', p

html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Thunderbird Fare Watch</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; background:#0f172a; color:#e2e8f0; padding:40px; }
  .w { max-width:900px; margin:0 auto; }
  h1 { font-size:24px; font-weight:700; color:#f8fafc; margin-bottom:4px; }
  .s { color:#94a3b8; font-size:14px; margin-bottom:24px; }
  .c { background:#1e293b; border:1px solid #334155; border-radius:12px; padding:24px; margin-bottom:20px; }
  .c h2 { font-size:16px; font-weight:600; color:#38bdf8; margin-bottom:16px; text-transform:uppercase; letter-spacing:0.5px; }
  table { width:100%; border-collapse:collapse; }
  th { text-align:left; padding:10px 12px; font-size:12px; font-weight:600; color:#64748b; text-transform:uppercase; letter-spacing:0.5px; border-bottom:1px solid #334155; }
  td { padding:12px; font-size:14px; border-bottom:1px solid #1e293b; }
  .p { font-weight:600; font-variant-numeric:tabular-nums; }
  .r { color:#ef4444; }
  .g { color:#22c55e; }
  .b { color:#94a3b8; }
  .badge { display:inline-block; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:600; }
  .badge-g { background:rgba(34,197,94,0.15); color:#22c55e; }
  .badge-r { background:rgba(239,68,68,0.15); color:#ef4444; }
  .badge-b { background:rgba(56,189,248,0.15); color:#38bdf8; }
  .f { color:#475569; font-size:12px; margin-top:32px; text-align:center; border-top:1px solid #1e293b; padding-top:16px; }
</style>
</head>
<body>
<div class="w">
<h1>Thunderbird Fare Watch</h1>
<div class="s">Jun 7, 2026 &middot; 07:00 MT &middot; Session 1 of 14</div>

<div class="c">
<h2> Icelandair May 2027 &mdash; Priority Monitoring</h2>
<p style="color:#94a3b8;font-size:13px;margin-bottom:12px;">Commander preference: Icelandair Saga Premium &middot; Daily Centrav refresh &middot; Alert at -8%</p>
<table>
<tr><th>Route</th><th>Cabin</th><th>Current/pp</th><th>Baseline/pp</th><th>Change</th><th>Alert</th></tr>
"""

b1b, p1 = badge(so["current_price_pp"], so["baseline_price_pp"], so["alert_below"])
b2b, p2 = badge(sr["current_price_pp"], sr["baseline_price_pp"], sr["alert_below"])
pc1 = "r" if p1 > 2 else ("g" if p1 < -2 else "b")
pc2 = "r" if p2 > 2 else ("g" if p2 < -2 else "b")

html += f"""<tr><td><strong>DEN&rarr;VCE</strong></td><td>Business</td><td class="p">${so["current_price_pp"]:.0f}</td><td>${so["baseline_price_pp"]:.0f}</td><td class="{pc1}">{p1:+.1f}%</td><td>{b1b}</td></tr>
<tr><td><strong>ATH&rarr;DEN</strong></td><td>Business</td><td class="p">${sr["current_price_pp"]:.0f}</td><td>${sr["baseline_price_pp"]:.0f}</td><td class="{pc2}">{p2:+.1f}%</td><td>{b2b}</td></tr>
"""

html += """</table>
</div>

<div class="c">
<h2> All Active Watches</h2>
<table>
<tr><th>Route</th><th>Date</th><th>Cabin</th><th>Current/pp</th><th>Baseline</th><th>&plusmn;%</th></tr>
"""

for wid, label in [("cos-fll","COS&rarr;FLL"), ("sna-cos","SNA&rarr;COS"), ("grb-out","DEN&rarr;GRB"), ("grb-ret","GRB&rarr;DEN")]:
    entry = w(IDS[wid])
    cp = entry["current_price_pp"]
    bp = entry["baseline_price_pp"]
    p = pct(cp, bp)
    pc = "r" if p > 2 else ("g" if p < -2 else "b")
    html += f"""<tr><td><strong>{label}</strong></td><td>{entry["travel_date"]}</td><td>Economy</td><td class="p">${cp:.0f}</td><td>${bp:.0f}</td><td class="{pc}">{p:+.1f}%</td></tr>
"""

out_pp = so["current_price_pp"]
ret_pp = sr["current_price_pp"]
rt_pp = out_pp + ret_pp
html += f"""</table>
</div>

<div class="c">
<h2> Best RT Price &mdash; Icelandair May 2027</h2>
<table>
<tr><td>DEN&rarr;VCE (out)</td><td class="p">${out_pp:.0f}/pp</td><td>${out_pp*2:.0f} total</td></tr>
<tr><td>ATH&rarr;DEN (return)</td><td class="p">${ret_pp:.0f}/pp</td><td>${ret_pp*2:.0f} total</td></tr>
<tr style="border-top:2px solid #38bdf8;"><td><strong>Round Trip /pp</strong></td><td class="p" style="color:#38bdf8;"><strong>${rt_pp:.0f}</strong></td><td><strong>${rt_pp*2:.0f} total 2 pax</strong></td></tr>
</table>
<p style="margin-top:12px;color:#64748b;font-size:13px;">Next Centrav refresh: Jun 8, 2026 &middot; 07:00 MT</p>
</div>

<div class="c">
<h2> DEN&rarr;GRB Sep 2026 &mdash; United Economy</h2>
<table>
<tr><td>DEN&rarr;GRB Sep 6</td><td class="p">${go["current_price_pp"]:.0f}/pp</td><td>${go["current_price_pp"]*2:.0f} total</td></tr>
<tr><td>GRB&rarr;DEN Sep 14</td><td class="p">${gr["current_price_pp"]:.0f}/pp</td><td>${gr["current_price_pp"]*2:.0f} total</td></tr>
<tr style="border-top:2px solid #38bdf8;"><td><strong>Round Trip</strong></td><td class="p" style="color:#38bdf8;"><strong>{go["current_price_pp"]+gr["current_price_pp"]:.0f}/pp</strong></td><td><strong>{(go["current_price_pp"]+gr["current_price_pp"])*2:.0f} total</strong></td></tr>
</table>
</div>

<div class="f">
Thunderbird Wing &middot; Dreams2Memories Travel, LLC &middot; Hale &middot; 2026-06-07 07:00 MT
</div>
</div>
</body>
</html>"""

out = Path.home() / "Thunderbird/output/fare_watch_jun7_2026.html"
out.write_text(html)
print(f"Written: {out} ({len(html)} bytes)")
print(f"DEN->VCE: ${out_pp:.0f}/pp | ATH->DEN: ${ret_pp:.0f}/pp | RT: ${rt_pp:.0f}/pp")
print(f"DEN->GRB: ${go['current_price_pp']:.0f}/pp | GRB->DEN: ${gr['current_price_pp']:.0f}/pp")
