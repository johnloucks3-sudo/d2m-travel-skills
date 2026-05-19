"""ALPHA Wing Watch — monitors wing_comms.md for new entries targeting HALE ALPHA
or HALE-YODA broadcasts. Surfaces alerts to alpha_alerts.md.
When ALPHA needs BRAVO: writes structured task to claude_inbox.md (watcher spawns BRAVO).

Usage:
    python3 alpha_wing_watch.py check   # check for new wing_comms entries
    python3 alpha_wing_watch.py alert-bravo "task description" --priority P0
"""
import json, os, re, sys, time
from pathlib import Path
from datetime import datetime, timezone

BASE = Path("/home/john/Thunderbird")
WING_COMMS = BASE / "OpsCenter/collaboration/wing_comms.md"
CLAUDE_INBOX = BASE / "claude_inbox.md"
ALERTS_FILE = BASE / "OpsCenter/alpha_alerts.md"
STATE_FILE = BASE / "state/alpha_watch_state.json"

TRIGGERS = ["@ALPHA", "HALE ALPHA", "ALPHA GROUP", "ALPHA —", "[HALE ALPHA", "HALE-YODA"]


def _load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"last_line_count": 0, "last_check": None}


def _save_state(s):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(s, indent=2))


def check():
    state = _load_state()
    if not WING_COMMS.exists():
        print("wing_comms.md not found")
        return

    lines = WING_COMMS.read_text().splitlines()
    current_count = len(lines)
    last_count = state.get("last_line_count", 0)

    # First run — just record position, don't alert on history
    first_run = last_count == 0

    if not first_run and current_count <= last_count:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        state["last_check"] = now
        _save_state(state)
        print("No new entries since last check")
        return

    if first_run:
        state["last_line_count"] = current_count
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        state["last_check"] = now
        _save_state(state)
        print(f"First run — indexed {current_count} lines. No alerts (history suppressed).")
        return

    # Find new entries
    new_lines = lines[last_count:]
    new_text = "\n".join(new_lines)

    # Check if any ALPHA-relevant triggers
    matched = []
    for trigger in TRIGGERS:
        if trigger in new_text:
            # Extract the section header
            for line in new_lines:
                if trigger in line or line.startswith("## [") or line.startswith("---"):
                    matched.append(line.strip()[:120])

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    state["last_line_count"] = current_count
    state["last_check"] = now
    _save_state(state)

    if matched:
        ALERTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        entry = f"\n---\n## 🔔 ALPHA ALERT — {now}\n"
        entry += f"**New entries in wing_comms.md targeting ALPHA:**\n"
        for m in matched:
            entry += f"- {m}\n"
        existing = ALERTS_FILE.read_text() if ALERTS_FILE.exists() else "# ALPHA Alerts\n"
        ALERTS_FILE.write_text(existing + entry)
        print(f"ALERT: {len(matched)} trigger(s) detected — logged to {ALERTS_FILE.name}")
    else:
        print(f"Checked: {current_count - last_count} new lines, no ALPHA triggers")

    # Check for YODA broadcasts (Commander directives)
    if "HALE-YODA" in new_text or "COMMANDER" in new_text.upper():
        print("  ⚠️  HALE-YODA or COMMANDER mention detected in new content")


def alert_bravo(task_desc, priority="P1"):
    """Write a task to claude_inbox.md → watcher picks it up → spawns BRAVO."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entry = f"""

---
## TASK: ALPHA-REQ-BRAVO-{int(time.time())}
status: UNREAD
from: HALE-ALPHA
injected: {now}
priority: {priority}
task: |
  {task_desc}
  Context: hale_handshake.jsonl has current ALPHA state.
"""
    with open(CLAUDE_INBOX, "a") as f:
        f.write(entry)
    print(f"✅ BRAVO tasked via claude_inbox.md — watcher will spawn Claude headless")
    print(f"   Priority: {priority}")
    print(f"   Task: {task_desc[:80]}")
    return entry


def status():
    state = _load_state()
    print(f"Last check: {state.get('last_check', 'never')}")
    print(f"Last line count: {state.get('last_line_count', 0)}")

    if ALERTS_FILE.exists():
        alerts = ALERTS_FILE.read_text()
        count = alerts.count("🔔 ALPHA ALERT")
        print(f"Pending alerts: {count}")
        if count > 0:
            print("\n--- Latest alert ---")
            print(alerts.split("🔔 ALPHA ALERT")[-1][:300] if count > 0 else "none")
    else:
        print("No alerts file")

    # Check handshake state
    hs = BASE / "OpsCenter/hale_handshake.jsonl"
    if hs.exists():
        with open(hs) as f:
            entries = [l for l in f if l.strip()]
        last = json.loads(entries[-1]) if entries else None
        if last:
            print(f"\nHandshake last: {last.get('instance')} — {last.get('event')} @ {last.get('opened_at','?')[:19]}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: alpha_wing_watch.py [check|alert-bravo|status]")
        sys.exit(1)

    action = sys.argv[1]
    if action == "check":
        check()
    elif action == "alert-bravo":
        if len(sys.argv) < 3:
            print("Usage: alpha_wing_watch.py alert-bravo 'task description' [--priority P0|P1|P2]")
            sys.exit(1)
        desc = sys.argv[2]
        prio = "P1"
        if "--priority" in sys.argv:
            idx = sys.argv.index("--priority")
            if idx + 1 < len(sys.argv):
                prio = sys.argv[idx + 1]
        alert_bravo(desc, prio)
    elif action == "status":
        status()
    else:
        print(f"Unknown action: {action}")
