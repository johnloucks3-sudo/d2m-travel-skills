#!/usr/bin/env python3
"""
Generate a human-readable HTML report from the T2 master cruise CSV.
Opens at: ~/Thunderbird/output/T2_CRUISE_REPORT.html
"""
import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from config import MASTER_CSV, STATS_JSON, OUTPUT_DIR

OUTPUT_HTML = OUTPUT_DIR / 'T2_CRUISE_REPORT.html'

# All 10 source columns in display order
FLAG_MAP = [
    ('on_deluxecruises', 'deluxe',      'D', 'deluxecruises.com', 'W1'),
    ('on_perx',          'perx',        'P', 'Perx.com',          'W1'),
    ('on_oat',           'oat',         'O', 'OAT',               'W1'),
    ('on_ponant',        'ponant',      'N', 'PONANT',            'W1'),
    ('on_hx',            'hx',          'H', 'HX Expeditions',    'W2'),
    ('on_seadream',      'seadream',    'S', 'SeaDream',          'W2'),
    ('on_explora',       'explora',     'E', 'Explora Journeys',  'W2'),
    ('on_cruisemapper',  'cruisemapper','M', 'CruiseMapper',      'W3'),
    ('on_cruisesonly',   'cruisesonly', 'C', 'CruisesOnly',       'W3'),
    ('on_cruiseplum',    'cruiseplum',  'L', 'CruisePlum',        'W3'),
]
ALL_SOURCE_COLS = [col for col, *_ in FLAG_MAP]


def load_data():
    rows = []
    with open(MASTER_CSV, newline='') as f:
        for r in csv.DictReader(f):
            rows.append(r)
    return rows


def coverage_badge(row):
    sources = [f'<span class="badge {cls}">{ltr}</span>'
               for col, cls, ltr, *_ in FLAG_MAP if row.get(col) == 'Y']
    count   = len(sources)
    multi   = ' multi' if count > 1 else ''
    return f'<span class="coverage{multi}">{"".join(sources)}</span>', count


def build_html(rows):
    lines    = sorted(set(r['cruise_line'] for r in rows if r['cruise_line']))
    by_line  = defaultdict(list)
    for r in rows:
        by_line[r['cruise_line'] or '(unknown)'].append(r)

    oct_rows     = [r for r in rows if r['departure_date'].startswith('2026-10')]
    nov_rows     = [r for r in rows if r['departure_date'].startswith('2026-11')]
    multi_source = [r for r in rows
                    if sum(1 for k in ALL_SOURCE_COLS if r.get(k) == 'Y') > 1]
    active_sources = [label for col, cls, ltr, label, wave in FLAG_MAP
                      if any(r.get(col) == 'Y' for r in rows)]
    n_sources    = len(active_sources)

    # Sort rows once → assign stable anchor IDs
    sorted_rows = sorted(rows, key=lambda x: (x['cruise_line'], x['departure_date']))
    row_ids = {id(r): i for i, r in enumerate(sorted_rows)}

    # ── Table rows ────────────────────────────────────────────────────────────
    table_rows_html = []
    for r in sorted_rows:
        idx       = row_ids[id(r)]
        badge_html, _ = coverage_badge(r)
        month_cls = 'oct' if r['departure_date'].startswith('2026-10') else 'nov'
        dep       = r['departure_date'][:10] if r['departure_date'] else ''
        try:
            dep_fmt = datetime.strptime(dep, '%Y-%m-%d').strftime('%b %d')
        except Exception:
            dep_fmt = dep
        days  = r['days'] or '—'
        route = r['route'][:60] + ('…' if len(r['route']) > 60 else '') if r['route'] else '—'
        price = f'${int(r["price_usd"]):,}' if r.get('price_usd') and r['price_usd'].isdigit() else ''
        table_rows_html.append(
            f'<tr class="{month_cls}" id="v-{idx}">'
            f'<td>{r["cruise_line"] or "—"}</td>'
            f'<td>{r["ship_name"] or "—"}</td>'
            f'<td class="date">{dep_fmt}</td>'
            f'<td class="num">{days}d</td>'
            f'<td class="route">{route}</td>'
            f'<td class="price">{price}</td>'
            f'<td class="cov">{badge_html}</td>'
            f'</tr>'
        )

    # ── Legend ────────────────────────────────────────────────────────────────
    legend_items = [
        f'<span><span class="badge {cls}">{ltr}</span> {label}</span>'
        for col, cls, ltr, label, wave in FLAG_MAP
        if any(r.get(col) == 'Y' for r in rows)
    ]

    # ── Line cards with voyage anchor links ───────────────────────────────────
    line_cards = []
    for line in sorted(by_line.keys()):
        group = sorted(by_line[line], key=lambda x: x['departure_date'])
        oct_c = sum(1 for r in group if r['departure_date'].startswith('2026-10'))
        nov_c = sum(1 for r in group if r['departure_date'].startswith('2026-11'))
        ships = sorted(set(r['ship_name'] for r in group if r['ship_name']))
        ship_str = ', '.join(ships[:3]) + (f' +{len(ships)-3}' if len(ships) > 3 else '')

        voyage_links = []
        for r in group[:14]:
            idx = row_ids[id(r)]
            dep = r['departure_date'][:10]
            try:
                dep_fmt = datetime.strptime(dep, '%Y-%m-%d').strftime('%b %d')
            except Exception:
                dep_fmt = dep
            ship = r['ship_name'] or '—'
            days = r['days'] or '?'
            link_cls = 'oct-link' if dep.startswith('2026-10') else 'nov-link'
            voyage_links.append(
                f'<a href="#v-{idx}" class="{link_cls}">'
                f'{ship} · {dep_fmt} · {days}d</a>'
            )
        overflow = len(group) - 14
        overflow_html = (f'<span class="more-voyages">… {overflow} more</span>'
                         if overflow > 0 else '')

        line_cards.append(f'''
        <div class="card">
          <div class="card-line">{line}</div>
          <div class="card-ships">{ship_str or "—"}</div>
          <div class="card-counts">
            <span class="oct-pill">{oct_c} Oct</span>
            <span class="nov-pill">{nov_c} Nov</span>
          </div>
          <div class="card-voyages">{''.join(voyage_links)}{overflow_html}</div>
        </div>''')

    sources_header = ' · '.join(active_sources)

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>T2 Cruise Intel — Oct/Nov 2026</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: Georgia, serif; background: #f7f3ea; color: #1a1a1a; }}

  /* ── Header & stats ─────────────────────────────────────── */
  .header {{ background: #0033A0; color: #fff; padding: 28px 40px 20px; }}
  .header h1 {{ font-size: 1.6rem; font-weight: normal; letter-spacing: 0.5px; }}
  .header p  {{ font-size: 0.82rem; opacity: 0.8; margin-top: 5px; line-height: 1.5; }}
  .stats-bar {{ display: flex; gap: 24px; padding: 18px 40px; background: #1a1a1a;
               color: #f7f3ea; flex-wrap: wrap; }}
  .stat {{ text-align: center; }}
  .stat-num {{ font-size: 2rem; font-weight: bold; color: #f0c040; line-height: 1; }}
  .stat-lbl {{ font-size: 0.7rem; text-transform: uppercase; letter-spacing: 1px;
               opacity: 0.7; margin-top: 2px; }}

  /* ── Sections ───────────────────────────────────────────── */
  .section {{ padding: 24px 40px; }}
  .section h2 {{ font-size: 1rem; text-transform: uppercase; letter-spacing: 1.5px;
                 color: #0033A0; border-bottom: 2px solid #0033A0;
                 padding-bottom: 6px; margin-bottom: 16px; }}

  /* ── Cards ──────────────────────────────────────────────── */
  .cards {{ display: flex; flex-wrap: wrap; gap: 12px; }}
  .card {{ background: #fff; border: 1px solid #ddd; border-radius: 8px;
           padding: 12px 14px; min-width: 220px; flex: 1 1 220px; max-width: 300px;
           transition: box-shadow 0.15s, border-color 0.15s; }}
  .card:hover {{ box-shadow: 0 4px 14px rgba(0,51,160,0.14); border-color: #0033A0; }}
  .card-line  {{ font-weight: bold; font-size: 0.88rem; color: #0033A0;
                 border-bottom: 1px solid #eee; padding-bottom: 5px; margin-bottom: 6px; }}
  .card-ships {{ font-size: 0.73rem; color: #666; font-style: italic; margin-bottom: 6px; }}
  .card-counts {{ display: flex; gap: 6px; margin-bottom: 8px; }}
  .oct-pill {{ background: #e8f0ff; color: #0033A0; font-size: 0.68rem;
               padding: 2px 8px; border-radius: 10px; font-weight: bold; }}
  .nov-pill {{ background: #fff3cd; color: #856404; font-size: 0.68rem;
               padding: 2px 8px; border-radius: 10px; font-weight: bold; }}

  /* ── Voyage links inside cards ──────────────────────────── */
  .card-voyages {{ display: flex; flex-direction: column; gap: 3px; }}
  .card-voyages a {{ font-size: 0.72rem; color: #222; text-decoration: none;
                     padding: 2px 5px; border-radius: 3px; display: block;
                     line-height: 1.4; transition: background 0.1s; }}
  .card-voyages a:hover {{ background: #f0f4ff; color: #0033A0; }}
  .card-voyages a.oct-link {{ border-left: 3px solid #0033A0; }}
  .card-voyages a.nov-link {{ border-left: 3px solid #f0c040; }}
  .more-voyages {{ font-size: 0.68rem; color: #888; padding: 2px 5px;
                   font-style: italic; }}

  /* ── Search / filter bar ────────────────────────────────── */
  .search-bar {{ margin-bottom: 12px; display: flex; gap: 10px;
                 align-items: center; flex-wrap: wrap; }}
  .search-bar input  {{ padding: 8px 12px; border: 1px solid #ccc; border-radius: 4px;
                        font-size: 0.9rem; width: 280px; background: #fff; }}
  .search-bar select {{ padding: 8px 10px; border: 1px solid #ccc; border-radius: 4px;
                        font-size: 0.85rem; background: #fff; }}
  .search-bar label  {{ font-size: 0.8rem; color: #555; }}

  /* ── Table ──────────────────────────────────────────────── */
  table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; background: #fff; }}
  th {{ background: #0033A0; color: #fff; text-align: left; padding: 10px 12px;
        font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px;
        cursor: pointer; user-select: none; white-space: nowrap; }}
  th:hover {{ background: #002280; }}
  td {{ padding: 8px 12px; border-bottom: 1px solid #eee; vertical-align: middle; }}
  tr:hover td {{ background: #f0f4ff; }}
  tr.oct td {{ border-left: 3px solid #0033A0; }}
  tr.nov td {{ border-left: 3px solid #f0c040; }}
  tr.hidden {{ display: none; }}
  tr:target td {{ background: #fff8e6; outline: 2px solid #f0c040; }}
  .date  {{ white-space: nowrap; font-variant-numeric: tabular-nums; }}
  .num   {{ text-align: center; color: #555; }}
  .price {{ text-align: right; color: #1a7a1a; font-size: 0.82rem; white-space: nowrap; }}
  .route {{ color: #444; max-width: 280px; }}
  .cov   {{ white-space: nowrap; }}

  /* ── Source badges ──────────────────────────────────────── */
  .badge {{ display: inline-block; width: 18px; height: 18px; border-radius: 3px;
            font-size: 0.62rem; font-weight: bold; text-align: center;
            line-height: 18px; margin-right: 2px; }}
  .badge.deluxe      {{ background: #0033A0; color: #fff; }}
  .badge.perx        {{ background: #28a745; color: #fff; }}
  .badge.oat         {{ background: #fd7e14; color: #fff; }}
  .badge.ponant      {{ background: #6f42c1; color: #fff; }}
  .badge.hx          {{ background: #17a2b8; color: #fff; }}
  .badge.seadream    {{ background: #20c997; color: #fff; }}
  .badge.explora     {{ background: #e83e8c; color: #fff; }}
  .badge.cruisemapper{{ background: #795548; color: #fff; }}
  .badge.cruisesonly {{ background: #ff5722; color: #fff; }}
  .badge.cruiseplum  {{ background: #9c27b0; color: #fff; }}
  .coverage.multi {{ background: #fffbe6; border-radius: 4px; padding: 1px 3px; }}

  /* ── Legend & misc ──────────────────────────────────────── */
  .legend {{ display: flex; gap: 10px; font-size: 0.73rem; color: #555;
             margin-bottom: 10px; flex-wrap: wrap; align-items: center; }}
  .legend span {{ display: flex; align-items: center; gap: 4px; }}
  .legend-note {{ font-size: 0.72rem; color: #888; margin-left: 8px; font-style: italic; }}
  .count-bar {{ font-size: 0.8rem; color: #555; margin-bottom: 8px; }}
  #count-display {{ font-weight: bold; color: #0033A0; }}
</style>
</head>
<body>

<div class="header">
  <h1>T2 Cruise Intelligence — October &amp; November 2026</h1>
  <p>Dreams2Memories Travel, LLC &nbsp;·&nbsp; Wing Exercise 2026-05-24</p>
  <p style="margin-top:6px; font-size:0.77rem; opacity:0.65">{sources_header}</p>
</div>

<div class="stats-bar">
  <div class="stat"><div class="stat-num">{len(rows)}</div><div class="stat-lbl">Total Sailings</div></div>
  <div class="stat"><div class="stat-num">{len(oct_rows)}</div><div class="stat-lbl">October</div></div>
  <div class="stat"><div class="stat-num">{len(nov_rows)}</div><div class="stat-lbl">November</div></div>
  <div class="stat"><div class="stat-num">{len(lines)}</div><div class="stat-lbl">Cruise Lines</div></div>
  <div class="stat"><div class="stat-num">{len(multi_source)}</div><div class="stat-lbl">Multi-Source</div></div>
  <div class="stat"><div class="stat-num">{n_sources}</div><div class="stat-lbl">Sources</div></div>
</div>

<div class="section">
  <h2>By Cruise Line — Click a Voyage to Jump to Table</h2>
  <div class="cards">{''.join(line_cards)}</div>
</div>

<div class="section">
  <h2>All Sailings</h2>
  <div class="legend">
    {'  '.join(legend_items)}
    <span class="legend-note">Blue left border = October &nbsp;·&nbsp; Gold = November &nbsp;·&nbsp; Highlighted = multi-source confirmed</span>
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
    <button onclick="resetFilters()" style="padding:6px 12px;font-size:0.8rem;border:1px solid #ccc;border-radius:4px;background:#fff;cursor:pointer;">Reset</button>
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
        <th onclick="sortTable(5)">Price ↕</th>
        <th>Sources</th>
      </tr>
    </thead>
    <tbody id="tableBody">
      {''.join(table_rows_html)}
    </tbody>
  </table>
</div>

<div style="padding:16px 40px;font-size:0.73rem;color:#888;border-top:1px solid #ddd;margin-top:20px;">
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
    const isLine  = !line  || row.cells[0].textContent.toLowerCase() === line;
    const isMulti = !multiOnly || row.querySelector('.multi');
    const isSearch = !q || text.includes(q);
    const show = isMonth && isLine && isMulti && isSearch;
    row.classList.toggle('hidden', !show);
    if (show) visible++;
  }});
  document.getElementById('count-display').textContent = visible;
}}

function resetFilters() {{
  document.getElementById('search').value = '';
  document.getElementById('monthFilter').selectedIndex = 0;
  document.getElementById('lineFilter').selectedIndex  = 0;
  document.getElementById('multiOnly').checked = false;
  filterTable();
}}

function sortTable(col) {{
  const tbody = document.getElementById('tableBody');
  const rows  = Array.from(tbody.querySelectorAll('tr'));
  sortDir[col] = !sortDir[col];
  rows.sort((a, b) => {{
    const av = a.cells[col].textContent.trim();
    const bv = b.cells[col].textContent.trim();
    return sortDir[col] ? av.localeCompare(bv) : bv.localeCompare(av);
  }});
  rows.forEach(r => tbody.appendChild(r));
}}

// Highlight anchor target row briefly after navigation
window.addEventListener('hashchange', highlightTarget);
function highlightTarget() {{
  const target = document.querySelector(':target');
  if (target) {{
    target.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
  }}
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
