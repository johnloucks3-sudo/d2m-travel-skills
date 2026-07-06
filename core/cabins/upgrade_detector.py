#!/usr/bin/env python3
"""
core/cabins/upgrade_detector.py — Cabin Upgrade Opportunity Detector
=====================================================================
Monitors suite availability on booked voyages via the cabin-availability
scraper (same page-scrape approach as check_cabin_availability MCP tool)
and flags when a premium suite becomes available for an already-booked
client at little or no extra cost (overbooking release, last-minute
cancellation) — for Dani to offer as a courtesy upgrade.

Logic (Phase 4 revenue optimization spec):
    if current_cabin_tier < available_cabin_tier
       AND available_cabin_tier is a real upgrade (ranked higher)
       AND price_delta < $500
    -> flag opportunity

Config:  data/cabin_upgrade_watches.json   — list of WatchedBooking dicts
Output:  data/upgrade_opportunities.json   — list of UpgradeOpportunity dicts

Usage:
    python3 core/cabins/upgrade_detector.py             # normal sweep
    python3 core/cabins/upgrade_detector.py --dry-run    # print only, no write

Cron install (weekly sweep):
    0 7 * * 1 /home/john/Thunderbird/.venv/bin/python3 \
              /home/john/Thunderbird/core/cabins/upgrade_detector.py \
              >> /home/john/Thunderbird/logs/cabin_upgrade_detector.log 2>&1

Dreams2Memories Travel, LLC — Thunderbird Wing
"""

import argparse
import json
import logging
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional

THUNDERBIRD = Path.home() / "Thunderbird"
sys.path.insert(0, str(THUNDERBIRD))

DATA_DIR = THUNDERBIRD / "data"
LOG_DIR = THUNDERBIRD / "logs"
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

WATCH_FILE = DATA_DIR / "cabin_upgrade_watches.json"
OUTPUT_FILE = DATA_DIR / "upgrade_opportunities.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s CABIN-UPGRADE %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(str(LOG_DIR / "cabin_upgrade_detector.log"), mode="a"),
    ],
)
log = logging.getLogger("cabin_upgrade")

# Spec: "price_delta < $500" — the max amount MORE a suite can cost to still
# qualify as a flaggable courtesy upgrade. Negative delta (cheaper) always qualifies.
MAX_PRICE_DELTA = 500.0

# ---------------------------------------------------------------------------
# Cabin tier ranking — low to high. Per-line lists override the generic one;
# keyword match is substring + longest-match-wins (so "Deluxe Veranda Suite"
# outranks a bare "Veranda" match). This is a heuristic, not an authoritative
# cruise-line schema — refine per line as real category names are confirmed.
# ---------------------------------------------------------------------------

GENERIC_TIER_ORDER: List[str] = [
    "interior", "inside",
    "oceanview", "ocean view", "window suite", "deluxe window suite",
    "balcony", "veranda", "classic veranda", "superior veranda",
    "deluxe veranda", "deluxe veranda suite",
    "concierge suite", "junior suite", "silver suite", "medallion suite",
    "penthouse suite", "seven seas suite", "royal suite", "grand suite", "explorer suite",
    "owner's suite", "owners suite", "master suite",
    "regent suite", "otium suite",
]

LINE_TIER_ORDER: Dict[str, List[str]] = {
    "regent": [
        "deluxe window suite", "deluxe veranda suite",
        "concierge suite", "penthouse suite", "seven seas suite",
        "grand suite", "master suite", "regent suite",
    ],
    "silversea": [
        "classic veranda", "superior veranda", "deluxe veranda",
        "silver suite", "medallion suite", "royal suite",
        "owner's suite", "grand suite", "otium suite",
    ],
    "viking": [
        "veranda", "deluxe veranda", "penthouse junior suite",
        "penthouse veranda suite", "explorer suite", "owner's suite",
    ],
}

PRICE_RE = re.compile(r"\$\s*([\d,]+(?:\.\d{2})?)")


def cabin_tier_rank(category: str, order: Optional[List[str]] = None) -> int:
    """Rank a free-text cabin category name against a tier ordering.

    Returns the index of the longest matching keyword (higher = better cabin),
    or -1 if the category text matches nothing in the ordering (unranked —
    callers must never treat -1 as an upgrade).
    """
    order = order or GENERIC_TIER_ORDER
    name = category.lower().strip()
    best_rank, best_len = -1, 0
    for idx, keyword in enumerate(order):
        if keyword in name and len(keyword) > best_len:
            best_rank, best_len = idx, len(keyword)
    return best_rank


def tier_order_for_line(cruise_line: Optional[str]) -> List[str]:
    return LINE_TIER_ORDER.get((cruise_line or "").strip().lower(), GENERIC_TIER_ORDER)


CABIN_PRICE_PROXIMITY = 200  # max char distance between a category name and its price


def parse_cabin_prices(text: str, cabin_targets: Optional[List[str]] = None) -> Dict[str, float]:
    """Heuristic extraction of {cabin_category: price_pp} from raw scraped
    page text (the `availability_data_snippet` the check_cabin_availability
    MCP tool returns). For each occurrence of a known category name, picks
    the NEAREST dollar figure by character distance (not just the first
    price in a broad window) so adjacent categories on the same page don't
    steal each other's price. Keeps the cheapest sighting per category
    (a page listing both a stale/waitlisted price and a newly-released
    lower price for the same category should surface the lower one).
    """
    cabin_targets = cabin_targets or GENERIC_TIER_ORDER
    text_lower = text.lower()
    found: Dict[str, float] = {}

    all_prices = []
    for m in PRICE_RE.finditer(text):
        try:
            price = float(m.group(1).replace(",", ""))
        except ValueError:
            continue
        if 200 <= price <= 60000:
            all_prices.append((m.start(), price))

    for cabin in cabin_targets:
        for m in re.finditer(re.escape(cabin), text_lower):
            pos = m.start()
            # Real listings read "Category — $price", so a price AFTER the
            # category name is preferred; only fall back to one preceding it
            # (e.g. "$price — Category") when nothing follows within range.
            forward = [
                (p_pos - pos, price)
                for p_pos, price in all_prices
                if p_pos >= pos and (p_pos - pos) <= CABIN_PRICE_PROXIMITY
            ]
            backward = [
                (pos - p_pos, price)
                for p_pos, price in all_prices
                if p_pos < pos and (pos - p_pos) <= CABIN_PRICE_PROXIMITY
            ]
            candidates = forward or backward
            if not candidates:
                continue
            candidates.sort(key=lambda x: x[0])
            price = candidates[0][1]
            if cabin not in found or price < found[cabin]:
                found[cabin] = price
    return found


@dataclass
class WatchedBooking:
    booking_id: str
    client_name: str
    ship: str
    current_cabin: str
    current_price_pp: float
    voyage_url: Optional[str] = None
    cruise_line: Optional[str] = None
    active: bool = True
    note: Optional[str] = None


@dataclass
class UpgradeOpportunity:
    booking_id: str
    client_name: str
    current_cabin: str
    available_upgrade: str
    upgrade_price_pp: float
    price_delta: float
    recommendation: str
    detected_at: str
    source_url: str


_WATCH_FIELDS = {f for f in WatchedBooking.__dataclass_fields__}


def load_watches(path: Path = WATCH_FILE) -> List[WatchedBooking]:
    if not path.exists():
        return []
    raw = json.loads(path.read_text())
    return [
        WatchedBooking(**{k: v for k, v in w.items() if k in _WATCH_FIELDS})
        for w in raw
        if w.get("active", True)
    ]


def save_opportunities(opps: List[dict], path: Path = OUTPUT_FILE) -> None:
    path.write_text(json.dumps(opps, indent=2))


FetchFn = Callable[[str], str]


def _default_fetch(voyage_url: str) -> str:
    """Live fetch — same Stealth+Playwright scrape as the check_cabin_availability
    MCP tool (core/mcp/travel_mcp_server.py). Imports are deferred so unit tests
    never pay for the Playwright/browser import."""
    import asyncio

    from playwright.async_api import async_playwright

    try:
        from playwright_stealth import Stealth
    except ImportError:
        Stealth = None

    async def _go() -> str:
        pw_ctx = Stealth().use_async(async_playwright()) if Stealth else async_playwright()
        async with pw_ctx as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
                )
            )
            page = await context.new_page()
            await page.goto(voyage_url, wait_until="networkidle", timeout=45000)
            content = await page.evaluate("document.body.innerText")
            await browser.close()
            return content

    return asyncio.run(_go())


def _recommendation_text(booking: WatchedBooking, cabin: str, delta: float) -> str:
    first_name = booking.client_name.split(" ")[0]
    if delta <= 0:
        return (
            f"{cabin} now available at ${abs(delta):,.2f} LESS per person than "
            f"{first_name}'s current {booking.current_cabin} — flag for Dani to "
            f"offer as a courtesy upgrade."
        )
    return (
        f"{cabin} now available for only ${delta:,.2f} more pp than "
        f"{first_name}'s current {booking.current_cabin} — flag for Dani to "
        f"offer as a courtesy upgrade."
    )


def detect_upgrade_for_booking(
    booking: WatchedBooking,
    fetch_fn: FetchFn = _default_fetch,
    max_price_delta: float = MAX_PRICE_DELTA,
) -> Optional[UpgradeOpportunity]:
    """Core detection for one booking. Returns the cheapest-delta qualifying
    upgrade, or None if no premium suite qualifies (or data is insufficient)."""
    if not booking.voyage_url:
        log.warning(f"{booking.booking_id}: no voyage_url configured — skipping")
        return None

    order = tier_order_for_line(booking.cruise_line)
    current_rank = cabin_tier_rank(booking.current_cabin, order)
    if current_rank == -1:
        log.warning(
            f"{booking.booking_id}: current cabin '{booking.current_cabin}' "
            f"unranked against known tiers for '{booking.cruise_line}' — skipping"
        )
        return None

    try:
        text = fetch_fn(booking.voyage_url)
    except Exception as exc:
        log.error(f"{booking.booking_id}: fetch failed — {exc}")
        return None

    prices = parse_cabin_prices(text, order)
    if not prices:
        return None

    best: Optional[UpgradeOpportunity] = None
    for cabin, price in prices.items():
        rank = cabin_tier_rank(cabin, order)
        if rank <= current_rank:
            continue  # not an upgrade over what's already booked
        delta = round(price - booking.current_price_pp, 2)
        if delta >= max_price_delta:
            continue  # too expensive to flag as a courtesy upgrade
        candidate = UpgradeOpportunity(
            booking_id=booking.booking_id,
            client_name=booking.client_name,
            current_cabin=booking.current_cabin,
            available_upgrade=cabin,
            upgrade_price_pp=price,
            price_delta=delta,
            recommendation=_recommendation_text(booking, cabin, delta),
            detected_at=datetime.now(timezone.utc).isoformat(),
            source_url=booking.voyage_url,
        )
        if best is None or delta < best.price_delta:
            best = candidate
    return best


def run_sweep(
    fetch_fn: FetchFn = _default_fetch,
    watch_path: Path = WATCH_FILE,
    output_path: Path = OUTPUT_FILE,
    dry_run: bool = False,
) -> List[dict]:
    """Entry point for the cron/timer sweep. Scans every active watched
    booking, writes data/upgrade_opportunities.json (unless dry_run)."""
    watches = load_watches(watch_path)
    if not watches:
        log.info("No active cabin upgrade watches configured — nothing to scan")
        if not dry_run:
            save_opportunities([], output_path)
        return []

    opportunities: List[dict] = []
    for booking in watches:
        opp = detect_upgrade_for_booking(booking, fetch_fn=fetch_fn)
        if opp:
            opportunities.append(asdict(opp))
            log.info(
                f"UPGRADE FLAGGED: {booking.booking_id} -> {opp.available_upgrade} "
                f"(Δ ${opp.price_delta:+.2f})"
            )

    if not dry_run:
        save_opportunities(opportunities, output_path)
    return opportunities


def main() -> None:
    parser = argparse.ArgumentParser(description="Cabin upgrade opportunity detector")
    parser.add_argument("--dry-run", action="store_true", help="print only, no write")
    args = parser.parse_args()

    results = run_sweep(dry_run=args.dry_run)
    print(json.dumps(results, indent=2))
    if not results:
        print("No upgrade opportunities detected this sweep.")


if __name__ == "__main__":
    main()
