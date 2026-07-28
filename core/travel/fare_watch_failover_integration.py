#!/usr/bin/env python3
"""
fare_watch_failover_integration.py — Wire SearchEngineFailover into existing fare_watch
=======================================================================================

Replaces single-engine fare_watch polling with autonomous cascade failover.

NEW ARCHITECTURE:
- fare_watch_poll.py (old): ITA-only poller with manual rate-limit handling
- search_engine_failover.py (new): Multi-engine cascade with auto health tracking
- THIS MODULE (new): Adapter that integrates failover into existing fare_watch data model

USAGE:
Instead of:
    result = await poll_url(ita_url)  # single engine, silent failure

Use:
    fo = FareWatchFailoverAdapter()
    result = fo.get_watch_price(watch_id)
    # Returns: (price, engine_used, status) or (None, None, error_status)

Integration points:
1. Replace ita_fare_watch_poll.py with hybrid: try failover, fallback to ITA direct
2. Add /logs/search_engine_health.json health dashboard
3. Add systemd timer to gc old health records (>30d)
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Tuple

from core.travel.search_engine_failover import (
    SearchEngineFailover, FlightSearchRequest, Engine, EngineStatus
)

logger = logging.getLogger(__name__)

ROOT = Path("/home/john/Thunderbird")
FARE_WATCHES_JSON = ROOT / "core" / "travel" / "data" / "fare_watches.json"

@dataclass
class WatchPriceResult:
    """Result of polling a single fare watch."""
    success: bool
    price_per_person: Optional[float]
    engine_used: Optional[Engine]
    engines_tried: list
    fetch_time_seconds: float
    error_message: Optional[str] = None

class FareWatchFailoverAdapter:
    """Adapter between fare_watches.json schema and SearchEngineFailover."""

    def __init__(self):
        self.failover = SearchEngineFailover()
        self.watches = self._load_watches()

    def _load_watches(self) -> Dict:
        """Load fare_watches.json into memory."""
        if FARE_WATCHES_JSON.exists():
            try:
                data = json.loads(FARE_WATCHES_JSON.read_text())
                if isinstance(data, list):
                    return {w.get("id"): w for w in data if isinstance(w, dict)}
                if "watches" in data:
                    return data["watches"] if isinstance(data["watches"], dict) else {w["id"]: w for w in data["watches"]}
                if "fare_watches" in data:
                    cont = data["fare_watches"]
                    return cont if isinstance(cont, dict) else {w["id"]: w for w in cont}
                return {w.get("id"): w for w in data.values() if isinstance(w, dict)}
            except Exception as e:
                logger.error(f"Failed to load fare_watches: {e}")
        return {}

    def get_watch_price(self, watch_id: str) -> WatchPriceResult:
        """Poll a single watch using cascade failover.

        Args:
            watch_id: ID from fare_watches.json (e.g., "watch_001")

        Returns:
            WatchPriceResult with success/price/engine_used or error details
        """
        watch = self.watches.get(watch_id)
        if not watch:
            return WatchPriceResult(
                success=False,
                price_per_person=None,
                engine_used=None,
                engines_tried=[],
                fetch_time_seconds=0.0,
                error_message=f"Watch {watch_id} not found"
            )

        # Extract search parameters from watch
        req = FlightSearchRequest(
            origin=watch.get("origin", ""),
            destination=watch.get("destination", ""),
            date=watch.get("departure_date", ""),
            return_date=watch.get("return_date"),
            passengers=watch.get("passengers", 1),
            cabin=watch.get("cabin_class", "economy")
        )

        # Run cascade search
        search_result = self.failover.search_cascade(req)

        # Convert to WatchPriceResult
        fetch_times = sum(search_result.fetch_times.values()) if search_result.fetch_times else 0.0
        return WatchPriceResult(
            success=search_result.success,
            price_per_person=search_result.price_per_person,
            engine_used=search_result.engine_used,
            engines_tried=search_result.engines_tried,
            fetch_time_seconds=fetch_times,
            error_message=search_result.error_message
        )

    def poll_all_watches(self, max_per_run: int = 2) -> Dict[str, WatchPriceResult]:
        """Poll all active watches with rate limiting.

        Args:
            max_per_run: Max watches to poll in this run (rotate others)

        Returns:
            {watch_id: WatchPriceResult, ...}
        """
        results = {}
        active_watches = [w for w in self.watches.values() if w.get("active", True)]

        # Simple round-robin rotation (in production: persist rotation state)
        for watch in active_watches[:max_per_run]:
            watch_id = watch.get("id")
            if watch_id:
                results[watch_id] = self.get_watch_price(watch_id)

        return results

if __name__ == "__main__":
    # Example: poll all watches using failover
    adapter = FareWatchFailoverAdapter()
    results = adapter.poll_all_watches(max_per_run=3)
    for watch_id, result in results.items():
        if result.success:
            print(f"✓ {watch_id}: ${result.price_per_person} ({result.engine_used.value})")
        else:
            print(f"✗ {watch_id}: {result.error_message}")
