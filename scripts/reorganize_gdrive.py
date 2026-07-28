#!/usr/bin/env python3
"""
REORGANIZE GOOGLE DRIVE
========================
Authority: COS Victoria Hale SES-6 | Dreams2Memories Travel
Performs separation of concerns:
- d2m (1KA_b2flnBHTYVRgl3U7erTFIv_aMH9cb) -> code, configs, briefs, SOs
- jl3 / Client (1l3WIjh2aL_fKEuDITmCIgQysfKVDNMUx) -> dossiers, outputs, templates
Moves scattered files in drive root (0AGPQl6-UOmJfUk9PVA) to correct folders.
"""

import sys
import logging
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
sys.path.insert(0, str(ROOT))

from scripts.drive_upload_robust import get_drive_service

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [GDRIVE-REORG]: %(message)s")
logger = logging.getLogger("GDriveReorg")

# Folder constants
D2M_ROOT = "1KA_b2flnBHTYVRgl3U7erTFIv_aMH9cb"
CLIENT_ROOT = "1l3WIjh2aL_fKEuDITmCIgQysfKVDNMUx"
DRIVE_ROOT = "0AGPQl6-UOmJfUk9PVA"

def get_or_create_folder(service, name, parent_id):
    """Retrieve folder ID if exists, or create a new one under parent."""
    query = f"name = '{name}' and mimeType = 'application/vnd.google-apps.folder' and '{parent_id}' in parents and trashed = false"
    results = service.files().list(
        q=query,
        fields="files(id, name)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True
    ).execute()
    files = results.get("files", [])
    if files:
        logger.info(f"Folder '{name}' already exists with ID: {files[0]['id']}")
        return files[0]["id"]
    
    # Create new folder
    metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id]
    }
    folder = service.files().create(
        body=metadata,
        fields="id",
        supportsAllDrives=True
    ).execute()
    logger.info(f"Created new folder '{name}' with ID: {folder['id']}")
    return folder["id"]

def move_file_in_drive(service, file_id, current_parent_id, new_parent_id):
    """Move file from current parent to new parent."""
    try:
        service.files().update(
            fileId=file_id,
            addParents=new_parent_id,
            removeParents=current_parent_id,
            fields="id, name, parents",
            supportsAllDrives=True
        ).execute()
        return True
    except Exception as e:
        logger.error(f"Failed to move file {file_id}: {e}")
        return False

def execute_reorg():
    service = get_drive_service()
    
    # 1. Create d2m system subfolders
    logger.info("Setting up D2M System folders...")
    d2m_folders = {
        "Standing_Orders": get_or_create_folder(service, "Standing_Orders", D2M_ROOT),
        "System_Configs": get_or_create_folder(service, "System_Configs", D2M_ROOT),
        "Daily_Brief_Logs": get_or_create_folder(service, "Daily_Brief_Logs", D2M_ROOT),
        "Systemd_Services": get_or_create_folder(service, "Systemd_Services", D2M_ROOT),
    }

    # 2. Create client/jl3 subfolders
    logger.info("Setting up Client/jl3 folders...")
    client_folders = {
        "Client_Dossiers": get_or_create_folder(service, "Client_Dossiers", CLIENT_ROOT),
        "Output_Deliverables": get_or_create_folder(service, "Output_Deliverables", CLIENT_ROOT),
        "Touchpoint_Templates": get_or_create_folder(service, "Touchpoint_Templates", CLIENT_ROOT),
        "Suspenses_Calendar": get_or_create_folder(service, "Suspenses_Calendar", CLIENT_ROOT),
    }

    # 3. Scan and move scattered files from both Shared Drive and My Drive root
    roots = [DRIVE_ROOT, "root"]
    for root_id in roots:
        logger.info(f"Scanning for scattered files in root folder: {root_id}...")
        page_token = None
        total_processed = 0
        
        while True:
            results = service.files().list(
                q=f"'{root_id}' in parents and trashed = false and mimeType != 'application/vnd.google-apps.folder'",
                fields="nextPageToken, files(id, name, mimeType)",
                pageSize=100,
                pageToken=page_token,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            
            files = results.get("files", [])
            page_token = results.get("nextPageToken")
            
            if not files:
                break
                
            logger.info(f"Found {len(files)} scattered files in {root_id} to process in this page.")
            for f in files:
                fid = f["id"]
                fname = f["name"]
                mimetype = f["mimeType"]
                
                target_folder = None
                
                # Mapping logic
                if fname.startswith("hale_chat_log_") and fname.endswith(".jsonl"):
                    target_folder = d2m_folders["Daily_Brief_Logs"]
                elif fname.endswith(".html") or fname.endswith(".pdf"):
                    target_folder = client_folders["Output_Deliverables"]
                elif fname.startswith("~EARA") or fname.startswith("EARA"):
                    target_folder = d2m_folders["System_Configs"]
                elif fname.endswith(".docx") and "template" in fname.lower():
                    target_folder = client_folders["Touchpoint_Templates"]
                elif fname.endswith(".py") or fname.endswith(".sh") or fname.endswith(".json"):
                    target_folder = d2m_folders["System_Configs"]
                elif fname.endswith(".md"):
                    if "sop" in fname.lower() or "standing_order" in fname.lower() or fname.startswith("SO_"):
                        target_folder = d2m_folders["Standing_Orders"]
                    else:
                        target_folder = d2m_folders["System_Configs"]

                if target_folder:
                    logger.info(f"Moving file: {fname} -> Target Folder ID: {target_folder}")
                    if move_file_in_drive(service, fid, root_id, target_folder):
                        logger.info(f"✓ Successfully moved {fname}")
                        total_processed += 1
                else:
                    logger.debug(f"No target folder mapped for: {fname} ({mimetype})")
                    
            if not page_token:
                break
                
        logger.info(f"Total files moved from {root_id}: {total_processed}")

    logger.info("Google Drive reorganization complete.")

if __name__ == "__main__":
    execute_reorg()
