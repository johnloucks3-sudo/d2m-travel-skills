#!/usr/bin/env python3
"""
OpenCode Redis Connector - redis-cli subprocess pattern
Tracks: mission board, task state, orchestration state
For OpsCenter/OpenCode task automation
"""
import subprocess
import json
from datetime import datetime
from typing import Dict, Any, Optional, List


class OpenCodeRedisConnectorCLI:
    """OpenCode mission board and task state via Redis using redis-cli subprocess"""

    def __init__(self, host: str = "127.0.0.1", port: int = 6379):
        self.host = host
        self.port = port
        self.cli_cmd = ["redis-cli", "-h", host, "-p", str(port)]
        # Test connection
        try:
            result = subprocess.run(
                self.cli_cmd + ["PING"],
                capture_output=True,
                text=True,
                timeout=2
            )
            if "PONG" in result.stdout:
                print(f"✅ Redis connected (OpenCode connector)")
            else:
                raise Exception("Redis PING failed")
        except Exception as e:
            print(f"❌ Redis connection failed: {e}")
            raise

    def _redis_cmd(self, *args) -> str:
        """Execute redis-cli command"""
        try:
            result = subprocess.run(
                self.cli_cmd + list(args),
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            print(f"⚠️  Redis timeout: {' '.join(args)}")
            return ""
        except Exception as e:
            print(f"❌ Redis error: {e}")
            return ""

    def create_mission(
        self,
        mission_id: str,
        title: str,
        description: str,
        priority: str,
        assigned_to: str
    ) -> bool:
        """Create a mission on the board"""
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
        result = self._redis_cmd("HSET", f"OPENCODE_MISSIONS:{mission_id}", "data", mission_json)
        if result != "" and result != "(integer) 0":
            print(f"✅ Mission {mission_id} created")
            return True
        return False

    def get_open_missions(self, priority: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all open missions, optionally filtered by priority"""
        keys = self._redis_cmd("KEYS", "OPENCODE_MISSIONS:*")
        missions = []

        if not keys:
            return missions

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

        return missions

    def update_mission_status(self, mission_id: str, new_status: str) -> bool:
        """Update mission status (open, in_progress, completed, blocked)"""
        data_json = self._redis_cmd("HGET", f"OPENCODE_MISSIONS:{mission_id}", "data")
        if not data_json:
            return False

        try:
            mission = json.loads(data_json)
            mission["status"] = new_status
            mission["updated"] = datetime.utcnow().isoformat()

            new_json = json.dumps(mission)
            result = self._redis_cmd("HSET", f"OPENCODE_MISSIONS:{mission_id}", "data", new_json)
            return result != "" and result != "(integer) 0"
        except:
            return False

    def save_orchestration_state(self, state_key: str, state_data: Dict[str, Any]) -> bool:
        """Save OpsCenter orchestration state"""
        state_json = json.dumps(state_data)
        result = self._redis_cmd("SET", f"OPENCODE_STATE:{state_key}", state_json)
        return result != "" and "OK" in result

    def get_orchestration_state(self, state_key: str) -> Dict[str, Any]:
        """Retrieve orchestration state"""
        data_json = self._redis_cmd("GET", f"OPENCODE_STATE:{state_key}")
        if data_json:
            try:
                return json.loads(data_json)
            except:
                pass

        return {}


# Test OpenCode connector
if __name__ == "__main__":
    print("=== OPENCODE REDIS CONNECTOR (redis-cli subprocess) TEST ===\n")

    conn = OpenCodeRedisConnectorCLI(host="127.0.0.1", port=6379)

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

    print("\n✅ OpenCode connector test complete")
