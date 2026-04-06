#!/usr/bin/env python3
import os
import asyncio
from openai import AsyncOpenAI
import logging

logging.basicConfig(filename='/home/john/Thunderbird/OpsCenter/overwatch.log', level=logging.INFO, format='%(asctime)s - [LIVE TECH SWEEP] - %(message)s')

openrouter_client = AsyncOpenAI(
    api_key=os.environ.get("OPENROUTER_API_KEY", "***REMOVED-SECRET***"),
    base_url="https://openrouter.ai/api/v1"
)

async def run_live_sweep():
    logging.info("A2 Dembe executing LIVE Perplexity scrape based on exact Commander specifications...")
    
    prompt = """
    You are a world-class AI developer and integrator.
    
    CRITICAL PROHIBITION: Discontinue ALL focus on the travel industry, hospitality news, or client-related travel locations. We have zero clients traveling until June 18.
    
    Your task is to execute a live intelligence synthesis strictly focusing on happenings from the PAST 7 DAYS regarding the following exact topics:
    
    1. WORLD-WIDE technology related to AI revolutionary development.
    2. Work being done through AI Teams (Multi-Agent Orchestration).
    3. AI enabling collaboration across different corporations' models.
    4. Use of graphics in developing products like itineraries and proposals.
    5. Newly developed or established Google Integration with AI production.
    6. Claude-Goose integration protocols.
    7. Goose and Gemini alternatives and how effective they are.
    
    SCORING METRIC: Solutions that have "Zero cost" raise the score and must be highlighted.
    
    Do not deviate from these exact search parameters. Output a formal, brutal, highly actionable intelligence brief. Give specific tool names, URLs, and a 1-sentence deployment thesis for each finding.
    """
    
    response = await openrouter_client.chat.completions.create(
        model="perplexity/llama-3-sonar-large-32k-online",
        messages=[{"role": "user", "content": prompt}]
    )
    
    with open("/home/john/Thunderbird/OpsCenter/collaboration/Live_Tech_Sweep_Results.md", "w") as f:
        f.write(response.choices[0].message.content)
        
    logging.info("LIVE TECH SWEEP COMPLETE.")

if __name__ == "__main__":
    asyncio.run(run_live_sweep())

