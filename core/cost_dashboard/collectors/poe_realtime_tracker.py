#!/usr/bin/env python3
"""
Poe API real-time points tracker.
Tracks baseline (40,090 used / 660,000 limit) and adds delta from /logs/poe_api_calls.jsonl
Updates dashboard without scraping (avoids Cloudflare blocks).
"""
import os, sqlite3, json
from datetime import datetime, timezone
from pathlib import Path

DB = Path.home() / "Thunderbird" / "storage" / "ai_costs.db"
POE_LOG = Path.home() / "Thunderbird" / "logs" / "poe_api_calls.jsonl"

# Baseline (from manual check 2026-05-19 22:00)
BASELINE_USED = 40090
BASELINE_BALANCE = 557610
BASELINE_LIMIT = 660000

def get_poe_calls_since_baseline():
    """Count Poe API calls logged since baseline was taken."""
    if not POE_LOG.exists():
        return []
    
    calls = []
    try:
        with open(POE_LOG) as f:
            for line in f:
                if line.strip():
                    try:
                        entry = json.loads(line)
                        # Entry format: {"timestamp": "...", "points": 100, "model": "..."}
                        calls.append(entry)
                    except:
                        pass
    except Exception as e:
        print(f"ERROR reading log: {e}")
    
    return calls

def compute_poe_state():
    """Compute current Poe state from baseline + logged calls."""
    calls = get_poe_calls_since_baseline()
    
    # Sum points from all calls
    total_points_logged = sum(c.get("points", 0) for c in calls)
    
    # Current state
    points_used_current = BASELINE_USED + total_points_logged
    points_balance_current = BASELINE_LIMIT - points_used_current
    pct_used = (points_used_current / BASELINE_LIMIT * 100)
    
    # Model breakdown
    model_counts = {}
    for call in calls:
        model = call.get("model", "unknown")
        model_counts[model] = model_counts.get(model, 0) + call.get("points", 0)
    
    return {
        "baseline_used": BASELINE_USED,
        "logged_calls": total_points_logged,
        "points_used_current": points_used_current,
        "points_balance_current": points_balance_current,
        "points_limit": BASELINE_LIMIT,
        "pct_used": pct_used,
        "num_calls": len(calls),
        "model_breakdown": model_counts,
        "last_call": calls[-1] if calls else None,
    }

def store_snapshot(state):
    """Store computed state in SQLite."""
    conn = sqlite3.connect(str(DB))
    ts = datetime.now(timezone.utc).isoformat()
    
    # Get top model for logging
    top_model = max(state.get("model_breakdown", {}).items(), key=lambda x: x[1], default=("unknown", 0))
    
    conn.execute("""
        INSERT OR REPLACE INTO poe_snapshots 
        (ts, points_balance, points_used_month, points_limit, points_pct_used, 
         source, model_gemini_flash, model_kimi_k2)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        ts,
        state["points_balance_current"],
        state["points_used_current"],
        state["points_limit"],
        state["pct_used"],
        "computed",
        state["model_breakdown"].get("gemini-2-5-flash", 0),
        state["model_breakdown"].get("kimi-k2", 0),
    ))
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    state = compute_poe_state()
    
    print("=" * 60)
    print("POE REALTIME TRACKER")
    print("=" * 60)
    print(f"Baseline (2026-05-19): {BASELINE_USED:,} / {BASELINE_LIMIT:,} used")
    print(f"Logged since:         +{state['logged_calls']:,} points ({state['num_calls']} calls)")
    print(f"Current:              {state['points_used_current']:,} / {BASELINE_LIMIT:,} ({state['pct_used']:.2f}%)")
    print(f"Remaining:            {state['points_balance_current']:,} points")
    print(f"\nModel breakdown:")
    for model, points in state["model_breakdown"].items():
        print(f"  {model}: {points:,} points")
    
    if state["last_call"]:
        print(f"\nLast call: {state['last_call'].get('timestamp')} ({state['last_call'].get('model')})")
    
    print("\nStoring snapshot...")
    store_snapshot(state)
    print("✓ Done")
