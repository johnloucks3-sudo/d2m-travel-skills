#!/usr/bin/env python3
"""
loucks_silvernova_artifact_refresh.py — injects real fare_history.json
data into output/loucks_silvernova_2027_flight_options.html's
FARE_HISTORY_DATA array, so the trend chart + daily-snapshot table render
real captured data instead of staying empty.

Run after scripts/loucks_silvernova_flight_daily_recheck.py so the
artifact reflects the latest snapshot. Read-only against fare_history.json.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
FARE_HISTORY = ROOT / "core" / "travel" / "data" / "fare_history.json"
ARTIFACT = ROOT / "output" / "loucks_silvernova_2027_flight_options.html"

WATCH_IDS = {"den-muc-vce", "ath-ist-den", "ath-muc-den", "den-vce-direct"}


def main() -> None:
    history = json.loads(FARE_HISTORY.read_text()) if FARE_HISTORY.exists() else []
    relevant = [e for e in history if e.get("watch_id") in WATCH_IDS]

    html = ARTIFACT.read_text()
    data_js = json.dumps(relevant, indent=2)
    new_html = re.sub(
        r"const FARE_HISTORY_DATA = \[.*?\];",
        f"const FARE_HISTORY_DATA = {data_js};",
        html,
        count=1,
        flags=re.DOTALL,
    )
    if new_html == html:
        print("WARNING: FARE_HISTORY_DATA placeholder not found — artifact not updated")
        return
    ARTIFACT.write_text(new_html)
    print(f"injected {len(relevant)} history entries into {ARTIFACT}")


if __name__ == "__main__":
    main()
