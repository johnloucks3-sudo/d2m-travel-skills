#!/usr/bin/env python3
"""
infra_bot — All OAuth keepalives, TESS, tool keys, Chrome/Qdrant health.
Interval: 300s. Credentials checked on their own sub-intervals.
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from supertimer.base_bot import BotBase, Task, venv, sys_py, bash

ROOT = Path("/home/john/Thunderbird")

class InfraBot(BotBase):
    bot_name = "infra_bot"
    tasks = [
        Task("claude-oauth",
             bash(f"{ROOT}/hooks/claude_oauth_keepalive.sh"),
             interval_sec=2700, timeout_sec=60),
        Task("d2mconcierge-oauth",
             sys_py("scripts/d2mconcierge_mcp_oauth_refresh.py"),
             interval_sec=2700, timeout_sec=60),
        Task("johnloucks3-oauth",
             sys_py("scripts/johnloucks3_mcp_oauth_refresh.py"),
             interval_sec=2700, timeout_sec=60),
        Task("tess-token",
             sys_py("scripts/tess_token_keepalive.py"),
             interval_sec=5400, timeout_sec=90),
        Task("portal-keepalive",
             sys_py("scripts/portal_keepalive.py"),
             interval_sec=2700, timeout_sec=120),
        Task("tool-key-refresh",
             bash(f"{ROOT}/hooks/refresh_tool_api_keys.sh"),
             interval_sec=840, timeout_sec=30),
        Task("chrome-cdp-health",
             sys_py("scripts/chrome_cdp_health.py"),
             interval_sec=300, timeout_sec=30),
        Task("qdrant-watchdog",
             venv("core/memory/qdrant_docker_watchdog.py"),
             interval_sec=300, timeout_sec=30),
        Task("autosave",
             bash(f"{ROOT}/scripts/autosave_checkpoint.sh"),
             interval_sec=600, timeout_sec=30),
        Task("keepalive-supervisor",
             venv("scripts/keepalive_supervisor.py"),
             interval_sec=1560, timeout_sec=60),
        Task("silversea-session",
             venv("scripts/silversea_cookie_refresh.py"),
             interval_sec=86400, timeout_sec=120),
        Task("centrav-warm",
             venv("scripts/centrav_session_warm.py"),
             interval_sec=3060, timeout_sec=120),
    ]

if __name__ == "__main__":
    result = InfraBot().run()
    print(json.dumps(result))
