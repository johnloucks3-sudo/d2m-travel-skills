#!/usr/bin/env python3
"""
Fix mission_board.json corruption - remove dangling entries with placeholder content
"""

import json
from pathlib import Path


def fix_mission_board():
    # Load the mission board
    board_path = Path("/home/john/Thunderbird/OpsCenter/mission_board.json")

    with open(board_path, "r") as f:
        data = json.load(f)

    print("🔧 Fixing mission board corruption...")

    # Find and remove missions with placeholder content
    corrupted_missions = []
    clean_missions = []

    for mission in data.get("active_missions", []):
        if mission.get("title") == "|" and mission.get("description") == "|":
            corrupted_missions.append(mission)
            print(f"❌ Removing corrupted mission: {mission.get('id')}")
        else:
            clean_missions.append(mission)

    # Update the active missions list
    data["active_missions"] = clean_missions

    # Create corruption audit log
    audit_log = {
        "fix_timestamp": "2026-04-08T19:00:00Z",
        "corrupted_missions_removed": len(corrupted_missions),
        "details": [
            {
                "mission_id": m.get("id"),
                "created_at": m.get("created_at"),
                "reason": "placeholder_content",
            }
            for m in corrupted_missions
        ],
    }

    # Save the fixed mission board
    with open(board_path, "w") as f:
        json.dump(data, f, indent=2)

    # Save audit log
    audit_path = Path("/home/john/Thunderbird/OpsCenter/mission_board_audit.json")
    with open(audit_path, "w") as f:
        json.dump(audit_log, f, indent=2)

    print(
        f"✅ Fixed mission board: Removed {len(corrupted_missions)} corrupted missions"
    )
    print(f"✅ Active missions now: {len(clean_missions)}")
    print(f"✅ Audit log saved to: {audit_path}")

    return len(corrupted_missions)


def validate_mission_board():
    """Validate the mission board structure"""
    board_path = Path("/home/john/Thunderbird/OpsCenter/mission_board.json")

    try:
        with open(board_path, "r") as f:
            data = json.load(f)

        # Check basic structure
        required_keys = [
            "active_missions",
            "completed_missions",
            "exec_inbox",
            "suspended_missions",
            "suspense_watch",
        ]
        missing_keys = [key for key in required_keys if key not in data]

        if missing_keys:
            print(f"❌ Missing keys: {missing_keys}")
            return False

        # Check mission status consistency
        for mission in data["active_missions"]:
            status = mission.get("status", "").lower()
            if status not in ["pending", "in_progress", "running"]:
                print(
                    f"⚠️  Unexpected status in active mission {mission.get('id')}: {status}"
                )

        print("✅ Mission board structure is valid")
        return True

    except json.JSONDecodeError as e:
        print(f"❌ JSON validation failed: {e}")
        return False


if __name__ == "__main__":
    print("=== MISSION BOARD REPAIR ===")

    # First validate current state
    print("\n🔍 Validating current mission board...")
    if not validate_mission_board():
        print("Current board has structural issues")

    # Fix corruption
    removed_count = fix_mission_board()

    # Validate after repair
    print("\n🔍 Validating after repair...")
    if validate_mission_board():
        print("✅ Mission board repair completed successfully!")
    else:
        print("❌ Repair may not have fixed all issues")

    # Update MISSION-004 status if we fixed the corruption
    if removed_count > 0:
        print(
            f"\n📋 MISSION-004 can now be marked COMPLETE - removed {removed_count} corrupted missions"
        )
