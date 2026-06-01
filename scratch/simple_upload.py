#!/usr/bin/env python3
"""
Simple Google Drive upload using direct API calls
"""

import os
import sys
from pathlib import Path

# Add the necessary paths to find our modules
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "core"))
sys.path.insert(0, str(Path(__file__).parent / "api"))

# Set up environment
os.environ['PYTHONPATH'] = ':'.join([
    str(Path(__file__).parent),
    str(Path(__file__).parent / "core"),
    str(Path(__file__).parent / "api"),
    str(Path(__file__).parent / "core" / "travel"),
    str(Path(__file__).parent / "core" / "communication"),
    str(Path(__file__).parent / "core" / "email"),
    str(Path(__file__).parent / "core" / "mcp"),
    str(Path(__file__).parent / "core" / "ops"),
    str(Path(__file__).parent / "core" / "client"),
    str(Path(__file__).parent / "core" / "booking"),
    str(Path(__file__).parent / "core" / "ai_infra"),
    str(Path(__file__).parent / "core" / "intel"),
    str(Path(__file__).parent / "core" / "learning"),
    str(Path(__file__).parent / "core" / "scheduling"),
    str(Path(__file__).parent / "core" / "watchtower"),
    str(Path(__file__).parent / "core" / "crewai")
])

try:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google.auth.transport.requests import Request
    
    # Load credentials
    creds = None
    token_path = '/home/john/Thunderbird/creds/drive_token.json'
    
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            print("No valid credentials found")
            sys.exit(1)
    
    # Build drive service
    service = build('drive', 'v3', credentials=creds)
    
    # File metadata
    file_metadata = {
        'name': 'Thunderbird Tech Scan 2026 - Cost-Effective Alternatives.md',
        'description': 'Comprehensive analysis of 18+ free technologies to enhance Thunderbird platform performance and capabilities while maintaining $0/month budget',
        'parents': ['1aVU22PPvcKMUFtyRDDpAYhqCvWTBohR7']  # Architecture Reviews folder
    }
    
    media = MediaFileUpload('/home/john/Thunderbird/TECH_SCAN_2026.md', 
                           mimetype='text/markdown')
    
    # Upload file
    file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
    
    print(f"✅ Tech Scan uploaded successfully!")
    print(f"📄 File ID: {file['id']}")
    print(f"🔗 View link: {file['webViewLink']}")
    
except Exception as e:
    print(f"❌ Error uploading to Google Drive: {e}")
    sys.exit(1)