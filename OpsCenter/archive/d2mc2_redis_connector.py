"""
D2MC2 (Claude Code) Redis Connector Integration
Subclass of base connector with COS-specific methods
"""
from core.redis_connector import RedisConnector
from typing import Dict, Any, Optional, List
import json


class D2MC2RedisConnector(RedisConnector):
    """
    COS-specific Redis connector for D2MC2 (Claude Code decision engine)
    Adds COS-level state management: client state, open decisions, staff load
    """

    def load_client_state(self, client_id: str) -> Dict[str, Any]:
        """
        Load full client state from Redis
        Returns: name, phase, booking_ref, open_items, last_updated
        """
        state = self.get_client(client_id)
        return state or {
            "client_id": client_id,
            "name": None,
            "phase": "unknown",
            "booking_ref": None,
            "open_items": [],
            "last_updated": None
        }

    def record_decision(
        self,
        decision_id: str,
        decision_type: str,
        question: str,
        options: List[str],
        owner: str,
        client_id: Optional[str] = None
    ) -> bool:
        """
        Record a new decision to Redis
        Types: financial, operational, strategic, ethical, product
        """
        decision_dict = {
            "decision_id": decision_id,
            "type": decision_type,
            "question": question,
            "options": options,
            "owner": owner,
            "client_id": client_id,
            "status": "open",
            "created": self._timestamp(),
            "expires": self._expires_at(days=7)  # Auto-expire after 7 days
        }
        return self.save_decision(decision_id, decision_dict)

    def get_open_decisions(self, decision_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all open decisions, optionally filtered by type
        """
        all_decisions = self.get_all_decisions()
        decisions = []

        for decision_id, decision_data in all_decisions.items():
            if decision_data.get("status") == "open":
                if decision_type is None or decision_data.get("type") == decision_type:
                    decisions.append(decision_data)

        return decisions

    def approve_decision(self, decision_id: str, approved_by: str) -> bool:
        """Mark decision as approved"""
        decision = self.get_decision(decision_id)
        if not decision:
            return False

        decision["status"] = "approved"
        decision["approved_by"] = approved_by
        decision["approved_at"] = self._timestamp()
        return self.save_decision(decision_id, decision)

    def reject_decision(self, decision_id: str, reason: str) -> bool:
        """Mark decision as rejected"""
        decision = self.get_decision(decision_id)
        if not decision:
            return False

        decision["status"] = "rejected"
        decision["rejection_reason"] = reason
        decision["rejected_at"] = self._timestamp()
        return self.save_decision(decision_id, decision)

    def get_staff_load(self) -> Dict[str, Dict[str, Any]]:
        """Get current staff workload"""
        if not self.redis_client:
            return {}

        try:
            staff_data = {}
            keys = self.redis_client.keys("STAFF_LOAD:*")
            for key in keys:
                agent_id = key.replace("STAFF_LOAD:", "")
                data = self.redis_client.hgetall(key)
                staff_data[agent_id] = data
            return staff_data
        except Exception as e:
            print(f"⚠️  Failed to get staff load: {e}")
            return {}

    def set_staff_status(self, agent_id: str, active_tasks: int, status: str = "idle") -> bool:
        """Update staff member status"""
        if not self.redis_client:
            return False

        try:
            self.redis_client.hset(f"STAFF_LOAD:{agent_id}", "active_tasks", active_tasks)
            self.redis_client.hset(f"STAFF_LOAD:{agent_id}", "status", status)
            self.redis_client.hset(f"STAFF_LOAD:{agent_id}", "last_updated", self._timestamp())
            return True
        except Exception as e:
            print(f"❌ Failed to set staff status: {e}")
            return False

    @staticmethod
    def _timestamp() -> str:
        """ISO8601 timestamp"""
        from datetime import datetime
        return datetime.utcnow().isoformat()

    @staticmethod
    def _expires_at(days: int = 7) -> str:
        """Calculate expiry timestamp"""
        from datetime import datetime, timedelta
        expire_date = datetime.utcnow() + timedelta(days=days)
        return expire_date.isoformat()


# Test D2MC2 connector
if __name__ == "__main__":
    conn = D2MC2RedisConnector(host="127.0.0.1", port=6379)
    print(f"Health: {conn.health_check()}\n")

    # Load client state
    client_state = conn.load_client_state("kuklinski")
    print(f"Kuklinski state: {client_state}\n")

    # Record a decision
    conn.record_decision(
        decision_id="STRAT-20260428-001",
        decision_type="strategic",
        question="Approve Panama Canal itinerary changes?",
        options=["approve_as_is", "request_modifications", "defer"],
        owner="A5_Castillo",
        client_id="kuklinski"
    )
    print("✅ Decision recorded\n")

    # Get open decisions
    open_decisions = conn.get_open_decisions()
    print(f"Open decisions ({len(open_decisions)}):")
    for d in open_decisions:
        print(f"  - {d['decision_id']}: {d['question']}")

    # Set staff status
    conn.set_staff_status("A5_Castillo", active_tasks=3, status="active")
    print(f"\nStaff load: {conn.get_staff_load()}")
