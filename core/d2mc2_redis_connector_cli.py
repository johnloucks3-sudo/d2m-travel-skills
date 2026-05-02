#!/usr/bin/env python3
"""
D2MC2 Redis Connector - redis-cli subprocess pattern
Avoids redis-py import issues; uses subprocess redis-cli calls
For COS operational state management across platforms
"""
import subprocess
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List


class D2MC2RedisConnectorCLI:
    """
    Redis connector using redis-cli subprocess pattern
    State types: CLIENT, DECISION, STAFF_LOAD, TELEGRAM_STATE
    """

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
                print(f"✅ Redis connected at {host}:{port}")
            else:
                raise Exception("Redis PING failed")
        except Exception as e:
            print(f"❌ Redis connection failed: {e}")
            raise

    def _redis_cmd(self, *args) -> str:
        """Execute redis-cli command, return stdout"""
        try:
            result = subprocess.run(
                self.cli_cmd + list(args),
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            print(f"⚠️  Redis command timeout: {' '.join(args)}")
            return ""
        except Exception as e:
            print(f"❌ Redis error: {e}")
            return ""

    def load_client_state(self, client_id: str) -> Dict[str, Any]:
        """Load full client state from Redis"""
        data_json = self._redis_cmd("HGET", f"ACTIVE_CLIENTS:{client_id}", "data")
        if data_json:
            try:
                return json.loads(data_json)
            except:
                pass

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
        """Record a new decision to Redis"""
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
        result = self._redis_cmd("HSET", f"OPEN_DECISIONS:{decision_id}", "data", decision_json)
        success = result != "" and result != "(integer) 0"
        if success:
            print(f"✅ Decision {decision_id} recorded")
        return success

    def get_open_decisions(self, decision_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all open decisions, optionally filtered by type"""
        keys = self._redis_cmd("KEYS", "OPEN_DECISIONS:*")
        decisions = []

        if not keys:
            return decisions

        for key in keys.split('\n'):
            if not key:
                continue
            decision_id = key.replace("OPEN_DECISIONS:", "")
            data_json = self._redis_cmd("HGET", key, "data")
            if data_json:
                try:
                    decision_data = json.loads(data_json)
                    if decision_data.get("status") == "open":
                        if decision_type is None or decision_data.get("type") == decision_type:
                            decisions.append(decision_data)
                except:
                    pass

        return decisions

    def approve_decision(self, decision_id: str, approved_by: str) -> bool:
        """Mark decision as approved"""
        data_json = self._redis_cmd("HGET", f"OPEN_DECISIONS:{decision_id}", "data")
        if not data_json:
            return False

        try:
            decision = json.loads(data_json)
            decision["status"] = "approved"
            decision["approved_by"] = approved_by
            decision["approved_at"] = datetime.utcnow().isoformat()

            new_json = json.dumps(decision)
            result = self._redis_cmd("HSET", f"OPEN_DECISIONS:{decision_id}", "data", new_json)
            return result != "" and result != "(integer) 0"
        except:
            return False

    def get_staff_load(self) -> Dict[str, Dict[str, Any]]:
        """Get current staff workload"""
        keys = self._redis_cmd("KEYS", "STAFF_LOAD:*")
        staff_data = {}

        if not keys:
            return staff_data

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

        return staff_data

    def set_staff_status(self, agent_id: str, active_tasks: int, status: str = "idle") -> bool:
        """Update staff member status"""
        try:
            self._redis_cmd("HSET", f"STAFF_LOAD:{agent_id}", "active_tasks", str(active_tasks))
            self._redis_cmd("HSET", f"STAFF_LOAD:{agent_id}", "status", status)
            self._redis_cmd("HSET", f"STAFF_LOAD:{agent_id}", "last_updated", datetime.utcnow().isoformat())
            return True
        except Exception as e:
            print(f"❌ Failed to set staff status: {e}")
            return False


# Test D2MC2 connector
if __name__ == "__main__":
    print("=== D2MC2 REDIS CONNECTOR (redis-cli subprocess) TEST ===\n")

    conn = D2MC2RedisConnectorCLI(host="127.0.0.1", port=6379)

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

    print("\n✅ D2MC2 connector test complete")
