#!/usr/bin/env python3
"""
ai_exec_bot — Mission executor, sculptor, incubator, power harvest, daily/EOD brief.
Interval: 3600s. These spawn headless Claude — each runs daily or 4x/day.
Tempo increased 2026-06-19 per Commander directive — within $20 API / $100 MAX budget.
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from supertimer.base_bot import BotBase, Task, venv, sys_py, bash

ROOT = Path("/home/john/Thunderbird")

# Mission executor gate hours: 08:00, 12:00, 16:00, 20:00 MDT (~4hr intervals)
MISSION_EXEC_INTERVAL = 14400

class AIExecBot(BotBase):
    bot_name = "ai_exec_bot"
    tasks = [
        Task("mission-executor",
             venv("scripts/daily_mission_executor.py", "--priority", "P0,P1"),
             interval_sec=MISSION_EXEC_INTERVAL, timeout_sec=600),
        Task("incubator-execute",
             venv("core/intel/thunderbird_incubator.py", "execute"),
             interval_sec=43200, timeout_sec=600),   # 2x/day (was daily)
        Task("sculptor-harvest",
             venv("core/intel/thunderbird_nightly_tech_harvest.py"),
             interval_sec=43200, timeout_sec=600),   # 2x/day (was daily)
        Task("sculptor-learn",
             venv("itinerary/thunderbird_doc_sculptor.py", "--learn"),
             interval_sec=86400, timeout_sec=600),
        Task("power-harvest",
             venv("api/thunderbird_power_harvest.py"),
             interval_sec=86400, timeout_sec=600),
        Task("daily-brief",
             venv("agents/thunderbird_daily_brief.py"),
             interval_sec=86400, timeout_sec=300),
        Task("eod-brief",
             venv("agents/thunderbird_eod_brief.py"),
             interval_sec=86400, timeout_sec=300),
        Task("metronome",
             venv("OpsCenter/metronome.py"),
             interval_sec=300, timeout_sec=60),
        Task("dani-voice",
             venv("scripts/dani_voice_draft.py", "--timer"),
             interval_sec=86400, timeout_sec=180),
        Task("spsa-intake",
             venv("OpsCenter/job_spsa_intake.py"),
             interval_sec=86400, timeout_sec=180),
        # AI heartbeats — spawn Claude/JET processes, belong here not ops_bot
        Task("jet-heartbeat",
             venv("OpsCenter/jet_heartbeat.py"),
             interval_sec=300, timeout_sec=60),
        Task("cc-heartbeat",
             venv("OpsCenter/hale_cc_heartbeat.py"),
             interval_sec=300, timeout_sec=60),
        Task("coo-watchdog",
             sys_py("OpsCenter/thunderbird_coo_watchdog.py"),
             interval_sec=600, timeout_sec=90),
        Task("opscenter-watchdog",
             venv("OpsCenter/opscenter_watchdog.py"),
             interval_sec=300, timeout_sec=60),
        Task("mission-readiness",
             sys_py("scripts/mission_readiness.py", "--brief"),
             interval_sec=900, timeout_sec=60),
    ]

if __name__ == "__main__":
    result = AIExecBot().run()
    print(json.dumps(result))
