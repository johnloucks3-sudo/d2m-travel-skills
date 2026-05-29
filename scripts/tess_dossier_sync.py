#!/usr/bin/env python3
"""
TESS Dossier Sync — Pull TESS Booking Data → Update Dossier Frontmatter
=========================================================================
Dreams2Memories Travel, LLC | scripts/tess_dossier_sync.py

Pulls live booking data from TESS and syncs key fields to dossier YAML:
- payment_status (paid_in_full / pending / partial)
- fpd / fpd_amount (from TESS booking payment schedule)
- departure / return dates (verify against dossier)

Matches TESS bookings to dossiers via the `booking` field in YAML frontmatter.

Usage:
    python3 scripts/tess_dossier_sync.py              # Sync all active dossiers
    python3 scripts/tess_dossier_sync.py --dry-run    # Preview changes
    python3 scripts/tess_dossier_sync.py --client Nichols
    python3 scripts/tess_dossier_sync.py --status     # Show last sync results
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import date, datetime
from pathlib import Path

import yaml

THUNDERBIRD = Path.home() / "Thunderbird"
sys.path.insert(0, str(THUNDERBIRD))
sys.path.insert(0, str(THUNDERBIRD / "core" / "booking"))

SYNC_LOG = THUNDERBIRD / "storage" / "tess_dossier_sync.jsonl"
SKIP_FILES = {"CLAUDE.md", "DOSSIER_Regent_Tips_Guide.md", "DANI_TESTER_BRIEFINGS.md"}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s TESS-SYNC %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(str(THUNDERBIRD / "logs" / "tess_dossier_sync.log"), mode="a"),
    ],
)
logger = logging.getLogger("tess_sync")


def _read_frontmatter(path: Path) -> tuple[dict, str, str, str]:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^(---\s*\n)(.*?)(\n---)", text, re.DOTALL)
    if not m:
        return {}, "---\n", "", text
    fm = yaml.safe_load(m.group(2)) or {}
    return fm, m.group(1), m.group(2), text[m.end():]


def _write_frontmatter(path: Path, fm: dict, pre: str, after: str) -> None:
    fm_text = yaml.dump(fm, default_flow_style=False, allow_unicode=True, sort_keys=False)
    path.write_text(pre + fm_text.rstrip() + "\n---" + after, encoding="utf-8")


def _parse_tess_date(val) -> str | None:
    if not val:
        return None
    # TESS returns ISO 8601 datetime strings
    try:
        dt = datetime.fromisoformat(str(val).replace("Z", "+00:00"))
        return dt.date().isoformat()
    except Exception:
        return None


def _infer_payment_status(booking: dict) -> str:
    """Map TESS booking status to dossier payment_status string."""
    # Commission status fields vary; try several known patterns
    status = str(booking.get("BookingStatus", "")).lower()
    commission = booking.get("Commission") or {}
    received = float(commission.get("AmountReceived", 0) or 0)
    due = float(commission.get("AmountDue", 0) or 0)

    if "cancel" in status:
        return "cancelled"
    if received > 0 and due == 0:
        return "paid_in_full"
    if received > 0 and due > 0:
        return "partial"
    if due > 0:
        return "pending"
    # Fall back to booking status text
    if "confirm" in status or "active" in status:
        return "confirmed"
    return "unknown"


def load_dossier_booking_map(client_filter: str | None = None) -> dict[str, Path]:
    """Build {booking_number: dossier_path} map from dossier frontmatter."""
    booking_map: dict[str, Path] = {}
    for path in sorted(THUNDERBIRD.glob("dossiers/*.md")):
        if path.name in SKIP_FILES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
            m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
            if not m:
                continue
            fm = yaml.safe_load(m.group(1)) or {}
            if str(fm.get("status", "")).lower() not in ("active", "prospect"):
                continue
            if client_filter and client_filter.lower() not in str(fm.get("client", "")).lower():
                continue
            booking_num = str(fm.get("booking", "")).strip().strip('"')
            if booking_num:
                booking_map[booking_num] = path
        except Exception as exc:
            logger.warning(f"Dossier read error [{path.name}]: {exc}")
    return booking_map


def sync_bookings(
    dry_run: bool = False,
    client_filter: str | None = None,
) -> list[dict]:
    from thunderbird_tess import TESSClient

    client = TESSClient()
    booking_map = load_dossier_booking_map(client_filter)

    if not booking_map:
        logger.info("No dossiers with booking numbers found.")
        return []

    logger.info(f"Syncing {len(booking_map)} dossiers: {', '.join(booking_map.keys())}")

    # Pull TESS bookings (up to 100)
    try:
        resp = client.list_bookings(page_size=100)
    except Exception as exc:
        logger.error(f"TESS API call failed: {exc}")
        return [{"status": "error", "error": str(exc)}]

    if "error" in resp:
        logger.error(f"TESS error: {resp['error']}")
        return [{"status": "error", "error": resp["error"]}]

    tess_bookings = resp.get("Items", [])
    logger.info(f"TESS returned {len(tess_bookings)} bookings")

    # Build {booking_number: booking_data} map from TESS
    tess_map: dict[str, dict] = {}
    for bk in tess_bookings:
        bk_num = str(bk.get("BookingNumber", "")).strip()
        if bk_num:
            tess_map[bk_num] = bk

    results = []

    for booking_num, dossier_path in booking_map.items():
        tess_bk = tess_map.get(booking_num)
        if not tess_bk:
            logger.info(f"Booking {booking_num} not found in TESS (may be on different page)")
            results.append({
                "booking": booking_num,
                "dossier": dossier_path.name,
                "status": "not_found_in_tess",
            })
            continue

        fm, pre, _, after = _read_frontmatter(dossier_path)
        changes: dict[str, tuple] = {}  # field: (old, new)

        # Payment status — only fill if currently absent; never downgrade
        PAID_STATUSES = {"paid_in_full", "paid", "complete"}
        new_status = _infer_payment_status(tess_bk)
        old_status = fm.get("payment_status", "")
        if new_status and new_status != "unknown" and not old_status and old_status not in PAID_STATUSES:
            changes["payment_status"] = (old_status, new_status)

        # Departure — only fill if missing in dossier
        tess_dep = _parse_tess_date(tess_bk.get("StartDate"))
        if tess_dep and not fm.get("departure"):
            changes["departure"] = ("", tess_dep)

        # Return — only fill if missing in dossier
        tess_ret = _parse_tess_date(tess_bk.get("EndDate"))
        if tess_ret and not fm.get("return"):
            changes["return"] = ("", tess_ret)

        entry = {
            "ts": datetime.now().isoformat(),
            "booking": booking_num,
            "dossier": dossier_path.name,
            "changes": {k: {"old": v[0], "new": v[1]} for k, v in changes.items()},
            "status": "updated" if changes else "no_change",
        }

        if changes:
            if dry_run:
                entry["status"] = "dry_run"
                print(f"  [DRY-RUN] {dossier_path.stem} (booking {booking_num})")
                for field, (old, new) in changes.items():
                    print(f"    {field}: '{old}' → '{new}'")
            else:
                for field, (_, new) in changes.items():
                    fm[field] = new
                _write_frontmatter(dossier_path, fm, pre, after)
                print(f"  ✅ {dossier_path.stem}: {list(changes.keys())} updated")
                logger.info(f"Updated {dossier_path.stem}: {changes}")
        else:
            logger.info(f"No changes for {dossier_path.stem} (booking {booking_num})")

        SYNC_LOG.parent.mkdir(parents=True, exist_ok=True)
        with SYNC_LOG.open("a") as f:
            f.write(json.dumps(entry) + "\n")
        results.append(entry)

    return results


def print_status() -> None:
    if not SYNC_LOG.exists():
        print("No sync history yet.")
        return
    lines = [l for l in SYNC_LOG.read_text().splitlines() if l.strip()]
    if not lines:
        print("Sync log empty.")
        return
    last = json.loads(lines[-1])
    print(f"\nLast sync: {last.get('ts', '?')}")
    print(f"{'BOOKING':<10}  {'DOSSIER':<40}  STATUS")
    print("-" * 70)
    for line in lines[-20:]:
        try:
            e = json.loads(line)
            print(f"{e.get('booking','?'):<10}  {e.get('dossier','?'):<40}  {e.get('status','?')}")
        except Exception:
            pass


def main() -> None:
    p = argparse.ArgumentParser(description="TESS → Dossier sync")
    p.add_argument("--dry-run", action="store_true", help="Preview only")
    p.add_argument("--client", help="Filter by client name")
    p.add_argument("--status", action="store_true", help="Show sync history")
    args = p.parse_args()

    if args.status:
        print_status()
        return

    print(f"\nTESS Dossier Sync — {date.today().isoformat()}")
    if args.dry_run:
        print("MODE: DRY-RUN\n")

    results = sync_bookings(dry_run=args.dry_run, client_filter=args.client)
    updated = [r for r in results if r.get("status") == "updated"]
    no_change = [r for r in results if r.get("status") == "no_change"]
    not_found = [r for r in results if r.get("status") == "not_found_in_tess"]
    errors = [r for r in results if r.get("status") == "error"]

    print(f"\nSync complete: {len(updated)} updated, {len(no_change)} no change, "
          f"{len(not_found)} not in TESS, {len(errors)} errors")


if __name__ == "__main__":
    main()
