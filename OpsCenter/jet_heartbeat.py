#!/usr/bin/env python3
"""HALE-OC Heartbeat — appends proof-of-life + whispers to hale_shared_state.jsonl.

Reads HALE-CC's latest heartbeat, stamps proof-of-read, escalates if stale.
Run via systemd timer (every 10 min) or manually with --whisper.

Protocol: HALE-SHARED-STATE/v1

Usage:
  python jet_heartbeat.py                          # timer mode — no whisper
  python jet_heartbeat.py --whisper "msg here"     # whisper to HALE-CC
  python jet_heartbeat.py --read                   # read latest heartbeat only
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

from hale_state_reader import read_last_other as shared_read_last_other

SHARED_STATE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "OpsCenter", "hale_shared_state.jsonl"
)

CC_TIMEOUT_S = 3600  # 60 min — session-gated hale_cc grace (CARRY-4)
CC_CRITICAL_S = 7200  # 120 min — 12 missed beats

# Instance aliases: the other side may write as "hale_cc" (post-T4) or "talon" (pre-T4)
OTHER_INSTANCES = {"hale_cc", "talon"}


def _matches_other(instance: str) -> bool:
    """Check if instance matches any alias for the other daemon."""
    return instance in OTHER_INSTANCES


def read_last(instances: set) -> dict | None:
    """Read the last entry for any of the given instances."""
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


def read_hale_cc_whispers(n: int = 3) -> list[dict]:
    """Read the last N entries from the other daemon that have whispers."""
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
            if _matches_other(entry.get("instance", "")):
                hb = entry.get("heartbeat", {})
                if hb.get("whisper"):
                    whispers.append(entry)
    return whispers[-n:]


def get_last_sequence() -> int:
    """Read the last monotonic_sequence from HEARTBEAT entries in shared state."""
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


def preflight_drift_check():
    """Write a test timestamp and verify it's within 60s of system UTC."""
    test_ts = datetime.now(timezone.utc)
    import subprocess
    try:
        # Get system UTC via date command as external reference
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


def append_heartbeat(health: str, last_talon: dict | None, other_alive: bool,
                     missed: int, whisper: str | None = None, open_tasks: list | None = None,
                     requests: list | None = None):
    """Append a HEARTBEAT event to hale_shared_state.jsonl."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    seq = get_last_sequence() + 1
    entry = {
        "protocol": "HALE-SHARED-STATE/v1",
        "event": "HEARTBEAT",
        "instance": "hale_oc",
        "timestamp": now,
        "heartbeat": {
            "interval_s": 600,
            "monotonic_sequence": seq,
            "health": health,
            "open_tasks": open_tasks or [],
            "requests_of_hale_cc": requests or [],
            "last_other_heartbeat_read": last_talon["timestamp"] if last_talon else None,
            "other_alive": other_alive,
            "other_missed_beats": missed
        }
    }
    if whisper:
        entry["heartbeat"]["whisper"] = whisper
    with open(SHARED_STATE, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def format_whispers(whispers: list[dict]) -> str:
    """Format recent HALE-CC whispers for human reading."""
    if not whispers:
        return "  (no whispers from HALE-CC)"
    lines = []
    for w in whispers:
        ts = w.get("timestamp", "?")
        whisper = w.get("heartbeat", {}).get("whisper", "")
        health = w.get("heartbeat", {}).get("health", "?")
        lines.append(f"  [{ts}] ({health}) {whisper}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="HALE-OC Heartbeat")
    parser.add_argument("--whisper", help="Brief text to whisper to HALE-CC")
    parser.add_argument("--read", action="store_true", help="Read latest heartbeats only")
    parser.add_argument("--skip-drift-check", action="store_true", help="Skip pre-flight drift check")
    args = parser.parse_args()

    # Pre-flight: verify clock is within 60s of system UTC
    if not args.skip_drift_check and not args.read:
        if not preflight_drift_check():
            print("DRIFT CHECK FAILED — refusing to write heartbeat with skewed clock")
            return 1

    last_other = read_last(OTHER_INSTANCES)
    now = datetime.now(timezone.utc)

    if args.read:
        print("=== HALE-OC last ===")
        last_oc = read_last({"hale_oc"})
        if last_oc:
            hb = last_oc.get("heartbeat", {})
            print(f"  Time: {last_oc.get('timestamp')}")
            print(f"  Health: {hb.get('health')}")
            print(f"  Seq: {hb.get('monotonic_sequence', 'N/A')}")
            print(f"  Whisper: {hb.get('whisper', '(none)')}")
            print(f"  HALE-CC/TALON last seen: {hb.get('last_other_heartbeat_read')}")
            print(f"  HALE-CC/TALON alive: {hb.get('other_alive')}")
        else:
            print("  (no HALE-OC heartbeat)")
        print("\n=== Other daemon last ===")
        if last_other:
            hb = last_other.get("heartbeat", {})
            print(f"  Instance: {last_other.get('instance')}")
            print(f"  Time: {last_other.get('timestamp')}")
            print(f"  Health: {hb.get('health')}")
            print(f"  Seq: {hb.get('monotonic_sequence', 'N/A')}")
            print(f"  Whisper: {hb.get('whisper', '(none)')}")
            print(f"  Open tasks: {hb.get('open_tasks', [])}")
        else:
            print("  (no other daemon heartbeat)")
        print("\n=== Other daemon recent whispers ===")
        print(format_whispers(read_hale_cc_whispers(5)))
        return 0

    if last_other is None:
        health = "YELLOW"
        other_alive = False
        missed = -1
        print("Other daemon: no heartbeat ever found")
    else:
        ts_str = last_other["timestamp"]
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except ValueError:
            ts = now
        elapsed = (now - ts).total_seconds()
        missed = int(elapsed / 600) if elapsed > 0 else 0

        # CARRY-4: HANDOFF-aware grace — if last entry is a HANDOFF with estimated_wake,
        # defer YELLOW until wake + 15 min grace
        handoff_grace = False
        if last_other.get("event") == "HANDOFF":
            estimated_wake = last_other.get("estimated_wake")
            if estimated_wake:
                try:
                    wake_dt = datetime.fromisoformat(estimated_wake.replace("Z", "+00:00"))
                    wake_grace_ts = wake_dt.timestamp() + 900
                    if now.timestamp() < wake_grace_ts:
                        handoff_grace = True
                except (ValueError, TypeError):
                    pass

        if handoff_grace:
            health = "GREEN"
            other_alive = True
            print(f"Other daemon: HANDOFF grace — {elapsed:.0f}s since last entry (estimated wake {estimated_wake})")
        elif elapsed > CC_CRITICAL_S:
            health = "RED"
            other_alive = False
            print(f"Other daemon: CRITICAL — {elapsed:.0f}s since last heartbeat ({missed} missed beats)")
        elif elapsed > CC_TIMEOUT_S:
            health = "YELLOW"
            other_alive = False
            print(f"Other daemon: stale — {elapsed:.0f}s since last heartbeat ({missed} missed beats)")
        else:
            health = "GREEN"
            other_alive = True
            print(f"Other daemon: alive — {elapsed:.0f}s since last heartbeat")

    append_heartbeat(health, last_other, other_alive, missed,
                     whisper=args.whisper)
    action = "whisper" if args.whisper else "heartbeat"
    print(f"HALE-OC {action} appended — health: {health}")
    if args.whisper:
        print(f"  -> {args.whisper}")

    if not other_alive:
        print("ALERT: HALE-CC heartbeat stale — flag for Commander attention")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
