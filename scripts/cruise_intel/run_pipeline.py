#!/usr/bin/env python3
"""
Cruise Intel Pipeline — One-Command Orchestrator

Usage:
  python3 run_pipeline.py                          # Full run: Oct/Nov 2026
  python3 run_pipeline.py --months 10 11 12        # Add December
  python3 run_pipeline.py --year 2027              # Different year
  python3 run_pipeline.py --skip-perx              # Skip Perx API (use cached)
  python3 run_pipeline.py --skip-oat               # Skip OAT gstack (slow)
  python3 run_pipeline.py --skip-ponant            # Skip Ponant gstack (slow)
  python3 run_pipeline.py --build-only             # Reassemble from existing JSONs

NOTE: deluxecruises.com scraping requires manual gstack session (JS-rendered pages).
      Run scrape_deluxecruises.py separately or use existing T2_EXERCISE_DEMBE_CRUISE_INTELLIGENCE.json.
"""
import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import (
    OUTPUT_DIR, MASTER_CSV, STATS_JSON,
    DELUXE_JSON, PERX_JSON, OAT_JSON, PONANT_CLEAN_JSON, PONANT_RAW_JSON,
    GSTACK_BIN,
)


def ts() -> str:
    return datetime.now().strftime('%H:%M:%S')


def step(label: str) -> None:
    print(f'\n[{ts()}] ══ {label} ══')


def run_pipeline(
    year: int,
    months: list,
    skip_perx: bool   = False,
    skip_oat: bool    = False,
    skip_ponant: bool = False,
    build_only: bool  = False,
    skip_smoke: bool  = False,
    verbose: bool     = False,
) -> None:
    start = time.time()
    month_labels = {1:'Jan',2:'Feb',3:'Mar',4:'Apr',5:'May',6:'Jun',
                    7:'Jul',8:'Aug',9:'Sep',10:'Oct',11:'Nov',12:'Dec'}
    months_str = '+'.join(month_labels.get(m, str(m)) for m in months)

    print(f'\n╔══════════════════════════════════════════════════╗')
    print(f'║  CRUISE INTEL PIPELINE — {year} {months_str:<22}║')
    print(f'╚══════════════════════════════════════════════════╝')

    # ── Step 1: Perx ──────────────────────────────────────────────────────────
    if not (skip_perx or build_only):
        step('STEP 1/4 — Perx.com (sail-personalize.com API)')
        from scrape_perx import scrape_perx
        scrape_perx(
            year=year, months=months,
            output_path=PERX_JSON,
            filter_region=True,
            verbose=verbose,
        )
    else:
        step('STEP 1/4 — Perx: SKIPPED (using cached)')
        if PERX_JSON.exists():
            import json
            count = len(json.loads(PERX_JSON.read_text()))
            print(f'  Cached: {count} records at {PERX_JSON}')
        else:
            print(f'  WARNING: No cached Perx data at {PERX_JSON}')

    # ── Step 2: OAT ───────────────────────────────────────────────────────────
    if not (skip_oat or build_only):
        step('STEP 2/4 — OAT.com (gstack browser)')
        if not GSTACK_BIN.exists():
            print(f'  ERROR: gstack binary not found. Skipping OAT.')
            print(f'  Run: cd ~/.claude/skills/gstack && ./setup')
        else:
            from scrape_oat import scrape_oat
            scrape_oat(
                year=year, months=months,
                output_path=OAT_JSON,
                verbose=verbose,
            )
    else:
        step('STEP 2/4 — OAT: SKIPPED (using cached)')
        if OAT_JSON.exists():
            import json
            count = len(json.loads(OAT_JSON.read_text()))
            print(f'  Cached: {count} records at {OAT_JSON}')

    # ── Step 3: Ponant ────────────────────────────────────────────────────────
    if not (skip_ponant or build_only):
        step('STEP 3/4 — Ponant.com (gstack browser)')
        if not GSTACK_BIN.exists():
            print(f'  ERROR: gstack binary not found. Skipping Ponant.')
        else:
            from scrape_ponant import scrape_ponant
            scrape_ponant(
                year=year, months=months,
                raw_output=PONANT_RAW_JSON,
                clean_output=PONANT_CLEAN_JSON,
                verbose=verbose,
            )
    else:
        step('STEP 3/4 — Ponant: SKIPPED (using cached)')
        if PONANT_CLEAN_JSON.exists():
            import json
            count = len(json.loads(PONANT_CLEAN_JSON.read_text()))
            print(f'  Cached: {count} records at {PONANT_CLEAN_JSON}')

    # ── Step 4: Build master ──────────────────────────────────────────────────
    step('STEP 4/4 — Build master CSV')
    from build_master import build_master
    build_master(
        deluxe_path=DELUXE_JSON,
        perx_path=PERX_JSON,
        oat_path=OAT_JSON,
        ponant_path=PONANT_CLEAN_JSON,
        output_csv=MASTER_CSV,
        stats_path=STATS_JSON,
        skip_smoke=skip_smoke,
    )

    elapsed = int(time.time() - start)
    mins, secs = divmod(elapsed, 60)
    print(f'\n╔══════════════════════════════════════════════════╗')
    print(f'║  PIPELINE COMPLETE  [{mins}m {secs:02d}s]')
    print(f'╠══════════════════════════════════════════════════╣')
    print(f'║  Master CSV : {str(MASTER_CSV)[-50:]}')
    print(f'║  Stats JSON : {str(STATS_JSON)[-50:]}')
    print(f'╚══════════════════════════════════════════════════╝')

    print('\n  NOTE: deluxecruises.com data must be pre-scraped.')
    print(f'  Expected at: {DELUXE_JSON}')
    print('  Run scrape_deluxecruises.py for a fresh scrape.\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Cruise Intel Pipeline — full scrape + assemble',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('--year',         type=int, default=2026)
    parser.add_argument('--months',       nargs='+', type=int, default=[10, 11],
                        help='Month numbers (default: 10 11)')
    parser.add_argument('--skip-perx',    action='store_true',
                        help='Skip Perx API call, use cached JSON')
    parser.add_argument('--skip-oat',     action='store_true',
                        help='Skip OAT gstack scrape, use cached JSON')
    parser.add_argument('--skip-ponant',  action='store_true',
                        help='Skip Ponant gstack scrape, use cached JSON')
    parser.add_argument('--build-only',   action='store_true',
                        help='Skip all scraping, only reassemble master CSV')
    parser.add_argument('--skip-smoke',   action='store_true')
    parser.add_argument('--verbose',      action='store_true')
    args = parser.parse_args()

    run_pipeline(
        year=args.year,
        months=args.months,
        skip_perx=args.skip_perx,
        skip_oat=args.skip_oat,
        skip_ponant=args.skip_ponant,
        build_only=args.build_only,
        skip_smoke=args.skip_smoke,
        verbose=args.verbose,
    )
