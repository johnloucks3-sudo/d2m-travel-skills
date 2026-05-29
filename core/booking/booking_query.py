"""
booking_query.py — Unified booking sweep with promo eligibility.

Sweeps BookingMaster (Google Sheet) and TESS (CRM). Deduplicates by
booking ID. Returns enriched, filterable result set.

Solves: promo checks that missed active bookings because the sweep was
manual and incomplete (incident: McLeod 2984034, 2026-05-28).
"""
from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parents[2]))

from core.booking.booking_master import BookingMasterClient

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Filter
# ---------------------------------------------------------------------------

@dataclass
class BookingFilter:
    supplier: Optional[str] = None
    """Substring match against Supplier column, e.g. 'Regent', 'Silversea'."""

    ship: Optional[str] = None
    """Substring match against Notes / TESS trip description, e.g. 'Grandeur'."""

    depart_after: Optional[date] = None
    depart_before: Optional[date] = None

    payment_status: Optional[str] = None
    """'deposit_only' | 'paid_in_full' | 'unpaid'"""

    booking_ids: list[str] = field(default_factory=list)
    """Exact Confirmation_Number match list. Empty = no restriction."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _classify_payment(balance: Optional[float], paid: Optional[float]) -> str:
    b = balance or 0.0
    p = paid or 0.0
    if b <= 0:
        return "paid_in_full"
    if p > 0:
        return "deposit_only"
    return "unpaid"


def _normalize_sheet_row(row: dict) -> dict:
    return {
        "client_name": (row.get("Client_Name") or "").strip(),
        "booking_id": str(
            row.get("Confirmation_Number") or row.get("Booking_ID") or ""
        ).strip(),
        "ship": (row.get("Notes") or "").strip()[:120],
        "supplier": (row.get("Supplier") or "").strip(),
        "start_date": row.get("_parsed_start_date"),
        "balance_due": row.get("_parsed_balance_due"),
        "amount_paid": row.get("_parsed_amount_paid"),
        "fpd": (row.get("Final_Payment_Date") or "").strip(),
        "total_cost": row.get("_parsed_total_cost"),
        "payment_status": _classify_payment(
            row.get("_parsed_balance_due"), row.get("_parsed_amount_paid")
        ),
        "source": "sheet",
        "promo_eligibility_reason": "",
        "_raw_sheet": row,
    }


# ---------------------------------------------------------------------------
# TESS enrichment — best-effort, fails gracefully
# ---------------------------------------------------------------------------

def _try_tess_enrich(results: list[dict]) -> list[dict]:
    """Attempt to add ship/trip info from TESS. No-op if TESS is offline."""
    try:
        from core.booking.thunderbird_tess import TESSClient
        tess = TESSClient()
        resp = tess.list_bookings(page_size=200)
        items = resp.get("Items", [])
    except Exception as e:
        logger.info("TESS enrichment skipped: %s", e)
        return results

    # Index by booking number (cruise-line confirmation number)
    tess_by_id: dict[str, dict] = {}
    for t in items:
        for key in ("BookingNumber", "TripGroupNumber", "bookingNumber"):
            bn = str(t.get(key) or "").strip()
            if bn:
                tess_by_id[bn] = t
                break

    for r in results:
        t = tess_by_id.get(r["booking_id"])
        if not t:
            continue
        r["source"] = "both"
        r["_raw_tess"] = t
        # Use TESS trip description as ship if Notes didn't carry it
        if not r["ship"]:
            desc = t.get("TripDescription") or t.get("tripDescription") or ""
            r["ship"] = desc[:120]

    return results


# ---------------------------------------------------------------------------
# Core sweep
# ---------------------------------------------------------------------------

def find_bookings(f: BookingFilter) -> list[dict]:
    """Sweep BookingMaster + TESS and return filtered, deduplicated bookings.

    Each result dict:
        client_name, booking_id, ship, supplier, start_date,
        balance_due, amount_paid, fpd, total_cost, payment_status,
        source ("sheet" | "both"), promo_eligibility_reason

    TESS enrichment is attempted but fails gracefully — sheet is always
    the authoritative floor.
    """
    bm = BookingMasterClient()
    all_rows = bm.list_bookings()

    results: list[dict] = []
    seen: set[str] = set()

    for row in all_rows:
        r = _normalize_sheet_row(row)
        bid = r["booking_id"]

        if bid and bid in seen:
            continue
        if bid:
            seen.add(bid)

        # --- apply filters ---
        if f.booking_ids and bid not in f.booking_ids:
            continue
        if f.supplier and f.supplier.lower() not in r["supplier"].lower():
            continue
        if f.ship and f.ship.lower() not in r["ship"].lower():
            continue
        if f.depart_after and r["start_date"] and r["start_date"] < f.depart_after:
            continue
        if f.depart_before and r["start_date"] and r["start_date"] > f.depart_before:
            continue
        if f.payment_status and r["payment_status"] != f.payment_status:
            continue

        results.append(r)

    results = _try_tess_enrich(results)
    results.sort(key=lambda r: r["start_date"] or date.max)

    logger.info(
        "find_bookings → %d results (supplier=%r ship=%r payment=%r)",
        len(results), f.supplier, f.ship, f.payment_status,
    )
    return results


# ---------------------------------------------------------------------------
# Promo eligibility
# ---------------------------------------------------------------------------

def check_promo_eligibility(promo: dict, bookings: list[dict]) -> list[dict]:
    """Filter bookings whose departure falls within a promo travel window.

    promo = {
        "code": "4232",
        "supplier": "Regent",
        "travel_window_start": date(2026, 7, 15),
        "travel_window_end": date(2027, 8, 25),
        "book_by": date(2026, 5, 31),   # optional deadline
        "description": "...",           # optional human label
    }

    Returns annotated copies of matching bookings with
    'promo_code' and 'promo_eligibility_reason' populated.
    """
    w_start = promo.get("travel_window_start")
    w_end = promo.get("travel_window_end")
    book_by = promo.get("book_by")
    today = date.today()

    eligible: list[dict] = []
    for b in bookings:
        start = b.get("start_date")
        if not start:
            continue
        if w_start and start < w_start:
            continue
        if w_end and start > w_end:
            continue

        entry = dict(b)
        parts = [f"departure {start} in window {w_start}–{w_end}"]
        if book_by:
            days = (book_by - today).days
            parts.append(
                f"book-by {book_by} {'in ' + str(days) + 'd' if days >= 0 else 'PASSED ' + str(abs(days)) + 'd ago'}"
            )
        entry["promo_code"] = promo.get("code", "")
        entry["promo_eligibility_reason"] = " | ".join(parts)
        eligible.append(entry)

    return eligible


# ---------------------------------------------------------------------------
# CLI smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    print("\n=== REGENT — DEPOSIT-ONLY BOOKINGS ===")
    results = find_bookings(BookingFilter(supplier="Regent", payment_status="deposit_only"))
    for r in results:
        bal = f"${r['balance_due']:,.2f}" if r["balance_due"] else "?"
        print(
            f"  {r['client_name']:<28} {r['booking_id']:<10} "
            f"bal={bal:<12} fpd={r['fpd']:<12} src={r['source']}"
        )
    print(f"  → {len(results)} bookings\n")

    print("=== PROMO 4232 — WOULD HAVE CAUGHT McLEOD 2026-05-28 ===")
    all_regent = find_bookings(BookingFilter(supplier="Regent"))
    eligible = check_promo_eligibility(
        promo={
            "code": "4232",
            "supplier": "Regent",
            "travel_window_start": date(2026, 7, 15),
            "travel_window_end": date(2027, 8, 25),
            "book_by": date(2026, 5, 31),
        },
        bookings=all_regent,
    )
    for e in eligible:
        print(f"  {e['client_name']:<28} {e['booking_id']:<10} {e['promo_eligibility_reason']}")
    print(f"  → {len(eligible)} eligible\n")
