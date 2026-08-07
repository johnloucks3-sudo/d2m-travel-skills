#!/usr/bin/env python3
"""rt_telegram_24h_check.py — RT-TELEGRAM 24h stability gate (MISSION-795).

Runs ~24h after the 2026-08-07 06:43 fix deploy. Verifies the gateway held
clean overnight; appends a dated verdict to the RT-TELEGRAM session log and
logs to the mission board via mission_board_sync.py.
"""
import subprocess
from datetime import datetime, timezone, timedelta

SINCE = "2026-08-07 06:43:00"
LOG = "/home/john/Thunderbird/OpsCenter/meetroom/RT-TELEGRAM/24h_check.md"
MT = timezone(timedelta(hours=-6))

def sh(cmd: str) -> str:
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout

def main():
    active = sh("systemctl --user is-active thunderbird-telegram-gw.service").strip()
    errs = sh(f"journalctl --user -u thunderbird-telegram-gw.service --since '{SINCE}' | grep -icE 'FAILED|exit-code|Conflict|level=ERROR'").strip() or "0"
    conflicts = sh(f"journalctl --user -u thunderbird-telegram-gw.service --since '{SINCE}' | grep -ic 'getUpdates error: Conflict'").strip() or "0"
    now = datetime.now(MT).strftime("%Y-%m-%d %H:%M MT")
    clean = active == "active" and errs == "0" and conflicts == "0"
    verdict = "PASS — clean 24h window" if clean else f"REVIEW — active={active} err_lines={errs} conflicts={conflicts}"
    with open(LOG, "a") as f:
        f.write(f"- {now} | 24h gate: {verdict} (err_lines={errs}, conflicts={conflicts})\n")
    mb = f"python3 /home/john/Thunderbird/OpsCenter/mission_board_sync.py log MISSION-795 '24h gate: {verdict} (err={errs}, conflicts={conflicts})'"
    sh(mb)
    print(verdict)

if __name__ == "__main__":
    main()