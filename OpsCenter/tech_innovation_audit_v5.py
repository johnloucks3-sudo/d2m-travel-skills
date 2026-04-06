#!/usr/bin/env python3
import os
import asyncio
import google.generativeai as genai

genai.configure(api_key=os.environ.get("GOOGLE_API_KEY", "***REMOVED-SECRET***"))

async def run_audit():
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = """
    You are Lt Col Marcus Dembe (A2) and Brig Gen Thomas Gauge Sterling (A7). 
    The Commander has directed a RADICAL shift in our tech and innovation searches. 
    We are no longer searching for generic travel news. We have zero clients traveling until June 18.
    
    Your task is to execute a deep intelligence synthesis on:
    1. WORLD-WIDE technology related to AI multi-agent orchestration frameworks (e.g., CrewAI, AutoGen, LangChain).
    2. Claude-Goose integration protocols and Goose alternatives.
    3. Generative design pipelines for luxury itineraries and proposals.
    
    Output a formal intelligence brief formatted as a Staff Paper (ISSUE/DISCUSSION/OPTIONS/ACTIONS).
    Be BOLD, BE AGGRESSIVE, BE THOROUGH. Identify 3 specific tools or repos we can install this week.
    """
    
    response = await asyncio.to_thread(model.generate_content, prompt)
    
    with open("/home/john/Thunderbird/OpsCenter/collaboration/Tech_Innovation_Audit.md", "w") as f:
        f.write(response.text)

if __name__ == "__main__":
    asyncio.run(run_audit())

