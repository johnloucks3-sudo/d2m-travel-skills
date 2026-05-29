#!/usr/bin/env python3
"""Session Continuity Checkpoint — MISSION-050.
Appends current state to OpsCenter/checkpoints.jsonl every ~15 min.
Read on session start to resume from last known state.
Max 100 entries (auto-groomed). Append-only.
"""
import json
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHECKPOINT_FILE = os.path.join(ROOT, "OpsCenter", "checkpoints.jsonl")
MAX_ENTRIES = 100

def write_checkpoint(task=None, files_modified=None, decisions_made=None, next_step=None):
    entry = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "task": task or os.environ.get("HALE_CURRENT_TASK", "unknown"),
        "files_modified": files_modified or [],
        "decisions_made": decisions_made or [],
        "next_step": next_step or "",
    }
    os.makedirs(os.path.dirname(CHECKPOINT_FILE), exist_ok=True)
    with open(CHECKPOINT_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
    _groom()
    return entry

def _groom():
    try:
        with open(CHECKPOINT_FILE, "r") as f:
            lines = f.readlines()
        if len(lines) > MAX_ENTRIES:
            with open(CHECKPOINT_FILE, "w") as f:
                f.writelines(lines[-MAX_ENTRIES:])
    except FileNotFoundError:
        pass

def read_latest(n=3):
    try:
        with open(CHECKPOINT_FILE, "r") as f:
            lines = f.readlines()
        entries = [json.loads(l) for l in lines if l.strip()]
        return entries[-n:]
    except (FileNotFoundError, json.JSONDecodeError):
        return []

if __name__ == "__main__":
    task = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "session_checkpoint_pulse"
    cp = write_checkpoint(task=task)
    print(f"Checkpoint written: {cp['ts']} — {cp['task']}")
    print(f"Total checkpoints on disk: ... (run again to verify grooming)")
