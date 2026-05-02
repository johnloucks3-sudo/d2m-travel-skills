#!/usr/bin/env python3
"""
Travel API Connectivity Tests
Test configured services to verify they work
"""

import json
import os
from pathlib import Path
from datetime import datetime

CREDS_DIR = Path("/home/john/Thunderbird/creds")
OUTPUT_FILE = Path("/home/john/Thunderbird/output") / f"api_connectivity_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

def test_amadeus():
    """Test Amadeus Test API connectivity."""
    try:
        import requests
    except ImportError:
        return {"service": "Amadeus", "status": "SKIPPED", "reason": "requests library not installed"}

    try:
        creds = json.loads((CREDS_DIR / "amadeus_credentials.json").read_text())
        client_id = creds.get("client_id")
        client_secret = creds.get("client_secret")
        base_url = creds.get("base_url")

        if not all([client_id, client_secret, base_url]):
            return {"service": "Amadeus", "status": "INCOMPLETE", "reason": "Missing client_id, client_secret, or base_url"}

        # Try to get access token
        token_url = f"{base_url}/v1/security/oauth2/token"
        payload = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret
        }

        response = requests.post(token_url, data=payload, timeout=5)

        if response.status_code == 200:
            token_data = response.json()
            return {
                "service": "Amadeus",
                "status": "CONNECTED",
                "endpoint": base_url,
                "token_type": token_data.get("token_type"),
                "expires_in": token_data.get("expires_in")
            }
        elif response.status_code == 400:
            return {"service": "Amadeus", "status": "AUTH_ERROR", "reason": "Invalid client credentials", "error": response.text[:200]}
        else:
            return {"service": "Amadeus", "status": "ERROR", "code": response.status_code, "error": response.text[:200]}

    except Exception as e:
        return {"service": "Amadeus", "status": "ERROR", "reason": str(e)}

def test_hotelbeds():
    """Test Hotelbeds Test API connectivity."""
    try:
        import requests
    except ImportError:
        return {"service": "Hotelbeds", "status": "SKIPPED", "reason": "requests library not installed"}

    try:
        creds = json.loads((CREDS_DIR / "hotelbeds_credentials.json").read_text())
        api_key = creds.get("api_key")
        base_url = creds.get("base_url")

        if not all([api_key, base_url]):
            return {"service": "Hotelbeds", "status": "INCOMPLETE", "reason": "Missing api_key or base_url"}

        # Try a simple availability check
        endpoint = f"{base_url}/hotel-api/1.0/hotels"
        headers = {
            "X-API-Key": api_key,
            "Accept": "application/json"
        }

        # This will likely 400 without required params but validates auth
        response = requests.get(endpoint, headers=headers, timeout=5)

        if response.status_code == 400:
            # 400 expected (missing required query params) but means API is reachable and key is recognized
            return {
                "service": "Hotelbeds",
                "status": "CONNECTED",
                "endpoint": base_url,
                "note": "API reachable, auth recognized (400 expected with no params)"
            }
        elif response.status_code == 401:
            return {"service": "Hotelbeds", "status": "AUTH_ERROR", "reason": "Invalid API key"}
        elif response.status_code == 200:
            return {"service": "Hotelbeds", "status": "CONNECTED", "endpoint": base_url}
        else:
            return {"service": "Hotelbeds", "status": "ERROR", "code": response.status_code, "error": response.text[:200]}

    except Exception as e:
        return {"service": "Hotelbeds", "status": "ERROR", "reason": str(e)}

def test_centrav():
    """Check Centrav session file status."""
    session_file = Path("/home/john/Thunderbird/core/travel/data/centrav_session.json")

    if not session_file.exists():
        return {
            "service": "Centrav",
            "status": "MISSING",
            "expected_location": str(session_file),
            "action": "Copy from core/travel/data to creds/ or create new session"
        }

    try:
        session_data = json.loads(session_file.read_text())
        return {
            "service": "Centrav",
            "status": "SESSION_FILE_EXISTS",
            "location": str(session_file),
            "cookies_count": len(session_data) if isinstance(session_data, list) else 1,
            "note": "Session file exists; needs verification via authenticated request"
        }
    except Exception as e:
        return {"service": "Centrav", "status": "ERROR", "reason": str(e)}

def main():
    print("Testing Travel API Connectivity...\n")

    results = {
        "timestamp": datetime.now().isoformat(),
        "tests": []
    }

    # Run all tests
    for test_func in [test_amadeus, test_hotelbeds, test_centrav]:
        result = test_func()
        results["tests"].append(result)
        print(f"{result['service']}: {result.get('status', 'UNKNOWN')}")
        if result.get("reason"):
            print(f"  Reason: {result['reason']}")
        if result.get("error"):
            print(f"  Error: {result['error']}")
        print()

    # Write output
    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(results, indent=2))
    print(f"✅ Tests complete. Results: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
