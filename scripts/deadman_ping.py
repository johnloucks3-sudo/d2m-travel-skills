#!/usr/bin/env python3
"""deadman_ping.py — deadman heartbeat for keepalive timers (RT-KEEPALIVES).

Healthchecks.io-style deadman: on success, timers ping the deadman; alerts fire
ONLY when a timer goes silent >2h (per AG's NEW-software ADOPT verdict).
Local-first: writes a heartbeat stamp to OpsCenter/deadman/{name}.stamp AND
pings an optional external Healthchecks.io URL (DEADMAN_URL in OpsCenter/config
or env). No deadman URL configured → local heartbeat only.

Usage:
  deadman_ping.py <timer-name>          # success ping
  deadman_ping.py check <timer-name> [max_age_h=2]   # exit 1 if stale
"""
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

STAMP_DIR = Path("/home/john/Thunderbird/OpsCenter/deadman")
MT = timezone(timedelta(hours=-6))

def _deadman_url() -> str:
    for cand in (os.environ.get("DEADMAN_URL"),
                 (Path("/home/john/Thunderbird/OpsCenter/config.py").read_text()
                  if Path("/home/john/Thunderbird/OpsCenter/config.py").exists() else "")):
        if isinstance(cand, str) and "http" in cand:
            import re
            m = re.search(r"DEADMAN_URL\s*=\s*[\"']([^\"']+)", cand)
            if m:
                return m.group(1)
    return ""

def ping(name: str) -> None:
    STAMP_DIR.mkdir(parents=True, exist_ok=True)
    (STAMP_DIR / f"{name}.stamp").write_text(datetime.now(MT).isoformat(timespec="seconds"))
    url = _deadman_url()
    if url:
        try:
            import requests
            requests.get(url, timeout=10)
        except Exception:
            pass

def check(name: str, max_age_h: float) -> int:
    fp = STAMP_DIR / f"{name}.stamp"
    if not fp.exists():
        return 1
    try:
        age_h = (datetime.now(MT) - datetime.fromisoformat(fp.read_text().strip())
                 .replace(tzinfo=MT)).total_seconds() / 3600
    except Exception:
        return 1
    return 0 if age_h <= max_age_h else 1

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(2)
    if sys.argv[1] == "check":
        name = sys.argv[2]
        max_h = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0
        sys.exit(check(name, max_h))
    ping(sys.argv[1])
    print("pinged:", sys.argv[1])