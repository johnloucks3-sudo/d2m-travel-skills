#!/usr/bin/env python3
"""
COMMANDER NOTIFICATION SYSTEM
Email alerts for upcoming client deliverables
Sends drafts ready notifications 14 days before send date
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("/home/john/Thunderbird/OpsCenter/notifications.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class CommanderNotificationSystem:
    """Manages email alerts to Commander for upcoming deliverables."""

    def __init__(self):
        self.notifications_sent = []
        self.commander_email = "johnloucks3@gmail.com"
        self.notification_dir = Path("/home/john/Thunderbird/OpsCenter/notifications")
        self.notification_dir.mkdir(parents=True, exist_ok=True)

    def should_notify(self, task: Dict, days_threshold: int = 14) -> bool:
        """Check if a task is due for notification (within threshold days)."""
        task_date = datetime.fromisoformat(task["scheduled_date"])
        days_until = (task_date - datetime.now()).days

        return 0 <= days_until <= days_threshold

    def generate_notification(self, client_name: str, client_id: str,
                             upcoming_tasks: List[Dict],
                             priority_level: str = "INFO") -> str:
        """Generate a readable notification message."""

        tasks_md = "\n".join([
            f"- **{t['task_name']}** (Task {t['task_id']}) — Due {t['scheduled_date'][:10]}"
            for t in upcoming_tasks[:5]
        ])

        message = f"""
## THUNDERBIRD STAFF DELIVERY PIPELINE READY

**Client:** {client_name}
**Client ID:** {client_id}
**Priority:** {priority_level}
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M MT')}

### Upcoming Deliverables

{tasks_md}

### What You're Getting

✅ **Draft Quality:** All drafts pass WF-17 compliance (logo, stationery, tone)
✅ **Staff Processed:** Researched → Narratived → Validated → Polished by Dani
✅ **Ready to Send:** No edits needed unless you choose to customize

### Timeline

- **Drafts ready:** 14 days before send (COS reviews 7 days before)
- **Send approval:** You approve on send day
- **Post-send:** Archive + satisfaction tracking

### Next Action

Review first draft when COS surfaces it in the inbox. All staff inputs pre-loaded.

---
*Sent from Thunderbird Timer Engine — Staff automation complete* ✈️
"""
        return message

    def queue_notification(self, client_name: str, client_id: str,
                          upcoming_tasks: List[Dict],
                          priority_level: str = "INFO") -> None:
        """Queue a notification for sending."""

        notification = {
            "timestamp": datetime.now().isoformat(),
            "to": self.commander_email,
            "client": client_name,
            "client_id": client_id,
            "priority": priority_level,
            "subject": f"[{priority_level}] Deliverable Ready: {client_name}",
            "body": self.generate_notification(client_name, client_id, upcoming_tasks, priority_level),
            "tasks": [
                {
                    "task_id": t["task_id"],
                    "name": t["task_name"],
                    "scheduled": t["scheduled_date"],
                    "send_date": t["send_date"],
                }
                for t in upcoming_tasks[:5]
            ]
        }

        self.notifications_sent.append(notification)
        self._save_notification(notification)
        logger.info(f"Queued notification for {client_name} ({priority_level})")

    def _save_notification(self, notification: Dict) -> None:
        """Save notification to disk for audit trail."""
        filename = f"{notification['client_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.notification_dir / filename

        with open(filepath, "w") as f:
            json.dump(notification, f, indent=2, default=str)

    def generate_daily_digest(self, all_tasks: List[Dict]) -> Optional[str]:
        """Generate a daily digest of all upcoming tasks (next 7 days)."""

        now = datetime.now()
        upcoming_7d = [
            t for t in all_tasks
            if now <= datetime.fromisoformat(t.get("scheduled_date")) <= now + timedelta(days=7)
        ]

        if not upcoming_7d:
            return None

        # Group by client
        by_client = {}
        for task in upcoming_7d:
            client = task.get("client", "Unknown")
            if client not in by_client:
                by_client[client] = []
            by_client[client].append(task)

        digest = "## DAILY TASK DIGEST (Next 7 Days)\n\n"
        for client, tasks in sorted(by_client.items()):
            digest += f"### {client}\n"
            for task in tasks:
                date_str = task.get("scheduled_date", "N/A")[:10]
                digest += f"- {task.get('task_name')} — {date_str}\n"
            digest += "\n"

        return digest

    def monitor_critical_path(self, all_tasks: List[Dict]) -> Dict:
        """Monitor critical path tasks (P0 priority)."""

        now = datetime.now()
        critical_tasks = [
            t for t in all_tasks
            if t.get("priority") == "P0"
        ]

        # Check for overdue critical tasks
        overdue = [
            t for t in critical_tasks
            if datetime.fromisoformat(t.get("scheduled_date")) < now
        ]

        # Check for critical tasks due soon (next 48h)
        due_soon = [
            t for t in critical_tasks
            if now <= datetime.fromisoformat(t.get("scheduled_date")) <= now + timedelta(hours=48)
        ]

        report = {
            "timestamp": datetime.now().isoformat(),
            "total_critical": len(critical_tasks),
            "overdue": len(overdue),
            "due_soon": len(due_soon),
            "overdue_tasks": [
                {
                    "task_id": t["task_id"],
                    "client": t.get("client"),
                    "due": t.get("scheduled_date"),
                }
                for t in overdue
            ],
            "due_soon_tasks": [
                {
                    "task_id": t["task_id"],
                    "client": t.get("client"),
                    "due": t.get("scheduled_date"),
                }
                for t in due_soon
            ]
        }

        if overdue:
            logger.warning(f"⚠️ {len(overdue)} critical tasks are overdue!")

        if due_soon:
            logger.info(f"📢 {len(due_soon)} critical tasks due in next 48 hours")

        return report


def main():
    """Test the notification system."""

    system = CommanderNotificationSystem()

    # Test data
    test_tasks = [
        {
            "task_id": "0.3",
            "task_name": "Insurance email",
            "client": "Kuklinski Group",
            "scheduled_date": (datetime.now() + timedelta(days=5)).isoformat(),
            "send_date": (datetime.now() + timedelta(days=12)).isoformat(),
            "priority": "P0"
        },
        {
            "task_id": "1.5",
            "task_name": "Air fare delivery",
            "client": "Kuklinski Group",
            "scheduled_date": (datetime.now() + timedelta(days=10)).isoformat(),
            "send_date": (datetime.now() + timedelta(days=17)).isoformat(),
            "priority": "P0"
        },
    ]

    # Test notification
    system.queue_notification("Kuklinski Group", "kuklinski-group", test_tasks, "INFO")

    # Test digest
    digest = system.generate_daily_digest(test_tasks)
    if digest:
        print(digest)

    # Test critical path monitoring
    report = system.monitor_critical_path(test_tasks)
    print(f"\nCritical Path Report: {json.dumps(report, indent=2, default=str)}")

    logger.info("✅ Notification system test complete")


if __name__ == "__main__":
    main()
