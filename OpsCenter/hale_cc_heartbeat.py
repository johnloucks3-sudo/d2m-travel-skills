"""HALE-CC Heartbeat — writes proof-of-life for Claude Code to hale_shared_state.jsonl.

Mirrors jet_heartbeat.py (HALE-OC side). Run via systemd timer every 10 min.
Satisfies CR-3 check in thunderbird_coo_watchdog.py (threshold: 15 min).

Usage:
    python hale_cc_heartbeat.py          # timer mode
    python hale_cc_heartbeat.py --read   # read current state only
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

THUNDERBIRD = Path(__file__).parent.parent
SHARED_STATE = THUNDERBIRD / "OpsCenter" / "hale_shared_state.jsonl"
OC_TIMEOUT_S = 3600   # 60 min before HALE-OC considered stale
OC_CRITICAL_S = 7200  # 120 min critical

OC_INSTANCES = {"hale_oc", "jet"}


def read_last(instances: set) -> dict | None:
    if not SHARED_STATE.exists():
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


def get_last_sequence() -> int:
    if not SHARED_STATE.exists():
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


def append_heartbeat(health: str, last_oc: dict | None, oc_alive: bool,
                     missed: int, whisper: str | None = None) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    seq = get_last_sequence() + 1
    entry = {
        "protocol": "HALE-SHARED-STATE/v1",
        "event": "HEARTBEAT",
        "instance": "hale_cc",
        "timestamp": now,
        "heartbeat": {
            "interval_s": 600,
            "monotonic_sequence": seq,
            "health": health,
            "open_tasks": [],
            "requests_of_hale_oc": [],
            "last_other_heartbeat_read": last_oc["timestamp"] if last_oc else None,
            "other_alive": oc_alive,
            "other_missed_beats": missed,
        },
    }
    if whisper:
        entry["heartbeat"]["whisper"] = whisper
    SHARED_STATE.parent.mkdir(parents=True, exist_ok=True)
    with open(SHARED_STATE, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="HALE-CC Heartbeat")
    parser.add_argument("--read", action="store_true", help="Read state only, no write")
    parser.add_argument("--whisper", help="Whisper to HALE-OC")
    args = parser.parse_args()

    last_oc = read_last(OC_INSTANCES)
    now = datetime.now(timezone.utc)

    if args.read:
        last_cc = read_last({"hale_cc"})
        print("=== HALE-CC last ===")
        if last_cc:
            hb = last_cc.get("heartbeat", {})
            print(f"  Time:   {last_cc.get('timestamp')}")
            print(f"  Health: {hb.get('health')}")
            print(f"  Seq:    {hb.get('monotonic_sequence')}")
        else:
            print("  (no hale_cc heartbeat)")
        print("\n=== HALE-OC last ===")
        if last_oc:
            hb = last_oc.get("heartbeat", {})
            print(f"  Time:   {last_oc.get('timestamp')}")
            print(f"  Health: {hb.get('health')}")
            print(f"  Seq:    {hb.get('monotonic_sequence')}")
        else:
            print("  (no hale_oc heartbeat)")
        return 0

    # Assess HALE-OC health
    if last_oc is None:
        health = "YELLOW"
        oc_alive = False
        missed = -1
        print("HALE-OC: no heartbeat ever found")
    else:
        ts_str = last_oc["timestamp"]
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except ValueError:
            ts = now
        elapsed = (now - ts).total_seconds()
        missed = int(elapsed / 600) if elapsed > 0 else 0

        if elapsed > OC_CRITICAL_S:
            health = "RED"
            oc_alive = False
            print(f"HALE-OC: CRITICAL — {elapsed:.0f}s since last heartbeat ({missed} missed)")
        elif elapsed > OC_TIMEOUT_S:
            health = "YELLOW"
            oc_alive = False
            print(f"HALE-OC: stale — {elapsed:.0f}s since last heartbeat")
        else:
            health = "GREEN"
            oc_alive = True
            print(f"HALE-OC: alive — {elapsed:.0f}s since last heartbeat")

    append_heartbeat(health, last_oc, oc_alive, missed, whisper=args.whisper)
    print(f"HALE-CC heartbeat appended — health: {health}, seq: {get_last_sequence()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
