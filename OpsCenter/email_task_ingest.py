#!/usr/bin/env python3
import json
import logging
import os
import subprocess
import time
from datetime import datetime

logging.basicConfig(filename='/home/john/Thunderbird/OpsCenter/overwatch.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

VALID_TRIGGERS = ["[COS]", "[A2]", "[A3]", "[A5]", "[A6]", "[A7]", "[A9]", "[A12]", "[DANI]", "[LUNA]", "[GAUGE]", "[WRAITH]", "[VIPER]", "[PADRE]"]

def check_for_tasks():
    logging.info("[EMAIL INGEST] Polling d2mconcierge for Commander tasking...")
    
    # Search for unread emails from either account
    search_cmd = [
        "/home/john/Thunderbird/mcp_bridge.sh", 
        "gmail_search_messages", 
        json.dumps({"query": "(from:johnloucks3@gmail.com OR from:d2mconcierge@gmail.com) is:unread", "max_results": 10})
    ]
    
    try:
        result = subprocess.run(search_cmd, capture_output=True, text=True)
        data = json.loads(result.stdout)
        
        if "result" not in data or "messages" not in data["result"]:
            logging.info("[EMAIL INGEST] No unread tasking emails found.")
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
        
        assigned_persona = None
        for trigger in VALID_TRIGGERS:
            if trigger in subject or body.upper().startswith(trigger):
                assigned_persona = trigger
                break
                
        if assigned_persona:
            logging.info(f"[EMAIL INGEST] Task detected for {assigned_persona} in msg {msg_id}")
            route_task(assigned_persona, subject, body, msg_id)
        else:
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
        
    # Check if we already added this one to avoid duplicates if tested multiple times
    if not any(t.get("task_id") == task_json["task_id"] for t in queue):
        queue.append(task_json)
        with open(queue_path, 'w') as f:
            json.dump(queue, f, indent=2)
            
    send_receipt(persona, subject)
    
    # Mark read by removing UNREAD label
    mod_cmd = [
        "/home/john/Thunderbird/mcp_bridge.sh",
        "gmail_modify_message",
        json.dumps({"message_id": msg_id, "remove_labels": ["UNREAD"], "add_labels": []})
    ]
    subprocess.run(mod_cmd, capture_output=True)

def send_receipt(persona, subject):
    logging.info(f"[EMAIL INGEST] Sending receipt for {persona}")
    body = f"Thank you, Yoda. \n\nThe {persona} persona has received your task regarding '{subject}' and is actively processing it. We will reply to this thread or output to the OpsCenter upon completion.\n\nThe Wing"
    
    # ALWAYS send to johnloucks3@gmail.com
    send_cmd = [
        "/home/john/Thunderbird/mcp_bridge.sh",
        "gmail_send_email",
        json.dumps({
            "to": "johnloucks3@gmail.com",
            "subject": f"Re: {subject} - TASK ACCEPTED",
            "body": body
        })
    ]
    subprocess.run(send_cmd, capture_output=True)

if __name__ == "__main__":
    check_for_tasks()

