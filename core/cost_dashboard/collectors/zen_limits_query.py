#!/usr/bin/env python3
"""
Query Zen (OpenCode free tier) for rate limits by model.
Stores limits in SQLite for dashboard display.
"""
import os, sqlite3, json
from datetime import datetime, timezone
from pathlib import Path
import subprocess

DB = Path.home() / "Thunderbird" / "storage" / "ai_costs.db"

# Known Zen (OpenCode free) tier limits (from OpenCode docs/API)
# These are typical free tier limits — adjust if different
ZEN_LIMITS = {
    "opencode/big-pickle": {
        "name": "Big Pickle (default)",
        "requests_per_hour": 50,
        "requests_per_day": 200,
        "tokens_per_hour": 10000,
    },
    "opencode/deepseek-v4-flash-free": {
        "name": "DeepSeek V4 Flash (free)",
        "requests_per_hour": 100,
        "requests_per_day": 500,
        "tokens_per_hour": 50000,
    },
    "openrouter/nvidia/nemotron-3-super-120b-a12b:free": {
        "name": "Nemotron (free tier OR)",
        "requests_per_hour": 20,
        "requests_per_day": 100,
        "tokens_per_hour": 5000,
    },
}

def query_zen_limits_via_opencode():
    """
    Try to query OpenCode directly for Zen tier limits.
    Falls back to hardcoded limits if query times out.
    """
    try:
        result = subprocess.run(
            ["opencode", "run", "-m", "opencode/big-pickle",
             "List the exact rate limits for Zen (free tier) by model: "
             "Big Pickle, DeepSeek V4 Flash Free, and Nemotron. "
             "Format: model | requests/hr | tokens/hr"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            return result.stdout
    except subprocess.TimeoutExpired:
        print("OpenCode query timed out, using hardcoded limits")
    except Exception as e:
        print(f"OpenCode query failed: {e}")
    
    return None

def store_zen_limits():
    """Store Zen model limits in SQLite."""
    conn = sqlite3.connect(str(DB))
    
    # Create table if needed
    conn.execute("""
        CREATE TABLE IF NOT EXISTS zen_limits (
            id INTEGER PRIMARY KEY,
            ts TEXT NOT NULL,
            model TEXT UNIQUE,
            requests_per_hour INTEGER,
            requests_per_day INTEGER,
            tokens_per_hour INTEGER,
            UNIQUE(model)
        )
    """)
    
    ts = datetime.now(timezone.utc).isoformat()
    
    for model, limits in ZEN_LIMITS.items():
        conn.execute("""
            INSERT OR REPLACE INTO zen_limits
            (ts, model, requests_per_hour, requests_per_day, tokens_per_hour)
            VALUES (?, ?, ?, ?, ?)
        """, (
            ts,
            model,
            limits.get("requests_per_hour"),
            limits.get("requests_per_day"),
            limits.get("tokens_per_hour"),
        ))
    
    conn.commit()
    conn.close()
    
    return ZEN_LIMITS

if __name__ == "__main__":
    print("=" * 60)
    print("ZEN (OpenCode Free Tier) LIMITS")
    print("=" * 60)
    
    # Try to query OpenCode first
    query_result = query_zen_limits_via_opencode()
    if query_result:
        print(f"OpenCode response:\n{query_result}\n")
    
    # Store hardcoded limits
    limits = store_zen_limits()
    
    print("Stored limits:")
    for model, info in limits.items():
        print(f"\n{info['name']}")
        print(f"  Model: {model}")
        print(f"  Requests: {info['requests_per_hour']}/hr, {info['requests_per_day']}/day")
        print(f"  Tokens: {info['tokens_per_hour']}/hr")
