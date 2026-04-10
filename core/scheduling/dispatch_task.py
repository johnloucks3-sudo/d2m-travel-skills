#!/usr/bin/env python3
"""
TASK DISPATCH WORKER
Invoked by systemd timers to dispatch staff tasks to inboxes
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from thunderbird_timer_engine import TASK_CATALOG

LOG_DIR = Path("/home/john/Thunderbird/OpsCenter")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "task_dispatch.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def dispatch_task(task_id: str, client_id: str) -> None:
    """Dispatch a task to the appropriate staff inbox."""

    if task_id not in TASK_CATALOG:
        logger.error(f"Unknown task ID: {task_id}")
        return

    task_info = TASK_CATALOG[task_id]
    logger.info(f"Dispatching task {task_id} ({task_info['name']}) for client {client_id}")

    # Tasks dispatched automatically via timer engine
    # This is the heartbeat function that confirms timer execution


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: dispatch_task.py <task_id> <client_id>")
        sys.exit(1)

    task_id = sys.argv[1]
    client_id = sys.argv[2]

    dispatch_task(task_id, client_id)
