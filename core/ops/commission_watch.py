#!/usr/bin/env python3
"""
d2m-commission-watch — Daily commission reconciliation.

Reads booking dossiers, cross-references expected commission dates,
alerts on commissions missing > 45 days post-travel.

Schedule: Daily 06:30 MDT via systemd timer
Output:   OpsCenter/logs/commission_watch.log
          hale_decisions.md if overdue commissions found
          Gmail draft to d2mconcierge for Commander review
"""

import json
import logging
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
DOSSIERS_DIR = ROOT / "dossiers"
BLACKBOARD_DIR = ROOT / "Blackboard/clients"
LOG_PATH = ROOT / "OpsCenter/logs/commission_watch.log"
AUDIT_LOG = ROOT / "OpsCenter/logs/commission_watch.jsonl"
HALE_DECISIONS = ROOT / "hale_decisions.md"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [COMMISSION-WATCH] %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(LOG_PATH)],
)
log = logging.getLogger(__name__)

OVERDUE_DAYS = 45  # flag if commission not received > this many days post-travel


def parse_date(s: str) -> date | None:
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except (ValueError, AttributeError):
            continue
    return None


def scan_dossiers() -> list[dict]:
    """Read all DOSSIER_*.md files and extract return date + booking ref."""
    records = []
    today = date.today()

    for fp in DOSSIERS_DIR.glob("DOSSIER_*.md"):
        text = fp.read_text(errors="ignore")

        # Extract key fields via regex
        booking_ref = None
        return_date = None
        client_name = fp.stem.replace("DOSSIER_", "")
        commission_received = False

        m = re.search(r"(?:Booking\s*(?:Ref|Reference|#|Number)[:\s]+)([A-Z0-9\-]+)", text, re.IGNORECASE)
        if m:
            booking_ref = m.group(1).strip()

        # Look for return/disembark date
        for pattern in [
            r"(?:Return|Disembark|End\s+Date|Return\s+Date)[:\s]+(\d{4}-\d{2}-\d{2})",
            r"(?:Return|Disembark|End\s+Date)[:\s]+(\w+ \d+, \d{4})",
        ]:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                return_date = parse_date(m.group(1))
                break

        # Check if commission already noted
        if re.search(r"commission[_\s]?received|commission[_\s]?paid|commission[_\s]?posted", text, re.IGNORECASE):
            commission_received = True

        if return_date and not commission_received:
            days_since_return = (today - return_date).days
            if days_since_return > OVERDUE_DAYS:
                records.append(
                    {
                        "client": client_name,
                        "file": str(fp),
                        "booking_ref": booking_ref,
                        "return_date": str(return_date),
                        "days_overdue": days_since_return - OVERDUE_DAYS,
                        "days_since_return": days_since_return,
                    }
                )
                log.warning(
                    f"OVERDUE COMMISSION: {client_name} — returned {return_date} "
                    f"({days_since_return}d ago), commission unconfirmed"
                )

    return records


def scan_blackboard() -> list[dict]:
    """Also check Blackboard YAML for commission fields."""
    import yaml

    records = []
    today = date.today()

    for fp in BLACKBOARD_DIR.glob("*.yaml"):
        try:
            data = yaml.safe_load(fp.read_text())
        except Exception:
            continue
        if not data:
            continue

        bookings = data.get("bookings", [])
        if isinstance(bookings, dict):
            bookings = [bookings]

        for booking in bookings:
            if not isinstance(booking, dict):
                continue
            return_date_str = booking.get("return_date") or booking.get("end_date")
            commission_received = booking.get("commission_received") or booking.get("commission_posted")
            if not return_date_str or commission_received:
                continue
            return_date = parse_date(str(return_date_str))
            if not return_date:
                continue
            days_since = (today - return_date).days
            if days_since > OVERDUE_DAYS:
                records.append(
                    {
                        "client": data.get("client_id", fp.stem),
                        "file": str(fp),
                        "booking_ref": booking.get("booking_ref") or booking.get("booking_number"),
                        "return_date": str(return_date),
                        "days_overdue": days_since - OVERDUE_DAYS,
                        "days_since_return": days_since,
                    }
                )
    return records


def write_hale_decision(overdue: list[dict], run_dt: datetime) -> None:
    if not overdue:
        return
    lines = [
        f"\n### {run_dt.strftime('%Y-%m-%d %H:%M:%S')} — Autonomous Decision (Tier T0)\n",
        f"**Decision:** Commission watch found {len(overdue)} overdue commission(s)\n",
        "**Overdue commissions:**\n",
    ]
    for item in overdue:
        lines.append(
            f"  - {item['client']} | Ref: {item.get('booking_ref','?')} | "
            f"Returned: {item['return_date']} | {item['days_overdue']}d overdue\n"
        )
    lines.append("**Domain:** Finance / Commission tracking\n**Type:** proactive alert\n**Outcome:** surfaced to Commander\n")
    with open(HALE_DECISIONS, "a") as f:
        f.writelines(lines)


def draft_commission_alert(overdue: list[dict]) -> None:
    """Create Gmail draft alerting Commander to overdue commissions."""
    try:
        sys.path.insert(0, str(ROOT))
        from core.email.thunderbird_gmail import gmail_create_draft_sync

        body_lines = [
            "<p style='color:#0000ff;font-family:Georgia;'>Commander —</p>",
            "<p style='color:#0000ff;font-family:Georgia;'>Commission watch has flagged the following bookings as overdue (>{} days post-travel, no commission confirmed):</p>".format(OVERDUE_DAYS),
            "<ul style='color:#0000ff;font-family:Georgia;'>",
        ]
        for item in overdue:
            body_lines.append(
                f"<li><b>{item['client']}</b> | Ref: {item.get('booking_ref','?')} | "
                f"Returned: {item['return_date']} | <b>{item['days_overdue']} days overdue</b></li>"
            )
        body_lines.extend([
            "</ul>",
            "<p style='color:#0000ff;font-family:Georgia;'>Action required: follow up with supplier for commission payment or confirm it was received and update the dossier.</p>",
            "<p style='color:#0000ff;font-family:Georgia;'>— Hale</p>",
        ])

        gmail_create_draft_sync(
            to="d2mconcierge@gmail.com",
            subject=f"[COMMISSION WATCH] {len(overdue)} Overdue Commission(s) — Action Required",
            body="\n".join(body_lines),
            persona_id="CONCIERGE",
        )
        log.info(f"Gmail draft created for {len(overdue)} overdue commissions")
    except Exception as e:
        log.warning(f"Could not create Gmail draft: {e}")


def main() -> int:
    run_dt = datetime.now()
    log.info(f"Commission watch starting — {run_dt.date()}")

    overdue = scan_dossiers()
    overdue += scan_blackboard()

    # Deduplicate by booking_ref
    seen = set()
    deduped = []
    for item in overdue:
        key = item.get("booking_ref") or item["client"]
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    overdue = deduped

    # Write audit log
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": run_dt.isoformat(),
        "overdue_count": len(overdue),
        "overdue": overdue,
    }
    with open(AUDIT_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")

    if overdue:
        log.warning(f"ALERT: {len(overdue)} overdue commission(s) found")
        write_hale_decision(overdue, run_dt)
        draft_commission_alert(overdue)
    else:
        log.info("All commissions current — no overdue items")

    return 0


if __name__ == "__main__":
    sys.exit(main())
