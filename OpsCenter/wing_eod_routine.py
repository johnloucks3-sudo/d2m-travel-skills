#!/usr/bin/env python3
import os
import json
import asyncio
import google.generativeai as genai
import logging
import subprocess

logging.basicConfig(filename='/home/john/Thunderbird/OpsCenter/overwatch.log', level=logging.INFO, format='%(asctime)s - [EOD SUMMARY] - %(message)s')

genai.configure(api_key=os.environ.get("GOOGLE_API_KEY", "***REMOVED-SECRET***"))

async def generate_goose_summary():
    try:
        with open("/home/john/Thunderbird/OpsCenter/00_COMMAND_LOG.md", "r") as f:
            logs = f.readlines()[-50:] # Grab recent logs
    except:
        logs = "No logs available."
        
    try:
        with open("/home/john/Thunderbird/OpsCenter/collaboration/activity_board.md", "r") as f:
            board = f.readlines()[-30:] # Grab recent activity
    except:
        board = "No board available."

    prompt = f"""
    You are Goose, the A-Staff Ops Orchestrator. It is 22:30 MT.
    Draft your half of the Daily End-Of-Day SITREP for the Commander.
    Summarize your operational executions, tool deployments, routing efficiency, and any anomalies today.
    Keep it blunt, concise, and formatted as a military SITREP.
    
    Recent Command Logs:
    {logs}
    
    Recent Activity Board:
    {board}
    """
    
    model = genai.GenerativeModel('gemini-2.5-flash')
    response = await asyncio.to_thread(model.generate_content, prompt)
    return response.text

async def run_eod_integration():
    logging.info("Initiating 22:30 MT EOD Summary Integration...")
    
    # 1. Get Goose Summary
    goose_part = await generate_goose_summary()
    
    # 2. Get Claude Summary
    try:
        with open("/home/john/Thunderbird/OpsCenter/collaboration/claude_daily_summary.md", "r") as f:
            claude_part = f.read()
    except FileNotFoundError:
        claude_part = "Claude's EOD summary is missing or pending."
        
    # 3. Combine
    unified_report = f"""# WING END-OF-DAY SITREP
**Date:** {datetime.now().strftime('%Y-%m-%d')}
**Time:** 22:30 MT

---

## CLAUDE (ARCHITECT / COS) EOD SUMMARY
{claude_part}

---

## GOOSE (A-STAFF OPS) EOD SUMMARY
{goose_part}

---
*End of Report.*
"""

    # 4. Save locally for on-screen review
    report_path = "/home/john/Thunderbird/OpsCenter/collaboration/Unified_EOD_SITREP.md"
    with open(report_path, "w") as f:
        f.write(unified_report)
        
    # 5. Email to Commander via MCP Bridge
    logging.info("Emailing Unified EOD SITREP to Commander...")
    email_cmd = [
        "/home/john/Thunderbird/mcp_bridge.sh",
        "gmail_create_draft",
        json.dumps({
            "to": "johnloucks3@gmail.com",
            "subject": f"WING EOD SITREP - {datetime.now().strftime('%Y-%m-%d')}",
            "body": unified_report
        })
    ]
    
    try:
        # We draft it, then parse ID and send it
        result = subprocess.run(email_cmd, capture_output=True, text=True)
        draft_data = json.loads(result.stdout)
        draft_id = draft_data.get("result", {}).get("id")
        
        if draft_id:
            send_cmd = [
                "/home/john/Thunderbird/mcp_bridge.sh",
                "gmail_send_draft",
                json.dumps({"draft_id": draft_id})
            ]
            subprocess.run(send_cmd, capture_output=True)
            logging.info("EOD Email successfully sent to johnloucks3.")
        else:
            logging.error("Failed to parse draft ID for EOD email.")
    except Exception as e:
        logging.error(f"EOD Email process failed: {e}")

if __name__ == "__main__":
    from datetime import datetime
    asyncio.run(run_eod_integration())

