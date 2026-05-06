#!/usr/bin/env python3
"""
thunderbird_coo_escalation.py — COO Watchdog Escalation Engine
Thunderbird OS | Dreams2Memories Travel, LLC | 2026-05-03

Handles mission board alerts, Commander email escalations, and audit logging
for COO watchdog failures. Deduplication prevents escalation spam.

Functions:
  escalate_to_mission_board(failure_dict) → bool
  escalate_to_email(failure_dict)         → bool
  log_escalation(failure_dict, attempt_type) → None
"""

import json
import logging
import sys
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── Config ─────────────────────────────────────────────────────────────────
LOG_FILE = Path("/home/john/Thunderbird/logs/coo_watchdog_escalations.log")
MISSION_BOARD_PATH = Path("/home/john/Thunderbird/OpsCenter/mission_board.json")
BOARD_LOCK_PATH = Path("/home/john/Thunderbird/OpsCenter/mission_board.lock")

COMMANDER_EMAIL = "johnloucks3@gmail.com"
WING_EMAIL = "d2mconcierge@gmail.com"

DEDUP_MISSION_WINDOW_MINUTES = 30
DEDUP_EMAIL_WINDOW_MINUTES = 60

# In-process dedup state: {service_name: {"mission": datetime, "email": datetime}}
_dedup_state: dict = {}

# ── Logging setup ──────────────────────────────────────────────────────────
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

_file_handler = logging.FileHandler(LOG_FILE, mode="a")
_file_handler.setFormatter(logging.Formatter("%(message)s"))

logger = logging.getLogger("coo_escalation")
logger.setLevel(logging.INFO)
if not logger.handlers:
    logger.addHandler(_file_handler)


# ── Helpers ────────────────────────────────────────────────────────────────

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now_utc().isoformat()


def _audit_id() -> str:
    return f"ESC-{uuid.uuid4().hex[:8].upper()}"


def _within_dedup_window(service_name: str, channel: str, window_minutes: int) -> bool:
    """Return True if a recent escalation exists within the dedup window."""
    entry = _dedup_state.get(service_name, {})
    last = entry.get(channel)
    if last is None:
        return False
    return (_now_utc() - last) < timedelta(minutes=window_minutes)


def _mark_dedup(service_name: str, channel: str) -> None:
    if service_name not in _dedup_state:
        _dedup_state[service_name] = {}
    _dedup_state[service_name][channel] = _now_utc()


def _board_has_recent_alert(service_name: str, window_minutes: int) -> bool:
    """Check mission board JSON for a recent open alert for this service."""
    try:
        import fcntl
        with open(MISSION_BOARD_PATH, "r") as f:
            board = json.load(f)
        cutoff = _now_utc() - timedelta(minutes=window_minutes)
        title_prefix = f"SYSTEM-ALERT: {service_name}"
        for mission in board.get("active_missions", []):
            if mission.get("title", "").startswith(title_prefix):
                created_str = mission.get("created_at", "")
                try:
                    created = datetime.fromisoformat(created_str)
                    if created.tzinfo is None:
                        created = created.replace(tzinfo=timezone.utc)
                    if created > cutoff:
                        return True
                except (ValueError, TypeError):
                    pass
    except Exception:
        pass
    return False


# ── Core Functions ─────────────────────────────────────────────────────────

def escalate_to_mission_board(failure_dict: dict) -> bool:
    """Create a mission board alert for a COO-detected failure.

    Returns True if item was created, False if duplicate within 30 minutes.
    """
    service_name = failure_dict.get("service_name", "UNKNOWN")
    tier = failure_dict.get("tier", 2)
    failure_reason = failure_dict.get("failure_reason", "Unknown failure")
    diagnostics = failure_dict.get("diagnostics", "No diagnostics available")
    timestamp = failure_dict.get("timestamp", _now_iso())
    self_healing_result = failure_dict.get("self_healing_result", "Not attempted")

    # Dedup: check in-process state first (fast), then board JSON (persistent across restarts)
    if _within_dedup_window(service_name, "mission", DEDUP_MISSION_WINDOW_MINUTES):
        log_escalation(failure_dict, "mission_board", result="SKIPPED (in-process dedup)")
        return False

    if _board_has_recent_alert(service_name, DEDUP_MISSION_WINDOW_MINUTES):
        _mark_dedup(service_name, "mission")
        log_escalation(failure_dict, "mission_board", result="SKIPPED (board dedup)")
        return False

    title = f"SYSTEM-ALERT: {service_name} degraded (Tier {tier})"
    description = (
        f"[{timestamp}] COO detected {service_name} failure.\n"
        f"Reason: {failure_reason}\n"
        f"Diagnostics:\n{diagnostics}\n"
        f"Self-healing: {self_healing_result}"
    )
    priority = "P1" if tier == 1 else "P2"

    try:
        # Import here to avoid circular at module load time
        sys.path.insert(0, str(Path(__file__).parent))
        from mission_board_sync import load_board, save_board, acquire_lock, now_iso

        fd = acquire_lock()
        board = load_board()

        existing_ids = [
            m["id"]
            for state in ["active_missions", "suspended_missions", "completed_missions"]
            for m in board.get(state, [])
        ]
        next_num = len(existing_ids) + 1
        mission_id = f"MISSION-{next_num:03d}"

        new_mission = {
            "id": mission_id,
            "title": title,
            "status": "open",
            "priority": priority,
            "assigned_to": "COS-AUTO",
            "description": description,
            "deliverables": [],
            "dependencies": [],
            "suspense_date": None,
            "escalation_rule": f"Tier {tier} auto-escalation from COO Watchdog",
            "logs": [f"[{timestamp}] Auto-created by COO Watchdog escalation engine"],
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }

        board["active_missions"].append(new_mission)
        save_board(board, fd)

        _mark_dedup(service_name, "mission")
        log_escalation(failure_dict, "mission_board", result=f"CREATED {mission_id}")
        return True

    except Exception as exc:
        log_escalation(failure_dict, "mission_board", result=f"ERROR: {exc}")
        return False


def escalate_to_email(failure_dict: dict) -> bool:
    """Send a Commander email for Tier 1 failures only.

    Returns True if email was sent, False if non-Tier-1 or duplicate within 1 hour.
    """
    tier = failure_dict.get("tier", 2)
    if tier != 1:
        log_escalation(failure_dict, "email", result="SKIPPED (not Tier 1)")
        return False

    service_name = failure_dict.get("service_name", "UNKNOWN")
    failure_reason = failure_dict.get("failure_reason", "Unknown failure")
    diagnostics = failure_dict.get("diagnostics", "No diagnostics available")
    timestamp = failure_dict.get("timestamp", _now_iso())
    self_healing_result = failure_dict.get("self_healing_result", "Not attempted")
    self_healing_attempted = failure_dict.get("self_healing_attempted", False)

    if _within_dedup_window(service_name, "email", DEDUP_EMAIL_WINDOW_MINUTES):
        log_escalation(failure_dict, "email", result="SKIPPED (dedup within 1h)")
        return False

    subject = f"URGENT: {service_name} failure - COO autonomous escalation"

    next_action = _infer_next_action(service_name, failure_reason)

    body = (
        f"Commander,\n\n"
        f"COO detected critical service failure at {timestamp}.\n\n"
        f"SERVICE: {service_name}\n"
        f"REASON: {failure_reason}\n\n"
        f"DIAGNOSTICS:\n{diagnostics}\n\n"
        f"SELF-HEALING ATTEMPTED: {'Yes' if self_healing_attempted else 'No'}\n"
        f"SELF-HEALING RESULT: {self_healing_result}\n\n"
        f"NEXT ACTION REQUIRED: {next_action}\n\n"
        f"Full audit trail: {LOG_FILE}\n\n"
        f"— Col Victoria Hale, COO | Thunderbird Wing"
    )

    try:
        sys.path.insert(0, str(Path(__file__).parent.parent / "core" / "email"))
        from thunderbird_gmail import gmail_send_from_wing

        result = gmail_send_from_wing(
            to=COMMANDER_EMAIL,
            subject=subject,
            body=body,
            persona_id="COS",
        )

        if result.get("status") == "success":
            _mark_dedup(service_name, "email")
            log_escalation(failure_dict, "email", result=f"SENT msg_id={result.get('message_id', 'unknown')}")
            return True
        else:
            log_escalation(failure_dict, "email", result=f"SEND_FAILED: {result}")
            return False

    except Exception as exc:
        log_escalation(failure_dict, "email", result=f"ERROR: {exc}")
        return False


def log_escalation(failure_dict: dict, attempt_type: str, result: str = "OK") -> None:
    """Append one line to the COO watchdog escalation audit log."""
    audit_id = _audit_id()
    service_name = failure_dict.get("service_name", "UNKNOWN")
    failure_reason = failure_dict.get("failure_reason", "Unknown")
    ts = _now_iso()

    line = f"[{ts}] | {audit_id} | {attempt_type} | {service_name} | {failure_reason} | {result}"

    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception as exc:
        # Last resort: stderr so it doesn't silently vanish
        print(f"LOG_WRITE_FAILED: {line} | err={exc}", file=sys.stderr)


# ── Helpers ────────────────────────────────────────────────────────────────

def _infer_next_action(service_name: str, failure_reason: str) -> str:
    """Return a human-readable suggested next action based on failure context."""
    s = service_name.lower()
    r = failure_reason.lower()

    if "token" in r or "auth" in r or "oauth" in r or "401" in r:
        return "Re-authenticate via Claude Desktop — run: python3 scripts/setup_d2mconcierge_oauth.py"
    if "telegram" in s:
        return "Check Telegram bot token and restart thunderbird_telegram_gw.service"
    if "mcp" in s or "mcp_server" in s:
        return "Restart thunderbird-mcp.service: sudo systemctl restart thunderbird-mcp.service"
    if "gmail" in s or "email" in s:
        return "Verify d2mconcierge OAuth token and Gmail API quota"
    if "disk" in r or "space" in r or "no space" in r:
        return "Free disk space on YOGA — check /home/john/Thunderbird/logs/ for large files"
    if "database" in r or "redis" in r:
        return "Check Redis service: sudo systemctl status redis"
    return "Review diagnostics above and restart the affected service. Escalate to COS if unresolved."


# ── CLI shim ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Quick smoke-test
    test_failure = {
        "service_name": "thunderbird-mcp",
        "tier": 1,
        "failure_reason": "MCP server stopped responding (timeout after 30s)",
        "diagnostics": "Port 8765 unreachable. Last heartbeat: 2026-05-03T10:00:00Z. systemctl status: failed.",
        "timestamp": _now_iso(),
        "self_healing_attempted": True,
        "self_healing_result": "Restart attempted via systemctl restart — process re-entered failed state after 5s",
    }

    print("=== COO Escalation Smoke Test ===")
    print(f"Mission board: {escalate_to_mission_board(test_failure)}")
    print(f"Email (Tier 1): {escalate_to_email(test_failure)}")
    print(f"Dedup check (should be False): {escalate_to_mission_board(test_failure)}")
    print(f"Log written to: {LOG_FILE}")
