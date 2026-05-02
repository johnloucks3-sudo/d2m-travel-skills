"""
rate_guard_daemon.py
Rate-Limit Guard Daemon — Phase 2 Project #9
Dreams2Memories Travel, LLC | Thunderbird Wing

Run by systemd timer every 5 minutes.
Calls evaluate() → updates state file → sends Telegram on transitions.
"""

import logging
import sys
from pathlib import Path

# Ensure Thunderbird core is importable
sys.path.insert(0, str(Path("/home/john/Thunderbird")))

from core.ops.thunderbird_rate_limit_guard import evaluate

LOG_DIR = Path("/home/john/Thunderbird/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [rate_guard] %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "rate_limit_guard.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("rate_guard_daemon")


def main() -> None:
    logger.info("Rate-limit guard cycle starting")
    try:
        result = evaluate(send_alerts=True)
        logger.info(
            "State=%s  pct=%.1f%%  remaining=%s  degraded=%s",
            result["state"],
            result["weekly_pct"],
            f"{result['tokens_remaining']:,}",
            result["degradation_active"],
        )
        if result["transitioned"]:
            logger.info(
                "TRANSITION: %s → %s",
                result["prev_state"],
                result["state"],
            )
    except Exception as e:
        logger.error("Daemon cycle failed: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
