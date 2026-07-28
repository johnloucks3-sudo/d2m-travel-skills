#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, "/home/john/Thunderbird")
from scripts.drive_upload_robust import get_drive_service

def list_all_folders():
    service = get_drive_service()
    # List all folders on the drive
    results = service.files().list(
        q="mimeType = 'application/vnd.google-apps.folder' and trashed = false",
        fields="files(id, name, parents)",
        pageSize=100,
        supportsAllDrives=True,
        includeItemsFromAllDrives=True
    ).execute()
    files = results.get("files", [])
    print(f"Found {len(files)} folders:")
    for f in files:
        parents = f.get("parents", [])
        print(f"  Folder Name: {f['name']} | ID: {f['id']} | Parents: {parents}")

if __name__ == "__main__":
    list_all_folders()
