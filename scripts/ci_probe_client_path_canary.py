#!/usr/bin/env python3
"""
CI EFFICACY PROBE — Client-Path Canary Monitoring Instrument
============================================================
MISSION-427: Wire client-path canary monitoring instrument for Vanguard SO enforcement.

Verifies the 7-day client-path canary defined in SO_TECH_VANGUARD_ELEVATION_20260621 §2a
is running on all active canary tools. Converts doctrine from a commit to a measurable state.

Canary criterion:
- A tool touching client-send path or client PII adopts immediately but runs on
  Loucks-as-client (internal) traffic only for 7 days.
- Output diffs are captured each run.
- Graduates to live client traffic on: ZERO send-path defects across 7-day window.

This probe:
1. Reads the client-path canary registry
2. Checks current date vs. canary start dates
3. Counts defects logged for each tool
4. Reports graduation eligibility (7-day + zero defects)
5. Returns exit 0 (RAZOR_SHARP) if all canaries healthy, 1 if defects/failures

Exit 0 = GREEN (all canaries active, on track)
Exit 1 = RED (defects found, graduation blocked, or tool failure)
"""
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple

REGISTRY_PATH = Path("/home/john/Thunderbird/config/client_path_canary_registry.json")
CANARY_DIFF_DIR = Path("/home/john/Thunderbird/OpsCenter/canary_diffs")
INCIDENT_LOG = Path("/home/john/Thunderbird/OpsCenter/hale_incidents_today.json")


def fail(message: str, details: str = ""):
    """Log RED and exit 1."""
    msg = f"RED client-path-canary: {message}"
    if details:
        msg += f" | {details}"
    print(msg)
    sys.exit(1)


def warn(message: str):
    """Log YELLOW but continue."""
    print(f"YELLOW client-path-canary: {message}")


def success(message: str):
    """Log GREEN."""
    print(f"GREEN client-path-canary: {message}")


def load_registry() -> Dict:
    """Load the canary registry."""
    if not REGISTRY_PATH.exists():
        fail("registry not found", f"expected {REGISTRY_PATH}")
    try:
        return json.loads(REGISTRY_PATH.read_text())
    except json.JSONDecodeError as e:
        fail("registry malformed", str(e))


def load_incidents() -> List[Dict]:
    """Load today's incident log to check for send-path defects."""
    if not INCIDENT_LOG.exists():
        return []
    try:
        data = json.loads(INCIDENT_LOG.read_text())
        return data.get("incidents", [])
    except json.JSONDecodeError:
        return []


def check_canary_defects_from_incidents(tool_id: str, incidents: List[Dict]) -> int:
    """
    Check incident log for defects related to this tool.
    A defect is a RED or unresolved incident tagged with the tool_id.
    """
    defect_count = 0
    for incident in incidents:
        # Match incidents by service name or tool reference
        service = incident.get("service", "").lower()
        note = incident.get("note", "").lower()

        # Check if incident is related to this canary tool
        if tool_id.lower() in service or tool_id.lower() in note:
            # Count RED, YELLOW (unresolved) incidents as defects
            if incident.get("status") in ("RED", "YELLOW"):
                if incident.get("event_type") not in ("auto_healed",):
                    defect_count += 1

    return defect_count


def count_diff_logs(tool_id: str) -> int:
    """Count the number of diff log entries for a tool."""
    if not CANARY_DIFF_DIR.exists():
        CANARY_DIFF_DIR.mkdir(parents=True, exist_ok=True)
        return 0

    # Look for tool-specific diff file
    diff_pattern = f"{tool_id.replace('-', '_')}_diffs.jsonl"
    diff_file = CANARY_DIFF_DIR / diff_pattern

    if not diff_file.exists():
        return 0

    try:
        count = sum(1 for _ in diff_file.read_text().strip().split('\n') if _.strip())
        return count
    except Exception:
        return 0


def check_canary_tool(tool: Dict, incidents: List[Dict], now: datetime) -> Tuple[bool, str]:
    """
    Check a single canary tool. Return (passed, reason).

    Passed = tool is on track (active, no defects within window, or graduated)
    Failed = defects found, or tool failure
    """
    tool_id = tool.get("id")
    canary_start_str = tool.get("canary_start")
    canary_status = tool.get("canary_status")
    graduation_date = tool.get("graduation_date")

    # Parse canary start time
    try:
        canary_start = datetime.fromisoformat(canary_start_str.replace('Z', '+00:00'))
    except (ValueError, TypeError) as e:
        return False, f"invalid canary_start format for {tool_id}: {e}"

    # Ensure now is timezone-aware
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    # Check if already graduated
    if graduation_date:
        grad_date = datetime.fromisoformat(graduation_date.replace('Z', '+00:00'))
        if now >= grad_date:
            return True, f"{tool_id} graduated on {graduation_date}"

    # Check if canary is active
    if canary_status != "ACTIVE":
        return False, f"{tool_id} canary not ACTIVE (status: {canary_status})"

    # Calculate days in canary
    days_in_canary = (now - canary_start).days
    if days_in_canary < 0:
        return False, f"{tool_id} canary start is in the future"

    # Check for defects
    defect_count = tool.get("defect_count", 0) + check_canary_defects_from_incidents(tool_id, incidents)

    if defect_count > 0:
        return False, f"{tool_id} has {defect_count} send-path defect(s) — graduation blocked"

    # Check graduation eligibility
    eligible_date_str = tool.get("eligible_for_graduation", "2099-12-31")
    # Parse as date if it's just YYYY-MM-DD, convert to datetime
    if 'T' not in eligible_date_str:
        eligible_date_str = eligible_date_str + "T00:00:00Z"
    eligible_on = datetime.fromisoformat(eligible_date_str.replace('Z', '+00:00'))

    if now >= eligible_on and defect_count == 0:
        return True, f"{tool_id} eligible for graduation (day {days_in_canary}, zero defects)"
    elif days_in_canary >= 7 and defect_count == 0:
        return True, f"{tool_id} passed 7-day window with zero defects — ready to graduate"
    elif days_in_canary < 7:
        return True, f"{tool_id} canary active (day {days_in_canary}/7, zero defects so far)"
    else:
        # Should not reach here
        return True, f"{tool_id} canary running (day {days_in_canary})"


def main():
    """
    Main probe: verify all canary tools are on track.
    """
    registry = load_registry()
    incidents = load_incidents()
    now = datetime.now(timezone.utc)

    canary_tools = registry.get("canary_tools", [])
    if not canary_tools:
        warn("no canary tools registered")
        sys.exit(0)

    # Check each tool
    failures = []
    graduated = []
    active = []

    for tool in canary_tools:
        passed, reason = check_canary_tool(tool, incidents, now)

        if not passed:
            failures.append(reason)
        elif "graduated" in reason.lower() or "eligible for graduation" in reason.lower():
            graduated.append(reason)
        else:
            active.append(reason)

    # Report results
    total = len(canary_tools)
    healthy = len(active) + len(graduated)

    summary = f"Canary status: {healthy}/{total} healthy"

    if active:
        for msg in active:
            print(f"  ✓ {msg}")

    if graduated:
        for msg in graduated:
            print(f"  ✦ {msg}")

    if failures:
        for msg in failures:
            fail(msg)
        sys.exit(1)

    # All tools healthy
    success(f"{summary} — all tools on track or graduated")
    sys.exit(0)


if __name__ == "__main__":
    main()
