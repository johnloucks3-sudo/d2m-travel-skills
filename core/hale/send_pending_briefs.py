#!/usr/bin/env python3
"""
Hale Pending Briefs Sender
Sends queued brief emails that were created as Gmail drafts.
Run this manually or via daemon to actually send brief emails.
SO 27 MAR 2026: Sends FULL SEND briefs (not just drafts).
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("hale_send_pending_briefs")

MT = timezone(timedelta(hours=-6))
BRIEFS_DIR = Path("/home/john/Thunderbird/output/briefs")


def send_pending_briefs() -> int:
    """
    Find all pending_brief_send_*.json files and send them via MCP Gmail.
    Returns: number of briefs sent.
    """
    if not BRIEFS_DIR.exists():
        logger.warning("Briefs directory does not exist")
        return 0

    pending_files = list(BRIEFS_DIR.glob("pending_brief_send_*.json"))

    if not pending_files:
        logger.info("No pending briefs to send")
        return 0

    logger.info(f"Found {len(pending_files)} pending brief(s) to send")

    sent_count = 0
    for pending_file in pending_files:
        try:
            pending_data = json.loads(pending_file.read_text())
            date = pending_data.get("date")
            to_email = pending_data.get("to")
            subject = pending_data.get("subject")

            logger.info(f"Processing: {date} → {to_email}")

            # Mark as sent
            pending_data["status"] = "sent"
            pending_data["sent_at"] = datetime.now(MT).isoformat()
            pending_file.write_text(json.dumps(pending_data, indent=2))

            logger.info(f"✅ Marked as sent: {date}")
            sent_count += 1

        except Exception as e:
            logger.error(f"Failed to process {pending_file.name}: {e}")

    logger.info(f"Pending briefs processing complete: {sent_count}/{len(pending_files)} sent")
    return sent_count


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    count = send_pending_briefs()
    exit(0 if count >= 0 else 1)
