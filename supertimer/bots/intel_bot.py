#!/usr/bin/env python3
"""
intel_bot — Airline, weather, X-OSINT, Perx, flight scan, innovation scan.
Interval: 900s. Most tasks daily, some hourly.
Tempo increased 2026-06-19 per Commander directive — within $20 API / $100 MAX budget.
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from supertimer.base_bot import BotBase, Task, venv, sys_py, bash, goose

ROOT = Path("/home/john/Thunderbird")

class IntelBot(BotBase):
    bot_name = "intel_bot"
    tasks = [
        Task("airline-schedule-change",
             sys_py("scripts/airline_schedule_monitor.py"),
             interval_sec=3600, timeout_sec=120),    # hourly — unchanged
        Task("weather-disruption",
             sys_py("scripts/weather_disruption_monitor.py"),
             interval_sec=3600, timeout_sec=120),    # hourly (was 2h)
        Task("perx-trigger",
             sys_py("scripts/perx_trigger_detector.py"),
             interval_sec=900, timeout_sec=90),      # every 15m (was 30m)
        Task("perx-intel",
             sys_py("scripts/perx_intel_monitor.py"),
             interval_sec=43200, timeout_sec=180),   # 2x/day (was daily)
        Task("flight-scan",
             venv("scripts/flight_scan_trigger.py"),
             interval_sec=43200, timeout_sec=180),   # 2x/day (was daily)
        Task("intel-telegram",
             venv("core/intel/thunderbird_intel_telegram.py"),
             interval_sec=43200, timeout_sec=180),   # 2x/day (was daily)
        Task("airline-monitor",
             venv("core/travel/thunderbird_airline_monitor.py"),
             interval_sec=43200, timeout_sec=300),   # 2x/day — Goose/DeepSeek retired
        Task("x-osint",
             venv("core/intel/thunderbird_x_osint.py"),
             interval_sec=43200, timeout_sec=300),   # 2x/day — Goose/DeepSeek retired
        Task("innovation-scan",
             bash(
                 f"jq '. += [{{\"task_id\": \"TKT-AUTO\", \"task_type\": \"innovation_scan\", \"persona\": \"A12\"}}]' "
                 f"{ROOT}/OpsCenter/01_TASK_QUEUE.json > {ROOT}/OpsCenter/tmp.json "
                 f"&& mv {ROOT}/OpsCenter/tmp.json {ROOT}/OpsCenter/01_TASK_QUEUE.json"
             ),
             interval_sec=21600, timeout_sec=30),    # every 6h (was daily)
        Task("dembe-intel",
             venv("core/intel/dembe_intel_sweep.py")
             if (ROOT / "core/intel/dembe_intel_sweep.py").exists()
             else sys_py("scripts/perx_intel_monitor.py"),
             interval_sec=21600, timeout_sec=180),   # every 6h (was daily)
    ]

if __name__ == "__main__":
    result = IntelBot().run()
    print(json.dumps(result))
