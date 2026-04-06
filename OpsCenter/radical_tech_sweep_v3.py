#!/usr/bin/env python3
import os
import asyncio
import google.generativeai as genai
from openai import AsyncOpenAI
import logging

logging.basicConfig(filename='/home/john/Thunderbird/OpsCenter/overwatch.log', level=logging.INFO, format='%(asctime)s - [LIVE TECH SWEEP V2] - %(message)s')

openrouter_client = AsyncOpenAI(
    api_key=os.environ.get("OPENROUTER_API_KEY", "***REMOVED-SECRET***"),
    base_url="https://openrouter.ai/api/v1"
)

groq_client = AsyncOpenAI(
    api_key=os.environ.get("GROQ_API_KEY", "***REMOVED-SECRET***"),
    base_url="https://api.groq.com/openai/v1"
)

async def a2_research():
    logging.info("A2 Dembe executing LIVE Perplexity scrape based on exact Commander specifications...")
    prompt = """
    You are Lt Col Marcus Dembe (A2). You are a World-Class AI Developer and Integrator.
    Discontinue ALL focus on travel industry, hospitality news, and client-related travel locations.
    
    Search the LIVE web strictly for the past 7 days of activity on:
    1. WORLD-WIDE technology related to AI revolutionary development.
    2. Work being done through AI Teams (Multi-Agent Orchestration).
    3. AI enabling collaboration across different corporations' models (Cross-Model Routing).
    4. Use of graphics in developing products like itineraries, proposals, and design.
    5. Newly developed or established Google Integration with AI production.
    6. Claude-Goose integration protocols.
    7. Goose and Gemini alternatives and their comparative effectiveness.
    
    Provide the raw data, URLs, and specific github repos. Do not hallucinate. Use only live web data from the last 7 days.
    """
    
    # Patched to the current live Perplexity model on OpenRouter
    response = await openrouter_client.chat.completions.create(
        model="perplexity/llama-3.1-sonar-large-128k-online",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

async def a7_audit(research_data):
    logging.info("A7 Sterling ruthlessly scoring the intel...")
    prompt = f"""
    You are Brig Gen Thomas Gauge Sterling (A7). 
    A2 Dembe has pulled this live intelligence from the last 7 days:
    {research_data}
    
    Format this into a high-level Staff Paper.
    Score and elevate solutions that are ZERO-COST or open-source. 
    Identify exactly 3 tools, repos, or frameworks we can physically install and test this week to improve Thunderbird OS.
    """
    
    response = await groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

async def run_sweep():
    try:
        raw_intel = await a2_research()
        final_report = await a7_audit(raw_intel)
        
        with open("/home/john/Thunderbird/OpsCenter/collaboration/Radical_Tech_Sweep.md", "w") as f:
            f.write(final_report)
            
        logging.info("LIVE TECH SWEEP V2 COMPLETE. File written.")
        
    except Exception as e:
        logging.error(f"Live Tech Sweep V2 Failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_sweep())

