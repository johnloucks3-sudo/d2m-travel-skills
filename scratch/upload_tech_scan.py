#!/usr/bin/env python3
"""
Upload Thunderbird Tech Scan Report to Google Drive
"""

import sys
import json
from pathlib import Path

# Add the Thunderbird directory to Python path
sys.path.insert(0, str(Path.home() / "Thunderbird"))

from api.thunderbird_drive import drive_upload_file
import asyncio

async def main():
    # Upload the tech scan report
    local_path = "/home/john/Thunderbird/OpsCenter/collaboration/claude_outbox.md"
    name = "Thunderbird_Tech_Scan_Report_20260418.md"
    description = "Comprehensive tech scan with 17+ technologies to augment/replace Thunderbird stack"
    
    print(f"Uploading {local_path} to Google Drive as {name}")
    
    try:
        result = await drive_upload_file(local_path=local_path, name=name)
        result_data = json.loads(result)
        
        if "error" in result_data:
            print(f"❌ Upload failed: {result_data['error']}")
            return False
        
        print(f"✅ Upload successful!")
        print(f"   File ID: {result_data['uploaded']['id']}")
        print(f"   File name: {result_data['uploaded']['name']}")
        print(f"   Web view link: {result_data['uploaded']['webViewLink']}")
        print(f"   Size: {result_data['uploaded']['size']} bytes")
        
        return True
        
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)