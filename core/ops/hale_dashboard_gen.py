#!/usr/bin/env python3
"""
Hale Dashboard Generator — builds output/hale_dashboard.html every 60s.
Accessible at https://itinerary.d2mluxury.quest/hale_dashboard.html
"""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE = Path("/home/john/Thunderbird")
OUTPUT = BASE / "output" / "hale_dashboard.html"
MISSION_BOARD = BASE / "OpsCenter" / "mission_board.json"
DECISIONS_FILE = BASE / "hale_decisions.md"
STATE_FILE = BASE / "hale_state.json"
ACTIVITY_LOG = BASE / "hale_activity_log.jsonl"

SERVICES = [
    "nexus", "d2m-scheduler", "d2m-preflight",
    "d2m-email-scanner", "d2m-correspondence-sync",
    "d2m-airline-monitor", "thunderbird-backup-verify",
]

STATUS_COLORS = {
    "in_progress": "#f59e0b",
    "complete": "#10b981",
    "completed": "#10b981",
    "blocked": "#ef4444",
    "pending": "#6b7280",
    "open": "#3b82f6",
}


def svc_status(name: str) -> tuple[str, str]:
    """Returns (label, color) for a systemd user service — timer-aware."""
    try:
        # Check if failed
        failed = subprocess.run(
            ["systemctl", "--user", "is-failed", f"{name}.service"],
            capture_output=True, text=True, timeout=3
        ).stdout.strip()
        if failed == "failed":
            return "FAILED", "#ef4444"

        # Get Result property (success/failure from last run)
        result = subprocess.run(
            ["systemctl", "--user", "show", f"{name}.service", "-p", "Result,ActiveState"],
            capture_output=True, text=True, timeout=3
        ).stdout.strip()
        props = dict(line.split("=", 1) for line in result.splitlines() if "=" in line)
        state = props.get("ActiveState", "unknown")
        last = props.get("Result", "")

        if state == "active":
            return "RUNNING", "#10b981"
        if state == "inactive":
            if last == "success":
                return "OK (last run ✓)", "#10b981"
            elif last in ("exit-code", "core-dump"):
                return f"WARN ({last})", "#f59e0b"
            else:
                return "idle", "#6b7280"
        if state == "activating":
            return "STARTING", "#f59e0b"
        return state or "unknown", "#6b7280"
    except Exception:
        return "unknown", "#6b7280"


def load_missions() -> list[dict]:
    if not MISSION_BOARD.exists():
        return []
    try:
        data = json.loads(MISSION_BOARD.read_text())
        missions = data.get("active_missions", [])
        return missions[-20:] if isinstance(missions, list) else []
    except Exception:
        return []


def load_state() -> dict:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return {}


def load_recent_decisions(n: int = 8) -> list[str]:
    if not DECISIONS_FILE.exists():
        return []
    try:
        text = DECISIONS_FILE.read_text(encoding="utf-8")
        blocks = [b.strip() for b in text.split("---") if b.strip()]
        results = []
        for block in reversed(blocks):
            lines = block.splitlines()
            heading = next((l for l in lines if l.startswith("###")), "")
            summary = heading.replace("###", "").strip()
            if summary:
                results.append(summary)
            if len(results) >= n:
                break
        return results
    except Exception:
        return []


def load_activity(n: int = 60) -> list[dict]:
    if not ACTIVITY_LOG.exists():
        return []
    try:
        lines = ACTIVITY_LOG.read_text(encoding="utf-8").strip().splitlines()
        events = []
        for line in reversed(lines):
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except Exception:
                    pass
            if len(events) >= n:
                break
        return events
    except Exception:
        return []


LEVEL_COLORS = {
    "ERROR": "#ef4444",
    "WARN": "#f59e0b",
    "INFO": "#6b7280",
}

# Hale standup voice lines — used in mission table
_STANDUP_TEMPLATES = {
    "completed": [
        "Done, sir. {title} is deployed and closed.",
        "Complete. {title} — tested and in production.",
        "Closed out. {title} delivered.",
    ],
    "in_progress": [
        "Working this now. {snippet}",
        "In execution — {snippet}",
        "Active. {snippet}",
    ],
    "open": [
        "On deck, sir. {snippet}",
        "Queued. {snippet}",
        "Ready to run when the slot opens. {snippet}",
    ],
    "blocked": [
        "Blocked — flagging for your review. {snippet}",
        "Stalled on a dependency. {snippet} Needs your call.",
    ],
}

def hale_standup(mission: dict) -> str:
    """Generate a 1-2 sentence Hale standup brief for a mission."""
    status = mission.get("status", "open")
    title = mission.get("title", "").replace("Hale Autonomy — ", "").replace("MISSION-", "M-")
    desc = mission.get("description", "")
    logs = mission.get("logs", [])

    # Pull freshest log note if available
    latest_note = ""
    if logs:
        latest_note = logs[-1].get("note", "")[:90] if isinstance(logs[-1], dict) else ""

    # Build snippet: latest log note beats description
    raw_snippet = latest_note or desc
    snippet = raw_snippet[:85].rstrip(".").strip()
    if snippet:
        snippet = snippet[0].upper() + snippet[1:]

    templates = _STANDUP_TEMPLATES.get(status, _STANDUP_TEMPLATES["open"])
    # Use hash of mission ID to pick a stable template (not random each refresh)
    idx = hash(mission.get("id", "")) % len(templates)
    line = templates[idx].format(title=title, snippet=snippet + "." if snippet else "")

    # For completed missions, append a short "what shipped" note
    if status in ("completed", "complete") and snippet:
        line = f"{line} {snippet[:70]}."

    return line.strip()


def build_html() -> str:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M MT")
    missions = load_missions()
    state = load_state()
    decisions = load_recent_decisions()
    events = load_activity()

    wing_health = state.get("wing_health", {})
    system_mode = state.get("system_mode", "UNKNOWN")
    mode_color = {"GREEN": "#10b981", "YELLOW": "#f59e0b", "RED": "#ef4444"}.get(system_mode, "#6b7280")

    # --- Missions HTML ---
    missions_rows = ""
    for m in reversed(missions):
        mid = m.get("id", "?")
        title = m.get("title", "")[:68]
        status = m.get("status", "open")
        priority = m.get("priority", "")
        color = STATUS_COLORS.get(status, "#6b7280")
        brief = hale_standup(m)
        brief_html = f'<br><span style="color:#94a3b8;font-size:12px;font-style:italic">{brief}</span>' if brief else ""
        missions_rows += f"""
        <tr>
          <td style="color:#64748b;font-size:11px;white-space:nowrap;vertical-align:top;padding-right:8px">{mid}</td>
          <td style="max-width:480px">{title}{brief_html}</td>
          <td style="vertical-align:top;padding-left:8px"><span style="background:{color};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px">{status}</span></td>
          <td style="color:#64748b;font-size:11px;white-space:nowrap;vertical-align:top;padding-left:6px">{priority}</td>
        </tr>"""

    # --- Service health HTML ---
    svc_rows = ""
    for svc in SERVICES:
        state_val, col = svc_status(svc)
        svc_rows += f"""
        <div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid #1e293b">
          <span style="font-size:13px">{svc}</span>
          <span style="color:{col};font-size:12px;font-weight:600">{state_val}</span>
        </div>"""

    # --- Decisions HTML ---
    dec_items = ""
    for d in decisions:
        dec_items += f'<li style="margin-bottom:6px;color:#cbd5e1;font-size:13px">{d}</li>'

    # --- Activity log HTML ---
    activity_rows = ""
    for ev in events:
        icon = ev.get("icon", "•")
        ts = ev.get("ts_local", "")
        cat = ev.get("category", "")
        title = ev.get("title", "")[:90]
        detail = ev.get("detail", "")[:80]
        lv = ev.get("level", "INFO")
        row_color = LEVEL_COLORS.get(lv, "#6b7280")
        detail_html = f'<br><span style="color:#64748b;font-size:11px">{detail}</span>' if detail else ""
        activity_rows += f"""
        <tr>
          <td style="color:#64748b;font-size:11px;white-space:nowrap;padding-right:8px">{ts}</td>
          <td style="font-size:11px;color:#94a3b8;white-space:nowrap;padding-right:8px">{icon} {cat}</td>
          <td style="font-size:13px;color:{row_color}">{title}{detail_html}</td>
        </tr>"""

    if not activity_rows:
        activity_rows = '<tr><td colspan="3" style="color:#475569;text-align:center;padding:20px">No activity logged yet</td></tr>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="30">
<title>Hale COS — Thunderbird Dashboard</title>
<style>
  * {{ box-sizing:border-box; margin:0; padding:0 }}
  body {{ background:#0f172a; color:#e2e8f0; font-family:'SF Pro Display',system-ui,sans-serif; padding:16px }}
  h2 {{ font-size:13px; text-transform:uppercase; letter-spacing:.1em; color:#475569; margin-bottom:8px; margin-top:0 }}
  .card {{ background:#1e293b; border-radius:8px; padding:16px; margin-bottom:16px }}
  .header {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:20px }}
  .badge {{ padding:4px 12px; border-radius:20px; font-size:12px; font-weight:700 }}
  table {{ width:100%; border-collapse:collapse }}
  td {{ padding:6px 4px; border-bottom:1px solid #1e293b; vertical-align:top }}
  tr:last-child td {{ border-bottom:none }}
  .grid2 {{ display:grid; grid-template-columns:1fr 1fr; gap:16px }}
  @media(max-width:700px){{ .grid2{{ grid-template-columns:1fr }} }}
  .pulse {{ animation:pulse 2s infinite }}
  @keyframes pulse {{ 0%,100%{{opacity:1}} 50%{{opacity:.5}} }}
</style>
</head>
<body>

<div class="header">
  <div>
    <div style="font-size:22px;font-weight:700;color:#f1f5f9">⚡ Hale COS — Thunderbird Wing</div>
    <div style="font-size:12px;color:#475569;margin-top:2px">Ms. Victoria "Victory" Hale, SES-6 | Auto-refresh every 30s</div>
  </div>
  <div style="text-align:right">
    <div class="badge" style="background:{mode_color};color:#fff">● {system_mode}</div>
    <div style="font-size:11px;color:#475569;margin-top:4px">{now_str}</div>
  </div>
</div>

<!-- Missions -->
<div class="card">
  <h2>Active Missions</h2>
  <table>
    <thead>
      <tr style="color:#64748b;font-size:11px;text-transform:uppercase">
        <td style="padding-bottom:6px">ID</td>
        <td>Title</td>
        <td>Status</td>
        <td>P</td>
      </tr>
    </thead>
    <tbody>{missions_rows or '<tr><td colspan="4" style="color:#475569;text-align:center;padding:20px">No missions</td></tr>'}</tbody>
  </table>
</div>

<div class="grid2">

<!-- Service Health -->
<div class="card">
  <h2>Service Health</h2>
  {svc_rows}
</div>

<!-- Recent Decisions -->
<div class="card">
  <h2>Recent Autonomous Decisions</h2>
  <ul style="padding-left:18px">
    {dec_items or '<li style="color:#475569">No decisions logged</li>'}
  </ul>
</div>

</div>

<!-- Activity Timeline -->
<div class="card">
  <h2>Activity Log <span style="font-size:11px;color:#475569">(last 60 events, newest first)</span></h2>
  <div style="max-height:420px;overflow-y:auto">
  <table>
    <tbody>{activity_rows}</tbody>
  </table>
  </div>
</div>

<div style="text-align:center;font-size:11px;color:#334155;margin-top:8px">
  Dreams2Memories Travel, LLC · Thunderbird OS · Generated {now_str}
</div>

</body>
</html>"""
    return html


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    html = build_html()
    OUTPUT.write_text(html, encoding="utf-8")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Dashboard written → {OUTPUT}")


if __name__ == "__main__":
    main()
