#!/usr/bin/env python3
"""
spencer_grandtour_artifact_refresh.py — injects real fare_history.json
data into output/spencer_grandtour_2027_flight_options.html's
FARE_HISTORY_DATA array. Mirrors loucks_silvernova_artifact_refresh.py.

Run after scripts/spencer_grandtour_flight_daily_recheck.py.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
FARE_HISTORY = ROOT / "core" / "travel" / "data" / "fare_history.json"
ARTIFACT = ROOT / "output" / "spencer_grandtour_2027_flight_options.html"

WATCH_IDS = {
    "spencer-leg1-den-fco-tim-business-jun2027",
    "spencer-leg1-den-fco-yaggispencer-pe-jun2027",
    "spencer-leg2-fco-den-tim-business-jun2027",
    "spencer-leg3-zrh-den-yaggispencer-pe-jul2027",
}


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
