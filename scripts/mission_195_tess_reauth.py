#!/usr/bin/env python3
"""
MISSION-195: Re-authenticate TESS and confirm received-commission baseline
============================================================================

Executes:
1. TESS token refresh (ensures fresh JWT)
2. Pull commission summary from TESS CheckReceived endpoint
3. Update hale_state.json financial_pulse with received commission baseline
4. Report findings

Usage:
    python3 scripts/mission_195_tess_reauth.py
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

THUNDERBIRD = Path.home() / "Thunderbird"
sys.path.insert(0, str(THUNDERBIRD))
sys.path.insert(0, str(THUNDERBIRD / "core" / "booking"))

from thunderbird_tess import TESSClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s MISSION-195 %(levelname)s %(message)s",
)
logger = logging.getLogger("mission_195")

HALE_STATE = THUNDERBIRD / "hale_state.json"
TOKEN_FILE = THUNDERBIRD / "tess_token.json"


def load_hale_state() -> dict:
    """Load current hale_state.json."""
    if not HALE_STATE.exists():
        logger.warning(f"{HALE_STATE} not found — creating new")
        return {}
    try:
        return json.loads(HALE_STATE.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error(f"Failed to load hale_state.json: {e}")
        return {}


def save_hale_state(state: dict) -> None:
    """Save hale_state.json with updated financial pulse."""
    try:
        HALE_STATE.write_text(json.dumps(state, indent=2), encoding="utf-8")
        logger.info(f"Updated {HALE_STATE}")
    except Exception as e:
        logger.error(f"Failed to save hale_state.json: {e}")


def main():
    logger.info("=" * 70)
    logger.info("MISSION-195: TESS Re-authentication & Commission Baseline")
    logger.info("=" * 70)

    # Step 1: Verify token file exists
    if not TOKEN_FILE.exists():
        logger.error(f"TESS token file not found: {TOKEN_FILE}")
        logger.error("Run: bash scripts/tess_authorize.sh first")
        return False

    logger.info(f"✓ Token file found: {TOKEN_FILE}")

    # Step 2: Initialize TESS client
    try:
        client = TESSClient()
        logger.info("✓ TESS client initialized")
    except Exception as e:
        logger.error(f"Failed to initialize TESS client: {e}")
        return False

    # Step 3: Verify authentication
    token = client.auth.get_valid_token()
    if not token:
        logger.error("No valid TESS token available")
        return False
    logger.info("✓ Valid token obtained")

    # Step 4: Pull commission summary
    logger.info("\nFetching commission summary from TESS...")
    try:
        summary = client.get_commission_summary()
        if "error" in summary:
            logger.error(f"Commission summary error: {summary['error']}")
            return False
    except Exception as e:
        logger.error(f"Failed to fetch commission summary: {e}")
        return False

    logger.info("✓ Commission summary retrieved from TESS")
    logger.info(f"\n  Total checks received: {summary.get('checks_received_count', 0)}")
    logger.info(f"  Total received: ${summary.get('total_received', 0):.2f}")
    logger.info(f"  Total earned: ${summary.get('total_earned', 0):.2f}")
    logger.info(f"  Total paid: ${summary.get('total_paid', 0):.2f}")
    logger.info(f"  Total due: ${summary.get('total_due', 0):.2f}")
    logger.info(f"  Booking count: {summary.get('booking_count', 0)}")

    # Step 5: Update hale_state.json financial_pulse
    logger.info("\nUpdating hale_state.json financial pulse...")
    state = load_hale_state()

    if "financial_pulse" not in state:
        state["financial_pulse"] = {}

    pulse = state["financial_pulse"]
    pulse["last_checked"] = datetime.utcnow().isoformat() + "Z"
    pulse["tess_auth_status"] = "ONLINE"
    pulse["tess_checks_received"] = summary.get("checks_received_count", 0)
    pulse["tess_received"] = round(summary.get("total_received", 0), 2)
    pulse["tess_earned"] = round(summary.get("total_earned", 0), 2)
    pulse["tess_paid"] = round(summary.get("total_paid", 0), 2)
    pulse["tess_due"] = round(summary.get("total_due", 0), 2)
    pulse["tess_booking_count"] = summary.get("booking_count", 0)

    save_hale_state(state)
    logger.info("✓ hale_state.json updated with commission baseline")

    # Step 6: Report summary
    logger.info("\n" + "=" * 70)
    logger.info("MISSION-195 COMPLETE")
    logger.info("=" * 70)
    logger.info(f"\nReceived Commission Baseline (as of {pulse['last_checked']}):")
    logger.info(f"  Total received: ${pulse['tess_received']:.2f}")
    logger.info(f"  Checks received: {pulse['tess_checks_received']}")
    logger.info(f"\nFinancial pulse ready for Harlan reconciliation.")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
