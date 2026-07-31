#!/usr/bin/env python3
"""Poe API burn rate monitor. Tracks daily points and alerts Commander."""
import os, sqlite3, json
from datetime import datetime, timezone, timedelta
from pathlib import Path

DB = Path.home() / "Thunderbird" / "storage" / "ai_costs.db"
POE_LOG = Path.home() / "Thunderbird" / "logs" / "poe_api_calls.jsonl"

DAILY_BURN_ALERT = 5000
WEEKLY_BURN_ALERT = 30000

def get_daily_burn():
    if not POE_LOG.exists():
        return 0
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    daily = 0
    try:
        with open(POE_LOG) as f:
            for line in f:
                if line.strip():
                    try:
                        entry = json.loads(line)
                        ts = datetime.fromisoformat(entry.get("timestamp", "").replace("Z", "+00:00"))
                        if ts >= cutoff:
                            daily += entry.get("points", 0)
                    except:
                        pass
    except:
        pass
    return daily

def get_weekly_burn():
    if not POE_LOG.exists():
        return 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    weekly = 0
    try:
        with open(POE_LOG) as f:
            for line in f:
                if line.strip():
                    try:
                        entry = json.loads(line)
                        ts = datetime.fromisoformat(entry.get("timestamp", "").replace("Z", "+00:00"))
                        if ts >= cutoff:
                            weekly += entry.get("points", 0)
                    except:
                        pass
    except:
        pass
    return weekly

def get_balance():
    conn = sqlite3.connect(str(DB))
    row = conn.execute("SELECT points_balance, points_used_month FROM poe_snapshots ORDER BY ts DESC LIMIT 1").fetchone()
    conn.close()
    return {"balance": row[0], "used": row[1]} if row else {"balance": 0, "used": 0}

def check_alerts():
    daily = get_daily_burn()
    weekly = get_weekly_burn()
    state = get_balance()
    alerts = []
    
    if daily > DAILY_BURN_ALERT:
        alerts.append(f"⚠️  POE DAILY: {daily:,} pts > {DAILY_BURN_ALERT:,} threshold")
    if weekly > WEEKLY_BURN_ALERT:
        alerts.append(f"⚠️  POE WEEKLY: {weekly:,} pts > {WEEKLY_BURN_ALERT:,} threshold")
    
    if (state["balance"] or 0) > 0 and daily > 0:
        days_left = state["balance"] / daily
        if days_left < 7:
            alerts.append(f"🔴 POE DEPLETES in {days_left:.1f}d at {daily:,}/day")
    
    return alerts, {"daily": daily, "weekly": weekly, "balance": state["balance"], "used": state["used"]}

if __name__ == "__main__":
    alerts, metrics = check_alerts()
    print("POE BURN MONITOR")
    print(f"24h: {metrics['daily'] or 0:,} | 7d: {metrics['weekly'] or 0:,} | Balance: {metrics['balance'] or 0:,}")
    if alerts:
        for a in alerts:
            print(f"  {a}")
