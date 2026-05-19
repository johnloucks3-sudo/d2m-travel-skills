#!/usr/bin/env python3
"""
Real-time Poe API metrics collector.
Fetches user account status (points balance, subscription) and logs recent usage.
Stores snapshots in SQLite for dashboard.
"""
import os, sqlite3, json, requests
from datetime import datetime, timezone
from pathlib import Path

POE_API_KEY = os.getenv("POE_API_KEY")
POE_BASE_URL = os.getenv("POE_BASE_URL", "https://api.poe.com")
DB = Path.home() / "Thunderbird" / "storage" / "ai_costs.db"

def get_poe_subscription_info():
    """Fetch user subscription info from Poe API."""
    if not POE_API_KEY:
        print("ERROR: POE_API_KEY not set in .env")
        return None
    
    headers = {"Authorization": f"Bearer {POE_API_KEY}"}
    
    try:
        # Get user info
        resp = requests.get(f"{POE_BASE_URL}/user", headers=headers, timeout=10)
        resp.raise_for_status()
        user_data = resp.json()
        
        # Extract subscription info
        subscription = user_data.get("subscription", {})
        
        return {
            "points_balance": subscription.get("points_balance", 0),
            "points_limit": subscription.get("points_limit", 660000),
            "points_used": subscription.get("points_used", 0),
            "subscription_type": subscription.get("subscription_type", "unknown"),
            "billing_period_start": subscription.get("billing_period_start"),
            "billing_period_end": subscription.get("billing_period_end"),
            "raw": user_data
        }
    except Exception as e:
        print(f"ERROR fetching Poe subscription: {e}")
        return None

def store_poe_snapshot(poe_info):
    """Store Poe snapshot in SQLite."""
    if not poe_info:
        return
    
    conn = sqlite3.connect(str(DB))
    ts = datetime.now(timezone.utc).isoformat()
    
    points_balance = poe_info.get("points_balance", 0)
    points_limit = poe_info.get("points_limit", 660000)
    points_used = poe_info.get("points_used", 0)
    pct_used = (points_used / points_limit * 100) if points_limit else 0
    
    # Update latest snapshot (replaces previous)
    conn.execute("""
        INSERT OR REPLACE INTO poe_snapshots
        (ts, points_balance, points_limit, points_used, points_pct_used, subscription_type)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (ts, points_balance, points_limit, points_used, pct_used, poe_info.get("subscription_type", "unknown")))
    
    conn.commit()
    conn.close()
    
    print(f"[{ts}] Poe snapshot: {points_used:,}/{points_limit:,} points ({pct_used:.1f}%)")

if __name__ == "__main__":
    info = get_poe_subscription_info()
    if info:
        store_poe_snapshot(info)
        print(json.dumps(info, indent=2))
    else:
        print("Failed to fetch Poe info")
