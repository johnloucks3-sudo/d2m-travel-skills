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
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
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

    # -- write operations ---------------------------------------------------

    def _get_headers(self) -> list[str]:
        """Return the header row from the sheet (row 1)."""
        ws = self._worksheet()
        return ws.row_values(1)

    def add_booking(self, data: dict[str, Any]) -> int:
        """Append a new booking row. Keys must match column headers.

        Returns the 1-based row index of the new row.
        """
        ws = self._worksheet()
        headers = self._get_headers()
        row = [str(data.get(h, "")) for h in headers]
        ws.append_row(row, value_input_option="USER_ENTERED")
        self._cache = None  # invalidate cache
        return ws.row_count  # approximate — last row after append

    def update_booking(
        self,
        booking_id: str,
        updates: dict[str, Any],
        match_col: str = "Booking_ID",
    ) -> bool:
        """Update fields on an existing booking row.

        Finds the row where match_col == booking_id and writes updates.
        Returns True if a row was found and updated, False otherwise.
        """
        ws = self._worksheet()
        headers = self._get_headers()

        try:
            col_idx = headers.index(match_col) + 1  # 1-based
        except ValueError:
            raise ValueError(f"Column '{match_col}' not found in sheet headers")

        # Find the row
        col_values = ws.col_values(col_idx)
        try:
            row_idx = col_values.index(booking_id) + 1  # 1-based (header is row 1)
        except ValueError:
            logger.warning("Booking_ID '%s' not found in column '%s'", booking_id, match_col)
            return False

        # Write each updated field
        for field, value in updates.items():
            if field not in headers:
                logger.warning("Column '%s' not in sheet — skipping", field)
                continue
            col = headers.index(field) + 1
            ws.update_cell(row_idx, col, str(value))

        self._cache = None  # invalidate cache
        logger.info("Updated booking '%s': %s", booking_id, list(updates.keys()))
        return True

    def get_booking_by_id(self, booking_id: str) -> dict[str, Any] | None:
        """Return the sheet row for a specific Booking_ID, or None."""
        for row in self.list_bookings():
            if str(row.get("Booking_ID", "")).strip() == str(booking_id).strip():
                return row
            if str(row.get("Confirmation_Number", "")).strip() == str(booking_id).strip():
                return row
        return None

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


# ----- CLI -----------------------------------------------------------------

if __name__ == "__main__":
    import argparse, sys

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="D2M Booking Master Sheet CLI")
    sub = parser.add_subparsers(dest="cmd")

    # list
    sub.add_parser("list", help="List all bookings (summary)")

    # query
    qp = sub.add_parser("query", help="Search by client name or booking ID")
    qp.add_argument("term", help="Name or booking ID to search")

    # get
    gp = sub.add_parser("get", help="Get one booking by ID")
    gp.add_argument("booking_id", help="Booking_ID or Confirmation_Number")

    # summary
    sub.add_parser("summary", help="Commission + pipeline totals")

    # upcoming
    sub.add_parser("upcoming", help="Upcoming voyages sorted by departure")

    # update
    up = sub.add_parser("update", help="Update fields on an existing booking")
    up.add_argument("booking_id", help="Booking_ID to update")
    up.add_argument("fields", nargs="+",
                    help="key=value pairs, e.g. Pre_Cruise_Hotel='Sina Palazzo'")

    # pulse — quick financial pulse for hale_state.json
    sub.add_parser("pulse", help="Emit JSON financial pulse block for hale_state.json")

    args = parser.parse_args()

    client = BookingMasterClient()

    if args.cmd == "list" or args.cmd is None:
        rows = client.list_bookings()
        print(f"{'Booking_ID':<20} {'Client_Name':<35} {'Supplier':<22} {'Start_Date':<12} {'Status'}")
        print("-" * 105)
        for r in rows:
            print(
                f"{str(r.get('Booking_ID','')):<20} "
                f"{str(r.get('Client_Name','')):<35} "
                f"{str(r.get('Supplier','')):<22} "
                f"{str(r.get('Start_Date','')):<12} "
                f"{r.get('Status','')}"
            )
        print(f"\n{len(rows)} bookings total.")

    elif args.cmd == "query":
        results = client.get_by_client(args.term)
        if not results:
            # Also try exact booking ID
            r = client.get_booking_by_id(args.term)
            results = [r] if r else []
        if not results:
            print(f"No results for '{args.term}'")
            sys.exit(1)
        for r in results:
            cols = [c for c in r.keys() if not c.startswith("_")]
            for c in cols:
                if r[c]:
                    print(f"  {c}: {r[c]}")
            print()

    elif args.cmd == "get":
        r = client.get_booking_by_id(args.booking_id)
        if not r:
            print(f"Not found: {args.booking_id}")
            sys.exit(1)
        cols = [c for c in r.keys() if not c.startswith("_")]
        for c in cols:
            if r[c]:
                print(f"  {c}: {r[c]}")

    elif args.cmd == "summary":
        s = client.commission_summary()
        print(f"Bookings: {s['booking_count']}")
        print(f"Commission expected: ${s['total_expected']:,.2f}")
        print(f"D2M share:           ${s['total_d2m_share']:,.2f}")
        print(f"Client paid:         ${s['total_received']:,.2f}")
        print(f"Balance due:         ${s['total_due']:,.2f}")
        print("\nBy supplier:")
        for sup, v in sorted(s["by_supplier"].items(), key=lambda x: -x[1]["share"]):
            print(f"  {sup:<30} expected ${v['expected']:>10,.2f}  D2M ${v['share']:>10,.2f}  ({v['count']} bookings)")

    elif args.cmd == "upcoming":
        rows = client.upcoming_voyages()
        print(f"{'Start_Date':<12} {'Client_Name':<35} {'Supplier':<22} {'Booking_ID'}")
        print("-" * 90)
        for r in rows:
            print(
                f"{str(r.get('Start_Date','')):<12} "
                f"{str(r.get('Client_Name','')):<35} "
                f"{str(r.get('Supplier','')):<22} "
                f"{r.get('Booking_ID','')}"
            )
        print(f"\n{len(rows)} upcoming voyages.")

    elif args.cmd == "update":
        updates: dict[str, str] = {}
        for kv in args.fields:
            if "=" not in kv:
                print(f"Bad field spec '{kv}' — use key=value", file=sys.stderr)
                sys.exit(1)
            k, _, v = kv.partition("=")
            updates[k.strip()] = v.strip().strip("'\"")
        ok = client.update_booking(args.booking_id, updates)
        if ok:
            print(f"Updated {args.booking_id}: {list(updates.keys())}")
        else:
            print(f"Booking '{args.booking_id}' not found.")
            sys.exit(1)

    elif args.cmd == "pulse":
        from datetime import datetime as dt
        rows = client.list_bookings()
        upcoming = client.upcoming_voyages()
        s = client.commission_summary()
        pulse = {
            "last_checked": dt.now().isoformat(),
            "sheet_status": "ONLINE",
            "sheet_bookings": len(rows),
            "sheet_commission_expected": s["total_expected"],
            "sheet_d2m_share": s["total_d2m_share"],
            "sheet_upcoming_count": len(upcoming),
            "pipeline_d2m_share_upcoming": round(
                sum(r["_parsed_d2m_share"] for r in upcoming), 2
            ),
            "pipeline_commission_upcoming": round(
                sum(r["_parsed_commission"] for r in upcoming), 2
            ),
        }
        pulse["total_d2m_pipeline"] = pulse["pipeline_d2m_share_upcoming"]
        pulse["raw_snippet"] = (
            f"D2M pipeline: ${pulse['pipeline_d2m_share_upcoming']:,.2f} D2M share "
            f"across {len(upcoming)} upcoming voyages (sheet)."
        )
        import json as _json
        print(_json.dumps(pulse, indent=2))
