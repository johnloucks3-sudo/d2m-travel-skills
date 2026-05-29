#!/usr/bin/env python3
"""
TESS FPD Dossier Sync — M-041 deliverable.

Sweeps TESS for FinalPaymentDate on all active bookings, then updates the
`fpd:` field in each matching dossier's YAML frontmatter.

Matching strategy (in priority order):
  1. `booking:` frontmatter field matches TESS BookingNumber (exact)
  2. Booking number appears anywhere in dossier text
  3. Client/trip name fuzzy match (fallback — logs LOW confidence)

Rules (SO-PIPELINE-INTEGRITY-20260528):
  - TESS is the authoritative source for FPD (Rule 4)
  - Dollar amounts must trace to portal/TESS — never to a memo (Rule 4)
  - All changes are logged with CONFIRMED tag

Usage:
    python3 scripts/tess_fpd_dossier_sync.py              # sync all dossiers
    python3 scripts/tess_fpd_dossier_sync.py --dry-run    # preview changes
    python3 scripts/tess_fpd_dossier_sync.py --status     # show current FPD status

Output: logs/tess_fpd_sync.log + console summary
"""
import json
import logging
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

THUNDERBIRD = Path("/home/john/Thunderbird")
DOSSIERS_DIR = THUNDERBIRD / "dossiers"
LOG_FILE = THUNDERBIRD / "logs" / "tess_fpd_sync.log"

# Add paths for imports
sys.path.insert(0, str(THUNDERBIRD / "core" / "booking"))
sys.path.insert(0, str(THUNDERBIRD))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("tess_fpd_sync")

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
FPD_LINE_RE = re.compile(r"^(fpd:\s*)(\S+)\s*$", re.MULTILINE)


def _parse_frontmatter(text: str) -> dict:
    """Extract key-value pairs from YAML frontmatter."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    fm: dict = {}
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip().strip('"')
    return fm


def _update_fpd_in_frontmatter(text: str, new_fpd: str) -> str:
    """Replace fpd: value in YAML frontmatter. Adds fpd: line if not present."""
    if FPD_LINE_RE.search(text):
        return FPD_LINE_RE.sub(lambda m: f"{m.group(1)}{new_fpd}", text, count=1)
    # Insert fpd: after first --- block opener if no existing fpd: line
    m = FRONTMATTER_RE.match(text)
    if m:
        end = m.end()
        insert_at = text.rfind("\n---", 0, end)
        if insert_at != -1:
            return text[:insert_at] + f"\nfpd: {new_fpd}" + text[insert_at:]
    return text


def load_dossiers() -> list[dict]:
    """Load all dossiers with `fpd:` in frontmatter."""
    dossiers = []
    for f in sorted(DOSSIERS_DIR.glob("*.md")):
        if f.name.startswith("DOSSIER_") or f.name == "CLAUDE.md":
            continue  # research dossiers, not client dossiers
        try:
            text = f.read_text(encoding="utf-8")
        except Exception:
            continue
        fm = _parse_frontmatter(text)
        if not fm:
            continue
        dossiers.append({
            "path": f,
            "frontmatter": fm,
            "text": text,
            "booking_number": fm.get("booking", "").strip('"'),
            "client": fm.get("client", "").strip('"'),
            "fpd_current": fm.get("fpd", ""),
        })
    return dossiers


def run_fpd_sweep_from_tess() -> list[dict]:
    """Run live FPD sweep from TESS. Returns list of booking alert dicts."""
    try:
        from core.mcp.tools.tess_reporting_scraper import run_fpd_sweep
        report = run_fpd_sweep(days_ahead=365, include_no_fpd=True)
        if "error" in report:
            logger.error("TESS sweep error: %s", report.get("error"))
            return []
        alerts = report.get("alerts", [])
        # Also include no_fpd bookings for logging
        no_fpd = report.get("no_fpd_bookings", [])
        logger.info(
            "TESS sweep: %d bookings, %d with FPD, %d without FPD",
            report.get("total_bookings_checked", 0),
            len(alerts),
            len(no_fpd),
        )
        return alerts
    except Exception as e:
        logger.error("TESS sweep failed: %s", e)
        return []


def match_booking_to_dossier(booking: dict, dossiers: list[dict]) -> dict | None:
    """Find the best dossier match for a TESS booking.

    Priority:
      1. Exact `booking:` frontmatter match to BookingNumber
      2. Booking number appears in dossier text
      3. Skip (no fuzzy match — avoids false positives)
    """
    booking_num = str(booking.get("booking_number") or "").strip()
    if not booking_num:
        return None

    for d in dossiers:
        if d["booking_number"] and d["booking_number"] == booking_num:
            return d

    if booking_num:
        for d in dossiers:
            if booking_num in d["text"]:
                return d

    return None


def sync_fpds(dry_run: bool = False) -> list[dict]:
    """Main sync routine.

    Returns list of change records:
        {dossier, client, booking_number, old_fpd, new_fpd, changed, confidence}
    """
    dossiers = load_dossiers()
    if not dossiers:
        logger.warning("No client dossiers found in %s", DOSSIERS_DIR)
        return []

    bookings = run_fpd_sweep_from_tess()
    if not bookings:
        logger.warning("No TESS bookings returned — is TESS authenticated?")
        logger.warning("Run: python3 core/booking/thunderbird_tess.py --inject-token '<localStorage blob>'")
        return []

    today = str(date.today())
    changes: list[dict] = []

    for booking in bookings:
        new_fpd = booking.get("fpd")
        if not new_fpd:
            continue

        dossier = match_booking_to_dossier(booking, dossiers)
        if not dossier:
            logger.debug(
                "No dossier match for booking %s (%s)",
                booking.get("booking_number"),
                booking.get("trip_description", "")[:40],
            )
            continue

        old_fpd = dossier["fpd_current"]
        client = dossier["client"]
        dossier_path = dossier["path"]

        if str(old_fpd) == str(new_fpd):
            logger.info("OK   %s — FPD %s matches TESS (no change)", client, new_fpd)
            continue

        record = {
            "dossier": str(dossier_path.name),
            "client": client,
            "booking_number": booking.get("booking_number"),
            "trip_description": booking.get("trip_description", "")[:60],
            "old_fpd": old_fpd,
            "new_fpd": new_fpd,
            "alert_level": booking.get("alert_level"),
            "days_until_fpd": booking.get("days_until_fpd"),
            "sync_date": today,
            "dry_run": dry_run,
            "changed": False,
        }

        if not dry_run:
            try:
                new_text = _update_fpd_in_frontmatter(dossier["text"], str(new_fpd))
                dossier["path"].write_text(new_text, encoding="utf-8")
                record["changed"] = True
                logger.info(
                    "UPDATED %s — fpd: %s → %s (CONFIRMED:TESS) [%s, %d days]",
                    client, old_fpd, new_fpd,
                    booking.get("alert_level"), booking.get("days_until_fpd", 0),
                )
            except Exception as e:
                logger.error("Failed to update %s: %s", dossier_path, e)
        else:
            logger.info(
                "DRY-RUN %s — fpd: %s → %s [%s, %d days]",
                client, old_fpd, new_fpd,
                booking.get("alert_level"), booking.get("days_until_fpd", 0),
            )
            record["changed"] = False

        changes.append(record)

    return changes


def show_status() -> None:
    """Print current FPD status for all dossiers with fpd: field."""
    dossiers = load_dossiers()
    today = date.today()
    print(f"\n{'Dossier':<42} {'FPD':<12} {'Days':<6} {'Level'}")
    print("-" * 75)
    for d in dossiers:
        fpd_str = d["fpd_current"]
        if not fpd_str or fpd_str in ("null", "None", "~"):
            print(f"  {d['path'].name:<40} {'NO FPD':12} {'—':6} {'—'}")
            continue
        try:
            fpd = date.fromisoformat(str(fpd_str)[:10])
            days = (fpd - today).days
            if days < 0:
                level = "PAST"
            elif days <= 30:
                level = "RED"
            elif days <= 45:
                level = "YELLOW"
            elif days <= 60:
                level = "ORANGE"
            else:
                level = "GREEN"
            print(f"  {d['path'].name:<40} {fpd_str:<12} {days:<6} {level}")
        except (ValueError, TypeError):
            print(f"  {d['path'].name:<40} {fpd_str:<12} {'?':6} {'?'}")
    print()


def _cli() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="TESS FPD → Dossier Sync (M-041)")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    parser.add_argument("--status", action="store_true", help="Show current dossier FPD status")
    args = parser.parse_args()

    if args.status:
        show_status()
        return

    changes = sync_fpds(dry_run=args.dry_run)

    if changes:
        print(f"\n{'[DRY RUN] ' if args.dry_run else ''}FPD sync complete:")
        for c in changes:
            tag = "WOULD UPDATE" if args.dry_run else "UPDATED"
            print(f"  {tag}: {c['client']} — {c['old_fpd']} → {c['new_fpd']} ({c['alert_level']}, {c['days_until_fpd']} days)")
        print(f"\n{len(changes)} dossier(s) {'would be ' if args.dry_run else ''}updated.")
    else:
        if not args.dry_run:
            print("No FPD changes needed (all dossiers match TESS, or TESS offline).")


if __name__ == "__main__":
    _cli()
