#!/usr/bin/env python3
import os
import asyncio
from openai import AsyncOpenAI
import logging

logging.basicConfig(filename='/home/john/Thunderbird/OpsCenter/overwatch.log', level=logging.INFO, format='%(asctime)s - [MARRIOTT INTEL V2] - %(message)s')

openrouter_client = AsyncOpenAI(
    api_key=os.environ.get("OPENROUTER_API_KEY", "***REMOVED-SECRET***"),
    base_url="https://openrouter.ai/api/v1"
)

async def a2_research():
    logging.info("A2 Dembe executing LIVE Perplexity scrape for Marriott Bayview Management...")
    prompt = """
    You are Lt Col Marcus Dembe (A2). 
    I need the direct contact information for the Marriott Bayview hotel in Newport Beach, CA (500 Bayview Cir).
    Specifically, search the live web for the name and direct email address of the current Reservations Manager, Front Office Manager, or General Manager.
    If the exact email is hidden, provide the exact naming convention for Marriott emails and the names of the managers so we can construct it (e.g., firstname.lastname@marriott.com).
    Output only the actionable contact data. Do not hallucinate.
    """
    
    response = await openrouter_client.chat.completions.create(
        model="perplexity/llama-3.1-sonar-huge-128k-online", 
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

async def run_intel():
    try:
        raw_intel = await a2_research()
        
        with open("/home/john/Thunderbird/OpsCenter/collaboration/Marriott_Bayview_Intel.md", "w") as f:
            f.write(raw_intel)
            
        logging.info("MARRIOTT INTEL V2 COMPLETE. File written.")
        
    except Exception as e:
        logging.error(f"Marriott Intel Failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_intel())

