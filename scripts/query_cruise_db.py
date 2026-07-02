#!/usr/bin/env python3
"""Query master cruise DB for client inquiries.

Usage:
    python3 scripts/query_cruise_db.py --destination "Mediterranean" --line "Silversea"
    python3 scripts/query_cruise_db.py --destination "Caribbean" --months "12 01" --limit 5
    python3 scripts/query_cruise_db.py --line "Regent" --months "05 06" --limit 10

Output: JSON array of matching sailings.
"""
import sqlite3
import argparse
import json
import sys
from pathlib import Path

DB = Path('/home/john/Thunderbird/data/master_cruise.db')


def get_table_name(conn):
    """Detect the actual table name in use."""
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    if not tables:
        return None
    # Prefer 'sailings', fall back to 'cruises' or first table
    for preferred in ('sailings', 'cruises', 'voyages'):
        if preferred in tables:
            return preferred
    return tables[0]


def search(destination=None, months=None, line=None, limit=10):
    if not DB.exists():
        return {"error": "master_cruise.db not found", "path": str(DB),
                "note": "DB needs to be populated via scripts/build_master_cruise_db.py"}

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    table = get_table_name(conn)
    if table is None:
        return {"error": "No tables in master_cruise.db",
                "note": "DB file exists but is empty — run scripts/build_master_cruise_db.py to populate"}

    # Build dynamic query
    q = f"SELECT * FROM {table} WHERE 1=1"
    params = []

    if destination:
        # Search across common text columns
        q += """ AND (
            destination LIKE ? OR ports LIKE ? OR itinerary_name LIKE ?
            OR ship_name LIKE ? OR embark_port LIKE ? OR debark_port LIKE ?
        )"""
        params += [f'%{destination}%'] * 6

    if line:
        q += " AND cruise_line LIKE ?"
        params.append(f'%{line}%')

    if months:
        month_list = months.split()
        # Handle month names and numbers
        month_map = {
            'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
            'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
            'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
        }
        normalized = []
        for m in month_list:
            if m.lower() in month_map:
                normalized.append(month_map[m.lower()])
            else:
                try:
                    normalized.append(f'{int(m):02d}')
                except ValueError:
                    pass

        if normalized:
            placeholders = ','.join('?' * len(normalized))
            # Try sail_date column first (ISO format); fall back to departure_date
            q += f" AND (strftime('%m', sail_date) IN ({placeholders}) OR strftime('%m', departure_date) IN ({placeholders}))"
            params += normalized * 2

    q += f" ORDER BY sail_date LIMIT {limit}"

    try:
        rows = conn.execute(q, params).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.OperationalError as e:
        # Column names may differ — return schema info
        schema_cur = conn.execute(f"PRAGMA table_info({table})")
        columns = [r[1] for r in schema_cur.fetchall()]
        return {"error": str(e), "table": table, "columns": columns,
                "note": "Query failed — column names may differ from expected schema"}


def main():
    p = argparse.ArgumentParser(
        description='Query master cruise DB for client inquiries',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --line "Silversea" --months "05 06" --limit 5
  %(prog)s --destination "Mediterranean" --line "Regent"
  %(prog)s --destination "Caribbean" --limit 20
"""
    )
    p.add_argument('--destination', help='Destination/port keyword (partial match)')
    p.add_argument('--months', help='Month numbers or names, space-separated (e.g. "05 06" or "may jun")')
    p.add_argument('--line', help='Cruise line name (partial match, e.g. "Silversea" or "Regent")')
    p.add_argument('--limit', type=int, default=10, help='Max results (default: 10)')
    p.add_argument('--pretty', action='store_true', help='Pretty-print JSON output')
    args = p.parse_args()

    if not any([args.destination, args.months, args.line]):
        p.print_help()
        print("\nError: provide at least one filter (--destination, --months, or --line)", file=sys.stderr)
        sys.exit(1)

    results = search(
        destination=args.destination,
        months=args.months,
        line=args.line,
        limit=args.limit
    )

    indent = 2 if args.pretty else None
    print(json.dumps(results, indent=indent, default=str))


if __name__ == '__main__':
    main()
