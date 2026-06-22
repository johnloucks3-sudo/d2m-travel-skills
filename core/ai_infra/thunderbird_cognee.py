#!/usr/bin/env python3
"""
thunderbird_cognee.py — Cognee knowledge graph memory adapter.
Cognee v1.2.1 — enriches LLM context with semantic knowledge graph layer.
Use for cross-session client preference memory and trip pattern recognition.

Usage:
    from core.ai_infra.thunderbird_cognee import add_memory, search_memory
    await add_memory("Client Amy Darrow prefers Regent, has Parkinson's — no Allianz insurance")
    results = await search_memory("Amy Darrow preferences")
"""
from __future__ import annotations
import os
import asyncio
from pathlib import Path

_ENV = Path(__file__).parent.parent.parent / ".env"


def _get_key(name: str) -> str:
    val = os.environ.get(name, "")
    if val:
        return val
    try:
        for line in _ENV.read_text().splitlines():
            if line.startswith(f"{name}=") and not line.startswith("#"):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return ""


async def add_memory(text: str, dataset: str = "thunderbird") -> dict:
    """Add text to Cognee knowledge graph."""
    import cognee
    cognee.config.llm_api_key = _get_key("ANTHROPIC_API_KEY")
    await cognee.add(text, dataset_name=dataset)
    await cognee.cognify()
    return {"status": "added", "dataset": dataset, "chars": len(text)}


async def search_memory(query: str, query_type: str = "insights") -> list:
    """Search Cognee knowledge graph. Returns list of result objects."""
    import cognee
    cognee.config.llm_api_key = _get_key("ANTHROPIC_API_KEY")
    results = await cognee.search(query_type, query)
    return results


def add_memory_sync(text: str, dataset: str = "thunderbird") -> dict:
    """Blocking wrapper for add_memory."""
    return asyncio.run(add_memory(text, dataset))


def search_memory_sync(query: str) -> list:
    """Blocking wrapper for search_memory."""
    return asyncio.run(search_memory(query))


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2 and sys.argv[1] == "add":
        print(add_memory_sync(" ".join(sys.argv[2:])))
    elif len(sys.argv) > 2 and sys.argv[1] == "search":
        results = search_memory_sync(" ".join(sys.argv[2:]))
        for r in results:
            print(r)
    else:
        print("Usage: thunderbird_cognee.py add <text>  |  search <query>")
