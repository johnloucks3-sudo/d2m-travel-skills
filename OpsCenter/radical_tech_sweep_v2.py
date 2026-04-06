#!/usr/bin/env python3
import os
import asyncio
from openai import AsyncOpenAI
import logging
from datetime import datetime, timedelta

logging.basicConfig(filename='/home/john/Thunderbird/OpsCenter/overwatch.log', level=logging.INFO, format='%(asctime)s - [RADICAL TECH SWEEP] - %(message)s')

openrouter_client = AsyncOpenAI(
    api_key=os.environ.get("OPENROUTER_API_KEY", "***REMOVED-SECRET***"),
    base_url="https://openrouter.ai/api/v1"
)

groq_client = AsyncOpenAI(
    api_key=os.environ.get("GROQ_API_KEY", "***REMOVED-SECRET***"),
    base_url="https://api.groq.com/openai/v1"
)

async def a2_dembe_scrape():
    logging.info("A2 Dembe initiating live OpenRouter/Perplexity scrape for Radical Tech Innovation...")
    prompt = """
    You are Lt Col Marcus Dembe (A2), a World-Class AI Developer and Integrator.
    PROHIBITION: Do NOT search for travel industry news, hospitality trends, or client travel locations.
    
    Search the live web strictly for events, tools, and GitHub repos published in the LAST 7 DAYS regarding:
    1. WORLD-WIDE technology related to AI revolutionary development.
    2. Work being done through AI Teams (Multi-Agent Orchestration).
    3. AI enabling collaboration across different corporations' models.
    4. Use of graphics/generative design in developing products (proposals, itineraries).
    5. Newly developed or established Google Integration with AI production.
    6. Claude-Goose integration protocols and Goose/Gemini alternatives.
    
    Extract specific links, tool names, and code repositories. You are highly technical.
    """
    
    response = await openrouter_client.chat.completions.create(
        model="perplexity/llama-3-sonar-large-32k-online",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

async def a7_sterling_audit(raw_intel):
    logging.info("A7 Sterling (Groq) filtering and scoring the intelligence...")
    prompt = f"""
    You are Brig Gen Thomas Gauge Sterling (A7). Review the raw tech intelligence gathered by A2 Dembe:
    
    {raw_intel}
    
    Your task:
    1. Ruthlessly filter this list. Discard any fluff or generic AI news. We only want actionable tools, protocols, or frameworks we can deploy to our Thunderbird OS multi-agent architecture.
    2. Score the remaining tools. The primary metric: Zero-cost or open-source solutions drastically raise the score.
    3. Output a formal Staff Paper (ISSUE/DISCUSSION/OPTIONS/ACTIONS) detailing the top 3-4 most critical findings from the last 7 days and EXACTLY how we can integrate them into our Wing (e.g., using a new graphic tool for client proposals).
    """
    
    response = await groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

async def email_report(report_text):
    # We will save to a file first as a backup
    with open("/home/john/Thunderbird/OpsCenter/collaboration/Radical_Tech_Sweep.md", "w") as f:
        f.write(report_text)
        
    logging.info("Staff paper written. Attempting to email Commander...")
    
    # We will use the MCP bridge script to call gmail_create_draft and gmail_send_draft
    # Since the Pydantic V2 error is fixed, this should work cleanly.
    import subprocess
    import json
    
    try:
        # Create draft
        draft_cmd = [
            "/home/john/Thunderbird/mcp_bridge.sh", 
            "gmail_create_draft", 
            json.dumps({"to": "johnloucks3@gmail.com", "subject": "A-STAFF BRIEF: Radical Tech Innovation Sweep", "body": report_text})
        ]
        result = subprocess.run(draft_cmd, capture_output=True, text=True)
        data = json.loads(result.stdout)
        
        if "result" in data:
            draft_data = json.loads(data["result"])
            draft_id = draft_data.get("id") or draft_data.get("draftId")
            
            if draft_id:
                # Send draft
                send_cmd = [
                    "/home/john/Thunderbird/mcp_bridge.sh",
                    "gmail_send_draft",
                    json.dumps({"draft_id": draft_id})
                ]
                subprocess.run(send_cmd, capture_output=True)
                logging.info(f"Successfully emailed Radical Tech Sweep to johnloucks3@gmail.com (Draft ID: {draft_id})")
            else:
                logging.error("Failed to parse Draft ID from response.")
    except Exception as e:
        logging.error(f"Email failed: {e}")

async def run_sweep():
    # Commander requested NOT TOMORROW (April 3, 2026).
    # If this script runs on April 3, it should abort silently.
    now = datetime.now()
    if now.year == 2026 and now.month == 4 and now.day == 3:
        logging.info("Commander override: Skipping tech sweep for April 3, 2026.")
        return
        
    try:
        raw_intel = await a2_dembe_scrape()
        staff_paper = await a7_sterling_audit(raw_intel)
        await email_report(staff_paper)
    except Exception as e:
        logging.error(f"Sweep pipeline failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_sweep())

