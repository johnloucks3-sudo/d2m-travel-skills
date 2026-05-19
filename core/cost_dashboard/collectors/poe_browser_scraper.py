#!/usr/bin/env python3
"""
Poe.com account scraper — fetches real-time points balance via Playwright.
Logs into yodainva@gmail.com, navigates to /account, extracts points used/balance.
Stores in SQLite for dashboard.
"""
import os, sqlite3, re, json
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

DB = Path.home() / "Thunderbird" / "storage" / "ai_costs.db"
POE_EMAIL = "yodainva@gmail.com"
POE_PASSWORD = os.getenv("POE_PASSWORD", "")  # Set in .env
HEADLESS = True

def scrape_poe_account():
    """
    Scrape Poe.com account page for points balance.
    Returns: {"points_balance": int, "points_limit": int, "points_used": int, "pct_used": float}
    """
    if not POE_PASSWORD:
        print("ERROR: POE_PASSWORD not set in .env")
        return None
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        page = browser.new_page()
        
        try:
            # Navigate to login
            print("[1/5] Navigating to poe.com...")
            page.goto("https://poe.com/login", wait_until="networkidle", timeout=30000)
            
            # Fill email
            print("[2/5] Logging in...")
            page.fill("input[type='email']", POE_EMAIL)
            page.fill("input[type='password']", POE_PASSWORD)
            page.click("button[type='submit']")
            page.wait_for_load_state("networkidle", timeout=30000)
            
            # Navigate to account page
            print("[3/5] Navigating to account page...")
            page.goto("https://poe.com/account", wait_until="networkidle", timeout=30000)
            
            # Wait for subscription info to load
            print("[4/5] Extracting points...")
            page.wait_for_selector("text=/Points|Subscription/i", timeout=10000)
            
            # Get page content
            content = page.content()
            
            # Parse points from page
            # Look for patterns like "123,456 / 660,000" or similar
            patterns = [
                r'(\d+[\d,]*)\s*(?:\/|out of)\s*(\d+[\d,]*)\s*(?:points?|Points)',
                r'Balance:\s*(\d+[\d,]*)',
                r'Used:\s*(\d+[\d,]*)',
            ]
            
            points_balance = 0
            points_used = 0
            points_limit = 660000
            
            for pattern in patterns:
                matches = re.findall(pattern, content)
                if matches:
                    print(f"  Found pattern: {pattern} → {matches}")
            
            # Try to extract from visible text more carefully
            text = page.text_content()
            lines = text.split('\n')
            
            for i, line in enumerate(lines):
                if 'point' in line.lower() or 'subscription' in line.lower():
                    print(f"  Line {i}: {line[:100]}")
                    # Try to parse numbers
                    nums = re.findall(r'\d+[\d,]*', line)
                    if len(nums) >= 2:
                        try:
                            num1 = int(nums[0].replace(',', ''))
                            num2 = int(nums[1].replace(',', ''))
                            if 'used' in line.lower() and num1 > num2:
                                points_used = num1
                                points_limit = num2
                            elif 'balance' in line.lower():
                                points_balance = num1
                        except:
                            pass
            
            print("[5/5] Done.")
            pct_used = (points_used / points_limit * 100) if points_limit else 0
            
            result = {
                "points_balance": points_balance,
                "points_limit": points_limit,
                "points_used": points_used,
                "pct_used": pct_used,
                "page_title": page.title()
            }
            
            return result
            
        except PlaywrightTimeoutError as e:
            print(f"ERROR: Timeout — {e}")
            return None
        except Exception as e:
            print(f"ERROR: {type(e).__name__}: {e}")
            return None
        finally:
            browser.close()

def store_poe_snapshot(data):
    """Store Poe snapshot in SQLite."""
    if not data:
        return
    
    conn = sqlite3.connect(str(DB))
    ts = datetime.now(timezone.utc).isoformat()
    
    conn.execute("""
        INSERT OR REPLACE INTO poe_snapshots
        (ts, points_balance, points_limit, points_used, points_pct_used, subscription_type)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        ts,
        data.get("points_balance", 0),
        data.get("points_limit", 660000),
        data.get("points_used", 0),
        data.get("pct_used", 0),
        "subscription"
    ))
    
    conn.commit()
    conn.close()
    
    print(f"✓ Stored: {data['points_used']:,}/{data['points_limit']:,} points ({data['pct_used']:.1f}%)")

if __name__ == "__main__":
    print("=== Poe.com Account Scraper ===")
    data = scrape_poe_account()
    if data:
        print(json.dumps(data, indent=2))
        store_poe_snapshot(data)
    else:
        print("Failed to scrape Poe account")
