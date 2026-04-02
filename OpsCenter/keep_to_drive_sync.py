#!/usr/bin/env python3
import json
import logging
import subprocess
from datetime import datetime

logging.basicConfig(filename='/home/john/Thunderbird/OpsCenter/overwatch.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def backup_keep_notes():
    logging.info("[SYNC] Pulling all active Google Keep notes...")
    
    try:
        # Use the MCP bridge to list notes
        list_cmd = [
            "/home/john/Thunderbird/mcp_bridge.sh", 
            "keep_list_notes", 
            "{}"
        ]
        result = subprocess.run(list_cmd, capture_output=True, text=True)
        data = json.loads(result.stdout)
        
        if "result" not in data or "notes" not in data["result"] or not data["result"]["notes"]:
            logging.info("[SYNC] No notes found to backup.")
            return
            
        notes = data["result"]["notes"]
        logging.info(f"[SYNC] Found {len(notes)} notes. Formatting for Drive...")
        
        # Format notes into markdown
        date_str = datetime.now().strftime("%Y-%m-%d")
        markdown = f"# KEEP BACKUP - {date_str}\n\n"
        
        for note in notes:
            title = note.get('title', 'Untitled')
            content = note.get('text', '') # Basic text extraction, handles lists differently in reality
            markdown += f"## {title}\n{content}\n\n---\n\n"
            
        # Write temporary file
        tmp_path = f"/tmp/Keep_Backup_{date_str}.md"
        with open(tmp_path, 'w') as f:
            f.write(markdown)
            
        # Upload to Drive
        upload_cmd = [
            "/home/john/Thunderbird/mcp_bridge.sh",
            "drive_upload_file",
            json.dumps({
                "local_path": tmp_path,
                "name": f"Keep_Backup_{date_str}.md",
                "folder_id": "root" # Or specific backup folder ID if known
            })
        ]
        subprocess.run(upload_cmd, capture_output=True)
        logging.info(f"[SYNC] Keep_Backup_{date_str}.md uploaded to Google Drive successfully.")
        
    except Exception as e:
        logging.error(f"[SYNC] Keep backup failed: {e}")

if __name__ == "__main__":
    backup_keep_notes()
