"""
Thunderbird Memory Embeddings — OpenClaw P1 Pattern Adaptation
Persistent vector memory system with semantic recall.

Indexes: wing communications, mission outcomes, client interactions, dossier updates
Query: semantic search via cosine similarity on stored embeddings
Storage: SQLite + FAISS (or fallback to pure cosine on NumPy arrays)
"""

import os
import json
import math
import logging
import hashlib
import sqlite3
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

# Try optional deps; fall back to pure-python if unavailable
try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False

try:
    import faiss
    _HAS_FAISS = True
except ImportError:
    _HAS_FAISS = False

try:
    from anthropic import Anthropic
    _HAS_ANTHROPIC = True
except ImportError:
    _HAS_ANTHROPIC = False


# ============================================================================
# EMBEDDING PROVIDERS
# ============================================================================

class EmbeddingProvider:
    """Base embedding provider interface"""

    def embed(self, text: str) -> List[float]:
        raise NotImplementedError

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed(t) for t in texts]

    @property
    def dimension(self) -> int:
        raise NotImplementedError


class AnthropicEmbeddingProvider(EmbeddingProvider):
    """Uses Claude's embedding-like capability via text representation.
    
    Since Anthropic doesn't have a public embedding API, we use a
    deterministic hash-based projection as a lightweight fallback,
    or call an external embedding API if configured.
    """

    def __init__(self, dimension: int = 384):
        self._dimension = dimension

    _fastembed_model = None  # lazy class-level cache (bge-small, 384-dim, local $0)

    def _fastembed(self, text: str) -> List[float]:
        """Local semantic embedding via FastEmbed (bge-small, 384-dim, zero API cost).
        Replaces the retired OpenRouter embedding path (MISSION-267, 2026-06-15)."""
        if AnthropicEmbeddingProvider._fastembed_model is None:
            from fastembed import TextEmbedding
            AnthropicEmbeddingProvider._fastembed_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
        vec = list(next(AnthropicEmbeddingProvider._fastembed_model.embed([text[:8000]])))
        return [float(x) for x in vec]

    def embed(self, text: str) -> List[float]:
        """Generate an embedding. Order: local FastEmbed (semantic, $0) -> hash fallback.
        OpenRouter embedding path retired 2026-06-15 (MISSION-267) in favor of local FastEmbed.
        """
        try:
            return self._fastembed(text)
        except Exception as _e:
            logger.debug(f"FastEmbed unavailable ({_e}); falling back")
        if os.environ.get("OPENROUTER_API_KEY"):
            return self._openrouter_embed(text)
        
        # Deterministic hash-based embedding (fallback)
        h = hashlib.sha256(text.encode("utf-8")).digest()
        # Expand hash to cover full dimension
        expanded = h * (self._dimension // 32 + 1)
        # Normalize to [-1, 1] range
        vec = [(b - 128) / 128.0 for b in expanded[:self._dimension]]
        # L2 normalize
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def _openrouter_embed(self, text: str) -> List[float]:
        """Use OpenRouter-compatible embedding endpoint if available."""
        import subprocess
        
        api_key = os.environ["OPENROUTER_API_KEY"]
        payload = json.dumps({
            "model": "openrouter/openai/text-embedding-3-small",
            "input": text[:8000],
        })
        
        try:
            result = subprocess.run(
                ["curl", "-s", "https://openrouter.ai/api/v1/embeddings",
                 "-H", f"Authorization: Bearer {api_key}",
                 "-H", "Content-Type: application/json",
                 "-d", payload],
                capture_output=True, text=True, timeout=30
            )
            data = json.loads(result.stdout)
            return data["data"][0]["embedding"]
        except Exception as e:
            logger.warning(f"OpenRouter embedding failed: {e}, using hash fallback")
            return self._hash_embed(text)

    def _hash_embed(self, text: str) -> List[float]:
        h = hashlib.sha256(text.encode("utf-8")).digest()
        expanded = h * (self._dimension // 32 + 1)
        vec = [(b - 128) / 128.0 for b in expanded[:self._dimension]]
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    @property
    def dimension(self) -> int:
        return self._dimension


# ============================================================================
# VECTOR STORE
# ============================================================================

@dataclass
class MemoryEntry:
    """A single memory entry with its embedding"""
    id: str
    text: str
    source: str  # e.g., "wing_comms", "mission_board", "dossier", "inbox"
    timestamp: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None


class ThunderbirdMemoryStore:
    """Persistent vector memory store with semantic search.
    
    Uses SQLite for storage + optional FAISS for fast similarity search.
    Falls back to pure NumPy/cosine if FAISS unavailable.
    """

    def __init__(self, db_path: Optional[Path] = None, thunderbird_root: Optional[Path] = None):
        self.thunderbird_root = thunderbird_root or Path.home() / "Thunderbird"
        self.db_path = Path(db_path) if db_path else self.thunderbird_root / "state" / "memory_store.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.embedding_provider = AnthropicEmbeddingProvider(dimension=384)
        self._faiss_index = None
        self._id_map = []  # Maps FAISS index position to memory entry id
        
        self._init_db()
        self._load_faiss_index()

    def _init_db(self):
        """Initialize SQLite schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    text TEXT NOT NULL,
                    source TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT DEFAULT '{}',
                    embedding BLOB,
                    created_at TEXT DEFAULT (datetime('now'))
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_source ON memories(source)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp ON memories(timestamp)
            """)
            conn.commit()

    def _load_faiss_index(self):
        """Load or create FAISS index from stored embeddings"""
        if not _HAS_FAISS:
            logger.info("FAISS not available, using SQLite cosine search")
            return
            
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT id, embedding FROM memories WHERE embedding IS NOT NULL ORDER BY rowid"
            )
            rows = cursor.fetchall()
            
        if not rows:
            self._faiss_index = faiss.IndexFlatIP(self.embedding_provider.dimension)
            return
            
        vectors = []
        self._id_map = []
        for entry_id, emb_blob in rows:
            emb = json.loads(emb_blob)
            vectors.append(emb)
            self._id_map.append(entry_id)
            
        vectors_np = np.array(vectors, dtype=np.float32)
        self._faiss_index = faiss.IndexFlatIP(self.embedding_provider.dimension)
        faiss.normalize_L2(vectors_np)
        self._faiss_index.add(vectors_np)
        logger.info(f"Loaded FAISS index with {len(self._id_map)} vectors")

    def add(self, text: str, source: str, metadata: Optional[Dict] = None,
            entry_id: Optional[str] = None) -> str:
        """Add a memory entry and compute its embedding"""
        entry_id = entry_id or f"{source}_{int(time.time() * 1000)}_{hashlib.md5(text[:100].encode()).hexdigest()[:8]}"
        timestamp = datetime.now(timezone.utc).isoformat()
        metadata = metadata or {}
        
        # Compute embedding
        embedding = self.embedding_provider.embed(text)
        emb_json = json.dumps(embedding)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO memories (id, text, source, timestamp, metadata, embedding) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (entry_id, text, source, timestamp, json.dumps(metadata), emb_json)
            )
            conn.commit()
        
        # Update FAISS index
        if _HAS_FAISS and self._faiss_index is not None:
            vec = np.array([embedding], dtype=np.float32)
            faiss.normalize_L2(vec)
            self._faiss_index.add(vec)
            self._id_map.append(entry_id)
        
        logger.info(f"Added memory entry: {entry_id} (source={source})")
        return entry_id

    def search(self, query: str, top_k: int = 5, source_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Semantic search: find most similar memories to query"""
        query_embedding = self.embedding_provider.embed(query)
        
        if _HAS_FAISS and self._faiss_index is not None and self._faiss_index.ntotal > 0:
            return self._search_faiss(query_embedding, top_k, source_filter)
        else:
            return self._search_sqlite(query_embedding, top_k, source_filter)

    def _search_faiss(self, query_emb: List[float], top_k: int,
                      source_filter: Optional[str]) -> List[Dict[str, Any]]:
        """Search using FAISS index"""
        query_vec = np.array([query_emb], dtype=np.float32)
        faiss.normalize_L2(query_vec)
        
        # Search more than top_k to allow source filtering
        search_k = min(top_k * 3, self._faiss_index.ntotal)
        scores, indices = self._faiss_index.search(query_vec, search_k)
        
        results = []
        with sqlite3.connect(self.db_path) as conn:
            for score, idx in zip(scores[0], indices[0]):
                if idx < 0 or idx >= len(self._id_map):
                    continue
                entry_id = self._id_map[idx]
                cursor = conn.execute(
                    "SELECT id, text, source, timestamp, metadata FROM memories WHERE id = ?",
                    (entry_id,)
                )
                row = cursor.fetchone()
                if row:
                    entry = {
                        "id": row[0],
                        "text": row[1],
                        "source": row[2],
                        "timestamp": row[3],
                        "metadata": json.loads(row[4]),
                        "similarity": float(score),
                    }
                    if source_filter and entry["source"] != source_filter:
                        continue
                    results.append(entry)
                    if len(results) >= top_k:
                        break
        
        return results

    def _search_sqlite(self, query_emb: List[float], top_k: int,
                       source_filter: Optional[str]) -> List[Dict[str, Any]]:
        """Fallback: load all embeddings and compute cosine similarity in Python"""
        where = "WHERE embedding IS NOT NULL"
        params: list = []
        if source_filter:
            where += " AND source = ?"
            params.append(source_filter)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                f"SELECT id, text, source, timestamp, metadata, embedding FROM memories {where} ORDER BY timestamp DESC LIMIT 500",
                params
            )
            rows = cursor.fetchall()
        
        results = []
        for row in rows:
            stored_emb = json.loads(row[5])
            sim = self._cosine_similarity(query_emb, stored_emb)
            results.append({
                "id": row[0],
                "text": row[1],
                "source": row[2],
                "timestamp": row[3],
                "metadata": json.loads(row[4]),
                "similarity": float(sim),
            })
        
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two vectors"""
        if _HAS_NUMPY:
            a_np = np.array(a)
            b_np = np.array(b)
            return float(np.dot(a_np, b_np) / (np.linalg.norm(a_np) * np.linalg.norm(b_np) + 1e-10))
        
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a)) or 1e-10
        norm_b = math.sqrt(sum(x * x for x in b)) or 1e-10
        return dot / (norm_a * norm_b)

    def get(self, entry_id: str) -> Optional[Dict[str, Any]]:
        """Get a single memory entry by ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT id, text, source, timestamp, metadata FROM memories WHERE id = ?",
                (entry_id,)
            )
            row = cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "text": row[1],
                "source": row[2],
                "timestamp": row[3],
                "metadata": json.loads(row[4]),
            }
        return None

    def delete(self, entry_id: str) -> bool:
        """Delete a memory entry"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM memories WHERE id = ?", (entry_id,))
            conn.commit()
        deleted = cursor.rowcount > 0
        
        if deleted and _HAS_FAISS and self._faiss_index is not None:
            # FAISS doesn't support deletion; rebuild index
            self._rebuild_faiss()
        
        return deleted

    def _rebuild_faiss(self):
        """Rebuild FAISS index after deletions"""
        if not _HAS_FAISS:
            return
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT id, embedding FROM memories WHERE embedding IS NOT NULL ORDER BY rowid"
            )
            rows = cursor.fetchall()
        
        if not rows:
            self._faiss_index = faiss.IndexFlatIP(self.embedding_provider.dimension)
            self._id_map = []
            return
        
        vectors = []
        self._id_map = []
        for entry_id, emb_blob in rows:
            emb = json.loads(emb_blob)
            vectors.append(emb)
            self._id_map.append(entry_id)
        
        vectors_np = np.array(vectors, dtype=np.float32)
        self._faiss_index = faiss.IndexFlatIP(self.embedding_provider.dimension)
        faiss.normalize_L2(vectors_np)
        self._faiss_index.add(vectors_np)

    def stats(self) -> Dict[str, Any]:
        """Return store statistics"""
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
            by_source = {}
            for row in conn.execute("SELECT source, COUNT(*) FROM memories GROUP BY source"):
                by_source[row[0]] = row[1]
        
        return {
            "total_entries": total,
            "by_source": by_source,
            "faiss_index_size": self._faiss_index.ntotal if _HAS_FAISS and self._faiss_index else 0,
            "embedding_dimension": self.embedding_provider.dimension,
        }


# ============================================================================
# INDEXING PIPELINE
# ============================================================================

class MemoryIndexer:
    """Indexes Thunderbird data sources into the memory store"""

    def __init__(self, store: Optional[ThunderbirdMemoryStore] = None,
                 thunderbird_root: Optional[Path] = None):
        self.thunderbird_root = thunderbird_root or Path.home() / "Thunderbird"
        self.store = store or ThunderbirdMemoryStore(thunderbird_root=self.thunderbird_root)
        self._indexed_ids = set()  # Prevent duplicate indexing

    def index_wing_comms(self) -> int:
        """Index wing communications"""
        comms_file = self.thunderbird_root / "OpsCenter" / "collaboration" / "wing_comms.md"
        if not comms_file.exists():
            return 0
        
        content = comms_file.read_text()
        # Split by sections (--- separators)
        sections = content.split("---")
        count = 0
        for section in sections:
            section = section.strip()
            if len(section) < 50:
                continue
            entry_id = f"wing_comms_{hashlib.md5(section[:200].encode()).hexdigest()[:8]}"
            if entry_id not in self._indexed_ids:
                self.store.add(
                    text=section[:4000],
                    source="wing_comms",
                    metadata={"file": "wing_comms.md"},
                    entry_id=entry_id,
                )
                self._indexed_ids.add(entry_id)
                count += 1
        return count

    def index_mission_board(self) -> int:
        """Index mission board"""
        board_file = self.thunderbird_root / "OpsCenter" / "mission_board.json"
        if not board_file.exists():
            return 0
        
        try:
            board = json.loads(board_file.read_text())
        except Exception:
            return 0
        
        count = 0
        missions = board.get("missions", []) if isinstance(board, dict) else []
        for mission in missions:
            mission_id = mission.get("id", "unknown")
            entry_id = f"mission_{mission_id}"
            if entry_id not in self._indexed_ids:
                text = json.dumps(mission, indent=2)
                self.store.add(
                    text=text,
                    source="mission_board",
                    metadata={"mission_id": mission_id},
                    entry_id=entry_id,
                )
                self._indexed_ids.add(entry_id)
                count += 1
        return count

    def index_dossiers(self) -> int:
        """Index client dossiers"""
        dossier_dir = self.thunderbird_root / "dossiers"
        if not dossier_dir.exists():
            return 0
        
        count = 0
        for f in dossier_dir.glob("*.md"):
            if f.name == "CLAUDE.md":
                continue
            try:
                content = f.read_text()
                entry_id = f"dossier_{f.stem}"
                if entry_id not in self._indexed_ids:
                    self.store.add(
                        text=content[:8000],
                        source="dossier",
                        metadata={"client": f.stem, "file": f.name},
                        entry_id=entry_id,
                    )
                    self._indexed_ids.add(entry_id)
                    count += 1
            except Exception as e:
                logger.warning(f"Failed to index dossier {f}: {e}")
        return count

    def index_inbox_queues(self) -> int:
        """Index inbox queues (opencode_inbox, claude_inbox)"""
        count = 0
        for inbox_name in ["opencode_inbox.md", "claude_inbox.md"]:
            inbox_file = self.thunderbird_root / "OpsCenter" / "collaboration" / inbox_name
            if not inbox_file.exists():
                continue
            
            content = inbox_file.read_text()
            # Split by task boundaries (--- separators)
            tasks = content.split("---")
            for task in tasks:
                task = task.strip()
                if len(task) < 30 or "TASK:" not in task:
                    continue
                entry_id = f"inbox_{hashlib.md5(task[:200].encode()).hexdigest()[:8]}"
                if entry_id not in self._indexed_ids:
                    self.store.add(
                        text=task[:4000],
                        source="inbox_queue",
                        metadata={"inbox": inbox_name},
                        entry_id=entry_id,
                    )
                    self._indexed_ids.add(entry_id)
                    count += 1
        return count

    def index_all(self) -> Dict[str, int]:
        """Index all data sources"""
        return {
            "wing_comms": self.index_wing_comms(),
            "mission_board": self.index_mission_board(),
            "dossiers": self.index_dossiers(),
            "inbox_queues": self.index_inbox_queues(),
        }


# ============================================================================
# MCP TOOL REGISTRATION
# ============================================================================

def register_memory_embedding_tools(mcp) -> None:
    """Register semantic memory tools with MCP server"""
    
    @mcp.tool()
    def search_memory_semantic(query: str, top_k: int = 5, source: str = "") -> str:
        """Search Thunderbird's persistent memory semantically.
        
        Args:
            query: Natural language search query
            top_k: Number of results (default 5)
            source: Filter by source (wing_comms, mission_board, dossier, inbox_queue)
        """
        store = ThunderbirdMemoryStore()
        results = store.search(query, top_k=top_k, source_filter=source or None)
        if not results:
            return "No memories found matching your query."
        
        lines = [f"Memory Search Results ({len(results)} found):\n"]
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. [{r['source']}] (similarity: {r['similarity']:.3f})")
            lines.append(f"   {r['text'][:300]}")
            lines.append(f"   Timestamp: {r['timestamp'][:19]}")
            lines.append("")
        return "\n".join(lines)

    @mcp.tool()
    def index_memory(source: str = "all") -> str:
        """Index Thunderbird data sources into persistent memory.
        
        Args:
            source: Which source to index (all, wing_comms, mission_board, dossier, inbox_queue)
        """
        indexer = MemoryIndexer()
        if source == "all":
            counts = indexer.index_all()
            total = sum(counts.values())
            lines = [f"Indexed {total} entries total:"]
            for src, count in counts.items():
                lines.append(f"  {src}: {count}")
            return "\n".join(lines)
        else:
            method = getattr(indexer, f"index_{source}", None)
            if method:
                count = method()
                return f"Indexed {count} entries from {source}"
            return f"Unknown source: {source}"

    @mcp.tool()
    def recall_by_context(context: str, top_k: int = 3) -> str:
        """Recall memories relevant to a given context.
        
        Args:
            context: The context to search within
            top_k: Number of results (default 3)
        """
        store = ThunderbirdMemoryStore()
        results = store.search(context, top_k=top_k)
        if not results:
            return "No relevant memories found for this context."
        
        lines = [f"Context Recall ({len(results)} memories):\n"]
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. [{r['source']}] similarity={r['similarity']:.3f}")
            lines.append(f"   {r['text'][:400]}")
            lines.append("")
        return "\n".join(lines)

    @mcp.tool()
    def memory_stats() -> str:
        """Get statistics about the persistent memory store."""
        store = ThunderbirdMemoryStore()
        stats = store.stats()
        lines = [
            "Memory Store Statistics:",
            f"  Total entries: {stats['total_entries']}",
            f"  FAISS index size: {stats['faiss_index_size']}",
            f"  Embedding dimension: {stats['embedding_dimension']}",
            "",
            "Entries by source:",
        ]
        for source, count in stats["by_source"].items():
            lines.append(f"  {source}: {count}")
        return "\n".join(lines)

    @mcp.tool()
    def add_to_memory(text: str, source: str = "manual", metadata: str = "{}") -> str:
        """Add a text entry to persistent memory.
        
        Args:
            text: The text content to store
            source: Source label (default: manual)
            metadata: JSON string with additional metadata
        """
        store = ThunderbirdMemoryStore()
        try:
            meta = json.loads(metadata) if isinstance(metadata, str) else metadata
        except Exception:
            meta = {}
        entry_id = store.add(text=text, source=source, metadata=meta)
        return f"Added memory entry: {entry_id}"


# ============================================================================
# PUBLIC API
# ============================================================================

def run_indexing_pipeline() -> Dict[str, Any]:
    """Run the full indexing pipeline"""
    indexer = MemoryIndexer()
    counts = indexer.index_all()
    store = indexer.store
    return {
        "indexed": counts,
        "total": sum(counts.values()),
        "store_stats": store.stats(),
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("Running memory indexing pipeline...")
    result = run_indexing_pipeline()
    print(f"Indexed {result['total']} entries")
    print(f"Store stats: {json.dumps(result['store_stats'], indent=2)}")
    
    # Test semantic search
    store = ThunderbirdMemoryStore()
    results = store.search("client booking status", top_k=3)
    print(f"\nSearch results for 'client booking status': {len(results)} found")
    for r in results:
        print(f"  [{r['source']}] sim={r['similarity']:.3f}: {r['text'][:100]}...")
