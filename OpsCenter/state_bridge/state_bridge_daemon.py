"""State Bridge daemon — orchestrates watchers and serves CLI subcommands.

Subcommands:
  --daemon    Run as background service (60s tick).
  --briefing  Print a one-shot briefing to stdout.
  --status    Print daemon health.
  --prune     Archive events older than 30 days (decisions preserved).
  --inject    Print briefing + open a new session record (used by hook).

The daemon writes its PID and logs into the state_bridge directory so a
single, well-known location holds all runtime state alongside the SQLite DB.
"""
from __future__ import annotations

import argparse
import json
import logging
import logging.handlers
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Allow `python3 state_bridge_daemon.py` invocation as well as -m.
_HERE = Path(__file__).resolve().parent
if __package__ in (None, ""):
    sys.path.insert(0, str(_HERE.parent.parent))
    from OpsCenter.state_bridge.event_store import EventStore, THUNDERBIRD_ROOT
    from OpsCenter.state_bridge.delta_briefing import DeltaBriefingGenerator
    from OpsCenter.state_bridge.watchers.git_watcher import GitWatcher
    from OpsCenter.state_bridge.watchers.file_watcher import FileWatcher
    from OpsCenter.state_bridge.watchers.mission_watcher import MissionWatcher
else:
    from .event_store import EventStore, THUNDERBIRD_ROOT
    from .delta_briefing import DeltaBriefingGenerator
    from .watchers.git_watcher import GitWatcher
    from .watchers.file_watcher import FileWatcher
    from .watchers.mission_watcher import MissionWatcher

STATE_DIR = THUNDERBIRD_ROOT / "OpsCenter" / "state_bridge"
PID_FILE = STATE_DIR / "state_bridge.pid"
LOG_FILE = STATE_DIR / "state_bridge.log"
TICK_SECONDS = 60

log = logging.getLogger("state_bridge")


def _configure_logging() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=2_000_000, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s"
    ))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    # Avoid duplicate handlers in long-running daemon
    if not any(isinstance(h, logging.handlers.RotatingFileHandler)
               and getattr(h, "baseFilename", "") == str(LOG_FILE)
               for h in root.handlers):
        root.addHandler(handler)


class Daemon:
    """Holds the EventStore + watchers + the persistent session id."""

    def __init__(self):
        self.store = EventStore()
        self.session_id = self.store.open_session(model="daemon")
        self.git = GitWatcher(self.store)
        self.files = FileWatcher(self.store)
        self.missions = MissionWatcher(self.store)
        self._running = True

    def _install_signals(self) -> None:
        signal.signal(signal.SIGTERM, self._on_stop)
        signal.signal(signal.SIGINT, self._on_stop)

    def _on_stop(self, signum, _frame) -> None:
        log.info("Received signal %s — shutting down.", signum)
        self._running = False

    def run(self) -> None:
        log.info("Daemon starting (session=%s tick=%ss)", self.session_id, TICK_SECONDS)
        # Write PID
        try:
            PID_FILE.write_text(str(os.getpid()))
        except OSError as exc:
            log.warning("Could not write PID file: %s", exc)
        self._install_signals()

        # Seed
        try:
            self.git.initialize(self.session_id)
            self.files.initialize(self.session_id)
            self.missions.initialize(self.session_id)
        except Exception as exc:  # noqa: BLE001
            log.exception("Initialization error: %s", exc)

        # Loop
        while self._running:
            tick_start = time.monotonic()
            try:
                self.git.tick(self.session_id)
                self.files.tick(self.session_id)
                self.missions.tick(self.session_id)
            except Exception as exc:  # noqa: BLE001 — daemon must not die
                log.exception("Tick error: %s", exc)
            elapsed = time.monotonic() - tick_start
            sleep_for = max(1.0, TICK_SECONDS - elapsed)
            # Sleep in 1-second slices so SIGTERM is responsive
            slept = 0.0
            while slept < sleep_for and self._running:
                time.sleep(1.0)
                slept += 1.0

        self.shutdown()

    def shutdown(self) -> None:
        try:
            self.store.close_session(self.session_id, issues=[])
        except Exception as exc:  # noqa: BLE001
            log.warning("close_session failed: %s", exc)
        try:
            if PID_FILE.exists():
                PID_FILE.unlink()
        except OSError:
            pass
        log.info("Daemon stopped.")


# ---------------- CLI subcommands ----------------

def _is_pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return pid > 0 and True  # PermissionError means it exists
    except OSError:
        return False


def cmd_status() -> int:
    print(f"State Bridge status @ {datetime.now().isoformat(timespec='seconds')}")
    print(f"  DB:   {EventStore().db_path}")
    print(f"  PID file: {PID_FILE}")
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
        except (OSError, ValueError):
            print("  PID file unreadable")
            pid = 0
        alive = _is_pid_alive(pid) if pid else False
        print(f"  Daemon PID: {pid} ({'ALIVE' if alive else 'STALE'})")
    else:
        print("  Daemon: not running")
    store = EventStore()
    latest = store.get_latest_session()
    if latest:
        print(f"  Last session: {latest['id']} started {latest['started_at']} "
              f"ended {latest.get('ended_at') or '(open)'}")
    chain = store.get_session_chain(3)
    print(f"  Sessions tracked (last 3): {len(chain)}")
    for s in chain:
        print(f"    - {s['id']}  events={s.get('event_count', 0)}  "
              f"started={s['started_at']}")
    return 0


def cmd_briefing(open_session: bool = False) -> int:
    """Generate briefing. If open_session=True, also open a session record."""
    store = EventStore()
    session_id = None
    if open_session:
        session_id = store.open_session(model="hook")
    gen = DeltaBriefingGenerator(store)
    out = gen.generate(current_session_id=session_id)
    print(out)
    if open_session and session_id:
        # Mark session start with a checkpoint event
        store.record_event(session_id, "checkpoint", "session", "start",
                            "session opened via --inject", {})
    return 0


def cmd_prune(days: int = 30) -> int:
    n = EventStore().prune_older_than(days=days)
    print(f"Pruned {n} event(s) older than {days} days (decisions preserved).")
    return 0


def cmd_daemon() -> int:
    # Refuse to start if a live PID is recorded
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
        except (OSError, ValueError):
            pid = 0
        if pid and _is_pid_alive(pid):
            print(f"Daemon already running (pid={pid}). Exiting.", file=sys.stderr)
            return 2
        else:
            try:
                PID_FILE.unlink()
            except OSError:
                pass
    Daemon().run()
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="state_bridge_daemon",
        description="State Bridge — session continuity daemon",
    )
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--daemon", action="store_true", help="Run as background service")
    g.add_argument("--briefing", action="store_true",
                    help="Print a one-shot briefing (no session opened)")
    g.add_argument("--inject", action="store_true",
                    help="Print briefing AND open a new session record")
    g.add_argument("--status", action="store_true", help="Show daemon status")
    g.add_argument("--prune", action="store_true",
                    help="Archive events older than N days (default 30)")
    p.add_argument("--days", type=int, default=30,
                    help="Pruning window in days (default 30)")
    return p


def main(argv: list[str] | None = None) -> int:
    _configure_logging()
    args = build_parser().parse_args(argv)
    try:
        if args.status:
            return cmd_status()
        if args.briefing:
            return cmd_briefing(open_session=False)
        if args.inject:
            return cmd_briefing(open_session=True)
        if args.prune:
            return cmd_prune(days=args.days)
        if args.daemon:
            return cmd_daemon()
    except Exception as exc:  # noqa: BLE001
        log.exception("Fatal: %s", exc)
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


# ---------------- MCP tool registration shim ----------------
#
# The wing has an MCP server in `core/mcp/` (dreams2memories). When that
# server starts, it imports skill modules from this directory and registers
# any `MCP_TOOLS` list. We expose two callable tools here so OpenCode /
# Claude Code can request a briefing or record a checkpoint via MCP.

def mcp_state_bridge_briefing(arguments: dict | None = None) -> dict:
    """MCP tool: return current State Bridge briefing as Markdown."""
    arguments = arguments or {}
    store = EventStore()
    session_id = None
    if arguments.get("open_session"):
        session_id = store.open_session(model=arguments.get("model", "mcp"))
    text = DeltaBriefingGenerator(store).generate(current_session_id=session_id)
    return {"briefing_markdown": text, "session_id": session_id}


def mcp_state_bridge_checkpoint(arguments: dict | None = None) -> dict:
    """MCP tool: record a checkpoint event."""
    arguments = arguments or {}
    sid = arguments.get("session_id") or "ad-hoc"
    summary = arguments.get("summary", "checkpoint")
    detail = arguments.get("detail") or {}
    entity_key = arguments.get("entity_key") or "session"
    eid = EventStore().record_event(
        session_id=sid,
        event_type="checkpoint",
        entity_type="session",
        entity_key=entity_key,
        summary=summary,
        detail=detail,
    )
    return {"event_id": eid, "recorded_at": datetime.now(timezone.utc).isoformat()}


MCP_TOOLS = [
    {
        "name": "state_bridge_briefing",
        "description": "Get session continuity briefing — delta since last session",
        "handler": mcp_state_bridge_briefing,
        "input_schema": {
            "type": "object",
            "properties": {
                "open_session": {"type": "boolean",
                                  "description": "If true, open a new session record"},
                "model": {"type": "string"},
            },
        },
    },
    {
        "name": "state_bridge_checkpoint",
        "description": "Record a session checkpoint event",
        "handler": mcp_state_bridge_checkpoint,
        "input_schema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "summary": {"type": "string"},
                "entity_key": {"type": "string"},
                "detail": {"type": "object"},
            },
            "required": ["summary"],
        },
    },
]


if __name__ == "__main__":
    sys.exit(main())
