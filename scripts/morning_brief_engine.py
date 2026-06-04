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

    md_brief, html_brief = generate_brief(state, clients, queue)

    # Write hale_brief.md — compressed header first, full brief appended
    combined_md = compressed_brief + "\n---\n\n" + md_brief
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
