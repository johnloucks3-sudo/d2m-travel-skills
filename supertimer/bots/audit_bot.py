#!/usr/bin/env python3
"""
audit_bot — Anti-theater audit, lessons tracker, timer self-audit, validation report.
Interval: 21600s (6hr). Tasks run weekly.
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from supertimer.base_bot import BotBase, Task, venv, sys_py

ROOT = Path("/home/john/Thunderbird")

class AuditBot(BotBase):
    bot_name = "audit_bot"
    tasks = [
        Task("anti-theater-audit",
             sys_py("scripts/anti_theater_audit.py"),
             interval_sec=604800, timeout_sec=300),
        Task("lessons-tracker",
             sys_py("scripts/lessons_implementation_tracker.py"),
             interval_sec=604800, timeout_sec=120),
        Task("timer-self-audit",
             venv("core/ops/timer_self_audit.py"),
             interval_sec=604800, timeout_sec=300),
        Task("validation-report",
             venv("core/lifecycle/validation_report_generator.py"),
             interval_sec=604800, timeout_sec=300),
        Task("continuity-recert",
             sys_py("scripts/continuity_daily_recert.py"),
             interval_sec=86400, timeout_sec=120),
        Task("qdrant-reindex",
             venv("core/memory/qdrant_reindex_incremental.py", "--memory-threshold", "70"),
             interval_sec=604800, timeout_sec=300),
        Task("mythos-monitor",
             venv("core/intel/mythos_availability_monitor.py"),
             interval_sec=86400, timeout_sec=120),
        Task("blackboard-conflict-resolver",
             sys_py("scripts/blackboard_conflict_resolver.py"),
             interval_sec=300, timeout_sec=60),
        Task("disk-pressure",
             sys_py("scripts/disk_pressure.py"),
             interval_sec=900, timeout_sec=30),
        Task("dead-code-scan",
             sys_py("scripts/dead_code_scan.py"),
             interval_sec=604800, timeout_sec=180),  # weekly
    ]

if __name__ == "__main__":
    result = AuditBot().run()
    print(json.dumps(result))
