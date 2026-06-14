#!/usr/bin/env python3
"""
metrics_bot — Dashboards, usage, FPD alerts, cost tracking.
Interval: 600s. Sub-tasks on 10min–1hr schedules.
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from supertimer.base_bot import BotBase, Task, venv, sys_py, bash

ROOT = Path("/home/john/Thunderbird")

class MetricsBot(BotBase):
    bot_name = "metrics_bot"
    tasks = [
        Task("dashboard-refresh",
             venv("OpsCenter/dashboard_generator.py", "--once"),
             interval_sec=1080, timeout_sec=60),
        Task("usage-monitor",
             venv("core/ops/thunderbird_usage_monitor.py", "--alert"),
             interval_sec=840, timeout_sec=60),
        Task("hale-dashboard",
             venv("core/ops/hale_dashboard_gen.py"),
             interval_sec=60, timeout_sec=60),
        Task("bryana-dashboard",
             venv("core/ops/bryana_dashboard.py"),
             interval_sec=300, timeout_sec=60),
        Task("fpd-alert",
             venv("core/watchtower/thunderbird_fpd_alert.py"),
             interval_sec=86400, timeout_sec=60),
        Task("fpd-auto-update",
             venv("core/ops/fpd_auto_update.py"),
             interval_sec=840, timeout_sec=60),
        Task("cost-claude",
             venv("core/cost_dashboard/collectors/claude_usage.py"),
             interval_sec=120, timeout_sec=30),
        Task("gemini-costs",
             bash(f"/usr/bin/python3 {Path.home()}/.claude/gcp_gemini_costs.py --alert"),
             interval_sec=1020, timeout_sec=60),
        Task("claude-token-monitor",
             sys_py("/home/john/claude_token_counter.py"),
             interval_sec=840, timeout_sec=30),
    ]

if __name__ == "__main__":
    result = MetricsBot().run()
    print(json.dumps(result))
