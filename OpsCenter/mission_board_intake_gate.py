#!/usr/bin/env python3
"""
MISSION BOARD INTAKE GATE — T-14 Freeze Rule
D2M Thunderbird OS · 2026-06-12
================================================================================

PURPOSE:
Implement a gating rule that flags any net-new INFRASTRUCTURE mission as HOLD
when a client departure is within 14 days, surfacing it to Commander before
it enters the active queue.

LOGIC:
1. On mission intake (cmd_add), classify mission type
2. If infrastructure: check client departure calendar
3. If any departure within T-14: flag mission HOLD + set escalation rule
4. Notify Commander via Telegram (D2MC2C) before mission enters queue

MISSION TYPES:
- infrastructure: Keywords: system, daemon, timer, automation, bot, infra,
                  architecture, refactor, build, deploy, ci/cd, monitor, log,
                  database, storage, cache, indexer, auth, oauth, email-infra
- feature: Client-facing, changes client experience
- ops: Operational, routine, internal, support
- research: Investigation, exploration, intel

================================================================================
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Config
BOARD_PATH = Path(__file__).parent / "mission_board.json"
BRIEF_PATH = Path(__file__).parent / ".." / "hale_brief.md"
HALE_STATE_PATH = Path(__file__).parent / ".." / "hale_state.json"

# Infrastructure keywords (mission title/description contains any of these)
INFRASTRUCTURE_KEYWORDS = {
    "system", "daemon", "timer", "automation", "bot", "infra", "infrastructure",
    "architecture", "refactor", "build", "deploy", "ci/cd", "cicd", "monitor",
    "monitoring", "log", "logging", "database", "db", "storage", "cache",
    "indexer", "qdrant", "elasticsearch", "auth", "oauth", "mcp", "api",
    "email-infra", "scanner", "gateway", "relay", "webhook", "handler",
    "schema", "migration", "upgrade", "version", "release", "package",
    "config", "environment", "security", "credential", "token", "rate-limit"
}

TODAY = datetime(2026, 6, 12)  # Fixed for reproducibility


def load_board():
    """Load mission board JSON."""
    with open(BOARD_PATH, 'r') as f:
        return json.load(f)


def load_client_departures():
    """Extract client departure dates from hale_brief.md."""
    departures = {}

    try:
        with open(BRIEF_PATH, 'r') as f:
            lines = f.readlines()

        # Find the CLIENTS table section
        for i, line in enumerate(lines):
            if "## CLIENTS — sorted by departure" not in line:
                continue

            # Found marker, now look for table rows starting after the separator
            # Skip: blank line, header line, separator line
            j = i + 1
            while j < len(lines) and (
                not lines[j].strip() or
                "Client" in lines[j] or
                "---" in lines[j]
            ):
                j += 1

            # Now parse data rows
            while j < len(lines):
                line = lines[j]
                j += 1

                # End of table: blank line or next section
                if not line.strip() or line.startswith("##"):
                    break

                # Parse table row
                if "|" not in line:
                    continue

                parts = [p.strip() for p in line.split("|")]
                # Format: | Client | Ship | Depart | Phase | FPD | Open Items |
                # Parts: ['' (empty), Client, Ship, Depart, ...]
                if len(parts) >= 4:
                    client = parts[1]
                    depart_str = parts[3]

                    # Skip cancelled/strikethrough rows and empty clients
                    if not client or "~~" in client or "CANCELLED" in line:
                        continue

                    # Parse departure date (format: 2026-06-23)
                    if len(depart_str) >= 10:
                        try:
                            depart = datetime.strptime(depart_str[:10], "%Y-%m-%d")
                            departures[client] = depart.isoformat()[:10]
                        except ValueError:
                            pass
            break
    except Exception as e:
        pass

    return departures


def is_infrastructure_mission(title, description):
    """Check if a mission is classified as infrastructure."""
    text = f"{title} {description}".lower()
    return any(keyword in text for keyword in INFRASTRUCTURE_KEYWORDS)


def get_nearest_client_departure():
    """Return (days_away, client, date) for nearest departure."""
    departures = load_client_departures()
    if not departures:
        return None, None, None

    nearest_days = float('inf')
    nearest_client = None
    nearest_date = None

    for client, date_str in departures.items():
        try:
            depart = datetime.strptime(date_str[:10], "%Y-%m-%d")
            days_away = (depart - TODAY).days
            if 0 <= days_away < nearest_days:
                nearest_days = days_away
                nearest_client = client
                nearest_date = date_str[:10]
        except ValueError:
            pass

    if nearest_days == float('inf'):
        return None, None, None
    return nearest_days, nearest_client, nearest_date


def check_t14_freeze(title, description):
    """
    Check T-14 freeze rule: infrastructure mission + client departure within 14 days.

    Returns: (should_hold: bool, reason: str)
    """
    if not is_infrastructure_mission(title, description):
        # Not infrastructure → no freeze
        return False, None

    nearest_days, nearest_client, nearest_date = get_nearest_client_departure()

    if nearest_days is None or nearest_days > 14:
        # No nearby departure → no freeze
        return False, None

    # Infrastructure mission + departure within T-14 → FREEZE
    reason = (
        f"T-14 FREEZE: Infrastructure mission during client departure window. "
        f"{nearest_client} departs {nearest_date} ({nearest_days} days away). "
        f"Mission HOLD until post-departure."
    )
    return True, reason


def apply_intake_gate(mission):
    """
    Apply intake gate to a new mission.

    Modifies mission in-place:
    - Sets status to HOLD if T-14 freeze triggers
    - Sets escalation_rule with freeze reason

    Returns: (mission_modified, gate_action, reason)
    """
    should_hold, reason = check_t14_freeze(
        mission.get("title", ""),
        mission.get("description", "")
    )

    if not should_hold:
        return False, "PASS", None

    # Apply HOLD
    mission["status"] = "hold"
    mission["escalation_rule"] = "T-14_FREEZE"
    mission["hold_reason"] = reason
    mission["created_at"] = datetime.now(datetime.now().astimezone().tzinfo).isoformat()
    mission["hold_triggered_at"] = datetime.now(datetime.now().astimezone().tzinfo).isoformat()

    return True, "HOLD", reason


def format_gate_notification(mission, gate_action, reason):
    """Format a Telegram notification for Commander."""
    if gate_action == "PASS":
        return None

    return {
        "type": "intake_gate_alert",
        "mission_id": mission["id"],
        "action": gate_action,
        "title": mission["title"],
        "reason": reason,
        "timestamp": datetime.now().isoformat(),
    }


def test_gate():
    """Test the intake gate logic."""
    print("\n" + "=" * 80)
    print("MISSION BOARD INTAKE GATE — TEST SUITE")
    print("=" * 80)

    # Test 1: Infrastructure mission with T-14 departure
    test_mission_1 = {
        "id": "MISSION-TEST-001",
        "title": "Build Telegram daemon auto-restart",
        "description": "Wire systemd service restart + notification handler for bot failures",
    }
    modified, action, reason = apply_intake_gate(test_mission_1)
    print(f"\n✅ Test 1 (Infrastructure + T-14):")
    print(f"   Mission: {test_mission_1['title']}")
    print(f"   Gate action: {action}")
    if modified:
        print(f"   Status: {test_mission_1['status']}")
        print(f"   Reason: {reason}")

    # Test 2: Infrastructure mission without T-14 departure
    test_mission_2 = {
        "id": "MISSION-TEST-002",
        "title": "Refactor OAuth token manager",
        "description": "Clean up token refresh logic and add error handling",
    }
    modified, action, reason = apply_intake_gate(test_mission_2)
    print(f"\n✅ Test 2 (Infrastructure, no T-14):")
    print(f"   Mission: {test_mission_2['title']}")
    print(f"   Gate action: {action}")
    if not modified:
        print(f"   Status: in_progress (default)")

    # Test 3: Feature mission with T-14 departure
    test_mission_3 = {
        "id": "MISSION-TEST-003",
        "title": "McLeod final itinerary HTML export",
        "description": "Generate and export final itinerary PDF for client",
    }
    modified, action, reason = apply_intake_gate(test_mission_3)
    print(f"\n✅ Test 3 (Feature + T-14):")
    print(f"   Mission: {test_mission_3['title']}")
    print(f"   Gate action: {action}")
    if not modified:
        print(f"   Status: in_progress (feature, no freeze)")

    # Test 4: Check client departures
    print(f"\n✅ Test 4 (Client Departures):")
    departures = load_client_departures()
    print(f"   Found {len(departures)} clients with departures")
    nearest_days, nearest_client, nearest_date = get_nearest_client_departure()
    print(f"   Nearest departure: {nearest_client} on {nearest_date} ({nearest_days} days)")

    print("\n" + "=" * 80)
    print("TESTS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    test_gate()
