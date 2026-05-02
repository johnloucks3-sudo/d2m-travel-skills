#!/usr/bin/env python3
"""
SPSA Weekly Brief Job — Runs Monday 0700 MT
Generates retrospective of cases closed in past week + lessons learned
Sends via Gmail to Commander
"""

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.hale.hale_template_brief import save_weekly_brief_to_file

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - spsa_weekly - %(levelname)s - %(message)s"
)
logger = logging.getLogger("spsa_weekly")


def main():
    logger.info("=== SPSA WEEKLY BRIEF JOB STARTING ===")

    try:
        brief_path = save_weekly_brief_to_file()
        logger.info(f"✅ Weekly brief generated: {brief_path}")

        # Read content
        content = Path(brief_path).read_text()

        # Send via Telegram C2
        try:
            from OpsCenter.spsa_telegram_c2 import send_telegram_c2_alert
            send_telegram_c2_alert(
                message=f"**WEEKLY RETROSPECTIVE** — SPSA Cases & Lessons\n\n{content}",
                subject="SPSA Weekly Lessons"
            )
            logger.info("✅ Weekly brief sent via Telegram")
        except Exception as e:
            logger.warning(f"Telegram send failed: {e}")

        logger.info("=== SPSA WEEKLY BRIEF JOB COMPLETE ===")
        return 0

    except Exception as e:
        logger.error(f"Weekly brief generation failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
