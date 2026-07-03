#!/usr/bin/env python3
"""
hale_bus_handoff.py — Inter-instance state handoff via shared JSON.

Claude Code ↔ OpenCode state synchronization. Enables seamless work handoff
when one instance is hot and another takes over.

Files:
  - core/hale_bus/hale_bus_state.json (shared state)
  - hale_decisions.md (logged decisions)

Usage:
    from core.hale_bus.hale_bus_handoff import HaleBusHandoff

    # Claude Code: checkpoint before handoff
    hale_bus = HaleBusHandoff("claude-code")
    context = hale_bus.read_prior_context()  # load from OpenCode session
    hale_bus.checkpoint_session()             # save for OpenCode to pick up

    # OpenCode: claim work from CC session
    hale_bus_oc = HaleBusHandoff("opencode")
    prior = hale_bus_oc.read_prior_context()  # load from CC checkpoint
    for mission in prior["open_tasks"]:
        hale_bus_oc.claim_work(mission["id"], status="in_progress")
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

ROOT = Path(__file__).parent.parent.parent


class HaleBusHandoff:
    """Inter-instance state handoff via hale_bus_state.json."""

    def __init__(self, instance_type: str = "claude-code"):
        """
        Args:
            instance_type: "claude-code" or "opencode"
        """
        self.instance = instance_type
        self.state_file = ROOT / "core" / "hale_bus" / "hale_bus_state.json"
        self.decisions_file = ROOT / "hale_decisions.md"

        # Ensure state file exists
        self._ensure_state_file()

    def _ensure_state_file(self):
        """Create state file if missing."""
        if not self.state_file.exists():
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            self._save_state(self._blank_state())

    def _blank_state(self) -> dict:
        """Return blank state structure."""
        return {
            "active_missions": {},
            "deferred_alerts": [],
            "fpd_alerts": [],
            "cached_zen": {},
            "open_tasks": [],
            "last_checkpoint": None,
        }

    def claim_work(self, mission_id: str, status: str = "in_progress"):
        """Register this instance as owner of a mission."""
        state = self._load_state()
        if "active_missions" not in state:
            state["active_missions"] = {}

        state["active_missions"][mission_id] = {
            "owner": self.instance,
            "status": status,
            "claimed_at": datetime.utcnow().isoformat(),
        }
        self._save_state(state)
        print(f"[{self.instance}] Claimed mission {mission_id} → {status}", file=sys.stderr)

    def release_work(self, mission_id: str):
        """Release ownership of a mission."""
        state = self._load_state()
        if "active_missions" in state and mission_id in state["active_missions"]:
            del state["active_missions"][mission_id]
            self._save_state(state)
            print(f"[{self.instance}] Released mission {mission_id}", file=sys.stderr)

    def update_mission_status(self, mission_id: str, status: str):
        """Update status of claimed mission."""
        state = self._load_state()
        if "active_missions" in state and mission_id in state["active_missions"]:
            state["active_missions"][mission_id]["status"] = status
            state["active_missions"][mission_id]["updated_at"] = datetime.utcnow().isoformat()
            self._save_state(state)

    def read_prior_context(self) -> dict:
        """Load inter-instance context from last session (prior instance's checkpoint)."""
        state = self._load_state()

        return {
            "alerts": state.get("deferred_alerts", []),
            "fpd_deadlines": state.get("fpd_alerts", []),
            "active_missions": state.get("active_missions", {}),
            "cached_zen": state.get("cached_zen", {}),
            "open_tasks": state.get("open_tasks", []),
            "last_checkpoint": state.get("last_checkpoint"),
        }

    def checkpoint_session(self):
        """Write session state for handoff to next instance."""
        state = self._load_state()

        # Capture current open tasks
        open_tasks = [
            {"id": k, **v}
            for k, v in state.get("active_missions", {}).items()
            if v.get("status") != "complete"
        ]

        state["open_tasks"] = open_tasks
        state["last_checkpoint"] = {
            "instance": self.instance,
            "timestamp": datetime.utcnow().isoformat(),
            "mission_count": len(open_tasks),
        }

        self._save_state(state)
        print(
            f"[{self.instance}] Checkpoint: {len(open_tasks)} open tasks, "
            f"{len(state.get('deferred_alerts', []))} alerts",
            file=sys.stderr
        )

    def handback_to_claude_code(self, releasing_instance: str = "opencode"):
        """Release instance missions, mark ready for Claude Code to claim."""
        state = self._load_state()

        # Release all missions owned by releasing instance
        active = state.get("active_missions", {})
        for mission_id, mission in list(active.items()):
            if mission.get("owner") == releasing_instance:
                mission["status"] = "ready_for_cc"
                mission["released_by"] = releasing_instance
                mission["released_at"] = datetime.utcnow().isoformat()

        state["last_handback"] = {
            "from": releasing_instance,
            "to": "claude-code",
            "timestamp": datetime.utcnow().isoformat(),
            "mission_count": sum(1 for m in active.values() if m.get("status") == "ready_for_cc"),
        }

        self._save_state(state)
        print(f"[{releasing_instance}] Handed back {state['last_handback']['mission_count']} missions to Claude Code", file=sys.stderr)

    def cache_zen_response(self, query: str, response: str, ttl_hours: int = 24):
        """Cache ZEN response for later reuse (24h TTL)."""
        state = self._load_state()
        if "cached_zen" not in state:
            state["cached_zen"] = {}

        state["cached_zen"][query] = {
            "response": response,
            "cached_at": datetime.utcnow().isoformat(),
            "ttl_hours": ttl_hours,
        }
        self._save_state(state)

    def get_cached_zen(self, query: str) -> Optional[str]:
        """Retrieve cached ZEN response if still valid."""
        state = self._load_state()
        cached = state.get("cached_zen", {}).get(query)

        if not cached:
            return None

        # Check TTL
        cached_at = datetime.fromisoformat(cached["cached_at"])
        ttl_hours = cached.get("ttl_hours", 24)
        age_hours = (datetime.utcnow() - cached_at).total_seconds() / 3600

        if age_hours > ttl_hours:
            return None  # Expired

        return cached["response"]

    def add_alert(self, alert_type: str, message: str, priority: str = "P1"):
        """Add deferred alert."""
        state = self._load_state()
        if "deferred_alerts" not in state:
            state["deferred_alerts"] = []

        state["deferred_alerts"].append({
            "type": alert_type,
            "message": message,
            "priority": priority,
            "added_at": datetime.utcnow().isoformat(),
        })
        self._save_state(state)

    def add_fpd_alert(self, client_name: str, fpd_date: str, amount: float, booking_ref: str):
        """Add FPD deadline alert."""
        state = self._load_state()
        if "fpd_alerts" not in state:
            state["fpd_alerts"] = []

        state["fpd_alerts"].append({
            "client": client_name,
            "fpd": fpd_date,
            "amount": amount,
            "booking_ref": booking_ref,
            "added_at": datetime.utcnow().isoformat(),
        })
        self._save_state(state)

    def log_decision(self, decision_title: str, reasoning: str, decision_details: Dict[str, Any]):
        """Log decision to hale_decisions.md."""
        if not self.decisions_file.exists():
            self.decisions_file.write_text("# Hale Decisions Log\n\n")

        entry = f"""
## {decision_title}
**Instance:** {self.instance}
**Timestamp:** {datetime.utcnow().isoformat()}
**Reasoning:** {reasoning}
**Details:** {json.dumps(decision_details, indent=2)}
"""
        with open(self.decisions_file, "a") as f:
            f.write(entry + "\n")

    def _load_state(self) -> dict:
        """Load state from JSON file."""
        if self.state_file.exists():
            try:
                return json.loads(self.state_file.read_text())
            except json.JSONDecodeError:
                print(f"[{self.instance}] WARNING: State file corrupted, resetting", file=sys.stderr)
                return self._blank_state()
        return self._blank_state()

    def _save_state(self, state: dict):
        """Save state to JSON file."""
        self.state_file.write_text(json.dumps(state, indent=2))

    def dump_state(self) -> str:
        """Pretty-print current state."""
        state = self._load_state()
        return json.dumps(state, indent=2)


if __name__ == "__main__":
    # Quick test
    hale_bus = HaleBusHandoff("claude-code")

    # Simulate work
    hale_bus.claim_work("MISSION-123", "in_progress")
    hale_bus.claim_work("MISSION-456", "pending")
    hale_bus.add_fpd_alert("McLeod", "2026-07-22", 11943.15, "2984034")
    hale_bus.cache_zen_response("counter-example", "ZEN response here")
    hale_bus.checkpoint_session()

    print("\n=== State ===")
    print(hale_bus.dump_state())

    print("\n=== Prior Context (for OpenCode) ===")
    context = hale_bus.read_prior_context()
    print(json.dumps(context, indent=2))
