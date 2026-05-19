#!/usr/bin/env python3
"""
Task Audit Log — Persistent JSONL logging for all HALE-dispatched tasks.

Maintains a rolling audit trail of task execution, SLA tracking, gate hits, escalations,
and costs. Enables COS monitoring daemon to detect failures and alert Commander.

File: /home/john/Thunderbird/OpsCenter/task_audit_log.jsonl
Format: One task record per line (JSONL)

Each record contains:
  - task_id: unique identifier for this task
  - ts_created: ISO 8601 creation timestamp
  - ts_completed: ISO 8601 completion timestamp (null if still running)
  - task_name: human-readable name for logging
  - task_type: research|analysis|intelligence|client_email|briefing|arbitration|etc
  - brain_routed: Brain 1 (DeepSeek) | Brain 2 (Sonnet) | Brain 3 (Opus) | none
  - agent_dispatched: opencode|claude_code|python|none
  - model: claude-haiku|claude-sonnet|claude-opus|deepseek-chat-v3.1|etc
  - status: SPAWNED|RUNNING|COMPLETED|ESCALATED|FAILED
  - escalated: True if task escalated from OpenCode to Claude Code
  - retries_attempted: count of retry attempts before escalation
  - gate_hit: client_send|financial_commit|new_client_contact|strategy_direction|none
  - gate_status: awaiting_approval|approved|denied|none
  - output_file: path where task output was written
  - cost_estimate_usd: estimated cost in USD
  - cost_actual_usd: actual cost in USD (null until completed)
  - elapsed_seconds: execution time in seconds
  - pid: process ID of spawned subprocess (if applicable)
  - log_file: path to task log file (if applicable)
  - error: error message if task failed (null if successful)
  - notes: optional freeform notes for COS
"""

import json
import os
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger("task_audit_log")

AUDIT_LOG_PATH = Path("/home/john/Thunderbird/OpsCenter/task_audit_log.jsonl")
ACTIVE_TASKS_PATH = Path("/home/john/Thunderbird/OpsCenter/active_tasks.json")


class TaskRecord:
    """Represents a single task audit record."""

    def __init__(
        self,
        task_name: str,
        task_type: str,
        task_id: Optional[str] = None,
        sla_minutes: int = 30,
    ):
        self.task_id = task_id or str(uuid.uuid4())[:12]
        self.ts_created = datetime.now(timezone.utc).isoformat()
        self.ts_completed = None
        self.task_name = task_name
        self.task_type = task_type
        self.brain_routed = None
        self.agent_dispatched = None
        self.model = None
        self.status = "SPAWNED"
        self.escalated = False
        self.retries_attempted = 0
        self.gate_hit = None
        self.gate_status = None
        self.output_file = None
        self.cost_estimate_usd = 0.0
        self.cost_actual_usd = None
        self.elapsed_seconds = None
        self.pid = None
        self.log_file = None
        self.error = None
        self.notes = None
        self.sla_minutes = sla_minutes

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "task_id": self.task_id,
            "ts_created": self.ts_created,
            "ts_completed": self.ts_completed,
            "task_name": self.task_name,
            "task_type": self.task_type,
            "brain_routed": self.brain_routed,
            "agent_dispatched": self.agent_dispatched,
            "model": self.model,
            "status": self.status,
            "escalated": self.escalated,
            "retries_attempted": self.retries_attempted,
            "gate_hit": self.gate_hit,
            "gate_status": self.gate_status,
            "output_file": self.output_file,
            "cost_estimate_usd": self.cost_estimate_usd,
            "cost_actual_usd": self.cost_actual_usd,
            "elapsed_seconds": self.elapsed_seconds,
            "pid": self.pid,
            "log_file": self.log_file,
            "error": self.error,
            "notes": self.notes,
            "sla_minutes": self.sla_minutes,
        }


def log_task(record: TaskRecord) -> str:
    """
    Write task record to audit log JSONL file.

    Returns task_id for tracking.
    """
    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(AUDIT_LOG_PATH, "a") as f:
        f.write(json.dumps(record.to_dict()) + "\n")

    logger.info(f"Logged task {record.task_id}: {record.task_name} ({record.status})")
    return record.task_id


def update_task(task_id: str, **updates) -> bool:
    """
    Update a task record in-place (read, modify, rewrite entire file).

    Used when task status changes, completion time known, cost updated, etc.

    Returns True if update succeeded, False if task not found.
    """
    if not AUDIT_LOG_PATH.exists():
        logger.warning(f"Audit log does not exist yet: {AUDIT_LOG_PATH}")
        return False

    records = []
    found = False

    # Read all records
    with open(AUDIT_LOG_PATH, "r") as f:
        for line in f:
            if not line.strip():
                continue
            record_dict = json.loads(line)

            if record_dict["task_id"] == task_id:
                # Update this record
                record_dict.update(updates)
                if "ts_completed" not in updates and updates.get("status") == "COMPLETED":
                    record_dict["ts_completed"] = datetime.now(timezone.utc).isoformat()
                found = True

            records.append(record_dict)

    if not found:
        logger.warning(f"Task {task_id} not found in audit log")
        return False

    # Rewrite entire file
    with open(AUDIT_LOG_PATH, "w") as f:
        for record_dict in records:
            f.write(json.dumps(record_dict) + "\n")

    logger.info(f"Updated task {task_id}: {updates}")
    return True


def load_active_tasks() -> list:
    """
    Load all tasks with status SPAWNED or RUNNING.

    Used by monitoring daemon to check SLA compliance.

    Returns list of task dicts.
    """
    if not AUDIT_LOG_PATH.exists():
        return []

    active = []
    now = datetime.now(timezone.utc)

    with open(AUDIT_LOG_PATH, "r") as f:
        for line in f:
            if not line.strip():
                continue
            record = json.loads(line)

            if record["status"] in ["SPAWNED", "RUNNING"]:
                # Calculate elapsed time
                ts_created = datetime.fromisoformat(record["ts_created"])
                elapsed = (now - ts_created).total_seconds()
                record["elapsed_seconds"] = elapsed

                # Check SLA
                sla_seconds = record["sla_minutes"] * 60
                record["sla_exceeded"] = elapsed > sla_seconds

                active.append(record)

    return active


def load_task(task_id: str) -> Optional[Dict[str, Any]]:
    """Load a single task record by ID."""
    if not AUDIT_LOG_PATH.exists():
        return None

    with open(AUDIT_LOG_PATH, "r") as f:
        for line in f:
            if not line.strip():
                continue
            record = json.loads(line)
            if record["task_id"] == task_id:
                return record

    return None


def list_tasks(status: Optional[str] = None, limit: int = 50) -> list:
    """
    List recent tasks, optionally filtered by status.

    Returns last `limit` tasks (LIFO — most recent first).
    """
    if not AUDIT_LOG_PATH.exists():
        return []

    tasks = []

    with open(AUDIT_LOG_PATH, "r") as f:
        for line in f:
            if not line.strip():
                continue
            record = json.loads(line)

            if status is None or record["status"] == status:
                tasks.append(record)

    # Return most recent first
    return list(reversed(tasks))[-limit:]


def archive_completed_tasks(days: int = 7) -> int:
    """
    Move completed tasks older than `days` to archive file.

    Returns count of tasks archived.
    """
    if not AUDIT_LOG_PATH.exists():
        return 0

    archive_path = AUDIT_LOG_PATH.parent / "task_audit_log.archive.jsonl"
    cutoff = datetime.now(timezone.utc)
    cutoff_ts = cutoff.replace(day=cutoff.day - days).isoformat()

    active = []
    archived = 0

    with open(AUDIT_LOG_PATH, "r") as f:
        for line in f:
            if not line.strip():
                continue
            record = json.loads(line)

            # Keep if still running or completed after cutoff
            if record["status"] in ["SPAWNED", "RUNNING"] or (
                record["ts_completed"] and record["ts_completed"] > cutoff_ts
            ):
                active.append(record)
            else:
                # Archive this record
                with open(archive_path, "a") as arch:
                    arch.write(json.dumps(record) + "\n")
                archived += 1

    # Rewrite active log
    with open(AUDIT_LOG_PATH, "w") as f:
        for record in active:
            f.write(json.dumps(record) + "\n")

    if archived > 0:
        logger.info(f"Archived {archived} completed tasks to {archive_path}")

    return archived


def cost_summary() -> Dict[str, Any]:
    """
    Calculate cost summary from completed tasks.

    Returns dict: total_tasks, total_cost_estimate, total_cost_actual, by_brain, by_agent
    """
    if not AUDIT_LOG_PATH.exists():
        return {
            "total_tasks": 0,
            "total_cost_estimate": 0.0,
            "total_cost_actual": 0.0,
            "by_brain": {},
            "by_agent": {},
        }

    summary = {
        "total_tasks": 0,
        "total_cost_estimate": 0.0,
        "total_cost_actual": 0.0,
        "by_brain": {},
        "by_agent": {},
    }

    with open(AUDIT_LOG_PATH, "r") as f:
        for line in f:
            if not line.strip():
                continue
            record = json.loads(line)

            if record["status"] == "COMPLETED":
                summary["total_tasks"] += 1
                summary["total_cost_estimate"] += record.get("cost_estimate_usd", 0)
                summary["total_cost_actual"] += record.get("cost_actual_usd", 0)

                # By brain
                brain = record.get("brain_routed") or "none"
                if brain not in summary["by_brain"]:
                    summary["by_brain"][brain] = {"count": 0, "cost": 0.0}
                summary["by_brain"][brain]["count"] += 1
                summary["by_brain"][brain]["cost"] += record.get("cost_actual_usd", 0)

                # By agent
                agent = record.get("agent_dispatched") or "none"
                if agent not in summary["by_agent"]:
                    summary["by_agent"][agent] = {"count": 0, "cost": 0.0}
                summary["by_agent"][agent]["count"] += 1
                summary["by_agent"][agent]["cost"] += record.get("cost_actual_usd", 0)

    return summary


if __name__ == "__main__":
    # Quick test
    logging.basicConfig(level=logging.INFO)

    # Create test task
    record = TaskRecord("test_research", "research")
    task_id = log_task(record)
    print(f"Created task: {task_id}")

    # Update it
    update_task(task_id, status="COMPLETED", elapsed_seconds=45.2, cost_actual_usd=0.01)
    print(f"Updated task: {task_id}")

    # Load it
    loaded = load_task(task_id)
    print(f"Loaded: {json.dumps(loaded, indent=2)}")

    # List active
    active = load_active_tasks()
    print(f"Active tasks: {len(active)}")

    # Cost summary
    summary = cost_summary()
    print(f"Cost summary: {json.dumps(summary, indent=2)}")
