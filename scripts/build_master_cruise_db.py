#!/usr/bin/env python3
"""
MASTER CRUISE DATABASE BUILDER
Merges T2 exercise sources + VTG FastDeals into a single public-facing HTML.
Output: /srv/www/htdocs/cruises/index.html
Also saves: output/MASTER_CRUISE_DB_<date>.json  (canonical export)

Sources:
  T2 CSV  — 765 sailings, Oct-Nov 2026, 10 source flags (deluxecruises/perx/oat/etc.)
  VTG     — 2272 FastDeals, multi-year, priced (Regent/Silversea/Atlas/Explora/PGC/Ponant)
"""
import json, csv, re, sys, sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# CI TRINITY Leg 1: Cruise link resolver for external itinerary URLs
# Script-mode execution puts scripts/ (not repo root) on sys.path — anchor the repo
# root so the `scripts.` package import resolves. Fixes cruise-db-refresh.service
# status=1 failure loop (2026-07-01).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.link_resolver import resolve_sailing

DB_PATH = Path("/home/john/Thunderbird/output/cruises.db")

OUT_DIR   = Path("/home/john/Thunderbird/cruises_web")
OUT_JSON  = Path("/home/john/Thunderbird/output/MASTER_CRUISE_DB_20260626.json")
T2_CSV    = Path("/home/john/Thunderbird/output/T2_MASTER_CRUISE_OCTOBER_NOVEMBER_2026.csv")
VTG_FILE  = Path("/home/john/Thunderbird/intel/vtg_structured_20260626.txt")
GENERATED = "2026-06-26"

# ── Canonical line names — normalize variant scraped names to one standard form
LINE_CANONICAL = {
    'Atlas':                    'Atlas Ocean Voyages',
    'Crystal':                  'Crystal Cruises',
    'Ponant':                   'PONANT',
    'Paul Gauguin':             'Paul Gauguin Cruises',
    'Regent':                   'Regent Seven Seas Cruises',
    'Silversea':                'Silversea Cruises',
    'Ritz-Carlton Yacht Club':  'Ritz-Carlton Yacht Collection',
}

# ── Region inference from port/route keywords ───────────────────────────────
REGION_MAP = [
    ("Mediterranean",  ["mediterranean","athens","piraeus","rome","civitavecchia","barcelona",
                         "lisbon","valletta","venice","istanbul","dubrovnik","marseille",
                         "palma","naples","sicily","malaga","santorini","mykonos","split",
                         "kotor","lima","florence","livorno","genoa","monaco","nice",
                         "portofino","ajaccio","palermo","catania","trapani","heraklion",
                         "rhodes","corfu","katakolon","patmos","kusadasi","ephesus",
                         "cannes","toulon","barcelona","tarragona","bilbao","porto",
                         "alicante","cartagena","valencia","ibiza","bari","brindisi",
                         "ravenna","chioggia","fusina","trieste","koper","zadar"]),
    ("Alaska",         ["alaska","anchorage","whittier","juneau","skagway","ketchikan",
                         "sitka","glacier bay","hubbard","vancouver bc","seattle"]),
    ("Caribbean",      ["caribbean","miami","fort lauderdale","san juan","barbados",
                         "bridgetown","st lucia","martinique","guadeloupe","st kitts",
                         "antigua","st maarten","aruba","curacao","cartagena colombia",
                         "puerto rico","nassau","bahamas","tortola","st thomas","key west",
                         "colon","panama","costa rica","belize","cozumel","cancun"]),
    ("Baltic / Northern Europe", ["baltic","stockholm","copenhagen","helsinki","tallinn",
                         "riga","vilnius","st. petersburg","gdansk","oslo","bergen",
                         "stavanger","amsterdam","hamburg","kiel","rostock","warnemunde",
                         "gothenburg","malmo","aarhus"]),
    ("Norway / Arctic", ["norway","fjords","northern lights","tromso","narvik","bodo",
                          "lofoten","svalbard","longyearbyen","kirkenes","honningsvag",
                          "bergen","flam","geiranger","stavanger","arctic","hurtigruten"]),
    ("British Isles",  ["southampton","london","dover","tilbury","edinburgh","glasgow",
                         "dublin","cork","belfast","liverpool","greenock","invergordon",
                         "lerwick","portsmouth","isle of man"]),
    ("Transatlantic",  ["transatlantic","new york","fort lauderdale to southampton",
                         "southampton to new york","quebec","montreal","lisbon to new york",
                         "new york to lisbon","crossing"]),
    ("South America",  ["buenos aires","rio de janeiro","montevideo","santiago","lima",
                         "valparaiso","ushuaia","patagonia","falkland","amazon","manaus",
                         "fortaleza","recife","salvador","santos"]),
    ("Asia & Pacific", ["tokyo","osaka","kobe","yokohama","singapore","hong kong","shanghai",
                         "beijing","tianjin","seoul","busan","taipei","keelung","vietnam",
                         "hanoi","ho chi minh","danang","thailand","bangkok","laem chabang",
                         "phuket","bali","benoa","jakarta","manila","philippines","sydney",
                         "melbourne","auckland","new zealand","hawaii","honolulu","tahiti",
                         "papeete","french polynesia"]),
    ("Indian Ocean / Africa", ["cape town","durban","mombasa","zanzibar","port louis",
                         "mauritius","seychelles","dubai","abu dhabi","muscat","oman",
                         "india","mumbai","cochin","colombo","sri lanka","maldives",
                         "madagascar","reunion","djibouti"]),
    ("Canary Islands / Atlantic Islands", ["canary islands","tenerife","gran canaria",
                         "lanzarote","fuerteventura","las palmas","santa cruz de tenerife",
                         "madeira","funchal","azores","cape verde","mindelo","dakar"]),
]

def infer_region(route, from_port="", to_port=""):
    text = (route + " " + from_port + " " + to_port).lower()
    for region, keywords in REGION_MAP:
        if any(kw in text for kw in keywords):
            return region
    return "Other / World"


# ── VTG Parser ───────────────────────────────────────────────────────────────
def parse_vtg(path):
    line_names = ["Regent", "Silversea", "Explora Journeys", "Atlas Ocean Voyages",
                  "Atlas", "Paul Gauguin", "Ponant"]
    ln_pat = '|'.join(re.escape(l) for l in line_names)
    row_re = re.compile(
        r'^#(\d+)\s+(\d+)\s+(.+?)\s+(' + ln_pat + r')\s*/\s*(.+?)\s+'
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
            dm = re.match(r'^(\w{3}\s+\d+(?:,\s*\d{4})?)\s*(.*)', before.strip())
            date_str = dm.group(1) if dm else ''
            route    = dm.group(2).strip() if dm else before.strip()
            # Parse date to ISO
            yr_m = re.search(r'(\d{4})', date_str)
            year = int(yr_m.group(1)) if yr_m else 2026
            # Try to build ISO date
            try:
                clean = re.sub(r',\s*\d{4}', '', date_str).strip()
                if year != 2026:
                    d = datetime.strptime(f"{clean} {year}", "%b %d %Y")
                else:
                    d = datetime.strptime(f"{clean} 2026", "%b %d %Y")
                iso_date = d.strftime("%Y-%m-%d")
            except:
                iso_date = ''
            canonical = LINE_CANONICAL.get(ln, ln)
            deals.append({
                'line':      canonical,
                'ship':      ship.strip(),
                'departure': iso_date,
                'date_str':  date_str,
                'nights':    int(nights),
                'from_port': route[:40],
                'to_port':   '',
                'route':     route,
                'region':    infer_region(route),
                'price_disc': int(disc.replace(',','')),
                'price_orig': int(orig.replace(',','')),
                'discount':  int(pct),
                'suite':     'Suite' in status,
                'vtg_fd':    fdeal,
                'sources':   ['vtg'],
                'scraped':   GENERATED,
            })
    return deals


# ── T2 CSV Parser ────────────────────────────────────────────────────────────
SOURCE_COLS = ['on_deluxecruises','on_perx','on_oat','on_ponant','on_hx',
               'on_seadream','on_explora','on_cruisemapper','on_cruisesonly','on_cruiseplum']
SOURCE_KEYS = ['deluxe','perx','oat','ponant','hx','seadream','explora','cruisemapper','cruisesonly','cruiseplum']

def parse_t2(path):
    records = []
    with open(path) as f:
        for row in csv.DictReader(f):
            srcs = [SOURCE_KEYS[i] for i, col in enumerate(SOURCE_COLS)
                    if row.get(col,'').strip().upper() in ('TRUE','1','YES','X','TRUE')]
            if not srcs:
                srcs = ['t2']
            price = None
            try:
                price = float(row.get('price_usd','').replace('$','').replace(',',''))
            except:
                pass
            route   = row.get('route','')
            from_p  = row.get('port','') or ''
            records.append({
                'line':      row.get('cruise_line',''),
                'ship':      row.get('ship_name',''),
                'departure': row.get('departure_date',''),
                'date_str':  row.get('departure_date',''),
                'nights':    int(row.get('days','0') or 0),
                'from_port': from_p,
                'to_port':   '',
                'route':     route,
                'region':    infer_region(route, from_p),
                'price_disc': price,
                'price_orig': None,
                'discount':  None,
                'suite':     False,
                'vtg_fd':    None,
                'sources':   srcs,
                'scraped':   GENERATED,
            })
    return records


# ── Merge ────────────────────────────────────────────────────────────────────
_VESSEL_PREFIXES = ('ms', 'mv', 'ss', 'mt', 'ry', 'sy')

def make_key(r):
    ship = re.sub(r'\W+', '', (r['ship'] or '').lower())
    for pfx in _VESSEL_PREFIXES:
        if ship.startswith(pfx) and len(ship) > len(pfx) + 2:
            ship = ship[len(pfx):]
            break
    dep = (r['departure'] or '')[:10]
    return (ship, dep, str(r['nights']))

def merge_all(source_lists):
    """Merge N source lists by (ship, departure, nights) key; union sources; keep best price."""
    by_key = defaultdict(list)
    for records in source_lists:
        for r in records:
            by_key[make_key(r)].append(r)

    merged = []
    for group in by_key.values():
        base = max(group, key=lambda r: (
            bool(r.get('price_disc')),
            len(r.get('route') or ''),
            len(r.get('ship') or ''),
        ))
        result = dict(base)
        all_srcs = set()
        for r in group:
            all_srcs.update(r.get('sources') or [])
        result['sources'] = sorted(all_srcs)
        priced = [r for r in group if r.get('price_disc')]
        if priced:
            best = min(priced, key=lambda r: r['price_disc'])
            result['price_disc'] = best['price_disc']
            result['price_orig'] = best.get('price_orig')
            result['discount']   = best.get('discount')
            result['suite']      = result.get('suite') or best.get('suite', False)
            if not result.get('vtg_fd'):
                result['vtg_fd'] = best.get('vtg_fd')
        merged.append(result)

    return merged


def _norm_record(r, source_key):
    """Normalize any scraped record to the standard DB schema."""
    nights = 0
    for k in ('nights', 'days'):
        try:
            nights = int(r.get(k) or 0)
            break
        except (ValueError, TypeError):
            pass
    dep = r.get('departure') or r.get('departure_date') or r.get('date') or r.get('date_str') or ''
    route = r.get('route') or ''
    from_port = r.get('from_port') or r.get('port') or ''
    raw_line = r.get('line') or r.get('cruise_line') or ''
    return {
        'line':       LINE_CANONICAL.get(raw_line, raw_line),
        'ship':       r.get('ship') or r.get('ship_name') or '',
        'departure':  dep,
        'date_str':   dep,
        'nights':     nights,
        'from_port':  from_port,
        'to_port':    r.get('to_port') or '',
        'route':      route,
        'region':     r.get('region') or infer_region(route, from_port),
        'price_disc': r.get('price_disc') or r.get('price') or None,
        'price_orig': r.get('price_orig') or None,
        'discount':   r.get('discount') or None,
        'suite':      bool(r.get('suite')),
        'vtg_fd':     r.get('vtg_fd') or None,
        'sources':    r.get('sources') or [source_key],
        'scraped':    GENERATED,
        'booking_url': '',
        'booking_label': '',
    }

def parse_source_json(path, source_key):
    """Load a JSON file of scraped records, normalize each to DB schema."""
    raw = json.loads(path.read_text())
    return [_norm_record(r, source_key) for r in raw if r.get('ship') or r.get('ship_name')]


# ── HTML Builder ─────────────────────────────────────────────────────────────
SOURCE_BADGE = {
    'deluxe':      ('D', '#0033A0', '#fff', 'deluxecruises.com'),
    'perx':        ('X', '#28a745', '#fff', 'ProjectExpedition'),
    'oat':         ('O', '#fd7e14', '#fff', 'OAT'),
    'ponant':      ('N', '#6f42c1', '#fff', 'PONANT'),
    'hx':          ('H', '#17a2b8', '#fff', 'HX Expeditions'),
    'seadream':    ('S', '#20c997', '#000', 'SeaDream'),
    'explora':     ('E', '#e83e8c', '#fff', 'Explora Journeys'),
    'cruisemapper':('M', '#795548', '#fff', 'CruiseMapper'),
    'cruisesonly': ('C', '#ff5722', '#fff', 'CruisesOnly'),
    'cruiseplum':  ('L', '#9c27b0', '#fff', 'CruisePlum'),
    'vtg':         ('V', '#c0392b', '#fff', 'VacationsToGo'),
    'oceania_vtg':   ('OC', '#00609c', '#fff', 'Oceania via VTG'),
    'crystal_vtg':   ('CR', '#7b2d8b', '#fff', 'Crystal Cruises via VTG'),
    'regent_vtg':    ('RG', '#1a3a5c', '#fff', 'Regent via VTG'),
    'silversea_vtg': ('SS', '#8b6914', '#fff', 'Silversea via VTG'),
    'atlas_vtg':     ('AT', '#2e7d32', '#fff', 'Atlas Ocean via VTG'),
    'regent_perx':   ('RP', '#1a3a5c', '#e0c068', 'Regent via Perx'),
    'silversea_perx':('SP', '#8b6914', '#e0c068', 'Silversea via Perx'),
    'atlas_perx':    ('AP', '#2e7d32', '#e0c068', 'Atlas Ocean via Perx'),
    't2':            ('T',  '#1a1a1a', '#fff', 'T2 Exercise'),
}

def badge_html(sources):
    out = ''
    for s in sorted(set(sources)):
        info = SOURCE_BADGE.get(s, ('?', '#888', '#fff', s))
        letter, bg, fg, title = info
        out += (f'<span class="badge" style="background:{bg};color:{fg};" '
                f'title="{title}">{letter}</span>')
    return out or ''


def build_html(records):
    total = len(records)
    by_line  = defaultdict(list)
    by_region= defaultdict(list)
    all_lines = []
    for r in records:
        by_line[r['line']].append(r)
        by_region[r['region']].append(r)
    all_lines = sorted(by_line.keys(), key=lambda l: -len(by_line[l]))
    all_regions = sorted(by_region.keys(), key=lambda r: -len(by_region[r]))

    multi_count = sum(1 for r in records if len(r['sources']) > 1)
    priced_count= sum(1 for r in records if r.get('price_disc'))
    suite_count = sum(1 for r in records if r.get('suite'))

    # Source legend badges HTML
    legend_badges = ''.join(
        f'<span class="legend-item">'
        f'<span class="badge" style="background:{bg};color:{fg};">{lt}</span> {title}'
        f'</span>'
        for key, (lt, bg, fg, title) in SOURCE_BADGE.items()
    )

    # ── Cards: top lines ────────────────────────────────────────────
    cards_html = ""
    max_ct = max(len(v) for v in by_line.values()) if by_line else 1
    for ln in all_lines[:12]:
        lds   = by_line[ln]
        ships = sorted(set(r['ship'] for r in lds if r['ship']))
        ships_str = ', '.join(ships[:3]) + (f' +{len(ships)-3}' if len(ships)>3 else '')
        bar   = int(len(lds)/max_ct*100)
        priced= [r for r in lds if r.get('price_disc')]
        min_p = min(r['price_disc'] for r in priced) if priced else None
        price_str = f'From <strong>${min_p:,}</strong> PPDO' if min_p else 'Pricing varies'
        leader = '<span class="vol-leader">&#9733; Most sailings</span>' if len(lds)==max_ct else ''

        # top voyages sorted by date first, price second; blank dates sink to bottom
        sorted_lds = sorted(lds, key=lambda x: (x.get('departure','') or '9999-99-99', x.get('price_disc') or 99999))
        idx_map = {id(r): records.index(r) for r in lds}
        voyage_links = ''.join(
            f'<a href="#v-{idx_map[id(d)]}" class="period-link">'
            f'{d["ship"] or ln} · {d["date_str"] or d["departure"]} · {d["nights"]}nt'
            + (f' · <strong>${d["price_disc"]:,}</strong>' if d.get("price_disc") else '')
            + f'</a>'
            for d in sorted_lds[:12]
        )
        if len(sorted_lds) > 12:
            voyage_links += ''.join(
                f'<a href="#v-{idx_map[id(d)]}" class="period-link">'
                f'{d["ship"] or ln} · {d["date_str"] or d["departure"]} · {d["nights"]}nt'
                + (f' · <strong>${d["price_disc"]:,}</strong>' if d.get("price_disc") else '')
                + f'</a>'
                for d in sorted_lds[12:]
            )

        cards_html += f"""
    <div class="card">
      <div class="card-line">{ln}</div>
      <div class="card-ships">{ships_str}</div>
      <div class="card-vol-label"><span>{len(lds)} sailings</span>{leader}</div>
      <div class="card-vol-bar"><div class="card-vol-fill" style="width:{bar}%"></div></div>
      <div class="card-price">{price_str}</div>
      <div class="card-voyages">{voyage_links}</div>
    </div>"""

    # ── Table rows ──────────────────────────────────────────────────
    rows_html = ""
    line_set  = sorted(set(r['line'] for r in records))
    region_set= sorted(set(r['region'] for r in records))

    for i, r in enumerate(records):
        multi = len(r['sources']) > 1
        multi_cls = ' multi' if multi else ''
        bg_multi  = ' style="background:#fffbe6;"' if multi else ''
        price_td = f'${r["price_disc"]:,}' if r.get('price_disc') else '—'
        disc_td  = f'{r["discount"]}% off' if r.get('discount') else '—'
        rows_html += (
            f'<tr id="v-{i}" class="row{multi_cls}" '
            f'data-line="{r["line"]}" data-region="{r["region"]}" '
            f'data-nights="{r["nights"]}" data-price="{r.get("price_disc") or 0}"'
            f'{bg_multi}>\n'
            f'  <td>{r["line"]}</td>\n'
            f'  <td>{r["ship"]}</td>\n'
            f'  <td class="date">{r["date_str"] or r["departure"]}</td>\n'
            f'  <td class="num">{r["nights"]}nt</td>\n'
            f'  <td class="route" title="{r["route"]}">{r["route"][:65]}</td>\n'
            f'  <td class="num" style="color:#555;font-size:0.8rem;">{r["region"]}</td>\n'
            f'  <td class="price">{price_td}</td>\n'
            f'  <td class="num" style="color:#856404;">{disc_td}</td>\n'
            f'  <td class="cov">{badge_html(r["sources"])}</td>\n'
            f'  <td class="link">{"<a href=\""+r["booking_url"]+"\" target=_blank title=\""+r["booking_label"]+"\">&#8599;</a>" if r.get("booking_url") else "—"}</td>\n'
            f'</tr>\n'
        )

    # filter options
    line_opts   = ''.join(f'<option value="{l}">{l}</option>' for l in line_set)
    region_opts = ''.join(f'<option value="{rg}">{rg}</option>' for rg in region_set)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Luxury Cruise Search — Dreams2Memories Travel</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: Georgia, serif; background: #f7f3ea; color: #1a1a1a; }}

  .header {{ background: #0033A0; color: #fff; padding: 28px 40px 20px; }}
  .header h1 {{ font-size: 1.6rem; font-weight: normal; letter-spacing: 0.5px; }}
  .header p  {{ font-size: 0.82rem; opacity: 0.8; margin-top: 5px; line-height: 1.5; }}
  .stats-bar {{ display: flex; gap: 24px; padding: 18px 40px; background: #1a1a1a;
               color: #f7f3ea; flex-wrap: wrap; }}
  .stat {{ text-align: center; min-width: 80px; }}
  .stat-num {{ font-size: 2rem; font-weight: bold; color: #f0c040; line-height: 1; }}
  .stat-lbl {{ font-size: 0.7rem; text-transform: uppercase; letter-spacing: 1px;
               opacity: 0.7; margin-top: 2px; }}

  .section {{ padding: 24px 40px; }}
  .section h2 {{ font-size: 1rem; text-transform: uppercase; letter-spacing: 1.5px;
                 color: #0033A0; border-bottom: 2px solid #0033A0;
                 padding-bottom: 6px; margin-bottom: 16px; }}

  /* Cards */
  .cards {{ display: flex; flex-wrap: wrap; gap: 12px; }}
  .card {{ background: #fff; border: 1px solid #ddd; border-radius: 8px;
           padding: 12px 14px; min-width: 220px; flex: 1 1 220px; max-width: 300px;
           transition: box-shadow 0.15s, border-color 0.15s; }}
  .card:hover {{ box-shadow: 0 4px 14px rgba(0,51,160,0.14); border-color: #0033A0; }}
  .card-line  {{ font-weight: bold; font-size: 0.88rem; color: #0033A0;
                 border-bottom: 1px solid #eee; padding-bottom: 5px; margin-bottom: 6px; }}
  .card-ships {{ font-size: 0.73rem; color: #666; font-style: italic; margin-bottom: 6px; }}
  .card-price {{ font-size: 0.75rem; color: #1a7a1a; margin-bottom: 8px; }}
  .card-voyages {{ display: flex; flex-direction: column; gap: 3px; }}
  .card-voyages a {{ font-size: 0.72rem; color: #222; text-decoration: none;
                     padding: 2px 5px; border-radius: 3px; display: block;
                     line-height: 1.4; border-left: 3px solid #0033A0;
                     transition: background 0.1s; }}
  .card-voyages a:hover {{ background: #f0f4ff; color: #0033A0; }}
  .more-voyages {{ font-size: 0.68rem; color: #888; padding: 2px 5px; font-style: italic; }}
  .card-vol-label {{ font-size: 0.67rem; color: #888; margin-bottom: 3px;
                     display: flex; justify-content: space-between; align-items: center; }}
  .card-vol-bar   {{ background: #e8e8e8; border-radius: 3px; height: 4px;
                     margin-bottom: 7px; overflow: hidden; }}
  .card-vol-fill  {{ background: linear-gradient(to right, #0033A0, #6492e0);
                     height: 4px; border-radius: 3px; }}
  .vol-leader     {{ background: #f0c040; color: #664d00; font-size: 0.61rem;
                     font-weight: bold; padding: 1px 7px; border-radius: 10px; }}

  /* Filter bar */
  .filter-box {{ background: #fff; border: 1px solid #ddd; border-radius: 8px;
                 padding: 16px 20px; margin-bottom: 14px; }}
  .filter-row {{ display: flex; gap: 10px; align-items: flex-end; flex-wrap: wrap; margin-bottom: 10px; }}
  .filter-row:last-child {{ margin-bottom: 0; }}
  .filter-group {{ display: flex; flex-direction: column; gap: 4px; }}
  .filter-group label {{ font-size: 0.75rem; color: #555; font-weight: bold;
                          text-transform: uppercase; letter-spacing: 0.5px; }}
  .filter-group input, .filter-group select {{
    padding: 8px 12px; border: 1px solid #ccc; border-radius: 4px;
    font-size: 0.9rem; background: #fff; font-family: Georgia, serif; }}
  .filter-group input[type=text] {{ width: 320px; }}
  .filter-group input[type=number] {{ width: 110px; }}
  .filter-group select {{ min-width: 160px; }}
  .filter-actions {{ display: flex; gap: 8px; align-items: flex-end; margin-left: auto; }}
  .btn {{ padding: 9px 18px; border: none; border-radius: 4px; cursor: pointer;
           font-size: 0.85rem; font-family: Georgia, serif; }}
  .btn-primary {{ background: #0033A0; color: #fff; }}
  .btn-primary:hover {{ background: #002280; }}
  .btn-ghost {{ background: #eee; color: #333; }}
  .btn-ghost:hover {{ background: #ddd; }}
  .filter-chips {{ display: flex; gap: 6px; flex-wrap: wrap; }}
  .chip {{ padding: 4px 12px; border-radius: 20px; font-size: 0.78rem; cursor: pointer;
           border: 1px solid #c0cfe8; background: #f0f4ff; color: #0033A0;
           transition: all 0.15s; user-select: none; }}
  .chip:hover {{ background: #d8e8ff; }}
  .chip.active {{ background: #0033A0; color: #fff; border-color: #0033A0; }}

  /* Table */
  .count-bar {{ font-size: 0.8rem; color: #555; margin-bottom: 8px; }}
  #count-display {{ font-weight: bold; color: #0033A0; }}
  .tbl-scroll {{ overflow-x: auto; }}
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
  .route {{ color: #444; max-width: 260px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
  .cov   {{ white-space: nowrap; }}
  .link  {{ text-align: center; white-space: nowrap; }}
  .link a {{ color: #0033A0; text-decoration: none; font-size: 1.1rem; padding: 2px 6px; border-radius: 3px; }}
  .link a:hover {{ background: #0033A0; color: #fff; }}

  /* Source badges */
  .badge {{ display: inline-block; min-width: 18px; height: 18px; border-radius: 3px;
            font-size: 0.62rem; font-weight: bold; text-align: center;
            line-height: 18px; margin-right: 2px; padding: 0 2px; cursor: default; }}
  .multi td {{ background: #fffbe6 !important; }}

  /* Legend */
  .legend {{ display: flex; gap: 8px; flex-wrap: wrap; font-size: 0.73rem; color: #555;
             padding: 10px 0; }}
  .legend-item {{ display: flex; align-items: center; gap: 4px; }}

  /* Footer */
  .footer {{ padding: 20px 40px; background: #1a1a1a; color: #888;
              font-size: 0.75rem; text-align: center; }}
  .footer a {{ color: #aaa; }}
</style>
</head>
<body>

<div class="header">
  <h1>Luxury Cruise Search</h1>
  <p>Dreams2Memories Travel, LLC &nbsp;·&nbsp; Multi-source cruise intelligence database</p>
  <p style="margin-top:6px;font-size:0.77rem;opacity:0.65;">
    Sources: deluxecruises.com · VacationsToGo · CruiseMapper · Explora Journeys · OAT · SeaDream · HX · CruisesOnly · Ponant · ProjectExpedition
  </p>
</div>

<div class="stats-bar">
  <div class="stat"><div class="stat-num">{total:,}</div><div class="stat-lbl">Sailings</div></div>
  <div class="stat"><div class="stat-num">{len(all_lines)}</div><div class="stat-lbl">Cruise Lines</div></div>
  <div class="stat"><div class="stat-num">{len(all_regions)}</div><div class="stat-lbl">Destinations</div></div>
  <div class="stat"><div class="stat-num">{multi_count}</div><div class="stat-lbl">Multi-Source</div></div>
  <div class="stat"><div class="stat-num">{priced_count}</div><div class="stat-lbl">With Pricing</div></div>
  <div class="stat"><div class="stat-num">{suite_count}</div><div class="stat-lbl">Suite Avail.</div></div>
  <div class="stat"><div class="stat-num" style="font-size:1rem;padding-top:6px;">{GENERATED}</div><div class="stat-lbl">Last Updated</div></div>
</div>

<div class="section">
  <h2>By Cruise Line — Click a Sailing to Jump to Table</h2>
  <div class="cards">
{cards_html}
  </div>
</div>

<div class="section">
  <h2>Search All Sailings
    <span style="font-weight:normal;font-size:0.8rem;color:#888;text-transform:none;letter-spacing:0;">
      &nbsp;·&nbsp; <span id="count-display">{total}</span> showing of {total:,} total
    </span>
  </h2>

  <div class="filter-box">
    <div class="filter-row">
      <div class="filter-group" style="flex:1;min-width:260px;">
        <label>Search — ship, route, port, destination</label>
        <input type="text" id="search"
               placeholder="e.g. Alaska · Regent · Mediterranean · 7 night · Barcelona…"
               oninput="filterTable()">
      </div>
      <div class="filter-group">
        <label>Destination</label>
        <select id="regionFilter" onchange="filterTable()">
          <option value="">All destinations</option>
          {region_opts}
        </select>
      </div>
      <div class="filter-group">
        <label>Cruise Line</label>
        <select id="lineFilter" onchange="filterTable()">
          <option value="">All lines</option>
          {line_opts}
        </select>
      </div>
    </div>
    <div class="filter-row">
      <div class="filter-group">
        <label>Duration</label>
        <select id="durationFilter" onchange="filterTable()">
          <option value="">Any length</option>
          <option value="1-6">Short (1–6 nights)</option>
          <option value="7-9">Week (7–9 nights)</option>
          <option value="10-14">Extended (10–14 nights)</option>
          <option value="15-999">Grand (15+ nights)</option>
        </select>
      </div>
      <div class="filter-group">
        <label>Max Price / person ($)</label>
        <input type="number" id="maxPrice" placeholder="e.g. 5000" oninput="filterTable()">
      </div>
      <div class="filter-group">
        <label>Min Discount (%)</label>
        <input type="number" id="minDisc" placeholder="e.g. 50" oninput="filterTable()">
      </div>
      <div class="filter-group" style="justify-content:flex-end;padding-bottom:2px;">
        <label>&nbsp;</label>
        <div style="display:flex;gap:8px;align-items:center;">
          <label style="font-size:0.82rem;text-transform:none;letter-spacing:0;display:flex;align-items:center;gap:5px;cursor:pointer;">
            <input type="checkbox" id="multiOnly" onchange="filterTable()"> Multi-source confirmed
          </label>
          <label style="font-size:0.82rem;text-transform:none;letter-spacing:0;display:flex;align-items:center;gap:5px;cursor:pointer;">
            <input type="checkbox" id="pricedOnly" onchange="filterTable()"> Has pricing
          </label>
          <label style="font-size:0.82rem;text-transform:none;letter-spacing:0;display:flex;align-items:center;gap:5px;cursor:pointer;">
            <input type="checkbox" id="suiteOnly" onchange="filterTable()"> Suite available
          </label>
          <button class="btn btn-ghost" onclick="resetFilters()">Reset all</button>
        </div>
      </div>
    </div>
    <div class="filter-row" style="margin-bottom:0;">
      <div style="font-size:0.75rem;color:#888;">Quick filter by line:</div>
      <div class="filter-chips" id="lineChips">
        {''.join(f'<span class="chip" onclick="chipClick(this,\'{ln}\')" data-line="{ln}">{ln} ({len(by_line[ln])})</span>' for ln in all_lines[:10])}
        <span class="chip" onclick="chipClick(this,\'\')" data-line="">All lines</span>
      </div>
    </div>
  </div>

  <div class="legend">
    <strong style="font-size:0.75rem;color:#333;">Sources:</strong>
    {legend_badges}
    <span style="margin-left:8px;font-style:italic;color:#aaa;">Highlighted rows = confirmed by 2+ sources</span>
  </div>

  <div class="count-bar">
    Showing <span id="count-display2">{total}</span> of {total:,} sailings
  </div>

  <div class="tbl-scroll">
  <table id="dealTable">
    <thead>
      <tr>
        <th onclick="sortTable(0)">Line ↕</th>
        <th onclick="sortTable(1)">Ship ↕</th>
        <th onclick="sortTable(2)">Date ↕</th>
        <th onclick="sortTable(3)">Nights ↕</th>
        <th onclick="sortTable(4)">Route / Ports</th>
        <th onclick="sortTable(5)">Destination ↕</th>
        <th onclick="sortTable(6)">Price PPDO ↕</th>
        <th onclick="sortTable(7)">Discount ↕</th>
        <th>Sources</th>
        <th>Link</th>
      </tr>
    </thead>
    <tbody id="tableBody">
{rows_html}
    </tbody>
  </table>
  </div>
</div>

<div class="footer">
  <p>Dreams2Memories Travel, LLC &nbsp;·&nbsp; Luxury cruise intelligence updated monthly</p>
  <p style="margin-top:6px;">
    All prices USD per person double occupancy · Subject to availability · Prices from VacationsToGo FastDeal program ·
    Book by phone 800-338-4962 (VTG) or <a href="mailto:concierge@d2mluxury.quest">contact D2M</a>
  </p>
  <p style="margin-top:4px;color:#666;">Generated {GENERATED} · {total:,} sailings across {len(all_lines)} cruise lines</p>
</div>

<script>
let sortDir = {{}};
let activeChipLine = '';

function filterTable() {{
  const q        = document.getElementById('search').value.toLowerCase();
  const words    = q.split(/[\\s]+/).filter(Boolean);
  const region   = document.getElementById('regionFilter').value.toLowerCase();
  const line     = document.getElementById('lineFilter').value.toLowerCase();
  const dur      = document.getElementById('durationFilter').value;
  const maxP     = parseFloat(document.getElementById('maxPrice').value) || Infinity;
  const minD     = parseFloat(document.getElementById('minDisc').value) || 0;
  const multiOnly= document.getElementById('multiOnly').checked;
  const pricedOnly= document.getElementById('pricedOnly').checked;
  const suiteOnly= document.getElementById('suiteOnly').checked;
  const chipLine = activeChipLine.toLowerCase();

  const rows = document.querySelectorAll('#tableBody tr');
  let visible = 0;
  rows.forEach(row => {{
    const rowText  = row.textContent.toLowerCase();
    const rowLine  = (row.dataset.line || '').toLowerCase();
    const rowReg   = (row.dataset.region || '').toLowerCase();
    const rowNight = parseInt(row.dataset.nights || '0');
    const rowPrice = parseFloat(row.dataset.price || '0');

    const isSearch = !words.length || words.every(w => rowText.includes(w));
    const isRegion = !region || rowReg === region;
    const isLine   = (!line || rowLine === line) && (!chipLine || rowLine === chipLine);

    let isDur = true;
    if (dur) {{
      const [lo, hi] = dur.split('-').map(Number);
      isDur = rowNight >= lo && rowNight <= hi;
    }}

    const isPrice  = !pricedOnly ? (rowPrice <= maxP) : (rowPrice > 0 && rowPrice <= maxP);
    const isDisc   = (() => {{
      if (!minD) return true;
      const discTd = row.cells[7]?.textContent.replace(/[^0-9]/g,'');
      return parseFloat(discTd || '0') >= minD;
    }})();
    const isMulti  = !multiOnly || row.classList.contains('multi');
    const isSuite  = !suiteOnly || rowText.includes('suite');

    const show = isSearch && isRegion && isLine && isDur && isPrice && isDisc && isMulti && isSuite;
    row.classList.toggle('hidden', !show);
    if (show) visible++;
  }});
  document.getElementById('count-display').textContent  = visible;
  document.getElementById('count-display2').textContent = visible;
}}

function chipClick(el, line) {{
  document.querySelectorAll('#lineChips .chip').forEach(c => c.classList.remove('active'));
  el.classList.add('active');
  activeChipLine = line;
  // also sync select
  const sel = document.getElementById('lineFilter');
  for (let i=0; i<sel.options.length; i++) {{
    if (sel.options[i].value.toLowerCase() === line.toLowerCase()) {{
      sel.selectedIndex = i; break;
    }}
  }}
  if (!line) sel.selectedIndex = 0;
  filterTable();
}}

function resetFilters() {{
  document.getElementById('search').value         = '';
  document.getElementById('regionFilter').selectedIndex = 0;
  document.getElementById('lineFilter').selectedIndex   = 0;
  document.getElementById('durationFilter').selectedIndex = 0;
  document.getElementById('maxPrice').value       = '';
  document.getElementById('minDisc').value        = '';
  document.getElementById('multiOnly').checked    = false;
  document.getElementById('pricedOnly').checked   = false;
  document.getElementById('suiteOnly').checked    = false;
  activeChipLine = '';
  document.querySelectorAll('#lineChips .chip').forEach(c => c.classList.remove('active'));
  filterTable();
}}

function sortTable(col) {{
  const tbody = document.getElementById('tableBody');
  const rows  = Array.from(tbody.querySelectorAll('tr'));
  sortDir[col] = !sortDir[col];
  rows.sort((a, b) => {{
    const av = a.cells[col]?.textContent.trim() || '';
    const bv = b.cells[col]?.textContent.trim() || '';
    const an = parseFloat(av.replace(/[$,%nt —]/g,''));
    const bn = parseFloat(bv.replace(/[$,%nt —]/g,''));
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


def _latest_intel(stem: str, suffix: str = "vtg") -> Path | None:
    """Return the most recent intel/<stem>_<suffix>_YYYYMMDD.json, or None."""
    candidates = sorted(INTEL_DIR.glob(f"{stem}_{suffix}_*.json"), reverse=True)
    return candidates[0] if candidates else None

INTEL_DIR         = Path("/home/john/Thunderbird/intel")
OCEANIA_FILE      = Path("/home/john/Thunderbird/intel/oceania_vtg_20260626.json")
CRYSTAL_FILE      = Path("/home/john/Thunderbird/intel/crystal_vtg_20260626.json")
CRUISEMAPPER_FILE = Path("/home/john/Thunderbird/intel/cruisemapper_live.json")
DELUXE_FILE       = Path("/home/john/Thunderbird/intel/deluxecruises_live.json")
PERX_FILE         = Path("/home/john/Thunderbird/intel/perx_live.json")


def build_sqlite(records):
    """Write SQLite DB with FTS5 for the search API. Overwrites existing."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE cruises (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            line      TEXT,
            ship      TEXT,
            departure TEXT,
            nights    INTEGER,
            from_port TEXT,
            route     TEXT,
            region    TEXT,
            sources   TEXT,
            multi     INTEGER DEFAULT 0,
            price_ind REAL,
            price_ts  TEXT,
            price_src TEXT,
            booking_url TEXT,
            booking_label TEXT
        )
    """)
    conn.execute("CREATE INDEX idx_line ON cruises(line)")
    conn.execute("CREATE INDEX idx_dep  ON cruises(departure)")
    conn.execute("CREATE INDEX idx_nts  ON cruises(nights)")
    conn.execute("CREATE INDEX idx_reg  ON cruises(region)")
    conn.execute("""
        CREATE VIRTUAL TABLE cruises_fts USING fts5(
            line, ship, region, route, from_port,
            content='cruises', content_rowid='id'
        )
    """)
    rows = []
    for r in records:
        sources = r.get('sources') or []
        # booking_url already resolved in main flow (CI Trinity Leg 1)
        rows.append((
            r.get('line') or '',
            r.get('ship') or '',
            r.get('departure') or '',
            r.get('nights') or 0,
            r.get('from_port') or '',
            (r.get('route') or '')[:200],
            r.get('region') or '',
            json.dumps(sources),
            1 if len(sources) > 1 else 0,
            r.get('price_disc'),
            r.get('price_ts'),
            r.get('price_src'),
            r.get('booking_url', ''),
            r.get('booking_label', ''),
        ))
    conn.executemany(
        "INSERT INTO cruises(line,ship,departure,nights,from_port,route,region,sources,multi,"
        "price_ind,price_ts,price_src,booking_url,booking_label) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        rows
    )
    conn.execute(
        "INSERT INTO cruises_fts(rowid,line,ship,region,route,from_port) "
        "SELECT id,line,ship,region,route,from_port FROM cruises"
    )
    conn.commit()
    conn.close()


if __name__ == '__main__':
    source_lists = []

    print("Loading VTG deals…")
    vtg = parse_vtg(VTG_FILE)
    print(f"  {len(vtg)} VTG deals")
    source_lists.append(vtg)

    if OCEANIA_FILE.exists():
        oceania = json.loads(OCEANIA_FILE.read_text())
        source_lists.append(oceania)
        print(f"  +{len(oceania)} Oceania deals")

    if CRYSTAL_FILE.exists():
        crystal = json.loads(CRYSTAL_FILE.read_text())
        source_lists.append(crystal)
        print(f"  +{len(crystal)} Crystal Cruises deals")

    for stem, label in [("regent", "Regent"), ("silversea", "Silversea"), ("atlas", "Atlas Ocean")]:
        f = _latest_intel(stem)
        if f:
            records = json.loads(f.read_text())
            source_lists.append(records)
            print(f"  +{len(records)} {label} VTG deals ({f.name})")

    for stem, label in [("regent", "Regent"), ("silversea", "Silversea"), ("atlas", "Atlas Ocean")]:
        f = _latest_intel(stem, suffix="perx")
        if f:
            records = parse_source_json(f, f"{stem}_perx")
            source_lists.append(records)
            print(f"  +{len(records)} {label} Perx sailings ({f.name})")

    if CRUISEMAPPER_FILE.exists():
        cm = parse_source_json(CRUISEMAPPER_FILE, 'cruisemapper')
        source_lists.append(cm)
        print(f"  +{len(cm)} CruiseMapper sailings")

    if DELUXE_FILE.exists():
        dx = parse_source_json(DELUXE_FILE, 'deluxe')
        source_lists.append(dx)
        print(f"  +{len(dx)} DeluxeCruises sailings")

    if PERX_FILE.exists():
        px = parse_source_json(PERX_FILE, 'perx')
        source_lists.append(px)
        print(f"  +{len(px)} Perx sailings")

    # Seabourn inclusion restored 2026-06-26 — all luxury/ultra-luxury lines included

    # Commander directive 2026-06-26: Viking = ocean ships only (exclude river fleet)
    # Viking Ocean fleet uses astronomical/classical names; river fleet uses Norse mythology names.
    # Complete Viking Ocean fleet confirmed from VTG 2026-06-26:
    # Astrea, Jupiter, Libra, Lyra, Mars, Mira, Neptune, Octantis, Orion,
    # Polaris, Saturn, Sea, Sky, Star, Vela, Venus, Vesta (+ older: Sun, Minerva)
    VIKING_OCEAN_KEYWORDS = {
        'sky', 'sun', 'sea', 'star', 'venus', 'mars', 'jupiter', 'saturn',
        'neptune', 'orion', 'octantis', 'polaris', 'minerva', 'vela',
        'libra', 'lyra', 'mira', 'vesta', 'astrea', 'aton', 'caledonian',
    }
    def _is_viking_ocean(r):
        line = (r.get('cruise_line') or r.get('line') or '').lower()
        if 'viking' not in line:
            return True  # not Viking — keep unconditionally
        ship = (r.get('ship_name') or r.get('ship') or '').lower()
        return any(kw in ship for kw in VIKING_OCEAN_KEYWORDS)

    pre_viking = sum(len(l) for l in source_lists)
    source_lists = [[r for r in lst if _is_viking_ocean(r)] for lst in source_lists]
    post_viking = sum(len(l) for l in source_lists)
    river_excl = pre_viking - post_viking
    if river_excl:
        print(f"  Excluded {river_excl} Viking river/non-ocean records")

    print("Merging all sources…")
    merged = merge_all(source_lists)
    multi = sum(1 for r in merged if len(r['sources']) > 1)
    print(f"  Total: {len(merged)} records · {multi} multi-source")

    print("Resolving external booking links (CI Trinity Leg 1)…")
    from scripts.link_resolver import resolve_sailing
    link_count = 0
    for r in merged:
        resolved = resolve_sailing(
            line=r.get("line", ""),
            ship=r.get("ship", ""),
            departure=r.get("departure"),
            voyage_code=r.get("voyage_code"),
            from_port=r.get("from_port"),
            nights=r.get("nights"),
        )
        r["booking_url"] = resolved.get("url", "")
        r["booking_label"] = resolved.get("label", "")
        if r["booking_url"]:
            link_count += 1
    print(f"  {link_count}/{len(merged)} records have booking URLs")

    print("Saving JSON export…")
    OUT_JSON.write_text(json.dumps(merged, indent=2, default=str))
    print(f"  → {OUT_JSON}")

    print("Building HTML (legacy archive — search shell is cruises_web/index.html)…")
    html = build_html(merged)
    legacy_path = Path("/home/john/Thunderbird/output/cruises_legacy.html")
    legacy_path.write_text(html)
    sz = len(html)
    print(f"  → {legacy_path}  ({sz:,} chars)")

    print("Building SQLite search database…")
    build_sqlite(merged)
    print(f"  → {DB_PATH}")
    print("Done.")
