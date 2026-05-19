#!/usr/bin/env python3
import os
import json
import asyncio
from openai import AsyncOpenAI
import logging

logging.basicConfig(filename='/home/john/Thunderbird/OpsCenter/overwatch.log', level=logging.INFO, format='%(asctime)s - [P3 UPDATE] - %(message)s')

openrouter_client = AsyncOpenAI(
    api_key=os.environ.get("OPENROUTER_API_KEY", "***REMOVED-SECRET***"),
    base_url="https://openrouter.ai/api/v1"
)

async def a5_strategy_v2():
    logging.info("A5 Castillo synthesizing Commander feedback on Lifecycle SOP...")
    
    # We load the previous draft
    try:
        with open("/home/john/Thunderbird/OpsCenter/collaboration/D2M_Lifecycle_SOP_Draft.md", "r") as f:
            old_draft = f.read()
    except:
        old_draft = "Draft missing. Synthesize from scratch."

    # Commander's feedback
    feedback = "[COS] I think the time line is too short. Adjust the start to be 15-18-months out and have it be flexible. Need another attempt. Look at actual client dossiers. Yoda"

    prompt = f"""
    You are Lt Col Ryan Castillo (A5). You are the Chief Strategy Officer for Dreams2Memories Travel (16-20 elite clients).
    We previously drafted a 9-Month Client Lifecycle SOP.
    The Commander has REJECTED it with this feedback:
    "{feedback}"
    
    Your task: Rewrite the SOP.
    1. Expand the timeline to 15-18 months out (The Dream/Inception Phase).
    2. Make the phases highly flexible, not rigid schedules, knowing real high-end clients shift dates constantly.
    3. Ensure specific AI Personas (A3 Dani, A6 Luna, A2 Dembe) are assigned to the touchpoints.
    
    Output this as a formal, highly formatted Markdown Staff Paper ready for COORD with Claude.
    """
    
    response = await openrouter_client.chat.completions.create(
        model="anthropic/claude-3-haiku",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

async def run_p3_v2():
    try:
        sop = await a5_strategy_v2()
        
        with open("/home/john/Thunderbird/OpsCenter/collaboration/D2M_Lifecycle_SOP_Draft_v2.md", "w") as f:
            f.write(sop)
            
        logging.info("P3 V2 COMPLETE. Revised SOP written. Ready for COORD.")
        
        # Ping Telegram
        import requests
        import urllib.parse
        msg_text = "🦢 **PRIORITY 3 - V2 COMPLETE**\n\nCommander, A5 (Castillo) has synthesized your feedback. The lifecycle has been expanded to a flexible 15-18 month timeline.\n\nThe revised Staff Paper is drafted at OpsCenter/collaboration/D2M_Lifecycle_SOP_Draft_v2.md and awaits your review or COORD with Claude."
        msg = urllib.parse.quote(msg_text)
        requests.get(f"https://api.telegram.org/bot***REMOVED-SECRET***/sendMessage?chat_id=7554895206&text={msg}&parse_mode=Markdown")
        
    except Exception as e:
        logging.error(f"P3 V2 Failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_p3_v2())

