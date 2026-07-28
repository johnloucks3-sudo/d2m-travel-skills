#!/usr/bin/env python3
"""
SYNC HALE STATE LOGS TO GOOGLE DRIVE
=====================================
Authority: COS Victoria Hale SES-6 | Dreams2Memories Travel
Generates a readable Markdown summary of local hale*.json states
and uploads it to the d2m Daily_Brief_Logs folder.
Bypasses raw state cluttering of personal accounts.
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
sys.path.insert(0, str(ROOT))

from scripts.drive_upload_robust import get_drive_service, upload_file
from scripts.reorganize_gdrive import get_or_create_folder, D2M_ROOT

logging.basicConfig(level=logging.INFO, format="%(asctime)s [HALE-STATE-SYNC]: %(message)s")
logger = logging.getLogger("HaleStateSync")

def generate_state_md():
    logger.info("Reading local hale state json files...")
    
    # Load hale_state.json
    state_path = ROOT / "state" / "hale_state.json"
    state_data = {}
    if state_path.exists():
        try:
            state_data = json.loads(state_path.read_text())
        except Exception as e:
            logger.error(f"Error reading hale_state.json: {e}")

    # Load hale_email_ooda_state.json
    ooda_path = ROOT / "hale_email_ooda_state.json"
    ooda_data = {}
    if ooda_path.exists():
        try:
            ooda_data = json.loads(ooda_path.read_text())
        except Exception as e:
            logger.error(f"Error reading hale_email_ooda_state.json: {e}")

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    
    md = f"""# 🦅 HALE SYSTEM STATE & TELEMETRY LOG
**Generated:** {now_str}
**Authority:** COS Victoria Hale SES-6 | D2M Travel Operations

---

## ⚙️ CORE STATE VARIABLES
* **Session Active:** `{state_data.get('session_active', True)}`
* **COS Protocol Active:** `{state_data.get('cos_protocol_active', True)}`
* **Bimodal Briefing Active:** `{state_data.get('bimodal_briefing_active', True)}`
* **Last Local State Update:** `{state_data.get('last_updated', '—')}`

---

## 📧 EMAIL OODA QUEUE STATUS
* **Last Scan Timestamp:** `{ooda_data.get('timestamp', '—')}`
* **Generated At:** `{ooda_data.get('generated_at', '—')}`
* **Total Pending Review Items:** `{len(ooda_data.get('pending_review', []))}`

### Pending Review List:
"""
    
    pending_items = ooda_data.get("pending_review", [])
    if pending_items:
        for idx, item in enumerate(pending_items[:15]):
            md += f"{idx+1}. **Subject:** {item.get('subject', '—')} | **From:** {item.get('from', '—')} | **Urg:** `{item.get('urgency', 'routine')}` | **Auth:** `{item.get('authority', 'L2')}`\n"
        if len(pending_items) > 15:
            md += f"\n*...and {len(pending_items) - 15} more items in queue.*"
    else:
        md += "*Zero pending email items in queue.* ✅\n"

    # Save to local temporary path
    temp_path = ROOT / "logs" / "Hale_State_Log_Latest.md"
    temp_path.write_text(md)
    logger.info(f"Generated local state MD: {temp_path.name}")
    return temp_path

def sync_log_to_drive():
    temp_file = generate_state_md()
    
    try:
        service = get_drive_service()
        # Retrieve target Daily_Brief_Logs folder
        logger.info("Locating target Daily_Brief_Logs folder in GDrive...")
        folder_id = get_or_create_folder(service, "Daily_Brief_Logs", D2M_ROOT)
        
        now_date = datetime.now().strftime("%Y-%m-%d")
        file_name = f"Hale_State_Log_{now_date}.md"
        
        logger.info(f"Syncing daily log to GDrive folder: {file_name} -> ID {folder_id}...")
        # Check if file with same name already exists in target folder, to overwrite or update
        query = f"name = '{file_name}' and '{folder_id}' in parents and trashed = false"
        results = service.files().list(
            q=query,
            fields="files(id, name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        files = results.get("files", [])
        
        # Upload
        from googleapiclient.http import MediaFileUpload
        import mimetypes
        
        metadata = {"name": file_name, "parents": [folder_id]}
        media = MediaFileUpload(str(temp_file), mimetype="text/markdown", resumable=True)
        
        if files:
            # Update existing file
            existing_id = files[0]["id"]
            logger.info(f"Overwriting existing log file ID: {existing_id}")
            service.files().update(
                fileId=existing_id,
                media_body=media,
                supportsAllDrives=True
            ).execute()
            logger.info("✓ Sync complete (overwritten).")
        else:
            # Create new file
            uploaded = service.files().create(
                body=metadata,
                media_body=media,
                fields="id",
                supportsAllDrives=True
            ).execute()
            logger.info(f"✓ Sync complete (created new file ID: {uploaded['id']})")
            
    except Exception as e:
        logger.error(f"Failed to sync state log to Drive: {e}")

if __name__ == "__main__":
    sync_log_to_drive()
