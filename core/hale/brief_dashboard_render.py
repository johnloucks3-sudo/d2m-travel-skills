"""
Renders output/hale-brief-dashboard/index.html from the same in-memory data
morning_brief_engine.py already assembles for the email (Client Wire + Financial
Pulse, v1 — remaining sections are a fast-follow, see VISUAL_INTEGRATION_ROADMAP).

Called from scripts/morning_brief_engine.py after BRIEF_OUT.write_text(md).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from core.hale.d2m_brand_tokens import PAGE_SHELL_CSS, SHIMMER, TEXT_ON_NAVY_MUTED
from core.hale.stat_tile import stat_tile, status_badge, tile_row

DASHBOARD_OUT = Path.home() / "Thunderbird" / "output" / "hale-brief-dashboard" / "index.html"


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


def render_dashboard_html(state: dict, clients: list[dict], queue: list[dict] | None = None) -> str:
    """Build the full standalone HTML page. v1: Client Wire + Financial Pulse sections."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M MT")
    financial = state.get("financial_pulse", {})
    queue = queue or []

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
    <h2>3. Financial Pulse</h2>
    {_financial_pulse_tiles(financial)}
  </div>

  <div class="d2m-card">
    <h2>2. WF-17 Gate</h2>
    <p style="color:{TEXT_ON_NAVY_MUTED};">{len(queue)} draft(s) awaiting Commander review.</p>
  </div>
</body>
</html>"""


def write_dashboard(state: dict, clients: list[dict], queue: list[dict] | None = None) -> Path:
    """Renders and writes the dashboard file. Raises if the section count looks wrong
    (safeguard against the silent-failure pattern seen in the ci-fix-d2m-dashboard churn)."""
    html = render_dashboard_html(state, clients, queue)
    if html.count("d2m-card") < 3:  # 3 open + 3 close = 6; catches a truncated render
        raise RuntimeError(
            f"brief_dashboard_render: expected >=3 section cards, found "
            f"{html.count('d2m-card')} — refusing to write a broken dashboard"
        )
    DASHBOARD_OUT.parent.mkdir(parents=True, exist_ok=True)
    DASHBOARD_OUT.write_text(html, encoding="utf-8")
    return DASHBOARD_OUT
