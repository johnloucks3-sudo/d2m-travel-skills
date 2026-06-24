#!/usr/bin/env python3
"""
Commission Clock — Weekly Commission Verification Report
=========================================================
Dreams2Memories Travel, LLC | scripts/commission_clock.py

Runs Harlan 6-step verification logic weekly. Sources:
    - TESS API (received payments, last 30 days)
    - Google Sheet commission tracker (expected commissions via hale_state.json)
    - harlan_verdict.json (model/token cost gate — referenced but not blocking here)

Generates weekly report in Hale brief format.
Delivers to johnloucks3@gmail.com via core/email send pattern.

Systemd timer: systemd/user/commission-clock.timer → Sunday 22:00 MT

Usage:
    python3 scripts/commission_clock.py             # Full run + email
    python3 scripts/commission_clock.py --dry-run   # Report only, no email
    python3 scripts/commission_clock.py --local     # Print to stdout
"""

from __future__ import annotations

import argparse
import base64
import json
import logging
import sys
from datetime import date, datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

THUNDERBIRD = Path.home() / "Thunderbird"
sys.path.insert(0, str(THUNDERBIRD))
sys.path.insert(0, str(THUNDERBIRD / "core" / "booking"))

HARLAN_VERDICT = THUNDERBIRD / "harlan_verdict.json"
HALE_STATE = THUNDERBIRD / "hale_state.json"
GMAIL_TOKEN = THUNDERBIRD / "gmail_token.json"
TESS_TOKEN = THUNDERBIRD / "tess_token.json"
REPORT_OUT = THUNDERBIRD / "OpsCenter" / "state" / "commission_clock_last.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s COMMISSION %(levelname)s %(message)s",
)
logger = logging.getLogger("commission_clock")

COMMANDER_INBOX = "johnloucks3@gmail.com"


# ---------------------------------------------------------------------------
# TESS — pull received payments (last 30 days)
# ---------------------------------------------------------------------------

def _get_tess_received(days: int = 30) -> dict:
    """Pull commission data from TESS for the last N days."""
    if not TESS_TOKEN.exists():
        return {"error": "tess_token.json not found — run tess_authorize.sh first", "items": []}

    try:
        from core.booking.thunderbird_tess import TESSClient
        client = TESSClient()
        since = (date.today() - timedelta(days=days)).strftime("%Y-%m-%d")
        result = client.list_bookings(
            page_size=100,
            paymentDateStart=since,
        )
        items = result.get("Items", [])
        received_total = sum(
            float(b.get("Commission", {}).get("AgencyAmountPaid", 0) or 0)
            for b in items
        )
        return {
            "items": items,
            "count": len(items),
            "received_total": received_total,
            "since": since,
            "fetched_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {"error": str(e), "items": [], "received_total": 0}


# ---------------------------------------------------------------------------
# Google Sheet — expected commissions from hale_state.json
# ---------------------------------------------------------------------------

def _get_sheet_expected() -> dict:
    """Load expected commission data from the financial pulse in hale_state."""
    try:
        state = json.loads(HALE_STATE.read_text(encoding="utf-8"))
        fin = state.get("financial_pulse", {})
        return {
            "sheet_commission_expected": fin.get("sheet_commission_expected", 0),
            "sheet_d2m_share": fin.get("sheet_d2m_share", 0),
            "pipeline_d2m_share_upcoming": fin.get("pipeline_d2m_share_upcoming", 0),
            "pipeline_commission_upcoming": fin.get("pipeline_commission_upcoming", 0),
            "sheet_bookings": fin.get("sheet_bookings", 0),
            "tess_received": fin.get("tess_received", 0),
            "last_checked": fin.get("last_checked", "unknown"),
            "status": "ok",
        }
    except Exception as e:
        return {"error": str(e), "status": "error"}


# ---------------------------------------------------------------------------
# Harlan 6-step verification
# ---------------------------------------------------------------------------

def harlan_six_step(tess_data: dict, sheet_data: dict) -> dict:
    """
    Harlan's 6-step commission verification:

    Step 1: Portal balance (TESS received payments)
    Step 2: Portal FPD (TESS payment dates)
    Step 3: Compare vs dossier/sheet + flag delta
    Step 4: Root cause or unresolved flag
    Step 5: Credits verified
    Step 6: Harlan sign-off
    """
    today = date.today()
    results: dict = {"steps": [], "sign_off": "", "status": "PASS"}

    # Step 1 — Portal balance
    tess_received = tess_data.get("received_total", 0)
    tess_count = tess_data.get("count", 0)
    tess_error = tess_data.get("error", "")
    step1_ok = not tess_error
    results["steps"].append({
        "step": 1,
        "label": "TESS received payments (last 30d)",
        "value": f"${tess_received:,.2f} across {tess_count} bookings",
        "status": "CONFIRMED" if step1_ok else "UNKNOWN",
        "note": tess_error if tess_error else "",
    })

    # Step 2 — Portal FPD dates
    sheet_received = sheet_data.get("tess_received", 0)
    step2_ok = not sheet_data.get("error")
    results["steps"].append({
        "step": 2,
        "label": "Sheet FPD / expected commission",
        "value": (
            f"Expected: ${sheet_data.get('sheet_commission_expected', 0):,.2f} | "
            f"D2M share: ${sheet_data.get('sheet_d2m_share', 0):,.2f} | "
            f"Upcoming pipeline: ${sheet_data.get('pipeline_d2m_share_upcoming', 0):,.2f}"
        ),
        "status": "CONFIRMED" if step2_ok else "UNKNOWN",
        "note": sheet_data.get("error", ""),
    })

    # Step 3 — Delta: TESS received vs sheet expected
    if step1_ok and step2_ok:
        delta = tess_received - sheet_received
        delta_pct = (delta / sheet_received * 100) if sheet_received else 0
        step3_status = "CONFIRMED" if abs(delta) < 100 else "INFERRED"
        results["steps"].append({
            "step": 3,
            "label": "Delta: TESS received vs sheet",
            "value": f"Δ=${delta:+,.2f} ({delta_pct:+.1f}%)",
            "status": step3_status,
            "note": "Within normal variance" if abs(delta) < 100 else "Variance > $100 — investigate",
        })
        if abs(delta) >= 100:
            results["status"] = "FLAG"
    else:
        results["steps"].append({
            "step": 3,
            "label": "Delta: skipped (data error)",
            "value": "N/A",
            "status": "UNKNOWN",
        })
        results["status"] = "FLAG"

    # Step 4 — Root cause / unresolved flags
    flags: list[str] = []
    if tess_error:
        flags.append(f"TESS fetch error: {tess_error}")
    if sheet_data.get("error"):
        flags.append(f"Sheet fetch error: {sheet_data['error']}")
    results["steps"].append({
        "step": 4,
        "label": "Open flags / root cause",
        "value": "; ".join(flags) if flags else "None",
        "status": "FLAG" if flags else "CONFIRMED",
    })

    # Step 5 — Credits verified
    results["steps"].append({
        "step": 5,
        "label": "Credits verified",
        "value": f"TESS checks received: ${tess_received:,.2f}",
        "status": "CONFIRMED" if step1_ok else "UNKNOWN",
    })

    # Step 6 — Harlan sign-off
    if results["status"] == "PASS":
        sign_off = (
            f"Confirmed: TESS received ${tess_received:,.2f} as of {today.isoformat()}, "
            f"source: TESS/sheet. Sheet expected ${sheet_data.get('sheet_commission_expected', 0):,.2f}. "
            f"D2M pipeline: ${sheet_data.get('pipeline_d2m_share_upcoming', 0):,.2f}. "
            f"No material variance detected."
        )
    else:
        sign_off = (
            f"FLAG: Variance or data gap detected. "
            f"TESS received ${tess_received:,.2f} as of {today.isoformat()}. "
            f"Manual review required before committing to financial reporting."
        )
    results["steps"].append({
        "step": 6,
        "label": "Harlan sign-off",
        "value": sign_off,
        "status": results["status"],
    })
    results["sign_off"] = sign_off

    return results


# ---------------------------------------------------------------------------
# Report generator
# ---------------------------------------------------------------------------

def generate_report(tess_data: dict, sheet_data: dict, harlan: dict) -> tuple[str, str]:
    """Returns (markdown, html)."""
    today = date.today()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M MT")

    step_rows_md = []
    for s in harlan.get("steps", []):
        status_icon = "✅" if s["status"] == "CONFIRMED" else "⚠️" if s["status"] == "FLAG" else "❓"
        note = f" — {s['note']}" if s.get("note") else ""
        step_rows_md.append(
            f"| {s['step']} | {s['label']} | {s['value']}{note} | {status_icon} {s['status']} |"
        )

    step_table = "\n".join([
        "| Step | Check | Value | Status |",
        "|---|---|---|---|",
    ] + step_rows_md)

    overall = harlan.get("status", "UNKNOWN")
    overall_icon = "✅ PASS" if overall == "PASS" else "🔴 FLAG"

    md = f"""# Commission Clock — Weekly Report
*Generated: {now_str}*

**Overall: {overall_icon}**

---

## Harlan 6-Step Verification

{step_table}

---

**Sign-off:**
> {harlan.get("sign_off", "Not available")}

---

*TESS data: last 30 days as of {tess_data.get("since", "unknown")}*
*Sheet data: last refreshed {sheet_data.get("last_checked", "unknown")}*
*Next report: {(today + timedelta(days=7)).isoformat()} Sunday 22:00 MT*
"""

    step_rows_html = []
    for s in harlan.get("steps", []):
        status_color = "#006600" if s["status"] == "CONFIRMED" else "#cc0000" if s["status"] == "FLAG" else "#888888"
        note = f"<br><small>{s['note']}</small>" if s.get("note") else ""
        step_rows_html.append(
            f"<tr><td>{s['step']}</td><td>{s['label']}</td>"
            f"<td>{s['value']}{note}</td>"
            f"<td style='color:{status_color}'><strong>{s['status']}</strong></td></tr>"
        )

    overall_color = "#006600" if overall == "PASS" else "#cc0000"

    html = f"""<div style="font-family:Georgia,serif;color:#1a3557;background:#f7f3ea;padding:24px;max-width:700px">
<div style="background:#1a3557;color:#fff;padding:12px 16px;margin-bottom:16px">
  <strong>Commission Clock — Weekly Report</strong><br>
  <small>Generated {now_str} · Harlan A9 · Thunderbird Wing</small>
</div>

<p><strong>Overall: <span style="color:{overall_color}">{overall_icon}</span></strong></p>

<h3 style="color:#1a3557">Harlan 6-Step Verification</h3>
<table style='width:100%;border-collapse:collapse;font-size:13px'>
<tr style='background:#1a3557;color:#fff'><th>#</th><th>Check</th><th>Value</th><th>Status</th></tr>
{''.join(step_rows_html)}
</table>

<div style="margin-top:16px;padding:12px;background:#fff;border-left:4px solid #1a3557">
  <strong>Sign-off:</strong><br>
  {harlan.get("sign_off", "Not available")}
</div>

<p style="font-size:11px;color:#888;border-top:1px solid #ccc;padding-top:8px;margin-top:20px">
TESS data: last 30d · Sheet: last refreshed {sheet_data.get("last_checked", "unknown")}<br>
Next report: {(today + timedelta(days=7)).isoformat()} 22:00 MT · Harlan A9 · Thunderbird Wing
</p>
</div>"""

    return md, html


# ---------------------------------------------------------------------------
# Email sender
# ---------------------------------------------------------------------------

def send_report_email(subject: str, html_body: str) -> bool:
    try:
        import google.oauth2.credentials as gc
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build

        data = json.loads(GMAIL_TOKEN.read_text())
        creds = gc.Credentials(
            token=data.get("token"),
            refresh_token=data.get("refresh_token"),
            token_uri=data.get("token_uri"),
            client_id=data.get("client_id"),
            client_secret=data.get("client_secret"),
            scopes=data.get("scopes"),
        )
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())

        service = build("gmail", "v1", credentials=creds)
        msg = MIMEMultipart("alternative")
        msg["to"] = COMMANDER_INBOX
        msg["from"] = "d2mconcierge@gmail.com"
        msg["subject"] = subject
        msg.attach(MIMEText(html_body, "html", "utf-8"))
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        service.users().messages().send(userId="me", body={"raw": raw}).execute()
        logger.info(f"Commission report emailed to {COMMANDER_INBOX}")
        return True
    except Exception as exc:
        logger.error(f"Email send failed: {exc}")
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    p = argparse.ArgumentParser(description="Commission Clock — weekly verification report")
    p.add_argument("--dry-run", action="store_true", help="Generate report, skip email")
    p.add_argument("--local", action="store_true", help="Print to stdout only")
    args = p.parse_args()

    today = date.today()
    logger.info(f"Commission Clock running — {today.isoformat()}")

    tess_data = _get_tess_received(days=30)
    sheet_data = _get_sheet_expected()
    harlan = harlan_six_step(tess_data, sheet_data)

    md_report, html_report = generate_report(tess_data, sheet_data, harlan)

    # Persist report
    REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
    report_payload = {
        "generated_at": datetime.utcnow().isoformat(),
        "overall_status": harlan.get("status"),
        "sign_off": harlan.get("sign_off"),
        "tess_received": tess_data.get("received_total", 0),
        "sheet_expected": sheet_data.get("sheet_commission_expected", 0),
    }
    REPORT_OUT.write_text(json.dumps(report_payload, indent=2), encoding="utf-8")

    if args.local:
        print(md_report)
        return

    if not args.dry_run:
        flag_marker = " 🔴 FLAG" if harlan.get("status") == "FLAG" else ""
        subject = f"Commission Clock — {today.strftime('%d %b %Y')}{flag_marker} — D2M Weekly"
        ok = send_report_email(subject, html_report)
        print(f"  {'OK' if ok else 'FAILED'} — report emailed to {COMMANDER_INBOX}")
    else:
        print(md_report)
        print("\n[DRY RUN — email not sent]")


if __name__ == "__main__":
    main()
