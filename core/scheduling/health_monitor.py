#!/usr/bin/env python3
"""
HEALTH MONITORING & DIAGNOSTIC FRAMEWORK
Monitors timer system health, missed deadlines, automation status
"""

import json
import logging
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HealthMonitor:
    """Monitors timer system health and automation status."""

    def __init__(self):
        self.timer_dir = Path("/etc/systemd/system/d2m-timers")
        self.log_dir = Path("/home/john/Thunderbird/OpsCenter")

    def get_systemd_timer_status(self) -> Dict:
        """Check systemd timer activation status."""

        try:
            result = subprocess.run(
                ["systemctl", "list-timers", "--all", "--user"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return {
                "status": "ok" if result.returncode == 0 else "error",
                "output": result.stdout,
            }
        except Exception as e:
            logger.error(f"Failed to check systemd timers: {e}")
            return {
                "status": "error",
                "output": str(e)
            }

    def check_missed_deadlines(self, tasks: List[Dict]) -> Dict:
        """Identify tasks that missed their deadline."""

        now = datetime.now()
        missed = []

        for task in tasks:
            try:
                scheduled = datetime.fromisoformat(task.get("scheduled_date"))
                if scheduled < now and task.get("status") != "COMPLETE":
                    missed.append({
                        "task_id": task["task_id"],
                        "client": task.get("client"),
                        "scheduled": task.get("scheduled_date"),
                        "days_overdue": (now - scheduled).days,
                        "priority": task.get("priority", "P2")
                    })
            except (ValueError, KeyError):
                continue

        return {
            "total_missed": len(missed),
            "critical_missed": sum(1 for m in missed if m["priority"] == "P0"),
            "missed_tasks": missed
        }

    def check_automation_health(self) -> Dict:
        """Check health of automation components."""

        health = {
            "timer_engine": self._check_file_exists("/home/john/Thunderbird/core/scheduling/thunderbird_timer_engine.py"),
            "dispatch_worker": self._check_file_exists("/home/john/Thunderbird/core/scheduling/dispatch_task.py"),
            "notification_system": self._check_file_exists("/home/john/Thunderbird/core/scheduling/commander_notification_system.py"),
            "timer_output_dir": self._check_file_exists("/home/john/Thunderbird/OpsCenter/timer_output"),
            "task_dispatch_log": self._check_file_exists("/home/john/Thunderbird/OpsCenter/task_dispatch.log"),
        }

        return {
            "components": health,
            "ready": all(health.values()),
            "checked_at": datetime.now().isoformat()
        }

    def _check_file_exists(self, path: str) -> bool:
        """Check if a file or directory exists."""
        return Path(path).exists()

    def generate_system_report(self, tasks: List[Dict] = None) -> Dict:
        """Generate comprehensive system health report."""

        report = {
            "timestamp": datetime.now().isoformat(),
            "systemd_timers": self.get_systemd_timer_status(),
            "automation_health": self.check_automation_health(),
        }

        if tasks:
            report["missed_deadlines"] = self.check_missed_deadlines(tasks)
            report["task_statistics"] = {
                "total_tasks": len(tasks),
                "by_priority": self._count_by_priority(tasks),
                "upcoming_7d": self._count_upcoming(tasks, 7),
                "upcoming_30d": self._count_upcoming(tasks, 30),
            }

        return report

    def _count_by_priority(self, tasks: List[Dict]) -> Dict[str, int]:
        """Count tasks by priority."""
        counts = {}
        for task in tasks:
            priority = task.get("priority", "P2")
            counts[priority] = counts.get(priority, 0) + 1
        return counts

    def _count_upcoming(self, tasks: List[Dict], days: int) -> int:
        """Count upcoming tasks within N days."""
        now = datetime.now()
        cutoff = now + timedelta(days=days)

        return sum(
            1 for task in tasks
            if now <= datetime.fromisoformat(task.get("scheduled_date")) <= cutoff
        )


def main():
    """Generate and display system health report."""

    monitor = HealthMonitor()

    # Load test tasks
    timer_output = Path("/home/john/Thunderbird/OpsCenter/timer_output/timer_schedule.json")
    tasks = []

    if timer_output.exists():
        with open(timer_output) as f:
            data = json.load(f)
            tasks = data.get("staff_tasks", [])

    # Generate report
    report = monitor.generate_system_report(tasks)

    # Save report
    report_path = Path("/home/john/Thunderbird/OpsCenter/health_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    # Display summary
    print(f"\n✅ HEALTH MONITOR REPORT")
    print(f"   Timestamp: {report['timestamp']}")
    print(f"   Automation Ready: {report['automation_health']['ready']}")
    if tasks:
        print(f"   Total Tasks: {report['task_statistics']['total_tasks']}")
        print(f"   Upcoming (30d): {report['task_statistics']['upcoming_30d']}")
        if report.get('missed_deadlines', {}).get('total_missed', 0) > 0:
            print(f"   ⚠️  MISSED DEADLINES: {report['missed_deadlines']['total_missed']}")

    logger.info(f"Health report saved to {report_path}")


if __name__ == "__main__":
    main()
