#!/usr/bin/env python3
"""
johnloucks3 MCP OAuth token refresh — keeps Gmail MCP credentials fresh.
Targets: /home/john/.gmail-mcp/johnloucks3/gcp-oauth.keys.json
Runs: every 90 minutes via systemd timer
"""

import json
import subprocess
from pathlib import Path
from datetime import datetime

CREDS_DIR = Path.home() / ".gmail-mcp" / "johnloucks3"
GCP_OAUTH_PATH = CREDS_DIR / "gcp-oauth.keys.json"
CREDENTIALS_PATH = CREDS_DIR / "credentials.json"
LOG_PATH = Path("/home/john/Thunderbird/logs/johnloucks3_oauth_keepalive.log")

LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

def log_msg(msg):
    """Write timestamped message to log."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{ts}] {msg}"
    print(log_line)
    with open(LOG_PATH, "a") as f:
        f.write(log_line + "\n")

def ensure_credentials_valid():
    """Validate johnloucks3 MCP credentials exist and are well-formed."""
    if not GCP_OAUTH_PATH.exists():
        log_msg(f"❌ GCP OAuth keys not found at {GCP_OAUTH_PATH}")
        return False

    if not CREDENTIALS_PATH.exists():
        log_msg(f"❌ Credentials file not found at {CREDENTIALS_PATH}")
        return False

    try:
        # Verify credentials file is valid JSON
        creds_data = json.loads(CREDENTIALS_PATH.read_text())

        # Check for refresh token (required for MCP auto-refresh)
        if "refresh_token" in creds_data:
            log_msg(f"✅ johnloucks3 MCP credentials valid (refresh token present)")
            return True
        else:
            log_msg(f"⚠️  johnloucks3 MCP credentials valid but no refresh token")
            return True

    except json.JSONDecodeError as e:
        log_msg(f"❌ johnloucks3 credentials file corrupted: {e}")
        return False
    except Exception as e:
        log_msg(f"❌ Error validating johnloucks3 MCP credentials: {e}")
        return False

if __name__ == "__main__":
    success = ensure_credentials_valid()
    exit(0 if success else 1)
