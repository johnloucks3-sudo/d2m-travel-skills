#!/usr/bin/env python3
"""CI probe: d2m-inbox-triage freshness. GREEN iff the triage cursor was
touched within the last 15 minutes (timer runs every 5 — 3 missed cycles = RED).

Exit 0 = GREEN, 1 = RED. Silent-sensor doctrine: a stale cursor must page,
never sit quiet (2026-07-04 incident: Commander mail sat 35+ min unseen).
"""
import sys
import time
from pathlib import Path

CURSOR = Path("/home/john/Thunderbird/OpsCenter/state/d2m_inbox_triage_cursor.json")
MAX_AGE_SEC = 15 * 60

if not CURSOR.exists():
    print("RED: triage cursor missing — d2m-inbox-triage has never run")
    sys.exit(1)

age = time.time() - CURSOR.stat().st_mtime
if age > MAX_AGE_SEC:
    print(f"RED: triage cursor stale {age/60:.0f} min (max 15) — d2m inbox is unswept")
    sys.exit(1)

print(f"GREEN: triage cursor fresh ({age/60:.1f} min old)")
sys.exit(0)
