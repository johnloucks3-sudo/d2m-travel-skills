"""
Thunderbird Client Lifecycle Ingester
Determines phase (PHASE_0 through PHASE_5) for all active clients.
Validates anchor dates and payment status.

Dreams2Memories Travel, LLC — Lifecycle System Core

Author: Claude (P0 Development Task)
Date: 2026-04-07
"""

import os
import json
from datetime import datetime, date, timedelta
from typing import Optional, Dict, List, Tuple
import logging

# Setup logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)

# ============================================================================
# PHASE CONSTANTS & DEFINITIONS
# ============================================================================

PHASE_DEFINITIONS = {
    "PHASE_0": {
        "name": "Dream",
        "description": "Initial inquiry, vision setting, destination exploration",
        "anchor": "booking_date",
        "payment_status": None,
        "condition": "today < booking_date"
    },
    "PHASE_1": {
        "name": "Craft",
        "description": "Proposal development, pricing, booking confirmation",
        "anchor": "booking_date",
        "payment_status": None,
        "condition": "booking_date <= today < (booking_date + 60 days)"
    },
    "PHASE_2": {
        "name": "Execute",
        "description": "Payment processing, documentation, supplier coordination",
        "anchor": "fpd",
        "payment_status": ["pending", "partial"],
        "condition": "(booking_date + 60 days) <= today < fpd"
    },
    "PHASE_3": {
        "name": "Polish",
        "description": "Pre-trip validation, guest forms, final approvals",
        "anchor": "embark_date",
        "payment_status": ["paid"],
        "condition": "fpd <= today < (embark_date - 7 days)"
    },
    "PHASE_4": {
        "name": "Voyage",
        "description": "Embarkation, active journey, real-time support",
        "anchor": "embark_date",
        "payment_status": ["paid"],
        "condition": "(embark_date - 7 days) <= today <= disembark_date"
    },
    "PHASE_5": {
        "name": "Return",
        "description": "Disembarkation, post-trip follow-up, review request",
        "anchor": "disembark_date",
        "payment_status": ["paid"],
        "condition": "today > disembark_date"
    }
}


# ============================================================================
# PHASE DETERMINATION ALGORITHM (1b)
# ============================================================================

def determine_phase(
    booking_date: date,
    embark_date: date,
    disembark_date: date,
    fpd: date,
    payment_status: Optional[str] = None,
    payment_date: Optional[date] = None,
    client_label: str = "",
    as_of: Optional[date] = None
) -> Tuple[str, str]:
    """
    Determine client lifecycle phase based on anchor dates and payment status.

    Args:
        booking_date: Date booking was confirmed
        embark_date: Ship embarkation date
        disembark_date: Ship disembarkation date
        fpd: Final payment due date
        payment_status: "paid", "pending", or "partial"
        payment_date: Actual date payment was received (if any)
        client_label: Human-readable client identifier
        as_of: Reference date to evaluate against (default: today). Lets
            callers (tests, event handlers) compute the phase for a fixed
            point in time instead of the moment the process happens to run.

    Returns:
        Tuple: (phase_code, phase_name)
        e.g. ("PHASE_3", "Polish")
    """
    today = as_of or date.today()

    # Business logic priority: immovable dates override everything

    # After disembark
    if today > disembark_date:
        return ("PHASE_5", PHASE_DEFINITIONS["PHASE_5"]["name"])

    # Embark through disembark
    if embark_date <= today <= disembark_date:
        return ("PHASE_4", PHASE_DEFINITIONS["PHASE_4"]["name"])

    # Within 7 days of embark (pre-voyage preparation phase)
    if today >= (embark_date - timedelta(days=7)):
        return ("PHASE_4", PHASE_DEFINITIONS["PHASE_4"]["name"])

    # Payment received → Polish phase
    if payment_status == "paid" and today >= fpd and today < (embark_date - timedelta(days=7)):
        return ("PHASE_3", PHASE_DEFINITIONS["PHASE_3"]["name"])

    # FPD approaching or passed
    if today >= fpd:
        # If paid: Polish
        if payment_status == "paid":
            return ("PHASE_3", PHASE_DEFINITIONS["PHASE_3"]["name"])
        # If not paid by FPD: still Execute (red flag)
        else:
            return ("PHASE_2", PHASE_DEFINITIONS["PHASE_2"]["name"])

    # Pre-FPD: Execute phase
    if today >= booking_date:
        # Allow 60 days for Craft phase after booking
        if today < (booking_date + timedelta(days=60)):
            return ("PHASE_1", PHASE_DEFINITIONS["PHASE_1"]["name"])
        else:
            return ("PHASE_2", PHASE_DEFINITIONS["PHASE_2"]["name"])

    # Before booking date: Dream phase
    if today < booking_date:
        return ("PHASE_0", PHASE_DEFINITIONS["PHASE_0"]["name"])

    # Fallback (should not reach)
    return ("PHASE_UNKNOWN", "Unknown")


# ============================================================================
# ANCHOR DATE VALIDATOR (1c)
# ============================================================================

def validate_anchor_dates(
    booking_date: Optional[date] = None,
    embark_date: Optional[date] = None,
    disembark_date: Optional[date] = None,
    fpd: Optional[date] = None,
    client_label: str = "",
    as_of: Optional[date] = None
) -> Dict[str, any]:
    """
    Validate that all required anchor dates exist and are logically consistent.

    Returns:
        {
            "valid": True/False,
            "errors": [...],
            "warnings": [...],
            "anchor_count": int
        }
    """
    errors = []
    warnings = []
    anchor_count = 0

    # Check existence
    if not booking_date:
        errors.append(f"{client_label}: Missing booking_date")
    else:
        anchor_count += 1

    if not embark_date:
        errors.append(f"{client_label}: Missing embark_date")
    else:
        anchor_count += 1

    if not disembark_date:
        errors.append(f"{client_label}: Missing disembark_date")
    else:
        anchor_count += 1

    if not fpd:
        errors.append(f"{client_label}: Missing fpd (final payment date)")
    else:
        anchor_count += 1

    # If all exist, validate logical order
    if all([booking_date, embark_date, disembark_date, fpd]):
        if embark_date <= disembark_date:
            # Good
            pass
        else:
            errors.append(f"{client_label}: embark_date after disembark_date")

        if fpd <= embark_date:
            # Good (FPD typically 60-120 days before embark)
            pass
        else:
            errors.append(f"{client_label}: fpd after embark_date")

        if booking_date < embark_date:
            # Good
            pass
        else:
            errors.append(f"{client_label}: booking_date not before embark")

        # Warning if FPD is very close to embark (< 14 days)
        today = as_of or date.today()
        days_to_fpd = (fpd - today).days
        if 0 <= days_to_fpd < 14:
            warnings.append(f"{client_label}: FPD approaching (T-{days_to_fpd} days)")

        # Warning if voyage dates are in the past (should be future-dated or current)
        if embark_date < today:
            warnings.append(f"{client_label}: embark_date is in the past")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "anchor_count": anchor_count
    }


# ============================================================================
# CLIENT PHASE ASSIGNMENT (1d)
# ============================================================================

def assign_phases_from_dossier(
    dossier_path: str,
    output_file: str = "/home/john/Thunderbird/storage/client_phase_assignment.json"
) -> Dict[str, dict]:
    """
    Read all dossiers and compute phase assignment for each client.
    Outputs to JSON file for further processing.

    Args:
        dossier_path: Path to dossiers directory
        output_file: Where to write client_phase_assignment.json

    Returns:
        Dict mapping client names to their phase data
    """
    results = {}

    # Hardcoded client data for MVP (from task context)
    clients_data = {
        "Furlow": {
            "booking_date": date(2025, 9, 15),
            "embark_date": date(2026, 8, 29),
            "disembark_date": date(2026, 9, 8),
            "fpd": date(2026, 4, 1),
            "payment_status": "paid",
            "payment_date": date(2026, 3, 25),
            "ship": "SS Grandeur",
            "voyage": "Scandinavia",
        },
        "Nichols": {
            "booking_date": date(2025, 10, 1),
            "embark_date": date(2026, 8, 29),
            "disembark_date": date(2026, 9, 8),
            "fpd": date(2026, 4, 1),
            "payment_status": "paid",
            "payment_date": date(2026, 3, 31),
            "ship": "SS Grandeur",
            "voyage": "Scandinavia",
        },
        "Ely": {
            "booking_date": date(2025, 10, 1),
            "embark_date": date(2026, 8, 29),
            "disembark_date": date(2026, 9, 8),
            "fpd": date(2026, 4, 1),
            "payment_status": "paid",
            "payment_date": date(2026, 3, 30),
            "ship": "SS Grandeur",
            "voyage": "Scandinavia",
        },
        "Lyons": {
            "booking_date": date(2026, 2, 1),
            "embark_date": date(2026, 8, 11),
            "disembark_date": date(2026, 8, 18),
            "fpd": date(2026, 5, 15),
            "payment_status": "pending",
            "payment_date": None,
            "ship": "RSSC Splendor",
            "voyage": "Athens to New York",
        },
        "McLeod": {
            "booking_date": date(2025, 11, 1),
            "embark_date": date(2026, 6, 23),
            "disembark_date": date(2026, 7, 3),
            "fpd": date(2026, 1, 24),
            "payment_status": "paid",
            "payment_date": date(2026, 1, 20),
            "ship": "Silver Muse",
            "voyage": "Mediterranean",
        },
        "Westbrook": {
            "booking_date": date(2026, 2, 15),
            "embark_date": date(2026, 4, 13),
            "disembark_date": date(2026, 4, 18),
            "fpd": date(2026, 3, 13),
            "payment_status": "paid",
            "payment_date": date(2026, 3, 10),
            "ship": "Silver Nova",
            "voyage": "Honolulu",
        },
        "Kuklinski": {
            "booking_date": date(2025, 12, 1),
            "embark_date": date(2026, 12, 17),
            "disembark_date": date(2026, 12, 27),
            "fpd": date(2026, 8, 15),
            "payment_status": "pending",
            "payment_date": None,
            "ship": "Viking Mars",
            "voyage": "Panama Canal",
        },
    }

    for client_name, data in clients_data.items():
        # Validate anchors
        validation = validate_anchor_dates(
            booking_date=data.get("booking_date"),
            embark_date=data.get("embark_date"),
            disembark_date=data.get("disembark_date"),
            fpd=data.get("fpd"),
            client_label=client_name
        )

        if not validation["valid"]:
            logger.error(f"{client_name}: {validation['errors']}")
            continue

        # Determine phase
        phase_code, phase_name = determine_phase(
            booking_date=data.get("booking_date"),
            embark_date=data.get("embark_date"),
            disembark_date=data.get("disembark_date"),
            fpd=data.get("fpd"),
            payment_status=data.get("payment_status"),
            payment_date=data.get("payment_date"),
            client_label=client_name
        )

        results[client_name] = {
            "phase_code": phase_code,
            "phase_name": phase_name,
            "phase_definition": PHASE_DEFINITIONS.get(phase_code),
            "booking_date": data.get("booking_date").isoformat(),
            "embark_date": data.get("embark_date").isoformat(),
            "disembark_date": data.get("disembark_date").isoformat(),
            "fpd": data.get("fpd").isoformat(),
            "payment_status": data.get("payment_status"),
            "payment_date": data.get("payment_date").isoformat() if data.get("payment_date") else None,
            "ship": data.get("ship"),
            "voyage": data.get("voyage"),
            "anchor_validation": validation,
            "days_to_embark": (data.get("embark_date") - date.today()).days,
            "days_to_disembark": (data.get("disembark_date") - date.today()).days,
        }

        logger.info(f"{client_name}: {phase_code} ({phase_name})")

    # Write output
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    logger.info(f"Client phase assignments written to {output_file}")
    return results


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import sys

    # Default output location
    output_path = "/home/john/Thunderbird/storage/client_phase_assignment.json"

    if len(sys.argv) > 1:
        output_path = sys.argv[1]

    results = assign_phases_from_dossier(
        dossier_path="/home/john/Thunderbird/dossiers",
        output_file=output_path
    )

    print(f"\n✅ Phase assignments complete: {output_path}")
    print(f"   Processed: {len(results)} clients")
    for client, data in results.items():
        print(f"   • {client}: {data['phase_code']} ({data['phase_name']})")
