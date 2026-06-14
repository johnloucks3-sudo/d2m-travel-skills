#!/usr/bin/env python3
"""
ops_bot — Wing pulse: heartbeats, watchdogs, blackboard sync.
Interval: 60s (every leader tick). Tasks run on their own sub-intervals.
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from supertimer.base_bot import BotBase, Task, venv, sys_py, bash

ROOT = Path("/home/john/Thunderbird")

class OpsBot(BotBase):
    bot_name = "ops_bot"
    # Fast deterministic checks only. No AI calls, no Playwright, no dbus.
    tasks = [
        Task("health-check",    sys_py("core/health_check_worker.py"),        interval_sec=60,  timeout_sec=30),
        Task("blackboard-sync", venv("OpsCenter/blackboard_sync.py"),          interval_sec=300, timeout_sec=60),
        Task("router-health",   venv("core/ai_infra/daemons/router_health_daemon.py", "--once"),
                                                                               interval_sec=300, timeout_sec=45),
        Task("disk-pressure",   sys_py("scripts/disk_pressure.py"),           interval_sec=300, timeout_sec=20),
        Task("sentinel",        bash("pgrep -f 'thunderbird_sentinel' > /dev/null && echo ok || echo not_running"),
                                                                               interval_sec=120, timeout_sec=10),
    ]

if __name__ == "__main__":
    result = OpsBot().run()
    print(json.dumps(result))
