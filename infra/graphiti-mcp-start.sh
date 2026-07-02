#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="/home/john/Thunderbird/infra/graphiti-compose.yml"

echo "[1/7] Checking Docker..."
if ! docker info > /dev/null 2>&1; then
  echo "ERROR: Docker is not running. Start Docker and retry." >&2
  exit 1
fi

echo "[2/7] Starting FalkorDB via docker compose..."
docker compose -f "$COMPOSE_FILE" up -d

echo "[3/7] Waiting for FalkorDB on port 6379..."
RETRIES=10
COUNT=0
until nc -z 127.0.0.1 6379 2>/dev/null; do
  COUNT=$((COUNT + 1))
  if [ "$COUNT" -ge "$RETRIES" ]; then
    echo "ERROR: FalkorDB did not come up after ${RETRIES} retries." >&2
    exit 1
  fi
  echo "  ... waiting (attempt $COUNT/$RETRIES)"
  sleep 2
done
echo "  FalkorDB is up."

echo "[4/7] Checking graphiti-core installation..."
if ! python3 -c "import graphiti_core" 2>/dev/null; then
  echo "  Installing graphiti-core[falkordb]..."
  pip install "graphiti-core[falkordb]" --quiet
else
  echo "  graphiti-core already installed."
fi

echo "[5/7] Exporting environment variables..."
export GRAPHITI_NEO4J_URI="bolt://localhost:6379"
export GRAPHITI_NEO4J_USER="falkordb"
export GRAPHITI_NEO4J_PASSWORD="falkordb"

echo "[6/7] Launching Graphiti MCP server on port 8766..."
python3 -m graphiti_core.mcp --port 8766 &
MCP_PID=$!
echo "  Graphiti MCP PID: $MCP_PID"

echo "[7/7] Waiting briefly for MCP server to bind..."
sleep 2

echo ""
echo "Graphiti MCP ready at http://127.0.0.1:8766"
