#!/usr/bin/env python3
"""Build VTG cruise intel HTML report — exact T2_CRUISE_REPORT format."""
import re, sys, base64
from collections import defaultdict
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

DATA_FILE = Path.home() / "Thunderbird" / "intel" / "vtg_structured_20260626.txt"
OUT_FILE  = Path.home() / "Thunderbird" / "output" / "VTG_INTEL_REPORT_20260626.html"
TOKEN     = Path.home() / "Thunderbird" / "creds" / "johnloucks3_token.json"

LINE_ORDER = ["Regent", "Silversea", "Explora Journeys", "Atlas", "Paul Gauguin", "Ponant"]
LINE_SITE  = {
    "Regent":           "https://www.rssc.com/cruises",
    "Silversea":        "https://www.silversea.com/cruise-search.html",
    "Explora Journeys": "https://www.explorajourneys.com/en/cruises",
    "Atlas":            "https://www.atlasoceancruises.com/find-a-cruise/",
    "Paul Gauguin":     "https://www.pgcruises.com/cruises/",
    "Ponant":           "https://us.ponant.com/cruises",
}
VTG_BASE = "https://www.vacationstogo.com"

# Period (year) definitions → pill class and label
PERIODS = [
    ("p-0", "2026",  "#e8f0ff", "#0033A0"),
    ("p-1", "2027",  "#fff3cd", "#856404"),
    ("p-2", "2028+", "#fce8f3", "#7b1a5a"),
]


def parse_deals(path):
    line_names = ["Regent", "Silversea", "Explora Journeys", "Atlas Ocean Voyages",
                  "Atlas", "Paul Gauguin", "Ponant"]
    ln_pat = '|'.join(re.escape(l) for l in line_names)
    row_re = re.compile(
        r'^#(\d+)\s+(\d+)\s+'
        r'(.+?)\s+'
        r'(' + ln_pat + r')\s*/\s*'
        r'(.+?)\s+'
        r'(?:5\.5|6)\s+\$([0-9,]+)\s+\$([0-9,]+)\s+(\d+)%\s+(.+)$'
    )
    deals = []
    with open(path) as f:
        for raw in f:
            line = raw.strip()
            if not line or not line.startswith('#') or not line[1:2].isdigit():
                continue
            m = row_re.match(line)
            if not m:
                continue
            fdeal, nights, before, ln, ship, orig, disc, pct, status = m.groups()
            # Extract date from before
            dm = re.match(r'^(\w{3}\s+\d+(?:,\s*\d{4})?)\s*(.*)', before.strip())
            if dm:
                date_str = dm.group(1)
                route    = dm.group(2).strip()
            else:
                date_str = ''
                route    = before.strip()
            # Determine year
            yr_m = re.search(r'(\d{4})', date_str)
            year = int(yr_m.group(1)) if yr_m else 2026
            if year >= 2028:
                period = 'p-2'
            elif year == 2027:
                period = 'p-1'
            else:
                period = 'p-0'
            canonical = ln.replace(' Ocean Voyages', '')
            deals.append({
                'fdeal':  fdeal,
                'nights': int(nights),
                'date':   date_str,
                'route':  route,
                'line':   canonical,
                'ship':   ship.strip(),
                'orig':   int(orig.replace(',', '')),
                'disc':   int(disc.replace(',', '')),
                'pct':    int(pct),
                'status': status.strip(),
                'period': period,
                'year':   year,
                'suite':  'Suite' in status,
            })
    return deals


def build_html(deals):
    total   = len(deals)
    by_line = defaultdict(list)
    for d in deals:
        by_line[d['line']].append(d)
    all_ships = defaultdict(set)
    for d in deals:
        all_ships[d['line']].add(d['ship'])

    yr_counts = defaultdict(int)
    for d in deals:
        yr_counts[d['year']] += 1

    # ── CARDS ──────────────────────────────────────────────────────
    max_count = max(len(v) for v in by_line.values()) if by_line else 1
    cards_html = ""
    for ln in LINE_ORDER:
        lds = by_line.get(ln, [])
        if not lds:
            continue
        ships_list = sorted(all_ships[ln])
        ships_str  = ', '.join(ships_list[:3])
        if len(ships_list) > 3:
            ships_str += f' +{len(ships_list)-3}'
        bar_width  = int(len(lds) / max_count * 100)
        leader_tag = '<span class="vol-leader">&#9733; Most Deals</span>' if len(lds) == max_count else ''
        # Period pill counts
        p0 = sum(1 for d in lds if d['period'] == 'p-0')
        p1 = sum(1 for d in lds if d['period'] == 'p-1')
        p2 = sum(1 for d in lds if d['period'] == 'p-2')
        pills = []
        if p0: pills.append(f'<span class="pill-0">{p0} 2026</span>')
        if p1: pills.append(f'<span class="pill-1">{p1} 2027</span>')
        if p2: pills.append(f'<span class="pill-2">{p2} 2028+</span>')
        pills_html = ' '.join(pills)
        min_disc  = min(d['disc'] for d in lds)
        avg_disc  = sum(d['disc'] for d in lds) / len(lds)
        site_url  = LINE_SITE.get(ln, '#')
        vtg_url   = f"{VTG_BASE}/search.cfm?cruise_line={ln.replace(' ','+')}"
        # Voyage links — top 14 sorted by price
        sorted_lds = sorted(lds, key=lambda x: x['disc'])
        voyage_links = ''
        for i, d in enumerate(sorted_lds[:14]):
            idx  = deals.index(d)
            voyage_links += (
                f'<a href="#v-{idx}" class="period-link-{d["period"][-1]}">'
                f'{d["ship"]} · {d["date"]} · {d["nights"]}nt · '
                f'<strong>${d["disc"]:,}</strong> (-{d["pct"]}%)</a>'
            )
        more = len(lds) - 14
        if more > 0:
            voyage_links += f'<span class="more-voyages">… {more} more</span>'

        cards_html += f"""
    <div class="card">
      <div class="card-line">{ln}</div>
      <div class="card-ships">{ships_str}</div>
      <div class="card-vol-label"><span>{len(lds)} deals</span>{leader_tag}</div>
      <div class="card-vol-bar"><div class="card-vol-fill" style="width:{bar_width}%"></div></div>
      <div class="card-counts">{pills_html}</div>
      <div class="card-price">From <strong>${min_disc:,}</strong> · Avg ${avg_disc:,.0f} PPDO</div>
      <div class="card-links">
        <a href="{site_url}" target="_blank" rel="noopener">Line site ↗</a>
        <a href="{VTG_BASE}" target="_blank" rel="noopener">VTG ↗</a>
      </div>
      <div class="card-voyages">{voyage_links}</div>
    </div>"""

    # ── TABLE ROWS ─────────────────────────────────────────────────
    rows_html = ""
    for i, d in enumerate(deals):
        multi_cls = ' multi' if d['suite'] else ''
        cov_cls   = ' class="coverage multi"' if d['suite'] else ' class="coverage"'
        suit_badge = (
            '<span class="badge" style="background:#1a7a1a;color:#fff;">'
            'S</span>' if d['suite'] else ''
        )
        pct_color = '#1a7a1a' if d['pct'] >= 60 else ('#856404' if d['pct'] >= 40 else '#555')
        rows_html += (
            f'<tr id="v-{i}" class="{d["period"]}{multi_cls}" '
            f'data-line="{d["line"]}" data-year="{d["year"]}">\n'
            f'  <td>{d["line"]}</td>\n'
            f'  <td>{d["ship"]}</td>\n'
            f'  <td class="date">{d["date"]}</td>\n'
            f'  <td class="num">{d["nights"]}nt</td>\n'
            f'  <td class="route">{d["route"][:70]}</td>\n'
            f'  <td class="price">${d["disc"]:,}</td>\n'
            f'  <td class="num" style="color:{pct_color};font-weight:bold;">{d["pct"]}% off</td>\n'
            f'  <td class="num" style="color:#aaa;font-size:0.75rem;">${d["orig"]:,}</td>\n'
            f'  <td{cov_cls}>{suit_badge} '
            f'<span style="font-size:0.72rem;color:#666;">#FD{d["fdeal"]}</span></td>\n'
            f'</tr>\n'
        )

    # ── LINE FILTER OPTIONS ─────────────────────────────────────────
    line_opts = ''.join(
        f'<option value="{ln}">{ln} ({len(by_line[ln])})</option>'
        for ln in LINE_ORDER if ln in by_line
    )

    # ── STATS ──────────────────────────────────────────────────────
    suite_count = sum(1 for d in deals if d['suite'])
    avg_pct     = sum(d['pct'] for d in deals) / total
    min_price   = min(d['disc'] for d in deals)
    y26 = yr_counts.get(2026, 0)
    y27 = yr_counts.get(2027, 0)
    y28p= total - y26 - y27

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>VTG Cruise Intel — Dreams2Memories Travel</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: Georgia, serif; background: #f7f3ea; color: #1a1a1a; }}

  .header {{ background: #0033A0; color: #fff; padding: 28px 40px 20px; }}
  .header h1 {{ font-size: 1.6rem; font-weight: normal; letter-spacing: 0.5px; }}
  .header p  {{ font-size: 0.82rem; opacity: 0.8; margin-top: 5px; line-height: 1.5; }}
  .stats-bar {{ display: flex; gap: 24px; padding: 18px 40px; background: #1a1a1a;
               color: #f7f3ea; flex-wrap: wrap; }}
  .stat {{ text-align: center; }}
  .stat-num {{ font-size: 2rem; font-weight: bold; color: #f0c040; line-height: 1; }}
  .stat-lbl {{ font-size: 0.7rem; text-transform: uppercase; letter-spacing: 1px;
               opacity: 0.7; margin-top: 2px; }}

  .section {{ padding: 24px 40px; }}
  .section h2 {{ font-size: 1rem; text-transform: uppercase; letter-spacing: 1.5px;
                 color: #0033A0; border-bottom: 2px solid #0033A0;
                 padding-bottom: 6px; margin-bottom: 16px; }}

  .cards {{ display: flex; flex-wrap: wrap; gap: 12px; }}
  .card {{ background: #fff; border: 1px solid #ddd; border-radius: 8px;
           padding: 12px 14px; min-width: 220px; flex: 1 1 220px; max-width: 300px;
           transition: box-shadow 0.15s, border-color 0.15s; }}
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
  .card-voyages {{ display: flex; flex-direction: column; gap: 3px; }}
  .card-voyages a {{ font-size: 0.72rem; color: #222; text-decoration: none;
                     padding: 2px 5px; border-radius: 3px; display: block;
                     line-height: 1.4; transition: background 0.1s; }}
  .card-voyages a:hover {{ background: #f0f4ff; color: #0033A0; }}
  .more-voyages {{ font-size: 0.68rem; color: #888; padding: 2px 5px; font-style: italic; }}

  .search-bar {{ margin-bottom: 12px; display: flex; gap: 10px;
                 align-items: center; flex-wrap: wrap; }}
  .search-bar input  {{ padding: 8px 12px; border: 1px solid #ccc; border-radius: 4px;
                        font-size: 0.9rem; width: 280px; background: #fff; }}
  .search-bar select {{ padding: 8px 10px; border: 1px solid #ccc; border-radius: 4px;
                        font-size: 0.85rem; background: #fff; }}
  .search-bar label  {{ font-size: 0.8rem; color: #555; }}
  .search-bar button {{ padding: 8px 14px; background: #0033A0; color: #fff;
                        border: none; border-radius: 4px; cursor: pointer; font-size: 0.82rem; }}
  .search-bar button:hover {{ background: #002280; }}

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
  .coverage.multi {{ background: #fffbe6; border-radius: 4px; padding: 1px 3px; }}
  .badge {{ display: inline-block; width: 18px; height: 18px; border-radius: 3px;
            font-size: 0.62rem; font-weight: bold; text-align: center;
            line-height: 18px; margin-right: 2px; }}

  .card-vol-label {{ font-size: 0.67rem; color: #888; margin-bottom: 3px;
                     display: flex; justify-content: space-between; align-items: center; }}
  .card-vol-bar   {{ background: #e8e8e8; border-radius: 3px; height: 4px;
                     margin-bottom: 7px; overflow: hidden; }}
  .card-vol-fill  {{ background: linear-gradient(to right, #0033A0, #6492e0);
                     height: 4px; border-radius: 3px; }}
  .vol-leader     {{ background: #f0c040; color: #664d00; font-size: 0.61rem;
                     font-weight: bold; padding: 1px 7px; border-radius: 10px; }}

  .legend {{ display: flex; gap: 10px; font-size: 0.73rem; color: #555;
             margin-bottom: 10px; flex-wrap: wrap; align-items: center; }}
  .count-bar {{ font-size: 0.8rem; color: #555; margin-bottom: 8px; }}
  #count-display {{ font-weight: bold; color: #0033A0; }}

  tr.p-0 td {{ border-left: 3px solid #0033A0; }}
  .pill-0 {{ background: #e8f0ff; color: #0033A0; font-size: 0.68rem; padding: 2px 8px;
              border-radius: 10px; font-weight: bold; }}
  .period-link-0 {{ border-left: 3px solid #0033A0; }}
  tr.p-1 td {{ border-left: 3px solid #856404; }}
  .pill-1 {{ background: #fff3cd; color: #856404; font-size: 0.68rem; padding: 2px 8px;
              border-radius: 10px; font-weight: bold; }}
  .period-link-1 {{ border-left: 3px solid #856404; }}
  tr.p-2 td {{ border-left: 3px solid #7b1a5a; }}
  .pill-2 {{ background: #fce8f3; color: #7b1a5a; font-size: 0.68rem; padding: 2px 8px;
              border-radius: 10px; font-weight: bold; }}
  .period-link-2 {{ border-left: 3px solid #7b1a5a; }}
</style>
</head>
<body>

<div class="header">
  <h1>VTG Cruise Intel — 2026-06-26</h1>
  <p>Dreams2Memories Travel, LLC &nbsp;·&nbsp; FastDeal Authenticated Scrape</p>
  <p style="margin-top:6px; font-size:0.77rem; opacity:0.65">Regent &nbsp;·&nbsp; Silversea &nbsp;·&nbsp; Explora Journeys &nbsp;·&nbsp; Atlas Ocean Voyages &nbsp;·&nbsp; Paul Gauguin &nbsp;·&nbsp; Ponant &nbsp;·&nbsp; VacationsToGo.com</p>
</div>

<div class="stats-bar">
  <div class="stat"><div class="stat-num">{total:,}</div><div class="stat-lbl">Total Deals</div></div>
  <div class="stat"><div class="stat-num">{y26}</div><div class="stat-lbl">2026</div></div>
  <div class="stat"><div class="stat-num">{y27}</div><div class="stat-lbl">2027</div></div>
  <div class="stat"><div class="stat-num">{y28p}</div><div class="stat-lbl">2028+</div></div>
  <div class="stat"><div class="stat-num">{len(LINE_ORDER)}</div><div class="stat-lbl">Cruise Lines</div></div>
  <div class="stat"><div class="stat-num">{suite_count}</div><div class="stat-lbl">Suite Available</div></div>
  <div class="stat"><div class="stat-num">{avg_pct:.0f}%</div><div class="stat-lbl">Avg Discount</div></div>
  <div class="stat"><div class="stat-num">${min_price:,}</div><div class="stat-lbl">Lowest PPDO</div></div>
</div>

<div class="section">
  <h2>By Cruise Line — Click a Deal to Jump to Table</h2>
  <div class="cards">
{cards_html}
  </div>
</div>

<div class="section">
  <h2>All Deals
    <span style="font-weight:normal; font-size:0.8rem; color:#888; text-transform:none; letter-spacing:0;">
      &nbsp;·&nbsp; <span id="count-display">{total}</span> showing &nbsp;·&nbsp;
      Highlighted = Suite available
    </span>
  </h2>

  <div class="search-bar">
    <input type="text" id="search" placeholder="Search ship, line, route…" oninput="filterTable()">
    <label>Year: <select id="yearFilter" onchange="filterTable()">
      <option value="">All</option>
      <option value="p-0">2026</option>
      <option value="p-1">2027</option>
      <option value="p-2">2028+</option>
    </select></label>
    <label>Line: <select id="lineFilter" onchange="filterTable()">
      <option value="">All lines</option>
      {line_opts}
    </select></label>
    <label>Max price ($): <input type="number" id="maxPrice" placeholder="" oninput="filterTable()" style="width:100px;"></label>
    <label>Min discount (%): <input type="number" id="minDisc" placeholder="" oninput="filterTable()" style="width:80px;"></label>
    <label><input type="checkbox" id="suiteOnly" onchange="filterTable()"> &nbsp;Suite only</label>
    <button onclick="resetFilters()">Reset</button>
  </div>

  <div class="legend">
    <span><span class="pill-0">2026</span> Near-term</span>
    <span><span class="pill-1">2027</span> Next year</span>
    <span><span class="pill-2">2028+</span> Future</span>
    <span style="background:#fffbe6;padding:2px 6px;border-radius:3px;">Highlighted = suite available</span>
  </div>

  <table id="dealTable">
    <thead>
      <tr>
        <th onclick="sortTable(0)">Line</th>
        <th onclick="sortTable(1)">Ship</th>
        <th onclick="sortTable(2)">Date</th>
        <th onclick="sortTable(3)">Nights</th>
        <th onclick="sortTable(4)">Route / From</th>
        <th onclick="sortTable(5)">Price PPDO</th>
        <th onclick="sortTable(6)">Discount</th>
        <th onclick="sortTable(7)">Was</th>
        <th>FastDeal / Status</th>
      </tr>
    </thead>
    <tbody id="tableBody">
{rows_html}
    </tbody>
  </table>
</div>

<div style="padding:20px 40px; background:#1a1a1a; color:#888; font-size:0.75rem; text-align:center; margin-top:24px;">
  Generated 2026-06-26 · Dreams2Memories Travel, LLC · VTG FastDeal authenticated scrape · All prices USD per person double occupancy · Subject to availability · Book by phone 800-338-4962
</div>

<script>
let sortDir = {{}};

function filterTable() {{
  const q        = document.getElementById('search').value.toLowerCase();
  const year     = document.getElementById('yearFilter').value;
  const line     = document.getElementById('lineFilter').value.toLowerCase();
  const maxP     = parseFloat(document.getElementById('maxPrice').value) || Infinity;
  const minD     = parseFloat(document.getElementById('minDisc').value) || 0;
  const suiteOnly= document.getElementById('suiteOnly').checked;
  const rows     = document.querySelectorAll('#tableBody tr');
  let visible = 0;
  rows.forEach(row => {{
    const cells    = row.querySelectorAll('td');
    const isYear   = !year  || row.classList.contains(year);
    const isLine   = !line  || (cells[0]?.textContent.toLowerCase() === line);
    const priceStr = cells[5]?.textContent.replace(/[$,]/g,'') || '99999';
    const discStr  = cells[6]?.textContent.replace(/[^0-9]/g,'') || '0';
    const price    = parseFloat(priceStr) || 99999;
    const disc     = parseFloat(discStr) || 0;
    const isSuite  = !suiteOnly || row.classList.contains('multi');
    const words = q.split(/\s+/).filter(Boolean);
    const rowText = row.textContent.toLowerCase();
    const isSearch = !q || words.every(w => rowText.includes(w));
    const isPrice  = price <= maxP;
    const isDisc   = disc >= minD;
    const show = isYear && isLine && isSuite && isSearch && isPrice && isDisc;
    row.classList.toggle('hidden', !show);
    if (show) visible++;
  }});
  document.getElementById('count-display').textContent = visible;
}}

function resetFilters() {{
  document.getElementById('search').value        = '';
  document.getElementById('yearFilter').selectedIndex = 0;
  document.getElementById('lineFilter').selectedIndex = 0;
  document.getElementById('maxPrice').value      = '';
  document.getElementById('minDisc').value       = '';
  document.getElementById('suiteOnly').checked   = false;
  filterTable();
}}

function sortTable(col) {{
  const tbody = document.getElementById('tableBody');
  const rows  = Array.from(tbody.querySelectorAll('tr'));
  sortDir[col] = !sortDir[col];
  rows.sort((a, b) => {{
    const av = a.cells[col]?.textContent.trim() || '';
    const bv = b.cells[col]?.textContent.trim() || '';
    const an = parseFloat(av.replace(/[$,%nt]/g,''));
    const bn = parseFloat(bv.replace(/[$,%nt]/g,''));
    if (!isNaN(an) && !isNaN(bn)) return sortDir[col] ? an-bn : bn-an;
    return sortDir[col] ? av.localeCompare(bv) : bv.localeCompare(av);
  }});
  rows.forEach(r => tbody.appendChild(r));
}}

window.addEventListener('hashchange', () => {{
  const t = document.querySelector(':target');
  if (t) t.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
}});

filterTable();
</script>
</body>
</html>"""
    return html


def send_email(subject, html_body):
    creds   = Credentials.from_authorized_user_file(TOKEN)
    service = build('gmail', 'v1', credentials=creds, cache_discovery=False)
    msg = MIMEMultipart('alternative')
    msg['To']      = 'johnloucks3@gmail.com'
    msg['From']    = 'johnloucks3@gmail.com'
    msg['Subject'] = subject
    msg.attach(MIMEText(html_body, 'html'))
    raw    = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    result = service.users().messages().send(userId='me', body={'raw': raw}).execute()
    return result['id']


if __name__ == '__main__':
    print("Parsing…")
    deals = parse_deals(DATA_FILE)
    print(f"  {len(deals)} deals")
    by_line = defaultdict(list)
    for d in deals:
        by_line[d['line']].append(d)
    for ln in LINE_ORDER:
        print(f"  {ln}: {len(by_line.get(ln,[]))}")

    print("Building HTML…")
    html = build_html(deals)
    Path(OUT_FILE).write_text(html)
    sz = len(html)
    print(f"  Saved → {OUT_FILE}  ({sz:,} chars)")

    if '--no-email' not in sys.argv:
        print("Sending email…")
        msg_id = send_email(
            f"⚡ VTG Cruise Intel — {len(deals):,} FastDeals · 6 Luxury Lines [2026-06-26]",
            html
        )
        print(f"  SENT: {msg_id}")
    print("Done.")
