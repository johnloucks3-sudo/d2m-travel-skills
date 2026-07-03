#!/usr/bin/env python3
"""
repair_bot — Auto-repair trigger when any bot exceeds 10 consecutive failures.
Interval: 60s. On threshold breach: attempt repair, reset counter, suppress notifications.
"""
import json, subprocess, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from supertimer.base_bot import BotBase, Task, venv, sys_py, bash

ROOT = Path("/home/john/Thunderbird")
THRESHOLD = 10  # Auto-repair trigger

class RepairBot(BotBase):
    bot_name = "repair_bot"
    tasks = [
        Task("auto-repair-trigger",
             sys_py("scripts/auto_repair_trigger.py"),
             interval_sec=60, timeout_sec=120),
    ]

if __name__ == "__main__":
    result = RepairBot().run()
    print(json.dumps(result))
