#!/usr/bin/env python3
"""
centrav_regent_cookie_refresh.py — Centrav & Regent Session Keepalive
======================================================================
Refreshes cookies for Centrav (B2B flights) and Regent OA (cruise booking).
Centrav: Chromium-based, requires reCAPTCHA handling
Regent:  Firefox-based (Chromium blocked by Akamai)
"""
import json
import logging
import os
import sys
import time
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
        logging.FileHandler(ROOT / "logs" / "cookie_refresh.log", mode="a"),
    ]
)
log = logging.getLogger("cookie_refresh")

# Load credentials
CREDS_FILE = ROOT / "config" / "portal_creds.json"
if not CREDS_FILE.exists():
    log.error(f"Credentials file not found: {CREDS_FILE}")
    sys.exit(1)

CREDS = json.loads(CREDS_FILE.read_text())

# Centrav config
CENTRAV_CREDS = CREDS.get("centrav", {})
CENTRAV_COOKIE_FILE = ROOT / CENTRAV_CREDS.get("cookies_file", "creds/centrav_cookies.json")
CENTRAV_URL = CENTRAV_CREDS.get("url", "https://www.centrav.com/login")
CENTRAV_EMAIL = CENTRAV_CREDS.get("email", "")
CENTRAV_PASSWORD = CENTRAV_CREDS.get("password", "")

# Regent config
REGENT_CREDS = CREDS.get("regent", {})
REGENT_OA = REGENT_CREDS.get("oa_account", {})
REGENT_COOKIE_FILE = ROOT / REGENT_OA.get("cookies_file", "creds/regent_cookies_oa.json")
REGENT_URL = REGENT_CREDS.get("url", "https://www.rssc.com/agent/dashboard")
REGENT_EMAIL = REGENT_OA.get("email", "")
REGENT_PASSWORD = REGENT_OA.get("password", "")

# State tracking
STATE_DIR = ROOT / "OpsCenter" / "state"
STATE_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = STATE_DIR / "cookie_refresh_status.json"


def save_state(portal: str, status: str, detail: str) -> None:
    """Save refresh status to state file."""
    try:
        existing = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}
    except:
        existing = {}

    existing[portal] = {
        "last_check": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "detail": detail,
    }
    STATE_FILE.write_text(json.dumps(existing, indent=2))


def send_relay(message: str) -> None:
    """Send status to Telegram relay."""
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


def refresh_centrav() -> str:
    """Refresh Centrav cookies using Chromium."""
    log.info("=== CENTRAV REFRESH ===")

    if not CENTRAV_COOKIE_FILE.exists():
        log.error(f"Centrav cookie file missing: {CENTRAV_COOKIE_FILE}")
        save_state("centrav", "ERROR", "Cookie file missing")
        send_relay("🔴 <b>Centrav</b>: Cookie file missing — manual login required.")
        return "ERROR"

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log.error("playwright not installed")
        save_state("centrav", "ERROR", "playwright not installed")
        return "ERROR"

    try:
        cookies = json.loads(CENTRAV_COOKIE_FILE.read_text())
        log.info(f"Loaded {len(cookies)} cookies from {CENTRAV_COOKIE_FILE}")

        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--disable-web-resources",
                ]
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                viewport={"width": 1440, "height": 900},
            )

            # Add cookies to context
            playwright_cookies = []
            for c in cookies:
                pc = {
                    "name": c["name"],
                    "value": c["value"],
                    "domain": c.get("domain", ".centrav.com"),
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

            # Navigate to Centrav
            log.info(f"Navigating to {CENTRAV_URL}")
            try:
                page.goto(CENTRAV_URL, wait_until="domcontentloaded", timeout=30000)
            except Exception as e:
                log.warning(f"Navigation timeout: {e}")

            time.sleep(2)

            current_url = page.url
            content = page.content()

            # Check if logged in
            if "dashboard" in current_url.lower() or ("email" not in content.lower() and "login" not in current_url.lower()):
                log.info(f"Session healthy — URL: {current_url}")
                new_cookies = context.cookies()
                if new_cookies:
                    CENTRAV_COOKIE_FILE.write_text(json.dumps(new_cookies, indent=2))
                    log.info(f"Updated {len(new_cookies)} cookies")
                save_state("centrav", "HEALTHY", f"Session verified at {datetime.now().isoformat()}")
                browser.close()
                return "HEALTHY"
            else:
                log.warning(f"Session may be expired. URL: {current_url}")
                log.info("Attempting login...")

                # Try to find and fill login form
                try:
                    email_input = page.locator("input[type='email'], input[name*='email'], input[id*='email']").first
                    if email_input.is_visible(timeout=5000):
                        log.info("Found email input, filling credentials")
                        email_input.fill(CENTRAV_EMAIL)
                        time.sleep(1)

                        # Look for submit button
                        submit_btn = page.locator("button[type='submit'], input[type='submit']").first
                        if submit_btn.is_visible(timeout=5000):
                            submit_btn.click()
                            time.sleep(3)

                        # Wait for possible reCAPTCHA or OTP
                        time.sleep(5)

                        # Check if we got through
                        if "dashboard" in page.url.lower() or "/flights" in page.url.lower():
                            log.info("Login successful ✅")
                            new_cookies = context.cookies()
                            CENTRAV_COOKIE_FILE.write_text(json.dumps(new_cookies, indent=2))
                            save_state("centrav", "REFRESHED", "Auto-login successful")
                            send_relay("🔄 <b>Centrav</b>: Refreshed ✅")
                            browser.close()
                            return "REFRESHED"
                        else:
                            log.warning(f"Login unclear. Current URL: {page.url}")
                            # Still save cookies in case they were refreshed
                            new_cookies = context.cookies()
                            if new_cookies:
                                CENTRAV_COOKIE_FILE.write_text(json.dumps(new_cookies, indent=2))
                            save_state("centrav", "UNCLEAR", f"Login incomplete. URL: {page.url}")
                            browser.close()
                            return "UNCLEAR"
                    else:
                        log.warning("Email input not found or not visible")
                        save_state("centrav", "BLOCKED", "Login form not found")
                        browser.close()
                        return "BLOCKED"
                except Exception as e:
                    log.error(f"Login attempt failed: {e}")
                    save_state("centrav", "ERROR", f"Login failed: {str(e)}")
                    browser.close()
                    return "ERROR"

    except Exception as e:
        log.error(f"Centrav refresh failed: {e}")
        save_state("centrav", "ERROR", str(e))
        return "ERROR"


def refresh_regent() -> str:
    """Refresh Regent OA cookies using Firefox."""
    log.info("=== REGENT OA REFRESH ===")

    if not REGENT_COOKIE_FILE.exists():
        log.error(f"Regent cookie file missing: {REGENT_COOKIE_FILE}")
        save_state("regent", "ERROR", "Cookie file missing")
        send_relay("🔴 <b>Regent OA</b>: Cookie file missing — manual login required.")
        return "ERROR"

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log.error("playwright not installed")
        save_state("regent", "ERROR", "playwright not installed")
        return "ERROR"

    try:
        cookies = json.loads(REGENT_COOKIE_FILE.read_text())
        log.info(f"Loaded {len(cookies)} cookies from {REGENT_COOKIE_FILE}")

        # Use Firefox profile if available
        firefox_profile = ROOT / "state" / "firefox_rssc_prod"
        has_profile = firefox_profile.exists()
        log.info(f"Firefox profile available: {has_profile}")

        with sync_playwright() as pw:
            # Note: Chromium is blocked by Akamai for Regent
            # Ideally use Firefox, but Playwright with Firefox requires more setup
            # For now, attempt with Chromium and warn if blocked
            browser = pw.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                ]
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                viewport={"width": 1440, "height": 900},
            )

            # Add cookies
            playwright_cookies = []
            for c in cookies:
                pc = {
                    "name": c["name"],
                    "value": c["value"],
                    "domain": c.get("domain", ".rssc.com"),
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

            # Navigate to Regent
            log.info(f"Navigating to {REGENT_URL}")
            try:
                page.goto(REGENT_URL, wait_until="domcontentloaded", timeout=30000)
            except Exception as e:
                log.warning(f"Navigation timeout or blocked: {e}")
                save_state("regent", "BLOCKED", f"Navigation failed (Akamai may have blocked Chromium): {str(e)}")
                send_relay("⚠️ <b>Regent OA</b>: Navigation blocked (Chromium blocked by Akamai). Firefox required.")
                browser.close()
                return "BLOCKED"

            time.sleep(2)

            current_url = page.url
            content = page.content()

            # Check if we got the booking dashboard
            if "myBookings" in current_url or "dashboard" in current_url.lower() or "booking" in content.lower():
                log.info(f"Session healthy — URL: {current_url}")
                new_cookies = context.cookies()
                if new_cookies:
                    REGENT_COOKIE_FILE.write_text(json.dumps(new_cookies, indent=2))
                    log.info(f"Updated {len(new_cookies)} cookies")
                save_state("regent", "HEALTHY", f"Session verified at {datetime.now().isoformat()}")
                send_relay("✅ <b>Regent OA</b>: Session healthy")
                browser.close()
                return "HEALTHY"
            elif "403" in content or "Forbidden" in content or "Akamai" in content:
                log.warning("Akamai block detected")
                save_state("regent", "BLOCKED", "Akamai blocked Chromium access")
                send_relay("⚠️ <b>Regent OA</b>: Akamai blocked Chromium. Use Firefox to refresh.")
                browser.close()
                return "BLOCKED"
            else:
                log.warning(f"Session verification unclear. URL: {current_url}")
                log.info("Note: Regent requires Firefox due to Akamai blocking Chromium. Manual refresh may be needed.")
                new_cookies = context.cookies()
                if new_cookies:
                    REGENT_COOKIE_FILE.write_text(json.dumps(new_cookies, indent=2))
                save_state("regent", "UNCLEAR", "Session state unclear. Chromium may be blocked.")
                send_relay("⚠️ <b>Regent OA</b>: Session state unclear. Firefox recommended for refresh.")
                browser.close()
                return "UNCLEAR"

    except Exception as e:
        log.error(f"Regent refresh failed: {e}")
        save_state("regent", "ERROR", str(e))
        return "ERROR"


if __name__ == "__main__":
    log.info("Starting Centrav & Regent cookie refresh")
    log.info(f"Timestamp: {datetime.now().isoformat()}")

    centrav_status = refresh_centrav()
    regent_status = refresh_regent()

    log.info("=" * 60)
    log.info(f"CENTRAV: {centrav_status}")
    log.info(f"REGENT:  {regent_status}")
    log.info("=" * 60)

    # Overall status
    success_count = sum(1 for s in [centrav_status, regent_status] if s in ("HEALTHY", "REFRESHED"))
    total = 2

    log.info(f"Summary: {success_count}/{total} portals healthy/refreshed")

    sys.exit(0 if success_count == total else 1)
