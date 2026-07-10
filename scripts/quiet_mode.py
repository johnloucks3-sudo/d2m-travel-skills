#!/usr/bin/env python3
"""quiet_mode.py — Thunderbird Wing CPU throttle toggle.

Writes/removes OpsCenter/quiet_mode.active sentinel.
- supertimer/leader.py: floors all bot intervals to 600s when active
- realtime_tracker.py:  sleeps 300s per scan instead of 60s when active
- thunderbird-health-check.timer: already at 5min (static, Tier 2)

Usage:
    python3 scripts/quiet_mode.py on       # activate quiet mode (engine idle)
    python3 scripts/quiet_mode.py off      # deactivate (session starting)
    python3 scripts/quiet_mode.py status   # print current state
    python3 scripts/quiet_mode.py toggle   # flip state

Called by:
    session_startup_hook.py → off  (session start, full cadence)
    supertimer/bots/ops_bot.py    → on   (no active session detected)
"""
from __future__ import annotations
import sys
import time
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
SENTINEL = ROOT / "OpsCenter/quiet_mode.active"
SESSION_MARKER = ROOT / "OpsCenter/session_active.marker"

QUIET_FLOOR_SEC = 600   # minimum bot interval in quiet mode
REALTIME_QUIET  = 300   # realtime_tracker sleep in quiet mode


def _is_active() -> bool:
    return SENTINEL.exists()


def activate(reason: str = "manual") -> None:
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    SENTINEL.write_text(f'{{"activated": "{ts}", "reason": "{reason}"}}\n')
    print(f"[quiet_mode] ON — bots floored at {QUIET_FLOOR_SEC}s, tracker at {REALTIME_QUIET}s ({reason})")


def deactivate(reason: str = "manual") -> None:
    if SENTINEL.exists():
        SENTINEL.unlink()
    print(f"[quiet_mode] OFF — full cadence restored ({reason})")


def status() -> None:
    if _is_active():
        data = SENTINEL.read_text().strip()
        print(f"[quiet_mode] ACTIVE — {data}")
        print(f"  bot floor:      {QUIET_FLOOR_SEC}s")
        print(f"  tracker sleep:  {REALTIME_QUIET}s")
    else:
        print("[quiet_mode] OFF — full cadence")


def toggle() -> None:
    if _is_active():
        deactivate("toggle")
    else:
        activate("toggle")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "on":
        activate(sys.argv[2] if len(sys.argv) > 2 else "manual")
    elif cmd == "off":
        deactivate(sys.argv[2] if len(sys.argv) > 2 else "manual")
    elif cmd == "toggle":
        toggle()
    elif cmd == "status":
        status()
    else:
        print(f"Usage: quiet_mode.py on|off|toggle|status", file=sys.stderr)
        sys.exit(1)
