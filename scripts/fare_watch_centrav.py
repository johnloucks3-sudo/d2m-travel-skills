#!/usr/bin/env python3
"""
Centrav Flight Watch Runner — systemd entry point
Dreams2Memories Travel, LLC

Called by thunderbird-fare-watch.service (daily 08:00 MDT).
Runs price checks for all active flight fare watches via Centrav B2B.

Results written to: OpsCenter/fare_watches/last_check.json
Logs to: OpsCenter/fare_watches/fare_watch.log (via service stdout redirect)
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Ensure core/travel modules are importable
_TB = Path(__file__).resolve().parent.parent
_CORE_TRAVEL = _TB / "core" / "travel"
if str(_CORE_TRAVEL) not in sys.path:
    sys.path.insert(0, str(_CORE_TRAVEL))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("fare_watch_centrav")

from thunderbird_centrav_search import run_centrav_flight_watch_cycle  # noqa: E402


def main() -> int:
    logger.info("Centrav flight watch cycle starting")
    try:
        result = asyncio.run(run_centrav_flight_watch_cycle())
    except Exception as exc:
        logger.error("Cycle failed with exception: %s", exc, exc_info=True)
        return 1

    # Print full JSON to stdout (captured in fare_watch.log by service)
    print(json.dumps(result, indent=2))

    # Summary line for log readability
    ok = result.get("watches_checked", 0)
    total = result.get("watches_total", 0)
    n_alerts = len(result.get("alerts", []))
    n_errors = len(result.get("errors", []))
    n_warnings = len(result.get("warnings", []))
    logger.info(
        "Cycle complete: %d/%d checked, %d alert(s), %d error(s), %d warning(s)",
        ok, total, n_alerts, n_errors, n_warnings,
    )

    if result.get("alerts"):
        logger.warning("PRICE ALERTS TRIGGERED:")
        for a in result["alerts"]:
            logger.warning("  %s: %s", a.get("watch_id"), a.get("alert"))

    if result.get("warnings"):
        for w in result["warnings"]:
            logger.warning("  %s", w)

    return 0


if __name__ == "__main__":
    sys.exit(main())
