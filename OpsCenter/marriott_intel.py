#!/usr/bin/env python3
import os
import asyncio
from openai import AsyncOpenAI
import logging

logging.basicConfig(filename='/home/john/Thunderbird/OpsCenter/overwatch.log', level=logging.INFO, format='%(asctime)s - [MARRIOTT INTEL] - %(message)s')

openrouter_client = AsyncOpenAI(
    api_key=os.environ.get("OPENROUTER_API_KEY", "***REMOVED-SECRET***"),
    base_url="https://openrouter.ai/api/v1"
)

async def run_intel():
    logging.info("A2 Dembe executing LIVE Perplexity scrape for Marriott Bayview Management...")
    prompt = """
    You are Lt Col Marcus Dembe (A2). Your objective is high-end luxury travel intelligence.
    The Commander needs the exact name and direct email address (or phone extension) for the Reservations Manager or General Manager at the **Newport Beach Marriott Bayview** (500 Bayview Cir, Newport Beach, CA 92660).
    
    Search the live web (LinkedIn, Marriott corporate directories, hospitality news, RocketReach).
    If you cannot find the exact Reservations Manager, find the General Manager, Rooms Executive, or Front Office Manager.
    Output the exact names, titles, and contact methods you find. Be precise.
    """
    
    try:
        response = await openrouter_client.chat.completions.create(
            model="perplexity/llama-3.1-sonar-large-128k-online",
            messages=[{"role": "user", "content": prompt}]
        )
        
        with open("/home/john/Thunderbird/OpsCenter/collaboration/Marriott_Bayview_Intel.md", "w") as f:
            f.write(response.choices[0].message.content)
            
        logging.info("Marriott Intel Gathered.")
    except Exception as e:
        logging.error(f"Marriott Intel Failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_intel())

