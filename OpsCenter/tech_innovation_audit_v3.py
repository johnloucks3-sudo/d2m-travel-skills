#!/usr/bin/env python3
import os
import json
import asyncio
from openai import AsyncOpenAI
import google.generativeai as genai
import logging

logging.basicConfig(filename='/home/john/Thunderbird/OpsCenter/overwatch.log', level=logging.INFO, format='%(asctime)s - [TECH AUDIT V3] - %(message)s')

# We will just use Gemini directly for the entire workflow to avoid any OpenRouter/Groq async auth failures that might be silently crashing the script.
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY", "***REMOVED-SECRET***"))

async def gather_past_scans():
    try:
        with open("/home/john/Thunderbird/OpsCenter/00_COMMAND_LOG.md", "r") as f:
            lines = f.readlines()
        scans = [line.strip() for line in lines[-1000:] if "innovation" in line.lower() or "tech" in line.lower()]
        return "\n".join(scans[-10:]) if scans else "No detailed logs found."
    except Exception as e:
        return f"Could not read logs: {e}"

async def run_tech_audit():
    try:
        past_scans = await gather_past_scans()
        logging.info("A7 (Gemini) auditing past scans...")
        
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        prompt_audit = f"""
        You are Brig Gen Thomas Gauge Sterling (A7). The Commander is highly dissatisfied with our recent 'Innovation Scans' over the past 7 days.
        He believes they are weak and not actionable for a high-end AI-driven travel agency.
        
        Raw log data: {past_scans}
        
        TASK 1: Critique these searches. Why are they failing?
        TASK 2: Output 3 highly specific, aggressive search queries that A2 (Dembe) must execute immediately to find actionable tech (e.g. MCP frameworks, autonomous travel agents).
        """
        
        audit_response = await asyncio.to_thread(model.generate_content, prompt_audit)
        audit_report = audit_response.text
        
        logging.info("A2 (Gemini) executing new intel sweep...")
        
        prompt_recon = f"""
        You are Lt Col Marcus Dembe (A2). Execute intelligence synthesis on these specific vectors defined by A7:
        {audit_report}
        
        Do not return generic AI news. Identify bleeding-edge autonomous agent frameworks (LangChain, browser-use) or tools that can be weaponized for luxury travel itinerary generation or dynamic pricing arbitrage. Provide a 1-sentence assessment of how D2M can use it this week.
        """
        
        recon_response = await asyncio.to_thread(model.generate_content, prompt_recon)
        new_intel = recon_response.text
        
        final_report = f"# A7 TECH & INNOVATION AUDIT (V3)\n\n## PART 1: The Critique (Sterling)\n{audit_report}\n\n---\n\n## PART 2: The New Intelligence (Dembe)\n{new_intel}"
        
        with open("/home/john/Thunderbird/OpsCenter/collaboration/Tech_Innovation_Audit.md", "w") as f:
            f.write(final_report)
            
        logging.info("TECH AUDIT V3 COMPLETE.")
        
    except Exception as e:
        logging.error(f"Tech Audit V3 Failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_tech_audit())

