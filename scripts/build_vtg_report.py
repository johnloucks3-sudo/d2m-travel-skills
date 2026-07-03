#!/usr/bin/env python3
"""Build VTG cruise intel HTML report matching T2_CRUISE_REPORT.html format."""
import re
import sys
from collections import defaultdict
from pathlib import Path
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

DATA_FILE = "/home/john/Thunderbird/intel/vtg_structured_20260626.txt"
OUT_FILE  = "/home/john/Thunderbird/intel/vtg_intel_report_20260626.html"
TOKEN     = "/home/john/Thunderbird/creds/johnloucks3_token.json"

LINE_ORDER = ["Regent", "Silversea", "Explora Journeys", "Atlas", "Paul Gauguin", "Ponant"]
LINE_COLORS = {
    "Regent":          "#c8a96e",
    "Silversea":       "#7eb8d4",
    "Explora Journeys":"#a0c878",
    "Atlas":           "#d4907e",
    "Paul Gauguin":    "#b89ed4",
    "Ponant":          "#7ec8b8",
}
LINE_BADGE = {
    "Regent":          "R",
    "Silversea":       "S",
    "Explora Journeys":"E",
    "Atlas":           "A",
    "Paul Gauguin":    "G",
    "Ponant":          "P",
}

def parse_vtg(path):
    deals = []
    current_line = None
    row_re = re.compile(
        r'^#(\d+)\s+(\d+)\s+(.+?)\s+(Regent|Silversea|Atlas|Explora Journeys|Paul Gauguin|Ponant)\s*/\s*(.+?)\s+6\s+\$([0-9,]+)\s+\$([0-9,]+)\s+(\d+)%\s+(.+)$'
    )
    with open(path) as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith('#') and 'SAILINGS' not in line and 'FastDeal' not in line and not line[1:].isdigit() and not line[1:2].isdigit():
                m2 = re.match(r'^# (\w[\w ]+?) — \d+ SAILINGS', line)
                if m2:
                    current_line = m2.group(1)
                continue
            if '# FastDeal' in line:
                continue
            # Try to match deal row
            m = row_re.match(line)
            if not m:
                # Try relaxed parse: starts with #digits
                m2 = re.match(r'^#(\d+)\s+(\d+)\s+(.+)', line)
                if m2:
                    fdeal = m2.group(1)
                    nights = m2.group(2)
                    rest = m2.group(3)
                    # Find line name
                    for ln in ["Regent", "Silversea", "Explora Journeys", "Atlas Ocean Voyages", "Paul Gauguin", "Ponant"]:
                        if ln in rest:
                            parts = rest.split(ln + ' /')
                            from_to = parts[0].strip()
                            after = parts[1].strip() if len(parts) > 1 else ""
                            # Extract ship and prices
                            ship_m = re.match(r'(.+?)\s+6\s+\$([0-9,]+)\s+\$([0-9,]+)\s+(\d+)%\s+(.+)', after)
                            if ship_m:
                                canonical_ln = ln.replace(" Ocean Voyages", "")
                                # Split from_to on date pattern
                                date_m = re.search(r'(\w{3}\s+\d+[\w,\s]*?)(?=[A-Z][a-z])', from_to)
                                deals.append({
                                    'fdeal': fdeal,
                                    'nights': int(nights),
                                    'date': '',
                                    'from': from_to,
                                    'to': '',
                                    'line': canonical_ln,
                                    'ship': ship_m.group(1).strip(),
                                    'orig': int(ship_m.group(2).replace(',','')),
                                    'disc': int(ship_m.group(3).replace(',','')),
                                    'pct':  int(ship_m.group(4)),
                                    'status': ship_m.group(5).strip(),
                                })
                            break
                continue
            fdeal, nights, datestr, ln, ship, orig, disc, pct, status = m.groups()
            # datestr is "Nights Date From To" — need to split properly
            # Actually the regex already captured them: group(3) is "date from to" combined
            # Let's re-split: first token = date, rest = from/to
            parts = datestr.strip()
            # The "from" and "to" are separated by the line name which is captured separately
            # So datestr = "Date From_port To_port" but all merged
            # Try to split on date pattern
            dm = re.match(r'^(\w{3}\s+\d+(?:,\s*\d{4})?)\s+(.+?),\s+([^,]+(?:,\s+[^/]+)?)\s+$', parts)
            if dm:
                date_part = dm.group(1)
                from_part = dm.group(2) + '...'
                to_part   = ''
            else:
                date_part = parts[:20].strip()
                from_part = parts[20:].strip()
                to_part   = ''
            canonical_ln = ln.replace(" Ocean Voyages", "")
            deals.append({
                'fdeal': fdeal,
                'nights': int(nights),
                'date': date_part,
                'from': from_part,
                'to': to_part,
                'line': canonical_ln,
                'ship': ship.strip(),
                'orig': int(orig.replace(',','')),
                'disc': int(disc.replace(',','')),
                'pct':  int(pct),
                'status': status.strip(),
            })
    return deals


def parse_v2(path):
    """Cleaner parser: read raw lines, use regex with known structure."""
    deals = []
    # Pattern: #FDEAL NIGHTS REST_OF_LINE
    # REST contains: date from_port LINE/SHIP 6 $ORIG $DISC PCT% STATUS
    line_names = ["Regent", "Silversea", "Explora Journeys", "Atlas Ocean Voyages", "Atlas", "Paul Gauguin", "Ponant"]
    # Build regex with all line names
    ln_pattern = '|'.join(re.escape(l) for l in line_names)
    row_re = re.compile(
        r'^#(\d+)\s+(\d+)\s+'          # fdeal, nights
        r'(.+?)\s+'                      # date+from+to (greedy, will trim)
        r'(' + ln_pattern + r')\s*/\s*' # line name
        r'(.+?)\s+'                      # ship
        r'(?:5\.5|6)\s+\$([0-9,]+)\s+\$([0-9,]+)\s+(\d+)%\s+(.+)$'  # cat, orig, disc, pct, status
    )
    with open(path) as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith('=') or line.startswith('#') and not line[1:2].isdigit():
                continue
            m = row_re.match(line)
            if not m:
                continue
            fdeal, nights, before_line, ln, ship, orig, disc, pct, status = m.groups()
            # before_line = "date from_port to_port" all concatenated
            # Extract date: first word(s) that look like "Dec 28" or "Jan 17, 2027" or "Jul 1"
            date_m = re.match(r'^(\w{3}\s+\d+(?:,\s*\d{4})?)\s+(.*)', before_line.strip())
            if date_m:
                date_part = date_m.group(1)
                from_to   = date_m.group(2).strip()
                # Try to split from/to at known separators... too complex, just store combined
                from_part = from_to
                to_part   = ''
            else:
                date_part = ''
                from_part = before_line.strip()
                to_part   = ''

            canonical = ln.replace(" Ocean Voyages", "")
            deals.append({
                'fdeal':  fdeal,
                'nights': int(nights),
                'date':   date_part,
                'route':  from_part,
                'line':   canonical,
                'ship':   ship.strip(),
                'orig':   int(orig.replace(',','')),
                'disc':   int(disc.replace(',','')),
                'pct':    int(pct),
                'status': status.strip(),
            })
    return deals


def build_html(deals):
    total = len(deals)
    by_line = defaultdict(list)
    for d in deals:
        by_line[d['line']].append(d)

    all_ships = defaultdict(set)
    for d in deals:
        all_ships[d['line']].add(d['ship'])

    # --- Line cards HTML ---
    cards_html = ""
    for ln in LINE_ORDER:
        lds = by_line.get(ln, [])
        if not lds:
            continue
        color = LINE_COLORS.get(ln, '#aaa')
        badge = LINE_BADGE.get(ln, ln[0])
        ships = sorted(all_ships[ln])
        ship_str = ', '.join(ships[:4])
        if len(ships) > 4:
            ship_str += f' +{len(ships)-4}'
        # Top 8 sailings preview
        top = sorted(lds, key=lambda x: x['disc'])[:8]
        top_html = ''.join(
            f'<div style="padding:2px 0;font-size:11px;color:#ccc;">'
            f'<span style="color:{color};">{d["ship"]}</span>'
            f' · <span style="color:#fff;">{d["date"]}</span>'
            f' · <span style="color:#4ade80;">{d["nights"]}nt</span>'
            f' · <span style="color:#f59e0b;">${d["disc"]:,}</span>'
            f' <span style="color:#7090cc;font-size:10px;">(-{d["pct"]}%)</span>'
            f'</div>'
            for d in top
        )
        more = len(lds) - 8
        if more > 0:
            top_html += f'<div style="color:#5060a0;font-size:11px;padding-top:4px;">… {more} more</div>'
        avgs = sum(d['disc'] for d in lds) / len(lds)
        mins = min(d['disc'] for d in lds)
        cards_html += f"""
<div style="background:#09095a;border:1px solid {color}55;border-radius:8px;padding:18px;margin-bottom:16px;">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;">
    <div>
      <span style="background:{color};color:#000;font-weight:bold;font-size:11px;padding:2px 7px;border-radius:3px;margin-right:8px;">{badge}</span>
      <span style="color:{color};font-size:16px;font-weight:bold;">{ln}</span>
    </div>
    <div style="text-align:right;">
      <span style="color:#4ade80;font-size:18px;font-weight:bold;">{len(lds)}</span>
      <span style="color:#7090cc;font-size:12px;"> deals</span>
    </div>
  </div>
  <div style="color:#7090cc;font-size:11px;margin-bottom:8px;">{ship_str}</div>
  <div style="color:#7090cc;font-size:11px;margin-bottom:10px;">
    From <span style="color:#4ade80;">${mins:,}</span> ·
    Avg <span style="color:#f59e0b;">${avgs:,.0f}</span>
  </div>
  {top_html}
</div>"""

    # --- Main table rows ---
    rows_html = ""
    for i, d in enumerate(deals):
        ln   = d['line']
        color = LINE_COLORS.get(ln, '#aaa')
        badge = LINE_BADGE.get(ln, ln[0])
        bg    = '#0a0a3a' if i % 2 == 0 else ''
        sold_color = '#f87171' if 'Sold' in d.get('status','') else '#4ade80'
        rows_html += (
            f'<tr data-line="{ln}" style="border-bottom:1px solid #1a1a4a;{f"background:{bg};" if bg else ""}">'
            f'<td style="padding:6px 8px;"><span style="background:{color};color:#000;font-size:10px;padding:1px 5px;border-radius:2px;">{badge}</span> '
            f'<span style="color:#e8f1ff;font-size:12px;">{ln}</span></td>'
            f'<td style="padding:6px 8px;color:#c8dcff;font-size:12px;">{d["ship"]}</td>'
            f'<td style="padding:6px 8px;color:#a8c4ff;font-size:12px;white-space:nowrap;">{d["date"]}</td>'
            f'<td style="padding:6px 8px;color:#7090cc;font-size:12px;text-align:center;">{d["nights"]}nt</td>'
            f'<td style="padding:6px 8px;color:#c8dcff;font-size:11px;">{d["route"][:60]}</td>'
            f'<td style="padding:6px 8px;color:#4ade80;font-size:13px;font-weight:bold;white-space:nowrap;">${d["disc"]:,}</td>'
            f'<td style="padding:6px 8px;color:#7090cc;font-size:11px;white-space:nowrap;">'
            f'<span style="color:#f59e0b;">-{d["pct"]}%</span> '
            f'<span style="color:#5060a0;font-size:10px;">(was ${d["orig"]:,})</span></td>'
            f'<td style="padding:6px 8px;color:#5060a0;font-size:10px;">#FD{d["fdeal"]}</td>'
            f'<td style="padding:6px 8px;color:{sold_color};font-size:11px;">{d["status"]}</td>'
            f'</tr>\n'
        )

    stats_total = total
    stats_lines = len(by_line)
    avg_disc = sum(d['pct'] for d in deals) / len(deals) if deals else 0
    min_price = min(d['disc'] for d in deals) if deals else 0

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>VTG Cruise Intel — Dreams2Memories Travel</title>
<style>
  body {{background:#07076b;color:#e8f1ff;font-family:Georgia,serif;margin:0;padding:24px;}}
  .container {{max-width:1200px;margin:0 auto;}}
  h1 {{color:#a8c4ff;font-size:24px;margin:0 0 4px;}}
  .subtitle {{color:#7090cc;font-size:13px;margin:0 0 20px;}}
  .stats {{display:flex;gap:12px;margin-bottom:24px;flex-wrap:wrap;}}
  .stat {{background:#09095a;border:1px solid #2a2a8f;border-radius:6px;padding:12px 20px;text-align:center;min-width:100px;}}
  .stat-num {{color:#4ade80;font-size:28px;font-weight:bold;display:block;}}
  .stat-lbl {{color:#7090cc;font-size:11px;display:block;}}
  .cards {{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:14px;margin-bottom:28px;}}
  .filter-bar {{background:#09095a;border:1px solid #2a2a8f;border-radius:6px;padding:14px;margin-bottom:16px;display:flex;gap:12px;align-items:center;flex-wrap:wrap;}}
  .filter-bar input, .filter-bar select {{background:#0d0d4a;border:1px solid #2a2a8f;color:#e8f1ff;padding:6px 10px;border-radius:4px;font-size:13px;}}
  .filter-bar label {{color:#7090cc;font-size:12px;}}
  table {{width:100%;border-collapse:collapse;font-size:12px;}}
  th {{color:#7090cc;text-align:left;padding:8px;border-bottom:1px solid #2a2a8f;font-size:11px;letter-spacing:0.5px;text-transform:uppercase;position:sticky;top:0;background:#07076b;}}
  .tbl-wrap {{max-height:600px;overflow-y:auto;border:1px solid #2a2a8f;border-radius:6px;}}
  .section-header {{background:#0a0a3a;border-bottom:1px solid #1a1a4a;}}
  .section-header td {{padding:5px 8px;color:#5060a0;font-size:11px;letter-spacing:1px;text-transform:uppercase;}}
  .footer {{text-align:center;padding:20px 0 8px;color:#5060a0;font-size:12px;border-top:1px solid #2a2a8f;margin-top:24px;}}
</style>
</head>
<body>
<div class="container">

<div style="background:#09095a;border:1px solid #2a2a8f;border-radius:8px;padding:24px 28px;margin-bottom:20px;">
  <h1>⚡ VTG Cruise Intel — 2026-06-26</h1>
  <p class="subtitle">VacationsToGo.com · FastDeal authenticated scrape · 6 luxury lines · All prices USD per person double occupancy</p>
</div>

<div class="stats">
  <div class="stat"><span class="stat-num">{stats_total:,}</span><span class="stat-lbl">Total Deals</span></div>
  <div class="stat"><span class="stat-num">{stats_lines}</span><span class="stat-lbl">Cruise Lines</span></div>
  <div class="stat"><span class="stat-num">{avg_disc:.0f}%</span><span class="stat-lbl">Avg Discount</span></div>
  <div class="stat"><span class="stat-num">${min_price:,}</span><span class="stat-lbl">Lowest PPDO</span></div>
  <div class="stat"><span class="stat-num">{len([d for d in deals if d['pct']>=70])}</span><span class="stat-lbl">70%+ Off Deals</span></div>
  <div class="stat"><span class="stat-num">{len([d for d in deals if 'Suite' in d['status']])}</span><span class="stat-lbl">Suite Available</span></div>
</div>

<div style="background:#09095a;border:1px solid #2a2a8f;border-radius:8px;padding:20px;margin-bottom:24px;">
<h2 style="color:#a8c4ff;font-size:15px;margin:0 0 14px;">By Cruise Line — Top Deals Preview</h2>
<div class="cards">
{cards_html}
</div>
</div>

<div style="background:#09095a;border:1px solid #2a2a8f;border-radius:8px;padding:20px;">
<h2 style="color:#a8c4ff;font-size:15px;margin:0 0 12px;">All Deals <span style="color:#7090cc;font-size:12px;font-weight:normal;">({stats_total:,} total)</span></h2>

<div class="filter-bar">
  <label>Search ship/route: <input type="text" id="search" placeholder="Search…" oninput="filterTable()"></label>
  <label>Line: <select id="lineFilter" onchange="filterTable()">
    <option value="">All lines</option>
    {''.join(f'<option value="{ln}">{ln}</option>' for ln in LINE_ORDER)}
  </select></label>
  <label>Max price ($): <input type="number" id="maxPrice" placeholder="99999" oninput="filterTable()" style="width:90px;"></label>
  <label>Min discount (%): <input type="number" id="minDisc" placeholder="0" oninput="filterTable()" style="width:70px;"></label>
  <label><input type="checkbox" id="suiteOnly" onchange="filterTable()"> Suite available only</label>
  <span id="countDisplay" style="color:#7090cc;font-size:12px;margin-left:auto;"></span>
</div>

<div class="tbl-wrap">
<table id="dealTable">
<thead>
<tr>
  <th>Line</th><th>Ship</th><th>Date</th><th>Nights</th><th>Route</th>
  <th>Price (PPDO)</th><th>Discount</th><th>FastDeal#</th><th>Status</th>
</tr>
</thead>
<tbody id="tbody">
{rows_html}
</tbody>
</table>
</div>
</div>

<div class="footer">
  <p style="color:#a8c4ff;margin:0 0 4px;">⚡ V. Hale, VCS · Thunderbird Wing · Dreams2Memories Travel, LLC</p>
  <p style="margin:0;">Generated 2026-06-26 · Source: VacationsToGo.com authenticated scrape · Book by phone 800-338-4962</p>
  <p style="color:#3a3a6a;margin:4px 0 0;">Book-by deadlines apply per deal · Prices per person double occupancy · Subject to availability</p>
</div>

</div>

<script>
function filterTable() {{
  const search = document.getElementById('search').value.toLowerCase();
  const line   = document.getElementById('lineFilter').value;
  const maxP   = parseFloat(document.getElementById('maxPrice').value) || Infinity;
  const minD   = parseFloat(document.getElementById('minDisc').value) || 0;
  const suiteOnly = document.getElementById('suiteOnly').checked;
  const rows = document.querySelectorAll('#tbody tr');
  let vis = 0;
  rows.forEach(row => {{
    const cells = row.querySelectorAll('td');
    if (!cells.length) return;
    const lineName  = row.getAttribute('data-line') || '';
    const ship      = cells[1]?.textContent || '';
    const route     = cells[4]?.textContent || '';
    const priceText = cells[5]?.textContent.replace(/[$,]/g,'') || '99999';
    const discText  = cells[6]?.textContent.match(/(\d+)%/);
    const status    = cells[8]?.textContent || '';
    const price = parseFloat(priceText) || 0;
    const disc  = discText ? parseFloat(discText[1]) : 0;
    const matchSearch = !search || ship.toLowerCase().includes(search) || route.toLowerCase().includes(search) || lineName.toLowerCase().includes(search);
    const matchLine   = !line || lineName === line;
    const matchPrice  = price <= maxP;
    const matchDisc   = disc >= minD;
    const matchSuite  = !suiteOnly || status.includes('Suite');
    const show = matchSearch && matchLine && matchPrice && matchDisc && matchSuite;
    row.style.display = show ? '' : 'none';
    if (show) vis++;
  }});
  document.getElementById('countDisplay').textContent = `Showing ${{vis}} of {stats_total} deals`;
}}
filterTable();
</script>
</body>
</html>"""
    return html


def send_email(subject, html_path):
    creds = Credentials.from_authorized_user_file(TOKEN)
    service = build('gmail', 'v1', credentials=creds, cache_discovery=False)
    html_body = Path(html_path).read_text()
    msg = MIMEMultipart('alternative')
    msg['To']      = 'johnloucks3@gmail.com'
    msg['From']    = 'johnloucks3@gmail.com'
    msg['Subject'] = subject
    msg.attach(MIMEText(html_body, 'html'))
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    result = service.users().messages().send(userId='me', body={'raw': raw}).execute()
    return result['id']


if __name__ == '__main__':
    print("Parsing VTG data…")
    deals = parse_v2(DATA_FILE)
    print(f"  Parsed {len(deals)} deals")

    by_line = defaultdict(list)
    for d in deals:
        by_line[d['line']].append(d)
    for ln, lds in sorted(by_line.items(), key=lambda x: -len(x[1])):
        print(f"  {ln}: {len(lds)} deals")

    print("Building HTML…")
    html = build_html(deals)
    Path(OUT_FILE).write_text(html)
    print(f"  Saved → {OUT_FILE}")

    if '--no-email' not in sys.argv:
        print("Sending email…")
        msg_id = send_email(
            "⚡ VTG Cruise Intel — 2,272 FastDeals · Regent · Silversea · 4 More Lines [2026-06-26]",
            OUT_FILE
        )
        print(f"  SENT: {msg_id}")
    else:
        print("  --no-email: skipping send")

    print("Done.")
