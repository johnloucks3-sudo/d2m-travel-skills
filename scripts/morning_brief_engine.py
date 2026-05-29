#!/usr/bin/env python3
"""
Morning Brief Engine — Auto-Generate hale_brief.md + Email to Commander
=========================================================================
Dreams2Memories Travel, LLC | scripts/morning_brief_engine.py

Runs daily at 06:00 MT via systemd timer. Reads live dossier data,
TP schedule, system health, and draft queue. Writes hale_brief.md and
sends the brief as a full email to johnloucks3@gmail.com.

Usage:
    python3 scripts/morning_brief_engine.py          # Generate + email
    python3 scripts/morning_brief_engine.py --local  # Write file only, no email
    python3 scripts/morning_brief_engine.py --timer  # Silent systemd mode
"""

from __future__ import annotations

import argparse
import base64
import json
import logging
import re
import sys
from datetime import date, datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import yaml

THUNDERBIRD = Path.home() / "Thunderbird"
sys.path.insert(0, str(THUNDERBIRD))
sys.path.insert(0, str(THUNDERBIRD / "core" / "booking"))

from thunderbird_tp_scheduler import (
    scan_dossiers,
    generate_schedule,
    get_actionable_tps,
    TPStatus,
)

GMAIL_TOKEN = THUNDERBIRD / "gmail_token.json"
BRIEF_OUT = THUNDERBIRD / "hale_brief.md"
QUEUE_LOG = THUNDERBIRD / "storage" / "lifecycle_draft_queue.jsonl"
STATE_FILE = THUNDERBIRD / "hale_state.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s BRIEF %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(str(THUNDERBIRD / "logs" / "morning_brief_engine.log"), mode="a"),
    ],
)
logger = logging.getLogger("brief")

SKIP_FILES = {"CLAUDE.md", "DOSSIER_Regent_Tips_Guide.md", "DANI_TESTER_BRIEFINGS.md"}


# ---------------------------------------------------------------------------
# Data readers
# ---------------------------------------------------------------------------

def load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return {}


def load_queue_summary() -> list[dict]:
    if not QUEUE_LOG.exists():
        return []
    entries = []
    for line in QUEUE_LOG.read_text().splitlines():
        try:
            e = json.loads(line)
            if e.get("status") in ("queued", "voice_drafted"):
                entries.append(e)
        except Exception:
            pass
    return entries


def get_client_statuses() -> list[dict]:
    """Read all active dossiers and compute phase + open items."""
    records = scan_dossiers()
    today = date.today()
    statuses = []

    for rec in records:
        if not rec.is_schedulable:
            continue

        # Read extra frontmatter
        meta = {}
        try:
            text = rec.path.read_text(encoding="utf-8")
            m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
            if m:
                meta = yaml.safe_load(m.group(1)) or {}
        except Exception:
            pass

        full_name = meta.get("full_name", rec.client)
        payment_status = meta.get("payment_status", "")
        completed_tps = set(str(t) for t in (meta.get("completed_tps") or []))

        # Compute next due TP
        schedule = generate_schedule(rec, today)
        actionable = get_actionable_tps(schedule, 30, today)
        # Filter completed
        actionable = [tp for tp in actionable if tp.tp_id not in completed_tps]

        next_tp = actionable[0] if actionable else None
        overdue = [tp for tp in actionable if tp.status == TPStatus.OVERDUE]

        days_to_dep = (rec.departure - today).days if rec.departure else None
        fpd_str = rec.fpd.strftime("%-d %b %Y") if rec.fpd else "TBD"

        # FPD status indicator
        if payment_status in ("paid_in_full", "paid", "complete"):
            fpd_label = f"✅ PAID"
        elif rec.fpd:
            days_to_fpd = (rec.fpd - today).days
            if days_to_fpd < 0:
                fpd_label = f"🔴 OVERDUE ({abs(days_to_fpd)}d ago)"
            elif days_to_fpd <= 14:
                fpd_label = f"🟡 DUE {fpd_str} (T-{days_to_fpd}d)"
            else:
                fpd_label = f"DUE {fpd_str}"
        else:
            fpd_label = "TBD"

        statuses.append({
            "client": full_name,
            "ship": f"{rec.cruise_line} {rec.ship}".strip() if rec.ship else rec.cruise_line,
            "departure": rec.departure.strftime("%-d %b %Y") if rec.departure else "TBD",
            "days_to_dep": days_to_dep,
            "fpd_label": fpd_label,
            "next_tp": f"TP {next_tp.tp_id} — {next_tp.label}" if next_tp else "All clear",
            "overdue_count": len(overdue),
        })

    # Sort by days to departure
    statuses.sort(key=lambda s: s.get("days_to_dep") or 9999)
    return statuses


# ---------------------------------------------------------------------------
# Brief generator
# ---------------------------------------------------------------------------

def generate_brief(state: dict, clients: list[dict], queue: list[dict]) -> tuple[str, str]:
    """Returns (markdown_brief, html_brief)."""
    today = date.today()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M MT")
    health = state.get("wing_health", state.get("system_health", {}))
    financial = state.get("financial_pulse", {})

    # --- Client table rows ---
    client_rows_md = []
    client_rows_html = []
    for c in clients:
        dep_flag = ""
        if c.get("days_to_dep") is not None and c["days_to_dep"] <= 14:
            dep_flag = " 🔴"
        overdue_flag = f" ⚠️ {c['overdue_count']} overdue" if c.get("overdue_count") else ""
        client_rows_md.append(
            f"| {c['client']} | {c['ship']} | {c['departure']}{dep_flag} | "
            f"{c['fpd_label']} | {c['next_tp']}{overdue_flag} |"
        )
        dep_color = "#cc0000" if dep_flag else "#1a3557"
        client_rows_html.append(
            f"<tr><td>{c['client']}</td><td>{c['ship']}</td>"
            f"<td style='color:{dep_color}'>{c['departure']}{dep_flag}</td>"
            f"<td>{c['fpd_label']}</td><td>{c['next_tp']}{overdue_flag}</td></tr>"
        )

    # --- WF-17 queue ---
    queue_rows_md = []
    queue_rows_html = []
    for e in queue[:8]:
        queue_rows_md.append(
            f"| {e.get('client')} | TP {e.get('tp_id')} | {e.get('phase_label')} | "
            f"{e.get('deadline', '?')} | {e.get('status')} |"
        )
        queue_rows_html.append(
            f"<tr><td>{e.get('client')}</td><td>TP {e.get('tp_id')}</td>"
            f"<td>{e.get('phase_label')}</td><td>{e.get('deadline','?')}</td>"
            f"<td>{e.get('status')}</td></tr>"
        )

    # --- System health ---
    health_lines_md = []
    for k, v in list(health.items())[:6]:
        if isinstance(v, dict):
            continue
        icon = "✅" if "ONLINE" in str(v).upper() or "LIVE" in str(v).upper() or "RUNNING" in str(v).upper() else "❌" if "OFFLINE" in str(v).upper() else "💤"
        health_lines_md.append(f"| {k} | {icon} {v} |")

    # --- Markdown ---
    client_table = "\n".join([
        "| Client | Ship | Departure | FPD Status | Next TP |",
        "|---|---|---|---|---|",
    ] + client_rows_md) if client_rows_md else "_No active clients_"

    queue_table = "\n".join([
        "| Client | TP | Phase | Deadline | Status |",
        "|---|---|---|---|---|",
    ] + queue_rows_md) if queue_rows_md else "_Queue empty_"

    health_table = "\n".join([
        "| System | Status |",
        "|---|---|",
    ] + health_lines_md) if health_lines_md else "_Health data unavailable_"

    pipeline = financial.get("total_d2m_pipeline", 0)
    tess_received = financial.get("tess_received", 0)

    md = f"""# HALE — Daily Brief
*Generated: {now_str}*

---

🦅

**THUNDERBIRD DAILY BRIEF — {today.isoformat()} · COS MODE**
*— V. Hale, VCS*

---

### 1. CLIENT WIRE

{client_table}

---

### 2. WF-17 GATE — DRAFTS AWAITING COMMANDER REVIEW

{queue_table}

---

### 3. FINANCIAL PULSE

| Metric | Value |
|---|---|
| D2M pipeline | **${pipeline:,.2f}** |
| TESS received | ${tess_received:,.2f} |

---

### 4. WING HEALTH

{health_table}

---

*— V. Hale, VCS · Thunderbird Wing · {now_str}*
*Next brief: {(today + timedelta(days=1)).isoformat()} 06:00 MT*
"""

    # --- HTML ---
    client_table_html = f"""<table style='width:100%;border-collapse:collapse;font-size:13px'>
<tr style='background:#1a3557;color:#fff'><th>Client</th><th>Ship</th><th>Departure</th><th>FPD</th><th>Next TP</th></tr>
{''.join(client_rows_html)}
</table>""" if client_rows_html else "<p><em>No active clients</em></p>"

    queue_table_html = f"""<table style='width:100%;border-collapse:collapse;font-size:13px'>
<tr style='background:#1a3557;color:#fff'><th>Client</th><th>TP</th><th>Phase</th><th>Deadline</th><th>Status</th></tr>
{''.join(queue_rows_html)}
</table>""" if queue_rows_html else "<p><em>Queue empty</em></p>"

    html = f"""<div style="font-family:Georgia,serif;color:#1a3557;background:#f7f3ea;padding:24px;max-width:700px">
<div style="background:#1a3557;color:#fff;padding:12px 16px;margin-bottom:16px">
  <strong>🦅 THUNDERBIRD DAILY BRIEF — {today.isoformat()}</strong><br>
  <small>Generated {now_str} · V. Hale, VCS</small>
</div>

<h3 style="color:#1a3557">1. Client Wire</h3>
{client_table_html}

<h3 style="color:#1a3557">2. WF-17 Gate — Drafts Awaiting Review</h3>
{queue_table_html}

<h3 style="color:#1a3557">3. Financial Pulse</h3>
<table style='font-size:13px'><tr><td><strong>D2M pipeline</strong></td><td><strong>${pipeline:,.2f}</strong></td></tr>
<tr><td>TESS received</td><td>${tess_received:,.2f}</td></tr></table>

<p style="font-size:11px;color:#888;border-top:1px solid #ccc;padding-top:8px;margin-top:20px">
— V. Hale, VCS · Thunderbird Wing · D2M<br>
Next brief: {(today + timedelta(days=1)).isoformat()} 06:00 MT
</p>
</div>"""

    return md, html


# ---------------------------------------------------------------------------
# Email sender (to johnloucks3 — within-wing, no gate)
# ---------------------------------------------------------------------------

def send_brief_email(subject: str, html_body: str) -> bool:
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
        msg["to"] = "johnloucks3@gmail.com"
        msg["from"] = "d2mconcierge@gmail.com"
        msg["subject"] = subject
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        service.users().messages().send(
            userId="me", body={"raw": raw}
        ).execute()
        logger.info(f"Brief emailed to johnloucks3")
        return True
    except Exception as exc:
        logger.error(f"Email send failed: {exc}")
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    p = argparse.ArgumentParser(description="Morning Brief Engine")
    p.add_argument("--local", action="store_true", help="Write file only, no email")
    p.add_argument("--timer", action="store_true", help="Silent systemd timer mode")
    args = p.parse_args()

    today = date.today()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M MT")

    if not args.timer:
        print(f"\nMorning Brief Engine — {now_str}")

    state = load_state()
    clients = get_client_statuses()
    queue = load_queue_summary()

    md_brief, html_brief = generate_brief(state, clients, queue)

    # Write hale_brief.md
    BRIEF_OUT.write_text(md_brief, encoding="utf-8")
    logger.info(f"hale_brief.md written ({len(md_brief)} chars)")

    if not args.local:
        subject = f"🦅 Thunderbird Brief — {today.strftime('%-d %b %Y')} — {len(clients)} clients"
        ok = send_brief_email(subject, html_brief)
        if not args.timer:
            print(f"  {'✅' if ok else '❌'} Brief emailed to johnloucks3")

    if not args.timer:
        print(f"  ✅ hale_brief.md updated ({len(clients)} clients, {len(queue)} WF-17 items)")


if __name__ == "__main__":
    main()
