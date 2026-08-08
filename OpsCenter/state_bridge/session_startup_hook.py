"""Session startup hook — called by AGENTS.md / CLAUDE.md on session open.

Usage (from shell):
    python3 /home/john/Thunderbird/OpsCenter/state_bridge/session_startup_hook.py

What it does:
  1. Opens a new session record in the event store.
  2. Generates a delta briefing.
  3. Prints the briefing to stdout (caller captures it for injection).
  4. Records the new session id in `state_bridge_session.txt` so the daemon
     and downstream tools can attribute events to this session.

Designed to fail soft — any error prints a one-line warning to stderr and
exits 0 so a broken bridge never blocks session start.
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if __package__ in (None, ""):
    sys.path.insert(0, str(_HERE.parent.parent))
    from OpsCenter.state_bridge.event_store import EventStore, THUNDERBIRD_ROOT
    from OpsCenter.state_bridge.delta_briefing import DeltaBriefingGenerator
else:
    from .event_store import EventStore, THUNDERBIRD_ROOT
    from .delta_briefing import DeltaBriefingGenerator

SESSION_FILE = THUNDERBIRD_ROOT / "OpsCenter" / "state_bridge" / "state_bridge_session.txt"
STOP_GATE_FILE = THUNDERBIRD_ROOT / "OpsCenter" / "approved_plans.json"

log = logging.getLogger("state_bridge.hook")


def stop_gate_banner() -> str:
    """Return the STOP-GATE banner for this session.

    Consults OpsCenter/approved_plans.json. If no plan with status
    "active" exists, prints a STOP notice — work halts after this
    initial run until the Commander approves a plan. If an active plan
    exists, prints a continuation notice naming it.

    Fail-soft by design: any read/parse error or missing file yields the
    STOP notice — a broken registry must never silently authorize work.
    """
    active = []
    try:
        data = json.loads(STOP_GATE_FILE.read_text(encoding="utf-8"))
        active = [
            p for p in data.get("plans", [])
            if p.get("status") == "active"
        ]
    except Exception:  # noqa: BLE001 — fail-soft to STOP
        active = []
    if active:
        names = "; ".join(
            p.get("title") or p.get("plan_id") or "?" for p in active
        )
        return (
            "STOP-GATE: ACTIVE approved plan — " + names + ". "
            "Continue per that plan. Halt for new direction only when the "
            "plan ends or changes."
        )
    return (
        "STOP-GATE: NO approved plan is currently active. STOP after this "
        "initial run; do not auto-continue. Await Commander feedback, a "
        "question, or an approved plan before further work."
    )


def run() -> str:
    """Open a session, return briefing text."""
    # Restore full cadence — quiet_mode goes OFF at every session start
    try:
        _qm = Path(str(THUNDERBIRD_ROOT) + "/OpsCenter/quiet_mode.active")
        if _qm.exists():
            _qm.unlink()
    except Exception:
        pass

    store = EventStore()
    session_id = store.open_session(model="session-startup")
    try:
        SESSION_FILE.write_text(session_id, encoding="utf-8")
    except OSError as exc:
        print(f"[state_bridge] warn: could not write session file: {exc}", file=sys.stderr)
    briefing = DeltaBriefingGenerator(store).generate(current_session_id=session_id)
    store.record_event(
        session_id=session_id,
        event_type="checkpoint",
        entity_type="session",
        entity_key="start",
        summary=f"session opened {datetime.now().isoformat(timespec='seconds')}",
    )
    return briefing


def main() -> int:
    try:
        banner = stop_gate_banner()
        text = run()
        sys.stdout.write(banner)
        if not banner.endswith("\n"):
            sys.stdout.write("\n")
        sys.stdout.write("\n")
        sys.stdout.write(text)
        if not text.endswith("\n"):
            sys.stdout.write("\n")
        # Print Unified Multi-Engine Limit Meter
        try:
            from OpsCenter.unified_limit_meter import evaluate_unified_meter
            meter_output = evaluate_unified_meter()
            sys.stdout.write("\n" + meter_output + "\n")
        except Exception as _e:
            sys.stderr.write(f"[unified_limit_meter] warn: {_e}\n")
        return 0
    except Exception as exc:  # noqa: BLE001 — must never block session start
        sys.stderr.write(f"[state_bridge] hook error (continuing): {exc}\n")
        return 0


if __name__ == "__main__":
    sys.exit(main())
