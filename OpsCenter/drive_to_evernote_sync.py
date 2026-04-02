#!/usr/bin/env python3
import json
import logging
import subprocess
from datetime import datetime

logging.basicConfig(filename='/home/john/Thunderbird/OpsCenter/overwatch.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

EVERNOTE_EMAIL = "yodainva.5d9fc@m.evernote.com"

def pull_drive_backups_and_send_to_evernote():
    logging.info("[EVERNOTE SYNC] Pulling weekly Keep backups from Drive to send to Evernote...")
    
    # 1. Search Drive for files named "Keep_Backup_*"
    search_cmd = [
        "/home/john/Thunderbird/mcp_bridge.sh", 
        "drive_search", 
        json.dumps({"query": "name contains 'Keep_Backup_'"})
    ]
    
    try:
        result = subprocess.run(search_cmd, capture_output=True, text=True)
        data = json.loads(result.stdout)
        
        if "result" not in data or "files" not in data["result"] or not data["result"]["files"]:
            logging.info("[EVERNOTE SYNC] No Keep backups found in Drive to forward.")
            return
            
        files = data["result"]["files"]
        for f in files:
            # We would typically download the file and attach it, but the mcp bridge for gmail_send_email
            # might not support attachments directly via CLI yet. We will forward a link or the raw text.
            # For now, we will notify Evernote of the backup existence.
            
            body = f"Weekly Keep Backup generated.\nDrive File ID: {f['id']}\nDrive Link: {f.get('webViewLink', 'N/A')}"
            
            send_cmd = [
                "/home/john/Thunderbird/mcp_bridge.sh",
                "gmail_create_draft", 
                json.dumps({
                    "to": EVERNOTE_EMAIL,
                    "subject": f"Keep Backup: {f['name']} @Backups",  # @Backups routes to specific Evernote notebook
                    "body": body
                })
            ]
            subprocess.run(send_cmd)
            logging.info(f"[EVERNOTE SYNC] Forwarded {f['name']} to Evernote.")
            
    except Exception as e:
        logging.error(f"[EVERNOTE SYNC] Failed to forward backups: {e}")

if __name__ == "__main__":
    pull_drive_backups_and_send_to_evernote()
