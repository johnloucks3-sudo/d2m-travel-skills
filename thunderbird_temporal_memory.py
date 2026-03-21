"""
Thunderbird Temporal Memory — Abstract Interface + Dual Backend
================================================================
Provides a unified API for temporal fact management that works with
EITHER our existing SQLite layer (Phase 1) or Zep Cloud/Graphiti (Phase 2).

Architecture:
  TemporalMemoryBackend (ABC)
    ├── SQLiteTemporalBackend  — uses learning_rules.db (existing tables)
    └── ZepTemporalBackend     — stub, ready for Zep Cloud API key

MCP tools registered:
  temporal_add_fact      — add a temporal fact with validity window
  temporal_query         — query a fact at a specific point in time
  temporal_history       — get full history of an entity+attribute
  temporal_detect_shifts — detect preference shifts within a time window

Usage:
  from thunderbird_temporal_memory import get_backend, register_temporal_tools
  backend = get_backend()  # auto-selects based on ZEP_API_KEY env var
  backend.add_temporal_fact("lyons_nancy_ken", "cabin_preference", "Penthouse Suite", ...)

Zep Cloud setup (when ready):
  1. Sign up at https://getzep.com (free tier, no CC required)
  2. Create project, get API key (starts with "z_")
  3. export ZEP_API_KEY=z_your_key_here
  4. Backend auto-switches to Zep

Zep Cloud pricing (as of March 2026):
  - Free:   1,000 credits/mo, lower priority, rate limits
  - Flex:   $25/mo — full Graphiti engine, temporal graph, entity resolution
  - Growth: Custom pricing — SOC2, HIPAA, VPC deployment

Zep Python SDK:
  pip install zep-cloud          # Cloud SDK
  pip install graphiti-core      # Self-hosted Graphiti engine

Zep MCP Server:
  Graphiti ships an official MCP server (experimental) with tools:
    add_episode, search_facts, search_nodes, get_episodes
  Transport: stdio (Claude Desktop) or HTTP
  Config lives in graphiti repo: mcp_server/

Self-hosted alternative:
  graphiti-core + Neo4j (or FalkorDB/Kuzu) — full control, no cloud dependency.
  Requires managing a graph DB instance. Our SQLite approach is simpler for now.
"""

import json
import logging
import os
import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Database path — shared with thunderbird_learning.py
# ---------------------------------------------------------------------------
DB_DIR = Path(os.path.expanduser("~/Thunderbird"))
DB_PATH = DB_DIR / "learning_rules.db"

# Schema extension for temporal_facts table (new, dedicated table)
_TEMPORAL_SCHEMA = """
CREATE TABLE IF NOT EXISTS temporal_facts (
    fact_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    entity          TEXT NOT NULL,
    attribute       TEXT NOT NULL,
    value           TEXT NOT NULL,
    valid_from      TEXT NOT NULL,
    valid_to        TEXT,
    source          TEXT NOT NULL DEFAULT 'manual',
    confidence      REAL NOT NULL DEFAULT 0.9,
    superseded_by   INTEGER,
    created_at      TEXT NOT NULL,
    metadata        TEXT,
    FOREIGN KEY (superseded_by) REFERENCES temporal_facts(fact_id)
);

CREATE INDEX IF NOT EXISTS idx_tf_entity     ON temporal_facts(entity);
CREATE INDEX IF NOT EXISTS idx_tf_attribute  ON temporal_facts(attribute);
CREATE INDEX IF NOT EXISTS idx_tf_valid      ON temporal_facts(valid_from, valid_to);
CREATE INDEX IF NOT EXISTS idx_tf_entity_attr ON temporal_facts(entity, attribute);
"""


# ---------------------------------------------------------------------------
# Abstract Backend
# ---------------------------------------------------------------------------

class TemporalMemoryBackend(ABC):
    """Abstract interface for temporal fact storage and retrieval."""

    @abstractmethod
    def add_temporal_fact(
        self,
        entity: str,
        attribute: str,
        value: str,
        valid_from: str,
        source: str = "manual",
        confidence: float = 0.9,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Store a temporal fact. Auto-supersedes prior values for same entity+attribute."""
        ...

    @abstractmethod
    def query_fact_at_time(
        self,
        entity: str,
        attribute: str,
        at_time: str,
    ) -> Optional[Dict[str, Any]]:
        """Query what a fact was at a specific point in time."""
        ...

    @abstractmethod
    def get_fact_history(
        self,
        entity: str,
        attribute: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get the full temporal history of an entity (optionally filtered by attribute)."""
        ...

    @abstractmethod
    def detect_preference_shifts(
        self,
        entity: str,
        attribute: Optional[str] = None,
        window_days: int = 90,
    ) -> List[Dict[str, Any]]:
        """Detect preference changes within a time window."""
        ...


# ---------------------------------------------------------------------------
# SQLite Backend — uses our existing learning_rules.db
# ---------------------------------------------------------------------------

class SQLiteTemporalBackend(TemporalMemoryBackend):
    """Phase 1 backend using SQLite with temporal_facts table."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self._ensure_schema()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _ensure_schema(self) -> None:
        conn = self._get_conn()
        try:
            conn.executescript(_TEMPORAL_SCHEMA)
            conn.commit()
        finally:
            conn.close()

    def add_temporal_fact(
        self,
        entity: str,
        attribute: str,
        value: str,
        valid_from: str,
        source: str = "manual",
        confidence: float = 0.9,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        conn = self._get_conn()
        try:
            # Auto-supersede: close out any active fact for same entity+attribute
            active = conn.execute(
                "SELECT fact_id, value FROM temporal_facts "
                "WHERE entity = ? AND attribute = ? AND valid_to IS NULL "
                "ORDER BY valid_from DESC LIMIT 1",
                (entity, attribute),
            ).fetchone()

            superseded_id = None
            if active and active["value"] != value:
                conn.execute(
                    "UPDATE temporal_facts SET valid_to = ? WHERE fact_id = ?",
                    (valid_from, active["fact_id"]),
                )
                superseded_id = active["fact_id"]
                logger.info(
                    f"Superseded fact #{active['fact_id']} for {entity}.{attribute}"
                )

            cur = conn.execute(
                "INSERT INTO temporal_facts "
                "(entity, attribute, value, valid_from, valid_to, source, "
                " confidence, superseded_by, created_at, metadata) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    entity, attribute, value, valid_from, None, source,
                    confidence, None, now,
                    json.dumps(metadata) if metadata else None,
                ),
            )
            new_id = cur.lastrowid

            # Link supersession
            if superseded_id:
                conn.execute(
                    "UPDATE temporal_facts SET superseded_by = ? WHERE fact_id = ?",
                    (new_id, superseded_id),
                )

            conn.commit()
            logger.info(
                f"Added temporal fact #{new_id}: {entity}.{attribute} = {value[:50]}"
            )

            return {
                "fact_id": new_id,
                "entity": entity,
                "attribute": attribute,
                "value": value,
                "valid_from": valid_from,
                "superseded_fact_id": superseded_id,
                "status": "added",
            }
        finally:
            conn.close()

    def query_fact_at_time(
        self,
        entity: str,
        attribute: str,
        at_time: str,
    ) -> Optional[Dict[str, Any]]:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM temporal_facts "
                "WHERE entity = ? AND attribute = ? "
                "AND valid_from <= ? "
                "AND (valid_to IS NULL OR valid_to > ?) "
                "ORDER BY valid_from DESC LIMIT 1",
                (entity, attribute, at_time, at_time),
            ).fetchone()
            if row:
                result = dict(row)
                if result.get("metadata"):
                    try:
                        result["metadata"] = json.loads(result["metadata"])
                    except (json.JSONDecodeError, TypeError):
                        pass
                return result
            return None
        finally:
            conn.close()

    def get_fact_history(
        self,
        entity: str,
        attribute: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        try:
            conditions = ["entity = ?"]
            params: List[Any] = [entity]

            if attribute:
                conditions.append("attribute = ?")
                params.append(attribute)

            where = " AND ".join(conditions)
            rows = conn.execute(
                f"SELECT * FROM temporal_facts WHERE {where} "
                f"ORDER BY valid_from ASC LIMIT ?",
                params + [limit],
            ).fetchall()

            results = []
            for row in rows:
                r = dict(row)
                if r.get("metadata"):
                    try:
                        r["metadata"] = json.loads(r["metadata"])
                    except (json.JSONDecodeError, TypeError):
                        pass
                results.append(r)
            return results
        finally:
            conn.close()

    def detect_preference_shifts(
        self,
        entity: str,
        attribute: Optional[str] = None,
        window_days: int = 90,
    ) -> List[Dict[str, Any]]:
        cutoff = (
            datetime.now(timezone.utc) - timedelta(days=window_days)
        ).isoformat()

        conn = self._get_conn()
        try:
            conditions = ["entity = ?", "valid_from >= ?"]
            params: List[Any] = [entity, cutoff]

            if attribute:
                conditions.append("attribute = ?")
                params.append(attribute)

            where = " AND ".join(conditions)
            rows = conn.execute(
                f"SELECT * FROM temporal_facts WHERE {where} "
                f"ORDER BY attribute, valid_from ASC",
                params,
            ).fetchall()

            # Group by attribute and detect shifts
            from collections import defaultdict
            by_attr: Dict[str, List[Dict]] = defaultdict(list)
            for row in rows:
                by_attr[row["attribute"]].append(dict(row))

            shifts = []
            for attr, facts in by_attr.items():
                if len(facts) < 2:
                    continue
                for i in range(1, len(facts)):
                    prev = facts[i - 1]
                    curr = facts[i]
                    if prev["value"] != curr["value"]:
                        shifts.append({
                            "entity": entity,
                            "attribute": attr,
                            "from_value": prev["value"],
                            "to_value": curr["value"],
                            "shift_date": curr["valid_from"],
                            "confidence_before": prev["confidence"],
                            "confidence_after": curr["confidence"],
                            "source": curr["source"],
                        })

            return shifts
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# Zep Cloud Backend — Stub (ready for API key)
# ---------------------------------------------------------------------------

class ZepTemporalBackend(TemporalMemoryBackend):
    """Phase 2 backend using Zep Cloud's temporal knowledge graph.

    Prerequisites:
      pip install zep-cloud
      export ZEP_API_KEY=z_your_key_here

    Zep Cloud API:
      - graph.add(user_id, data, type)  — add facts/episodes to knowledge graph
      - graph.search(user_id, query)    — semantic + BM25 hybrid search
      - Temporal edges: created_at, expired_at, valid_at, invalid_at
      - Auto entity extraction and deduplication

    Graphiti (self-hosted alternative):
      pip install graphiti-core
      Requires Neo4j / FalkorDB / Kuzu graph database
      API: add_episode(), search(), retrieve_nodes(), retrieve_episodes()
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("ZEP_API_KEY", "")
        self._client = None

        if not self.api_key:
            logger.warning(
                "ZEP_API_KEY not set. Zep backend will not function. "
                "Sign up at https://getzep.com and set ZEP_API_KEY."
            )

    def _get_client(self):
        """Lazy-initialize Zep client."""
        if self._client is None:
            try:
                from zep_cloud.client import Zep  # type: ignore
                self._client = Zep(api_key=self.api_key)
                logger.info("Zep Cloud client initialized")
            except ImportError:
                raise ImportError(
                    "zep-cloud package not installed. Run: pip install zep-cloud"
                )
        return self._client

    def add_temporal_fact(
        self,
        entity: str,
        attribute: str,
        value: str,
        valid_from: str,
        source: str = "manual",
        confidence: float = 0.9,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Add a temporal fact to Zep's knowledge graph.

        Maps to Zep's graph.add() API:
          client.graph.add(
              user_id=entity,
              data=f"{attribute}: {value}",
              type="json",
          )

        Zep automatically:
          - Extracts entities and relationships
          - Detects contradictions with existing facts
          - Invalidates superseded edges
          - Maintains temporal metadata (valid_at, invalid_at)
        """
        # TODO: Implement when ZEP_API_KEY is available
        # client = self._get_client()
        #
        # # Format as structured data for Zep's graph.add()
        # fact_data = json.dumps({
        #     "entity": entity,
        #     "attribute": attribute,
        #     "value": value,
        #     "valid_from": valid_from,
        #     "source": source,
        #     "confidence": confidence,
        #     **(metadata or {}),
        # })
        #
        # # Zep's graph.add automatically handles entity extraction,
        # # deduplication, and temporal edge management
        # result = client.graph.add(
        #     user_id=entity,
        #     data=fact_data,
        #     type="json",
        # )
        #
        # return {
        #     "status": "added_to_zep",
        #     "entity": entity,
        #     "attribute": attribute,
        #     "value": value,
        #     "zep_response": result,
        # }
        raise NotImplementedError(
            "Zep backend not yet configured. Set ZEP_API_KEY env var. "
            "Sign up at https://getzep.com (free tier, no CC required)."
        )

    def query_fact_at_time(
        self,
        entity: str,
        attribute: str,
        at_time: str,
    ) -> Optional[Dict[str, Any]]:
        """Query Zep's knowledge graph for a fact at a specific time.

        Maps to Zep's graph.search() with temporal filtering:
          results = client.graph.search(
              user_id=entity,
              query=f"What was {attribute}?",
              search_scope="edges",
          )

        Then filter results by temporal validity:
          - edge.valid_at <= at_time
          - edge.invalid_at is None or edge.invalid_at > at_time

        Zep advantages over SQLite:
          - Semantic search (no need for exact LIKE patterns)
          - Graph traversal (entity→relationship→entity)
          - Built-in temporal edge metadata
        """
        # TODO: Implement when ZEP_API_KEY is available
        # client = self._get_client()
        #
        # results = client.graph.search(
        #     user_id=entity,
        #     query=f"What was {attribute} at {at_time}?",
        #     search_scope="edges",
        #     limit=5,
        # )
        #
        # # Filter by temporal validity
        # for edge in results:
        #     if (edge.valid_at and edge.valid_at <= at_time and
        #         (edge.invalid_at is None or edge.invalid_at > at_time)):
        #         return {
        #             "entity": entity,
        #             "attribute": attribute,
        #             "value": edge.fact,
        #             "valid_from": edge.valid_at,
        #             "valid_to": edge.invalid_at,
        #             "source": "zep_graph",
        #         }
        # return None
        raise NotImplementedError(
            "Zep backend not yet configured. Set ZEP_API_KEY env var."
        )

    def get_fact_history(
        self,
        entity: str,
        attribute: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get temporal history from Zep's knowledge graph.

        Maps to Zep's graph.search() with broad scope:
          results = client.graph.search(
              user_id=entity,
              query=attribute or "all facts",
              search_scope="edges",
              limit=limit,
          )

        Returns all edges (including invalidated ones) sorted by valid_at.
        Zep preserves the full history — invalidated edges are marked but
        not deleted, unlike our SQLite approach.
        """
        # TODO: Implement when ZEP_API_KEY is available
        raise NotImplementedError(
            "Zep backend not yet configured. Set ZEP_API_KEY env var."
        )

    def detect_preference_shifts(
        self,
        entity: str,
        attribute: Optional[str] = None,
        window_days: int = 90,
    ) -> List[Dict[str, Any]]:
        """Detect preference shifts using Zep's temporal graph.

        Zep advantage: The graph engine automatically detects contradictions
        when new facts are added. Edges have 4 temporal dimensions:
          - created_at: when the edge was added to the graph
          - expired_at: when the edge was invalidated
          - valid_at:   when the real-world fact became true
          - invalid_at: when the real-world fact stopped being true

        We can query for edges where expired_at is within window_days
        and compare with their replacement edges.
        """
        # TODO: Implement when ZEP_API_KEY is available
        raise NotImplementedError(
            "Zep backend not yet configured. Set ZEP_API_KEY env var."
        )


# ---------------------------------------------------------------------------
# Backend factory
# ---------------------------------------------------------------------------

_backend_instance: Optional[TemporalMemoryBackend] = None


def get_backend(force_backend: Optional[str] = None) -> TemporalMemoryBackend:
    """Get the temporal memory backend.

    Auto-selects Zep if ZEP_API_KEY is set, otherwise falls back to SQLite.
    Override with force_backend='sqlite' or force_backend='zep'.
    """
    global _backend_instance

    if _backend_instance is not None and force_backend is None:
        return _backend_instance

    backend_type = force_backend or os.environ.get("TEMPORAL_BACKEND", "auto")

    if backend_type == "zep" or (
        backend_type == "auto" and os.environ.get("ZEP_API_KEY")
    ):
        logger.info("Using Zep Cloud temporal memory backend")
        _backend_instance = ZepTemporalBackend()
    else:
        logger.info("Using SQLite temporal memory backend")
        _backend_instance = SQLiteTemporalBackend()

    return _backend_instance


# ---------------------------------------------------------------------------
# MCP Tool Registration
# ---------------------------------------------------------------------------

def register_temporal_tools(mcp_server) -> None:
    """Register temporal memory MCP tools."""

    @mcp_server.tool(
        name="temporal_add_fact",
        annotations={"title": "Add Temporal Fact"},
    )
    async def temporal_add_fact_tool(
        entity: str,
        attribute: str,
        value: str,
        valid_from: str = "",
        source: str = "manual",
        confidence: float = 0.9,
    ) -> str:
        """Add a temporal fact about an entity (client, persona, process).

        Auto-supersedes any prior value for the same entity+attribute.
        Preserves the full history for point-in-time queries.

        Args:
            entity: The entity key (e.g., 'lyons_nancy_ken', 'commander', 'furlow_missy_john')
            attribute: The attribute name (e.g., 'cabin_preference', 'sign_off', 'hotel_brand')
            value: The current value of the attribute
            valid_from: ISO datetime when this became true (default: now)
            source: Where this fact came from (e.g., 'email_diff', 'client_call', 'booking')
            confidence: Confidence level 0.0-1.0 (default: 0.9)
        """
        if not valid_from:
            valid_from = datetime.now(timezone.utc).isoformat()

        backend = get_backend()
        try:
            result = backend.add_temporal_fact(
                entity=entity,
                attribute=attribute,
                value=value,
                valid_from=valid_from,
                source=source,
                confidence=confidence,
            )
            return json.dumps(result, indent=2)
        except NotImplementedError as e:
            return json.dumps({"error": str(e)})

    @mcp_server.tool(
        name="temporal_query",
        annotations={"title": "Query Temporal Fact at Time"},
    )
    async def temporal_query_tool(
        entity: str,
        attribute: str,
        at_time: str = "",
    ) -> str:
        """Query what a fact was at a specific point in time.

        Examples:
          - 'What was Commander's sign-off in January 2026?'
          - 'What hotel brand did the Furlows prefer last December?'
          - 'What cabin type did the Lyons want in October 2025?'

        Args:
            entity: The entity key (e.g., 'commander', 'lyons_nancy_ken')
            attribute: The attribute name (e.g., 'sign_off', 'cabin_preference')
            at_time: ISO datetime to query at (default: now)
        """
        if not at_time:
            at_time = datetime.now(timezone.utc).isoformat()

        backend = get_backend()
        try:
            result = backend.query_fact_at_time(
                entity=entity,
                attribute=attribute,
                at_time=at_time,
            )
            if result:
                return json.dumps(result, indent=2, default=str)
            return json.dumps({
                "status": "not_found",
                "entity": entity,
                "attribute": attribute,
                "at_time": at_time,
            })
        except NotImplementedError as e:
            return json.dumps({"error": str(e)})

    @mcp_server.tool(
        name="temporal_history",
        annotations={"title": "Get Temporal Fact History"},
    )
    async def temporal_history_tool(
        entity: str,
        attribute: str = "",
        limit: int = 50,
    ) -> str:
        """Get the full temporal history of an entity's attribute.

        Shows how a preference or fact evolved over time, including
        superseded values with their validity windows.

        Args:
            entity: The entity key (e.g., 'furlow_missy_john')
            attribute: Optional — filter to specific attribute (e.g., 'hotel_brand')
            limit: Max results to return (default: 50)
        """
        backend = get_backend()
        try:
            results = backend.get_fact_history(
                entity=entity,
                attribute=attribute or None,
                limit=limit,
            )
            return json.dumps({
                "entity": entity,
                "attribute": attribute or "(all)",
                "count": len(results),
                "history": results,
            }, indent=2, default=str)
        except NotImplementedError as e:
            return json.dumps({"error": str(e)})

    @mcp_server.tool(
        name="temporal_detect_shifts",
        annotations={"title": "Detect Preference Shifts"},
    )
    async def temporal_detect_shifts_tool(
        entity: str,
        attribute: str = "",
        window_days: int = 90,
    ) -> str:
        """Detect preference or fact changes within a time window.

        Surfaces when and how a client's preferences shifted,
        including confidence deltas and sources of change.

        Args:
            entity: The entity key (e.g., 'lyons_nancy_ken')
            attribute: Optional — filter to specific attribute
            window_days: How far back to look (default: 90 days)
        """
        backend = get_backend()
        try:
            shifts = backend.detect_preference_shifts(
                entity=entity,
                attribute=attribute or None,
                window_days=window_days,
            )
            return json.dumps({
                "entity": entity,
                "window_days": window_days,
                "shifts_detected": len(shifts),
                "shifts": shifts,
            }, indent=2, default=str)
        except NotImplementedError as e:
            return json.dumps({"error": str(e)})
