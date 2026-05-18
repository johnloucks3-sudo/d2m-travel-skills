#!/usr/bin/env python3
"""
MISSION BOARD SYNC — EXEC Interface
D2M Thunderbird OS · 2026-04-04
$0/month cost · No API calls required

Purpose: Passive read/write interface for Commander via CLI.
Called by: Telegram GW (voice), Gmail poller, manual CLI.
Never calls out — only reads/writes mission_board.json.

Commands:
  EXEC: list board          → Show all active missions
  EXEC: list suspended      → Show suspense queue
  EXEC: list complete       → Show completed missions
  EXEC: add <title> <desc>  → Create new mission (auto-P0)
  EXEC: add suspense <id> <date>  → Set suspense_date
  EXEC: complete <id>       → Mark mission done
  EXEC: status <id>         → Show mission details
  EXEC: log <id> <message>  → Append log entry
  EXEC: purge <id>          → Move to completed
  EXEC: help                → Show commands
"""

import json
import os
import sys
import fcntl
from datetime import datetime, timezone
from pathlib import Path

BOARD_PATH = Path(__file__).parent / "mission_board.json"
LOCK_PATH = Path(__file__).parent / "mission_board.lock"


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def acquire_lock():
    """Atomic lock to prevent concurrent board corruption."""
    os.makedirs(LOCK_PATH.parent, exist_ok=True)
    fd = open(LOCK_PATH, 'w')
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("BOARD LOCKED: Another process is writing. Try again in 3s.")
        sys.exit(3)
    fd.write(str(os.getpid()))
    fd.flush()
    return fd


def release_lock(fd):
    fcntl.flock(fd, fcntl.LOCK_UN)
    fd.close()
    try:
        LOCK_PATH.unlink()
    except FileNotFoundError:
        pass


def load_board():
    with open(BOARD_PATH, 'r') as f:
        return json.load(f)


def save_board(board, fd):
    with open(BOARD_PATH, 'w') as f:
        json.dump(board, f, indent=2, default=str)
    release_lock(fd)


def get_active(board):
    all_missions = board.get("missions", board.get("active_missions", []))
    return [m for m in all_missions if m.get("status") not in ("completed", "complete", "done", "cancelled")]


def find_mission(board, mission_id):
    """Search flat missions array for a mission by ID."""
    all_missions = board.get("missions", board.get("active_missions", []))
    for m in all_missions:
        if m["id"] == mission_id:
            status = m.get("status", "active")
            if status in ("completed", "complete", "done"):
                return m, "completed_missions"
            elif status == "suspended":
                return m, "suspended_missions"
            else:
                return m, "active_missions"
    return None, None


def cmd_list_board(board):
    """EXEC: list board"""
    active = get_active(board)
    if not active:
        return "📋 Mission Board: EMPTY\nNo active missions."
    
    lines = ["📋 MISSION BOARD (Active):", "=" * 40]
    for m in active:
        priority_flag = {"P0": "🔴", "P1": "🟠", "P2": "🟡", "P3": "🟢"}.get(m.get("priority", "P3"), "⚪")
        suspense = f" ⏰ {m.get('suspense_date', 'none')[:16]}" if m.get("suspense_date") else ""
        lines.append(f"{priority_flag} {m['id']}: {m['title']}")
        lines.append(f"    Status: {m['status']} | Priority: {m.get('priority', 'P3')} | To: {m.get('assigned_to', 'unassigned')}{suspense}")
    lines.append(f"\nTotal active: {len(active)}")
    return "\n".join(lines)


def cmd_list_suspended(board):
    """EXEC: list suspended"""
    all_missions = board.get("missions", board.get("suspended_missions", []))
    suspended = [m for m in all_missions if m.get("status") == "suspended"]
    if not suspended:
        return "⏸️ Suspended Queue: EMPTY"
    
    lines = ["⏸️ SUSPENDED MISSIONS:", "=" * 40]
    for m in suspended:
        suspense = m.get("suspense_date", "unknown")
        lines.append(f"⏰ {m['id']}: {m['title']} (suspended until {suspense[:16] if suspense else 'N/A'})")
    return "\n".join(lines)


def cmd_list_complete(board):
    """EXEC: list complete"""
    all_missions = board.get("missions", board.get("completed_missions", []))
    completed = [m for m in all_missions if m.get("status") in ("completed", "complete", "done")]
    if not completed:
        return "✅ Completed Missions: EMPTY"
    
    lines = ["✅ COMPLETED MISSIONS:", "=" * 40]
    for m in completed:
        lines.append(f"✅ {m['id']}: {m['title']}")
    return "\n".join(lines)


def cmd_add(board, args):
    """EXEC: add <title> [--priority P0|P1|P2|P3] [--to <assignee>] <description>"""
    # Parse simple format: EXEC: add MISSION-XXX title here
    title = " ".join(args[:3])
    desc = " ".join(args[3:]) if len(args) > 3 else "No description"
    
    # Generate ID
    all_missions = board.get("missions", board.get("active_missions", []))
    existing_ids = [m["id"] for m in all_missions]
    # Find next available MISSION-NNN
    nums = []
    for mid in existing_ids:
        try:
            nums.append(int(mid.split("-")[-1]))
        except (ValueError, IndexError):
            pass
    next_num = (max(nums) + 1) if nums else 1
    mission_id = f"MISSION-{next_num:03d}"
    
    new_mission = {
        "id": mission_id,
        "title": title,
        "status": "in_progress",
        "priority": "P0",
        "assigned_to": "NEXUS (auto)",
        "description": desc,
        "deliverables": [],
        "dependencies": [],
        "suspense_date": None,
        "escalation_rule": None,
        "logs": [],
        "created_at": now_iso(),
        "updated_at": now_iso()
    }
    
    if "missions" in board:
        board["missions"].append(new_mission)
    else:
        board.setdefault("active_missions", []).append(new_mission)
    return f"✅ Created: {mission_id} — {title}\nPriority: P0 | Assigned: NEXUS (auto)"


def cmd_suspense(board, mission_id, date_str):
    """EXEC: add suspense MISSION-001 2026-04-05T05:00:00Z"""
    mission, state = find_mission(board, mission_id)
    if not mission:
        return f"❌ Mission {mission_id} not found"
    
    mission["suspense_date"] = date_str
    mission["updated_at"] = now_iso()
    
    # Add to suspense_watch if not already
    watch = board.get("suspense_watch", [])
    if mission_id not in watch:
        watch.append(mission_id)
    board["suspense_watch"] = watch
    
    return f"⏰ Suspense set: {mission_id} until {date_str}"


def cmd_complete(board, mission_id):
    """EXEC: complete MISSION-001"""
    mission, state = find_mission(board, mission_id)
    if not mission:
        return f"❌ Mission {mission_id} not found"
    
    # Mark completed in-place (flat missions array)
    mission["status"] = "completed"
    mission["completed_at"] = now_iso()
    
    # Remove from suspense_watch
    watch = board.get("suspense_watch", [])
    if mission_id in watch:
        watch.remove(mission_id)
    board["suspense_watch"] = watch
    
    return f"✅ Completed: {mission['id']} — {mission['title']}"


def cmd_status(board, mission_id):
    """EXEC: status MISSION-001"""
    mission, state = find_mission(board, mission_id)
    if not mission:
        return f"❌ Mission {mission_id} not found"
    
    lines = [f"📋 {mission['id']}: {mission['title']}", f"State: {state} | Status: {mission['status']}",
             f"Priority: {mission.get('priority', 'P3')}", f"Assigned: {mission.get('assigned_to', 'unassigned')}",
             f"Created: {mission.get('created_at', '?')[:16]}", f"Updated: {mission.get('updated_at', '?')[:16]}"]
    
    if mission.get("description"):
        lines.append(f"\nDescription: {mission['description']}")
    if mission.get("suspense_date"):
        lines.append(f"⏰ Suspense: {mission['suspense_date']}")
    if mission.get("escalation_rule"):
        lines.append(f"⚠️ Escalation: {mission['escalation_rule']}")
    if mission.get("logs"):
        lines.append(f"\nRecent logs ({len(mission['logs'])}):")
        for log in mission["logs"][-3:]:
            lines.append(f"  - {log}")
    
    return "\n".join(lines)


def cmd_log(board, mission_id, message):
    """EXEC: log MISSION-001 <message>"""
    mission, state = find_mission(board, mission_id)
    if not mission:
        return f"❌ Mission {mission_id} not found"
    
    if "logs" not in mission:
        mission["logs"] = []
    
    log_entry = f"[{now_iso()[:19]}] {message}"
    mission["logs"].append(log_entry)
    mission["updated_at"] = now_iso()
    
    return f"📝 Log added to {mission_id}"


def cmd_help():
    """EXEC: help"""
    return """📋 EXEC Commands:
  EXEC: list board          → Show active missions
  EXEC: list suspended      → Show suspense queue
  EXEC: list complete       → Show completed
  EXEC: add <title> <desc>  → Create mission
  EXEC: add suspense <id> <date> → Set suspense
  EXEC: complete <id>       → Mark done
  EXEC: status <id>         → Show details
  EXEC: log <id> <msg>      → Add log entry
  EXEC: help                → This message"""


def process_exec_command(command_text):
    """Parse EXEC: command text and return response."""
    # Strip "EXEC: " prefix if present
    text = command_text.strip()
    if text.upper().startswith("EXEC:"):
        text = text[5:].strip()
    elif text.upper().startswith("EXEC "):
        text = text[5:].strip()
    
    parts = text.split()
    if not parts:
        return cmd_help()
    
    action = parts[0].lower()
    args = parts[1:]
    
    if action == "help":
        return cmd_help()
    
    fd = acquire_lock()
    try:
        board = load_board()
        
        if action == "list":
            sub = args[0].lower() if args else "board"
            if sub == "board":
                result = cmd_list_board(board)
            elif sub in ["suspended", "suspense"]:
                result = cmd_list_suspended(board)
            elif sub in ["complete", "completed", "done"]:
                result = cmd_list_complete(board)
            else:
                result = cmd_list_board(board)
        
        elif action == "add":
            if args and args[0].lower() in ["suspense", "suspend"]:
                # EXEC: add suspense MISSION-001 2026-04-05T05:00:00Z
                if len(args) >= 3:
                    result = cmd_suspense(board, args[1], args[2])
                else:
                    result = "❌ Usage: EXEC: add suspense <mission_id> <date>"
            else:
                result = cmd_add(board, args)
        
        elif action == "complete":
            if args:
                result = cmd_complete(board, args[0])
            else:
                result = "❌ Usage: EXEC: complete <mission_id>"
        
        elif action == "status":
            if args:
                result = cmd_status(board, args[0])
            else:
                result = "❌ Usage: EXEC: status <mission_id>"
        
        elif action == "log":
            if len(args) >= 2:
                result = cmd_log(board, args[0], " ".join(args[1:]))
            else:
                result = "❌ Usage: EXEC: log <mission_id> <message>"
        
        elif action == "purge":
            if args:
                result = cmd_complete(board, args[0])  # Same as complete
            else:
                result = "❌ Usage: EXEC: purge <mission_id>"
        
        else:
            result = f"❌ Unknown command: {action}\n{cmd_help()}"
        
        save_board(board, fd)
        return result
    except Exception as e:
        release_lock(fd)
        return f"❌ Board error: {e}"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(cmd_help())
        sys.exit(0)
    
    command = " ".join(sys.argv[1:])
    result = process_exec_command(command)
    print(result)
