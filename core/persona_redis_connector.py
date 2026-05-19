#!/usr/bin/env python3
"""
Persona Redis Connector — OC-YOGA-BUILD-002
Single parameterized class replacing 10+ per-persona connector files.
CLI-compatible: same interface as *_cli.py files.
Inherits from RedisConnectorFallback (local JSON cache when Redis is down).

Replaces:
  claude_redis_subscriber.py / _v2.py
  d2mc2_redis_connector_cli.py / _v2.py / d2mc2_redis_connector.py
  dani_redis_connector_cli.py / _v2.py
  opencode_redis_connector_cli.py / _v2.py

Usage (CLI):
  python3 persona_redis_connector.py --persona d2mc2 get CLIENT_STATE user_123
  python3 persona_redis_connector.py --persona dani set DRAFT_STATE msg_456 '{"status":"pending"}'
  python3 persona_redis_connector.py --persona opencode publish TASK_EVENTS '{"task":"..."}'
  python3 persona_redis_connector.py --persona claude get HALE_STATE current

Usage (library):
  from core.persona_redis_connector import PersonaRedisConnector
  conn = PersonaRedisConnector("d2mc2")
  conn.set_state("CLIENT_STATE", "user_123", {"name": "Furlow"})
  data = conn.get_state("CLIENT_STATE", "user_123")
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Adjust import path for both direct execution and library import
try:
    from core.redis_connector_fallback import RedisConnectorFallback
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.redis_connector_fallback import RedisConnectorFallback


VALID_PERSONAS = {"d2mc2", "dani", "opencode", "claude", "hale", "a1", "a2", "a3", "a5", "a8", "a9"}

# Namespace prefixes per persona — matches existing Redis key conventions
PERSONA_NAMESPACES = {
    "d2mc2":   "D2MC2",
    "dani":    "DANI",
    "opencode": "OPENCODE",
    "claude":  "CLAUDE",
    "hale":    "HALE_STATE",
    "a1":      "A1_NAVARRO",
    "a2":      "A2_DEMBE",
    "a3":      "A3_MOREAU",
    "a5":      "A5_CASTILLO",
    "a8":      "A8_REYES",
    "a9":      "A9_HARLAN",
}


class PersonaRedisConnector(RedisConnectorFallback):
    """
    Parameterized Redis connector. One class for all personas.

    Args:
        persona_name: One of the VALID_PERSONAS strings (e.g. "d2mc2", "dani").
        host: Redis host (default 127.0.0.1)
        port: Redis port (default 6379)
    """

    def __init__(self, persona_name: str, host: str = "127.0.0.1", port: int = 6379):
        persona_name = persona_name.lower().strip()
        if persona_name not in VALID_PERSONAS:
            raise ValueError(f"Unknown persona '{persona_name}'. Valid: {sorted(VALID_PERSONAS)}")

        self.persona_name = persona_name
        self.namespace = PERSONA_NAMESPACES.get(persona_name, persona_name.upper())
        cache_dir = Path.home() / ".thunderbird_cache" / persona_name

        super().__init__(
            host=host,
            port=port,
            connector_name=persona_name,
            cache_dir=cache_dir,
        )

    def _key(self, category: str, identifier: str = "current") -> str:
        """Build namespaced Redis key: NAMESPACE:category:identifier"""
        return f"{self.namespace}:{category}:{identifier}"

    # ── Core CRUD ──────────────────────────────────────────────────────────

    def get_state(self, category: str, identifier: str = "current") -> Optional[Dict[str, Any]]:
        """Get JSON state blob. Returns dict or None."""
        key = self._key(category, identifier)
        raw = self._redis_cmd("GET", key)
        if raw:
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return {"raw": raw}
        # Fallback: check local cache file
        cache_file = self.cache_dir / f"{category}_{identifier}.json"
        if cache_file.exists():
            try:
                return json.loads(cache_file.read_text())
            except Exception:
                pass
        return None

    def set_state(self, category: str, identifier: str, data: Dict[str, Any], ttl_seconds: int = 0) -> bool:
        """Set JSON state blob. Returns True on success."""
        key = self._key(category, identifier)
        payload = json.dumps(data, default=str)

        if ttl_seconds > 0:
            ok = self._redis_cmd("SETEX", key, str(ttl_seconds), payload)
        else:
            ok = self._redis_cmd("SET", key, payload)

        # Always write to local cache
        cache_file = self.cache_dir / f"{category}_{identifier}.json"
        try:
            cache_file.write_text(payload)
        except Exception:
            pass

        return bool(ok)

    def delete_state(self, category: str, identifier: str = "current") -> bool:
        """Delete a state key."""
        key = self._key(category, identifier)
        result = self._redis_cmd("DEL", key)
        cache_file = self.cache_dir / f"{category}_{identifier}.json"
        if cache_file.exists():
            cache_file.unlink()
        return result == "1"

    # ── List / Queue Operations ─────────────────────────────────────────────

    def push(self, queue_name: str, item: Dict[str, Any]) -> int:
        """Push item to the right of a list queue. Returns queue length."""
        key = self._key("QUEUE", queue_name)
        payload = json.dumps({"ts": datetime.now().isoformat(), "data": item}, default=str)
        result = self._redis_cmd("RPUSH", key, payload)
        try:
            return int(result)
        except (ValueError, TypeError):
            return 0

    def pop(self, queue_name: str) -> Optional[Dict[str, Any]]:
        """Pop item from left of queue. Returns dict or None."""
        key = self._key("QUEUE", queue_name)
        raw = self._redis_cmd("LPOP", key)
        if raw:
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return {"raw": raw}
        return None

    def list_queue(self, queue_name: str, count: int = 20) -> List[Dict[str, Any]]:
        """List up to count items from queue without consuming."""
        key = self._key("QUEUE", queue_name)
        raw_list = self._redis_cmd("LRANGE", key, "0", str(count - 1))
        items = []
        if raw_list:
            for line in raw_list.strip().splitlines():
                line = line.strip()
                if line:
                    try:
                        items.append(json.loads(line))
                    except json.JSONDecodeError:
                        items.append({"raw": line})
        return items

    # ── Pub/Sub ────────────────────────────────────────────────────────────

    def publish(self, channel: str, message: Dict[str, Any]) -> int:
        """Publish message to channel. Returns subscriber count."""
        full_channel = f"{self.namespace}:{channel}"
        payload = json.dumps({"ts": datetime.now().isoformat(), "persona": self.persona_name, "data": message}, default=str)
        result = self._redis_cmd("PUBLISH", full_channel, payload)
        try:
            return int(result)
        except (ValueError, TypeError):
            return 0

    # ── Hash Operations ────────────────────────────────────────────────────

    def hset(self, hash_name: str, field: str, value: Any) -> bool:
        """Set a field in a hash."""
        key = self._key("HASH", hash_name)
        payload = json.dumps(value, default=str) if not isinstance(value, str) else value
        result = self._redis_cmd("HSET", key, field, payload)
        return result is not None

    def hget(self, hash_name: str, field: str) -> Optional[Any]:
        """Get a field from a hash."""
        key = self._key("HASH", hash_name)
        raw = self._redis_cmd("HGET", key, field)
        if raw:
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return raw
        return None

    def hgetall(self, hash_name: str) -> Dict[str, Any]:
        """Get all fields from a hash."""
        key = self._key("HASH", hash_name)
        raw = self._redis_cmd("HGETALL", key)
        result = {}
        if raw:
            lines = raw.strip().splitlines()
            for i in range(0, len(lines) - 1, 2):
                field = lines[i].strip()
                value = lines[i + 1].strip()
                try:
                    result[field] = json.loads(value)
                except json.JSONDecodeError:
                    result[field] = value
        return result

    # ── Health ─────────────────────────────────────────────────────────────

    def health(self) -> Dict[str, Any]:
        """Return connector health summary."""
        return {
            "persona": self.persona_name,
            "namespace": self.namespace,
            "redis_available": self.redis_available,
            "cache_dir": str(self.cache_dir),
            "ts": datetime.now().isoformat(),
        }


# ── CLI entrypoint ──────────────────────────────────────────────────────────

def _cli():
    parser = argparse.ArgumentParser(
        description="Persona Redis Connector CLI — replaces all per-persona connector files"
    )
    parser.add_argument("--persona", required=True, choices=sorted(VALID_PERSONAS),
                        help="Which persona namespace to use")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=6379)
    parser.add_argument("command", choices=["get", "set", "delete", "push", "pop", "list", "publish", "hget", "hset", "hgetall", "health"],
                        help="Redis operation")
    parser.add_argument("args", nargs="*", help="Operation arguments")

    args = parser.parse_args()
    conn = PersonaRedisConnector(args.persona, host=args.host, port=args.port)

    cmd = args.command
    op_args = args.args

    if cmd == "health":
        print(json.dumps(conn.health(), indent=2))

    elif cmd == "get":
        if len(op_args) < 1:
            print("Usage: get <category> [identifier]", file=sys.stderr); sys.exit(1)
        result = conn.get_state(op_args[0], op_args[1] if len(op_args) > 1 else "current")
        print(json.dumps(result, indent=2, default=str) if result is not None else "null")

    elif cmd == "set":
        if len(op_args) < 3:
            print("Usage: set <category> <identifier> <json_data>", file=sys.stderr); sys.exit(1)
        data = json.loads(op_args[2])
        ok = conn.set_state(op_args[0], op_args[1], data)
        print("OK" if ok else "FAILED")

    elif cmd == "delete":
        if len(op_args) < 1:
            print("Usage: delete <category> [identifier]", file=sys.stderr); sys.exit(1)
        ok = conn.delete_state(op_args[0], op_args[1] if len(op_args) > 1 else "current")
        print("DELETED" if ok else "NOT_FOUND")

    elif cmd == "push":
        if len(op_args) < 2:
            print("Usage: push <queue_name> <json_data>", file=sys.stderr); sys.exit(1)
        data = json.loads(op_args[1])
        length = conn.push(op_args[0], data)
        print(f"Queue length: {length}")

    elif cmd == "pop":
        if len(op_args) < 1:
            print("Usage: pop <queue_name>", file=sys.stderr); sys.exit(1)
        item = conn.pop(op_args[0])
        print(json.dumps(item, indent=2, default=str) if item else "null")

    elif cmd == "list":
        if len(op_args) < 1:
            print("Usage: list <queue_name> [count]", file=sys.stderr); sys.exit(1)
        count = int(op_args[1]) if len(op_args) > 1 else 20
        items = conn.list_queue(op_args[0], count)
        print(json.dumps(items, indent=2, default=str))

    elif cmd == "publish":
        if len(op_args) < 2:
            print("Usage: publish <channel> <json_data>", file=sys.stderr); sys.exit(1)
        data = json.loads(op_args[1])
        n = conn.publish(op_args[0], data)
        print(f"Delivered to {n} subscriber(s)")

    elif cmd == "hget":
        if len(op_args) < 2:
            print("Usage: hget <hash_name> <field>", file=sys.stderr); sys.exit(1)
        result = conn.hget(op_args[0], op_args[1])
        print(json.dumps(result, indent=2, default=str) if result is not None else "null")

    elif cmd == "hset":
        if len(op_args) < 3:
            print("Usage: hset <hash_name> <field> <value>", file=sys.stderr); sys.exit(1)
        ok = conn.hset(op_args[0], op_args[1], op_args[2])
        print("OK" if ok else "FAILED")

    elif cmd == "hgetall":
        if len(op_args) < 1:
            print("Usage: hgetall <hash_name>", file=sys.stderr); sys.exit(1)
        result = conn.hgetall(op_args[0])
        print(json.dumps(result, indent=2, default=str))

    else:
        print(f"Unknown command: {cmd}", file=sys.stderr); sys.exit(1)


if __name__ == "__main__":
    _cli()
