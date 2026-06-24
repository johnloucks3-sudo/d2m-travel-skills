#!/home/john/Thunderbird/.venv/bin/python3
"""
Dossier Freshness Cron — MISSION-433
Daily scan: flag stale dossiers for clients with imminent voyages.
Staleness rules:
  1. Modified >30 days ago AND voyage within 90 days
  2. Missing required fields (embarkation_date, booking_ref, payment_status)
  3. FPD within 30 days AND dossier not updated recently
"""

import json
import logging
import os
import re
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

THUNDERBIRD = Path("/home/john/Thunderbird")
DOSSIER_DIR = THUNDERBIRD / "dossiers"
OUTPUT_FILE = THUNDERBIRD / "output" / "dossier_freshness_report.json"
LOG_FILE = THUNDERBIRD / "logs" / "dossier_freshness_cron.log"
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
VOYAGE_HORIZON_DAYS = 90
STALE_MODIFIED_DAYS = 30
FPD_ALERT_DAYS = 30

# Skip destination docs, tracker files, reference docs, prospects — only active/complete client dossiers
SKIP_PREFIXES = ("DOSSIER_", "GROUP_", "MISSION-", "PROSPECT_", "CLAUDE", "Scandi_")
SKIP_SUFFIXES = (
    "_TIMELINE.md", "_TRACKER.md", "_TEMPLATE.md", "_EXCURSIONS.md",
    "_drive.md", "_Research.md", "_RUNBOOK.md", "_CallPrep.md",
    "_Coverage_Brief.md", "_guide.md", "_Guide.md",
    # Additional supplemental/reference patterns
    "_Excursions.md", "_Eligibility.md", "_Brief.md", "_Monthly_Brief.md",
    "_Correspondence_Draft.md", "_Itinerary_Apr2026.md",
    "_Romance_April2026.md",
)
# Substrings that mark non-booking files: prospects, personal reference, supplemental
SKIP_SUBSTRINGS = ("_Prospect", "_ProBono", "_SelfDrive", "_Complete", "_Personal",
                   "_Family", "_Excursion", "Scandi_Group")

REQUIRED_FIELDS = ["departure", "booking_ref", "payment_status"]
REQUIRED_FIELD_ALIASES = {
    # Multi-booking dossiers use booking_1_departure — accept all forms
    "departure": ["departure", "embarkation_date", "departure_date", "Embarkation", "EMBARKATION",
                  "booking_1_departure", "booking_2_departure"],
    # Dossier schema uses "booking:" (per dossiers/CLAUDE.md) — also accept common variants
    # Multi-booking uses "booking_1:", "booking_2:" (bare, no _ref suffix)
    "booking_ref": ["booking", "booking_ref", "booking_id", "booking_number", "reservation_number",
                    "booking_1", "booking_2", "booking_1_ref", "booking_2_ref"],
    "payment_status": ["payment_status", "payment status", "booking_1_payment_status"],
}
# Only scan dossiers with these status values — skip prospects, archived, complete
ACTIVE_STATUSES = {"active", ""}  # empty = not set = assume active until proven otherwise


def should_skip(name: str) -> bool:
    for prefix in SKIP_PREFIXES:
        if name.startswith(prefix):
            return True
    for suffix in SKIP_SUFFIXES:
        if name.endswith(suffix):
            return True
    for substring in SKIP_SUBSTRINGS:
        if substring in name:
            return True
    return False


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
    for key in keys:
        m = re.search(rf"^{re.escape(key)}:\s*(.+)$", text, re.MULTILINE | re.IGNORECASE)
        if m:
            return m.group(1).strip().strip('"').strip("'")
    return None


def find_departure(text: str) -> date | None:
    # Try frontmatter aliases first
    for alias in REQUIRED_FIELD_ALIASES["departure"]:
        val = extract_field(text, alias)
        if val:
            d = parse_date(val)
            if d:
                return d
    # Try multi-booking: take earliest future or most recent past
    matches = re.findall(r"booking_\d+_departure:\s*(\S+)", text, re.IGNORECASE)
    dates = [parse_date(m) for m in matches if parse_date(m)]
    if dates:
        future_dates = [d for d in dates if d >= TODAY]
        return min(future_dates) if future_dates else min(dates)
    # Table pattern
    m = re.search(
        r"\|\s*(\d{4}-\d{2}-\d{2}|\w+ \d+, \d{4})\s*\|\s*EMBARKATION",
        text, re.IGNORECASE
    )
    if m:
        return parse_date(m.group(1))
    return None


def find_fpd(text: str) -> date | None:
    val = extract_field(text, "fpd", "final_payment_date", "final_payment", "Final Payment Date", "FPD")
    if val:
        return parse_date(val)
    # Pattern: DUE 22 Jul 2026 or Due: 2026-07-22
    m = re.search(r"(?:DUE|due|Due)\s+(\d{1,2}\s+\w+ \d{4}|\d{4}-\d{2}-\d{2})", text)
    if m:
        return parse_date(m.group(1))
    return None


def check_required_fields(text: str) -> list[str]:
    missing = []
    for field, aliases in REQUIRED_FIELD_ALIASES.items():
        found = any(extract_field(text, alias) for alias in aliases)
        if not found:
            # Also check multi-booking pattern for booking_ref and payment_status
            if field == "booking_ref" and re.search(r"booking_\d+_ref:", text, re.IGNORECASE):
                continue
            if field == "payment_status" and re.search(r"booking_\d+_payment_status:", text, re.IGNORECASE):
                continue
            missing.append(field)
    return missing


def classify_dossier(path: Path) -> dict | None:
    text = path.read_text(errors="replace")

    # Skip non-active dossiers (prospects, complete, archived) by status field
    status_val = (extract_field(text, "status") or "").lower().strip()
    if status_val in ("prospect", "complete", "archived", "cancelled", "pro_bono", "probono"):
        return None  # skip silently

    stat = path.stat()
    last_modified = date.fromtimestamp(stat.st_mtime)
    days_since_modified = (TODAY - last_modified).days

    departure = find_departure(text)
    fpd = find_fpd(text)
    missing_fields = check_required_fields(text)

    days_to_voyage = None
    if departure:
        days_to_voyage = (departure - TODAY).days  # negative = already departed

    stale_reasons = []
    is_stale = False

    # Rule 1: Modified >30 days ago AND voyage within 90 days
    if departure and days_to_voyage is not None and 0 <= days_to_voyage <= VOYAGE_HORIZON_DAYS:
        if days_since_modified > STALE_MODIFIED_DAYS:
            stale_reasons.append(
                f"Not updated in {days_since_modified}d but voyage in {days_to_voyage}d"
            )
            is_stale = True

    # Rule 2: Missing required fields
    if missing_fields:
        stale_reasons.append(f"Missing fields: {', '.join(missing_fields)}")
        is_stale = True

    # Rule 3: FPD within 30 days and dossier stale
    if fpd:
        days_to_fpd = (fpd - TODAY).days
        if 0 <= days_to_fpd <= FPD_ALERT_DAYS and days_since_modified > STALE_MODIFIED_DAYS:
            stale_reasons.append(
                f"FPD in {days_to_fpd}d but dossier not updated in {days_since_modified}d"
            )
            is_stale = True

    client_name = (
        extract_field(text, "client_name", "name", "guest_name")
        or path.stem.replace("_", " ")
    )

    return {
        "file": path.name,
        "client_name": client_name,
        "last_modified": last_modified.isoformat(),
        "days_since_modified": days_since_modified,
        "departure_date": departure.isoformat() if departure else None,
        "days_to_voyage": days_to_voyage,
        "fpd_date": fpd.isoformat() if fpd else None,
        "missing_fields": missing_fields,
        "is_stale": is_stale,
        "stale_reasons": stale_reasons,
        "freshness_status": "STALE" if is_stale else "FRESH",
    }


def send_telegram_alert(stale: list[dict]) -> None:
    if not stale:
        return
    lines = [f"⚠️ DOSSIER FRESHNESS ALERT — {len(stale)} stale dossier(s)\n"]
    for d in stale:
        voyage_info = f"voyage in {d['days_to_voyage']}d" if d["days_to_voyage"] is not None else "no departure date"
        lines.append(
            f"• {d['client_name']} ({d['file']}) — {voyage_info}: {'; '.join(d['stale_reasons'])}"
        )
    msg = "\n".join(lines)
    try:
        venv_python = str(THUNDERBIRD / ".venv" / "bin" / "python3")
        subprocess.run(
            [venv_python, WING_PAGE, "--priority", "normal", "--message", msg],
            cwd=str(THUNDERBIRD), timeout=30, check=False
        )
        log.info("Telegram alert sent for %d stale dossiers.", len(stale))
    except Exception as e:
        log.error("Telegram page failed: %s", e)


def main() -> None:
    log.info("=== Dossier Freshness Cron — %s ===", TODAY.isoformat())
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    dossier_files = sorted(
        f for f in DOSSIER_DIR.glob("*.md") if not should_skip(f.name)
    )

    results = []
    stale_dossiers = []

    for path in dossier_files:
        try:
            record = classify_dossier(path)
            if record is None:
                continue  # status gate: skipped (prospect/complete/archived)
            results.append(record)
            if record["is_stale"]:
                stale_dossiers.append(record)
                log.warning("[STALE] %s — %s", path.name, "; ".join(record["stale_reasons"]))
            else:
                log.info("[FRESH] %s", path.name)
        except Exception as e:
            log.warning("Error scanning %s: %s", path.name, e)

    # Sort: stale first, then by days_to_voyage ascending
    results.sort(key=lambda x: (0 if x["is_stale"] else 1, x.get("days_to_voyage") or 9999))

    report = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "report_date": TODAY.isoformat(),
        "total_dossiers_scanned": len(results),
        "stale_count": len(stale_dossiers),
        "fresh_count": len(results) - len(stale_dossiers),
        "dossiers": results,
    }

    OUTPUT_FILE.write_text(json.dumps(report, indent=2))
    log.info("Report written → %s (%d scanned, %d stale)", OUTPUT_FILE, len(results), len(stale_dossiers))

    if stale_dossiers:
        send_telegram_alert(stale_dossiers)
    else:
        log.info("All dossiers fresh — no alerts needed.")


if __name__ == "__main__":
    main()
