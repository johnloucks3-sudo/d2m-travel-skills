#!/usr/bin/env python3
import os
import glob
import json
import asyncio
from openai import AsyncOpenAI
import logging
from datetime import datetime

logging.basicConfig(filename='/home/john/Thunderbird/OpsCenter/overwatch.log', level=logging.INFO, format='%(asctime)s - [MASTER AUDIT V3] - %(message)s')

openrouter_client = AsyncOpenAI(
    api_key=os.environ.get("OPENROUTER_API_KEY", "***REMOVED-SECRET***"),
    base_url="https://openrouter.ai/api/v1"
)

groq_client = AsyncOpenAI(
    api_key=os.environ.get("GROQ_API_KEY", ""),
    base_url="https://api.groq.com/openai/v1"
)

def gather_markdown_files():
    logging.info("Gathering all .md and init files in ~/Thunderbird and subdirectories...")
    all_md_files = []
    
    exclude_dirs = ['.venv', 'node_modules', '.git', '__pycache__', 'output', 'reverie']
    
    base_dir = "/home/john/Thunderbird"
    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for file in files:
            if file.endswith('.md') or file.endswith('init') or 'init' in file.lower():
                all_md_files.append(os.path.join(root, file))
                
    massive_context = ""
    for fpath in all_md_files:
        try:
            with open(fpath, 'r', errors='ignore') as f:
                content = f.read()
                massive_context += f"\n\n=== FILE: {fpath} ===\n{content}"
        except Exception as e:
            logging.error(f"Could not read {fpath}: {e}")
            
    return massive_context, len(all_md_files)

async def deepseek_summarize(massive_context):
    logging.info("DeepSeek V4 Pro via OpenRouter executing deep context summarization and conflict detection...")
    
    prompt = f"""
    You are Vic Harlan (A9). You are tasked with analyzing the entire Thunderbird OS documentation stack.
    You have been provided with the raw text of hundreds of Markdown and init files.
    
    TASK 1: SUMMARIZE
    Provide a master summary of the system architecture, the active personas, the communication protocols (e.g., A2A, Zero-Paste, 15s Watcher), and the operational frameworks (e.g., Kuklinski 18-month lifecycle, 99% email rule).
    If an existing master summary is found in the text, append your new findings to it rather than starting over.
    
    TASK 2: CONFLICT DETECTION
    This is the critical phase. Scan all of this documentation for inconsistencies, outdated rules, or contradictions. 
    For example, does one file say we use a 15s watcher, while another says we use a 2-minute crontab? Does one say Goose is secondary, while another says Goose is Primary?
    
    TASK 3: REMEDIES
    For every contradiction you find, propose a strict, actionable remedy to synchronize the documentation.
    
    Format the output as a clean, highly structured Markdown report.
    
    [BEGIN MASSIVE CONTEXT BLOCK]
    {massive_context[:1000000]} 
    """
    
    response = await openrouter_client.chat.completions.create(
        model="deepseek/deepseek-v4-pro",  # Using DeepSeek V4 Pro on OpenRouter for massive context
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

async def a7_groq_json_formatter(markdown_report):
    logging.info("A7 (Groq) converting summary into structured JSON format...")
    
    prompt = f"""
    Convert the following Thunderbird OS Master Audit report into a strict JSON payload.
    The JSON must have the following keys:
    - "last_updated": current date/time
    - "system_summary": string
    - "active_personas": list of objects (name, role)
    - "core_protocols": list of strings
    - "detected_conflicts": list of objects (conflict_description, proposed_remedy)
    
    Report to convert:
    {markdown_report}
    """
    
    response = await groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

async def run_master_audit():
    try:
        context, file_count = gather_markdown_files()
        
        # 1. DeepSeek generates the deep markdown analysis
        md_report = await deepseek_summarize(context)
        
        # We will write a brand new master audit file
        audit_path = "/home/john/Thunderbird/OpsCenter/collaboration/THUNDERBIRD_MASTER_AUDIT.md"
        with open(audit_path, "w") as f:
            f.write(f"# THUNDERBIRD MASTER SYSTEM AUDIT\n**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M MT')}\n**Files Scanned:** {file_count}\n\n" + md_report)
            
        # 2. A7 converts it to JSON
        json_report = await a7_groq_json_formatter(md_report)
        json_path = "/home/john/Thunderbird/OpsCenter/collaboration/THUNDERBIRD_MASTER_AUDIT.json"
        with open(json_path, "w") as f:
            f.write(json_report)
            
        logging.info("MASTER AUDIT COMPLETE. Files written.")
        
        # Ping Telegram
        import requests
        import urllib.parse
        msg_text = f"**THUNDERBIRD MASTER AUDIT COMPLETE**\n\nDeepSeek V3.1 (via OpenRouter) successfully scanned {file_count} system files. The master summary and conflict resolution report is ready.\nA7 (Groq) generated the corresponding JSON payload.\n\nFiles located at: OpsCenter/collaboration/THUNDERBIRD_MASTER_AUDIT.md"
        msg = urllib.parse.quote(msg_text)
        requests.get(f"https://api.telegram.org/bot***REMOVED-SECRET***/sendMessage?chat_id=7554895206&text={msg}&parse_mode=Markdown")
        
    except Exception as e:
        logging.error(f"Master Audit Failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_master_audit())

