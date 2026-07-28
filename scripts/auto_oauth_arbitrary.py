#!/usr/bin/env python3
import asyncio
import sys
import os
from pathlib import Path
from playwright.async_api import async_playwright

CDP_URL = "http://localhost:9222"
ARTIFACT_DIR = Path("/home/john/.gemini/antigravity-cli/brain/c80a4815-e86d-4dd6-94e6-fa17a3ec2d3e")

async def main():
    if len(sys.argv) < 2:
        print("ERROR: Please provide the Google OAuth URL as an argument.")
        sys.exit(1)
        
    auth_url = sys.argv[1]
    print(f"Target Auth URL: {auth_url}")
    os.makedirs(str(ARTIFACT_DIR), exist_ok=True)
    
    print(f"Connecting to Chrome CDP at {CDP_URL}...")
    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp(CDP_URL)
        except Exception as e:
            print(f"ERROR: Could not connect to Chrome CDP: {e}")
            return
            
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await ctx.new_page()
        
        print("Navigating to target URL...")
        await page.goto(auth_url)
        await page.wait_for_timeout(5000)
        
        await page.screenshot(path=str(ARTIFACT_DIR / "arbitrary_1_initial.png"))
        print(f"Initial Page URL: {page.url}")
        
        content = await page.content()
        
        # 1. Handle Account Chooser
        if "Choose an account" in content or "accountchooser" in page.url:
            print("Action: Account Chooser detected. Clicking johnloucks3@gmail.com...")
            try:
                await page.click("text=johnloucks3@gmail.com", timeout=5000)
                await page.wait_for_timeout(5000)
            except Exception as e:
                print(f"Failed to click account: {e}")
            
            await page.screenshot(path=str(ARTIFACT_DIR / "arbitrary_2_after_account_click.png"))
            print(f"URL after account click: {page.url}")
            content = await page.content()
            
        # 2. Check if Google asks for password
        if "Enter your password" in content or "password" in page.url:
            print("WARNING: Google is prompting for a password. Cannot automate password entry.")
            await page.close()
            return
            
        # 3. Handle Unverified App Warning
        if "warning" in page.url or "hasn’t verified" in content or "hasn't verified" in content:
            print("Action: Unverified App Warning detected. Clicking 'Advanced'...")
            try:
                await page.click("text=Advanced", timeout=5000)
                await page.wait_for_timeout(2000)
                await page.screenshot(path=str(ARTIFACT_DIR / "arbitrary_3_advanced_clicked.png"))
                
                print("Action: Clicking 'unsafe' proceed link...")
                await page.click("text=unsafe", timeout=5000)
                await page.wait_for_timeout(5000)
            except Exception as e:
                print(f"Failed to bypass warning page: {e}")
                
            await page.screenshot(path=str(ARTIFACT_DIR / "arbitrary_4_after_warning_bypass.png"))
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
                await page.screenshot(path=str(ARTIFACT_DIR / "arbitrary_5_checkboxes_checked.png"))
        except Exception as e:
            print(f"Failed to handle checkboxes: {e}")
            
        # 5. Click Continue/Allow
        print("Action: Clicking final Continue/Allow button...")
        for selector in ["button:has-text('Continue')", "button:has-text('Allow')", "#submit_approve_access"]:
            try:
                await page.click(selector, timeout=5000)
                print(f"Success: Clicked {selector}")
                await page.wait_for_timeout(5000)
                break
            except Exception:
                pass
                
        await page.screenshot(path=str(ARTIFACT_DIR / "arbitrary_6_final.png"))
        print(f"\nRESULT_REDIRECT_URL: {page.url}")
        await page.close()

if __name__ == "__main__":
    asyncio.run(main())
