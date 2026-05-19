#!/usr/bin/env python3
"""
D2MC2 Redis Connector (V2) - with Error Recovery Fallback
Tracks: decisions, command state, staff load
For COS operational command & control
NOTE: This is the refactored version using RedisConnectorFallback.
Inherits automatic local cache fallback when Redis is unavailable.
All public methods remain unchanged for backward compatibility.
"""
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path
from core.redis_connector_fallback import RedisConnectorFallback


class D2MC2RedisConnectorCLIV2(RedisConnectorFallback):
    """
    D2MC2 state management via Redis with automatic local cache fallback.

    Public API (unchanged from V1):
    - load_client_state(client_id) -> Dict
    - record_decision(decision_id, decision_type, question, options, owner, client_id) -> bool
    - get_open_decisions(decision_type=None) -> List[Dict]
    - approve_decision(decision_id, approved_by) -> bool
    - get_staff_load() -> Dict
    - set_staff_status(agent_id, active_tasks, status) -> bool

    New capabilities (from fallback base class):
    - Automatic fallback to local cache when Redis is unavailable
    - Periodic health checks (check_redis_health)
    - Cache sync on reconnect (_sync_cache_to_redis)
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 6379):
        # Initialize base class with D2MC2-specific cache directory
        cache_dir = Path.home() / ".thunderbird_cache" / "d2mc2"
        super().__init__(host=host, port=port, connector_name="d2mc2", cache_dir=cache_dir)

    def load_client_state(self, client_id: str) -> Dict[str, Any]:
        """
        Load full client state from Redis or local cache.

        Returns:
        - Client state dict if found
        - Default empty state if not found
        """
        key = f"ACTIVE_CLIENTS:{client_id}"

        # Try Redis first
        data_json = self._redis_cmd("HGET", key, "data")

        if data_json:
            try:
                return json.loads(data_json)
            except:
                pass

        # Try local cache
        cached_data = self._read_from_cache(key)
        if cached_data:
            return cached_data

        # Return default if not found
        return {
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
        Record a new decision to Redis with fallback to local cache.

        Returns:
        - True if saved to Redis
        - False if saved to local cache (Redis unavailable)
        """
        key = f"OPEN_DECISIONS:{decision_id}"

        decision_dict = {
            "decision_id": decision_id,
            "type": decision_type,
            "question": question,
            "options": options,
            "owner": owner,
            "client_id": client_id,
            "status": "open",
            "created": datetime.utcnow().isoformat(),
            "expires": (datetime.utcnow() + timedelta(days=7)).isoformat()
        }

        decision_json = json.dumps(decision_dict)
        result = self._redis_cmd("HSET", key, "data", decision_json)

        if result != "" and result != "(integer) 0":
            print(f"✅ Decision {decision_id} recorded to Redis")
            return True
        else:
            # Redis failed, fall back to local cache
            self._save_to_cache(key, decision_dict)
            print(f"✅ Decision {decision_id} recorded to local cache (Redis unavailable)")
            return False

    def get_open_decisions(self, decision_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all open decisions from Redis or local cache.

        Returns:
        - List of decision dicts matching criteria
        - Combines results from both Redis and local cache
        """
        decisions = []

        # Try Redis first
        if self.redis_available:
            keys = self._redis_cmd("KEYS", "OPEN_DECISIONS:*")

            if keys:
                for key in keys.split('\n'):
                    if not key:
                        continue
                    data_json = self._redis_cmd("HGET", key, "data")
                    if data_json:
                        try:
                            decision_data = json.loads(data_json)
                            if decision_data.get("status") == "open":
                                if decision_type is None or decision_data.get("type") == decision_type:
                                    decisions.append(decision_data)
                        except:
                            pass

        # Also check local cache (may have entries from when Redis was down)
        cached_keys = self._list_cached_keys("OPEN_DECISIONS:*")
        for key in cached_keys:
            cached_data = self._read_from_cache(key)
            if cached_data and cached_data.get("status") == "open":
                if decision_type is None or cached_data.get("type") == decision_type:
                    # Avoid duplicates
                    if not any(d["decision_id"] == cached_data["decision_id"] for d in decisions):
                        decisions.append(cached_data)

        return decisions

    def approve_decision(self, decision_id: str, approved_by: str) -> bool:
        """
        Mark decision as approved in Redis or local cache.

        Returns:
        - True if updated in Redis
        - False if updated in local cache (Redis unavailable)
        """
        key = f"OPEN_DECISIONS:{decision_id}"

        # Try Redis first
        data_json = self._redis_cmd("HGET", key, "data")

        if not data_json:
            # Try local cache
            data = self._read_from_cache(key)
            if not data:
                return False
            decision = data
        else:
            try:
                decision = json.loads(data_json)
            except:
                return False

        # Update decision status
        decision["status"] = "approved"
        decision["approved_by"] = approved_by
        decision["approved_at"] = datetime.utcnow().isoformat()

        # Save back to Redis
        new_json = json.dumps(decision)
        result = self._redis_cmd("HSET", key, "data", new_json)

        if result != "" and result != "(integer) 0":
            print(f"✅ Decision {decision_id} approved in Redis")
            return True
        else:
            # Redis failed, fall back to local cache
            self._save_to_cache(key, decision)
            print(f"✅ Decision {decision_id} approved in local cache")
            return False

    def get_staff_load(self) -> Dict[str, Dict[str, Any]]:
        """
        Get current staff workload from Redis or local cache.

        Returns:
        - Dict mapping agent_id to status dict
        - Combines results from both Redis and local cache
        """
        staff_data = {}

        # Try Redis first
        if self.redis_available:
            keys = self._redis_cmd("KEYS", "STAFF_LOAD:*")

            if keys:
                for key in keys.split('\n'):
                    if not key:
                        continue
                    agent_id = key.replace("STAFF_LOAD:", "")
                    # Get hash data
                    tasks = self._redis_cmd("HGET", key, "active_tasks")
                    status = self._redis_cmd("HGET", key, "status")
                    updated = self._redis_cmd("HGET", key, "last_updated")

                    staff_data[agent_id] = {
                        "active_tasks": tasks or "0",
                        "status": status or "idle",
                        "last_updated": updated or ""
                    }

        # Also check local cache
        cached_keys = self._list_cached_keys("STAFF_LOAD:*")
        for key in cached_keys:
            cached_data = self._read_from_cache(key)
            if cached_data:
                agent_id = key.replace("STAFF_LOAD:", "")
                # Skip if already loaded from Redis
                if agent_id not in staff_data:
                    staff_data[agent_id] = cached_data

        return staff_data

    def set_staff_status(self, agent_id: str, active_tasks: int, status: str = "idle") -> bool:
        """
        Update staff member status in Redis or local cache.

        Returns:
        - True if updated in Redis
        - False if updated in local cache (Redis unavailable)
        """
        key = f"STAFF_LOAD:{agent_id}"
        now = datetime.utcnow().isoformat()

        staff_dict = {
            "agent_id": agent_id,
            "active_tasks": active_tasks,
            "status": status,
            "last_updated": now
        }

        # Try Redis first
        result = self._redis_cmd("HSET", key, "data", json.dumps(staff_dict))

        if result != "" and result != "(integer) 0":
            print(f"✅ Staff status for {agent_id} updated in Redis")
            return True
        else:
            # Redis failed, fall back to local cache
            self._save_to_cache(key, staff_dict)
            print(f"✅ Staff status for {agent_id} updated in local cache")
            return False


# Test D2MC2 connector (V2 with fallback)
if __name__ == "__main__":
    print("=== D2MC2 REDIS CONNECTOR V2 (with Error Recovery) TEST ===\n")

    conn = D2MC2RedisConnectorCLIV2(host="127.0.0.1", port=6379)

    # Show Redis/cache status
    print(f"Redis available: {conn.redis_available}")
    print(f"Cache directory: {conn.cache_dir}\n")

    # Load client state
    client_state = conn.load_client_state("kuklinski")
    print(f"Client state loaded: {client_state['client_id']}\n")

    # Record a decision
    success = conn.record_decision(
        decision_id="STRAT-20260428-001",
        decision_type="strategic",
        question="Approve Panama Canal itinerary changes?",
        options=["approve_as_is", "request_modifications", "defer"],
        owner="A5_Castillo",
        client_id="kuklinski"
    )
    print(f"Decision recorded: {success}\n")

    # Get open decisions
    open_decisions = conn.get_open_decisions()
    print(f"Open decisions ({len(open_decisions)}):")
    for d in open_decisions:
        print(f"  - {d['decision_id']}: {d['question']}")

    # Set staff status
    conn.set_staff_status("A5_Castillo", active_tasks=3, status="active")
    print(f"\nStaff load: {conn.get_staff_load()}")

    # Health check
    print(f"\nPerforming health check...")
    conn.check_redis_health()
    print(f"Redis available after check: {conn.redis_available}")

    print("\n✅ D2MC2 connector V2 test complete")
