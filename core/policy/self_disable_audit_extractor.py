#!/usr/bin/env python3
"""
SELF-DISABLE-001 Audit Extractor
==================================
core/policy/self_disable_audit_extractor.py

Extracts all SELF-DISABLE-001 block events from the policy audit log and
writes them to a dedicated named audit file. Called by Sterling's Sunday sweep
to ensure block events are visible and tracked.

Usage:
    python3 core/policy/self_disable_audit_extractor.py
    python3 core/policy/self_disable_audit_extractor.py --recent 7d
    python3 core/policy/self_disable_audit_extractor.py --summary

Output:
    Writes to: logs/policy_audit_self_disable_001.jsonl
    Summary mode prints a human-readable report.
"""

import json
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional


REPO_ROOT = Path("/home/john/Thunderbird")
POLICY_AUDIT_LOG = REPO_ROOT / "logs" / "policy_audit.jsonl"
SELF_DISABLE_AUDIT_LOG = REPO_ROOT / "logs" / "policy_audit_self_disable_001.jsonl"


def parse_timestamp(ts_str: str) -> Optional[datetime]:
    """Parse ISO 8601 timestamp string (with timezone)."""
    try:
        # Try with timezone info first
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        try:
            # Fallback: try without timezone
            return datetime.fromisoformat(ts_str)
        except (ValueError, AttributeError):
            return None


def read_policy_audit_log() -> List[Dict]:
    """Read the policy audit log and return all entries."""
    if not POLICY_AUDIT_LOG.exists():
        return []

    entries = []
    try:
        with open(POLICY_AUDIT_LOG, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    entries.append(entry)
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        print(f"WARNING: Error reading policy audit log: {e}", file=sys.stderr)

    return entries


def extract_self_disable_events(
    entries: List[Dict], since: Optional[timedelta] = None
) -> List[Dict]:
    """
    Extract SELF-DISABLE-001 block events.
    If `since` is provided, only return events within that timeframe.
    """
    self_disable_events = []

    for entry in entries:
        # Look for SELF-DISABLE-001 rule_id in the result
        result = entry.get("result", {})
        if result.get("rule_id") != "SELF-DISABLE-001":
            continue

        # If we have a time filter, check it
        if since:
            ts_str = entry.get("ts")
            if ts_str:
                ts = parse_timestamp(ts_str)
                if ts and (datetime.now(ts.tzinfo) - ts) > since:
                    continue  # Too old

        self_disable_events.append(entry)

    return self_disable_events


def write_self_disable_audit(events: List[Dict]) -> None:
    """Write SELF-DISABLE-001 events to the dedicated audit file."""
    try:
        os.makedirs(SELF_DISABLE_AUDIT_LOG.parent, exist_ok=True)
        with open(SELF_DISABLE_AUDIT_LOG, "w", encoding="utf-8") as f:
            for event in events:
                f.write(json.dumps(event) + "\n")
        print(f"✓ Wrote {len(events)} SELF-DISABLE-001 events to {SELF_DISABLE_AUDIT_LOG}")
    except Exception as e:
        print(f"ERROR: Failed to write audit file: {e}", file=sys.stderr)
        sys.exit(1)


def print_summary(events: List[Dict]) -> None:
    """Print human-readable summary of SELF-DISABLE-001 events."""
    if not events:
        print("✓ GREEN: No SELF-DISABLE-001 block events detected.")
        return

    print(f"\n🔴 RED: {len(events)} SELF-DISABLE-001 block events detected:\n")

    # Group by tool
    by_tool = {}
    for event in events:
        ctx = event.get("ctx", {})
        tool = ctx.get("tool", "unknown")
        if tool not in by_tool:
            by_tool[tool] = []
        by_tool[tool].append(event)

    for tool, tool_events in sorted(by_tool.items()):
        print(f"  {tool}: {len(tool_events)} events")
        for event in tool_events[-3:]:  # Show last 3 of each type
            ts = event.get("ts", "unknown time")
            ctx = event.get("ctx", {})
            path = ctx.get("file_path") or ctx.get("command", "")
            print(f"    {ts}: {path[:60]}")

    print()
    print("POLICY VIOLATION DETAILS:")
    print("  Rule: SELF-DISABLE-001 (Wing policy engine is self-protecting)")
    print("  Decision: DENY (hard block)")
    print("  Action Required: Review and remediate — these are failed attempts to")
    print("    modify the policy engine or protected email/relay infrastructure.")
    print(f"  Audit File: {SELF_DISABLE_AUDIT_LOG}")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Extract SELF-DISABLE-001 block events from policy audit log"
    )
    parser.add_argument(
        "--recent",
        type=str,
        default=None,
        help="Filter to events within this timeframe (e.g., '7d', '1h')",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print human-readable summary instead of writing audit file",
    )

    args = parser.parse_args()

    # Parse timeframe if provided
    since = None
    if args.recent:
        match args.recent.lower():
            case "7d":
                since = timedelta(days=7)
            case "1d":
                since = timedelta(days=1)
            case "1h":
                since = timedelta(hours=1)
            case _:
                print(f"WARNING: Unknown timeframe '{args.recent}' — using all events")

    # Extract events
    all_entries = read_policy_audit_log()
    self_disable_events = extract_self_disable_events(all_entries, since=since)

    if args.summary:
        print_summary(self_disable_events)
    else:
        write_self_disable_audit(self_disable_events)
        print_summary(self_disable_events)

    return 0


if __name__ == "__main__":
    sys.exit(main())
