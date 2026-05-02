#!/usr/bin/env python3
"""
Thunderbird Fare Sweep — Automated Weekly Price Monitoring

Scheduled agent that runs weekly fare checks for all active watches.
Integrates with MCP fare_watch tools to check prices and trigger alerts.
Part of MISSION-011: Fare & Flight Research Protocol Implementation.

Usage:
    .venv/bin/python agents/thunderbird_fare_sweep.py
    
Schedule via systemd timer: weekly on Monday 08:00 MT for cruise watches, 
daily at 07:00 for flights within T-90 window.

Event-driven architecture:
1. Trigger: Weekly/Monday morning 
2. Check all active watches 
3. Query relevant APIs (flight search, cruise line scraping)
4. Log price changes 
5. Alert via Telegram if thresholds crossed
"""

import json
import logging
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import asyncio

# Add Thunderbird to path
THUNDERBIRD_DIR = Path.home() / "Thunderbird"
sys.path.insert(0, str(THUNDERBIRD_DIR))

# Import MCP client tools
from core.mcp.travel_mcp_client import TravelMCPClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(THUNDERBIRD_DIR / "logs" / "fare_sweep.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("fare_sweep")

# MCP server URL (HTTP mode)
MCP_SERVER_URL = "http://localhost:8767"


def load_fare_watches() -> List[Dict]:
    """Load active fare watches from JSON file."""
    watches_file = THUNDERBIRD_DIR / "core" / "travel" / "data" / "fare_watches.json"
    if not watches_file.exists():
        logger.error(f"Fare watches file not found: {watches_file}")
        return []
    
    try:
        with open(watches_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Filter active watches
        active_watches = []
        for watch_id, watch in data.items():
            if watch.get("active", True):
                # Calculate days to travel
                travel_date = datetime.fromisoformat(watch["travel_date"])
                days_to_travel = (travel_date - datetime.now()).days
                watch["days_to_travel"] = days_to_travel
                active_watches.append(watch)
        
        logger.info(f"Loaded {len(active_watches)} active fare watches")
        return active_watches
    except Exception as e:
        logger.error(f"Error loading fare watches: {e}")
        return []


def determine_check_frequency(watch: Dict) -> str:
    """Determine how often to check based on watch type and days to travel."""
    watch_type = watch.get("watch_type", "cruise")
    days_to_travel = watch.get("days_to_travel", 365)
    
    if watch_type == "flight":
        if days_to_travel <= 90:  # Within 90 days
            return "daily"
        elif days_to_travel <= 180:  # Within 180 days
            return "weekly"
        else:
            return "monthly"
    else:  # cruise, hotel
        if days_to_travel <= 180:
            return "weekly"
        else:
            return "monthly"


def should_check_today(watch: Dict) -> bool:
    """Determine if we should check this watch today based on frequency."""
    today = datetime.now()
    last_checked = watch.get("last_checked")
    
    if not last_checked:
        return True  # Never checked
    
    try:
        last_date = datetime.fromisoformat(last_checked)
    except (ValueError, TypeError):
        return True  # Invalid date format, check anyway
    
    frequency = determine_check_frequency(watch)
    days_since_last = (today - last_date).days
    
    if frequency == "daily" and days_since_last >= 1:
        return True
    elif frequency == "weekly" and days_since_last >= 7:
        return True
    elif frequency == "monthly" and days_since_last >= 30:
        return True
    
    return False


async def check_cruise_price(client: TravelMCPClient, watch: Dict) -> Optional[float]:
    """Check current cruise price using scrapers or APIs."""
    # For now, return baseline price as placeholder
    # TODO: Implement actual cruise price scraping
    logger.warning(f"Cruise price check not implemented for {watch['label']}")
    return watch.get("current_price_pp")


async def check_flight_price(client: TravelMCPClient, watch: Dict) -> Optional[float]:
    """Check current flight price using flight search tools."""
    route = watch.get("route", "")
    travel_date = watch.get("travel_date", "")
    passengers = watch.get("passengers", 1)
    
    # Parse route (e.g., "RIC → PTY")
    if "→" in route:
        origin, destination = route.split("→")
        origin = origin.strip()
        destination = destination.strip()
    elif "-" in route:
        origin, destination = route.split("-", 1)
        origin = origin.strip()
        destination = destination.strip()
    else:
        logger.error(f"Could not parse route format: {route}")
        return None
    
    try:
        # Use Amadeus flight search (free tier)
        result = await client.call_tool(
            "search_flights",
            {
                "origin": origin,
                "destination": destination,
                "departure_date": travel_date,
                "adults": min(passengers, 9),
                "max_results": 5,
                "cabin_class": "ECONOMY",  # Default to economy for price watch
            }
        )
        
        if result and "offers" in result and result["offers"]:
            # Take the first (cheapest) offer
            first_offer = result["offers"][0]
            price_data = first_offer.get("price", {})
            total_price = price_data.get("total_raw", price_data.get("total", 0))
            if isinstance(total_price, str) and total_price.startswith("$"):
                total_price = float(total_price.replace("$", "").replace(",", ""))
            
            return total_price / passengers  # Price per person
        else:
            logger.warning(f"No flight offers found for {route} on {travel_date}")
            return None
            
    except Exception as e:
        logger.error(f"Flight search failed for {watch['id']}: {e}")
        return None


async def update_watch_price(client: TravelMCPClient, watch: Dict, new_price_pp: float) -> Dict:
    """Update a watch with new price via MCP tool."""
    try:
        result = await client.call_tool(
            "fare_watch_check",
            {
                "watch_id": watch["id"],
                "new_price_pp": new_price_pp
            }
        )
        
        if result.get("status") == "checked":
            logger.info(f"Updated {watch['label']}: {result.get('price_pp')} ({result.get('change_from_baseline')})")
            
            # Check if alert was triggered
            if "alert" in result:
                await send_telegram_alert(watch, result)
                logger.warning(f"ALERT triggered for {watch['label']}: {result['alert']}")
        
        return result
    except Exception as e:
        logger.error(f"Failed to update watch {watch['id']}: {e}")
        return {"status": "error", "message": str(e)}


async def send_telegram_alert(watch: Dict, result: Dict):
    """Send Telegram alert for price threshold crossed."""
    try:
        # Use Thunderbird Telegram C2 bot
        alert_msg = f"🚨 FARE ALERT: {watch['label']}\n"
        alert_msg += f"Price: {result.get('price_pp', 'N/A')} ({result.get('change_from_baseline', 'N/A')})\n"
        alert_msg += f"Trigger: {result.get('alert', 'Threshold crossed')}\n"
        alert_msg += f"Travel: {watch.get('travel_date')} ({watch.get('days_to_travel', '?')} days)\n"
        
        # Import here to avoid circular dependencies
        from core.communication.thunderbird_telegram_c2 import send_telegram_message
        
        # Send to Commander (Yoda)
        await send_telegram_message(
            chat_id=7554895206,  # Commander Telegram ID
            message=alert_msg,
            parse_mode="HTML"
        )
        
        logger.info(f"Telegram alert sent for {watch['label']}")
    except ImportError:
        logger.warning("Telegram C2 module not available, skipping alert")
    except Exception as e:
        logger.error(f"Failed to send Telegram alert: {e}")


def update_google_sheets(watch: Dict, result: Dict):
    """Update Google Sheets price tracker (placeholder)."""
    # TODO: Implement Google Sheets integration
    logger.info(f"[SHEETS] Would update sheet for {watch['label']}: {result.get('price_pp')}")


async def main():
    """Run the fare sweep."""
    logger.info("=" * 60)
    logger.info("Starting Thunderbird Fare Sweep")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    logger.info("=" * 60)
    
    # Load active watches
    watches = load_fare_watches()
    if not watches:
        logger.warning("No active fare watches found")
        return
    
    # Connect to MCP server
    client = TravelMCPClient(MCP_SERVER_URL)
    try:
        await client.connect()
        logger.info(f"Connected to MCP server: {MCP_SERVER_URL}")
        
        # Process each watch
        checked_count = 0
        alerted_count = 0
        
        for watch in watches:
            watch_id = watch["id"]
            label = watch["label"]
            
            # Check if we should check today
            if not should_check_today(watch):
                logger.debug(f"Skipping {label} (checked recently)")
                continue
            
            logger.info(f"Checking: {label}")
            
            # Get current price based on watch type
            new_price = None
            if watch["watch_type"] == "flight":
                new_price = await check_flight_price(client, watch)
            elif watch["watch_type"] == "cruise":
                new_price = await check_cruise_price(client, watch)
            else:
                logger.warning(f"Unsupported watch type: {watch['watch_type']}")
                continue
            
            if new_price is None:
                logger.warning(f"Could not get price for {label}")
                continue
            
            # Update watch with new price
            result = await update_watch_price(client, watch, new_price)
            
            # Update Google Sheets
            update_google_sheets(watch, result)
            
            checked_count += 1
            if "alert" in result:
                alerted_count += 1
            
            # Rate limiting
            await asyncio.sleep(2)
        
        # Summary
        logger.info("=" * 60)
        logger.info(f"SWEEP COMPLETE: Checked {checked_count}/{len(watches)} watches")
        logger.info(f"Alerts triggered: {alerted_count}")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Fare sweep failed: {e}")
        raise
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
## AGENTS DOCUMENTATION

# Updated to enforce free-model guardrail for OpenRouter.
# - See docs/AGENTS_MODEL_GUIDE.md for allowed models and usage.

