#!/usr/bin/env python3
"""
Cruise Intel — Master CSV Builder
Assembles deluxecruises, Perx, OAT, and Ponant into one deduplicated master CSV.
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
    CSV_COLUMNS, SHIP_LINE_MAP,
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
) -> dict:
    d_obj = parse_date(str(departure_date)) if departure_date else None
    d_iso = d_obj.isoformat() if d_obj else (str(departure_date) if departure_date else '')
    mon = month or (d_obj.strftime('%B') if d_obj else '')
    return {
        'cruise_line':     cruise_line,
        'ship_name':       ship_name,
        'ship_norm':       norm_ship(ship_name),
        'departure_date':  d_iso,
        'departure_date_obj': d_obj,
        'month':           mon,
        'days':            str(days),
        'route':           route,
        'voyage_code':     voyage_code,
        'on_deluxecruises': normalize_flag(on_deluxecruises),
        'on_perx':          normalize_flag(on_perx),
        'on_oat':           normalize_flag(on_oat),
        'on_ponant':        normalize_flag(on_ponant),
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
                tolerance: float = 0.02) -> bool:
    """
    SP-T2-5: count(csv[on_source]='Y') must equal count(source_json records).
    Only validates sources where expected > 0.
    tolerance: fractional allowance for sources with raw (undeduped) input files,
               e.g. Perx raw API data where same sailing appears in multiple region
               queries and gets correctly absorbed by ±1 day cross-match. WARN not FAIL.
    """
    actual = {
        'deluxecruises': sum(1 for e in entries if e['on_deluxecruises'] == 'Y'),
        'perx':          sum(1 for e in entries if e['on_perx'] == 'Y'),
        'oat':           sum(1 for e in entries if e['on_oat'] == 'Y'),
        'ponant':        sum(1 for e in entries if e['on_ponant'] == 'Y'),
    }
    expected = {
        'deluxecruises': deluxe_expected,
        'perx':          perx_expected,
        'oat':           oat_expected,
        'ponant':        ponant_expected,
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
    stats = {
        'exercise': 'T2 Wing Exercise — Arctic/Europe/Med Cruise Intelligence',
        'generated': datetime.now().strftime('%Y-%m-%d'),
        'sources': {k: {'sailings': v} for k, v in sources.items()},
        'master_totals': {
            'unique_sailings':      len(entries),
            'october':              len(oct_e),
            'november':             len(nov_e),
            'on_deluxe_and_perx':   sum(1 for e in entries
                                        if e['on_deluxecruises'] == 'Y' and e['on_perx'] == 'Y'),
            'on_deluxe_and_ponant': sum(1 for e in entries
                                        if e['on_deluxecruises'] == 'Y' and e['on_ponant'] == 'Y'),
            'on_perx_and_ponant':   sum(1 for e in entries
                                        if e['on_perx'] == 'Y' and e['on_ponant'] == 'Y'),
            'on_all_sources':       sum(1 for e in entries
                                        if e['on_deluxecruises'] == 'Y' and e['on_perx'] == 'Y'
                                        and e['on_oat'] == 'Y' and e['on_ponant'] == 'Y'),
            'cruise_lines':         len(lines),
            'cruise_line_list':     lines,
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(stats, indent=2))


def build_master(
    deluxe_path: Path = DELUXE_JSON,
    perx_path: Path   = PERX_JSON,
    oat_path: Path    = OAT_JSON,
    ponant_path: Path = PONANT_CLEAN_JSON,
    output_csv: Path  = MASTER_CSV,
    stats_path: Path  = STATS_JSON,
    skip_smoke: bool  = False,
) -> list:
    print('[build] Loading source data...')
    deluxe_data  = load_json(deluxe_path,  'deluxecruises')
    perx_data    = load_json(perx_path,    'perx')
    oat_data     = load_json(oat_path,     'oat')
    ponant_data  = load_json(ponant_path,  'ponant')

    print(f'  Loaded: deluxe={len(deluxe_data)}, perx={len(perx_data)}, '
          f'oat={len(oat_data)}, ponant={len(ponant_data)}')

    print('[build] Building master entries...')
    entries: list = []
    ingest_deluxecruises(entries, deluxe_data)
    # Snapshots prevent ±1 day tolerance from collapsing same-source adjacent sailings
    after_deluxe = list(entries)
    ingest_perx(entries, perx_data, search_pool=after_deluxe)
    after_perx = list(entries)
    ingest_oat(entries, oat_data, search_pool=after_perx)
    after_oat = list(entries)
    ingest_ponant(entries, ponant_data, search_pool=after_oat)

    # Fill missing cruise_line fields
    fixed = fill_missing_lines(entries)
    if fixed:
        print(f'[build] Resolved {fixed} missing cruise_line fields via SHIP_LINE_MAP')

    # Sort by departure date
    entries.sort(key=lambda e: e.get('departure_date', ''))
    print(f'[build] Total unique sailings: {len(entries)}')

    # Smoke check
    if not skip_smoke:
        sources = {
            'deluxecruises': len(deluxe_data),
            'perx':          len(perx_data),
            'oat':           len(oat_data),
            'ponant':        len(ponant_data),
        }
        passed = smoke_check(entries,
                             deluxe_expected=len(deluxe_data) if deluxe_data else 0,
                             perx_expected=len(perx_data) if perx_data else 0,
                             oat_expected=len(oat_data) if oat_data else 0,
                             ponant_expected=len(ponant_data) if ponant_data else 0)
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
    }
    write_stats(entries, sources, stats_path)
    print(f'[build] Stats → {stats_path}')

    # Summary
    lines = sorted(set(e['cruise_line'] for e in entries if e['cruise_line']))
    blank_lines = sum(1 for e in entries if not e['cruise_line'])
    print(f'\n[build] === FINAL SUMMARY ===')
    print(f'  Unique sailings : {len(entries)}')
    print(f'  Cruise lines    : {len(lines)}')
    print(f'  Blank cruise_line: {blank_lines}')
    print(f'  on_deluxecruises: {sum(1 for e in entries if e["on_deluxecruises"]=="Y")}')
    print(f'  on_perx         : {sum(1 for e in entries if e["on_perx"]=="Y")}')
    print(f'  on_oat          : {sum(1 for e in entries if e["on_oat"]=="Y")}')
    print(f'  on_ponant       : {sum(1 for e in entries if e["on_ponant"]=="Y")}')

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
