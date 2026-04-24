#!/usr/bin/env python3
"""
Preemptive OAuth refresh — refresh token before spawning Claude if expiry is near.

If token expires within 30 minutes, refresh it using the refreshToken before
invoking claude -p. This ensures we always have a fresh token for headless invocations.

Requires: Access to ~/.claude/.credentials.json and ability to write back to it.
"""

import json
import time
import requests
from pathlib import Path
from typing import Optional, Dict

CREDS_PATH = Path.home() / ".claude" / ".credentials.json"
REFRESH_MARGIN_MS = 30 * 60 * 1000  # Refresh if within 30 min of expiry


def read_oauth_credentials() -> Optional[Dict]:
    """Read OAuth credentials from official Claude CLI storage."""
    try:
        if CREDS_PATH.exists():
            return json.loads(CREDS_PATH.read_text())
    except Exception as e:
        print(f"❌ Error reading credentials: {e}")
    return None


def is_token_expiring_soon() -> bool:
    """Check if token expires within the margin (30 minutes)."""
    creds = read_oauth_credentials()
    if not creds:
        return True  # Assume expired if we can't read
    
    token_data = creds.get("claudeAiOauth", {})
    expires_at = token_data.get("expiresAt")
    
    if not expires_at:
        return True
    
    now_ms = int(time.time() * 1000)
    time_until_expiry = expires_at - now_ms
    
    return time_until_expiry < REFRESH_MARGIN_MS


def refresh_oauth_token() -> bool:
    """Refresh the OAuth token using the refresh token.
    
    This is REVERSE-ENGINEERED based on Anthropic's OAuth flow.
    If Anthropic's endpoint changes, this will fail and we'll fall back to tier 3.
    """
    creds = read_oauth_credentials()
    if not creds:
        print("❌ Cannot refresh: no credentials found")
        return False
    
    token_data = creds.get("claudeAiOauth", {})
    refresh_token = token_data.get("refreshToken")
    
    if not refresh_token:
        print("❌ Cannot refresh: no refresh token available")
        return False
    
    # Try known Anthropic OAuth endpoints (reverse-engineered)
    endpoints = [
        "https://claude.ai/api/auth/refresh",
        "https://api.anthropic.com/oauth/token",
        "https://console.anthropic.com/v1/oauth/token",
    ]
    
    payload = {
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
    
    for endpoint in endpoints:
        try:
            print(f"[refresh] Trying endpoint: {endpoint}")
            resp = requests.post(
                endpoint,
                json=payload,
                timeout=10,
                headers={"Content-Type": "application/json"}
            )
            
            if resp.status_code == 200:
                new_data = resp.json()
                token_data["accessToken"] = new_data.get("access_token", new_data.get("accessToken"))
                token_data["expiresAt"] = new_data.get("expires_at", new_data.get("expiresAt"))
                
                creds["claudeAiOauth"] = token_data
                CREDS_PATH.write_text(json.dumps(creds, indent=2))
                
                print(f"✅ Token refreshed successfully")
                return True
            
            elif resp.status_code in [401, 403]:
                print(f"   [{resp.status_code}] Endpoint rejected refresh — trying next")
            
            elif resp.status_code == 429:
                print(f"   [429] Rate limited — backing off")
                time.sleep(5)
            
            else:
                print(f"   [{resp.status_code}] Unexpected response: {resp.text[:100]}")
        
        except requests.exceptions.Timeout:
            print(f"   Timeout — trying next endpoint")
        except Exception as e:
            print(f"   Error: {e}")
    
    print("❌ All refresh endpoints failed")
    return False


def ensure_fresh_token() -> bool:
    """Check if token needs refresh; refresh if needed. Return True if token is fresh."""
    creds = read_oauth_credentials()
    if not creds:
        print("❌ No credentials available")
        return False
    
    token_data = creds.get("claudeAiOauth", {})
    expires_at = token_data.get("expiresAt")
    
    now_ms = int(time.time() * 1000)
    time_until_expiry_min = (expires_at - now_ms) / 60000 if expires_at else -1
    
    print(f"[oauth] Token expires in {time_until_expiry_min:.1f} minutes")
    
    if time_until_expiry_min < 0:
        print(f"❌ Token already expired")
        return False
    
    if time_until_expiry_min < 30:
        print(f"⚠️ Token expiring soon — attempting refresh")
        return refresh_oauth_token()
    
    print(f"✅ Token fresh (expires in {time_until_expiry_min:.1f} min)")
    return True


if __name__ == "__main__":
    # Test/standalone usage
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "force-refresh":
        print("Forcing refresh...")
        success = refresh_oauth_token()
        sys.exit(0 if success else 1)
    else:
        success = ensure_fresh_token()
        sys.exit(0 if success else 1)

