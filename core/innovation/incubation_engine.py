"""
core/innovation/incubation_engine.py — Autonomous ELON 2x Daily OODA + Whetstone Sweep Engine.

Rules:
1. Runs twice daily at 04:30 MT and 16:30 MT (Temporal Cron Schedule).
2. YOGA LOAD GUARD: Strictly blocked during Commander computer hours (06:30–10:30 MT).
3. Zero off-meter cost ($0.00).
"""

import datetime
import json
import logging
import os
import pytz
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger("incubation_engine")

BLACKOUT_START_HOUR = 6
BLACKOUT_START_MIN = 30
BLACKOUT_END_HOUR = 10
BLACKOUT_END_MIN = 30


def is_in_yoga_blackout_window() -> bool:
    """Checks if current Mountain Time is inside the 06:30–10:30 MT YOGA blackout window."""
    mt_tz = pytz.timezone("America/Denver")
    now_mt = datetime.datetime.now(mt_tz)
    
    start_time = now_mt.replace(hour=BLACKOUT_START_HOUR, minute=BLACKOUT_START_MIN, second=0, microsecond=0)
    end_time = now_mt.replace(hour=BLACKOUT_END_HOUR, minute=BLACKOUT_END_MIN, second=0, microsecond=0)
    
    return start_time <= now_mt <= end_time


def execute_elon_ooda_whetstone_sweep() -> Dict[str, Any]:
    """Executes the ELON autonomous 2x daily OODA + Whetstone sweep."""
    if is_in_yoga_blackout_window():
        logger.warning("YOGA LOAD GUARD ACTIVE: Blocked sweep during 06:30–10:30 MT Commander computer window.")
        return {
            "status": "BLOCKED_BLACKOUT_WINDOW",
            "reason": "YOGA Load Protection active during 06:30–10:30 MT.",
            "executed": False
        }

    logger.info("Starting ELON 2x Daily OODA + Whetstone Sweep...")
    
    # 1. Harvest candidate targets from catalog
    catalog_path = Path("/home/john/Thunderbird/storage/capability_targets_catalog.json")
    targets = []
    if catalog_path.exists():
        data = json.loads(catalog_path.read_text())
        targets = data.get("capabilities", [])

    # 2. Run Whetstone gap check
    gaps_found = [t for t in targets if "PENDING" in t.get("status", "")]

    # 3. Publish results via Executive Portal & Notification Gateway
    summary = f"ELON OODA Sweep Complete: {len(targets)} capabilities cataloged, {len(gaps_found)} open gaps monitored."
    
    try:
        from core.relay.notification_gateway import dispatch_notification
        dispatch_notification(
            subject="⚡ ELON 2x Daily OODA Sweep Report",
            content=summary,
            level="INFO"
        )
    except Exception as e:
        logger.warning(f"Notification gateway dispatch failed: {e}")

    return {
        "status": "SUCCESS",
        "targets_monitored": len(targets),
        "open_gaps": len(gaps_found),
        "executed": True,
        "timestamp": datetime.datetime.now().isoformat()
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    res = execute_elon_ooda_whetstone_sweep()
    print(json.dumps(res, indent=2))
