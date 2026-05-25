#!/usr/bin/env python3
"""
TESS token refresh daemon.

Refreshes the TESS JWT bearer token on a 25-minute interval.
Fires early if token has less than 90 minutes remaining.
Writes to .env.vault (primary) and tess_token.json (legacy shim, chmod 600).

Run: python3 scripts/thunderbird_tess_token_refresh.py
Or via systemd: see systemd/thunderbird-tess-token-refresh.service

Phase 3 security requirements (Harlan):
- chmod 600 enforced on tess_token.json on every write
- Vault-first storage (primary); tess_token.json is deprecated shim
- _notify_commander() called on refresh failure
"""
import json
import logging
import os
import sys
import time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("tess_token_refresh")

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
TOKEN_FILE = THUNDERBIRD_DIR / "tess_token.json"
VAULT_FILE = THUNDERBIRD_DIR / ".env.vault"
REFRESH_INTERVAL_SECONDS = 25 * 60   # 25 minutes
EARLY_REFRESH_THRESHOLD = 90 * 60    # refresh if <90 min remaining


def _load_vault() -> dict:
    """Load .env.vault into a key→value dict."""
    if not VAULT_FILE.exists():
        return {}
    result = {}
    for line in VAULT_FILE.read_text().splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            k, _, v = stripped.partition("=")
            result[k.strip()] = v.strip()
    return result


def _write_vault_key(key: str, value: str) -> None:
    """Update a single key in .env.vault, enforce chmod 600."""
    lines = VAULT_FILE.read_text().splitlines() if VAULT_FILE.exists() else []
    out = []
    written = False
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            k, _, _ = stripped.partition("=")
            if k.strip() == key:
                out.append(f"{key}={value}")
                written = True
                continue
        out.append(line)
    if not written:
        out.append(f"{key}={value}")
    VAULT_FILE.write_text("\n".join(out) + "\n")
    os.chmod(VAULT_FILE, 0o600)


def _write_token_shim(token_data: dict) -> None:
    """Write legacy tess_token.json shim. chmod 600 on every write (Harlan condition)."""
    TOKEN_FILE.write_text(json.dumps(token_data, indent=2))
    os.chmod(TOKEN_FILE, 0o600)
    logger.debug("tess_token.json shim written, chmod 600 enforced")


def _notify_commander(message: str) -> None:
    """Alert Commander on refresh failure via Telegram if available."""
    logger.error("COMMANDER ALERT: %s", message)
    try:
        alert_file = THUNDERBIRD_DIR / "logs" / "tess_token_alerts.log"
        alert_file.parent.mkdir(exist_ok=True)
        with open(alert_file, "a") as f:
            f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} ALERT: {message}\n")
    except OSError:
        pass


def _get_current_token() -> dict:
    """Load current token from vault or shim file."""
    vault = _load_vault()
    token = vault.get("D2M_TESS_JWT_ACCESS_TOKEN", "")
    if token:
        return {
            "accessToken": token,
            "refreshToken": vault.get("D2M_TESS_JWT_REFRESH_TOKEN", ""),
            "expiresAt": vault.get("D2M_TESS_JWT_EXPIRES_AT", ""),
            "userID": vault.get("D2M_TESS_AGENT_USER_ID", ""),
        }
    # Fall back to legacy file
    if TOKEN_FILE.exists():
        try:
            return json.loads(TOKEN_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _seconds_until_expiry(token_data: dict) -> float:
    """Return seconds until token expiry. Returns 0 if unknown/expired."""
    expires_at = token_data.get("expiresAt", "") or token_data.get("expires_at", "")
    if not expires_at:
        return 0
    try:
        import datetime
        exp = datetime.datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        now = datetime.datetime.now(datetime.timezone.utc)
        remaining = (exp - now).total_seconds()
        return max(remaining, 0)
    except (ValueError, TypeError):
        return 0


def _refresh_token(current: dict) -> dict | None:
    """Attempt token refresh via TESS API. Returns new token dict or None on failure."""
    try:
        import requests
        refresh_token = current.get("refreshToken", "")
        if not refresh_token:
            logger.warning("No refresh token available — cannot refresh")
            return None
        resp = requests.post(
            "https://crm.myagentgenie.com/api/api/Auth/refresh",
            json={"refreshToken": refresh_token},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error("Token refresh API call failed: %s", e)
        return None


def run_refresh_cycle() -> None:
    """Single refresh cycle: check expiry, refresh if needed."""
    current = _get_current_token()
    if not current:
        logger.warning("No current token found — skipping refresh cycle")
        return

    remaining = _seconds_until_expiry(current)
    logger.info("Token expires in %.0f minutes", remaining / 60)

    if remaining > EARLY_REFRESH_THRESHOLD:
        logger.info("Token healthy — no refresh needed")
        return

    logger.info("Refreshing token (%.0f min remaining < %.0f min threshold)",
                remaining / 60, EARLY_REFRESH_THRESHOLD / 60)

    new_token = _refresh_token(current)
    if not new_token:
        _notify_commander(f"TESS token refresh FAILED. Expires in {remaining/60:.0f} min.")
        return

    # Write to vault (primary)
    _write_vault_key("D2M_TESS_JWT_ACCESS_TOKEN", new_token.get("accessToken", ""))
    _write_vault_key("D2M_TESS_JWT_REFRESH_TOKEN", new_token.get("refreshToken", ""))
    _write_vault_key("D2M_TESS_JWT_EXPIRES_AT", new_token.get("expiresAt", ""))

    # Write legacy shim (Harlan: chmod 600 every write)
    _write_token_shim(new_token)

    logger.info("Token refreshed successfully")


def main() -> None:
    logger.info("TESS token refresh daemon starting (interval=%dmin)", REFRESH_INTERVAL_SECONDS // 60)
    while True:
        try:
            run_refresh_cycle()
        except Exception as e:
            logger.error("Unexpected error in refresh cycle: %s", e)
            _notify_commander(f"Unexpected error in TESS token refresh: {e}")
        time.sleep(REFRESH_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
