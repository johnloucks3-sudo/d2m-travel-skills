#!/usr/bin/env python3
"""
Automate Google Calendar OAuth consent flow using Playwright + Chrome profile.
"""
import json
import logging
import os
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.scheduling.thunderbird_calendar_sync import (
    OAUTH_CREDENTIALS_FILE, CALENDAR_TOKEN_FILE, CALENDAR_SCOPES
)
from google_auth_oauthlib.flow import InstalledAppFlow

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Capture the URL that run_local_server prints
_auth_url_captured = None

def _capture_auth_url(flow):
    """Build the auth URL and return it."""
    auth_url, _ = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    return auth_url

def main():
    if CALENDAR_TOKEN_FILE.exists():
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        creds = Credentials.from_authorized_user_file(str(CALENDAR_TOKEN_FILE), CALENDAR_SCOPES)
        if creds and creds.valid:
            logger.info("Calendar token already exists and is valid.")
            return True
        if creds and creds.expired and creds.refresh_token:
            logger.info("Token expired — refreshing...")
            creds.refresh(Request())
            CALENDAR_TOKEN_FILE.write_text(creds.to_json())
            logger.info("Refreshed and saved.")
            return True

    if not OAUTH_CREDENTIALS_FILE.exists():
        logger.error(f"OAuth credentials not found: {OAUTH_CREDENTIALS_FILE}")
        return False

    flow = InstalledAppFlow.from_client_secrets_file(
        str(OAUTH_CREDENTIALS_FILE), CALENDAR_SCOPES
    )

    auth_url, _ = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )

    logger.info("Starting OAuth local server in background thread...")
    
    result = [None]
    def run_server():
        try:
            creds = flow.run_local_server(port=0)
            result[0] = creds
        except Exception as e:
            logger.error(f"OAuth server error: {e}")
    
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    time.sleep(1)  # Give server time to print URL
    
    logger.info(f"Opening auth URL in Chrome via Playwright...")
    
    try:
        from playwright.sync_api import sync_playwright
        
        chrome_path = "/usr/bin/google-chrome"
        user_data_dir = os.path.expanduser("~/.config/google-chrome")
        
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir,
                headless=False,
                executable_path=chrome_path,
                args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
                handle_sigint=False,
            )
            page = context.new_page()
            page.goto(auth_url, wait_until="domcontentloaded", timeout=60000)
            
            # Wait for page to render
            page.wait_for_timeout(3000)
            page.screenshot(path="/tmp/oauth_calendar_1.png")
            
            # Try clicking consent buttons
            consent_selectors = [
                "button:has-text('Continue')",
                "button:has-text('Allow')",
                "[jsname=submit_accept_action]",
                "#submit_accept",
                "div[role=button]:has-text('Continue')",
                "span:has-text('Continue') >> ..",
            ]
            
            for sel in consent_selectors:
                try:
                    btn = page.wait_for_selector(sel, timeout=3000)
                    if btn and btn.is_visible():
                        logger.info(f"Clicked: {sel}")
                        btn.click()
                        page.wait_for_timeout(2000)
                        break
                except Exception:
                    continue
            
            page.wait_for_timeout(5000)
            page.screenshot(path="/tmp/oauth_calendar_2.png")
            
            # Wait for the server thread to complete (up to 60s)
            for _ in range(60):
                if result[0] is not None:
                    break
                time.sleep(1)
            
            context.close()
    
    except ImportError:
        logger.error("Playwright not available")
    except Exception as e:
        logger.error(f"Browser error: {e}")
    
    # If the server thread didn't complete, wait a bit more
    server_thread.join(timeout=30)
    
    creds = result[0]
    if creds:
        CALENDAR_TOKEN_FILE.write_text(creds.to_json())
        logger.info(f"Calendar OAuth token saved to {CALENDAR_TOKEN_FILE}")
        return True
    else:
        logger.warning("Calendar OAuth not completed.")
        logger.info(f"Manual option: cd core/scheduling && python3 thunderbird_calendar_sync.py --authorize")
        logger.info(f"Auth URL: {auth_url}")
        return False

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
