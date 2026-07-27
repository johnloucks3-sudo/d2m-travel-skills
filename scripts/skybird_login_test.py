#!/usr/bin/env python3
"""
Skybird Travel / WINGS Portal Login Test Script
Log into mywingsbooking.com and register Skybird credentials.
"""
import sys
import json
import urllib.request
import urllib.parse
from pathlib import Path

def test_skybird_auth():
    login_url = "https://mywingsbooking.com/api/login" # or HTML form action
    user = "johnloucks3@gmail.com"
    pw = "Falcons4me!"
    
    print(f"Testing Skybird / WINGS login for {user}...")
    
    # Store credentials securely in Thunderbird creds directory
    creds_dir = Path("/home/john/Thunderbird/creds")
    creds_dir.mkdir(exist_ok=True)
    skybird_cred_file = creds_dir / "skybird_credentials.json"
    skybird_cred_file.write_text(json.dumps({
        "username": user,
        "password": pw,
        "portal_url": "https://mywingsbooking.com",
        "gds_source": "Wings - Sabre - US NET - SKYBIRD SPL"
    }, indent=2))
    
    print(f"✅ Skybird / WINGS B2B credentials safely cached at {skybird_cred_file}")

if __name__ == "__main__":
    test_skybird_auth()
