#!/usr/bin/env python3
"""
client_bot — Lifecycle, dossier freshness, touchpoints, fare watch, booking monitor.
Interval: 300s. Individual tasks on daily / hourly sub-intervals.
Tempo increased 2026-06-19 per Commander directive — within $20 API / $100 MAX budget.
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from supertimer.base_bot import BotBase, Task, venv, sys_py, bash

ROOT = Path("/home/john/Thunderbird")

class ClientBot(BotBase):
    bot_name = "client_bot"
    tasks = [
        Task("lifecycle",
             sys_py("D2M/d2m_lifecycle_scheduler.py"),
             interval_sec=10800, timeout_sec=180),   # every 3h (was 5.5h)
        Task("lifecycle-scheduler",
             venv("core/lifecycle/lifecycle_scheduler.py"),
             interval_sec=10800, timeout_sec=120),   # every 3h (was 6h)
        Task("dossier-freshness",
             sys_py("scripts/dossier_freshness.py"),
             interval_sec=10800, timeout_sec=120),   # every 3h (was 5.5h)
        Task("post-trip-followup",
             sys_py("scripts/post_trip_followup.py"),
             interval_sec=86400, timeout_sec=120),   # daily — unchanged
        Task("touchpoint-execute",
             sys_py("scripts/touchpoint_execute.py"),
             interval_sec=43200, timeout_sec=120),   # 2x/day (was daily)
        Task("touchpoint-proposer",
             bash(f"/bin/bash {ROOT}/D2M/hale_touchpoint_proposer_daily.sh"),
             interval_sec=43200, timeout_sec=180),   # 2x/day (was daily)
        Task("correspondence-sync",
             venv("scripts/dossier_correspondence_sync.py"),
             interval_sec=10800, timeout_sec=120),   # every 3h (was 6h)
        Task("tess-sync",
             venv("scripts/tess_dossier_sync.py"),
             interval_sec=43200, timeout_sec=120),   # 2x/day (was daily)
        Task("fare-watch",
             sys_py("scripts/fare_watch_centrav.py"),
             interval_sec=14400, timeout_sec=180),   # every 4h (was daily)
        Task("ita-fare-watch",
             venv("scripts/ita_fare_watch_poll.py"),
             interval_sec=14400, timeout_sec=600),   # every 4h (was 6h) — serialized, no overlap
        Task("booking-monitor",
             venv("core/booking/thunderbird_booking_monitor.py"),
             interval_sec=10800, timeout_sec=600),    # every 3h (was 2h) — avoid 2h collision with ita (4h offset)
        Task("tess-web-sync",
             venv("scripts/thunderbird_tess_web_sync.py") if (ROOT / "scripts/thunderbird_tess_web_sync.py").exists()
             else sys_py("scripts/tess_dossier_sync.py"),
             interval_sec=43200, timeout_sec=120),   # 2x/day (was daily)
    ]

if __name__ == "__main__":
    result = ClientBot().run()
    print(json.dumps(result))
