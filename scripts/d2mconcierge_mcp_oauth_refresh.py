"""
d2mconcierge MCP OAuth token refresh — keeps d2mconcierge Gmail credentials fresh.

Two targets:
  1. ~/.gmail-mcp/d2mconcierge/credentials.json  — MCP server creds (validate only)
  2. config/persona_gmail_token.json              — gmail_create_draft_sync token (active refresh)

Runs: every 90 minutes via systemd d2mconcierge-oauth-keepalive.timer
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

MCP_CREDS_DIR = Path.home() / ".gmail-mcp" / "d2mconcierge"
MCP_CREDENTIALS_PATH = MCP_CREDS_DIR / "credentials.json"
PERSONA_TOKEN_PATH = Path("/home/john/Thunderbird/config/persona_gmail_token.json")
LOG_PATH = Path("/home/john/Thunderbird/logs/d2mconcierge_oauth_keepalive.log")

LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


def log_msg(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{ts}] {msg}"
    print(log_line)
    with open(LOG_PATH, "a") as f:
        f.write(log_line + "\n")


def validate_mcp_credentials() -> bool:
    """Validate d2mconcierge MCP credentials exist and have refresh_token."""
    if not MCP_CREDENTIALS_PATH.exists():
        log_msg(f"❌ MCP credentials not found at {MCP_CREDENTIALS_PATH}")
        return False
    try:
        data = json.loads(MCP_CREDENTIALS_PATH.read_text())
        if "refresh_token" in data:
            log_msg("✅ d2mconcierge MCP credentials valid (refresh token present)")
            return True
        log_msg("⚠️  d2mconcierge MCP credentials exist but no refresh token")
        return True
    except Exception as e:
        log_msg(f"❌ Error reading MCP credentials: {e}")
        return False


def refresh_persona_token() -> bool:
    """Actively refresh config/persona_gmail_token.json using google-auth."""
    if not PERSONA_TOKEN_PATH.exists():
        log_msg(f"❌ Persona token not found at {PERSONA_TOKEN_PATH}")
        return False
    try:
        data = json.loads(PERSONA_TOKEN_PATH.read_text())
        creds = Credentials(
            token=data.get("token"),
            refresh_token=data["refresh_token"],
            token_uri=data["token_uri"],
            client_id=data["client_id"],
            client_secret=data["client_secret"],
            scopes=data["scopes"],
        )

        expiry_str = data.get("expiry", "")
        if expiry_str:
            expiry_dt = datetime.fromisoformat(expiry_str.replace("Z", "+00:00"))
            # google-auth writes expiry as a NAIVE ISO string (no Z/offset). The .replace()
            # above is then a no-op and fromisoformat returns a naive datetime. Subtracting it
            # from an aware now_utc raised TypeError → exit 1 every other run. Force UTC tzinfo
            # when naive so the comparison is always aware-vs-aware. Fixed 2026-06-10 (Sterling/A7).
            if expiry_dt.tzinfo is None:
                expiry_dt = expiry_dt.replace(tzinfo=timezone.utc)
            now_utc = datetime.now(timezone.utc)
            mins_left = (expiry_dt - now_utc).total_seconds() / 60
            if mins_left > 30:
                log_msg(f"✅ Persona token fresh — {mins_left:.0f} min remaining, skipping refresh")
                return True

        creds.refresh(Request())

        updated = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": list(creds.scopes) if creds.scopes else data["scopes"],
            "universe_domain": data.get("universe_domain", "googleapis.com"),
            "account": data.get("account", ""),
            "expiry": creds.expiry.isoformat() if creds.expiry else None,
        }
        PERSONA_TOKEN_PATH.write_text(json.dumps(updated, indent=2))
        log_msg(f"✅ Persona token refreshed — expires {creds.expiry}")
        return True

    except Exception as e:
        log_msg(f"❌ Persona token refresh failed: {e}")
        return False


if __name__ == "__main__":
    ok_mcp = validate_mcp_credentials()
    ok_persona = refresh_persona_token()
    exit(0 if (ok_mcp and ok_persona) else 1)
