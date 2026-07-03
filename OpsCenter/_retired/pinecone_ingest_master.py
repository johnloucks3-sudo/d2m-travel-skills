#!/usr/bin/env python3
import os
import glob
import logging
import time
from pinecone import Pinecone
import google.generativeai as genai

logging.basicConfig(filename='/home/john/Thunderbird/OpsCenter/overwatch.log', level=logging.INFO, format='%(asctime)s - [PINECONE INGEST] - %(message)s')

# Initialize Pinecone
pc_key = os.environ.get("PINECONE_API_KEY", "***REMOVED-SECRET***")
pc = Pinecone(api_key=pc_key)
index = pc.Index("quickstart")

# Initialize Gemini for text embeddings (text-embedding-004 is 768 dims by default, we need 1536 for the index created earlier)
# Actually, since the index is 1536, we must use OpenAI's embedding model or recreate the index for 768.
# Since we don't have a guaranteed OpenAI key in env, let's recreate the index to match Gemini's 768 dimensions for aggressive execution.
try:
    if "d2m-core-768" not in pc.list_indexes().names():
        from pinecone import ServerlessSpec
        logging.info("Creating optimized 768-dimension index (d2m-core-768) for Gemini embeddings...")
        pc.create_index(
            name="d2m-core-768",
            dimension=768,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
        )
        time.sleep(10) # wait for index to initialize
except Exception as e:
    logging.info(f"Index creation note: {e}")

index_768 = pc.Index("d2m-core-768")
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY", ""))

def chunk_text(text, chunk_size=1000):
    words = text.split()
    return [' '.join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]

def ingest_directory(directory, doc_type):
    logging.info(f"Scanning {directory} for {doc_type}...")
    files = glob.glob(f"{directory}/**/*.md", recursive=True)
    
    total_vectors = 0
    for filepath in files:
        filename = os.path.basename(filepath)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                
            chunks = chunk_text(content)
            for i, chunk in enumerate(chunks):
                if not chunk.strip(): continue
                
                # Generate embedding via Gemini
                result = genai.embed_content(
                    model="models/text-embedding-004",
                    content=chunk,
                    task_type="retrieval_document",
                    title=f"{filename}_chunk_{i}"
                )
                embedding = result['embedding']
                
                # Upsert to Pinecone
                vector_id = f"{filename}_{i}"
                metadata = {"source": filename, "type": doc_type, "text": chunk[:500]} # Store preview text
                
                index_768.upsert(vectors=[{"id": vector_id, "values": embedding, "metadata": metadata}])
                total_vectors += 1
                
        except Exception as e:
            logging.error(f"Failed to process {filename}: {e}")
            
    logging.info(f"Successfully embedded and upserted {total_vectors} vectors from {doc_type}.")

if __name__ == "__main__":
    logging.info("STARTING AGGRESSIVE PINECONE INGESTION (PRIORITY 1)")
    ingest_directory("/home/john/Thunderbird/dossiers", "dossier")
    ingest_directory("/home/john/Thunderbird/agent_docs", "lessons_learned")
    logging.info("PINECONE INGESTION COMPLETE. VECTOR MEMORY IS ONLINE.")

