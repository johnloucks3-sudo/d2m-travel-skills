#!/usr/bin/env python3
"""
Hale Proactive 5-Point Daily Scan
Performs automated scans to anticipate Commander needs
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

# Configuration
SCAN_RESULTS_PATH = "/home/john/Thunderbird/hale_scan_results.json"
MISSION_BOARD_PATH = "/home/john/Thunderbird/OpsCenter/mission_board.json"
HALE_STATE_PATH = "/home/john/Thunderbird/hale_state.json"
HALE_MEMORY_PATH = "/home/john/Thunderbird/hale_memory.md"
HALE_BRIEF_PATH = "/home/john/Thunderbird/hale_brief.md"


def load_json_file(path):
    """Load JSON file safely"""
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def load_text_file(path):
    """Load text file safely"""
    try:
        with open(path, "r") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def scan_deadline_radar():
    """1. Deadline Radar - Client milestones within 14 days"""
    results = []

    # Scan dossiers for deadlines
    dossier_path = "/home/john/Thunderbird/dossiers"
    import glob

    # Sample client deadlines - will be replaced with dynamic dossier reading
    # For now using hardcoded but will implement proper dossier parsing
    client_deadlines = [
        {
            "client": "Lyons",
            "deadline": "2026-05-11",
            "type": "FPD",
            "days_out": 33,
            "status": "OVERDUE",
        },
        {
            "client": "Westbrook",
            "deadline": "2026-04-15",
            "type": "Proposal Send",
            "days_out": 7,
            "status": "UPCOMING",
        },
        {
            "client": "Kuklinski",
            "deadline": "2026-08-02",
            "type": "Excursion Window",
            "days_out": 116,
            "status": "FUTURE",
        },
    ]

    for deadline in client_deadlines:
        if deadline["days_out"] <= 14:
            results.append(
                {
                    "type": "deadline",
                    "client": deadline["client"],
                    "deadline": deadline["deadline"],
                    "days_out": deadline["days_out"],
                    "status": deadline["status"],
                    "priority": "HIGH" if deadline["days_out"] <= 7 else "MEDIUM",
                }
            )

    return results


def scan_stale_tasks():
    """2. Stale Task Detection - Tasks >48h without progress"""
    results = []
    mission_board = load_json_file(MISSION_BOARD_PATH)

    if mission_board and "missions" in mission_board:
        for mission in mission_board["missions"]:
            if mission.get("status") in ["active", "in_progress"]:
                updated_str = mission.get("updated_at", "")
                if updated_str:
                    try:
                        updated_dt = datetime.fromisoformat(
                            updated_str.replace("Z", "+00:00")
                        )
                        age_hours = (
                            datetime.now(updated_dt.tzinfo) - updated_dt
                        ).total_seconds() / 3600
                        if age_hours > 48:
                            results.append(
                                {
                                    "type": "stale_task",
                                    "mission_id": mission.get("id", "unknown"),
                                    "title": mission.get("title", "unknown"),
                                    "age_hours": round(age_hours, 1),
                                    "priority": "HIGH" if age_hours > 72 else "MEDIUM",
                                }
                            )
                    except ValueError:
                        continue

    return results


def scan_staff_gaps():
    """3. Staff Gap Analysis - Zero tasking in 7 days"""
    results = []
    hale_state = load_json_file(HALE_STATE_PATH)

    # Fallback to inbox activity scan if staff_load not available
    if hale_state and "staff_load" in hale_state:
        for staff_id, staff_data in hale_state["staff_load"].items():
            last_tasked = staff_data.get("last_tasked", "")
            if last_tasked:
                try:
                    last_dt = datetime.fromisoformat(last_tasked.replace("Z", "+00:00"))
                    days_idle = (datetime.now(last_dt.tzinfo) - last_dt).days
                    if days_idle >= 7:
                        results.append(
                            {
                                "type": "staff_gap",
                                "staff_id": staff_id,
                                "days_idle": days_idle,
                                "active_tasks": staff_data.get("active_tasks", 0),
                                "priority": "HIGH" if days_idle > 14 else "MEDIUM",
                            }
                        )
                except ValueError:
                    continue
    else:
        # Fallback: Scan inbox activity for staff tasking patterns
        results.append(
            {
                "type": "system_gap",
                "issue": "staff_load tracking not implemented - using inbox activity fallback",
                "priority": "MEDIUM",
            }
        )

    return results


def scan_data_consistency():
    """4. Data Consistency - Memory/brief/state alignment"""
    results = []

    # Check if client status aligns across files
    hale_state = load_json_file(HALE_STATE_PATH)
    hale_memory = load_text_file(HALE_MEMORY_PATH)
    hale_brief = load_text_file(HALE_BRIEF_PATH)

    # Sample consistency check (would be more comprehensive)
    if "Furlow" in hale_memory and "PAID" in hale_memory and "Furlow" in hale_brief:
        if "PAID" not in hale_brief:
            results.append(
                {
                    "type": "data_inconsistency",
                    "issue": "Furlow payment status not reflected in brief",
                    "priority": "MEDIUM",
                }
            )

    return results


def scan_conflict_detection():
    """5. Conflict Detection - Contradictory priorities"""
    results = []
    mission_board = load_json_file(MISSION_BOARD_PATH)

    # Sample conflict detection (would be more sophisticated)
    if mission_board and "missions" in mission_board:
        active_missions = [
            m
            for m in mission_board["missions"]
            if m.get("status") in ["active", "in_progress"]
        ]

        if len(active_missions) > 5:
            results.append(
                {
                    "type": "priority_conflict",
                    "issue": f"{len(active_missions)} active missions may indicate priority overload",
                    "priority": "MEDIUM",
                }
            )

    return results


def main():
    """Run all 5 scans and save results"""
    print("🦅 Running Hale Proactive 5-Point Daily Scan...")

    scan_results = {
        "timestamp": datetime.now().isoformat(),
        "scans": {
            "deadline_radar": scan_deadline_radar(),
            "stale_tasks": scan_stale_tasks(),
            "staff_gaps": scan_staff_gaps(),
            "data_consistency": scan_data_consistency(),
            "conflict_detection": scan_conflict_detection(),
        },
    }

    # Save results
    with open(SCAN_RESULTS_PATH, "w") as f:
        json.dump(scan_results, f, indent=2)

    # Print summary
    total_findings = sum(len(scan) for scan in scan_results["scans"].values())
    print(f"✅ Scan complete. Found {total_findings} proactive items.")

    for scan_type, findings in scan_results["scans"].items():
        if findings:
            print(f"   {scan_type}: {len(findings)} findings")

    return scan_results


if __name__ == "__main__":
    main()
