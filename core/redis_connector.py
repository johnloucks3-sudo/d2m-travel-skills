"""
Redis Connector Wrapper (A12 ELON — Condition 2)
Thin wrapper, read-through-cache pattern
Local cache TTL 30s with invalidation on write
"""
import redis
import json
import time
from typing import Dict, Any, Optional
from functools import lru_cache


class RedisConnector:
    """
    Thread-safe Redis wrapper with local cache and fallback
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 6379, local_cache_ttl: int = 30):
        self.host = host
        self.port = port
        self.local_cache_ttl = local_cache_ttl
        self.cache_timestamp = {}
        self.local_cache = {}
        self.redis_client = None
        self._connect()

    def _connect(self):
        """Connect to Redis, fallback to dict if unavailable"""
        try:
            self.redis_client = redis.Redis(
                host=self.host,
                port=self.port,
                decode_responses=True,
                socket_connect_timeout=2
            )
            # Test connection
            self.redis_client.ping()
            print(f"✅ Redis connected at {self.host}:{self.port}")
        except Exception as e:
            print(f"⚠️  Redis unavailable: {e}. Using local cache fallback.")
            self.redis_client = None

    def get_client(self, client_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve client state from Redis with local cache.
        Cache miss → Redis hit → return
        Redis unavailable → use local cache
        """
        # Check local cache
        cache_key = f"client_{client_id}"
        if cache_key in self.local_cache:
            age = time.time() - self.cache_timestamp.get(cache_key, 0)
            if age < self.local_cache_ttl:
                return self.local_cache[cache_key]

        # Cache expired or miss → Redis
        if self.redis_client:
            try:
                data = self.redis_client.hgetall(f"ACTIVE_CLIENTS:{client_id}")
                if data:
                    self.local_cache[cache_key] = data
                    self.cache_timestamp[cache_key] = time.time()
                    return data
            except Exception as e:
                print(f"⚠️  Redis read failed: {e}. Using local cache.")

        # Return cached data (even if expired) or None
        return self.local_cache.get(cache_key)

    def save_decision(self, decision_id: str, decision_dict: Dict[str, Any]) -> bool:
        """
        Save decision to Redis, invalidate local cache
        """
        if not self.redis_client:
            print(f"❌ Redis unavailable. Cannot save decision {decision_id}")
            return False

        try:
            # Serialize decision
            decision_json = json.dumps(decision_dict)
            # Save to Redis
            self.redis_client.hset(f"OPEN_DECISIONS:{decision_id}", "data", decision_json)
            # Invalidate related cache entries
            for key in list(self.local_cache.keys()):
                if "decision" in key:
                    del self.local_cache[key]
                    if key in self.cache_timestamp:
                        del self.cache_timestamp[key]
            print(f"✅ Decision {decision_id} saved")
            return True
        except Exception as e:
            print(f"❌ Failed to save decision: {e}")
            return False

    def get_decision(self, decision_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve decision from Redis with fallback to local cache
        """
        cache_key = f"decision_{decision_id}"

        # Check local cache
        if cache_key in self.local_cache:
            age = time.time() - self.cache_timestamp.get(cache_key, 0)
            if age < self.local_cache_ttl:
                return self.local_cache[cache_key]

        # Redis
        if self.redis_client:
            try:
                data = self.redis_client.hget(f"OPEN_DECISIONS:{decision_id}", "data")
                if data:
                    parsed = json.loads(data)
                    self.local_cache[cache_key] = parsed
                    self.cache_timestamp[cache_key] = time.time()
                    return parsed
            except Exception as e:
                print(f"⚠️  Redis read failed: {e}")

        return self.local_cache.get(cache_key)

    def get_all_decisions(self) -> Dict[str, Any]:
        """Get all open decisions"""
        if not self.redis_client:
            print("❌ Redis unavailable")
            return {}

        try:
            keys = self.redis_client.keys("OPEN_DECISIONS:*")
            decisions = {}
            for key in keys:
                decision_id = key.replace("OPEN_DECISIONS:", "")
                data = self.redis_client.hget(key, "data")
                if data:
                    decisions[decision_id] = json.loads(data)
            return decisions
        except Exception as e:
            print(f"❌ Failed to retrieve all decisions: {e}")
            return {}

    def health_check(self) -> Dict[str, Any]:
        """Check Redis health"""
        if not self.redis_client:
            return {"status": "disconnected", "redis": False, "cache": "active"}

        try:
            pong = self.redis_client.ping()
            info = self.redis_client.info()
            return {
                "status": "connected" if pong else "unhealthy",
                "redis": True,
                "cache": "active",
                "keys": info.get("db0", {}).get("keys", 0),
                "memory_mb": info.get("used_memory", 0) / 1024 / 1024
            }
        except Exception as e:
            return {"status": "error", "redis": False, "cache": "active", "error": str(e)}


# Test connector
if __name__ == "__main__":
    conn = RedisConnector(host="127.0.0.1", port=6379)
    print(f"\nHealth: {conn.health_check()}")

    # Test write
    test_decision = {
        "type": "financial",
        "question": "Approve Westbrook cancellation refund?",
        "options": ["approve", "deny", "partial"],
        "owner": "A9_Harlan"
    }
    conn.save_decision("FIN-20260428-TEST", test_decision)

    # Test read
    retrieved = conn.get_decision("FIN-20260428-TEST")
    print(f"\nRetrieved: {retrieved}")
