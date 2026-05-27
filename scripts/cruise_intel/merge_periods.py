#!/usr/bin/env python3
"""
Cruise Intel — Multi-Period CSV Merger

Combines two or more tagged master CSVs (from run_pipeline.py --tag) into one
deduplicated, chronologically sorted master for multi-period reporting.

Dedup key: (norm_ship(ship_name), departure_date)
           — same vessel on same date is one sailing regardless of source period.

Usage:
  python3 merge_periods.py CSV1 CSV2 [CSV3 ...]
  python3 merge_periods.py CSV1 CSV2 --output output/T2_MASTER_ALL.csv
  python3 merge_periods.py output/T2_MASTER_2026-full.csv output/T2_MASTER_2027-h1.csv

Then generate the combined report:
  python3 generate_report.py --csv output/T2_MASTER_ALL.csv
"""
import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import OUTPUT_DIR, CSV_COLUMNS
from utils import norm_ship


def merge_csvs(input_paths: list[Path], output_path: Path) -> int:
    seen: set[tuple] = set()
    rows: list[dict] = []

    for csv_path in input_paths:
        if not csv_path.exists():
            print(f'  [merge] WARNING: {csv_path} not found — skipping', flush=True)
            continue
        with open(csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            file_rows = 0
            for row in reader:
                key = (norm_ship(row.get('ship_name', '')), row.get('departure_date', ''))
                if key not in seen:
                    seen.add(key)
                    rows.append(row)
                    file_rows += 1
        print(f'  [merge] {csv_path.name}: {file_rows} unique rows loaded', flush=True)

    # Sort by departure_date then cruise_line
    rows.sort(key=lambda r: (r.get('departure_date', ''), r.get('cruise_line', '')))

    # Determine column order — use CSV_COLUMNS if all present, else union of all headers
    all_keys: list[str] = list(CSV_COLUMNS)
    for row in rows:
        for k in row:
            if k not in all_keys:
                all_keys.append(k)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=all_keys, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)

    return len(rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Merge multiple tagged cruise master CSVs into one deduped file',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('inputs', nargs='+', type=Path,
                        help='Two or more tagged master CSV files to merge')
    parser.add_argument('--output', '-o', type=Path,
                        default=OUTPUT_DIR / 'T2_MASTER_ALL.csv',
                        help='Output path (default: output/T2_MASTER_ALL.csv)')
    args = parser.parse_args()

    if len(args.inputs) < 2:
        print('ERROR: need at least 2 input CSVs to merge', file=sys.stderr)
        sys.exit(1)

    print(f'[merge] Merging {len(args.inputs)} period CSVs → {args.output}')
    total = merge_csvs(args.inputs, args.output)
    print(f'[merge] Done — {total} unique sailings → {args.output}')
    print(f'[merge] Generate report: python3 generate_report.py --csv {args.output}')
