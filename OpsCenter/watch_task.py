#!/usr/bin/env python3
"""
watch_task.py — 2-stage progress watcher for headless Claude dispatch tasks.

Stage 1 (0–120s): polls every 5s with live spinner + stage label
Stage 2 (120s+):  2-minute recurring heartbeat lines

Usage:
  python3 OpsCenter/watch_task.py <output_file> <pid>
  python3 OpsCenter/watch_task.py <output_file> <pid> --timeout 3600
"""

import os
import sys
import time
from pathlib import Path

STAGE1_POLL = 5
STAGE1_WINDOW = 150   # 150s of fast polling covers most Claude tasks
STAGE2_POLL = 120
DEFAULT_TIMEOUT = 1800

_SPINNER = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

_STAGES = [
    (0,   "Initializing"),
    (10,  "Loading context"),
    (25,  "Analyzing request"),
    (50,  "Generating response"),
    (90,  "Writing output"),
    (150, "Extended task running"),
    (300, "Long-running — still active"),
]


def _stage_name(elapsed: float) -> str:
    name = _STAGES[0][1]
    for threshold, label in _STAGES:
        if elapsed >= threshold:
            name = label
    return name


def _fmt_time(secs: float) -> str:
    if secs < 60:
        return f"{int(secs)}s"
    m, s = divmod(int(secs), 60)
    return f"{m}m{s:02d}s"


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError, OSError):
        return False


def watch(output_file: str, pid: int, timeout: int) -> int:
    out = Path(output_file)
    start = time.monotonic()
    spin_i = 0
    stage = 1

    print(f"Task dispatched — PID {pid}")
    print(f"Output  → {output_file}")
    print()

    interval = STAGE1_POLL
    while True:
        elapsed = time.monotonic() - start

        # Done check
        if out.exists() and out.stat().st_size > 0:
            if stage == 1:
                print(f"\r✅  Done in {_fmt_time(elapsed)}{' ' * 40}")
            else:
                print(f"✅  Done in {_fmt_time(elapsed)}")
            print()
            print(out.read_text())
            return 0

        # Timeout
        if elapsed >= timeout:
            if stage == 1:
                print(f"\r⏱  Timeout after {_fmt_time(elapsed)}{' ' * 30}")
            else:
                print(f"⏱  Timeout after {_fmt_time(elapsed)}")
            print(f"Check: cat {output_file}")
            return 1

        # Stage 1 → Stage 2 transition — immediate re-check before first long sleep
        if stage == 1 and elapsed >= STAGE1_WINDOW:
            stage = 2
            interval = STAGE2_POLL
            print(f"\r⏳  {_fmt_time(elapsed)} — switching to 2-min checks{' ' * 20}")
            print(f"    Output: {output_file}")
            print()
            continue  # loop back to done-check immediately before first 120s sleep

        # Stage 2: print a heartbeat line and sleep
        if stage == 2:
            next_in = _fmt_time(interval)
            remaining = _fmt_time(timeout - elapsed)
            print(f"  [{_fmt_time(elapsed)}] Running — next check in {next_in}  ({remaining} until timeout)")
            time.sleep(interval)
            continue

        # Stage 1: spinner on a single overwritten line
        spin = _SPINNER[spin_i % len(_SPINNER)]
        spin_i += 1
        label = _stage_name(elapsed)
        print(f"\r  {spin} {_fmt_time(elapsed)} — {label} ...", end="", flush=True)
        time.sleep(interval)


def main() -> None:
    args = sys.argv[1:]
    if len(args) < 2:
        sys.exit(f"Usage: {sys.argv[0]} <output_file> <pid> [--timeout SECS]")

    output_file = args[0]
    pid = int(args[1])
    timeout = DEFAULT_TIMEOUT

    for i, a in enumerate(args):
        if a == "--timeout" and i + 1 < len(args):
            timeout = int(args[i + 1])

    sys.exit(watch(output_file, pid, timeout))


if __name__ == "__main__":
    main()
