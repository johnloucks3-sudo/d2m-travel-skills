#!/usr/bin/env python3
"""
Hale Hourly Summary — emails the last hour's activity to johnloucks3@gmail.com.
Run via systemd timer: hale-hourly-summary.timer
"""
import json
import sys
from datetime import datetime
from pathlib import Path

BASE = Path("/home/john/Thunderbird")
sys.path.insert(0, str(BASE))

from core.ops.hale_activity_logger import read_since

MISSION_BOARD = BASE / "OpsCenter" / "mission_board.json"
STATE_FILE = BASE / "hale_state.json"
RECIPIENT = "johnloucks3@gmail.com"
SENDER = "d2mconcierge@gmail.com"


def load_missions() -> list[dict]:
    if not MISSION_BOARD.exists():
        return []
    try:
        data = json.loads(MISSION_BOARD.read_text())
        missions = data.get("active_missions", [])
        return [m for m in missions if m.get("status") not in ("complete", "completed")] if isinstance(missions, list) else []
    except Exception:
        return []


def load_system_mode() -> str:
    if not STATE_FILE.exists():
        return "UNKNOWN"
    try:
        return json.loads(STATE_FILE.read_text()).get("system_mode", "UNKNOWN")
    except Exception:
        return "UNKNOWN"


def build_html_body(events: list[dict], missions: list[dict], mode: str) -> str:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M MT")
    mode_color = {"GREEN": "#10b981", "YELLOW": "#f59e0b", "RED": "#ef4444"}.get(mode, "#666")

    # Categorize events
    errors = [e for e in events if e.get("category") == "ERROR"]
    decisions = [e for e in events if e.get("category") == "DECISION"]
    dispatches = [e for e in events if e.get("category") == "DISPATCH"]
    completions = [e for e in events if e.get("category") == "COMPLETE"]
    others = [e for e in events if e.get("category") not in ("ERROR", "DECISION", "DISPATCH", "COMPLETE")]

    def rows(evs: list[dict], color: str = "#334") -> str:
        if not evs:
            return '<tr><td style="color:#888;font-size:12px;padding:4px 0">None this hour</td></tr>'
        out = ""
        for e in evs:
            icon = e.get("icon", "•")
            title = e.get("title", "")
            detail = e.get("detail", "")
            ts = e.get("ts_local", "")
            detail_span = f'<br><span style="color:#888;font-size:11px">{detail}</span>' if detail else ""
            out += f'<tr><td style="padding:3px 0;color:{color};font-size:13px">{icon} {title}{detail_span}</td><td style="color:#aaa;font-size:11px;white-space:nowrap;padding-left:8px">{ts}</td></tr>'
        return out

    mission_rows = ""
    for m in missions[-10:]:
        mid = m.get("id", "?")
        title = m.get("title", "")[:70]
        status = m.get("status", "")
        s_color = {"in_progress": "#f59e0b", "complete": "#10b981"}.get(status, "#888")
        mission_rows += f'<tr><td style="font-size:13px;padding:3px 0"><span style="color:#94a3b8">{mid}</span> {title}</td><td style="color:{s_color};font-size:11px;white-space:nowrap;padding-left:8px">{status}</td></tr>'

    if not mission_rows:
        mission_rows = '<tr><td style="color:#888">No active missions</td></tr>'

    def section(title: str, body_rows: str) -> str:
        return f"""
        <tr><td colspan="2" style="padding-top:18px;padding-bottom:4px">
          <div style="font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:#64748b;border-bottom:1px solid #e2e8f0;padding-bottom:4px">{title}</div>
        </td></tr>
        {body_rows}"""

    total = len(events)
    subject = f"Hale Hourly — {total} events | {mode} | {now_str}"

    html = f"""
<div style="font-family:'Georgia',serif;max-width:640px;margin:0 auto;background:#fff;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden">
  <div style="background:#0f172a;padding:20px 24px;display:flex;justify-content:space-between;align-items:center">
    <div>
      <div style="color:#f1f5f9;font-size:18px;font-weight:700">⚡ Hale — Hourly Report</div>
      <div style="color:#64748b;font-size:12px;margin-top:2px">Thunderbird Wing | {now_str}</div>
    </div>
    <div style="background:{mode_color};color:#fff;padding:4px 14px;border-radius:20px;font-size:12px;font-weight:700">{mode}</div>
  </div>

  <div style="padding:20px 24px">
    <table style="width:100%;border-collapse:collapse">

      {section("Active Missions", mission_rows)}
      {section(f"Errors ({len(errors)})", rows(errors, "#ef4444"))}
      {section(f"Autonomous Decisions ({len(decisions)})", rows(decisions, "#f59e0b"))}
      {section(f"Tasks Dispatched ({len(dispatches)})", rows(dispatches, "#3b82f6"))}
      {section(f"Completions ({len(completions)})", rows(completions, "#10b981"))}
      {section(f"Other Events ({len(others)})", rows(others)) if others else ""}

    </table>
  </div>

  <div style="background:#f8fafc;padding:12px 24px;border-top:1px solid #e2e8f0">
    <div style="font-size:12px;color:#64748b">
      Live dashboard: <a href="https://itinerary.d2mluxury.quest/hale_dashboard.html" style="color:#0000ff">itinerary.d2mluxury.quest/hale_dashboard.html</a>
    </div>
    <div style="font-size:11px;color:#94a3b8;margin-top:4px">
      Col Victoria "Iron Vic" Hale · COS · Thunderbird Wing · Dreams2Memories Travel, LLC
    </div>
  </div>
</div>"""
    return subject, html


def send_summary():
    events = read_since(hours=1)
    missions = load_missions()
    mode = load_system_mode()

    subject, html_body = build_html_body(events, missions, mode)

    try:
        import sys
        sys.path.insert(0, str(BASE))
        from core.email.thunderbird_gmail import ThunderbirdGmail
        gmail = ThunderbirdGmail()
        gmail.send_email(
            to=RECIPIENT,
            subject=subject,
            body_html=html_body,
            sender_alias="concierge@d2mluxury.quest",
        )
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Hourly summary sent → {RECIPIENT}")
        return True
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Email send failed: {e}", file=sys.stderr)
        # Fall back to direct SMTP if gmail module unavailable
        return False


if __name__ == "__main__":
    success = send_summary()
    sys.exit(0 if success else 1)
