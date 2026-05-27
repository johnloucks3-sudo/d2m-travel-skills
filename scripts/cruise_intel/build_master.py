#!/usr/bin/env python3
"""
Cruise Intel — Master CSV Builder
Assembles deluxecruises, Perx, OAT, Ponant + Wave 2 (HX, SeaDream, Explora)
+ Wave 3 aggregators (CruiseMapper, CruisesOnly, CruisePlum)
into one deduplicated master CSV.
Cross-reference key: normalized_ship + departure_date ±1 day (SP-T2-2).
Runs SP-T2-5 smoke check before reporting COMPLETE.
"""
import argparse
import csv
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import (
    OUTPUT_DIR, MASTER_CSV, STATS_JSON,
    DELUXE_JSON, PERX_JSON, OAT_JSON, PONANT_CLEAN_JSON,
    HX_JSON, SEADREAM_JSON, EXPLORA_JSON,
    CRUISEMAPPER_JSON, CRUISESONLY_JSON, CRUISEPLUM_JSON,
    CSV_COLUMNS, SHIP_LINE_MAP, LINE_CANONICAL,
)
from utils import parse_date, norm_ship, find_match, resolve_cruise_line, normalize_flag


def load_json(path: Path, label: str) -> list:
    if not path.exists():
        print(f'  [build] WARNING: {label} file not found at {path} — skipping')
        return []
    data = json.loads(path.read_text())
    if isinstance(data, list):
        return data
    # Ponant clean is a list; raw has {'all': [...]}
    if isinstance(data, dict):
        return data.get('filtered', data.get('all', data.get('data', [])))
    return []


def make_entry(
    cruise_line='', ship_name='', departure_date=None,
    month='', days='', route='', voyage_code='',
    on_deluxecruises='', on_perx='', on_oat='', on_ponant='',
    on_hx='', on_seadream='', on_explora='',
    on_cruisemapper='', on_cruisesonly='', on_cruiseplum='',
    price_usd='',
) -> dict:
    d_obj = parse_date(str(departure_date)) if departure_date else None
    d_iso = d_obj.isoformat() if d_obj else (str(departure_date) if departure_date else '')
    mon = month or (d_obj.strftime('%B') if d_obj else '')
    return {
        'cruise_line':        cruise_line,
        'ship_name':          ship_name,
        'ship_norm':          norm_ship(ship_name),
        'departure_date':     d_iso,
        'departure_date_obj': d_obj,
        'month':              mon,
        'days':               str(days),
        'route':              route,
        'voyage_code':        voyage_code,
        'on_deluxecruises':   normalize_flag(on_deluxecruises),
        'on_perx':            normalize_flag(on_perx),
        'on_oat':             normalize_flag(on_oat),
        'on_ponant':          normalize_flag(on_ponant),
        'on_hx':              normalize_flag(on_hx),
        'on_seadream':        normalize_flag(on_seadream),
        'on_explora':         normalize_flag(on_explora),
        'on_cruisemapper':    normalize_flag(on_cruisemapper),
        'on_cruisesonly':     normalize_flag(on_cruisesonly),
        'on_cruiseplum':      normalize_flag(on_cruiseplum),
        'price_usd':          str(price_usd) if price_usd else '',
    }


def ingest_deluxecruises(entries: list, data: list) -> None:
    for r in data:
        e = make_entry(
            cruise_line   = r.get('cruise_line', ''),
            ship_name     = r.get('ship_name', ''),
            departure_date= r.get('date_str', ''),
            month         = r.get('month', ''),
            days          = r.get('days', ''),
            route         = r.get('route', ''),
            voyage_code   = r.get('voyage_code', ''),
            on_deluxecruises = 'Y',
        )
        entries.append(e)


def ingest_perx(entries: list, data: list, search_pool: list = None) -> None:
    """Cross-match against search_pool only (prevents same-source ±1 day collapse)."""
    pool = search_pool if search_pool is not None else entries
    added = matched = 0
    for r in data:
        d_obj = parse_date(r.get('date', ''))
        ship_n = norm_ship(r.get('ship', ''))

        m = find_match(ship_n, d_obj, pool)
        if m:
            m['on_perx'] = 'Y'
            if not m['cruise_line'] and r.get('cruise_line'):
                m['cruise_line'] = r['cruise_line']
            matched += 1
        else:
            entries.append(make_entry(
                cruise_line   = r.get('cruise_line', ''),
                ship_name     = r.get('ship', ''),
                departure_date= r.get('date', ''),
                days          = r.get('days', ''),
                route         = r.get('route', ''),
                on_perx       = 'Y',
            ))
            added += 1
    print(f'  [build] Perx: {matched} cross-matched, {added} net-new')


def ingest_oat(entries: list, data: list, search_pool: list = None) -> None:
    """Cross-match against search_pool only (prevents same-source ±1 day collapse)."""
    pool = search_pool if search_pool is not None else entries
    added = matched = 0
    for r in data:
        dep_str = r.get('departure_date') or r.get('date_str', '')
        d_obj = parse_date(dep_str)
        ship_n = norm_ship(r.get('ship_name', ''))

        m = find_match(ship_n, d_obj, pool)
        if m:
            m['on_oat'] = 'Y'
            matched += 1
        else:
            entries.append(make_entry(
                cruise_line   = r.get('cruise_line', 'Overseas Adventure Travel'),
                ship_name     = r.get('ship_name', ''),
                departure_date= dep_str,
                days          = r.get('days', ''),
                route         = r.get('route', ''),
                on_oat        = 'Y',
            ))
            added += 1
    print(f'  [build] OAT: {matched} cross-matched, {added} net-new')


def ingest_ponant(entries: list, data: list, search_pool: list = None) -> None:
    """Cross-match against search_pool only (prevents same-source ±1 day collapse)."""
    pool = search_pool if search_pool is not None else entries
    added = matched = 0
    for r in data:
        dep_str = r.get('departure_date', '')
        d_obj = parse_date(dep_str)
        ship_n = norm_ship(r.get('ship', '') or r.get('ship_name', ''))

        m = find_match(ship_n, d_obj, pool)
        if m:
            m['on_ponant'] = 'Y'
            matched += 1
        else:
            route = (r.get('route') or r.get('name', '') or
                     (f"{r.get('from_port','')} to {r.get('to_port','')}"
                      if r.get('from_port') else ''))
            entries.append(make_entry(
                cruise_line   = 'PONANT',
                ship_name     = r.get('ship') or r.get('ship_name', ''),
                departure_date= dep_str,
                days          = r.get('nights') or r.get('days', ''),
                route         = route[:100],
                on_ponant     = 'Y',
            ))
            added += 1
    print(f'  [build] Ponant: {matched} cross-matched, {added} net-new')


def ingest_hx(entries: list, data: list, search_pool: list = None) -> None:
    """Ingest HX Expeditions — cross-match against search_pool."""
    pool = search_pool if search_pool is not None else entries
    added = matched = 0
    for r in data:
        dep_str = r.get('departure_date', '')
        d_obj = parse_date(dep_str)
        ship_n = norm_ship(r.get('ship_name', ''))

        m = find_match(ship_n, d_obj, pool)
        if m:
            m['on_hx'] = 'Y'
            matched += 1
        else:
            entries.append(make_entry(
                cruise_line    = r.get('cruise_line', 'HX Expeditions'),
                ship_name      = r.get('ship_name', ''),
                departure_date = dep_str,
                days           = r.get('days', ''),
                route          = r.get('route', '')[:100],
                voyage_code    = r.get('voyage_code', ''),
                on_hx          = 'Y',
            ))
            added += 1
    print(f'  [build] HX Expeditions: {matched} cross-matched, {added} net-new')


def ingest_seadream(entries: list, data: list, search_pool: list = None) -> None:
    """Ingest SeaDream Yacht Club — cross-match against search_pool."""
    pool = search_pool if search_pool is not None else entries
    added = matched = 0
    for r in data:
        dep_str = r.get('departure_date', '')
        d_obj = parse_date(dep_str)
        ship_n = norm_ship(r.get('ship_name', '') or r.get('ship', ''))

        m = find_match(ship_n, d_obj, pool)
        if m:
            m['on_seadream'] = 'Y'
            matched += 1
        else:
            route = r.get('route', '') or r.get('name', '')
            entries.append(make_entry(
                cruise_line    = 'SeaDream Yacht Club',
                ship_name      = r.get('ship_name', '') or r.get('ship', ''),
                departure_date = dep_str,
                days           = r.get('nights', '') or r.get('days', ''),
                route          = route[:100],
                voyage_code    = r.get('voyage_id', ''),
                on_seadream    = 'Y',
            ))
            added += 1
    print(f'  [build] SeaDream: {matched} cross-matched, {added} net-new')


def ingest_explora(entries: list, data: list, search_pool: list = None) -> None:
    """Ingest Explora Journeys — cross-match against search_pool, carry price."""
    pool = search_pool if search_pool is not None else entries
    added = matched = 0
    for r in data:
        dep_str = r.get('departure_date', '')
        d_obj = parse_date(dep_str)
        ship_n = norm_ship(r.get('ship_name', ''))
        price = r.get('price_usd_disc', '') or r.get('price_usd', '')

        m = find_match(ship_n, d_obj, pool)
        if m:
            m['on_explora'] = 'Y'
            if price and not m.get('price_usd'):
                m['price_usd'] = str(price)
            matched += 1
        else:
            entries.append(make_entry(
                cruise_line    = r.get('cruise_line', 'Explora Journeys'),
                ship_name      = r.get('ship_name', ''),
                departure_date = dep_str,
                days           = r.get('days', ''),
                route          = r.get('route', '')[:120],
                voyage_code    = r.get('voyage_code', ''),
                on_explora     = 'Y',
                price_usd      = price,
            ))
            added += 1
    print(f'  [build] Explora Journeys: {matched} cross-matched, {added} net-new')


def ingest_cruisemapper(entries: list, data: list, search_pool: list = None) -> None:
    """Ingest CruiseMapper — cross-match against search_pool, carry route."""
    pool = search_pool if search_pool is not None else entries
    added = matched = 0
    for r in data:
        dep_str = r.get('departure_date', '')
        d_obj = parse_date(dep_str)
        ship_n = norm_ship(r.get('ship_name', ''))

        m = find_match(ship_n, d_obj, pool)
        if m:
            m['on_cruisemapper'] = 'Y'
            if not m.get('route') and r.get('route'):
                m['route'] = r['route']
            matched += 1
        else:
            entries.append(make_entry(
                cruise_line    = r.get('cruise_line', ''),
                ship_name      = r.get('ship_name', ''),
                departure_date = dep_str,
                days           = r.get('days', ''),
                route          = r.get('route', '')[:120],
                on_cruisemapper= 'Y',
            ))
            added += 1
    print(f'  [build] CruiseMapper: {matched} cross-matched, {added} net-new')


def ingest_cruisesonly(entries: list, data: list, search_pool: list = None) -> None:
    """Ingest CruisesOnly — cross-match, carry price when higher-confidence."""
    pool = search_pool if search_pool is not None else entries
    added = matched = 0
    for r in data:
        dep_str = r.get('departure_date', '')
        d_obj = parse_date(dep_str)
        ship_n = norm_ship(r.get('ship_name', ''))
        price = r.get('price_usd', '')

        m = find_match(ship_n, d_obj, pool)
        if m:
            m['on_cruisesonly'] = 'Y'
            if price and not m.get('price_usd'):
                m['price_usd'] = str(price)
            matched += 1
        else:
            entries.append(make_entry(
                cruise_line   = r.get('cruise_line', ''),
                ship_name     = r.get('ship_name', ''),
                departure_date= dep_str,
                days          = r.get('days', ''),
                route         = r.get('route', '')[:120],
                on_cruisesonly= 'Y',
                price_usd     = price,
            ))
            added += 1
    print(f'  [build] CruisesOnly: {matched} cross-matched, {added} net-new')


def ingest_cruiseplum(entries: list, data: list, search_pool: list = None) -> None:
    """Ingest CruisePlum — cross-match, carry out-the-door price (preferred over others)."""
    pool = search_pool if search_pool is not None else entries
    added = matched = 0
    for r in data:
        dep_str = r.get('departure_date', '')
        d_obj = parse_date(dep_str)
        ship_n = norm_ship(r.get('ship_name', ''))
        price = r.get('price_usd', '')

        m = find_match(ship_n, d_obj, pool)
        if m:
            m['on_cruiseplum'] = 'Y'
            # CruisePlum has "out-the-door" pricing — prefer it over promo estimates
            if price:
                m['price_usd'] = str(price)
            matched += 1
        else:
            entries.append(make_entry(
                cruise_line   = r.get('cruise_line', ''),
                ship_name     = r.get('ship_name', ''),
                departure_date= dep_str,
                days          = r.get('days', ''),
                route         = r.get('route', '')[:120],
                on_cruiseplum = 'Y',
                price_usd     = price,
            ))
            added += 1
    print(f'  [build] CruisePlum: {matched} cross-matched, {added} net-new')


def fill_missing_lines(entries: list) -> int:
    """Use SHIP_LINE_MAP to fill blank cruise_line fields."""
    fixed = 0
    for e in entries:
        if not e['cruise_line'] and e['ship_name']:
            resolved = resolve_cruise_line(e['ship_name'])
            if resolved:
                e['cruise_line'] = resolved
                fixed += 1
    return fixed


def smoke_check(entries: list,
                deluxe_expected: int, perx_expected: int,
                oat_expected: int, ponant_expected: int,
                hx_expected: int = 0, seadream_expected: int = 0,
                explora_expected: int = 0,
                cruisemapper_expected: int = 0,
                cruisesonly_expected: int = 0,
                cruiseplum_expected: int = 0,
                tolerance: float = 0.02) -> bool:
    """
    SP-T2-5: count(csv[on_source]='Y') must equal count(source_json records).
    Only validates sources where expected > 0.
    tolerance: fractional allowance for sources with raw (undeduped) input files.
    """
    actual = {
        'deluxecruises': sum(1 for e in entries if e.get('on_deluxecruises') == 'Y'),
        'perx':          sum(1 for e in entries if e.get('on_perx') == 'Y'),
        'oat':           sum(1 for e in entries if e.get('on_oat') == 'Y'),
        'ponant':        sum(1 for e in entries if e.get('on_ponant') == 'Y'),
        'hx':            sum(1 for e in entries if e.get('on_hx') == 'Y'),
        'seadream':      sum(1 for e in entries if e.get('on_seadream') == 'Y'),
        'explora':       sum(1 for e in entries if e.get('on_explora') == 'Y'),
        'cruisemapper':  sum(1 for e in entries if e.get('on_cruisemapper') == 'Y'),
        'cruisesonly':   sum(1 for e in entries if e.get('on_cruisesonly') == 'Y'),
        'cruiseplum':    sum(1 for e in entries if e.get('on_cruiseplum') == 'Y'),
    }
    expected = {
        'deluxecruises': deluxe_expected,
        'perx':          perx_expected,
        'oat':           oat_expected,
        'ponant':        ponant_expected,
        'hx':            hx_expected,
        'seadream':      seadream_expected,
        'explora':       explora_expected,
        'cruisemapper':  cruisemapper_expected,
        'cruisesonly':   cruisesonly_expected,
        'cruiseplum':    cruiseplum_expected,
    }
    passed = True
    print('\n  [smoke] SP-T2-5 Smoke Check:')
    for src, exp in expected.items():
        act = actual[src]
        if exp == 0:
            print(f'    {src:20s}  SKIP (no data loaded)')
            continue
        ratio = act / exp if exp else 1.0
        if act >= exp:
            ok = '✓ PASS'
        elif ratio >= (1.0 - tolerance):
            ok = '~ WARN'  # within tolerance — expected for raw multi-region API data
        else:
            ok = '✗ FAIL'
        print(f'    {src:20s}  {ok}  actual={act}  expected_min={exp}  ({ratio:.1%})')
        if ratio < (1.0 - tolerance):
            passed = False
    return passed


def write_csv(entries: list, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        w.writeheader()
        for e in entries:
            w.writerow({c: e.get(c, '') for c in CSV_COLUMNS})


def write_stats(entries: list, sources: dict, path: Path) -> None:
    lines = sorted(set(e['cruise_line'] for e in entries if e['cruise_line']))
    oct_e = [e for e in entries if e['departure_date'][:7] == '2026-10']
    nov_e = [e for e in entries if e['departure_date'][:7] == '2026-11']

    def flag_count(key: str) -> int:
        return sum(1 for e in entries if e.get(key) == 'Y')

    orig_flags   = ('on_deluxecruises', 'on_perx', 'on_oat', 'on_ponant')
    wave2_flags  = ('on_hx', 'on_seadream', 'on_explora')
    wave3_flags  = ('on_cruisemapper', 'on_cruisesonly', 'on_cruiseplum')
    all_flags    = orig_flags + wave2_flags + wave3_flags

    # Net-new: entries ONLY appearing in that wave (not confirmed by earlier waves)
    wave2_only = sum(1 for e in entries
                     if any(e.get(f) == 'Y' for f in wave2_flags)
                     and not any(e.get(f) == 'Y' for f in orig_flags))
    wave3_only = sum(1 for e in entries
                     if any(e.get(f) == 'Y' for f in wave3_flags)
                     and not any(e.get(f) == 'Y' for f in orig_flags + wave2_flags))

    stats = {
        'exercise': 'T2 Wing Exercise — Arctic/Europe/Med Cruise Intelligence',
        'wave': 'Wave 3 (10 sources: deluxe + perx + oat + ponant + hx + seadream + explora + cruisemapper + cruisesonly + cruiseplum)',
        'generated': datetime.now().strftime('%Y-%m-%d'),
        'sources': {k: {'sailings': v} for k, v in sources.items()},
        'master_totals': {
            'unique_sailings':          len(entries),
            'october':                  len(oct_e),
            'november':                 len(nov_e),
            'wave2_net_new_sailings':   wave2_only,
            'wave3_net_new_sailings':   wave3_only,
            'on_deluxecruises':         flag_count('on_deluxecruises'),
            'on_perx':                  flag_count('on_perx'),
            'on_oat':                   flag_count('on_oat'),
            'on_ponant':                flag_count('on_ponant'),
            'on_hx':                    flag_count('on_hx'),
            'on_seadream':              flag_count('on_seadream'),
            'on_explora':               flag_count('on_explora'),
            'on_cruisemapper':          flag_count('on_cruisemapper'),
            'on_cruisesonly':           flag_count('on_cruisesonly'),
            'on_cruiseplum':            flag_count('on_cruiseplum'),
            'multi_source_confidence':  sum(1 for e in entries
                                            if sum(1 for f in all_flags
                                                   if e.get(f) == 'Y') >= 2),
            'cruise_lines':             len(lines),
            'cruise_line_list':         lines,
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(stats, indent=2))


def build_master(
    deluxe_path: Path        = DELUXE_JSON,
    perx_path: Path          = PERX_JSON,
    oat_path: Path           = OAT_JSON,
    ponant_path: Path        = PONANT_CLEAN_JSON,
    hx_path: Path            = HX_JSON,
    seadream_path: Path      = SEADREAM_JSON,
    explora_path: Path       = EXPLORA_JSON,
    cruisemapper_path: Path  = CRUISEMAPPER_JSON,
    cruisesonly_path: Path   = CRUISESONLY_JSON,
    cruiseplum_path: Path    = CRUISEPLUM_JSON,
    output_csv: Path         = MASTER_CSV,
    stats_path: Path         = STATS_JSON,
    skip_smoke: bool         = False,
) -> list:
    print('[build] Loading source data...')
    deluxe_data       = load_json(deluxe_path,       'deluxecruises')
    perx_data         = load_json(perx_path,         'perx')
    oat_data          = load_json(oat_path,          'oat')
    ponant_data       = load_json(ponant_path,       'ponant')
    hx_data           = load_json(hx_path,           'hx_expeditions')
    seadream_data     = load_json(seadream_path,     'seadream')
    explora_data      = load_json(explora_path,      'explora_journeys')
    cruisemapper_data = load_json(cruisemapper_path, 'cruisemapper')
    cruisesonly_data  = load_json(cruisesonly_path,  'cruisesonly')
    cruiseplum_data   = load_json(cruiseplum_path,   'cruiseplum')

    print(f'  Wave 1: deluxe={len(deluxe_data)}, perx={len(perx_data)}, '
          f'oat={len(oat_data)}, ponant={len(ponant_data)}')
    print(f'  Wave 2: hx={len(hx_data)}, seadream={len(seadream_data)}, '
          f'explora={len(explora_data)}')
    print(f'  Wave 3: cruisemapper={len(cruisemapper_data)}, '
          f'cruisesonly={len(cruisesonly_data)}, cruiseplum={len(cruiseplum_data)}')

    print('[build] Building master entries...')
    entries: list = []
    # Wave 1 — original four sources
    ingest_deluxecruises(entries, deluxe_data)
    after_deluxe = list(entries)
    ingest_perx(entries, perx_data, search_pool=after_deluxe)
    after_perx = list(entries)
    ingest_oat(entries, oat_data, search_pool=after_perx)
    after_oat = list(entries)
    ingest_ponant(entries, ponant_data, search_pool=after_oat)
    # Wave 2 — three new native sources
    after_wave1 = list(entries)
    ingest_hx(entries, hx_data, search_pool=after_wave1)
    after_hx = list(entries)
    ingest_seadream(entries, seadream_data, search_pool=after_hx)
    after_seadream = list(entries)
    ingest_explora(entries, explora_data, search_pool=after_seadream)
    # Wave 3 — aggregator sources (cross-match against full existing pool)
    after_wave2 = list(entries)
    ingest_cruisemapper(entries, cruisemapper_data, search_pool=after_wave2)
    after_cm = list(entries)
    ingest_cruisesonly(entries, cruisesonly_data, search_pool=after_cm)
    after_co = list(entries)
    ingest_cruiseplum(entries, cruiseplum_data, search_pool=after_co)

    # Fill missing cruise_line fields
    fixed = fill_missing_lines(entries)
    if fixed:
        print(f'[build] Resolved {fixed} missing cruise_line fields via SHIP_LINE_MAP')

    # Canonicalize cruise line names (e.g. 'Oceania' → 'Oceania Cruises')
    canon_fixed = 0
    for e in entries:
        canonical = LINE_CANONICAL.get(e.get('cruise_line', ''))
        if canonical:
            e['cruise_line'] = canonical
            canon_fixed += 1
    if canon_fixed:
        print(f'[build] Canonicalized {canon_fixed} cruise_line names via LINE_CANONICAL')

    # Sort by departure date
    entries.sort(key=lambda e: e.get('departure_date', ''))
    print(f'[build] Total unique sailings (10 sources): {len(entries)}')

    # All source flags for confidence counting
    ALL_FLAGS = (
        'on_deluxecruises', 'on_perx', 'on_oat', 'on_ponant',
        'on_hx', 'on_seadream', 'on_explora',
        'on_cruisemapper', 'on_cruisesonly', 'on_cruiseplum',
    )
    W1_FLAGS = ('on_deluxecruises', 'on_perx', 'on_oat', 'on_ponant')
    W2_FLAGS = ('on_hx', 'on_seadream', 'on_explora')
    W3_FLAGS = ('on_cruisemapper', 'on_cruisesonly', 'on_cruiseplum')

    # Smoke check — all 10 sources
    if not skip_smoke:
        passed = smoke_check(
            entries,
            deluxe_expected       = len(deluxe_data)       if deluxe_data       else 0,
            perx_expected         = len(perx_data)         if perx_data         else 0,
            oat_expected          = len(oat_data)          if oat_data          else 0,
            ponant_expected       = len(ponant_data)       if ponant_data       else 0,
            hx_expected           = len(hx_data)           if hx_data           else 0,
            seadream_expected     = len(seadream_data)     if seadream_data     else 0,
            explora_expected      = len(explora_data)      if explora_data      else 0,
            cruisemapper_expected = len(cruisemapper_data) if cruisemapper_data else 0,
            cruisesonly_expected  = len(cruisesonly_data)  if cruisesonly_data  else 0,
            cruiseplum_expected   = len(cruiseplum_data)   if cruiseplum_data   else 0,
        )
        if not passed:
            print('\n[build] WARNING: Smoke check FAILED — review mismatches above')
        else:
            print('\n[build] Smoke check PASSED')

    # Write CSV
    write_csv(entries, output_csv)
    print(f'[build] CSV → {output_csv}')

    # Write stats
    sources = {
        'deluxecruises': len(deluxe_data),
        'perx':          len(perx_data),
        'oat':           len(oat_data),
        'ponant':        len(ponant_data),
        'hx':            len(hx_data),
        'seadream':      len(seadream_data),
        'explora':       len(explora_data),
        'cruisemapper':  len(cruisemapper_data),
        'cruisesonly':   len(cruisesonly_data),
        'cruiseplum':    len(cruiseplum_data),
    }
    write_stats(entries, sources, stats_path)
    print(f'[build] Stats → {stats_path}')

    # Summary
    lines = sorted(set(e['cruise_line'] for e in entries if e['cruise_line']))

    def flag_count(col: str) -> int:
        return sum(1 for e in entries if e.get(col) == 'Y')

    multi_source = sum(
        1 for e in entries
        if sum(1 for col in ALL_FLAGS if e.get(col) == 'Y') >= 2
    )
    wave3_net_new = sum(
        1 for e in entries
        if any(e.get(f) == 'Y' for f in W3_FLAGS)
        and all(e.get(f) != 'Y' for f in W1_FLAGS + W2_FLAGS)
    )

    print(f'\n[build] === FINAL SUMMARY — 10 Sources ===')
    print(f'  Unique sailings   : {len(entries)}')
    print(f'  Cruise lines      : {len(lines)}')
    print(f'  Multi-source (2+) : {multi_source}')
    print(f'  Wave 3 net-new    : {wave3_net_new}')
    print(f'  ---')
    print(f'  Wave 1:')
    print(f'    on_deluxecruises : {flag_count("on_deluxecruises")}')
    print(f'    on_perx          : {flag_count("on_perx")}')
    print(f'    on_oat           : {flag_count("on_oat")}')
    print(f'    on_ponant        : {flag_count("on_ponant")}')
    print(f'  Wave 2:')
    print(f'    on_hx            : {flag_count("on_hx")}')
    print(f'    on_seadream      : {flag_count("on_seadream")}')
    print(f'    on_explora       : {flag_count("on_explora")}')
    print(f'  Wave 3:')
    print(f'    on_cruisemapper  : {flag_count("on_cruisemapper")}')
    print(f'    on_cruisesonly   : {flag_count("on_cruisesonly")}')
    print(f'    on_cruiseplum    : {flag_count("on_cruiseplum")}')

    return entries


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Build master cruise intelligence CSV')
    parser.add_argument('--deluxe',  type=Path, default=DELUXE_JSON,
                        help='deluxecruises.com JSON source')
    parser.add_argument('--perx',    type=Path, default=PERX_JSON)
    parser.add_argument('--oat',     type=Path, default=OAT_JSON)
    parser.add_argument('--ponant',  type=Path, default=PONANT_CLEAN_JSON)
    parser.add_argument('--output',  type=Path, default=MASTER_CSV)
    parser.add_argument('--stats',   type=Path, default=STATS_JSON)
    parser.add_argument('--skip-smoke', action='store_true')
    args = parser.parse_args()

    build_master(
        deluxe_path=args.deluxe,
        perx_path=args.perx,
        oat_path=args.oat,
        ponant_path=args.ponant,
        output_csv=args.output,
        stats_path=args.stats,
        skip_smoke=args.skip_smoke,
    )
