#!/usr/bin/env python3
"""CI probe: qdrant-memory — tests the CAPABILITY, not server liveness.

The probe this replaced was `curl http://localhost:6333/collections/thunderbird_memories`
— it only proved Qdrant was up and a collection with that name existed. It
NEVER exercised the actual embed→store→query path the MCP qdrant-find/store
tool uses. Result (2026-07-04): the MCP tool was completely broken (named
vs unnamed vector mismatch) while this probe reported GREEN every single
day, because the collection it checked was never the one that broke.

This probe does the real thing: embeds a throwaway string, upserts it into
the collection the MCP tool actually uses, queries it back, and fails loudly
if any step errors or the round trip doesn't return the point just written.
Cleans up after itself. Exit 0 = GREEN, 1 = RED.
"""
import sys
import time
import uuid

QDRANT_URL = "http://127.0.0.1:6333"
MCP_COLLECTION = "thunderbird_memories_mcp"
VECTOR_NAME = "fast-all-minilm-l6-v2"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def main() -> int:
    try:
        from qdrant_client import QdrantClient, models
        from fastembed import TextEmbedding
    except ImportError as e:
        print(f"RED: probe dependencies missing ({e}) — cannot verify capability")
        return 1

    probe_id = str(uuid.uuid4())
    probe_text = f"__ci_probe__ {probe_id} {time.time()}"

    try:
        client = QdrantClient(url=QDRANT_URL, timeout=10)
        model = TextEmbedding(EMBED_MODEL)

        if not client.collection_exists(MCP_COLLECTION):
            print(f"RED: collection '{MCP_COLLECTION}' does not exist")
            return 1

        vec = list(model.passage_embed([probe_text]))[0].tolist()
        client.upsert(
            collection_name=MCP_COLLECTION,
            points=[models.PointStruct(
                id=probe_id, vector={VECTOR_NAME: vec},
                payload={"document": probe_text, "ci_probe": True},
            )],
        )

        query_vec = list(model.query_embed([probe_text]))[0].tolist()
        results = client.query_points(
            collection_name=MCP_COLLECTION, query=query_vec,
            using=VECTOR_NAME, limit=1,
        ).points

        client.delete(
            collection_name=MCP_COLLECTION,
            points_selector=models.PointIdsList(points=[probe_id]),
        )

        if not results or str(results[0].id) != probe_id:
            print("RED: store succeeded but query did not return the probe point — round trip broken")
            return 1

        print(f"GREEN: embed→store→query round trip verified against {MCP_COLLECTION}")
        return 0

    except Exception as e:
        print(f"RED: capability round trip failed — {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
