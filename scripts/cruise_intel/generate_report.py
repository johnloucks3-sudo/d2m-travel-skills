#!/usr/bin/env python3
"""
Generate a human-readable HTML report from the T2 master cruise CSV.
Opens at: ~/Thunderbird/output/T2_CRUISE_REPORT.html
"""
import csv
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from config import MASTER_CSV, STATS_JSON, OUTPUT_DIR

OUTPUT_HTML = OUTPUT_DIR / 'T2_CRUISE_REPORT.html'

def load_data():
    rows = []
    with open(MASTER_CSV, newline='') as f:
        for r in csv.DictReader(f):
            rows.append(r)
    return rows

def coverage_badge(row):
    sources = []
    if row['on_deluxecruises'] == 'Y': sources.append('<span class="badge deluxe">D</span>')
    if row['on_perx']          == 'Y': sources.append('<span class="badge perx">P</span>')
    if row['on_oat']           == 'Y': sources.append('<span class="badge oat">O</span>')
    if row['on_ponant']        == 'Y': sources.append('<span class="badge ponant">N</span>')
    count = len(sources)
    multi = ' multi' if count > 1 else ''
    return f'<span class="coverage{multi}">{"".join(sources)}</span>', count

def build_html(rows):
    # Summary stats
    lines = sorted(set(r['cruise_line'] for r in rows if r['cruise_line']))
    by_line = defaultdict(list)
    for r in rows:
        by_line[r['cruise_line'] or '(unknown)'].append(r)

    oct_rows = [r for r in rows if r['departure_date'].startswith('2026-10')]
    nov_rows = [r for r in rows if r['departure_date'].startswith('2026-11')]
    multi_source = [r for r in rows if sum(1 for k in ['on_deluxecruises','on_perx','on_oat','on_ponant'] if r[k]=='Y') > 1]

    # Build table rows
    table_rows_html = []
    for r in sorted(rows, key=lambda x: (x['cruise_line'], x['departure_date'])):
        badge_html, count = coverage_badge(r)
        month_cls = 'oct' if r['departure_date'].startswith('2026-10') else 'nov'
        dep = r['departure_date'][:10] if r['departure_date'] else ''
        # Format date nicely
        try:
            dep_fmt = datetime.strptime(dep, '%Y-%m-%d').strftime('%b %d')
        except:
            dep_fmt = dep
        days = r['days'] or '—'
        route = r['route'][:60] + ('…' if len(r['route']) > 60 else '') if r['route'] else '—'
        table_rows_html.append(
            f'<tr class="{month_cls}">'
            f'<td>{r["cruise_line"] or "—"}</td>'
            f'<td>{r["ship_name"] or "—"}</td>'
            f'<td class="date">{dep_fmt}</td>'
            f'<td class="num">{days}d</td>'
            f'<td class="route">{route}</td>'
            f'<td class="cov">{badge_html}</td>'
            f'</tr>'
        )

    # Line summary cards
    line_cards = []
    for line in sorted(by_line.keys()):
        group = by_line[line]
        oct_c = sum(1 for r in group if r['departure_date'].startswith('2026-10'))
        nov_c = sum(1 for r in group if r['departure_date'].startswith('2026-11'))
        ships = sorted(set(r['ship_name'] for r in group if r['ship_name']))
        ship_str = ', '.join(ships[:4]) + (f' +{len(ships)-4}' if len(ships) > 4 else '')
        line_cards.append(f'''
        <div class="card">
          <div class="card-line">{line}</div>
          <div class="card-ships">{ship_str or "—"}</div>
          <div class="card-counts">
            <span class="oct-pill">{oct_c} Oct</span>
            <span class="nov-pill">{nov_c} Nov</span>
          </div>
        </div>''')

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>T2 Cruise Intel — Oct/Nov 2026</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: Georgia, serif; background: #f7f3ea; color: #1a1a1a; }}
  .header {{ background: #0033A0; color: #fff; padding: 28px 40px 20px; }}
  .header h1 {{ font-size: 1.6rem; font-weight: normal; letter-spacing: 0.5px; }}
  .header p {{ font-size: 0.85rem; opacity: 0.8; margin-top: 4px; }}
  .stats-bar {{ display: flex; gap: 24px; padding: 18px 40px; background: #1a1a1a; color: #f7f3ea; flex-wrap: wrap; }}
  .stat {{ text-align: center; }}
  .stat-num {{ font-size: 2rem; font-weight: bold; color: #f0c040; line-height: 1; }}
  .stat-lbl {{ font-size: 0.7rem; text-transform: uppercase; letter-spacing: 1px; opacity: 0.7; margin-top: 2px; }}
  .section {{ padding: 24px 40px; }}
  .section h2 {{ font-size: 1rem; text-transform: uppercase; letter-spacing: 1.5px; color: #0033A0; border-bottom: 2px solid #0033A0; padding-bottom: 6px; margin-bottom: 16px; }}
  .cards {{ display: flex; flex-wrap: wrap; gap: 10px; }}
  .card {{ background: #fff; border: 1px solid #ddd; border-radius: 6px; padding: 12px 14px; min-width: 200px; flex: 1 1 200px; max-width: 260px; }}
  .card-line {{ font-weight: bold; font-size: 0.85rem; color: #0033A0; }}
  .card-ships {{ font-size: 0.75rem; color: #555; margin: 4px 0; font-style: italic; }}
  .card-counts {{ display: flex; gap: 6px; margin-top: 6px; }}
  .oct-pill {{ background: #e8f0ff; color: #0033A0; font-size: 0.7rem; padding: 2px 8px; border-radius: 10px; }}
  .nov-pill {{ background: #fff3cd; color: #856404; font-size: 0.7rem; padding: 2px 8px; border-radius: 10px; }}
  .search-bar {{ margin-bottom: 12px; display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }}
  .search-bar input {{ padding: 8px 12px; border: 1px solid #ccc; border-radius: 4px; font-size: 0.9rem; width: 280px; background: #fff; }}
  .search-bar select {{ padding: 8px 10px; border: 1px solid #ccc; border-radius: 4px; font-size: 0.85rem; background: #fff; }}
  .search-bar label {{ font-size: 0.8rem; color: #555; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; background: #fff; }}
  th {{ background: #0033A0; color: #fff; text-align: left; padding: 10px 12px; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px; cursor: pointer; user-select: none; white-space: nowrap; }}
  th:hover {{ background: #002280; }}
  td {{ padding: 8px 12px; border-bottom: 1px solid #eee; vertical-align: middle; }}
  tr:hover td {{ background: #f0f4ff; }}
  tr.oct td {{ border-left: 3px solid #0033A0; }}
  tr.nov td {{ border-left: 3px solid #f0c040; }}
  tr.hidden {{ display: none; }}
  .date {{ white-space: nowrap; font-variant-numeric: tabular-nums; }}
  .num {{ text-align: center; color: #555; }}
  .route {{ color: #444; max-width: 300px; }}
  .cov {{ white-space: nowrap; }}
  .badge {{ display: inline-block; width: 18px; height: 18px; border-radius: 3px; font-size: 0.65rem; font-weight: bold; text-align: center; line-height: 18px; margin-right: 2px; }}
  .badge.deluxe {{ background: #0033A0; color: #fff; }}
  .badge.perx {{ background: #28a745; color: #fff; }}
  .badge.oat {{ background: #fd7e14; color: #fff; }}
  .badge.ponant {{ background: #6f42c1; color: #fff; }}
  .coverage.multi {{ background: #fffbe6; border-radius: 4px; padding: 1px 3px; }}
  .legend {{ display: flex; gap: 12px; font-size: 0.75rem; color: #555; margin-bottom: 10px; flex-wrap: wrap; }}
  .legend span {{ display: flex; align-items: center; gap: 4px; }}
  .count-bar {{ font-size: 0.8rem; color: #555; margin-bottom: 8px; }}
  #count-display {{ font-weight: bold; color: #0033A0; }}
</style>
</head>
<body>

<div class="header">
  <h1>T2 Cruise Intelligence — October &amp; November 2026</h1>
  <p>Dreams2Memories Travel, LLC &nbsp;·&nbsp; Wing Exercise 2026-05-24 &nbsp;·&nbsp; 4 sources: deluxecruises.com · Perx · OAT · Ponant</p>
</div>

<div class="stats-bar">
  <div class="stat"><div class="stat-num">{len(rows)}</div><div class="stat-lbl">Total Sailings</div></div>
  <div class="stat"><div class="stat-num">{len(oct_rows)}</div><div class="stat-lbl">October</div></div>
  <div class="stat"><div class="stat-num">{len(nov_rows)}</div><div class="stat-lbl">November</div></div>
  <div class="stat"><div class="stat-num">{len(lines)}</div><div class="stat-lbl">Cruise Lines</div></div>
  <div class="stat"><div class="stat-num">{len(multi_source)}</div><div class="stat-lbl">Multi-Source Confirmed</div></div>
  <div class="stat"><div class="stat-num">4</div><div class="stat-lbl">Sources</div></div>
</div>

<div class="section">
  <h2>By Cruise Line</h2>
  <div class="cards">{''.join(line_cards)}</div>
</div>

<div class="section">
  <h2>All Sailings</h2>
  <div class="legend">
    <span><span class="badge deluxe">D</span> deluxecruises.com</span>
    <span><span class="badge perx">P</span> Perx.com</span>
    <span><span class="badge oat">O</span> OAT</span>
    <span><span class="badge ponant">N</span> Ponant</span>
    <span style="margin-left:8px">Blue left border = October &nbsp;·&nbsp; Gold = November &nbsp;·&nbsp; Highlighted row = multi-source confirmed</span>
  </div>
  <div class="search-bar">
    <input type="text" id="search" placeholder="Search ship, line, route…" oninput="filterTable()">
    <label>Month: <select id="monthFilter" onchange="filterTable()">
      <option value="">All</option>
      <option value="oct">October</option>
      <option value="nov">November</option>
    </select></label>
    <label>Line: <select id="lineFilter" onchange="filterTable()">
      <option value="">All lines</option>
      {''.join(f'<option value="{l}">{l}</option>' for l in sorted(by_line.keys()))}
    </select></label>
    <label><input type="checkbox" id="multiOnly" onchange="filterTable()"> Multi-source only</label>
  </div>
  <div class="count-bar">Showing <span id="count-display">{len(rows)}</span> sailings</div>
  <table id="cruiseTable">
    <thead>
      <tr>
        <th onclick="sortTable(0)">Cruise Line ↕</th>
        <th onclick="sortTable(1)">Ship ↕</th>
        <th onclick="sortTable(2)">Departs ↕</th>
        <th onclick="sortTable(3)">Days ↕</th>
        <th>Route</th>
        <th>Sources</th>
      </tr>
    </thead>
    <tbody id="tableBody">
      {''.join(table_rows_html)}
    </tbody>
  </table>
</div>

<div style="padding: 16px 40px; font-size: 0.75rem; color: #888; border-top: 1px solid #ddd; margin-top: 20px;">
  Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} MT &nbsp;·&nbsp; Dreams2Memories Travel, LLC &nbsp;·&nbsp; T2 Wing Exercise
</div>

<script>
let sortDir = {{}};

function filterTable() {{
  const q = document.getElementById('search').value.toLowerCase();
  const month = document.getElementById('monthFilter').value;
  const line = document.getElementById('lineFilter').value.toLowerCase();
  const multiOnly = document.getElementById('multiOnly').checked;
  const rows = document.querySelectorAll('#tableBody tr');
  let visible = 0;
  rows.forEach(row => {{
    const text = row.textContent.toLowerCase();
    const isMonth = !month || row.classList.contains(month);
    const isLine = !line || row.cells[0].textContent.toLowerCase() === line;
    const isMulti = !multiOnly || row.querySelector('.multi');
    const isSearch = !q || text.includes(q);
    const show = isMonth && isLine && isMulti && isSearch;
    row.classList.toggle('hidden', !show);
    if (show) visible++;
  }});
  document.getElementById('count-display').textContent = visible;
}}

function sortTable(col) {{
  const tbody = document.getElementById('tableBody');
  const rows = Array.from(tbody.querySelectorAll('tr'));
  sortDir[col] = !sortDir[col];
  rows.sort((a, b) => {{
    const av = a.cells[col].textContent.trim();
    const bv = b.cells[col].textContent.trim();
    return sortDir[col] ? av.localeCompare(bv) : bv.localeCompare(av);
  }});
  rows.forEach(r => tbody.appendChild(r));
}}
</script>
</body>
</html>'''

def main():
    rows = load_data()
    html = build_html(rows)
    OUTPUT_HTML.write_text(html)
    print(f'Report → {OUTPUT_HTML}')
    print(f'  {len(rows)} sailings | {len(set(r["cruise_line"] for r in rows if r["cruise_line"]))} lines')

if __name__ == '__main__':
    main()
