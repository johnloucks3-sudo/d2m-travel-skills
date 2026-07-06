"""
insurance_integrator.py — Auto-quote + dossier sync for travel insurance
=========================================================================
On booking, pulls trip cost / traveler ages / destinations, gets quotes from
all three partner wrappers (TravelGuard, Generali, World Nomads), persists
them to insurance_quotes.json, and formats the TP 0.5 insurance block.
When a client accepts a plan, syncs carrier/policy/coverage dates back to
the dossier frontmatter.

Negative-Space Rule (SO-PIPELINE-INTEGRITY-20260528): traveler age is not
stored in the dossier schema today. auto_quote_for_booking() never guesses
an age — if it isn't passed explicitly and isn't in the dossier, it returns
a result with ok=False and a named missing field instead of quoting against
a fabricated age.

CLI:
    python3 -m core.insurance.insurance_integrator \\
        --dossier dossiers/Loucks.md --booking booking_2 \\
        --trip-cost 24798 --ages 65 63 --destinations "Mediterranean"
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

import yaml

from core.insurance.partner_apis import ALL_PARTNERS, InsuranceQuote

THUNDERBIRD_ROOT = Path(__file__).resolve().parents[2]
QUOTES_STORE_PATH = THUNDERBIRD_ROOT / "core" / "insurance" / "insurance_quotes.json"

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


# ---------------------------------------------------------------------------
# Quote generation
# ---------------------------------------------------------------------------

def generate_quotes(
    trip_cost: float,
    traveler_ages: list,
    destinations: list,
    departure_date,
    return_date,
    deposit_date=None,
    booking_ref: str = "",
) -> list:
    """Call every partner wrapper, return a list of InsuranceQuote."""
    quotes = []
    for partner_cls in ALL_PARTNERS:
        partner = partner_cls()
        quotes.append(
            partner.quote(
                trip_cost=trip_cost,
                traveler_ages=traveler_ages,
                destinations=destinations,
                departure_date=departure_date,
                return_date=return_date,
                deposit_date=deposit_date,
                booking_ref=booking_ref,
            )
        )
    return quotes


# ---------------------------------------------------------------------------
# Dossier read
# ---------------------------------------------------------------------------

def _read_frontmatter(dossier_path: Path) -> dict:
    text = dossier_path.read_text()
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    return yaml.safe_load(m.group(1)) or {}


def _write_frontmatter(dossier_path: Path, frontmatter: dict) -> None:
    text = dossier_path.read_text()
    m = FRONTMATTER_RE.match(text)
    new_yaml = yaml.safe_dump(frontmatter, sort_keys=False, default_flow_style=False, allow_unicode=True)
    new_block = f"---\n{new_yaml}---\n"
    if m:
        text = FRONTMATTER_RE.sub(new_block, text, count=1)
    else:
        text = new_block + text
    dossier_path.write_text(text)


def _extract_booking_fields(fm: dict, booking_id: str) -> tuple:
    """
    Supports two dossier schemas seen in this repo:
      - multi-booking: booking_1, booking_2, ... with booking_N_ship / _departure / _total / _fpd_amount
      - single-booking: booking / ship / departure / invoice_total / balance_due at top level

    Returns (prefix_or_ref, trip_cost, ship, departure_date, deposit_date).
    Never fabricates a value — missing fields come back as None.
    """
    prefix = booking_id if booking_id.startswith("booking_") else f"booking_{booking_id}"
    if any(k.startswith(f"{prefix}_") for k in fm) or prefix in fm:
        trip_cost = fm.get(f"{prefix}_total") or fm.get(f"{prefix}_fpd_amount")
        ship = fm.get(f"{prefix}_ship", "")
        departure_date = fm.get(f"{prefix}_departure")
        deposit_date = fm.get(f"{prefix}_fpd_amount_verified_date")
        booking_ref = fm.get(prefix, prefix)
        return prefix, trip_cost, ship, departure_date, deposit_date, booking_ref

    # Single-booking flat schema — booking_id should match fm['booking']
    if str(fm.get("booking", "")) == str(booking_id):
        trip_cost = fm.get("invoice_total") or fm.get("balance_due")
        ship = fm.get("ship", "")
        departure_date = fm.get("departure")
        deposit_date = fm.get("balance_due_verified_date") or fm.get("fpd_verified_date")
        booking_ref = fm.get("booking", booking_id)
        return "booking", trip_cost, ship, departure_date, deposit_date, booking_ref

    return prefix, None, "", None, None, booking_id


def auto_quote_for_booking(
    dossier_path: str,
    booking_id: str,
    trip_cost: Optional[float] = None,
    traveler_ages: Optional[list] = None,
    destinations: Optional[list] = None,
) -> dict:
    """
    Reads trip cost / departure date / ship from the dossier (when not passed
    explicitly), across both the multi-booking (booking_N_*) and single-booking
    (flat) dossier schemas used in this repo. traveler_ages MUST be supplied
    by the caller or already present in the dossier — never inferred or
    defaulted (Negative-Space Rule, SO-PIPELINE-INTEGRITY-20260528).
    """
    path = Path(dossier_path)
    fm = _read_frontmatter(path)

    prefix, fm_trip_cost, ship, fm_departure, fm_deposit_date, booking_ref = _extract_booking_fields(
        fm, booking_id
    )

    if trip_cost is None:
        trip_cost = fm_trip_cost
    if traveler_ages is None:
        traveler_ages = fm.get(f"{prefix}_traveler_ages") or fm.get("traveler_ages")
    if destinations is None:
        destinations = [ship] if ship else []
    departure_date = fm_departure

    missing = [
        name
        for name, val in [
            ("trip_cost", trip_cost),
            ("traveler_ages", traveler_ages),
            ("departure_date", departure_date),
        ]
        if not val
    ]
    if missing:
        return {"ok": False, "missing_fields": missing, "booking_id": prefix}
    quotes = generate_quotes(
        trip_cost=float(trip_cost),
        traveler_ages=list(traveler_ages),
        destinations=list(destinations),
        departure_date=departure_date,
        return_date=departure_date,
        deposit_date=fm_deposit_date,
        booking_ref=str(booking_ref),
    )

    client_name = fm.get("client", path.stem)
    persist_quotes(client_name, prefix, quotes, {"dossier": str(path), "booking_ref": booking_ref})

    return {
        "ok": True,
        "booking_id": prefix,
        "client": client_name,
        "quotes": [q.to_dict() for q in quotes],
    }


# ---------------------------------------------------------------------------
# Persistence — insurance_quotes.json
# ---------------------------------------------------------------------------

def _load_store() -> dict:
    if not QUOTES_STORE_PATH.exists():
        return {}
    return json.loads(QUOTES_STORE_PATH.read_text())


def _save_store(store: dict) -> None:
    QUOTES_STORE_PATH.write_text(json.dumps(store, indent=2, sort_keys=True))


def persist_quotes(client_name: str, booking_id: str, quotes: list, meta: dict) -> None:
    store = _load_store()
    key = f"{client_name}::{booking_id}"
    store[key] = {
        "client": client_name,
        "booking_id": booking_id,
        "quoted_at": datetime.now(timezone.utc).isoformat(),
        "quotes": [q.to_dict() for q in quotes],
        "meta": meta,
        "acceptance": store.get(key, {}).get("acceptance"),
    }
    _save_store(store)


# ---------------------------------------------------------------------------
# TP 0.5 integration
# ---------------------------------------------------------------------------

def format_tp05_insurance_snippet(quotes: list, coverage_deadline: Optional[str] = None) -> str:
    """
    Render an HTML block (dark-navy template convention) listing the 3
    partner quotes for embedding in TP 0.5. Not a standalone email —
    a fragment to splice into the existing tp_0_5_welcome_validation.html
    body ahead of the sign-off.
    """
    rows = []
    for q in quotes:
        waiver = (
            f"waiver by {q['pre_existing_waiver_deadline']}"
            if q["pre_existing_waiver_available"] and q["pre_existing_waiver_deadline"]
            else ("waiver available" if q["pre_existing_waiver_available"] else "no pre-existing waiver")
        )
        rows.append(
            '<tr><td style="padding:10px 12px;color:#d0e4ff;font-family:Georgia,serif;'
            'font-size:14px;border:1px solid rgba(180,200,255,0.15);width:30%">'
            f'<strong style="color:#f0f6ff">{q["carrier"]}</strong> — {q["plan_name"]}</td>'
            '<td style="padding:10px 12px;color:#d0e4ff;font-family:Georgia,serif;'
            f'font-size:14px;border:1px solid rgba(180,200,255,0.15)">${q["premium"]:,.2f} &mdash; {waiver}</td></tr>'
        )
    deadline_html = (
        f'<div style="background:rgba(255,180,50,0.12);border-left:4px solid rgba(255,180,50,0.7);'
        f'padding:14px 18px;margin:16px 0"><span style="color:#ffe0a0;font-family:Georgia,serif;'
        f'font-size:14px"><strong>Pre-Existing Condition Deadline: {coverage_deadline}</strong></span></div>'
        if coverage_deadline
        else ""
    )
    return (
        '<h2 style="color:#c8dcff;font-family:Georgia,serif;font-size:16px;letter-spacing:1.5px;'
        'text-transform:uppercase;margin:24px 0 18px 0;border-bottom:1px solid rgba(180,200,255,0.3);'
        'padding-bottom:8px">TRAVEL INSURANCE — YOUR OPTIONS</h2>'
        + deadline_html
        + '<table cellpadding="0" cellspacing="0" border="0" width="100%" '
        'style="border-collapse:collapse;margin:0 0 24px 0">'
        + "".join(rows)
        + "</table>"
    )


# ---------------------------------------------------------------------------
# Acceptance sync — dossier write-back
# ---------------------------------------------------------------------------

def record_client_acceptance(
    dossier_path: str,
    booking_id: str,
    carrier: str,
    policy_number: str,
    coverage_start: str,
    coverage_end: str,
    premium: Optional[float] = None,
) -> dict:
    path = Path(dossier_path)
    fm = _read_frontmatter(path)
    prefix, _, _, _, _, _ = _extract_booking_fields(fm, booking_id)
    # "booking" (flat schema) has no per-booking prefix; use "insurance_" directly
    field_prefix = "" if prefix == "booking" else f"{prefix}_"

    fm[f"{field_prefix}insurance_status"] = "accepted"
    fm[f"{field_prefix}insurance_carrier"] = carrier
    fm[f"{field_prefix}insurance_policy_number"] = policy_number
    fm[f"{field_prefix}insurance_coverage_start"] = coverage_start
    fm[f"{field_prefix}insurance_coverage_end"] = coverage_end
    if premium is not None:
        fm[f"{field_prefix}insurance_premium"] = premium
    fm[f"{field_prefix}insurance_accepted_date"] = date.today().isoformat()

    _write_frontmatter(path, fm)

    client_name = fm.get("client", path.stem)
    store = _load_store()
    key = f"{client_name}::{prefix}"
    if key in store:
        store[key]["acceptance"] = {
            "carrier": carrier,
            "policy_number": policy_number,
            "coverage_start": coverage_start,
            "coverage_end": coverage_end,
            "premium": premium,
            "accepted_date": date.today().isoformat(),
        }
        _save_store(store)

    return {"ok": True, "booking_id": prefix, "carrier": carrier, "policy_number": policy_number}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _main():
    ap = argparse.ArgumentParser(description="Auto-quote travel insurance for a booking")
    ap.add_argument("--dossier", required=True)
    ap.add_argument("--booking", required=True)
    ap.add_argument("--trip-cost", type=float)
    ap.add_argument("--ages", type=int, nargs="+")
    ap.add_argument("--destinations", nargs="+")
    args = ap.parse_args()

    result = auto_quote_for_booking(
        dossier_path=args.dossier,
        booking_id=args.booking,
        trip_cost=args.trip_cost,
        traveler_ages=args.ages,
        destinations=args.destinations,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    _main()
