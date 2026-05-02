#!/usr/bin/env python3
"""
Claude Code Redis Subscriber - auto-notification on HALE_STATE changes
Allows headless Claude to be aware of state changes across platforms
Pattern: Watch HALE_STATE key, fire callback when state updates
"""
import subprocess
import json
import sys
from datetime import datetime
from typing import Dict, Any, Callable, Optional


class ClaudeRedisSubscriber:
    """
    Subscribe to HALE_STATE changes in Redis
    Used by headless Claude to auto-sync Hale state across platforms
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
                print(f"✅ Redis connected (Claude subscriber)")
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
        except Exception as e:
            print(f"⚠️  Redis error: {e}")
            return ""

    def get_hale_state(self) -> Dict[str, Any]:
        """Get current Hale operational state"""
        data_json = self._redis_cmd("GET", "HALE_STATE:current")
        if data_json:
            try:
                return json.loads(data_json)
            except:
                pass

        return {
            "state": "unknown",
            "last_update": None,
            "active_agents": [],
            "open_decisions": 0
        }

    def watch_hale_state(self, poll_interval: int = 30) -> None:
        """
        Watch HALE_STATE for changes
        poll_interval: seconds between checks
        """
        print(f"🔍 Watching HALE_STATE (poll every {poll_interval}s)...")
        print("   Claude Code will auto-sync when state changes\n")

        last_state = None
        check_count = 0

        while True:
            import time
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
        """Record Hale state change"""
        state_json = json.dumps(state_data)
        result = self._redis_cmd("SET", "HALE_STATE:current", state_json)
        return "OK" in result

    def get_all_platform_state(self) -> Dict[str, Any]:
        """Get unified state from all connected platforms"""
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
            data_json = self._redis_cmd("GET", state_key)
            if data_json:
                try:
                    unified_state["platforms"][platform_name] = json.loads(data_json)
                except:
                    unified_state["platforms"][platform_name] = {"error": "parse_failed"}
            else:
                unified_state["platforms"][platform_name] = {"status": "not_initialized"}

        return unified_state


# Demo
if __name__ == "__main__":
    print("=== CLAUDE CODE REDIS SUBSCRIBER ===\n")

    subscriber = ClaudeRedisSubscriber(host="127.0.0.1", port=6379)

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

    print("\n✅ Claude subscriber test complete")
    print("   In production: subscriber.watch_hale_state() polls for changes")
    print("   Headless Claude wakes on state change → full context re-load")
