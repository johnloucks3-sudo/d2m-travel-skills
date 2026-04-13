#!/usr/bin/env python3
"""
THUNDERBIRD STAFF TASKING TIMER ENGINE
Automated client deliverable workflow with systemd timers
Dreams2Memories Travel, LLC | Thunderbird OS

Generates 35-touchpoint lifecycle timers for each client booking.
Automates staff workflow: A2 → A6 → A9 → A3 → COS → Commander
"""

import json
import os
import subprocess
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import sys

# Setup logging
LOG_DIR = Path("/home/john/Thunderbird/OpsCenter")
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "timer_engine.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# TASK CATALOG — 35 TOUCHPOINTS (From STAFF_TASKING_TIMER_SCHEMA.md)
# ============================================================================

TASK_CATALOG = {
    # PHASE 0 — ONBOARDING (D+0 to D+30)
    "0.3": {
        "name": "Insurance email",
        "phase": "booking",
        "days_offset": 3,
        "send_day": 7,
        "staff_chain": ["A9", "A3"],
        "priority": "P0",
        "consequence": "Pre-existing waiver expires → coverage void"
    },
    "0.4": {
        "name": "Guest profile forms",
        "phase": "booking",
        "days_offset": 3,
        "send_day": 7,
        "staff_chain": ["A3"],
        "priority": "P0",
        "consequence": "Registration delays → cabin assignment issues"
    },
    "0.5": {
        "name": "Welcome email",
        "phase": "booking",
        "days_offset": 7,
        "send_day": 14,
        "staff_chain": ["A2", "A6", "A9", "A3"],
        "priority": "P1",
        "consequence": "Client feels ignored → poor start"
    },

    # PHASE 1 — DISCOVERY (D+30 to T-12mo)
    "1.4": {
        "name": "Voyage preview",
        "phase": "booking",
        "days_offset": 90,
        "send_day": 104,
        "staff_chain": ["A2", "A6", "A3"],
        "priority": "P1",
        "consequence": "Client plans without vision"
    },
    "1.5": {
        "name": "Air fare delivery",
        "phase": "embark",
        "days_offset": -379,
        "send_day": -365,
        "staff_chain": ["A2", "A3"],
        "priority": "P0",
        "consequence": "Business class inventory vanishes → client pays 2-3×"
    },
    "1.6": {
        "name": "Hotel delivery",
        "phase": "embark",
        "days_offset": -379,
        "send_day": -365,
        "staff_chain": ["A2", "A6", "A3"],
        "priority": "P0",
        "consequence": "Luxury properties fill → inferior options at higher rates"
    },

    # PHASE 2 — MOMENTUM (T-12mo to T-4mo)
    "2.1": {
        "name": "Air booking decision",
        "phase": "embark",
        "days_offset": -334,
        "send_day": -320,
        "staff_chain": ["A2", "A9", "A3"],
        "priority": "P0",
        "consequence": "Air booking window closes"
    },
    "2.3": {
        "name": "Hotel booking rec",
        "phase": "embark",
        "days_offset": -304,
        "send_day": -290,
        "staff_chain": ["A2", "A6", "A9", "A3"],
        "priority": "P0",
        "consequence": "Premium rooms sell out"
    },
    "2.6": {
        "name": "Excursion rec",
        "phase": "embark",
        "days_offset": -194,
        "send_day": -180,
        "staff_chain": ["A2", "A6", "A3"],
        "priority": "P1",
        "consequence": "Popular excursions sell out"
    },
    "2.8": {
        "name": "Excursion confirm",
        "phase": "embark",
        "days_offset": -177,
        "send_day": -173,
        "staff_chain": ["A3"],
        "priority": "P1",
        "consequence": "Excursion slots lost"
    },
    "2.9": {
        "name": "FPD reminder",
        "phase": "fpd",
        "days_offset": -44,
        "send_day": -30,
        "staff_chain": ["A9", "A3"],
        "priority": "P0",
        "consequence": "FPD missed → booking cancellation"
    },
    "2.12": {
        "name": "Dining rec",
        "phase": "embark",
        "days_offset": -104,
        "send_day": -90,
        "staff_chain": ["A2", "A6", "A3"],
        "priority": "P1",
        "consequence": "Specialty restaurants fill"
    },
    "2.14": {
        "name": "FPD confirmation",
        "phase": "fpd",
        "days_offset": 0,
        "send_day": 1,
        "staff_chain": ["A9", "A3"],
        "priority": "P0",
        "consequence": "Payment confirmation delayed"
    },

    # PHASE 3 — PRE-DEPARTURE (T-4mo to T-0)
    "3.1": {
        "name": "Document audit",
        "phase": "embark",
        "days_offset": -104,
        "send_day": -90,
        "staff_chain": ["COS", "A3"],
        "priority": "P0",
        "consequence": "Missing documents → boarding issues"
    },
    "3.3": {
        "name": "Pre-voyage brief",
        "phase": "embark",
        "days_offset": -35,
        "send_day": -21,
        "staff_chain": ["A2", "A6", "A9", "A3"],
        "priority": "P1",
        "consequence": "Client unprepared for voyage"
    },
    "3.5": {
        "name": "Final confirmation",
        "phase": "embark",
        "days_offset": -10,
        "send_day": -7,
        "staff_chain": ["A3"],
        "priority": "P1",
        "consequence": "Client anxiety increases"
    },
    "3.6": {
        "name": "Send-off email",
        "phase": "embark",
        "days_offset": -3,
        "send_day": 0,
        "staff_chain": ["A6", "A3"],
        "priority": "P1",
        "consequence": "Missed emotional touchpoint"
    },

    # PHASE 5 — POST-VOYAGE (T+1 to T+30)
    "5.1": {
        "name": "Welcome home",
        "phase": "disembark",
        "days_offset": -3,
        "send_day": 3,
        "staff_chain": ["A6", "A3"],
        "priority": "P1",
        "consequence": "Relationship cools after voyage"
    },
    "5.2": {
        "name": "Post-voyage survey",
        "phase": "disembark",
        "days_offset": -3,
        "send_day": 7,
        "staff_chain": ["A3"],
        "priority": "P2",
        "consequence": "Feedback window closes"
    },
    "5.3": {
        "name": "Thank you + referral",
        "phase": "disembark",
        "days_offset": 12,
        "send_day": 14,
        "staff_chain": ["A6", "A3"],
        "priority": "P1",
        "consequence": "Referral opportunity missed"
    },
    "5.4": {
        "name": "Next voyage plant",
        "phase": "disembark",
        "days_offset": 28,
        "send_day": 30,
        "staff_chain": ["A2", "A6", "A3"],
        "priority": "P2",
        "consequence": "Client goes to competitor"
    },
}


# ============================================================================
# TIMER CALCULATION ENGINE
# ============================================================================

def calculate_timer_dates(booking_date: datetime, embark_date: datetime,
                          fpd: datetime, disembark_date: Optional[datetime] = None) -> Dict[str, datetime]:
    """
    Dynamically calculates all timer trigger dates based on anchor dates.

    Args:
        booking_date: Client booking date
        embark_date: Ship embarkation date
        fpd: Final Payment Date
        disembark_date: Ship disembarkation date (if known)

    Returns:
        Dict mapping phase names to trigger dates
    """
    # Disembark = embark + ~10 days (typical cruise length)
    if disembark_date is None:
        disembark_date = embark_date + timedelta(days=10)

    return {
        "booking": booking_date,
        "embark": embark_date,
        "fpd": fpd,
        "disembark": disembark_date,
    }


def get_task_trigger_date(task_id: str, phase_dates: Dict[str, datetime]) -> datetime:
    """Get the trigger date for a specific task."""
    task = TASK_CATALOG[task_id]
    phase = task["phase"]
    offset_days = task["days_offset"]

    if phase not in phase_dates:
        return None

    return phase_dates[phase] + timedelta(days=offset_days)


# ============================================================================
# STAFF TASKING AUTOMATION
# ============================================================================

def generate_staff_tasks(task_id: str, client_name: str, client_id: str,
                         trigger_date: datetime, task_info: Dict) -> List[Dict]:
    """
    Generate staff tasking sequence for a task.
    Each staff member in the chain gets a task at specific intervals.

    Staff workflow offsets (days before send):
    - A2 (Research): T-21
    - A6 (Narrative): T-18
    - A9 (Financial): T-16
    - A3 (Dani): T-14
    - COS (Hale): T-7
    - Commander: Send day (T-0)
    """
    staff_chain = task_info.get("staff_chain", [])
    tasks = []

    # Map staff to their lead times
    staff_lead_times = {
        "A2": 21,  # Days before send
        "A6": 18,
        "A9": 16,
        "A3": 14,
        "COS": 7,
    }

    # Calculate send date (trigger_date + days_offset to send_day)
    send_offset = task_info.get("send_day", trigger_date.day)
    send_date = trigger_date + timedelta(days=max(0, task_info.get("send_day", 0) - task_info.get("days_offset", 0)))

    for staff in staff_chain:
        lead_time = staff_lead_times.get(staff, 0)
        task_date = send_date - timedelta(days=lead_time)

        if task_date <= datetime.now():
            # Skip past tasks
            continue

        inbox_map = {
            "A2": "opencode_inbox.md",
            "A6": "claude_inbox.md",
            "A9": "claude_inbox.md",
            "A3": "claude_inbox.md",
            "COS": "claude_inbox.md",
        }

        tasks.append({
            "task_id": task_id,
            "client": client_name,
            "client_id": client_id,
            "assigned_to": staff,
            "task_name": task_info["name"],
            "scheduled_date": task_date.isoformat(),
            "send_date": send_date.isoformat(),
            "priority": task_info.get("priority", "P2"),
            "inbox": inbox_map.get(staff, "claude_inbox.md"),
            "description": f"Task {task_id}: {task_info['name']} for {client_name}"
        })

    return tasks


# ============================================================================
# SYSTEMD TIMER GENERATION
# ============================================================================

def create_systemd_timer(task_id: str, client_id: str, client_name: str,
                         trigger_date: datetime) -> Tuple[str, str]:
    """
    Generate systemd timer and service files.

    Returns:
        (timer_content, service_content)
    """
    timer_name = f"d2m-task-{task_id.replace('.', '-')}-{client_id}".lower()
    trigger_time = trigger_date.strftime("%Y-%m-%d %H:00")

    # Systemd timer
    timer_content = f"""[Unit]
Description=Thunderbird Task {task_id} - {client_name}
Documentation=man:systemd.timer(5)

[Timer]
OnCalendar={trigger_time}
Persistent=true
Unit={timer_name}.service

[Install]
WantedBy=timers.target
"""

    # Systemd service
    service_content = f"""[Unit]
Description=Thunderbird Task {task_id} - {client_name}
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=john
WorkingDirectory=/home/john/Thunderbird
ExecStart=/home/john/Thunderbird/core/scheduling/dispatch_task.py {task_id} {client_id}
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""

    return timer_content, service_content


# ============================================================================
# COMMANDER NOTIFICATION SYSTEM
# ============================================================================

def generate_commander_notification(client_name: str, client_id: str,
                                   upcoming_tasks: List[Dict],
                                   days_until_send: int) -> str:
    """
    Generate a Commander notification for upcoming client deliverables.
    """
    tasks_summary = "\n".join([
        f"  • {t['task_name']} (Task {t['task_id']}) - {t['scheduled_date'][:10]}"
        for t in upcoming_tasks[:3]  # Show top 3
    ])

    notification = f"""
[READY FOR REVIEW] Client Lifecycle Task Pipeline

**Client:** {client_name} ({client_id})
**Days Until Send:** {days_until_send}

**Upcoming Tasks:**
{tasks_summary}

**Next Action:** Review draft when COS surfaces in {days_until_send - 7} days

---
Sent from Thunderbird Timer Engine
"""
    return notification


# ============================================================================
# MAIN ENGINE
# ============================================================================

class TimerEngine:
    """Orchestrates timer generation and staff automation."""

    def __init__(self):
        self.clients: List[Dict] = []
        self.timers: Dict[str, Dict] = {}
        self.tasks: List[Dict] = []

    def load_client(self, client_data: Dict) -> None:
        """Load client booking data."""
        self.clients.append(client_data)
        logger.info(f"Loaded client: {client_data.get('name')}")

    def generate_all_timers(self) -> None:
        """Generate all timers for all clients."""
        for client in self.clients:
            self.generate_client_timers(client)

    def generate_client_timers(self, client_data: Dict) -> None:
        """Generate all 35-touchpoint timers for a single client."""
        client_id = client_data.get("id", "unknown")
        client_name = client_data.get("name", "unknown")

        # Skip F&F / non-commercial clients — no lifecycle timers for friends/family
        if client_data.get("exclude_from_timers") or client_data.get("service_type") == "F&F":
            logger.info(f"Skipping {client_name} — F&F service, no lifecycle timers.")
            return

        # Parse dates
        booking_date = datetime.fromisoformat(client_data["booking_date"])
        embark_date = datetime.fromisoformat(client_data["embark_date"])
        fpd = datetime.fromisoformat(client_data["fpd"])
        disembark_date = datetime.fromisoformat(client_data.get("disembark_date", ""))

        # Calculate all phase dates
        phase_dates = calculate_timer_dates(booking_date, embark_date, fpd, disembark_date)

        # Generate timers for each task
        for task_id, task_info in TASK_CATALOG.items():
            trigger_date = get_task_trigger_date(task_id, phase_dates)

            if trigger_date is None:
                logger.warning(f"Skipping task {task_id}: unknown phase {task_info['phase']}")
                continue

            # Store timer
            timer_key = f"{client_id}-{task_id}"
            self.timers[timer_key] = {
                "client_id": client_id,
                "client_name": client_name,
                "task_id": task_id,
                "trigger_date": trigger_date.isoformat(),
                "task_name": task_info["name"],
                "priority": task_info.get("priority", "P2"),
            }

            # Generate staff tasks
            staff_tasks = generate_staff_tasks(task_id, client_name, client_id,
                                              trigger_date, task_info)
            self.tasks.extend(staff_tasks)

            logger.debug(f"Generated timer for task {task_id} on {trigger_date.date()}")

    def export_timers_json(self, output_path: str) -> None:
        """Export timer schedule as JSON."""
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        with open(output, "w") as f:
            json.dump({
                "generated_at": datetime.now().isoformat(),
                "total_timers": len(self.timers),
                "total_tasks": len(self.tasks),
                "timers": self.timers,
                "staff_tasks": self.tasks,
            }, f, indent=2, default=str)

        logger.info(f"Exported timers to {output_path}")

    def export_tasks_to_inbox(self, output_path: str) -> None:
        """Export staff tasks to inbox files."""
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        # Group tasks by inbox
        tasks_by_inbox = {}
        for task in self.tasks:
            inbox = task.get("inbox", "claude_inbox.md")
            if inbox not in tasks_by_inbox:
                tasks_by_inbox[inbox] = []
            tasks_by_inbox[inbox].append(task)

        # Write to inbox files
        for inbox_name, tasks in tasks_by_inbox.items():
            inbox_path = output / inbox_name
            with open(inbox_path, "a") as f:
                f.write(f"\n\n---\n## AUTO-GENERATED STAFF TASKS ({datetime.now().date()})\n\n")
                for task in tasks:
                    f.write(f"- [{task['assigned_to']}] {task['task_name']} for {task['client']} (Task {task['task_id']}) - Due: {task['scheduled_date'][:10]}\n")

        logger.info(f"Exported {len(self.tasks)} tasks to inbox files")

    def generate_health_report(self) -> Dict:
        """Generate system health report."""
        # Count timers by priority
        priority_counts = {}
        for timer in self.timers.values():
            priority = timer.get("priority", "P2")
            priority_counts[priority] = priority_counts.get(priority, 0) + 1

        # Count upcoming tasks (next 30 days)
        now = datetime.now()
        upcoming_30d = sum(1 for task in self.tasks
                          if now <= datetime.fromisoformat(task["scheduled_date"]) <= now + timedelta(days=30))

        return {
            "total_timers": len(self.timers),
            "total_tasks": len(self.tasks),
            "priority_breakdown": priority_counts,
            "upcoming_30d": upcoming_30d,
            "critical_path_coverage": {
                "insurance": any("0.3" in t for t in self.timers),
                "air_fares": any("1.5" in t for t in self.timers),
                "hotels": any("1.6" in t for t in self.timers),
                "fpd_reminder": any("2.9" in t for t in self.timers),
            }
        }


# ============================================================================
# ENTRY POINT — TEST WITH KUKLINSKI DATA
# ============================================================================

def main():
    """Run timer engine with Kuklinski test data."""
    engine = TimerEngine()

    # Kuklinski test data
    kuklinski_data = {
        "id": "kuklinski-group",
        "name": "Kuklinski Group (3 bookings)",
        "ship": "Viking Mars",
        "voyage": "Panama Canal",
        "booking_date": "2026-02-20",  # Estimated from dossier
        "embark_date": "2026-12-17",
        "disembark_date": "2026-12-27",
        "fpd": "2026-03-31",
    }

    engine.load_client(kuklinski_data)
    engine.generate_all_timers()

    # Export results
    output_dir = Path("/home/john/Thunderbird/OpsCenter/timer_output")
    output_dir.mkdir(parents=True, exist_ok=True)

    engine.export_timers_json(str(output_dir / "timer_schedule.json"))
    engine.export_tasks_to_inbox(output_dir)

    # Generate health report
    health = engine.generate_health_report()
    with open(output_dir / "health_report.json", "w") as f:
        json.dump(health, f, indent=2)

    # Log summary
    logger.info(f"✅ Timer engine complete")
    logger.info(f"   Total timers: {health['total_timers']}")
    logger.info(f"   Total staff tasks: {health['total_tasks']}")
    logger.info(f"   Upcoming (30d): {health['upcoming_30d']}")
    logger.info(f"   Critical path coverage: {health['critical_path_coverage']}")

    print(f"\n✅ TIMER ENGINE COMPLETE")
    print(f"   Generated {health['total_timers']} timers")
    print(f"   Generated {health['total_tasks']} staff tasks")
    print(f"   Output: {output_dir}")

    return engine


if __name__ == "__main__":
    main()
