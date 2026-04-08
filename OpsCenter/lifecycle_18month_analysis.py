#!/usr/bin/env python3
"""
MISSION-003 — D2M 18-Month Lifecycle Analysis
===============================================
Full 18-month view across all active clients.
- Timeline Gantt chart (voyage windows)
- Gap identification (clients with no upcoming touchpoints)
- Revenue projection summary
- Staff workflow overlay (A2→A6→A9→A3)

Output: ~/Thunderbird/output/lifecycle_18month.html

Usage:
  python3 OpsCenter/lifecycle_18month_analysis.py
"""

import logging
from datetime import date, datetime, timedelta
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "output"
OUTPUT_FILE = OUTPUT_DIR / "lifecycle_18month.html"
LOG_FILE = Path(__file__).parent.parent / "logs" / "overwatch.log"

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s [LIFECYCLE-003] %(message)s",
)
log = logging.getLogger("lifecycle_18month")

TODAY = date.today()
WINDOW_START = date(TODAY.year, TODAY.month, 1)
WINDOW_END = WINDOW_START + timedelta(days=548)  # ~18 months

# ── Client Master Data ───────────────────────────────────────────────────────
CLIENTS = [
    {
        "name": "McLeod / McGlasson",
        "ship": "Silver Muse",
        "voyage": "Mediterranean",
        "embark": date(2026, 6, 23),
        "disembark": date(2026, 7, 3),
        "fpd": date(2026, 1, 24),
        "fpd_paid": True,
        "revenue": 0,        # confirm from dossier
        "commission_est": 0,
        "color": "#b03030",
        "open_items": 2,
        "booking": "298475-25",
        "priority": 1,
    },
    {
        "name": "Furlow",
        "ship": "Regent Grandeur",
        "voyage": "Scandinavia",
        "embark": date(2026, 8, 29),
        "disembark": date(2026, 9, 8),
        "fpd": date(2026, 4, 1),
        "fpd_paid": True,
        "revenue": 19236,
        "commission_est": 4809,   # 25% markup
        "color": "#1a6fa8",
        "open_items": 1,
        "booking": "3071222",
        "priority": 2,
    },
    {
        "name": "Nichols",
        "ship": "Regent Grandeur",
        "voyage": "Scandinavia",
        "embark": date(2026, 8, 29),
        "disembark": date(2026, 9, 8),
        "fpd": date(2026, 4, 1),
        "fpd_paid": True,
        "revenue": 0,
        "commission_est": 0,
        "color": "#2d8a6e",
        "open_items": 2,
        "booking": "3078056",
        "priority": 3,
    },
    {
        "name": "Ely / Darrow",
        "ship": "Regent Grandeur",
        "voyage": "Scandinavia",
        "embark": date(2026, 8, 29),
        "disembark": date(2026, 9, 8),
        "fpd": date(2026, 3, 23),
        "fpd_paid": True,
        "revenue": 0,
        "commission_est": 0,
        "color": "#7b3fa8",
        "open_items": 2,
        "booking": "3096289",
        "priority": 4,
    },
    {
        "name": "Lyons",
        "ship": "Regent Splendor",
        "voyage": "Athens → NY",
        "embark": date(2026, 8, 11),
        "disembark": date(2026, 8, 25),
        "fpd": date(2026, 5, 11),
        "fpd_paid": False,
        "revenue": 0,
        "commission_est": 0,
        "color": "#c47a1e",
        "open_items": 3,
        "booking": "TBD",
        "priority": 5,
    },
    {
        "name": "Westbrook",
        "ship": "Silver Nova",
        "voyage": "Pacific/Hawaii",
        "embark": date(2026, 8, 20),
        "disembark": date(2026, 9, 5),
        "fpd": date(2026, 5, 1),
        "fpd_paid": False,
        "revenue": 0,
        "commission_est": 0,
        "color": "#6b6b6b",
        "open_items": 2,
        "booking": "PROSPECT",
        "priority": 6,
    },
    {
        "name": "Kuklinski Group",
        "ship": "Viking Mars",
        "voyage": "Panama Canal",
        "embark": date(2026, 12, 17),
        "disembark": date(2026, 12, 27),
        "fpd": date(2026, 3, 31),
        "fpd_paid": True,
        "revenue": 21244,
        "commission_est": 4249,   # ~20% Ponant/Viking rate
        "color": "#1a5c1a",
        "open_items": 4,
        "booking": "9593880/73/29",
        "priority": 7,
    },
]

# Sort by embark date
CLIENTS.sort(key=lambda c: c["embark"])


def date_to_pct(d: date) -> float:
    """Convert date to percentage position in 18-month window."""
    total_days = (WINDOW_END - WINDOW_START).days
    offset = (d - WINDOW_START).days
    return max(0.0, min(100.0, offset / total_days * 100))


def build_month_headers() -> str:
    """Build month column headers for Gantt."""
    headers = []
    d = WINDOW_START
    while d <= WINDOW_END:
        pct = date_to_pct(d)
        headers.append(
            f'<div class="month-label" style="left:{pct:.1f}%">'
            f'{d.strftime("%b %y")}</div>'
        )
        # advance to next month
        if d.month == 12:
            d = date(d.year + 1, 1, 1)
        else:
            d = date(d.year, d.month + 1, 1)
    return "\n".join(headers)


def build_gantt_rows() -> str:
    rows = []
    for c in CLIENTS:
        embark_pct = date_to_pct(c["embark"])
        disembark_pct = date_to_pct(c["disembark"])
        bar_width = max(0.5, disembark_pct - embark_pct)
        fpd_pct = date_to_pct(c["fpd"])
        today_pct = date_to_pct(TODAY)

        fpd_color = "#1a8a1a" if c["fpd_paid"] else "#c0392b"
        fpd_label = "✅ FPD" if c["fpd_paid"] else "⚠️ FPD"

        days_to_embark = (c["embark"] - TODAY).days
        if days_to_embark < 0:
            urgency = "on-voyage" if TODAY <= c["disembark"] else "complete"
        elif days_to_embark <= 30:
            urgency = "urgent"
        elif days_to_embark <= 90:
            urgency = "soon"
        else:
            urgency = "planned"

        urgency_colors = {
            "urgent": "#ffeaa7",
            "soon": "#dfe6e9",
            "planned": "#f8f9fa",
            "on-voyage": "#55efc4",
            "complete": "#eeeeee",
        }
        row_bg = urgency_colors.get(urgency, "#f8f9fa")

        open_badge = f'<span class="open-badge">{c["open_items"]} open</span>' if c["open_items"] > 0 else ""
        revenue_txt = f"${c['revenue']:,}" if c["revenue"] else "TBD"
        commission_txt = f"${c['commission_est']:,}" if c["commission_est"] else "TBD"

        rows.append(f"""
        <div class="gantt-row" style="background:{row_bg};">
          <div class="gantt-label">
            <div class="client-name">{c['name']} {open_badge}</div>
            <div class="client-meta">{c['ship']}</div>
            <div class="client-meta">{c['embark'].strftime('%b %d')} – {c['disembark'].strftime('%b %d, %Y')}</div>
            <div class="client-meta">Rev: {revenue_txt} · Comm: {commission_txt}</div>
          </div>
          <div class="gantt-track">
            <!-- FPD marker -->
            <div class="fpd-marker" style="left:{fpd_pct:.1f}%; background:{fpd_color};" title="{fpd_label} {c['fpd'].strftime('%b %d')}"></div>
            <!-- Voyage bar -->
            <div class="voyage-bar" style="left:{embark_pct:.1f}%; width:{bar_width:.1f}%; background:{c['color']};"
                 title="{c['voyage']}: {c['embark'].strftime('%b %d')} – {c['disembark'].strftime('%b %d')}">
              <span class="bar-label">{c['voyage']}</span>
            </div>
            <!-- Today line -->
            <div class="today-line" style="left:{today_pct:.1f}%;"></div>
          </div>
        </div>""")
    return "\n".join(rows)


def build_gap_analysis() -> str:
    """Identify clients with no voyage in next 90 days and no upcoming FPD."""
    gaps = []
    fpd_due = []
    for c in CLIENTS:
        days_to_embark = (c["embark"] - TODAY).days
        days_to_fpd = (c["fpd"] - TODAY).days if c["fpd"] else None

        if not c["fpd_paid"] and days_to_fpd is not None and 0 <= days_to_fpd <= 60:
            fpd_due.append(
                f'<li style="color:#c0392b;"><strong>{c["name"]}</strong> — FPD due '
                f'{c["fpd"].strftime("%b %d")} (T-{days_to_fpd}d) · {c["ship"]}</li>'
            )

        if days_to_embark > 180:
            gaps.append(
                f'<li><strong>{c["name"]}</strong> — {days_to_embark}d until embark · '
                f'{c["open_items"]} open items · <em>{c["voyage"]}</em></li>'
            )

    gap_html = "".join(gaps) if gaps else "<li style='color:#888'>No long-horizon gaps identified</li>"
    fpd_html = "".join(fpd_due) if fpd_due else "<li style='color:#1a8a1a'>All FPDs current ✅</li>"
    return f"""
    <div class="analysis-box">
      <h3>⚠️ FPD Alerts (Next 60 Days)</h3>
      <ul>{fpd_html}</ul>
    </div>
    <div class="analysis-box">
      <h3>📊 Long-Horizon Clients (&gt;180d to Embark)</h3>
      <ul>{gap_html}</ul>
    </div>"""


def build_revenue_table() -> str:
    total_rev = sum(c["revenue"] for c in CLIENTS if c["revenue"])
    total_comm = sum(c["commission_est"] for c in CLIENTS if c["commission_est"])
    rows = []
    for c in sorted(CLIENTS, key=lambda x: x["embark"]):
        rev = f"${c['revenue']:,}" if c["revenue"] else "TBD"
        comm = f"${c['commission_est']:,}" if c["commission_est"] else "TBD"
        paid_icon = "✅" if c["fpd_paid"] else "⚠️"
        rows.append(
            f"<tr><td>{c['name']}</td><td>{c['ship']}</td>"
            f"<td>{c['embark'].strftime('%b %Y')}</td>"
            f"<td>{paid_icon}</td><td>{rev}</td><td>{comm}</td></tr>"
        )
    return f"""
    <table class="rev-table">
      <thead>
        <tr><th>Client</th><th>Ship</th><th>Sail</th><th>FPD</th><th>Revenue</th><th>Est. Commission</th></tr>
      </thead>
      <tbody>{''.join(rows)}</tbody>
      <tfoot>
        <tr><td colspan="4"><strong>TOTALS (confirmed bookings)</strong></td>
            <td><strong>${total_rev:,}</strong></td>
            <td><strong>${total_comm:,}</strong></td></tr>
      </tfoot>
    </table>"""


def build_html() -> str:
    generated = datetime.now().strftime("%Y-%m-%d %H:%M MT")
    month_headers = build_month_headers()
    gantt_rows = build_gantt_rows()
    gap_analysis = build_gap_analysis()
    revenue_table = build_revenue_table()
    today_pct = date_to_pct(TODAY)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>D2M 18-Month Lifecycle Analysis — {generated}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: Georgia, serif; background: #f7f3ea; color: #222; padding: 24px; }}
  h1 {{ font-size: 1.8em; color: #1a3a5c; text-align: center; margin-bottom: 4px; }}
  .subtitle {{ text-align: center; color: #666; font-size: 0.9em; margin-bottom: 28px; }}
  .section-title {{ font-size: 1.1em; font-weight: bold; color: #1a3a5c;
                    margin: 28px 0 12px; border-bottom: 2px solid #1a3a5c; padding-bottom: 6px; }}

  /* Gantt */
  .gantt-container {{ background: #fff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);
                      overflow: hidden; margin-bottom: 24px; }}
  .gantt-header {{ position: relative; height: 32px; background: #1a3a5c; overflow: hidden; }}
  .month-label {{ position: absolute; top: 6px; color: #fff; font-size: 0.72em;
                  white-space: nowrap; transform: translateX(-50%); }}
  .gantt-row {{ display: flex; align-items: stretch; border-bottom: 1px solid #eee; }}
  .gantt-row:last-child {{ border-bottom: none; }}
  .gantt-label {{ width: 220px; min-width: 220px; padding: 12px 14px; border-right: 1px solid #ddd;
                  background: rgba(255,255,255,0.8); }}
  .client-name {{ font-weight: bold; font-size: 0.92em; color: #1a3a5c; }}
  .client-meta {{ font-size: 0.78em; color: #666; margin-top: 2px; }}
  .open-badge {{ display: inline-block; background: #e74c3c; color: #fff;
                 border-radius: 10px; padding: 1px 6px; font-size: 0.72em; margin-left: 4px; }}
  .gantt-track {{ flex: 1; position: relative; min-height: 60px; }}
  .voyage-bar {{ position: absolute; top: 50%; transform: translateY(-50%);
                 height: 28px; border-radius: 4px; display: flex; align-items: center;
                 overflow: hidden; cursor: default; }}
  .bar-label {{ color: #fff; font-size: 0.75em; padding: 0 6px; white-space: nowrap;
                overflow: hidden; text-overflow: ellipsis; }}
  .fpd-marker {{ position: absolute; top: 8px; width: 3px; height: 44px;
                 border-radius: 2px; opacity: 0.8; }}
  .today-line {{ position: absolute; top: 0; bottom: 0; width: 2px;
                 background: #e74c3c; opacity: 0.6; z-index: 10; }}
  .today-line::before {{ content: 'TODAY'; position: absolute; top: 2px; left: 4px;
                          font-size: 0.62em; color: #e74c3c; white-space: nowrap; }}

  /* Analysis */
  .analysis-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px; }}
  .analysis-box {{ background: #fff; border-radius: 8px; padding: 16px 20px;
                   box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
  .analysis-box h3 {{ font-size: 0.95em; color: #1a3a5c; margin-bottom: 10px; }}
  .analysis-box ul {{ list-style: none; font-size: 0.88em; }}
  .analysis-box ul li {{ padding: 5px 0; border-bottom: 1px solid #f0ece0; }}

  /* Revenue */
  .rev-table {{ width: 100%; border-collapse: collapse; background: #fff;
                border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
  .rev-table th {{ background: #1a3a5c; color: #fff; padding: 10px 14px;
                   text-align: left; font-size: 0.85em; }}
  .rev-table td {{ padding: 9px 14px; font-size: 0.88em; border-bottom: 1px solid #eee; }}
  .rev-table tfoot td {{ background: #f0ece0; font-size: 0.9em; }}

  .footer {{ text-align: center; color: #999; font-size: 0.78em; margin-top: 28px; }}
  @media (max-width: 700px) {{
    .analysis-grid {{ grid-template-columns: 1fr; }}
    .gantt-label {{ width: 140px; min-width: 140px; }}
  }}
</style>
</head>
<body>
<h1>Dreams2Memories Travel — 18-Month Lifecycle Analysis</h1>
<div class="subtitle">
  {WINDOW_START.strftime('%b %Y')} – {WINDOW_END.strftime('%b %Y')} · {len(CLIENTS)} active clients · Generated {generated}
</div>

<div class="section-title">📊 Voyage Timeline (Gantt)</div>
<div class="gantt-container">
  <div class="gantt-header" style="padding-left: 220px; position: relative;">
    {month_headers}
  </div>
  {gantt_rows}
</div>

<div class="section-title">🔍 Gap Analysis & Alerts</div>
<div class="analysis-grid">
  {gap_analysis}
</div>

<div class="section-title">💰 Revenue Projection</div>
{revenue_table}

<div class="footer">
  Dreams2Memories Travel, LLC · Thunderbird OS · MISSION-003 · {generated}<br>
  ⚠️ Revenue figures show confirmed bookings only. TBD = dossier confirmation needed.
</div>
</body>
</html>"""


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    html = build_html()
    OUTPUT_FILE.write_text(html, encoding="utf-8")
    log.info(f"18-month analysis written to {OUTPUT_FILE}")
    print(f"✅ MISSION-003 COMPLETE — {OUTPUT_FILE}")
    return str(OUTPUT_FILE)


if __name__ == "__main__":
    main()
