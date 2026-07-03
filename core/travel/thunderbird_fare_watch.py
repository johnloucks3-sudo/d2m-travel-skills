"""
Thunderbird Fare Watch — Flight & Cruise Price Monitoring
==========================================================

Ported from AllegiantFareTracker.gs pattern into reusable MCP tools.
Tracks prices daily, logs history, alerts on drops/spikes.

Tools:
  - fare_watch_check: Run a price check for a watched fare
  - fare_watch_list: List all active fare watches
  - fare_watch_add: Add a new fare to watch
  - fare_watch_remove: Remove a fare watch

Storage: ~/Thunderbird/data/fare_watches.json
History: ~/Thunderbird/data/fare_history.json
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"
WATCHES_FILE = DATA_DIR / "fare_watches.json"
HISTORY_FILE = DATA_DIR / "fare_history.json"


# ============================================================================
# DATA MODELS
# ============================================================================

class FareWatch(BaseModel):
    """A fare/price being monitored."""
    id: str = Field(..., description="Unique watch ID (e.g. 'allegiant-cos-sna-apr10')")
    watch_type: str = Field(..., description="Type: 'flight', 'cruise', or 'hotel'")
    label: str = Field(..., description="Human-readable label (e.g. 'G4-3212 COS>SNA Apr 10')")
    provider: str = Field(..., description="Provider name (e.g. 'Allegiant', 'Silversea')")
    route: str = Field(..., description="Route or property (e.g. 'COS>SNA', 'Lisbon>Barcelona')")
    travel_date: str = Field(..., description="Travel date (YYYY-MM-DD)")
    passengers: int = Field(2, description="Number of travelers")
    current_price_pp: float = Field(..., description="Current price per person in USD")
    baseline_price_pp: float = Field(..., description="Baseline/original price per person")
    alert_below: Optional[float] = Field(None, description="Alert if price drops below this")
    alert_above: Optional[float] = Field(None, description="Alert if price rises above this")
    notes: str = Field("", description="Additional notes or bundle details")
    active: bool = Field(True, description="Whether this watch is active")
    created: str = Field(default_factory=lambda: datetime.now().isoformat())
    last_checked: Optional[str] = Field(None)


class FareHistoryEntry(BaseModel):
    """A single price check record."""
    watch_id: str
    timestamp: str
    price_pp: float
    total: float
    price_change_pct: float
    alert_triggered: Optional[str] = None
    notes: str = ""


# ============================================================================
# STORAGE
# ============================================================================

def _ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_watches() -> Dict[str, dict]:
    _ensure_data_dir()
    if WATCHES_FILE.exists():
        return json.loads(WATCHES_FILE.read_text(encoding="utf-8"))
    return {}


def _save_watches(watches: Dict[str, dict]):
    _ensure_data_dir()
    WATCHES_FILE.write_text(
        json.dumps(watches, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


def _load_history() -> List[dict]:
    _ensure_data_dir()
    if HISTORY_FILE.exists():
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    return []


def _save_history(history: List[dict]):
    _ensure_data_dir()
    HISTORY_FILE.write_text(
        json.dumps(history, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


# ============================================================================
# CORE LOGIC
# ============================================================================

def add_watch(
    watch_id: str,
    watch_type: str,
    label: str,
    provider: str,
    route: str,
    travel_date: str,
    current_price_pp: float,
    passengers: int = 2,
    alert_below: Optional[float] = None,
    alert_above: Optional[float] = None,
    notes: str = "",
) -> dict:
    """Add a new fare watch."""
    watches = _load_watches()

    watch = FareWatch(
        id=watch_id,
        watch_type=watch_type,
        label=label,
        provider=provider,
        route=route,
        travel_date=travel_date,
        passengers=passengers,
        current_price_pp=current_price_pp,
        baseline_price_pp=current_price_pp,
        alert_below=alert_below,
        alert_above=alert_above,
        notes=notes,
    )

    watches[watch_id] = watch.model_dump()
    _save_watches(watches)

    return {
        "status": "created",
        "watch_id": watch_id,
        "label": label,
        "price_pp": f"${current_price_pp:,.0f}",
        "total": f"${current_price_pp * passengers:,.0f}",
        "alert_below": f"${alert_below:,.0f}" if alert_below else "none",
        "alert_above": f"${alert_above:,.0f}" if alert_above else "none",
    }


def check_fare(watch_id: str, new_price_pp: float) -> dict:
    """Record a price check and return analysis."""
    watches = _load_watches()
    if watch_id not in watches:
        return {"status": "error", "message": f"Watch '{watch_id}' not found"}

    watch = watches[watch_id]
    baseline = watch["baseline_price_pp"]
    previous = watch["current_price_pp"]
    passengers = watch["passengers"]

    # Calculate changes
    change_from_baseline = ((new_price_pp - baseline) / baseline) * 100 if baseline else 0
    change_from_last = new_price_pp - previous
    total = new_price_pp * passengers

    # Check alerts
    alert = None
    if watch.get("alert_below") and new_price_pp < watch["alert_below"]:
        alert = f"PRICE DROP: ${new_price_pp:,.0f}/pp is below alert threshold ${watch['alert_below']:,.0f}"
    elif watch.get("alert_above") and new_price_pp > watch["alert_above"]:
        alert = f"PRICE SPIKE: ${new_price_pp:,.0f}/pp exceeds alert threshold ${watch['alert_above']:,.0f}"

    # Log to history
    now = datetime.now().isoformat()
    entry = FareHistoryEntry(
        watch_id=watch_id,
        timestamp=now,
        price_pp=new_price_pp,
        total=total,
        price_change_pct=round(change_from_baseline, 1),
        alert_triggered=alert,
    )
    history = _load_history()
    history.append(entry.model_dump())
    _save_history(history)

    # Update watch
    watch["current_price_pp"] = new_price_pp
    watch["last_checked"] = now
    watches[watch_id] = watch
    _save_watches(watches)

    # Build response
    direction = "up" if change_from_last > 0 else "down" if change_from_last < 0 else "unchanged"
    result = {
        "status": "checked",
        "watch_id": watch_id,
        "label": watch["label"],
        "price_pp": f"${new_price_pp:,.0f}",
        "total": f"${total:,.0f} ({passengers} pax)",
        "baseline_pp": f"${baseline:,.0f}",
        "change_from_baseline": f"{change_from_baseline:+.1f}%",
        "change_from_last": f"${change_from_last:+,.0f}/pp ({direction})",
        "direction": direction,
        "checked_at": now,
    }

    if alert:
        result["alert"] = alert

    # Get recent history for trend
    watch_history = [h for h in history if h["watch_id"] == watch_id]
    if len(watch_history) >= 2:
        recent = watch_history[-5:]
        result["recent_prices"] = [
            f"{h['timestamp'][:10]}: ${h['price_pp']:,.0f}" for h in recent
        ]

    return result


def list_watches(active_only: bool = True) -> dict:
    """List all fare watches."""
    watches = _load_watches()
    items = []

    for wid, w in watches.items():
        if active_only and not w.get("active", True):
            continue
        price = w.get("current_price_pp")
        baseline = w.get("baseline_price_pp")
        pax = w.get("passengers", 2)
        change = ((price - baseline) / baseline * 100) if (baseline and price is not None) else 0

        price_str = f"${price:,.0f}" if price is not None else "N/A"
        total_str = f"${price * pax:,.0f} ({pax} pax)" if price is not None else "N/A"

        items.append({
            "id": wid,
            "label": w.get("label", "?"),
            "type": w.get("watch_type", "?"),
            "provider": w.get("provider", "?"),
            "travel_date": w.get("travel_date") or w.get("outbound_date", ""),
            "price_pp": price_str,
            "total": total_str,
            "vs_baseline": f"{change:+.1f}%",
            "last_checked": w.get("last_checked", "never")[:10] if w.get("last_checked") else "never",
            "active": w.get("active", True),
        })

    return {
        "status": "success",
        "count": len(items),
        "watches": items,
    }


def remove_watch(watch_id: str, hard_delete: bool = False) -> dict:
    """Deactivate or delete a fare watch."""
    watches = _load_watches()
    if watch_id not in watches:
        return {"status": "error", "message": f"Watch '{watch_id}' not found"}

    if hard_delete:
        del watches[watch_id]
        _save_watches(watches)
        return {"status": "deleted", "watch_id": watch_id}
    else:
        watches[watch_id]["active"] = False
        _save_watches(watches)
        return {"status": "deactivated", "watch_id": watch_id}


def get_fare_history(watch_id: str, limit: int = 30) -> dict:
    """Get price history for a watch."""
    watches = _load_watches()
    if watch_id not in watches:
        return {"status": "error", "message": f"Watch '{watch_id}' not found"}

    history = _load_history()
    entries = [h for h in history if h["watch_id"] == watch_id]
    entries = entries[-limit:]

    watch = watches[watch_id]
    prices = [h["price_pp"] for h in entries]

    summary = {}
    if prices:
        summary = {
            "min": f"${min(prices):,.0f}",
            "max": f"${max(prices):,.0f}",
            "avg": f"${sum(prices) / len(prices):,.0f}",
            "latest": f"${prices[-1]:,.0f}",
            "data_points": len(prices),
        }

    return {
        "status": "success",
        "watch_id": watch_id,
        "label": watch["label"],
        "summary": summary,
        "history": [
            {
                "date": h["timestamp"][:10],
                "price_pp": f"${h['price_pp']:,.0f}",
                "total": f"${h['total']:,.0f}",
                "change": f"{h['price_change_pct']:+.1f}%",
                "alert": h.get("alert_triggered"),
            }
            for h in entries
        ],
    }


# ============================================================================
# MCP TOOL REGISTRATION
# ============================================================================

def register_fare_watch_tools(mcp):
    """Register fare watch MCP tools."""

    @mcp.tool(name="fare_watch_add")
    async def tool_fare_watch_add(
        watch_id: str = Field(..., description="Unique ID (e.g. 'allegiant-cos-sna-apr10')"),
        watch_type: str = Field("flight", description="Type: 'flight', 'cruise', or 'hotel'"),
        label: str = Field(..., description="Human label (e.g. 'G4-3212 COS>SNA Apr 10 2026')"),
        provider: str = Field(..., description="Provider (e.g. 'Allegiant', 'Silversea')"),
        route: str = Field(..., description="Route (e.g. 'COS>SNA', 'Lisbon>Barcelona')"),
        travel_date: str = Field(..., description="Travel date YYYY-MM-DD"),
        current_price_pp: float = Field(..., description="Current price per person USD"),
        passengers: int = Field(2, description="Number of travelers"),
        alert_below: Optional[float] = Field(None, description="Alert if price drops below"),
        alert_above: Optional[float] = Field(None, description="Alert if price rises above"),
        notes: str = Field("", description="Bundle details, add-on fees, etc."),
    ) -> str:
        """Add a new flight, cruise, or hotel fare to the price watch list."""
        result = add_watch(
            watch_id=watch_id,
            watch_type=watch_type,
            label=label,
            provider=provider,
            route=route,
            travel_date=travel_date,
            current_price_pp=current_price_pp,
            passengers=passengers,
            alert_below=alert_below,
            alert_above=alert_above,
            notes=notes,
        )
        return json.dumps(result, indent=2)

    @mcp.tool(name="fare_watch_check")
    async def tool_fare_watch_check(
        watch_id: str = Field(..., description="Watch ID to check"),
        new_price_pp: float = Field(..., description="Current price per person USD"),
    ) -> str:
        """Record a price check for a watched fare. Logs history and triggers alerts."""
        result = check_fare(watch_id, new_price_pp)
        return json.dumps(result, indent=2)

    @mcp.tool(name="fare_watch_list")
    async def tool_fare_watch_list(
        active_only: bool = Field(True, description="Show only active watches"),
    ) -> str:
        """List all fare watches with current prices and trends."""
        result = list_watches(active_only)
        return json.dumps(result, indent=2)

    @mcp.tool(name="fare_watch_remove")
    async def tool_fare_watch_remove(
        watch_id: str = Field(..., description="Watch ID to remove"),
        hard_delete: bool = Field(False, description="Permanently delete (vs deactivate)"),
    ) -> str:
        """Deactivate or delete a fare watch."""
        result = remove_watch(watch_id, hard_delete)
        return json.dumps(result, indent=2)

    @mcp.tool(name="fare_watch_history")
    async def tool_fare_watch_history(
        watch_id: str = Field(..., description="Watch ID to get history for"),
        limit: int = Field(30, description="Max entries to return"),
    ) -> str:
        """Get price history for a watched fare with min/max/avg summary."""
        result = get_fare_history(watch_id, limit)
        return json.dumps(result, indent=2)

    logger.info("Fare Watch tools registered (5 tools)")
