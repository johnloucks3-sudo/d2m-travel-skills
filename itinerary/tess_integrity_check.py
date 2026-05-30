#!/usr/bin/env python3
"""
TESS Pre-Generation Integrity Check
====================================
A7 Sterling | Dreams2Memories Travel, LLC
Built: 2026-05-30 | Per ELON overnight recommendation

PURPOSE:
  Before any generator (McLeod, Furlow, Kuklinski, etc.) runs, cross-check
  the dossier against live TESS booking data to catch contamination-class
  errors (like the Loucks dossier incident 2026-05-28 where fabricated data
  entered a dossier without TESS verification).

FAIL-OPEN CONTRACT:
  If TESS is unreachable, token is expired, or returns nothing — the check
  logs "TESS UNAVAILABLE — skipping integrity check" and returns a result
  that does NOT block generation. Generators must never be blocked by a
  monitoring tool. Contamination detection is advisory unless a hard MISMATCH
  is found on a CONFIRMED field.

FIELD COMPARISON LOGIC:
  - departure_date  : dossier frontmatter 'departure' vs TESS StartDate
  - return_date     : dossier frontmatter 'return'    vs TESS EndDate
  - fpd             : dossier frontmatter 'fpd'        vs TESS FinalPaymentDate
  - package_price   : dossier frontmatter 'fpd_amount' vs TESS PackagePrice
  - booking_status  : dossier frontmatter 'payment_status' mapped vs TESS StatusName

STATUS CODES:
  CONFIRMED   — values match (within tolerance for amounts)
  MISMATCH    — values present on both sides but differ — HARD FLAG
  NOT_FOUND   — booking number not in TESS — treat as WARN, not block
  TESS_UNAVAILABLE — TESS unreachable or auth failed — do not block
  SKIP        — field not present in dossier frontmatter

USAGE:
  # CLI
  python3 itinerary/tess_integrity_check.py --dossier dossiers/Kuklinski_Viking_Panama.md
  python3 itinerary/tess_integrity_check.py --dossier dossiers/Furlow_Regent_3071222.md

  # Programmatic
  from itinerary.tess_integrity_check import check_tess_integrity
  results = check_tess_integrity("dossiers/Furlow_Regent_3071222.md")

RETURN CONTRACT:
  List of dicts, one per compared field:
  {
    "field": str,
    "status": "CONFIRMED" | "MISMATCH" | "NOT_FOUND" | "TESS_UNAVAILABLE" | "SKIP",
    "dossier": str,   # value from dossier frontmatter (or "" if absent)
    "tess": str,      # value from TESS (or "" if not found)
    "note": str       # human-readable explanation
  }
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Bootstrap: ensure Thunderbird root is on sys.path regardless of cwd
# ---------------------------------------------------------------------------
THUNDERBIRD_DIR = Path(__file__).resolve().parent.parent
if str(THUNDERBIRD_DIR) not in sys.path:
    sys.path.insert(0, str(THUNDERBIRD_DIR))

try:
    from core.booking.thunderbird_tess import TESSClient
    _TESS_IMPORT_OK = True
except ImportError as _e:
    _TESS_IMPORT_OK = False
    _TESS_IMPORT_ERR = str(_e)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

AMOUNT_TOLERANCE_PCT = 0.02   # 2% — allow minor rounding across booking legs
DATE_FORMAT_ISO = "%Y-%m-%d"

# Payment status → TESS StatusName mapping (dossier values → TESS values)
PAYMENT_STATUS_MAP = {
    "paid_in_full": "Active",
    "paid": "Active",
    "active": "Active",
    "balance_due": "Active",
    "overdue": "Active",
    "cancelled": "Cancelled",
    "canceled": "Cancelled",
    "pending": "Active",
}


# ---------------------------------------------------------------------------
# Dossier frontmatter parser
# ---------------------------------------------------------------------------

def _parse_frontmatter(dossier_path: str | Path) -> dict[str, str]:
    """Extract YAML-style frontmatter from a markdown dossier.

    Returns a dict of {key: value} strings. Empty dict if no frontmatter found.
    Frontmatter is defined as the block between the first pair of '---' lines.
    """
    path = Path(dossier_path)
    if not path.exists():
        logger.error(f"Dossier not found: {path}")
        return {}

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    # Must start with '---'
    if not lines or lines[0].strip() != "---":
        return {}

    fm_lines: list[str] = []
    in_fm = False
    for i, line in enumerate(lines):
        if i == 0 and line.strip() == "---":
            in_fm = True
            continue
        if in_fm:
            if line.strip() == "---":
                break
            fm_lines.append(line)

    result: dict[str, str] = {}
    for line in fm_lines:
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key:
            result[key] = val

    return result


def _parse_body_booking_numbers(dossier_path: str | Path) -> list[str]:
    """Scan dossier body for booking numbers in tables (for group dossiers).

    Looks for patterns like | 9593880 | in markdown tables.
    Returns deduplicated list of 7-digit booking numbers found.
    """
    path = Path(dossier_path)
    if not path.exists():
        return []

    text = path.read_text(encoding="utf-8")
    # Match 7-digit numbers in table cells (common Viking/Regent booking format)
    # Also match 7-digit numbers after "Booking " prefix
    pattern = r"\b(\d{7})\b"
    candidates = re.findall(pattern, text)
    # Deduplicate preserving order
    seen: set[str] = set()
    result: list[str] = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            result.append(c)
    return result


# ---------------------------------------------------------------------------
# TESS query
# ---------------------------------------------------------------------------

def _query_tess_booking(booking_number: str) -> dict[str, Any] | None:
    """Query TESS for a booking by booking number.

    Returns the first matching booking Item dict, or None if not found
    or if TESS is unavailable.

    Raises no exceptions — all errors are caught and logged.
    """
    if not _TESS_IMPORT_OK:
        logger.warning(f"TESS client import failed: {_TESS_IMPORT_ERR}")
        return None

    try:
        client = TESSClient()
        result = client.list_bookings(
            bookingNumber=booking_number,
            pageNumber=1,
            pageSize=5,
        )
    except Exception as e:
        logger.warning(f"TESS query exception for booking {booking_number}: {e}")
        return None

    if "error" in result:
        logger.warning(f"TESS API error for booking {booking_number}: {result['error']}")
        return None

    items = result.get("Items", [])
    if not items:
        return None

    # If multiple items (shouldn't happen for a booking number search), take first
    return items[0]


# ---------------------------------------------------------------------------
# Field comparisons
# ---------------------------------------------------------------------------

def _compare_date(
    field: str,
    dossier_val: str,
    tess_val: str | None,
) -> dict[str, str]:
    """Compare a date field. TESS dates are ISO8601 with time component."""
    if not dossier_val:
        return {
            "field": field, "status": "SKIP",
            "dossier": "", "tess": tess_val or "",
            "note": f"Field '{field}' not in dossier frontmatter — skipped"
        }
    if tess_val is None:
        return {
            "field": field, "status": "NOT_FOUND",
            "dossier": dossier_val, "tess": "",
            "note": f"TESS returned no value for {field}"
        }

    # Parse TESS date (ISO8601 with or without time)
    try:
        tess_date = datetime.fromisoformat(tess_val.replace("Z", "+00:00")).date()
        tess_str = tess_date.strftime(DATE_FORMAT_ISO)
    except ValueError:
        return {
            "field": field, "status": "MISMATCH",
            "dossier": dossier_val, "tess": tess_val,
            "note": f"TESS date format unrecognized: {tess_val!r}"
        }

    if dossier_val == tess_str:
        return {
            "field": field, "status": "CONFIRMED",
            "dossier": dossier_val, "tess": tess_str,
            "note": "Date matches TESS record"
        }
    return {
        "field": field, "status": "MISMATCH",
        "dossier": dossier_val, "tess": tess_str,
        "note": f"Date mismatch — dossier says {dossier_val}, TESS says {tess_str}"
    }


def _compare_amount(
    field: str,
    dossier_val: str,
    tess_val: float | None,
    note_prefix: str = "",
) -> dict[str, str]:
    """Compare a monetary amount within tolerance."""
    if not dossier_val:
        return {
            "field": field, "status": "SKIP",
            "dossier": "", "tess": str(tess_val) if tess_val is not None else "",
            "note": f"Field '{field}' not in dossier frontmatter — skipped"
        }
    if tess_val is None:
        return {
            "field": field, "status": "NOT_FOUND",
            "dossier": dossier_val, "tess": "",
            "note": f"TESS returned no value for {field}"
        }

    try:
        dossier_amount = float(dossier_val.replace(",", "").replace("$", ""))
    except ValueError:
        return {
            "field": field, "status": "SKIP",
            "dossier": dossier_val, "tess": str(tess_val),
            "note": f"Dossier amount not parseable: {dossier_val!r}"
        }

    tolerance = max(dossier_amount, tess_val) * AMOUNT_TOLERANCE_PCT
    if abs(dossier_amount - tess_val) <= tolerance:
        return {
            "field": field, "status": "CONFIRMED",
            "dossier": f"${dossier_amount:,.2f}",
            "tess": f"${tess_val:,.2f}",
            "note": f"{note_prefix}Amount within {AMOUNT_TOLERANCE_PCT*100:.0f}% tolerance"
        }

    return {
        "field": field, "status": "MISMATCH",
        "dossier": f"${dossier_amount:,.2f}",
        "tess": f"${tess_val:,.2f}",
        "note": (
            f"{note_prefix}Amount mismatch — dossier ${dossier_amount:,.2f}, "
            f"TESS ${tess_val:,.2f} (delta ${abs(dossier_amount - tess_val):,.2f})"
        )
    }


def _compare_booking_status(
    dossier_payment_status: str,
    tess_status_name: str | None,
) -> dict[str, str]:
    """Compare payment status via the mapping table."""
    field = "payment_status"
    if not dossier_payment_status:
        return {
            "field": field, "status": "SKIP",
            "dossier": "", "tess": tess_status_name or "",
            "note": "payment_status not in dossier frontmatter — skipped"
        }
    if tess_status_name is None:
        return {
            "field": field, "status": "NOT_FOUND",
            "dossier": dossier_payment_status, "tess": "",
            "note": "TESS returned no status"
        }

    expected_tess = PAYMENT_STATUS_MAP.get(dossier_payment_status.lower(), "")
    if expected_tess and expected_tess.lower() == tess_status_name.lower():
        return {
            "field": field, "status": "CONFIRMED",
            "dossier": dossier_payment_status,
            "tess": tess_status_name,
            "note": f"Status maps correctly: dossier '{dossier_payment_status}' → TESS '{tess_status_name}'"
        }
    if not expected_tess:
        return {
            "field": field, "status": "SKIP",
            "dossier": dossier_payment_status,
            "tess": tess_status_name,
            "note": f"No mapping for dossier status '{dossier_payment_status}' — cannot compare"
        }
    return {
        "field": field, "status": "MISMATCH",
        "dossier": dossier_payment_status,
        "tess": tess_status_name,
        "note": (
            f"Status mismatch — dossier '{dossier_payment_status}' "
            f"maps to '{expected_tess}' but TESS shows '{tess_status_name}'"
        )
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def check_tess_integrity(dossier_path: str | Path) -> list[dict[str, str]]:
    """Run TESS integrity check against a dossier file.

    Returns a list of field comparison results. Always returns a list —
    never raises. On TESS unavailability, returns a single TESS_UNAVAILABLE
    result that does NOT block generation.

    Parameters
    ----------
    dossier_path : str | Path
        Path to the .md dossier file to check.

    Returns
    -------
    list[dict]
        Each dict has keys: field, status, dossier, tess, note.
        status values: CONFIRMED | MISMATCH | NOT_FOUND | TESS_UNAVAILABLE | SKIP
    """
    dossier_path = Path(dossier_path)
    results: list[dict[str, str]] = []

    # --- Parse dossier frontmatter ---
    fm = _parse_frontmatter(dossier_path)
    if not fm:
        logger.warning(f"No frontmatter found in {dossier_path}")
        results.append({
            "field": "frontmatter",
            "status": "SKIP",
            "dossier": "",
            "tess": "",
            "note": f"No YAML frontmatter found in {dossier_path.name} — integrity check skipped"
        })
        return results

    # --- Resolve booking number ---
    booking_number = fm.get("booking", "").strip('"').strip("'")

    # For group dossiers without a frontmatter 'booking' field,
    # attempt to extract from body
    body_booking_numbers: list[str] = []
    if not booking_number:
        body_booking_numbers = _parse_body_booking_numbers(dossier_path)
        if body_booking_numbers:
            booking_number = body_booking_numbers[0]
            logger.info(
                f"No 'booking' in frontmatter — using first body booking number: {booking_number}"
                f" (all found: {body_booking_numbers})"
            )

    if not booking_number:
        results.append({
            "field": "booking_number",
            "status": "SKIP",
            "dossier": "",
            "tess": "",
            "note": "No booking number found in frontmatter or body — TESS check skipped"
        })
        return results

    # --- Query TESS ---
    logger.info(f"Querying TESS for booking number: {booking_number}")
    tess_item = _query_tess_booking(booking_number)

    if tess_item is None:
        # TESS unavailable or booking not found — determine which
        if not _TESS_IMPORT_OK:
            unavail_reason = f"TESS client import failed: {_TESS_IMPORT_ERR}"
        else:
            unavail_reason = f"Booking {booking_number} not found in TESS (auth may have expired)"

        logger.warning(f"TESS UNAVAILABLE — {unavail_reason}")
        results.append({
            "field": "tess_connection",
            "status": "TESS_UNAVAILABLE",
            "dossier": booking_number,
            "tess": "",
            "note": f"TESS UNAVAILABLE — skipping integrity check. Reason: {unavail_reason}"
        })
        return results

    # We have a TESS record — run field comparisons
    tess_booking_id = tess_item.get("BookingID", "")
    logger.info(
        f"TESS record found for booking {booking_number}: "
        f"BookingID={tess_booking_id}, Trip='{tess_item.get('TripDescription', '')}'"
    )

    # --- 1. Departure date ---
    results.append(_compare_date(
        "departure_date",
        fm.get("departure", ""),
        tess_item.get("StartDate"),
    ))

    # --- 2. Return date ---
    results.append(_compare_date(
        "return_date",
        fm.get("return", ""),
        tess_item.get("EndDate"),
    ))

    # --- 3. Final payment date ---
    results.append(_compare_date(
        "fpd",
        fm.get("fpd", ""),
        tess_item.get("FinalPaymentDate"),
    ))

    # --- 4. Package price ---
    # Note: group dossiers carry a group total in fpd_amount; TESS carries per-booking.
    # If multiple booking numbers were found in body, note that comparison is per-booking.
    price_note = ""
    if len(body_booking_numbers) > 1:
        price_note = (
            f"Group dossier — comparing per-booking TESS price vs dossier fpd_amount "
            f"(group total). Checked booking {booking_number} of {body_booking_numbers}. "
        )

    results.append(_compare_amount(
        "package_price",
        fm.get("fpd_amount", ""),
        tess_item.get("PackagePrice"),
        note_prefix=price_note,
    ))

    # --- 5. Booking status ---
    tess_status = (tess_item.get("BookingStatus") or {}).get("StatusName")
    results.append(_compare_booking_status(
        fm.get("payment_status", ""),
        tess_status,
    ))

    # --- Metadata row (informational, not a comparison) ---
    results.append({
        "field": "tess_booking_id",
        "status": "CONFIRMED",
        "dossier": booking_number,
        "tess": str(tess_booking_id),
        "note": f"TESS internal BookingID for booking number {booking_number}"
    })

    return results


# ---------------------------------------------------------------------------
# Report formatter
# ---------------------------------------------------------------------------

def format_report(
    results: list[dict[str, str]],
    dossier_path: str | Path,
    booking_number: str = "",
) -> str:
    """Format integrity check results as a human-readable report."""
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append(f"TESS INTEGRITY CHECK — {Path(dossier_path).name}")
    lines.append("=" * 60)
    if booking_number:
        lines.append(f"Booking number: {booking_number}")
    lines.append("")

    status_icons = {
        "CONFIRMED": "OK",
        "MISMATCH": "MISMATCH",
        "NOT_FOUND": "NOT_FOUND",
        "TESS_UNAVAILABLE": "TESS_UNAVAILABLE",
        "SKIP": "SKIP",
    }

    mismatches: list[dict] = []
    for r in results:
        icon = status_icons.get(r["status"], r["status"])
        lines.append(f"  [{icon}] {r['field']}")
        if r["dossier"] or r["tess"]:
            lines.append(f"        dossier: {r['dossier']}")
            lines.append(f"        tess:    {r['tess']}")
        lines.append(f"        note:    {r['note']}")
        lines.append("")
        if r["status"] == "MISMATCH":
            mismatches.append(r)

    lines.append("-" * 60)
    confirmed = sum(1 for r in results if r["status"] == "CONFIRMED")
    skipped = sum(1 for r in results if r["status"] in ("SKIP", "TESS_UNAVAILABLE"))
    not_found = sum(1 for r in results if r["status"] == "NOT_FOUND")

    if mismatches:
        lines.append(f"RESULT: {len(mismatches)} MISMATCH(ES) DETECTED — REVIEW BEFORE GENERATION")
        for m in mismatches:
            lines.append(f"  -> {m['field']}: {m['note']}")
    elif any(r["status"] == "TESS_UNAVAILABLE" for r in results):
        lines.append("RESULT: TESS UNAVAILABLE — skipping integrity check (fail-open)")
    else:
        lines.append(
            f"RESULT: CLEAN — {confirmed} confirmed, {not_found} not_found, {skipped} skipped"
        )
    lines.append("=" * 60)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(
        description="TESS pre-generation integrity check for D2M dossiers"
    )
    parser.add_argument(
        "--dossier", "-d",
        required=True,
        help="Path to the .md dossier file (absolute or relative to cwd)",
    )
    parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Output raw JSON results instead of formatted report",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.INFO)

    dossier_path = Path(args.dossier)
    if not dossier_path.is_absolute():
        # Try relative to Thunderbird dir first, then cwd
        candidate = THUNDERBIRD_DIR / dossier_path
        if candidate.exists():
            dossier_path = candidate

    results = check_tess_integrity(dossier_path)

    # Extract booking number for report header
    fm = _parse_frontmatter(dossier_path)
    booking_number = fm.get("booking", "")
    if not booking_number:
        body_nums = _parse_body_booking_numbers(dossier_path)
        if body_nums:
            booking_number = body_nums[0] + f" (+ {len(body_nums)-1} more)" if len(body_nums) > 1 else body_nums[0]

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(format_report(results, dossier_path, booking_number))

    # Exit code: 0=clean/skip, 1=mismatch found
    has_mismatch = any(r["status"] == "MISMATCH" for r in results)
    return 1 if has_mismatch else 0


if __name__ == "__main__":
    sys.exit(main())
