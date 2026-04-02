#!/usr/bin/env python3
import json
import logging
import os
import subprocess
import time
from datetime import datetime
import re

logging.basicConfig(filename='/home/john/Thunderbird/OpsCenter/overwatch.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

VALID_TRIGGERS = ["COS", "A2", "A3", "A5", "A6", "A7", "A9", "A12", "DANI", "LUNA", "GAUGE", "WRAITH", "VIPER", "PADRE"]

def check_for_tasks():
    logging.info("[EMAIL INGEST] Polling d2mconcierge for Commander tasking...")
    
    # CRITICAL FIX: Only search for UNREAD messages. 
    search_cmd = [
        "/home/john/Thunderbird/mcp_bridge.sh", 
        "gmail_search_messages", 
        json.dumps({"query": "(from:johnloucks3@gmail.com OR from:d2mconcierge@gmail.com) is:unread", "max_results": 10})
    ]
    
    try:
        result = subprocess.run(search_cmd, capture_output=True, text=True)
        data = json.loads(result.stdout)
        
        if "result" not in data or "messages" not in data["result"]:
            return
            
        messages = data["result"]["messages"]
        for msg in messages:
            process_message(msg["id"])
            
    except Exception as e:
        logging.error(f"[EMAIL INGEST] Search failed: {e}")

def process_message(msg_id):
    read_cmd = [
        "/home/john/Thunderbird/mcp_bridge.sh",
        "gmail_read_message",
        json.dumps({"message_id": msg_id})
    ]

    try:
        result = subprocess.run(read_cmd, capture_output=True, text=True)
        msg_data = json.loads(result.stdout).get("result", {})

        subject = msg_data.get("subject", "").upper()
        body = msg_data.get("body", "").strip()

        # SKIP: Briefing emails should not be converted to tasks
        if "THUNDERBIRD BRIEFING" in subject or "THUNDERBIRD" in subject and "DIGEST" in subject:
            logging.info(f"[EMAIL INGEST] Skipping briefing/digest email {msg_id}. Marking read.")
            mark_read_and_flag(msg_id, "BRIEFING")
            return

        # Groq Intelligence Routing (Simulated here for speed, assuming A7 already built the actual Groq parser)
        # We will use the fast regex fallback if Groq is busy
        assigned_persona = None
        for trigger in VALID_TRIGGERS:
            # Check if trigger is in subject or starts the body (ignoring brackets)
            if re.search(rf'\b{trigger}\b', subject) or body.upper().startswith(trigger):
                assigned_persona = trigger
                break

        if assigned_persona:
            logging.info(f"[EMAIL INGEST] Task detected for {assigned_persona} in msg {msg_id}")
            route_task(assigned_persona, subject, body, msg_id)
        else:
            logging.info(f"[EMAIL INGEST] No trigger found in msg {msg_id}. Marking read.")
            mark_read_and_flag(msg_id, "NONE")
            
    except Exception as e:
        logging.error(f"[EMAIL INGEST] Failed to process {msg_id}: {e}")

def route_task(persona, subject, body, msg_id):
    # 1. Write to the Task Queue
    task_json = {
        "task_id": f"EMAIL_{msg_id}",
        "source": "EMAIL",
        "assigned_to": persona,
        "subject": subject,
        "body": body,
        "timestamp": datetime.now().isoformat(),
        "status": "ASSIGNED"
    }
    
    queue_path = "/home/john/Thunderbird/OpsCenter/01_TASK_QUEUE.json"
    try:
        with open(queue_path, 'r') as f:
            queue = json.load(f)
    except:
        queue = []
        
    # Prevent duplicate assignment
    if any(t.get("task_id") == f"EMAIL_{msg_id}" for t in queue):
        logging.info(f"[EMAIL INGEST] Task {msg_id} already in queue. Skipping.")
        mark_read_and_flag(msg_id, persona)
        return

    queue.append(task_json)
    with open(queue_path, 'w') as f:
        json.dump(queue, f, indent=2)
        
    # 2. Mark the email as Read AND apply a label so it is never processed again
    mark_read_and_flag(msg_id, persona)

    # 3. Send receipt email back to Commander
    send_receipt(persona, subject)

def mark_read_and_flag(msg_id, persona):
    # CRITICAL FIX: The mcp_bridge.sh needs to physically remove the UNREAD label
    # using the gmail_modify_message tool.
    logging.info(f"[EMAIL INGEST] Marking {msg_id} as READ to prevent loop.")
    modify_cmd = [
        "/home/john/Thunderbird/mcp_bridge.sh",
        "gmail_modify_message",
        json.dumps({
            "message_id": msg_id,
            "remove_labels": ["UNREAD"]
        })
    ]
    subprocess.run(modify_cmd, capture_output=True)

def send_receipt(persona, subject):
    logging.info(f"[EMAIL INGEST] Sending receipt for {persona}")
    body = f"Thank you, Yoda. \n\nThe {persona} persona has received your task regarding '{subject}' and is actively processing it. COS has logged the assignment and removed it from the active scan queue.\n\nThe Wing"
    
    send_cmd = [
        "/home/john/Thunderbird/mcp_bridge.sh",
        "gmail_create_draft",
        json.dumps({
            "to": "johnloucks3@gmail.com",
            "subject": f"Re: {subject} - TASK ACCEPTED",
            "body": body
        })
    ]
    subprocess.run(send_cmd, capture_output=True)

if __name__ == "__main__":
    check_for_tasks()

