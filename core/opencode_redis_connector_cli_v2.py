#!/usr/bin/env python3
"""
OpenCode Redis Connector (V2) - with Error Recovery Fallback
Tracks: mission board, task state, orchestration state
For OpsCenter/OpenCode task automation
NOTE: This is the refactored version using RedisConnectorFallback.
Inherits automatic local cache fallback when Redis is unavailable.
All public methods remain unchanged for backward compatibility.
"""
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
from core.redis_connector_fallback import RedisConnectorFallback


class OpenCodeRedisConnectorCLIV2(RedisConnectorFallback):
    """
    OpenCode mission board and task state via Redis with automatic local cache fallback.

    Public API (unchanged from V1):
    - create_mission(mission_id, title, description, priority, assigned_to) -> bool
    - get_open_missions(priority=None) -> List[Dict]
    - update_mission_status(mission_id, new_status) -> bool
    - save_orchestration_state(state_key, state_data) -> bool
    - get_orchestration_state(state_key) -> Dict

    New capabilities (from fallback base class):
    - Automatic fallback to local cache when Redis is unavailable
    - Periodic health checks (check_redis_health)
    - Cache sync on reconnect (_sync_cache_to_redis)
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 6379):
        # Initialize base class with OpenCode-specific cache directory
        cache_dir = Path.home() / ".thunderbird_cache" / "opencode"
        super().__init__(host=host, port=port, connector_name="opencode", cache_dir=cache_dir)

    def create_mission(
        self,
        mission_id: str,
        title: str,
        description: str,
        priority: str,
        assigned_to: str
    ) -> bool:
        """
        Create a mission on the board with fallback to local cache.

        Returns:
        - True if saved to Redis
        - False if saved to local cache (Redis unavailable)
        """
        key = f"OPENCODE_MISSIONS:{mission_id}"

        mission_dict = {
            "mission_id": mission_id,
            "title": title,
            "description": description,
            "priority": priority,
            "assigned_to": assigned_to,
            "status": "open",
            "created": datetime.utcnow().isoformat(),
            "updated": datetime.utcnow().isoformat()
        }

        mission_json = json.dumps(mission_dict)
        result = self._redis_cmd("HSET", key, "data", mission_json)

        if result != "" and result != "(integer) 0":
            print(f"✅ Mission {mission_id} created in Redis")
            return True
        else:
            # Redis failed, fall back to local cache
            self._save_to_cache(key, mission_dict)
            print(f"✅ Mission {mission_id} created in local cache (Redis unavailable)")
            return False

    def get_open_missions(self, priority: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all open missions from Redis or local cache.

        Returns:
        - List of mission dicts matching criteria
        - Combines results from both Redis and local cache
        """
        missions = []

        # Try Redis first
        if self.redis_available:
            keys = self._redis_cmd("KEYS", "OPENCODE_MISSIONS:*")

            if keys:
                for key in keys.split('\n'):
                    if not key:
                        continue
                    data_json = self._redis_cmd("HGET", key, "data")
                    if data_json:
                        try:
                            mission_data = json.loads(data_json)
                            if mission_data.get("status") == "open":
                                if priority is None or mission_data.get("priority") == priority:
                                    missions.append(mission_data)
                        except:
                            pass

        # Also check local cache
        cached_keys = self._list_cached_keys("OPENCODE_MISSIONS:*")
        for key in cached_keys:
            cached_data = self._read_from_cache(key)
            if cached_data and cached_data.get("status") == "open":
                if priority is None or cached_data.get("priority") == priority:
                    # Avoid duplicates
                    if not any(m["mission_id"] == cached_data["mission_id"] for m in missions):
                        missions.append(cached_data)

        return missions

    def update_mission_status(self, mission_id: str, new_status: str) -> bool:
        """
        Update mission status in Redis or local cache.

        Returns:
        - True if updated in Redis
        - False if updated in local cache (Redis unavailable)
        """
        key = f"OPENCODE_MISSIONS:{mission_id}"

        # Try Redis first
        data_json = self._redis_cmd("HGET", key, "data")

        if not data_json:
            # Try local cache
            data = self._read_from_cache(key)
            if not data:
                return False
            mission = data
        else:
            try:
                mission = json.loads(data_json)
            except:
                return False

        # Update mission status
        mission["status"] = new_status
        mission["updated"] = datetime.utcnow().isoformat()

        # Save back to Redis
        new_json = json.dumps(mission)
        result = self._redis_cmd("HSET", key, "data", new_json)

        if result != "" and result != "(integer) 0":
            print(f"✅ Mission {mission_id} status updated in Redis")
            return True
        else:
            # Redis failed, fall back to local cache
            self._save_to_cache(key, mission)
            print(f"✅ Mission {mission_id} status updated in local cache")
            return False

    def save_orchestration_state(self, state_key: str, state_data: Dict[str, Any]) -> bool:
        """
        Save OpsCenter orchestration state to Redis or local cache.

        Returns:
        - True if saved to Redis
        - False if saved to local cache (Redis unavailable)
        """
        key = f"OPENCODE_STATE:{state_key}"

        state_json = json.dumps(state_data)
        result = self._redis_cmd("SET", key, state_json)

        if result != "" and "OK" in result:
            print(f"✅ Orchestration state {state_key} saved to Redis")
            return True
        else:
            # Redis failed, fall back to local cache
            self._save_to_cache(key, state_data)
            print(f"✅ Orchestration state {state_key} saved to local cache")
            return False

    def get_orchestration_state(self, state_key: str) -> Dict[str, Any]:
        """
        Retrieve orchestration state from Redis or local cache.

        Returns:
        - State dict if found
        - Empty dict if not found
        """
        key = f"OPENCODE_STATE:{state_key}"

        # Try Redis first
        data_json = self._redis_cmd("GET", key)

        if data_json:
            try:
                return json.loads(data_json)
            except:
                pass

        # Try local cache
        cached_data = self._read_from_cache(key)
        if cached_data:
            return cached_data

        return {}


# Test OpenCode connector (V2 with fallback)
if __name__ == "__main__":
    print("=== OPENCODE REDIS CONNECTOR V2 (with Error Recovery) TEST ===\n")

    conn = OpenCodeRedisConnectorCLIV2(host="127.0.0.1", port=6379)

    # Show Redis/cache status
    print(f"Redis available: {conn.redis_available}")
    print(f"Cache directory: {conn.cache_dir}\n")

    # Create a mission
    success = conn.create_mission(
        mission_id="MISSION-INTEL-SHIP-20260428",
        title="Ship Intelligence Sweep - All Lines",
        description="Scan Silversea, Regent, Viking, Oceania, Seabourn for new itineraries",
        priority="P1",
        assigned_to="Goose"
    )
    print(f"Mission created: {success}\n")

    # Get open missions
    missions = conn.get_open_missions(priority="P1")
    print(f"Open P1 missions ({len(missions)}):")
    for m in missions:
        print(f"  - {m['mission_id']}: {m['title']} → {m['assigned_to']}")

    # Update mission status
    success = conn.update_mission_status("MISSION-INTEL-SHIP-20260428", "in_progress")
    print(f"\nMission marked in_progress: {success}")

    # Save orchestration state
    orch_state = {
        "last_sync": datetime.utcnow().isoformat(),
        "active_agents": ["Goose", "OpenCode", "Claude Code"],
        "queue_depth": 3,
        "mode": "active"
    }
    conn.save_orchestration_state("SYSTEM_STATE", orch_state)
    print(f"Orchestration state saved")

    # Retrieve orchestration state
    state = conn.get_orchestration_state("SYSTEM_STATE")
    print(f"System mode: {state.get('mode')} | Active agents: {state.get('active_agents')}")

    # Health check
    print(f"\nPerforming health check...")
    conn.check_redis_health()
    print(f"Redis available after check: {conn.redis_available}")

    print("\n✅ OpenCode connector V2 test complete")
