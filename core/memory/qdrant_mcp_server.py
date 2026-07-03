#!/usr/bin/env python3
"""
Thunderbird Qdrant MCP Server
==============================
core/memory/qdrant_mcp_server.py

Exposes QdrantMemorySystem as three MCP tools, mountable by both CC and OC engines.
Uses mcp.server.fastmcp (bundled with the MCP SDK) and FastEmbed (local, zero API cost).

Tools exposed:
  memory_search(query, top_k=5)   — semantic search across thunderbird_memories
  memory_embed_file(filepath)      — ingest / re-embed a single Wing knowledge file
  memory_embed_all()               — full corpus reindex (run after bulk changes)

⚠ PII BOUNDARY: Qdrant runs locally and results stay on-machine. However, if OC
forwards search results to its LLM provider (DeepSeek), client PII in dossier chunks
will egress to that provider. OC must NOT relay dossier-sourced chunks to DeepSeek.
CC (Sonnet/Opus) is PII-cleared — no restriction on dossier results there.

Mount in opencode.json:
  "mcp": {"servers": {"thunderbird-qdrant": {"type": "local",
    "command": "python3",
    "args": ["/home/john/Thunderbird/core/memory/qdrant_mcp_server.py"]}}}

Mount in ~/.claude/mcp.json:
  "thunderbird-qdrant": {"command": "python3",
    "args": ["/home/john/Thunderbird/core/memory/qdrant_mcp_server.py"]}

CI registry: config/ci_registry.json — probe GET /healthz + GET /collections/thunderbird_memories
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path

# ── path setup ────────────────────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from mcp.server.fastmcp import FastMCP
from core.memory.qdrant_memory import QdrantMemorySystem

logging.basicConfig(level=logging.INFO, format="%(asctime)s [qdrant-mcp] %(message)s")
logger = logging.getLogger("qdrant_mcp")

mcp = FastMCP(
    name="thunderbird-qdrant",
    description="Semantic memory search and indexing for the Thunderbird Wing knowledge corpus.",
)

# ── register the three core tools ─────────────────────────────────────────────
# Delegates to QdrantMemorySystem which holds all chunking/embedding/upsert logic.

@mcp.tool(
    name="memory_search",
    annotations={"title": "Semantic Memory Search", "readOnlyHint": True},
)
async def memory_search(query: str, top_k: int = 5) -> str:
    """Search Thunderbird Wing knowledge using semantic (vector) similarity.

    Searches dossiers, standing orders, personas, docs, blackboard, and
    OC/CC memory — returns ranked chunks with source file, score, and excerpt.

    ⚠ OC callers: do NOT forward dossier-sourced chunks to DeepSeek (PII fence).
    CC callers: no restriction — PII-cleared.

    Args:
        query: Natural language question or topic (e.g. "Westbrook balcony preference")
        top_k: Number of results to return (default 5, max 20)
    """
    try:
        mem = QdrantMemorySystem()
        results = mem.search_memories(query, top_k=min(top_k, 20))
        return json.dumps({"query": query, "results": results, "count": len(results)}, indent=2)
    except Exception as exc:
        logger.error("memory_search failed: %s", exc)
        return json.dumps({"error": str(exc), "query": query}, indent=2)


@mcp.tool(
    name="memory_embed_file",
    annotations={"title": "Index Single Knowledge File", "readOnlyHint": False},
)
async def memory_embed_file(filepath: str) -> str:
    """Ingest or re-index a single Wing knowledge file into Qdrant.

    Cleans stale chunks for this file, then re-embeds and upserts.
    Safe to call on every dossier save — idempotent.

    Args:
        filepath: Absolute path to the .md file to index
    """
    try:
        mem = QdrantMemorySystem()
        t0 = time.time()
        stats = mem.embed_new_memory(filepath)
        stats["elapsed_s"] = round(time.time() - t0, 1)
        return json.dumps({"status": "ok", "filepath": filepath, **stats}, indent=2)
    except Exception as exc:
        logger.error("memory_embed_file failed for %s: %s", filepath, exc)
        return json.dumps({"error": str(exc), "filepath": filepath}, indent=2)


@mcp.tool(
    name="memory_embed_all",
    annotations={"title": "Full Corpus Reindex", "readOnlyHint": False},
)
async def memory_embed_all() -> str:
    """Full reindex of all Wing knowledge files into Qdrant.

    Processes dossiers, standing orders, personas, docs, and CC/OC memory.
    Uses FastEmbed bge-small-en-v1.5 (local, zero API cost, ~5-10 min on CPU).
    Run after bulk changes or as the weekly safety-net reindex.
    """
    try:
        mem = QdrantMemorySystem()
        t0 = time.time()
        stats = mem.embed_all_memories()
        stats["elapsed_s"] = round(time.time() - t0, 1)
        return json.dumps({"status": "ok", **stats}, indent=2)
    except Exception as exc:
        logger.error("memory_embed_all failed: %s", exc)
        return json.dumps({"error": str(exc)}, indent=2)


@mcp.tool(
    name="memory_stats",
    annotations={"title": "Qdrant Collection Stats", "readOnlyHint": True},
)
async def memory_stats() -> str:
    """Return point count, collection config, and health for thunderbird_memories.

    Warns at >20K points (task result growth milestone per Opus review 2026-07-03).
    """
    try:
        from core.memory.qdrant_memory import QdrantClient, QDRANT_HOST, QDRANT_PORT, COLLECTION
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        info = client.get_collection(COLLECTION)
        count = info.points_count
        warning = count > 20_000
        return json.dumps({
            "collection": COLLECTION,
            "points_count": count,
            "vector_size": info.config.params.vectors.size,
            "distance": str(info.config.params.vectors.distance),
            "status": info.status,
            "warning": "point count >20K — consider splitting task_results to separate collection" if warning else None,
        }, indent=2)
    except Exception as exc:
        return json.dumps({"error": str(exc)}, indent=2)


# ── entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logger.info("Thunderbird Qdrant MCP server starting (host=%s port=%s collection=%s)",
                os.environ.get("QDRANT_HOST", "localhost"),
                os.environ.get("QDRANT_PORT", "6333"),
                "thunderbird_memories")
    mcp.run()
