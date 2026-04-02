#!/usr/bin/env python3
import os
import json
from pinecone import Pinecone

# A2 / WING MEMORY: Pinecone Vector Database Connector
# Targets the "quickstart" index.

def get_api_key():
    # Attempt to read from config or environment
    key = os.environ.get("PINECONE_API_KEY")
    if not key:
        # Check vault file as fallback
        vault_path = "/home/john/Thunderbird/~~DO NOT DELETE API Keys.txt"
        if os.path.exists(vault_path):
            with open(vault_path, 'r') as f:
                lines = f.readlines()
                for i, line in enumerate(lines):
                    if "━━━ PINECONE ━━━" in line:
                        # Try to find a key in the next few lines that isn't the URL
                        for j in range(1, 4):
                            if i+j < len(lines):
                                potential_key = lines[i+j].strip()
                                if len(potential_key) > 20 and "http" not in potential_key:
                                    return potential_key
    return None

def test_connection():
    api_key = get_api_key()
    
    if not api_key or "********" in api_key:
        print("ERROR: Pinecone API Key is missing or masked. Cannot connect.")
        return False
        
    try:
        print("Initializing Pinecone client...")
        pc = Pinecone(api_key=api_key)
        
        print("Connecting to 'quickstart' index...")
        index = pc.Index("quickstart")
        
        stats = index.describe_index_stats()
        print("✅ SUCCESS: Connected to Pinecone index!")
        print(f"Index Stats: {stats}")
        return True
        
    except Exception as e:
        print(f"❌ FAILED to connect: {e}")
        return False

if __name__ == "__main__":
    test_connection()

