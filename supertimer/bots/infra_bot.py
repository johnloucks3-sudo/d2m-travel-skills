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
             interval_sec=2700, timeout_sec=180),  # Claude CLI (Opus) takes 60-120s; 60s caused infinite-DUE loop (same as chrome-cdp-health)
        Task("d2mconcierge-oauth",
             sys_py("scripts/d2mconcierge_mcp_oauth_refresh.py"),
             interval_sec=2700, timeout_sec=60),
        Task("johnloucks3-oauth",
             sys_py("scripts/johnloucks3_mcp_oauth_refresh.py"),
             interval_sec=2700, timeout_sec=60),
        Task("tess-token",
             sys_py("scripts/tess_token_keepalive.py"),
             interval_sec=5400, timeout_sec=90),
        # portal-keepalive REMOVED 2026-08-07 — retired by Commander's 2026-07-16 order;
        # was resurrected + running here (zombie). Super+systemd duplication. (RT-KEEPALIVES CC/AG)
        # Task("portal-keepalive",
        #      sys_py("scripts/portal_keepalive.py"),
        #      interval_sec=2700, timeout_sec=120),
        # bsk-session-keepalive REMOVED 2026-08-09 (RT-CENTRAV-SPAWN CC) — this task
        # rides bsk (browser-skill, drives the Commander's real Chrome via CDP) into
        # Centrav every 20 min. It is the actual source of "Chrome Spawn of Centrav.com
        # 13+ times" — missed by the 2026-08-07 cleanup that removed the two adjacent
        # portal-keepalive/centrav-warm tasks. Commander 2026-08-07: KILL all airfare
        # session keep-alives except Skybird. Centrav is on-demand re-auth only.
        # Task("bsk-session-keepalive",
        #      venv("scripts/bsk_session_keepalive.py", "--portal", "centrav", "--once"),
        #      interval_sec=1200, timeout_sec=90,
        #      allowed_rcs=(0, 1)),
        Task("tool-key-refresh",
             bash(f"{ROOT}/hooks/refresh_tool_api_keys.sh"),
             interval_sec=840, timeout_sec=30),
        # chrome-cdp-health REMOVED — was auto-spawning Chrome every 60s due to infra_bot RED loop
        # (infra_bot RED → leader never updates last_run → always DUE; task exit 1 → same loop)
        # chrome-debug.service disabled; start Chrome manually when needed for scraping.
        Task("qdrant-watchdog",
             venv("core/memory/qdrant_docker_watchdog.py"),
             interval_sec=300, timeout_sec=30),
        Task("autosave",
             bash(f"{ROOT}/scripts/autosave_checkpoint.sh"),
             interval_sec=600, timeout_sec=30),
        Task("keepalive-supervisor",
             venv("scripts/keepalive_supervisor.py"),
             interval_sec=1560, timeout_sec=60,
             allowed_rcs=(0, 1)),  # rc=1=escalations pending (centrav needs manual reauth — logged, not fixable by bot)
        Task("silversea-session",
             venv("scripts/silversea_cookie_refresh.py"),
             interval_sec=86400, timeout_sec=120),
        # centrav-warm REMOVED 2026-08-07 (Commander) — 30-min attention spam: session dead,
        # headless relogin fails (browser profile locked), pages repeatedly. Go on-demand re-auth only.
        # Task("centrav-warm",
        #      venv("scripts/centrav_session_warm.py"),
        #      interval_sec=3060, timeout_sec=120,
        #      allowed_rcs=(0, 3)),
        Task("fare-watch-deadman",
             venv("scripts/fare_watch_deadman.py"),
             interval_sec=10800, timeout_sec=30,
             allowed_rcs=(0, 1)),  # rc=1=dark but already paged: expected. rc=0=live. (FIX-4 2026-06-27)
        Task("tess-fare-watch-autoregister",
             venv("scripts/tess_fare_watch_autoregister.py"),
             interval_sec=86400, timeout_sec=60,
             allowed_rcs=(0,)),  # daily: auto-register TESS air bookings without watches (FIX-10 2026-06-27)
    ]

if __name__ == "__main__":
    result = InfraBot().run()
    print(json.dumps(result))
