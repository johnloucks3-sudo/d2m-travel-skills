#!/usr/bin/env python3
"""
Claude OAuth Token Refresh Daemon — Aggressive Token Maintenance
==================================================================
Runs every 20 minutes. Keeps the OAuth token perpetually fresh.
This prevents token expiry from ever blocking headless Claude operations.

Single job: refresh the token if it's within ANY risk window.
Launched by: systemd timer (historical reference — current OAuth refresh is handled by
claude-token-monitor.timer + claude-oauth-keepalive.timer, both user-level)
"""

import json
import time
import logging
import requests
from pathlib import Path
from datetime import datetime

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [TOKEN-DAEMON] - %(message)s",
    handlers=[
        logging.FileHandler("/home/john/Thunderbird/logs/token_refresh_daemon.log"),
    ],
)

CREDS_PATH = Path.home() / ".claude" / ".credentials.json"

def read_token_state():
    """Read current token state."""
    try:
        if CREDS_PATH.exists():
            creds = json.loads(CREDS_PATH.read_text())
            token_data = creds.get("claudeAiOauth", {})
            return {
                "accessToken": token_data.get("accessToken"),
                "refreshToken": token_data.get("refreshToken"),
                "expiresAt": token_data.get("expiresAt"),
            }
    except Exception as e:
        logging.error(f"Error reading credentials: {e}")
    return None

def refresh_token():
    """Refresh OAuth token using refreshToken."""
    state = read_token_state()
    if not state or not state.get("refreshToken"):
        logging.warning("No token or refresh token available")
        return False

    refresh_token = state["refreshToken"]
    endpoints = [
        "https://claude.ai/api/auth/refresh",
        "https://api.anthropic.com/oauth/token",
    ]

    for endpoint in endpoints:
        try:
            resp = requests.post(
                endpoint,
                json={"refresh_token": refresh_token, "grant_type": "refresh_token"},
                timeout=10,
                headers={"Content-Type": "application/json"}
            )

            if resp.status_code == 200:
                new_data = resp.json()
                creds = json.loads(CREDS_PATH.read_text())
                token_data = creds.get("claudeAiOauth", {})
                
                token_data["accessToken"] = new_data.get("access_token") or new_data.get("accessToken")
                token_data["expiresAt"] = new_data.get("expires_at") or new_data.get("expiresAt")
                
                creds["claudeAiOauth"] = token_data
                CREDS_PATH.write_text(json.dumps(creds, indent=2))
                
                expires_at = token_data.get("expiresAt")
                if expires_at:
                    now_ms = int(time.time() * 1000)
                    time_left_min = (expires_at - now_ms) / 60000
                    logging.info(f"✅ Token refreshed — valid for {time_left_min:.0f} minutes")
                
                return True
        except Exception:
            pass

    logging.warning("Token refresh endpoints unavailable")
    return False

def check_and_refresh():
    """Check token state and refresh if needed."""
    state = read_token_state()
    if not state:
        logging.warning("No token state found")
        return

    expires_at = state.get("expiresAt")
    if not expires_at:
        logging.warning("No expiry timestamp")
        return

    now_ms = int(time.time() * 1000)
    time_until_expiry_min = (expires_at - now_ms) / 60000

    logging.info(f"Token status: expires in {time_until_expiry_min:.1f} minutes")

    # Aggressive refresh: if within 60 minutes OR already expired, refresh
    if time_until_expiry_min < 60:
        logging.warning(f"Token expiring soon ({time_until_expiry_min:.1f} min) — refreshing NOW")
        refresh_token()
    else:
        logging.info(f"Token healthy ({time_until_expiry_min:.1f} min remaining)")

if __name__ == "__main__":
    logging.info("=" * 70)
    logging.info("Claude OAuth Token Refresh Daemon Started")
    logging.info("=" * 70)
    
    check_and_refresh()
    
    logging.info("Daemon cycle complete")

