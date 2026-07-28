#!/usr/bin/env python3
"""
SETUP CONSOLIDATED REPORTING SYSTEMD USER TIMERS
================================================
Authority: SO-REPORTING-2026 & Commander Directive (2026-07-28)

Timers Created:
1. thunderbird-morning-consolidated.timer (Daily 06:30 MT) -> thunderbird-morning-consolidated.service
2. thunderbird-evening-consolidated.timer (Daily 18:30 MT) -> thunderbird-evening-consolidated.service
"""

import sys
import os
import subprocess
from pathlib import Path

SYSTEMD_DIR = Path("/home/john/.config/systemd/user")
SYSTEMD_DIR.mkdir(parents=True, exist_ok=True)

MORNING_SERVICE = """[Unit]
Description=Thunderbird Wing Morning Consolidated Briefing Service (06:30 MT)

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /home/john/Thunderbird/core/ops/morning_consolidated_brief_engine.py
"""

MORNING_TIMER = """[Unit]
Description=Thunderbird Wing Morning Consolidated Briefing Timer (Daily 06:30 MT)

[Timer]
OnCalendar=*-*-* 06:30:00 America/Denver
Persistent=true

[Install]
WantedBy=timers.target
"""

EVENING_SERVICE = """[Unit]
Description=Thunderbird Wing Evening Consolidated EOD Briefing Service (18:30 MT)

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /home/john/Thunderbird/core/ops/evening_consolidated_eod_engine.py
"""

EVENING_TIMER = """[Unit]
Description=Thunderbird Wing Evening Consolidated EOD Briefing Timer (Daily 18:30 MT)

[Timer]
OnCalendar=*-*-* 18:30:00 America/Denver
Persistent=true

[Install]
WantedBy=timers.target
"""

def setup_timers():
    print("Writing systemd service and timer unit files...")
    
    (SYSTEMD_DIR / "thunderbird-morning-consolidated.service").write_text(MORNING_SERVICE)
    (SYSTEMD_DIR / "thunderbird-morning-consolidated.timer").write_text(MORNING_TIMER)
    (SYSTEMD_DIR / "thunderbird-evening-consolidated.service").write_text(EVENING_SERVICE)
    (SYSTEMD_DIR / "thunderbird-evening-consolidated.timer").write_text(EVENING_TIMER)
    
    print("Reloading systemd user daemon and enabling timers...")
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "--user", "enable", "--now", "thunderbird-morning-consolidated.timer"], check=True)
    subprocess.run(["systemctl", "--user", "enable", "--now", "thunderbird-evening-consolidated.timer"], check=True)
    
    print("✅ Systemd consolidated timers active!")

if __name__ == "__main__":
    setup_timers()
