#!/usr/bin/env python3
"""ZEN Limit Check — run after every heavy task.
Shows estimated remaining % for big-pickle (the current model).
"""
import json
import os
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DB = ROOT / "storage" / "ai_costs.db"
CHECKPOINTS = ROOT / "OpsCenter" / "checkpoints.jsonl"
LOG = ROOT / "logs" / "opencode_calls.jsonl"

LIMITS = {
    "opencode/big-pickle": {"name": "Big Pickle", "req_hr": 50, "req_day": 200, "tok_hr": 10000},
    "opencode/deepseek-v4-flash-free": {"name": "DeepSeek V4 Flash", "req_hr": 100, "req_day": 500, "tok_hr": 50000},
}

def count_recent_activity():
    """Count checkpoints + log entries as proxy for activity."""
    checkpoint_count = 0
    if CHECKPOINTS.exists():
        with open(CHECKPOINTS) as f:
            checkpoint_count = sum(1 for _ in f)

    log_count = 0
    if LOG.exists():
        with open(LOG) as f:
            for line in f:
                if line.strip():
                    try:
                        e = json.loads(line)
                        ts = datetime.fromisoformat(e.get("timestamp", "").replace("Z", "+00:00"))
                        if ts >= datetime.now(timezone.utc) - timedelta(hours=1):
                            log_count += 1
                    except:
                        pass

    return max(checkpoint_count, log_count)

def check_status(model="opencode/deepseek-v4-flash-free"):
    limits = LIMITS.get(model, LIMITS["opencode/deepseek-v4-flash-free"])
    activity = count_recent_activity()

    # Estimate usage from activity count
    est_usage = min(activity * 3, limits["req_hr"])  # rough: each activity ~3 calls
    pct_used = (est_usage / limits["req_hr"]) * 100
    pct_remaining = 100 - pct_used

    print(f"=== ZEN STATUS — {datetime.now(timezone.utc).strftime('%H:%M UTC')} ===")
    print(f"Model: {limits['name']} ({model})")
    print(f"Limits: {limits['req_hr']}/hr req, {limits['tok_hr']}/hr tokens, {limits['req_day']}/day req")
    print(f"Activity proxy: ~{est_usage} calls/hr ({pct_used:.0f}% used)")

    if pct_remaining > 50:
        print(f"Remaining: ~{pct_remaining:.0f}% GREEN — keep going")
    elif pct_remaining > 20:
        print(f"Remaining: ~{pct_remaining:.0f}% YELLOW — moderate pace")
    else:
        print(f"Remaining: ~{pct_remaining:.0f}% RED — consider pausing")

    print()
    # Also show checkpoint count
    if CHECKPOINTS.exists():
        with open(CHECKPOINTS) as f:
            total = sum(1 for _ in f)
        print(f"Session checkpoints written: {total}")
    print()

if __name__ == "__main__":
    check_status()
