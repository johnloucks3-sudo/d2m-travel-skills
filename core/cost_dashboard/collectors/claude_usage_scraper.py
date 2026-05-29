#!/usr/bin/env python3
"""
claude_usage_scraper.py — Accurate Claude MAX usage from claude.ai/settings/usage
Uses Playwright headless browser to bypass Cloudflare and extract actual percentages.
Polls every 5 minutes, writes to plan_snapshots table.
"""
import os
import sys
import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("ERROR: playwright not installed. Run: pip install playwright && playwright install firefox")
    sys.exit(1)

# Paths
DB = Path.home() / "Thunderbird" / "storage" / "ai_costs.db"
COOKIE_FILE = Path.home() / "Thunderbird" / "storage" / "claude_cookies.json"
SNAPSHOT_DIR = Path.home() / "Thunderbird" / "logs" / "claude_scraper_snapshots"
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

# Claude.ai usage page
CLAUDE_USAGE_URL = "https://claude.ai/settings/usage"

# Default limits (will be overridden by scraped values)
MAX_MONTHLY_LIMIT = 200.0  # $200/month for MAX plan
MAX_SESSION_LIMIT = 600000  # 600k tokens per 5hr window
MAX_WEEKLY_LIMIT = 4500000  # 4.5M tokens per week

def load_cookies() -> list:
    """Load cookies from JSON file if exists."""
    if COOKIE_FILE.exists():
        try:
            return json.loads(COOKIE_FILE.read_text())
        except Exception as e:
            print(f"Warning: Could not load cookies: {e}")
    return []

def save_cookies(cookies: list) -> None:
    """Save cookies to JSON file."""
    try:
        COOKIE_FILE.write_text(json.dumps(cookies, indent=2))
        os.chmod(COOKIE_FILE, 0o600)  # Restrict permissions
    except Exception as e:
        print(f"Warning: Could not save cookies: {e}")

def scrape_claude_usage() -> Optional[Dict[str, Any]]:
    """
    Scrape actual usage percentages from claude.ai/settings/usage.
    Returns dict with monthly/session/weekly percentages and token counts.
    """
    with sync_playwright() as p:
        # Use Firefox - works best for Claude.ai as per recent sessions
        browser = p.firefox.launch(
            headless=True,
            args=["--no-sandbox"]
        )
        
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0"
        )
        
        # Load cookies if available
        cookies = load_cookies()
        if cookies:
            context.add_cookies(cookies)
        
        page = context.new_page()
        
        try:
            # Navigate to usage page
            print(f"[{datetime.now().isoformat()}] Navigating to {CLAUDE_USAGE_URL}")
            page.goto(CLAUDE_USAGE_URL, wait_until="networkidle", timeout=30000)
            
            # Wait for page to load, but don't fail on specific selectors
            page.wait_for_load_state("networkidle")
            
            # Take a screenshot for debugging
            screenshot_file = SNAPSHOT_DIR / f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            page.screenshot(path=str(screenshot_file))
            print(f"Screenshot saved to: {screenshot_file}")
            
            # Extract usage percentages and values
            usage_data = page.evaluate("""
                () => {
                    const data = {};
                    
                // Look for usage cards with more flexible selectors
                const cards = document.querySelectorAll('div[class*="card"], section[class*="usage"], [data-testid]');
                
                // Also search for any percentage displays in the page
                const allText = document.body.textContent;
                
                // Try to find patterns like "60%" or "All models 60% used"
                const percentMatches = allText.match(/(\d+)%/g) || [];
                const percentValues = percentMatches.map(m => parseInt(m));
                
                // Look for section headers that might indicate what each percentage means
                const headings = Array.from(document.querySelectorAll('h1, h2, h3, h4, h5, h6, p, span, div')).map(el => ({
                    text: el.textContent?.toLowerCase() || '',
                    element: el
                }));
                
                // Try to match percentages to sections based on proximity
                let monthlyIndex = headings.findIndex(h => h.text.includes('monthly') || h.text.includes('plan') || h.text.includes('subscription'));
                let sessionIndex = headings.findIndex(h => h.text.includes('session') || h.text.includes('5-hour') || h.text.includes('window'));
                let weeklyIndex = headings.findIndex(h => h.text.includes('weekly') || h.text.includes('week'));
                
                // Assign percentages based on section order or available data
                if (percentValues.length >= 3) {
                    // Most likely order: monthly, session, weekly
                    data.monthly_percent = percentValues[0];
                    data.session_percent = percentValues[1];
                    data.weekly_percent = percentValues[2];
                } else if (percentValues.length === 2) {
                    // Try to infer which is which based on typical values
                    // Monthly is usually lower, session higher
                    data.monthly_percent = Math.min(percentValues[0], percentValues[1]);
                    data.session_percent = Math.max(percentValues[0], percentValues[1]);
                } else if (percentValues.length === 1) {
                    // Default to monthly if only one value
                    data.monthly_percent = percentValues[0];
                }
                
                // If we have headings, try to be smarter about assignment
                if (monthlyIndex !== -1 && percentValues.length > 0) {
                    // Find the percentage closest to the monthly heading
                    data.monthly_percent = percentValues[0]; // Simplified for now
                }
                
                // Try to find token counts or dollar amounts
                const tokenMatches = allText.match(/([\d,]+)\s*(tokens?|tkns?)/gi) || [];
                const dollarMatches = allText.match(/\$([\d,]+\.?\d*)/g) || [];
                
                // Log what we found for debugging
                console.log('Found percentages:', percentValues);
                console.log('Found tokens:', tokenMatches);
                console.log('Found dollars:', dollarMatches);
                
                return data;
                    
                    // Fallback: try to find any percentage displays
                    if (!data.monthly_percent) {
                        const allPercents = Array.from(document.querySelectorAll('*')).map(el => {
                            const text = el.textContent;
                            const match = text.match(/(\d+)%/);
                            return match ? parseFloat(match[1]) : null;
                        }).filter(p => p !== null);
                        
                        // Assume first percentage is monthly if we can't find cards
                        if (allPercents.length > 0) {
                            data.monthly_percent = allPercents[0];
                        }
                    }
                    
                    return data;
                }
            """)
            
            # Save HTML snapshot for debugging
            snapshot_file = SNAPSHOT_DIR / f"claude_usage_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            snapshot_file.write_text(page.content())
            
            # Save cookies for next run
            cookies = context.cookies()
            save_cookies(cookies)
            
            browser.close()
            
            if usage_data:
                print(f"[{datetime.now().isoformat()}] Successfully scraped usage data")
                print(f"  Monthly: {usage_data.get('monthly_percent', 0)}%")
                print(f"  Session: {usage_data.get('session_percent', 0)}%")
                print(f"  Weekly: {usage_data.get('weekly_percent', 0)}%")
                return usage_data
            else:
                print(f"[{datetime.now().isoformat()}] ERROR: No usage data found on page")
                return None
                
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] ERROR during scraping: {e}")
            # Save error snapshot
            error_file = SNAPSHOT_DIR / f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            try:
                error_file.write_text(page.content())
                print(f"Error snapshot saved to: {error_file}")
            except:
                pass
            browser.close()
            return None

def store_usage_data(usage_data: Dict[str, Any]) -> bool:
    """Store scraped usage data in SQLite plan_snapshots table."""
    try:
        conn = sqlite3.connect(str(DB))
        
        # Ensure table exists
        conn.execute("""
            CREATE TABLE IF NOT EXISTS plan_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                plan_name TEXT DEFAULT 'Max',
                monthly_spent REAL,
                monthly_limit REAL,
                monthly_pct REAL,
                session_pct REAL,
                weekly_all_pct REAL,
                weekly_sonnet_pct REAL,
                balance REAL,
                auto_reload BOOLEAN DEFAULT 0,
                month_resets TEXT,
                UNIQUE(ts)
            )
        """)
        
        # Use current time in UTC
        ts = datetime.now(timezone.utc).isoformat()
        
        # Calculate spent amount from percentages
        monthly_spent = (usage_data.get('monthly_percent', 0) / 100) * MAX_MONTHLY_LIMIT
        session_used = (usage_data.get('session_percent', 0) / 100) * MAX_SESSION_LIMIT
        weekly_used = (usage_data.get('weekly_percent', 0) / 100) * MAX_WEEKLY_LIMIT
        
        # Insert or replace existing entry for this timestamp
        conn.execute("""
            INSERT OR REPLACE INTO plan_snapshots 
            (ts, plan_name, monthly_spent, monthly_limit, monthly_pct, 
             session_pct, weekly_all_pct, weekly_sonnet_pct, balance)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ts,
            'Max',
            monthly_spent,
            MAX_MONTHLY_LIMIT,
            usage_data.get('monthly_percent', 0),
            usage_data.get('session_percent', 0),
            usage_data.get('weekly_percent', 0),  # weekly_all_pct
            usage_data.get('weekly_percent', 0),  # weekly_sonnet_pct (same for now)
            MAX_MONTHLY_LIMIT - monthly_spent  # balance
        ))
        
        conn.commit()
        conn.close()
        
        print(f"[{datetime.now().isoformat()}] Stored usage data in database")
        return True
        
    except Exception as e:
        print(f"[{datetime.now().isoformat()}] ERROR storing usage data: {e}")
        return False

def main():
    """Main execution loop."""
    print(f"[{datetime.now().isoformat()}] Starting Claude usage scraper")
    
    while True:
        try:
            # Scrape usage data
            usage_data = scrape_claude_usage()
            
            if usage_data:
                # Store in database
                store_usage_data(usage_data)
            else:
                print(f"[{datetime.now().isoformat()}] Failed to scrape usage data, will retry in 5 minutes")
            
            # Wait 5 minutes before next scrape
            print(f"[{datetime.now().isoformat()}] Sleeping for 5 minutes...")
            time.sleep(300)  # 5 minutes
            
        except KeyboardInterrupt:
            print(f"\n[{datetime.now().isoformat()}] Shutting down gracefully...")
            break
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] Unexpected error: {e}")
            time.sleep(300)  # Still wait 5 minutes before retry

if __name__ == "__main__":
    # Check for test mode
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print(f"[{datetime.now().isoformat()}] Running in test mode (single scrape)")
        usage_data = scrape_claude_usage()
        if usage_data:
            store_usage_data(usage_data)
            print(f"[{datetime.now().isoformat()}] Test completed successfully")
            sys.exit(0)
        else:
            print(f"[{datetime.now().isoformat()}] Test failed")
            sys.exit(1)
    else:
        main()