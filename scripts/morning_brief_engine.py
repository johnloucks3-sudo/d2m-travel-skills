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

# A3 — FPD Sentinel integration
try:
    from fpd_sentinel import sync_state as fpd_sync_state, get_fpd_brief_rows
    FPD_SENTINEL_AVAILABLE = True
except ImportError:
    FPD_SENTINEL_AVAILABLE = False

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


def load_staff_concerns() -> list[dict]:
    """Read open staff concerns about Mission Board from OpsCenter/staff_concerns.json."""
    path = THUNDERBIRD / "OpsCenter" / "staff_concerns.json"
    try:
        raw = json.loads(path.read_text())
        # Support both list format and {concerns: [...]} format
        items = raw if isinstance(raw, list) else raw.get("concerns", [])
        return [c for c in items if not c.get("resolved", False)]
    except Exception:
        return []


def load_tp_draft() -> dict | None:
    """Return the next pending TP lifecycle draft awaiting Commander approval."""
    path = THUNDERBIRD / "OpsCenter" / "tp_draft_queue.json"
    try:
        items = json.loads(path.read_text())
        for item in items:
            if item.get("status") == "pending_approval":
                return item
    except Exception:
        pass
    return None


def get_client_statuses() -> list[dict]:
    """Read all active dossiers and compute phase + open items."""
    records = scan_dossiers()
    today = date.today()
    statuses = []

    # A3 — sync FPD sentinel state once per brief run
    fpd_state: dict = {}
    if FPD_SENTINEL_AVAILABLE:
        try:
            fpd_state = fpd_sync_state()
        except Exception as _e:
            logger.warning(f"FPD sentinel sync failed: {_e}")

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

        # FPD status indicator — A3 sentinel-aware
        sentinel_entry = fpd_state.get(full_name, {})
        sentinel_status = sentinel_entry.get("status", "")

        if sentinel_status == "RECEIVED" or payment_status in ("paid_in_full", "paid", "complete"):
            fpd_label = "✅ PAID"
        elif sentinel_status == "SILENT":
            fpd_label = f"SILENT ({fpd_str})"
        elif rec.fpd:
            days_to_fpd = (rec.fpd - today).days
            if days_to_fpd < 0:
                # OVERDUE — check if already flagged (suppress from TODAY, goes to 30-day watch)
                flag_count = sentinel_entry.get("flag_count", 0)
                last_flagged = sentinel_entry.get("last_flagged_at", "")
                days_since_flag = 0
                if last_flagged:
                    try:
                        days_since_flag = (today - date.fromisoformat(last_flagged)).days
                    except ValueError:
                        pass
                if flag_count > 1 and days_since_flag < 30:
                    # In 30-day watch window — mark as watch, not fresh flag
                    fpd_label = f"👁 WATCH ({abs(days_to_fpd)}d overdue)"
                else:
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
# A1 — Brief Compression Engine: 3-7-30 format
# ---------------------------------------------------------------------------

BRIEF_DELTA_PATH = THUNDERBIRD / "OpsCenter" / "state" / "brief_delta.json"


def _load_brief_delta() -> dict:
    """Load yesterday's brief snapshot for delta computation."""
    if BRIEF_DELTA_PATH.exists():
        try:
            return json.loads(BRIEF_DELTA_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_brief_delta(snapshot: dict) -> None:
    BRIEF_DELTA_PATH.parent.mkdir(parents=True, exist_ok=True)
    BRIEF_DELTA_PATH.write_text(json.dumps(snapshot, indent=2, default=str), encoding="utf-8")


def generate_compressed_brief(
    state: dict,
    clients: list[dict],
    queue: list[dict],
    fpd_state: dict | None = None,
) -> str:
    """
    A1 — 3-7-30 compressed brief format.

    TODAY (≤3 items): Commander action required now.
    7-DAY HORIZON: Status changes since last brief.
    30-DAY WATCH: Suppressed repeats / slow-burn items.

    Integrates with A3 FPD sentinel state.
    Full brief always linked from compressed header.
    """
    today = date.today()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M MT")
    yesterday_snap = _load_brief_delta()
    yesterday_items = yesterday_snap.get("items", {})

    # ── TODAY section — max 3, highest priority Commander actions ──────────

    today_items: list[str] = []

    # WF-17 items that are deadline-critical (today or past due)
    for e in queue:
        deadline_str = e.get("deadline", "")
        is_urgent = False
        if deadline_str:
            try:
                dl = datetime.strptime(deadline_str, "%Y-%m-%d").date()
                if (dl - today).days <= 1:
                    is_urgent = True
            except ValueError:
                pass
        if is_urgent and len(today_items) < 3:
            today_items.append(
                f"  🔴 WF-17: {e.get('client')} TP {e.get('tp_id')} — "
                f"review + send by {deadline_str}"
            )

    # Fresh FPD overdue flags (first-time or re-flag day)
    if fpd_state is not None and FPD_SENTINEL_AVAILABLE:
        try:
            fpd_rows = get_fpd_brief_rows(fpd_state)
            for row in fpd_rows.get("today_flags", [])[:2]:
                if len(today_items) >= 3:
                    break
                today_items.append(
                    f"  🔴 FPD OVERDUE: {row['client']} — "
                    f"{row['days_overdue']}d past due ({row['fpd']})"
                )
        except Exception:
            pass

    # Upcoming departures within 7 days
    for c in clients:
        if len(today_items) >= 3:
            break
        if c.get("days_to_dep") is not None and 0 <= c["days_to_dep"] <= 7:
            today_items.append(
                f"  🛳 DEPARTURE T-{c['days_to_dep']}d: {c['client']} — {c['ship']}"
            )

    if not today_items:
        today_items = ["  All clear — no Commander action required today."]

    # ── 7-DAY HORIZON — status changes since last brief ────────────────────

    seven_day_changes: list[str] = []

    # New WF-17 queue items since yesterday
    prev_wf17_ids = set(str(x) for x in yesterday_items.get("wf17_ids", []))
    curr_wf17_ids = {f"{e.get('client')}:{e.get('tp_id')}" for e in queue}
    new_drafts = curr_wf17_ids - prev_wf17_ids
    for nd in list(new_drafts)[:3]:
        seven_day_changes.append(f"  + NEW DRAFT: {nd}")

    # Client count delta
    prev_client_count = yesterday_items.get("client_count", 0)
    curr_client_count = len(clients)
    delta_clients = curr_client_count - prev_client_count
    if delta_clients != 0:
        sign = "+" if delta_clients > 0 else ""
        seven_day_changes.append(f"  Δ Clients: {sign}{delta_clients} ({curr_client_count} total)")

    # FPD watch items (ongoing overdue, not fresh flags)
    if fpd_state is not None and FPD_SENTINEL_AVAILABLE:
        try:
            fpd_rows = get_fpd_brief_rows(fpd_state)
            for row in fpd_rows.get("watch_items", [])[:3]:
                seven_day_changes.append(
                    f"  👁 FPD WATCH: {row['client']} — "
                    f"{row['days_overdue']}d overdue (flagged {row['flag_count']}x)"
                )
        except Exception:
            pass

    # Departures within 7-14 days
    for c in clients:
        if c.get("days_to_dep") is not None and 7 < c["days_to_dep"] <= 14:
            seven_day_changes.append(
                f"  🛳 T-{c['days_to_dep']}d: {c['client']} — {c['ship']}"
            )

    if not seven_day_changes:
        seven_day_changes = ["  No status changes since last brief."]

    yesterday_delta_count = yesterday_items.get("item_count", 0)
    delta_str = f"yesterday's Δ: {len(today_items) + len(seven_day_changes) - yesterday_delta_count:+d} items"

    # ── 30-DAY WATCH — suppressed repeats ──────────────────────────────────

    watch_30: list[str] = []

    # WF-17 queue items not in today/urgent bucket
    for e in queue[3:6]:
        watch_30.append(
            f"  ⏳ PENDING: {e.get('client')} TP {e.get('tp_id')} — {e.get('status')}"
        )

    # FPD items received (confirm suppression working)
    if fpd_state is not None and FPD_SENTINEL_AVAILABLE:
        try:
            fpd_rows = get_fpd_brief_rows(fpd_state)
            received = fpd_rows.get("received", [])
            if received:
                watch_30.append(
                    f"  ✅ RECEIVED (suppressed): "
                    + ", ".join(r["client"] for r in received[:4])
                )
        except Exception:
            pass

    if not watch_30:
        watch_30 = ["  Nothing in 30-day watch."]

    # ── Assemble compressed brief ────────────────────────────────────────────

    financial = state.get("financial_pulse", {})
    pipeline = financial.get("total_d2m_pipeline", 0)

    compressed = f"""# HALE — Compressed Brief [{now_str}]
*3-7-30 Format | {delta_str}*

---

## TODAY (Commander Action Required)
{chr(10).join(today_items)}

## 7-DAY HORIZON (Status Since Last Brief)
{chr(10).join(seven_day_changes)}

## 30-DAY WATCH (Suppressed Repeats)
{chr(10).join(watch_30)}

---

| Pipeline | WF-17 Queue | Active Clients |
|---|---|---|
| **${pipeline:,.0f}** | {len(queue)} drafts | {len(clients)} |

*Full brief: /home/john/Thunderbird/hale_brief.md*
*— V. Hale, VCS · Next: {(today + timedelta(days=1)).isoformat()} 06:00 MT*
"""

    # Save delta snapshot for tomorrow's diff
    _save_brief_delta({
        "date": today.isoformat(),
        "items": {
            "wf17_ids": list(curr_wf17_ids),
            "client_count": curr_client_count,
            "item_count": len(today_items) + len(seven_day_changes),
        },
    })

    return compressed


# ---------------------------------------------------------------------------
# Brief generator
# ---------------------------------------------------------------------------

def generate_brief(state: dict, clients: list[dict], queue: list[dict], concerns: list[dict] | None = None, tp_draft: dict | None = None) -> tuple[str, str]:
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

    # --- Staff concerns ---
    concerns = concerns or []
    if concerns:
        concerns_lines = []
        for c in concerns:
            badge = "🔴" if c.get("priority") == "P0" else "🟡" if c.get("priority") == "P1" else "⚪"
            who = c.get("staff") or c.get("source", "?")
            mission_ref = c.get("mission_id") or c.get("mission", "—")
            concerns_lines.append(
                f"| {badge} {who} | {c.get('concern','?')} | {mission_ref} |"
            )
        concerns_table = "\n".join([
            "| Staff | Concern | Mission |",
            "|---|---|---|",
        ] + concerns_lines)
    else:
        concerns_table = "_No staff concerns logged this cycle._"

    # --- TP draft ---
    if tp_draft:
        tp_draft_section = (
            f"**Client:** {tp_draft.get('client','?')}  \n"
            f"**TP:** {tp_draft.get('tp_id','?')} — {tp_draft.get('label','?')}  \n"
            f"**Owner:** {tp_draft.get('owner','Dani')}  \n\n"
            f"{tp_draft.get('draft_preview','_Draft preview not available._')}  \n\n"
            f"_Reply APPROVED or REVISE to this email._"
        )
    else:
        tp_draft_section = "_No TP draft queued. Add to OpsCenter/tp_draft_queue.json with status=pending_approval._"

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

### 5. STAFF CONCERNS — MISSION BOARD

{concerns_table}

---

### 6. TP DRAFT FOR APPROVAL

{tp_draft_section}

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

    # --- HTML: Staff concerns ---
    if concerns:
        concerns_rows_html = "".join(
            f"<tr style='border-bottom:1px solid #e0d9cc'>"
            f"<td style='padding:4px 8px'>{'🔴' if c.get('priority')=='P0' else '🟡' if c.get('priority')=='P1' else '⚪'} {c.get('staff') or c.get('source','?')}</td>"
            f"<td style='padding:4px 8px'>{c.get('concern','?')}</td>"
            f"<td style='padding:4px 8px'>{c.get('mission_id') or c.get('mission','—')}</td></tr>"
            for c in concerns
        )
        concerns_html = (
            f"<table style='width:100%;border-collapse:collapse;font-size:13px'>"
            f"<tr style='background:#1a3557;color:#fff'><th style='padding:4px 8px'>Staff</th><th style='padding:4px 8px'>Concern</th><th style='padding:4px 8px'>Mission</th></tr>"
            f"{concerns_rows_html}</table>"
        )
    else:
        concerns_html = "<p><em>No concerns logged this cycle. Staff: add to OpsCenter/staff_concerns.json to surface here.</em></p>"

    # --- HTML: TP draft ---
    if tp_draft:
        tp_draft_html = (
            f"<table style='width:100%;font-size:13px;border-collapse:collapse;margin-bottom:8px'>"
            f"<tr><td style='padding:3px 8px'><strong>Client:</strong></td><td style='padding:3px 8px'>{tp_draft.get('client','?')}</td></tr>"
            f"<tr><td style='padding:3px 8px'><strong>TP:</strong></td><td style='padding:3px 8px'>{tp_draft.get('tp_id','?')} — {tp_draft.get('label','?')}</td></tr>"
            f"<tr><td style='padding:3px 8px'><strong>Owner:</strong></td><td style='padding:3px 8px'>{tp_draft.get('owner','Dani')}</td></tr>"
            f"</table>"
            f"<div style='background:#fff;border:1px solid #ccc;padding:12px;font-size:13px;white-space:pre-wrap'>"
            f"{tp_draft.get('draft_preview','Draft preview not available.')}"
            f"</div>"
            f"<p style='color:#1a3557;font-weight:bold;margin-top:8px'>Reply <strong>APPROVED</strong> or <strong>REVISE [notes]</strong> to this email.</p>"
        )
    else:
        tp_draft_html = "<p><em>No TP draft queued. Add to OpsCenter/tp_draft_queue.json with status=pending_approval.</em></p>"

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

<h3 style="color:#1a3557">5. Staff Concerns — Mission Board</h3>
{concerns_html}

<h3 style="color:#1a3557">6. TP Draft for Approval</h3>
{tp_draft_html}

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
# Overnight ops + credentials section
# ---------------------------------------------------------------------------

def _build_overnight_section() -> str:
    """
    Build OVERNIGHT OPS section for the brief.
    Reads overnight_ops_log.json and credentials_health.json.
    CP model: tells Commander what happened overnight without waking him.
    """
    state_dir = THUNDERBIRD / "OpsCenter" / "state"
    overnight_log = state_dir / "overnight_ops_log.json"
    creds_health = state_dir / "credentials_health.json"

    lines = ["### 0. OVERNIGHT OPS\n*What the Wing did while you slept — no action needed unless flagged 🔴*\n"]

    # --- Overnight events ---
    events = []
    if overnight_log.exists():
        try:
            entries = json.loads(overnight_log.read_text())
            # Show last 12 hours of entries
            cutoff = datetime.now().timestamp() - (12 * 3600)
            for e in entries:
                try:
                    ts = datetime.fromisoformat(e["ts"].rstrip("Z")).timestamp()
                    if ts > cutoff:
                        events.append(e)
                except Exception:
                    pass
        except Exception:
            pass

    if events:
        for e in events:
            ts_short = e.get("ts", "")[:16].replace("T", " ")
            event_name = e.get("event", "event")
            details = ", ".join(e.get("details", [])[:3])
            client_alerts = e.get("client_alerts", 0)
            flag = "🔴" if client_alerts > 0 else "✅"
            lines.append(f"| {ts_short} | {flag} {event_name} | {details} |")
    else:
        lines.append("_No overnight events logged_")

    lines.append("")

    # --- Credentials health ---
    lines.append("**Credentials Status:**\n")
    cred_rows = []
    if creds_health.exists():
        try:
            health = json.loads(creds_health.read_text())
            for name, r in health.get("credentials", {}).items():
                status = r.get("status", "?")
                icon = "✅" if status == "valid" else "🔴" if r.get("client_affecting") else "🟡"
                reason = r.get("reason", "")[:60]
                cred_rows.append(f"| {icon} {name} | {status} | {reason} |")
        except Exception:
            pass

    if cred_rows:
        lines.append("| Credential | Status | Detail |")
        lines.append("|---|---|---|")
        lines.extend(cred_rows)
    else:
        lines.append("_Run `python3 scripts/credentials_health_check.py` to populate_")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# ELON proposals section
# ---------------------------------------------------------------------------

def _build_elon_proposals_section() -> str:
    """
    Surface ELON technical proposals so they never again silently pile up
    unread. Root cause (2026-07-05): proposals were written to
    OpsCenter/elon_proposals/ and only ever counted (elon_proposals_new in
    hale_incidents_today.json) — no brief ever listed them. This closes that
    gap: new-since-last-brief proposals are listed with decision tag +
    synopsis, and any QUEUE_FOR_COMMANDER proposal stays listed until
    acknowledged via the seen-cursor file.
    """
    import re

    proposals_dir = THUNDERBIRD / "OpsCenter" / "elon_proposals"
    cursor_file = THUNDERBIRD / "OpsCenter" / "state" / "elon_proposals_seen.json"

    lines = ["### ELON PROPOSALS\n*New technical proposals since last brief — nothing sits unseen*\n"]

    if not proposals_dir.exists():
        return ""

    files = sorted(
        [f for f in proposals_dir.iterdir() if f.suffix == ".md" and f.stat().st_size > 0],
        key=lambda f: f.stat().st_mtime,
    )
    if not files:
        return ""

    try:
        cursor = json.loads(cursor_file.read_text()) if cursor_file.exists() else {}
    except Exception:
        cursor = {}
    last_seen_mtime = cursor.get("last_seen_mtime", 0)
    acked_queued = set(cursor.get("acked_queue_for_commander", []))

    def decision_of(text: str) -> str:
        if re.search(r"QUEUE_FOR_COMMANDER", text):
            return "QUEUE_FOR_COMMANDER"
        if re.search(r"APPLY_AUTONOMOUSLY", text):
            return "APPLY_AUTONOMOUSLY"
        return "UNTAGGED"

    def synopsis_of(text: str) -> str:
        for pat in (r"\*\*Root cause[:\s]*\*\*[:\s]*(.+)", r"\*\*Recommendation[:\s]*\*\*[:\s]*(.+)",
                    r"\*\*Decision[:\s]*\*\*[:\s]*(.+)"):
            m = re.search(pat, text)
            if m:
                return re.sub(r"[`*]", "", m.group(1)).strip()[:160]
        for l in text.splitlines():
            l = l.strip()
            if l and not l.startswith("#") and "written to" not in l.lower() and "proposal complete" not in l.lower():
                return re.sub(r"[`*]", "", l)[:160]
        return "(no synopsis)"

    new_items = []
    unacked_queued = []
    newest_mtime = last_seen_mtime

    for f in files:
        mtime = f.stat().st_mtime
        newest_mtime = max(newest_mtime, mtime)
        text = f.read_text(errors="ignore")
        decision = decision_of(text)
        is_new = mtime > last_seen_mtime
        if is_new:
            new_items.append((f.name, decision, synopsis_of(text)))
        if decision == "QUEUE_FOR_COMMANDER" and f.name not in acked_queued:
            unacked_queued.append((f.name, synopsis_of(text)))

    if new_items:
        for name, decision, syn in new_items:
            flag = "🔴" if decision == "QUEUE_FOR_COMMANDER" else ("🟢" if decision == "APPLY_AUTONOMOUSLY" else "⚪")
            lines.append(f"| {flag} **{decision}** | {name} | {syn} |")
    else:
        lines.append("_No new proposals since last brief_")

    if unacked_queued:
        lines.append("")
        lines.append(f"**⚠️ {len(unacked_queued)} QUEUE_FOR_COMMANDER proposal(s) still awaiting your decision (any age):**")
        for name, syn in unacked_queued:
            lines.append(f"- `{name}` — {syn}")

    cursor_file.parent.mkdir(parents=True, exist_ok=True)
    cursor_file.write_text(json.dumps({
        "last_seen_mtime": newest_mtime,
        "acked_queue_for_commander": list(acked_queued),  # ack happens via separate command, not auto
    }, indent=2))

    return "\n".join(lines) + "\n"


def _build_quota_review_section() -> str:
    """Surface named-waiver user quota usage (Bryana Jarboe et al.) on the
    quarterly review cadence (1st of Jan/Apr/Jul/Oct) or any time a user is
    at/above 80% of their monthly allowance — otherwise silent, since daily
    noise on a soft 750/month limit isn't useful."""
    report_path = THUNDERBIRD / "OpsCenter" / f"bryana_usage_report_{date.today().strftime('%Y-%m')}.json"
    if not report_path.exists():
        return ""
    try:
        report = json.loads(report_path.read_text())
    except Exception:
        return ""

    if not (report.get("is_quarterly_review_day") or report.get("recommend_rebalance")):
        return ""

    lines = ["### USER QUOTA REVIEW — Bryana Jarboe\n"]
    lines.append(f"| Used | Allowance | % Used | Trend |")
    lines.append(f"|---|---|---|---|")
    lines.append(f"| {report['used_this_month']} | {report['allowance']} | {report['pct_used']}% | {report['trend']} |")
    if report.get("recommend_rebalance"):
        lines.append("\n⚠️ >=80% of monthly allowance used — rebalance decision recommended "
                      "(upgrade AgentMail tier, adjust allowance, or both).")
    if report.get("weekly_alert_weeks"):
        lines.append(f"\n🔴 Weekly threshold (85%) crossed: {report['weekly_alert_weeks']}")
    return "\n".join(lines) + "\n"


def _build_predicted_next_moves_section() -> str:
    """Commander Next-Move Predictor (core/prediction/commander_predictor.py).
    Real consumer for the ledger — this is what keeps it from becoming an
    unread, unwired module by tomorrow. Runs the generator fresh each brief
    (cheap, file-based) rather than trusting a stale ledger snapshot."""
    try:
        from core.prediction.commander_predictor import run as _predict_run
        preds = _predict_run(write=True)
    except Exception:
        return ""
    if not preds:
        return ""

    confirmed = [p for p in preds if p.confidence == "CONFIRMED"]
    inferred = [p for p in preds if p.confidence == "INFERRED"]

    lines = ["### PREDICTED NEXT MOVES — Hale + Silver + Staff\n"]
    lines.append("*Grounded predictions only — each cites a real source file. "
                  "Accuracy is tracked in `OpsCenter/commander_prediction_ledger.json`, "
                  "not asserted.*\n")
    if confirmed:
        lines.append("**Scheduled (CONFIRMED — already on the books):**")
        for p in confirmed[:8]:
            lines.append(f"- {p.predicted_action} — _{p.basis}_")
        lines.append("")
    if inferred:
        lines.append("**Pattern-based (INFERRED — worth a glance, not a certainty):**")
        for p in inferred[:8]:
            lines.append(f"- [{p.domain}] {p.predicted_action} — _{p.basis}_")

    # Feedback loop — this is what marks the ledger for real instead of
    # leaving mark_outcomes() ownerless. Ask, don't assume.
    open_preds = [p for p in preds if p.status == "open"]
    if open_preds:
        lines.append("\n**Rate last cycle's predictions** (closes the accuracy loop — "
                      "reply with any of these, or skip if none apply):")
        for p in open_preds[:6]:
            lines.append(f"- `{p.id}` — {p.predicted_action[:100]}")
        lines.append('\n> Reply e.g. `"DA-MCLEOD... hit"` or `"P0AGE-MISSION-214 miss, still pending"` '
                      '— or tell me in plain language which ones landed.')
    return "\n".join(lines) + "\n"


def _build_recurring_corrections_section() -> str:
    """Separate, deliberately UNSCORED lane — a synthesis of recurring
    corrections OF THE WING (not a claim about the Commander's own problems),
    weighted by his own stated emphasis + recency, never by raw file count.
    Never written to commander_prediction_ledger.json."""
    try:
        from core.prediction.commander_predictor import analyze_recurring_corrections
        analysis = analyze_recurring_corrections()
    except Exception:
        return ""

    lines = ["### RECURRING CORRECTION PATTERNS — Wing self-critique (not scored)\n"]
    lines.append(f"*{analysis['framing']}*\n")
    for p in analysis["top_patterns_by_his_own_stated_emphasis"]:
        lines.append(f"- **{p['pattern']}** ({p['so_date']}) — {p['note']}")
    lines.append(f"\n{analysis['this_session_live_instance']}")
    rec = analysis["secondary_signal_recency_cluster"]
    lines.append(f"\n_Secondary signal: {rec['feedback_files_mentioning_2026-07']}/"
                  f"{rec['feedback_files_total']} feedback memories touch this month "
                  f"— {rec['caveat']}_")
    return "\n".join(lines) + "\n"


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

    # Retrieve fpd_state generated during get_client_statuses()
    fpd_state: dict = {}
    if FPD_SENTINEL_AVAILABLE:
        try:
            from fpd_sentinel import _load_state as _fpd_load
            fpd_state = _fpd_load()
        except Exception:
            pass

    # A1 — Compressed 3-7-30 header
    compressed_brief = generate_compressed_brief(state, clients, queue, fpd_state)

    # OVERNIGHT OPS + CREDENTIALS — run health check, inject into brief
    overnight_section = _build_overnight_section()
    elon_section = _build_elon_proposals_section()
    quota_section = _build_quota_review_section()
    predictor_section = _build_predicted_next_moves_section()
    recurring_section = _build_recurring_corrections_section()

    concerns = load_staff_concerns()
    tp_draft = load_tp_draft()
    md_brief, html_brief = generate_brief(state, clients, queue, concerns, tp_draft)

    # Write hale_brief.md — compressed header first, overnight ops, ELON proposals, full brief appended
    combined_md = compressed_brief + "\n---\n\n" + overnight_section
    if elon_section:
        combined_md += "\n---\n\n" + elon_section
    if quota_section:
        combined_md += "\n---\n\n" + quota_section
    if predictor_section:
        combined_md += "\n---\n\n" + predictor_section
    if recurring_section:
        combined_md += "\n---\n\n" + recurring_section
    combined_md += "\n---\n\n" + md_brief
    BRIEF_OUT.write_text(combined_md, encoding="utf-8")
    logger.info(f"hale_brief.md written ({len(combined_md)} chars, compressed+full)")

    if not args.local:
        # Email sends the compressed brief + full HTML — compressed as plain text header
        compressed_html = f"<pre style='font-family:monospace;font-size:12px;background:#f7f3ea;padding:12px'>{compressed_brief}</pre><hr>"
        full_html_out = compressed_html + html_brief
        subject = f"🦅 Thunderbird Brief — {today.strftime('%-d %b %Y')} — {len(clients)} clients"
        ok = send_brief_email(subject, full_html_out)
        if not args.timer:
            print(f"  {'✅' if ok else '❌'} Brief emailed to johnloucks3")

    if not args.timer:
        print(f"  ✅ hale_brief.md updated ({len(clients)} clients, {len(queue)} WF-17 items)")


if __name__ == "__main__":
    main()
