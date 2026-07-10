#!/usr/bin/env python3
"""
ELON Proposal Weekly Closure Review (Sunday 18:00 MT)
Scans open proposals against closure targets, archives completed ones, updates metrics.
"""
import json
import os
from pathlib import Path
from datetime import datetime
import re

PROPOSALS_DIR = Path.home() / "Thunderbird" / "OpsCenter" / "elon_proposals"
CLOSED_DIR = PROPOSALS_DIR / "CLOSED"
HALE_STATE = Path.home() / "Thunderbird" / "hale_state.json"
HALE_DECISIONS = Path.home() / "Thunderbird" / "hale_decisions.md"

def main():
    # Ensure CLOSED directory exists
    CLOSED_DIR.mkdir(exist_ok=True)

    # Load hale_state.json
    try:
        with open(HALE_STATE) as f:
            state = json.load(f)
    except:
        state = {"elon_proposals": {}}

    # Scan proposals
    proposals = {}
    for f in PROPOSALS_DIR.glob("PROPOSAL-*.md"):
        match = re.search(r'PROPOSAL-(\d{8})-(.+)\.md', f.name)
        if not match:
            continue
        date_str, system = match.groups()

        # Check for EXECUTION doc (marker of completion)
        exec_file = PROPOSALS_DIR / f"{system.upper()}_EXECUTION.md".replace('-', '_').upper()
        exec_file = next(PROPOSALS_DIR.glob(f"*_{system.upper()}_EXECUTION.md"), None) or \
                    next(PROPOSALS_DIR.glob(f"*{system}*EXECUTION.md"), None)

        is_completed = exec_file and exec_file.exists()
        proposals[system] = {
            'date': date_str,
            'completed': is_completed,
            'file': f.name
        }

    # Update metrics
    active = sum(1 for p in proposals.values() if not p['completed'])
    closed = len(proposals) - active

    state['elon_proposals'] = {
        'active': active,
        'closed_this_review': closed,
        'last_review': datetime.now().isoformat(),
        'total_in_cycle': len(proposals)
    }

    # Write updated state
    with open(HALE_STATE, 'w') as f:
        json.dump(state, f, indent=2)

    # Log to hale_decisions.md
    with open(HALE_DECISIONS, 'a') as f:
        f.write(f"\n## {datetime.now().strftime('%Y-%m-%d %H:%M')} — ELON Weekly Review\n")
        f.write(f"Scanned: {len(proposals)} proposals | Active: {active} | Closed: {closed}\n")

    print(f"✓ ELON weekly review: {active} active, {closed} completed")

if __name__ == '__main__':
    main()
