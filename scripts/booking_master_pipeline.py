#!/usr/bin/env python3
"""
Generate the full TESS-vs-Sheet pipeline artifact set.

Produces in /home/john/Thunderbird/output/tess_map/:
  - booking_master_schema.md   column inventory + sample row
  - booking_master_dump.json   full sheet dump (JSON-serializable)
  - cross_ref.json             match results between TESS and Sheet
  - cross_ref.md               human summary of cross-ref
  - d2m_full_pipeline.md       executive summary (totals, by-client, upcoming)

Run from project root:
    python3 scripts/booking_master_pipeline.py
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.booking.booking_master import BookingMasterClient, _norm_name  # noqa: E402

OUTPUT_DIR = ROOT / "output" / "tess_map"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _json_safe(obj: Any) -> Any:
    """Recursively convert dates/datetimes/sets to JSON-friendly forms."""
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items() if not str(k).startswith("_")}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(x) for x in obj]
    if isinstance(obj, set):
        return sorted(_json_safe(x) for x in obj)
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    return obj


# ---- 1. schema dump --------------------------------------------------------


def write_schema(client: BookingMasterClient) -> None:
    rows = client.list_bookings()
    cols = [c for c in rows[0].keys() if not c.startswith("_")] if rows else []
    sample = rows[0] if rows else {}
    sample_clean = {k: v for k, v in sample.items() if not k.startswith("_") and v not in ("", None)}

    lines = [
        "# Booking Master — Schema",
        "",
        f"**Sheet ID:** `{client.sheet_id}`",
        f"**Tab:** `{client.tab}`",
        f"**Auth:** service account `dreams2memories@d2m-python-pipeline.iam.gserviceaccount.com`",
        f"**Credentials path:** `{client._creds_path}`",
        f"**Row count:** {len(rows)}",
        f"**Column count:** {len(cols)}",
        "",
        "## Columns",
        "",
    ]
    for i, c in enumerate(cols, 1):
        lines.append(f"{i}. `{c}`")
    lines += [
        "",
        "## Sample row (non-empty fields only)",
        "",
        "```json",
        json.dumps(_json_safe(sample_clean), indent=2),
        "```",
        "",
        "## Notes",
        "",
        "- Row 1 (Kuklinski) shows column drift in the source data — `Status: 9595029`,",
        "  `Total_Cost: 'Confirmed'`, `Final_Payment_Date: '$743.76'`. Money parsing is",
        "  defensive and will return 0 for non-numeric cells.",
        "- Row 2 wraps the McLeod booking under `NEXION LLC` (host agency). Cross-",
        "  reference uses surname tokens from Notes + Traveler columns to recover.",
        "- The official auth path documented in `thunderbird_email_intel.py`",
        "  references `credentials.json`, but on disk that file holds OAuth installed-",
        "  app secrets, not a service account. We resolve to",
        "  `.service_account_gemini.json` automatically.",
        "",
    ]
    (OUTPUT_DIR / "booking_master_schema.md").write_text("\n".join(lines), encoding="utf-8")


# ---- 2. full dump ----------------------------------------------------------


def write_dump(client: BookingMasterClient) -> None:
    rows = client.list_bookings()
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "sheet_id": client.sheet_id,
        "tab": client.tab,
        "row_count": len(rows),
        "rows": [_json_safe(r) for r in rows],
    }
    (OUTPUT_DIR / "booking_master_dump.json").write_text(
        json.dumps(payload, indent=2, default=str), encoding="utf-8"
    )


# ---- 3. cross-reference ----------------------------------------------------


def fetch_tess_bookings() -> tuple[list[dict[str, Any]], str | None]:
    """Pull bookings from TESS. Returns (records, error_message).

    Walks all pages up to a hard cap. Returns ([], reason) if TESS is offline.
    """
    try:
        sys.path.insert(0, str(ROOT / "core" / "booking"))
        from thunderbird_tess import TESSClient  # type: ignore
    except Exception as e:  # noqa: BLE001
        return [], f"Could not import TESSClient: {e}"

    try:
        tc = TESSClient()
    except Exception as e:  # noqa: BLE001
        return [], f"Could not construct TESSClient: {e}"

    records: list[dict[str, Any]] = []
    page = 1
    page_size = 100
    max_pages = 10
    while page <= max_pages:
        try:
            resp = tc.list_bookings(page_number=page, page_size=page_size)
        except Exception as e:  # noqa: BLE001
            return records, f"TESS list_bookings exception on page {page}: {e}"
        if not isinstance(resp, dict):
            return records, f"TESS returned non-dict on page {page}: {type(resp)}"
        if resp.get("error"):
            reason = resp.get("error_description") or resp.get("error")
            return records, f"TESS error: {reason} ({resp.get('type', 'unknown')})"
        items = resp.get("Items", []) or []
        if not items:
            break
        records.extend(items)
        if len(items) < page_size:
            break
        page += 1
    return records, None


def write_cross_ref(client: BookingMasterClient) -> dict[str, Any]:
    tess_records, error = fetch_tess_bookings()
    cross = client.cross_reference_with_tess(tess_records)

    out = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "tess_status": "offline" if error else "online",
        "tess_error": error,
        "tess_record_count": len(tess_records),
        "sheet_record_count": len(client.list_bookings()),
        "matched_count": len(cross["matched"]),
        "only_in_sheet_count": len(cross["only_in_sheet"]),
        "only_in_tess_count": len(cross["only_in_tess"]),
        "matched": [
            {
                "match_type": m["match_type"],
                "client_sheet": m["sheet_row"].get("Client_Name"),
                "supplier_sheet": m["sheet_row"].get("Supplier"),
                "start_date_sheet": m["sheet_row"].get("Start_Date"),
                "confirmation_sheet": m["sheet_row"].get("Confirmation_Number"),
                "tess_keys": list(m["tess_record"].keys())[:15],
            }
            for m in cross["matched"]
        ],
        "only_in_sheet": [
            {
                "client": r.get("Client_Name"),
                "supplier": r.get("Supplier"),
                "start_date": r.get("Start_Date"),
                "confirmation": r.get("Confirmation_Number"),
                "booking_id": r.get("Booking_ID"),
                "trip": r.get("Trip_Name"),
                "notes": (r.get("Notes") or "")[:120],
            }
            for r in cross["only_in_sheet"]
        ],
        "only_in_tess": [_json_safe(t) for t in cross["only_in_tess"][:50]],
    }
    (OUTPUT_DIR / "cross_ref.json").write_text(
        json.dumps(out, indent=2, default=str), encoding="utf-8"
    )

    # Markdown summary
    md = ["# TESS ↔ Booking Master Cross-Reference", ""]
    md.append(f"_Generated: {out['generated_at']}_")
    md.append("")
    md.append(f"- **TESS status:** {out['tess_status']}")
    if error:
        md.append(f"- **TESS error:** `{error}`")
    md.append(f"- **TESS records pulled:** {out['tess_record_count']}")
    md.append(f"- **Sheet records:** {out['sheet_record_count']}")
    md.append(f"- **Matched:** {out['matched_count']}")
    md.append(f"- **Only in Sheet:** {out['only_in_sheet_count']}")
    md.append(f"- **Only in TESS:** {out['only_in_tess_count']}")
    md.append("")

    if error:
        md.append("> ⚠️ TESS is offline; this report reflects sheet-only data plus a stub")
        md.append("> for TESS until re-auth. Run `python3 core/booking/thunderbird_tess.py")
        md.append("> --authorize` to re-establish the session and re-run this pipeline.")
        md.append("")

    md.append("## Matched")
    md.append("")
    if not out["matched"]:
        md.append("_No matches — TESS data unavailable._")
    else:
        md.append("| Client (Sheet) | Supplier | Start | Confirmation | Match |")
        md.append("|---|---|---|---|---|")
        for m in out["matched"]:
            md.append(
                f"| {m['client_sheet']} | {m['supplier_sheet']} | "
                f"{m['start_date_sheet']} | {m['confirmation_sheet']} | "
                f"{m['match_type']} |"
            )
    md.append("")

    md.append("## Only in Sheet")
    md.append("")
    md.append("| Client | Supplier | Start | Confirmation | Trip |")
    md.append("|---|---|---|---|---|")
    for r in out["only_in_sheet"]:
        md.append(
            f"| {r['client']} | {r['supplier']} | {r['start_date']} | "
            f"{r['confirmation']} | {r['trip']} |"
        )
    md.append("")

    md.append("## Only in TESS")
    md.append("")
    if not out["only_in_tess"]:
        md.append("_None — or TESS unreachable._")
    else:
        for t in out["only_in_tess"][:25]:
            label = (
                t.get("ClientName")
                or t.get("PrimaryTravelerName")
                or t.get("BookingNumber")
                or "(unnamed)"
            )
            md.append(f"- {label}")
    md.append("")

    (OUTPUT_DIR / "cross_ref.md").write_text("\n".join(md), encoding="utf-8")
    return out


# ---- 4. executive summary --------------------------------------------------


def write_full_pipeline(client: BookingMasterClient, cross: dict[str, Any]) -> None:
    summary = client.commission_summary()
    upcoming = client.upcoming_voyages()
    rows = client.list_bookings()

    # Group by surname token across both systems
    sheet_by_surname: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        key = _norm_name(r.get("Client_Name") or "") or "_unknown"
        # If NEXION LLC (host agency), prefer surname from Notes
        if key in ("nexion", "_unknown"):
            for n in (
                r.get("Notes"),
                r.get("Lead_Traveler"),
                r.get("Traveler_3_Name"),
            ):
                alt = _norm_name(str(n or ""))
                if alt and alt != "nexion":
                    key = alt
                    break
        sheet_by_surname.setdefault(key, []).append(r)

    md: list[str] = []
    md.append("# D2M Full Booking Pipeline — TESS + Booking Master")
    md.append("")
    md.append(f"_Generated: {datetime.now().isoformat(timespec='seconds')}_")
    md.append("")

    # System totals
    md.append("## System totals")
    md.append("")
    md.append("| System | Bookings | Commission Expected | D2M Share | Notes |")
    md.append("|---|---:|---:|---:|---|")
    md.append(
        f"| Booking Master (Sheet) | {summary['booking_count']} | "
        f"${summary['total_expected']:,.2f} | ${summary['total_d2m_share']:,.2f} | "
        f"Source of truth incl. pre-TESS bookings |"
    )
    md.append(
        f"| TESS (myAgentGenie) | {cross['tess_record_count']} | n/a | n/a | "
        f"Status: {cross['tess_status']} |"
    )
    md.append("")

    if cross.get("tess_error"):
        md.append(f"> ⚠️ TESS commission-paid totals unavailable — `{cross['tess_error']}`")
        md.append("")

    md.append("## Cross-system reconciliation")
    md.append("")
    md.append(f"- **Matched (in both):** {cross['matched_count']}")
    md.append(f"- **Sheet only:** {cross['only_in_sheet_count']}")
    md.append(f"- **TESS only:** {cross['only_in_tess_count']}")
    md.append("")

    # By client
    md.append("## By client")
    md.append("")
    md.append("| Surname | Sheet bookings | Commission Expected | D2M Share | In TESS? |")
    md.append("|---|---:|---:|---:|---|")
    matched_keys = {
        _norm_name(m["client_sheet"] or "") for m in cross.get("matched", [])
    }
    # Also pull surnames from TESS-only side
    tess_keys: set[str] = set()
    for t in cross.get("only_in_tess", []):
        for fld in ("ClientName", "PrimaryTravelerName", "LeadTravelerName"):
            if fld in t and t[fld]:
                k = _norm_name(t[fld])
                if k:
                    tess_keys.add(k)
                    break

    for surname in sorted(sheet_by_surname.keys()):
        rows_for = sheet_by_surname[surname]
        comm = sum(r["_parsed_commission"] for r in rows_for)
        share = sum(r["_parsed_d2m_share"] for r in rows_for)
        in_tess = "✓" if surname in matched_keys or surname in tess_keys else "—"
        md.append(
            f"| {surname or '(unknown)'} | {len(rows_for)} | "
            f"${comm:,.2f} | ${share:,.2f} | {in_tess} |"
        )
    md.append("")

    # By supplier
    md.append("## By supplier")
    md.append("")
    md.append("| Supplier | Bookings | Commission Expected | D2M Share |")
    md.append("|---|---:|---:|---:|")
    for sup, v in sorted(
        summary["by_supplier"].items(), key=lambda kv: -kv[1]["expected"]
    ):
        md.append(
            f"| {sup} | {v['count']} | ${v['expected']:,.2f} | ${v['share']:,.2f} |"
        )
    md.append("")

    # Upcoming voyages
    md.append(f"## Upcoming voyages ({len(upcoming)})")
    md.append("")
    md.append(
        "| Client | Supplier | Trip | Start | End | "
        "Final Pmt | Commission | D2M Share | Status |"
    )
    md.append("|---|---|---|---|---|---|---:|---:|---|")
    for r in upcoming:
        client_n = r.get("Client_Name") or ""
        if _norm_name(client_n) in ("nexion", ""):
            for n in (r.get("Notes"), r.get("Traveler_3_Name"), r.get("Lead_Traveler")):
                if n and "client" in str(n).lower():
                    client_n = str(n).split(":", 1)[-1].strip()[:60]
                    break
                if n:
                    client_n = str(n)[:60]
                    break
        md.append(
            f"| {client_n} | {r.get('Supplier','')} | {r.get('Trip_Name','')} | "
            f"{r.get('Start_Date','')} | {r.get('End_Date','')} | "
            f"{r.get('Final_Payment_Date','') or r.get('Payment_Due_Date','')} | "
            f"${r['_parsed_commission']:,.2f} | ${r['_parsed_d2m_share']:,.2f} | "
            f"{r.get('Status','')} |"
        )
    md.append("")

    md.append("## Caveats")
    md.append("")
    md.append("- `total_received` in `commission_summary()` reflects **client payments**")
    md.append("  (Amount_Paid column), not commission paid out by the supplier. The sheet")
    md.append("  does not track received commission; TESS is the source of truth there.")
    md.append("- Row 1 (Kuklinski) has column drift in the source — money parsing returns 0")
    md.append("  for non-numeric cells, so its commission contribution is undercounted.")
    md.append("- NEXION LLC rows are the host-agency wrapper for McLeod December.")
    md.append("")

    (OUTPUT_DIR / "d2m_full_pipeline.md").write_text("\n".join(md), encoding="utf-8")


# ---- main ------------------------------------------------------------------


def main() -> int:
    client = BookingMasterClient()
    print(f"Output dir: {OUTPUT_DIR}")
    write_schema(client)
    print("✓ booking_master_schema.md")
    write_dump(client)
    print("✓ booking_master_dump.json")
    cross = write_cross_ref(client)
    print(f"✓ cross_ref.json + cross_ref.md  (TESS: {cross['tess_status']})")
    write_full_pipeline(client, cross)
    print("✓ d2m_full_pipeline.md")

    summary = client.commission_summary()
    print()
    print("=== SUMMARY ===")
    print(f"  Bookings:            {summary['booking_count']}")
    print(f"  Commission expected: ${summary['total_expected']:,.2f}")
    print(f"  D2M share:           ${summary['total_d2m_share']:,.2f}")
    print(f"  Client paid:         ${summary['total_received']:,.2f}")
    print(f"  Balance due:         ${summary['total_due']:,.2f}")
    print(f"  Upcoming voyages:    {len(client.upcoming_voyages())}")
    print(f"  TESS records:        {cross['tess_record_count']} ({cross['tess_status']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
