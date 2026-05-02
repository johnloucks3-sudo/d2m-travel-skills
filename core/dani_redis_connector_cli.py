#!/usr/bin/env python3
"""
Dani Redis Connector - redis-cli subprocess pattern
Tracks: draft emails, client interactions, conversation state
For D2M Luxury Travel Concierge bot
"""
import subprocess
import json
from datetime import datetime
from typing import Dict, Any, Optional, List


class DaniRedisConnectorCLI:
    """Dani state management via Redis using redis-cli subprocess"""

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
                print(f"✅ Redis connected (Dani connector)")
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

    def save_draft(
        self,
        draft_id: str,
        client_id: str,
        subject: str,
        body: str,
        recipient: str,
        draft_type: str
    ) -> bool:
        """Save draft email to Redis"""
        draft_dict = {
            "draft_id": draft_id,
            "client_id": client_id,
            "subject": subject,
            "body": body,
            "recipient": recipient,
            "draft_type": draft_type,  # validation, proposal, itinerary, etc
            "status": "draft",
            "created": datetime.utcnow().isoformat(),
            "last_updated": datetime.utcnow().isoformat()
        }
        draft_json = json.dumps(draft_dict)
        result = self._redis_cmd("HSET", f"DANI_DRAFTS:{draft_id}", "data", draft_json)
        if result != "" and result != "(integer) 0":
            print(f"✅ Draft {draft_id} saved")
            return True
        return False

    def get_pending_drafts(self, client_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all pending drafts, optionally filtered by client"""
        keys = self._redis_cmd("KEYS", "DANI_DRAFTS:*")
        drafts = []

        if not keys:
            return drafts

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

        return drafts

    def send_draft(self, draft_id: str, sent_to: str, message_id: str) -> bool:
        """Mark draft as sent"""
        data_json = self._redis_cmd("HGET", f"DANI_DRAFTS:{draft_id}", "data")
        if not data_json:
            return False

        try:
            draft = json.loads(data_json)
            draft["status"] = "sent"
            draft["sent_to"] = sent_to
            draft["message_id"] = message_id
            draft["sent_at"] = datetime.utcnow().isoformat()

            new_json = json.dumps(draft)
            result = self._redis_cmd("HSET", f"DANI_DRAFTS:{draft_id}", "data", new_json)
            return result != "" and result != "(integer) 0"
        except:
            return False

    def save_conversation(self, client_id: str, last_message: str, context: Dict[str, Any]) -> bool:
        """Save client conversation context"""
        conv_dict = {
            "client_id": client_id,
            "last_message": last_message,
            "context": context,
            "updated": datetime.utcnow().isoformat()
        }
        conv_json = json.dumps(conv_dict)
        result = self._redis_cmd("HSET", f"DANI_CONVERSATIONS:{client_id}", "data", conv_json)
        return result != "" and result != "(integer) 0"

    def get_conversation(self, client_id: str) -> Dict[str, Any]:
        """Retrieve client conversation history"""
        data_json = self._redis_cmd("HGET", f"DANI_CONVERSATIONS:{client_id}", "data")
        if data_json:
            try:
                return json.loads(data_json)
            except:
                pass

        return {
            "client_id": client_id,
            "last_message": None,
            "context": {},
            "updated": None
        }


# Test Dani connector
if __name__ == "__main__":
    print("=== DANI REDIS CONNECTOR (redis-cli subprocess) TEST ===\n")

    conn = DaniRedisConnectorCLI(host="127.0.0.1", port=6379)

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

    print("\n✅ Dani connector test complete")
