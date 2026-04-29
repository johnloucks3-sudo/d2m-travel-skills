#!/usr/bin/env python3
"""
Claude Code Redis Subscriber (V2) - with Error Recovery Fallback
Auto-notification on HALE_STATE changes across platforms
Allows headless Claude to be aware of state changes
NOTE: This is the refactored version using RedisConnectorFallback.
Inherits automatic local cache fallback when Redis is unavailable.
All public methods remain unchanged for backward compatibility.
"""
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
from core.redis_connector_fallback import RedisConnectorFallback


class ClaudeRedisSubscriberV2(RedisConnectorFallback):
    """
    Subscribe to HALE_STATE changes in Redis with automatic local cache fallback.
    Used by headless Claude to auto-sync Hale state across platforms.

    Public API (unchanged from V1):
    - get_hale_state() -> Dict
    - watch_hale_state(poll_interval) -> None
    - record_hale_state(state_data) -> bool
    - get_all_platform_state() -> Dict

    New capabilities (from fallback base class):
    - Automatic fallback to local cache when Redis is unavailable
    - Periodic health checks (check_redis_health)
    - Cache sync on reconnect (_sync_cache_to_redis)
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 6379):
        # Initialize base class with Claude-specific cache directory
        cache_dir = Path.home() / ".thunderbird_cache" / "claude"
        super().__init__(host=host, port=port, connector_name="claude", cache_dir=cache_dir)

    def get_hale_state(self) -> Dict[str, Any]:
        """
        Get current Hale operational state from Redis or local cache.

        Returns:
        - State dict if found
        - Default empty state if not found
        """
        key = "HALE_STATE:current"

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

        # Return default if not found
        return {
            "state": "unknown",
            "last_update": None,
            "active_agents": [],
            "open_decisions": 0
        }

    def watch_hale_state(self, poll_interval: int = 30) -> None:
        """
        Watch HALE_STATE for changes. Supports both Redis and local cache fallback.
        poll_interval: seconds between checks
        """
        print(f"🔍 Watching HALE_STATE (poll every {poll_interval}s)...")
        print("   Claude Code will auto-sync when state changes\n")

        last_state = None
        check_count = 0

        while True:
            time.sleep(poll_interval)
            check_count += 1

            current_state = self.get_hale_state()
            state_str = json.dumps(current_state)

            # Detect change
            if state_str != last_state:
                last_state = state_str
                self._notify_state_change(current_state, check_count)

    def _notify_state_change(self, new_state: Dict[str, Any], check_num: int) -> None:
        """Notify on state change"""
        timestamp = datetime.utcnow().isoformat()
        print(f"[{timestamp}] CHECK #{check_num}: HALE_STATE changed")
        print(f"  State: {new_state.get('state')}")
        print(f"  Active agents: {new_state.get('active_agents')}")
        print(f"  Open decisions: {new_state.get('open_decisions')}")
        print()

    def record_hale_state(self, state_data: Dict[str, Any]) -> bool:
        """
        Record Hale state change to Redis or local cache.

        Returns:
        - True if saved to Redis
        - False if saved to local cache (Redis unavailable)
        """
        key = "HALE_STATE:current"

        state_json = json.dumps(state_data)
        result = self._redis_cmd("SET", key, state_json)

        if "OK" in result:
            print(f"✅ Hale state recorded to Redis")
            return True
        else:
            # Redis failed, fall back to local cache
            self._save_to_cache(key, state_data)
            print(f"✅ Hale state recorded to local cache (Redis unavailable)")
            return False

    def get_all_platform_state(self) -> Dict[str, Any]:
        """
        Get unified state from all connected platforms.
        Retrieves from Redis first, falls back to cache for each platform.

        Returns:
        - Dict with timestamp and platform states
        """
        unified_state = {
            "timestamp": datetime.utcnow().isoformat(),
            "platforms": {}
        }

        # Aggregate state from each platform
        platforms = [
            ("D2MC2", "D2MC2_STATE:current"),
            ("Dani", "DANI_STATE:current"),
            ("Goose", "GOOSE_STATE:current"),
            ("OpenCode", "OPENCODE_STATE:current"),
            ("HaleCore", "HALE_STATE:current")
        ]

        for platform_name, state_key in platforms:
            # Try Redis first
            data_json = self._redis_cmd("GET", state_key)

            if data_json:
                try:
                    unified_state["platforms"][platform_name] = json.loads(data_json)
                except:
                    unified_state["platforms"][platform_name] = {"error": "parse_failed"}
            else:
                # Try local cache
                cached_data = self._read_from_cache(state_key)
                if cached_data:
                    unified_state["platforms"][platform_name] = cached_data
                else:
                    unified_state["platforms"][platform_name] = {"status": "not_initialized"}

        return unified_state


# Demo
if __name__ == "__main__":
    print("=== CLAUDE CODE REDIS SUBSCRIBER V2 (with Error Recovery) ===\n")

    subscriber = ClaudeRedisSubscriberV2(host="127.0.0.1", port=6379)

    # Show Redis/cache status
    print(f"Redis available: {subscriber.redis_available}")
    print(f"Cache directory: {subscriber.cache_dir}\n")

    # Record initial Hale state
    initial_state = {
        "state": "operational",
        "last_update": datetime.utcnow().isoformat(),
        "active_agents": ["D2MC2", "Dani", "Goose"],
        "open_decisions": 3,
        "mode": "active"
    }
    subscriber.record_hale_state(initial_state)
    print(f"✅ Initial Hale state recorded\n")

    # Get current state
    current = subscriber.get_hale_state()
    print(f"Current Hale state: {current.get('state')}")
    print(f"  Mode: {current.get('mode')}")
    print(f"  Active agents: {len(current.get('active_agents', []))} connected")
    print(f"  Open decisions: {current.get('open_decisions')}\n")

    # Get unified platform state
    unified = subscriber.get_all_platform_state()
    print(f"Unified platform state ({len(unified.get('platforms', {}))} platforms):")
    for platform, data in unified.get('platforms', {}).items():
        print(f"  - {platform}: {list(data.keys())}")

    # Health check
    print(f"\nPerforming health check...")
    subscriber.check_redis_health()
    print(f"Redis available after check: {subscriber.redis_available}")

    print("\n✅ Claude subscriber V2 test complete")
    print("   In production: subscriber.watch_hale_state() polls for changes")
    print("   Headless Claude wakes on state change → full context re-load")
