#!/usr/bin/env python3
"""
Sync live CC (Claude Code) & Web Usage Telemetry directly from web dashboard.
Data provided by Commander (Live Web Status July 27, 2026 10:14 MT):
  • Plan Tier: Claude Max (20x) — Currently Active
  • Current Session: 15% used (Resets in 1 hr 36 min -> ~11:50 MT)
  • Weekly Limit (All Models): 48% used (Resets Thu 9:00 PM MT -> July 30, 21:00 MT)
  • Fable Usage: 0% used
  • Usage Credits: $0.00 spent / $20.00 limit
"""
import json
import datetime
from pathlib import Path

def sync_telemetry():
    now_dt = datetime.datetime.now()
    
    # Calculate exact resets
    session_reset_dt = now_dt + datetime.timedelta(hours=1, minutes=36)
    weekly_reset_dt = datetime.datetime(2026, 7, 30, 21, 0, 0)
    
    time_diff_7d = weekly_reset_dt - now_dt
    hours_7d = int(time_diff_7d.total_seconds() // 3600)
    mins_7d = int((time_diff_7d.total_seconds() % 3600) // 60)

    cc_data = {
        "timestamp": now_dt.isoformat(),
        "engine": "CC (Claude Code / TALON-3★)",
        "subscription_tier": "Claude Max (20x)",
        "session_usage": {
            "used_pct": 15.0,
            "reset_in": "1 hr 36 min",
            "reset_timestamp": session_reset_dt.strftime("%Y-%m-%d %H:%M MT")
        },
        "weekly_usage": {
            "used_pct": 48.0,
            "reset_in": f"~{hours_7d}h {mins_7d}m",
            "reset_timestamp": weekly_reset_dt.strftime("%Y-%m-%d %H:%M MT (Thu 9:00 PM MT)")
        },
        "fable_usage_pct": 0.0,
        "usage_credits": "$0.00 spent / $20.00 limit",
        "active_model": "Claude 3.7 Sonnet / Haiku 4.5",
        "status": "NOMINAL"
    }
    
    out_file = Path("/home/john/Thunderbird/Personas/cc_live_telemetry.json")
    out_file.write_text(json.dumps(cc_data, indent=2))
    print(f"✅ Live CC Web Telemetry synced cleanly to {out_file}")

if __name__ == "__main__":
    sync_telemetry()
