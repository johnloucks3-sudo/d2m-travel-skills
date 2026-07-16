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
  EXEC: add <title> <desc>  → Create new mission (Hale assigns — no NEXUS)
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

# Repo root on sys.path so the cross-Hale delegation wiring (core.relay.*,
# core.hale_bus.*) resolves under a bare `python3 OpsCenter/mission_board_sync.py`
# invocation, not only under pytest. Without this the `delegate` CLI path would
# import-crash even though _delegation_seats() falls back cleanly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

BOARD_PATH = Path(__file__).parent / "mission_board.json"
LOCK_PATH = Path(__file__).parent / "mission_board.lock"


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def _delegation_seats():
    """Cross-Hale seat codes that trigger the delegation-wiring path. Defensive
    lazy import so a bare CLI run (no repo root on sys.path) still creates
    persona-name / unassigned missions normally — those never touch this set."""
    try:
        from core.relay.task_delegation import SEATS
        return SEATS
    except Exception:
        return ("CC", "OC", "AG")


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


def _normalize_title(title):
    """Lowercase, strip punctuation/whitespace for duplicate comparison."""
    return "".join(c for c in title.lower() if c.isalnum() or c.isspace()).split()


def _find_open_duplicate(all_missions, title):
    """ONE AND DONE (fixed 2026-07-04 — Sterling/A7): before creating a new
    mission, check open missions for the same work already tracked under a
    different ID (e.g. MISSION-SEC-05/1510/1522 were the same GitHub
    credential rotation created 3 times; MISSION-820/1511/1523 were the same
    Regent portal auth created 3 times). Exact/substring match only — no
    fuzzy matching, which would silently merge genuinely distinct tasks.

    REGRESSION FIX (2026-07-16): TCD's Create Task action
    (tcd/writeback.py::_default_create_task_fn) files missions with
    status="pending_review", which this function didn't recognize as
    "open" — so every TCD-routed duplicate sailed straight past this check
    (Regent pricing x4, TESS restore x3+, WF-17 drafts x4, etc). Added
    "pending_review" to the open-status list and wired this function into
    the TCD path directly (see _default_create_task_fn)."""
    new_norm = _normalize_title(title)
    new_set = set(new_norm)
    if not new_set:
        return None
    for m in all_missions:
        if m.get("status") not in ("active", "in_progress", "pending", "open", "pending_review"):
            continue
        existing_norm = _normalize_title(m.get("title", ""))
        existing_set = set(existing_norm)
        if not existing_set:
            continue
        if new_set == existing_set:
            return m
        # substring: shorter title's words are a subset of the longer title's words
        shorter, longer = (new_set, existing_set) if len(new_set) <= len(existing_set) else (existing_set, new_set)
        if shorter and shorter.issubset(longer) and len(shorter) >= 3:
            return m
    return None


def add_mission(board, title, description="No description", priority="P0", assigned_to="unassigned", source=None,
                acceptance_criteria=None, certified_by=None, deadline_hours=None, task_type=None, from_seat="CC"):
    """Create a new mission on ``board`` (mutates in place) — the ONE place
    mission-creation + open-duplicate logic lives. ``cmd_add`` (the CLI's
    space-separated argv parser, below) and any structured/programmatic
    caller (MCP tools, TCD writeback, etc.) both delegate here so there is
    exactly one dedup code path, not one per caller — see
    _find_open_duplicate's REGRESSION FIX note (2026-07-16) for why three
    independent creation paths already burned this system once.

    CROSS-HALE DELEGATION WIRING (2026-07-16, design
    CROSS_HALE_TASK_DELEGATION_DESIGN §3.2-3.6): when ``assigned_to`` is a
    real cross-Hale seat (CC/OC/AG — NOT a persona name like "Hale" and NOT
    "unassigned"), the mission is a delegation ticket. It then REQUIRES
    ``acceptance_criteria`` (the PDTAC "T"), carries the extended schema
    (verification_artifact / certified_by / delegation_rationale / deadline),
    and is taken live on the C2 Fabric bus via
    core.relay.delegation_wiring.delegate_mission() — which validates the
    routing rationale, notifies the seat over the relay, and mirrors the
    ``assigned`` lifecycle stage onto hale_bus_state.json. ``certified_by``
    MUST differ from ``assigned_to`` (§3.5 anti-theater) or this raises.
    Persona-name / unassigned missions are untouched by this path.

    Does NOT acquire/release the board lock itself — callers that aren't
    already inside process_exec_command's lock (i.e. MCP tools) must wrap
    this in acquire_lock()/save_board() themselves.

    Returns (message, mission_id_or_None) — mission_id is None when the
    call was blocked as a duplicate (the existing mission's id is embedded
    in the message instead)."""
    all_missions = board.get("missions", board.get("active_missions", []))

    dup = _find_open_duplicate(all_missions, title)
    if dup is not None:
        dup.setdefault("logs", []).append(
            f"{now_iso()}: duplicate creation attempt blocked — \"{title}\" already tracked here"
        )
        dup["updated_at"] = now_iso()
        return (
            f"⚠️ Duplicate blocked — already tracked as {dup['id']} ({dup.get('status')}): "
            f"{dup['title']}\nNo new mission created. Use log/status/complete on {dup['id']} instead.",
            None,
        )

    # Find next available MISSION-NNN
    nums = []
    for m in all_missions:
        try:
            nums.append(int(m["id"].split("-")[-1]))
        except (ValueError, IndexError, KeyError):
            pass
    next_num = (max(nums) + 1) if nums else 1
    mission_id = f"MISSION-{next_num:03d}"

    is_delegation = assigned_to in _delegation_seats()
    new_mission = {
        "id": mission_id,
        "title": title,
        "status": "assigned" if is_delegation else "in_progress",
        "priority": priority,
        "assigned_to": assigned_to,
        "description": description,
        "deliverables": [],
        "dependencies": [],
        "suspense_date": None,
        "escalation_rule": None,
        "logs": [],
        "created_at": now_iso(),
        "updated_at": now_iso()
    }
    if source:
        new_mission["source"] = source

    if is_delegation:
        # Cross-Hale seat assignment → live delegation ticket on the C2 Fabric
        # bus. Requires acceptance_criteria (§3.5.1) and a cross-seat certifier
        # (§3.5.3); delegate_mission raises DelegationError if either is missing.
        from datetime import timedelta
        new_mission["acceptance_criteria"] = (acceptance_criteria or "").strip()
        new_mission["verification_artifact"] = ""
        new_mission["certified_by"] = certified_by or "CC"
        if deadline_hours:
            new_mission["deadline"] = (
                datetime.now(timezone.utc) + timedelta(hours=deadline_hours)
            ).isoformat()
        from core.relay.delegation_wiring import delegate_mission
        delegate_mission(new_mission, from_seat=from_seat, task_type=task_type)
        board.setdefault("missions", []).append(new_mission)
        return (
            f"✅ Delegated: {mission_id} — {title}\n"
            f"Priority: {priority} | Seat: {assigned_to} | Certifier: {new_mission['certified_by']}\n"
            f"Rationale: {new_mission['delegation_rationale']}",
            mission_id,
        )

    board.setdefault("missions", []).append(new_mission)
    return f"✅ Created: {mission_id} — {title}\nPriority: {priority} | Assigned: {assigned_to}", mission_id


def cmd_add(board, args):
    """EXEC: add <title> <description> [P0|P1|P2|P3] — CLI space-separated
    argv parser only. Kept byte-for-byte (including the title=first-3-words
    quirk existing Telegram/manual callers already depend on); creation +
    dedup now live in add_mission() above, the single source of truth."""
    args = list(args)
    # Honor a trailing priority token if present (default P0 for back-compat)
    priority = "P0"
    if args and args[-1].upper() in ("P0", "P1", "P2", "P3"):
        priority = args.pop().upper()
    # Parse simple format: EXEC: add MISSION-XXX title here
    title = " ".join(args[:3])
    desc = " ".join(args[3:]) if len(args) > 3 else "No description"

    message, _mission_id = add_mission(board, title, desc, priority, assigned_to="unassigned")
    return message


def cmd_delegate(board, arg_string):
    """EXEC: delegate SEAT :: title :: acceptance_criteria [:: PRIORITY :: task_type :: certifier]

    The real cross-Hale delegation entry point (CC/OC/AG). Fields are `::`-
    delimited because titles/criteria contain spaces the whitespace argv parser
    would shred. Delegates to add_mission(assigned_to=SEAT, ...), which fires
    delegate_mission() — routing validation + relay handoff + `assigned` bus
    mirror. certifier defaults to CC and MUST differ from SEAT (§3.5)."""
    seats = _delegation_seats()
    fields = [f.strip() for f in arg_string.split("::")]
    if len(fields) < 3 or not fields[0]:
        return ("❌ Usage: EXEC: delegate SEAT :: title :: acceptance_criteria "
                "[:: PRIORITY :: task_type :: certifier]\n"
                f"   SEAT ∈ {seats}")
    seat = fields[0].upper()
    if seat not in seats:
        return f"❌ Unknown seat {seat!r} — must be one of {seats}"
    title = fields[1]
    acceptance_criteria = fields[2]
    if not title or not acceptance_criteria:
        return "❌ title and acceptance_criteria are both required for a delegation"
    priority = fields[3].upper() if len(fields) > 3 and fields[3].upper() in ("P0", "P1", "P2", "P3") else "P2"
    task_type = fields[4] if len(fields) > 4 and fields[4] else None
    certifier = fields[5].upper() if len(fields) > 5 and fields[5] else "CC"

    try:
        from core.relay.delegation_wiring import DelegationError
    except ImportError:
        DelegationError = Exception
    try:
        message, _mission_id = add_mission(
            board, title, description=acceptance_criteria, priority=priority,
            assigned_to=seat, acceptance_criteria=acceptance_criteria,
            certified_by=certifier, task_type=task_type,
        )
        return message
    except DelegationError as e:
        return f"❌ Delegation rejected: {e}"


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
    
    # Cross-Hale delegation ticket → completion must clear the anti-theater
    # gate (§3.5): a cross-seat certifier + a verification_artifact. Enforced
    # here rather than silently flipping status, and mirrored onto the C2
    # Fabric bus as the `done` stage. Persona-name / unassigned missions are
    # untouched by this branch.
    if mission.get("assigned_to") in _delegation_seats() and mission.get("acceptance_criteria"):
        try:
            from core.relay.delegation_wiring import certify_mission, DelegationError
            try:
                certify_mission(
                    mission_id,
                    mission.get("assigned_to", ""),
                    mission.get("certified_by", "CC"),
                    mission.get("verification_artifact", ""),
                    mission.get("acceptance_criteria", ""),
                )
            except DelegationError as e:
                return (
                    f"⛔ Cannot complete {mission_id} — delegation gate: {e}\n"
                    f"Set a verification_artifact and a cross-seat certified_by first."
                )
        except ImportError:
            pass  # wiring unavailable (bare CLI, no repo root) — fall through

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
  EXEC: delegate SEAT :: title :: criteria [:: PRIO :: task_type :: certifier] → Cross-Hale delegate (CC/OC/AG)
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
        
        elif action == "delegate":
            # Reconstruct the raw remainder (the `::`-delimited fields) — the
            # whitespace split above would otherwise destroy titles/criteria.
            raw = text[len("delegate"):].strip()
            result = cmd_delegate(board, raw)

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
