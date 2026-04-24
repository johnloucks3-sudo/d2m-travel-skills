#!/usr/bin/env bash
# memory_inject.sh — Semantic memory retrieval for Claude Code hooks.
# Usage: bash scripts/memory_inject.sh "query text here"
# Output: Formatted memory injection block to stdout.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

QUERY="${1:-}"
TOP_K="${2:-5}"

if [ -z "$QUERY" ]; then
    echo "Usage: memory_inject.sh <query> [top_k]"
    exit 1
fi

# Verify Qdrant is up
if ! curl -sf http://localhost:6333/healthz > /dev/null 2>&1; then
    echo "[memory-inject] Qdrant not running — skipping semantic memory."
    exit 0
fi

# Run search, capture output
RAW=$(python3 "$PROJECT_DIR/core/memory/qdrant_memory.py" search "$QUERY" --top-k "$TOP_K" 2>/dev/null || true)

if [ -z "$RAW" ] || echo "$RAW" | grep -q "No results found"; then
    exit 0
fi

# Format as injection block
echo ""
echo "# Relevant Memories (semantic search)"
echo "$RAW"
echo ""
