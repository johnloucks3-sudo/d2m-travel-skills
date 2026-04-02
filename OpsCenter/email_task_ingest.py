#!/usr/bin/env python3
import json
import logging
import subprocess
from datetime import datetime
import os

logging.basicConfig(filename='/home/john/Thunderbird/OpsCenter/overwatch.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# We look for the raw name in the subject, or the first word of the body.
# We include both the bracketed version and the raw version to be robust.
VALID_TRIGGERS = [
    "COS", "[COS]", 
    "A2", "[A2]", "DEMBE", 
    "A3", "[A3]", "DANI", 
    "A5", "[A5]", "VIPER", "CASTILLO",
    "A6", "[A6]", "LUNA",
    "A7", "[A7]", "GAUGE", "STERLING",
    "A9", "[A9]", "HARLAN",
    "A12", "[A12]", "ELON",
    "PADRE", "[PADRE]"
]

def check_for_tasks():
    logging.info("[EMAIL INGEST] Polling d2mconcierge for Commander tasking...")
    search_cmd = [
        "/home/john/Thunderbird/mcp_bridge.sh", 
        "gmail_search_messages", 
        json.dumps({"query": "from:johnloucks3@gmail.com is:unread OR from:d2mconcierge@gmail.com is:unread", "max_results": 10})
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
        body = msg_data.get("body", "").strip().upper()
        first_word = body.split()[0] if body else ""
        
        assigned_persona = None
        
        # Check subject or first word
        for trigger in VALID_TRIGGERS:
            # We enforce strict boundaries so we don't accidentally trigger on random words
            # like "cost" containing "COS".
            if f"[{trigger}]" in subject or f" {trigger} " in f" {subject} " or first_word == trigger or first_word == f"[{trigger}]":
                assigned_persona = trigger.replace("[", "").replace("]", "")
                break
                
        if assigned_persona:
            logging.info(f"[EMAIL INGEST] Task detected for {assigned_persona} in msg {msg_id}")
            route_task(assigned_persona, msg_data.get("subject", ""), msg_data.get("body", ""), msg_id)
        else:
            # We don't mark read if it's not a task, so the Commander can still read it natively
            logging.info(f"[EMAIL INGEST] No trigger found in msg {msg_id}")
            
    except Exception as e:
        logging.error(f"[EMAIL INGEST] Failed to process {msg_id}: {e}")

def route_task(persona, subject, body, msg_id):
    task_json = {
        "task_id": f"EMAIL_{msg_id}",
        "source": "EMAIL",
        "assigned_to": persona,
        "subject": subject,
        "body": body,
        "timestamp": datetime.now().isoformat()
    }
    
    queue_path = "/home/john/Thunderbird/OpsCenter/01_TASK_QUEUE.json"
    try:
        with open(queue_path, 'r') as f:
            queue = json.load(f)
    except:
        queue = []
        
    queue.append(task_json)
    with open(queue_path, 'w') as f:
        json.dump(queue, f, indent=2)
        
    send_receipt(persona, subject)
    mark_read(msg_id)

def send_receipt(persona, subject):
    logging.info(f"[EMAIL INGEST] Sending receipt for {persona}")
    body = f"Thank you, Yoda. \n\nThe {persona} persona has received your task regarding '{subject}' and is actively processing it. We will reply to this thread or output to the OpsCenter upon completion.\n\nThe Wing"
    
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

def mark_read(msg_id):
    # To actually remove UNREAD, we'd use gmail_modify_message {"addLabelIds": [], "removeLabelIds": ["UNREAD"]}
    # Currently waiting on bridge confirmation for modification tools.
    pass

if __name__ == "__main__":
    check_for_tasks()

