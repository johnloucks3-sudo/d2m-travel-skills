"""
WAR Generator — Weekly Activity Report
Runs every Friday at 2100 MT. Generates WAR HTML from git log + mission board,
sends to johnloucks3@gmail.com as full send (internal comms SO).
"""

import json
import subprocess
import sys
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

MT = ZoneInfo("America/Denver")
NOW = datetime.now(MT)
WEEK_END = NOW.strftime("%Y-%m-%d")
WEEK_START = (NOW - timedelta(days=6)).strftime("%Y-%m-%d")
WEEK_LABEL = f"{(NOW - timedelta(days=6)).strftime('%b %d')}–{NOW.strftime('%b %d, %Y')}"
OUT_FILE = ROOT / "WAR" / f"WAR_{WEEK_START}.html"
LOG_FILE = ROOT / "logs" / "war_generator.log"


def log(msg):
    ts = datetime.now(MT).strftime("%Y-%m-%d %H:%M MT")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def get_git_log():
    try:
        result = subprocess.run(
            ["git", "log", f"--since={WEEK_START}", f"--until={WEEK_END}",
             "--pretty=format:%h|%ad|%s", "--date=short"],
            cwd=ROOT, capture_output=True, text=True
        )
        lines = [l.strip() for l in result.stdout.splitlines() if l.strip()]
        commits = []
        for line in lines:
            parts = line.split("|", 2)
            if len(parts) == 3:
                commits.append({"hash": parts[0], "date": parts[1], "msg": parts[2]})
        return commits
    except Exception as e:
        log(f"git log error: {e}")
        return []


def get_mission_stats():
    try:
        mb = json.loads((ROOT / "OpsCenter" / "mission_board.json").read_text())
        missions = mb.get("missions", mb.get("tasks", []))
        total = len(missions)
        active = len([m for m in missions if m.get("status") in ("active", "in_progress")])
        closed_this_week = [
            m for m in missions
            if m.get("status") == "complete" and WEEK_START in str(m.get("notes", ""))
        ]
        return total, active, closed_this_week
    except Exception as e:
        log(f"mission board error: {e}")
        return 0, 0, []


def get_financial_pulse():
    try:
        state = json.loads((ROOT / "hale_state.json").read_text())
        fp = state.get("financial_pulse", {})
        return fp
    except Exception:
        return {}


def categorize_commit(msg):
    msg_l = msg.lower()
    if msg_l.startswith("feat"):
        return "BUILD"
    if msg_l.startswith("fix"):
        return "FIX"
    if "client" in msg_l or "dossier" in msg_l or "spencer" in msg_l or "mcleod" in msg_l or "kuklinski" in msg_l:
        return "CLIENT"
    if "ops" in msg_l or "telegram" in msg_l or "relay" in msg_l:
        return "OPS"
    return "BUILD"


TAG_CSS = {
    "BUILD": "tag-build",
    "FIX": "tag-fix",
    "CLIENT": "tag-client",
    "OPS": "tag-ops",
    "DOC": "tag-doc",
}


def build_commit_rows(commits):
    rows = ""
    for c in commits[:40]:
        tag = categorize_commit(c["msg"])
        css = TAG_CSS.get(tag, "tag-build")
        rows += (
            f'<div class="build-item">'
            f'<span class="tag {css}">{tag}</span>'
            f'<div class="item-body"><strong>{c["date"]}</strong> — {c["msg"]}'
            f' <span style="color:#aaa;font-size:0.78rem;">({c["hash"]})</span></div>'
            f'</div>\n'
        )
    return rows or "<p style='color:#888;font-size:0.85rem;'>No commits found for this period.</p>"


def build_mission_rows(closed):
    if not closed:
        return "<tr><td colspan='2' style='color:#888;'>No missions closed this week.</td></tr>"
    rows = ""
    for m in closed:
        rows += f"<tr><td>{m.get('id','?')}</td><td>{m.get('title','')[:80]}</td></tr>\n"
    return rows


def generate_html(commits, total_m, active_m, closed_m, fp):
    commit_count = len(commits)
    closed_count = len(closed_m)
    pipeline = fp.get("total_d2m_pipeline", 0)
    commission = fp.get("sheet_commission_expected", 0)
    received = fp.get("tess_received", 0)

    commit_rows = build_commit_rows(commits)
    mission_rows = build_mission_rows(closed_m)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>D2M WAR — Week of {WEEK_LABEL}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: Georgia, 'Times New Roman', serif; background: #f7f3ea; color: #1a1a1a; }}
  .header {{ background: linear-gradient(135deg, #003087 0%, #000d3a 100%); color: white; padding: 40px 48px 28px; }}
  .header-eye {{ font-size: 0.65rem; letter-spacing: 3px; text-transform: uppercase; color: #a8c4ff; margin-bottom: 6px; }}
  .header-title {{ font-size: 2rem; font-weight: normal; color: #fff; }}
  .header-sub {{ font-size: 1rem; color: #f0c040; margin-top: 6px; }}
  .header-meta {{ font-size: 0.75rem; color: #a8c4ff; margin-top: 10px; }}
  .accentline {{ height: 4px; background: linear-gradient(90deg, #003087, #a9b0b7, #fff, #a9b0b7, #003087); }}
  .stat-bar {{ background: #003087; padding: 12px 48px; display: flex; gap: 36px; flex-wrap: wrap; }}
  .stat {{ color: white; font-size: 0.75rem; }}
  .stat span {{ color: #f0c040; font-weight: bold; font-size: 0.95rem; display: block; margin-bottom: 2px; }}
  .body {{ max-width: 940px; margin: 0 auto; padding: 36px 48px; }}
  .section-head {{ font-size: 0.65rem; text-transform: uppercase; letter-spacing: 2.5px; color: #003087; border-bottom: 2px solid #003087; padding-bottom: 5px; margin: 30px 0 14px; }}
  .section-head.gold {{ color: #b45309; border-color: #b45309; }}
  .section-head.green {{ color: #15803d; border-color: #15803d; }}
  .day-card {{ background: white; border-radius: 8px; overflow: hidden; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,48,135,0.07); }}
  .day-card-header {{ background: #003087; color: white; padding: 12px 22px; }}
  .day-label {{ font-size: 0.62rem; letter-spacing: 2px; text-transform: uppercase; color: #a8c4ff; }}
  .day-title {{ font-size: 1rem; color: white; margin-top: 2px; }}
  .day-card-body {{ padding: 16px 22px; }}
  .build-item {{ display: flex; gap: 12px; padding: 9px 0; border-bottom: 1px solid #ede8df; font-size: 0.86rem; line-height: 1.6; }}
  .build-item:last-child {{ border-bottom: none; }}
  .tag {{ flex-shrink: 0; font-size: 0.65rem; font-weight: bold; padding: 2px 7px; border-radius: 9px; height: fit-content; margin-top: 2px; letter-spacing: 0.4px; }}
  .tag-build {{ background: #eff6ff; color: #1d4ed8; }}
  .tag-fix {{ background: #fef2f2; color: #b91c1c; }}
  .tag-client {{ background: #f0fdf4; color: #15803d; }}
  .tag-ops {{ background: #fffbeb; color: #92400e; }}
  .tag-doc {{ background: #f5f3ff; color: #6d28d9; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; margin: 10px 0; }}
  thead tr {{ background: #003087; color: white; }}
  thead th {{ padding: 9px 13px; text-align: left; font-size: 0.68rem; letter-spacing: 0.5px; font-weight: normal; }}
  tbody tr {{ border-bottom: 1px solid #ede8df; }}
  tbody tr:nth-child(even) {{ background: #faf8f4; }}
  tbody td {{ padding: 9px 13px; color: #333; }}
  .num {{ color: #003087; font-weight: bold; }}
  .footer {{ background: #000d3a; padding: 22px 48px; margin-top: 40px; text-align: center; }}
  .footer-brand {{ color: #f0c040; font-size: 0.95rem; letter-spacing: 3px; text-transform: uppercase; }}
  .footer-sub {{ color: #a8c4ff; font-size: 0.72rem; margin-top: 4px; }}
</style>
</head>
<body>

<div class="header">
  <div class="header-eye">Dreams2Memories Travel · Thunderbird Wing · Internal</div>
  <div class="header-title">Weekly Activity Report</div>
  <div class="header-sub">Week of {WEEK_LABEL}</div>
  <div class="header-meta">Auto-generated {NOW.strftime('%Y-%m-%d %H:%M MT')} · Commander Eyes Only</div>
</div>
<div class="accentline"></div>

<div class="stat-bar">
  <div class="stat"><span>{commit_count}</span>Commits</div>
  <div class="stat"><span>{closed_count}</span>Missions Closed</div>
  <div class="stat"><span>${pipeline:,.0f}</span>D2M Pipeline</div>
  <div class="stat"><span>${commission:,.0f}</span>Commission Expected</div>
  <div class="stat"><span>${received:,.2f}</span>Received (TESS)</div>
  <div class="stat"><span>{active_m}</span>Active Missions</div>
</div>

<div class="body">

  <div class="section-head">Week in Review — All Commits</div>
  <div class="day-card">
    <div class="day-card-header">
      <div class="day-label">Git Log</div>
      <div class="day-title">{WEEK_START} → {WEEK_END} · {commit_count} commits</div>
    </div>
    <div class="day-card-body">
      {commit_rows}
    </div>
  </div>

  <div class="section-head gold">Missions Closed This Week</div>
  <table>
    <thead><tr><th>Mission ID</th><th>Title</th></tr></thead>
    <tbody>{mission_rows}</tbody>
  </table>

  <div class="section-head green">Financial Pulse</div>
  <table>
    <thead><tr><th>Metric</th><th>Value</th></tr></thead>
    <tbody>
      <tr><td>D2M Pipeline (upcoming voyages)</td><td class="num">${pipeline:,.2f}</td></tr>
      <tr><td>Commission Expected (total sheet)</td><td class="num">${commission:,.2f}</td></tr>
      <tr><td>Checks Received (TESS)</td><td class="num">${received:,.2f}</td></tr>
      <tr><td>Active Missions on Board</td><td class="num">{active_m} of {total_m}</td></tr>
    </tbody>
  </table>

</div>

<div class="footer">
  <div class="footer-brand">Dreams2Memories Travel · Thunderbird Wing</div>
  <div class="footer-sub">WAR auto-generated every Friday at 2100 MT</div>
</div>
</body>
</html>"""


def send_to_commander(html_content):
    try:
        from core.email.thunderbird_gmail import gmail_send_from_wing
        subject = f"WAR — Week of {WEEK_LABEL} · {len(get_git_log())} commits"
        result = gmail_send_from_wing(
            to="johnloucks3@gmail.com",
            subject=subject,
            body=html_content,
        )
        log(f"WAR sent to Commander: {result}")
        return True
    except Exception as e:
        log(f"Send failed: {e}")
        return False


def main():
    log(f"WAR generation starting — week {WEEK_START} → {WEEK_END}")
    commits = get_git_log()
    total_m, active_m, closed_m = get_mission_stats()
    fp = get_financial_pulse()

    log(f"Data: {len(commits)} commits, {len(closed_m)} missions closed, pipeline ${fp.get('total_d2m_pipeline',0):,.0f}")

    html = generate_html(commits, total_m, active_m, closed_m, fp)

    OUT_FILE.parent.mkdir(exist_ok=True)
    OUT_FILE.write_text(html)
    log(f"WAR written: {OUT_FILE}")

    sent = send_to_commander(html)
    log(f"WAR complete. Sent: {sent}")


if __name__ == "__main__":
    main()
