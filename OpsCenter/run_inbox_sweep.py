#!/usr/bin/env python3
"""
run_inbox_sweep.py — Scheduled Commander Inbox Sweep
=====================================================
Called by systemd timer every 4 hours.
Wraps thunderbird_commander_inbox.run_commander_inbox_sweep().
The sweep handles Telegram notification to COS/Commander internally.
"""
import sys
from pathlib import Path

# Add all core paths
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
for sub in (ROOT / "core").iterdir():
    if sub.is_dir():
        sys.path.insert(0, str(sub))

from thunderbird_commander_inbox import run_commander_inbox_sweep

result = run_commander_inbox_sweep(hours_back=0.25)  # 15-min lookback for 2-min scanner
print(f"[inbox_sweep] scanned={result.get('emails_scanned', 0)} "
      f"tasked={result.get('tasked', 0)} "
      f"drafted={result.get('drafted', 0)} "
      f"status={result.get('status', '?')}")
sys.exit(0 if result.get("status") not in ("error",) else 1)
