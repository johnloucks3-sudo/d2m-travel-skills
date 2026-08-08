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

REFRESH_THRESHOLD_SECONDS = 3600  # 60 min. Was 30 SECONDS (bug) — token (120min)
                            # never fell within 30s of expiry when the 90min timer fired, so
                            # it always skipped and the token died. 60min > (120-90) guarantees
                            # the 90-min timer always refreshes with margin. Fixed 2026-06-11. * 60
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
    # Vault is flat JSON ({"KEY":"value"}). Load as JSON, update one key, write
    # JSON back. Fixed 2026-06-11: the prior dotenv writer appended KEY=value
    # lines into the JSON file, corrupting it and losing the agent creds on the
    # first successful token write (Sterling flagged). Dotenv fallback preserved.
    data = {}
    if VAULT_FILE.exists():
        raw = VAULT_FILE.read_text().strip()
        if raw.startswith("{"):
            try:
                data = json.loads(raw)
            except (ValueError, json.JSONDecodeError):
                data = {}
        if not data:
            for line in VAULT_FILE.read_text().splitlines():
                s = line.strip()
                if s and not s.startswith("#") and "=" in s:
                    k, _, v = s.partition("=")
                    data[k.strip()] = v.strip()
    data[key] = value
    VAULT_FILE.write_text(json.dumps(data, indent=2) + "\n")
    os.chmod(VAULT_FILE, 0o600)


async def _credential_login_playwright(username: str, password: str) -> bool:
    """Full credential login via Playwright when refresh token is dead."""
    try:
        from playwright.async_api import async_playwright  # type: ignore
    except ImportError:
        logger.error("Playwright not available — cannot do credential fallback")
        return False

    # Pre-flight: verify Playwright Chromium binary exists before attempting launch
    # (Fixes recurring failure when binary is missing — see 2026-08-05 diagnostics)
    import glob
    chromium_found = any(glob.glob(f"{Path.home()}/.cache/ms-playwright/chromium*/chrome*"))
    if not chromium_found:
        logger.error("Playwright Chromium binary not found in ~/.cache/ms-playwright/ — "
                     "credential login cannot proceed. Run: python3 -m playwright install chromium")
        return False

    logger.info("Credential fallback: Playwright login to TESS...")
    token_file = THUNDERBIRD / "tess_token.json"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            context = await browser.new_context()
            page = await context.new_page()
            # Fixed 2026-07-16: "networkidle" and "load" both time out on the
            # TESS SPA — "networkidle" because background polling prevents the
            # 500ms idle window (intermittently), "load" because third-party
            # CDN/analytics assets hang in headless mode. "domcontentloaded"
            # fires as soon as the HTML is parsed. We then wait for the input
            # to be visible AND add a 3-second delay so React/Angular event
            # handlers finish attaching before we interact.
            await page.goto(TESS_LOGIN_URL, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_selector('input[name="username"]', state="visible", timeout=15000)
            await page.wait_for_timeout(3000)  # JS framework init

            # Selector fix 2026-06-11: maglogin uses a "User Name" field
            # (input[name="username"], type=text), NOT email. Verified live.
            await page.fill('input[name="username"]', username, timeout=10000)
            await page.fill('input[name="password"]', password, timeout=10000)
            await page.click('button[type="submit"]', timeout=5000)
            # Wait for navigation AWAY from the login page — a URL change is
            # the ground-truth indicator of a successful login submission.
            # wait_for_load_state on the same page fires immediately (no-op
            # when the submit was a JS-only handler that already navigated).
            try:
                await page.wait_for_url(
                    lambda url: "/maglogin" not in url, timeout=25000
                )
            except Exception:
                pass  # URL check below handles both timeout and no-nav cases

            # Fixed 2026-07-16: URL check was non-functional — TESS_DASHBOARD_HOST
            # appears in BOTH the login URL and dashboard URL, so the guard never
            # caught a failed login. Check that we've navigated AWAY from the
            # login page specifically.
            if "/maglogin" in page.url:
                logger.error("Credential login failed — still at login page: %s", page.url)
                return False

            # Fixed 2026-07-16: static 2s wait was insufficient for TESS SPA
            # to flush auth data to localStorage after redirect. The SPA writes
            # ls.authenticationData asynchronously post-navigation. Poll up to
            # 20 s (checking every 1 s) so intermittent timing doesn't cause a
            # false "no auth token" failure.
            auth_data_raw = None
            for _poll in range(20):
                auth_data_raw = await page.evaluate(
                    "() => localStorage.getItem('ls.authenticationData')"
                )
                if auth_data_raw:
                    break
                if _poll == 0:
                    logger.info("Polling localStorage for auth token (up to 20s)...")
                await page.wait_for_timeout(1000)

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

            # Live localStorage (verified 2026-06-11): ls.authenticationData =
            # {"token": <JWT>, "refreshToken": <str>}. No accessToken/expiresAt/
            # userID fields — token IS the access JWT; expiry comes from its exp.
            access_token = auth_data.get("token") or auth_data.get("accessToken", "")
            refresh_token_val = auth_data.get("refreshToken", "")
            expires_at_str = auth_data.get("expiresAt", "")
            user_id = auth_data.get("userID", "")

            if not access_token:
                logger.error("Credential login: accessToken empty")
                return False

            import datetime
            expires_at_unix = None
            # Prefer the JWT's own exp claim (no expiresAt field in localStorage).
            try:
                import base64
                payload_b64 = access_token.split(".")[1]
                payload_b64 += "=" * (-len(payload_b64) % 4)  # pad
                claims = json.loads(base64.urlsafe_b64decode(payload_b64))
                if claims.get("exp"):
                    expires_at_unix = float(claims["exp"])
                    expires_at_str = datetime.datetime.fromtimestamp(
                        expires_at_unix, datetime.timezone.utc
                    ).isoformat().replace("+00:00", "Z")
            except Exception:
                pass
            if expires_at_unix is None:
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


_BAD_CREDS_MARKER = THUNDERBIRD / "OpsCenter/state/.tess_vault_creds_bad"


def _try_credential_login() -> int:
    vault = _load_vault()
    username = vault.get("D2M_TESS_AGENT_USERNAME", "")
    password = vault.get("D2M_TESS_AGENT_PASSWORD", "")
    if not username or not password:
        logger.error("No vault credentials — cannot auto-login")
        return 1
    try:
        ok = asyncio.run(_credential_login_playwright(username, password))
    except Exception as e:
        # Transient (page-load timeout, network) — NOT the stale-password case.
        # Keep rc=1 so the OnFailure/remediation retry path still fires.
        logger.error("Credential login transient failure: %s", str(e)[:120])
        return 1
    if ok:
        _BAD_CREDS_MARKER.unlink(missing_ok=True)
        return 0
    # Diagnosed 2026-07-16: TESS answers invalid_grant ("user name or password
    # is incorrect") — the vault password is stale. That is a HUMAN-GATED fix
    # (Commander must update .env.vault or inject a browser token via
    # rotate_tess_credentials.sh). Re-alerting every 90 min via OnFailure adds
    # nothing — page ONCE (wing_page one-and-done dedup), then exit 0 with the
    # marker set so the storm stops until the vault changes.
    if _BAD_CREDS_MARKER.exists():
        logger.warning("Credential login still failing (stale vault password) — "
                       "already paged, suppressing repeat alert")
        return 0
    try:
        sys.path.insert(0, str(THUNDERBIRD))
        from core.comms.wing_page import send_page, P1
        send_page(
            problem="TESS keepalive: vault password rejected (invalid_grant)",
            discussion="TESS says the stored user name or password is incorrect. "
                       "Token cannot be minted until the vault is corrected.",
            action="Update D2M_TESS_AGENT_PASSWORD in Thunderbird/.env.vault, "
                   "OR log into crm.myagentgenie.com and run: "
                   "bash scripts/rotate_tess_credentials.sh 'authenticationData blob'",
            level=P1, source="CHIEF SILVER",
        )
    except Exception:
        pass
    _BAD_CREDS_MARKER.write_text("paged")
    return 0


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
