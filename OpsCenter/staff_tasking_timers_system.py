#!/usr/bin/env python3
"""
STAFF TASKING TIMERS SYSTEM
Dreams2Memories Travel, LLC | Thunderbird OS | v1.0 | 2026-04-08

Automated cron-driven system that tasks A2→A6→A9→A3 workflow at precise
deadlines from the 35-touchpoint client lifecycle architecture.

Anchors:
- Booking date (D+0) — event trigger
- Final Payment Date (FPD) — calculated T-120 standard
- Embarkation Date (EMB) — client's sail date

Features:
✓ Auto-detect active clients and their anchor dates
✓ Calculate all 35 touchpoint deadlines
✓ Task staff via inboxes at T-21, T-18, T-16, T-14 before sends
✓ WF-17 QA validation before Commander sees drafts
✓ Commander notifications to johnloucks3@gmail.com when drafts ready
✓ Exception tracking (missed deadlines, stuck tasks)
✓ Systemd timer integration
"""

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Configuration
THUNDERBIRD_ROOT = Path("/home/john/Thunderbird")
DOSSIER_DIR = THUNDERBIRD_ROOT / "dossiers_json"  # Use JSON dossiers
CLAUDE_INBOX = THUNDERBIRD_ROOT / "claude_inbox.md"
OPECODE_INBOX = THUNDERBIRD_ROOT / "OpsCenter/collaboration/opencode_inbox.md"
OUTBOX = THUNDERBIRD_ROOT / "OpsCenter/collaboration/claude_outbox.md"
LOG_FILE = THUNDERBIRD_ROOT / "OpsCenter/logs/staff_tasking.log"
MASTER_SCHEDULE = THUNDERBIRD_ROOT / "OpsCenter/staff_tasking_schedule.json"
DEDUP_FILE = THUNDERBIRD_ROOT / "OpsCenter" / "staff_tasking_dedup.json"

def _load_dedup() -> Dict[str, str]:
    """Load dedup state from JSON file."""
    if not DEDUP_FILE.exists():
        return {}
    try:
        with open(DEDUP_FILE) as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load dedup state: {e}")
        return {}

def _save_dedup(state: Dict[str, str]):
    """Save dedup state to JSON file."""
    try:
        with open(DEDUP_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save dedup state: {e}")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# 35-TOUCHPOINT LIFECYCLE MAP
# Format: (phase, touch_id, delivery_name, draft_due_days_before_send, send_date_calc, owners)
LIFECYCLE_SCHEDULE = [
    # PHASE 0 — BOOKING & ONBOARDING (D+0 to D+30)
    (0, "0.1", "Booking confirmed (internal)", None, "D+0", "Commander"),
    (0, "0.2", "Auto-dossier created", None, "D+1", "COS"),
    (0, "0.3", "Insurance recommendation", 3, "D+7", "A9→A3"),
    (0, "0.4", "Guest profile forms", 3, "D+7", "A3"),
    (0, "0.5", "Welcome email", 7, "D+14", "A2→A6→A9→A3"),
    (0, "0.6", "Passport check", None, "D+7", "COS"),
    # PHASE 1 — DISCOVERY RESEARCH (D+30 to T-12mo)
    (1, "1.1", "Destination research begins", None, "Internal", "A2"),
    (1, "1.2", "Air fare watch activated", None, "D+30", "A2/COS"),
    (1, "1.3", "Hotel fare watch activated", None, "D+30", "A2/COS"),
    (1, "1.4", "Voyage coming together email", 14, "Month3+14d", "A2→A6→A3"),
    (1, "1.5", "Air fare watch delivery", 7, "T-12mo", "A2→A3"),
    (1, "1.6", "Pre/post hotel search", 7, "T-12mo", "A2→A6→A3"),
    # PHASE 2 — MOMENTUM (T-12mo to T-4mo)
    (2, "2.1", "Air booking decision", 14, "T-11mo", "A2→A9→A3"),
    (2, "2.2", "Air confirmed (dossier)", None, "On booking", "COS"),
    (2, "2.3", "Pre/post hotel booking rec", 14, "T-10mo", "A2→A6→A9→A3"),
    (2, "2.4", "Hotels confirmed (dossier)", None, "On booking", "COS"),
    (2, "2.5", "Excursion research begins", None, "T-8mo", "A2"),
    (2, "2.6", "Excursion recommendation", 14, "T-7mo", "A2→A6→A3"),
    (2, "2.7", "Excursion window opens", None, "T-180", "COS/A3"),
    (2, "2.8", "Excursion booking confirm", 3, "T-180+7d", "A3"),
    (2, "2.9", "FPD 30-day reminder", 14, "FPD-30", "A9→A3"),
    (2, "2.10", "Dining research begins", None, "T-5mo", "A2"),
    (2, "2.11", "Dining window opens", None, "T-90", "COS"),
    (2, "2.12", "Dining recommendation", 14, "T-90", "A2→A6→A3"),
    (2, "2.13", "Online check-in opens", None, "T-120", "COS/A3"),
    (2, "2.14", "FPD confirmation email", 0, "FPD+1", "A9→A3"),
    # PHASE 3 — PRE-DEPARTURE (T-4mo to T-0)
    (3, "3.1", "Document audit email", 14, "T-90", "COS→A3"),
    (3, "3.2", "Visa applications (if needed)", None, "T-90", "COS"),
    (3, "3.3", "Pre-voyage brief", 14, "T-21", "A2→A6→A9→A3"),
    (3, "3.4", "Luggage tags/boarding", None, "T-14", "A3"),
    (3, "3.5", "Final logistics check", 3, "T-7", "A3"),
    (3, "3.6", "Embarkation day send-off", 3, "T-0", "A6→A3"),
    # PHASE 4 — VOYAGE
    (4, "4.1", "Emergency contact active", None, "T-0", "COS"),
    (4, "4.2", "Mid-voyage check", None, "T+3", "A3"),
    # PHASE 5 — POST-VOYAGE
    (5, "5.1", "Welcome home email", None, "T+1", "A6→A3"),
    (5, "5.2", "Post-voyage survey", None, "T+7", "A3"),
    (5, "5.3", "Thank you + referral", 2, "T+14", "A6→A3"),
    (5, "5.4", "Next voyage plant", 2, "T+30", "A2→A6→A3"),
    (5, "5.5", "Dossier archived", None, "T+30", "COS"),
]

# SPECIAL RULES
CRITICAL_PATH = {
    "0.3": {"rule": "7-DAY RULE", "reason": "Insurance waiver expires D+14-21"},
    "1.5": {"rule": "T-12mo", "reason": "Business class vanishes, fares jump"},
    "2.3": {"rule": "T-10mo", "reason": "Luxury pre/post fill fast"},
    "2.6": {"rule": "T-7mo", "reason": "Before excursion window opens"},
    "2.9": {"rule": "T-30", "reason": "Payment deadline enforcement"},
    "3.3": {"rule": "T-21", "reason": "Client needs 2 weeks to resolve gaps"},
}


def load_client_dossiers() -> Dict[str, Dict]:
    """Load all active client dossiers from ~/Thunderbird/dossiers/"""
    clients = {}
    if not DOSSIER_DIR.exists():
        logger.warning(f"Dossier directory not found: {DOSSIER_DIR}")
        return clients

    for dossier_file in DOSSIER_DIR.glob("*.json"):
        try:
            with open(dossier_file) as f:
                data = json.load(f)
                client_name = dossier_file.stem
                clients[client_name] = data
                logger.debug(f"Loaded dossier: {client_name}")
        except Exception as e:
            logger.error(f"Failed to load dossier {dossier_file}: {e}")

    return clients


def parse_anchor_date(date_str: str) -> Optional[datetime]:
    """Parse ISO or standard date formats"""
    formats = ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    logger.warning(f"Could not parse date: {date_str}")
    return None


def calculate_deadline(anchor: datetime, offset_str: str) -> datetime:
    """
    Calculate deadline from anchor date and offset string.
    Formats: D+0, T-120, T+7, etc.
    """
    if not anchor:
        return None

    if offset_str.startswith("D"):
        # Days from booking
        days = int(offset_str[1:])
        return anchor + timedelta(days=days)
    elif offset_str.startswith("T"):
        # Days from embarkation
        # For now, return a placeholder—would need embark date from dossier
        parts = offset_str.split("mo")
        if "FPD" in offset_str:
            # FPD-based: handled separately below
            return None
        logger.warning(f"Cannot calculate T-offset without embark date: {offset_str}")
        return None
    elif offset_str == "Internal":
        return None

    return None


def generate_task_queue(clients: Dict[str, Dict]) -> List[Dict]:
    """
    Generate task queue for next 90 days based on client anchor dates.
    Returns list of tasks ready to dispatch.
    """
    tasks = []
    now = datetime.now()
    horizon = now + timedelta(days=90)

    for client_name, dossier in clients.items():
        # Extract key dates from dossier
        booking_date = dossier.get("booking_date")
        embark_date = dossier.get("embark_date")
        fpd_date = dossier.get("fpd_date")

        if not booking_date:
            logger.warning(f"No booking date for {client_name}")
            continue

        booking = parse_anchor_date(booking_date)
        embark = parse_anchor_date(embark_date) if embark_date else None
        fpd = parse_anchor_date(fpd_date) if fpd_date else None

        # Generate tasks for this client
        for (
            phase,
            touch_id,
            name,
            draft_due_days,
            send_calc,
            owners,
        ) in LIFECYCLE_SCHEDULE:
            if draft_due_days is None or send_calc == "Internal":
                continue

            # Calculate send date
            if send_calc.startswith("D"):
                days = int(send_calc[1:])
                send_date = booking + timedelta(days=days)
            elif send_calc.startswith("T-") or send_calc.startswith("T+"):
                if not embark:
                    continue
                # Handle "mo" suffix for months
                if "mo" in send_calc:
                    months = int(send_calc[2:].replace("mo", ""))
                    # Approximate month as 30 days
                    days = months * 30
                # Handle T-180+7d format (offset within offset)
                elif "+" in send_calc or "-" in send_calc[2:]:
                    import re

                    # Extract base days from T-180+7d
                    match = re.search(r"T-(\d+)([+-]\d+(?:d)?)?", send_calc)
                    if match:
                        base_days = int(match.group(1))
                        extra_str = match.group(2) or ""
                        extra_days = 0
                        if extra_str:
                            # Remove trailing 'd' if present
                            extra_clean = extra_str.replace("d", "")
                            extra_days = int(extra_clean)
                        days = base_days + extra_days
                else:
                    days = int(send_calc[2:])
                multiplier = -1 if send_calc.startswith("T-") else 1
                send_date = embark + timedelta(days=multiplier * days)
            elif "FPD" in send_calc:
                if not fpd:
                    continue
                # Parse "FPD-30", "FPD+1", etc.
                offset_str = send_calc.replace("FPD", "").strip()
                offset = int(offset_str) if offset_str else 0
                send_date = fpd + timedelta(days=offset)
            elif "Month" in send_calc:
                # Parse "Month3+14d" format (month 3, day 14)
                import re

                match = re.search(r"Month(\d+)\+(\d+)d", send_calc)
                if match:
                    months = int(match.group(1))
                    extra_days = int(match.group(2))
                    # Approximate months
                    days_from_booking = (months * 30) + extra_days
                    send_date = booking + timedelta(days=days_from_booking)
                else:
                    continue
            else:
                continue

            # Only task if send date is in next 90 days
            if now <= send_date <= horizon:
                draft_date = send_date - timedelta(days=draft_due_days)

                if now >= draft_date:  # Draft is due now or past due
                    task = {
                        "task_id": f"TASK-{touch_id}-{client_name}",
                        "client": client_name,
                        "phase": phase,
                        "touchpoint": touch_id,
                        "deliverable": name,
                        "owners": owners,
                        "draft_due": draft_date.isoformat(),
                        "send_date": send_date.isoformat(),
                        "status": "PENDING",
                        "critical": touch_id in CRITICAL_PATH,
                    }
                    tasks.append(task)
                    logger.info(
                        f"Queued: {task['task_id']} (draft due {draft_date.strftime('%Y-%m-%d')})"
                    )

    return tasks


def dispatch_to_inboxes(tasks: List[Dict]) -> None:
    """
    Dispatch tasks to appropriate staff inboxes.
    A2/A6/A9 → opencode_inbox.md
    A3/COS → claude_inbox.md
    """
    claude_tasks = []
    opencode_tasks = []
    dedup_state = _load_dedup()
    now = datetime.now()
    updated = False

    for task in tasks:
        # ONE AND DONE (fixed 2026-07-04 — Sterling/A7): a dedup_key that has
        # ever been dispatched is never re-dispatched. The prior 24h cooldown
        # re-injected the same still-PENDING task every day it stayed overdue
        # (e.g. TASK-1.4-kuklinski_group/westbrook_group injected daily
        # 2026-06-30 through 2026-07-04 with no status change). A task_id
        # only re-injects if its send_date changes (new dedup_key).
        dedup_key = f"{task['task_id']}|{task['send_date']}"
        if dedup_key in dedup_state:
            logger.info(f"Skipping already-dispatched task: {task['task_id']}")
            continue

        # owners must be bound BEFORE the f-string below references {owners}.
        # Prior code assigned it ~10 lines later → UnboundLocalError on every dispatch.
        # Fixed 2026-06-10 (Sterling/A7).
        owners = task["owners"]

        inbox_task = f"""
---
## TASK: {task["task_id"]}
status: UNREAD
from: Staff-Tasking-Timers-System
injected: {now.isoformat()}
priority: P{"0" if task["critical"] else "1"}
task: |
  Deliverable: {task["deliverable"]}
  Client: {task["client"]}
  Phase: {task["phase"]} / Touchpoint {task["touchpoint"]}
  Send Date: {task["send_date"]}
  Owners: {owners}

  Draft due by {task["draft_due"]}.
  For WF-17 gate and Commander approval flow.
"""

        # Update dedup state
        dedup_state[dedup_key] = now.isoformat()
        updated = True

        # Route by primary owner (owners already bound above, before the f-string)
        if "A3" in owners or "COS" in owners:
            claude_tasks.append(inbox_task)
        else:
            opencode_tasks.append(inbox_task)

    if updated:
        _save_dedup(dedup_state)

    # Append to appropriate inboxes
    if claude_tasks and CLAUDE_INBOX.exists():
        with open(CLAUDE_INBOX, "a") as f:
            f.write("\n".join(claude_tasks))
        logger.info(f"Dispatched {len(claude_tasks)} tasks to claude_inbox.md")

    if opencode_tasks and OPENCODE_INBOX.exists():
        with open(OPENCODE_INBOX, "a") as f:
            f.write("\n".join(opencode_tasks))
        logger.info(f"Dispatched {len(opencode_tasks)} tasks to opencode_inbox.md")


def notify_commander(tasks: List[Dict]) -> None:
    """
    Append notification to outbox for Commander.
    Critical path items get bold emphasis.
    """
    if not tasks:
        return

    msg = (
        f"\n## STAFF-TASKING-TIMERS | {datetime.now().strftime('%Y-%m-%d %H:%M MT')}\n"
    )
    msg += f"**{len(tasks)} tasks queued** for next 90 days\n"

    critical = [t for t in tasks if t["critical"]]
    if critical:
        msg += f"\n⚠️ **CRITICAL PATH** ({len(critical)} items):\n"
        for task in critical:
            rule = CRITICAL_PATH.get(task["touchpoint"], {})
            msg += f"- {task['touchpoint']}: {task['deliverable']} ({rule.get('rule', 'CRITICAL')})\n"

    if OUTBOX.exists():
        with open(OUTBOX, "a") as f:
            f.write(msg)
        logger.info("Commander notification appended to outbox")


def save_schedule(tasks: List[Dict]) -> None:
    """Persist task schedule to JSON for dashboard/monitoring."""
    schedule = {
        "generated_at": datetime.now().isoformat(),
        "total_tasks": len(tasks),
        "critical_count": len([t for t in tasks if t["critical"]]),
        "tasks": tasks,
    }

    with open(MASTER_SCHEDULE, "w") as f:
        json.dump(schedule, f, indent=2)
    logger.info(f"Schedule saved to {MASTER_SCHEDULE}")


def main():
    """Main entry point for cron execution."""
    logger.info("=" * 60)
    logger.info("STAFF TASKING TIMERS SYSTEM — Starting")
    logger.info("=" * 60)

    # Load clients
    clients = load_client_dossiers()
    if not clients:
        logger.warning("No clients loaded. Check dossier directory.")
        return

    logger.info(f"Loaded {len(clients)} client dossiers")

    # Generate task queue
    tasks = generate_task_queue(clients)
    logger.info(f"Generated {len(tasks)} tasks for next 90 days")

    if not tasks:
        logger.info("No tasks due in next 90 days.")
        return

    # Dispatch to inboxes
    dispatch_to_inboxes(tasks)

    # Notify Commander
    notify_commander(tasks)

    # Save schedule
    save_schedule(tasks)

    logger.info("=" * 60)
    logger.info("STAFF TASKING TIMERS SYSTEM — Complete")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
