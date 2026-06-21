#!/usr/bin/env python3
"""leader_loop.py — Persistent loop wrapper for supertimer leader.
Simulates systemd timer OnUnitActiveSec=60s in environments without systemctl.
"""
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
LEADER = str(ROOT / "supertimer/leader.py")
VENV = str(ROOT / ".venv/bin/python3")
LOG = str(ROOT / "logs/supertimer_leader_loop.log")


def log(msg: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} LEADER_LOOP {msg}\n"
    sys.stdout.write(line)
    sys.stdout.flush()
    with open(LOG, "a") as f:
        f.write(line)


def main() -> None:
    log("START — running leader.py every 60s")
    tick = 0
    while True:
        tick += 1
        try:
            proc = subprocess.run(
                [VENV, LEADER],
                cwd=str(ROOT),
                timeout=1400,
                capture_output=True,
                text=True,
            )
            if proc.returncode != 0:
                log(f"TICK {tick} FAIL rc={proc.returncode}: {(proc.stderr or proc.stdout or '')[:200]}")
            else:
                log(f"TICK {tick} OK")
        except subprocess.TimeoutExpired:
            log(f"TICK {tick} TIMEOUT after 1400s")
        except Exception as e:
            log(f"TICK {tick} ERROR: {e}")
        time.sleep(60)


if __name__ == "__main__":
    main()
