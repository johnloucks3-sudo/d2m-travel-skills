#!/usr/bin/env python3
"""
d2m-fdp-reconcile — Final Payment Date vs actual payment reconciliation.

Reads Blackboard YAML, finds FPDs that have passed, checks if
payment is recorded. Alerts Commander on missed/upcoming FPDs.

Schedule: Daily 02:00 MDT via systemd timer
Output:   OpsCenter/logs/fdp_reconcile.log
          hale_decisions.md on overdue FPDs
          Gmail draft on critical items (FPD today or passed)
"""

import json
import logging
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
BLACKBOARD_DIR = ROOT / "Blackboard/clients"
LOG_PATH = ROOT / "OpsCenter/logs/fdp_reconcile.log"
AUDIT_LOG = ROOT / "OpsCenter/logs/fdp_reconcile.jsonl"
HALE_DECISIONS = ROOT / "hale_decisions.md"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [FDP-RECONCILE] %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(LOG_PATH)],
)
log = logging.getLogger(__name__)

WARN_DAYS_AHEAD = 14  # Warn if FPD is within this many days
OVERDUE_FLAG_DAYS = 1  # Flag as overdue after this many days past FPD


def parse_date(s: str) -> date | None:
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(str(s).strip(), fmt).date()
        except (ValueError, AttributeError):
            continue
    return None


def check_fdps() -> dict:
    import yaml

    today = date.today()
    results = {"overdue": [], "due_soon": [], "ok": []}

    for fp in BLACKBOARD_DIR.glob("*.yaml"):
        try:
            data = yaml.safe_load(fp.read_text())
        except Exception:
            continue
        if not data:
            continue

        client_name = data.get("name") or data.get("client_name") or fp.stem
        bookings = data.get("bookings", [])
        if isinstance(bookings, dict):
            bookings = [bookings]

        for booking in bookings:
            if not isinstance(booking, dict):
                continue

            fdp_str = booking.get("final_payment_date") or booking.get("fdp") or booking.get("final_payment")
            if not fdp_str:
                continue

            fdp_date = parse_date(str(fdp_str))
            if not fdp_date:
                continue

            payment_received = (
                booking.get("payment_received")
                or booking.get("final_payment_received")
                or booking.get("paid_in_full")
            )

            days_until_fdp = (fdp_date - today).days
            dep_str = booking.get("departure_date") or booking.get("embark_date")
            dep_date = parse_date(str(dep_str)) if dep_str else None

            # Skip if departure already passed
            if dep_date and dep_date < today - timedelta(days=30):
                continue

            record = {
                "client": client_name,
                "booking_ref": booking.get("booking_ref") or booking.get("booking_number", ""),
                "fdp": str(fdp_date),
                "days_until_fdp": days_until_fdp,
                "payment_received": bool(payment_received),
                "departure": str(dep_date) if dep_date else "?",
            }

            if payment_received:
                results["ok"].append(record)
                log.info(f"OK: {client_name} FPD {fdp_date} — payment received")
            elif days_until_fdp < -OVERDUE_FLAG_DAYS:
                record["days_overdue"] = abs(days_until_fdp)
                results["overdue"].append(record)
                log.warning(f"OVERDUE FPD: {client_name} — FPD was {fdp_date} ({abs(days_until_fdp)}d ago)")
            elif days_until_fdp <= WARN_DAYS_AHEAD:
                results["due_soon"].append(record)
                log.info(f"DUE SOON: {client_name} FPD {fdp_date} ({days_until_fdp}d)")
            else:
                results["ok"].append(record)

    return results


def write_hale_decision(results: dict, run_dt: datetime) -> None:
    issues = results["overdue"] + results["due_soon"]
    if not issues:
        return
    lines = [
        f"\n### {run_dt.strftime('%Y-%m-%d %H:%M:%S')} — Autonomous Decision (Tier T0)\n",
        f"**Decision:** FDP reconciliation: {len(results['overdue'])} overdue, {len(results['due_soon'])} due soon\n",
    ]
    for item in results["overdue"]:
        lines.append(f"  - OVERDUE: {item['client']} FPD {item['fdp']} ({item['days_overdue']}d ago)\n")
    for item in results["due_soon"]:
        lines.append(f"  - DUE SOON: {item['client']} FPD {item['fdp']} ({item['days_until_fdp']}d)\n")
    lines.append("**Domain:** Finance / FDP management\n**Type:** proactive alert\n**Outcome:** surfaced to Commander\n")
    with open(HALE_DECISIONS, "a") as f:
        f.writelines(lines)


def draft_fdp_alert(results: dict, run_dt: datetime) -> None:
    issues = results["overdue"] + [r for r in results["due_soon"] if r["days_until_fdp"] <= 7]
    if not issues:
        return
    try:
        sys.path.insert(0, str(ROOT))
        from core.email.thunderbird_gmail import gmail_create_draft_sync

        def _row(item):
            color = "red" if item.get("days_overdue") else "orange"
            status = f"{item.get('days_overdue', item['days_until_fdp'])}d {'OVERDUE' if item.get('days_overdue') else 'remaining'}"
            return (
                f"<tr><td>{item['client']}</td><td>{item.get('booking_ref','?')}</td>"
                f"<td style='color:{color};'><b>{item['fdp']}</b></td>"
                f"<td>{status}</td><td>{item['departure']}</td></tr>"
            )
        rows = "".join(_row(item) for item in issues)
        body = f"""<div style='background:#f7f3ea;padding:20px;font-family:Georgia;color:#0000ff;'>
<p>Commander —</p>
<p><strong>FDP RECONCILIATION ALERT — {run_dt.strftime('%B %d, %Y')}</strong></p>
<table border='1' cellpadding='6' style='border-collapse:collapse;color:#0000ff;'>
<tr><th>Client</th><th>Booking Ref</th><th>FPD</th><th>Status</th><th>Departure</th></tr>
{rows}
</table>
<p>Action required: process outstanding payments and confirm with supplier.</p>
<p>— Hale / Harlan</p>
</div>"""
        gmail_create_draft_sync(
            to="d2mconcierge@gmail.com",
            subject=f"[FDP ALERT] {len(results['overdue'])} Overdue, {len(results['due_soon'])} Due Soon",
            body=body,
        )
        log.info(f"FDP alert draft created for {len(issues)} items")
    except Exception as e:
        log.warning(f"Could not create Gmail draft: {e}")


def main() -> int:
    run_dt = datetime.now()
    log.info(f"FDP reconciliation — {run_dt.date()}")

    results = check_fdps()
    log.info(
        f"FDP check: {len(results['overdue'])} overdue, "
        f"{len(results['due_soon'])} due soon, {len(results['ok'])} ok"
    )

    entry = {
        "ts": run_dt.isoformat(),
        "overdue": len(results["overdue"]),
        "due_soon": len(results["due_soon"]),
        "ok": len(results["ok"]),
        "detail": {"overdue": results["overdue"], "due_soon": results["due_soon"]},
    }
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")

    if results["overdue"] or results["due_soon"]:
        write_hale_decision(results, run_dt)
        draft_fdp_alert(results, run_dt)

    return 0


if __name__ == "__main__":
    sys.exit(main())
