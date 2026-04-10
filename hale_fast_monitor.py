#!/usr/bin/env python3
"""
Hale Transformation Fast Monitor — 5-minute checks, 2-word summaries
"""

import time
import json
from pathlib import Path
from datetime import datetime


def check_hale_progress():
    """5-minute progress check with 2-word summary"""
    try:
        # Check decisions log
        decisions_path = Path("/home/john/Thunderbird/hale_decisions.md")
        if decisions_path.exists():
            decisions = decisions_path.read_text()
            decision_count = decisions.count("## DECISION:")
        else:
            decision_count = 0

        # Check brief format
        brief_path = Path("/home/john/Thunderbird/hale_brief.md")
        if brief_path.exists():
            brief = brief_path.read_text()
            has_handled = "I HANDLED THESE" in brief
        else:
            has_handled = False

        # Generate 2-word summary
        if decision_count >= 5 and has_handled:
            summary = "Phase1 Complete"
        elif decision_count > 0:
            summary = f"Decisions {decision_count}"
        elif has_handled:
            summary = "Brief Reformed"
        else:
            summary = "Starting Work"

        print(f"[{datetime.now().strftime('%H:%M')}] {summary}")

    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M')}] Monitor Error")


# Main loop
print("🦅 Hale Monitor: 5-min checks, 2-word summaries")
while True:
    check_hale_progress()
    time.sleep(300)  # 5 minutes
