#!/usr/bin/env python3
"""
ETB-006: D2M HTML Status Dashboard Generator
=============================================
Reads Blackboard client YAML every 30 min, calculates metrics,
renders HTML dashboard, writes to output/d2m-dashboard/index.html.

Accessible at: itinerary.d2mluxury.quest/d2m-dashboard/
Schedule: Systemd timer every 30 min, 0600-2200 MT

Usage: python3 dashboard_generator.py [--once]
"""

import sys
import json
import yaml
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Optional

# ── Paths ─────────────────────────────────────────────────────────────────────
BLACKBOARD_DIR = Path("/home/john/Thunderbird/Blackboard/clients")
OUTPUT_DIR = Path("/home/john/Thunderbird/output/d2m-dashboard")
AUDIT_LOG = Path("/home/john/Thunderbird/OpsCenter/logs/dashboard_audit.jsonl")
VALIDATION_SUMMARY = Path("/home/john/Thunderbird/OpsCenter/data/validation_summary.json")

RISK_THRESHOLD = 120.0  # days_out / (pct/100) > 120 = HIGH risk

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [DASHBOARD] %(levelname)s %(message)s",
    handlers=[logging.StreamHandler()]
)
log = logging.getLogger(__name__)

CATEGORIES = [
    "flights_outbound", "flights_return", "hotel_pre", "hotel_post",
    "cruise", "transfers_inbound", "transfers_outbound", "excursions",
    "dining_specialty", "insurance", "visas", "passports", "vaccinations",
    "emergency_contacts", "financial", "crew_comms", "client_comms", "post_travel"
]

STATUS_WEIGHT = {"confirmed": 1.0, "not_applicable": 1.0, "pending": 0.5, "missing": 0.0}
CATEGORY_SHORT = {
    "flights_outbound": "✈ Out", "flights_return": "✈ Ret",
    "hotel_pre": "🏨 Pre", "hotel_post": "🏨 Post",
    "cruise": "🚢 Cruise", "transfers_inbound": "🚗 In",
    "transfers_outbound": "🚗 Out", "excursions": "🗺 Excur",
    "dining_specialty": "🍽 Dining", "insurance": "🛡 Insur",
    "visas": "📋 Visas", "passports": "🛂 Pass",
    "vaccinations": "💉 Vacc", "emergency_contacts": "🆘 Emerg",
    "financial": "💰 $$$", "crew_comms": "🚢 Reg",
    "client_comms": "📧 Comms", "post_travel": "🏠 Post",
}


def calculate_completion(validation_block: dict) -> float:
    cats = validation_block.get("categories", [])
    if not cats:
        return 0.0
    total = sum(STATUS_WEIGHT.get(c.get("status", "missing"), 0.0) for c in cats)
    return round((total / len(cats)) * 100, 1)


def calculate_risk(client: dict, completion_pct: float) -> tuple:
    lifecycle = client.get("lifecycle", {})
    dep_str = lifecycle.get("departure_date")
    if not dep_str or str(dep_str) in ("NEEDED", "TBD", "null", "None"):
        return 0.0, "—", "#8b949e", 0
    try:
        dep = date.fromisoformat(str(dep_str))
        days = (dep - date.today()).days
        if days < 0:
            return 0.0, "PAST", "#8b949e", days
        if completion_pct <= 0:
            score = 999.0
        else:
            score = round(days / (completion_pct / 100), 2)
        if score > RISK_THRESHOLD or completion_pct < 75:
            label, color = "HIGH", "#da3633"
        elif completion_pct < 90:
            label, color = "MED", "#e36209"
        else:
            label, color = "LOW", "#238636"
        return score, label, color, days
    except Exception:
        return 0.0, "?", "#8b949e", 0


def get_overdue_phases(client: dict) -> list:
    overdue = []
    lifecycle = client.get("lifecycle", {})
    today = date.today()
    for phase in lifecycle.get("phases", []):
        if phase.get("status") == "scheduled":
            due_str = phase.get("due_date")
            if due_str and str(due_str) not in ("NEEDED", "TBD", "null", "None"):
                try:
                    if date.fromisoformat(str(due_str)) < today:
                        overdue.append(phase.get("phase_id", "?"))
                except Exception:
                    pass
    return overdue


def get_critical_items(clients_data: list) -> list:
    """Return action items due within 14 days."""
    critical = []
    cutoff = date.today()
    import datetime as dt
    two_weeks = cutoff + dt.timedelta(days=14)
    for cd in clients_data:
        for ai in cd["client"].get("action_items", []):
            if ai.get("status") not in ("complete", "cancelled"):
                due_str = ai.get("due_date")
                if due_str and str(due_str) not in ("NEEDED", "TBD", "null", "None"):
                    try:
                        due = date.fromisoformat(str(due_str))
                        if cutoff <= due <= two_weeks:
                            critical.append({
                                "client": cd["client_names"],
                                "task": ai.get("task", ""),
                                "priority": ai.get("priority", "P3"),
                                "owner": ai.get("owner", "?"),
                                "due": str(due),
                            })
                    except Exception:
                        pass
    return sorted(critical, key=lambda x: (x["priority"], x["due"]))


def render_dashboard(clients_data: list) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M MT")
    today = date.today()

    # Client rows
    client_rows = ""
    for cd in sorted(clients_data, key=lambda x: x["days_out"] if isinstance(x["days_out"], int) else 9999):
        cn = cd["client_names"]
        dep = cd["departure"]
        pct = cd["completion_pct"]
        risk_label = cd["risk_label"]
        risk_color = cd["risk_color"]
        days = cd["days_out"]
        missing = cd["missing_count"]
        overdue = cd["overdue_phases"]
        cid = cd["client_id"]
        status_str = cd["status"]

        pct_color = "#3fb950" if pct >= 90 else ("#e36209" if pct >= 75 else "#da3633")
        days_str = f"{days}d" if isinstance(days, int) and days >= 0 else ("PAST" if isinstance(days, int) else "TBD")

        # Mini validation bar (18 cells)
        bar_cells = ""
        cats = {c.get("category"): c for c in cd["client"].get("validation", {}).get("categories", [])}
        for cat in CATEGORIES:
            s = cats.get(cat, {}).get("status", "missing")
            sc = "#238636" if s in ("confirmed", "not_applicable") else ("#e36209" if s == "pending" else "#da3633")
            short = CATEGORY_SHORT.get(cat, cat[:4])
            bar_cells += f'<span title="{short}" style="display:inline-block;width:10px;height:10px;background:{sc};border-radius:2px;margin:1px"></span>'

        overdue_badge = f' <span style="background:#da3633;color:#fff;font-size:9px;padding:1px 5px;border-radius:10px">{len(overdue)} overdue</span>' if overdue else ""

        client_rows += f"""
      <tr onclick="toggleDetail('{cid}')" style="cursor:pointer">
        <td style="padding:10px 14px;border-bottom:1px solid #21262d">
          <div style="font-weight:bold;color:#f7f3ea">{cn}</div>
          <div style="font-size:11px;color:#8b949e;margin-top:2px">{bar_cells}{overdue_badge}</div>
        </td>
        <td style="padding:10px 14px;border-bottom:1px solid #21262d;color:#8b949e;white-space:nowrap">{dep}</td>
        <td style="padding:10px 14px;border-bottom:1px solid #21262d;color:#8b949e;white-space:nowrap">{days_str}</td>
        <td style="padding:10px 14px;border-bottom:1px solid #21262d;color:{pct_color};font-weight:bold">{pct}%</td>
        <td style="padding:10px 14px;border-bottom:1px solid #21262d;color:{risk_color};font-weight:bold">{risk_label}</td>
        <td style="padding:10px 14px;border-bottom:1px solid #21262d;color:#da3633">{missing}</td>
        <td style="padding:10px 14px;border-bottom:1px solid #21262d;color:#8b949e;font-size:12px">{status_str}</td>
      </tr>
      <tr id="detail-{cid}" style="display:none">
        <td colspan="7" style="padding:0;border-bottom:2px solid #0000ff">
          <div style="background:#0d2040;padding:16px 14px">
            {render_client_detail(cd)}
          </div>
        </td>
      </tr>"""

    # Critical items section
    critical = get_critical_items(clients_data)
    critical_rows = ""
    for ci in critical:
        pc = "#da3633" if "P1" in ci["priority"] else ("#e36209" if "P2" in ci["priority"] else "#8b949e")
        critical_rows += f"""
      <tr>
        <td style="padding:8px 12px;border-bottom:1px solid #21262d;color:{pc};font-weight:bold">{ci['priority']}</td>
        <td style="padding:8px 12px;border-bottom:1px solid #21262d;color:#e6edf3">{ci['client']}</td>
        <td style="padding:8px 12px;border-bottom:1px solid #21262d;color:#c9d1d9;font-size:12px">{ci['task']}</td>
        <td style="padding:8px 12px;border-bottom:1px solid #21262d;color:#8b949e">{ci['owner']}</td>
        <td style="padding:8px 12px;border-bottom:1px solid #21262d;color:#8b949e">{ci['due']}</td>
      </tr>"""

    high_risk_count = sum(1 for cd in clients_data if cd["risk_label"] == "HIGH")
    avg_pct = round(sum(cd["completion_pct"] for cd in clients_data) / len(clients_data), 1) if clients_data else 0

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="1800">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>D2M Status Dashboard</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#0d1117;color:#e6edf3;font-family:'Courier New',monospace;padding:16px;min-height:100vh}}
.hdr{{border-bottom:2px solid #003087;padding-bottom:12px;margin-bottom:20px;display:flex;justify-content:space-between;align-items:flex-end;flex-wrap:wrap;gap:8px}}
.hdr h1{{color:#f7f3ea;font-size:18px;letter-spacing:2px}}
.hdr .ts{{color:#8b949e;font-size:11px}}
.stats{{display:flex;gap:12px;margin-bottom:20px;flex-wrap:wrap}}
.stat{{background:#161b22;border:1px solid #21262d;border-radius:8px;padding:12px 16px;flex:1;min-width:100px}}
.stat .v{{font-size:24px;font-weight:bold;color:#f7f3ea}}
.stat .l{{font-size:10px;color:#8b949e;margin-top:3px;text-transform:uppercase;letter-spacing:1px}}
table{{width:100%;border-collapse:collapse;background:#161b22;border:1px solid #21262d;border-radius:8px;overflow:hidden;margin-bottom:20px}}
th{{background:#21262d;color:#8b949e;padding:8px 14px;text-align:left;font-size:10px;letter-spacing:1px;text-transform:uppercase}}
tr:hover td{{background:#1c2128}}
h2{{color:#8b949e;font-size:11px;letter-spacing:2px;text-transform:uppercase;margin-bottom:12px}}
.section{{margin-bottom:24px}}
.warn{{background:#1a1000;border:1px solid #e36209;border-radius:8px;padding:12px 16px;margin-bottom:16px;font-size:12px;color:#e36209}}
.footer{{color:#8b949e;font-size:10px;text-align:center;border-top:1px solid #21262d;padding-top:12px;margin-top:24px}}
@media(max-width:600px){{.stats{{flex-direction:column}}.hdr{{flex-direction:column}}}}
</style>
<script>
function toggleDetail(id){{
  var r=document.getElementById('detail-'+id);
  r.style.display=r.style.display==='none'?'table-row':'none';
}}
</script>
</head>
<body>
<div class="hdr">
  <h1>🦅 D2M STATUS DASHBOARD</h1>
  <div class="ts">Updated: {now} · Auto-refresh: 30min · ETB-006</div>
</div>

<div class="stats">
  <div class="stat"><div class="v">{len(clients_data)}</div><div class="l">Active Clients</div></div>
  <div class="stat"><div class="v" style="color:{'#da3633' if high_risk_count>0 else '#3fb950'}">{high_risk_count}</div><div class="l">High Risk</div></div>
  <div class="stat"><div class="v" style="color:{'#3fb950' if avg_pct>=85 else '#e36209'}">{avg_pct}%</div><div class="l">Avg Complete</div></div>
  <div class="stat"><div class="v">{len(critical)}</div><div class="l">Due 14d</div></div>
</div>

{'<div class="warn">⚠️ HIGH RISK CLIENTS: ' + ', '.join(cd["client_names"] for cd in clients_data if cd["risk_label"]=="HIGH") + '</div>' if high_risk_count > 0 else ''}

<div class="section">
<h2>All Clients (click to expand)</h2>
<table>
  <thead><tr>
    <th>Client</th><th>Departure</th><th>Days Out</th>
    <th>Complete</th><th>Risk</th><th>Missing</th><th>Status</th>
  </tr></thead>
  <tbody>{client_rows}</tbody>
</table>
</div>

{'<div class="section"><h2>Critical Items — Due Within 14 Days</h2><table><thead><tr><th>Priority</th><th>Client</th><th>Task</th><th>Owner</th><th>Due</th></tr></thead><tbody>' + critical_rows + '</tbody></table></div>' if critical_rows else ''}

<div class="footer">
  🦅 Thunderbird Wing · Dreams2Memories Travel, LLC · ETB-006<br>
  Source: /home/john/Thunderbird/Blackboard/clients/ · Refresh: 30 min<br>
  <a href="../ETB_PROGRESS.html" style="color:#0000ff">Build Progress</a>
</div>
</body>
</html>"""


def render_client_detail(cd: dict) -> str:
    client = cd["client"]
    cats = {c.get("category"): c for c in client.get("validation", {}).get("categories", [])}

    cat_html = ""
    for cat in CATEGORIES:
        info = cats.get(cat, {})
        s = info.get("status", "missing")
        notes = info.get("notes", "")
        short = CATEGORY_SHORT.get(cat, cat)
        color = "#3fb950" if s in ("confirmed","not_applicable") else ("#e36209" if s=="pending" else "#da3633")
        icon = "✅" if s in ("confirmed","not_applicable") else ("⚠️" if s=="pending" else "❌")
        cat_html += f'<div style="display:flex;gap:8px;padding:4px 0;border-bottom:1px solid #1c2a40;font-size:11px"><span style="color:{color};width:18px">{icon}</span><span style="width:120px;color:#c9d1d9">{short}</span><span style="color:#8b949e">{notes[:80]}</span></div>'

    action_html = ""
    for ai in client.get("action_items", []):
        if ai.get("status") not in ("complete","cancelled"):
            p = ai.get("priority","P3")
            pc = "#da3633" if "P1" in p else ("#e36209" if "P2" in p else "#8b949e")
            action_html += f'<div style="font-size:11px;padding:3px 0;color:{pc}">{p} · {ai.get("task","")[:80]} [{ai.get("owner","")}] due {ai.get("due_date","")}</div>'

    lifecycle = client.get("lifecycle", {})
    overdue = cd["overdue_phases"]
    overdue_html = f'<div style="color:#da3633;font-size:11px">Overdue TPs: {", ".join(overdue)}</div>' if overdue else ""

    primary_cruise = next((b for b in client.get("bookings",[]) if b.get("booking_type")=="cruise"),{})
    booking_html = f'<div style="font-size:12px;color:#c9d1d9">{primary_cruise.get("supplier","")} · {primary_cruise.get("ship","")} · Booking: {primary_cruise.get("booking_id","")} · {primary_cruise.get("payment_status","")}</div>'

    return f"""
<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;flex-wrap:wrap">
  <div>
    <div style="color:#8b949e;font-size:10px;letter-spacing:1px;text-transform:uppercase;margin-bottom:6px">BOOKING</div>
    {booking_html}
    {overdue_html}
    <div style="margin-top:12px;color:#8b949e;font-size:10px;letter-spacing:1px;text-transform:uppercase;margin-bottom:6px">VALIDATION</div>
    {cat_html}
  </div>
  <div>
    <div style="color:#8b949e;font-size:10px;letter-spacing:1px;text-transform:uppercase;margin-bottom:6px">ACTION ITEMS</div>
    {action_html if action_html else '<div style="color:#8b949e;font-size:11px">No open action items</div>'}
  </div>
</div>"""


def load_clients() -> list:
    if not BLACKBOARD_DIR.exists():
        return []
    clients_data = []
    for f in sorted(BLACKBOARD_DIR.glob("*.yaml")):
        try:
            with open(f) as fh:
                client = yaml.safe_load(fh)
            if not isinstance(client, dict):
                continue
            if client.get("status") == "inactive":
                continue

            validation = client.get("validation", {})
            completion_pct = calculate_completion(validation)
            risk_score, risk_label, risk_color, days_out = calculate_risk(client, completion_pct)

            cats = {c.get("category"): c for c in validation.get("categories", [])}
            missing_count = sum(1 for cat in CATEGORIES if cats.get(cat, {}).get("status") == "missing")
            overdue_phases = get_overdue_phases(client)

            lifecycle = client.get("lifecycle", {})
            dep = lifecycle.get("departure_date", "TBD")

            clients_data.append({
                "client_id": client.get("client_id", f.stem),
                "client_names": client.get("client_names", "Unknown"),
                "departure": str(dep),
                "days_out": days_out,
                "completion_pct": completion_pct,
                "risk_score": risk_score,
                "risk_label": risk_label,
                "risk_color": risk_color,
                "missing_count": missing_count,
                "overdue_phases": overdue_phases,
                "status": client.get("status", ""),
                "client": client,
            })
        except Exception as e:
            log.error(f"Error loading {f.name}: {e}")
    return clients_data


def generate():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)

    clients_data = load_clients()
    if not clients_data:
        log.warning("No client data found — dashboard will show empty state")

    html = render_dashboard(clients_data)
    out_path = OUTPUT_DIR / "index.html"
    out_path.write_text(html)

    log.info(f"Dashboard written: {out_path} ({len(clients_data)} clients)")

    audit_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "event": "dashboard_generated",
        "clients": len(clients_data),
        "high_risk": sum(1 for c in clients_data if c["risk_label"] == "HIGH"),
        "output": str(out_path),
    }
    with open(AUDIT_LOG, "a") as f:
        f.write(json.dumps(audit_entry) + "\n")

    return out_path


def main():
    import argparse
    parser = argparse.ArgumentParser(description="D2M Dashboard Generator — ETB-006")
    parser.add_argument("--once", action="store_true", help="Generate once and exit")
    args = parser.parse_args()

    path = generate()
    print(f"Dashboard generated: {path}")


if __name__ == "__main__":
    main()
