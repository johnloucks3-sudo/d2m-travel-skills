#!/usr/bin/env python3
"""
claude_usage_scraper_v2.py — Claude MAX usage via undetected-chromedriver
Bypasses Cloudflare bot detection using specialized Chrome patching.
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
    import undetected_chromedriver as uc
    from selenium.webdriver.support.ui import WebDriverWait
except ImportError:
    print("ERROR: undetected-chromedriver or selenium not installed.")
    print("Run: pip install undetected-chromedriver selenium")
    sys.exit(1)

# Paths
DB = Path.home() / "Thunderbird" / "storage" / "ai_costs.db"
SNAPSHOT_DIR = Path.home() / "Thunderbird" / "logs" / "claude_scraper_snapshots"
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

# Claude.ai usage page
CLAUDE_USAGE_URL = "https://claude.ai/settings/usage"

# Default limits
MAX_MONTHLY_LIMIT = 200.0  # $200/month for MAX plan
MAX_SESSION_LIMIT = 600000  # 600k tokens per 5hr window
MAX_WEEKLY_LIMIT = 4500000  # 4.5M tokens per week

def scrape_claude_usage() -> Optional[Dict[str, Any]]:
    """
    Scrape usage percentages from claude.ai/settings/usage using undetected-chromedriver.
    Specifically designed to bypass Cloudflare bot detection.
    """
    driver = None
    try:
        # Launch Chrome with undetected_chromedriver (patches to hide automation signals)
        print(f"[{datetime.now().isoformat()}] Launching undetected Chrome...")

        # Try to auto-detect Chrome or allow auto-download
        try:
            driver = uc.Chrome(
                headless=True,
                use_subprocess=False,
                version_main=None,  # Auto-detect Chrome version
            )
        except Exception as chrome_error:
            print(f"[{datetime.now().isoformat()}] Chrome auto-detect failed: {chrome_error}")
            # Try with explicit binary path search
            import shutil
            chrome_bin = shutil.which("chromium") or shutil.which("google-chrome") or shutil.which("chrome")
            if chrome_bin:
                print(f"[{datetime.now().isoformat()}] Found Chrome binary at: {chrome_bin}")
                driver = uc.Chrome(browser_executable_path=chrome_bin, headless=True, use_subprocess=False)
            else:
                print(f"[{datetime.now().isoformat()}] No Chrome binary found on system")
                raise chrome_error

        print(f"[{datetime.now().isoformat()}] Navigating to {CLAUDE_USAGE_URL}")
        driver.get(CLAUDE_USAGE_URL)

        # Wait for page to fully load (Cloudflare challenge + React render)
        # Try to wait for any percentage element to appear
        wait = WebDriverWait(driver, 30)

        # Wait for page to contain "%" indicating usage data has loaded
        wait.until(lambda d: "%" in d.page_source)

        print(f"[{datetime.now().isoformat()}] Page loaded, extracting usage data...")

        # Take screenshot for debugging
        screenshot_file = SNAPSHOT_DIR / f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        driver.save_screenshot(str(screenshot_file))
        print(f"Screenshot saved to: {screenshot_file}")

        # Extract usage data via JavaScript
        usage_data = driver.execute_script("""
            const data = {};

            // Get all text from page
            const pageText = document.body.innerText;

            // Look for percentage patterns (e.g., "73%", "5%", "45%")
            const percentMatches = pageText.match(/(\d+)%/g) || [];
            const percentValues = percentMatches.map(m => parseInt(m));

            // Log for debugging
            console.log('Found percentages:', percentValues);
            console.log('Full page text sample:', pageText.substring(0, 500));

            // Try to identify which percentage is which based on context
            let monthlyPct = null;
            let sessionPct = null;
            let weeklyPct = null;

            // Look for indicators in surrounding text
            const lines = pageText.split('\\n');

            for (let i = 0; i < lines.length; i++) {
                const line = lines[i].toLowerCase();
                const nextLine = (lines[i+1] || '').toLowerCase();
                const combinedLine = line + ' ' + nextLine;

                // Monthly usage pattern
                if ((line.includes('monthly') || line.includes('plan') || line.includes('month'))
                    && nextLine.match(/\\d+%/)) {
                    const pctMatch = (line + nextLine).match(/(\\d+)%/);
                    if (pctMatch) monthlyPct = parseInt(pctMatch[1]);
                }

                // Session usage pattern
                if ((line.includes('session') || line.includes('5') || line.includes('hour') || line.includes('window'))
                    && nextLine.match(/\\d+%/)) {
                    const pctMatch = (line + nextLine).match(/(\\d+)%/);
                    if (pctMatch) sessionPct = parseInt(pctMatch[1]);
                }

                // Weekly usage pattern
                if ((line.includes('week')) && nextLine.match(/\\d+%/)) {
                    const pctMatch = (line + nextLine).match(/(\\d+)%/);
                    if (pctMatch) weeklyPct = parseInt(pctMatch[1]);
                }
            }

            // Fallback: if we found 3+ percentages, assign in order (typical Claude UI: monthly, session, weekly)
            if (!monthlyPct && percentValues.length >= 3) {
                monthlyPct = percentValues[0];
                sessionPct = percentValues[1];
                weeklyPct = percentValues[2];
            } else if (!monthlyPct && percentValues.length >= 2) {
                // Heuristic: monthly is usually lower, session higher
                monthlyPct = Math.min(percentValues[0], percentValues[1]);
                sessionPct = Math.max(percentValues[0], percentValues[1]);
            } else if (!monthlyPct && percentValues.length >= 1) {
                monthlyPct = percentValues[0];
            }

            return {
                monthly_percent: monthlyPct || 0,
                session_percent: sessionPct || 0,
                weekly_percent: weeklyPct || 0,
                all_percentages: percentValues,
                raw_text_sample: pageText.substring(0, 1000)
            };
        """)

        # Save HTML snapshot
        snapshot_file = SNAPSHOT_DIR / f"claude_usage_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        snapshot_file.write_text(driver.page_source)
        print(f"HTML snapshot saved to: {snapshot_file}")

        if usage_data and (usage_data.get('monthly_percent') or usage_data.get('session_percent')):
            print(f"[{datetime.now().isoformat()}] Successfully scraped usage data:")
            print(f"  Monthly: {usage_data.get('monthly_percent', 0)}%")
            print(f"  Session: {usage_data.get('session_percent', 0)}%")
            print(f"  Weekly: {usage_data.get('weekly_percent', 0)}%")
            print(f"  All found: {usage_data.get('all_percentages', [])}")
            return usage_data
        else:
            print(f"[{datetime.now().isoformat()}] ERROR: No valid usage data extracted")
            print(f"  Raw data: {usage_data}")
            return None

    except Exception as e:
        print(f"[{datetime.now().isoformat()}] ERROR during scraping: {e}")
        if driver:
            try:
                error_file = SNAPSHOT_DIR / f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                error_file.write_text(driver.page_source)
                print(f"Error snapshot saved to: {error_file}")
            except:
                pass
        return None

    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

def store_usage_data(usage_data: Dict[str, Any], source: str = 'auto') -> bool:
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
                source TEXT DEFAULT 'auto',
                UNIQUE(ts)
            )
        """)

        ts = datetime.now(timezone.utc).isoformat()

        # Calculate spent amount from percentages
        monthly_spent = (usage_data.get('monthly_percent', 0) / 100) * MAX_MONTHLY_LIMIT

        # Insert or replace
        conn.execute("""
            INSERT OR REPLACE INTO plan_snapshots
            (ts, plan_name, monthly_spent, monthly_limit, monthly_pct,
             session_pct, weekly_all_pct, weekly_sonnet_pct, balance, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ts,
            'Max',
            monthly_spent,
            MAX_MONTHLY_LIMIT,
            usage_data.get('monthly_percent', 0),
            usage_data.get('session_percent', 0),
            usage_data.get('weekly_percent', 0),
            usage_data.get('weekly_percent', 0),
            MAX_MONTHLY_LIMIT - monthly_spent,
            source
        ))

        conn.commit()
        conn.close()

        print(f"[{datetime.now().isoformat()}] Stored usage data (source={source}) in database")
        return True

    except Exception as e:
        print(f"[{datetime.now().isoformat()}] ERROR storing usage data: {e}")
        return False

def main():
    """Main execution loop."""
    print(f"[{datetime.now().isoformat()}] Starting Claude usage scraper (v2 - undetected-chromedriver)")

    while True:
        try:
            usage_data = scrape_claude_usage()

            if usage_data:
                store_usage_data(usage_data, source='auto')
            else:
                print(f"[{datetime.now().isoformat()}] Failed to scrape, will retry in 5 minutes")

            print(f"[{datetime.now().isoformat()}] Sleeping for 5 minutes...")
            time.sleep(300)

        except KeyboardInterrupt:
            print(f"\n[{datetime.now().isoformat()}] Shutting down gracefully...")
            break
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] Unexpected error: {e}")
            time.sleep(300)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print(f"[{datetime.now().isoformat()}] Running in test mode (single scrape)")
        usage_data = scrape_claude_usage()
        if usage_data and (usage_data.get('monthly_percent') or usage_data.get('session_percent')):
            store_usage_data(usage_data, source='test')
            print(f"[{datetime.now().isoformat()}] Test completed successfully")
            sys.exit(0)
        else:
            print(f"[{datetime.now().isoformat()}] Test failed - no data extracted")
            sys.exit(1)
    else:
        main()
