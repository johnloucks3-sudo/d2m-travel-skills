#!/usr/bin/env python3
"""Poe Activity Scraper — uses Playwright to bypass Cloudflare and scrape actual usage.

Usage: python poe_activity_scraper.py
Output: Writes snapshot to poe_snapshots table in SQLite
"""
import json
import sqlite3
import os
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    print("ERROR: playwright not installed. Run: pip install playwright")
    print("Then: playwright install chromium")
    exit(1)

DB = Path.home() / "Thunderbird" / "storage" / "ai_costs.db"
EMAIL = "yodainva@gmail.com"
PASSWORD = "Falcons4me!"


def scrape_poe_activity():
    """Login to Poe and scrape activity page for usage data."""
    with sync_playwright() as p:
        # Use chromium, headless mode
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        )
        page = context.new_page()
        
        try:
            print("Navigating to poe.com...")
            page.goto("https://poe.com", wait_until="networkidle", timeout=30000)
            
            # Check if already logged in
            if "activity" in page.url:
                print("Already logged in")
            else:
                # Click login button or navigate to login
                print("Logging in...")
                page.goto("https://poe.com/login", wait_until="networkidle", timeout=30000)
                
                # Fill email
                page.fill('input[type="email"]', EMAIL)
                time.sleep(0.5)
                
                # Fill password
                page.fill('input[type="password"]', PASSWORD)
                time.sleep(0.5)
                
                # Click submit
                page.click('button[type="submit"]')
                print("Waiting for redirect...")
                page.wait_for_url("**/activity**", timeout=30000)
            
            # Navigate to activity page
            print("Navigating to activity page...")
            page.goto("https://poe.com/activity", wait_until="networkidle", timeout=30000)
            
            # Parse activity table
            rows = page.query_selector_all("table tbody tr")
            print(f"Found {len(rows)} activity rows")
            
            total_points = 0
            data_by_model = {}
            
            for row in rows[:50]:  # Limit to first 50 rows
                cells = row.query_selector_all("td")
                if len(cells) < 4:
                    continue
                
                try:
                    # Extract cells: Timestamp, Model/Bot, Source, Cost (pts)
                    ts_text = cells[0].text_content().strip()
                    model = cells[1].text_content().strip()
                    source = cells[2].text_content().strip() if len(cells) > 2 else "unknown"
                    cost_text = cells[3].text_content().strip() if len(cells) > 3 else "0 pts"
                    
                    # Parse points from cost (e.g., "540 pts" → 540)
                    points = int(cost_text.split()[0].replace(",", ""))
                    
                    total_points += points
                    if model not in data_by_model:
                        data_by_model[model] = 0
                    data_by_model[model] += points
                    
                    print(f"  {model}: {points} pts ({ts_text})")
                except Exception as e:
                    print(f"  Parse error: {e}")
                    continue
            
            print(f"\nTotal points (last 50 rows): {total_points}")
            print(f"By model: {data_by_model}")
            
            # Try to find balance (often displayed at top)
            balance_text = page.query_selector(".balance, [class*='balance'], [class*='credit']")
            balance = None
            if balance_text:
                print(f"Balance element: {balance_text.text_content()[:50]}")
            
            context.close()
            browser.close()
            
            return {
                "success": True,
                "total_points_scraped": total_points,
                "models": data_by_model,
                "balance": balance
            }
            
        except PlaywrightTimeout as e:
            print(f"Timeout: {e}")
            context.close()
            browser.close()
            return {"success": False, "error": f"Timeout: {str(e)[:100]}"}
        except Exception as e:
            print(f"Error: {e}")
            context.close()
            browser.close()
            return {"success": False, "error": str(e)[:100]}


def store_snapshot(data: dict):
    """Store scraped data in SQLite."""
    if not data.get("success"):
        print(f"Skipping store: {data.get('error')}")
        return
    
    conn = sqlite3.connect(str(DB), timeout=10)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    try:
        conn.execute("""
            INSERT OR IGNORE INTO poe_snapshots
            (ts, points_balance, points_used_today, estimated_cost_usd, source)
            VALUES (?,?,?,?,?)
        """, (
            now,
            data.get("balance"),
            data.get("total_points_scraped", 0),
            None,
            "scrape"
        ))
        conn.commit()
        print(f"Snapshot stored: {data.get('total_points_scraped')} points")
    finally:
        conn.close()


if __name__ == "__main__":
    print("Scraping Poe activity...")
    result = scrape_poe_activity()
    print(f"Result: {result}")
    if result.get("success"):
        store_snapshot(result)
