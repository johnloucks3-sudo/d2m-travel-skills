"""
TESS Reporting Scraper — standalone FPD sweep + dossier auto-update utility.

Calls the TESS API directly (no MCP required) for use by:
  - M-041 dossier auto-updater (updates local dossier FPD fields from TESS live data)
  - Cron-based monitoring (nightly FPD sweep, alerts to wing_comms)
  - Harlan A9 commission checks

The MCP version of the FPD sweep is registered as `tess_fpd_sweep` in
register_tess_tools() inside thunderbird_tess.py. This module is the
standalone/scripting counterpart for non-MCP callers.

Usage:
    python3 tess_reporting_scraper.py --fpd-sweep          # print FPD report
    python3 tess_reporting_scraper.py --fpd-sweep --days 90
    python3 tess_reporting_scraper.py --update-dossiers    # update local dossier FPDs

Or from Python:
    from core.mcp.tools.tess_reporting_scraper import run_fpd_sweep, update_dossier_fpds
    report = run_fpd_sweep(days_ahead=60)
    updated = update_dossier_fpds(report)
"""
import json
import logging
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

THUNDERBIRD = Path("/home/john/Thunderbird")
DOSSIERS_DIR = THUNDERBIRD / "dossiers"

# FPD alert thresholds (days until FPD)
THRESHOLD_RED = 30
THRESHOLD_YELLOW = 45
THRESHOLD_ORANGE = 60


def _get_tess_client():
    """Import and return a configured TESS client."""
    booking_dir = THUNDERBIRD / "core" / "booking"
    if str(booking_dir) not in sys.path:
        sys.path.insert(0, str(booking_dir))
    from thunderbird_tess import TESSClient  # type: ignore
    return TESSClient()


def _parse_fpd(fpd_raw: Any) -> date | None:
    """Parse a TESS FinalPaymentDate value to a Python date."""
    if not fpd_raw:
        return None
    try:
        s = str(fpd_raw)
        if "T" in s:
            return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
        return date.fromisoformat(s[:10])
    except (ValueError, TypeError):
        return None


def run_fpd_sweep(days_ahead: int = 60, include_no_fpd: bool = False) -> dict:
    """Run an FPD sweep across all TESS bookings.

    Returns:
        {
            sweep_date: str,
            days_ahead_window: int,
            total_bookings_checked: int,
            cancelled_skipped: int,
            alerts_found: int,
            by_level: {PAST, RED, YELLOW, ORANGE, GREEN},
            alerts: [{alert_level, days_until_fpd, fpd, booking_id, ...}],
            no_fpd_bookings: [...],   # if include_no_fpd=True
        }
    """
    client = _get_tess_client()
    raw = client.search_bookings({})

    items = raw.get("Items", raw) if isinstance(raw, dict) else raw
    if not isinstance(items, list):
        return {"error": "Unexpected TESS response", "raw_type": type(raw).__name__}

    today = date.today()
    alerts: list[dict] = []
    no_fpd_bookings: list[dict] = []
    skipped_cancelled = 0

    for b in items:
        bs = b.get("BookingStatus") or {}
        status = (bs.get("StatusName") if isinstance(bs, dict) else str(bs)).lower()
        if status in ("cancelled", "canceled", "void"):
            skipped_cancelled += 1
            continue

        fpd = _parse_fpd(b.get("FinalPaymentDate"))
        if fpd is None:
            if include_no_fpd:
                no_fpd_bookings.append({
                    "booking_id": b.get("BookingID"),
                    "booking_number": b.get("BookingNumber") or b.get("Number"),
                    "trip_description": b.get("TripDescription"),
                    "tour_operator": b.get("TourOperator"),
                    "status": bs.get("StatusName") if isinstance(bs, dict) else str(bs),
                    "start_date": b.get("StartDate"),
                })
            continue

        days_until = (fpd - today).days

        if days_until < 0:
            level = "PAST"
        elif days_until <= THRESHOLD_RED:
            level = "RED"
        elif days_until <= THRESHOLD_YELLOW:
            level = "YELLOW"
        elif days_until <= THRESHOLD_ORANGE:
            level = "ORANGE"
        else:
            level = "GREEN"

        if level == "GREEN" and days_until > days_ahead:
            continue

        commission = b.get("Commission") or {}
        comm_amount = None
        if isinstance(commission, dict):
            comm_amount = commission.get("AgencyCommission") or commission.get("CommissionAmount")

        alerts.append({
            "alert_level": level,
            "days_until_fpd": days_until,
            "fpd": str(fpd),
            "booking_id": b.get("BookingID"),
            "booking_number": b.get("BookingNumber") or b.get("Number"),
            "trip_description": b.get("TripDescription"),
            "tour_operator": b.get("TourOperator"),
            "booking_status": bs.get("StatusName") if isinstance(bs, dict) else str(bs),
            "start_date": b.get("StartDate"),
            "end_date": b.get("EndDate"),
            "package_price": b.get("PackagePrice"),
            "commission_expected": comm_amount,
        })

    alerts.sort(key=lambda x: x["days_until_fpd"])

    report = {
        "sweep_date": str(today),
        "days_ahead_window": days_ahead,
        "total_bookings_checked": len(items),
        "cancelled_skipped": skipped_cancelled,
        "alerts_found": len(alerts),
        "by_level": {
            "PAST": sum(1 for a in alerts if a["alert_level"] == "PAST"),
            "RED": sum(1 for a in alerts if a["alert_level"] == "RED"),
            "YELLOW": sum(1 for a in alerts if a["alert_level"] == "YELLOW"),
            "ORANGE": sum(1 for a in alerts if a["alert_level"] == "ORANGE"),
            "GREEN": sum(1 for a in alerts if a["alert_level"] == "GREEN"),
        },
        "alerts": alerts,
    }
    if include_no_fpd:
        report["no_fpd_bookings"] = no_fpd_bookings

    return report


def update_dossier_fpds(report: dict | None = None, dry_run: bool = False) -> list[dict]:
    """Update dossier final_payment_date fields from TESS FPD sweep data.

    For each booking alert, searches dossier files for a matching client/booking
    and updates the `final_payment_date` field with the TESS-authoritative value.

    Args:
        report: Pre-computed FPD sweep dict (from run_fpd_sweep). If None, runs sweep.
        dry_run: If True, log what would change but don't write files.

    Returns:
        List of {dossier_file, client_name, old_fpd, new_fpd, changed} dicts.
    """
    if report is None:
        report = run_fpd_sweep(days_ahead=365, include_no_fpd=False)

    alerts = report.get("alerts", [])
    changes: list[dict] = []

    if not DOSSIERS_DIR.exists():
        logger.warning("update_dossier_fpds: dossiers dir not found at %s", DOSSIERS_DIR)
        return changes

    dossier_files = list(DOSSIERS_DIR.glob("*.json")) + list(DOSSIERS_DIR.glob("*.md"))

    for alert in alerts:
        trip_desc = (alert.get("trip_description") or "").lower()
        tour_op = (alert.get("tour_operator") or "").lower()
        new_fpd = alert.get("fpd")

        for df in dossier_files:
            try:
                text = df.read_text(encoding="utf-8")
            except Exception:
                continue

            # Name-match heuristic: check if tour operator or trip keywords appear in dossier
            name_stem = df.stem.lower()
            if not any(
                kw in text.lower()
                for kw in [tour_op[:6], trip_desc[:10]] if kw
            ):
                # Also try matching booking_id
                booking_id = str(alert.get("booking_id") or "")
                if booking_id and booking_id not in text:
                    continue

            if df.suffix == ".json":
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    continue

                old_fpd = (
                    data.get("final_payment_date")
                    or data.get("FinalPaymentDate")
                    or data.get("fpd")
                )

                if str(old_fpd) == str(new_fpd):
                    continue

                changes.append({
                    "dossier_file": str(df),
                    "client_name": data.get("client_name") or df.stem,
                    "old_fpd": str(old_fpd),
                    "new_fpd": new_fpd,
                    "booking_id": alert.get("booking_id"),
                    "alert_level": alert.get("alert_level"),
                    "changed": not dry_run,
                })

                if not dry_run:
                    for key in ("final_payment_date", "FinalPaymentDate", "fpd"):
                        if key in data:
                            data[key] = new_fpd
                            break
                    else:
                        data["final_payment_date"] = new_fpd

                    df.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
                    logger.info("update_dossier_fpds: %s → FPD %s → %s", df.stem, old_fpd, new_fpd)

            elif df.suffix == ".md":
                import re
                # Match lines like: final_payment_date: 2026-10-15  or  FPD: 2026-10-15
                pattern = re.compile(
                    r"(final_payment_date|FinalPaymentDate|fpd):\s*(\S+)", re.IGNORECASE
                )
                match = pattern.search(text)
                old_fpd = match.group(2) if match else None

                if str(old_fpd) == str(new_fpd):
                    continue

                changes.append({
                    "dossier_file": str(df),
                    "client_name": df.stem,
                    "old_fpd": str(old_fpd),
                    "new_fpd": new_fpd,
                    "booking_id": alert.get("booking_id"),
                    "alert_level": alert.get("alert_level"),
                    "changed": not dry_run,
                })

                if not dry_run and match:
                    key = match.group(1)
                    new_text = pattern.sub(f"{key}: {new_fpd}", text, count=1)
                    df.write_text(new_text, encoding="utf-8")
                    logger.info("update_dossier_fpds: %s (md) → FPD %s → %s", df.stem, old_fpd, new_fpd)

    return changes


def _cli() -> None:
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="TESS Reporting Scraper")
    parser.add_argument("--fpd-sweep", action="store_true", help="Run FPD sweep across all bookings")
    parser.add_argument("--days", type=int, default=60, help="Look-ahead days (default: 60)")
    parser.add_argument("--include-no-fpd", action="store_true", help="Include bookings with no FPD set")
    parser.add_argument("--update-dossiers", action="store_true", help="Update local dossier FPD fields from TESS")
    parser.add_argument("--dry-run", action="store_true", help="Show changes but don't write files")
    args = parser.parse_args()

    if args.fpd_sweep or args.update_dossiers:
        report = run_fpd_sweep(days_ahead=args.days, include_no_fpd=args.include_no_fpd)

        if args.fpd_sweep:
            print(json.dumps(report, indent=2, default=str))

        if args.update_dossiers:
            print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Updating dossier FPDs...")
            changes = update_dossier_fpds(report, dry_run=args.dry_run)
            if changes:
                for c in changes:
                    tag = "[DRY RUN] " if args.dry_run else ""
                    print(f"  {tag}{c['client_name']}: {c['old_fpd']} → {c['new_fpd']} (booking {c['booking_id']}, {c['alert_level']})")
                print(f"\n{len(changes)} dossier(s) {'would be ' if args.dry_run else ''}updated.")
            else:
                print("No dossier FPD changes needed.")
    else:
        parser.print_help()


if __name__ == "__main__":
    _cli()
