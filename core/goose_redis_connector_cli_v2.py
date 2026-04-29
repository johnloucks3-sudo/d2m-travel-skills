#!/usr/bin/env python3
"""
Goose Redis Connector (V2) - with Error Recovery Fallback
Tracks: task queue, research state, intel sweep status
For OpenCode/Goose research agent
NOTE: This is the refactored version using RedisConnectorFallback.
Inherits automatic local cache fallback when Redis is unavailable.
All public methods remain unchanged for backward compatibility.
"""
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
from core.redis_connector_fallback import RedisConnectorFallback


class GooseRedisConnectorCLIV2(RedisConnectorFallback):
    """
    Goose task and research state management via Redis with automatic local cache fallback.

    Public API (unchanged from V1):
    - queue_task(task_id, task_type, description, client_id, priority) -> bool
    - get_pending_tasks(task_type=None) -> List[Dict]
    - start_task(task_id) -> bool
    - complete_task(task_id, result_path) -> bool
    - save_sweep_status(sweep_id, sweep_type, sources, status) -> bool

    New capabilities (from fallback base class):
    - Automatic fallback to local cache when Redis is unavailable
    - Periodic health checks (check_redis_health)
    - Cache sync on reconnect (_sync_cache_to_redis)
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 6379):
        # Initialize base class with Goose-specific cache directory
        cache_dir = Path.home() / ".thunderbird_cache" / "goose"
        super().__init__(host=host, port=port, connector_name="goose", cache_dir=cache_dir)

    def queue_task(
        self,
        task_id: str,
        task_type: str,
        description: str,
        client_id: str,
        priority: str = "P2"
    ) -> bool:
        """
        Queue a task for Goose research with fallback to local cache.

        Returns:
        - True if saved to Redis
        - False if saved to local cache (Redis unavailable)
        """
        key = f"GOOSE_TASKS:{task_id}"

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
        result = self._redis_cmd("HSET", key, "data", task_json)

        if result != "" and result != "(integer) 0":
            print(f"✅ Task {task_id} queued to Redis")
            return True
        else:
            # Redis failed, fall back to local cache
            self._save_to_cache(key, task_dict)
            print(f"✅ Task {task_id} queued to local cache (Redis unavailable)")
            return False

    def get_pending_tasks(self, task_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all pending Goose tasks from Redis or local cache.

        Returns:
        - List of task dicts matching criteria
        - Combines results from both Redis and local cache
        """
        tasks = []

        # Try Redis first
        if self.redis_available:
            keys = self._redis_cmd("KEYS", "GOOSE_TASKS:*")

            if keys:
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

        # Also check local cache
        cached_keys = self._list_cached_keys("GOOSE_TASKS:*")
        for key in cached_keys:
            cached_data = self._read_from_cache(key)
            if cached_data and cached_data.get("status") == "queued":
                if task_type is None or cached_data.get("task_type") == task_type:
                    # Avoid duplicates
                    if not any(t["task_id"] == cached_data["task_id"] for t in tasks):
                        tasks.append(cached_data)

        return tasks

    def start_task(self, task_id: str) -> bool:
        """
        Mark task as in-progress in Redis or local cache.

        Returns:
        - True if updated in Redis
        - False if updated in local cache (Redis unavailable)
        """
        key = f"GOOSE_TASKS:{task_id}"

        # Try Redis first
        data_json = self._redis_cmd("HGET", key, "data")

        if not data_json:
            # Try local cache
            data = self._read_from_cache(key)
            if not data:
                return False
            task = data
        else:
            try:
                task = json.loads(data_json)
            except:
                return False

        # Update task status
        task["status"] = "in_progress"
        task["started_at"] = datetime.utcnow().isoformat()

        # Save back to Redis
        new_json = json.dumps(task)
        result = self._redis_cmd("HSET", key, "data", new_json)

        if result != "" and result != "(integer) 0":
            print(f"✅ Task {task_id} started in Redis")
            return True
        else:
            # Redis failed, fall back to local cache
            self._save_to_cache(key, task)
            print(f"✅ Task {task_id} started in local cache")
            return False

    def complete_task(self, task_id: str, result_path: str) -> bool:
        """
        Mark task as complete with output path in Redis or local cache.

        Returns:
        - True if updated in Redis
        - False if updated in local cache (Redis unavailable)
        """
        key = f"GOOSE_TASKS:{task_id}"

        # Try Redis first
        data_json = self._redis_cmd("HGET", key, "data")

        if not data_json:
            # Try local cache
            data = self._read_from_cache(key)
            if not data:
                return False
            task = data
        else:
            try:
                task = json.loads(data_json)
            except:
                return False

        # Update task status
        task["status"] = "completed"
        task["result_path"] = result_path
        task["completed_at"] = datetime.utcnow().isoformat()

        # Save back to Redis
        new_json = json.dumps(task)
        result = self._redis_cmd("HSET", key, "data", new_json)

        if result != "" and result != "(integer) 0":
            print(f"✅ Task {task_id} completed in Redis")
            return True
        else:
            # Redis failed, fall back to local cache
            self._save_to_cache(key, task)
            print(f"✅ Task {task_id} completed in local cache")
            return False

    def save_sweep_status(
        self,
        sweep_id: str,
        sweep_type: str,
        sources: List[str],
        status: str
    ) -> bool:
        """
        Save intel sweep status to Redis or local cache.

        Returns:
        - True if saved to Redis
        - False if saved to local cache (Redis unavailable)
        """
        key = f"GOOSE_SWEEPS:{sweep_id}"

        sweep_dict = {
            "sweep_id": sweep_id,
            "sweep_type": sweep_type,
            "sources": sources,
            "status": status,
            "updated": datetime.utcnow().isoformat()
        }

        sweep_json = json.dumps(sweep_dict)
        result = self._redis_cmd("HSET", key, "data", sweep_json)

        if result != "" and result != "(integer) 0":
            print(f"✅ Sweep {sweep_id} status saved to Redis")
            return True
        else:
            # Redis failed, fall back to local cache
            self._save_to_cache(key, sweep_dict)
            print(f"✅ Sweep {sweep_id} status saved to local cache")
            return False


# Test Goose connector (V2 with fallback)
if __name__ == "__main__":
    print("=== GOOSE REDIS CONNECTOR V2 (with Error Recovery) TEST ===\n")

    conn = GooseRedisConnectorCLIV2(host="127.0.0.1", port=6379)

    # Show Redis/cache status
    print(f"Redis available: {conn.redis_available}")
    print(f"Cache directory: {conn.cache_dir}\n")

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

    # Health check
    print(f"\nPerforming health check...")
    conn.check_redis_health()
    print(f"Redis available after check: {conn.redis_available}")

    print("\n✅ Goose connector V2 test complete")
