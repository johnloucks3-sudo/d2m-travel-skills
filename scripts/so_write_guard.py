#!/usr/bin/env python3
"""
SO Write Guard — Enforces: "CLAUDE.md and SO files → Sterling owns. Route, don't write."

Prevents OpenCode from writing SO files (ops/SO-*) without prior routing to Sterling (A7).
When routing tools fail, the guard captures the failure and requires escalation — never bypass.

Usage:
  python3 scripts/so_write_guard.py route "Task description for Sterling"
      → Attempts Sterling routing via ask, logs the attempt, saves proof

  python3 scripts/so_write_guard.py check <filepath>
      → Exit 0: Write permitted (routing on record for this session)
      → Exit 1: BLOCKED — must route first or escalate to Commander

  python3 scripts/so_write_guard.py status
      → Shows routing log entries for current session

  python3 scripts/so_write_guard.py escalate "Reason"
      → Records an escalation to Commander when routing cannot be completed
      → This is the ONLY override path for blocked SO writes
"""

import json
import sys
import subprocess
import time
from datetime import datetime
from pathlib import Path

ROUTING_LOG = Path("/home/john/Thunderbird/ops/.so_routing_log.jsonl")
SO_DIR = Path("/home/john/Thunderbird/ops")
SESSION_START = datetime.now().isoformat()
_GLOBAL_LOG_CACHE: list[dict] | None = None  # Lazy-loaded per process


def _is_so_file(filepath: str) -> bool:
    """Check if a file path is an SO document."""
    path = Path(filepath)
    return "SO-" in path.name


def _read_log() -> list[dict]:
    """Read all routing log entries."""
    if not ROUTING_LOG.exists():
        return []
    with open(ROUTING_LOG) as f:
        return [json.loads(line) for line in f if line.strip()]


def _write_log(entry: dict) -> None:
    """Append an entry to the routing log."""
    ROUTING_LOG.parent.mkdir(exist_ok=True)
    with open(ROUTING_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


def cmd_route(task: str) -> None:
    """Route a task to Sterling via ask, log the attempt."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "action": "route",
        "task": task[:200],
        "status": "attempted",
        "output_file": None,
        "error": None,
    }

    print(f"\n{'='*60}")
    print(f"  ROUTING TO STERLING (A7): {task[:80]}...")
    print(f"{'='*60}\n")

    ask_script = "/home/john/.local/bin/ask"
    if not Path(ask_script).exists():
        entry["status"] = "failed"
        entry["error"] = f"ask binary not found at {ask_script}"
        _write_log(entry)
        print(f"  ❌ {entry['error']}")
        print(f"  → Use 'escalate' to record Commander override.")
        sys.exit(1)

    output_path = Path(f"/home/john/Thunderbird/output/sterling_routing_{int(time.time())}.txt")
    routing_prompt = (
        f"You are STERLING (A7), Thunderbird Wing — Process / SO Owner.\n\n"
        f"Commander needs you to review and handle the following:\n\n{task}\n\n"
        f"Provide your assessment. If this requires an SO amendment, implement it.\n"
        f"Write your full response."
    )

    try:
        result = subprocess.run(
            [ask_script, routing_prompt],
            capture_output=True,
            text=True,
            timeout=180,
        )
        entry["exit_code"] = result.returncode
        entry["stderr"] = result.stderr[:500] if result.stderr else None

        # ask wrapper writes output to a file — find it
        output_files = sorted(Path("/home/john/Thunderbird/output").glob("opencode_sonnet_*.txt"))
        if output_files:
            latest = max(output_files, key=lambda p: p.stat().st_mtime)
            if latest.stat().st_size > 0 and "FAILED" not in latest.read_text():
                output_path = latest
                entry["output_file"] = str(latest)
                entry["status"] = "delivered"
                entry["output_size"] = latest.stat().st_size
                print(f"  ✅ Routing delivered — output at {latest}")
                print(f"     Size: {latest.stat().st_size} bytes")
            else:
                entry["status"] = "failed"
                entry["error"] = "Output file exists but indicates failure"
                print(f"  ❌ Routing failed — output file indicates error")
                print(f"     Check: {latest}")
        else:
            entry["status"] = "failed"
            entry["error"] = "No output file produced by ask"
            print(f"  ❌ Routing failed — no output produced within timeout")
            if result.stderr:
                print(f"     stderr: {result.stderr[:300]}")

    except subprocess.TimeoutExpired:
        entry["status"] = "timeout"
        entry["error"] = "ask command timed out (180s)"
        print(f"  ❌ Routing timed out after 180s")
    except FileNotFoundError:
        entry["status"] = "failed"
        entry["error"] = "ask binary not found at path"
        print(f"  ❌ ask binary not found")
    except Exception as e:
        entry["status"] = "error"
        entry["error"] = str(e)[:300]
        print(f"  ❌ Unexpected error: {e}")

    _write_log(entry)

    if entry["status"] != "delivered":
        print(f"\n  → Routing failed. Options:")
        print(f"     1. Retry: python3 scripts/so_write_guard.py route '{task}'")
        print(f"     2. Escalate: python3 scripts/so_write_guard.py escalate 'ask failed — {entry['error']}'")
        print(f"     3. Do NOT write SO files directly without routing or escalation.\n")
        sys.exit(1)

    sys.exit(0)


def cmd_check(filepath: str) -> None:
    """Check if writing to an SO file is permitted."""
    path = Path(filepath)

    if not _is_so_file(filepath):
        sys.exit(0)  # Not an SO file, pass through

    log = _read_log()

    # Check for a successful routing or escalation on record
    has_routing = any(e.get("status") == "delivered" for e in log)
    has_escalation = any(e.get("action") == "escalate" for e in log)

    if has_routing or has_escalation:
        sys.exit(0)  # Write permitted

    print(f"\n{'='*60}")
    print(f"  ❌ BLOCKED: Direct write to SO file")
    print(f"{'='*60}")
    print(f"  File: {filepath}")
    print(f"  Rule: SO files → Sterling owns. Route, don't write.")
    print(f"\n  You must route to Sterling first:")
    print(f"    python3 scripts/so_write_guard.py route 'Describe what Sterling needs to do'")
    print(f"\n  If routing tools are unavailable, escalate to Commander:")
    print(f"    python3 scripts/so_write_guard.py escalate 'Why routing is blocked'")
    print(f"\n  Do NOT write SO files directly without routing or escalation.\n")
    sys.exit(1)


def cmd_status() -> None:
    """Show routing log for current session."""
    log = _read_log()

    print(f"\n{'='*60}")
    print(f"  SO ROUTING LOG ({len(log)} entries)")
    print(f"{'='*60}")

    if not log:
        print("  (no routing activity)")
        print()
        sys.exit(0)

    for i, entry in enumerate(log, 1):
        action = entry.get("action", "unknown")
        status = entry.get("status", "unknown")
        task = entry.get("task", "")[:80]
        ts = entry.get("timestamp", "")[11:19]

        icon = {"route": "📋", "escalate": "🚨", "check": "🔍"}.get(action, "•")
        status_icon = {"delivered": "✅", "failed": "❌", "timeout": "⏱", "attempted": "🔄", "blocked": "🚫"}.get(status, "•")

        print(f"  {i}. {icon} {ts} [{status_icon}] {action.upper()}: {task}")
        if entry.get("error"):
            print(f"     Error: {entry['error'][:120]}")
        if entry.get("output_file"):
            print(f"     Output: {entry['output_file']}")

    print(f"\n  {len(session_entries)} total entries")
    print()


def cmd_escalate(reason: str) -> None:
    """Record escalation to Commander when routing cannot be completed."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "action": "escalate",
        "reason": reason[:500],
        "status": "escalated",
    }
    _write_log(entry)
    print(f"\n{'='*60}")
    print(f"  🚨 ESCALATION RECORDED")
    print(f"{'='*60}")
    print(f"  Reason: {reason}")
    print(f"  This authorizes SO write bypass for this session only.")
    print(f"  Commander must be notified of this escalation.")
    print()


def cmd_reset() -> None:
    """Clear routing log for new session."""
    if ROUTING_LOG.exists():
        ROUTING_LOG.unlink()
    print("  ✅ Routing log cleared. New session started.")
    print()


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 scripts/so_write_guard.py route 'Task for Sterling'")
        print("  python3 scripts/so_write_guard.py check <filepath>")
        print("  python3 scripts/so_write_guard.py status")
        print("  python3 scripts/so_write_guard.py escalate 'Reason'")
        print("  python3 scripts/so_write_guard.py reset")
        sys.exit(1)

    command = sys.argv[1]

    if command == "route":
        if len(sys.argv) < 3:
            print("Error: provide a task description")
            sys.exit(1)
        cmd_route(" ".join(sys.argv[2:]))

    elif command == "check":
        if len(sys.argv) < 3:
            print("Error: provide a file path")
            sys.exit(1)
        cmd_check(sys.argv[2])

    elif command == "status":
        cmd_status()

    elif command == "escalate":
        if len(sys.argv) < 3:
            print("Error: provide an escalation reason")
            sys.exit(1)
        cmd_escalate(" ".join(sys.argv[2:]))

    elif command == "reset":
        cmd_reset()

    else:
        print(f"Unknown command: {command}")
        print("Use: route, check, status, escalate, reset")
        sys.exit(1)


if __name__ == "__main__":
    main()
