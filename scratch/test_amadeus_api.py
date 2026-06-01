#!/usr/bin/env python3
"""
Test Amadeus API connectivity
"""
import json
import requests
from pathlib import Path

THUNDERBIRD_DIR = Path.home() / "Thunderbird"

def load_credentials():
    """Load Amadeus API credentials from config file."""
    cred_file = THUNDERBIRD_DIR / "creds" / "amadeus_credentials.json"
    if cred_file.exists():
        with open(cred_file, encoding="utf-8") as f:
            creds = json.load(f)
        return creds.get("client_id", ""), creds.get("client_secret", "")
    return "", ""

def get_amadeus_token(client_id, client_secret):
    """Get OAuth2 token from Amadeus."""
    url = "https://test.api.amadeus.com/v1/security/oauth2/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret
    }
    
    try:
        response = requests.post(url, headers=headers, data=data, timeout=10)
        response.raise_for_status()
        token_data = response.json()
        return token_data.get("access_token"), token_data.get("expires_in", 0)
    except Exception as e:
        print(f"Error getting token: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response: {e.response.text}")
        return None, 0

def test_flight_search(access_token):
    """Test flight search API."""
    url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    params = {
        "originLocationCode": "DEN",
        "destinationLocationCode": "LAX",
        "departureDate": "2026-06-15",
        "adults": 1,
        "nonStop": "false",
        "max": 5
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        print(f"✓ Flight search successful!")
        print(f"  Found {len(data.get('data', []))} flight offers")
        return True
    except Exception as e:
        print(f"✗ Flight search failed: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"  Response: {e.response.text}")
        return False

def main():
    print("Testing Amadeus API connectivity...")
    
    # Load credentials
    client_id, client_secret = load_credentials()
    if not client_id or not client_secret:
        print("✗ Missing credentials in amadeus_credentials.json")
        return False
    
    print(f"✓ Credentials loaded (client_id: {client_id[:10]}...)")
    
    # Get token
    access_token, expires_in = get_amadeus_token(client_id, client_secret)
    if not access_token:
        print("✗ Failed to get access token")
        return False
    
    print(f"✓ Token obtained (expires in: {expires_in} seconds)")
    
    # Test flight search
    success = test_flight_search(access_token)
    
    return success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)