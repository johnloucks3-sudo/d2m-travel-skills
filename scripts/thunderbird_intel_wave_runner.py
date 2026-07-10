#!/usr/bin/env python3
"""
THUNDERBIRD INTEL WAVE RUNNER — 22:00 Daily
=============================================
Merged dispatch: Innovation Scanner (daily) + Nightly Tech Harvest.
Runs sequentially. Output lands in intel/ directory for AM digest pickup.

Schedule: systemd timer thunderbird-intel-wave.timer @ 22:00 MT
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOG = LOG_DIR / f"intel_wave_{datetime.now().strftime('%Y%m%d')}.log"


def log(msg: str):
    ts = datetime.now().isoformat()
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def run_step(label: str, cmd: list) -> bool:
    log(f"START {label}")
    try:
        r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=300)
        if r.returncode == 0:
            log(f"OK {label}")
            return True
        else:
            log(f"FAIL {label} (exit {r.returncode}): {r.stderr.strip()[-200:]}")
            return False
    except subprocess.TimeoutExpired:
        log(f"TIMEOUT {label}")
        return False
    except Exception as e:
        log(f"ERROR {label}: {e}")
        return False


def main():
    log("=== INTEL WAVE START ===")

    # Step 1: Innovation Scanner daily quick scan
    run_step("INNOVATION_SCAN_DAILY", [
        sys.executable,
        str(ROOT / "core" / "intel" / "thunderbird_innovation_scanner.py"),
        "daily"
    ])

    # Step 2: Nightly Tech Harvest
    run_step("TECH_HARVEST", [
        sys.executable,
        str(ROOT / "core" / "intel" / "thunderbird_nightly_tech_harvest.py")
    ])

    log("=== INTEL WAVE END ===")


if __name__ == "__main__":
    main()
