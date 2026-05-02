#!/usr/bin/env python3
"""
SPSA EOD Brief Job — Runs daily at 1700 MT
Generates EOD summary of case activity for the day
Sends via Gmail to Commander
"""

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.hale.hale_template_brief import save_eod_brief_to_file

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - spsa_eod - %(levelname)s - %(message)s"
)
logger = logging.getLogger("spsa_eod")


def main():
    logger.info("=== SPSA EOD BRIEF JOB STARTING ===")

    try:
        brief_path = save_eod_brief_to_file()
        logger.info(f"✅ EOD brief generated: {brief_path}")

        # Read content
        content = Path(brief_path).read_text()

        # Send via Telegram C2 (same channel as AM brief)
        try:
            from OpsCenter.spsa_telegram_c2 import send_telegram_c2_alert
            send_telegram_c2_alert(
                message=f"**EOD BRIEF** — {Path(brief_path).name}\n\n{content[:2000]}",
                subject="SPSA EOD Summary"
            )
            logger.info("✅ Telegram notification sent")
        except Exception as e:
            logger.warning(f"Telegram send failed: {e}")

        logger.info("=== SPSA EOD BRIEF JOB COMPLETE ===")
        return 0

    except Exception as e:
        logger.error(f"EOD brief generation failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
