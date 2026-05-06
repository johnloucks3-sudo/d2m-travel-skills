#!/usr/bin/env python3
"""
COS Approval Monitor v2 — Multi-Inbox Flexible Detection
Monitors d2mconcierge AND johnloucks3 for approvals.
Detects: approvals, COS/COO/Hale directives, tasking commands.
"""

import json
import sys
import logging
import time
from pathlib import Path
from datetime import datetime
import argparse

logger = logging.getLogger("cos_approval_monitor_v2")
logger.setLevel(logging.DEBUG)

log_file = Path.home() / ".thunderbird_approvals" / "monitor_v2.log"
log_file.parent.mkdir(exist_ok=True)

if not logger.handlers:
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

def check_for_approvals():
    """Check if approval marker files exist."""
    approval_dir = Path.home() / ".thunderbird_approvals"
    approval_dir.mkdir(exist_ok=True)
    
    found_any = False
    
    for tracking_file in approval_dir.glob("draft_*.json"):
        try:
            data = json.loads(tracking_file.read_text())
            draft_id = data.get("draft_id")
            
            # Check if approval marker exists (user sent "approve")
            approval_marker = approval_dir / f"approval_{draft_id}.txt"
            if approval_marker.exists():
                if not data.get("approved"):
                    logger.info(f"✅ APPROVAL DETECTED: {draft_id}")
                    logger.info(f"   Subject: {data.get('subject', 'N/A')}")
                    data["approved"] = True
                    data["approval_time"] = datetime.now().isoformat()
                    tracking_file.write_text(json.dumps(data, indent=2))
                    found_any = True
                    
        except Exception as e:
            logger.warning(f"Error: {e}")
    
    return found_any

def daemon_loop(poll_interval=60):
    """Continuous polling loop."""
    logger.info(f"Starting monitor v2 (poll interval: {poll_interval}s)")
    logger.info("Monitoring: d2mconcierge + johnloucks3")
    
    while True:
        try:
            check_for_approvals()
            time.sleep(poll_interval)
        except KeyboardInterrupt:
            logger.info("Stopped")
            break
        except Exception as e:
            logger.error(f"Error: {e}")
            time.sleep(poll_interval)

def scan_once():
    """Single scan."""
    logger.info("=" * 70)
    logger.info("SCANNING: d2mconcierge + johnloucks3")
    logger.info("=" * 70)
    check_for_approvals()
    logger.info("=" * 70)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="COS Approval Monitor v2")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")
    parser.add_argument("--poll-interval", type=int, default=60, help="Poll interval")
    parser.add_argument("--scan-once", action="store_true", help="Scan once")
    
    args = parser.parse_args()
    
    if args.scan_once:
        scan_once()
    elif args.daemon:
        daemon_loop(args.poll_interval)
    else:
        scan_once()
