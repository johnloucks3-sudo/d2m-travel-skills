#!/usr/bin/env python3
"""
Cruise Intel Pipeline — One-Command Orchestrator  (Wave 3 — 10 sources)

Usage:
  python3 run_pipeline.py                              # Full run: Oct/Nov 2026
  python3 run_pipeline.py --months 10 11 12            # Add December
  python3 run_pipeline.py --year 2027                  # Different year
  python3 run_pipeline.py --tag 2026-full              # Named output: T2_MASTER_2026-full.csv
  python3 run_pipeline.py --skip-perx                  # Skip Perx (use cached)
  python3 run_pipeline.py --skip-oat                   # Skip OAT gstack (slow)
  python3 run_pipeline.py --skip-ponant                # Skip Ponant gstack (slow)
  python3 run_pipeline.py --skip-hx                    # Skip HX (use cached)
  python3 run_pipeline.py --skip-seadream              # Skip SeaDream gstack (use cached)
  python3 run_pipeline.py --skip-explora               # Skip Explora sitemap (use cached)
  python3 run_pipeline.py --skip-cruisemapper          # Skip CruiseMapper scrape (use cached)
  python3 run_pipeline.py --skip-cruisesonly           # Skip CruisesOnly gstack (use cached)
  python3 run_pipeline.py --skip-cruiseplum            # Skip CruisePlum gstack+login (use cached)
  python3 run_pipeline.py --build-only                 # Reassemble from existing JSONs

Multi-period example:
  python3 run_pipeline.py --year 2026 --months 7 8 9 10 11 12 --tag 2026-full --skip-cruiseplum
  python3 run_pipeline.py --year 2027 --months 1 2 3 4 5 6 7 8 9 --tag 2027-h1 --skip-cruiseplum
  python3 merge_periods.py output/T2_MASTER_2026-full.csv output/T2_MASTER_2027-h1.csv

NOTE: deluxecruises.com scraping requires manual gstack session.
      Run scrape_deluxecruises.py separately or use existing JSON.
NOTE: CruisePlum requires credentials. Set CRUISEPLUM_USER + CRUISEPLUM_PASS env vars
      or create ~/.config/d2m/cruiseplum.env with USER=... / PASS=... lines.
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import (
    OUTPUT_DIR, MASTER_CSV, STATS_JSON,
    DELUXE_JSON, PERX_JSON, OAT_JSON, PONANT_CLEAN_JSON, PONANT_RAW_JSON,
    HX_JSON, SEADREAM_JSON, EXPLORA_JSON,
    CRUISEMAPPER_JSON, CRUISESONLY_JSON, CRUISEPLUM_JSON,
    GSTACK_BIN,
)
from progress import StepTracker, SummaryTable, header as prog_header


def _load_cached(path: Path) -> int:
    """Return record count from cached JSON, or 0 if missing."""
    if path.exists():
        try:
            return len(json.loads(path.read_text()))
        except Exception:
            pass
    return 0


def run_pipeline(
    year: int,
    months: list,
    tag: str                 = '',
    skip_perx: bool          = False,
    skip_oat: bool           = False,
    skip_ponant: bool        = False,
    skip_hx: bool            = False,
    skip_seadream: bool      = False,
    skip_explora: bool       = False,
    skip_cruisemapper: bool  = False,
    skip_cruisesonly: bool   = False,
    skip_cruiseplum: bool    = False,
    build_only: bool         = False,
    skip_smoke: bool         = False,
    verbose: bool            = False,
    cruiseplum_user: str     = '',
    cruiseplum_pass: str     = '',
) -> None:
    # Resolve tagged output paths (or fall back to defaults)
    if tag:
        output_csv   = OUTPUT_DIR / f'T2_MASTER_{tag}.csv'
        output_stats = OUTPUT_DIR / f'T2_STATS_{tag}.json'
    else:
        output_csv   = MASTER_CSV
        output_stats = STATS_JSON

    table = SummaryTable()
    prog_header(year, months)
    if tag:
        print(f'  Tag: {tag}  →  {output_csv.name}')

    TOTAL = 10

    # ── STEP 1: Perx ─────────────────────────────────────────────────────────
    with StepTracker(1, TOTAL, 'Perx.com  (sail-personalize.com REST API)',
                     'perx', skipped=(skip_perx or build_only)) as t:
        if skip_perx or build_only:
            t.records = _load_cached(PERX_JSON)
            t.note = str(PERX_JSON.name)
        else:
            from scrape_perx import scrape_perx
            results = scrape_perx(
                year=year, months=months,
                output_path=PERX_JSON,
                filter_region=True,
                verbose=verbose,
            )
            t.records = len(results)
    table.add('perx', 'Perx.com', t.records, 0, 0, skip_perx or build_only, 'W1')

    # ── STEP 2: OAT ──────────────────────────────────────────────────────────
    with StepTracker(2, TOTAL, 'OAT  (oattravel.com — gstack browser)',
                     'oat', skipped=(skip_oat or build_only)) as t:
        if skip_oat or build_only:
            t.records = _load_cached(OAT_JSON)
            t.note = str(OAT_JSON.name)
        elif not GSTACK_BIN.exists():
            t.note = 'gstack binary not found — skipped'
            t.records = _load_cached(OAT_JSON)
        else:
            from scrape_oat import scrape_oat
            results = scrape_oat(
                year=year, months=months,
                output_path=OAT_JSON,
                verbose=verbose,
            )
            t.records = len(results)
    table.add('oat', 'OAT', t.records, 0, 0, skip_oat or build_only, 'W1')

    # ── STEP 3: Ponant ────────────────────────────────────────────────────────
    with StepTracker(3, TOTAL, 'PONANT  (us.ponant.com — gstack browser)',
                     'ponant', skipped=(skip_ponant or build_only)) as t:
        if skip_ponant or build_only:
            t.records = _load_cached(PONANT_CLEAN_JSON)
            t.note = str(PONANT_CLEAN_JSON.name)
        elif not GSTACK_BIN.exists():
            t.note = 'gstack binary not found — skipped'
            t.records = _load_cached(PONANT_CLEAN_JSON)
        else:
            from scrape_ponant import scrape_ponant
            scrape_ponant(
                year=year, months=months,
                raw_output=PONANT_RAW_JSON,
                clean_output=PONANT_CLEAN_JSON,
                verbose=verbose,
            )
            t.records = _load_cached(PONANT_CLEAN_JSON)
    table.add('ponant', 'PONANT', t.records, 0, 0, skip_ponant or build_only, 'W1')

    # ── STEP 4: HX Expeditions ───────────────────────────────────────────────
    with StepTracker(4, TOTAL, 'HX Expeditions  (travelhx.com — __NEXT_DATA__)',
                     'hx', skipped=(skip_hx or build_only)) as t:
        if skip_hx or build_only:
            t.records = _load_cached(HX_JSON)
            t.note = str(HX_JSON.name)
        else:
            from scrape_hx import scrape_hx
            results = scrape_hx(
                year=year, months=months,
                output_path=HX_JSON,
                verbose=verbose,
            )
            t.records = len(results)
    table.add('hx', 'HX Expeditions', t.records, 0, 0, skip_hx or build_only, 'W2')

    # ── STEP 5: SeaDream Yacht Club ───────────────────────────────────────────
    with StepTracker(5, TOTAL, 'SeaDream Yacht Club  (seadream.com — gstack browser)',
                     'seadream', skipped=(skip_seadream or build_only)) as t:
        if skip_seadream or build_only:
            t.records = _load_cached(SEADREAM_JSON)
            t.note = str(SEADREAM_JSON.name)
        elif not GSTACK_BIN.exists():
            t.note = 'gstack binary not found — skipped'
            t.records = _load_cached(SEADREAM_JSON)
        else:
            from scrape_seadream import scrape_seadream
            results = scrape_seadream(
                year=year, months=months,
                output_path=SEADREAM_JSON,
                verbose=verbose,
            )
            t.records = len(results)
    table.add('seadream', 'SeaDream', t.records, 0, 0, skip_seadream or build_only, 'W2')

    # ── STEP 6: Explora Journeys ──────────────────────────────────────────────
    with StepTracker(6, TOTAL, 'Explora Journeys  (explorajourneys.com — sitemap)',
                     'explora', skipped=(skip_explora or build_only)) as t:
        if skip_explora or build_only:
            t.records = _load_cached(EXPLORA_JSON)
            t.note = str(EXPLORA_JSON.name)
        else:
            from scrape_explora import scrape_explora
            results = scrape_explora(
                year=year, months=months,
                output_path=EXPLORA_JSON,
                verbose=verbose,
            )
            t.records = len(results)
    table.add('explora', 'Explora Journeys', t.records, 0, 0, skip_explora or build_only, 'W2')

    # ── STEP 7: CruiseMapper ─────────────────────────────────────────────────
    with StepTracker(7, TOTAL, 'CruiseMapper  (cruisemapper.com — requests+BS4)',
                     'cruisemapper', skipped=(skip_cruisemapper or build_only)) as t:
        if skip_cruisemapper or build_only:
            t.records = _load_cached(CRUISEMAPPER_JSON)
            t.note = str(CRUISEMAPPER_JSON.name)
        else:
            from scrape_cruisemapper import scrape_cruisemapper
            results = scrape_cruisemapper(
                year=year, months=months,
                output_path=CRUISEMAPPER_JSON,
                verbose=verbose,
            )
            t.records = len(results)
    table.add('cruisemapper', 'CruiseMapper', t.records, 0, 0,
              skip_cruisemapper or build_only, 'W3')

    # ── STEP 8: CruisesOnly ───────────────────────────────────────────────────
    with StepTracker(8, TOTAL, 'CruisesOnly  (cruisesonly.com — gstack browser)',
                     'cruisesonly', skipped=(skip_cruisesonly or build_only)) as t:
        if skip_cruisesonly or build_only:
            t.records = _load_cached(CRUISESONLY_JSON)
            t.note = str(CRUISESONLY_JSON.name)
        elif not GSTACK_BIN.exists():
            t.note = 'gstack binary not found — skipped'
            t.records = _load_cached(CRUISESONLY_JSON)
        else:
            from scrape_cruisesonly import scrape_cruisesonly
            try:
                results = scrape_cruisesonly(
                    year=year, months=months,
                    output_path=CRUISESONLY_JSON,
                    verbose=verbose,
                )
                t.records = len(results)
            except RuntimeError as e:
                t.note = f'scrape failed: {e} — falling back to cache'
                t.records = _load_cached(CRUISESONLY_JSON)
    table.add('cruisesonly', 'CruisesOnly', t.records, 0, 0,
              skip_cruisesonly or build_only, 'W3')

    # ── STEP 9: CruisePlum ────────────────────────────────────────────────────
    with StepTracker(9, TOTAL, 'CruisePlum  (cruiseplum.com — gstack + login)',
                     'cruiseplum', skipped=(skip_cruiseplum or build_only)) as t:
        if skip_cruiseplum or build_only:
            t.records = _load_cached(CRUISEPLUM_JSON)
            t.note = str(CRUISEPLUM_JSON.name)
        elif not GSTACK_BIN.exists():
            t.note = 'gstack binary not found — skipped'
            t.records = _load_cached(CRUISEPLUM_JSON)
        else:
            from scrape_cruiseplum import scrape_cruiseplum
            try:
                results = scrape_cruiseplum(
                    year=year, months=months,
                    output_path=CRUISEPLUM_JSON,
                    username=cruiseplum_user,
                    password=cruiseplum_pass,
                    verbose=verbose,
                )
                t.records = len(results)
            except RuntimeError as e:
                t.note = f'credentials not configured — use --skip-cruiseplum or set creds'
                t.records = _load_cached(CRUISEPLUM_JSON)
    table.add('cruiseplum', 'CruisePlum', t.records, 0, 0,
              skip_cruiseplum or build_only, 'W3')

    # ── STEP 10: Build master ─────────────────────────────────────────────────
    with StepTracker(10, TOTAL, 'Build master CSV  (10-source merge + smoke check)',
                     'build') as t:
        from build_master import build_master
        entries = build_master(
            deluxe_path=DELUXE_JSON,
            perx_path=PERX_JSON,
            oat_path=OAT_JSON,
            ponant_path=PONANT_CLEAN_JSON,
            hx_path=HX_JSON,
            seadream_path=SEADREAM_JSON,
            explora_path=EXPLORA_JSON,
            cruisemapper_path=CRUISEMAPPER_JSON,
            cruisesonly_path=CRUISESONLY_JSON,
            cruiseplum_path=CRUISEPLUM_JSON,
            output_csv=output_csv,
            stats_path=output_stats,
            skip_smoke=skip_smoke,
        )
        t.records = len(entries)

    # ── Final summary table ───────────────────────────────────────────────────
    if entries:
        def fc(col):
            return sum(1 for e in entries if e.get(col) == 'Y')

        ALL_FLAGS = (
            'on_deluxecruises','on_perx','on_oat','on_ponant',
            'on_hx','on_seadream','on_explora',
            'on_cruisemapper','on_cruisesonly','on_cruiseplum',
        )
        W1_FLAGS = ('on_deluxecruises','on_perx','on_oat','on_ponant')
        W2_FLAGS = ('on_hx','on_seadream','on_explora')
        W3_FLAGS = ('on_cruisemapper','on_cruisesonly','on_cruiseplum')
        multi_source = sum(
            1 for e in entries
            if sum(1 for c in ALL_FLAGS if e.get(c) == 'Y') >= 2
        )
        wave2_net_new = sum(
            1 for e in entries
            if any(e.get(c) == 'Y' for c in W2_FLAGS)
            and all(e.get(c) != 'Y' for c in W1_FLAGS)
        )
        wave3_net_new = sum(
            1 for e in entries
            if any(e.get(c) == 'Y' for c in W3_FLAGS)
            and all(e.get(c) != 'Y' for c in W1_FLAGS + W2_FLAGS)
        )
        lines = len(set(e['cruise_line'] for e in entries if e['cruise_line']))

        # Update summary table with actual cross-match/net-new from entries
        counts = {
            'perx':         (fc('on_perx'), 0),
            'oat':          (fc('on_oat'), 0),
            'ponant':       (fc('on_ponant'), 0),
            'hx':           (fc('on_hx'), 0),
            'seadream':     (fc('on_seadream'), 0),
            'explora':      (fc('on_explora'), 0),
            'cruisemapper': (fc('on_cruisemapper'), 0),
            'cruisesonly':  (fc('on_cruisesonly'), 0),
            'cruiseplum':   (fc('on_cruiseplum'), 0),
        }
        for row in table._rows:
            k = row['key']
            if k in counts:
                row['records'] = counts[k][0]

        table.print(
            total_unique=len(entries),
            total_lines=lines,
            multi_source=multi_source,
            wave2_net_new=wave2_net_new,
            wave3_net_new=wave3_net_new,
        )

    print(f'  Master CSV  : {output_csv}')
    print(f'  Stats JSON  : {output_stats}')
    print()
    print(f'  NOTE: deluxecruises.com must be pre-scraped.')
    print(f'  Expected at : {DELUXE_JSON}')
    print()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Cruise Intel Pipeline — full scrape + assemble (10 sources)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('--year',               type=int, default=2026)
    parser.add_argument('--months',             nargs='+', type=int, default=[10, 11],
                        help='Month numbers (default: 10 11)')
    parser.add_argument('--tag',                default='',
                        help='Named output tag (e.g. 2026-full → T2_MASTER_2026-full.csv)')
    parser.add_argument('--skip-perx',          action='store_true',
                        help='Skip Perx API call, use cached JSON')
    parser.add_argument('--skip-oat',           action='store_true',
                        help='Skip OAT gstack scrape, use cached JSON')
    parser.add_argument('--skip-ponant',        action='store_true',
                        help='Skip Ponant gstack scrape, use cached JSON')
    parser.add_argument('--skip-hx',            action='store_true',
                        help='Skip HX Expeditions Next.js scrape, use cached JSON')
    parser.add_argument('--skip-seadream',      action='store_true',
                        help='Skip SeaDream gstack scrape, use cached JSON')
    parser.add_argument('--skip-explora',       action='store_true',
                        help='Skip Explora sitemap scrape, use cached JSON')
    parser.add_argument('--skip-cruisemapper',  action='store_true',
                        help='Skip CruiseMapper requests scrape, use cached JSON')
    parser.add_argument('--skip-cruisesonly',   action='store_true',
                        help='Skip CruisesOnly gstack scrape, use cached JSON')
    parser.add_argument('--skip-cruiseplum',    action='store_true',
                        help='Skip CruisePlum gstack+login scrape, use cached JSON')
    parser.add_argument('--cruiseplum-user',    default='',
                        help='CruisePlum login email (overrides env/file)')
    parser.add_argument('--cruiseplum-pass',    default='',
                        help='CruisePlum login password (overrides env/file)')
    parser.add_argument('--build-only',         action='store_true',
                        help='Skip all scraping, only reassemble master CSV')
    parser.add_argument('--skip-smoke',         action='store_true')
    parser.add_argument('--verbose',            action='store_true')
    args = parser.parse_args()

    run_pipeline(
        year=args.year,
        months=args.months,
        tag=args.tag,
        skip_perx=args.skip_perx,
        skip_oat=args.skip_oat,
        skip_ponant=args.skip_ponant,
        skip_hx=args.skip_hx,
        skip_seadream=args.skip_seadream,
        skip_explora=args.skip_explora,
        skip_cruisemapper=args.skip_cruisemapper,
        skip_cruisesonly=args.skip_cruisesonly,
        skip_cruiseplum=args.skip_cruiseplum,
        cruiseplum_user=args.cruiseplum_user,
        cruiseplum_pass=args.cruiseplum_pass,
        build_only=args.build_only,
        skip_smoke=args.skip_smoke,
        verbose=args.verbose,
    )
