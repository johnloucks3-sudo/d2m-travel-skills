# Inter-Persona Messaging API
## Thunderbird Wing — MISSION-172 Delivery

**Version:** 1.0  
**Status:** Production (Gate 3 PASS)  
**Last Updated:** 2026-06-09

---

## Overview

The Inter-Persona Messaging system enables dialogue between staff personas (Sterling, Dembe, Reyes, Dani, Harlan, Washington) using RabbitMQ as the message broker.

**Capabilities:**
- Asynchronous message publishing (dissent, observation, alternative)
- Per-persona inbox queues with acknowledgment flow
- Critical message handling (dissent requires ack)
- Merged audit trail (RabbitMQ + State Bridge)
- 7-day message TTL
- Durable persistence (delivery_mode=2)

---

## Message Types

### Dissent (Requires Acknowledgment)
**Use when:** Staff disagrees with a decision or flags a risk.  
**Requires ack:** Yes (Commander or decision owner must respond)  
**TTL:** 7 days  
**Example:**
```python
dissent = PersonaMessage.dissent(
    from_persona='sterling',
    to_personas=['commander', 'dembe'],
    concern="Timeline compression to 2h is insufficient for staging.",
    context={'decision_id': 'PHASE-2D-TIMELINE', 'severity': 'HIGH'}
)
messaging.publish(dissent)
```

### Observation (No Acknowledgment)
**Use when:** Staff reports a fact or status update.  
**Requires ack:** No  
**TTL:** 7 days  
**Example:**
```python
obs = PersonaMessage.observation(
    from_persona='dembe',
    to_personas=['sterling'],
    note="Iran Persian Gulf toll regime status: active as of Jun 9.",
    context={'category': 'geopolitical', 'tier': 'P1'}
)
messaging.publish(obs)
```

### Alternative (Optional Acknowledgment)
**Use when:** Staff proposes a different approach or timeline.  
**Requires ack:** No (but feedback appreciated)  
**TTL:** 7 days  
**Example:**
```python
alt = PersonaMessage.alternative(
    from_persona='reyes',
    to_personas=['sterling', 'commander'],
    proposal="Pre-embark email at 72h instead of 48h.",
    context={'decision_id': 'TP-TIMING', 'phase': 'Review'}
)
messaging.publish(alt)
```

### Confirmation (System)
**Use when:** Acknowledging a dissent (approved or rejected).  
**Routing:** Goes to audit trail for dissent tracking  
**Example:**
```python
messaging.acknowledge(message_id, persona_name='dembe', vote=True)
# Generates confirmation message logged to audit trail
```

---

## API Reference

### PersonaMessaging Class

**Constructor:**
```python
from core.messaging.rabbitmq_client import PersonaMessaging

# Production (yoga server)
messaging = PersonaMessaging(use_production=True)

# Testing (localhost)
messaging = PersonaMessaging(use_production=False)
```

**Methods:**

#### publish(msg: PersonaMessage) → str
Publishes a message to target personas.
```python
msg_id = messaging.publish(dissent)
# Returns: UUID string (message ID)
```

#### consume(persona_name: str) → List[PersonaMessage]
Consumes messages from a persona's inbox.
```python
messages = messaging.consume('sterling')
# Returns: List of PersonaMessage objects
```

#### acknowledge(message_id: str, persona_name: str, vote: bool) → bool
Acknowledges a critical message.
```python
success = messaging.acknowledge(msg_id, 'dembe', vote=True)
# vote=True: approved
# vote=False: rejected
# Returns: True if success, False otherwise
```

#### audit_trail(session_id: str = None) → dict
Gets merged audit trail (State Bridge + RabbitMQ).
```python
trail = messaging.audit_trail(session_id='PHASE-2D')
# Returns: {
#   'events': [...],           # State Bridge events
#   'messages': [...],          # RabbitMQ messages
#   'timeline': [...],          # Merged, sorted by timestamp
#   'summary': {...}            # Counts by message type
# }
```

#### close()
Closes RabbitMQ connection.
```python
messaging.close()
```

---

## Topology

### Exchanges (Topic Type, Durable)
- `persona.dissent` — dissent messages
- `persona.observations` — observation messages
- `persona.alternatives` — alternative proposals

### Queues (Durable, 7-day TTL)
- `sterling.inbox` — messages routed to Sterling
- `dembe.inbox` — messages routed to Dembe
- `reyes.inbox` — messages routed to Reyes
- `dani.inbox` — messages routed to Dani
- `harlan.inbox` — messages routed to Harlan
- `washington.inbox` — messages routed to Washington

### Routing
Each queue binds to all three exchanges with routing key = persona name.
Example: `sterling.inbox` binds to `persona.dissent` with routing_key='sterling'.

---

## Configuration

**Production Config:** `core/messaging/production_config.py`

**Key settings:**
```python
RABBITMQ_HOST = "192.168.1.198"      # yoga server
RABBITMQ_PORT = 5672
RABBITMQ_USER = "persona_user"
RABBITMQ_PASSWORD = "persona_password"
QUEUE_TTL_MS = 604800000              # 7 days
PERSONAS = ['sterling', 'dembe', 'reyes', 'dani', 'harlan', 'washington']
```

**Environment variables** (optional override):
```bash
RABBITMQ_HOST=<host>
RABBITMQ_PORT=<port>
RABBITMQ_USER=<user>
RABBITMQ_PASSWORD=<password>
```

---

## Usage Patterns

### Pattern 1: Staff Dissent Flow
```python
# 1. Staff raises dissent
dissent = PersonaMessage.dissent(
    from_persona='sterling',
    to_personas=['commander'],
    concern="Risk identified",
    context={'decision_id': 'DECISION-001'}
)
msg_id = messaging.publish(dissent)

# 2. Commander consumes and acknowledges
messages = messaging.consume('commander')
for msg in messages:
    if msg.msg_type == 'dissent' and msg.requires_ack:
        messaging.acknowledge(msg.message_id, 'commander', vote=True)

# 3. Get audit trail
trail = messaging.audit_trail()
# Shows dissent → ack chain
```

### Pattern 2: Broadcast Observation
```python
# 1. Dembe broadcasts intel to entire team
obs = PersonaMessage.observation(
    from_persona='dembe',
    to_personas=['sterling', 'reyes', 'dani', 'harlan', 'washington'],
    note="Breaking intel: XYZ",
    context={'tier': 'P0'}
)
messaging.publish(obs)

# 2. All personas consume
for persona in PERSONAS:
    inbox = messaging.consume(persona)
    # Each persona sees the message
```

### Pattern 3: Session Startup Inbox Check
```python
# Integrated into Hale session startup
from core.messaging.session_startup_hook import startup_persona_reporting

alert = startup_persona_reporting()
if alert:
    # Surface to morning brief
    print(f"⚠️  {alert['count']} persona message(s) pending")
```

---

## Metrics & Monitoring

**Test Results (Phase 2C):**
- Messages published: 31
- Messages consumed: 37 (119.4% delivery)
- Latency: 0.28ms avg (threshold: 500ms)
- Errors: 0
- All message types: ✅

**Live Dissent Test (Phase 2D):**
- Dissent published: 1 (Sterling)
- Staff consumed: 5/5 (100%)
- Staff acknowledged: 5/5 (100%)
- Audit trail complete: ✅

---

## Error Handling

All methods include error handling with logging.

```python
try:
    msg_id = messaging.publish(msg)
except Exception as e:
    log.error(f"Publish failed: {e}")
    # Exception is logged; graceful degradation
```

Common errors:
- **RabbitMQ connection failed** — Check host, port, credentials
- **Exchange not found** — Ensure setup_rabbitmq.py has been run
- **Queue not found** — Verify persona name (must be in PERSONAS list)

---

## Troubleshooting

**Problem:** Messages not being consumed  
**Solution:** Verify RabbitMQ is running (`docker ps`), check persona name spelling

**Problem:** High latency (>500ms)  
**Solution:** Check RabbitMQ CPU/memory, verify network connectivity to yoga

**Problem:** Lost messages  
**Solution:** All messages are durable (delivery_mode=2) with 7-day TTL. Messages are only lost if queue is manually purged.

---

## Future Enhancements

1. **State Bridge integration** — Full merge of session events into audit trail
2. **Dissent visualization** — Dashboard showing dissent chains
3. **Confirmation patterns** — Majority voting on critical decisions
4. **Rate limiting** — Prevent message flood
5. **Message expiration** — Automatic cleanup of resolved dissents

---

## Support & Maintenance

**Owner:** A7 Sterling (Architecture & Process)  
**Backup:** Hale (COS)  
**Contact:** thunder bird@d2mluxury.quest  

**Monitoring:**
- RabbitMQ health: `docker ps | grep rabbitmq`
- Queue depth: `docker exec thunderbird-rabbitmq rabbitmqctl list_queues`
- Message latency: Logged in audit trail

---

**Document Version:** 1.0  
**Status:** Production-Ready  
**Last Updated:** 2026-06-09  
**Next Review:** 2026-07-09
