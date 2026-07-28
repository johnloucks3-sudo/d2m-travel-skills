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
    server.handle_request()

async def main():
    print("=== Automated OAuth Debug ===")
    os.makedirs(str(ARTIFACT_DIR), exist_ok=True)
    
    flow = InstalledAppFlow.from_client_secrets_file(str(OAUTH_CREDENTIALS_FILE), SCOPES)
    flow.redirect_uri = f"http://localhost:{CALLBACK_PORT}/"
    auth_url, state = flow.authorization_url(prompt="consent", access_type="offline")
    
    t = threading.Thread(target=start_callback_server, daemon=True)
    t.start()
    await asyncio.sleep(1)
    
    print(f"Connecting to Chrome CDP at {CDP_URL}...")
    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp(CDP_URL)
        except Exception as e:
            print(f"ERROR: Could not connect to Chrome CDP: {e}")
            return
            
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await ctx.new_page()
        
        print(f"Navigating to: {auth_url}")
        await page.goto(auth_url)
        await page.wait_for_timeout(5000)
        
        await page.screenshot(path=str(ARTIFACT_DIR / "debug_1_initial.png"))
        print(f"Initial Page URL: {page.url}")
        
        content = await page.content()
        
        # 1. Handle Account Chooser
        if "Choose an account" in content or "accountchooser" in page.url:
            print("Action: Account Chooser detected. Clicking johnloucks3@gmail.com...")
            try:
                await page.click("text=johnloucks3@gmail.com", timeout=10000)
                print("Click successful. Waiting for transition...")
                await page.wait_for_timeout(5000)
            except Exception as e:
                print(f"Failed to click account: {e}")
            
            await page.screenshot(path=str(ARTIFACT_DIR / "debug_2_after_account_click.png"))
            print(f"URL after account click: {page.url}")
            content = await page.content()
            
        # 2. Check if Google asks for password
        if "Enter your password" in content or "password" in page.url:
            print("WARNING: Google is prompting for password. Cannot automate password entry headless.")
            await page.close()
            return
            
        # 3. Handle Unverified App Warning
        if "warning" in page.url or "hasn’t verified" in content or "hasn't verified" in content:
            print("Action: Unverified App Warning detected. Clicking 'Advanced'...")
            try:
                # Try clicking Advanced link
                await page.click("text=Advanced", timeout=5000)
                await page.wait_for_timeout(2000)
                await page.screenshot(path=str(ARTIFACT_DIR / "debug_3_advanced_clicked.png"))
                
                print("Action: Clicking 'unsafe' proceed link...")
                # Click the unsafe link. In Google UI it typically reads: "Go to Thunderbird Command (unsafe)"
                # Let's search for the element containing "unsafe"
                await page.click("text=unsafe", timeout=5000)
                print("Click successful. Waiting for transition...")
                await page.wait_for_timeout(5000)
            except Exception as e:
                print(f"Failed to bypass warning page: {e}")
                
            await page.screenshot(path=str(ARTIFACT_DIR / "debug_4_after_warning_bypass.png"))
            print(f"URL after warning bypass: {page.url}")
            content = await page.content()
            
        # 4. Handle Consent Scope Checkboxes
        try:
            checkboxes = page.locator('input[type="checkbox"]')
            count = await checkboxes.count()
            if count > 0:
                print(f"Action: Found {count} scope checkboxes. Checking all...")
                for i in range(count):
                    checkbox = checkboxes.nth(i)
                    if not await checkbox.is_checked():
                        await checkbox.check()
                await page.wait_for_timeout(2000)
                await page.screenshot(path=str(ARTIFACT_DIR / "debug_5_checkboxes_checked.png"))
        except Exception as e:
            print(f"Failed to handle checkboxes: {e}")
            
        # 5. Click Continue/Allow
        print("Action: Clicking final Continue/Allow button...")
        clicked_submit = False
        for selector in ["button:has-text('Continue')", "button:has-text('Allow')", "#submit_approve_access"]:
            try:
                await page.click(selector, timeout=5000)
                print(f"Success: Clicked {selector}")
                clicked_submit = True
                await page.wait_for_timeout(5000)
                break
            except Exception:
                pass
                
        await page.screenshot(path=str(ARTIFACT_DIR / "debug_6_after_allow.png"))
        print(f"Final URL: {page.url}")
        await page.close()
        
    print("Waiting for callback server to join...")
    t.join(timeout=10)
    
    if received_code.get('code') and received_code.get('state') == state:
        print("\nExchanging code...")
        flow.fetch_token(code=received_code['code'])
        creds = flow.credentials
        TOKEN_FILE.write_text(creds.to_json())
        print(f"SUCCESS! Token saved to {TOKEN_FILE}")
    else:
        print(f"\nFailed. Captured code state: {received_code}")

if __name__ == "__main__":
    asyncio.run(main())
