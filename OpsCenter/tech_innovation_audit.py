#!/usr/bin/env python3
import os
import json
import asyncio
from openai import AsyncOpenAI
import logging

logging.basicConfig(filename='/home/john/Thunderbird/OpsCenter/overwatch.log', level=logging.INFO, format='%(asctime)s - [TECH AUDIT] - %(message)s')

groq_client = AsyncOpenAI(
    api_key=os.environ.get("GROQ_API_KEY", "***REMOVED-SECRET***"),
    base_url="https://api.groq.com/openai/v1"
)

openrouter_client = AsyncOpenAI(
    api_key=os.environ.get("OPENROUTER_API_KEY", "***REMOVED-SECRET***"),
    base_url="https://openrouter.ai/api/v1"
)

async def gather_past_scans():
    logging.info("Gathering past 7 days of innovation scans...")
    try:
        with open("/home/john/Thunderbird/OpsCenter/00_COMMAND_LOG.md", "r") as f:
            lines = f.readlines()
            
        scans = []
        for line in lines:
            if "innovation_scan" in line.lower() or "tech monitor" in line.lower() or "arxiv" in line.lower():
                scans.append(line.strip())
                
        if not scans:
            return "No detailed logs found for the past 7 days, likely due to rotation or generic naming conventions."
        return "\n".join(scans[-20:])
    except Exception as e:
        return f"Could not read logs: {e}"

async def a7_audit(past_scans):
    logging.info("A7 (Groq) auditing past scans for weakness...")
    prompt = f"""
    You are Brig Gen Thomas Gauge Sterling (A7). The Commander is highly dissatisfied with our recent 'Innovation Scans' and tech monitor searches over the past 7 days.
    He believes they are weak, superficial, or not actionable for a high-end AI-driven travel agency.
    
    Here is the raw log data of our recent tech/innovation scan outputs:
    {past_scans}
    
    TASK:
    1. Ruthlessly critique the subjects and findings of these past searches. Why are they failing the Commander's standard? (e.g., Are they just generic ChatGPT updates? Are they ignoring the luxury travel integration piece?)
    2. Define exactly what a "Tier 1 Innovation Search" SHOULD look like for a firm operating at the bleeding edge of AI and luxury travel (e.g., finding niche MCP tools, advanced browser automation, or ultra-luxury personalization AI).
    3. Output 3 highly specific, aggressive search queries that A2 (Dembe) must execute immediately to find actionable tech.
    """
    
    response = await groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

async def a2_execute_new_scan(queries):
    logging.info("A2 (Perplexity) executing the new aggressive tech scan...")
    prompt = f"""
    You are Lt Col Marcus Dembe (A2). A7 Sterling has ordered an aggressive, highly specific tech innovation scan based on the Commander's dissatisfaction with generic news.
    
    Execute live web intelligence on these specific vectors defined by A7:
    {queries}
    
    Do not return generic AI news. Find open-source GitHub repos, newly released MCP (Model Context Protocol) extensions, or bleeding-edge autonomous agent frameworks (like LangChain, AutoGen, or browser-use) that can be weaponized for luxury travel itinerary generation, dynamic pricing arbitrage, or hyper-personalized client dossiers.
    Provide direct URLs, tools, and a 1-sentence assessment of how D2M can use it this week.
    """
    
    response = await openrouter_client.chat.completions.create(
        model="perplexity/llama-3-sonar-large-32k-online",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

async def run_tech_audit():
    try:
        past_scans = await gather_past_scans()
        audit_report = await a7_audit(past_scans)
        new_intel = await a2_execute_new_scan(audit_report)
        
        final_report = f"# A7 TECH & INNOVATION AUDIT\n\n## PART 1: The Critique (Groq/Sterling)\n{audit_report}\n\n---\n\n## PART 2: The New Intelligence (Perplexity/Dembe)\n{new_intel}"
        
        with open("/home/john/Thunderbird/OpsCenter/collaboration/Tech_Innovation_Audit.md", "w") as f:
            f.write(final_report)
            
        logging.info("TECH AUDIT COMPLETE. Report generated.")
        
        # Ping Telegram
        import requests
        import urllib.parse
        msg_text = "🦢 **TECH INNOVATION AUDIT COMPLETE**\n\nCommander, A7 (Sterling) agreed the past 7 days of innovation scans were superficial. He deployed Groq to rip them apart and set new standards.\n\nHe then tasked A2 (Dembe via Perplexity) to execute a highly aggressive, niche search for actual MCP/AI tools we can weaponize.\n\nThe brutal critique and the new intel are ready in OpsCenter/collaboration/Tech_Innovation_Audit.md"
        msg = urllib.parse.quote(msg_text)
        requests.get(f"https://api.telegram.org/bot***REMOVED-SECRET***/sendMessage?chat_id=7554895206&text={msg}&parse_mode=Markdown")
        
    except Exception as e:
        logging.error(f"Tech Audit Failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_tech_audit())

