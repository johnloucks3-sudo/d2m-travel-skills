#!/usr/bin/env python3
"""MISSION-172: RabbitMQ setup — create exchanges and queues."""

import pika
import sys

def setup_rabbitmq():
    """Create RabbitMQ infrastructure for persona messaging."""
    try:
        # Connect
        credentials = pika.PlainCredentials('persona_user', 'persona_password')
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host='localhost',
                port=5672,
                credentials=credentials,
                connection_attempts=3,
                retry_delay=2
            )
        )
        channel = connection.channel()
        print("✅ Connected to RabbitMQ")

        # Declare exchanges
        exchanges = [
            'persona.dissent',
            'persona.observations',
            'persona.alternatives'
        ]
        for exchange in exchanges:
            channel.exchange_declare(
                exchange=exchange,
                exchange_type='topic',
                durable=True
            )
            print(f"✅ Exchange created: {exchange}")

        # Declare queues and bind to exchanges
        personas = ['sterling', 'dembe', 'reyes', 'dani', 'harlan', 'washington']
        for persona in personas:
            queue_name = f"{persona}.inbox"
            channel.queue_declare(
                queue=queue_name,
                durable=True,
                arguments={'x-message-ttl': 604800000}  # 7 days TTL
            )
            # Bind to all exchanges with routing key = persona name
            for exchange in exchanges:
                channel.queue_bind(
                    exchange=exchange,
                    queue=queue_name,
                    routing_key=persona
                )
            print(f"✅ Queue created: {queue_name}")

        connection.close()
        print("\n✅ RabbitMQ infrastructure ready for persona messaging")
        print("\nQueues:")
        for persona in personas:
            print(f"  - {persona}.inbox")
        return True

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return False

if __name__ == '__main__':
    success = setup_rabbitmq()
    sys.exit(0 if success else 1)
