#!/usr/bin/env python3
"""
Sync live CC (Claude Code) usage telemetry into Thunderbird status boards.
Data provided directly by Commander:
  • 5h Usage: 3% (~2h left)
  • 7d Usage: 43% (~94h left)
  • Context: 82% Used
  • Model: Haiku 4.5
  • Version: v2.1.218
"""
import json
import datetime
from pathlib import Path

def sync_telemetry():
    cc_data = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "engine": "CC (Claude Code / TALON-3★)",
        "usage_5h_pct": 3.0,
        "usage_5h_remaining": "~2h",
        "usage_7d_pct": 43.0,
        "usage_7d_remaining": "~94h",
        "context_used_pct": 82.0,
        "active_model": "Haiku 4.5",
        "cli_version": "v2.1.218",
        "status": "NOMINAL"
    }
    
    out_file = Path("/home/john/Thunderbird/Personas/cc_live_telemetry.json")
    out_file.write_text(json.dumps(cc_data, indent=2))
    print(f"✅ Live CC Telemetry synced to {out_file}")

if __name__ == "__main__":
    sync_telemetry()
