#!/usr/bin/env python3
"""
Task Dispatch Integration — Wrappers for dispatch patterns that auto-log to audit trail.

Provides decorators and context managers for the four dispatch patterns:
1. dispatch_to_headless_claude (OpenCode → Brain 1)
2. dispatch_with_fallback (OpenCode → Claude Code escalation)
3. invoke_persona_sdk (Agent SDK → Brain 2)
4. call_deepseek_reasoning (Arbitration → Brain 3)

Usage:
    from task_dispatch_integration import tracked_dispatch

    record = tracked_dispatch(
        task_name="daily_intelligence_sweep",
        task_type="intelligence",
        sla_minutes=20
    )

    # ... do actual dispatch logic ...

    record.brain_routed = "Brain 1"
    record.agent_dispatched = "opencode"
    record.model = "deepseek-chat-v3.1"
    record.pid = proc.pid
    record.output_file = "/path/to/output.txt"
    record.log_file = "/path/to/log.log"

    record.log()  # Write to audit trail

    # Later, when task completes:
    update_task_result(
        task_id=record.task_id,
        status="COMPLETED",
        elapsed_seconds=45.2,
        cost_actual_usd=0.01
    )
"""

import sys
from pathlib import Path
from typing import Optional, Dict, Any
import time

THUNDERBIRD_ROOT = Path("/home/john/Thunderbird")
sys.path.insert(0, str(THUNDERBIRD_ROOT))

from OpsCenter.task_audit_log import TaskRecord, log_task, update_task


def tracked_dispatch(
    task_name: str,
    task_type: str,
    sla_minutes: int = 30,
    cost_estimate_usd: float = 0.0,
) -> TaskRecord:
    """
    Create and return a TaskRecord for tracked dispatch.

    Usage:
        record = tracked_dispatch(
            task_name="daily_intelligence",
            task_type="intelligence",
            sla_minutes=20
        )

        # Dispatch logic here...

        record.brain_routed = "Brain 1"
        record.agent_dispatched = "opencode"
        record.pid = proc.pid
        record.output_file = output_path
        record.log_file = log_path

        log_task(record)  # Write to audit trail
    """
    record = TaskRecord(
        task_name=task_name,
        task_type=task_type,
        sla_minutes=sla_minutes,
    )
    record.cost_estimate_usd = cost_estimate_usd
    return record


def update_task_result(
    task_id: str,
    status: str,
    elapsed_seconds: Optional[float] = None,
    cost_actual_usd: Optional[float] = None,
    error: Optional[str] = None,
    gate_hit: Optional[str] = None,
    gate_status: Optional[str] = None,
    notes: Optional[str] = None,
) -> bool:
    """
    Update a task record with final result.

    Usage:
        update_task_result(
            task_id=record.task_id,
            status="COMPLETED",
            elapsed_seconds=45.2,
            cost_actual_usd=0.01
        )

    Or for gate hits:
        update_task_result(
            task_id=record.task_id,
            status="COMPLETED",
            gate_hit="client_send",
            gate_status="awaiting_approval"
        )
    """
    updates = {
        "status": status,
    }

    if elapsed_seconds is not None:
        updates["elapsed_seconds"] = elapsed_seconds

    if cost_actual_usd is not None:
        updates["cost_actual_usd"] = cost_actual_usd

    if error is not None:
        updates["error"] = error

    if gate_hit is not None:
        updates["gate_hit"] = gate_hit

    if gate_status is not None:
        updates["gate_status"] = gate_status

    if notes is not None:
        updates["notes"] = notes

    return update_task(task_id, **updates)


class TaskContext:
    """Context manager for tracked task dispatch."""

    def __init__(
        self,
        task_name: str,
        task_type: str,
        sla_minutes: int = 30,
        cost_estimate_usd: float = 0.0,
    ):
        self.task_name = task_name
        self.task_type = task_type
        self.sla_minutes = sla_minutes
        self.cost_estimate_usd = cost_estimate_usd
        self.record = None
        self.start_time = None
        self.error = None

    def __enter__(self) -> TaskRecord:
        """Create and log task record on entry."""
        self.start_time = time.time()
        self.record = tracked_dispatch(
            task_name=self.task_name,
            task_type=self.task_type,
            sla_minutes=self.sla_minutes,
            cost_estimate_usd=self.cost_estimate_usd,
        )
        self.record.log()
        return self.record

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Update task record on exit."""
        if self.record is None:
            return

        elapsed = time.time() - self.start_time

        if exc_type is not None:
            # Exception occurred
            update_task_result(
                task_id=self.record.task_id,
                status="FAILED",
                elapsed_seconds=elapsed,
                error=str(exc_val),
            )
        # else: caller should update status via update_task_result()


# Example usage patterns (for documentation):

"""
PATTERN 1: OpenCode dispatch with tracking

from OpsCenter.task_dispatch_integration import tracked_dispatch

record = tracked_dispatch(
    task_name="daily_intelligence_sweep",
    task_type="intelligence",
    sla_minutes=20,
    cost_estimate_usd=0.05
)

# ... call dispatch_to_headless_claude() ...
result = dispatch_to_headless_claude(
    task_description="Run intelligence sweep on cruise lines",
    output_file_path="/home/john/Thunderbird/output/intel.txt",
    task_name=record.task_id
)

if result["status"] == "SPAWNED":
    record.brain_routed = "Brain 1"
    record.agent_dispatched = "opencode"
    record.model = "deepseek-chat-v3.1"
    record.pid = result["pid"]
    record.output_file = result["output_file"]
    record.log_file = result["log_file"]
    log_task(record)

# Later, monitor for completion and update:
update_task_result(
    task_id=record.task_id,
    status="COMPLETED",
    elapsed_seconds=45.2,
    cost_actual_usd=0.01
)


PATTERN 2: Claude Code with context manager

from OpsCenter.task_dispatch_integration import TaskContext

with TaskContext(
    task_name="client_validation_email",
    task_type="client_email",
    sla_minutes=15
) as record:
    # Dispatch Claude Code
    result = dispatch_with_fallback(
        task_description="Draft validation email for Kuklinski",
        output_file_path=f"/home/john/Thunderbird/output/validation_{record.task_id}.html",
        task_name=record.task_id
    )

    record.brain_routed = "Brain 2"
    record.agent_dispatched = "claude_code"
    record.model = "claude-sonnet-4-6"
    record.pid = result["pid"]
    record.output_file = result["output_file"]
    record.log_file = result["log_file"]
    record.log()

    # Task runs in background
    # COS monitors and updates on completion


PATTERN 3: Arbitration with tracking

from OpsCenter.task_dispatch_integration import tracked_dispatch

record = tracked_dispatch(
    task_name="pricing_arbitration",
    task_type="arbitration",
    sla_minutes=10,
    cost_estimate_usd=0.0  # DeepSeek R1 is free
)

result = call_deepseek_reasoning(
    prompt="DECISION: Which cruise line fits the client best? ... DECIDE: ..."
)

record.brain_routed = "Brain 3"
record.agent_dispatched = "deepseek_r1"
record.model = "deepseek-r1"
record.status = "COMPLETED"
record.output_file = "/path/to/decision.txt"
record.log()

update_task_result(
    task_id=record.task_id,
    status="COMPLETED",
    elapsed_seconds=8.3,
    cost_actual_usd=0.0
)
"""

if __name__ == "__main__":
    # Test basic tracking
    record = tracked_dispatch(
        task_name="test_task",
        task_type="research",
        sla_minutes=30,
    )

    print(f"Created task: {record.task_id}")
    print(f"Task record: {record.to_dict()}")

    # Log it
    record.brain_routed = "Brain 1"
    record.agent_dispatched = "opencode"
    record.model = "deepseek-chat-v3.1"
    log_task(record)

    print(f"Logged task")

    # Update it
    import time

    time.sleep(1)
    updated = update_task_result(
        task_id=record.task_id,
        status="COMPLETED",
        elapsed_seconds=1.0,
        cost_actual_usd=0.001,
    )
    print(f"Updated task: {updated}")
