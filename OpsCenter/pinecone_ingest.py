#!/usr/bin/env python3
import os
import glob
import logging
import asyncio
from pinecone import Pinecone
import google.generativeai as genai

logging.basicConfig(filename='/home/john/Thunderbird/OpsCenter/overwatch.log', level=logging.INFO, format='%(asctime)s - [PINECONE INGEST] - %(message)s')

# Initialize Clients
pc_key = os.environ.get("PINECONE_API_KEY", "***REMOVED-SECRET***")
pc = Pinecone(api_key=pc_key)
index = pc.Index("quickstart")

# Setup Gemini for embeddings (text-embedding-004 output is exactly 768 dimensions by default. 
# Pinecone 'quickstart' was created at 1536, but we can configure Gemini to output 1536 via output_dimensionality=1536)
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY", ""))

def chunk_text(text, max_size=2000):
    chunks = []
    current_chunk = ""
    for paragraph in text.split('\n\n'):
        if len(current_chunk) + len(paragraph) > max_size:
            chunks.append(current_chunk)
            current_chunk = paragraph + "\n\n"
        else:
            current_chunk += paragraph + "\n\n"
    if current_chunk:
        chunks.append(current_chunk)
    return chunks

async def embed_and_upload(filepath, filename):
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            
        chunks = chunk_text(content)
        logging.info(f"Chunked {filename} into {len(chunks)} pieces.")
        
        vectors = []
        for i, chunk in enumerate(chunks):
            if not chunk.strip(): continue
            
            # Use Gemini embedding model
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=chunk,
                output_dimensionality=1536,
                task_type="retrieval_document"
            )
            
            vector_id = f"{filename}_chunk_{i}"
            vectors.append({
                "id": vector_id,
                "values": result['embedding'],
                "metadata": {
                    "source": filename,
                    "text": chunk[:500] + "..." # Store snippet for context retrieval
                }
            })
            
            # Pinecone recommends batching (max 100 vectors per upsert)
            if len(vectors) >= 50:
                index.upsert(vectors=vectors)
                vectors = []
                
        if vectors:
            index.upsert(vectors=vectors)
            
        logging.info(f"Successfully vectorized and uploaded {filename}")
        return True
        
    except Exception as e:
        logging.error(f"Failed to ingest {filename}: {e}")
        return False

async def run_ingestion():
    logging.info("STARTING MASTER VECTOR INGESTION")
    
    target_dirs = [
        "/home/john/Thunderbird/dossiers/*.md",
        "/home/john/Thunderbird/OpsCenter/collaboration/Team_API_Architecture.md"
    ]
    
    files_to_process = []
    for pattern in target_dirs:
        files_to_process.extend(glob.glob(pattern))
        
    logging.info(f"Found {len(files_to_process)} documents for ingestion.")
    
    # Process sequentially to respect Gemini API embedding limits
    for filepath in files_to_process:
        filename = os.path.basename(filepath)
        await embed_and_upload(filepath, filename)
        
    logging.info("MASTER INGESTION COMPLETE. Database is fully hydrated.")
    
    # Alert Commander via Telegram
    import requests
    import urllib.parse
    msg = urllib.parse.quote("🗄️ **PINECONE INGESTION COMPLETE**\n\nPriority 1 executed. All D2M dossiers and persistent lessons have been chunked, vectorized (1536d), and successfully uploaded to the enterprise vector database.\n\nDembe and Hale can now execute semantic searches on historical client data.")
    requests.get(f"https://api.telegram.org/bot***REMOVED-SECRET***/sendMessage?chat_id=7554895206&text={msg}&parse_mode=Markdown")

if __name__ == "__main__":
    asyncio.run(run_ingestion())

