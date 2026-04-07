"""
NEXUS Configuration — All paths, thresholds, and action whitelist.
Imported by nexus.py via: from config import *

Paths:
  BASE_DIR          — OpsCenter directory (auto-derived from config.py's __file__)
  MISSION_BOARD      — JSON state file for mission tracking
  OPENCODE_INBOX     — OpenCode agent inbox (collaboration/opencode_inbox.md)
  CLAUDE_INBOX       — Claude agent inbox (sibling dir ../claude_inbox.md)
  AUDIT_LOG          — Nexus daemon audit log (global Thunderbird/logs/)
  NEXUS_LOCK         — File lock to prevent concurrent daemon instances
  ROUTING_LOG        — Audit trail of agent routing decisions (collaboration/)

Thresholds:
  MAX_ITERATIONS     — Max spawns per mission (hard stop 1)
  MAX_TTL_HOURS      — Max wall-clock hours per mission (hard stop 2)
  MAX_TOKENS         — Token budget per mission (hard stop 3)
  DEADLOCK_THRESHOLD — Iterations with unchanged status → deadlock (hard stop 4)
  HEARTBEAT_INTERVAL — Seconds between lock heartbeat updates (child process)

Actions:
  ALLOWED_ACTIONS    — Whitelist of valid next_action values (no blind pass-through)
"""

from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
MISSION_BOARD = BASE_DIR / "mission_board.json"
AUDIT_LOG = Path("/home/john/Thunderbird/logs/nexus_audit.log")
NEXUS_LOCK = BASE_DIR / "nexus.lock"
OPENCODE_INBOX = BASE_DIR / "collaboration/opencode_inbox.md"
GOOSE_INBOX = OPENCODE_INBOX  # legacy alias — goose_inbox.md → opencode_inbox.md
CLAUDE_INBOX = BASE_DIR.parent / "claude_inbox.md"
ROUTING_LOG = BASE_DIR / "collaboration/routing_log.md"

# ── Limits / Thresholds ─────────────────────────────────────────────────────
MAX_ITERATIONS = 6              # Hard stop 1: max spawns per mission
MAX_TTL_HOURS = 4               # Hard stop 2: max wall-clock hours
MAX_TOKENS = 50_000             # Hard stop 3: token budget per mission
DEADLOCK_THRESHOLD = 2          # Hard stop 4: iterations w/ no status change
HEARTBEAT_INTERVAL = 30         # Seconds between lock heartbeat writes

# ── Action Whitelist (no blind pass-through) ─────────────────────────────────
ALLOWED_ACTIONS = {
    "route_to_qwen",
    "route_to_claude",
    "mark_complete",
    "mark_deadlock",
    "escalate_commander",
    "log_iteration",
    "check_suspense",
    "update_board",
}
