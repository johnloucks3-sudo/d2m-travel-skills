"""
Renders output/hale-brief-dashboard/index.html from the same in-memory data
morning_brief_engine.py already assembles for the email.

v1.1 — Client Wire, WF-17 Gate, Financial Pulse, FPD Alerts, Wing Health,
Mission Kanban, Staff Concerns, TP Draft (read-only preview, no send action).

Called from scripts/morning_brief_engine.py after BRIEF_OUT.write_text(md).

Coverage note (2026-07-10): sections below port real data + one guardrail from
a parallel, uncommitted Track A build (output/morning_brief_dashboard.html) —
FPD countdown, live wing health, mission kanban. That build also hardcoded a
YTD pipeline target ($27,692.54, "estimate") with no source in the repo — not
ported here; Rule 1 (Negative-Space) bars fabricated figures in any Commander
product, dashboards included.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

from core.hale.d2m_brand_tokens import PAGE_SHELL_CSS, SHIMMER, TEXT_ON_NAVY_MUTED, status_color
from core.hale.stat_tile import stat_tile, status_badge, tile_row

DASHBOARD_OUT = Path.home() / "Thunderbird" / "output" / "hale-brief-dashboard" / "index.html"
THUNDERBIRD = Path.home() / "Thunderbird"
MISSION_BOARD = THUNDERBIRD / "OpsCenter" / "mission_board.json"


def _client_wire_table(clients: list[dict]) -> str:
    if not clients:
        return "<p style='color:%s'>No active clients.</p>" % TEXT_ON_NAVY_MUTED
    rows = []
    for c in clients:
        dep_flag = " 🔴" if c.get("days_to_dep") is not None and c["days_to_dep"] <= 14 else ""
        overdue = f" ⚠️ {c['overdue_count']} overdue" if c.get("overdue_count") else ""
        rows.append(
            f"<tr><td>{c.get('client','')}</td><td>{c.get('ship','')}</td>"
            f"<td>{c.get('departure','')}{dep_flag}</td>"
            f"<td>{status_badge(c.get('fpd_label',''))}</td>"
            f"<td>{c.get('next_tp','')}{overdue}</td></tr>"
        )
    return f"""
    <table class="d2m-table">
      <tr><th>Client</th><th>Ship</th><th>Departure</th><th>FPD Status</th><th>Next TP</th></tr>
      {''.join(rows)}
    </table>"""


def _financial_pulse_tiles(financial: dict) -> str:
    pipeline = financial.get("total_d2m_pipeline", 0)
    tess_received = financial.get("tess_received", 0)
    tiles = [
        stat_tile("D2M Pipeline", f"${pipeline:,.2f}", color=SHIMMER),
        stat_tile("TESS Received", f"${tess_received:,.2f}"),
    ]
    return tile_row(tiles)


def _fpd_alerts_html(state: dict) -> str:
    """FPD/deferred-alert countdown, sourced from hale_state.json['deferred_alerts'] —
    the real trigger list, not derived/estimated dates."""
    alerts = state.get("deferred_alerts", [])
    today = date.today()
    rows = []
    for a in alerts:
        fpd_raw = a.get("fpd")
        days_out = None
        if fpd_raw:
            try:
                days_out = (date.fromisoformat(fpd_raw) - today).days
            except ValueError:
                pass
        amount = a.get("amount")
        amount_str = f"${amount:,.2f}" if isinstance(amount, (int, float)) else "—"
        badge = status_badge(a.get("priority", ""))
        countdown = f"T-{days_out}d" if days_out is not None else "—"
        rows.append(
            f"<tr><td>{badge}</td><td>{a.get('client','')}</td>"
            f"<td>{fpd_raw or '—'} ({countdown})</td><td>{amount_str}</td>"
            f"<td>{a.get('message','')[:90]}</td></tr>"
        )
    if not rows:
        return f"<p style='color:{TEXT_ON_NAVY_MUTED}'>No deferred FPD alerts on file.</p>"
    return f"""
    <table class="d2m-table">
      <tr><th>Pri</th><th>Client</th><th>FPD</th><th>Amount</th><th>Alert</th></tr>
      {''.join(rows)}
    </table>"""


def _wing_health_grid_html(state: dict) -> str:
    """Live wing_health block from hale_state.json — every value here is read from
    the same struct the OVERNIGHT OPS section of hale_brief.md already carries.
    No synthetic 'system health' probe re-run here — single source of truth."""
    health = state.get("wing_health", {})
    tiles = []
    for label, key in [
        ("MCP Server", "mcp_server"),
        ("OpenCode", "opencode_status"),
        ("Telegram", "telegram_bot"),
        ("Chrome Debug :9222", "chrome_debug_port_9222"),
    ]:
        val = str(health.get(key, "UNKNOWN"))
        short = val.split(":", 1)[0].split("(", 1)[0].strip()[:60] or val[:60]
        tiles.append(stat_tile(label, short, color=status_color(val)))

    cred_status = health.get("credential_status", {})
    for cred_name, cred in list(cred_status.items())[:4]:
        status_val = cred.get("status", "?") if isinstance(cred, dict) else str(cred)
        tiles.append(stat_tile(cred_name, str(status_val), color=status_color(str(status_val))))

    return tile_row(tiles) if tiles else f"<p style='color:{TEXT_ON_NAVY_MUTED}'>No wing_health data.</p>"


def _mission_kanban_html() -> str:
    """Real counts from OpsCenter/mission_board.json — never a placeholder/sample count."""
    if not MISSION_BOARD.exists():
        return f"<p style='color:{TEXT_ON_NAVY_MUTED}'>mission_board.json not found.</p>"
    try:
        board = json.loads(MISSION_BOARD.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return f"<p style='color:{TEXT_ON_NAVY_MUTED}'>mission_board.json unreadable.</p>"

    missions = board.get("missions", [])
    counts: dict[str, int] = {}
    for m in missions:
        st = m.get("status", "unknown")
        counts[st] = counts.get(st, 0) + 1

    columns = ["active", "in_progress", "pending_review", "pending_commander", "completed"]
    tiles = [stat_tile(col.replace("_", " ").title(), str(counts.get(col, 0))) for col in columns]
    return tile_row(tiles)


def _staff_concerns_html(concerns: list[dict]) -> str:
    if not concerns:
        return f"<p style='color:{TEXT_ON_NAVY_MUTED}'>No concerns logged this cycle.</p>"
    rows = []
    for c in concerns:
        rows.append(
            f"<tr><td>{status_badge(c.get('priority',''))}</td><td>{c.get('source','')}</td>"
            f"<td>{c.get('concern','')}</td><td>{c.get('mission_id','')}</td></tr>"
        )
    return f"""
    <table class="d2m-table">
      <tr><th>Pri</th><th>Staff</th><th>Concern</th><th>Mission</th></tr>
      {''.join(rows)}
    </table>"""


def _tp_draft_html(tp_draft: dict | None) -> str:
    """Read-only preview card. No send affordance — this is a dashboard, WF-17
    approval/send stays in the johnloucks3 draft, never here."""
    if not tp_draft:
        return f"<p style='color:{TEXT_ON_NAVY_MUTED}'>No TP draft queued.</p>"
    body = str(tp_draft.get("body", tp_draft.get("content", "")))[:600]
    return f"""
    <div style="color:{TEXT_ON_NAVY_MUTED};font-size:0.85em;margin-bottom:8px;">
      READ-ONLY PREVIEW — no send action on this page. Approve/send from the johnloucks3 draft.
    </div>
    <div><strong>{tp_draft.get('client','')}</strong> — {tp_draft.get('tp_name', tp_draft.get('subject',''))}</div>
    <pre style="white-space:pre-wrap;font-family:{TEXT_ON_NAVY_MUTED};font-size:0.85em;margin-top:8px;">{body}</pre>"""


def render_dashboard_html(
    state: dict,
    clients: list[dict],
    queue: list[dict] | None = None,
    concerns: list[dict] | None = None,
    tp_draft: dict | None = None,
) -> str:
    """Build the full standalone HTML page."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M MT")
    financial = state.get("financial_pulse", {})
    queue = queue or []
    concerns = concerns or []

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Thunderbird Brief Dashboard — {now_str}</title>
<style>{PAGE_SHELL_CSS}</style>
</head>
<body>
  <h1 style="color:{SHIMMER};font-weight:400;">🦅 Thunderbird Daily Brief</h1>
  <div style="color:{TEXT_ON_NAVY_MUTED};margin-bottom:20px;">Generated {now_str} · V. Hale, VCS</div>

  <div class="d2m-card">
    <h2>1. Client Wire</h2>
    {_client_wire_table(clients)}
  </div>

  <div class="d2m-card">
    <h2>2. WF-17 Gate</h2>
    <p style="color:{TEXT_ON_NAVY_MUTED};">{len(queue)} draft(s) awaiting Commander review.</p>
  </div>

  <div class="d2m-card">
    <h2>3. Financial Pulse</h2>
    {_financial_pulse_tiles(financial)}
  </div>

  <div class="d2m-card">
    <h2>4. FPD Alerts</h2>
    {_fpd_alerts_html(state)}
  </div>

  <div class="d2m-card">
    <h2>5. Wing Health</h2>
    {_wing_health_grid_html(state)}
  </div>

  <div class="d2m-card">
    <h2>6. Mission Kanban</h2>
    {_mission_kanban_html()}
  </div>

  <div class="d2m-card">
    <h2>7. Staff Concerns</h2>
    {_staff_concerns_html(concerns)}
  </div>

  <div class="d2m-card">
    <h2>8. TP Draft</h2>
    {_tp_draft_html(tp_draft)}
  </div>
</body>
</html>"""


def write_dashboard(
    state: dict,
    clients: list[dict],
    queue: list[dict] | None = None,
    concerns: list[dict] | None = None,
    tp_draft: dict | None = None,
) -> Path:
    """Renders and writes the dashboard file. Raises if the section count looks wrong
    (safeguard against the silent-failure pattern seen in the ci-fix-d2m-dashboard churn)."""
    html = render_dashboard_html(state, clients, queue, concerns, tp_draft)
    if html.count("d2m-card") < 8:  # 8 sections now — v1.1
        raise RuntimeError(
            f"brief_dashboard_render: expected >=8 section cards, found "
            f"{html.count('d2m-card')} — refusing to write a broken dashboard"
        )
    DASHBOARD_OUT.parent.mkdir(parents=True, exist_ok=True)
    DASHBOARD_OUT.write_text(html, encoding="utf-8")
    return DASHBOARD_OUT
