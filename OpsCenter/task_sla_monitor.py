#!/usr/bin/env python3
"""
Task SLA Monitoring Daemon — Detects and alerts on SLA violations.

Runs every 60 seconds. Checks for tasks that have exceeded their SLA_MINUTES.
When a violation is detected, sends alert to Commander via:
1. Telegram (@D2MC2C): Urgent notification
2. Email (d2mconcierge): Alert with log file reference
3. Logs to task_sla_violations.log with full context

SLA defaults:
- research: 30 minutes
- analysis: 45 minutes
- intelligence: 20 minutes
- briefing: 60 minutes
- client_email: 15 minutes
- arbitration: 10 minutes
- default: 30 minutes

Standing Order 2026-04-24: "COS alerts when task SLA is exceeded"
"""

import logging
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional
import time

# Add Thunderbird to path
THUNDERBIRD_ROOT = Path("/home/john/Thunderbird")
sys.path.insert(0, str(THUNDERBIRD_ROOT))

from OpsCenter.task_audit_log import load_active_tasks, load_task

logger = logging.getLogger("task_sla_monitor")

# Configure logging
LOG_DIR = THUNDERBIRD_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "task_sla_monitor.log"),
        logging.StreamHandler(),
    ],
)

# SLA definitions (in minutes)
SLA_DEFAULTS = {
    "research": 30,
    "analysis": 45,
    "intelligence": 20,
    "briefing": 60,
    "client_email": 15,
    "arbitration": 10,
    "default": 30,
}

# Track previously alerted tasks (avoid duplicate alerts)
ALERTED_TASKS_FILE = THUNDERBIRD_ROOT / "OpsCenter" / ".sla_alerted_tasks.json"
ALERTED_TASKS = None  # Loaded at daemon startup


def load_alerted_tasks() -> set:
    """Load set of previously alerted task IDs."""
    if ALERTED_TASKS_FILE.exists():
        try:
            with open(ALERTED_TASKS_FILE, "r") as f:
                return set(json.load(f))
        except Exception as e:
            logger.warning(f"Failed to load alerted tasks: {e}")
    return set()


def save_alerted_tasks(task_ids: set) -> None:
    """Save set of alerted task IDs to file."""
    try:
        with open(ALERTED_TASKS_FILE, "w") as f:
            json.dump(list(task_ids), f)
    except Exception as e:
        logger.error(f"Failed to save alerted tasks: {e}")


def get_sla_minutes(task_type: str) -> int:
    """Get SLA for task type."""
    return SLA_DEFAULTS.get(task_type, SLA_DEFAULTS["default"])


def send_alert(task: dict, elapsed_seconds: int, sla_seconds: int) -> None:
    """
    Send alert for SLA violation.

    Channels:
    1. Log to file
    2. Telegram (if available)
    3. Email (if available)
    """
    task_id = task["task_id"]
    task_name = task["task_name"]
    status = task["status"]
    elapsed_min = elapsed_seconds / 60
    sla_min = sla_seconds / 60
    pid = task.get("pid")
    log_file = task.get("log_file")

    # Always log
    logger.error(
        f"SLA VIOLATION: {task_id} ({task_name}) "
        f"elapsed={elapsed_min:.1f}m, sla={sla_min:.1f}m, "
        f"status={status}, pid={pid}"
    )

    # Log to violations file
    violations_log = LOG_DIR / "task_sla_violations.log"
    with open(violations_log, "a") as f:
        f.write(
            json.dumps(
                {
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "task_id": task_id,
                    "task_name": task_name,
                    "status": status,
                    "elapsed_seconds": elapsed_seconds,
                    "sla_seconds": sla_seconds,
                    "pid": pid,
                    "log_file": log_file,
                }
            )
            + "\n"
        )

    # Alert via Telegram (if available)
    try:
        from OpsCenter.thunderbird_telegram_gw import telegram_alert_cos

        alert_msg = (
            f"🚨 **SLA VIOLATION**\n\n"
            f"Task: `{task_id}`\n"
            f"Name: {task_name}\n"
            f"Status: {status}\n"
            f"Elapsed: {elapsed_min:.1f}m (SLA: {sla_min:.1f}m)\n"
            f"PID: {pid}\n"
            f"Log: {log_file}\n"
        )
        telegram_alert_cos(alert_msg)
        logger.info(f"Sent Telegram alert for {task_id}")
    except Exception as e:
        logger.debug(f"Telegram alert failed (non-critical): {e}")

    # Alert via Email (if available)
    try:
        from core.email.thunderbird_gmail import gmail_send_email

        subject = f"⚠️ Task SLA Violation: {task_id}"
        body = f"""Task SLA VIOLATION detected.

Task ID: {task_id}
Task Name: {task_name}
Status: {status}
Elapsed: {elapsed_min:.1f} minutes
SLA Limit: {sla_min:.1f} minutes
PID: {pid}
Log File: {log_file}

This task has exceeded its SLA and requires attention.

---
Sent by COS Task SLA Monitor
"""
        gmail_send_email(
            to=["johnloucks3@gmail.com"],
            subject=subject,
            body=body,
        )
        logger.info(f"Sent email alert for {task_id}")
    except Exception as e:
        logger.debug(f"Email alert failed (non-critical): {e}")


def monitor_cycle() -> int:
    """
    Run one monitoring cycle.

    Returns: count of violations detected
    """
    global ALERTED_TASKS
    active = load_active_tasks()
    violations = 0

    for task in active:
        task_id = task["task_id"]
        task_type = task.get("task_type", "default")
        elapsed_seconds = task.get("elapsed_seconds", 0)
        sla_seconds = get_sla_minutes(task_type) * 60

        if elapsed_seconds > sla_seconds:
            if task_id not in ALERTED_TASKS:
                # New violation
                send_alert(task, elapsed_seconds, sla_seconds)
                ALERTED_TASKS.add(task_id)
                violations += 1
            # else: already alerted, skip

    # Cleanup alerted tasks that are no longer active
    active_ids = {t["task_id"] for t in active}
    completed_alerts = ALERTED_TASKS - active_ids
    if completed_alerts:
        logger.info(f"Cleared {len(completed_alerts)} completed task alerts")
        ALERTED_TASKS -= completed_alerts

    # Persist state
    save_alerted_tasks(ALERTED_TASKS)

    return violations


def daemon_loop(poll_interval_sec: int = 60) -> None:
    """
    Run monitoring daemon loop.

    Polls every poll_interval_sec seconds.
    """
    logger.info(f"Task SLA Monitor daemon starting (poll interval: {poll_interval_sec}s)")

    # Load initial state
    global ALERTED_TASKS
    ALERTED_TASKS = load_alerted_tasks()
    logger.info(f"Loaded {len(ALERTED_TASKS)} previously alerted tasks")

    try:
        iteration = 0
        while True:
            iteration += 1

            try:
                violations = monitor_cycle()
                if iteration % 10 == 0:  # Log health check every 10 iterations
                    logger.info(f"[SLA Monitor] Cycle {iteration}, violations={violations}")
            except Exception as e:
                logger.error(f"Error in monitor cycle: {e}", exc_info=True)

            time.sleep(poll_interval_sec)

    except KeyboardInterrupt:
        logger.info("Task SLA Monitor daemon shutting down")
        sys.exit(0)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Task SLA Monitoring Daemon")
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=60,
        help="Poll interval in seconds (default: 60)",
    )
    parser.add_argument(
        "--once", action="store_true", help="Run one cycle and exit (for testing)"
    )

    args = parser.parse_args()

    if args.once:
        logger.info("Running one monitoring cycle (--once mode)")
        # Set global for this run
        globals()['ALERTED_TASKS'] = load_alerted_tasks()
        violations = monitor_cycle()
        print(f"Violations detected: {violations}")
        sys.exit(0)
    else:
        daemon_loop(args.poll_interval)
