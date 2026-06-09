#!/bin/bash
# MISSION-172 Production Deployment to yoga (192.168.1.198)
#
# Prerequisites:
#   - Docker installed on yoga
#   - Network connectivity to thunderbird repo
#   - sudo access (or docker group membership)
#
# Execution:
#   1. Copy this script to yoga
#   2. Set RABBITMQ_PASSWORD environment variable
#   3. Run: bash deploy_rabbitmq_to_yoga.sh

set -e

echo "════════════════════════════════════════════════════════════════"
echo "MISSION-172 PRODUCTION DEPLOYMENT — yoga (192.168.1.198)"
echo "════════════════════════════════════════════════════════════════"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
YOGA_HOST="192.168.1.198"
CONTAINER_NAME="thunderbird-rabbitmq-prod"
RABBITMQ_USER="persona_user"
RABBITMQ_PASSWORD="${RABBITMQ_PASSWORD:-}"
AMQP_PORT="5672"
MGMT_PORT="15672"

# Validation
if [ -z "$RABBITMQ_PASSWORD" ]; then
    echo -e "${RED}❌ ERROR: RABBITMQ_PASSWORD not set${NC}"
    echo "   Set it: export RABBITMQ_PASSWORD=<secure-password>"
    exit 1
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "STEP 1: Stop existing container (if running)"
echo "═══════════════════════════════════════════════════════════════"

if docker ps -a | grep -q "$CONTAINER_NAME"; then
    echo "Stopping existing container..."
    docker stop "$CONTAINER_NAME" 2>/dev/null || true
    docker rm "$CONTAINER_NAME" 2>/dev/null || true
    echo -e "${GREEN}✅ Old container stopped${NC}"
else
    echo "No existing container found"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "STEP 2: Launch RabbitMQ container (production)"
echo "═══════════════════════════════════════════════════════════════"

echo "Launching RabbitMQ 3.13-management..."
docker run -d \
    --name "$CONTAINER_NAME" \
    -p "$AMQP_PORT:5672" \
    -p "$MGMT_PORT:15672" \
    -e RABBITMQ_DEFAULT_USER="$RABBITMQ_USER" \
    -e RABBITMQ_DEFAULT_PASS="$RABBITMQ_PASSWORD" \
    -v rabbitmq-data:/var/lib/rabbitmq \
    -v rabbitmq-logs:/var/log/rabbitmq \
    --restart unless-stopped \
    rabbitmq:3.13-management

sleep 3

if docker ps | grep -q "$CONTAINER_NAME"; then
    echo -e "${GREEN}✅ RabbitMQ container running${NC}"
else
    echo -e "${RED}❌ Container failed to start${NC}"
    docker logs "$CONTAINER_NAME"
    exit 1
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "STEP 3: Initialize RabbitMQ topology"
echo "═══════════════════════════════════════════════════════════════"

echo "Setting up exchanges and queues..."

# Create exchanges
for exchange in "persona.dissent" "persona.observations" "persona.alternatives"; do
    docker exec "$CONTAINER_NAME" rabbitmqctl declare_exchange "$exchange" topic --durable
    echo -e "${GREEN}✅${NC} Exchange: $exchange"
done

# Create queues with TTL
for persona in sterling dembe reyes dani harlan washington; do
    queue_name="${persona}.inbox"
    docker exec "$CONTAINER_NAME" rabbitmqctl declare_queue "$queue_name" --durable
    echo -e "${GREEN}✅${NC} Queue: $queue_name (7-day TTL)"
done

# Set queue argument for TTL (requires direct command)
echo "Setting 7-day TTL on all queues..."
for persona in sterling dembe reyes dani harlan washington; do
    queue_name="${persona}.inbox"
    docker exec "$CONTAINER_NAME" \
        rabbitmqctl set_queue_attributes "$queue_name" x-message-ttl 604800000
done

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "STEP 4: Verify topology"
echo "═══════════════════════════════════════════════════════════════"

echo "Listing users..."
docker exec "$CONTAINER_NAME" rabbitmqctl list_users

echo ""
echo "Listing exchanges..."
docker exec "$CONTAINER_NAME" rabbitmqctl list_exchanges | grep persona

echo ""
echo "Listing queues..."
docker exec "$CONTAINER_NAME" rabbitmqctl list_queues name messages | grep inbox

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "STEP 5: Health check"
echo "═══════════════════════════════════════════════════════════════"

echo "Pinging RabbitMQ..."
docker exec "$CONTAINER_NAME" rabbitmqctl ping

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "DEPLOYMENT COMPLETE ✅"
echo "═══════════════════════════════════════════════════════════════"

echo ""
echo "📊 PRODUCTION DETAILS:"
echo "   Host:            $YOGA_HOST"
echo "   Container:       $CONTAINER_NAME"
echo "   AMQP port:       $AMQP_PORT"
echo "   Management UI:   http://$YOGA_HOST:$MGMT_PORT"
echo "   User:            $RABBITMQ_USER"
echo "   Data volume:     rabbitmq-data"
echo "   Logs volume:     rabbitmq-logs"
echo "   Restart policy:  unless-stopped"
echo ""
echo "🔑 CREDENTIALS:"
echo "   Username:        $RABBITMQ_USER"
echo "   Password:        (set via RABBITMQ_PASSWORD)"
echo ""
echo "📡 TOPOLOGY:"
echo "   Exchanges:       3 (persona.dissent, observations, alternatives)"
echo "   Queues:          6 (one per persona)"
echo "   TTL:             7 days per queue"
echo "   Persistence:     Durable (delivery_mode=2)"
echo ""
echo "✓ Next steps:"
echo "  1. Update production_config.py RABBITMQ_HOST='192.168.1.198'"
echo "  2. Set export RABBITMQ_PASSWORD=<your-password>"
echo "  3. Test: python3 tests/test_live_dissent_production.py"
echo "  4. Activate: session_init.py will auto-detect yoga"
echo ""
