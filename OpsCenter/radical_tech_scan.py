#!/usr/bin/env python3
import os
import asyncio
from openai import AsyncOpenAI
import google.generativeai as genai
import logging
import json
import subprocess

logging.basicConfig(filename='/home/john/Thunderbird/OpsCenter/overwatch.log', level=logging.INFO, format='%(asctime)s - [TECH INNOVATION SHIFT] - %(message)s')

# Groq Client for fast web scraping triage
groq_client = AsyncOpenAI(
    api_key=os.environ.get("GROQ_API_KEY", ""),
    base_url="https://api.groq.com/openai/v1"
)

# OpenRouter for Perplexity Live Web Search (Replaces DeepSeek)
openrouter_client = AsyncOpenAI(
    api_key=os.environ.get("OPENROUTER_API_KEY", "***REMOVED-SECRET***"),
    base_url="https://openrouter.ai/api/v1"
)

# Gemini Client for synthesis and formatting
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY", "***REMOVED-SECRET***"))

async def a2_perplexity_live_search():
    logging.info("A2 Dembe initiating live web search via Perplexity for global AI tech trends...")
    prompt = """
    You are Lt Col Marcus Dembe (A2). The Commander has explicitly ordered a radical shift in our innovation scans.
    ABORT ALL SEARCHES related to travel industry news, client locations, or standard hospitality tech. We have no clients traveling until June 18.
    
    Instead, search the live web for breaking news, Github repos, HackerNews discussions, and ArXiv papers from the last 72 hours covering:
    1. Multi-Agent AI collaboration frameworks (e.g., LangChain, AutoGen, CrewAI updates).
    2. OpenCode alternatives or advanced Claude/OpenCode integrations.
    3. AI-driven generative design for proposals, dynamic PDF rendering, or visual UI agents.
    4. Advanced Google Workspace API/MCP integrations (Gmail, Calendar, Drive automation).
    
    Output detailed, highly technical findings with raw URLs. No fluff.
    """
    
    try:
        response = await openrouter_client.chat.completions.create(
            model="perplexity/llama-3-sonar-large-32k-online",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"Perplexity search failed: {e}")
        return "Live search failed."

async def a7_groq_triage(raw_data):
    logging.info("A7 Sterling triaging raw data via Groq for actionability...")
    prompt = f"""
    You are Brig Gen Thomas Gauge Sterling (A7). Review this raw intelligence from A2 Dembe:
    {raw_data}
    
    Filter out any theoretical garbage. Keep only the tools, frameworks, or updates that the Thunderbird Wing can actually download, clone, or hit via API *this week* to improve our autonomous architecture. 
    Output a ruthless 3-bullet summary.
    """
    try:
        response = await groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"Groq triage failed: {e}")
        return "Triage failed."

def email_results(content):
    logging.info("Emailing results to Commander...")
    
    body = f"Commander,\n\nPer your radical shift directive, all client/travel location searches are suspended until June. Here is tonight's Global AI & Automation Innovation Scan:\n\n{content}\n\nThe Wing"
    
    send_cmd = [
        "/home/john/Thunderbird/mcp_bridge.sh",
        "gmail_create_draft",
        json.dumps({
            "to": "johnloucks3@gmail.com",
            "subject": "THUNDERBIRD OS: Global AI Innovation Scan (Groq/Gemini Pipeline)",
            "body": body
        })
    ]
    
    subprocess.run(send_cmd, capture_output=True)

async def run_scan():
    logging.info("Starting Radical Shift Innovation Scan...")
    raw_intel = await a2_perplexity_live_search()
    actionable_intel = await a7_groq_triage(raw_intel)
    
    # We will use Gemini to do the final formatting/synthesis to test the pipeline as requested
    model = genai.GenerativeModel('gemini-2.5-pro')
    final_prompt = f"Format this intel into a highly readable, aggressive military sitrep report for the Commander. Focus heavily on AI collaboration and OpenCode alternatives:\nRaw: {raw_intel}\nTriage: {actionable_intel}"
    final_report = model.generate_content(final_prompt).text
    
    email_results(final_report)
    logging.info("Scan complete and emailed.")

if __name__ == "__main__":
    asyncio.run(run_scan())

