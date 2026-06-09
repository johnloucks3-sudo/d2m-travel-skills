"""
Harlan A9 — Booking Master Sheet Reader
core/finance/harlan_booking_master.py

Ground truth for all booking financials. Reading directly from the
Google Sheet so Harlan can verify numbers even when PDFs aren't accessible.

Sheet: EARA D2M Thunderbird v2 → 'Booking Master' tab
ID: 1GFjUe8RvP-GT4YHGn0DYv_BEAZGXlYfwEicFrm8ANuU

Usage:
    from core.finance.harlan_booking_master import HarlanBookingMaster

    hbm = HarlanBookingMaster()
    row = hbm.lookup_by_confirmation('3096289')
    row = hbm.lookup_by_client('McLeod')
    rows = hbm.get_all_active()
    report = hbm.harlan_verify('3096289')  # full sign-off block

CLI:
    python3 core/finance/harlan_booking_master.py --conf 3096289
    python3 core/finance/harlan_booking_master.py --client McLeod
    python3 core/finance/harlan_booking_master.py --all
    python3 core/finance/harlan_booking_master.py --fpd-alerts
"""

import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

THUNDERBIRD = Path(__file__).resolve().parent.parent.parent
SHEET_ID = "1GFjUe8RvP-GT4YHGn0DYv_BEAZGXlYfwEicFrm8ANuU"
SHEET_TAB = "Booking Master"
TOKEN_PATH = THUNDERBIRD / "creds" / "drive_token.json"

# Column name → index mapping (built dynamically from header row)
# But we need these key columns
FINANCIAL_COLS = [
    "Total_Cost", "Commission", "D2M Share",
    "Amount_Paid", "Balance_Due",
    "Payment_Due_Date", "Final_Payment_Date",
]
KEY_COLS = ["Client_Name", "Confirmation_Number", "Status", "Supplier",
            "Start_Date", "End_Date", "Trip_Name"] + FINANCIAL_COLS


class HarlanBookingMaster:
    """Read-only access to the Booking Master Google Sheet for financial verification."""

    def __init__(self):
        self._rows: list[dict] = []
        self._loaded = False
        self._load_error: str | None = None

    def _get_service(self):
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from google.auth.transport.requests import Request

        creds_data = json.loads(TOKEN_PATH.read_text())
        creds = Credentials(
            token=creds_data.get("token"),
            refresh_token=creds_data.get("refresh_token"),
            token_uri=creds_data.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=creds_data.get("client_id"),
            client_secret=creds_data.get("client_secret"),
            scopes=creds_data.get("scopes", []),
        )
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        return build("sheets", "v4", credentials=creds)

    def load(self) -> bool:
        """Load all rows from the sheet. Returns True on success."""
        try:
            service = self._get_service()
            result = service.spreadsheets().values().get(
                spreadsheetId=SHEET_ID,
                range=f"'{SHEET_TAB}'!A1:AZ200",
            ).execute()
            raw = result.get("values", [])
            if not raw:
                self._load_error = "Sheet returned no data"
                return False

            headers = raw[0]
            col_idx = {h: i for i, h in enumerate(headers)}

            self._rows = []
            for row in raw[1:]:
                def g(col):
                    i = col_idx.get(col, -1)
                    return row[i].strip() if i >= 0 and i < len(row) else ""

                record = {col: g(col) for col in headers}
                record["_col_idx"] = col_idx
                self._rows.append(record)

            self._loaded = True
            return True

        except Exception as e:
            self._load_error = str(e)
            return False

    def _ensure_loaded(self):
        if not self._loaded:
            self.load()

    def lookup_by_confirmation(self, conf: str) -> list[dict]:
        """Return all rows matching a confirmation number. May return multiple (duplicates)."""
        self._ensure_loaded()
        conf = str(conf).strip()
        return [r for r in self._rows if r.get("Confirmation_Number", "").strip() == conf]

    def lookup_by_client(self, name: str) -> list[dict]:
        """Return rows where client name contains the search term (case-insensitive)."""
        self._ensure_loaded()
        name_lower = name.lower()
        return [r for r in self._rows
                if name_lower in r.get("Client_Name", "").lower()
                and r.get("Status", "") not in ("ARCHIVED", "Cancelled", "")]

    def get_all_active(self) -> list[dict]:
        """Return all non-archived rows with a confirmation number."""
        self._ensure_loaded()
        return [r for r in self._rows
                if r.get("Confirmation_Number")
                and r.get("Status", "") not in ("ARCHIVED", "Cancelled", "")
                and "DUPLICATE" not in r.get("Status", "")]

    def _clean_amount(self, val: str) -> float | None:
        """Parse '$1,234.56' or '1234.56' to float."""
        if not val:
            return None
        cleaned = val.replace("$", "").replace(",", "").strip()
        try:
            return float(cleaned)
        except ValueError:
            return None

    def harlan_verify(self, conf: str, as_of: str | None = None) -> dict:
        """
        Full Harlan financial verification block for a booking confirmation number.

        Returns:
            {
                'conf': str,
                'found': bool,
                'rows': list[dict],          # raw sheet rows (may be multiple)
                'canonical': dict,            # best/most recent row
                'total_cost': float|None,
                'amount_paid': float|None,
                'balance_due': float|None,
                'commission': float|None,
                'd2m_share': float|None,
                'fpd': str,
                'status': str,
                'harlan_signoff': str,        # ready-to-paste sign-off line
                'warning': str|None,          # data quality issues
            }
        """
        as_of = as_of or date.today().isoformat()
        rows = self.lookup_by_confirmation(conf)

        if not rows:
            return {
                "conf": conf,
                "found": False,
                "rows": [],
                "canonical": {},
                "harlan_signoff": f"NOT FOUND in Booking Master (conf={conf}). Verify against invoice or portal.",
                "warning": "Confirmation not in sheet",
            }

        # Pick canonical row: prefer non-DUPLICATE, non-NEXION, with actual financial data
        def row_score(r):
            score = 0
            if "DUPLICATE" in r.get("Status", ""):
                score -= 10
            if r.get("Client_Name", "").upper() in ("NEXION LLC", "CRUISES AND TOURS UNLIMITED"):
                score -= 3
            if r.get("Total_Cost") and r.get("Total_Cost") not in ("0", "$0.00", ""):
                score += 5
            if r.get("Balance_Due") not in ("", "0"):
                score += 2
            if r.get("Final_Payment_Date"):
                score += 2
            return score

        canonical = sorted(rows, key=row_score, reverse=True)[0]

        total = self._clean_amount(canonical.get("Total_Cost", ""))
        paid = self._clean_amount(canonical.get("Amount_Paid", ""))
        balance = self._clean_amount(canonical.get("Balance_Due", ""))
        commission = self._clean_amount(canonical.get("Commission", ""))
        d2m = self._clean_amount(canonical.get("D2M Share", ""))
        fpd = canonical.get("Final_Payment_Date", "") or canonical.get("Payment_Due_Date", "")
        status = canonical.get("Status", "")
        client = canonical.get("Client_Name", "")

        # Derive payment status
        if balance is not None and balance <= 0:
            pay_status = "PAID IN FULL"
        elif total and paid and total > 0:
            pct = (paid / total) * 100 if total else 0
            pay_status = f"PARTIAL ({pct:.0f}% paid, ${balance or 0:,.2f} remaining)"
        else:
            pay_status = "UNKNOWN"

        # Build sign-off
        parts = []
        if total is not None:
            parts.append(f"total=${total:,.2f}")
        if balance is not None:
            parts.append(f"balance=${balance:,.2f}")
        if fpd:
            parts.append(f"FPD={fpd}")
        if commission is not None:
            parts.append(f"commission=${commission:,.2f}")

        warning = None
        if len(rows) > 1:
            non_dup = [r for r in rows if "DUPLICATE" not in r.get("Status", "")]
            if len(non_dup) > 1:
                warning = f"{len(rows)} rows found for {conf} — data may be inconsistent"

        signoff = (
            f"Harlan A9 CONFIRMED: conf={conf} | {pay_status} | "
            + " | ".join(parts)
            + f" | source: Booking Master Google Sheet as of {as_of}"
        )
        if warning:
            signoff += f" | ⚠️ {warning}"

        return {
            "conf": conf,
            "found": True,
            "rows": rows,
            "canonical": canonical,
            "client": client,
            "total_cost": total,
            "amount_paid": paid,
            "balance_due": balance,
            "commission": commission,
            "d2m_share": d2m,
            "fpd": fpd,
            "status": pay_status,
            "harlan_signoff": signoff,
            "warning": warning,
        }

    def fpd_alerts(self, days_ahead: int = 60) -> list[dict]:
        """Return rows where FPD falls within days_ahead, sorted by urgency."""
        self._ensure_loaded()
        today = date.today()
        alerts = []
        for row in self._rows:
            if "DUPLICATE" in row.get("Status", ""):
                continue
            fpd_str = row.get("Final_Payment_Date") or row.get("Payment_Due_Date", "")
            if not fpd_str or fpd_str in ("TBD", ""):
                continue
            # Parse various date formats
            for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%-m/%-d/%Y"):
                try:
                    fpd_date = datetime.strptime(fpd_str.strip(), fmt).date()
                    days = (fpd_date - today).days
                    if 0 <= days <= days_ahead:
                        balance = self._clean_amount(row.get("Balance_Due", ""))
                        if balance and balance > 0:
                            alerts.append({
                                "client": row.get("Client_Name", ""),
                                "conf": row.get("Confirmation_Number", ""),
                                "fpd": fpd_str,
                                "days_until": days,
                                "balance_due": balance,
                                "supplier": row.get("Supplier", ""),
                                "status": row.get("Status", ""),
                            })
                    break
                except ValueError:
                    continue
        return sorted(alerts, key=lambda x: x["days_until"])


# ── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Harlan A9 — Booking Master Lookup")
    parser.add_argument("--conf", help="Look up by confirmation number")
    parser.add_argument("--client", help="Look up by client name (partial match)")
    parser.add_argument("--all", action="store_true", help="Show all active bookings")
    parser.add_argument("--fpd-alerts", action="store_true", help="Show upcoming FPD alerts")
    parser.add_argument("--days", type=int, default=60, help="Days ahead for FPD alerts")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    hbm = HarlanBookingMaster()
    if not hbm.load():
        print(f"❌ Failed to load Booking Master: {hbm._load_error}")
        sys.exit(1)

    if args.conf:
        result = hbm.harlan_verify(args.conf)
        if args.json:
            result.pop("rows", None); result.pop("canonical", None)
            print(json.dumps(result, indent=2, default=str))
        else:
            print(f"\n{'='*72}")
            print(f"HARLAN A9 — BOOKING MASTER VERIFICATION")
            print(f"Confirmation: {args.conf}")
            print(f"{'='*72}")
            if result["found"]:
                print(f"\nClient:     {result.get('client','?')}")
                print(f"Total:      ${result.get('total_cost',0):,.2f}" if result.get("total_cost") else "Total:      N/A")
                print(f"Balance:    ${result.get('balance_due',0):,.2f}" if result.get("balance_due") is not None else "Balance:    N/A")
                print(f"FPD:        {result.get('fpd','—')}")
                print(f"Commission: ${result.get('commission',0):,.2f}" if result.get("commission") else "Commission: N/A")
                print(f"Status:     {result.get('status','?')}")
                if result.get("warning"):
                    print(f"\n⚠️  {result['warning']}")
                print(f"\n✅ SIGN-OFF:\n   {result['harlan_signoff']}")
            else:
                print(f"\n❌ NOT FOUND: {result['harlan_signoff']}")
            print(f"{'='*72}\n")

    elif args.client:
        rows = hbm.lookup_by_client(args.client)
        print(f"\n{len(rows)} row(s) for '{args.client}':")
        for r in rows:
            print(f"  {r.get('Confirmation_Number','?'):12s} | {r.get('Client_Name','?'):40s} | "
                  f"total={r.get('Total_Cost','?'):12s} | bal={r.get('Balance_Due','?'):12s} | "
                  f"fpd={r.get('Final_Payment_Date','?')}")

    elif args.all:
        rows = hbm.get_all_active()
        print(f"\n{len(rows)} active bookings:\n")
        print(f"{'Confirmation':14s} {'Client':35s} {'Total':12s} {'Balance':12s} {'FPD':14s} Status")
        print("-" * 100)
        for r in rows:
            print(f"{r.get('Confirmation_Number',''):14s} "
                  f"{r.get('Client_Name','')[:35]:35s} "
                  f"{r.get('Total_Cost',''):12s} "
                  f"{r.get('Balance_Due',''):12s} "
                  f"{r.get('Final_Payment_Date',''):14s} "
                  f"{r.get('Status','')}")

    elif args.fpd_alerts:
        alerts = hbm.fpd_alerts(days_ahead=args.days)
        print(f"\nFPD ALERTS — next {args.days} days:\n")
        if not alerts:
            print("  None.")
        for a in alerts:
            level = "🔴" if a["days_until"] <= 30 else "🟡" if a["days_until"] <= 45 else "🟠"
            print(f"  {level} {a['days_until']:3d}d | {a['client']:35s} | conf={a['conf']:12s} | "
                  f"${a['balance_due']:,.2f} | FPD {a['fpd']}")
    else:
        parser.print_help()
