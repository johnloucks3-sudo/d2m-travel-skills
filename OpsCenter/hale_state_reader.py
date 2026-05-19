#!/usr/bin/env python3
"""HALE Shared State Reader — reusable module for BOTH sides (hale_oc + hale_cc).

Provides backward-compatible reader functions for hale_shared_state.jsonl.
hale_cc can use this to read hale_oc entries (instance: "hale_oc" or legacy "jet").

Usage:
    from hale_state_reader import read_last_other, preflight_drift_check

    last = read_last_other()
    if last:
        print(last["timestamp"])
"""

import json
import os
import sys
from datetime import datetime, timezone

SHARED_STATE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "OpsCenter", "hale_shared_state.jsonl"
)

OTHER_INSTANCES = {"hale_oc", "jet"}


def _matches_other(instance: str, instances: set) -> bool:
    return instance in instances


def read_last_other(instances: set = None) -> dict | None:
    """Read the last entry matching any of the given instances.
    Defaults to OTHER_INSTANCES (backward-compatible: hale_oc + jet).
    """
    if instances is None:
        instances = OTHER_INSTANCES
    if not os.path.exists(SHARED_STATE):
        return None
    last = None
    with open(SHARED_STATE) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("instance") in instances:
                last = entry
    return last


def read_hale_oc_whispers(n: int = 3) -> list[dict]:
    """Read the last N entries from hale_oc that have whispers."""
    if not os.path.exists(SHARED_STATE):
        return []
    whispers = []
    with open(SHARED_STATE) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if _matches_other(entry.get("instance", ""), OTHER_INSTANCES):
                hb = entry.get("heartbeat", {})
                if hb.get("whisper"):
                    whispers.append(entry)
    return whispers[-n:]


def get_last_sequence() -> int:
    """Read the highest monotonic_sequence from HEARTBEAT entries."""
    if not os.path.exists(SHARED_STATE):
        return 0
    last_seq = 0
    with open(SHARED_STATE) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("event") == "HEARTBEAT":
                seq = entry.get("heartbeat", {}).get("monotonic_sequence", 0)
                if isinstance(seq, int) and seq > last_seq:
                    last_seq = seq
    return last_seq


def preflight_drift_check() -> bool:
    """Write a test timestamp and verify it's within 60s of system UTC."""
    test_ts = datetime.now(timezone.utc)
    import subprocess
    try:
        result = subprocess.run(
            ["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            sys_ts_str = result.stdout.strip()
            sys_dt = datetime.fromisoformat(sys_ts_str.replace("Z", "+00:00"))
            drift = abs((test_ts - sys_dt).total_seconds())
            if drift > 60:
                print(f"CLOCK SKEW CRITICAL: Python UTC {test_ts.isoformat()} vs system UTC {sys_ts_str} — drift {drift:.0f}s")
                return False
            else:
                print(f"Pre-flight drift check: {drift:.0f}s — OK")
    except Exception as e:
        print(f"Pre-flight drift check skipped (date command unavailable): {e}")
    return True


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="HALE Shared State Reader")
    parser.add_argument("--read", action="store_true", help="Read latest hale_oc entry")
    args = parser.parse_args()

    last = read_last_other()
    if args.read:
        print("=== HALE-OC latest (via shared reader) ===")
        if last:
            hb = last.get("heartbeat", {})
            print(f"  Instance: {last.get('instance')}")
            print(f"  Time: {last.get('timestamp')}")
            print(f"  Health: {hb.get('health')}")
            print(f"  Seq: {hb.get('monotonic_sequence', 'N/A')}")
            print(f"  Whisper: {hb.get('whisper', '(none)')}")
        else:
            print("  (no hale_oc / jet entry found)")
        print(f"\nBackward compat set: {OTHER_INSTANCES}")
        print(f"File: {SHARED_STATE}")
