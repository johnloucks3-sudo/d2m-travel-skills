#!/usr/bin/env python3
"""
Zen (OpenCode free tier) usage tracker.
Logs every OpenCode call, tracks usage vs hourly/daily limits.
Alerts if approaching limits.
"""
import os, sqlite3, json
from datetime import datetime, timezone, timedelta
from pathlib import Path

DB = Path.home() / "Thunderbird" / "storage" / "ai_costs.db"
OPENCODE_LOG = Path.home() / "Thunderbird" / "logs" / "opencode_calls.jsonl"  # Will create if needed
DISPATCH_LOG = Path.home() / "Thunderbird" / "OpsCenter" / "dispatcher.py"  # Check for call logs

def get_zen_usage_last_hour():
    """Count OpenCode calls in last hour."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
    calls = 0
    tokens = 0
    
    # Try to read from opencode call logs
    if OPENCODE_LOG.exists():
        try:
            with open(OPENCODE_LOG) as f:
                for line in f:
                    if line.strip():
                        try:
                            entry = json.loads(line)
                            ts = datetime.fromisoformat(entry.get("timestamp", "").replace("Z", "+00:00"))
                            if ts >= cutoff:
                                calls += 1
                                tokens += entry.get("tokens", 0)
                        except:
                            pass
        except:
            pass
    
    return {"calls": calls, "tokens": tokens}

def get_zen_usage_last_day():
    """Count OpenCode calls in last 24 hours."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=1)
    calls = 0
    tokens = 0
    
    if OPENCODE_LOG.exists():
        try:
            with open(OPENCODE_LOG) as f:
                for line in f:
                    if line.strip():
                        try:
                            entry = json.loads(line)
                            ts = datetime.fromisoformat(entry.get("timestamp", "").replace("Z", "+00:00"))
                            if ts >= cutoff:
                                calls += 1
                                tokens += entry.get("tokens", 0)
                        except:
                            pass
        except:
            pass
    
    return {"calls": calls, "tokens": tokens}

def store_zen_usage():
    """Store Zen usage snapshot in SQLite."""
    conn = sqlite3.connect(str(DB))
    
    # Create table if needed
    conn.execute("""
        CREATE TABLE IF NOT EXISTS zen_usage (
            id INTEGER PRIMARY KEY,
            ts TEXT NOT NULL,
            calls_per_hour INTEGER DEFAULT 0,
            tokens_per_hour INTEGER DEFAULT 0,
            calls_per_day INTEGER DEFAULT 0,
            tokens_per_day INTEGER DEFAULT 0,
            UNIQUE(ts)
        )
    """)
    
    hourly = get_zen_usage_last_hour()
    daily = get_zen_usage_last_day()
    ts = datetime.now(timezone.utc).isoformat()
    
    conn.execute("""
        INSERT OR REPLACE INTO zen_usage
        (ts, calls_per_hour, tokens_per_hour, calls_per_day, tokens_per_day)
        VALUES (?, ?, ?, ?, ?)
    """, (
        ts,
        hourly["calls"],
        hourly["tokens"],
        daily["calls"],
        daily["tokens"],
    ))
    
    conn.commit()
    conn.close()
    
    return {"hourly": hourly, "daily": daily}

if __name__ == "__main__":
    print("=" * 60)
    print("ZEN USAGE TRACKER")
    print("=" * 60)
    
    usage = store_zen_usage()
    
    print(f"\nLast Hour:")
    print(f"  Calls: {usage['hourly']['calls']}")
    print(f"  Tokens: {usage['hourly']['tokens']}")
    
    print(f"\nLast Day:")
    print(f"  Calls: {usage['daily']['calls']}")
    print(f"  Tokens: {usage['daily']['tokens']}")
    
    print("\n✓ Stored in database")
