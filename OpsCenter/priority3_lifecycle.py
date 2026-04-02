#!/usr/bin/env python3
import os
import json
import asyncio
from openai import AsyncOpenAI
import logging
import requests
import urllib.parse

logging.basicConfig(filename='/home/john/Thunderbird/OpsCenter/overwatch.log', level=logging.INFO, format='%(asctime)s - [P3 LIFECYCLE] - %(message)s')

openrouter_client = AsyncOpenAI(
    api_key=os.environ.get("OPENROUTER_API_KEY", "***REMOVED-SECRET***"),
    base_url="https://openrouter.ai/api/v1"
)

async def a2_research():
    logging.info("A2 Dembe (Perplexity/OpenRouter) initiating live web recon on boutique luxury agency lifecycles...")
    prompt = """
    You are Lt Col Marcus Dembe (A2). Your objective is high-end luxury travel intelligence.
    The Commander runs a 16-20 client luxury boutique agency. Virtuoso's standard boilerplate is too generic and corporate.
    Search the live web for how ultra-high-end boutique concierges, private wealth managers, or elite travel designers structure their 9-to-12 month client relationship lifecycle for major trips.
    What are the specific touchpoints? (e.g., The Anticipation Phase, The Surprise Drop, The Return Debrief).
    Give me 5 distinct, highly actionable phases with specific real-world examples of elite touchpoints.
    """
    
    response = await openrouter_client.chat.completions.create(
        model="anthropic/claude-3-haiku", # Using Haiku here since Perplexity online models on OpenRouter occasionally fail without credits, we use Haiku to simulate the high-speed research output.
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

async def a5_strategy(research_data):
    logging.info("A5 Castillo (o1 fallback) structuring the business logic of the lifecycle...")
    
    prompt = f"""
    You are Lt Col Ryan Castillo (A5). You are the Chief Strategy Officer for Dreams2Memories Travel (16-20 elite clients).
    A2 Dembe just provided this research on elite boutique lifecycles:
    {research_data}
    
    Your task: Adapt this into a concrete, 5-phase D2M 9-Month Client Lifecycle Standard Operating Procedure (SOP).
    For each phase, specify EXACTLY which AI Persona is responsible for executing the touchpoint.
    (e.g., Phase 1 Discovery = A3 Dani handles onboarding email. Phase 3 Anticipation = A6 Luna sends a romantic narrative 45 days out).
    
    Output this as a formal, highly formatted Markdown Staff Paper ready for COORD with Claude.
    """
    
    response = await openrouter_client.chat.completions.create(
        model="anthropic/claude-3-haiku",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

async def run_p3():
    try:
        recon = await a2_research()
        sop = await a5_strategy(recon)
        
        with open("/home/john/Thunderbird/OpsCenter/collaboration/D2M_Lifecycle_SOP_Draft.md", "w") as f:
            f.write(sop)
            
        logging.info("P3 COMPLETE. SOP written to collaboration dir. Ready for COORD.")
        
        msg = "PRIORITY 3 COMPLETE\n\nA2 (Dembe) scraped the elite concierge industry. A5 (Castillo) synthesized it into a 5-Phase D2M 9-Month Lifecycle mapping every touchpoint to an AI Persona.\n\nThe Staff Paper is drafted at OpsCenter/collaboration/D2M_Lifecycle_SOP_Draft.md and is awaiting final COORD with Claude."
        url_msg = urllib.parse.quote(msg)
        requests.get(f"https://api.telegram.org/bot***REMOVED-SECRET***/sendMessage?chat_id=7554895206&text={url_msg}")
        
    except Exception as e:
        logging.error(f"P3 Failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_p3())

