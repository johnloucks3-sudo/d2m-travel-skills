#!/usr/bin/env python3
"""
claude_manual_update.py — Bridge for manual Claude usage percentage input
Commander runs this to update actual percentages from claude.ai/settings/usage
"""
import sys
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB = Path.home() / "Thunderbird" / "storage" / "ai_costs.db"

def update_claude_percentages(monthly_pct: float, session_pct: float, weekly_pct: float) -> bool:
    """Update plan_snapshots table with manually entered percentages."""
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
        
        # Calculate spent amounts from percentages
        MAX_MONTHLY_LIMIT = 200.0
        MAX_SESSION_LIMIT = 600000
        MAX_WEEKLY_LIMIT = 4500000
        
        monthly_spent = (monthly_pct / 100) * MAX_MONTHLY_LIMIT
        session_used = (session_pct / 100) * MAX_SESSION_LIMIT
        weekly_used = (weekly_pct / 100) * MAX_WEEKLY_LIMIT
        
        # Insert manual update
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
            monthly_pct,
            session_pct,
            weekly_pct,
            weekly_pct,  # Same for sonnet weekly
            MAX_MONTHLY_LIMIT - monthly_spent,
            'manual'
        ))
        
        conn.commit()
        conn.close()
        
        print(f"✓ Updated Claude percentages at {ts}")
        print(f"  Monthly: {monthly_pct}%")
        print(f"  Session: {session_pct}%")
        print(f"  Weekly: {weekly_pct}%")
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def main():
    """Interactive prompt for manual percentage entry."""
    print("🦅 Claude Usage Manual Update")
    print("=" * 50)
    print("Visit: https://claude.ai/settings/usage")
    print("Enter the percentages you see:")
    print()
    
    try:
        monthly = float(input("Monthly plan usage (%): ").strip() or "0")
        session = float(input("5-hour session usage (%): ").strip() or "0")
        weekly = float(input("Weekly usage (%): ").strip() or "0")
        
        print()
        confirm = input(f"Update with: Monthly {monthly}%, Session {session}%, Weekly {weekly}%? [y/N]: ").strip().lower()
        
        if confirm == 'y':
            if update_claude_percentages(monthly, session, weekly):
                print("\n✅ Update successful! Dashboard will reflect changes in ~30 seconds.")
                sys.exit(0)
            else:
                print("\n❌ Update failed.")
                sys.exit(1)
        else:
            print("\nCancelled.")
            sys.exit(0)
            
    except KeyboardInterrupt:
        print("\n\nCancelled.")
        sys.exit(0)
    except ValueError:
        print("\n❌ Invalid input. Please enter numbers only.")
        sys.exit(1)

if __name__ == "__main__":
    main()