"""
Thunderbird Shared Memory — Mem0 Integration
=============================================
Gives all Wing personas a shared memory layer that persists
across sessions, channels, and conversations.

What gets stored:
  - Client preferences, dietary restrictions, travel style
  - Booking decisions and rationale
  - Persona observations ("Dani noticed Mrs. Furlow prefers balcony suites")
  - Staff insights ("A2 flagged Mediterranean weather risk for September")
  - Interaction outcomes (what worked, what didn't)

Architecture:
  - Mem0 auto-extracts "memories" from persona interactions
  - Each persona call gets relevant memories injected into context
  - Memories are tagged by client, persona, and topic
  - COS and Commander can query the full memory corpus

Usage:
  from thunderbird_shared_memory import shared_memory

  # After a persona interaction:
  shared_memory.add_interaction("A3", "client:furlow", query, response)

  # Before a persona call — get relevant context:
  memories = shared_memory.get_relevant("furlow balcony suite preference")

  # Staff-wide knowledge:
  memories = shared_memory.get_all_for_client("furlow")
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger("thunderbird_shared_memory")

# Mem0 configuration — uses local storage (no external vector DB needed)
MEM0_CONFIG = {
    "version": "v1.1",
    # Mem0 LLM via OpenRouter/DeepSeek V3.1 — no ANTHROPIC_API_KEY required
    "llm": {
        "provider": "openai",
        "config": {
            "model": "deepseek/deepseek-chat-v3-5",
            "openai_base_url": "https://openrouter.ai/api/v1",
            "api_key": os.getenv("OPENROUTER_API_KEY", ""),
            "temperature": 0.1,
            "max_tokens": 1000,
        }
    },
    "embedder": {
        "provider": "huggingface",
        "config": {
            "model": "sentence-transformers/all-MiniLM-L6-v2",
        }
    },
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "collection_name": "d2m_wing_memory",
            "path": str(Path.home() / "Thunderbird" / "data" / "mem0_qdrant"),
            "embedding_model_dims": 384,
        }
    },
}

# Persona metadata for memory tagging
PERSONA_LABELS = {
    "COS": "Col Hale (Chief of Staff)",
    "EXEC": "Naia Solberg-Vega (EXEC)",
    "A2": "Lt Col Dembe (Intel)",
    "A3": "Dani Moreau (Concierge)",
    "A5": "Lt Col Castillo (Strategy)",
    "A9": "Victor Harlan (Finance)",
    "CH": "Col Washington (Chaplain)",
    "A12": "ELON (Innovation)",
}


class SharedMemory:
    """Shared memory layer for all Wing personas via Mem0."""

    def __init__(self):
        self._mem = None
        self._initialized = False

    def _init(self):
        """Lazy initialization — only load Mem0 when first used."""
        if self._initialized:
            return
        try:
            from mem0 import Memory
            # Ensure data dir exists
            data_dir = Path.home() / "Thunderbird" / "data" / "mem0_qdrant"
            data_dir.mkdir(parents=True, exist_ok=True)

            # Anthropic key loaded from environment (Claude Max plan)
            # No external API key needed if using Claude CLI

            self._mem = Memory.from_config(MEM0_CONFIG)
            self._initialized = True
            logger.info("Shared memory initialized (Mem0 + Qdrant local)")
        except Exception as e:
            logger.error(f"Shared memory init failed: {e}")
            self._mem = None
            self._initialized = True  # Don't retry on every call

    def add_interaction(self, persona_id: str, client_key: str,
                        query: str, response: str,
                        metadata: Optional[dict] = None):
        """Store a persona interaction — Mem0 auto-extracts memories.

        Args:
            persona_id: "A3", "COS", "A2", etc.
            client_key: "client:furlow", "client:kuklinski", "internal", etc.
            query: What was asked
            response: What the persona answered
            metadata: Optional extra tags
        """
        self._init()
        if not self._mem:
            return

        try:
            persona_label = PERSONA_LABELS.get(persona_id, persona_id)
            text = (
                f"[{persona_label}] was asked: {query}\n"
                f"[{persona_label}] responded: {response}"
            )

            meta = {
                "persona": persona_id,
                "client": client_key,
                "timestamp": datetime.now().isoformat(),
                "type": "interaction",
            }
            if metadata:
                meta.update(metadata)

            # user_id = client for client-scoped, "wing" for internal
            user_id = client_key if client_key.startswith("client:") else "wing"
            agent_id = persona_id

            self._mem.add(text, user_id=user_id, agent_id=agent_id, metadata=meta)
            logger.debug(f"Memory stored: {persona_id} → {client_key}")
        except Exception as e:
            logger.error(f"Memory add failed: {e}")

    def add_observation(self, persona_id: str, observation: str,
                        client_key: str = "internal"):
        """Store a persona observation (not tied to a specific interaction).

        Use for: "A2 notes that Mediterranean weather in September is risky"
        """
        self._init()
        if not self._mem:
            return

        try:
            persona_label = PERSONA_LABELS.get(persona_id, persona_id)
            text = f"[{persona_label}] observation: {observation}"

            user_id = client_key if client_key.startswith("client:") else "wing"
            self._mem.add(text, user_id=user_id, agent_id=persona_id,
                         metadata={
                             "persona": persona_id,
                             "client": client_key,
                             "type": "observation",
                             "timestamp": datetime.now().isoformat(),
                         })
            logger.debug(f"Observation stored: {persona_id}")
        except Exception as e:
            logger.error(f"Observation add failed: {e}")

    def get_relevant(self, query: str, user_id: str = None,
                     agent_id: str = None, limit: int = 10) -> list:
        """Get memories relevant to a query.

        Args:
            query: Natural language query
            user_id: Filter by client (e.g., "client:furlow") or "wing" for internal
            agent_id: Filter by persona (e.g., "A3")
            limit: Max memories to return
        """
        self._init()
        if not self._mem:
            return []

        try:
            kwargs = {"query": query, "limit": limit}
            # Mem0 requires at least one of user_id, agent_id, run_id
            kwargs["user_id"] = user_id or "wing"
            if agent_id:
                kwargs["agent_id"] = agent_id

            results = self._mem.search(**kwargs)
            memories = []
            for r in results.get("results", results) if isinstance(results, dict) else results:
                if isinstance(r, dict):
                    memories.append({
                        "text": r.get("memory", r.get("text", "")),
                        "score": r.get("score", 0),
                        "metadata": r.get("metadata", {}),
                    })
            return memories
        except Exception as e:
            logger.error(f"Memory search failed: {e}")
            return []

    def get_all_for_client(self, client_name: str, limit: int = 50) -> list:
        """Get all memories for a specific client."""
        return self.get_relevant(
            f"client {client_name} preferences history",
            user_id=f"client:{client_name.lower()}",
            limit=limit,
        )

    def get_persona_memories(self, persona_id: str, limit: int = 20) -> list:
        """Get all memories stored by a specific persona."""
        return self.get_relevant(
            "all observations and interactions",
            agent_id=persona_id,
            limit=limit,
        )

    def get_wing_knowledge(self, topic: str, limit: int = 15) -> list:
        """Search across all personas for knowledge on a topic."""
        return self.get_relevant(topic, user_id="wing", limit=limit)

    def format_for_context(self, memories: list, max_chars: int = 2000) -> str:
        """Format memories for injection into a persona's context window."""
        if not memories:
            return ""

        lines = ["SHARED MEMORY (from Wing personas):"]
        total = 0
        for m in memories:
            text = m.get("text", "")
            if total + len(text) > max_chars:
                break
            lines.append(f"  • {text}")
            total += len(text)

        return "\n".join(lines)

    def stats(self) -> dict:
        """Get memory statistics."""
        self._init()
        if not self._mem:
            return {"status": "not initialized"}

        try:
            all_memories = self._mem.get_all(user_id="wing")
            items = all_memories.get("results", all_memories) if isinstance(all_memories, dict) else all_memories
            count = len(items) if isinstance(items, list) else 0

            return {
                "status": "active",
                "total_memories": count,
                "storage": str(Path.home() / "Thunderbird" / "data" / "mem0_qdrant"),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


# Singleton instance — import and use directly
shared_memory = SharedMemory()


# ============================================================================
# MCP TOOL REGISTRATION
# ============================================================================

def register_memory_tools(mcp):
    """Register shared memory tools with the MCP server."""
    from pydantic import Field

    @mcp.tool(name="wing_memory_search",
              annotations={"title": "Search Wing Shared Memory", "readOnlyHint": True})
    async def wing_memory_search(
        query: str = Field(..., description="Natural language query to search memories"),
        client: str = Field("", description="Filter by client name (e.g., 'furlow')"),
        persona: str = Field("", description="Filter by persona (e.g., 'A3', 'COS')"),
        limit: int = Field(10, description="Max results"),
    ) -> str:
        """Search the Wing's shared memory for relevant knowledge."""
        user_id = f"client:{client.lower()}" if client else None
        agent_id = persona.upper() if persona else None
        results = shared_memory.get_relevant(query, user_id=user_id,
                                              agent_id=agent_id, limit=limit)
        return json.dumps({"memories": results, "count": len(results)}, indent=2, default=str)

    @mcp.tool(name="wing_memory_add",
              annotations={"title": "Add to Wing Shared Memory", "readOnlyHint": False})
    async def wing_memory_add(
        persona: str = Field(..., description="Persona ID (e.g., 'A3', 'COS', 'A2')"),
        observation: str = Field(..., description="The observation or insight to store"),
        client: str = Field("internal", description="Client key (e.g., 'client:furlow') or 'internal'"),
    ) -> str:
        """Add an observation to the Wing's shared memory."""
        shared_memory.add_observation(persona, observation, client)
        return json.dumps({"status": "stored", "persona": persona, "client": client})

    @mcp.tool(name="wing_memory_stats",
              annotations={"title": "Wing Memory Statistics", "readOnlyHint": True})
    async def wing_memory_stats() -> str:
        """Get statistics on the Wing's shared memory."""
        return json.dumps(shared_memory.stats(), indent=2, default=str)


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    if "--stats" in sys.argv:
        print(json.dumps(shared_memory.stats(), indent=2))
    elif "--test" in sys.argv:
        print("Testing shared memory...")
        shared_memory.add_observation("A3", "Mrs. Furlow prefers balcony suites and is celebrating her 25th anniversary", "client:furlow")
        shared_memory.add_observation("A2", "Mediterranean in September has occasional Meltemi wind risk in Greek islands", "internal")
        shared_memory.add_observation("A9", "Silversea commission confirmed at 18% for 2026 season", "internal")
        print("Added 3 test observations")

        results = shared_memory.get_relevant("Furlow preferences")
        print(f"\nSearch 'Furlow preferences': {len(results)} results")
        for r in results:
            print(f"  • {r['text']}")

        print(f"\nStats: {json.dumps(shared_memory.stats(), indent=2)}")
    else:
        print("Usage: python thunderbird_shared_memory.py --test | --stats")
