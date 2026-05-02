#!/usr/bin/env python3
"""
Hale Telegram Tracker — Track Telegram activity integrated into hale_state_unified.json
Logs all incoming commands, dispatch outcomes, and failures reported to Commander.

PLATFORMS:
- Claude Code (primary dispatcher)
- OpenCode (headless operations, DeepSeek/Gemini models)

Both platforms read/write to same unified state. Telegram is the single source of truth
for all task lifecycles, whether routed to OpenCode or Claude Code.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

STATE_FILE = Path("/home/john/Thunderbird/hale_state_unified.json")

class HaleTelegramTracker:
    """Track Telegram activity across all platforms (Claude Code + OpenCode)."""

    def __init__(self):
        self.state = self._load_state()

    def _load_state(self) -> Dict:
        """Load unified state from disk."""
        if not STATE_FILE.exists():
            return {}
        try:
            return json.loads(STATE_FILE.read_text())
        except:
            return {}

    def log_incoming_command(
        self,
        command: str,
        user_id: str,
        message_text: str,
        routing_target: str = "opencode",
    ) -> Dict[str, Any]:
        """
        Log incoming Telegram command and routing decision.
        Called by Telegram bot when a command arrives.
        """
        if "telegram" not in self.state:
            self.state["telegram"] = {}

        telegram = self.state["telegram"]

        # Record command
        telegram["last_command"] = command
        telegram["last_message_received"] = datetime.now().isoformat()

        command_entry = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "command": command,
            "message_text": message_text[:100],  # First 100 chars
            "routing_target": routing_target,
            "status": "RECEIVED",
        }

        if "recent_commands" not in telegram:
            telegram["recent_commands"] = []

        telegram["recent_commands"].append(command_entry)

        # Keep only last 20 commands
        if len(telegram["recent_commands"]) > 20:
            telegram["recent_commands"] = telegram["recent_commands"][-20:]

        self._save_state()

        return {
            "logged": True,
            "command": command,
            "routing": routing_target,
            "timestamp": datetime.now().isoformat(),
        }

    def log_dispatch_outcome(
        self,
        command: str,
        routing_source: str,
        model: str,
        status: str,  # "SUCCESS", "ESCALATED", "FAILED"
        duration_seconds: float,
        output_brief: str = "",
        error_message: str = "",
    ) -> Dict[str, Any]:
        """
        Log dispatch outcome and report back to Telegram.
        Called after OpenCode/Claude Code completes a task.
        """
        if "telegram" not in self.state:
            self.state["telegram"] = {}

        telegram = self.state["telegram"]

        outcome_entry = {
            "timestamp": datetime.now().isoformat(),
            "command": command,
            "routing_source": routing_source,
            "model": model,
            "status": status,
            "duration_seconds": round(duration_seconds, 2),
            "output_brief": output_brief[:100],
            "error_message": error_message[:100] if error_message else "",
        }

        if "message_log" not in telegram:
            telegram["message_log"] = []

        telegram["message_log"].append(outcome_entry)

        # Keep only last 100 entries
        if len(telegram["message_log"]) > 100:
            telegram["message_log"] = telegram["message_log"][-100:]

        # Track failures
        if status == "FAILED":
            if "failures_reported" not in telegram:
                telegram["failures_reported"] = []

            telegram["failures_reported"].append({
                "timestamp": datetime.now().isoformat(),
                "command": command,
                "error": error_message,
                "routing_source": routing_source,
            })

            # Keep only last 20 failures
            if len(telegram["failures_reported"]) > 20:
                telegram["failures_reported"] = telegram["failures_reported"][-20:]

        self._save_state()

        return {
            "logged": True,
            "status": status,
            "command": command,
            "model": model,
            "duration_seconds": round(duration_seconds, 2),
        }

    def log_active_session(
        self,
        session_id: str,
        command: str,
        platform: str,  # "claude_code" or "opencode"
        status: str,  # "DISPATCHED", "RUNNING", "COMPLETE"
    ) -> Dict[str, Any]:
        """Log active Telegram session/command being processed."""
        if "telegram" not in self.state:
            self.state["telegram"] = {}

        telegram = self.state["telegram"]

        if "active_sessions" not in telegram:
            telegram["active_sessions"] = []

        session_entry = {
            "session_id": session_id,
            "command": command,
            "platform": platform,
            "status": status,
            "started": datetime.now().isoformat(),
        }

        # Update or add session
        existing = None
        for i, sess in enumerate(telegram["active_sessions"]):
            if sess["session_id"] == session_id:
                existing = i
                break

        if existing is not None:
            telegram["active_sessions"][existing] = session_entry
        else:
            telegram["active_sessions"].append(session_entry)

        self._save_state()
        return {"logged": True, "session_id": session_id}

    def remove_active_session(self, session_id: str):
        """Mark session as complete and remove from active list."""
        if "telegram" not in self.state:
            return

        telegram = self.state["telegram"]
        if "active_sessions" not in telegram:
            return

        telegram["active_sessions"] = [
            s for s in telegram["active_sessions"]
            if s["session_id"] != session_id
        ]

        self._save_state()

    def get_message_status(self) -> Dict[str, Any]:
        """Return summary of recent Telegram activity."""
        if "telegram" not in self.state:
            return {}

        telegram = self.state["telegram"]

        return {
            "bot_status": telegram.get("bot_status", "UNKNOWN"),
            "last_message_received": telegram.get("last_message_received"),
            "last_command": telegram.get("last_command"),
            "active_sessions_count": len(telegram.get("active_sessions", [])),
            "recent_commands_count": len(telegram.get("recent_commands", [])),
            "recent_failures_count": len(telegram.get("failures_reported", [])),
            "message_queue_depth": telegram.get("message_queue_depth", 0),
        }

    def report_failure_to_commander(
        self,
        command: str,
        error: str,
        routing_source: str,
    ) -> str:
        """
        Generate Telegram message for Commander when both OpenCode + Claude fail.
        """
        return (
            f"⚠️ Task failed: `{command}`\n"
            f"Error: {error}\n"
            f"Routing source: {routing_source}\n"
            f"Check logs: /home/john/Thunderbird/logs/hale_*.log"
        )

    def _save_state(self):
        """Write state back to disk."""
        STATE_FILE.write_text(json.dumps(self.state, indent=2))


# Integration hook for Telegram bot
def track_incoming_command(
    command: str,
    user_id: str,
    message_text: str,
    routing_target: str = "opencode",
) -> Dict[str, Any]:
    """
    Public interface: Call when Telegram command arrives.

    Usage in Telegram bot (Claude Code):
        from hale_telegram_tracker import track_incoming_command
        result = track_incoming_command("/status", "7554895206", "/status", "opencode")

    Usage in OpenCode (headless):
        from hale_telegram_tracker import track_incoming_command
        result = track_incoming_command("/analyze", "7554895206", message_text, "opencode")
    """
    tracker = HaleTelegramTracker()
    return tracker.log_incoming_command(command, user_id, message_text, routing_target)


def track_dispatch_outcome(
    command: str,
    routing_source: str,
    model: str,
    status: str,
    duration_seconds: float,
    output_brief: str = "",
    error_message: str = "",
) -> Dict[str, Any]:
    """
    Public interface: Call when dispatch completes (both Claude Code and OpenCode).

    Usage in OpenCode dispatch handler:
        from hale_telegram_tracker import track_dispatch_outcome
        result = track_dispatch_outcome(
            command="/analyze",
            routing_source="opencode",  # This dispatch came from OpenCode
            model="gemini-3.1-flash-lite",
            status="SUCCESS",
            duration_seconds=2.5,
            output_brief="Analysis complete: 3 trends identified"
        )

    Usage in Claude Code dispatch handler:
        result = track_dispatch_outcome(
            command="/analyze",
            routing_source="claude_code",  # This dispatch came from Claude Code
            model="claude-sonnet-4-6",
            status="SUCCESS",
            duration_seconds=1.2,
            output_brief="Strategic recommendation generated"
        )
    """
    tracker = HaleTelegramTracker()
    return tracker.log_dispatch_outcome(
        command, routing_source, model, status, duration_seconds, output_brief, error_message
    )


"""
OPENCODE INTEGRATION GUIDE:

1. On incoming Telegram command:
   from hale_telegram_tracker import track_incoming_command
   track_incoming_command(
       command=user_message,
       user_id="7554895206",
       message_text=user_message,
       routing_target="opencode"  # OpenCode is handling this
   )

2. When OpenCode dispatches to Gemini:
   from hale_telegram_tracker import track_dispatch_outcome
   track_dispatch_outcome(
       command=original_command,
       routing_source="opencode",
       model="gemini-3.1-flash-lite",
       status="SUCCESS" | "ESCALATED" | "FAILED",
       duration_seconds=elapsed,
       output_brief=result[:100],
       error_message=error if failed
   )

3. If OpenCode escalates to Claude Code:
   track_dispatch_outcome(
       command=original_command,
       routing_source="opencode",  # Still started in OpenCode
       model="gemini-2.0-flash-lite",  # Tried fallback first
       status="ESCALATED",
       duration_seconds=elapsed,
       error_message="Gemini 3.1 timeout - escalating to Claude Code"
   )

Result: All OpenCode activity visible in hale_state_unified.json['telegram']
"""

if __name__ == "__main__":
    # Test both platforms
    tracker = HaleTelegramTracker()

    print("=== OPENCODE WORKFLOW ===")
    # OpenCode receives command from Telegram
    tracker.log_incoming_command("/analyze", "7554895206", "/analyze cruise trends", "opencode")

    # OpenCode starts dispatching
    tracker.log_active_session("sess_001", "/analyze", "opencode", "DISPATCHED")

    # OpenCode executes in Gemini
    tracker.log_dispatch_outcome(
        "/analyze", "opencode", "gemini-3.1-flash-lite", "SUCCESS", 2.5,
        "Analysis complete: 3 trends identified"
    )
    tracker.remove_active_session("sess_001")

    print("\n=== CLAUDE CODE WORKFLOW ===")
    # Claude Code receives command
    tracker.log_incoming_command("/strategy", "7554895206", "/strategy for Q2", "claude_code")

    # Claude Code dispatches to Sonnet
    tracker.log_dispatch_outcome(
        "/strategy", "claude_code", "claude-sonnet-4-6", "SUCCESS", 1.2,
        "Strategic recommendations drafted"
    )

    print("\n=== TELEGRAM STATUS (BOTH PLATFORMS) ===")
    status = tracker.get_message_status()
    for key, val in status.items():
        print(f"{key}: {val}")

    print("\nFailure scenario:")
    failure_msg = tracker.report_failure_to_commander(
        "/analyze", "OpenCode timeout + Claude Code unavailable", "escalation_failed"
    )
    print(failure_msg)
