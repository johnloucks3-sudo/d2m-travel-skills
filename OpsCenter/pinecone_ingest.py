#!/usr/bin/env python3
import os
import json
import logging
from pathlib import Path
from pinecone import Pinecone
from openai import OpenAI
import hashlib

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

openai_key = os.environ.get("OPENAI_API_KEY")
pc_key = os.environ.get("PINECONE_API_KEY", "***REMOVED-SECRET***")

def chunk_text(text, chunk_size=1000):
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size):
        chunks.append(" ".join(words[i:i+chunk_size]))
    return chunks

def ingest_dossiers():
    if not openai_key:
        logging.error("OpenAI API key required for embeddings.")
        return
        
    pc = Pinecone(api_key=pc_key)
    index = pc.Index("quickstart")
    client = OpenAI(api_key=openai_key)
    
    dossier_dir = Path("/home/john/Thunderbird/dossiers")
    files_processed = 0
    
    logging.info("Starting Pinecone Ingestion of Dossiers...")
    
    for file_path in dossier_dir.glob("*.md"):
        logging.info(f"Processing: {file_path.name}")
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        chunks = chunk_text(content)
        vectors = []
        
        for i, chunk in enumerate(chunks):
            # Generate embedding
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=chunk
            )
            embedding = response.data[0].embedding
            
            # Create unique ID for chunk
            chunk_id = hashlib.md5(f"{file_path.name}_{i}".encode()).hexdigest()
            
            vectors.append({
                "id": chunk_id,
                "values": embedding,
                "metadata": {
                    "source": file_path.name,
                    "chunk_index": i,
                    "text_snippet": chunk[:200] + "..."
                }
            })
            
        # Upsert in batches
        if vectors:
            index.upsert(vectors=vectors)
            files_processed += 1
            
    logging.info(f"Ingestion complete. {files_processed} dossiers vectorized and stored in Pinecone.")

if __name__ == "__main__":
    ingest_dossiers()

