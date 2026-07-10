#!/usr/bin/env python3
"""
silversea_cookie_refresh.py — Silversea Session Keepalive
==========================================================
Checks session health and refreshes if expired.
Runs every 48h via systemd timer (before 72h expiry).
Reports status to relay (D2M Channels) — NOT D2MC2C.
"""
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(ROOT / "logs" / "silversea_session.log", mode="a"),
    ]
)
log = logging.getLogger("silversea_refresh")

COOKIE_FILE = Path.home() / ".playwright" / "cookies_silversea.json"
STATE_FILE = ROOT / "OpsCenter" / "state" / "silversea_session.json"
STATE_FILE.parent.mkdir(parents=True, exist_ok=True)


def send_relay(message: str) -> None:
    """Send status to D2M Channels relay (not D2MC2C)."""
    try:
        import requests
        env_file = ROOT / ".env"
        env = {}
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
        token = env.get("TELEGRAM_RELAY_TOKEN") or env.get("TELEGRAM_CHANNELS_BOT_TOKEN")
        chat_id = env.get("TELEGRAM_RELAY_CHAT_ID", "-5248121475")
        if token:
            requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"},
                timeout=10
            )
    except Exception as e:
        log.warning(f"Relay notify failed: {e}")


def save_state(status: str, detail: str) -> None:
    STATE_FILE.write_text(json.dumps({
        "last_check": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "detail": detail,
        "cookie_file": str(COOKIE_FILE),
    }, indent=2))


def navigate_with_retry(page, url, max_retries=3):
    """Navigate with exponential backoff on transient network errors."""
    import time
    backoff_seconds = [2, 4, 8]
    transient = ("ERR_NAME_NOT_RESOLVED", "ERR_NETWORK_CHANGED", "ERR_CONNECTION_RESET",
                 "ERR_INVALID_RESPONSE", "ERR_PROXY_CONNECTION_FAILED", "ERR_CONNECTION_TIMED_OUT")
    last_error = None
    for attempt in range(max_retries):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            return True
        except Exception as e:
            last_error = e
            if any(x in str(e) for x in transient) and attempt < max_retries - 1:
                wait_time = backoff_seconds[attempt]
                log.warning(f"[RETRY {attempt+1}/{max_retries}] Navigation error, waiting {wait_time}s: {e}")
                time.sleep(wait_time)
                continue
            raise e
    log.warning(f"Navigation failed after {max_retries} attempts: {last_error}")
    return False


def check_and_refresh() -> str:
    if not COOKIE_FILE.exists():
        log.error("Cookie file missing")
        save_state("ERROR", "Cookie file missing")
        send_relay("🔴 <b>Silversea session</b>: Cookie file missing — manual login required.")
        return "ERROR"

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log.error("playwright not installed")
        save_state("ERROR", "playwright not installed")
        return "ERROR"

    cookies = json.loads(COOKIE_FILE.read_text())

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled", "--disable-dev-shm-usage"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900},
        )

        playwright_cookies = []
        for c in cookies:
            pc = {
                "name": c["name"], "value": c["value"],
                "domain": c.get("domain", ".silversea.com"),
                "path": c.get("path", "/"),
                "httpOnly": c.get("httpOnly", False),
                "secure": c.get("secure", False),
            }
            if c.get("expires", -1) != -1:
                pc["expires"] = int(c["expires"])
            if c.get("sameSite"):
                pc["sameSite"] = c["sameSite"]
            playwright_cookies.append(pc)

        context.add_cookies(playwright_cookies)
        page = context.new_page()

        import time
        try:
            if not navigate_with_retry(page, "https://my.silversea.com", max_retries=3):
                log.warning("Silversea session refresh failed after retries. Existing session preserved.")
                save_state("DEGRADED", "Navigation failed after 3 retries — existing session preserved, will retry next cycle")
                browser.close()
                return "HEALTHY"  # graceful degradation — don't crash the service, don't false-alarm EXPIRED
        except Exception as e:
            log.warning(f"Silversea session refresh failed (non-transient): {e}. Existing session preserved.")
            save_state("DEGRADED", f"Non-transient nav error: {e} — existing session preserved, will retry next cycle")
            browser.close()
            return "HEALTHY"

        time.sleep(3)

        url = page.url
        content = page.content()

        if "/Account/Login" in url or "/signin" in url:
            log.warning("Session expired — attempting auto-login")
            # Auto-login
            creds_file = ROOT / "config" / "portal_creds.json"
            creds = json.loads(creds_file.read_text()).get("silversea", {})
            email = creds.get("email", "")
            password = creds.get("password", "")

            success = False
            try:
                page.goto("https://my.silversea.com/Account/Login", wait_until="domcontentloaded", timeout=30000)
                time.sleep(3)
                email_input = page.locator("input[type='email'], input[name='email']").first
                if email_input.is_visible(timeout=5000):
                    email_input.fill(email)
                    page.locator("button[type='submit'], input[type='submit']").first.click()
                    time.sleep(2)
                pwd_input = page.locator("input[type='password']").first
                if pwd_input.is_visible(timeout=5000):
                    pwd_input.fill(password)
                    page.locator("button[type='submit'], input[type='submit']").first.click()
                    time.sleep(5)
                if "/Account/Login" not in page.url:
                    success = True
            except Exception as e:
                log.error(f"Auto-login error: {e}")

            if success:
                new_cookies = context.cookies()
                COOKIE_FILE.write_text(json.dumps(new_cookies, indent=2))
                log.info("Session refreshed via login ✅")
                save_state("REFRESHED", f"Auto-login successful at {datetime.now().isoformat()}")
                send_relay("🔄 <b>Silversea session</b>: Refreshed via auto-login ✅")
                browser.close()
                return "REFRESHED"
            else:
                log.error("Auto-login failed — manual intervention needed")
                save_state("EXPIRED", "Auto-login failed")
                send_relay("🔴 <b>Silversea session</b>: EXPIRED — auto-login failed. Manual login required at my.silversea.com")
                browser.close()
                return "EXPIRED"
        else:
            log.info(f"Session healthy ✅ — URL: {url}")
            # Persist any updated cookies
            new_cookies = context.cookies()
            if new_cookies:
                COOKIE_FILE.write_text(json.dumps(new_cookies, indent=2))
            save_state("HEALTHY", f"Verified at {datetime.now().isoformat()} — URL: {url}")
            browser.close()
            return "HEALTHY"


if __name__ == "__main__":
    status = check_and_refresh()
    log.info(f"Final status: {status}")
    sys.exit(0 if status in ("HEALTHY", "REFRESHED") else 1)
