"""
Fare Watch Integration — Connects fare watch system with price monitoring

Bridges the gap between:
- thunderbird_fare_watch.py (watch management)
- thunderbird_price_monitor.py (price checking)
- thunderbird_scheduler.py (automation)

Provides actual price checking for fare watches instead of just logging.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

# Import both systems
import sys

sys.path.insert(0, "/home/john/Thunderbird/core/intel")
from thunderbird_fare_watch import list_watches, check_fare
from thunderbird_price_monitor import check_current_prices

logger = logging.getLogger(__name__)


def convert_fare_watch_to_departure(watch: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a fare watch entry to price monitor departure format."""
    label = watch.get("label", "")

    # Extract cruise line and ship from label
    cruise_line = "Unknown"
    ship = "Unknown"
    route = "Unknown"

    # Parse common patterns from fare watch labels
    if "Regent" in label:
        cruise_line = "Regent Seven Seas"
        if "Grandeur" in label:
            ship = "SS Grandeur"
        elif "Splendor" in label:
            ship = "SS Splendor"
    elif "Viking" in label:
        cruise_line = "Viking"
        if "Mars" in label:
            ship = "Viking Mars"
    elif "Silversea" in label:
        cruise_line = "Silversea"
        if "Nova" in label:
            ship = "Silver Nova"
        elif "Muse" in label:
            ship = "Silver Muse"

    # Extract route from label
    if "Scandinavia" in label:
        route = "Scandinavia"
    elif "Panama Canal" in label:
        route = "Panama Canal"
    elif "Mediterranean" in label:
        route = "Mediterranean"
    elif "Trans-Pacific" in label:
        route = "Trans-Pacific"
    elif "Lesser Antilles" in label:
        route = "Lesser Antilles"

    # Extract departure date from travel_date
    travel_date = watch.get("travel_date", "")

    return {
        "cruise_line": cruise_line,
        "ship": ship,
        "departure": travel_date,
        "route": route,
        "watch_id": watch.get("id"),
        "baseline_price": watch.get("baseline_price_pp", 0),
        "passengers": watch.get("passengers", 2),
    }


def check_all_fare_watch_prices() -> Dict[str, Any]:
    """Check current prices for all active fare watches."""
    logger.info("Checking prices for all active fare watches")

    # Get all active watches
    result = list_watches(active_only=True)
    watches = result.get("watches", [])

    if not watches:
        logger.info("No active fare watches to check")
        return {"status": "success", "checked": 0, "updated": 0}

    # Convert to price monitor format
    departures = []
    for watch in watches:
        departure = convert_fare_watch_to_departure(watch)
        if departure["departure"] and departure["cruise_line"] != "Unknown":
            departures.append(departure)

    if not departures:
        logger.info("No valid cruise departures found in fare watches")
        return {"status": "success", "checked": 0, "updated": 0}

    logger.info(f"Checking prices for {len(departures)} cruise departures")

    # Use price monitor to check current prices
    results = check_current_prices(departures)

    updated_count = 0
    alerts = []

    # Update fare watch with current prices
    for result in results:
        watch_id = result.get("watch_id")
        current_price = result.get("current_price")

        if watch_id and current_price:
            try:
                # Record the price check in fare watch system
                check_result = check_fare(watch_id, current_price)
                if check_result.get("status") == "success":
                    updated_count += 1

                    # Check if this triggered any alerts
                    alert = check_result.get("alert")
                    if alert:
                        alerts.append(
                            {
                                "watch_id": watch_id,
                                "alert": alert,
                                "current_price": current_price,
                                "baseline": result.get("baseline_price"),
                            }
                        )

            except Exception as e:
                logger.error(f"Failed to update fare watch {watch_id}: {e}")

    return {
        "status": "success",
        "checked": len(departures),
        "updated": updated_count,
        "alerts": alerts,
        "timestamp": datetime.now().isoformat(),
    }


def register_fare_watch_integration_tools(mcp: Any):
    """Register integration tools with MCP server."""

    @mcp.tool()
    def fare_watch_check_all_prices() -> Dict[str, Any]:
        """Check current prices for all active fare watches."""
        return check_all_fare_watch_prices()

    @mcp.tool()
    def fare_watch_get_alerts() -> Dict[str, Any]:
        """Get current fare watch alerts (price drops/spikes)."""
        result = list_watches(active_only=True)
        alerts = []

        for watch in result.get("watches", []):
            vs_baseline = watch.get("vs_baseline", "")
            if vs_baseline.startswith(("+", "-")):
                alerts.append(
                    {
                        "watch_id": watch.get("id"),
                        "label": watch.get("label"),
                        "change": vs_baseline,
                        "current_price": watch.get("current_price_pp"),
                        "baseline": watch.get("baseline_price_pp"),
                    }
                )

        return {"status": "success", "alerts": alerts, "count": len(alerts)}


if __name__ == "__main__":
    # Test the integration
    result = check_all_fare_watch_prices()
    print(
        f"Checked {result['checked']} departures, updated {result['updated']} watches"
    )
    if result["alerts"]:
        print(f"Alerts: {len(result['alerts'])}")
        for alert in result["alerts"]:
            print(f"  {alert['watch_id']}: {alert['alert']}")
