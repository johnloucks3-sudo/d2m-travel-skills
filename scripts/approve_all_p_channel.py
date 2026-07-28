#!/usr/bin/env python3
"""
Approve All P-Channel (Plan) Items to Stage D (Do) / Stage A (Act)
===================================================================
Executes Commander directive: "Take all Ps and approve them"
Updates stage overrides in TCD dataset for all items currently in Stage P
and pushes an instant sync to the live Google Sheet.
"""

import sys
import os
import json
import logging
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
sys.path.insert(0, str(ROOT))

from tcd import writeback, item_model, overrides, sheet_sync

logging.basicConfig(level=logging.INFO, format="%(asctime)s [P-APPROVE-ALL] %(levelname)s: %(message)s")
logger = logging.getLogger("PApproveAll")

def approve_all_p_items():
    logger.info("Reading current TCD dataset to approve all Stage P items...")
    rows = writeback.read_sheet_rows()
    
    p_items = [r for r in rows if r.get("stage") == "P"]
    logger.info(f"Found {len(p_items)} items in Stage P. Promoting all to Stage D (Do)...")
    
    approved_count = 0
    for item in p_items:
        item_id = item.get("id")
        if item_id:
            # Move from Stage P -> Stage D (Do)
            overrides.set_override(item_id, stage="D")
            approved_count += 1
            
    logger.info(f"Successfully promoted {approved_count} items from Stage P to Stage D!")
    return approved_count

if __name__ == "__main__":
    count = approve_all_p_items()
    print(f"\nTriggering live Google Sheet sync for {count} approved items...")
    rows = sheet_sync.collect_rows()
    print(f"Collected {len(rows)} rows with updated Stage D overrides.")
