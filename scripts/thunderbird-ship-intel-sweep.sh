#!/usr/bin/env bash
# Daily Ship Intel Sweep — cron/systemd entry point
# Runs at 06:00 MT daily via thunderbird-ship-intel-sweep.timer
set -e
cd /home/john/Thunderbird
python3 -c "
from core.intel.thunderbird_ship_intel_dashboard import run_daily_sweep
import json, sys
result = run_daily_sweep()
print(json.dumps(result, indent=2, default=str))
sys.exit(0 if result['ships_failed'] == 0 else 1)
"
