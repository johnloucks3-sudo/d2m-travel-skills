#!/usr/bin/env python3
"""
Goose Redis Connector - redis-cli subprocess pattern
Tracks: task queue, research state, intel sweep status
For OpenCode/Goose research agent
"""
import subprocess
import json
from datetime import datetime
from typing import Dict, Any, Optional, List


class GooseRedisConnectorCLI:
    """Goose task and research state management via Redis using redis-cli subprocess"""

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
                print(f"✅ Redis connected (Goose connector)")
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

    def queue_task(
        self,
        task_id: str,
        task_type: str,
        description: str,
        client_id: str,
        priority: str = "P2"
    ) -> bool:
        """Queue a task for Goose research"""
        task_dict = {
            "task_id": task_id,
            "task_type": task_type,  # research, intel, analysis, scan
            "description": description,
            "client_id": client_id,
            "priority": priority,
            "status": "queued",
            "created": datetime.utcnow().isoformat()
        }
        task_json = json.dumps(task_dict)
        result = self._redis_cmd("HSET", f"GOOSE_TASKS:{task_id}", "data", task_json)
        if result != "" and result != "(integer) 0":
            print(f"✅ Task {task_id} queued")
            return True
        return False

    def get_pending_tasks(self, task_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all pending Goose tasks"""
        keys = self._redis_cmd("KEYS", "GOOSE_TASKS:*")
        tasks = []

        if not keys:
            return tasks

        for key in keys.split('\n'):
            if not key:
                continue
            data_json = self._redis_cmd("HGET", key, "data")
            if data_json:
                try:
                    task_data = json.loads(data_json)
                    if task_data.get("status") == "queued":
                        if task_type is None or task_data.get("task_type") == task_type:
                            tasks.append(task_data)
                except:
                    pass

        return tasks

    def start_task(self, task_id: str) -> bool:
        """Mark task as in-progress"""
        data_json = self._redis_cmd("HGET", f"GOOSE_TASKS:{task_id}", "data")
        if not data_json:
            return False

        try:
            task = json.loads(data_json)
            task["status"] = "in_progress"
            task["started_at"] = datetime.utcnow().isoformat()

            new_json = json.dumps(task)
            result = self._redis_cmd("HSET", f"GOOSE_TASKS:{task_id}", "data", new_json)
            return result != "" and result != "(integer) 0"
        except:
            return False

    def complete_task(self, task_id: str, result_path: str) -> bool:
        """Mark task as complete with output path"""
        data_json = self._redis_cmd("HGET", f"GOOSE_TASKS:{task_id}", "data")
        if not data_json:
            return False

        try:
            task = json.loads(data_json)
            task["status"] = "completed"
            task["result_path"] = result_path
            task["completed_at"] = datetime.utcnow().isoformat()

            new_json = json.dumps(task)
            result = self._redis_cmd("HSET", f"GOOSE_TASKS:{task_id}", "data", new_json)
            return result != "" and result != "(integer) 0"
        except:
            return False

    def save_sweep_status(
        self,
        sweep_id: str,
        sweep_type: str,
        sources: List[str],
        status: str
    ) -> bool:
        """Save intel sweep status"""
        sweep_dict = {
            "sweep_id": sweep_id,
            "sweep_type": sweep_type,
            "sources": sources,
            "status": status,
            "updated": datetime.utcnow().isoformat()
        }
        sweep_json = json.dumps(sweep_dict)
        result = self._redis_cmd("HSET", f"GOOSE_SWEEPS:{sweep_id}", "data", sweep_json)
        return result != "" and result != "(integer) 0"


# Test Goose connector
if __name__ == "__main__":
    print("=== GOOSE REDIS CONNECTOR (redis-cli subprocess) TEST ===\n")

    conn = GooseRedisConnectorCLI(host="127.0.0.1", port=6379)

    # Queue a research task
    success = conn.queue_task(
        task_id="GOOSE-RESEARCH-KUKLINSKI-001",
        task_type="research",
        description="Analyze Panama Canal route options and alternatives",
        client_id="kuklinski",
        priority="P1"
    )
    print(f"Task queued: {success}\n")

    # Get pending tasks
    pending = conn.get_pending_tasks()
    print(f"Pending tasks ({len(pending)}):")
    for t in pending:
        print(f"  - {t['task_id']} ({t['priority']}): {t['description']}")

    # Mark task in progress
    success = conn.start_task("GOOSE-RESEARCH-KUKLINSKI-001")
    print(f"\nTask started: {success}")

    # Save sweep status
    conn.save_sweep_status(
        sweep_id="SWEEP-SHIP-20260428",
        sweep_type="ship_intelligence",
        sources=["iCruise", "cruise_reviews", "crew_center"],
        status="in_progress"
    )
    print(f"Sweep status saved")

    print("\n✅ Goose connector test complete")
