#!/usr/bin/env python3
"""CLI: run the birthday/anniversary trip suggestion engine.

Usage:
    python3 scripts/run_milestone_suggestions.py                # live run, sends digest
    python3 scripts/run_milestone_suggestions.py --dry-run       # no email send
    python3 scripts/run_milestone_suggestions.py --date 2026-08-01

Scheduled monthly (1st, 09:00 MT) via deploy/d2m-milestone-suggestions.timer.
"""
import argparse
import logging
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.client.thunderbird_milestone_matcher import run_monthly_scan

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="Override 'today' as YYYY-MM-DD (for testing/backfill)")
    parser.add_argument("--dry-run", action="store_true", help="Skip sending the internal digest email")
    args = parser.parse_args()

    today = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else date.today()

    result = run_monthly_scan(today=today, send_digest=not args.dry_run)
    print(f"Clients found: {result['clients_found']}")
    print(f"Voyages considered: {result['voyages_considered']}")
    print(f"Suggestions generated: {len(result['suggestions'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
