"""
Thunderbird A2A — Agent-to-Agent Protocol
==========================================
Direct persona-to-persona communication layer inspired by Google's A2A protocol.
Enables personas to consult each other without routing through COS for lightweight,
targeted exchanges.

Architecture:
  - Each persona has an "agent card" (capabilities, topics it handles)
  - Personas can directly query other personas via `ask_persona()`
  - Conversations are logged in shared memory (Mem0) for cross-learning
  - COS is always notified of multi-hop chains (3+ persona consultations)

Use cases:
  - Dani asks A2 for destination intel mid-client-conversation
  - A9 asks A2 for pricing data during commission audit
  - A12 asks A5 to validate a strategy before presenting to COS
  - COS broadcasts a query to all relevant personas

Usage:
  from thunderbird_a2a import a2a

  # Direct persona query
  result = a2a.ask("A2", "What's the weather risk for Greek islands in September?", from_persona="A3")

  # Multi-persona chain
  results = a2a.chain(["A2", "A9"], "Compare Silversea vs Regent pricing for Alaska July 2026", from_persona="COS")

  # Broadcast to all
  results = a2a.broadcast("New client onboarded: Kuklinski family, 4 pax, luxury Mediterranean cruise")
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

logger = logging.getLogger("thunderbird_a2a")

# ============================================================================
# AGENT CARDS — what each persona handles
# ============================================================================

AGENT_CARDS = {
    "COS": {
        "topics": ["orchestration", "priorities", "staff coordination", "synthesis", "crisis"],
        "can_delegate": True,
        "accepts_from": ["all"],
    },
    "EXEC": {
        "topics": ["brand voice", "client communications", "visual design", "proposals", "copy"],
        "can_delegate": False,
        "accepts_from": ["COS", "A3", "Commander"],
    },
    "A2": {
        "topics": ["destinations", "research", "travel advisories", "weather", "competitor analysis", "pricing intel", "suppliers"],
        "can_delegate": False,
        "accepts_from": ["all"],
    },
    "A3": {
        "topics": ["client interactions", "bookings", "logistics", "itineraries", "excursions", "dining"],
        "can_delegate": True,  # Can task any persona per CLAUDE.md
        "accepts_from": ["all"],
    },
    "A5": {
        "topics": ["strategy", "growth", "competitive positioning", "pricing strategy", "business decisions"],
        "can_delegate": False,
        "accepts_from": ["COS", "A12", "Commander"],
    },
    "A9": {
        "topics": ["commissions", "costs", "ROI", "budget", "waste", "financial analysis"],
        "can_delegate": False,
        "accepts_from": ["all"],
    },
    "CH": {
        "topics": ["ethics", "morale", "perspective", "wisdom", "is this right"],
        "can_delegate": False,
        "accepts_from": ["all"],
    },
    "A12": {
        "topics": ["automation", "innovation", "first principles", "why are we doing this", "process redesign"],
        "can_delegate": False,
        "accepts_from": ["COS", "A5", "Commander"],
    },
}


class AgentProtocol:
    """Agent-to-Agent communication protocol for the Wing."""

    def __init__(self):
        self._conversation_log: List[Dict] = []

    def ask(self, target_persona: str, query: str,
            from_persona: str = "Commander",
            max_tokens: int = 600) -> Dict[str, Any]:
        """Send a direct query from one persona to another.

        Args:
            target_persona: Who to ask (e.g., "A2", "COS")
            query: The question
            from_persona: Who's asking (e.g., "A3", "COS", "Commander")
            max_tokens: Response length limit

        Returns:
            Dict with persona response + metadata
        """
        from thunderbird_personas import call_persona, resolve_id

        target = resolve_id(target_persona)
        source = resolve_id(from_persona) if from_persona != "Commander" else "Commander"

        # Check if target accepts queries from source
        card = AGENT_CARDS.get(target, {})
        accepts = card.get("accepts_from", ["all"])
        if "all" not in accepts and source not in accepts:
            return {
                "status": "rejected",
                "reason": f"{target} does not accept queries from {source}",
                "target": target,
                "source": source,
            }

        # Prefix query with source context
        prefixed_query = f"[A2A from {source}] {query}"

        result = call_persona(target, prefixed_query, max_tokens=max_tokens)

        # Log the exchange
        exchange = {
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "target": target,
            "query": query,
            "response_preview": result.get("answer", "")[:200],
            "model": result.get("model", ""),
        }
        self._conversation_log.append(exchange)

        # Store in shared memory for cross-learning
        try:
            from thunderbird_shared_memory import shared_memory
            shared_memory.add_interaction(
                target, "internal", prefixed_query, result.get("answer", ""),
                metadata={"a2a_source": source, "type": "a2a_exchange"},
            )
        except Exception:
            pass

        logger.info(f"A2A: {source} → {target} ({len(result.get('answer', ''))} chars)")

        return {
            "status": "ok",
            "source": source,
            "target": target,
            **result,
        }

    def chain(self, personas: List[str], query: str,
              from_persona: str = "Commander",
              max_tokens: int = 600) -> Dict[str, Any]:
        """Query multiple personas sequentially, each building on the previous.

        Each persona sees the query + all previous responses.
        """
        results = []
        accumulated_context = query

        for pid in personas:
            # Build context from previous responses
            context_query = accumulated_context
            if results:
                prev_summaries = "\n".join(
                    f"[{r['target']}]: {r.get('answer', '')[:300]}"
                    for r in results
                )
                context_query = f"{query}\n\nPrevious staff input:\n{prev_summaries}"

            result = self.ask(pid, context_query, from_persona=from_persona, max_tokens=max_tokens)
            results.append(result)

            if result.get("status") != "ok":
                break

        # Alert COS if chain is 3+ personas
        if len(results) >= 3 and from_persona != "COS":
            self.ask("COS",
                     f"A2A chain alert: {from_persona} consulted {len(results)} personas on: {query[:200]}",
                     from_persona="SYSTEM", max_tokens=200)

        return {
            "chain": [pid for pid in personas],
            "results": results,
            "query": query,
        }

    async def broadcast(self, message: str, from_persona: str = "COS",
                        exclude: Optional[List[str]] = None) -> Dict[str, Any]:
        """Broadcast a message to all personas — fire-and-forget.

        Used for: new client onboarding, policy changes, alerts.
        Returns immediately after logging intent; actual delivery is async.
        """
        return self.broadcast_sync(message, from_persona, exclude)

    def broadcast_sync(self, message: str, from_persona: str = "COS",
                       exclude: Optional[List[str]] = None) -> Dict[str, Any]:
        """Synchronous broadcast — suitable for thread dispatch."""
        ex = set(exclude or [])
        ex.add(from_persona)
        targets = [p for p in AGENT_CARDS if p not in ex]
        log_msg = f"[Broadcast from {from_persona}] {message[:200]}"
        logger.info(f"Dispatching broadcast to {len(targets)} personas: {log_msg}")
        for pid in targets:
            try:
                self.ask(pid, message, from_persona=from_persona, max_tokens=300)
                logger.debug(f"Broadcast delivered to {pid}")
            except Exception as e:
                logger.warning(f"Broadcast to {pid} failed: {e}")
        return {
            "broadcast": True,
            "from": from_persona,
            "recipients": targets,
            "count": len(targets),
        }

    def find_expert(self, topic: str) -> List[str]:
        """Find which persona(s) are best suited for a topic."""
        matches = []
        topic_words = topic.lower().split()
        for pid, card in AGENT_CARDS.items():
            for t in card["topics"]:
                t_words = t.lower().split()
                # Match if any topic word appears in any card topic word (substring)
                if any(tw in cw or cw in tw for tw in topic_words for cw in t_words):
                    matches.append(pid)
                    break
        return matches if matches else ["COS"]  # Default to COS

    def get_log(self, limit: int = 20) -> List[Dict]:
        """Get recent A2A conversation log."""
        return self._conversation_log[-limit:]

    def stats(self) -> Dict[str, Any]:
        """Get A2A usage statistics."""
        if not self._conversation_log:
            return {"total_exchanges": 0}

        source_counts = {}
        target_counts = {}
        for ex in self._conversation_log:
            src = ex.get("source", "unknown")
            tgt = ex.get("target", "unknown")
            source_counts[src] = source_counts.get(src, 0) + 1
            target_counts[tgt] = target_counts.get(tgt, 0) + 1

        return {
            "total_exchanges": len(self._conversation_log),
            "most_active_source": max(source_counts, key=source_counts.get),
            "most_consulted": max(target_counts, key=target_counts.get),
            "source_counts": source_counts,
            "target_counts": target_counts,
        }


# Singleton
a2a = AgentProtocol()


# ============================================================================
# MCP TOOL REGISTRATION
# ============================================================================

def register_a2a_tools(mcp):
    """Register A2A protocol tools with the MCP server."""
    from pydantic import Field

    @mcp.tool(name="a2a_ping",
              annotations={"title": "A2A — Ping Test", "readOnlyHint": True})
    async def a2a_ping() -> str:
        """Test tool — just returns pong."""
        return json.dumps({"status": "pong", "from": "a2a"})

    @mcp.tool(name="a2a_ask",
              annotations={"title": "A2A — Ask a Persona Directly", "readOnlyHint": True})
    async def a2a_ask(
        target: str = Field(..., description="Target persona ID (e.g., 'A2', 'COS', 'A9')"),
        query: str = Field(..., description="The question to ask"),
        from_persona: str = Field("Commander", description="Who's asking (e.g., 'A3', 'COS')"),
    ) -> str:
        """Send a direct query from one persona to another via A2A protocol."""
        result = a2a.ask(target, query, from_persona=from_persona)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool(name="a2a_chain",
              annotations={"title": "A2A — Chain Query Multiple Personas", "readOnlyHint": True})
    async def a2a_chain(
        personas: str = Field(..., description="Comma-separated persona IDs (e.g., 'A2,A9,COS')"),
        query: str = Field(..., description="The question — each persona builds on the previous"),
        from_persona: str = Field("Commander", description="Who initiated the chain"),
    ) -> str:
        """Query multiple personas in sequence, each building on previous responses."""
        persona_list = [p.strip() for p in personas.split(",")]
        result = a2a.chain(persona_list, query, from_persona=from_persona)
        # Trim for readability
        for r in result.get("results", []):
            if "answer" in r and len(r["answer"]) > 500:
                r["answer"] = r["answer"][:500] + "..."
        return json.dumps(result, indent=2, default=str)

    @mcp.tool(name="a2a_broadcast",
              annotations={"title": "A2A — Broadcast to All Personas", "readOnlyHint": False})
    async def a2a_broadcast(
        message: str = Field(..., description="Message to broadcast to all personas"),
        from_persona: str = Field("COS", description="Who's broadcasting"),
    ) -> str:
        """Broadcast a message to all Wing personas (fire-and-forget in thread)."""
        import threading
        t = threading.Thread(
            target=a2a.broadcast_sync,
            args=(message, from_persona),
            daemon=True
        )
        t.start()
        return json.dumps({
            "status": "dispatched",
            "message": f"Broadcast from {from_persona} dispatched to all personas",
            "count": len([p for p in AGENT_CARDS if p != from_persona]),
        }, indent=2, default=str)

    @mcp.tool(name="a2a_find_expert",
              annotations={"title": "A2A — Find Expert for Topic", "readOnlyHint": True})
    async def a2a_find_expert(
        topic: str = Field(..., description="Topic to find the right persona for"),
    ) -> str:
        """Find which persona(s) are best suited for a given topic."""
        experts = a2a.find_expert(topic)
        return json.dumps({"topic": topic, "experts": experts})


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python thunderbird_a2a.py --ask A2 'weather risk Mediterranean September'")
        print("  python thunderbird_a2a.py --chain 'A2,A9' 'Silversea Alaska pricing'")
        print("  python thunderbird_a2a.py --expert 'budget analysis'")
        print("  python thunderbird_a2a.py --test")
        sys.exit(0)

    if "--test" in sys.argv:
        print("A2A module loads OK")
        print(f"Agent cards: {len(AGENT_CARDS)} personas")
        experts = a2a.find_expert("commission audit")
        print(f"Expert for 'commission audit': {experts}")
        experts = a2a.find_expert("client booking")
        print(f"Expert for 'client booking': {experts}")
        print("Ready.")
        sys.exit(0)

    if "--ask" in sys.argv:
        idx = sys.argv.index("--ask")
        target = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else "COS"
        query = sys.argv[idx + 2] if idx + 2 < len(sys.argv) else "Status report"
        result = a2a.ask(target, query)
        print(json.dumps(result, indent=2, default=str))

    elif "--chain" in sys.argv:
        idx = sys.argv.index("--chain")
        personas_str = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else "A2,COS"
        query = sys.argv[idx + 2] if idx + 2 < len(sys.argv) else "General analysis"
        personas = [p.strip() for p in personas_str.split(",")]
        result = a2a.chain(personas, query)
        print(json.dumps(result, indent=2, default=str))

    elif "--expert" in sys.argv:
        idx = sys.argv.index("--expert")
        topic = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else "pricing"
        experts = a2a.find_expert(topic)
        print(f"Experts for '{topic}': {experts}")
