"""
Thunderbird Price Monitor Module (Item #9)
==========================================

Cruise departure price tracking for Dreams2Memories Travel, LLC.

Features:
- Watch list of departures from config file or Booking Master
- Check current prices via cruise scraping, web search, or A2 research
- Compare against historical prices and flag meaningful changes
- Generate rebooking alerts for price drops >5%
- Store 52-week price history

Integrates with: travel_mcp_server.py, thunderbird_model_router.py, thunderbird_personas.py
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

from pydantic import Field
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

THUNDERBIRD_DIR = Path(__file__).parent
CONFIG_DIR = THUNDERBIRD_DIR / "config"
WATCHED_FILE = CONFIG_DIR / "watched_departures.json"
HISTORY_FILE = CONFIG_DIR / "price_history.json"
PRICE_LOG = THUNDERBIRD_DIR / "logs" / "price_monitor.log"
SPREADSHEET_ID = "1GFjUe8RvP-GT4YHGn0DYv_BEAZGXlYfwEicFrm8ANuU"

# Initially empty — populated from Booking Master or manually
WATCHED_DEPARTURES = [
    # {"cruise_line": "Silversea", "ship": "Silver Nova", "departure": "2026-09-15",
    #  "route": "Mediterranean", "last_price": None},
]

# Maximum weeks of price history to retain
MAX_HISTORY_WEEKS = 52


# ============================================================================
# WATCHED DEPARTURES
# ============================================================================

def get_watched_departures() -> List[Dict[str, Any]]:
    """Read watched departures from config file and Booking Master.

    If config file doesn't exist, creates it with an empty list.
    Also checks Booking Master for active cruise bookings to auto-add.

    Returns list of departure dicts.
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # Load from config file
    departures = []
    if WATCHED_FILE.exists():
        try:
            with open(WATCHED_FILE, "r", encoding="utf-8") as f:
                departures = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to read watched_departures.json: {e}")
            departures = []
    else:
        # Create empty config file
        with open(WATCHED_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)
        logger.info(f"Created empty watched departures config: {WATCHED_FILE}")

    # Try to auto-add from Booking Master
    booking_departures = _fetch_booking_master_departures()
    if booking_departures:
        # Merge without duplicates (match on cruise_line + departure date)
        existing_keys = {
            (d.get("cruise_line", "").lower(), d.get("departure", ""))
            for d in departures
        }
        for bd in booking_departures:
            key = (bd.get("cruise_line", "").lower(), bd.get("departure", ""))
            if key not in existing_keys:
                departures.append(bd)
                existing_keys.add(key)

    _log_price("get_departures", f"Loaded {len(departures)} watched departures")
    return departures


def _fetch_booking_master_departures() -> List[Dict[str, Any]]:
    """Fetch active cruise bookings from Booking Master to auto-watch.

    Returns list of departure dicts extracted from the sheet.
    """
    try:
        import gspread
        from google.oauth2.service_account import Credentials

        creds_file = THUNDERBIRD_DIR / "credentials.json"
        if not creds_file.exists():
            return []

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_file(str(creds_file), scopes=scopes)
        gc = gspread.authorize(creds)
        ws = gc.open_by_key(SPREADSHEET_ID).worksheet("Booking Master")
        records = ws.get_all_records()

        departures = []
        for row in records:
            # Look for cruise-type bookings with departure dates
            supplier = str(row.get("Supplier", "")).strip()
            booking_type = str(row.get("Type", "")).strip().lower()
            departure = str(row.get("Departure Date", "") or row.get("Start Date", "")).strip()

            if not departure:
                continue

            # Only auto-watch cruise bookings
            cruise_lines = [
                "silversea", "regent", "cunard", "oceania", "seabourn",
                "viking", "amawaterways", "ponant",
            ]
            is_cruise = any(cl in supplier.lower() for cl in cruise_lines)
            is_cruise = is_cruise or "cruise" in booking_type

            if is_cruise:
                departures.append({
                    "cruise_line": supplier,
                    "ship": str(row.get("Ship", "") or row.get("Vessel", "")).strip() or "Unknown",
                    "departure": departure,
                    "route": str(row.get("Route", "") or row.get("Itinerary", "")).strip() or "Unknown",
                    "last_price": None,
                    "source": "Booking Master",
                    "client": str(row.get("Client", "")).strip(),
                })

        return departures

    except Exception as e:
        logger.warning(f"Booking Master fetch failed: {e}")
        return []


# ============================================================================
# PRICE CHECKING
# ============================================================================

def check_current_prices(departures: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Check current pricing for each watched departure.

    Attempts multiple methods:
    1. Web search via Grok for current pricing
    2. Fall back to A2 research consultation

    Returns departures enriched with current_price and source.
    """
    from thunderbird_model_router import _call_grok, XAI_API_KEY

    results = []

    for dep in departures:
        cruise_line = dep.get("cruise_line", "Unknown")
        ship = dep.get("ship", "Unknown")
        departure = dep.get("departure", "Unknown")
        route = dep.get("route", "Unknown")

        price_query = (
            f"What is the current per-person price for {cruise_line} {ship} "
            f"departing {departure} on the {route} route? "
            f"Look for the starting cabin price in USD. "
            f"Return ONLY a JSON object: "
            f'{{"price_usd": 12345, "cabin_type": "Veranda Suite", "source": "cruise line website or travel site"}}'
            f" If price is unavailable, return: "
            f'{{"price_usd": null, "cabin_type": null, "source": "not found"}}'
        )

        system_prompt = (
            "You are a cruise pricing research assistant. "
            "Find the most current per-person pricing for the specified cruise departure. "
            "Return ONLY valid JSON. No explanation text."
        )

        result = {**dep, "current_price": None, "cabin_type": None, "price_source": "not_found"}

        try:
            if XAI_API_KEY:
                raw = _call_grok(system_prompt, price_query, max_tokens=300, temperature=0.1)
            else:
                import anthropic
                client = anthropic.Anthropic()
                resp = client.messages.create(
                    model="claude-haiku-4-5-20251001",  # Haiku — price extraction fallback (SO-2026-03-25)
                    max_tokens=300,
                    system=system_prompt,
                    messages=[{"role": "user", "content": price_query}],
                )
                raw = resp.content[0].text

            import re
            json_match = re.search(r'\{.*\}', raw, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                price = parsed.get("price_usd")
                if price is not None:
                    try:
                        result["current_price"] = float(price)
                    except (ValueError, TypeError):
                        pass
                result["cabin_type"] = parsed.get("cabin_type")
                result["price_source"] = parsed.get("source", "web_search")

        except Exception as e:
            logger.warning(f"Price check failed for {cruise_line} {ship} {departure}: {e}")

        result["checked_at"] = datetime.now(timezone.utc).isoformat()
        results.append(result)

    _log_price("check_prices", f"Checked {len(results)} departures, {sum(1 for r in results if r.get('current_price'))} with prices")
    return results


# ============================================================================
# PRICE COMPARISON
# ============================================================================

def compare_prices(current: List[Dict[str, Any]],
                   previous_file: Optional[str] = None) -> List[Dict[str, Any]]:
    """Compare current prices against historical data.

    Loads previous prices from price_history.json (or custom path).
    Calculates delta and flags changes.

    Returns list of dicts with delta info.
    """
    history_path = Path(previous_file) if previous_file else HISTORY_FILE

    # Load previous prices
    previous_prices = {}
    if history_path.exists():
        try:
            with open(history_path, "r", encoding="utf-8") as f:
                history = json.load(f)
            # Build lookup: key -> most recent price
            for entry in history:
                key = _departure_key(entry)
                price = entry.get("current_price") or entry.get("price")
                if price is not None:
                    previous_prices[key] = float(price)
        except Exception as e:
            logger.warning(f"Failed to load price history: {e}")

    # Compare
    changes = []
    for dep in current:
        key = _departure_key(dep)
        current_price = dep.get("current_price")
        previous_price = previous_prices.get(key)

        change = {**dep}

        if current_price is None:
            change["status"] = "no_current_price"
            change["delta_usd"] = None
            change["delta_pct"] = None
        elif previous_price is None:
            change["status"] = "new_tracking"
            change["delta_usd"] = None
            change["delta_pct"] = None
            change["previous_price"] = None
        else:
            delta = current_price - previous_price
            delta_pct = (delta / previous_price * 100) if previous_price > 0 else 0
            change["previous_price"] = previous_price
            change["delta_usd"] = round(delta, 2)
            change["delta_pct"] = round(delta_pct, 1)

            if abs(delta_pct) < 0.5:
                change["status"] = "price_unchanged"
            elif delta < 0:
                change["status"] = "price_dropped"
            else:
                change["status"] = "price_rose"

        changes.append(change)

    return changes


def _departure_key(dep: Dict) -> str:
    """Generate a unique key for a departure (for dedup and matching)."""
    parts = [
        dep.get("cruise_line", "").strip().lower(),
        dep.get("ship", "").strip().lower(),
        dep.get("departure", "").strip(),
    ]
    return "|".join(parts)


# ============================================================================
# PRICE ALERTS
# ============================================================================

def generate_price_alert(changes: List[Dict[str, Any]]) -> Optional[str]:
    """Generate an alert email body for meaningful price changes (>2% delta).

    Returns alert text, or None if no meaningful changes.
    """
    meaningful = [
        c for c in changes
        if c.get("delta_pct") is not None and abs(c["delta_pct"]) > 2.0
    ]

    if not meaningful:
        return None

    lines = []
    rebooking_opportunities = []

    for c in meaningful:
        cruise = f"{c.get('cruise_line', '?')} {c.get('ship', '?')}"
        departure = c.get("departure", "?")
        route = c.get("route", "?")
        old_price = c.get("previous_price", 0)
        new_price = c.get("current_price", 0)
        delta = c.get("delta_usd", 0)
        delta_pct = c.get("delta_pct", 0)
        status = c.get("status", "unknown")

        direction = "DOWN" if delta < 0 else "UP"
        lines.append(
            f"  {cruise} — {departure} ({route})\n"
            f"    Previous: ${old_price:,.0f}  ->  Current: ${new_price:,.0f}\n"
            f"    Change: {direction} ${abs(delta):,.0f} ({delta_pct:+.1f}%)\n"
        )

        if delta_pct < -5.0:
            rebooking_opportunities.append(
                f"  ** {cruise} — {departure}: ${abs(delta):,.0f} savings ({delta_pct:.1f}%)"
            )

    alert = f"""
{'=' * 60}
CRUISE PRICE MONITOR ALERT
Dreams2Memories Travel — {datetime.now().strftime('%Y-%m-%d %H:%M')}
{'=' * 60}

PRICE CHANGES (>{2}% threshold)
{'-' * 60}
{chr(10).join(lines)}
"""

    if rebooking_opportunities:
        alert += f"""
{'*' * 60}
REBOOKING OPPORTUNITIES (>5% drop)
{'*' * 60}
{chr(10).join(rebooking_opportunities)}

ACTION: Review these departures for client rebooking — potential savings above.
{'*' * 60}
"""

    alert += f"""
{'-' * 60}
Total departures tracked: {len(changes)}
Meaningful changes: {len(meaningful)}
Generated by Thunderbird Price Monitor
"""

    return alert


# ============================================================================
# PRICE HISTORY STORAGE
# ============================================================================

def store_price_history(data: List[Dict[str, Any]]):
    """Append timestamped prices to price_history.json, keeping last 52 weeks."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # Load existing history
    history = []
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except (json.JSONDecodeError, IOError):
            history = []

    # Append new entries with timestamp
    ts = datetime.now(timezone.utc).isoformat()
    for dep in data:
        if dep.get("current_price") is not None:
            entry = {
                "cruise_line": dep.get("cruise_line", ""),
                "ship": dep.get("ship", ""),
                "departure": dep.get("departure", ""),
                "route": dep.get("route", ""),
                "price": dep["current_price"],
                "cabin_type": dep.get("cabin_type"),
                "source": dep.get("price_source", ""),
                "recorded_at": ts,
            }
            history.append(entry)

    # Prune: keep only last 52 weeks of entries
    cutoff_days = MAX_HISTORY_WEEKS * 7
    now = datetime.now(timezone.utc)
    pruned = []
    for entry in history:
        recorded = entry.get("recorded_at", "")
        try:
            entry_dt = datetime.fromisoformat(recorded.replace("Z", "+00:00"))
            age_days = (now - entry_dt).days
            if age_days <= cutoff_days:
                pruned.append(entry)
        except (ValueError, TypeError):
            pruned.append(entry)  # Keep entries we can't parse

    # Write back
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(pruned, f, indent=2, ensure_ascii=False)

    _log_price("store_history", f"Stored {len(data)} new entries, {len(pruned)} total in history")


# ============================================================================
# FULL PRICE CHECK PIPELINE
# ============================================================================

def run_price_check() -> Dict[str, Any]:
    """Full price monitoring pipeline.

    1. Get watched departures
    2. Check current prices
    3. Compare with history
    4. Generate alert if meaningful changes
    5. Store price history

    Returns summary dict.
    """
    _log_price("run_start", "Beginning price check run")

    # Step 1: Get departures
    departures = get_watched_departures()
    if not departures:
        _log_price("run_end", "No watched departures — run aborted")
        return {
            "status": "no_departures",
            "note": "No watched departures configured. Add to ~/Thunderbird/config/watched_departures.json or Booking Master.",
        }

    # Step 2: Check prices
    current = check_current_prices(departures)

    # Step 3: Compare
    changes = compare_prices(current)

    # Step 4: Alert
    alert = generate_price_alert(changes)
    email_status = "no_meaningful_changes"

    if alert:
        try:
            from thunderbird_gmail import gmail_send_with_approval
            gmail_send_with_approval(
                to="johnloucks3@gmail.com",
                subject=f"Cruise Price Alert — {datetime.now().strftime('%Y-%m-%d')}",
                body=alert,
                persona_id="A3",
                auto_send=False,
            )
            email_status = "draft_created"
        except Exception as e:
            logger.warning(f"Price alert email failed: {e}")
            email_status = f"failed: {e}"

    # Step 5: Store history
    store_price_history(current)

    _log_price("run_end", f"Price check complete — {len(departures)} tracked, alert: {email_status}")

    # Summary of changes
    drops = sum(1 for c in changes if c.get("status") == "price_dropped")
    rises = sum(1 for c in changes if c.get("status") == "price_rose")
    unchanged = sum(1 for c in changes if c.get("status") == "price_unchanged")
    new_tracking = sum(1 for c in changes if c.get("status") == "new_tracking")

    return {
        "status": "success",
        "departures_tracked": len(departures),
        "prices_found": sum(1 for c in current if c.get("current_price")),
        "price_drops": drops,
        "price_rises": rises,
        "unchanged": unchanged,
        "new_tracking": new_tracking,
        "email_status": email_status,
        "alert_generated": alert is not None,
    }


# ============================================================================
# LOGGING
# ============================================================================

def _log_price(action: str, detail: str):
    """Append to price monitor log."""
    try:
        PRICE_LOG.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        line = f"[{ts}] {action} | {detail}\n"
        with open(PRICE_LOG, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception as e:
        logger.warning(f"Price log write failed: {e}")


# ============================================================================
# MCP TOOL REGISTRATION
# ============================================================================

def register_price_monitor_tools(mcp: FastMCP):
    """Register price monitor tools with the MCP server."""

    @mcp.tool(
        name="check_departure_prices",
        annotations={"title": "Check Cruise Departure Prices", "readOnlyHint": False},
    )
    async def check_departure_prices() -> str:
        """Run a full cruise price monitoring check.

        Reads watched departures from config and Booking Master,
        checks current prices via web search, compares against
        historical prices, generates alerts for significant changes,
        and stores the updated price history.

        Email alert draft is created only if meaningful changes (>2%) are found.
        """
        result = run_price_check()
        return json.dumps(result, indent=2, default=str)

    logger.info("Price monitor tools registered (check_departure_prices)")
