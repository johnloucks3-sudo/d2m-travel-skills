#!/usr/bin/env python3
"""
Generate a human-readable HTML report from the T2 master cruise CSV.
Usage: python3 generate_report.py [--period 2026-10,2026-11] [--csv PATH] [--output PATH]
  --period  Comma-separated YYYY-MM values. Defaults to auto-detect from CSV.
  --csv     Override CSV path (default: config MASTER_CSV).
  --output  Override output HTML path.
"""
import argparse
import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from config import MASTER_CSV, STATS_JSON, OUTPUT_DIR

OUTPUT_HTML = OUTPUT_DIR / 'T2_CRUISE_REPORT.html'

# Color palette per period index — (row-border, pill-bg, pill-text)
PERIOD_PALETTE = [
    ('#0033A0', '#e8f0ff', '#0033A0'),  # p-0: USAFA blue (October)
    ('#856404', '#fff3cd', '#856404'),  # p-1: gold (November)
    ('#155724', '#d4edda', '#155724'),  # p-2: green
    ('#6f0072', '#f3e5f5', '#6f0072'),  # p-3: purple
]

CURATED_LINES = {
    'Silversea', 'Regent Seven Seas Cruises', 'Seabourn', 'Viking',
    'Oceania Cruises', 'Cunard', 'PONANT', 'Atlas Ocean Voyages',
}

LINE_URLS = {
    'Silversea':                  ('https://www.silversea.com/cruises.html',
                                   'https://www.deluxecruises.com/silversea/cruises/'),
    'Regent Seven Seas Cruises':  ('https://www.rssc.com/voyages',
                                   'https://www.deluxecruises.com/regent-seven-seas/cruises/'),
    'Seabourn':                   ('https://www.seabourn.com/find-a-cruise',
                                   'https://www.deluxecruises.com/seabourn/cruises/'),
    'Viking':                     ('https://www.vikingcruises.com/oceans/cruises/',
                                   'https://www.deluxecruises.com/viking-ocean/cruises/'),
    'Oceania Cruises':            ('https://www.oceaniacruises.com/cruises',
                                   'https://www.deluxecruises.com/oceania/cruises/'),
    'Cunard':                     ('https://www.cunard.com/en-us/cruise-search',
                                   'https://www.deluxecruises.com/cunard/cruises/'),
    'PONANT':                     ('https://us.ponant.com/cruises',
                                   'https://www.deluxecruises.com/ponant/cruises/'),
    'Atlas Ocean Voyages':        ('https://www.atlasoceanvoyages.com/cruise',
                                   'https://www.deluxecruises.com/atlas-ocean/cruises/'),
}

FLAG_MAP = [
    ('on_deluxecruises', 'deluxe',       'D', 'deluxecruises.com', 'W1'),
    ('on_perx',          'perx',         'P', 'Perx.com',          'W1'),
    ('on_oat',           'oat',          'O', 'OAT',               'W1'),
    ('on_ponant',        'ponant',       'N', 'PONANT',            'W1'),
    ('on_hx',            'hx',           'H', 'HX Expeditions',    'W2'),
    ('on_seadream',      'seadream',     'S', 'SeaDream',          'W2'),
    ('on_explora',       'explora',      'E', 'Explora Journeys',  'W2'),
    ('on_cruisemapper',  'cruisemapper', 'M', 'CruiseMapper',      'W3'),
    ('on_cruisesonly',   'cruisesonly',  'C', 'CruisesOnly',       'W3'),
    ('on_cruiseplum',    'cruiseplum',   'L', 'CruisePlum',        'W3'),
]
ALL_SOURCE_COLS = [col for col, *_ in FLAG_MAP]


def month_label(ym, fmt='%B %Y'):
    """'2026-10' → 'October 2026'"""
    try:
        return datetime.strptime(ym + '-01', '%Y-%m-%d').strftime(fmt)
    except Exception:
        return ym


def month_abbr(ym):
    return month_label(ym, '%b')


def load_data(csv_path=None):
    path = csv_path or MASTER_CSV
    rows = []
    with open(path, newline='') as f:
        for r in csv.DictReader(f):
            rows.append(r)
    return rows


def detect_periods(rows):
    """Auto-detect sorted YYYY-MM periods present in data."""
    seen = set()
    for r in rows:
        d = r.get('departure_date', '')
        if d and len(d) >= 7:
            seen.add(d[:7])
    return sorted(seen)


def coverage_badge(row):
    sources = [f'<span class="badge {cls}">{ltr}</span>'
               for col, cls, ltr, *_ in FLAG_MAP if row.get(col) == 'Y']
    count = len(sources)
    multi = ' multi' if count > 1 else ''
    return f'<span class="coverage{multi}">{"".join(sources)}</span>', count


def build_html(rows, periods):
    period_idx = {p: i for i, p in enumerate(periods)}

    def row_period_class(r):
        ym = r.get('departure_date', '')[:7]
        return f'p-{period_idx.get(ym, 0)}'

    lines   = sorted(set(r['cruise_line'] for r in rows if r['cruise_line']))
    by_line = defaultdict(list)
    for r in rows:
        by_line[r['cruise_line'] or '(unknown)'].append(r)

    # Volume leader computation — curated lines sorted by count desc
    line_counts = {line: len(grp) for line, grp in by_line.items()}
    curated_present = [l for l in by_line if l in CURATED_LINES]
    max_curated = max((line_counts[l] for l in curated_present), default=1)
    top_line = max(curated_present, key=lambda l: line_counts[l]) if curated_present else None
    sorted_curated = sorted(curated_present, key=lambda l: -line_counts[l])
    sorted_extras  = sorted(l for l in by_line if l not in CURATED_LINES)
    all_sorted_lines = sorted_curated + sorted_extras

    period_counts = [
        sum(1 for r in rows if r.get('departure_date', '')[:7] == p)
        for p in periods
    ]
    multi_source = [r for r in rows
                    if sum(1 for k in ALL_SOURCE_COLS if r.get(k) == 'Y') > 1]
    active_sources = [label for col, cls, ltr, label, wave in FLAG_MAP
                      if any(r.get(col) == 'Y' for r in rows)]
    n_sources = len(active_sources)

    sorted_rows = sorted(rows, key=lambda x: (x['cruise_line'], x['departure_date']))
    row_ids = {id(r): i for i, r in enumerate(sorted_rows)}

    # ── Table rows ─────────────────────────────────────────────────────────────
    table_rows_html = []
    for r in sorted_rows:
        idx = row_ids[id(r)]
        badge_html, _ = coverage_badge(r)
        pcls = row_period_class(r)
        dep  = r['departure_date'][:10] if r['departure_date'] else ''
        try:
            dep_fmt = datetime.strptime(dep, '%Y-%m-%d').strftime('%b %d')
        except Exception:
            dep_fmt = dep
        days  = r['days'] or '—'
        route = r['route'][:60] + ('…' if len(r['route']) > 60 else '') if r['route'] else '—'
        price = f'${int(r["price_usd"]):,}' if r.get('price_usd') and r['price_usd'].isdigit() else ''
        table_rows_html.append(
            f'<tr class="{pcls}" id="v-{idx}">'
            f'<td>{r["cruise_line"] or "—"}</td>'
            f'<td>{r["ship_name"] or "—"}</td>'
            f'<td class="date">{dep_fmt}</td>'
            f'<td class="num">{days}d</td>'
            f'<td class="route">{route}</td>'
            f'<td class="price">{price}</td>'
            f'<td class="cov">{badge_html}</td>'
            f'</tr>'
        )

    # ── Legend ─────────────────────────────────────────────────────────────────
    legend_items = [
        f'<span><span class="badge {cls}">{ltr}</span> {label}</span>'
        for col, cls, ltr, label, wave in FLAG_MAP
        if any(r.get(col) == 'Y' for r in rows)
    ]

    # ── Line cards ─────────────────────────────────────────────────────────────
    line_cards = []
    extra_count = 0
    for line in all_sorted_lines:
        group = sorted(by_line[line], key=lambda x: x['departure_date'])
        is_curated = line in CURATED_LINES
        if not is_curated:
            extra_count += 1

        # Volume bar (curated lines only)
        if is_curated:
            count = line_counts[line]
            pct   = round(count / max_curated * 100)
            leader_badge = '<span class="vol-leader">&#9733; Most Active</span>' if line == top_line else ''
            vol_html = (
                f'<div class="card-vol-label">'
                f'<span>{count} sailing{"s" if count != 1 else ""}</span>'
                f'{leader_badge}</div>'
                f'<div class="card-vol-bar">'
                f'<div class="card-vol-fill" style="width:{pct}%"></div>'
                f'</div>'
            )
        else:
            vol_html = ''

        period_pill_html = ''.join(
            f'<span class="pill-{i}">'
            f'{sum(1 for r in group if r.get("departure_date","")[:7]==p)}'
            f' {month_abbr(p)}</span>'
            for i, p in enumerate(periods)
        )

        ships = sorted(set(r['ship_name'] for r in group if r['ship_name']))
        ship_str = ', '.join(ships[:3]) + (f' +{len(ships)-3}' if len(ships) > 3 else '')

        prices = [int(r['price_usd']) for r in group
                  if r.get('price_usd') and r['price_usd'].isdigit()]
        if prices:
            price_html = (
                f'<div class="card-price">'
                f'From ${min(prices):,}'
                f' &nbsp;·&nbsp; Avg ${round(sum(prices)/len(prices)):,}'
                f'</div>'
            )
        else:
            price_html = ''

        urls = LINE_URLS.get(line)
        if urls:
            own_url, dlx_url = urls
            link_html = (
                f'<div class="card-links">'
                f'<a href="{own_url}" target="_blank" rel="noopener">Line site ↗</a>'
                f'<a href="{dlx_url}" target="_blank" rel="noopener">Deluxe ↗</a>'
                f'</div>'
            )
        else:
            link_html = ''

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
            pi = period_idx.get(dep[:7], 0)
            voyage_links.append(
                f'<a href="#v-{idx}" class="period-link-{pi}">'
                f'{ship} · {dep_fmt} · {days}d</a>'
            )
        overflow = len(group) - 14
        overflow_html = (f'<span class="more-voyages">… {overflow} more</span>'
                         if overflow > 0 else '')

        extra_cls = '' if is_curated else ' extra-line'
        line_cards.append(f'''
        <div class="card{extra_cls}">
          <div class="card-line">{line}</div>
          <div class="card-ships">{ship_str or "—"}</div>
          {vol_html}
          <div class="card-counts">{period_pill_html}</div>
          {price_html}
          {link_html}
          <div class="card-voyages">{''.join(voyage_links)}{overflow_html}</div>
        </div>''')

    extra_html = ''
    if extra_count > 0:
        extra_html = f'''
        <div id="toggle-bar" style="margin-top:10px;">
          <button id="toggle-btn" onclick="toggleExtraLines()"
            style="padding:6px 14px;font-size:0.8rem;border:1px solid #0033A0;
                   border-radius:4px;background:#fff;color:#0033A0;cursor:pointer;">
            Show all lines ({extra_count} more)
          </button>
        </div>'''

    # ── Dynamic period CSS ──────────────────────────────────────────────────────
    period_css_parts = []
    for i, p in enumerate(periods):
        border_col, pill_bg, pill_text = PERIOD_PALETTE[i % len(PERIOD_PALETTE)]
        period_css_parts.append(
            f'  tr.p-{i} td {{ border-left: 3px solid {border_col}; }}\n'
            f'  .pill-{i} {{ background: {pill_bg}; color: {pill_text}; font-size: 0.68rem;'
            f' padding: 2px 8px; border-radius: 10px; font-weight: bold; }}\n'
            f'  .period-link-{i} {{ border-left: 3px solid {border_col}; }}'
        )
    period_css = '\n'.join(period_css_parts)

    # ── Stats bar ───────────────────────────────────────────────────────────────
    stats_period_html = ''.join(
        f'<div class="stat"><div class="stat-num">{period_counts[i]}</div>'
        f'<div class="stat-lbl">{month_label(p, "%B")}</div></div>'
        for i, p in enumerate(periods)
    )

    # ── Month filter options ────────────────────────────────────────────────────
    month_options = ''.join(
        f'<option value="p-{i}">{month_label(p)}</option>'
        for i, p in enumerate(periods)
    )

    # ── Period legend note ──────────────────────────────────────────────────────
    if len(periods) >= 2:
        note_parts = []
        for i, p in enumerate(periods):
            col = PERIOD_PALETTE[i % len(PERIOD_PALETTE)][0]
            note_parts.append(f'<span style="color:{col}">■</span> {month_label(p)}')
        period_legend = (' &nbsp;·&nbsp; '.join(note_parts)
                         + ' &nbsp;·&nbsp; Highlighted = multi-source confirmed')
    else:
        period_legend = 'Highlighted = multi-source confirmed'

    # ── Title ───────────────────────────────────────────────────────────────────
    if not periods:
        title_period = 'All Periods'
    elif len(periods) == 1:
        title_period = month_label(periods[0])
    elif len(periods) == 2 and periods[0][:4] == periods[1][:4]:
        title_period = (f'{month_label(periods[0], "%B")}'
                        f' &amp; {month_label(periods[1])}')
    else:
        title_period = ' &amp; '.join(month_label(p) for p in periods)

    sources_header = ' · '.join(active_sources)

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>T2 Cruise Intel — {title_period}</title>
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
  .card.extra-line {{ display: none; }}
  .card:hover {{ box-shadow: 0 4px 14px rgba(0,51,160,0.14); border-color: #0033A0; }}
  .card-line  {{ font-weight: bold; font-size: 0.88rem; color: #0033A0;
                 border-bottom: 1px solid #eee; padding-bottom: 5px; margin-bottom: 6px; }}
  .card-ships {{ font-size: 0.73rem; color: #666; font-style: italic; margin-bottom: 6px; }}
  .card-counts {{ display: flex; gap: 6px; margin-bottom: 6px; flex-wrap: wrap; }}
  .card-price {{ font-size: 0.72rem; color: #1a7a1a; margin-bottom: 6px; }}
  .card-links {{ display: flex; gap: 8px; margin-bottom: 8px; }}
  .card-links a {{ font-size: 0.7rem; color: #0033A0; text-decoration: none;
                   padding: 2px 7px; border: 1px solid #c0cfe8; border-radius: 3px;
                   background: #f0f4ff; }}
  .card-links a:hover {{ background: #0033A0; color: #fff; }}

  /* ── Voyage links inside cards ──────────────────────────── */
  .card-voyages {{ display: flex; flex-direction: column; gap: 3px; }}
  .card-voyages a {{ font-size: 0.72rem; color: #222; text-decoration: none;
                     padding: 2px 5px; border-radius: 3px; display: block;
                     line-height: 1.4; transition: background 0.1s; }}
  .card-voyages a:hover {{ background: #f0f4ff; color: #0033A0; }}
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

  /* ── Volume bar (curated cards) ────────────────────────── */
  .card-vol-label {{ font-size: 0.67rem; color: #888; margin-bottom: 3px;
                     display: flex; justify-content: space-between; align-items: center; }}
  .card-vol-bar   {{ background: #e8e8e8; border-radius: 3px; height: 4px;
                     margin-bottom: 7px; overflow: hidden; }}
  .card-vol-fill  {{ background: linear-gradient(to right, #0033A0, #6492e0);
                     height: 4px; border-radius: 3px; }}
  .vol-leader     {{ background: #f0c040; color: #664d00; font-size: 0.61rem;
                     font-weight: bold; padding: 1px 7px; border-radius: 10px; }}

  /* ── Legend & misc ──────────────────────────────────────── */
  .legend {{ display: flex; gap: 10px; font-size: 0.73rem; color: #555;
             margin-bottom: 10px; flex-wrap: wrap; align-items: center; }}
  .legend span {{ display: flex; align-items: center; gap: 4px; }}
  .legend-note {{ font-size: 0.72rem; color: #888; margin-left: 8px; font-style: italic; }}
  .count-bar {{ font-size: 0.8rem; color: #555; margin-bottom: 8px; }}
  #count-display {{ font-weight: bold; color: #0033A0; }}

  /* ── Period-specific (generated) ───────────────────────── */
{period_css}
</style>
</head>
<body>

<div class="header">
  <h1>T2 Cruise Intelligence — {title_period}</h1>
  <p>Dreams2Memories Travel, LLC &nbsp;·&nbsp; Wing Exercise 2026-05-24</p>
  <p style="margin-top:6px; font-size:0.77rem; opacity:0.65">{sources_header}</p>
</div>

<div class="stats-bar">
  <div class="stat"><div class="stat-num">{len(rows)}</div><div class="stat-lbl">Total Sailings</div></div>
  {stats_period_html}
  <div class="stat"><div class="stat-num">{len(lines)}</div><div class="stat-lbl">Cruise Lines</div></div>
  <div class="stat"><div class="stat-num">{len(multi_source)}</div><div class="stat-lbl">Multi-Source</div></div>
  <div class="stat"><div class="stat-num">{n_sources}</div><div class="stat-lbl">Sources</div></div>
</div>

<div class="section">
  <h2>By Cruise Line — Click a Voyage to Jump to Table</h2>
  <div class="cards">{''.join(line_cards)}</div>
  {extra_html}
</div>

<div class="section">
  <h2>All Sailings</h2>
  <div class="legend">
    {'  '.join(legend_items)}
    <span class="legend-note">{period_legend}</span>
  </div>
  <div class="search-bar">
    <input type="text" id="search" placeholder="Search ship, line, route…" oninput="filterTable()">
    <label>Month: <select id="monthFilter" onchange="filterTable()">
      <option value="">All</option>
      {month_options}
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
let extraLinesVisible = false;

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

function toggleExtraLines() {{
  extraLinesVisible = !extraLinesVisible;
  document.querySelectorAll('.card.extra-line').forEach(c => {{
    c.style.display = extraLinesVisible ? '' : 'none';
  }});
  const btn = document.getElementById('toggle-btn');
  if (btn) {{
    btn.textContent = extraLinesVisible
      ? 'Show curated only'
      : 'Show all lines ({extra_count} more)';
  }}
}}

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
    parser = argparse.ArgumentParser(description='Generate T2 cruise intelligence report')
    parser.add_argument('--period',
                        help='Comma-separated YYYY-MM periods, e.g. 2026-10,2026-11')
    parser.add_argument('--csv',    help='Path to master CSV (overrides config MASTER_CSV)')
    parser.add_argument('--output', help='Output HTML path (overrides default)')
    args = parser.parse_args()

    rows = load_data(args.csv)

    if args.period:
        periods = sorted(p.strip() for p in args.period.split(','))
        rows = [r for r in rows if r.get('departure_date', '')[:7] in set(periods)]
    else:
        periods = detect_periods(rows)

    if not rows:
        print('ERROR: No rows found for the requested period(s). '
              'Check --period flag and CSV data.')
        sys.exit(1)

    html = build_html(rows, periods)

    out_path = Path(args.output) if args.output else OUTPUT_HTML
    out_path.write_text(html)
    print(f'Report → {out_path}')
    print(f'  {len(rows)} sailings | '
          f'{len(set(r["cruise_line"] for r in rows if r["cruise_line"]))} lines | '
          f'periods: {", ".join(periods)}')


if __name__ == '__main__':
    main()
