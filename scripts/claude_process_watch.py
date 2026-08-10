#!/usr/bin/env python3
"""
claude_process_watch.py — Guard dog: alert on long-lived `claude` CLI processes.
Never auto-kills (see claude-process-watch.service description). Run every 20min
by claude-process-watch.timer.

Root cause 2026-08-10: this script was referenced by a live systemd unit but
never committed to the repo — the unit has been failing ~120+ consecutive
scans, auto-repair correctly gave up, and it silently re-logged the same
"needs a human look" note into hale_incidents_today.json 37x/day with no one
ever seeing it (0 ELON proposals generated). This restores it.
"""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone

LONG_LIVED_THRESHOLD_SECONDS = 2 * 60 * 60  # 2h — a `claude` process alive this long is worth a human look, not a kill

try:
    from OpsCenter.incident_queue import enqueue_incident
except Exception:
    sys.path.insert(0, "/home/john/Thunderbird")
    try:
        from OpsCenter.incident_queue import enqueue_incident
    except Exception:
        def enqueue_incident(event: dict) -> None:
            print(f"[claude_process_watch] incident queue unavailable, event dropped: {event}")


import re

# Target: actual `claude` CLI binary invocations only (interactive/headless
# sessions that should exit but didn't). NOT the always-on daemon/gateway/MCP
# infrastructure that legitimately has "claude" in its path (litellm gateway,
# metrics_daemon.py, claude-code-router, *-mcp-server.cjs, claude-mem worker,
# context-mode, chroma-mcp) — first cut of this script flagged all of those
# and would have re-created the exact noisy-false-positive problem this audit
# exists to fix. Match the binary itself, not the substring "claude" anywhere.
_CLI_BINARY_RE = re.compile(r"(^|/)claude(\s|$)")
_EXCLUDE_SUBSTRINGS = (
    "claude_process_watch", "litellm", "metrics_daemon", "claude-code-router",
    "mcp-server", "claude-mem", "context-mode", "worker-service", "chroma-mcp",
)


def _long_lived_claude_processes() -> list[dict]:
    """ps etime for actual `claude` CLI binary processes; returns those over threshold."""
    try:
        out = subprocess.run(
            ["ps", "-eo", "pid,etimes,args"],
            capture_output=True, text=True, timeout=10, check=True,
        ).stdout
    except Exception as e:
        print(f"[claude_process_watch] ps failed: {e}")
        return []

    hits = []
    for line in out.splitlines()[1:]:
        parts = line.strip().split(None, 2)
        if len(parts) < 3:
            continue
        pid, etimes, args = parts
        if not _CLI_BINARY_RE.search(args) or any(x in args for x in _EXCLUDE_SUBSTRINGS):
            continue
        try:
            secs = int(etimes)
        except ValueError:
            continue
        if secs >= LONG_LIVED_THRESHOLD_SECONDS:
            hits.append({"pid": pid, "etime_seconds": secs, "cmd": args})
    return hits


def main() -> int:
    hits = _long_lived_claude_processes()
    if not hits:
        print(f"[claude_process_watch] {datetime.now(timezone.utc).isoformat()} — clean, no long-lived claude processes")
        return 0

    for h in hits:
        hours = h["etime_seconds"] / 3600
        print(f"[claude_process_watch] ALERT pid={h['pid']} alive {hours:.1f}h — {h['cmd'][:120]}")
        enqueue_incident({
            "service": "claude-process-watch.service",
            "event_type": "long_lived_claude_process",
            "action": "queued_for_brief",
            "status": "INFO",
            "note": f"pid {h['pid']} alive {hours:.1f}h — never auto-killed, review manually. cmd: {h['cmd'][:200]}",
            "elon_invoked": False,
        })
    return 0


if __name__ == "__main__":
    sys.exit(main())
