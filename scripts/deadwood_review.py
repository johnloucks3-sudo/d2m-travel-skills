#!/usr/bin/env python3
"""
Deadwood Review Cycles (1m/3m/6m/9m)
Surfaces candidates for removal, logs to hale_decisions.md for Sterling audit.
"""
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

CYCLE = sys.argv[1] if len(sys.argv) > 1 else "1month"
HALE_DECISIONS = Path.home() / "Thunderbird" / "hale_decisions.md"

CYCLES = {
    "1month": {"days": 30, "label": "1-MONTH"},
    "3month": {"days": 90, "label": "3-MONTH"},
    "6month": {"days": 180, "label": "6-MONTH"},
    "9month": {"days": 270, "label": "9-MONTH"},
}

def main():
    cycle_info = CYCLES.get(CYCLE, CYCLES["1month"])

    # Log review trigger
    with open(HALE_DECISIONS, 'a') as f:
        f.write(f"\n## {datetime.now().strftime('%Y-%m-%d %H:%M')} — DEADWOOD REVIEW ({cycle_info['label']})\n")
        f.write(f"**Cycle:** {cycle_info['label']} review\n")
        f.write(f"**Gate date:** {cycle_info['days']} days post-ship\n")
        f.write(f"**Owner:** Sterling (A7) — audit usage, test coverage, maintenance cost\n")
        f.write(f"**Candidates:** [staged for Sterling review]\n")
        f.write(f"**Status:** AWAITING STERLING AUDIT\n")

    print(f"✓ {cycle_info['label']} deadwood review triggered. Sterling to audit.")

if __name__ == '__main__':
    main()
