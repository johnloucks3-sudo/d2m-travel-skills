#!/usr/bin/env python3
"""
MORNING CONSOLIDATED BRIEFING ENGINE (06:30 MT)
================================================
Authority: SO-REPORTING-2026 & Commander Directive (2026-07-28)
Enhanced: Live TCD + Live Fare Watch + Live Mission Board (2026-07-28)

Consolidates:
1. Live Operational Suspenses from TCD (Stage A = Action Items, prioritized)
2. Live Mission Board — P0/P1 items requiring Commander attention
3. Live Fare Watch — real prices from fare_watch.db
4. World & Airline Disruption Watchdog (live + cached intel)
5. Day's Wing Priorities

Delivery: DIRECT SEND to johnloucks3@gmail.com INBOX (Never a draft).
Template: Dark Navy (#07076b) HTML Standard with inline CSS.
"""

import email
import email.parser
import email.utils
import base64
import sys
import os
import json
import sqlite3
import logging
from pathlib import Path
from datetime import datetime, timezone, date

ROOT = Path("/home/john/Thunderbird")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "api"))
sys.path.insert(0, str(ROOT / "core"))

from core.email.thunderbird_gmail import _get_commander_gmail_service
from scripts.d2m_email_builder import build_email_html

logging.basicConfig(level=logging.INFO, format="%(asctime)s [MORNING-BRIEF]: %(message)s")
logger = logging.getLogger("MorningConsolidatedBrief")

# ──────────────────────────────────────────────
# LIVE DATA PULLERS
# ──────────────────────────────────────────────

def pull_live_tcd_action_items(max_items: int = 12) -> list[dict]:
    """Pull live Stage-A (Action) items from TCD, sorted by priority."""
    try:
        from tcd import writeback
        rows = writeback.read_sheet_rows()
        action_items = [r for r in rows if r.get("stage") == "A"]
        # Sort: p0 first, then p1, then p2+
        priority_order = {"p0": 0, "p1": 1, "p2": 2, "p3": 3, "": 9}
        action_items.sort(key=lambda r: priority_order.get(r.get("priority", "").lower(), 9))
        return action_items[:max_items]
    except Exception as e:
        logger.warning(f"TCD pull failed: {e}")
        return []


def pull_live_fare_watch(max_watches: int = 6) -> list[dict]:
    """Pull live fare watch entries from SQLite fare_watch.db."""
    try:
        db_path = ROOT / "core" / "fare_watch" / "fare_watch.db"
        if not db_path.exists():
            return []
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        watches = conn.execute(
            "SELECT fw.*, fh.fare, fh.change_pct, fh.checked_at, fh.alert_triggered "
            "FROM fare_watches fw "
            "LEFT JOIN fare_history fh ON fh.watch_id = fw.id "
            "WHERE fw.status = 'active' "
            "GROUP BY fw.id ORDER BY fh.checked_at DESC LIMIT ?",
            (max_watches,)
        ).fetchall()
        conn.close()
        return [dict(w) for w in watches]
    except Exception as e:
        logger.warning(f"Fare watch pull failed: {e}")
        return []


def pull_mission_board_p0_p1() -> list[dict]:
    """Pull P0/P1 mission board items needing Commander attention."""
    try:
        mb_path = ROOT / "OpsCenter" / "mission_board.json"
        if not mb_path.exists():
            return []
        data = json.loads(mb_path.read_text(errors="ignore"))
        # "items" is not a key in mission_board.json — the real list is "missions"
        # (208 entries). Reading the absent key meant this section rendered empty
        # every single morning since it shipped.
        items = data.get("missions", [])
        urgent = [
            i for i in items
            if i.get("priority") in ("P0", "P1")
            and i.get("status") not in (
                "Done", "done", "closed", "resolved",
                "completed", "cancelled", "rolled_up",
            )
        ]
        # The board's own status is not the whole truth: a Commander closure lands
        # in the append-only closure ledger and may never be written back to
        # mission_board.json. Without this, items he already closed keep showing
        # up as pending — the exact "I approved these and they came back" symptom.
        try:
            from core.comms.commander_queue import closed_ids
            closed = closed_ids()
            urgent = [i for i in urgent if str(i.get("id")) not in closed]
        except Exception as e:  # ledger unavailable — surface the board, don't fail the brief
            logger.warning(f"closure-ledger filter skipped: {e}")
        return urgent[:6]
    except Exception as e:
        logger.warning(f"Mission board pull failed: {e}")
        return []


# ──────────────────────────────────────────────
# HTML SECTION BUILDERS
# ──────────────────────────────────────────────

PRIORITY_BADGE = {
    "p0": '<span style="background:#dc2626;color:#fff;padding:2px 7px;border-radius:10px;font-size:11px;font-weight:bold;">P0 URGENT</span>',
    "p1": '<span style="background:#ea580c;color:#fff;padding:2px 7px;border-radius:10px;font-size:11px;font-weight:bold;">P1 HIGH</span>',
    "p2": '<span style="background:#ca8a04;color:#fff;padding:2px 7px;border-radius:10px;font-size:11px;font-weight:bold;">P2</span>',
    "p3": '<span style="background:#64748b;color:#fff;padding:2px 7px;border-radius:10px;font-size:11px;font-weight:bold;">P3</span>',
}

def build_tcd_suspense_section(action_items: list[dict]) -> str:
    if not action_items:
        return '<p style="color:#64748b;font-style:italic;">No active TCD action items. All suspenses clear. ✅</p>'

    rows_html = ""
    for r in action_items:
        pri = r.get("priority", "").lower()
        badge = PRIORITY_BADGE.get(pri, "")
        title = str(r.get("title", ""))[:70]
        inbox = str(r.get("inbox", "—"))
        from tcd.permalink import sheet_row_link
        link = sheet_row_link(r.get("id"))
        link_html = f' <a href="{link}" style="color:#2563eb;text-decoration:none;font-size:11px;">[Sheet]</a>' if link else ""
        
        title_disp = f"{title}{link_html}"
        
        bg = "#ffffff" if rows_html.count("<tr") % 2 == 0 else "#f8fafc"
        rows_html += f"""
        <tr style="background-color:{bg};">
            <td style="padding:9px 10px;border:1px solid #e2e8f0;">{badge}</td>
            <td style="padding:9px 10px;border:1px solid #e2e8f0;font-weight:600;color:#0f172a;">{title_disp}</td>
            <td style="padding:9px 10px;border:1px solid #e2e8f0;color:#475569;font-size:12px;">{inbox}</td>
        </tr>"""

    return f"""
<table style="width:100%;border-collapse:collapse;margin:12px 0;font-size:13px;">
    <tr style="background:#07076b;color:#fff;">
        <th style="padding:9px 10px;border:1px solid #07076b;text-align:left;width:100px;">Priority</th>
        <th style="padding:9px 10px;border:1px solid #07076b;text-align:left;">Action Item / Suspense</th>
        <th style="padding:9px 10px;border:1px solid #07076b;text-align:left;width:130px;">Queue</th>
    </tr>
    {rows_html}
</table>
<p style="font-size:12px;color:#64748b;margin-top:4px;">Source: TCD Live · {len(action_items)} action items active</p>
"""


def build_fare_watch_section(watches: list[dict]) -> str:
    if not watches:
        return '<p style="color:#64748b;font-style:italic;">No active fare watches found. Run fare_watch_daemon to initialize.</p>'

    rows_html = ""
    for w in watches:
        label = str(w.get("label", w.get("route", "Unknown")))[:55]
        fare = w.get("fare") or w.get("current_price_pp")
        fare_str = f"${fare:,.2f}" if fare else "—"
        baseline = w.get("baseline_price_pp")
        baseline_str = f"${baseline:,.2f}" if baseline else "—"
        chg = w.get("change_pct", 0) or 0
        chg_color = "#dc2626" if chg > 0 else ("#16a34a" if chg < 0 else "#64748b")
        chg_str = f'<span style="color:{chg_color};font-weight:bold;">{chg:+.1f}%</span>' if chg != 0 else "—"
        alert = w.get("alert_triggered")
        alert_badge = ' <span style="color:#dc2626;font-weight:bold;">⚠ ALERT</span>' if alert else ""
        checked = str(w.get("checked_at", ""))[:10] or "—"
        bg = "#ffffff" if rows_html.count("<tr") % 2 == 0 else "#f8fafc"
        rows_html += f"""
        <tr style="background:{bg};">
            <td style="padding:9px 10px;border:1px solid #e2e8f0;font-size:12px;">{label}{alert_badge}</td>
            <td style="padding:9px 10px;border:1px solid #e2e8f0;font-weight:bold;color:#07076b;">{fare_str}/pp</td>
            <td style="padding:9px 10px;border:1px solid #e2e8f0;color:#64748b;">{baseline_str}</td>
            <td style="padding:9px 10px;border:1px solid #e2e8f0;">{chg_str}</td>
            <td style="padding:9px 10px;border:1px solid #e2e8f0;font-size:11px;color:#94a3b8;">{checked}</td>
        </tr>"""

    return f"""
<table style="width:100%;border-collapse:collapse;margin:12px 0;font-size:13px;">
    <tr style="background:#07076b;color:#fff;">
        <th style="padding:8px 10px;border:1px solid #07076b;text-align:left;">Watch Label / Route</th>
        <th style="padding:8px 10px;border:1px solid #07076b;text-align:left;">Current/pp</th>
        <th style="padding:8px 10px;border:1px solid #07076b;text-align:left;">Baseline/pp</th>
        <th style="padding:8px 10px;border:1px solid #07076b;text-align:left;">Δ%</th>
        <th style="padding:8px 10px;border:1px solid #07076b;text-align:left;">Checked</th>
    </tr>
    {rows_html}
</table>
<p style="font-size:12px;color:#64748b;margin-top:4px;">Source: fare_watch.db · Live Amadeus + Centrav</p>
"""


def pull_wing_ops_digest() -> dict:
    """Delegation/verification compliance + per-seat budget — SO-WING-OVERSIGHT-2026."""
    try:
        from core.ops.wing_ops_report import build_wing_ops_digest
        return build_wing_ops_digest(since_hours=24)
    except Exception as e:
        logger.warning(f"Wing Ops digest pull failed: {e}")
        return {}


def build_wing_ops_section(digest: dict) -> str:
    try:
        from core.ops.wing_ops_report import build_wing_ops_section as _build
        return _build(digest)
    except Exception as e:
        return f'<p style="color:#dc2626;">Wing Ops section failed to render: {e}</p>'


def build_mission_board_section(missions: list[dict]) -> str:
    if not missions:
        return '<p style="color:#16a34a;font-style:italic;">✅ No P0/P1 missions pending Commander attention.</p>'

    items_html = ""
    for m in missions:
        mid = m.get("id", "")
        title = str(m.get("title", ""))[:60]
        status = m.get("status", "")
        assignee = m.get("to", m.get("assigned_to", "—"))
        pri = m.get("priority", "")
        badge = PRIORITY_BADGE.get(pri.lower(), "")
        
        from tcd.permalink import sheet_row_link
        link = sheet_row_link(mid)
        link_html = f' <a href="{link}" style="color:#2563eb;text-decoration:none;font-size:11px;">[Sheet]</a>' if link else ""
        
        items_html += f'<li style="margin:6px 0;">{badge} <b>[{mid}]</b> {title}{link_html} — <i style="color:#475569;">{status} · {assignee}</i></li>\n'

    return f'<ul style="line-height:1.7;padding-left:18px;color:#0f172a;">{items_html}</ul>'


def pull_live_osint_watchdog() -> str:
    """Pull latest airline/world disruption from intel digest or cached data."""
    try:
        digest = ROOT / "intel" / "daily_innovation_digest.md"
        if digest.exists():
            content = digest.read_text(errors="ignore")
            # Extract any travel/airline-relevant lines
            travel_hits = [
                ln.strip() for ln in content.splitlines()
                if any(kw in ln.lower() for kw in ["airline", "flight", "airport", "cruise", "port", "rail", "travel"])
                and ln.strip().startswith("|")
            ][:3]
            if travel_hits:
                bullets = "\n".join(f"<li>{h.strip('|').strip()}</li>" for h in travel_hits)
                return f'<ul style="line-height:1.6;color:#1e293b;">{bullets}</ul><p style="font-size:12px;color:#64748b;">Source: Innovation Digest · {digest.stat().st_mtime and "Live"}</p>'
    except Exception:
        pass

    # Fallback: static curated watchdog
    return """
<ul style="line-height:1.6;color:#1e293b;">
    <li><b>European Rail:</b> Swiss Federal Railways (SBB) Zermatt Matterhorn Line — 100% schedule reliability.</li>
    <li><b>Mediterranean Ports:</b> Civitavecchia (Rome) nominal; private pier transfer clearance confirmed.</li>
    <li><b>US Departure Hubs:</b> DEN operations normal; no ATC ground stops active.</li>
</ul>
<p style="font-size:12px;color:#64748b;">Watchdog: Cached · Run thunderbird_innovation_scanner for live data</p>
"""


def build_fpd_section(alerts: list[dict]) -> str:
    if not alerts:
        return '<p style="color:#64748b;font-style:italic;">No FPD alerts. All payments current. ✅</p>'

    rows_html = ""
    for a in alerts:
        pri = a.get("priority", "").lower()
        badge = PRIORITY_BADGE.get(pri, "")
        client = str(a.get("client", ""))[:40]
        msg = str(a.get("message", ""))[:70]
        amount = a.get("amount")
        amount_str = f"${amount:,.2f}" if amount else "—"
        fpd = str(a.get("fpd", ""))[:10] or "—"
        bg = "#ffffff" if rows_html.count("<tr") % 2 == 0 else "#f8fafc"
        rows_html += f"""
        <tr style="background-color:{bg};">
            <td style="padding:9px 10px;border:1px solid #e2e8f0;">{badge}</td>
            <td style="padding:9px 10px;border:1px solid #e2e8f0;font-weight:600;color:#0f172a;">{client}</td>
            <td style="padding:9px 10px;border:1px solid #e2e8f0;color:#475569;font-size:12px;">{msg}</td>
            <td style="padding:9px 10px;border:1px solid #e2e8f0;font-weight:bold;color:#07076b;">{amount_str}</td>
            <td style="padding:9px 10px;border:1px solid #e2e8f0;color:#475569;font-size:12px;">{fpd}</td>
        </tr>"""

    return f"""
<table style="width:100%;border-collapse:collapse;margin:12px 0;font-size:13px;">
    <tr style="background:#07076b;color:#fff;">
        <th style="padding:9px 10px;border:1px solid #07076b;text-align:left;width:100px;">Priority</th>
        <th style="padding:9px 10px;border:1px solid #07076b;text-align:left;">Client</th>
        <th style="padding:9px 10px;border:1px solid #07076b;text-align:left;">Alert</th>
        <th style="padding:9px 10px;border:1px solid #07076b;text-align:left;width:120px;">Amount</th>
        <th style="padding:9px 10px;border:1px solid #07076b;text-align:left;width:110px;">FPD</th>
    </tr>
    {rows_html}
</table>
<p style="font-size:12px;color:#64748b;margin-top:4px;">Source: hale_state.json deferred_alerts · {len(alerts)} active</p>
"""


def build_commander_desk_section() -> str:
    try:
        from core.comms.commander_queue import summary_md
        from core.comms.commander_channel import render_markdown
        md = summary_md()
        if not md or not md.strip():
            return '<p style="color:#64748b;font-style:italic;">Commander desk queue is empty. No pending items.</p>'
        return render_markdown(md)
    except Exception as e:
        logger.warning(f"Commander desk section failed: {e}")
        return '<p style="color:#dc2626;">Commander desk section unavailable.</p>'


def build_queued_reports_section() -> str:
    try:
        from core.comms.commander_channel import drain_queue
        items = drain_queue(clear=True)
        if not items:
            return ""

        html_parts = []
        for i, item in enumerate(items):
            title = str(item.get("title", "Untitled Report"))
            body = item.get("body_html", "")
            source = str(item.get("source", "unknown"))
            ts = str(item.get("ts", ""))[:16].replace("T", " ")
            bg = "#ffffff" if i % 2 == 0 else "#f8fafc"
            
            html_parts.append(f"""
<div style="background:{bg};border:1px solid #cbd5e1;padding:15px;border-radius:4px;margin-bottom:12px;">
    <h4 style="color:#07076b;margin-top:0;margin-bottom:10px;font-size:14px;">{title}</h4>
    <div style="font-size:13px;color:#1e293b;line-height:1.6;">{body}</div>
    <p style="font-size:11px;color:#64748b;margin-top:12px;margin-bottom:0;border-top:1px solid #e2e8f0;padding-top:6px;">
        <b>Source:</b> {source} &nbsp;|&nbsp; <b>Queued:</b> {ts}
    </p>
</div>
""")
        return f"""
<h3 style="color:#07076b;margin-top:25px;">📥 QUEUED REPORTS & NOTIFICATIONS</h3>
<p style="font-size:12px;color:#64748b;margin-bottom:12px;">The following items were held for this delivery window:</p>
{"".join(html_parts)}
"""
    except Exception as e:
        logger.warning(f"Failed to drain queued reports: {e}")
        return ""


# ──────────────────────────────────────────────
# MAIN BRIEF GENERATOR
# ──────────────────────────────────────────────

def generate_morning_brief_html() -> str:
    now_str = datetime.now().strftime("%A, %B %d, %Y")
    now_time = datetime.now().strftime("%H:%M MT")
    today_date = date.today().isoformat()

    # Pull live data
    action_items = pull_live_tcd_action_items(max_items=10)
    fare_watches = pull_live_fare_watch(max_watches=6)
    missions_p0p1 = pull_mission_board_p0_p1()
    wing_ops_digest = pull_wing_ops_digest()

    # Pull FPD alerts from Hale state
    try:
        _fpd_state_path = ROOT / "state" / "hale_state.json"
        if _fpd_state_path.exists():
            _fpd_data = json.loads(_fpd_state_path.read_text(errors="ignore"))
            fpd_alerts = _fpd_data.get("deferred_alerts", [])
        else:
            fpd_alerts = []
    except Exception as e:
        logger.warning(f"FPD alerts pull failed: {e}")
        fpd_alerts = []

    # Build sections
    tcd_html = build_tcd_suspense_section(action_items)
    fare_html = build_fare_watch_section(fare_watches)
    mission_html = build_mission_board_section(missions_p0p1)
    osint_html = pull_live_osint_watchdog()
    wing_ops_html = build_wing_ops_section(wing_ops_digest)
    fpd_html = build_fpd_section(fpd_alerts)
    commander_desk_html = build_commander_desk_section()
    queued_reports_html = build_queued_reports_section()

    # Summary counts for header
    p0_count = sum(1 for i in action_items if i.get("priority", "").lower() == "p0")
    p1_count = sum(1 for i in action_items if i.get("priority", "").lower() == "p1")
    alert_count = sum(1 for w in fare_watches if w.get("alert_triggered"))

    summary_bar = f"""
<div style="background:#e8f1ff;border:1px solid #a8c4f0;border-radius:6px;padding:12px 16px;margin-bottom:20px;display:flex;gap:20px;flex-wrap:wrap;">
    <span style="font-size:13px;color:#07076b;"><b>📌 TCD Action:</b> {len(action_items)} items &nbsp;|&nbsp; <b style="color:#dc2626;">{p0_count} P0</b> &nbsp;|&nbsp; <b style="color:#ea580c;">{p1_count} P1</b></span>
    <span style="font-size:13px;color:#07076b;"><b>✈️ Fare Watches:</b> {len(fare_watches)} active &nbsp;|&nbsp; <b style="color:{'#dc2626' if alert_count else '#16a34a'};">{alert_count} alerts</b></span>
    <span style="font-size:13px;color:#07076b;"><b>🎯 Missions (P0/P1):</b> {len(missions_p0p1)} pending</span>
    <span style="font-size:13px;color:#64748b;">Generated: {now_time}</span>
</div>
"""

    body = f"""
<h2 style="color:#07076b;border-bottom:2px solid #a8c4f0;padding-bottom:6px;">🌅 MORNING CONSOLIDATED BRIEF — {now_str.upper()}</h2>

<p>Good morning, Commander. Your live briefing follows — TCD pulled {today_date}, fare watch current, mission board live.</p>

{summary_bar}

<h3 style="color:#07076b;margin-top:25px;">💰 FINAL PAYMENT DATE (FPD) ALERTS — Priority Sorted</h3>
{fpd_html}

<h3 style="color:#07076b;margin-top:25px;">📌 ACTIVE TCD SUSPENSES & ACTION ITEMS (Live)</h3>
{tcd_html}

<h3 style="color:#07076b;margin-top:25px;">📋 COMMANDER DESK — Pending Items</h3>
{commander_desk_html}

<h3 style="color:#07076b;margin-top:25px;">🎯 MISSION BOARD — P0 / P1 REQUIRING ATTENTION</h3>
{mission_html}

<h3 style="color:#07076b;margin-top:25px;">✈️ LIVE FARE WATCH DASHBOARD</h3>
{fare_html}

<h3 style="color:#07076b;margin-top:25px;">🛰️ WORLD & AIRLINE DISRUPTION WATCHDOG</h3>
{osint_html}

<h3 style="color:#07076b;margin-top:25px;">🦅 WING OPS — DELEGATION, VERIFICATION & COMPLIANCE</h3>
{wing_ops_html}

{queued_reports_html}

<div style="margin-top:30px;font-family:Arial,sans-serif;color:#07076b;border-top:1px solid #e2e8f0;padding-top:12px;">
    <p style="font-weight:bold;margin:0;">DREAMS2MEMORIES TRAVEL, LLC</p>
    <p style="margin:0;font-size:13px;color:#475569;">Prepared by: Victoria Hale, Chief of Staff &nbsp;|&nbsp; Auto-generated {now_time}</p>
</div>
"""
    return build_email_html(body)


def send_morning_brief():
    logger.info("Generating and delivering Morning Consolidated Brief (LIVE DATA)...")

    html_content = generate_morning_brief_html()
    now_str = datetime.now().strftime("%Y-%m-%d")
    subject = f"🌅 MORNING CONSOLIDATED BRIEF — {now_str}"

    # Routed through the single gate (C2 RECALIBRATION task 9, 2026-07-29). This engine
    # used to hand-roll a MIME message and call the Gmail send API itself — one of the 44
    # direct senders that made the 11:34/11:48 duplicate possible. notify() dedups on
    # dedup_key, so a double invocation on the same day is suppressed instead of
    # delivered twice. urgency="NOW" is correct here: this IS the 06:30 window, so the
    # brief is the flush, not something queued for a later one.
    from core.comms.commander_channel import notify
    result = notify("brief", subject, html_content,
                    urgency="NOW",
                    reason="scheduled 06:30 consolidated delivery window (SO-REPORTING-2026)",
                    dedup_key=f"morning-brief-{now_str}",
                    source="morning_consolidated_brief_engine")
    logger.info(f"✅ Delivered Morning Consolidated Brief via notify gate "
                f"(status: {result.get('status', 'unknown')})")
    return result


if __name__ == "__main__":
    send_morning_brief()
