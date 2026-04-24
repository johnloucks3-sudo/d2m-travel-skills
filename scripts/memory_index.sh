#!/usr/bin/env bash
# memory_index.sh — One-shot indexer: starts Qdrant, embeds all 149+ memory files.
# Usage: bash scripts/memory_index.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CONTAINER="thunderbird-qdrant"

echo "=== Thunderbird Memory Indexer ==="
echo "Project: $PROJECT_DIR"
echo ""

# 1. Ensure Qdrant container is running
if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
    echo "[OK] Qdrant container already running."
elif docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
    echo "[..] Starting existing Qdrant container..."
    docker start "$CONTAINER"
    sleep 3
    echo "[OK] Qdrant started."
else
    echo "[..] Creating Qdrant container..."
    docker run -d \
        --name "$CONTAINER" \
        --restart=no \
        -p 6333:6333 \
        -p 6334:6334 \
        -v "$PROJECT_DIR/data/qdrant:/qdrant/storage:z" \
        qdrant/qdrant:latest
    echo "[..] Waiting for Qdrant to initialize..."
    sleep 5
    echo "[OK] Qdrant created and started."
fi

# 2. Verify Qdrant is responding
for i in 1 2 3 4 5; do
    if curl -sf http://localhost:6333/healthz > /dev/null 2>&1; then
        echo "[OK] Qdrant healthy on port 6333."
        break
    fi
    if [ "$i" -eq 5 ]; then
        echo "[FAIL] Qdrant not responding after 5 attempts."
        exit 1
    fi
    echo "[..] Waiting for Qdrant (attempt $i/5)..."
    sleep 2
done

# 3. Run the bulk embedder
echo ""
echo "=== Embedding all memory files ==="
python3 "$PROJECT_DIR/core/memory/qdrant_memory.py" embed-all

echo ""
echo "=== Indexing complete ==="
