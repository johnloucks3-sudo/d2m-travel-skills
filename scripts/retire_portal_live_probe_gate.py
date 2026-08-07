#!/usr/bin/env python3
"""retire_portal_live_probe_gate.py — Commander-authorized removal gate.

Commander 2026-08-07: KEEP d2m-portal-live-probe, but IF it errors once more,
its removal is AUTHORIZED. This watchdog checks the last hour of journal; on a
failure it disables the unit and logs the removal to OpsCenter/meetroom/RT-KEEPALIVES/.
Safe: never re-enables; one-shot per failure window.
"""
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

UNIT = "d2m-portal-live-probe"
LOG = Path("/home/john/Thunderbird/OpsCenter/meetroom/RT-KEEPALIVES/live_probe_gate.md")

def sh(cmd: str) -> str:
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout

def main():
    now = datetime.now(timezone(timedelta(hours=-6))).strftime("%Y-%m-%d %H:%M MT")
    # failure signature: a REAL error in the probe's journal output. Oneshot
    # units read "inactive/active"=completed-normally, so is-active is NOT a
    # signal — errs>0 is the ONLY trigger (fix 2026-08-07 gate).
    errs = int(sh(f"journalctl --user -u {UNIT} --since '1 hour ago' | grep -icE 'Failed with result|status=1|ERROR|exception|Traceback'").strip() or "0")
    LOG.parent.mkdir(parents=True, exist_ok=True)
    if errs == 0:
        with open(LOG, "a") as f:
            f.write(f"- {now} | gate: clean (errs=0) — KEEP\n")
        print("KEEP")
        return
    # authorized removal (Commander directive 2026-08-07)
    sh(f"systemctl --user disable --now {UNIT}")
    with open(LOG, "a") as f:
        f.write(f"- {now} | GATE FIRED: error detected (errs={errs}) — AUTHORIZED REMOVAL of {UNIT} (Commander 2026-08-07)\n")
    sh(f"python3 /home/john/Thunderbird/OpsCenter/mission_board_sync.py add 'd2m-portal-live-probe REMOVED by gate' 'Authorized removal on first post-2026-08-07 error. See RT-KEEPALIVES/live_probe_gate.md.' P2 >/dev/null 2>&1")
    print(f"GATE FIRED — {UNIT} removed (errs={errs})")

if __name__ == "__main__":
    main()