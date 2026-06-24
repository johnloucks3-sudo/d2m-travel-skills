#!/home/john/Thunderbird/.venv/bin/python3
"""
Commission Aging Pipeline — MISSION-432
Tracks days since embarkation vs commission receipt.
Alert thresholds: 31 days → Harlan, 60 days → Commander (Telegram).
"""

import json
import logging
import os
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

THUNDERBIRD = Path("/home/john/Thunderbird")
DOSSIER_DIR = THUNDERBIRD / "dossiers"
OUTPUT_FILE = THUNDERBIRD / "output" / "commission_aging_report.json"
LOG_FILE = THUNDERBIRD / "logs" / "commission_aging_pipeline.log"
WING_PAGE = str(THUNDERBIRD / "OpsCenter" / "wing_page.py")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

TODAY = date.today()

# Dossier files that are destination/reference docs — skip these
SKIP_PREFIXES = ("DOSSIER_", "GROUP_", "MISSION-", "PROSPECT_", "CLAUDE")
SKIP_SUFFIXES = ("_TIMELINE.md", "_TRACKER.md", "_TEMPLATE.md", "_EXCURSIONS.md",
                 "_TIMELINE.md", "_drive.md", "_Research.md", "_RUNBOOK.md",
                 "_CallPrep.md", "_Coverage_Brief.md", "_guide.md", "_Guide.md")


def parse_date(val: str | None) -> date | None:
    if not val:
        return None
    val = val.strip().strip('"').strip("'")
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%b %d, %Y", "%B %d, %Y", "%d %b %Y"):
        try:
            return datetime.strptime(val, fmt).date()
        except ValueError:
            continue
    return None


def extract_field(text: str, *keys: str) -> str | None:
    """Extract the first matching key: value from frontmatter or inline text."""
    for key in keys:
        # YAML-style frontmatter: key: value
        m = re.search(rf"^{re.escape(key)}:\s*(.+)$", text, re.MULTILINE | re.IGNORECASE)
        if m:
            return m.group(1).strip().strip('"').strip("'")
        # Bold table row: **Key** | value  or | key | value |
        m = re.search(
            rf"\|\s*\*?\*?{re.escape(key)}\*?\*?\s*\|\s*([^|\n]+)",
            text, re.IGNORECASE
        )
        if m:
            return m.group(1).strip()
    return None


def extract_commission_received(text: str) -> bool:
    """Determine if commission has been received."""
    val = extract_field(text, "commission_received", "commission_status")
    if val:
        return val.lower() in ("true", "yes", "received", "paid", "confirmed")
    # Presence of a verified_date indicates receipt
    verified = extract_field(text, "commission_verified_date")
    if verified:
        return True
    # harlan_signoff with "PAID" suggests commission confirmed
    harlan = extract_field(text, "harlan_signoff")
    if harlan and "PAID" in harlan.upper():
        return True
    return False


def extract_commission_amount(text: str) -> float:
    val = extract_field(text, "commission_amount", "d2m_commission", "commission_expected")
    if val:
        try:
            return float(re.sub(r"[^\d.]", "", val))
        except ValueError:
            pass
    return 0.0


def should_skip(name: str) -> bool:
    for prefix in SKIP_PREFIXES:
        if name.startswith(prefix):
            return True
    for suffix in SKIP_SUFFIXES:
        if name.endswith(suffix):
            return True
    return False


def is_non_d2m_booking(path: Path) -> bool:
    """Return True if dossier explicitly marks the booking as non-D2M (Interline, personal, etc.)."""
    text = path.read_text(errors="replace")[:500]
    non_d2m_signals = (
        "interline travel & tour",
        "interline travel and tour",
        "not d2m-booked",
        "personal trip, not d2m",
        "non-d2m",
        "jwoodcock@perx.com",   # Interline agent
        "d2m_booking: false",   # explicit front-matter exclusion flag
        "commission_scope: none",
    )
    text_lower = text.lower()
    return any(s in text_lower for s in non_d2m_signals)


def parse_dossier(path: Path) -> list[dict]:
    """Return one or more booking records from a dossier."""
    text = path.read_text(errors="replace")
    records = []

    # Check for multi-booking dossier (booking_1_departure, booking_2_departure, ...)
    booking_numbers = re.findall(r"booking_(\d+)_departure:\s*(\S+)", text, re.IGNORECASE)
    if booking_numbers:
        for num, dep_str in booking_numbers:
            dep_date = parse_date(dep_str)
            if not dep_date:
                continue
            payment_raw = extract_field(text, f"booking_{num}_payment_status") or ""
            commission_received = payment_raw.lower() == "paid_in_full"
            ref = extract_field(text, f"booking_{num}_ref", f"booking_{num}_booking_ref") or f"{path.stem}-b{num}"
            cruise = extract_field(text, "cruise_line") or "Unknown"
            client = extract_field(text, "client_name", "name") or path.stem.replace("_", " ")
            commission_amt = extract_commission_amount(text)
            records.append({
                "source_file": path.name,
                "client_name": client,
                "booking_ref": ref,
                "cruise_line": cruise,
                "embarkation_date": dep_date.isoformat(),
                "commission_received": commission_received,
                "commission_amount_expected": commission_amt,
            })
        return records

    # Single booking
    dep_date = parse_date(
        extract_field(text, "departure", "embarkation_date", "departure_date",
                      "Embarkation", "EMBARKATION", "Departure Date")
    )
    if not dep_date:
        # Try markdown table pattern: | Aug 29 | EMBARKATION |
        m = re.search(r"\|\s*(\w+ \d+, \d{4}|\d{4}-\d{2}-\d{2})\s*\|\s*EMBARKATION", text, re.IGNORECASE)
        if m:
            dep_date = parse_date(m.group(1))

    if not dep_date:
        return []  # No embarkation date — skip

    commission_received = extract_commission_received(text)
    commission_amt = extract_commission_amount(text)
    booking_ref = (
        extract_field(text, "booking_ref", "booking_id", "booking_number", "reservation_number")
        or path.stem
    )
    cruise_line = extract_field(text, "cruise_line", "cruise line") or "Unknown"
    client = (
        extract_field(text, "client_name", "name", "guest_name")
        or path.stem.replace("_", " ")
    )

    records.append({
        "source_file": path.name,
        "client_name": client,
        "booking_ref": booking_ref,
        "cruise_line": cruise_line,
        "embarkation_date": dep_date.isoformat(),
        "commission_received": commission_received,
        "commission_amount_expected": commission_amt,
    })
    return records


def build_alert_status(days: int, commission_received: bool, future: bool) -> tuple[str, str]:
    if future:
        return "NOT_YET_SAILED", "No action — voyage not yet departed."
    if commission_received:
        return "NORMAL", "Commission confirmed received."
    if days >= 60:
        return "COMMANDER_ESCALATE", f"⚠️ {days} days post-embarkation — no commission. ESCALATE TO COMMANDER."
    if days >= 31:
        return "HARLAN_ALERT", f"🔔 {days} days post-embarkation — no commission. Alert Harlan for follow-up."
    return "NORMAL", f"{days} days post-embarkation — within 30-day window, no action yet."


def send_telegram_alert(clients_needing_escalation: list[dict]) -> None:
    if not clients_needing_escalation:
        return
    lines = ["⚠️ COMMISSION AGING ALERT — Commander Escalation Required\n"]
    for c in clients_needing_escalation:
        lines.append(
            f"• {c['client_name']} ({c['booking_ref']}) — "
            f"{c['days_since_embarkation']}d post-embarkation, no commission. "
            f"Expected: ${c['commission_amount_expected']:,.2f}"
        )
    msg = "\n".join(lines)
    try:
        venv_python = str(THUNDERBIRD / ".venv" / "bin" / "python3")
        subprocess.run(
            [venv_python, WING_PAGE, "--priority", "high", "--message", msg],
            cwd=str(THUNDERBIRD), timeout=30, check=False
        )
        log.info("Telegram escalation sent for %d clients.", len(clients_needing_escalation))
    except Exception as e:
        log.error("Telegram page failed: %s", e)


def main() -> None:
    log.info("=== Commission Aging Pipeline — %s ===", TODAY.isoformat())

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    dossier_files = sorted(
        f for f in DOSSIER_DIR.glob("*.md")
        if not should_skip(f.name) and not is_non_d2m_booking(f)
    )

    clients = []
    commander_escalations = []

    for dossier in dossier_files:
        try:
            records = parse_dossier(dossier)
        except Exception as e:
            log.warning("Error parsing %s: %s", dossier.name, e)
            continue

        for rec in records:
            dep = date.fromisoformat(rec["embarkation_date"])
            future = dep > TODAY
            days = 0 if future else (TODAY - dep).days

            alert_status, action_needed = build_alert_status(
                days, rec["commission_received"], future
            )

            entry = {
                "client_name": rec["client_name"],
                "booking_ref": rec["booking_ref"],
                "cruise_line": rec["cruise_line"],
                "embarkation_date": rec["embarkation_date"],
                "days_since_embarkation": days,
                "commission_received": rec["commission_received"],
                "commission_amount_expected": rec["commission_amount_expected"],
                "alert_status": alert_status,
                "action_needed": action_needed,
                "source_file": rec["source_file"],
            }
            clients.append(entry)

            if alert_status == "COMMANDER_ESCALATE":
                commander_escalations.append(entry)

            log.info(
                "[%s] %s | %s | dep=%s | days=%d | commission_received=%s | status=%s",
                alert_status,
                rec["client_name"],
                rec["booking_ref"],
                rec["embarkation_date"],
                days,
                rec["commission_received"],
                alert_status,
            )

    # Sort: escalations first, then alerts, then normal
    priority_order = {"COMMANDER_ESCALATE": 0, "HARLAN_ALERT": 1, "NORMAL": 2, "NOT_YET_SAILED": 3}
    clients.sort(key=lambda x: (priority_order.get(x["alert_status"], 9), x["embarkation_date"]))

    report = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "report_date": TODAY.isoformat(),
        "total_records": len(clients),
        "commander_escalate_count": sum(1 for c in clients if c["alert_status"] == "COMMANDER_ESCALATE"),
        "harlan_alert_count": sum(1 for c in clients if c["alert_status"] == "HARLAN_ALERT"),
        "clients": clients,
    }

    OUTPUT_FILE.write_text(json.dumps(report, indent=2))
    log.info("Report written → %s (%d records)", OUTPUT_FILE, len(clients))

    if commander_escalations:
        send_telegram_alert(commander_escalations)
    else:
        log.info("No commander escalations needed today.")


if __name__ == "__main__":
    main()
