#!/usr/bin/env python3
"""
TESS Token Keepalive — called by tess-token-keepalive.timer every 90 min.

Checks token expiry. If within 30 minutes of expiring, refreshes via
TESSAuth.refresh_token() and saves the new token to tess_token.json.
Exits 0 on success, 1 on failure (timer logs the exit code).
"""
import logging
import sys
import time
from pathlib import Path

THUNDERBIRD = Path("/home/john/Thunderbird")
sys.path.insert(0, str(THUNDERBIRD / "core" / "booking"))
sys.path.insert(0, str(THUNDERBIRD))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(THUNDERBIRD / "logs" / "tess_keepalive.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("tess_keepalive")

REFRESH_THRESHOLD_SECONDS = 30 * 60  # refresh if <30 min remaining


def main() -> int:
    try:
        from thunderbird_tess import TESSAuth  # type: ignore
    except ImportError as e:
        logger.error("Cannot import TESSAuth: %s", e)
        return 1

    auth = TESSAuth()

    if not auth._tokens:
        logger.error("No token on disk — manual re-injection required")
        logger.error("Run: python3 core/booking/thunderbird_tess.py --inject-token '<localStorage blob>'")
        return 1

    expires_at = auth._tokens.get("expires_at")
    if expires_at is None:
        # No expiry info — try refresh proactively
        logger.warning("No expires_at in token — refreshing proactively")
    else:
        remaining = float(expires_at) - time.time()
        if remaining > REFRESH_THRESHOLD_SECONDS:
            logger.info(
                "Token healthy — %.0f min remaining (refresh threshold: %d min). No action.",
                remaining / 60,
                REFRESH_THRESHOLD_SECONDS // 60,
            )
            return 0
        logger.info("Token expires in %.0f min — refreshing now", remaining / 60)

    ok = auth.refresh_token()
    if ok:
        new_exp = auth._tokens.get("expires_at", 0)
        new_remaining = float(new_exp) - time.time()
        logger.info(
            "TESS token refreshed. New expiry in %.1f hours (CONFIRMED:TESS)",
            new_remaining / 3600,
        )
        return 0
    else:
        logger.error("Token refresh FAILED — manual re-injection may be required")
        return 1


if __name__ == "__main__":
    sys.exit(main())
