#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, "/home/john/Thunderbird")
from scripts.drive_upload_robust import get_drive_service

def check_root():
    service = get_drive_service()
    
    # List files directly in 'root' (My Drive)
    results = service.files().list(
        q="'root' in parents and trashed = false",
        fields="files(id, name, mimeType)",
        pageSize=100
    ).execute()
    files = results.get("files", [])
    print(f"Found {len(files)} files in 'root' (My Drive):")
    for f in files:
        print(f"  Name: {f['name']} | ID: {f['id']} | MimeType: {f['mimeType']}")

if __name__ == "__main__":
    check_root()
