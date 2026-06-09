"""Production configuration for RabbitMQ messaging on yoga server.

Deployment: yoga (192.168.1.198:5672)
Auth: persona_user (password from RABBITMQ_PASSWORD environment variable)
TTL: 7 days per queue
Persistence: durable exchanges + queues
Ack pattern: critical messages (dissent) require ack
"""

import os
from pathlib import Path


def _load_dotenv_password() -> str | None:
    """Read RABBITMQ_PASSWORD from the repo .env if not already in os.environ.

    No python-dotenv dependency — a minimal KEY=VALUE parse. This makes the
    secret available to every client regardless of how it was launched
    (session_init, handlers, tests, daemons) without baking it into source.
    .env is gitignored; the password never enters version control.
    """
    if os.getenv("RABBITMQ_PASSWORD"):
        return os.environ["RABBITMQ_PASSWORD"]
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if not env_path.exists():
        return None
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line.startswith("RABBITMQ_PASSWORD="):
            val = line.split("=", 1)[1].strip().strip('"').strip("'")
            if val:
                os.environ["RABBITMQ_PASSWORD"] = val  # cache for other readers
                return val
    return None


class MessagingConfig:
    """Production configuration."""

    # Yoga deployment (192.168.1.198)
    # Credentials come from the environment or the gitignored .env — never source.
    # No insecure fallback: a missing password fails loud at connect time rather
    # than silently using a default that is committed and network-guessable.
    RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "192.168.1.198")
    RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
    RABBITMQ_USER = os.getenv("RABBITMQ_USER", "persona_user")
    RABBITMQ_PASSWORD = _load_dotenv_password()

    # Fallback to localhost for testing
    RABBITMQ_HOST_FALLBACK = "localhost"
    RABBITMQ_PORT_FALLBACK = 5672

    # Queue config
    QUEUE_TTL_MS = 604800000  # 7 days
    MESSAGE_TTL_MS = 604800000  # 7 days
    DURABLE = True
    AUTO_DELETE = False

    # Connection
    CONNECTION_ATTEMPTS = 3
    RETRY_DELAY = 2
    HEARTBEAT = 30  # seconds
    BLOCKED_CONNECTION_TIMEOUT = 300  # seconds

    # Topology
    EXCHANGES = {
        'persona.dissent': 'topic',
        'persona.observations': 'topic',
        'persona.alternatives': 'topic'
    }

    PERSONAS = [
        'sterling',
        'dembe',
        'reyes',
        'dani',
        'harlan',
        'washington'
    ]


    @staticmethod
    def get_bindings():
        """Get queue-to-exchange bindings for all personas."""
        return [
            (f"{persona}.inbox", exchange, persona)
            for persona in MessagingConfig.PERSONAS
            for exchange in MessagingConfig.EXCHANGES.keys()
        ]

    # Audit
    ENABLE_AUDIT = True
    AUDIT_QUEUE = 'audit.trail'

    @staticmethod
    def get_connection_params(use_fallback=False):
        """Get RabbitMQ connection parameters.

        Args:
            use_fallback: If True, use localhost (for testing)

        Returns:
            dict with host, port, credentials, connection settings
        """
        host = MessagingConfig.RABBITMQ_HOST_FALLBACK if use_fallback else MessagingConfig.RABBITMQ_HOST
        port = MessagingConfig.RABBITMQ_PORT_FALLBACK if use_fallback else MessagingConfig.RABBITMQ_PORT

        password = MessagingConfig.RABBITMQ_PASSWORD or _load_dotenv_password()
        if not password:
            raise RuntimeError(
                "RABBITMQ_PASSWORD is not set. Add it to the repo .env "
                "(RABBITMQ_PASSWORD=...) or export it. Refusing to connect with "
                "an insecure default."
            )

        return {
            'host': host,
            'port': port,
            'username': MessagingConfig.RABBITMQ_USER,
            'password': password,
            'connection_attempts': MessagingConfig.CONNECTION_ATTEMPTS,
            'retry_delay': MessagingConfig.RETRY_DELAY,
            'heartbeat': MessagingConfig.HEARTBEAT,
            'blocked_connection_timeout': MessagingConfig.BLOCKED_CONNECTION_TIMEOUT
        }

    @staticmethod
    def describe():
        """Return human-readable config summary."""
        return f"""
RabbitMQ Production Configuration
==================================

Host:       {MessagingConfig.RABBITMQ_HOST}:{MessagingConfig.RABBITMQ_PORT}
Fallback:   {MessagingConfig.RABBITMQ_HOST_FALLBACK}:{MessagingConfig.RABBITMQ_PORT_FALLBACK}
Auth:       {MessagingConfig.RABBITMQ_USER}

Exchanges:  {len(MessagingConfig.EXCHANGES)} (all topic, durable)
Queues:     {len(MessagingConfig.PERSONAS)} (one per persona, 7-day TTL)
Personas:   {', '.join(MessagingConfig.PERSONAS)}

Message TTL:    7 days
Queue TTL:      7 days
Persistence:    Durable (delivery_mode=2)
Max messages:   10,000 per queue (safety cap)
Audit:          Enabled (all messages logged)
"""

if __name__ == '__main__':
    print(MessagingConfig.describe())
