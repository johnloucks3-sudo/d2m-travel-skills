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

log = logging.getLogger("messaging")

class PersonaMessaging:
    """RabbitMQ-backed messaging for persona dialogue."""

    def __init__(self, host: str = "localhost", port: int = 5672, username: str = "persona_user", password: str = "persona_password"):
        """Initialize messaging client.

        Args:
            host: RabbitMQ host (default: localhost / yoga)
            port: RabbitMQ port (default: 5672)
            username: RabbitMQ user
            password: RabbitMQ password
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
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

            # Route to exchange based on message type
            exchange = f"persona.{msg.msg_type}"

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
        """Get all dissent messages for a decision.

        Args:
            decision_id: Decision ID (from context)

        Returns:
            Chronological list of dissent + responses
        """
        try:
            messages = []
            # Query audit trail for all messages with matching context.decision_id
            for entry in self.message_log:
                if entry.get('context', {}).get('decision_id') == decision_id:
                    messages.append(entry)

            log.info(f"✅ Retrieved {len(messages)} dissent messages for {decision_id}")
            return messages
        except Exception as e:
            log.error(f"❌ Get dissent chain failed: {e}")
            return []

    def audit_trail(self, session_id: str = None) -> dict:
        """Get merged audit trail (RabbitMQ message log).

        Args:
            session_id: Optional session ID filter

        Returns:
            {"events": [...], "messages": [...], "timeline": [...]}
        """
        try:
            return {
                "events": [],  # State Bridge events would go here
                "messages": self.message_log,
                "timeline": sorted(self.message_log, key=lambda x: x.get('timestamp', ''))
            }
        except Exception as e:
            log.error(f"❌ Audit trail failed: {e}")
            return {"events": [], "messages": [], "timeline": []}

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
