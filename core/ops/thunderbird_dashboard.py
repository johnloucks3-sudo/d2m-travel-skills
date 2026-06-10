#!/usr/bin/env python3
"""
Thunderbird Dashboard — Dreams2Memories Travel, LLC
=====================================================
Mobile-friendly Flask dashboard for D2M operations.

Serves at /dashboard with payment alerts, active bookings,
recent actions, and scheduler status.

Usage:
  python3 thunderbird_dashboard.py              # Default port 8766
  python3 thunderbird_dashboard.py --port 9000  # Custom port
"""

import argparse
import logging
import re
import sys
from datetime import date, datetime
from pathlib import Path

from flask import Flask, render_template_string, abort

# Add project root
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

THUNDERBIRD_DIR = Path(__file__).parent
DOSSIER_DIR = THUNDERBIRD_DIR / "Dossiers"
CREDENTIALS_FILE = THUNDERBIRD_DIR / "credentials.json"
SHEET_ID = "1GFjUe8RvP-GT4YHGn0DYv_BEAZGXlYfwEicFrm8ANuU"

# Import DEADLINES from payment alerts
from thunderbird_payment_alerts import DEADLINES

app = Flask(__name__)

# ============================================================================
# DATA HELPERS
# ============================================================================

def _get_sheets_client():
    """Get authenticated gspread client."""
    import gspread
    from google.oauth2 import service_account as sa
    creds = sa.Credentials.from_service_account_file(
        str(CREDENTIALS_FILE),
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    )
    return gspread.authorize(creds)


def _load_bookings():
    """Read Booking Master tab from Google Sheets."""
    try:
        gc = _get_sheets_client()
        ws = gc.open_by_key(SHEET_ID).worksheet("Booking Master")
        rows = ws.get_all_records()
        return rows
    except Exception as e:
        logger.error(f"Failed to load bookings: {e}")
        return []


def _load_action_tracker():
    """Read recent items from Action_Tracker tab."""
    try:
        gc = _get_sheets_client()
        ws = gc.open_by_key(SHEET_ID).worksheet("Action_Tracker")
        rows = ws.get_all_records()
        # Return last 10, newest first
        return list(reversed(rows[-10:])) if rows else []
    except Exception as e:
        logger.warning(f"Action_Tracker not available: {e}")
        return []


def _load_deadlines():
    """Process DEADLINES into display-ready dicts with urgency levels."""
    today = date.today()
    results = []
    for d in DEADLINES:
        deadline_date = date.fromisoformat(d["date"])
        days_left = (deadline_date - today).days

        if d["amount"] in ("PAID", "TBD"):
            urgency = "paid" if d["amount"] == "PAID" else "tbd"
        elif days_left < 0:
            urgency = "overdue"
        elif days_left <= 3:
            urgency = "critical"
        elif days_left <= 7:
            urgency = "warning"
        elif days_left <= 14:
            urgency = "caution"
        else:
            urgency = "ok"

        results.append({
            "client": d["client"],
            "cruise": d["cruise"],
            "conf": d["conf"],
            "date": d["date"],
            "date_display": deadline_date.strftime("%b %d, %Y"),
            "amount": d["amount"],
            "days_left": days_left,
            "urgency": urgency,
            "note": d.get("note", ""),
        })

    # Sort: overdue first, then by days_left ascending
    results.sort(key=lambda x: (
        0 if x["urgency"] == "overdue" else
        1 if x["urgency"] == "critical" else
        2 if x["urgency"] == "warning" else
        3 if x["urgency"] == "caution" else
        4 if x["urgency"] == "ok" else
        5 if x["urgency"] == "tbd" else 6,
        x["days_left"]
    ))
    return results


def _load_dossiers():
    """Load summary info from each dossier .md file."""
    dossiers = []
    if not DOSSIER_DIR.exists():
        return dossiers
    for md_file in sorted(DOSSIER_DIR.glob("*.md")):
        text = md_file.read_text(encoding="utf-8", errors="replace")
        # Extract header line
        title = ""
        status = ""
        cruise = ""
        dates = ""
        for line in text.split("\n"):
            if line.startswith("# CLIENT DOSSIER"):
                title = line.replace("# CLIENT DOSSIER — ", "").strip()
            elif line.startswith("## "):
                cruise = line.replace("## ", "").strip()
            elif "STATUS:" in line:
                status = line.split("STATUS:")[-1].strip().rstrip(" |")
                # Clean markdown bold
                status = status.replace("**", "")
            if title and cruise and status:
                break
        # Count open action items
        open_items = len(re.findall(r'^\d+\.\s*\[ \]', text, re.MULTILINE))
        done_items = len(re.findall(r'^\d+\.\s*\[x\]', text, re.MULTILINE))

        dossiers.append({
            "filename": md_file.stem,
            "title": title or md_file.stem,
            "cruise": cruise,
            "status": status,
            "open_items": open_items,
            "done_items": done_items,
            "total_items": open_items + done_items,
        })
    return dossiers


def _load_dossier_detail(name):
    """Load a specific dossier by filename stem."""
    md_file = DOSSIER_DIR / f"{name}.md"
    if not md_file.exists():
        # Try fuzzy match
        for f in DOSSIER_DIR.glob("*.md"):
            if name.lower() in f.stem.lower():
                md_file = f
                break
    if not md_file.exists():
        return None
    return md_file.read_text(encoding="utf-8", errors="replace")


def _get_scheduler_status():
    """Check for scheduled jobs (cron or systemd timers)."""
    import subprocess
    jobs = []
    # Check crontab
    try:
        result = subprocess.run(
            ["crontab", "-l"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                line = line.strip()
                if line and not line.startswith("#"):
                    jobs.append({"type": "cron", "schedule": line[:30], "command": line[30:].strip()[:60]})
    except Exception:
        pass
    # Check systemd user timers
    try:
        result = subprocess.run(
            ["systemctl", "--user", "list-timers", "--no-pager", "--plain"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n")[1:]:  # skip header
                parts = line.split()
                if len(parts) >= 2:
                    jobs.append({"type": "timer", "schedule": " ".join(parts[:3]), "command": parts[-1] if parts else ""})
    except Exception:
        pass
    # Check d2m systemd services
    for svc in ["d2m-mcp", "d2m-api", "thunderbird-tunnel"]:
        try:
            result = subprocess.run(
                ["systemctl", "--user", "is-active", f"{svc}.service"],
                capture_output=True, text=True, timeout=5
            )
            status = result.stdout.strip()
            jobs.append({"type": "service", "schedule": status, "command": f"{svc}.service"})
        except Exception:
            jobs.append({"type": "service", "schedule": "unknown", "command": f"{svc}.service"})
    return jobs


# ============================================================================
# HTML TEMPLATE
# ============================================================================

DASHBOARD_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>D2M Dashboard — Dreams2Memories Travel</title>
<style>
  :root {
    --navy: #0d1b2e;
    --navy2: #152540;
    --navy3: #1e3358;
    --gold: #c9a84c;
    --gold-light: #e8c97a;
    --gold-pale: #f5e9c8;
    --muted: #8a9ab5;
    --white: #f0f0f0;
    --red: #e74c3c;
    --orange: #f39c12;
    --yellow: #f1c40f;
    --green: #27ae60;
    --blue: #3498db;
  }

  * { margin: 0; padding: 0; box-sizing: border-box; }

  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, sans-serif;
    background: var(--navy);
    color: var(--white);
    min-height: 100vh;
    line-height: 1.5;
  }

  header {
    background: linear-gradient(135deg, var(--navy2), var(--navy3));
    border-bottom: 3px solid var(--gold);
    padding: 16px 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 8px;
  }

  header h1 {
    font-size: 1.3rem;
    font-weight: 700;
    color: var(--gold);
    letter-spacing: 0.5px;
  }

  header .subtitle {
    font-size: 0.8rem;
    color: var(--muted);
  }

  header .timestamp {
    font-size: 0.75rem;
    color: var(--muted);
  }

  .container {
    max-width: 900px;
    margin: 0 auto;
    padding: 16px;
  }

  .section {
    margin-bottom: 24px;
  }

  .section-title {
    font-size: 1rem;
    font-weight: 700;
    color: var(--gold);
    text-transform: uppercase;
    letter-spacing: 1px;
    border-bottom: 1px solid var(--navy3);
    padding-bottom: 8px;
    margin-bottom: 12px;
  }

  /* Cards */
  .card {
    background: var(--navy2);
    border: 1px solid var(--navy3);
    border-radius: 8px;
    padding: 14px 16px;
    margin-bottom: 10px;
    transition: border-color 0.2s;
  }

  .card:hover {
    border-color: var(--gold);
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 6px;
  }

  .card-title {
    font-weight: 600;
    font-size: 0.95rem;
    color: var(--white);
  }

  .card-meta {
    font-size: 0.8rem;
    color: var(--muted);
  }

  .card-body {
    font-size: 0.85rem;
    color: var(--muted);
  }

  /* Badges */
  .badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .badge-critical { background: var(--red); color: #fff; }
  .badge-overdue { background: #8b0000; color: #fff; }
  .badge-warning { background: var(--orange); color: #000; }
  .badge-caution { background: var(--yellow); color: #000; }
  .badge-ok { background: var(--green); color: #fff; }
  .badge-paid { background: var(--blue); color: #fff; }
  .badge-tbd { background: var(--navy3); color: var(--muted); border: 1px solid var(--muted); }
  .badge-active { background: var(--green); color: #fff; }
  .badge-inactive { background: var(--red); color: #fff; }

  /* Amount display */
  .amount {
    font-weight: 700;
    color: var(--gold-light);
    font-size: 1rem;
  }

  .days-left {
    font-weight: 700;
    font-size: 0.85rem;
  }

  .days-critical { color: var(--red); }
  .days-warning { color: var(--orange); }
  .days-caution { color: var(--yellow); }
  .days-ok { color: var(--green); }

  /* Countdown strip */
  .countdown {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }

  /* Payment grid */
  .payment-row {
    display: grid;
    grid-template-columns: 1fr auto auto;
    gap: 8px;
    align-items: center;
  }

  /* Dossier link */
  a.dossier-link {
    color: var(--gold);
    text-decoration: none;
    border-bottom: 1px dotted var(--gold);
  }

  a.dossier-link:hover {
    color: var(--gold-light);
    border-bottom-color: var(--gold-light);
  }

  /* Progress bar for action items */
  .progress-bar {
    height: 4px;
    background: var(--navy3);
    border-radius: 2px;
    margin-top: 6px;
    overflow: hidden;
  }

  .progress-fill {
    height: 100%;
    background: var(--gold);
    border-radius: 2px;
    transition: width 0.3s;
  }

  /* Scheduler table */
  .sched-table {
    width: 100%;
    font-size: 0.8rem;
    border-collapse: collapse;
  }

  .sched-table th {
    text-align: left;
    color: var(--gold);
    padding: 6px 8px;
    border-bottom: 1px solid var(--navy3);
    font-weight: 600;
    font-size: 0.75rem;
    text-transform: uppercase;
  }

  .sched-table td {
    padding: 6px 8px;
    border-bottom: 1px solid var(--navy3);
    color: var(--muted);
    word-break: break-all;
  }

  /* Dossier detail */
  .dossier-content {
    background: var(--navy2);
    border: 1px solid var(--navy3);
    border-radius: 8px;
    padding: 20px;
    font-size: 0.85rem;
    line-height: 1.7;
    color: var(--white);
    overflow-x: auto;
  }

  .dossier-content h1 { color: var(--gold); font-size: 1.2rem; margin: 16px 0 8px; }
  .dossier-content h2 { color: var(--gold-light); font-size: 1rem; margin: 14px 0 6px; }
  .dossier-content h3 { color: var(--gold); font-size: 0.9rem; margin: 12px 0 6px; }
  .dossier-content strong { color: var(--gold-light); }
  .dossier-content table { border-collapse: collapse; width: 100%; margin: 8px 0; }
  .dossier-content th, .dossier-content td {
    border: 1px solid var(--navy3); padding: 6px 8px; text-align: left; font-size: 0.8rem;
  }
  .dossier-content th { background: var(--navy3); color: var(--gold); }
  .dossier-content blockquote {
    border-left: 3px solid var(--gold); padding-left: 12px; margin: 8px 0; color: var(--muted); font-style: italic;
  }
  .dossier-content code { background: var(--navy3); padding: 2px 6px; border-radius: 3px; font-size: 0.8rem; }
  .dossier-content hr { border: none; border-top: 1px solid var(--navy3); margin: 16px 0; }

  .back-link {
    display: inline-block;
    color: var(--gold);
    text-decoration: none;
    font-size: 0.85rem;
    margin-bottom: 16px;
    border-bottom: 1px dotted var(--gold);
  }

  .back-link:hover { color: var(--gold-light); }

  /* Stats strip */
  .stats-strip {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 10px;
    margin-bottom: 20px;
  }

  .stat-box {
    background: var(--navy2);
    border: 1px solid var(--navy3);
    border-radius: 8px;
    padding: 12px;
    text-align: center;
  }

  .stat-number {
    font-size: 1.6rem;
    font-weight: 700;
    color: var(--gold-light);
  }

  .stat-label {
    font-size: 0.7rem;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  /* Responsive */
  @media (max-width: 600px) {
    header h1 { font-size: 1.1rem; }
    .payment-row { grid-template-columns: 1fr; gap: 4px; }
    .stats-strip { grid-template-columns: repeat(2, 1fr); }
  }
</style>
</head>
<body>
<header>
  <div>
    <h1>Dreams2Memories Travel</h1>
    <div class="subtitle">Thunderbird Operations Dashboard</div>
  </div>
  <div class="timestamp">{{ now }}</div>
</header>

<div class="container">

  <!-- Stats Strip -->
  <div class="stats-strip">
    <div class="stat-box">
      <div class="stat-number">{{ deadlines | selectattr('urgency', 'in', ['critical','overdue','warning','caution','ok']) | list | length }}</div>
      <div class="stat-label">Active Payments</div>
    </div>
    <div class="stat-box">
      <div class="stat-number">{{ deadlines | selectattr('urgency', 'equalto', 'critical') | list | length + deadlines | selectattr('urgency', 'equalto', 'overdue') | list | length }}</div>
      <div class="stat-label">Urgent</div>
    </div>
    <div class="stat-box">
      <div class="stat-number">{{ dossiers | length }}</div>
      <div class="stat-label">Clients</div>
    </div>
    <div class="stat-box">
      <div class="stat-number">{{ bookings | length }}</div>
      <div class="stat-label">Bookings</div>
    </div>
  </div>

  <!-- Payment Alerts -->
  <div class="section">
    <div class="section-title">Payment Alerts</div>
    {% for d in deadlines %}
    <div class="card">
      <div class="card-header">
        <div>
          <span class="card-title">{{ d.client }}</span>
          <div class="card-meta">{{ d.cruise }} &middot; Conf #{{ d.conf }}</div>
        </div>
        <div class="countdown">
          <span class="amount">{{ d.amount }}</span>
          {% if d.urgency == 'overdue' %}
            <span class="badge badge-overdue">OVERDUE</span>
          {% elif d.urgency == 'critical' %}
            <span class="badge badge-critical">{{ d.days_left }}d</span>
          {% elif d.urgency == 'warning' %}
            <span class="badge badge-warning">{{ d.days_left }}d</span>
          {% elif d.urgency == 'caution' %}
            <span class="badge badge-caution">{{ d.days_left }}d</span>
          {% elif d.urgency == 'ok' %}
            <span class="badge badge-ok">{{ d.days_left }}d</span>
          {% elif d.urgency == 'paid' %}
            <span class="badge badge-paid">PAID</span>
          {% elif d.urgency == 'tbd' %}
            <span class="badge badge-tbd">TBD</span>
          {% endif %}
        </div>
      </div>
      <div class="card-body">
        Due {{ d.date_display }}
        {% if d.days_left >= 0 and d.urgency not in ('paid', 'tbd') %}
          &middot; <span class="days-left days-{{ d.urgency }}">{{ d.days_left }} day{{ 's' if d.days_left != 1 }} remaining</span>
        {% elif d.urgency == 'overdue' %}
          &middot; <span class="days-left days-critical">{{ d.days_left|abs }} day{{ 's' if d.days_left|abs != 1 }} overdue</span>
        {% endif %}
        {% if d.note %} &middot; {{ d.note }}{% endif %}
      </div>
    </div>
    {% endfor %}
  </div>

  <!-- Client Dossiers -->
  <div class="section">
    <div class="section-title">Client Dossiers</div>
    {% for dos in dossiers %}
    <div class="card">
      <div class="card-header">
        <div>
          <a href="/dashboard/client/{{ dos.filename }}" class="dossier-link card-title">{{ dos.title }}</a>
          <div class="card-meta">{{ dos.cruise }}</div>
        </div>
        <div>
          {% if 'URGENT' in dos.status.upper() %}
            <span class="badge badge-critical">URGENT</span>
          {% elif 'ACTIVE' in dos.status.upper() %}
            <span class="badge badge-ok">ACTIVE</span>
          {% elif 'PAID' in dos.status.upper() %}
            <span class="badge badge-paid">PAID</span>
          {% else %}
            <span class="badge badge-tbd">{{ dos.status[:20] }}</span>
          {% endif %}
        </div>
      </div>
      <div class="card-body">
        {{ dos.status }}
        {% if dos.total_items > 0 %}
        <div class="progress-bar">
          <div class="progress-fill" style="width: {{ (dos.done_items / dos.total_items * 100)|int }}%"></div>
        </div>
        <div class="card-meta" style="margin-top:4px">{{ dos.done_items }}/{{ dos.total_items }} action items complete</div>
        {% endif %}
      </div>
    </div>
    {% endfor %}
  </div>

  <!-- Active Bookings (from Sheets) -->
  <div class="section">
    <div class="section-title">Active Bookings</div>
    {% if bookings %}
      {% for b in bookings %}
      <div class="card">
        <div class="card-header">
          <span class="card-title">{{ b.get('Client', b.get('client', 'Unknown')) }}</span>
          <span class="card-meta">{{ b.get('Ship', b.get('ship', '')) }}</span>
        </div>
        <div class="card-body">
          {% for key, val in b.items() %}
            {% if key not in ('Client', 'client', 'Ship', 'ship') and val %}
              <span style="margin-right:12px"><strong style="color:var(--gold)">{{ key }}:</strong> {{ val }}</span>
            {% endif %}
          {% endfor %}
        </div>
      </div>
      {% endfor %}
    {% else %}
      <div class="card"><div class="card-body">No booking data loaded from Sheets (check credentials or connectivity).</div></div>
    {% endif %}
  </div>

  <!-- Recent Actions -->
  <div class="section">
    <div class="section-title">Recent Actions</div>
    {% if actions %}
      {% for a in actions %}
      <div class="card">
        <div class="card-body">
          {% for key, val in a.items() %}
            {% if val %}
              <span style="margin-right:12px"><strong style="color:var(--gold)">{{ key }}:</strong> {{ val }}</span>
            {% endif %}
          {% endfor %}
        </div>
      </div>
      {% endfor %}
    {% else %}
      <div class="card"><div class="card-body">No recent actions tracked.</div></div>
    {% endif %}
  </div>

  <!-- Scheduler Status -->
  <div class="section">
    <div class="section-title">Scheduler &amp; Services</div>
    {% if scheduler %}
    <table class="sched-table">
      <thead><tr><th>Type</th><th>Status / Schedule</th><th>Job</th></tr></thead>
      <tbody>
      {% for j in scheduler %}
        <tr>
          <td>{{ j.type }}</td>
          <td>
            {% if j.schedule == 'active' %}
              <span class="badge badge-active">active</span>
            {% elif j.schedule in ('inactive', 'failed') %}
              <span class="badge badge-inactive">{{ j.schedule }}</span>
            {% else %}
              {{ j.schedule }}
            {% endif %}
          </td>
          <td>{{ j.command }}</td>
        </tr>
      {% endfor %}
      </tbody>
    </table>
    {% else %}
      <div class="card"><div class="card-body">No scheduled jobs detected.</div></div>
    {% endif %}
  </div>

</div>

<script>
  // Auto-refresh every 5 minutes
  setTimeout(function(){ location.reload(); }, 300000);
</script>
</body>
</html>
"""

CLIENT_DETAIL_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{ title }} — D2M Dashboard</title>
<style>
  :root {
    --navy: #0d1b2e;
    --navy2: #152540;
    --navy3: #1e3358;
    --gold: #c9a84c;
    --gold-light: #e8c97a;
    --gold-pale: #f5e9c8;
    --muted: #8a9ab5;
    --white: #f0f0f0;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, sans-serif;
    background: var(--navy);
    color: var(--white);
    min-height: 100vh;
    line-height: 1.5;
  }
  header {
    background: linear-gradient(135deg, var(--navy2), var(--navy3));
    border-bottom: 3px solid var(--gold);
    padding: 16px 20px;
  }
  header h1 {
    font-size: 1.2rem;
    font-weight: 700;
    color: var(--gold);
  }
  .container { max-width: 900px; margin: 0 auto; padding: 16px; }
  .back-link {
    display: inline-block;
    color: var(--gold);
    text-decoration: none;
    font-size: 0.85rem;
    margin-bottom: 16px;
    border-bottom: 1px dotted var(--gold);
  }
  .back-link:hover { color: var(--gold-light); }
  .dossier-content {
    background: var(--navy2);
    border: 1px solid var(--navy3);
    border-radius: 8px;
    padding: 20px;
    font-size: 0.85rem;
    line-height: 1.7;
    color: var(--white);
    overflow-x: auto;
  }
  .dossier-content h1 { color: var(--gold); font-size: 1.2rem; margin: 16px 0 8px; }
  .dossier-content h2 { color: var(--gold-light); font-size: 1rem; margin: 14px 0 6px; }
  .dossier-content h3 { color: var(--gold); font-size: 0.9rem; margin: 12px 0 6px; }
  .dossier-content strong { color: var(--gold-light); }
  .dossier-content table { border-collapse: collapse; width: 100%; margin: 8px 0; font-size: 0.8rem; }
  .dossier-content th, .dossier-content td {
    border: 1px solid var(--navy3); padding: 6px 8px; text-align: left;
  }
  .dossier-content th { background: var(--navy3); color: var(--gold); }
  .dossier-content blockquote {
    border-left: 3px solid var(--gold); padding-left: 12px; margin: 8px 0; color: var(--muted); font-style: italic;
  }
  .dossier-content hr { border: none; border-top: 1px solid var(--navy3); margin: 16px 0; }
  .dossier-content ul, .dossier-content ol { padding-left: 20px; margin: 6px 0; }
  .dossier-content li { margin-bottom: 4px; }
</style>
</head>
<body>
<header>
  <h1>{{ title }}</h1>
</header>
<div class="container">
  <a href="/dashboard" class="back-link">&larr; Back to Dashboard</a>
  <div class="dossier-content">{{ content }}</div>
</div>
</body>
</html>
"""


# ============================================================================
# SIMPLE MARKDOWN -> HTML (no external deps)
# ============================================================================

def _md_to_html(text):
    """Convert basic Markdown to HTML for dossier display."""
    import html as html_mod
    lines = text.split("\n")
    out = []
    in_table = False
    in_blockquote = False
    in_list = False

    for line in lines:
        stripped = line.strip()

        # Close blockquote if needed
        if in_blockquote and not stripped.startswith(">"):
            out.append("</blockquote>")
            in_blockquote = False

        # Close table if needed
        if in_table and not stripped.startswith("|"):
            out.append("</tbody></table>")
            in_table = False

        # Close list if needed
        if in_list and not re.match(r'^\d+\.\s', stripped):
            out.append("</ol>")
            in_list = False

        # Blank line
        if not stripped:
            out.append("<br>")
            continue

        # Headings
        if stripped.startswith("### "):
            out.append(f"<h3>{html_mod.escape(stripped[4:])}</h3>")
            continue
        if stripped.startswith("## "):
            out.append(f"<h2>{html_mod.escape(stripped[3:])}</h2>")
            continue
        if stripped.startswith("# "):
            out.append(f"<h1>{html_mod.escape(stripped[2:])}</h1>")
            continue

        # HR
        if stripped == "---":
            out.append("<hr>")
            continue

        # Blockquote
        if stripped.startswith("> "):
            if not in_blockquote:
                out.append("<blockquote>")
                in_blockquote = True
            out.append(html_mod.escape(stripped[2:]) + "<br>")
            continue

        # Table
        if stripped.startswith("|"):
            cells = [c.strip() for c in stripped.split("|")[1:-1]]
            # Skip separator rows
            if all(re.match(r'^[-:]+$', c) for c in cells):
                continue
            if not in_table:
                out.append("<table><thead><tr>")
                for c in cells:
                    out.append(f"<th>{_inline_md(html_mod.escape(c))}</th>")
                out.append("</tr></thead><tbody>")
                in_table = True
            else:
                out.append("<tr>")
                for c in cells:
                    out.append(f"<td>{_inline_md(html_mod.escape(c))}</td>")
                out.append("</tr>")
            continue

        # Ordered list
        m = re.match(r'^(\d+)\.\s(.+)', stripped)
        if m:
            if not in_list:
                out.append("<ol>")
                in_list = True
            out.append(f"<li>{_inline_md(html_mod.escape(m.group(2)))}</li>")
            continue

        # Regular paragraph
        out.append(f"<p>{_inline_md(html_mod.escape(stripped))}</p>")

    # Close open elements
    if in_blockquote:
        out.append("</blockquote>")
    if in_table:
        out.append("</tbody></table>")
    if in_list:
        out.append("</ol>")

    return "\n".join(out)


def _inline_md(text):
    """Process inline markdown: bold, italic, code."""
    # Bold **text**
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # Italic *text*
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    # Inline code
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    # Checkbox [ ] and [x]
    text = text.replace("[ ]", '<input type="checkbox" disabled>')
    text = text.replace("[x]", '<input type="checkbox" disabled checked>')
    return text


# ============================================================================
# ROUTES
# ============================================================================

@app.route("/dashboard")
def dashboard():
    deadlines = _load_deadlines()
    dossiers = _load_dossiers()
    bookings = _load_bookings()
    actions = _load_action_tracker()
    scheduler = _get_scheduler_status()
    now = datetime.now().strftime("%a %b %d, %Y  %I:%M %p")

    return render_template_string(
        DASHBOARD_TEMPLATE,
        deadlines=deadlines,
        dossiers=dossiers,
        bookings=bookings,
        actions=actions,
        scheduler=scheduler,
        now=now,
    )


@app.route("/dashboard/client/<name>")
def client_detail(name):
    raw = _load_dossier_detail(name)
    if raw is None:
        abort(404, description=f"Dossier '{name}' not found")

    # Extract title from first heading
    title = name
    for line in raw.split("\n"):
        if line.startswith("# "):
            title = line[2:].strip()
            break

    content = _md_to_html(raw)
    return render_template_string(CLIENT_DETAIL_TEMPLATE, title=title, content=content)


@app.route("/")
def root_redirect():
    """Redirect root to dashboard."""
    from flask import redirect
    return redirect("/dashboard")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="D2M Operations Dashboard")
    parser.add_argument("--port", type=int, default=8766, help="Port to serve on (default: 8766)")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind (default: 0.0.0.0)")
    parser.add_argument("--debug", action="store_true", help="Enable Flask debug mode")
    args = parser.parse_args()

    logger.info(f"D2M Dashboard starting on {args.host}:{args.port}")
    logger.info(f"Access at http://localhost:{args.port}/dashboard")
    app.run(host=args.host, port=args.port, debug=args.debug)
