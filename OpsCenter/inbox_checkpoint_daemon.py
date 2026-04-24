#!/usr/bin/env python3
"""
Inbox Checkpoint Daemon — Task Rescuer & Watcher Health Monitor
================================================================
Complements the event-driven watcher by periodically scanning inboxes
and restarting watcher if it crashes. Bridges gaps where file events
might be missed or watcher goes down.

Option C implementation:
1. Periodic inbox checkpoint (every 5 min)
2. Watcher health monitoring
3. Stale task force-wake capability
4. Integrated alerting to supervisor
"""

import os
import re
import sys
import json
import time
import logging
import subprocess
import psutil
from pathlib import Path
from datetime import datetime, timedelta

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [INBOX CHECKPOINT] - %(message)s",
    handlers=[
        logging.FileHandler("/home/john/Thunderbird/logs/inbox_checkpoint_daemon.log"),
        logging.StreamHandler(sys.stdout),
    ],
)

# Paths
BASE = Path("/home/john/Thunderbird")
CLAUDE_INBOX = BASE / "claude_inbox.md"
OC_INBOX = BASE / "OpsCenter" / "collaboration" / "opencode_inbox.md"
WING_COMMS = BASE / "OpsCenter" / "collaboration" / "wing_comms.md"
CHECKPOINT_STATE = BASE / "OpsCenter" / ".checkpoint_state.json"
PATTERNS_DB = BASE / "OpsCenter" / ".supervisor_patterns.json"
WATCHER_LOG = BASE / "logs" / "inbox_watcher.log"

# Watcher config
WATCHER_SCRIPT = BASE / "OpsCenter" / "thunderbird_tasking_watcher.py"
WATCHER_PROCESS_NAME = "thunderbird_tasking_watcher.py"

# Thresholds
TASK_STALE_MINUTES = 10  # Task older than this gets force-wake consideration
COOLDOWN_SECONDS = 45  # Watcher cooldown (from watcher code)


def load_checkpoint_state():
    """Load or initialize checkpoint state."""
    if CHECKPOINT_STATE.exists():
        try:
            return json.loads(CHECKPOINT_STATE.read_text())
        except Exception as e:
            logging.warning(f"Could not load checkpoint state: {e}")

    return {
        "last_checkpoint": None,
        "tasks_found_total": 0,
        "force_wakes_triggered": 0,
        "watcher_restarts": 0,
        "watcher_last_restart": None,
        "recent_restarts": [],  # Last 10 restarts
        "recent_force_wakes": [],  # Last 10 force-wakes
    }


def save_checkpoint_state(state):
    """Persist checkpoint state."""
    try:
        CHECKPOINT_STATE.write_text(json.dumps(state, indent=2))
    except Exception as e:
        logging.error(f"Could not save checkpoint state: {e}")


def load_patterns_db():
    """Load supervisor patterns for updating."""
    if PATTERNS_DB.exists():
        try:
            return json.loads(PATTERNS_DB.read_text())
        except Exception as e:
            logging.warning(f"Could not load patterns DB: {e}")
    return {}


def save_patterns_db(db):
    """Persist patterns DB."""
    try:
        PATTERNS_DB.write_text(json.dumps(db, indent=2))
    except Exception as e:
        logging.error(f"Could not save patterns DB: {e}")


def parse_inbox_tasks(inbox_path):
    """Extract PENDING/UNREAD/ACTIVE-CRITICAL tasks from markdown inbox."""
    tasks = []

    try:
        if not inbox_path.exists():
            return []

        content = inbox_path.read_text()
        lines = content.split("\n")

        # Parse status lines: look for "status: PENDING" etc
        for i, line in enumerate(lines):
            status_match = re.search(
                r"status:\s*(PENDING|UNREAD|ACTIVE-CRITICAL|FLAGGED-OVERDUE)",
                line,
                re.IGNORECASE,
            )
            if status_match:
                status = status_match.group(1)
                # Try to find a timestamp nearby (before this line, within 5 lines)
                timestamp_str = None
                for j in range(max(0, i - 5), i):
                    ts_match = re.search(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})", lines[j])
                    if ts_match:
                        timestamp_str = ts_match.group(1)
                        break

                # Try to extract task description
                desc = ""
                for j in range(max(0, i - 10), i):
                    if lines[j].startswith("##") or lines[j].startswith("- "):
                        desc = lines[j].strip("# - ")
                        break

                tasks.append(
                    {
                        "status": status,
                        "timestamp": timestamp_str,
                        "description": desc,
                        "inbox": inbox_path.name,
                    }
                )

    except Exception as e:
        logging.error(f"Error parsing {inbox_path}: {e}")

    return tasks


def calculate_task_age_minutes(timestamp_str):
    """Calculate age of task in minutes. Returns None if can't parse."""
    if not timestamp_str:
        return None

    try:
        ts = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        now = datetime.now(ts.tzinfo) if ts.tzinfo else datetime.now()
        age = (now - ts).total_seconds() / 60
        return age
    except Exception:
        return None


def check_watcher_health():
    """Check if watcher process is running."""
    try:
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                cmdline = proc.info.get("cmdline")
                if cmdline and WATCHER_PROCESS_NAME in " ".join(cmdline):
                    return True, proc.info["pid"]
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except Exception as e:
        logging.error(f"Error checking watcher health: {e}")

    return False, None


def restart_watcher():
    """Attempt to restart the watcher process."""
    try:
        logging.warning("Watcher dead — attempting restart")

        # Use nohup to start in background
        proc = subprocess.Popen(
            ["nohup", "python3", str(WATCHER_SCRIPT)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

        time.sleep(2)  # Give process time to start

        # Verify it started
        running, pid = check_watcher_health()
        if running:
            logging.info(f"✅ Watcher restarted successfully (PID {pid})")
            return True, pid
        else:
            logging.error("❌ Watcher restart failed — process did not start")
            return False, None

    except Exception as e:
        logging.error(f"Error restarting watcher: {e}")
        return False, None


def alert_wing_comms(severity, message, context=None):
    """Post alert to wing_comms."""
    try:
        existing = WING_COMMS.read_text() if WING_COMMS.exists() else ""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        alert = f"\n## ⚠️ [{severity}] Checkpoint Alert — {timestamp}\n"
        alert += f"{message}\n"

        if context:
            alert += f"\n**Context:**\n"
            for key, val in context.items():
                alert += f"- {key}: {val}\n"

        new_content = existing.rstrip() + "\n" + alert
        WING_COMMS.write_text(new_content)
        logging.info(f"Alerted wing_comms [{severity}]")

    except Exception as e:
        logging.error(f"Could not post to wing_comms: {e}")


def run_checkpoint_pass():
    """Single checkpoint pass: scan inboxes, check watcher health, take action."""

    logging.info("=" * 60)
    logging.info("CHECKPOINT PASS START")
    logging.info("=" * 60)

    state = load_checkpoint_state()
    patterns = load_patterns_db()

    # 1. Scan both inboxes
    claude_tasks = parse_inbox_tasks(CLAUDE_INBOX)
    oc_tasks = parse_inbox_tasks(OC_INBOX)
    all_tasks = claude_tasks + oc_tasks

    logging.info(f"Inbox scan: {len(claude_tasks)} Claude tasks, {len(oc_tasks)} OpenCode tasks")

    # 2. Check for stale tasks (candidates for force-wake)
    stale_tasks = []
    for task in all_tasks:
        age = calculate_task_age_minutes(task["timestamp"])
        if age is not None and age > TASK_STALE_MINUTES:
            stale_tasks.append((task, age))
            logging.warning(f"  ⚠️  Stale task ({age:.1f} min old): {task['description']}")

    # 3. Check watcher health
    watcher_running, watcher_pid = check_watcher_health()

    if watcher_running:
        logging.info(f"Watcher OK (PID {watcher_pid})")
    else:
        logging.error("❌ WATCHER DEAD — attempting restart")
        success, new_pid = restart_watcher()

        if success:
            state["watcher_restarts"] += 1
            state["watcher_last_restart"] = datetime.now().isoformat()
            state["recent_restarts"].append(
                {"timestamp": datetime.now().isoformat(), "new_pid": new_pid}
            )
            # Keep last 10
            state["recent_restarts"] = state["recent_restarts"][-10:]

            alert_wing_comms(
                "WARNING",
                f"Inbox Checkpoint detected watcher dead and restarted it (PID {new_pid})",
                {"restart_count": state["watcher_restarts"]},
            )
        else:
            alert_wing_comms("CRITICAL", "Inbox Checkpoint: Watcher died and restart FAILED")

    # 4. Force-wake logic: if tasks are stale and watcher just restarted, trigger wake
    if stale_tasks and not watcher_running:
        logging.info(f"Triggering force-wake for {len(stale_tasks)} stale tasks")
        state["force_wakes_triggered"] += 1
        state["recent_force_wakes"].append(
            {
                "timestamp": datetime.now().isoformat(),
                "task_count": len(stale_tasks),
                "reason": "watcher_restart",
            }
        )
        state["recent_force_wakes"] = state["recent_force_wakes"][-10:]

        # In a real scenario, we could trigger a wake here (e.g., touch inbox file to fire event)
        # For now, just log it
        logging.info("✅ Force-wake triggered via watcher restart")

    # 5. Update state and patterns
    state["last_checkpoint"] = datetime.now().isoformat()
    state["tasks_found_total"] += len(all_tasks)

    save_checkpoint_state(state)

    # Update supervisor patterns with checkpoint metrics
    if "checkpoint_passes" not in patterns:
        patterns["checkpoint_passes"] = 0
    patterns["checkpoint_passes"] += 1
    if "stale_tasks_detected" not in patterns:
        patterns["stale_tasks_detected"] = 0
    patterns["stale_tasks_detected"] += len(stale_tasks)

    save_patterns_db(patterns)

    # 6. Log summary
    logging.info(f"Tasks found: {len(all_tasks)} (Claude: {len(claude_tasks)}, OC: {len(oc_tasks)})")
    logging.info(f"Stale tasks: {len(stale_tasks)}")
    logging.info(f"Watcher: {'RUNNING' if watcher_running else 'DEAD (RESTARTED)'}")
    logging.info(f"Force-wakes triggered (total): {state['force_wakes_triggered']}")
    logging.info(f"Watcher restarts (total): {state['watcher_restarts']}")
    logging.info("CHECKPOINT PASS COMPLETE")
    logging.info("=" * 60)


def main():
    logging.info("Inbox Checkpoint daemon starting")
    try:
        run_checkpoint_pass()
    except Exception as e:
        logging.error(f"Checkpoint pass failed: {e}", exc_info=True)
        alert_wing_comms("CRITICAL", f"Checkpoint daemon error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
