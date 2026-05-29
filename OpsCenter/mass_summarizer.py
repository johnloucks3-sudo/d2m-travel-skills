#!/usr/bin/env python3
import os
import glob
import json
import asyncio
import google.generativeai as genai
from datetime import datetime
import logging

logging.basicConfig(filename='/home/john/Thunderbird/OpsCenter/overwatch.log', level=logging.INFO, format='%(asctime)s - [MASS SUMMARY] - %(message)s')
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY", ""))

async def summarize_chunk(files, chunk_name):
    logging.info(f"Summarizing chunk: {chunk_name} ({len(files)} files)")
    combined_text = ""
    for fpath in files:
        try:
            with open(fpath, 'r', errors='ignore') as f:
                content = f.read()
                # Grab top 100 lines to prevent context overflow per file
                lines = content.split('\n')[:100]
                combined_text += f"\n\n--- FILE: {os.path.basename(fpath)} ---\n" + "\n".join(lines)
        except Exception as e:
            logging.error(f"Could not read {fpath}: {e}")
            
    model = genai.GenerativeModel('gemini-2.5-flash')
    prompt = f"""
    You are A7 (Gauge Sterling). The Commander requested a massive summary of all active .md and init files in the Thunderbird Wing.
    Here is a chunk of files from the {chunk_name} directory.
    Extract the core rules, operational parameters, active itineraries, and system states.
    Ignore standard boilerplate. Focus on actionable intelligence, hard rules, and architecture.
    
    RAW DATA:
    {combined_text[:60000]} # Cap input at 60k chars to ensure speed and safety
    """
    
    response = await asyncio.to_thread(model.generate_content, prompt)
    return {
        "directory": chunk_name,
        "files_scanned": len(files),
        "summary": response.text
    }

async def run_master_summary():
    logging.info("STARTING WING MASTER SUMMARY GENERATION")
    
    # Target directories
    dirs = {
        "Root_and_Docs": glob.glob("/home/john/Thunderbird/*.md") + glob.glob("/home/john/Thunderbird/docs/*.md"),
        "OpsCenter": glob.glob("/home/john/Thunderbird/OpsCenter/*.md") + glob.glob("/home/john/Thunderbird/OpsCenter/collaboration/*.md"),
        "Personas_and_Agents": glob.glob("/home/john/Thunderbird/Personas/*.md") + glob.glob("/home/john/Thunderbird/agent_docs/*.md"),
        "Dossiers": glob.glob("/home/john/Thunderbird/dossiers/*.md")
    }
    
    master_results = []
    for name, files in dirs.items():
        if files:
            res = await summarize_chunk(files, name)
            master_results.append(res)
            
    # 1. Output to JSON
    json_path = "/home/john/Thunderbird/OpsCenter_Master_Summary_2026.json"
    with open(json_path, "w") as f:
        json.dump(master_results, f, indent=2)
        
    # 2. Append to the existing OpsCenter_KnowledgeBase.md
    md_path = "/home/john/Thunderbird/OpsCenter_KnowledgeBase.md"
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M MT')
    
    append_text = f"\n\n## [UPDATE: {timestamp}] MASSIVE DIRECTORY SUMMARY (A7 SCAN)\n"
    for r in master_results:
        append_text += f"\n### {r['directory']} ({r['files_scanned']} files)\n{r['summary']}\n"
        
    with open(md_path, "a") as f:
        f.write(append_text)
        
    logging.info("MASTER SUMMARY COMPLETE. JSON and MD updated.")

if __name__ == "__main__":
    asyncio.run(run_master_summary())

