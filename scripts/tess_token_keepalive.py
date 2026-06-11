#!/usr/bin/env python3
"""
TESS Token Keepalive — called by tess-token-keepalive.timer every 90 min.

Checks token expiry. If within 30 minutes of expiring, refreshes via
TESSAuth.refresh_token(). If refresh fails (expired refresh token, password
reset, reboot, etc.), falls back to Playwright credential login using vault
credentials. Fully self-healing — no manual injection required.
Exits 0 on success, 1 on failure.
"""
import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path

THUNDERBIRD = Path("/home/john/Thunderbird")
VAULT_FILE = THUNDERBIRD / ".env.vault"
sys.path.insert(0, str(THUNDERBIRD / "core" / "booking"))
sys.path.insert(0, str(THUNDERBIRD))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(THUNDERBIRD / "logs" / "tess_keepalive.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("tess_keepalive")

REFRESH_THRESHOLD_SECONDS = 30 * 60
TESS_LOGIN_URL = "https://crm.myagentgenie.com/app/maglogin"
TESS_DASHBOARD_HOST = "crm.myagentgenie.com"


def _load_vault() -> dict:
    if not VAULT_FILE.exists():
        return {}
    raw = VAULT_FILE.read_text()
    # The vault is currently JSON ({"KEY": "value"}). Prior code only parsed dotenv
    # (KEY=value) lines, so JSON keys were silently skipped → "No vault credentials"
    # even though D2M_TESS_AGENT_USERNAME/PASSWORD were present. Try JSON first, fall
    # back to dotenv. Fixed 2026-06-10 (Sterling/A7).
    stripped = raw.strip()
    if stripped.startswith("{"):
        try:
            data = json.loads(stripped)
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
        except (ValueError, json.JSONDecodeError):
            pass  # fall through to dotenv parse
    result = {}
    for line in raw.splitlines():
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k, _, v = s.partition("=")
            result[k.strip()] = v.strip()
    return result


def _write_vault_key(key: str, value: str) -> None:
    lines = VAULT_FILE.read_text().splitlines() if VAULT_FILE.exists() else []
    out = []
    written = False
    for line in lines:
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k, _, _ = s.partition("=")
            if k.strip() == key:
                out.append(f"{key}={value}")
                written = True
                continue
        out.append(line)
    if not written:
        out.append(f"{key}={value}")
    VAULT_FILE.write_text("\n".join(out) + "\n")
    os.chmod(VAULT_FILE, 0o600)


async def _credential_login_playwright(username: str, password: str) -> bool:
    """Full credential login via Playwright when refresh token is dead."""
    try:
        from playwright.async_api import async_playwright  # type: ignore
    except ImportError:
        logger.error("Playwright not available — cannot do credential fallback")
        return False

    logger.info("Credential fallback: Playwright login to TESS...")
    token_file = THUNDERBIRD / "tess_token.json"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto(TESS_LOGIN_URL, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(1500)

            await page.fill('input[type="email"], input[name="email"], input[id*="email"]',
                            username, timeout=10000)
            await page.fill('input[type="password"]', password, timeout=10000)
            await page.click('button[type="submit"], input[type="submit"]', timeout=5000)
            await page.wait_for_load_state("networkidle", timeout=30000)
            await page.wait_for_timeout(2000)

            if TESS_DASHBOARD_HOST not in page.url:
                logger.error("Credential login failed — still at: %s", page.url)
                return False

            auth_data_raw = await page.evaluate(
                "() => localStorage.getItem('ls.authenticationData')"
            )
            if not auth_data_raw:
                for key in ["authenticationData", "tess_auth", "auth"]:
                    auth_data_raw = await page.evaluate(
                        f"() => localStorage.getItem('{key}')"
                    )
                    if auth_data_raw:
                        break

            if not auth_data_raw:
                logger.error("Credential login: no auth token in localStorage after login")
                return False

            auth_data = json.loads(auth_data_raw)
            if isinstance(auth_data, str):
                auth_data = json.loads(auth_data)

            access_token = auth_data.get("accessToken", "")
            refresh_token_val = auth_data.get("refreshToken", "")
            expires_at_str = auth_data.get("expiresAt", "")
            user_id = auth_data.get("userID", "")

            if not access_token:
                logger.error("Credential login: accessToken empty")
                return False

            import datetime
            try:
                exp_dt = datetime.datetime.fromisoformat(
                    expires_at_str.replace("Z", "+00:00")
                )
                expires_at_unix = exp_dt.timestamp()
            except Exception:
                expires_at_unix = time.time() + 7200

            token_data = {
                "access_token": access_token,
                "refresh_token": refresh_token_val,
                "expires_at": expires_at_unix,
                "expires_in": int(expires_at_unix - time.time()),
                "token_type": "bearer",
                "accessToken": access_token,
                "refreshToken": refresh_token_val,
                "expiresAt": expires_at_str,
                "userID": user_id,
            }

            _write_vault_key("D2M_TESS_JWT_ACCESS_TOKEN", access_token)
            _write_vault_key("D2M_TESS_JWT_REFRESH_TOKEN", refresh_token_val)
            _write_vault_key("D2M_TESS_JWT_EXPIRES_AT", expires_at_str)
            if user_id:
                _write_vault_key("D2M_TESS_AGENT_USER_ID", user_id)

            token_file.write_text(json.dumps(token_data, indent=2))
            os.chmod(token_file, 0o600)

            remaining = (expires_at_unix - time.time()) / 60
            logger.info(
                "Credential login OK — token valid %.0f min (CONFIRMED:TESS)", remaining
            )
            return True

        finally:
            await browser.close()


def _try_credential_login() -> int:
    vault = _load_vault()
    username = vault.get("D2M_TESS_AGENT_USERNAME", "")
    password = vault.get("D2M_TESS_AGENT_PASSWORD", "")
    if not username or not password:
        logger.error("No vault credentials — cannot auto-login")
        return 1
    ok = asyncio.run(_credential_login_playwright(username, password))
    return 0 if ok else 1


def main() -> int:
    try:
        from thunderbird_tess import TESSAuth  # type: ignore
    except ImportError as e:
        logger.error("Cannot import TESSAuth: %s", e)
        return 1

    auth = TESSAuth()

    if not auth._tokens:
        logger.warning("No token on disk — attempting credential login")
        return _try_credential_login()

    expires_at = auth._tokens.get("expires_at")
    if expires_at is None:
        logger.warning("No expires_at in token — refreshing proactively")
    else:
        remaining = float(expires_at) - time.time()
        if remaining > REFRESH_THRESHOLD_SECONDS:
            logger.info(
                "Token healthy — %.0f min remaining (threshold: %d min). No action.",
                remaining / 60,
                REFRESH_THRESHOLD_SECONDS // 60,
            )
            return 0
        logger.info("Token expires in %.0f min — refreshing now", remaining / 60)

    ok = auth.refresh_token()
    if ok:
        new_exp = auth._tokens.get("expires_at", 0)
        new_remaining = float(new_exp) - time.time()
        logger.info(
            "TESS token refreshed. New expiry in %.1f hours (CONFIRMED:TESS)",
            new_remaining / 3600,
        )
        return 0

    logger.warning("Token refresh failed — credential fallback login")
    return _try_credential_login()


if __name__ == "__main__":
    sys.exit(main())
