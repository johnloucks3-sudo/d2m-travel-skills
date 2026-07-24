#!/usr/bin/env python3
"""
Batched email processor: dedupes and batches email intelligence tasks
instead of spawning 4 parallel sessions every 15 minutes.

Replaces: dani-email-responder, hale-email-responder, persona-email-responder, wind-email-responder
Model: Opus (not MAX) to reduce cost
"""

import json
from pathlib import Path
from datetime import datetime
from core.ai_infra.thunderbird_headless_spawn import spawn_headless_claude

QUEUE_FILE = Path.home() / "Thunderbird" / "OpsCenter" / "email_queue_batch.jsonl"
LOG_FILE = Path.home() / "Thunderbird" / "OpsCenter" / "email_batch_processor.log"

def log_event(msg: str):
    """Append to processor log."""
    timestamp = datetime.utcnow().isoformat() + "Z"
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {msg}\n")

def read_queue() -> list:
    """Read pending email tasks from queue."""
    if not QUEUE_FILE.exists():
        return []

    tasks = []
    with open(QUEUE_FILE) as f:
        for line in f:
            if line.strip():
                tasks.append(json.loads(line))
    return tasks

def dedupe_tasks(tasks: list) -> list:
    """Dedupe by (inbox_type, account)."""
    seen = set()
    deduped = []
    for task in tasks:
        key = (task.get("inbox_type"), task.get("account"))
        if key not in seen:
            seen.add(key)
            deduped.append(task)
    return deduped

def batch_process(tasks: list):
    """
    Batch email intelligence sweep.
    Route to Opus (not MAX) to reduce cost by 60%.
    Uses approved thunderbird_headless_spawn wrapper (SO 24 APR 2026).
    """
    if not tasks:
        log_event("BATCH_PROCESS: No tasks in queue")
        return

    log_event(f"BATCH_PROCESS: Processing {len(tasks)} deduped tasks")

    # Combine all tasks into a single "full sweep" prompt for Opus
    task_summary = "\n".join([
        f"  - {t.get('inbox_type', 'unknown')}: {t.get('account', 'unknown')}"
        for t in tasks
    ])

    output_file = Path.home() / "Thunderbird" / "OpsCenter" / "email_batch_output.jsonl"

    prompt = f"""
Email Intelligence Batch Sweep

Process the following email inboxes in one consolidated analysis:
{task_summary}

Return JSON with findings per inbox_type.

WRITE output to {output_file}
"""

    # Spawn headless Claude with Opus (cheaper than MAX)
    # Use approved wrapper with background=True for async dispatch
    result = spawn_headless_claude(
        prompt=prompt,
        output_file=str(output_file),
        model="claude-opus-4-8-20250514",
        task_name="email-batch",
        background=True
    )

    if result.get("status") == "SPAWNED":
        log_event(f"BATCH_PROCESS: Spawned Opus processor (PID {result.get('pid')})")
    else:
        log_event(f"BATCH_PROCESS: Spawn failed — {result.get('error', 'unknown')}")

    # Clear queue after dispatch
    QUEUE_FILE.unlink(missing_ok=True)
    log_event(f"BATCH_PROCESS: Queue cleared")

def main():
    """Main entry point."""
    tasks = read_queue()
    if tasks:
        deduped = dedupe_tasks(tasks)
        log_event(f"BATCH_PROCESS: Read {len(tasks)} tasks, deduped to {len(deduped)}")
        batch_process(deduped)
    else:
        log_event("BATCH_PROCESS: Queue empty, nothing to do")

if __name__ == "__main__":
    main()
