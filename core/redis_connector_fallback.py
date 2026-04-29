#!/usr/bin/env python3
"""
Redis Connector with Local Cache Fallback
Provides transparent fallback to local JSON cache when Redis is unavailable.
Used by all 5 platform connectors (D2MC2, Dani, Goose, OpenCode, Claude).

Pattern: Try Redis → On failure, use local cache → Sync on reconnect
"""
import json
import os
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional


class RedisConnectorFallback:
    """
    Base class for Redis connectors with automatic local cache fallback.

    Behavior:
    - Primary: Redis via redis-cli subprocess
    - Fallback: Local JSON cache (~/.thunderbird_cache/{connector_name}/)
    - Sync: On reconnect, merge local cache back to Redis
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 6379,
        connector_name: str = "redis_connector",
        cache_dir: Optional[Path] = None
    ):
        self.host = host
        self.port = port
        self.connector_name = connector_name
        self.cli_cmd = ["redis-cli", "-h", host, "-p", str(port)]

        # Set up local cache directory
        if cache_dir is None:
            cache_dir = Path.home() / ".thunderbird_cache" / connector_name
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Track Redis health
        self.redis_available = False
        self._test_connection()

    def _test_connection(self) -> bool:
        """Test Redis connection. Sets self.redis_available."""
        try:
            result = subprocess.run(
                self.cli_cmd + ["PING"],
                capture_output=True,
                text=True,
                timeout=2
            )
            if "PONG" in result.stdout:
                self.redis_available = True
                print(f"✅ Redis connected ({self.connector_name})")
                return True
            else:
                self.redis_available = False
                print(f"⚠️  Redis PING failed, using local cache ({self.connector_name})")
                return False
        except Exception as e:
            self.redis_available = False
            print(f"⚠️  Redis unavailable, using local cache: {e}")
            return False

    def _redis_cmd(self, *args) -> str:
        """
        Execute redis-cli command with automatic fallback to local cache.

        Returns:
        - On success: Redis response (stdout)
        - On failure: Empty string (and state is stored in local cache)
        """
        if not self.redis_available:
            return ""  # Redis is known to be down, skip attempt

        try:
            result = subprocess.run(
                self.cli_cmd + list(args),
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                # Redis command failed, mark as unavailable
                self.redis_available = False
                print(f"⚠️  Redis command failed: {' '.join(args)}, switching to local cache")
                return ""
        except subprocess.TimeoutExpired:
            self.redis_available = False
            print(f"⚠️  Redis timeout on {' '.join(args)}, switching to local cache")
            return ""
        except Exception as e:
            self.redis_available = False
            print(f"⚠️  Redis error: {e}, switching to local cache")
            return ""

    def _save_to_cache(self, key: str, data: Dict[str, Any]) -> bool:
        """
        Save data to local cache file.

        Args:
            key: Cache key (e.g., "DANI_DRAFTS:draft123")
            data: Data dict to cache

        Returns:
            True if saved successfully
        """
        try:
            cache_file = self.cache_dir / f"{key}.json"
            cache_file.write_text(json.dumps({
                "key": key,
                "data": data,
                "cached_at": datetime.utcnow().isoformat(),
                "redis_available": self.redis_available
            }))
            return True
        except Exception as e:
            print(f"❌ Cache write failed for {key}: {e}")
            return False

    def _read_from_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Read data from local cache file.

        Returns:
            Data dict if cache exists, None otherwise
        """
        try:
            cache_file = self.cache_dir / f"{key}.json"
            if cache_file.exists():
                cache_data = json.loads(cache_file.read_text())
                return cache_data.get("data")
            return None
        except Exception as e:
            print(f"⚠️  Cache read failed for {key}: {e}")
            return None

    def _list_cached_keys(self, pattern: str = "*") -> list:
        """List all cached keys matching pattern."""
        try:
            files = list(self.cache_dir.glob("*.json"))
            keys = [f.stem for f in files]  # Remove .json extension

            # Simple pattern matching (Redis-style KEYS pattern)
            if pattern == "*":
                return keys
            else:
                # TODO: implement proper Redis KEYS pattern matching
                return keys
        except Exception as e:
            print(f"⚠️  Cache list failed: {e}")
            return []

    def _sync_cache_to_redis(self) -> int:
        """
        Sync local cache back to Redis when connection is restored.

        Returns:
            Number of items synced
        """
        if not self.redis_available:
            print("⚠️  Redis still unavailable, cannot sync cache")
            return 0

        synced = 0
        cached_keys = self._list_cached_keys()

        for key in cached_keys:
            try:
                cache_data = self._read_from_cache(key)
                if cache_data:
                    # Reconstruct the original Redis command
                    # This is simplified — actual sync depends on data structure
                    data_json = json.dumps(cache_data)
                    # Assuming hash-based storage (HSET key field value)
                    result = self._redis_cmd("HSET", key, "data", data_json)
                    if result:
                        synced += 1
                        print(f"✅ Synced {key} to Redis")
            except Exception as e:
                print(f"⚠️  Sync failed for {key}: {e}")

        print(f"✅ Cache sync complete: {synced} items restored to Redis")
        return synced

    def check_redis_health(self) -> bool:
        """
        Check if Redis is now available (periodic health check).
        Triggers sync if Redis has become available again.
        """
        was_available = self.redis_available
        self._test_connection()

        if not was_available and self.redis_available:
            print("✅ Redis is back online, syncing cache...")
            self._sync_cache_to_redis()

        return self.redis_available


# Example usage for subclasses
class DaniRedisConnectorWithFallback(RedisConnectorFallback):
    """Dani connector with automatic local cache fallback."""

    def __init__(self):
        super().__init__(connector_name="dani")

    def save_draft(self, draft_id: str, data: Dict[str, Any]) -> bool:
        """Save draft with fallback to local cache."""
        key = f"DANI_DRAFTS:{draft_id}"

        # Try Redis first
        draft_json = json.dumps(data)
        result = self._redis_cmd("HSET", key, "data", draft_json)

        if result:  # Redis succeeded
            return True
        else:  # Redis failed, use local cache
            self._save_to_cache(key, data)
            return False

    def get_draft(self, draft_id: str) -> Optional[Dict[str, Any]]:
        """Get draft from Redis or local cache."""
        key = f"DANI_DRAFTS:{draft_id}"

        # Try Redis first
        data_json = self._redis_cmd("HGET", key, "data")

        if data_json:
            try:
                return json.loads(data_json)
            except:
                pass

        # Fallback to local cache
        return self._read_from_cache(key)
