#!/usr/bin/env python3
"""
Dani Redis Connector (V2) - with Error Recovery Fallback
Tracks: draft emails, client interactions, conversation state
For D2M Luxury Travel Concierge bot

NOTE: This is the refactored version using RedisConnectorFallback.
Inherits automatic local cache fallback when Redis is unavailable.
All public methods remain unchanged for backward compatibility.
"""
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
from core.redis_connector_fallback import RedisConnectorFallback


class DaniRedisConnectorCLI(RedisConnectorFallback):
    """
    Dani state management via Redis with automatic local cache fallback.

    Public API (unchanged from V1):
    - save_draft(draft_id, client_id, subject, body, recipient, draft_type) -> bool
    - get_pending_drafts(client_id=None) -> List[Dict]
    - send_draft(draft_id, sent_to, message_id) -> bool
    - save_conversation(client_id, last_message, context) -> bool
    - get_conversation(client_id) -> Dict

    New capabilities (from fallback base class):
    - Automatic fallback to local cache when Redis is unavailable
    - Periodic health checks (check_redis_health)
    - Cache sync on reconnect (_sync_cache_to_redis)
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 6379):
        # Initialize base class with Dani-specific cache directory
        cache_dir = Path.home() / ".thunderbird_cache" / "dani"
        super().__init__(host=host, port=port, connector_name="dani", cache_dir=cache_dir)

    def save_draft(
        self,
        draft_id: str,
        client_id: str,
        subject: str,
        body: str,
        recipient: str,
        draft_type: str
    ) -> bool:
        """
        Save draft email to Redis with fallback to local cache.

        Returns:
        - True if saved to Redis
        - False if saved to local cache (Redis unavailable)
        """
        key = f"DANI_DRAFTS:{draft_id}"

        draft_dict = {
            "draft_id": draft_id,
            "client_id": client_id,
            "subject": subject,
            "body": body,
            "recipient": recipient,
            "draft_type": draft_type,
            "status": "draft",
            "created": datetime.utcnow().isoformat(),
            "last_updated": datetime.utcnow().isoformat()
        }

        draft_json = json.dumps(draft_dict)
        result = self._redis_cmd("HSET", key, "data", draft_json)

        if result != "" and result != "(integer) 0":
            print(f"✅ Draft {draft_id} saved to Redis")
            return True
        else:
            # Redis failed, fall back to local cache
            self._save_to_cache(key, draft_dict)
            print(f"✅ Draft {draft_id} saved to local cache (Redis unavailable)")
            return False

    def get_pending_drafts(self, client_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all pending drafts from Redis or local cache.

        Returns:
        - List of draft dicts matching criteria
        - Combines results from both Redis and local cache
        """
        drafts = []

        # Try Redis first
        if self.redis_available:
            keys = self._redis_cmd("KEYS", "DANI_DRAFTS:*")

            if keys:
                for key in keys.split('\n'):
                    if not key:
                        continue
                    data_json = self._redis_cmd("HGET", key, "data")
                    if data_json:
                        try:
                            draft_data = json.loads(data_json)
                            if draft_data.get("status") == "draft":
                                if client_id is None or draft_data.get("client_id") == client_id:
                                    drafts.append(draft_data)
                        except:
                            pass

        # Also check local cache (may have entries from when Redis was down)
        cached_keys = self._list_cached_keys("DANI_DRAFTS:*")
        for key in cached_keys:
            cached_data = self._read_from_cache(key)
            if cached_data and cached_data.get("status") == "draft":
                if client_id is None or cached_data.get("client_id") == client_id:
                    # Avoid duplicates
                    if not any(d["draft_id"] == cached_data["draft_id"] for d in drafts):
                        drafts.append(cached_data)

        return drafts

    def send_draft(self, draft_id: str, sent_to: str, message_id: str) -> bool:
        """
        Mark draft as sent in Redis or local cache.

        Returns:
        - True if updated in Redis
        - False if updated in local cache (Redis unavailable)
        """
        key = f"DANI_DRAFTS:{draft_id}"

        # Try Redis first
        data_json = self._redis_cmd("HGET", key, "data")

        if not data_json:
            # Try local cache
            data = self._read_from_cache(key)
            if not data:
                return False
            draft = data
        else:
            try:
                draft = json.loads(data_json)
            except:
                return False

        # Update draft status
        draft["status"] = "sent"
        draft["sent_to"] = sent_to
        draft["message_id"] = message_id
        draft["sent_at"] = datetime.utcnow().isoformat()

        # Save back to Redis
        new_json = json.dumps(draft)
        result = self._redis_cmd("HSET", key, "data", new_json)

        if result != "" and result != "(integer) 0":
            print(f"✅ Draft {draft_id} marked sent in Redis")
            return True
        else:
            # Redis failed, fall back to local cache
            self._save_to_cache(key, draft)
            print(f"✅ Draft {draft_id} marked sent in local cache")
            return False

    def save_conversation(self, client_id: str, last_message: str, context: Dict[str, Any]) -> bool:
        """
        Save client conversation context to Redis with fallback.

        Returns:
        - True if saved to Redis
        - False if saved to local cache
        """
        key = f"DANI_CONVERSATIONS:{client_id}"

        conv_dict = {
            "client_id": client_id,
            "last_message": last_message,
            "context": context,
            "updated": datetime.utcnow().isoformat()
        }

        conv_json = json.dumps(conv_dict)
        result = self._redis_cmd("HSET", key, "data", conv_json)

        if result != "" and result != "(integer) 0":
            return True
        else:
            self._save_to_cache(key, conv_dict)
            return False

    def get_conversation(self, client_id: str) -> Dict[str, Any]:
        """
        Retrieve client conversation history from Redis or local cache.

        Returns:
        - Conversation dict if found
        - Empty conversation dict if not found
        """
        key = f"DANI_CONVERSATIONS:{client_id}"

        # Try Redis first
        data_json = self._redis_cmd("HGET", key, "data")

        if data_json:
            try:
                return json.loads(data_json)
            except:
                pass

        # Try local cache
        cached_data = self._read_from_cache(key)
        if cached_data:
            return cached_data

        # Default empty conversation
        return {
            "client_id": client_id,
            "last_message": None,
            "context": {},
            "updated": None
        }


# Test Dani connector (V2 with fallback)
if __name__ == "__main__":
    print("=== DANI REDIS CONNECTOR V2 (with Error Recovery) TEST ===\n")

    conn = DaniRedisConnectorCLI(host="127.0.0.1", port=6379)

    # Show Redis/cache status
    print(f"Redis available: {conn.redis_available}")
    print(f"Cache directory: {conn.cache_dir}\n")

    # Save a validation email draft
    success = conn.save_draft(
        draft_id="DANI-VALID-MCLEOD-001",
        client_id="mcleod",
        subject="Your Silver Muse Itinerary - Welcome Aboard!",
        body="Erik, welcome to Silver Muse! Your itinerary is ready. [...]",
        recipient="erik@example.com",
        draft_type="validation"
    )
    print(f"Validation draft saved: {success}\n")

    # Get pending drafts
    pending = conn.get_pending_drafts()
    print(f"Pending drafts ({len(pending)}):")
    for d in pending:
        print(f"  - {d['draft_id']} for {d['client_id']}: {d['draft_type']}")

    # Save conversation context
    conn.save_conversation(
        client_id="mcleod",
        last_message="When does the ship depart from Barcelona?",
        context={"phase": "pre-departure", "days_until_departure": 56}
    )
    print(f"\nConversation saved for mcleod")

    # Retrieve conversation
    conv = conn.get_conversation("mcleod")
    print(f"Conversation for {conv['client_id']}: {conv['last_message']}")

    # Health check
    print(f"\nPerforming health check...")
    conn.check_redis_health()
    print(f"Redis available after check: {conn.redis_available}")

    print("\n✅ Dani connector V2 test complete")
