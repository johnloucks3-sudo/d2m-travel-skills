#!/usr/bin/env python3
"""
finance_bot — Commission watch, FDP reconcile, supplier rate/promo scan, daily audit.
Interval: 1800s. Tasks run daily or twice-daily.
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from supertimer.base_bot import BotBase, Task, venv, sys_py

ROOT = Path("/home/john/Thunderbird")

class FinanceBot(BotBase):
    bot_name = "finance_bot"
    tasks = [
        Task("commission-watch",
             sys_py("scripts/commission_watch.py"),
             interval_sec=86400, timeout_sec=180),
        Task("fdp-reconcile",
             sys_py("scripts/fdp_reconcile.py"),
             interval_sec=86400, timeout_sec=120),
        Task("supplier-promo-scan",
             sys_py("scripts/supplier_promo_scan.py"),
             interval_sec=86400, timeout_sec=180),
        Task("supplier-rate-drift",
             sys_py("scripts/supplier_rate_drift.py"),
             interval_sec=86400, timeout_sec=180),
        Task("daily-audit",
             venv("OpsCenter/hale_daily_audit.py"),
             interval_sec=86400, timeout_sec=180),
    ]

if __name__ == "__main__":
    result = FinanceBot().run()
    print(json.dumps(result))
