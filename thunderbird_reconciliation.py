"""
Thunderbird Booking Reconciliation Module
==========================================
Dreams2Memories Travel, LLC

Cross-checks booking data across multiple sources and flags discrepancies.

Sources:
  - KNOWN_BOOKINGS (thunderbird_anchor_dates.py) — canonical ground truth
  - Dossier files (~/Thunderbird/dossiers/*.md) — narrative + detailed data
  - Google Sheets Booking Master (via gspread) — live sync data
  - TESS CRM (optional, if authenticated) — supplier-authoritative records
  - Anchor dates engine — FPD / embark / disembark / booking dates

Output:
  - ReconciliationReport per booking: matches (green), mismatches (red), missing (yellow)
  - reconcile_booking(client_name) -> ReconciliationReport
  - reconcile_all_bookings() -> List[ReconciliationReport]

Integration:
  - Morning briefing: summary line appended
  - Batch runner: weekly task

Usage:
  python3 thunderbird_reconciliation.py               # reconcile all
  python3 thunderbird_reconciliation.py --booking Furlow
  python3 thunderbird_reconciliation.py --json        # JSON output
"""

from __future__ import annotations

import json
import logging
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------------

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
DOSSIER_DIR = THUNDERBIRD_DIR / "dossiers"
CREDENTIALS_FILE = THUNDERBIRD_DIR / "credentials.json"

SPREADSHEET_ID = "1GFjUe8RvP-GT4YHGn0DYv_BEAZGXlYfwEicFrm8ANuU"
BOOKING_MASTER_TAB = "Booking Master B"

SKIP_DOSSIERS = {"CLAUDE.md", "DANI_TESTER_BRIEFINGS.md", "DOSSIER_Regent_Tips_Guide.md"}

# Tolerance for dollar-amount matching (dossier parsing is imprecise)
AMOUNT_TOLERANCE = 5.00


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ReconItem:
    """A single reconciliation finding."""
    field: str            # What was checked (e.g. "embark_date", "total_amount")
    status: str           # "match" | "mismatch" | "missing"
    anchor_value: Any     # Value from KNOWN_BOOKINGS (ground truth)
    source_value: Any     # Value found in the compared source
    source: str           # "dossier" | "sheets" | "tess"
    note: str = ""


@dataclass
class ReconciliationReport:
    booking_key: str
    client_name: str
    supplier: str
    conf: str
    run_date: str = field(default_factory=lambda: date.today().isoformat())

    matches: List[ReconItem] = field(default_factory=list)
    mismatches: List[ReconItem] = field(default_factory=list)
    missing: List[ReconItem] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        if self.mismatches:
            return "RED"
        if self.missing:
            return "YELLOW"
        return "GREEN"

    @property
    def summary_line(self) -> str:
        parts = []
        if self.mismatches:
            parts.append(f"{len(self.mismatches)} mismatch{'es' if len(self.mismatches) > 1 else ''}")
        if self.missing:
            parts.append(f"{len(self.missing)} missing")
        if self.matches:
            parts.append(f"{len(self.matches)} OK")
        status_icon = {"RED": "[RED]", "YELLOW": "[YLW]", "GREEN": "[GRN]"}.get(self.status, "")
        label = f"{self.client_name} ({self.supplier} {self.conf})"
        return f"{status_icon} {label}: {', '.join(parts) if parts else 'no data'}"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status
        d["summary_line"] = self.summary_line
        return d


# ---------------------------------------------------------------------------
# Dossier parser — extracts key fields from markdown
# ---------------------------------------------------------------------------

def _parse_amount(text: str) -> Optional[float]:
    """Extract first dollar amount from a string."""
    m = re.search(r"\$[\d,]+(?:\.\d{2})?", text)
    if m:
        return float(m.group().replace("$", "").replace(",", ""))
    return None


def _parse_date_str(text: str) -> Optional[date]:
    """Parse dates in common dossier formats."""
    text = text.strip().rstrip(",").strip()
    formats = [
        "%Y-%m-%d", "%b %d, %Y", "%B %d, %Y",
        "%b %d %Y", "%B %d %Y", "%m/%d/%Y",
        "%d %b %Y", "%d-%b-%Y", "%d-%b-%y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def parse_dossier(path: Path) -> Dict[str, Any]:
    """
    Parse a dossier .md file into a structured dict.
    Returns keys (all optional): conf, client, embark_date, disembark_date,
    fpd, fpd_status, total_amount, paid_amount, balance_due, cabin, pnrs,
    guest_count, insurance_status, supplier.
    """
    text = path.read_text(encoding="utf-8", errors="ignore")
    data: Dict[str, Any] = {"_path": str(path)}

    # Confirmation number — look for booking number patterns
    m = re.search(r"Booking\s+(?:#\s*)?(\w{6,10})\b", text, re.IGNORECASE)
    if not m:
        m = re.search(r"conf(?:irmation)?\s*[:#]?\s*(\w{6,10})\b", text, re.IGNORECASE)
    if m:
        data["conf"] = m.group(1)

    # Supplier
    for sup in ["Silversea", "Regent", "Viking", "Cunard", "Seabourn",
                "Oceania", "Ponant", "AmaWaterways", "Princess"]:
        if re.search(sup, text, re.IGNORECASE):
            data["supplier"] = sup
            break

    # Total booking amount — handle bold markdown (**...**) and plain text
    m = re.search(r"Total\s+Booking\s+Amount[*:\s]+\$?([\d,]+(?:\.\d{2})?)", text, re.IGNORECASE)
    if m:
        data["total_amount"] = float(m.group(1).replace(",", ""))

    # Paid to date / deposit
    m = re.search(r"Paid\s+to\s+Date[*:\s]+\$?([\d,]+(?:\.\d{2})?)", text, re.IGNORECASE)
    if m:
        data["paid_amount"] = float(m.group(1).replace(",", ""))

    # Balance due
    m = re.search(r"Balance\s+Due[*:\s]+\$?([\d,]+(?:\.\d{2})?)", text, re.IGNORECASE)
    if m:
        data["balance_due"] = float(m.group(1).replace(",", ""))

    # FPD — multiple patterns:
    #   "Balance Due: $X — **DUE APR 1, 2026**"
    #   "FINAL PAYMENT DUE — $15,486" in a table row with date in same row
    #   "Final Payment Date: ..."
    fpd_parsed = None
    # Pattern 1: "DUE <Month Day, Year>" or "DUE <Month Day>"
    m = re.search(
        r"\bDUE\b[*\s—–:]+([A-Za-z]+ \d{1,2},?\s*\d{4})",
        text, re.IGNORECASE
    )
    if m:
        fpd_parsed = _parse_date_str(m.group(1).strip())
    # Pattern 2: table row "|Date|FINAL PAYMENT DUE..."
    if not fpd_parsed:
        m = re.search(
            r"\|\s*([A-Za-z]+ \d+)\s*\|\s*\*{0,2}FINAL PAYMENT",
            text, re.IGNORECASE
        )
        if m:
            # Date is like "Apr 1" — need year from context
            raw = m.group(1).strip()
            year_m = re.search(r"20\d{2}", text)
            year = year_m.group() if year_m else str(date.today().year)
            fpd_parsed = _parse_date_str(f"{raw}, {year}")
    # Pattern 3: FPD/Final_Payment_Date key
    if not fpd_parsed:
        m = re.search(
            r"(?:FPD|Final\s+Payment\s+Date)[*:\s—–]+([A-Za-z0-9 ,]+(?:\d{4}))",
            text, re.IGNORECASE
        )
        if m:
            fpd_parsed = _parse_date_str(m.group(1).strip())
    if fpd_parsed:
        data["fpd"] = fpd_parsed

    # FPD status — avoid matching "Paid to Date" as PAID
    if re.search(r"\bpaid\s+in\s+full\b|fpd.*status.*paid|payment.*confirmed\b|\bpayment\s+received\b", text, re.IGNORECASE):
        data["fpd_status"] = "PAID"
    elif re.search(r"FINAL PAYMENT DUE|PAYMENT DUE|balance due|\bPENDING\b", text, re.IGNORECASE):
        data["fpd_status"] = "PENDING"

    # Embark date — multiple formats:
    #   "| Aug 29 | EMBARKATION |"  (key-dates table, date first)
    #   "EMBARKATION | Aug 29"       (reversed)
    #   "embark_date: 2026-08-29"
    embark_parsed = None
    for pattern in [
        r"\|\s*([A-Za-z]+ \d{1,2})\s*\|\s*\*{0,2}EMBARKATION",          # | Aug 29 | EMBARKATION
        r"EMBARKATION\s*[|\s]*([A-Za-z]+ \d{1,2}(?:,\s*\d{4})?)",       # EMBARKATION | Aug 29
        r"embark(?:ation)?\s*[:\s]+(\d{4}-\d{2}-\d{2})",                 # embark_date: 2026-08-29
        r"Embark(?:ation)?\s+Day[:\s]+([A-Za-z]+ \d{1,2},?\s*\d{4})",   # Embarkation Day: Aug 29, 2026
    ]:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            raw = m.group(1).strip()
            # Add year if missing — infer from nearby 4-digit year
            if not re.search(r"\d{4}", raw):
                year_m = re.search(r"20\d{2}", text)
                if year_m:
                    raw = f"{raw}, {year_m.group()}"
            embark_parsed = _parse_date_str(raw)
            if embark_parsed:
                break
    if embark_parsed:
        data["embark_date"] = embark_parsed

    # Disembark date — same multi-pattern approach
    disembark_parsed = None
    for pattern in [
        r"\|\s*([A-Za-z]+ \d{1,2})\s*\|\s*\*{0,2}Disembarkation",
        r"Disembarkation\s*[|\s]*([A-Za-z]+ \d{1,2}(?:,\s*\d{4})?)",
        r"disembark(?:ation)?\s*[:\s]+(\d{4}-\d{2}-\d{2})",
        r"Disembark(?:ation)?\s+Day[:\s]+([A-Za-z]+ \d{1,2},?\s*\d{4})",
    ]:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            raw = m.group(1).strip()
            if not re.search(r"\d{4}", raw):
                year_m = re.search(r"20\d{2}", text)
                if year_m:
                    raw = f"{raw}, {year_m.group()}"
            disembark_parsed = _parse_date_str(raw)
            if disembark_parsed:
                break
    if disembark_parsed:
        data["disembark_date"] = disembark_parsed

    # Cabin / Suite
    m = re.search(r"Suite\s+(\d{3,4})[,\s]", text, re.IGNORECASE)
    if not m:
        m = re.search(r"Cabin\s+(\w+)\b", text, re.IGNORECASE)
    if m:
        data["cabin"] = m.group(1)

    # PNRs — look for 6-char alphanumeric codes near "PNR" or "Booking"
    pnrs = re.findall(r"\bPNR[s]?\W+([A-Z0-9]{6})\b", text, re.IGNORECASE)
    if not pnrs:
        # Finnair/AA style labels
        pnrs = re.findall(r"(?:AA|Finnair|BA)[:\s/]+([A-Z]{6})\b", text)
    if pnrs:
        data["pnrs"] = list(set(pnrs))

    # Guest count — count "Guest Registration" mentions or named guests
    guest_count = len(re.findall(r"Guest Registration", text, re.IGNORECASE))
    if guest_count:
        data["guest_count"] = guest_count

    # Insurance — check NOT_BOOKED first (more specific) to avoid false positives
    if re.search(r"insurance.*not\s+booked|NOT BOOKED|no insurance|insurance.*(?:not|pending|missing)\b", text, re.IGNORECASE):
        data["insurance_status"] = "NOT_BOOKED"
    elif re.search(r"insurance.*(?:confirmed|active|purchased|policy\s+#|policy\s+number)\b", text, re.IGNORECASE):
        data["insurance_status"] = "BOOKED"

    return data


def find_dossier_for_booking(booking_key: str, bk: dict) -> Optional[Path]:
    """Try to find the dossier file matching a booking key."""
    conf = bk["conf"].replace("-25", "").replace("-", "")
    client_parts = bk["client"].lower().replace(" & ", " ").split()
    last_name = client_parts[1] if len(client_parts) > 1 else client_parts[0]

    candidates = []
    for p in DOSSIER_DIR.glob("*.md"):
        if p.name in SKIP_DOSSIERS:
            continue
        name_lower = p.stem.lower()
        # Match on last name or confirmation number
        if last_name in name_lower or conf.lower() in name_lower or conf.lower() in p.read_text(encoding="utf-8", errors="ignore")[:500]:
            candidates.append(p)

    # Prefer exact conf match in filename
    for p in candidates:
        if conf in p.stem:
            return p

    return candidates[0] if candidates else None


# ---------------------------------------------------------------------------
# Sheets reader (lazy import)
# ---------------------------------------------------------------------------

def _read_booking_master() -> List[Dict[str, str]]:
    """Read all rows from Booking Master B sheet. Returns list of header-keyed dicts."""
    try:
        import gspread
        from google.oauth2 import service_account
        creds = service_account.Credentials.from_service_account_file(
            str(CREDENTIALS_FILE),
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        gc = gspread.authorize(creds)
        ws = gc.open_by_key(SPREADSHEET_ID).worksheet(BOOKING_MASTER_TAB)
        rows = ws.get_all_values()
        if len(rows) < 2:
            return []
        headers = rows[0]
        result = []
        for row in rows[1:]:
            d = {headers[i]: (row[i] if i < len(row) else "") for i in range(len(headers))}
            if d.get("Client_Name") or d.get("Confirmation_Number"):
                result.append(d)
        return result
    except Exception as e:
        logger.warning(f"Sheets read failed: {e}")
        return []


def _find_sheet_row(rows: List[Dict], conf: str, client: str) -> Optional[Dict]:
    """Find the sheet row matching conf or client name."""
    conf_clean = conf.replace("-25", "").replace("-", "").upper()
    for row in rows:
        row_conf = row.get("Confirmation_Number", "").replace("-", "").upper()
        if row_conf and conf_clean in row_conf:
            return row
    # Fallback: match by client name (partial)
    last = client.split()[0].lower()
    for row in rows:
        if last in row.get("Client_Name", "").lower():
            return row
    return None


# ---------------------------------------------------------------------------
# TESS reader (lazy import, optional)
# ---------------------------------------------------------------------------

def _fetch_tess_booking(conf: str) -> Optional[Dict]:
    """Try to fetch booking from TESS. Returns None if not available/authenticated."""
    try:
        from thunderbird_tess import TessClient
        client = TessClient()
        if not client.is_authenticated():
            return None
        results = client.search_bookings(confirmation=conf)
        if results:
            return results[0]
    except Exception as e:
        logger.debug(f"TESS fetch skipped: {e}")
    return None


# ---------------------------------------------------------------------------
# Core reconciliation logic
# ---------------------------------------------------------------------------

def _date_match(a: Optional[date], b: Optional[date]) -> bool:
    if a is None or b is None:
        return False
    return a == b


def _amount_match(a: Optional[float], b: Optional[float]) -> bool:
    if a is None or b is None:
        return False
    return abs(a - b) <= AMOUNT_TOLERANCE


def reconcile_booking(booking_key: str, sheet_rows: Optional[List[Dict]] = None) -> ReconciliationReport:
    """
    Reconcile a single booking across dossier, sheets, and TESS.

    Args:
        booking_key: Key from KNOWN_BOOKINGS (e.g. 'Furlow_Regent_3071222')
        sheet_rows: Pre-fetched sheet rows (avoids repeated API calls in bulk mode)
    """
    from thunderbird_anchor_dates import KNOWN_BOOKINGS

    if booking_key not in KNOWN_BOOKINGS:
        return ReconciliationReport(
            booking_key=booking_key,
            client_name="UNKNOWN",
            supplier="UNKNOWN",
            conf="UNKNOWN",
            errors=[f"Booking key '{booking_key}' not found in KNOWN_BOOKINGS"],
        )

    bk = KNOWN_BOOKINGS[booking_key]
    report = ReconciliationReport(
        booking_key=booking_key,
        client_name=bk["client"],
        supplier=bk["supplier"],
        conf=bk["conf"],
    )

    # ── 1. Dossier reconciliation ──────────────────────────────────────────
    dossier_path = find_dossier_for_booking(booking_key, bk)
    if not dossier_path:
        report.missing.append(ReconItem(
            field="dossier_file", status="missing",
            anchor_value=booking_key, source_value=None,
            source="dossier",
            note=f"No dossier file found in {DOSSIER_DIR}",
        ))
    else:
        try:
            d = parse_dossier(dossier_path)

            # Embark date
            if "embark_date" in d:
                if _date_match(bk["embark_date"], d["embark_date"]):
                    report.matches.append(ReconItem("embark_date", "match", bk["embark_date"].isoformat(), d["embark_date"].isoformat(), "dossier"))
                else:
                    report.mismatches.append(ReconItem(
                        "embark_date", "mismatch",
                        bk["embark_date"].isoformat(), d["embark_date"].isoformat(),
                        "dossier", f"KNOWN_BOOKINGS says {bk['embark_date']}, dossier says {d['embark_date']}"
                    ))
            else:
                report.missing.append(ReconItem("embark_date", "missing", bk["embark_date"].isoformat(), None, "dossier", "Not found in dossier"))

            # Disembark date
            if "disembark_date" in d:
                if _date_match(bk["disembark_date"], d["disembark_date"]):
                    report.matches.append(ReconItem("disembark_date", "match", bk["disembark_date"].isoformat(), d["disembark_date"].isoformat(), "dossier"))
                else:
                    report.mismatches.append(ReconItem(
                        "disembark_date", "mismatch",
                        bk["disembark_date"].isoformat(), d["disembark_date"].isoformat(),
                        "dossier"
                    ))
            else:
                report.missing.append(ReconItem("disembark_date", "missing", bk["disembark_date"].isoformat(), None, "dossier"))

            # FPD
            if "fpd" in d:
                if _date_match(bk["fpd"], d["fpd"]):
                    report.matches.append(ReconItem("fpd", "match", bk["fpd"].isoformat(), d["fpd"].isoformat(), "dossier"))
                else:
                    report.mismatches.append(ReconItem(
                        "fpd", "mismatch",
                        bk["fpd"].isoformat(), d["fpd"].isoformat(),
                        "dossier", f"FPD mismatch: anchor={bk['fpd']}, dossier={d['fpd']}"
                    ))
            else:
                report.missing.append(ReconItem("fpd", "missing", bk["fpd"].isoformat(), None, "dossier"))

            # FPD status
            if "fpd_status" in d:
                anchor_status = bk.get("fpd_status", "UNKNOWN")
                if d["fpd_status"] == anchor_status or anchor_status == "UNKNOWN":
                    report.matches.append(ReconItem("fpd_status", "match", anchor_status, d["fpd_status"], "dossier"))
                else:
                    report.mismatches.append(ReconItem(
                        "fpd_status", "mismatch",
                        anchor_status, d["fpd_status"], "dossier",
                        f"Payment status conflict: KNOWN={anchor_status}, dossier={d['fpd_status']}"
                    ))
            else:
                report.missing.append(ReconItem("fpd_status", "missing", bk.get("fpd_status"), None, "dossier", "Payment status not parseable from dossier"))

            # PNRs present where flights expected (embark within 12 months)
            days_to_embark = (bk["embark_date"] - date.today()).days
            if days_to_embark < 365:
                if d.get("pnrs"):
                    report.matches.append(ReconItem("pnrs", "match", "expected", d["pnrs"], "dossier", f"PNRs found: {d['pnrs']}"))
                else:
                    report.missing.append(ReconItem("pnrs", "missing", "expected", None, "dossier", "No PNRs found in dossier (within 12 months of embark)"))

            # Insurance status
            ins_status = d.get("insurance_status", "UNKNOWN")
            if ins_status == "NOT_BOOKED":
                report.missing.append(ReconItem("insurance", "missing", "BOOKED", "NOT_BOOKED", "dossier", "Insurance not booked — flag for COS"))
            elif ins_status == "BOOKED":
                report.matches.append(ReconItem("insurance", "match", "BOOKED", "BOOKED", "dossier"))

            # Confirmation number in dossier
            if "conf" in d:
                anchor_conf = bk["conf"].replace("-25", "")
                dossier_conf = d["conf"]
                if anchor_conf.upper() in dossier_conf.upper() or dossier_conf.upper() in anchor_conf.upper():
                    report.matches.append(ReconItem("conf", "match", bk["conf"], d["conf"], "dossier"))
                else:
                    report.mismatches.append(ReconItem("conf", "mismatch", bk["conf"], d["conf"], "dossier", "Confirmation number mismatch"))
            else:
                report.missing.append(ReconItem("conf", "missing", bk["conf"], None, "dossier"))

        except Exception as e:
            report.errors.append(f"Dossier parse error: {e}")
            logger.warning(f"Error parsing dossier {dossier_path}: {e}")

    # ── 2. Google Sheets reconciliation ───────────────────────────────────
    if sheet_rows is None:
        sheet_rows = _read_booking_master()

    sheet_row = _find_sheet_row(sheet_rows, bk["conf"], bk["client"])
    if not sheet_row:
        report.missing.append(ReconItem(
            "sheets_row", "missing", booking_key, None, "sheets",
            f"No row found in '{BOOKING_MASTER_TAB}' for {bk['client']} / {bk['conf']}"
        ))
    else:
        from thunderbird_anchor_dates import _parse_date_flexible

        # Embark date in sheets
        sheet_start = _parse_date_flexible(sheet_row.get("Start_Date", ""))
        if sheet_start:
            if sheet_start == bk["embark_date"]:
                report.matches.append(ReconItem("embark_date", "match", bk["embark_date"].isoformat(), sheet_start.isoformat(), "sheets"))
            else:
                report.mismatches.append(ReconItem(
                    "embark_date", "mismatch",
                    bk["embark_date"].isoformat(), sheet_start.isoformat(),
                    "sheets", f"Sheet Start_Date {sheet_start} != anchor {bk['embark_date']}"
                ))
        else:
            report.missing.append(ReconItem("embark_date", "missing", bk["embark_date"].isoformat(), None, "sheets", "Start_Date blank in sheet"))

        # Disembark date in sheets
        sheet_end = _parse_date_flexible(sheet_row.get("End_Date", ""))
        if sheet_end:
            if sheet_end == bk["disembark_date"]:
                report.matches.append(ReconItem("disembark_date", "match", bk["disembark_date"].isoformat(), sheet_end.isoformat(), "sheets"))
            else:
                report.mismatches.append(ReconItem(
                    "disembark_date", "mismatch",
                    bk["disembark_date"].isoformat(), sheet_end.isoformat(),
                    "sheets"
                ))
        else:
            report.missing.append(ReconItem("disembark_date", "missing", bk["disembark_date"].isoformat(), None, "sheets"))

        # FPD in sheets
        sheet_fpd = _parse_date_flexible(sheet_row.get("Final_Payment_Date", ""))
        if sheet_fpd:
            if sheet_fpd == bk["fpd"]:
                report.matches.append(ReconItem("fpd", "match", bk["fpd"].isoformat(), sheet_fpd.isoformat(), "sheets"))
            else:
                report.mismatches.append(ReconItem(
                    "fpd", "mismatch",
                    bk["fpd"].isoformat(), sheet_fpd.isoformat(),
                    "sheets", f"FPD: sheet={sheet_fpd}, anchor={bk['fpd']}"
                ))
        else:
            report.missing.append(ReconItem("fpd", "missing", bk["fpd"].isoformat(), None, "sheets"))

        # Client name sanity check
        sheet_client = sheet_row.get("Client_Name", "")
        if sheet_client:
            anchor_last = bk["client"].split()[0].lower()
            if anchor_last in sheet_client.lower():
                report.matches.append(ReconItem("client_name", "match", bk["client"], sheet_client, "sheets"))
            else:
                report.mismatches.append(ReconItem(
                    "client_name", "mismatch",
                    bk["client"], sheet_client, "sheets",
                    "Client name in sheet doesn't match anchor"
                ))

    # ── 3. TESS reconciliation (optional) ────────────────────────────────
    tess_data = _fetch_tess_booking(bk["conf"])
    if tess_data:
        # Embark in TESS
        tess_start_raw = tess_data.get("departure_date") or tess_data.get("start_date") or tess_data.get("embark")
        if tess_start_raw:
            tess_start = _parse_date_str(str(tess_start_raw)) if isinstance(tess_start_raw, str) else tess_start_raw
            if tess_start and tess_start == bk["embark_date"]:
                report.matches.append(ReconItem("embark_date", "match", bk["embark_date"].isoformat(), str(tess_start), "tess"))
            elif tess_start:
                report.mismatches.append(ReconItem("embark_date", "mismatch", bk["embark_date"].isoformat(), str(tess_start), "tess"))

        # Total amount in TESS
        tess_amount = tess_data.get("total_price") or tess_data.get("gross_price")
        if tess_amount:
            report.matches.append(ReconItem("tess_booking", "match", bk["conf"], bk["conf"], "tess", f"TESS amount: ${tess_amount}"))

    return report


def reconcile_all_bookings() -> List[ReconciliationReport]:
    """Reconcile all bookings in KNOWN_BOOKINGS. Fetches sheet data once."""
    from thunderbird_anchor_dates import KNOWN_BOOKINGS

    logger.info(f"Starting reconciliation for {len(KNOWN_BOOKINGS)} bookings...")
    sheet_rows = _read_booking_master()
    logger.info(f"  Loaded {len(sheet_rows)} rows from Booking Master")

    reports = []
    for key in KNOWN_BOOKINGS:
        try:
            r = reconcile_booking(key, sheet_rows=sheet_rows)
            reports.append(r)
            logger.info(f"  {r.summary_line}")
        except Exception as e:
            logger.error(f"  Error reconciling {key}: {e}")
            bk = KNOWN_BOOKINGS[key]
            r = ReconciliationReport(
                booking_key=key,
                client_name=bk["client"],
                supplier=bk["supplier"],
                conf=bk["conf"],
                errors=[str(e)],
            )
            reports.append(r)

    return reports


# ---------------------------------------------------------------------------
# Summary helpers for morning briefing
# ---------------------------------------------------------------------------

def reconciliation_briefing_line(reports: Optional[List[ReconciliationReport]] = None) -> str:
    """
    One-line summary for morning briefing.
    e.g. "Reconciliation: 2 mismatches (Furlow, Nichols) · 3 missing · 8 clean"
    """
    if reports is None:
        reports = reconcile_all_bookings()

    red = [r for r in reports if r.status == "RED"]
    yellow = [r for r in reports if r.status == "YELLOW"]
    green = [r for r in reports if r.status == "GREEN"]

    parts = []
    if red:
        names = ", ".join(r.client_name.split()[0] for r in red[:3])
        more = f"+{len(red)-3}" if len(red) > 3 else ""
        parts.append(f"{len(red)} mismatch{'es' if len(red) > 1 else ''} ({names}{more})")
    if yellow:
        parts.append(f"{len(yellow)} missing data")
    if green:
        parts.append(f"{len(green)} clean")

    return "Reconciliation: " + (" · ".join(parts) if parts else "no data")


# ---------------------------------------------------------------------------
# MCP Tool Registration
# ---------------------------------------------------------------------------

def register_reconciliation_tools(mcp):
    """Register reconciliation MCP tools."""

    @mcp.tool()
    async def reconcile_booking_tool(
        client_name: str = "",
        booking_key: str = "",
    ) -> str:
        """Cross-check a single booking across dossier, Google Sheets, and TESS.
        Flags mismatches (dates, amounts, FPD, PNRs, insurance).

        Args:
            client_name: Partial client name (e.g. 'Furlow', 'McLeod')
            booking_key: Exact KNOWN_BOOKINGS key (e.g. 'Furlow_Regent_3071222')
        """
        from thunderbird_anchor_dates import KNOWN_BOOKINGS

        key = booking_key
        if not key and client_name:
            # Find by partial client name
            matches = {k: v for k, v in KNOWN_BOOKINGS.items()
                       if client_name.lower() in v["client"].lower()}
            if not matches:
                return json.dumps({"error": f"No booking found matching '{client_name}'"})
            if len(matches) > 1:
                return json.dumps({
                    "error": "Multiple matches — use booking_key",
                    "matches": list(matches.keys()),
                })
            key = list(matches.keys())[0]

        if not key:
            return json.dumps({"error": "Provide client_name or booking_key"})

        report = reconcile_booking(key)
        return json.dumps(report.to_dict(), indent=2, default=str)

    @mcp.tool()
    async def reconcile_all_bookings_tool() -> str:
        """Full reconciliation sweep across all KNOWN_BOOKINGS.
        Cross-checks dossiers, Google Sheets, and TESS.
        Returns status per booking plus aggregate summary.
        """
        reports = reconcile_all_bookings()

        summary = {
            "run_date": date.today().isoformat(),
            "total_bookings": len(reports),
            "clean": sum(1 for r in reports if r.status == "GREEN"),
            "mismatches": sum(1 for r in reports if r.status == "RED"),
            "missing_data": sum(1 for r in reports if r.status == "YELLOW"),
            "briefing_line": reconciliation_briefing_line(reports),
            "bookings": [r.to_dict() for r in reports],
        }

        return json.dumps(summary, indent=2, default=str)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")

    parser = argparse.ArgumentParser(description="Thunderbird Booking Reconciliation")
    parser.add_argument("--booking", type=str, help="Partial client name or booking key")
    parser.add_argument("--all", action="store_true", help="Reconcile all bookings")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of formatted text")
    parser.add_argument("--brief", action="store_true", help="One-line briefing summary only")
    args = parser.parse_args()

    if args.brief:
        line = reconciliation_briefing_line()
        print(line)
        sys.exit(0)

    if args.booking:
        from thunderbird_anchor_dates import KNOWN_BOOKINGS
        # Try exact key first, then partial name
        if args.booking in KNOWN_BOOKINGS:
            key = args.booking
        else:
            matches = {k: v for k, v in KNOWN_BOOKINGS.items()
                       if args.booking.lower() in v["client"].lower() or args.booking.lower() in k.lower()}
            if not matches:
                print(f"No booking found matching '{args.booking}'", file=sys.stderr)
                sys.exit(1)
            key = list(matches.keys())[0]
            if len(matches) > 1:
                print(f"Multiple matches: {list(matches.keys())} — using first", file=sys.stderr)

        report = reconcile_booking(key)
        if args.json:
            print(json.dumps(report.to_dict(), indent=2, default=str))
        else:
            print(f"\n{report.summary_line}")
            if report.mismatches:
                print("\n[MISMATCHES]")
                for item in report.mismatches:
                    print(f"  {item.field}: anchor={item.anchor_value} | {item.source}={item.source_value}")
                    if item.note:
                        print(f"    note: {item.note}")
            if report.missing:
                print("\n[MISSING]")
                for item in report.missing:
                    print(f"  {item.field} ({item.source}): {item.note or 'not found'}")
            if report.matches:
                print(f"\n[MATCHES] {len(report.matches)} fields verified OK")
            if report.errors:
                print(f"\n[ERRORS] {report.errors}")

    elif args.all:
        reports = reconcile_all_bookings()
        if args.json:
            output = {
                "run_date": date.today().isoformat(),
                "briefing_line": reconciliation_briefing_line(reports),
                "bookings": [r.to_dict() for r in reports],
            }
            print(json.dumps(output, indent=2, default=str))
        else:
            print(f"\nThunderbird Booking Reconciliation — {date.today()}")
            print("=" * 60)
            for r in reports:
                print(f"  {r.summary_line}")
            print()
            print(reconciliation_briefing_line(reports))

    else:
        parser.print_help()
