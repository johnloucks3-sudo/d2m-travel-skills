#!/usr/bin/env python3
"""Status Brief — "What am I working on?" in 3 seconds.
MISSION-052: Reads mission board + inbox + continuity log → one-paragraph brief.
"""
import json
import os
import re
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MISSION_BOARD = os.path.join(ROOT, "OpsCenter", "mission_board.json")
INBOX = os.path.join(ROOT, "OpsCenter", "collaboration", "opencode_inbox.md")
CONTINUITY_LOG = os.path.join(ROOT, "OpsCenter", "continuity_log.md")
OUTPUT = os.path.join(ROOT, "OpsCenter", "last_status.md")

def read_mission_board():
    missions = []
    try:
        with open(MISSION_BOARD) as f:
            data = json.load(f)
        for m in data.get("missions", []):
            if m.get("status") in ("active", "in_progress", "pending"):
                missions.append(m)
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return missions

def count_unread_inbox():
    try:
        with open(INBOX) as f:
            content = f.read()
        return len(re.findall(r"^status:\s*UNREAD", content, re.MULTILINE))
    except FileNotFoundError:
        return 0

def last_activity():
    try:
        with open(CONTINUITY_LOG) as f:
            lines = f.readlines()
        # Find last 3 log entries (lines starting with ### and date)
        entries = [l.strip() for l in lines if l.startswith("### 2026")]
        if entries:
            return entries[-1]
    except FileNotFoundError:
        pass
    return "No recent activity logged"

def generate_brief():
    missions = read_mission_board()
    unread = count_unread_inbox()
    activity = last_activity()

    active = [m for m in missions if m.get("status") == "active"]
    pending = [m for m in missions if m.get("status") in ("pending", "in_progress")]
    total = len(active) + len(pending)

    lines = []
    lines.append(f"# HALE-OC Status Brief — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("")
    lines.append(f"**Active missions:** {total} ({len(active)} active, {len(pending)} pending)")
    lines.append(f"**Inbox UNREAD:** {unread}")
    lines.append("")
    if active:
        lines.append("### Currently Active")
        for m in active[:5]:
            lines.append(f"- **{m['id']}**: {m['title']} — {m.get('status', 'unknown')}")
    if pending:
        lines.append("### Pending")
        for m in pending[:5]:
            lines.append(f"- **{m['id']}**: {m['title']} — assigned to {m.get('assigned_to', 'unknown')}")
    lines.append("")
    lines.append(f"**Last activity:** {activity}")
    lines.append("")
    lines.append("---")
    lines.append("Run `python3 core/ops/status_brief.py` to refresh.")

    brief = "\n".join(lines)

    with open(OUTPUT, "w") as f:
        f.write(brief)

    return brief

if __name__ == "__main__":
    print(generate_brief())
