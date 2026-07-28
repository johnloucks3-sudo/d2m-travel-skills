#!/usr/bin/env python3
import asyncio
import sys
import os
import http.server
import threading
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from playwright.async_api import async_playwright
from google_auth_oauthlib.flow import InstalledAppFlow

ROOT = Path("/home/john/Thunderbird")
sys.path.insert(0, str(ROOT))

from api.thunderbird_google_auth import OAUTH_CREDENTIALS_FILE, SCOPES, TOKEN_FILE

CDP_URL = "http://localhost:9222"
CALLBACK_PORT = 8789
ARTIFACT_DIR = Path("/home/john/.gemini/antigravity-cli/brain/c80a4815-e86d-4dd6-94e6-fa17a3ec2d3e")

received_code = {}

class CallbackHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        received_code['code'] = params.get('code', [None])[0]
        received_code['state'] = params.get('state', [None])[0]
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(b"<html><body><h1>Auth Complete!</h1><p>You can close this tab now.</p></body></html>")

class ReuseAddrHTTPServer(http.server.HTTPServer):
    allow_reuse_address = True

def start_callback_server():
    server = ReuseAddrHTTPServer(('127.0.0.1', CALLBACK_PORT), CallbackHandler)
    server.handle_request() # Listen for a single request and terminate

async def main():
    print("=== Automated OAuth Clicker ===")
    
    # 1. Build flow and generate URL with state
    flow = InstalledAppFlow.from_client_secrets_file(str(OAUTH_CREDENTIALS_FILE), SCOPES)
    flow.redirect_uri = f"http://localhost:{CALLBACK_PORT}/"
    
    auth_url, state = flow.authorization_url(prompt="consent", access_type="offline")
    print(f"Auth URL: {auth_url}")
    print(f"State token: {state}")
    
    # Start the callback server thread
    t = threading.Thread(target=start_callback_server, daemon=True)
    t.start()
    await asyncio.sleep(1.5)
    
    # 2. Connect Playwright to Chrome CDP
    print(f"Connecting to Chrome CDP at {CDP_URL}...")
    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp(CDP_URL)
        except Exception as e:
            print(f"ERROR: Could not connect to Chrome CDP: {e}")
            return
            
        print("Connected! Opening consent page...")
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await ctx.new_page()
        
        # Go to auth URL
        await page.goto(auth_url)
        await page.wait_for_timeout(5000) # wait for page load / redirect
        
        # Make sure artifact directory exists
        os.makedirs(str(ARTIFACT_DIR), exist_ok=True)
        
        # Take screenshot of page 1
        screenshot_path = ARTIFACT_DIR / "oauth_step1.png"
        await page.screenshot(path=str(screenshot_path))
        print(f"Screenshot saved to {screenshot_path}")
        print(f"Current page URL: {page.url}")
        
        content = await page.content()
        
        # Click account selection card if present
        if "Choose an account" in content or "accounts.google.com/v3/signin/accountchooser" in page.url:
            print("Detecting account chooser. Clicking johnloucks3@gmail.com...")
            try:
                await page.click("text=johnloucks3@gmail.com", timeout=5000)
                await page.wait_for_timeout(3000)
                await page.screenshot(path=str(ARTIFACT_DIR / "oauth_step2_clicked_account.png"))
            except Exception as e:
                print(f"Could not click account: {e}")
                
        # Check if unverified app warning page is shown
        content = await page.content()
        if "Google hasn't verified this app" in content or "unverified" in page.url:
            print("Detecting unverified app warning. Clicking 'Advanced'...")
            try:
                await page.click("text=Advanced", timeout=5000)
                await page.wait_for_timeout(2000)
                await page.screenshot(path=str(ARTIFACT_DIR / "oauth_step2a_advanced.png"))
                
                print("Clicking 'Go to Thunderbird Command (unsafe)'...")
                await page.click("text=Go to Thunderbird Command (unsafe)", timeout=5000)
                await page.wait_for_timeout(5000)
                await page.screenshot(path=str(ARTIFACT_DIR / "oauth_step2b_unsafe.png"))
            except Exception as e:
                print(f"Could not bypass warning: {e}")
                
        # Select all checkboxes if present on the consent page
        try:
            checkboxes = page.locator('input[type="checkbox"]')
            count = await checkboxes.count()
            if count > 0:
                print(f"Found {count} checkboxes for scopes. Checking all...")
                for i in range(count):
                    checkbox = checkboxes.nth(i)
                    if not await checkbox.is_checked():
                        await checkbox.check()
                await page.wait_for_timeout(2000)
                await page.screenshot(path=str(ARTIFACT_DIR / "oauth_step3_checkboxes_checked.png"))
        except Exception as e:
            print(f"Could not check checkboxes: {e}")
            
        # Click final Continue/Allow button
        print("Clicking final Continue/Allow button...")
        submitted = False
        for selector in ["button:has-text('Continue')", "button:has-text('Allow')", "#submit_approve_access"]:
            try:
                await page.click(selector, timeout=5000)
                print(f"Clicked submission button: {selector}")
                submitted = True
                await page.wait_for_timeout(5000)
                break
            except Exception:
                pass
        
        await page.screenshot(path=str(ARTIFACT_DIR / "oauth_step4_after_submission.png"))
        
        # Wait a bit for callback redirect to finish
        await page.wait_for_timeout(5000)
        await page.close()
        
    print("Waiting for callback server thread to join...")
    t.join(timeout=10)
    
    # 3. Exchange code for credentials
    if received_code.get('code') and received_code.get('state') == state:
        print("\nExchanging authorization code...")
        flow.fetch_token(code=received_code['code'])
        creds = flow.credentials
        TOKEN_FILE.write_text(creds.to_json())
        print(f"SUCCESS! Token saved to {TOKEN_FILE}")
        print(f"Granted scopes: {len(creds.scopes or SCOPES)}")
    else:
        print("\nFailed to capture code or state mismatch.")
        print(f"Captured: {received_code}")

if __name__ == "__main__":
    asyncio.run(main())
