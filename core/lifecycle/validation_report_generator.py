#!/usr/bin/env python3
"""
ETB-004: D2M Validation Report Generator
==========================================
Monthly batch process — reads all Blackboard client YAML, validates 18 categories,
calculates completion % and risk score, generates HTML reports + summary email.

Usage:
  python3 validation_report_generator.py [--client CLIENT_ID] [--dry-run]

Schedule: Monthly on the 15th at 0700 MT via systemd timer
Output:   OpsCenter/validations/YYYY-MM/[client_id]_validation.html
          OpsCenter/data/validation_summary.json
          Gmail draft (A-Staff summary email)
          OpsCenter/logs/validation_audit.jsonl
"""

import sys
import json
import yaml
import logging
import argparse
from datetime import date, datetime
from pathlib import Path
from typing import Optional

# ── Paths ─────────────────────────────────────────────────────────────────────
BLACKBOARD_DIR = Path("/home/john/Thunderbird/Blackboard/clients")
VALIDATIONS_DIR = Path("/home/john/Thunderbird/OpsCenter/validations")
DATA_DIR = Path("/home/john/Thunderbird/OpsCenter/data")
AUDIT_LOG = Path("/home/john/Thunderbird/OpsCenter/logs/validation_audit.jsonl")
THUNDERBIRD_ROOT = Path("/home/john/Thunderbird")

RISK_THRESHOLD = 120.0  # days_out / (pct/100) > 120 = HIGH risk (30d out, 25% pct = HIGH)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [VALIDATION] %(levelname)s %(message)s",
    handlers=[logging.StreamHandler()]
)
log = logging.getLogger(__name__)


# ── Validation Categories ─────────────────────────────────────────────────────

CATEGORIES = [
    "flights_outbound", "flights_return", "hotel_pre", "hotel_post",
    "cruise", "transfers_inbound", "transfers_outbound", "excursions",
    "dining_specialty", "insurance", "visas", "passports", "vaccinations",
    "emergency_contacts", "financial", "crew_comms", "client_comms", "post_travel"
]

CATEGORY_LABELS = {
    "flights_outbound": "Outbound Flights",
    "flights_return": "Return Flights",
    "hotel_pre": "Pre-Cruise Hotel",
    "hotel_post": "Post-Cruise Hotel",
    "cruise": "Cruise Booking",
    "transfers_inbound": "Inbound Transfers",
    "transfers_outbound": "Outbound Transfers",
    "excursions": "Shore Excursions",
    "dining_specialty": "Specialty Dining",
    "insurance": "Travel Insurance",
    "visas": "Visas",
    "passports": "Passports",
    "vaccinations": "Vaccinations",
    "emergency_contacts": "Emergency Contacts",
    "financial": "Financial / Payments",
    "crew_comms": "Cruise Line Registration",
    "client_comms": "Client Communications",
    "post_travel": "Post-Travel Planning",
}

STATUS_WEIGHT = {"confirmed": 1.0, "not_applicable": 1.0, "pending": 0.5, "missing": 0.0}
STATUS_COLOR = {
    "confirmed": "#238636",
    "not_applicable": "#8b949e",
    "pending": "#e36209",
    "missing": "#da3633",
}
STATUS_ICON = {
    "confirmed": "✅",
    "not_applicable": "—",
    "pending": "⚠️",
    "missing": "❌",
}


# ── Risk Score Calculation ────────────────────────────────────────────────────

def calculate_risk_score(client: dict, completion_pct: float) -> float:
    """
    Risk formula: days_to_departure / (completion_pct / 100)
    Higher score = more risk. Cap at 999 for division-by-zero protection.
    """
    lifecycle = client.get("lifecycle", {})
    departure_str = lifecycle.get("departure_date")
    if not departure_str or departure_str in ("NEEDED", "TBD", None):
        return 0.0
    try:
        departure = date.fromisoformat(str(departure_str))
        days_out = (departure - date.today()).days
        if days_out < 0:
            return 0.0
        if completion_pct <= 0:
            return 999.0
        return round(days_out / (completion_pct / 100), 2)
    except Exception:
        return 0.0


# ── Completion Calculation ────────────────────────────────────────────────────

def calculate_completion(validation_block: dict) -> float:
    """Calculate completion % from 18 validation categories."""
    cats = validation_block.get("categories", [])
    if not cats:
        return 0.0
    total = sum(STATUS_WEIGHT.get(c.get("status", "missing"), 0.0) for c in cats)
    return round((total / len(cats)) * 100, 1)


# ── Per-Client HTML Report ────────────────────────────────────────────────────

def generate_client_report_html(client: dict, month_str: str) -> str:
    """Generate HTML validation report for one client."""
    client_names = client.get("client_names", "Unknown")
    client_id = client.get("client_id", "unknown")
    validation = client.get("validation", {})
    completion_pct = calculate_completion(validation)
    risk_score = calculate_risk_score(client, completion_pct)
    lifecycle = client.get("lifecycle", {})
    departure_str = lifecycle.get("departure_date", "TBD")

    # Risk color
    if risk_score > RISK_THRESHOLD or completion_pct < 75:
        risk_label = "HIGH"
        risk_color = "#da3633"
    elif completion_pct < 90:
        risk_label = "MEDIUM"
        risk_color = "#e36209"
    else:
        risk_label = "LOW"
        risk_color = "#238636"

    # Primary cruise booking
    cruise = next((b for b in client.get("bookings", []) if b.get("booking_type") == "cruise"), {})
    ship = cruise.get("ship", "TBD")
    supplier = cruise.get("supplier", "TBD")

    # Category rows
    cats = {c.get("category"): c for c in validation.get("categories", [])}
    rows = ""
    missing_items = []
    for cat in CATEGORIES:
        info = cats.get(cat, {})
        status = info.get("status", "missing")
        notes = info.get("notes", "")
        label = CATEGORY_LABELS.get(cat, cat)
        color = STATUS_COLOR.get(status, "#21262d")
        icon = STATUS_ICON.get(status, "❌")
        rows += f"""
        <tr>
          <td style="padding:8px 12px;border-bottom:1px solid #21262d;color:#e6edf3">{label}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #21262d;color:{color};font-weight:bold">{icon} {status.replace('_', ' ').title()}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #21262d;color:#8b949e;font-size:12px">{notes}</td>
        </tr>"""
        if status == "missing":
            missing_items.append(label)

    # Action items
    action_rows = ""
    for ai in client.get("action_items", []):
        if ai.get("status") not in ("complete", "cancelled"):
            p = ai.get("priority", "P3")
            pc = "#da3633" if "P1" in p else ("#e36209" if "P2" in p else "#8b949e")
            action_rows += f"""
        <tr>
          <td style="padding:8px 12px;border-bottom:1px solid #21262d;color:{pc};font-weight:bold">{p}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #21262d;color:#e6edf3">{ai.get('task','')}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #21262d;color:#8b949e">{ai.get('owner','')}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #21262d;color:#8b949e">{ai.get('due_date','')}</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{client_names} — Validation Report {month_str}</title>
<style>
  body{{background:#0d1117;color:#e6edf3;font-family:'Courier New',monospace;padding:24px;margin:0}}
  h1{{color:#f7f3ea;font-size:20px;border-bottom:2px solid #003087;padding-bottom:12px}}
  h2{{color:#8b949e;font-size:13px;letter-spacing:2px;text-transform:uppercase;margin:24px 0 12px}}
  table{{width:100%;border-collapse:collapse;background:#161b22;border:1px solid #21262d;border-radius:8px;overflow:hidden}}
  th{{background:#21262d;color:#8b949e;padding:8px 12px;text-align:left;font-size:11px;letter-spacing:1px;text-transform:uppercase}}
  .stat-row{{display:flex;gap:16px;margin-bottom:24px;flex-wrap:wrap}}
  .stat{{background:#161b22;border:1px solid #21262d;border-radius:8px;padding:14px 20px;flex:1;min-width:120px}}
  .stat .v{{font-size:28px;font-weight:bold}}
  .stat .l{{font-size:11px;color:#8b949e;margin-top:4px;text-transform:uppercase;letter-spacing:1px}}
  .missing-list{{background:#1a0e0e;border:1px solid #da3633;border-radius:8px;padding:14px 18px;margin-bottom:20px}}
  .missing-list p{{color:#da3633;font-weight:bold;font-size:12px;margin:0 0 8px}}
  .missing-list li{{font-size:12px;color:#c9d1d9;margin:4px 0}}
  .footer{{color:#8b949e;font-size:11px;margin-top:24px;text-align:center;border-top:1px solid #21262d;padding-top:16px}}
</style>
</head>
<body>
<h1>🦅 {client_names} — Validation Report</h1>
<div style="color:#8b949e;font-size:12px;margin-bottom:20px">{supplier} · {ship} · Departure: {departure_str} · Report: {month_str}</div>

<div class="stat-row">
  <div class="stat"><div class="v" style="color:{'#3fb950' if completion_pct >= 90 else '#e36209' if completion_pct >= 75 else '#da3633'}">{completion_pct}%</div><div class="l">Complete</div></div>
  <div class="stat"><div class="v" style="color:{risk_color}">{risk_label}</div><div class="l">Risk Level</div></div>
  <div class="stat"><div class="v">{risk_score}</div><div class="l">Risk Score</div></div>
  <div class="stat"><div class="v" style="color:#da3633">{len(missing_items)}</div><div class="l">Missing Items</div></div>
</div>

{'<div class="missing-list"><p>❌ Missing Items — Action Required</p><ul>' + ''.join(f'<li>{m}</li>' for m in missing_items) + '</ul></div>' if missing_items else ''}

<h2>Validation Checklist (18 Categories)</h2>
<table>
  <thead><tr><th>Category</th><th>Status</th><th>Notes</th></tr></thead>
  <tbody>{rows}</tbody>
</table>

{'<h2>Open Action Items</h2><table><thead><tr><th>Priority</th><th>Task</th><th>Owner</th><th>Due</th></tr></thead><tbody>' + action_rows + '</tbody></table>' if action_rows else ''}

<div class="footer">
  D2M Validation Report · ETB-004 · Generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC<br>
  Source: Blackboard YAML · /home/john/Thunderbird/Blackboard/clients/{client_id}.yaml
</div>
</body>
</html>"""


# ── Summary JSON ──────────────────────────────────────────────────────────────

def generate_summary_json(results: list) -> dict:
    return {
        "generated": datetime.utcnow().isoformat() + "Z",
        "clients": results,
        "total": len(results),
        "high_risk": sum(1 for r in results if r.get("risk_level") == "HIGH"),
        "medium_risk": sum(1 for r in results if r.get("risk_level") == "MEDIUM"),
        "low_risk": sum(1 for r in results if r.get("risk_level") == "LOW"),
    }


# ── Summary Email HTML ────────────────────────────────────────────────────────

def generate_summary_email_html(results: list, month_str: str) -> str:
    rows = ""
    for r in sorted(results, key=lambda x: x.get("completion_pct", 100)):
        color = "#3fb950" if r["completion_pct"] >= 90 else ("#e36209" if r["completion_pct"] >= 75 else "#da3633")
        risk_color = "#da3633" if r["risk_level"] == "HIGH" else ("#e36209" if r["risk_level"] == "MEDIUM" else "#3fb950")
        rows += f"""
        <tr>
          <td style="padding:8px 12px;border-bottom:1px solid #ddd">{r['client_names']}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #ddd">{r['departure']}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #ddd;color:{color};font-weight:bold">{r['completion_pct']}%</td>
          <td style="padding:8px 12px;border-bottom:1px solid #ddd;color:{risk_color};font-weight:bold">{r['risk_level']}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #ddd;color:#c0392b">{r['missing_count']}</td>
        </tr>"""

    high_risk = [r for r in results if r["risk_level"] == "HIGH"]
    alerts = ""
    if high_risk:
        alerts = f"<p style='color:#c0392b;font-weight:bold'>⚠️ HIGH RISK CLIENTS ({len(high_risk)}):</p><ul>"
        for r in high_risk:
            alerts += f"<li>{r['client_names']} — {r['completion_pct']}% complete — {r['missing_count']} missing items</li>"
        alerts += "</ul>"

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>body{{font-family:Georgia,serif;background:#f7f3ea;color:#003087;max-width:700px;margin:0 auto;padding:24px}}
h1{{color:#003087;border-bottom:2px solid #003087;padding-bottom:10px}}
table{{width:100%;border-collapse:collapse}}th{{background:#003087;color:#f7f3ea;padding:8px 12px;text-align:left}}
</style></head>
<body>
<h1>🦅 D2M Monthly Validation Report — {month_str}</h1>
<p>Wing A-Staff — here is the monthly validation snapshot across all active clients.</p>
{alerts}
<h2>All Clients</h2>
<table>
  <thead><tr><th>Client</th><th>Departure</th><th>Complete %</th><th>Risk</th><th>Missing</th></tr></thead>
  <tbody>{rows}</tbody>
</table>
<p style="margin-top:20px;font-size:12px;color:#888">Generated by ETB-004 Validation Report Generator · {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC</p>
<p style="font-size:12px;color:#888">Review individual client reports in OpsCenter/validations/{month_str}/</p>
</body></html>"""


# ── Audit Logging ─────────────────────────────────────────────────────────────

def audit_log(entry: dict) -> None:
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_LOG, "a") as f:
        f.write(json.dumps({**entry, "timestamp": datetime.utcnow().isoformat() + "Z"}) + "\n")


# ── Main Generator ────────────────────────────────────────────────────────────

def run_generator(dry_run: bool = False, client_filter: Optional[str] = None) -> dict:
    today = date.today()
    month_str = today.strftime("%Y-%m")
    out_dir = VALIDATIONS_DIR / month_str
    out_dir.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    log.info(f"Validation report generator starting — month={month_str} dry_run={dry_run}")

    client_files = sorted(BLACKBOARD_DIR.glob("*.yaml"))
    if client_filter:
        client_files = [f for f in client_files if client_filter in f.stem]

    summary_results = []
    report_paths = []

    for client_file in client_files:
        try:
            with open(client_file) as f:
                client = yaml.safe_load(f)

            if not isinstance(client, dict):
                continue

            client_id = client.get("client_id", client_file.stem)
            status = client.get("status", "")
            if status == "inactive":
                continue

            validation = client.get("validation", {})
            completion_pct = calculate_completion(validation)
            risk_score = calculate_risk_score(client, completion_pct)

            if risk_score > RISK_THRESHOLD or completion_pct < 75:
                risk_level = "HIGH"
            elif completion_pct < 90:
                risk_level = "MEDIUM"
            else:
                risk_level = "LOW"

            cats = {c.get("category"): c for c in validation.get("categories", [])}
            missing_count = sum(1 for cat in CATEGORIES if cats.get(cat, {}).get("status") == "missing")

            lifecycle = client.get("lifecycle", {})
            departure = lifecycle.get("departure_date", "TBD")

            result_entry = {
                "client_id": client_id,
                "client_names": client.get("client_names", "Unknown"),
                "departure": str(departure),
                "completion_pct": completion_pct,
                "risk_score": risk_score,
                "risk_level": risk_level,
                "missing_count": missing_count,
                "report_path": str(out_dir / f"{client_id}_validation.html"),
            }
            summary_results.append(result_entry)

            if not dry_run:
                html = generate_client_report_html(client, month_str)
                report_path = out_dir / f"{client_id}_validation.html"
                report_path.write_text(html)
                report_paths.append(str(report_path))
                log.info(f"{client_id} — {completion_pct}% complete, {risk_level} risk → {report_path}")

            audit_log({
                "event": "client_validated",
                "client_id": client_id,
                "completion_pct": completion_pct,
                "risk_level": risk_level,
                "missing_count": missing_count,
            })

        except Exception as e:
            log.error(f"Error processing {client_file.name}: {e}")
            audit_log({"event": "error", "file": str(client_file), "error": str(e)[:200]})

    summary = generate_summary_json(summary_results)

    if not dry_run:
        # Write validation_summary.json
        summary_path = DATA_DIR / "validation_summary.json"
        summary_path.write_text(json.dumps(summary, indent=2))
        log.info(f"Summary JSON written: {summary_path}")

        # Create Gmail draft with summary email
        try:
            sys.path.insert(0, str(THUNDERBIRD_ROOT / "core" / "email"))
            from thunderbird_gmail import gmail_create_draft_sync

            summary_html = generate_summary_email_html(summary_results, month_str)
            draft = gmail_create_draft_sync(
                to="johnloucks3@gmail.com",
                subject=f"D2M Monthly Validation Report — {month_str}",
                body=summary_html
            )
            if draft:
                log.info(f"Summary email draft created: {draft.get('id')}")
                audit_log({"event": "summary_draft_created", "draft_id": draft.get("id"), "month": month_str})
        except Exception as e:
            log.warning(f"Summary email draft failed (non-critical): {e}")

    summary["report_paths"] = report_paths
    log.info(f"Generator complete: {len(summary_results)} clients processed")
    audit_log({"event": "generator_complete", "month": month_str, "clients": len(summary_results)})
    return summary


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="D2M Validation Report Generator — ETB-004")
    parser.add_argument("--dry-run", action="store_true", help="Calculate without writing reports")
    parser.add_argument("--client", help="Filter to specific client_id")
    args = parser.parse_args()

    result = run_generator(dry_run=args.dry_run, client_filter=args.client)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
