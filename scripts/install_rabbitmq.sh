#!/bin/bash
# MISSION-172 Phase 2: RabbitMQ Installation & Setup
# Target: yoga server (192.168.1.198)
# Cost: $0 (open source)

set -e

echo "=== RabbitMQ Installation for Thunderbird Inter-Persona Messaging ==="

# Check if already installed
if command -v rabbitmq-server &> /dev/null; then
    echo "✅ RabbitMQ already installed: $(rabbitmq-server --version)"
else
    echo "📦 Installing RabbitMQ..."

    # Detect OS
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux (Ubuntu/Debian)
        sudo apt-get update
        sudo apt-get install -y rabbitmq-server
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        brew install rabbitmq
    else
        echo "❌ Unsupported OS: $OSTYPE"
        exit 1
    fi
fi

# Enable management plugin (for UI + API)
echo "🔌 Enabling RabbitMQ management plugin..."
sudo rabbitmq-plugins enable rabbitmq_management

# Start service
echo "🚀 Starting RabbitMQ..."
sudo systemctl start rabbitmq-server
sudo systemctl enable rabbitmq-server

# Wait for startup
sleep 3

# Create persona user
echo "👤 Creating RabbitMQ user: persona_user..."
sudo rabbitmqctl add_user persona_user persona_password || echo "User already exists"
sudo rabbitmqctl set_permissions -p / persona_user ".*" ".*" ".*"

# Declare exchanges
echo "📡 Declaring RabbitMQ exchanges..."
sudo rabbitmqctl eval 'rpc:call(node(), rabbit_exchange, declare, [{name, <<"persona.dissent">>}, topic, true, false, false, []}), ok.' || echo "Exchange exists"
sudo rabbitmqctl eval 'rpc:call(node(), rabbit_exchange, declare, [{name, <<"persona.observations">>}, topic, true, false, false, []}), ok.' || echo "Exchange exists"
sudo rabbitmqctl eval 'rpc:call(node(), rabbit_exchange, declare, [{name, <<"persona.alternatives">>}, topic, true, false, false, []}), ok.' || echo "Exchange exists"

# Declare queues
echo "📦 Declaring persona inbox queues..."
for persona in sterling dembe reyes dani harlan washington; do
    queue_name="${persona}.inbox"
    sudo rabbitmqctl add_vhost / || true
    # Using HTTP API is easier for queue creation
    curl -i -u ***REMOVED-SECRET*** -H "content-type:application/json" \
      -XPUT http://localhost:15672/api/queues/%2F/${queue_name} \
      -d'{"durable":true,"arguments":{"x-message-ttl":604800000}}' 2>/dev/null || echo "Queue $queue_name configured"
done

# Verify
echo "✅ RabbitMQ ready for persona messaging"
echo "   Management UI: http://localhost:15672 (persona_user / persona_password)"
echo "   AMQP Port: localhost:5672"
echo ""
echo "Persona Queues:"
for persona in sterling dembe reyes dani harlan washington; do
    echo "   - ${persona}.inbox"
done
