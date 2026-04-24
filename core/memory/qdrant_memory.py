#!/usr/bin/env python3
"""
Thunderbird Semantic Memory — Qdrant vector search over Claude Code memory files.

Provides:
  - embed_all_memories()    — bulk index all .md files from memory dir
  - embed_new_memory(path)  — index/re-index a single memory file
  - search_memories(query)  — semantic search, returns top-k results

CLI:
  python3 qdrant_memory.py embed-all
  python3 qdrant_memory.py search "Westbrook Silver Nova itinerary"
  python3 qdrant_memory.py embed-file /path/to/file.md
"""

import argparse
import glob
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

MEMORY_DIR = Path(
    os.environ.get(
        "THUNDERBIRD_MEMORY_DIR",
        os.path.expanduser(
            "~/.claude/projects/-home-john-Thunderbird/memory"
        ),
    )
)
ENV_FILE = Path(
    os.environ.get(
        "THUNDERBIRD_ENV",
        os.path.expanduser("~/Thunderbird/.env"),
    )
)
COLLECTION = "thunderbird_memories"
# FastEmbed local model — no API key, no cost, runs on CPU
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
VECTOR_SIZE = 384  # bge-small-en-v1.5 output dimension
QDRANT_HOST = os.environ.get("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", "6333"))

# Chunking — target 400 tokens with 50-token overlap.
# Without tiktoken we approximate: 1 token ~ 0.75 words → 400 tokens ~ 300 words.
CHUNK_WORDS = 300
OVERLAP_WORDS = 38  # ~50 tokens

# Embedding batch size (OpenAI accepts lists)
EMBED_BATCH = 80

# Deterministic UUID namespace
_NS = uuid.UUID("a3b2c1d0-e5f6-4a7b-8c9d-0e1f2a3b4c5d")


def _point_id(filepath: str, chunk_index: int) -> str:
    """Deterministic UUID5 from filepath + chunk_index — safe for re-indexing."""
    return str(uuid.uuid5(_NS, f"{filepath}:{chunk_index}"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_env():
    """Load .env for any optional settings. No API key required — using local FastEmbed."""
    load_dotenv(ENV_FILE)


def _chunk_text(text: str) -> list[str]:
    """Split text into overlapping word-based chunks (~400 tokens each)."""
    words = text.split()
    if len(words) <= CHUNK_WORDS:
        return [text]

    chunks = []
    start = 0
    while start < len(words):
        end = start + CHUNK_WORDS
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        if end >= len(words):
            break
        start = end - OVERLAP_WORDS
    return chunks


def _estimate_tokens(texts: list[str]) -> int:
    """Rough token count: words / 0.75."""
    total_words = sum(len(t.split()) for t in texts)
    return int(total_words / 0.75)


# ---------------------------------------------------------------------------
# QdrantMemorySystem
# ---------------------------------------------------------------------------

class QdrantMemorySystem:
    """Semantic memory backed by Qdrant + FastEmbed local embeddings (zero API cost)."""

    def __init__(self):
        _load_env()
        self._embedder = TextEmbedding(model_name=EMBEDDING_MODEL)
        self.qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        self._ensure_collection()

    # -- Collection setup ---------------------------------------------------

    def _ensure_collection(self):
        """Create the collection if it doesn't exist (idempotent)."""
        try:
            self.qdrant.get_collection(COLLECTION)
        except (UnexpectedResponse, Exception):
            self.qdrant.create_collection(
                collection_name=COLLECTION,
                vectors_config=VectorParams(
                    size=VECTOR_SIZE,
                    distance=Distance.COSINE,
                ),
            )

    # -- Embedding ----------------------------------------------------------

    def _embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts via FastEmbed (local, zero API cost). Returns list of vectors."""
        embeddings = list(self._embedder.embed(texts))
        return [e.tolist() for e in embeddings]

    # -- Bulk index ---------------------------------------------------------

    def embed_all_memories(self, memory_dir: Path | None = None) -> dict:
        """Read all .md files, chunk, embed, upsert. Returns stats dict."""
        mem_dir = memory_dir or MEMORY_DIR
        files = sorted(glob.glob(str(mem_dir / "*.md")))
        if not files:
            return {"files": 0, "chunks": 0, "tokens_est": 0}

        all_chunks: list[dict] = []  # {id, filepath, filename, content, chunk_index}
        for fpath in files:
            text = Path(fpath).read_text(errors="replace").strip()
            if not text:
                continue
            filename = Path(fpath).name
            chunks = _chunk_text(text)
            for i, chunk in enumerate(chunks):
                all_chunks.append(
                    {
                        "id": _point_id(fpath, i),
                        "filepath": fpath,
                        "filename": filename,
                        "content": chunk,
                        "chunk_index": i,
                    }
                )

        if not all_chunks:
            return {"files": 0, "chunks": 0, "tokens_est": 0}

        # Batch embed
        texts = [c["content"] for c in all_chunks]
        token_est = _estimate_tokens(texts)
        vectors: list[list[float]] = []
        for i in range(0, len(texts), EMBED_BATCH):
            batch = texts[i : i + EMBED_BATCH]
            vectors.extend(self._embed_texts(batch))

        # Build points
        now = datetime.now(timezone.utc).isoformat()
        points = []
        for chunk_meta, vec in zip(all_chunks, vectors):
            points.append(
                PointStruct(
                    id=chunk_meta["id"],
                    vector=vec,
                    payload={
                        "filename": chunk_meta["filename"],
                        "filepath": chunk_meta["filepath"],
                        "content": chunk_meta["content"],
                        "chunk_index": chunk_meta["chunk_index"],
                        "created_at": now,
                    },
                )
            )

        # Upsert in batches of 100
        for i in range(0, len(points), 100):
            self.qdrant.upsert(
                collection_name=COLLECTION,
                points=points[i : i + 100],
            )

        cost_est = token_est * 0.02 / 1_000_000
        return {
            "files": len(files),
            "chunks": len(all_chunks),
            "tokens_est": token_est,
            "cost_est_usd": round(cost_est, 6),
        }

    # -- Single file index --------------------------------------------------

    def embed_new_memory(self, filepath: str) -> dict:
        """Embed (or re-embed) a single memory file. Cleans stale chunks."""
        fpath = os.path.abspath(filepath)
        text = Path(fpath).read_text(errors="replace").strip()
        filename = Path(fpath).name

        # Delete old points for this filepath
        self.qdrant.delete(
            collection_name=COLLECTION,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="filepath",
                        match=MatchValue(value=fpath),
                    )
                ]
            ),
        )

        if not text:
            return {"filepath": fpath, "chunks": 0}

        chunks = _chunk_text(text)
        texts = [c for c in chunks]
        vectors = self._embed_texts(texts)

        now = datetime.now(timezone.utc).isoformat()
        points = []
        for i, (chunk, vec) in enumerate(zip(chunks, vectors)):
            points.append(
                PointStruct(
                    id=_point_id(fpath, i),
                    vector=vec,
                    payload={
                        "filename": filename,
                        "filepath": fpath,
                        "content": chunk,
                        "chunk_index": i,
                        "created_at": now,
                    },
                )
            )

        self.qdrant.upsert(collection_name=COLLECTION, points=points)
        return {"filepath": fpath, "chunks": len(chunks)}

    # -- Search -------------------------------------------------------------

    def embed_directory(self, directory: str, glob_pattern: str = "**/*.md") -> dict:
        """Embed all matching files from any directory (e.g. dossiers, intel).

        Usage:
            mem.embed_directory("~/Thunderbird/dossiers")
            mem.embed_directory("~/Thunderbird/intel")
        """
        import glob as glob_mod
        base = Path(directory).expanduser()
        files = sorted(base.glob(glob_pattern))
        if not files:
            return {"directory": str(base), "files": 0, "chunks": 0}

        total_chunks = 0
        for fpath in files:
            result = self.embed_new_memory(str(fpath))
            total_chunks += result.get("chunks", 0)

        return {"directory": str(base), "files": len(files), "chunks": total_chunks}

    def rag_query(
        self,
        query: str,
        top_k: int = 5,
        ollama_model: str = "phi3:mini",
        ollama_timeout: int = 90,
    ) -> dict:
        """Retrieval-Augmented Generation: search Qdrant, generate answer via Ollama.

        Zero cost: FastEmbed (local) for retrieval + Ollama (local) for generation.

        Returns:
            {
                "answer": str,
                "sources": list[{filename, score, excerpt}],
                "retrieved_chunks": int,
                "source": "qdrant+ollama",
            }
        """
        import sys, os
        sys.path.insert(0, str(Path.home() / "Thunderbird"))
        from core.ai_infra.thunderbird_ollama_client import OllamaClient, OllamaUnavailableError

        # Step 1: Retrieve relevant chunks
        hits = self.search_memories(query, top_k=top_k)
        if not hits:
            return {
                "answer": "No relevant context found in memory.",
                "sources": [],
                "retrieved_chunks": 0,
                "source": "qdrant+ollama",
            }

        # Step 2: Build context block
        context_parts = []
        for h in hits:
            context_parts.append(
                f"[{h['filename']} score={h['score']}]\n{h['content']}"
            )
        context = "\n\n---\n\n".join(context_parts)

        # Step 3: Generate answer via Ollama
        system = (
            "You are Hale, Chief of Staff for Dreams2Memories Travel. "
            "Answer the question using ONLY the provided context. "
            "Be concise and factual. If the context doesn't contain the answer, say so."
        )
        prompt = f"Context:\n{context}\n\nQuestion: {query}\n\nAnswer:"

        try:
            client = OllamaClient(model=ollama_model, timeout=ollama_timeout)
            result = client.generate(prompt, system=system, max_tokens=400, temperature=0.1)
            answer = result["text"]
        except OllamaUnavailableError:
            # Fallback: return top hit content directly
            answer = f"[Ollama unavailable — top match from {hits[0]['filename']}]\n{hits[0]['content']}"

        return {
            "answer": answer,
            "sources": [
                {"filename": h["filename"], "score": h["score"], "excerpt": h["content"][:150]}
                for h in hits
            ],
            "retrieved_chunks": len(hits),
            "source": "qdrant+ollama",
        }

    def search_memories(
        self, query: str, top_k: int = 5
    ) -> list[dict]:
        """Semantic search. Returns list of {filename, filepath, score, content}."""
        q_vec = self._embed_texts([query])[0]
        results = self.qdrant.query_points(
            collection_name=COLLECTION,
            query=q_vec,
            limit=top_k,
        ).points
        out = []
        for hit in results:
            payload = hit.payload or {}
            out.append(
                {
                    "filename": payload.get("filename", ""),
                    "filepath": payload.get("filepath", ""),
                    "score": round(hit.score, 4),
                    "chunk_index": payload.get("chunk_index", 0),
                    "content": payload.get("content", "")[:500],
                }
            )
        return out


# ---------------------------------------------------------------------------
# MCP Tool Registration
# ---------------------------------------------------------------------------

def register_qdrant_memory_tools(mcp) -> None:
    """Register Qdrant semantic memory tools with a FastMCP server instance."""

    @mcp.tool(
        name="memory_search",
        annotations={"title": "Semantic Memory Search (Qdrant)", "readOnlyHint": True},
    )
    async def memory_search(
        query: str,
        top_k: int = 5,
    ) -> str:
        """Search Thunderbird memory files using semantic (vector) search.

        Finds the most relevant memory entries for a query — client context,
        standing orders, staff decisions, project history. Returns ranked
        chunks with source file, relevance score, and content excerpt.
        """
        import json
        mem = QdrantMemorySystem()
        results = mem.search_memories(query, top_k=top_k)
        return json.dumps({"query": query, "results": results}, indent=2)

    @mcp.tool(
        name="memory_embed_all",
        annotations={"title": "Re-index All Memory Files (Qdrant)", "readOnlyHint": False},
    )
    async def memory_embed_all() -> str:
        """Bulk re-index all Thunderbird memory .md files into Qdrant.

        Reads ~/.claude/projects/-home-john-Thunderbird/memory/*.md,
        chunks, embeds via FastEmbed (local, zero API cost), and upserts.
        Run after adding or updating memory files.
        Returns file count, chunk count, and timing.
        """
        import json, time
        mem = QdrantMemorySystem()
        t0 = time.time()
        stats = mem.embed_all_memories()
        stats["elapsed_s"] = round(time.time() - t0, 1)
        return json.dumps({"status": "ok", **stats}, indent=2)

    @mcp.tool(
        name="memory_embed_file",
        annotations={"title": "Re-index Single Memory File (Qdrant)", "readOnlyHint": False},
    )
    async def memory_embed_file(filepath: str) -> str:
        """Re-index a single memory file into Qdrant (replaces stale chunks).

        Pass the absolute path to the .md file to re-embed.
        Use after writing or updating a specific memory file.
        """
        import json
        mem = QdrantMemorySystem()
        stats = mem.embed_new_memory(filepath)
        return json.dumps({"status": "ok", **stats}, indent=2)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Thunderbird Semantic Memory")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("embed-all", help="Index all memory .md files")

    p_search = sub.add_parser("search", help="Semantic search")
    p_search.add_argument("query", type=str)
    p_search.add_argument("--top-k", type=int, default=5)

    p_file = sub.add_parser("embed-file", help="Index a single file")
    p_file.add_argument("filepath", type=str)

    args = parser.parse_args()

    if args.command == "embed-all":
        mem = QdrantMemorySystem()
        t0 = time.time()
        stats = mem.embed_all_memories()
        elapsed = time.time() - t0
        print(f"Indexed {stats['files']} files -> {stats['chunks']} chunks")
        print(f"Estimated tokens: {stats['tokens_est']:,}")
        print(f"Estimated cost: ${stats.get('cost_est_usd', 0):.6f}")
        print(f"Elapsed: {elapsed:.1f}s")

    elif args.command == "search":
        mem = QdrantMemorySystem()
        results = mem.search_memories(args.query, top_k=args.top_k)
        if not results:
            print("No results found.")
            return
        for i, r in enumerate(results, 1):
            print(f"\n--- Result {i} (score: {r['score']}) ---")
            print(f"File: {r['filename']}")
            print(f"Path: {r['filepath']}")
            print(f"Chunk: {r['chunk_index']}")
            print(f"Content:\n{r['content']}")

    elif args.command == "embed-file":
        mem = QdrantMemorySystem()
        stats = mem.embed_new_memory(args.filepath)
        print(f"Indexed {stats['filepath']} -> {stats['chunks']} chunks")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
