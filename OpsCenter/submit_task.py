#!/usr/bin/env python3
"""
submit_task.py — Universal task submission CLI + library
=========================================================
Used by: C2 bot, OpenCode (via shell), Claude, cron scripts, MCP tools.

CLI usage:
    python submit_task.py "Run morning intel sweep" --to opencode --type intel_sweep
    python submit_task.py "Draft reply to Furlow" --to hale --priority 2

Library usage:
    from OpsCenter.submit_task import queue
    task_id = queue("Do X", assigned_to="opencode", task_type="intel_sweep")
"""

import argparse
import sys
import os

sys.path.insert(0, "/home/john/Thunderbird")

from OpsCenter.task_queue import init_db, submit_task, get_queue_stats, has_pending


def queue(
    content: str,
    assigned_to: str = "auto",
    task_type: str = "general",
    priority: int = 5,
    source: str = "api",
    chat_id: str = None,
    timeout_sec: int = 300,
) -> str:
    """Submit a task and return its ID. Initialises DB if needed."""
    init_db()
    return submit_task(
        content=content,
        assigned_to=assigned_to,
        task_type=task_type,
        priority=priority,
        source=source,
        chat_id=chat_id,
        timeout_sec=timeout_sec,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Submit a task to the Thunderbird dispatcher queue."
    )
    parser.add_argument("content", help="Task description / prompt")
    parser.add_argument(
        "--to", default="auto",
        help="Agent: hale | opencode | auto  (default: auto)",
    )
    parser.add_argument(
        "--type", default="general", dest="task_type",
        help="Task type (commander_message|intel_sweep|client_email|…)",
    )
    parser.add_argument(
        "--priority", type=int, default=5,
        help="1=urgent … 5=normal … 9=low  (default: 5)",
    )
    parser.add_argument(
        "--timeout", type=int, default=300,
        help="Agent timeout in seconds  (default: 300)",
    )
    parser.add_argument(
        "--source", default="cli",
        help="Source identifier for audit trail",
    )
    parser.add_argument(
        "--chat-id", default=None,
        help="Telegram chat_id for completion notification",
    )
    parser.add_argument(
        "--stats", action="store_true",
        help="Print queue stats and exit",
    )
    args = parser.parse_args()

    init_db()

    if args.stats:
        stats = get_queue_stats()
        pending = stats.get("pending", 0)
        running = stats.get("running", 0)
        done    = stats.get("done", 0)
        failed  = stats.get("failed", 0)
        print(f"pending={pending}  running={running}  done={done}  failed={failed}")
        return

    task_id = queue(
        content=args.content,
        assigned_to=args.to,
        task_type=args.task_type,
        priority=args.priority,
        source=args.source,
        chat_id=args.chat_id,
        timeout_sec=args.timeout,
    )

    stats = get_queue_stats()
    print(f"queued: {task_id}  (pending={stats.get('pending',0)})")


if __name__ == "__main__":
    main()
