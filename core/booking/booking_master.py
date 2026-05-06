"""
Booking Master Google Sheet client.

Source of truth for ALL D2M bookings — including those not yet in TESS.
Mirrors the TESSClient surface area so callers can use either backend
interchangeably.

Sheet:  1GFjUe8RvP-GT4YHGn0DYv_BEAZGXlYfwEicFrm8ANuU
Tab:    "Booking Master"
Auth:   service account `dreams2memories@d2m-python-pipeline.iam.gserviceaccount.com`

NOTE on credentials path: the service account JSON lives at
`/home/john/Thunderbird/.service_account_gemini.json`.

`thunderbird_email_intel.py` references `credentials.json`, but on disk that
file is the OAuth installed-app secret, not a service account — gspread fails
on it. `.service_account_gemini.json` carries the actual service-account key
for `dreams2memories@d2m-python-pipeline.iam.gserviceaccount.com`. We use it
directly; if a real `credentials.json` service account ever lands at the
canonical path, the constructor will prefer it.
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Any, Iterable

import gspread
from google.oauth2 import service_account

logger = logging.getLogger(__name__)

# ----- constants -----------------------------------------------------------

SHEETS_ID = "1GFjUe8RvP-GT4YHGn0DYv_BEAZGXlYfwEicFrm8ANuU"
BOOKING_MASTER_TAB = "Booking Master"

THUNDERBIRD_DIR = Path(__file__).resolve().parents[2]

# Try the canonical name first; fall back to the working SA file we verified.
_CRED_CANDIDATES = [
    THUNDERBIRD_DIR / "credentials.json",
    THUNDERBIRD_DIR / ".service_account_gemini.json",
    Path("/home/john/Personal/Credentials/credentials.json"),
]

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]


# ----- helpers --------------------------------------------------------------

_MONEY_RE = re.compile(r"-?\$?\s*([\d,]+(?:\.\d+)?)")


def _parse_money(value: Any) -> float:
    """Best-effort dollar-string parser. Returns 0.0 on anything unparseable.

    Tolerates: '$13,398.00', '13398', '$0.00', '', None, 'Confirmed', numbers.
    """
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if not s:
        return 0.0
    m = _MONEY_RE.search(s.replace(",", ""))
    if not m:
        return 0.0
    try:
        return float(m.group(1).replace(",", ""))
    except ValueError:
        return 0.0


_DATE_FORMATS = (
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%-m/%-d/%Y",
    "%d-%b-%y",
    "%d-%b-%Y",
    "%b %d, %Y",
    "%B %d, %Y",
)


def _parse_date(value: Any) -> date | None:
    """Parse the messy date strings the sheet emits. Return None on failure."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    s = str(value).strip()
    if not s:
        return None
    # Strip time component if present (e.g. '2/16/2026 23:10:56')
    s = s.split()[0]
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    # Try generic m/d/yyyy with single digits
    try:
        parts = s.split("/")
        if len(parts) == 3:
            m, d, y = (int(p) for p in parts)
            if y < 100:
                y += 2000
            return date(y, m, d)
    except (ValueError, TypeError):
        pass
    return None


# Known D2M client surnames — used as anchors when a name string is messy
# (e.g. "MR ERIK WIEDENBACH MC LEOD" or "MELISSA MC GLASSON"). If any anchor
# appears as a substring (lowercased, non-alpha-stripped), it wins.
_CLIENT_SURNAMES = (
    "mcleod",
    "mcglasson",
    "kuklinski",
    "loucks",
    "furlow",
    "nichols",
    "ely",
    "darrow",
    "westbrook",
    "lyons",
    "britan",
)

# Tokens that are clearly NOT a surname even if they appear last
_NAME_NOISE = {
    "mr", "mrs", "ms", "dr", "col", "and", "the", "llc", "inc",
    "guest", "declined", "host", "agency", "agent", "client",
    "unlimited", "tours", "cruises", "travel", "nexion", "confirmation",
    "pending", "tbd",
}


def _norm_name(name: str) -> str:
    """Best-effort surname extraction.

    Strategy:
      1. Lowercase the whole string with non-alpha chars stripped to spaces;
         collapse multi-word surnames like "MC LEOD" -> "mcleod".
      2. If any known D2M client surname appears as a substring, return it.
      3. Otherwise, return the last token that isn't an honorific or noise word.
      4. Fallback: empty string.
    """
    if not name:
        return ""
    raw = re.sub(r"[^a-zA-Z]+", " ", str(name)).lower().strip()
    if not raw:
        return ""
    # Collapse "mc leod" / "mac donald" splits
    collapsed = re.sub(r"\b(mc|mac)\s+([a-z]+)", r"\1\2", raw)
    no_space = collapsed.replace(" ", "")
    # 1. anchor on known surnames
    for surname in _CLIENT_SURNAMES:
        if surname in no_space:
            return surname
    # 2. last meaningful token
    parts = [p for p in collapsed.split() if p and p not in _NAME_NOISE]
    if parts:
        # Prefer tokens >=3 chars to avoid "co" / "jr"
        long_parts = [p for p in parts if len(p) >= 3]
        return (long_parts or parts)[-1]
    return ""


def _resolve_credentials_path(path: str | os.PathLike[str] | None) -> Path:
    if path:
        p = Path(path)
        if p.exists():
            return p
        raise FileNotFoundError(f"Credentials file not found: {p}")
    for cand in _CRED_CANDIDATES:
        if not cand.exists():
            continue
        # Ensure it's a real service account (not OAuth installed-app)
        try:
            with open(cand) as f:
                data = json.load(f)
            if data.get("type") == "service_account":
                return cand
        except (OSError, json.JSONDecodeError):
            continue
    raise FileNotFoundError(
        "No service-account credentials found. Tried: "
        + ", ".join(str(c) for c in _CRED_CANDIDATES)
    )


# ----- client ---------------------------------------------------------------


class BookingMasterClient:
    """Read-only client for the D2M Booking Master Google Sheet."""

    def __init__(
        self,
        sheet_id: str = SHEETS_ID,
        tab: str = BOOKING_MASTER_TAB,
        credentials_path: str | os.PathLike[str] | None = None,
    ):
        self.sheet_id = sheet_id
        self.tab = tab
        self._creds_path = _resolve_credentials_path(credentials_path)
        self._gc: gspread.Client | None = None
        self._cache: list[dict[str, Any]] | None = None

    # -- internals ----------------------------------------------------------

    def _client(self) -> gspread.Client:
        if self._gc is None:
            creds = service_account.Credentials.from_service_account_file(
                str(self._creds_path), scopes=SCOPES
            )
            self._gc = gspread.authorize(creds)
        return self._gc

    def _worksheet(self):
        return self._client().open_by_key(self.sheet_id).worksheet(self.tab)

    # -- public API ---------------------------------------------------------

    def list_bookings(self, refresh: bool = False) -> list[dict[str, Any]]:
        """Return all rows from Booking Master tab as list of dicts.

        Cached after first call; pass refresh=True to force re-fetch.
        """
        if self._cache is not None and not refresh:
            return self._cache
        ws = self._worksheet()
        rows = ws.get_all_records()
        # Annotate with parsed helpers for downstream consumers.
        for row in rows:
            row["_parsed_start_date"] = _parse_date(row.get("Start_Date"))
            row["_parsed_end_date"] = _parse_date(row.get("End_Date"))
            row["_parsed_total_cost"] = _parse_money(row.get("Total_Cost"))
            row["_parsed_commission"] = _parse_money(row.get("Commission"))
            row["_parsed_d2m_share"] = _parse_money(row.get("D2M Share"))
            row["_parsed_amount_paid"] = _parse_money(row.get("Amount_Paid"))
            row["_parsed_balance_due"] = _parse_money(row.get("Balance_Due"))
        self._cache = rows
        logger.info("Booking Master: %d rows loaded", len(rows))
        return rows

    def get_by_client(self, client_name: str) -> list[dict[str, Any]]:
        """Filter bookings by client name (case-insensitive substring match).

        Also matches Notes column and Traveler_*_Name columns so the
        NEXION LLC host-agency wrapper rows still surface for "McLeod".
        """
        if not client_name:
            return []
        needle = client_name.strip().lower()
        out: list[dict[str, Any]] = []
        search_cols = (
            "Client_Name",
            "Notes",
            "Lead_Traveler",
            "Traveler_2_Name",
            "Traveler_3_Name",
            "Traveler_4_Name",
        )
        for row in self.list_bookings():
            for col in search_cols:
                val = str(row.get(col, "") or "").lower()
                if needle in val:
                    out.append(row)
                    break
        return out

    def commission_summary(self) -> dict[str, Any]:
        """Aggregate commission totals across all rows.

        Returns:
          {
            total_expected: float,        # sum of Commission column
            total_d2m_share: float,       # sum of D2M Share column
            total_received: float,        # sum of Amount_Paid (client payments)
            total_due: float,             # sum of Balance_Due
            booking_count: int,
            by_supplier: {supplier: {expected, share, count}},
            by_client:   {client:   {expected, share, count}},
          }

        NOTE: "received" here = client payments (Amount_Paid), not commission
        actually paid out by the supplier — the sheet doesn't track the
        latter. TESS is the source of truth for paid commission.
        """
        bookings = self.list_bookings()
        totals = {
            "total_expected": 0.0,
            "total_d2m_share": 0.0,
            "total_received": 0.0,
            "total_due": 0.0,
            "booking_count": len(bookings),
            "by_supplier": {},
            "by_client": {},
        }
        for row in bookings:
            comm = row["_parsed_commission"]
            share = row["_parsed_d2m_share"]
            paid = row["_parsed_amount_paid"]
            due = row["_parsed_balance_due"]

            totals["total_expected"] += comm
            totals["total_d2m_share"] += share
            totals["total_received"] += paid
            totals["total_due"] += due

            supplier = (row.get("Supplier") or "Unknown").strip() or "Unknown"
            client = (row.get("Client_Name") or "Unknown").strip() or "Unknown"

            sb = totals["by_supplier"].setdefault(
                supplier, {"expected": 0.0, "share": 0.0, "count": 0}
            )
            sb["expected"] += comm
            sb["share"] += share
            sb["count"] += 1

            cb = totals["by_client"].setdefault(
                client, {"expected": 0.0, "share": 0.0, "count": 0}
            )
            cb["expected"] += comm
            cb["share"] += share
            cb["count"] += 1

        # Round for readability
        for k in ("total_expected", "total_d2m_share", "total_received", "total_due"):
            totals[k] = round(totals[k], 2)
        for bucket in (totals["by_supplier"], totals["by_client"]):
            for v in bucket.values():
                v["expected"] = round(v["expected"], 2)
                v["share"] = round(v["share"], 2)
        return totals

    def upcoming_voyages(self, today: date | None = None) -> list[dict[str, Any]]:
        """Filter to bookings with start_date >= today, sorted by start_date."""
        cutoff = today or date.today()
        upcoming = [
            row
            for row in self.list_bookings()
            if row["_parsed_start_date"] and row["_parsed_start_date"] >= cutoff
        ]
        upcoming.sort(key=lambda r: r["_parsed_start_date"])
        return upcoming

    # -- TESS cross-reference ----------------------------------------------

    @staticmethod
    def _tess_booking_keys(t: dict[str, Any]) -> dict[str, Any]:
        """Pull common identifiers from a TESS booking dict.

        TESS uses CamelCase keys; we look for the most common ones and tolerate
        absence (different endpoints return different shapes).
        """
        booking_no = (
            t.get("BookingNumber")
            or t.get("BookingNo")
            or t.get("ConfirmationNumber")
            or t.get("VendorConfirmationNumber")
            or ""
        )
        client = (
            t.get("ClientName")
            or t.get("PrimaryTravelerName")
            or t.get("LeadTravelerName")
            or ""
        )
        start = (
            t.get("StartDate")
            or t.get("DepartureDate")
            or t.get("BeginDate")
            or t.get("BookingDate")
            or None
        )
        return {
            "booking_no": str(booking_no).strip(),
            "client": str(client).strip(),
            "start_date": _parse_date(start),
            "raw": t,
        }

    def cross_reference_with_tess(
        self, tess_bookings: Iterable[dict[str, Any]]
    ) -> dict[str, list[dict[str, Any]]]:
        """Match Booking Master rows against TESS booking records.

        Match strategy (tiered):
          1. Exact match on Confirmation_Number / Booking_ID
          2. Surname token match + start_date within ±3 days

        Returns:
          {
            matched:        [{sheet_row, tess_record, match_type}],
            only_in_sheet:  [sheet_row, ...],
            only_in_tess:   [tess_record, ...],
          }
        """
        sheet_rows = self.list_bookings()
        tess_list = [self._tess_booking_keys(t) for t in tess_bookings]

        matched: list[dict[str, Any]] = []
        used_tess_idx: set[int] = set()
        unmatched_sheet: list[dict[str, Any]] = []

        for row in sheet_rows:
            sheet_conf = str(row.get("Confirmation_Number") or "").strip()
            sheet_book = str(row.get("Booking_ID") or "").strip()
            sheet_ids = {x for x in (sheet_conf, sheet_book) if x}
            sheet_start = row["_parsed_start_date"]
            sheet_surname = _norm_name(row.get("Client_Name") or "")
            # Also try last names from traveler columns and Notes (covers
            # NEXION LLC wrapper rows where Notes = "Client: Erik McLeod ...")
            extra_names = [
                row.get("Lead_Traveler"),
                row.get("Traveler_2_Name"),
                row.get("Traveler_3_Name"),
                row.get("Traveler_4_Name"),
                row.get("Notes"),
            ]
            surname_set = {sheet_surname} if sheet_surname else set()
            for n in extra_names:
                ns = _norm_name(str(n or ""))
                if ns:
                    surname_set.add(ns)

            match: tuple[int, str] | None = None  # (idx, match_type)

            # Tier 1: ID exact match
            if sheet_ids:
                for i, t in enumerate(tess_list):
                    if i in used_tess_idx:
                        continue
                    if t["booking_no"] and t["booking_no"] in sheet_ids:
                        match = (i, "id_exact")
                        break

            # Tier 2: surname + date proximity
            if match is None and sheet_start and surname_set:
                for i, t in enumerate(tess_list):
                    if i in used_tess_idx:
                        continue
                    t_surname = _norm_name(t["client"])
                    if not t_surname or t_surname not in surname_set:
                        continue
                    if not t["start_date"]:
                        continue
                    if abs((t["start_date"] - sheet_start).days) <= 3:
                        match = (i, "surname_date")
                        break

            if match:
                idx, mtype = match
                used_tess_idx.add(idx)
                matched.append(
                    {
                        "sheet_row": row,
                        "tess_record": tess_list[idx]["raw"],
                        "match_type": mtype,
                    }
                )
            else:
                unmatched_sheet.append(row)

        only_in_tess = [
            tess_list[i]["raw"]
            for i in range(len(tess_list))
            if i not in used_tess_idx
        ]

        return {
            "matched": matched,
            "only_in_sheet": unmatched_sheet,
            "only_in_tess": only_in_tess,
        }


# ----- singleton convenience -----------------------------------------------

_default_client: BookingMasterClient | None = None


def get_booking_master_client() -> BookingMasterClient:
    """Get/create singleton BookingMasterClient."""
    global _default_client
    if _default_client is None:
        _default_client = BookingMasterClient()
    return _default_client


# ----- CLI smoke test ------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    client = BookingMasterClient()
    rows = client.list_bookings()
    print(f"Loaded {len(rows)} bookings.")
    if rows:
        cols = [c for c in rows[0].keys() if not c.startswith("_")]
        print(f"{len(cols)} columns. First 5: {cols[:5]}")
    summary = client.commission_summary()
    print(
        f"Commission expected: ${summary['total_expected']:,.2f}  "
        f"D2M share: ${summary['total_d2m_share']:,.2f}  "
        f"Bookings: {summary['booking_count']}"
    )
    upcoming = client.upcoming_voyages()
    print(f"Upcoming voyages: {len(upcoming)}")
