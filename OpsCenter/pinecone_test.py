#!/usr/bin/env python3
import os
import sys
import logging
from pinecone import Pinecone, ServerlessSpec

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# Read key from environment or fallback to what we found
pc_key = os.environ.get("PINECONE_API_KEY", "***REMOVED-SECRET***")

def test_pinecone():
    logging.info("Initializing Pinecone client...")
    try:
        pc = Pinecone(api_key=pc_key)
        
        # List indexes to see if 'quickstart' exists
        indexes = pc.list_indexes().names()
        logging.info(f"Available indexes: {indexes}")
        
        if "quickstart" not in indexes:
            logging.info("Creating 'quickstart' index (Dimension 1536 for OpenAI embeddings)...")
            pc.create_index(
                name="quickstart",
                dimension=1536,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1"
                )
            )
            logging.info("Index created.")
        
        index = pc.Index("quickstart")
        stats = index.describe_index_stats()
        logging.info(f"Index stats: {stats}")
        
        # Simple upsert test with a dummy vector
        logging.info("Testing upsert...")
        index.upsert(
            vectors=[
                {"id": "test-vec-1", "values": [0.1] * 1536, "metadata": {"test": "true", "author": "goose"}}
            ]
        )
        
        logging.info("Pinecone Vector Memory connection SUCCESSFUL.")
        
    except Exception as e:
        logging.error(f"Pinecone connection failed: {e}")

if __name__ == "__main__":
    test_pinecone()

