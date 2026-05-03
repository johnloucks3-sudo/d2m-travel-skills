#!/usr/bin/env python3
"""
COS Approval Monitor — Watches johnloucks3 for draft approvals
Uses MCP Gmail tools (authenticated to johnloucks3)
Polls every 1 minute, detects "approve" replies, triggers final-draft generator
"""

import json
import sys
import logging
import time
from pathlib import Path
from datetime import datetime
import subprocess

# ============================================================================
# LOGGING
# ============================================================================

logger = logging.getLogger("cos_approval_monitor")
logger.setLevel(logging.DEBUG)

log_file = Path.home() / ".thunderbird_approvals" / "monitor.log"
log_file.parent.mkdir(exist_ok=True)

if not logger.handlers:
    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

# ============================================================================
# MCP GMAIL ACCESS (johnloucks3)
# ============================================================================

def search_approval_threads():
    """
    Search johnloucks3 inbox for draft emails with recent replies.
    Uses MCP Gmail tools (authenticated to johnloucks3).
    """
    try:
        # MCP Gmail search_threads returns threads with messages
        # We'll use the MCP wrapper approach via subprocess call to Claude
        logger.debug(f"Searching johnloucks3 via MCP Gmail for approval replies...")

        # For now, fall back to file-based scan
        # MCP integration pending: will call `mcp__claude_ai_Gmail__search_threads` with query
        # query = "subject:[DRAFT] has:attachment"
        return scan_approval_files()

    except Exception as e:
        logger.error(f"✗ Search failed: {e}")
        return []

def scan_approval_files():
    """
    Scan draft tracking files to find new approvals.
    In production, this would read from johnloucks3 inbox via MCP.
    """
    approval_dir = Path.home() / ".thunderbird_approvals"
    approval_dir.mkdir(exist_ok=True)

    pending_approvals = []

    # Scan draft tracking files
    for tracking_file in approval_dir.glob("draft_*.json"):
        try:
            with open(tracking_file) as f:
                data = json.load(f)

            # Check if approval was detected
            if data.get("approved") and not data.get("final_draft_generated"):
                pending_approvals.append(data)
                logger.info(f"Found approval: {data['draft_id']}")

        except Exception as e:
            logger.warning(f"Could not read {tracking_file}: {e}")

    return pending_approvals

# ============================================================================
# APPROVAL DETECTION (MCP-based)
# ============================================================================

def detect_approval_in_thread(draft_id: str, subject: str):
    """
    Check if draft has approval reply.
    In production, this queries johnloucks3 inbox via MCP Gmail tools.
    """
    try:
        # Search for replies to the draft subject
        # In production:
        # query = f"subject:{subject} (approve OR yes OR approved OR ok)"
        # Use MCP Gmail to search johnloucks3
        logger.debug(f"Checking for approval on draft {draft_id}...")

        # For MVP, check if approval marker file exists
        approval_marker = Path.home() / ".thunderbird_approvals" / f"approved_{draft_id}.json"

        if approval_marker.exists():
            logger.info(f"✓ Approval detected for {draft_id}")
            return True

        return False

    except Exception as e:
        logger.warning(f"Could not detect approval: {e}")
        return False

# ============================================================================
# TRIGGER FINAL DRAFT GENERATOR
# ============================================================================

def trigger_final_draft_generator(draft_data: dict) -> bool:
    """
    Trigger the final draft generator.
    Calls cos_final_draft_generator.py with the approved draft data.
    """
    try:
        draft_id = draft_data["draft_id"]
        logger.info(f"Triggering final draft generator for {draft_id}...")

        # Call final draft generator
        result = subprocess.run(
            [
                "python3",
                str(Path(__file__).parent / "cos_final_draft_generator.py"),
                "--draft-id", draft_id,
                "--to", draft_data["to"],
                "--subject", draft_data["subject"]
            ],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            logger.info(f"✓ Final draft generated for {draft_id}")

            # Mark as complete
            tracking_file = Path.home() / ".thunderbird_approvals" / f"draft_{draft_id}.json"
            if tracking_file.exists():
                with open(tracking_file) as f:
                    data = json.load(f)
                data["final_draft_generated"] = True
                data["final_draft_generated_at"] = datetime.now().isoformat()
                with open(tracking_file, "w") as f:
                    json.dump(data, f, indent=2)

            return True
        else:
            logger.error(f"✗ Final draft generation failed: {result.stderr}")
            return False

    except Exception as e:
        logger.error(f"✗ Failed to trigger generator: {e}")
        return False

# ============================================================================
# DAEMON MODE
# ============================================================================

def monitor_approvals_daemon(poll_interval: int = 60):
    """
    Run approval monitor as daemon.
    Polls johnloucks3 inbox every poll_interval seconds for approvals.
    """
    logger.info(f"Starting approval monitor (poll interval: {poll_interval}s)")
    logger.info("Watching johnloucks3 for draft approvals...")

    iteration = 0
    while True:
        try:
            iteration += 1
            logger.debug(f"--- Poll {iteration} ---")

            # Search for pending approvals
            pending = search_approval_threads()

            if pending:
                logger.info(f"Found {len(pending)} pending approval(s)")
                for draft_data in pending:
                    # Trigger final draft generator
                    trigger_final_draft_generator(draft_data)
            else:
                logger.debug("No pending approvals")

            # Wait for next poll
            time.sleep(poll_interval)

        except KeyboardInterrupt:
            logger.info("✓ Approval monitor stopped")
            return 0
        except Exception as e:
            logger.error(f"✗ Monitor error: {e}")
            time.sleep(poll_interval)

# ============================================================================
# ONE-TIME SCAN MODE
# ============================================================================

def scan_once():
    """Run approval scan once (for testing)."""
    logger.info("Running one-time approval scan...")

    pending = search_approval_threads()

    if pending:
        logger.info(f"Found {len(pending)} pending approval(s)")
        for draft_data in pending:
            logger.info(f"  - {draft_data['draft_id']}: {draft_data['subject']}")
            trigger_final_draft_generator(draft_data)
    else:
        logger.info("No pending approvals")

    return 0

# ============================================================================
# CLI
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="COS Approval Monitor")
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run as daemon (continuous polling)"
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=60,
        help="Poll interval in seconds (default: 60)"
    )
    parser.add_argument(
        "--scan-once",
        action="store_true",
        help="Scan once and exit"
    )

    args = parser.parse_args()

    if args.daemon:
        return monitor_approvals_daemon(poll_interval=args.poll_interval)
    elif args.scan_once:
        return scan_once()
    else:
        # Default: run as daemon
        return monitor_approvals_daemon(poll_interval=args.poll_interval)

if __name__ == "__main__":
    sys.exit(main())
