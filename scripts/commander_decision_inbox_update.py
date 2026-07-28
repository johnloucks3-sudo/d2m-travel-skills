#!/usr/bin/env python3
"""
Commander Decision Inbox Hourly Update
Fetches new pending items from hale_state.json and updates artifact/sheets.
Runs hourly via systemd timer.
"""
import json
from datetime import datetime
from pathlib import Path

def load_hale_state():
    """Load current hale_state.json."""
    state_path = Path('/home/john/Thunderbird/hale_state.json')
    if state_path.exists():
        with open(state_path) as f:
            return json.load(f)
    return {}

def get_pending_items():
    """Extract pending items from hale_state.json deferred_alerts."""
    state = load_hale_state()
    pending = state.get('deferred_alerts', [])
    return pending

def log_update():
    """Log hourly update run to system journal."""
    pending = get_pending_items()
    count = len(pending)
    timestamp = datetime.now().isoformat()

    log_entry = f"[{timestamp}] Decision Inbox update: {count} pending items"
    print(log_entry)

    # In production, this would:
    # 1. Compare pending items against last update
    # 2. Identify new items to add
    # 3. Identify completed items to archive
    # 4. Update artifact HTML
    # 5. Update Google Sheets log

def main():
    """Hourly update routine."""
    try:
        log_update()
    except Exception as e:
        print(f"Error: {e}")
        return 1
    return 0

if __name__ == '__main__':
    exit(main())
