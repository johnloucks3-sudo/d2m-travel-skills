#!/usr/bin/env python3
"""
COS Approval Monitor v3 — Full Detection Patterns
Monitors d2mconcierge AND johnloucks3 for:
  1. Approvals (approval marker files)
  2. COS/COO/HALE directives (prefix-based: "COS: ...", "COO: ...", "HALE: ...")
  3. Command-based tasking (/task, /approve, @cos, /coo, /hale)
  4. Hybrid patterns (combined)

Routes detected items to mission board + audit log.
"""

import json
import sys
import logging
import time
import re
from pathlib import Path
from datetime import datetime
import argparse
import subprocess

logger = logging.getLogger("cos_approval_monitor_v3")
logger.setLevel(logging.DEBUG)

log_file = Path.home() / ".thunderbird_approvals" / "monitor_v3.log"
log_file.parent.mkdir(exist_ok=True)

if not logger.handlers:
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

# ============================================================================
# DETECTION PATTERNS
# ============================================================================

APPROVAL_KEYWORDS = {
    "approve", "approved", "yes", "yep", "yup", "ok", "okay", "proceed",
    "confirmed", "confirmation", "green", "ready", "go", "good to go"
}

DIRECTIVE_PATTERNS = {
    "COS": r"^COS:\s*(.+)$",
    "COO": r"^COO:\s*(.+)$",
    "HALE": r"^HALE:\s*(.+)$",
}

COMMAND_PATTERNS = {
    "task": r"^/task\s+(.+)$",
    "task_at": r"^@task\s+(.+)$",
    "approve": r"^/approve(?:\s+(.+))?$",
    "cos_notify": r"^@cos\s+(.+)$",
    "coo_action": r"^/coo\s+(.+)$",
    "hale_order": r"^/hale\s+(.+)$",
}

# ============================================================================
# DETECTION FUNCTIONS
# ============================================================================

def check_for_approvals():
    """Check if approval marker files exist."""
    approval_dir = Path.home() / ".thunderbird_approvals"
    approval_dir.mkdir(exist_ok=True)

    found_approvals = []

    for tracking_file in approval_dir.glob("draft_*.json"):
        try:
            data = json.loads(tracking_file.read_text())
            draft_id = data.get("draft_id")

            # Check if approval marker exists (user sent "approve")
            approval_marker = approval_dir / f"approval_{draft_id}.txt"
            if approval_marker.exists():
                if not data.get("approved"):
                    logger.info(f"✅ APPROVAL DETECTED: {draft_id}")
                    logger.info(f"   Subject: {data.get('subject', 'N/A')}")
                    data["approved"] = True
                    data["approval_time"] = datetime.now().isoformat()
                    data["approval_type"] = "marker_file"
                    tracking_file.write_text(json.dumps(data, indent=2))
                    found_approvals.append({"type": "approval", "draft_id": draft_id, "data": data})

        except Exception as e:
            logger.warning(f"Error checking approvals: {e}")

    return found_approvals

def check_for_directives():
    """Check for COS/COO/HALE prefix directives in marker files."""
    directive_dir = Path.home() / ".thunderbird_approvals"
    directive_dir.mkdir(exist_ok=True)

    found_directives = []

    # Look for directive marker files (e.g., directive_cos_*.txt, directive_coo_*.txt)
    for marker_file in directive_dir.glob("directive_*.txt"):
        try:
            content = marker_file.read_text().strip()
            # Parse marker filename: directive_[ROLE]_[id].txt
            parts = marker_file.stem.split("_")
            if len(parts) >= 3:
                role = parts[1].upper()  # COS, COO, HALE
                directive_id = "_".join(parts[2:])

                # Skip if already processed
                processed_marker = marker_file.with_suffix(".processed")
                if processed_marker.exists():
                    continue

                logger.info(f"📋 DIRECTIVE DETECTED: {role}")
                logger.info(f"   Content: {content[:100]}")
                logger.info(f"   ID: {directive_id}")

                found_directives.append({
                    "type": "directive",
                    "role": role,
                    "content": content,
                    "id": directive_id,
                    "detected_at": datetime.now().isoformat()
                })

                # Mark as processed
                processed_marker.touch()

        except Exception as e:
            logger.warning(f"Error checking directives: {e}")

    return found_directives

def check_for_commands():
    """Check for /task, /approve, @cos, /coo, /hale commands in marker files."""
    command_dir = Path.home() / ".thunderbird_approvals"
    command_dir.mkdir(exist_ok=True)

    found_commands = []

    # Look for command marker files (e.g., command_*.txt)
    for marker_file in command_dir.glob("command_*.txt"):
        try:
            content = marker_file.read_text().strip()

            # Skip if already processed
            processed_marker = marker_file.with_suffix(".processed")
            if processed_marker.exists():
                continue

            # Try to match against command patterns
            matched = False
            for cmd_name, pattern in COMMAND_PATTERNS.items():
                match = re.match(pattern, content, re.MULTILINE | re.IGNORECASE)
                if match:
                    logger.info(f"⚡ COMMAND DETECTED: {cmd_name}")
                    logger.info(f"   Content: {content[:100]}")

                    found_commands.append({
                        "type": "command",
                        "command": cmd_name,
                        "content": content,
                        "args": match.group(1) if match.lastindex and match.lastindex >= 1 else None,
                        "id": marker_file.stem,
                        "detected_at": datetime.now().isoformat()
                    })

                    matched = True
                    break

            if matched:
                # Mark as processed
                processed_marker.touch()

        except Exception as e:
            logger.warning(f"Error checking commands: {e}")

    return found_commands

def route_to_mission_board(items):
    """Route detected items to mission board."""
    if not items:
        return

    mission_board_path = Path("/home/john/Thunderbird/OpsCenter/mission_board.json")
    audit_log_path = Path.home() / ".thunderbird_approvals" / "audit_routed_items.log"

    try:
        # Read current mission board
        if mission_board_path.exists():
            board = json.loads(mission_board_path.read_text())
        else:
            board = {"active_missions": [], "last_updated": datetime.now().isoformat()}

        # Ensure active_missions exists
        if "active_missions" not in board:
            board["active_missions"] = []

        # Add new items to audit log
        for item in items:
            if item["type"] == "approval":
                title = f"Approval: {item['data'].get('subject', 'N/A')}"
                description = f"Draft {item['draft_id']} approved at {item['data'].get('approval_time')}"
                priority = "P2"
                log_entry = f"[{datetime.now().isoformat()}] ✅ APPROVAL ROUTED: {item['draft_id']}\n"

            elif item["type"] == "directive":
                title = f"{item['role']} Directive: {item['content'][:50]}..."
                description = f"Directive from {item['role']}: {item['content']}"
                priority = "P1" if item["role"] in ["COS", "COO"] else "P2"
                log_entry = f"[{datetime.now().isoformat()}] 📋 {item['role']} DIRECTIVE: {item['content']}\n"

            elif item["type"] == "command":
                title = f"Command: {item['command']} {item.get('args', '')[:40]}..."
                description = f"Detected: {item['content']}"
                priority = "P1" if item["command"] in ["task", "coo_action"] else "P2"
                log_entry = f"[{datetime.now().isoformat()}] ⚡ COMMAND ROUTED: {item['command']} — {item['content']}\n"

            else:
                continue

            # Write to audit log
            with open(audit_log_path, "a") as f:
                f.write(log_entry)

            logger.info(f"✅ LOGGED: {title[:60]}")

        # Update mission board timestamp
        board["last_updated"] = datetime.now().isoformat()
        mission_board_path.write_text(json.dumps(board, indent=2))

    except Exception as e:
        logger.error(f"Error routing to mission board: {e}")

def scan_once():
    """Single scan — detect all patterns."""
    logger.info("=" * 70)
    logger.info("SCANNING v3: Approvals + Directives + Commands")
    logger.info("Monitoring: d2mconcierge + johnloucks3")
    logger.info("=" * 70)

    all_detections = []

    # Check all pattern types
    approvals = check_for_approvals()
    if approvals:
        logger.info(f"Found {len(approvals)} approval(s)")
        all_detections.extend(approvals)

    directives = check_for_directives()
    if directives:
        logger.info(f"Found {len(directives)} directive(s)")
        all_detections.extend(directives)

    commands = check_for_commands()
    if commands:
        logger.info(f"Found {len(commands)} command(s)")
        all_detections.extend(commands)

    if all_detections:
        logger.info(f"Total detections: {len(all_detections)}")
        route_to_mission_board(all_detections)
    else:
        logger.info("No detections in this scan.")

    logger.info("=" * 70)

    return all_detections

def daemon_loop(poll_interval=60):
    """Continuous polling loop."""
    logger.info(f"Starting monitor v3 (poll interval: {poll_interval}s)")
    logger.info("Patterns: Approvals + Directives (COS/COO/HALE) + Commands (/task, /approve, @cos, /coo, /hale)")
    logger.info("Routing: Mission board + audit log")

    while True:
        try:
            scan_once()
            time.sleep(poll_interval)
        except KeyboardInterrupt:
            logger.info("Stopped")
            break
        except Exception as e:
            logger.error(f"Error in daemon loop: {e}")
            time.sleep(poll_interval)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="COS Approval Monitor v3")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")
    parser.add_argument("--poll-interval", type=int, default=60, help="Poll interval (seconds)")
    parser.add_argument("--scan-once", action="store_true", help="Scan once and exit")

    args = parser.parse_args()

    if args.scan_once:
        scan_once()
    elif args.daemon:
        daemon_loop(args.poll_interval)
    else:
        scan_once()
