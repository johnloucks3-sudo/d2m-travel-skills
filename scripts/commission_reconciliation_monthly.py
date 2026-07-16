#!/usr/bin/env python3
"""
Commission Reconciliation — Monthly
====================================
Dreams2Memories Travel, LLC | scripts/commission_reconciliation_monthly.py

Reconciles PROJECTED (Booking Master / expected) commissions against ACTUAL
commissions received in a target month, across three receipt sources:

    1. TESS API           — core.booking.thunderbird_tess.TESSClient.list_checks_received()
    2. OA partner payouts — config/oa_commission_ledger.json ("received" ledger,
                             populated from Outside Agents weekly statements)
    3. Manual entries     — config/manual_commission_entries.json (Harlan-entered
                             receipts not yet synced into TESS or the OA ledger)

Expected/projected commissions come from the Booking Master sheet via the
existing reader in core.booking.thunderbird_commission_recon.get_expected_commissions()
— reused rather than re-implemented, since that reader already handles the
sheet's column-naming variance.

NOTE ON SCOPE: this pipeline reconciles the MAGNITUDE of commissions that
DID arrive this month against what was expected for those same bookings.
It does not re-implement "commission never arrived" aging alerts — that is
already owned by scripts/commission_aging_pipeline.py (31d/60d dossier-based)
and core/ops/commission_watch.py (45d overdue). Duplicating that logic here
would create two sources of truth for the same alert; this script instead
flags magnitude discrepancies only.

Discrepancy rule: a matched booking is FLAGGED if
    abs(received - expected) > $100   OR   abs(received - expected) / expected > 5%
(either threshold alone is sufficient — see is_discrepancy()).

Output: output/Commission_Reconciliation_YYYY-MM.json
Email:  Gmail DRAFT (WF-17 hold, NOT sent) to johnloucks3@gmail.com, written in
        Harlan's (A9) voice via gmail_create_draft_sync — Commander/Harlan review
        before this becomes a settled financial claim, per this project's
        Phase-1 pipeline-integrity confidence-tagging discipline.

Systemd: commission-reconciliation-monthly.timer — 1st of month, 06:00 MT.

Usage:
    python3 scripts/commission_reconciliation_monthly.py                 # reconcile last full month, draft email
    python3 scripts/commission_reconciliation_monthly.py --month 2026-06 # explicit month
    python3 scripts/commission_reconciliation_monthly.py --dry-run       # no draft, report only
    python3 scripts/commission_reconciliation_monthly.py --local         # print to stdout, no draft
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date, datetime, timezone
from pathlib import Path

THUNDERBIRD = Path.home() / "Thunderbird"
sys.path.insert(0, str(THUNDERBIRD))

MANUAL_LEDGER = THUNDERBIRD / "config" / "manual_commission_entries.json"
OA_LEDGER = THUNDERBIRD / "config" / "oa_commission_ledger.json"
TESS_TOKEN = THUNDERBIRD / "tess_token.json"
OUTPUT_DIR = THUNDERBIRD / "output"
LOG_FILE = THUNDERBIRD / "logs" / "commission_reconciliation_monthly.log"

COMMANDER_INBOX = "johnloucks3@gmail.com"
VARIANCE_PCT_THRESHOLD = 5.0
VARIANCE_ABS_THRESHOLD = 100.0

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s COMMISSION-RECON %(levelname)s %(message)s",
)
logger = logging.getLogger("commission_reconciliation_monthly")


# ---------------------------------------------------------------------------
# Month bounds
# ---------------------------------------------------------------------------

def month_bounds(month_str: str) -> tuple[date, date]:
    """'2026-06' -> (2026-06-01, 2026-06-30)."""
    year, month = (int(x) for x in month_str.split("-"))
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    from datetime import timedelta
    return start, end - timedelta(days=1)


def previous_month_str(today: date | None = None) -> str:
    today = today or date.today()
    first_of_this_month = today.replace(day=1)
    from datetime import timedelta
    last_of_prev = first_of_this_month - timedelta(days=1)
    return f"{last_of_prev.year:04d}-{last_of_prev.month:02d}"


def _in_range(d: date | None, start: date, end: date) -> bool:
    return d is not None and start <= d <= end


def _parse_date(val) -> date | None:
    if not val:
        return None
    s = str(val).strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(s[: len(fmt) + 2], fmt).date()
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# PULL — TESS API (received commissions)
# ---------------------------------------------------------------------------

def pull_tess_received(start: date, end: date) -> list[dict]:
    """Pull CheckReceived records from TESS and normalize to the common receipt shape.

    Field names are best-effort — the CheckReceived Item schema isn't fully
    documented in this codebase (see core/booking/thunderbird_tess.py). Falls
    back across candidate key names rather than assuming one; skips items
    that don't parse instead of crashing the run.
    """
    if not TESS_TOKEN.exists():
        return []

    try:
        from core.booking.thunderbird_tess import TESSClient
        client = TESSClient()
        result = client.list_checks_received(page_size=200)
    except Exception as e:
        logger.warning(f"TESS pull failed: {e}")
        return []

    if "error" in result:
        logger.warning(f"TESS pull returned error: {result['error']}")
        return []

    # Verified against a live CheckReceived record (CheckID 605635, 2026-07-16):
    # the TESS list response does NOT expose a top-level BookingNumber — the
    # amount lives in Commission.TotalReceived/Received, the supplier is under
    # CheckFrom.TourOperatorName, and the payee under CheckTo.Name. A check can
    # aggregate several bookings (Commission.BookingCount), so the check itself
    # carries no single booking id; CheckNumber is its stable receipt id. The
    # previous mapping read the wrong paths and then dropped every record whose
    # (absent) top-level booking_ref was empty — silently discarding real
    # commission checks. Now: map from the real schema, and keep receipts that
    # lack a Booking Master ref so they surface as `unmatched` rather than vanish.
    normalized = []
    for item in result.get("Items", []):
        check_date = _parse_date(
            item.get("CheckDate") or item.get("PaymentDate") or item.get("CreatedDateTimeUTC")
        )
        if not _in_range(check_date, start, end):
            continue

        commission = item.get("Commission") or {}
        amount = (
            commission.get("TotalReceived")
            or commission.get("Received")
            or 0
        ) or 0

        check_from = item.get("CheckFrom") or {}
        check_to = item.get("CheckTo") or {}
        booking_ref = str(
            item.get("BookingNumber")
            or item.get("BookingID")
            or item.get("BookingReference")
            or item.get("CheckNumber")   # stable receipt id when no booking is exposed
            or ""
        ).strip()
        supplier = (
            check_from.get("TourOperatorName")
            or (item.get("TourOperator") or {}).get("TourOperatorName")
            or item.get("TourOperatorName")
            or ""
        )
        client_name = (
            check_to.get("Name")
            or item.get("ClientName")
            or (item.get("Client") or {}).get("Name")
            or ""
        )

        # Only skip zero-value receipts. A missing Booking Master ref is NOT a
        # reason to drop money that actually arrived — it becomes `unmatched`.
        if not amount:
            continue

        booking_count = commission.get("BookingCount")
        notes = f"CheckNumber {item.get('CheckNumber')}" if item.get("CheckNumber") else ""
        if booking_count and booking_count != 1:
            notes = (notes + f"; aggregates {booking_count} bookings").strip("; ")

        normalized.append({
            "source": "TESS",
            "booking_ref": booking_ref,
            "client_name": client_name,
            "supplier": supplier,
            "amount": round(float(amount), 2),
            "date": check_date.isoformat(),
            "notes": notes,
        })

    logger.info(f"TESS: {len(normalized)} received commissions in {start}..{end}")
    return normalized


# ---------------------------------------------------------------------------
# PULL — OA partner payouts (config/oa_commission_ledger.json)
# ---------------------------------------------------------------------------

def pull_oa_received(start: date, end: date, ledger_path: Path = OA_LEDGER) -> list[dict]:
    if not ledger_path.exists():
        return []
    try:
        data = json.loads(ledger_path.read_text())
    except Exception as e:
        logger.warning(f"OA ledger read failed: {e}")
        return []

    normalized = []
    for entry in data.get("received", []):
        d = _parse_date(entry.get("date"))
        if not _in_range(d, start, end):
            continue
        booking_ref = str(entry.get("booking", "")).strip()
        amount = entry.get("d2m_received_usd", 0) or 0
        if not booking_ref or not amount:
            continue
        normalized.append({
            "source": "OA",
            "booking_ref": booking_ref,
            "client_name": entry.get("client", ""),
            "supplier": entry.get("supplier", ""),
            "amount": round(float(amount), 2),
            "date": d.isoformat(),
            "notes": entry.get("statement_ref", ""),
        })

    logger.info(f"OA ledger: {len(normalized)} received commissions in {start}..{end}")
    return normalized


# ---------------------------------------------------------------------------
# PULL — manual entries (config/manual_commission_entries.json)
# ---------------------------------------------------------------------------

def pull_manual_received(start: date, end: date, ledger_path: Path = MANUAL_LEDGER) -> list[dict]:
    if not ledger_path.exists():
        return []
    try:
        data = json.loads(ledger_path.read_text())
    except Exception as e:
        logger.warning(f"Manual ledger read failed: {e}")
        return []

    normalized = []
    for entry in data.get("entries", []):
        d = _parse_date(entry.get("date"))
        if not _in_range(d, start, end):
            continue
        booking_ref = str(entry.get("booking_ref", "")).strip()
        amount = entry.get("amount_usd", 0) or 0
        if not booking_ref or not amount:
            continue
        normalized.append({
            "source": "MANUAL",
            "booking_ref": booking_ref,
            "client_name": entry.get("client", ""),
            "supplier": entry.get("supplier", ""),
            "amount": round(float(amount), 2),
            "date": d.isoformat(),
            "notes": entry.get("note", ""),
        })

    logger.info(f"Manual ledger: {len(normalized)} received commissions in {start}..{end}")
    return normalized


# ---------------------------------------------------------------------------
# PULL — expected/projected (Booking Master sheet)
# ---------------------------------------------------------------------------

def pull_expected() -> list[dict]:
    """Reuse the existing Booking Master reader — do not re-implement sheet parsing."""
    try:
        from core.booking.thunderbird_commission_recon import get_expected_commissions
        return get_expected_commissions()
    except Exception as e:
        logger.warning(f"Expected/Booking Master pull failed: {e}")
        return []


# ---------------------------------------------------------------------------
# MERGE — dedupe receipts across sources by booking_ref
# ---------------------------------------------------------------------------

def merge_received(tess: list[dict], oa: list[dict], manual: list[dict]) -> list[dict]:
    """TESS is authoritative when the same booking_ref appears in more than one
    source (portal figure > ledger > manual, per this project's financial
    hard-source rule). Later sources for an already-seen ref are recorded as
    a note on the kept entry rather than silently dropped.
    """
    merged: dict[str, dict] = {}
    for group in (tess, oa, manual):
        for item in group:
            ref = item["booking_ref"]
            if ref not in merged:
                merged[ref] = dict(item)
            else:
                kept = merged[ref]
                if abs(kept["amount"] - item["amount"]) > 0.01:
                    extra = f"Also seen in {item['source']}: ${item['amount']:,.2f} ({item['date']})"
                    kept["notes"] = (kept["notes"] + "; " + extra).strip("; ")
    return list(merged.values())


# ---------------------------------------------------------------------------
# RECONCILIATION ENGINE (pure — no I/O, directly testable)
# ---------------------------------------------------------------------------

def is_discrepancy(expected_amt: float, received_amt: float) -> tuple[bool, float, float]:
    """Returns (flagged, delta, delta_pct). Flag if variance exceeds $100 OR 5%."""
    delta = round(received_amt - expected_amt, 2)
    if expected_amt:
        pct = round((delta / expected_amt) * 100, 2)
    else:
        pct = 100.0 if delta else 0.0
    flagged = abs(delta) > VARIANCE_ABS_THRESHOLD or abs(pct) > VARIANCE_PCT_THRESHOLD
    return flagged, delta, pct


def reconcile_month(expected: list[dict], received: list[dict]) -> dict:
    """Match received (this month) to expected (Booking Master) by booking_id.

    Returns:
        matched:   received items within tolerance of their expected commission
        flagged:   received items whose variance exceeds $100 or 5%
        unmatched: received items with no matching booking_id in expected
    """
    expected_by_ref = {
        str(e.get("booking_id", "")).strip(): e
        for e in expected
        if str(e.get("booking_id", "")).strip()
    }

    matched, flagged, unmatched = [], [], []

    for recv in received:
        ref = recv["booking_ref"]
        exp = expected_by_ref.get(ref)
        if exp is None:
            unmatched.append({**recv, "reason": "No matching booking_id in Booking Master"})
            continue

        expected_amt = exp.get("expected_commission", 0.0) or 0.0
        received_amt = recv["amount"]
        is_flag, delta, pct = is_discrepancy(expected_amt, received_amt)

        entry = {
            "booking_ref": ref,
            "client_name": exp.get("client_name") or recv.get("client_name", ""),
            "supplier": exp.get("supplier") or recv.get("supplier", ""),
            "source": recv["source"],
            "expected_commission": round(expected_amt, 2),
            "received_amount": round(received_amt, 2),
            "delta": delta,
            "delta_pct": pct,
            "date": recv["date"],
            "notes": recv.get("notes", ""),
        }
        (flagged if is_flag else matched).append(entry)

    total_expected_matched = sum(e["expected_commission"] for e in matched + flagged)
    total_received = sum(e["received_amount"] for e in matched + flagged) + sum(u["amount"] for u in unmatched)

    return {
        "matched": matched,
        "flagged": flagged,
        "unmatched": unmatched,
        "totals": {
            "total_expected_for_matched_bookings": round(total_expected_matched, 2),
            "total_received": round(total_received, 2),
        },
        "counts": {
            "received_items": len(received),
            "matched": len(matched),
            "flagged": len(flagged),
            "unmatched": len(unmatched),
        },
    }


# ---------------------------------------------------------------------------
# REPORT GENERATION
# ---------------------------------------------------------------------------

def _fmt(amount: float) -> str:
    return f"-${abs(amount):,.2f}" if amount < 0 else f"${amount:,.2f}"


def generate_report(month_str: str, results: dict) -> tuple[str, str]:
    c = results["counts"]
    t = results["totals"]
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M MT")
    overall = "FLAG" if c["flagged"] or c["unmatched"] else "PASS"

    lines = [
        f"# Commission Reconciliation — {month_str}",
        f"*Generated: {now_str} · Vic Harlan (A9), Finance & Process Improvement*",
        "",
        f"**Overall: {'🔴 FLAG' if overall == 'FLAG' else '✅ PASS'}**",
        "",
        "---",
        "## Summary",
        f"| Metric | Value |",
        f"|---|---|",
        f"| Received items reconciled | {c['received_items']} |",
        f"| Matched (within tolerance) | {c['matched']} |",
        f"| Flagged (variance >5% or >$100) | {c['flagged']} |",
        f"| Unmatched (no Booking Master ref) | {c['unmatched']} |",
        f"| Total expected (matched bookings) | {_fmt(t['total_expected_for_matched_bookings'])} |",
        f"| Total received | {_fmt(t['total_received'])} |",
        "",
    ]

    if results["flagged"]:
        lines.append("## 🔴 Flagged Discrepancies")
        lines.append("| Booking | Client | Supplier | Source | Expected | Received | Delta | Delta % |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for f in results["flagged"]:
            lines.append(
                f"| {f['booking_ref']} | {f['client_name']} | {f['supplier']} | {f['source']} | "
                f"{_fmt(f['expected_commission'])} | {_fmt(f['received_amount'])} | "
                f"{_fmt(f['delta'])} | {f['delta_pct']:+.1f}% |"
            )
        lines.append("")

    if results["unmatched"]:
        lines.append("## ❓ Unmatched Receipts (no Booking Master booking_id)")
        lines.append("| Booking | Client | Supplier | Source | Amount | Date |")
        lines.append("|---|---|---|---|---|---|")
        for u in results["unmatched"]:
            lines.append(
                f"| {u['booking_ref']} | {u.get('client_name','')} | {u.get('supplier','')} | "
                f"{u['source']} | {_fmt(u['amount'])} | {u['date']} |"
            )
        lines.append("")

    if results["matched"]:
        lines.append("## ✅ Matched (within tolerance)")
        lines.append("| Booking | Client | Expected | Received |")
        lines.append("|---|---|---|---|")
        for m in results["matched"]:
            lines.append(
                f"| {m['booking_ref']} | {m['client_name']} | "
                f"{_fmt(m['expected_commission'])} | {_fmt(m['received_amount'])} |"
            )
        lines.append("")

    lines.append("---")
    if overall == "FLAG":
        lines.append(
            f"**Harlan sign-off:** FLAG — {c['flagged']} discrepancy(ies) and {c['unmatched']} unmatched "
            f"receipt(s) this reconciliation. Manual review required before this stands as settled figures."
        )
    else:
        lines.append(
            f"**Harlan sign-off:** Confirmed — all {c['matched']} matched receipts for {month_str} within "
            f"tolerance. No material variance detected."
        )

    md = "\n".join(lines)

    # HTML — D2M dark navy per storage/templates/d2m_canonical_darknavy.html convention
    def _row(cells: list[str]) -> str:
        return "<tr>" + "".join(f"<td style='padding:4px 8px'>{c}</td>" for c in cells) + "</tr>"

    flagged_rows = "".join(
        _row([f["booking_ref"], f["client_name"], f["supplier"], f["source"],
              _fmt(f["expected_commission"]), _fmt(f["received_amount"]),
              _fmt(f["delta"]), f"{f['delta_pct']:+.1f}%"])
        for f in results["flagged"]
    )
    unmatched_rows = "".join(
        _row([u["booking_ref"], u.get("client_name", ""), u.get("supplier", ""),
              u["source"], _fmt(u["amount"]), u["date"]])
        for u in results["unmatched"]
    )

    html = f"""<div style="font-family:Georgia,serif;color:#1a3557;background:#f7f3ea;padding:24px;max-width:760px">
<div style="background:#1a3557;color:#fff;padding:12px 16px;margin-bottom:16px">
  <strong>Commission Reconciliation — {month_str}</strong><br>
  <small>Generated {now_str} · Vic Harlan (A9) · Thunderbird Wing</small>
</div>
<p><strong>Overall: <span style="color:{'#cc0000' if overall == 'FLAG' else '#006600'}">{'🔴 FLAG' if overall == 'FLAG' else '✅ PASS'}</span></strong></p>
<table style='width:100%;border-collapse:collapse;font-size:13px;margin-bottom:16px'>
<tr style='background:#1a3557;color:#fff'><th style='padding:4px 8px'>Metric</th><th style='padding:4px 8px'>Value</th></tr>
{_row(["Received items reconciled", str(c['received_items'])])}
{_row(["Matched", str(c['matched'])])}
{_row(["Flagged", str(c['flagged'])])}
{_row(["Unmatched", str(c['unmatched'])])}
{_row(["Total expected (matched)", _fmt(t['total_expected_for_matched_bookings'])])}
{_row(["Total received", _fmt(t['total_received'])])}
</table>
{"<h3 style='color:#cc0000'>Flagged Discrepancies</h3><table style='width:100%;border-collapse:collapse;font-size:13px'><tr style='background:#1a3557;color:#fff'><th>Booking</th><th>Client</th><th>Supplier</th><th>Source</th><th>Expected</th><th>Received</th><th>Delta</th><th>Delta %%</th></tr>" + flagged_rows + "</table>" if results["flagged"] else ""}
{"<h3 style='color:#888'>Unmatched Receipts</h3><table style='width:100%;border-collapse:collapse;font-size:13px'><tr style='background:#1a3557;color:#fff'><th>Booking</th><th>Client</th><th>Supplier</th><th>Source</th><th>Amount</th><th>Date</th></tr>" + unmatched_rows + "</table>" if results["unmatched"] else ""}
<div style="margin-top:16px;padding:12px;background:#fff;border-left:4px solid {'#cc0000' if overall == 'FLAG' else '#1a3557'}">
  <strong>Harlan sign-off:</strong><br>
  {lines[-1].replace("**Harlan sign-off:** ", "")}
</div>
</div>"""

    return md, html


# ---------------------------------------------------------------------------
# OUTPUT FILE
# ---------------------------------------------------------------------------

def write_output(month_str: str, results: dict) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"Commission_Reconciliation_{month_str}.json"
    payload = {
        "month": month_str,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        **results,
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out_path


# ---------------------------------------------------------------------------
# EMAIL — WF-17 hold draft (not sent)
# ---------------------------------------------------------------------------

def draft_summary_email(month_str: str, html_body: str, overall_flag: bool) -> dict:
    try:
        from core.email.thunderbird_gmail import gmail_create_draft_sync
    except Exception as e:
        logger.warning(f"Could not import gmail_create_draft_sync: {e}")
        return {"status": "error", "error": str(e)}

    marker = " 🔴 FLAG" if overall_flag else ""
    subject = f"Commission Reconciliation — {month_str}{marker} — D2M Monthly"
    try:
        result = gmail_create_draft_sync(
            to=COMMANDER_INBOX,
            subject=subject,
            body=html_body,
            persona_id="A9",
            product_type="Commission Reconciliation — Monthly",
            label_review=True,
        )
        logger.info(f"Draft staged in johnloucks3 — {result.get('draft_id', 'unknown id')}")
        return result
    except Exception as e:
        logger.error(f"Draft creation failed: {e}")
        return {"status": "error", "error": str(e)}


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def run(month_str: str, dry_run: bool = False, local: bool = False) -> dict:
    start, end = month_bounds(month_str)
    logger.info(f"Commission Reconciliation — {month_str} ({start}..{end})")

    tess = pull_tess_received(start, end)
    oa = pull_oa_received(start, end)
    manual = pull_manual_received(start, end)
    received = merge_received(tess, oa, manual)
    expected = pull_expected()

    results = reconcile_month(expected, received)
    md_report, html_report = generate_report(month_str, results)
    out_path = write_output(month_str, results)

    overall_flag = bool(results["counts"]["flagged"] or results["counts"]["unmatched"])

    if local:
        print(md_report)
        print(f"\nOutput written: {out_path}")
        return {"results": results, "output_path": str(out_path)}

    if dry_run:
        print(md_report)
        print(f"\nOutput written: {out_path}")
        print("\n[DRY RUN — no draft created]")
        return {"results": results, "output_path": str(out_path)}

    draft = draft_summary_email(month_str, html_report, overall_flag)
    return {"results": results, "output_path": str(out_path), "draft": draft}


def main():
    p = argparse.ArgumentParser(description="Monthly commission reconciliation")
    p.add_argument("--month", default=None, help="YYYY-MM (default: previous full month)")
    p.add_argument("--dry-run", action="store_true", help="Generate report + JSON, skip email draft")
    p.add_argument("--local", action="store_true", help="Print to stdout only, no draft, no side effects")
    args = p.parse_args()

    month_str = args.month or previous_month_str()
    run(month_str, dry_run=args.dry_run, local=args.local)


if __name__ == "__main__":
    main()
