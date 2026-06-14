#!/usr/bin/env python3
"""
mission_bot — Mission board promoter, 1730 nomination, WAR, preflight gate.
Interval: 900s. Most tasks run daily.
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from supertimer.base_bot import BotBase, Task, venv, sys_py, bash

ROOT = Path("/home/john/Thunderbird")

class MissionBot(BotBase):
    bot_name = "mission_bot"
    tasks = [
        Task("mission-board-promoter",
             sys_py("scripts/mission_board_promoter.py"),
             interval_sec=21600, timeout_sec=120),
        Task("1730-nomination",
             venv("agents/thunderbird_1730_nomination.py"),
             interval_sec=86400, timeout_sec=180),
        Task("war-report",
             venv("scripts/generate_war.py"),
             interval_sec=86400, timeout_sec=120),
        Task("decision-log",
             sys_py("scripts/hale_decision_log_rollup.py"),
             interval_sec=86400, timeout_sec=60),
        Task("commander-context",
             sys_py("scripts/commander_context_restore.py"),
             interval_sec=86400, timeout_sec=60),
        Task("preflight-gate",
             sys_py("scripts/preflight_gate.py"),
             interval_sec=86400, timeout_sec=120),
        Task("preflight",
             venv("api/thunderbird_preflight.py"),
             interval_sec=86400, timeout_sec=120),
        Task("mission-090-sweep",
             bash(f"{ROOT}/output/mission-090_worktree_sweep.sh --email-json")
             if (ROOT / "output/mission-090_worktree_sweep.sh").exists()
             else sys_py("scripts/mission_board_promoter.py"),
             interval_sec=86400, timeout_sec=120),
    ]

if __name__ == "__main__":
    result = MissionBot().run()
    print(json.dumps(result))
