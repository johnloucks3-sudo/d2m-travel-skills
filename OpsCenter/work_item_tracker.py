#!/usr/bin/env python3
"""
Work Item Tracker — Monitor 8 autonomous runner action items
Status: In progress → Complete
Reports: Morning brief + weekly review only
Escalation: RED status (deadline passed) or critical blocker
"""

import json
from pathlib import Path
from datetime import datetime, timedelta

TRACKER_FILE = Path("/home/john/Thunderbird/OpsCenter/work_items_active.json")

INITIAL_ITEMS = [
    {
        "id": "WI-001",
        "title": "Grandeur Furlow HEL→ARN seat assignment",
        "owner": "Sterling",
        "priority": "P0",
        "deadline": "2026-06-13",  # This week
        "status": "open",
        "created": "2026-06-06",
        "notes": "Finnair AA 9018, PNR BB4X94, 2 seats unassigned"
    },
    {
        "id": "WI-002",
        "title": "McLeod Hilton Molino Stucky CRS confirmation",
        "owner": "Dembe",
        "priority": "P1",
        "deadline": "2026-06-15",
        "status": "open",
        "created": "2026-06-06",
        "notes": "Verbal confirmation only (May 5), needs CRS # for client delivery"
    },
    {
        "id": "WI-003",
        "title": "McLeod pre-voyage coordination (phone #, GIF, charges)",
        "owner": "Dembe",
        "priority": "P1",
        "deadline": "2026-06-17",  # T-6 before embark
        "status": "open",
        "created": "2026-06-06",
        "notes": "Collect phone numbers, verify GIF on MySilversea, settle $716 charges"
    },
    {
        "id": "WI-004",
        "title": "Kuklinski Jun 15 validation email",
        "owner": "Dembe",
        "priority": "P1",
        "deadline": "2026-06-15",
        "status": "open",
        "created": "2026-06-06",
        "notes": "DUE IN 9 DAYS — Monthly validation touch to all 3 couples"
    },
    {
        "id": "WI-005",
        "title": "Kuklinski Josh Morton form resolution",
        "owner": "Dembe",
        "priority": "P1",
        "deadline": "2026-06-20",
        "status": "open",
        "created": "2026-06-06",
        "notes": "Follow up with Kyle Kuklinski on Josh's missing GIF"
    },
    {
        "id": "WI-006",
        "title": "Grandeur Furlow missing address + seat docs",
        "owner": "Dembe",
        "priority": "P1",
        "deadline": "2026-06-20",
        "status": "open",
        "created": "2026-06-06",
        "notes": "Collect Melissa email + address, confirm DFW→HEL seat docs"
    },
    {
        "id": "WI-007",
        "title": "Kuklinski post-departure insurance options",
        "owner": "Intel",
        "priority": "P1",
        "deadline": "2026-06-20",  # E-180 gate
        "status": "open",
        "created": "2026-06-06",
        "notes": "Research Viking post-departure TP availability (pre-existing closed Feb 23)"
    },
    {
        "id": "WI-008",
        "title": "Grandeur excursion recommendations",
        "owner": "Dembe",
        "priority": "P2",
        "deadline": "2026-08-22",
        "status": "open",
        "created": "2026-06-06",
        "notes": "Send to all 3 couples before Aug 22 close date"
    }
]

def init_tracker():
    """Initialize work item tracker."""
    if not TRACKER_FILE.exists():
        data = {
            "created": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "items": INITIAL_ITEMS
        }
        TRACKER_FILE.write_text(json.dumps(data, indent=2))
        print(f"✅ Tracker initialized: {TRACKER_FILE}")
    else:
        print(f"ℹ️  Tracker already exists: {TRACKER_FILE}")

def load_tracker():
    """Load current work items."""
    if not TRACKER_FILE.exists():
        init_tracker()
    return json.loads(TRACKER_FILE.read_text())

def save_tracker(data):
    """Save work items."""
    data["last_updated"] = datetime.now().isoformat()
    TRACKER_FILE.write_text(json.dumps(data, indent=2))

def mark_complete(item_id, notes=""):
    """Mark work item as complete."""
    data = load_tracker()
    for item in data["items"]:
        if item["id"] == item_id:
            item["status"] = "complete"
            item["completed"] = datetime.now().isoformat()
            if notes:
                item["notes"] += f" [COMPLETED: {notes}]"
            save_tracker(data)
            print(f"✅ {item_id}: {item['title']} → COMPLETE")
            return
    print(f"❌ {item_id} not found")

def mark_in_progress(item_id):
    """Mark work item as in progress."""
    data = load_tracker()
    for item in data["items"]:
        if item["id"] == item_id:
            item["status"] = "in_progress"
            item["started"] = datetime.now().isoformat()
            save_tracker(data)
            print(f"🔄 {item_id}: {item['title']} → IN PROGRESS")
            return
    print(f"❌ {item_id} not found")

def get_status_brief():
    """Return status for morning brief."""
    data = load_tracker()
    items = data["items"]

    total = len(items)
    complete = sum(1 for i in items if i["status"] == "complete")
    open_count = sum(1 for i in items if i["status"] == "open")
    in_progress = sum(1 for i in items if i["status"] == "in_progress")

    red_items = []
    for item in items:
        if item["status"] != "complete":
            deadline = datetime.fromisoformat(item["deadline"]).date()
            if deadline <= datetime.now().date():
                red_items.append(item)

    return {
        "summary": f"{complete}/{total} complete | {in_progress} in progress | {open_count} open",
        "percentage": round(100 * complete / total) if total > 0 else 0,
        "red_items": red_items,
        "status_by_priority": {
            "P0": sum(1 for i in items if i["priority"] == "P0" and i["status"] != "complete"),
            "P1": sum(1 for i in items if i["priority"] == "P1" and i["status"] != "complete"),
            "P2": sum(1 for i in items if i["priority"] == "P2" and i["status"] != "complete")
        }
    }

def print_status():
    """Print full status report."""
    data = load_tracker()
    items = data["items"]

    print("\n" + "="*70)
    print("WORK ITEM TRACKER — AUTONOMOUS RUNNER ACTION ITEMS")
    print("="*70)

    by_status = {"open": [], "in_progress": [], "complete": []}
    for item in items:
        by_status[item["status"]].append(item)

    # Open items
    if by_status["open"]:
        print("\n🔴 OPEN:")
        for item in by_status["open"]:
            days_left = (datetime.fromisoformat(item["deadline"]).date() - datetime.now().date()).days
            status_icon = "🔴" if days_left <= 7 else "🟠" if days_left <= 14 else "🟡"
            print(f"  {status_icon} {item['id']} | {item['owner']:10} | {item['priority']} | T-{days_left:2}")
            print(f"      {item['title']}")

    # In progress
    if by_status["in_progress"]:
        print("\n🔄 IN PROGRESS:")
        for item in by_status["in_progress"]:
            print(f"  🔄 {item['id']} | {item['owner']:10} | {item['priority']}")
            print(f"      {item['title']}")

    # Complete
    if by_status["complete"]:
        print("\n✅ COMPLETE:")
        for item in by_status["complete"]:
            print(f"  ✅ {item['id']} | {item['owner']:10}")
            print(f"      {item['title']}")

    # Summary
    total = len(items)
    complete = len(by_status["complete"])
    print(f"\nSUMMARY: {complete}/{total} complete ({round(100*complete/total)}%)")

    # Red alerts
    brief = get_status_brief()
    if brief["red_items"]:
        print("\n🚨 OVERDUE:")
        for item in brief["red_items"]:
            print(f"  {item['id']} | {item['owner']} | {item['deadline']}")
            print(f"      {item['title']}")

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        init_tracker()
        print_status()
    elif sys.argv[1] == "init":
        init_tracker()
    elif sys.argv[1] == "status":
        print_status()
    elif sys.argv[1] == "brief":
        brief = get_status_brief()
        print(json.dumps(brief, indent=2))
    elif sys.argv[1] == "complete":
        if len(sys.argv) >= 3:
            mark_complete(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "")
        else:
            print("Usage: work_item_tracker.py complete <ITEM_ID> [notes]")
    elif sys.argv[1] == "in_progress":
        if len(sys.argv) >= 3:
            mark_in_progress(sys.argv[2])
        else:
            print("Usage: work_item_tracker.py in_progress <ITEM_ID>")
