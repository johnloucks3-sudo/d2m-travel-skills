#!/usr/bin/env python3
"""
Poe.com account scraper using saved browser cookies.
Avoids login flow — just uses existing session to fetch account page.
"""
import os, sqlite3, re, json
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright

DB = Path.home() / "Thunderbird" / "storage" / "ai_costs.db"
COOKIES_FILE = Path.home() / "Thunderbird" / ".poe_cookies.json"

def scrape_with_cookies():
    """Load cookies from file and scrape account page."""
    
    if not COOKIES_FILE.exists():
        print(f"ERROR: Cookie file not found: {COOKIES_FILE}")
        print("First, run: opencode connect-chrome, login to poe.com, then export cookies")
        return None
    
    with open(COOKIES_FILE) as f:
        cookies = json.load(f)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        
        # Add cookies
        context.add_cookies(cookies)
        page = context.new_page()
        
        try:
            print("[1/3] Navigating to account page with cookies...")
            page.goto("https://poe.com/account", wait_until="domcontentloaded", timeout=15000)
            
            print("[2/3] Waiting for content to load...")
            page.wait_for_load_state("networkidle", timeout=10000)
            
            print("[3/3] Extracting points...")
            body_text = page.locator("body").text_content()
            
            # Parse points
            # Expected: "123,456 points used of 660,000" or similar
            pattern = r'([\d,]+)\s+points?\s+(?:used|of|\/)\s+([\d,]+)'
            match = re.search(pattern, body_text, re.IGNORECASE)
            
            if match:
                points_used = int(match.group(1).replace(',', ''))
                points_limit = int(match.group(2).replace(',', ''))
                points_balance = points_limit - points_used
                pct_used = (points_used / points_limit * 100)
                
                result = {
                    "points_balance": points_balance,
                    "points_limit": points_limit,
                    "points_used": points_used,
                    "pct_used": pct_used,
                    "status": "success"
                }
                
                return result
            else:
                print(f"Pattern not found. Page text (first 1000 chars):\n{body_text[:1000]}")
                return None
                
        except Exception as e:
            print(f"ERROR: {e}")
            return None
        finally:
            context.close()
            browser.close()

def store_snapshot(data):
    """Store in SQLite."""
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
    
    print(f"✓ Stored: {data['points_used']:,}/{data['points_limit']:,} ({data['pct_used']:.1f}%)")

if __name__ == "__main__":
    print("=== Poe Account Scraper (Cookie-based) ===")
    data = scrape_with_cookies()
    if data:
        print(json.dumps(data, indent=2))
        store_snapshot(data)
    else:
        print("FAILED")
