"""RabbitMQ client for Thunderbird inter-persona messaging.

Handles:
- Message publishing to persona queues
- Consuming messages from personal inbox
- Acknowledgment/confirmation flow for critical messages
- Audit trail integration with State Bridge
"""

import json
import logging
import uuid
from typing import List, Optional, Callable
from dataclasses import asdict
from datetime import datetime
import pika
from .schemas import PersonaMessage
from .production_config import MessagingConfig

log = logging.getLogger("messaging")

class PersonaMessaging:
    """RabbitMQ-backed messaging for persona dialogue."""

    def __init__(self, use_production=True, host: str = None, port: int = None, username: str = None, password: str = None):
        """Initialize messaging client.

        Args:
            use_production: If True, use production config (yoga). If False, use localhost for testing.
            host: Optional override for RabbitMQ host
            port: Optional override for RabbitMQ port
            username: Optional override for RabbitMQ user
            password: Optional override for RabbitMQ password
        """
        if use_production:
            config = MessagingConfig.get_connection_params(use_fallback=False)
        else:
            config = MessagingConfig.get_connection_params(use_fallback=True)

        self.host = host or config['host']
        self.port = port or config['port']
        self.username = username or config['username']
        self.password = password or config['password']
        self.connection = None
        self.channel = None
        self.message_log = []  # Track all messages published for audit trail
        self._ensure_infrastructure()

    def _ensure_infrastructure(self):
        """Connect to RabbitMQ and verify topology."""
        try:
            credentials = pika.PlainCredentials(self.username, self.password)
            self.connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=self.host,
                    port=self.port,
                    credentials=credentials,
                    connection_attempts=3,
                    retry_delay=2
                )
            )
            self.channel = self.connection.channel()

            # Idempotent: declare but don't fail if exists
            for exchange in ['persona.dissent', 'persona.observations', 'persona.alternatives']:
                self.channel.exchange_declare(
                    exchange=exchange,
                    exchange_type='topic',
                    durable=True,
                    passive=False
                )

            for persona in ['sterling', 'dembe', 'reyes', 'dani', 'harlan', 'washington']:
                queue_name = f"{persona}.inbox"
                self.channel.queue_declare(
                    queue=queue_name,
                    durable=True,
                    arguments={'x-message-ttl': 604800000},  # 7-day TTL
                    passive=False
                )

            # Audit trail queue — durable record of every acknowledgement/vote.
            # MUST exist before acknowledge() publishes to it: acknowledge() routes
            # via the default exchange to routing_key 'audit.trail', so a queue of
            # that exact name must be declared or votes are silently discarded.
            # 30-day TTL (votes outlive the 7-day inbox TTL for decision auditing).
            self.channel.queue_declare(
                queue='audit.trail',
                durable=True,
                arguments={'x-message-ttl': 2592000000},  # 30-day TTL
                passive=False
            )

            log.info(f"✅ RabbitMQ connected: {self.host}:{self.port}")
        except Exception as e:
            log.error(f"❌ RabbitMQ connection failed: {e}")
            raise

    def publish(self, msg: PersonaMessage) -> str:
        """Publish a message to target personas.

        Args:
            msg: PersonaMessage to publish

        Returns:
            message_id (UUID)
        """
        try:
            # Assign unique ID if not present
            if not msg.message_id:
                msg.message_id = str(uuid.uuid4())

            # Route to exchange based on message type (pluralize: observation→observations)
            exchange_map = {
                'dissent': 'persona.dissent',
                'observation': 'persona.observations',
                'alternative': 'persona.alternatives',
                'confirmation': 'persona.dissent'  # confirmations route to dissent for now
            }
            exchange = exchange_map.get(msg.msg_type, f"persona.{msg.msg_type}s")

            # Broadcast routing: send to each target persona separately
            for target in msg.to_personas:
                self.channel.basic_publish(
                    exchange=exchange,
                    routing_key=target,
                    body=json.dumps(asdict(msg)),
                    properties=pika.BasicProperties(
                        delivery_mode=2,  # Persistent
                        content_type='application/json'
                    )
                )

            # Log for audit trail
            self.message_log.append({
                'message_id': msg.message_id,
                'from_persona': msg.from_persona,
                'to_personas': msg.to_personas,
                'msg_type': msg.msg_type,
                'timestamp': datetime.utcnow().isoformat(),
                'requires_ack': msg.requires_ack
            })

            log.info(f"✅ Published {msg.msg_type} #{msg.message_id} from {msg.from_persona} to {msg.to_personas}")
            return msg.message_id
        except Exception as e:
            log.error(f"❌ Publish failed: {e}")
            raise

    def consume(self, persona_name: str, callback: Callable = None, auto_ack: bool = False) -> List[PersonaMessage]:
        """Consume messages from persona's inbox.

        Args:
            persona_name: Name of persona (e.g., 'sterling')
            callback: Optional callback to invoke on each message
            auto_ack: If False, messages require manual acknowledge

        Returns:
            List of messages in inbox
        """
        try:
            queue_name = f"{persona_name}.inbox"
            messages = []

            # Get all messages from queue without consuming them
            method, properties, body = self.channel.basic_get(queue=queue_name, auto_ack=auto_ack)

            while method:
                msg_dict = json.loads(body)
                msg = PersonaMessage(**msg_dict)
                messages.append(msg)

                if callback:
                    callback(msg)

                # Get next message
                method, properties, body = self.channel.basic_get(queue=queue_name, auto_ack=auto_ack)

            log.info(f"✅ Consumed {len(messages)} messages for {persona_name}")
            return messages
        except Exception as e:
            log.error(f"❌ Consume failed for {persona_name}: {e}")
            return []

    def acknowledge(self, message_id: str, persona_name: str, vote: bool = True) -> bool:
        """Acknowledge a critical message.

        Args:
            message_id: Message ID to acknowledge
            persona_name: Persona acknowledging
            vote: True=approved, False=rejected

        Returns:
            Success
        """
        try:
            # Publish confirmation message to system audit queue
            confirmation_msg = PersonaMessage.confirmation(
                from_persona=persona_name,
                decision_id=message_id,
                vote=vote
            )

            # Route to audit trail
            self.channel.basic_publish(
                exchange='',
                routing_key='audit.trail',
                body=json.dumps(asdict(confirmation_msg)),
                properties=pika.BasicProperties(delivery_mode=2)
            )

            log.info(f"✅ {persona_name} acknowledged {message_id}: {'approved' if vote else 'rejected'}")
            return True
        except Exception as e:
            log.error(f"❌ Acknowledge failed: {e}")
            return False

    def get_dissent_chain(self, decision_id: str) -> List[PersonaMessage]:
        """Get the acknowledgement/vote tally for a decision.

        Reads the persisted `audit.trail` queue (NOT an in-memory log) so the
        tally survives across client instances — this is the Gate-4 capability:
        "who acknowledged decision X, and how did they vote." acknowledge()
        publishes a confirmation per vote with context={decision_id, vote};
        this returns every such record matching decision_id.

        The read is non-destructive: messages are fetched unacked and then
        requeued, leaving the audit trail intact for repeat queries.

        Args:
            decision_id: The dissent's message_id being voted on.

        Returns:
            List of confirmation PersonaMessages (one per vote).
        """
        results: List[PersonaMessage] = []
        pending_tags = []
        valid_fields = set(PersonaMessage.__dataclass_fields__)
        try:
            while True:
                method, _props, body = self.channel.basic_get(
                    queue='audit.trail', auto_ack=False
                )
                if method is None:
                    break  # queue drained of ready messages
                pending_tags.append(method.delivery_tag)
                try:
                    data = json.loads(body)
                except (ValueError, TypeError):
                    continue
                if data.get('context', {}).get('decision_id') == decision_id:
                    results.append(PersonaMessage(
                        **{k: v for k, v in data.items() if k in valid_fields}
                    ))
            log.info(f"✅ Retrieved {len(results)} vote(s) for decision {decision_id}")
            return results
        except Exception as e:
            log.error(f"❌ Get dissent chain failed: {e}")
            return results
        finally:
            # Requeue everything read so the audit trail is non-destructive.
            for tag in pending_tags:
                try:
                    self.channel.basic_nack(delivery_tag=tag, requeue=True)
                except Exception:
                    pass

    def audit_trail(self, session_id: str = None) -> dict:
        """Get merged audit trail (State Bridge + RabbitMQ message log).

        Args:
            session_id: Optional session ID filter

        Returns:
            {"events": [...], "messages": [...], "timeline": [...], "summary": {...}}
        """
        try:
            # State Bridge events (from State Bridge SQLite session continuity daemon)
            state_bridge_events = self._load_state_bridge_events(session_id)

            # Merge: interleave events and messages by timestamp
            all_items = []
            all_items.extend([{'type': 'event', 'data': e} for e in state_bridge_events])
            all_items.extend([{'type': 'message', 'data': m} for m in self.message_log])

            # Sort by timestamp
            timeline = sorted(all_items, key=lambda x: x.get('data', {}).get('timestamp', ''))

            # Summary
            summary = {
                'total_events': len(state_bridge_events),
                'total_messages': len(self.message_log),
                'dissent_count': len([m for m in self.message_log if m.get('msg_type') == 'dissent']),
                'observation_count': len([m for m in self.message_log if m.get('msg_type') == 'observation']),
                'alternative_count': len([m for m in self.message_log if m.get('msg_type') == 'alternative']),
                'ack_count': len([m for m in self.message_log if m.get('msg_type') == 'confirmation'])
            }

            return {
                "events": state_bridge_events,
                "messages": self.message_log,
                "timeline": timeline,
                "summary": summary
            }
        except Exception as e:
            log.error(f"❌ Audit trail failed: {e}")
            return {"events": [], "messages": [], "timeline": [], "summary": {}}

    def _load_state_bridge_events(self, session_id: str = None) -> list:
        """Load events from State Bridge session continuity daemon.

        Args:
            session_id: Optional session ID filter

        Returns:
            List of State Bridge events with timestamps
        """
        try:
            # State Bridge stores session events in SQLite at:
            # ~/.claude/state_bridge/session_events.db
            # For now, return empty list (State Bridge integration in Phase 3)
            # When implemented: query SQLite for session_id events
            return []
        except Exception as e:
            log.error(f"State Bridge load failed: {e}")
            return []

    def close(self):
        """Close RabbitMQ connection."""
        try:
            if self.channel:
                self.channel.close()
            if self.connection:
                self.connection.close()
            log.info("✅ Messaging client closed")
        except Exception as e:
            log.error(f"❌ Close failed: {e}")
