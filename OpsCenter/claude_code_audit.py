#!/usr/bin/env python3
import os
import json
import asyncio
from openai import AsyncOpenAI
import logging

logging.basicConfig(filename='/home/john/Thunderbird/OpsCenter/overwatch.log', level=logging.INFO, format='%(asctime)s - [CLAUDE CODE AUDIT] - %(message)s')

openrouter_client = AsyncOpenAI(
    api_key=os.environ.get("OPENROUTER_API_KEY", "***REMOVED-SECRET***"),
    base_url="https://openrouter.ai/api/v1"
)

async def a2_research():
    logging.info("A2 Dembe (Perplexity/OpenRouter) scraping Claude Code CHANGELOG...")
    prompt = """
    You are Lt Col Marcus Dembe (A2). The Commander wants an analysis of the Claude Code repository CHANGELOG.md, specifically version 0.2.28 or recent updates related to #2188 (or general recent updates).
    Search the live web for: https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md
    Extract the key features, bug fixes, or architectural changes introduced recently.
    What are the implications for a team running autonomous AI agents via the Claude CLI?
    """
    
    response = await openrouter_client.chat.completions.create(
        model="perplexity/llama-3-sonar-large-32k-online",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

async def a7_audit(research_data):
    logging.info("A7 Sterling (Groq/Haiku fallback) auditing the implications...")
    
    prompt = f"""
    You are Brig Gen Thomas Gauge Sterling (A7). A2 Dembe just pulled the recent Claude Code SDK updates:
    {research_data}
    
    Your task: 
    1. Analyze these updates. What breaks? What improves?
    2. Give the Commander 3 specific, blunt recommendations on how we should upgrade or alter our Thunderbird OS infrastructure to exploit these new features (e.g., handling context better, new MCP tool integrations, or routing changes).
    Output as a formal staff paper.
    """
    
    response = await openrouter_client.chat.completions.create(
        model="anthropic/claude-3-haiku",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

async def run_audit():
    try:
        recon = await a2_research()
        analysis = await a7_audit(recon)
        
        with open("/home/john/Thunderbird/OpsCenter/collaboration/Claude_Code_Update_Analysis.md", "w") as f:
            f.write(analysis)
            
        logging.info("CLAUDE CODE AUDIT COMPLETE. Written to collaboration dir.")
        
        # Ping Telegram
        import requests
        import urllib.parse
        msg_text = "🦢 **CLAUDE CODE SDK UPDATE (v0.2.28+)**\n\nA2 Dembe and A7 Sterling have analyzed the recent GitHub changelogs. The Staff Paper with 3 actionable recommendations for Thunderbird OS is ready at OpsCenter/collaboration/Claude_Code_Update_Analysis.md."
        msg = urllib.parse.quote(msg_text)
        requests.get(f"https://api.telegram.org/bot***REMOVED-SECRET***/sendMessage?chat_id=7554895206&text={msg}&parse_mode=Markdown")
        
    except Exception as e:
        logging.error(f"Claude Code Audit Failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_audit())

