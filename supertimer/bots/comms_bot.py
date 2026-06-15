#!/usr/bin/env python3
"""
comms_bot — Commander directive sweep, inbox hygiene, email intel.
Interval: 120s. Most tasks run every 2-10 min on their own sub-intervals.
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from supertimer.base_bot import BotBase, Task, venv, sys_py, bash, VENV_PYTHON

ROOT = Path("/home/john/Thunderbird")

class CommsBot(BotBase):
    bot_name = "comms_bot"
    tasks = [
        Task("directive-sweep",
             bash(f"{ROOT}/.venv/bin/python3 {ROOT}/OpsCenter/run_commander_directive_sweep.py"),
             interval_sec=120, timeout_sec=60),
        Task("inbox-hygiene",
             sys_py("core/email/inbox_hygiene.py"),
             interval_sec=600, timeout_sec=60),
        Task("email-intel",
             venv("core/email/thunderbird_email_intel.py", "--sweep", "--hours=1"),
             interval_sec=3600, timeout_sec=300),
        Task("inbox-sweep",
             venv("OpsCenter/run_inbox_sweep.py"),
             interval_sec=10800, timeout_sec=120),
        # venv() prepends ROOT, so -c must be passed directly (not via venv helper)
        Task("chatlog-backup",
             [VENV_PYTHON, "-c",
              "import sys; sys.path.insert(0,'.'); "
              "from OpsCenter.task_processor import _backup_chat_log_to_drive; "
              "_backup_chat_log_to_drive()"],
             interval_sec=3600, timeout_sec=60),
    ]

if __name__ == "__main__":
    result = CommsBot().run()
    print(json.dumps(result))
